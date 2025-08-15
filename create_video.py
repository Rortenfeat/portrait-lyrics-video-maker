import sys
import os
import subprocess
import asyncio
from playwright.async_api import async_playwright
import mimetypes
import argparse
from utils import prewrite_file, HtmlTempManager
from config import Config
from urllib.parse import urljoin, urlparse

# --- Video generation constants ---
WIDTH, HEIGHT = 1080, 2160
# DURATION_SECONDS = 10
FPS = 30 # Frames per second
CRF = '18' # Constant Rate Factor
WEB_FILE_ROOT = os.path.join(os.getcwd(),'html')
HOMEPAGE = 'index.html'
URL_PREFIX = 'http://portrait-lyrics-video-maker/'

mimetypes.init()
mimetypes.add_type('application/javascript', '.js')

async def context_routes(route, request): 
    if request.url.startswith(URL_PREFIX):
        file_path = os.path.join(WEB_FILE_ROOT, urlparse(request.url).path[1:])
        if os.path.isfile(file_path):
            content_type, _ = mimetypes.guess_file_type(file_path)
            await route.fulfill(path=file_path, content_type=content_type)
        else:
            await route.abort()
    else:
        await route.continue_()


async def main(config: Config, config_path: str, output_path: str):
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

        html_path = urljoin(URL_PREFIX, HOMEPAGE)
        await page.goto(html_path, wait_until='load')

        # print(page.url, await page.title())
        # await(page.screenshot(path='test.png'))

        controller = await page.evaluate_handle("window.lv.controller")

        # print(await controller.evaluate('(controller) => controller.testMessage'))
        # return

        await controller.evaluate('async (controller, data) => await controller.setup(data.config_path)', {
            "config_path": config_path
        })

        # Video configuration
        duration = 10
        if config.mode == 'single':
            duration = config.config.get('duration', 10)
        elif config.mode == 'playlist':
            pass # [TODO]

        total_frames = int(duration * FPS)

        # FFmpeg command line arguments
        ffmpeg_command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-f', 'image2pipe',
            '-framerate', str(FPS),
            '-s', f'{WIDTH}x{HEIGHT}',
            '-i', '-',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-crf', CRF,
            output_path,
        ]
        prewrite_file(output_path)

        # Lauch FFmpeg process
        print(f"Starting FFmpeg process: {' '.join(ffmpeg_command)}")
        ffmpeg_process = subprocess.Popen(
            ffmpeg_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=sys.stderr
        )

        # --- 帧生成循环 ---
        for i in range(total_frames):

            # 在浏览器页面上执行 JS 函数来更新帧内容
            await controller.evaluate('(controller, data) => controller.updateFrame(data.frame, data.frame_rate)', {
                "frame": i,
                "frame_rate": FPS
            })
            
            # 截取当前页面，不保存为文件，而是获取其二进制数据
            screenshot_bytes = await page.screenshot(type="png")
            
            try:
                # 将 PNG 图像的二进制数据写入FFmpeg
                if ffmpeg_process.stdin:
                    ffmpeg_process.stdin.write(screenshot_bytes)
            except BrokenPipeError:
                # 当 FFmpeg 进程关闭管道时，会发生此错误。
                print("FFmpeg process exited unexpectedly. Aborting.", file=sys.stderr)
                break
            
            # 在标准错误流中打印进度，避免污染输出管道
            print(f"Generated frame {i + 1}/{total_frames}", file=sys.stderr)

        await browser.close()
        print("Frame generation complete.")

        if ffmpeg_process.stdin:
            ffmpeg_process.stdin.close()
        ffmpeg_process.wait()
        print("FFmpeg process finished.")




def run():
    parser = argparse.ArgumentParser(description='Generate a vertical lyrics video.')
    parser.add_argument('config', type=str, help='Path to the config file.')
    parser.add_argument('output', type=str, help='Path to the output video file. Should end with .mp4')
    # parser.add_argument('-c', '--config', action='store_true', help='Flag to indicate that the input is a config file.')
    args = parser.parse_args()

    # print("hello.")
    if os.path.isfile(args.config):
        con = Config(args.config)
        if not con.is_valid():
            print("Invalid config file.")
            return
        print("Config loaded.")
        print(str(con))
        ans = input("Continue? (y/n)")
        if ans.lower() != 'y': return

        htm = HtmlTempManager(WEB_FILE_ROOT)
        config_temp = htm.add_temp_file('config.json', con.to_json())
        config_temp_path = urljoin(URL_PREFIX, config_temp['url_path'])

        asyncio.run(main(con, config_temp_path, args.output))

    else:
        print("Config file not found.")

    return

if __name__ == "__main__":
    run()