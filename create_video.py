import sys
import os
import re
import asyncio
from playwright.async_api import async_playwright
import mimetypes
import argparse
import json
import time
from typing import Literal
from utils import prewrite_file

# --- 视频参数 ---
WIDTH, HEIGHT = 1080, 2160
DURATION_SECONDS = 10
FPS = 30
TOTAL_FRAMES = DURATION_SECONDS * FPS
WEB_FILE_ROOT = os.path.join(os.getcwd(),'html')
PAGE = 'index.html'

mimetypes.init()
mimetypes.add_type('application/javascript', '.js')

async def context_routes(route, request): 
    if request.url.startswith(f'http://portrait-lyrics-video-maker/'):
        file_path = os.path.join(WEB_FILE_ROOT, re.match(r'.*://portrait-lyrics-video-maker/(.*)', request.url).group(1))
        if os.path.isfile(file_path):
            content_type, _ = mimetypes.guess_file_type(file_path)
            await route.fulfill(path=file_path, content_type=content_type)
        else:
            await route.abort()
    else:
        await route.continue_()


async def main():
    """
    主函数：生成所有视频帧并输出到 stdout
    """
    async with async_playwright() as p:
        # 启动一个无头浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.route("**/*", context_routes)

        page = await context.new_page()

        # 设置视口大小，确保截图尺寸一致
        await page.set_viewport_size({"width": WIDTH, "height": HEIGHT})

        html_path = f"http://portrait-lyrics-video-maker/{PAGE}"
        await page.goto(html_path, wait_until='load')

        # print(page.url, await page.title())
        # await(page.screenshot(path='test.png'))

        controller = await page.evaluate_handle("window.lv.controller")

        # print(await controller.evaluate('(controller) => controller.testMessage'))
        # return

        await controller.evaluate('async (controller, data) => await controller.setup(data.config_path)')

        # --- 帧生成循环 ---
        for i in range(TOTAL_FRAMES):

            # 在浏览器页面上执行 JS 函数来更新帧内容
            await controller.evaluate('(controller, data) => controller.updateFrame(data.frame, data.frame_rate)', {
                "frame": i,
                "frame_rate": FPS
            })
            
            # 截取当前页面，不保存为文件，而是获取其二进制数据
            screenshot_bytes = await page.screenshot(type="png")
            
            try:
                # 将 PNG 图像的二进制数据写入标准输出流
                sys.stdout.buffer.write(screenshot_bytes)
            except BrokenPipeError:
                # 当 FFmpeg 进程关闭管道时，会发生此错误。
                # 这是正常行为，意味着视频编码完成或被中断。
                print("FFmpeg pipe closed. Exiting script.", file=sys.stderr)
                break
            
            # 在标准错误流中打印进度，避免污染输出管道
            print(f"Generated frame {i + 1}/{TOTAL_FRAMES}", file=sys.stderr)

        await browser.close()



type TempFile = dict

class HtmlTempManager:
    def __init__(self):
        self.temp_files = {}
    def _generate_id(self) -> int:
        if not self._id_counter: self._id_counter = 0
        self._id_counter += 1
        return self._id_counter - 1
        
    def add_temp_file(self, name: str, content: str|bytes) -> TempFile:
        target_path = os.path.join(WEB_FILE_ROOT, f'{name.split(".")[0]}_{int(time.time())}.{name.split(".")[-1]}')
        prewrite_file(target_path)

        if isinstance(content, str):
            content = content.encode('utf-8')
        with open(target_path, 'wb') as f:
            f.write(content)
        url_path = os.path.relpath(target_path, WEB_FILE_ROOT)
        id = self._generate_id()
        temp_file = {
            "name": name,
            "id": id,
            "path": target_path,
            "url_path": url_path,
        }
        self.temp_files[id] = temp_file
        return temp_file
    
    def get_temp_file_by_name(self, name: str) -> TempFile|None:
        for temp_file in self.temp_files.values():
            if temp_file['name'] == name:
                return temp_file
        return None
    
    def remove_temp_file(self, id: int) -> None:
        temp_file = self.temp_files.pop(id, None)
        if not temp_file: return

        os.remove(temp_file['path'])
        return
    
    def remove_all(self) -> None:
        for id in self.temp_files.keys():
            self.remove_temp_file(id)
        return

class Config:
    def __init__(self, config_path: str|None = None):
        self.config = {}
        self.mode = 'single'
        if config_path: self.load_from_file(config_path)
    
    def set_mode(self, mode: Literal['single', 'playlist']):
        self.mode = mode

    def set_config(self, key: str, value) -> None:
        if self.mode == 'single':
            self.config[key] = value

    def load_lyrics(self, lyrics_file: str|None = None, lyrics: str|None = None) -> None:
        if not lyrics_file and not lyrics: return
        if lyrics:
            self.set_config('lyrics', lyrics)
        
    def load_from_file(self, config_path: str) -> None:
        input_config = json.load(open(config_path))

        get = lambda key: input_config.get(key)
        if get('mode') == 'single':
            self.set_mode('single')
            if get('title'): self.set_config('title', get('title'))
            if get('artist'): self.set_config('artist', get('artist'))
            if get('duration'): self.set_config('duration', get('duration'))
            self.load_lyrics(get('lyrics_file'), get('lyrics'))
    
    def save(self, output_path: str) -> None:
        output = {
            **self.config,
            "mode": self.mode
        }
        prewrite_file(output_path)
        json.dump(output, open(output_path, 'w', encoding='utf-8'), indent=4)

    def to_temp_file(self, htm: HtmlTempManager) -> TempFile:
        return htm.add_temp_file('config.json', json.dumps(self.config, indent=4))


htm = HtmlTempManager()
con = Config()


def run():
    parser = argparse.ArgumentParser(description='Generate a vertical lyrics video.')
    parser.add_argument('input', type=str, help='Path to the input file(s).\nShould be a .json config file or a directory with music and lyrics files.')
    parser.add_argument('output', type=str, help='Path to the output video file.\nShould end with .mp4')
    parser.add_argument('-c', '--config', action='store_true', help='Flag to indicate that the input is a config file.')
    args = parser.parse_args()

    print("hello.")
    if os.path.isfile(args.input):
        if args.config or args.input.endswith('.json'):
            con.load_from_file(args.input)
            print(con.mode, con.config)
        else:
            raise ValueError("Input file should be a .json config file or a directory with music and lyrics files.")
    else:
        print("Input is a directory.")
        pass 

    return
    asyncio.run(main())

if __name__ == "__main__":
    run()