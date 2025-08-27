import sys
import os
import subprocess
import asyncio
from playwright.async_api import async_playwright
import mimetypes
import argparse
from utils import prewrite_file, HtmlTempManager, is_valid_audio_file
from config import Config
from urllib.parse import urljoin, urlparse
import time
from tqdm import tqdm
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

load_dotenv()

# --- Video generation constants ---
WIDTH = int(os.environ.get('VIDEO_WIDTH', '1080'))
HEIGHT = int(os.environ.get('VIDEO_HEIGHT', '2160'))
FPS = int(os.environ.get('VIDEO_FPS', '30'))
CRF = os.environ.get('VIDEO_CRF', '20')
WEB_FILE_ROOT = os.path.abspath(os.environ.get('WEB_ROOT_PATH', 'html'))
HOMEPAGE = os.environ.get('HOMEPAGE', 'index.html')
URL_PREFIX = 'http://portrait-lyrics-video-maker/'
FORCE_VALID_CONFIG = os.environ.get('FORCE_VALID_CONFIG', 'false').lower() == 'true'

mimetypes.init()
mimetypes.add_type('application/javascript', '.js')

htm = HtmlTempManager(WEB_FILE_ROOT)

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

async def clear_queue(q: asyncio.Queue):
    while not q.empty():
        try:
            q.get_nowait()
        except asyncio.QueueEmpty:
            break

