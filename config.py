import json
import argparse
from utils import prewrite_file
import os

class Config:
    def __init__(self, config_path: str|None = None):
        self.config = {}
        self.mode = 'single'
        if config_path: self.load_from_file(config_path)
    
    def set_mode(self, mode: str):
        self.mode = mode
        self.config['mode'] = mode

    def set_config(self, key: str, value) -> None:
        if self.mode == 'single':
            self.config[key] = value

    def load_lyrics(self, lyrics_path: str|None = None, lyrics: str|None = None) -> None:
        if not lyrics_path and not lyrics: return
        if lyrics:
            self.set_config('lyrics', lyrics)
        else:
            config_dir = self.config_dir if self.config_dir else os.getcwd()
            lyrics_path = os.path.join(config_dir, lyrics_path)
            with open(lyrics_path, 'r', encoding='utf-8') as f:
                self.set_config('lyrics', f.read())
        
    def load_from_file(self, config_path: str) -> None:
        input_config = json.load(open(config_path))
        config_dir = os.path.abspath(os.path.dirname(config_path))
        self.config_dir = config_dir

        get = lambda key: input_config.get(key)
        if get('mode') == 'single':
            self.set_mode('single')
            if get('title'): self.set_config('title', get('title'))
            if get('artist'): self.set_config('artist', get('artist'))
            if get('duration'): self.set_config('duration', get('duration'))
            self.load_lyrics(get('lyrics_path'), get('lyrics'))
    
    def save(self, output_path: str) -> None:
        # output = {
        #     **self.config,
        #     "mode": self.mode
        # }
        prewrite_file(output_path)
        json.dump(self.config, open(output_path, 'w', encoding='utf-8'), indent=4)

    def to_json(self) -> str:
        return json.dumps(self.config, indent=4, ensure_ascii=False)
    
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
            res += f'Title: {get("title")}' + '\n'
            res += f'Artist: {get("artist")}' + '\n'
            res += f'Duration: {get("duration")}' + '\n'
            res += f'Lyrics: {shorten(get("lyrics"))}' + '\n'
            res += '=========================' + '\n'
        elif self.mode == 'playlist':
            res += '=========================' + '\n'
            res += f'Mode: playlist' + '\n'
            res += f'Title: {get("title")}' + '\n'
            res += 'Playlist:' + '\n'
            if ( self.config['playlist'] ):
                for i, song in enumerate(self.config['playlist']):
                    def get(key) -> str:
                        res = song.get(key)
                        if not res: res = 'UNDEFINED'
                        return str(res)
                    res += f'    {str(i+1).rjust(2)}) Title: {get("title")}' + '\n'
                    res += f'        Artist: {get("artist")}' + '\n'
                    res += f'        Duration: {get("duration")}' + '\n'
                    res += f'        Lyrics: {get("lyrics")}' + '\n'
            else:
                res += '    Playlist is empty.' + '\n'
            res += '=========================' + '\n'
        return res

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', type=str, choices=['read', 'write'], help='To read or write the config file.')
    parser.add_argument('config_path', type=str, help='Path to the config file to read or write.')
    parser.add_argument('-m', '--mode', type=str, choices=['single', 'playlist'], help='Available when "write" is specified. Set the mode of the config file. Required when creating a new config file.')
    parser.add_argument('-s', '--song', nargs='+', type=str, help='Available when "write" is specified. It can be one or multiple song files or folders containing songs, and the program will recognize the song information as configuration. When the config mode is "single", only the first song file found will take effect.')
    parser.add_argument('-i', '--index', type=int, help='Available when "write" is specified. Required when setting a song in "playlist" mode. The index can be found by checking "read" command.')
    parser.add_argument('-t', '--title', type=str, help='Available when "write" is specified. Set the title of the song.')
    parser.add_argument('-a', '--artist', type=str, help='Available when "write" is specified. Set the artist of the song.')
    parser.add_argument('-d', '--duration', type=int, help='Available when "write" is specified. Set the duration of the song in seconds.')
    parser.add_argument('-l', '--lyrics-file', type=str, help='Available when "write" is specified. Set the path to the file containing the lyrics of the song.')

    args = parser.parse_args()

    config = Config(args.config_path)
    if args.command == 'read':
        print(str(config))

if __name__ == '__main__':
    main()