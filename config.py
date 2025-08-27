import json
import argparse
from utils import prewrite_file, get_audio_metadata, is_valid_audio_file, get_lrc_file_path, load_lyrics
import os

class Config:
    BASIC_SONG_KEYS = ['title', 'artist', 'album', 'duration', 'audio', 'lyrics', 'cover-base64-url']
    BASIC_GENERAL_KEYS = ['custom-message'] # testing

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

    def load_from_file(self, config_path: str) -> None:
        if not os.path.isfile(config_path): return

        input_config = json.load(open(config_path, 'r', encoding='utf-8'))
        config_dir = os.path.abspath(os.path.dirname(config_path))
        self.config_dir = config_dir

        get = lambda key: input_config.get(key)
        if get('mode') == 'single':
            self.mode = 'single'
            for key in self.BASIC_SONG_KEYS:
                if get(key): self.config[key] = get(key)
            for key in self.BASIC_GENERAL_KEYS:
                if get(key): self.config[key] = get(key)
            # lyrics = get('lyrics')
            # if get('lyrics_path'):
            #     lyrics_path = os.path.join(config_dir, get('lyrics_path'))
            #     lyrics = load_lyrics(lyrics_path, lyrics)
            # if lyrics: self.config['lyrics'] = lyrics
        elif get('mode') == 'playlist':
            self.mode = 'playlist'
            for key in self.BASIC_GENERAL_KEYS:
                if get(key): self.config[key] = get(key)
            if get('playlist'):
                self.config['playlist'] = []
                playlist = get('playlist')
                for song in playlist:
                    song_data = {}
                    for key in self.BASIC_SONG_KEYS:
                        if song.get(key): song_data[key] = song.get(key)
                    # lyrics = song.get('lyrics')
                    # if song.get('lyrics_path'):
                    #     lyrics_path = os.path.join(config_dir, song.get('lyrics_path'))
                    #     lyrics = load_lyrics(lyrics_path, lyrics)
                    # if lyrics: song_['lyrics'] = lyrics
                    self.set_song_config(**song_data)
        return

    
    def set_general_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if key in self.BASIC_GENERAL_KEYS:
                self.config[key] = value
        return

    def set_song_config(self, **kwargs) -> None:
        if self.mode == 'single':
            for key, value in kwargs.items():
                if key in self.BASIC_SONG_KEYS: self.config[key] = value
        elif self.mode == 'playlist':
            if not 'playlist' in self.config: self.config['playlist'] = []

            playlist = self.config['playlist']
            if 'index' in kwargs:
                index = kwargs['index']
                if index < 0 or index >= len(playlist):
                    raise ValueError('Index out of range.')
                song = playlist[index]
                for key, value in kwargs.items():
                    if key in self.BASIC_SONG_KEYS: song[key] = value
            else:
                song = {}
                for key, value in kwargs.items():
                    if key in self.BASIC_SONG_KEYS: song[key] = value
                playlist.append(song)
        return

    
    
    def load_song(self, song_path: str) -> None:
        metadata = get_audio_metadata(song_path)

        song = {}

        if not metadata:
            print(f'{song_path} is not a valid audio file.')
            return
    
        for key, value in metadata.items():
            if key in self.BASIC_SONG_KEYS:
                song[key] = value

        if 'title' not in song or not song['title']:
            song['title'] = os.path.basename(song_path).split('.')[0]

        song['audio'] = os.path.abspath(song_path)

        lrc_file = get_lrc_file_path(song['audio'])
        lyrics = load_lyrics(lrc_file, song.get('lyrics'))
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
            for key in self.BASIC_SONG_KEYS:
                if not self.config.get(key): return False
            if not self.config.get('lyrics'): return False
        elif self.mode == 'playlist':
            if not self.config.get('playlist'): return False
            for song in self.config['playlist']:
                for key in self.BASIC_SONG_KEYS:
                    if not song.get(key): return False
                if not song.get('lyrics'): return False
        else: return False
        return True
    
    def get_duration(self) -> float:
        return sum(self.get_duration_list())
    
    def get_duration_list(self) -> list[float] :
        if self.mode =='single':
            return [self.config.get('duration', 0.0)]
        elif self.mode == 'playlist':
            return [song.get('duration', 0.0) for song in self.config['playlist']]
        return []
    
    def get_audio_list(self) -> list[str]:
        if self.mode =='single':
            return [self.config.get('audio', '')]
        elif self.mode == 'playlist':
            return [song.get('audio', '') for song in self.config['playlist']]
        return []
    
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
            for key in self.BASIC_GENERAL_KEYS:
                res += f'{key.capitalize()}: {get(key)}' + '\n'
            for key in self.BASIC_SONG_KEYS:
                if key in ['lyrics', 'cover-base64-url']:
                    res += f'{key.capitalize()}: {shorten(get(key))}' + '\n'
                else:
                    res += f'{key.capitalize()}: {get(key)}' + '\n'
            res += '=========================' + '\n'
        elif self.mode == 'playlist':
            res += '=========================' + '\n'
            res += f'Mode: playlist' + '\n'
            for key in self.BASIC_GENERAL_KEYS:
                res += f'{key.capitalize()}: {get(key)}' + '\n'
            res += 'Playlist:' + '\n'
            if ( 'playlist' in self.config and self.config['playlist'] ):
                for i, song in enumerate(self.config['playlist']):
                    def get_(key) -> str:
                        res = song.get(key)
                        if not res: res = 'UNDEFINED'
                        return str(res)
                    res += f'    Index: {i}' + '\n'
                    for key in self.BASIC_SONG_KEYS:
                        if key in ['lyrics', 'cover-base64-url']:
                            res += f'        {key.capitalize()}: {shorten(get_(key))}' + '\n'
                        else:
                            res += f'        {key.capitalize()}: {get_(key)}' + '\n'
            else:
                res += '    Playlist is empty.' + '\n'
            res += '=========================' + '\n'
        return res
    
    def __len__(self) -> int:
        if self.mode =='single':
            return 1
        elif self.mode == 'playlist':
            return len(self.config['playlist'])
        else: return 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', type=str, choices=['read', 'write'], help='To read or write the config file.')
    parser.add_argument('config_path', type=str, help='Path to the config file to read or write.')
    parser.add_argument('-m', '--mode', type=str, choices=['single', 'playlist'], default=None, help='Available when "write" is specified. Set the mode of the config file. Default is "single".')
    parser.add_argument('-l', '--load', nargs='+', type=str, help='Available when "write" is specified. It can be one or multiple song files or folders containing songs, and the program will recognize the song information as configuration. When the config mode is "single", only the first song file found will take effect.')
    parser.add_argument('-s', '--set', nargs='*', metavar=('INDEX_OR_KEY', 'VALUE'), help='Available when "write" is specified. Set song properties. Usage: [-s [INDEX] key1 value1 key2 value2 ...]. In playlist mode, an optional numeric INDEX can be provided first to modify an existing song.')
    # parser.add_argument('-i', '--index', type=int, help='Available when "write" is specified. Required when setting a existing song in "playlist" mode. The index can be found by checking "read" command.')
    # parser.add_argument('-t', '--title', type=str, help='Available when "write" is specified. Set the title of the song.')
    # parser.add_argument('-a', '--artist', type=str, help='Available when "write" is specified. Set the artist of the song.')
    # parser.add_argument('-A', '--album', type=str, help='Available when "write" is specified. Set the album of the song.')
    # parser.add_argument('-d', '--duration', type=float, help='Available when "write" is specified. Set the duration of the song in seconds.')
    # parser.add_argument('-C', '--custom', nargs='2', type=str, help='Available when "write" is specified. Set a custom key-value pair argument to the song. The first argument is the key, and the second argument is the value.')
    # parser.add_argument('-l', '--lyrics-file', type=str, help='Available when "write" is specified. Set the path to the file containing the lyrics of the song.')

    args = parser.parse_args()

    config = Config(args.config_path)
    if args.command == 'read':
        print(str(config))
    elif args.command == 'write':
        mode = config.mode
        if args.mode:
            mode = args.mode
            config.mode = mode
        if args.load:
            config.parse_song(*args.load)
        if args.set:
            set_args = args.set
            index = None

            if mode == 'playlist' and set_args and set_args[0].isdigit():
                try:
                    index = int(set_args[0])
                    set_args = set_args[1:]
                except ValueError:
                    pass
            
            if len(set_args) % 2 != 0:
                parser.error('Arguments for --set must be in key-value pairs.')
            
            song_data = {}
            general_data = {}
            song_keys = list(config.BASIC_SONG_KEYS) + ['lyrics-file']
            general_keys = list(config.BASIC_GENERAL_KEYS)

            kv_pairs = {set_args[i]: set_args[i + 1] for i in range(0, len(set_args), 2)}

            for key, value in kv_pairs.items():
                if key in song_keys:
                    if key == 'lyrics-file':
                        lyrics = load_lyrics(args.lyrics_file)
                        if lyrics: song_data['lyrics'] = lyrics
                    elif key == 'duration':
                        try:
                            song_data[key] = float(value)
                        except ValueError:
                            parser.error(f'Duration must be a float number, but got "{value}".')
                    else:
                        song_data[key] = value
                elif key in general_keys:
                    general_data[key] = value
                else:
                    parser.error(f'Unknown key "{key}".')

            if song_data:
                if index is not None:
                    song_data['index'] = index
                config.set_song_config(**song_data)
            if general_data:
                config.set_general_config(**general_data)





        # print(mode)
        # if mode == 'single':
        #     if args.song:
        #         config.parse_song(*args.song)
        #     else:
        #         song = {}
        #         if args.title: song['title'] = args.title
        #         if args.artist: song['artist'] = args.artist
        #         if args.album: song['album'] = args.artist
        #         if args.duration: song['duration'] = args.duration
        #         if args.lyrics_file:
        #             lyrics = load_lyrics(args.lyrics_file)
        #             if lyrics: song['lyrics'] = lyrics
        #         config.set_song_config(**song)
        # elif mode == 'playlist':
        #     if args.song:
        #         config.parse_song(*args.song)
        #     elif type(args.index) == int and args.index and args.index >= 0 and args.index < len(config):
        #         song = {}
        #         song['index'] = args.index
        #         if args.title: song['title'] = args.title
        #         if args.artist: song['artist'] = args.artist
        #         if args.album: song['album'] = args.album
        #         if args.duration: song['duration'] = args.duration
        #         if args.lyrics_file:
        #             lyrics = load_lyrics(args.lyrics_file)
        #             if lyrics: song['lyrics'] = lyrics
        #         config.set_song_config(**song)
        #     else:
        #         print('Index not specified or out of range.')
        print('Writting config:')
        print(str(config))
        ans = input('Are you sure to save the config? (y/n) ')
        if ans.lower() == 'y':
            config.save(args.config_path)
            print(f'Config saved to {args.config_path}.')
    return



if __name__ == '__main__':
    main()