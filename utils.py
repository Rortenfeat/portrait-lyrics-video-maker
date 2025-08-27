import os
import sys
import json
import time
from typing import TypedDict
import atexit
import mutagen
from mutagen._file import File
from mutagen.id3 import ID3
import base64

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

def get_audio_metadata(filepath):
    """
    从音频文件中提取详细的元数据。

    :param filepath: 音频文件的路径
    :return: 一个包含元数据的字典，如果无法处理则返回 None
    """
    if not os.path.exists(filepath):
        return None

    try:
        audio = File(filepath)
        if audio is None:
            print(f"Error: Mutagen can not handle this file {filepath}.")
            return None

        metadata = {
            'title': None,
            'artist': None,
            'album': None,
            'duration': 0,
            'lyrics': None,
            'cover-base64-url': None
        }

        # 1. 获取时长
        if audio.info:
            metadata['duration'] = float(audio.info.length)

        # 2. 获取标签 (标题, 艺术家, 专辑, 歌词)
        # 不同格式的标签键名不同，我们尝试兼容
        # MP3 (ID3)
        if isinstance(audio.tags, ID3):
            metadata['title'] = audio.tags.get('TIT2', [None])[0] # type: ignore
            metadata['artist'] = audio.tags.get('TPE1', [None])[0] # type: ignore
            metadata['album'] = audio.tags.get('TALB', [None])[0] # type: ignore
            # 歌词通常在 USLT 帧中
            uslt_frame = audio.tags.getall('USLT')
            if uslt_frame:
                metadata['lyrics'] = uslt_frame[0].text
        # FLAC, OGG (Vorbis Comments)
        else:
            metadata['title'] = audio.tags.get('title', [None])[0]
            metadata['artist'] = audio.tags.get('artist', [None])[0]
            metadata['album'] = audio.tags.get('album', [None])[0]
            metadata['lyrics'] = audio.tags.get('lyrics', [None])[0]
            
            
        # 3. 获取封面并转换为 Base64 Data URL
        artwork_data = None
        mime_type = None

        # MP3 (ID3)
        # if 'APIC:' in audio.tags:
        #     artwork_data = audio.tags['APIC:'].data
        #     mime_type = audio.tags['APIC:'].mime
        # FLAC, M4A, etc.
        # elif 'picture' in audio:
        #     artwork_data = audio.pictures[0].data
        #     mime_type = audio.pictures[0].mime

        for key in audio.keys():
            if key == 'pictures':
                artwork_data = audio.pictures[0].data
                mime_type = audio.pictures[0].mime
            elif key.startswith('APIC:'):
                artwork_data = audio.tags[key].data
                mime_type = audio.tags[key].mime
        
        if artwork_data and mime_type:
            base64_data = base64.b64encode(artwork_data).decode('utf-8')
            metadata['cover-base64-url'] = f"data:{mime_type};base64,{base64_data}"

        return metadata

    except Exception as e:
        print(f"Error while getting metadata from {filepath}: {e}")
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
    