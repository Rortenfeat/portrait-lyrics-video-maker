import os
import subprocess
import sys
import json
import time
from typing import TypedDict
import atexit

def prewrite_file(path: str) -> None:
    path = os.path.abspath(path)
    if os.path.isfile(path):
        save_print(f"File {path} will be overwritten.")
    else:
        dir = os.path.dirname(path)
        if not os.path.exists(dir):
            os.makedirs(dir)
    return

def save_print(text: str) -> None:
    pass

def get_audio_metadata(file_path: str) -> dict|None:
    """
    使用 ffprobe 获取音频文件的元数据. 

    :param file_path: 音频文件的路径
    :return: 一个包含元数据信息的字典, 如果出错则返回 None
    """
    try:
        # 构建 ffprobe 命令
        # -v quiet:       减少不必要的日志输出
        # -print_format json: 输出为 JSON 格式
        # -show_format:   显示容器格式信息（包含时长、标签等）
        # -show_streams:  显示流信息（如果需要编码、采样率等）
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]

        # 执行命令并捕获输出
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True, # 如果 ffprobe 返回非零退出码, 则抛出异常
            encoding='utf-8' # 确保正确解码输出
        )

        # 解析 JSON 输出
        metadata = json.loads(result.stdout)
        return metadata

    except FileNotFoundError:
        print("错误: 'ffprobe' 命令未找到. 请确保 FFmpeg 已安装并位于系统的 PATH 中. ", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"错误: ffprobe 执行失败. 返回码: {e.returncode}", file=sys.stderr)
        print(f"ffprobe 输出: {e.stderr}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("错误: 解析 ffprobe 的 JSON 输出失败. ", file=sys.stderr)
        return None
    
def is_valid_audio_file(file_path: str) -> bool:
    if not os.path.isfile(file_path): return False
    ext = os.path.basename(file_path).split('.')[-1]
    if ext.lower() not in ['mp3', 'wav', 'flac', 'ogg', 'opus', 'aac', 'm4a', 'aiff', '.aif', 'alac']: return False
    return True

def get_lrc_file_path(audio_file_path: str) -> str|None:
    audio_dir = os.path.dirname(audio_file_path)
    audio_name = os.path.basename(audio_file_path).split('.')[0]
    for file_name in os.listdir(audio_dir):
        if file_name.startswith(audio_name) and file_name.endswith('.lrc'):
            return os.path.join(audio_dir, file_name)
    return None

def load_lyrics(lyrics_path: str|None = None, lyrics: str|None = None) -> str|None:
    if not lyrics_path and not lyrics: return
    if lyrics_path:
        with open(lyrics_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return lyrics
    
class TempFile(TypedDict):
    name: str
    id: int
    path: str
    url_path: str

class HtmlTempManager:
    def __init__(self, root_path: str):
        self.temp_files = {}
        self.root_path = root_path
        self._id_counter = 0
        atexit.register(self.remove_all)

    def _generate_id(self) -> int:
        self._id_counter += 1
        return self._id_counter
        
    def add_temp_file(self, name: str, content: str|bytes) -> TempFile:
        target_path = os.path.join(self.root_path, 'temp', f'{name.split(".")[0]}_{int(time.time())}.{name.split(".")[-1]}')
        prewrite_file(target_path)

        if isinstance(content, str):
            content = content.encode('utf-8')
        with open(target_path, 'wb') as f:
            f.write(content)

        url_path = os.path.relpath(target_path, self.root_path)
        url_path = url_path.replace('\\', '/')

        id = self._generate_id()
        temp_file: TempFile = {
            "name": name,
            "id": id,
            "path": target_path,
            "url_path": url_path,
        }
        print(temp_file)
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
        for id in list(self.temp_files.keys()):
            self.remove_temp_file(id)
        return
    