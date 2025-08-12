import sys
import os
import asyncio
from playwright.async_api import async_playwright

# --- 视频参数 ---
WIDTH, HEIGHT = 800, 600
DURATION_SECONDS = 10
FPS = 30
TOTAL_FRAMES = DURATION_SECONDS * FPS

async def main():
    """
    主函数：生成所有视频帧并输出到 stdout
    """
    async with async_playwright() as p:
        # 启动一个无头浏览器
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # 设置视口大小，确保截图尺寸一致
        await page.set_viewport_size({"width": WIDTH, "height": HEIGHT})

        # 打开本地的 HTML 文件
        html_path = f"file://{os.path.abspath('animation.html')}"
        await page.goto(html_path)

        # --- 帧生成循环 ---
        for i in range(TOTAL_FRAMES):
            # 计算当前时间和进度
            current_time = DURATION_SECONDS - (i / FPS)
            progress = i / (TOTAL_FRAMES - 1)

            # 在浏览器页面上执行 JS 函数来更新帧内容
            await page.evaluate(f"updateFrame({current_time}, {progress})")
            
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

if __name__ == "__main__":
    asyncio.run(main())