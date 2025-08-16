import json
import argparse
from utils import prewrite_file, get_audio_metadata, is_valid_audio_file, get_lrc_file_path, load_lyrics
import os

class Config:
    BASIC_KEYS = ['title', 'artist', 'album', 'duration']

    def __init__(self, config_path: str|None = None):
        self.config = {}
        self.mode = 'single'
        if config_path: self.load_from_file(config_path)
    
    @property
    def mode(self) -> str|None:
        return self.config.get('mode')
    
    @mode.setter
    def mode(self, value: str) -> None:
        self.config['mode'] = value

    def set_config(self, key: str, value) -> None:
        if self.mode == 'single':
            self.config[key] = value

    def load_from_file(self, config_path: str) -> None:
        if not os.path.isfile(config_path): return

        input_config = json.load(open(config_path))
        config_dir = os.path.abspath(os.path.dirname(config_path))
        self.config_dir = config_dir

        get = lambda key: input_config.get(key)
        if get('mode') == 'single':
            self.mode = 'single'
            for key in self.BASIC_KEYS:
                if get(key): self.set_config(key, get(key))
            lyrics = get('lyrics')
            if get('lyrics_path'):
                lyrics_path = os.path.join(config_dir, get('lyrics_path'))
                lyrics = load_lyrics(lyrics_path, lyrics)
            if lyrics: self.set_config('lyrics', lyrics)
        elif get('mode') == 'playlist':
            self.mode = 'playlist'
            if get('playlist'):
                self.config['playlist'] = []
                playlist = get('playlist')
                for song in playlist:
                    song_ = {}
                    for key in self.BASIC_KEYS:
                        if song.get(key): song_[key] = song.get(key)
                    lyrics = song.get('lyrics')
                    if song.get('lyrics_path'):
                        lyrics_path = os.path.join(config_dir, song.get('lyrics_path'))
                        lyrics = load_lyrics(lyrics_path, lyrics)
                    if lyrics: song_['lyrics'] = lyrics
                    self.set_song_config(**song_)
        return

    
    def set_song_config(self, **kwargs) -> None:
        if self.mode == 'single':
            for key in self.BASIC_KEYS:
                if key in kwargs: self.set_config(key, kwargs[key])
            if 'lyrics' in kwargs: self.set_config('lyrics', kwargs['lyrics'])
        elif self.mode == 'playlist':
            if not 'playlist' in self.config: self.config['playlist'] = []
            playlist = self.config['playlist']
            if 'index' in kwargs:
                index = kwargs['index']
                if index < 0 or index >= len(playlist):
                    raise ValueError('Index out of range.')
                song = playlist[index]
                for key in self.BASIC_KEYS:
                    if key in kwargs: song[key] = kwargs[key]
                if 'lyrics' in kwargs: song['lyrics'] = kwargs['lyrics']
            else:
                song = {}
                for key in self.BASIC_KEYS:
                    if key in kwargs: song[key] = kwargs[key]
                if 'lyrics' in kwargs: song['lyrics'] = kwargs['lyrics']
                playlist.append(song)
        return

    
    
    def load_song(self, song_path: str) -> None:
        metadata = get_audio_metadata(song_path)

        song = {}

        if not metadata or 'format' not in metadata:
            print(f'{song_path} is not a valid audio file.')
            return
    
        # 1. 获取持续时间 (Duration)
        # 持续时间通常在 'format' -> 'duration' 字段中，单位是秒
        duration_seconds = float(metadata['format'].get('duration', 0))
        if duration_seconds: song['duration'] = duration_seconds
    
        # 2. 获取 Tags (标题、艺术家、歌词等)
        # Tags 信息通常在 'format' -> 'tags' 字典中
        tags = metadata['format'].get('tags', {})
        
        # 提取标题 (Title)
        # .get() 方法可以避免因标签不存在而导致的 KeyError
        title = tags.get('title', None)
        if title: song['title'] = title
    
        # 提取艺术家 (Artist)
        artist = tags.get('artist', None)
        if artist: song['artist'] = artist
        
        # 提取专辑 (Album)
        album = tags.get('album', None)
        if album: song['album'] = album
    
        # 提取歌词 (Lyrics)
        # 歌词的标签键名可能不统一，常见的有 'lyrics', 'lyrics-eng', 'UNSYNCEDLYRICS' 等
        # 这里我们做一个不区分大小写的查找
        lyrics = None
        for key, value in tags.items():
            if 'lyrics' in key.lower():
                lyrics = value
                break
        lrc_file = get_lrc_file_path(song_path)
        lyrics = load_lyrics(lrc_file, lyrics)
        if lyrics: song['lyrics'] = lyrics
        
        self.set_song_config(**song)


    def parse_song(self, *song_paths):
        for song_path in song_paths:
            if is_valid_audio_file(song_path):
                self.load_song(song_path)
                if self.mode == 'single': return
            elif os.path.isdir(song_path):
                for file_name in os.listdir(song_path):
                    file_path = os.path.join(song_path, file_name)
                    if is_valid_audio_file(file_path):
                        self.load_song(file_path)
                        if self.mode == 'single': return
        return


    def save(self, output_path: str) -> None:
        # output = {
        #     **self.config,
        #     "mode": self.mode
        # }
        prewrite_file(output_path)
        json.dump(self.config, open(output_path, 'w', encoding='utf-8'), indent=4, ensure_ascii=False)

    def to_json(self) -> str:
        return json.dumps(self.config, indent=4, ensure_ascii=False)
    
    def is_valid(self) -> bool:
        if self.mode == 'single':
            for key in self.BASIC_KEYS:
                if not self.config.get(key): return False
            if not self.config.get('lyrics'): return False
        elif self.mode == 'playlist':
            if not self.config.get('playlist'): return False
            for song in self.config['playlist']:
                for key in self.BASIC_KEYS:
                    if not song.get(key): return False
                if not song.get('lyrics'): return False
        else: return False
        return True
    
    def __str__(self) -> str:
        if not self.config:
            return 'This configuration is empty.'
        def shorten(text: str) -> str:
            if len(text) > 20:
                return text[:17] + '...'
            return text
        def get(key: str) -> str:
            res = self.config.get(key)
            if not res: res = 'UNDEFINED'
            return str(res)
        
        res = ''
        if self.mode =='single':
            res += '=========================' + '\n'
            res += f'Mode: single' + '\n'
            for key in self.BASIC_KEYS:
                res += f'{key.capitalize()}: {get(key)}' + '\n'
            res += f'Lyrics: {shorten(get("lyrics"))}' + '\n'
            res += '=========================' + '\n'
        elif self.mode == 'playlist':
            res += '=========================' + '\n'
            res += f'Mode: playlist' + '\n'
            # res += f'Title: {get("title")}' + '\n'
            res += 'Playlist:' + '\n'
            if ( self.config['playlist'] ):
                for i, song in enumerate(self.config['playlist']):
                    def get_(key) -> str:
                        res = song.get(key)
                        if not res: res = 'UNDEFINED'
                        return str(res)
                    res += f'    Index: {i}' + '\n'
                    for key in self.BASIC_KEYS:
                        res += f'        {key.capitalize()}: {get_(key)}' + '\n'
                    res += f'        Lyrics: {shorten(get_("lyrics"))}' + '\n'
            else:
                res += '    Playlist is empty.' + '\n'
            res += '=========================' + '\n'
        return res

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', type=str, choices=['read', 'write'], help='To read or write the config file.')
    parser.add_argument('config_path', type=str, help='Path to the config file to read or write.')
    parser.add_argument('-m', '--mode', type=str, choices=['single', 'playlist'], default=None, help='Available when "write" is specified. Set the mode of the config file. Default is "single".')
    parser.add_argument('-s', '--song', nargs='+', type=str, help='Available when "write" is specified. It can be one or multiple song files or folders containing songs, and the program will recognize the song information as configuration. When the config mode is "single", only the first song file found will take effect.')
    parser.add_argument('-i', '--index', type=int, help='Available when "write" is specified. Required when setting a existing song in "playlist" mode. The index can be found by checking "read" command.')
    parser.add_argument('-t', '--title', type=str, help='Available when "write" is specified. Set the title of the song.')
    parser.add_argument('-a', '--artist', type=str, help='Available when "write" is specified. Set the artist of the song.')
    parser.add_argument('-A', '--album', type=str, help='Available when "write" is specified. Set the album of the song.')
    parser.add_argument('-d', '--duration', type=float, help='Available when "write" is specified. Set the duration of the song in seconds.')
    parser.add_argument('-l', '--lyrics-file', type=str, help='Available when "write" is specified. Set the path to the file containing the lyrics of the song.')

    args = parser.parse_args()

    config = Config(args.config_path)
    if args.command == 'read':
        print(str(config))
    elif args.command == 'write':
        mode = config.mode
        if args.mode:
            mode = args.mode
            config.mode = mode
        # print(mode)
        if mode == 'single':
            if args.song:
                config.parse_song(*args.song)
            else:
                song = {}
                if args.title: song['title'] = args.title
                if args.artist: song['artist'] = args.artist
                if args.album: song['album'] = args.artist
                if args.duration: song['duration'] = args.duration
                if args.lyrics_file:
                    lyrics = load_lyrics(args.lyrics_file)
                    if lyrics: song['lyrics'] = lyrics
                config.set_song_config(**song)
        elif mode == 'playlist':
            if args.song:
                config.parse_song(*args.song)
            else:
                song = {}
                if args.index or args.index == 0: song['index'] = args.index
                if args.title: song['title'] = args.title
                if args.artist: song['artist'] = args.artist
                if args.album: song['album'] = args.artist
                if args.duration: song['duration'] = args.duration
                if args.lyrics_file:
                    lyrics = load_lyrics(args.lyrics_file)
                    if lyrics: song['lyrics'] = lyrics
                config.set_song_config(**song)
        print('Writting config:')
        print(str(config))
        ans = input('Are you sure to save the config? (y/n) ')
        if ans.lower() == 'y':
            config.save(args.config_path)
            print(f'Config saved to {args.config_path}.')
    return



if __name__ == '__main__':
    main()