async def main(config: Config, config_path: str, output_path: str):
    """
    主函数：生成所有视频帧并输出到 stdout
    """

    async with async_playwright() as p:
        # 启动一个无头浏览器
        async with await p.chromium.launch(headless=True) as browser:
            context = await browser.new_context()
            await context.route("**/*", context_routes)

            page = await context.new_page()

            # cdp = await page.context.new_cdp_session(page)

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
            duration_list = config.get_duration_list()
            if not duration_list:
                raise ValueError("Duration list is empty.")
            frames_list = [int(d * FPS) for d in duration_list]
            total_frames = sum(frames_list)

            audio_list = config.get_audio_list()

            audio_list_text = ''
            for audio in audio_list:
                if not os.path.isfile(audio) or not is_valid_audio_file(audio):
                    raise ValueError(f"Invalid audio file: {audio}")
                if "'" in audio:
                    raise ValueError(f"Audio file name contains apostrophe: {audio}")
                audio_list_text += f"file '{audio.replace("\\", "/")}'\n"

            audio_list_path = htm.add_temp_file('audio_list.txt', audio_list_text).get('path')

            # FFmpeg command line arguments
            ffmpeg_command = [
                'ffmpeg',
                '-y',  # Overwrite output file if it exists

                # Video input
                '-f', 'image2pipe',
                '-framerate', str(FPS),
                '-s', f'{WIDTH}x{HEIGHT}',
                '-c:v', 'mjpeg',
                '-color_range', 'pc',
                '-i', '-',

                # Audio input
                '-f', 'concat',
                '-safe', '0',  # Allow absolute paths
                '-i', audio_list_path,

                # Output
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', CRF,
                '-color_range', 'tv',
                '-colorspace', 'bt709',
                '-color_primaries', 'bt709',
                '-color_trc', 'bt709',

                '-c:a', 'aac',
                '-b:a', '320k',

                # Stream mapping
                '-map', '0:v:0',
                '-map', '1:a:0',

                '-shortest',  # Shortest possible duration
                output_path,
            ]
            prewrite_file(output_path)

            ffmpeg_log_file = open('ffmpeg.log', 'w', encoding='utf-8')

            # Lauch FFmpeg process
            print(f"Starting FFmpeg process: {' '.join(ffmpeg_command)}")
            ffmpeg_process = subprocess.Popen(
                ffmpeg_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=ffmpeg_log_file
            )

            # frame_queue = asyncio.Queue()
            # async def on_screencast_frame(event):
            #     # print(f"Received frame {event['sessionId']}")
            #     await frame_queue.put(event)
                
            # cdp.on('Page.screencastFrame', on_screencast_frame)
            # await cdp.send('Page.startScreencast', {'format': 'jpeg', 'quality': 90, 'everyNthFrame': 1})






            total_time_start = time.monotonic()
            total_eval_time = 0
            total_screenshot_time = 0
            total_write_time = 0
            total_save_canvas_time = 0
            skipped_frames = 0

            
            

            # --- 帧生成循环 ---
            with tqdm(total=total_frames, desc="Generating video") as pbar:
                for i, frames in enumerate(frames_list):
                    await controller.evaluate('(controller, data) => controller.jumpToSong(data.index)', {
                            "index": i
                    })

                    pbar.set_description(f"Generating video for song {i+1}/{len(frames_list)}")

                    # 画布
                    initial_frame_buffer = BytesIO(await page.screenshot(type="jpeg", animations='disabled', scale='css', quality=90))
                    previous_screenshot_bytes = initial_frame_buffer
                    master_canvas = Image.open(initial_frame_buffer)
                    

                    for j in tqdm(range(frames), desc=f"Generating frames for song {i+1}", position=1, leave=False):

                        t_start = time.monotonic()

                        # 在浏览器页面上执行 JS 函数来更新帧内容
                        changed_bounding = await controller.evaluate('(controller, data) => {return controller.updateFrame(data.frame, data.frame_rate)}', {
                                "frame": j,
                                "frame_rate": FPS
                        })


                        t_eval_end = time.monotonic()
                        total_eval_time += t_eval_end - t_start

                        # 截取当前页面，不保存为文件，而是获取其二进制数据
                        if changed_bounding:

                            # event = await asyncio.wait_for(frame_queue.get(), timeout=0.01)

                            # patch_data = base64.b64decode(event['data'])
                            # patch_image = Image.open(BytesIO(patch_data))
                            # metadata = event['metadata']

                            x = int(changed_bounding['left'])
                            y = int(changed_bounding['top'])
                            w = int(changed_bounding['right']) - x
                            h = int(changed_bounding['bottom']) - y

                            patch_bytes = BytesIO(await page.screenshot(type="jpeg", animations='disabled', scale='css', quality=90, clip={"x": x, "y": y, "width": w, "height": h}))
                            t_screenshot_end = time.monotonic()
                            total_screenshot_time += t_screenshot_end - t_eval_end
                            
                            patch_image = Image.open(patch_bytes)

                            # 合并画布
                            master_canvas.paste(patch_image, (
                                x,
                                y
                            ))

                            screenshot_bytes = BytesIO()
                            if master_canvas.mode != 'RGB':
                                master_canvas = master_canvas.convert('RGB')
                            master_canvas.save(screenshot_bytes, format='JPEG', quality=90)

                            t_canvas_end = time.monotonic()
                            total_save_canvas_time += t_canvas_end - t_screenshot_end

                            # await cdp.send('Page.screencastFrameAck', {'sessionId': event['sessionId']})

                            # b64_str: str = (await cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 90}))["data"] # type: ignore
                            # b64_bytes = b64_str.encode('ascii')
                            # screenshot_bytes = base64.decodebytes(b64_bytes)
                            previous_screenshot_bytes = screenshot_bytes
                        else:
                            screenshot_bytes = previous_screenshot_bytes
                            skipped_frames += 1
                        


                        # await clear_queue(frame_queue)
                        t_write_start = time.monotonic()
                        try:
                            # 将 PNG 图像的二进制数据写入FFmpeg
                            if ffmpeg_process.stdin:
                                ffmpeg_process.stdin.write(screenshot_bytes.getvalue())
                        except BrokenPipeError:
                            # 当 FFmpeg 进程关闭管道时，会发生此错误。
                            print("FFmpeg process exited unexpectedly. Aborting.", file=sys.stderr)
                            break
                        
                        t_write_end = time.monotonic()
                        total_write_time += t_write_end - t_write_start

                        pbar.update(1)

                        # 在标准错误流中打印进度，避免污染输出管道
                        # print(f"Generated frame {j + 1}/{total_frames}  ", file=sys.stderr)
    
        print("Frame generation complete.")

        if ffmpeg_process.stdin:
            ffmpeg_process.stdin.close()
        ffmpeg_process.wait()
        ffmpeg_log_file.close()
        print("FFmpeg process finished.")

        total_time_end = time.monotonic()

        if config.mode == 'playlist':
            print("\n\n--- Playlist Timeline ---")
            sum_d = 0
            for i, d in enumerate(duration_list):
                hour = int(sum_d // 3600)
                minute = int(sum_d // 60 % 60)
                second = int(sum_d % 60)
                print(f'{(str(hour) + ":") if hour > 0 else ""}{minute:02d}:{second:02d} {config.config.get("playlist", [])[i].get("title", audio_list[i])}')
                sum_d += d
            
        

        
        print("\n\n--- Performance Analysis Report ---")
        total_duration = total_time_end - total_time_start
        producer_time = total_eval_time + total_screenshot_time
        print(f"Total script execution time: {total_duration:.2f} seconds")
        print(f"Generated {total_frames} frames at an average of {total_frames / total_duration:.2f} FPS.")
        print(f"Skipped screenshots of {skipped_frames} frames due to unchanged content.")
        print("-" * 35)
        print("Time spent per stage (in total):")
        print(f"  - Updating frames (JS eval): {total_eval_time:.2f} s ({total_eval_time/total_duration:.1%})")
        print(f"  - Screenshot & transfer:     {total_screenshot_time:.2f} s ({total_screenshot_time/total_duration:.1%})")
        print(f"  - Canvas:     {total_save_canvas_time:.2f} s ({total_save_canvas_time/total_duration:.1%})")
        print(f"  - Writing to FFmpeg pipe:    {total_write_time:.2f} s ({total_write_time/total_duration:.1%})")
        print("-" * 35)
        print("Average time per frame:")
        print(f"  - Update:   {total_eval_time / total_frames * 1000:.2f} ms")
        print(f"  - Screenshot: {total_screenshot_time / (total_frames - skipped_frames) * 1000:.2f} ms")
        print(f"  - Write:      {total_write_time / total_frames * 1000:.2f} ms")
        print("-" * 35)




def run():
    parser = argparse.ArgumentParser(description='Generate a vertical lyrics video.')
    parser.add_argument('config', type=str, help='Path to the config file.')
    parser.add_argument('output', type=str, help='Path to the output video file. Should end with .mp4')
    # parser.add_argument('-c', '--config', action='store_true', help='Flag to indicate that the input is a config file.')
    args = parser.parse_args()

    # print("hello.")
    if os.path.isfile(args.config):
        con = Config(args.config)
        if FORCE_VALID_CONFIG and not con.is_valid():
            print("Invalid config file.")
            return
        print("Config loaded.")
        print(str(con))
        ans = input("Continue? (y/n)")
        if ans.lower() != 'y': return

        config_temp = htm.add_temp_file('config.json', con.to_json())
        config_temp_path = urljoin(URL_PREFIX, config_temp['url_path'])

        asyncio.run(main(con, config_temp_path, args.output))


    else:
        print("Config file not found.")

    return

if __name__ == "__main__":
    run()