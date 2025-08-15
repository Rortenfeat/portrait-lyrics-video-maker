import { parse, parseEnhanced, LineType } from './clrc.js';

/**
 * Get pixels of 1 rem
 * @returns {number}
 */
function getRemValue() {
    const root = document.documentElement;
    const computedStyle = window.getComputedStyle(root);
    return parseFloat(computedStyle.fontSize);
}
const rem = getRemValue();

function ease(t, start, end) {
    if (end - start <= 0) return start;
    if (t <= start) return start;
    if (t >= end) return end;
    const x = (t - start) / (end - start);
    return x < 0.5 ? 4 * x ** 3 : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

const isDom = (v) => typeof v === 'object' && v instanceof HTMLElement;



class Player {
    LINE_TRANSITION_DURATION = 1000; // ms

    constructor(song = undefined) {
        this.hasLyrics = false;
        if (song) {
            this.Song = song;
        }
        this.titleDom = document.querySelector('.song-title');
        this.lyricsContainerDom = document.querySelector('.lyrics-container');
        this.progressBarDom = document.querySelector('.progress-bar');
        this.progressBarTimeLeftDom = document.querySelector('.progress-bar-time-left');
        this.progressBarTimeRightDom = document.querySelector('.progress-bar-time-right');
    }
    set Time(t) {
        this.time = t;

        if (this.Song) {
            this.progressBarTimeLeftDom.textContent = this.formatTime(t);
            if (this.Song.duration) {
                this.progressBarTimeRightDom.textContent = this.formatTime(this.Song.duration - t);
                this.progressBarDom.style.setProperty('--progress', `${Math.min(1, (t / this.Song.duration)) * 100}%`);
            }

            if (this.hasLyrics) {
                const parsed = this.Lyrics.parsed;
                const t_ms = t * 1000;
                // Lyrics line transition
                for (let i = 0; i < parsed.length; i++) {
                    if (t_ms >= parsed[i].startMillisecond - this.LINE_TRANSITION_DURATION && t_ms < parsed[i].startMillisecond) {
                        let line_interp = 0;
                        if (i > 0 && this.LINE_TRANSITION_DURATION > parsed[i].startMillisecond - parsed[i - 1].startMillisecond) {
                            line_interp = ease(t_ms, parsed[i - 1].startMillisecond, parsed[i].startMillisecond);
                        } else {
                            line_interp = ease(t_ms, parsed[i].startMillisecond - this.LINE_TRANSITION_DURATION, parsed[i].startMillisecond);
                        }
                        this.scrollToShowLine(i - 1 + line_interp);
                        break;
                    } else if (i === parsed.length - 1 || t_ms < parsed[i + 1].startMillisecond - this.LINE_TRANSITION_DURATION) {
                        this.scrollToShowLine(i);
                        this.activateLine(i);
                        break;
                    }
                }
                if (this.hasActiveLine && this.Lyrics.mode === 'enhanced') {
                    const i = this.activeLine;
                    for (let j = 0; j < parsed[i].words.length; j++) {
                        if (j === 0 && t_ms < parsed[i].words[j].startMillisecond) {
                            break;
                        } else if (j === parsed[i].words.length - 1) {
                            this.scrollToShowWord(j);
                            this.activateWord(j);
                        } else if (t_ms >= parsed[i].words[j].startMillisecond && t_ms < parsed[i].words[j + 1].startMillisecond) {
                            this.scrollToShowWord(j);
                            this.activateWord(j);
                            break;
                        }
                    }
                }
            }
        }
    }
    get Time() {
        return this.time;
    }
    set Title(title) {
        this.title = title;
        this.titleDom.textContent = title;
    }
    get Title() {
        return this.title;
    }
    set Lyrics(lyrics) {
        this.lyrics = lyrics;
        this.hasLyrics = true;

        this.lyricsContainerDom.innerHTML = '';
        this.lyrics.plain.forEach((line, index) => {
            const lyricLine = document.createElement('div');
            lyricLine.classList.add('lyric-line');
            const scrollWrapper = document.createElement('div');
            scrollWrapper.classList.add('lyric-scroll-wrapper');
            if (this.lyrics.mode === 'enhanced') {
                this.lyrics.parsed[index].words.forEach(word => {
                    const lyricLineText = document.createElement('span');
                    lyricLineText.classList.add('lyric-line-text');
                    lyricLineText.textContent = word.content;
                    scrollWrapper.appendChild(lyricLineText);
                });
            } else {
                const lyricLineText = document.createElement('span');
                lyricLineText.classList.add('lyric-line-text');
                lyricLineText.textContent = line;
                scrollWrapper.appendChild(lyricLineText);
            }
            lyricLine.appendChild(scrollWrapper);
            this.lyricsContainerDom.appendChild(lyricLine);
        });
    }
    get Lyrics() {
        return this.lyrics;
    }
    set Song(song) {
        this.song = song;
        this.initSong();
    }
    get Song() {
        return this.song;
    }
    initSong() {
        const song = this.song;
        if (!song) return;

        this.Title = song.title;
        if (song.lyrics) this.Lyrics = song.lyrics;
        this.Time = 0;
    }
    formatTime(t) {
        if (t < 0) return '--:--';
        const minutes = Math.floor(t / 60);
        const seconds = Math.floor(t % 60);
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    /**
     * Scroll the first line of the lyrics container to the specified line
     * @param {number} line
     * @returns {void}
     */
    scrollLyricsContainer(line) {
        if (this.currentLine === line) return;
        const lyricsContainer = this.lyricsContainerDom;
        if (!this.lineHeight) {
            const firstLyricLine = lyricsContainer.querySelector('.lyric-line');
            if (!firstLyricLine) return;
            const rect = firstLyricLine.getBoundingClientRect();
            this.lineHeight = rect.height;
        }

        lyricsContainer.scrollTop = this.lineHeight * line;
        this.currentLine = line;
        return;
    }

    /**
     * Scroll the lyrics container to show the specified line
     * @param {number} line
     * @returns {void}
     */
    scrollToShowLine(line) {
        if (!this.hasLyrics) return;
        const totalLines = this.lyrics.parsed.length;
        if (line < 0 || line >= totalLines) return;

        if (line < 1) this.scrollLyricsContainer(0);
        else if (line > totalLines - 2) this.scrollLyricsContainer(totalLines - 3);
        else this.scrollLyricsContainer(line - 1);
        return;
    }
    /**
     * Scroll the horizontal scroll wrapper to show the word of active line
     * @param {number|HTMLElement} word
     * 
     */
    scrollToShowWord(word) {
        let scrollWrapper;
        let targetWord;
        if (isDom(word)) {
            scrollWrapper = word.closest('.lyric-scroll-wrapper');
            targetWord = word;
        } else {
            if (!this.hasActiveLine) return;
            scrollWrapper = this.lyricsContainerDom.children[this.activeLine].querySelector('.lyric-scroll-wrapper');
            targetWord = scrollWrapper.querySelector(`span:nth-child(${word + 1})`);
        }

        if (!scrollWrapper || !targetWord) return;
        if (this.currentWord === targetWord) return;
        this.currentWord = targetWord;

        // console.log('hey');
        const maxScrollLeft = scrollWrapper.scrollWidth - scrollWrapper.clientWidth;
        if (maxScrollLeft == 0) return;

        const wordCenterAbsolute = targetWord.offsetLeft + targetWord.offsetWidth / 2;
        const viewportHalfWidth = scrollWrapper.clientWidth / 2;
        let targetScrollLeft = wordCenterAbsolute - viewportHalfWidth;
        if (targetScrollLeft < 0) targetScrollLeft = 0;
        if (targetScrollLeft > maxScrollLeft) targetScrollLeft = maxScrollLeft;

        scrollWrapper.scrollLeft = targetScrollLeft;
        return;

    }
    /**
     * Start automatically updating time by time
     * @param {number} rate
     * @returns {void}
     */
    startTimer(rate = 60) {
        if (this.timer) this.stopTimer();
        if (!this.Time) this.Time = 0;
        this.timer_start = performance.now() - (this.time * 1000);
        this.timer = setInterval(() => {
            if (this.Song && this.Song.duration && this.Time >= this.Song.duration) this.stopTimer();
            this.Time = (performance.now() - this.timer_start) / 1000;
        }, 1000 / rate);
    }
    stopTimer() {
        clearInterval(this.timer);
    }
    /**
     * Class style handling for line activation
     * @param {number} line
     * @returns {void}
     */
    activateLine(line) {
        if (!this.hasLyrics) return;
        if (this.hasActiveLine && this.activeLine === line) return;

        const children = this.lyricsContainerDom.children;
        for (let i = 0; i < children.length; i++) {
            const classList = children[i].classList;
            if (i < line) {
                if (classList.contains('active')) classList.remove('active');
                if (!classList.contains('past')) classList.add('past');
            } else if (i === line) {
                if (!classList.contains('active')) classList.add('active');
                if (classList.contains('past')) classList.remove('past');
            } else {
                if (classList.contains('active')) classList.remove('active');
                if (classList.contains('past')) classList.remove('past');
            }
        }
        this.hasActiveLine = true;
        this.activeLine = line;
        return;
    }
    /**
     * Class style handling for word activation
     * @param {number} word
     * @returns {void}
     */
    activateWord(word) {
        if (!this.hasLyrics || !this.hasActiveLine) return;

        const scrollWrapper = this.lyricsContainerDom.children[this.activeLine].querySelector('.lyric-scroll-wrapper');
        if (!scrollWrapper) return;

        const words = scrollWrapper.querySelectorAll('span');
        for (let i = 0; i < words.length; i++) {
            const classList = words[i].classList;
            if (i < word) {
                if (classList.contains('active')) classList.remove('active');
                if (!classList.contains('past')) classList.add('past');
            } else if (i === word) {
                if (!classList.contains('active')) classList.add('active');
                if (classList.contains('past')) classList.remove('past');
            } else {
                if (classList.contains('active')) classList.remove('active');
                if (classList.contains('past')) classList.remove('past');
            }
        }
        return;
    }
}

class Song {
    constructor(title, artist, duration, raw_lyrics = undefined, callback = undefined) {
        this.title = title;
        this.artist = artist;
        this.raw_lyrics = raw_lyrics;
        this.duration = duration;
        this.callback = callback;
        this.parseLyrics();
    }
    parseLyrics = async () => {
        if (!this.raw_lyrics) return;
        const raw = this.raw_lyrics.replace(/\r\n/g, '\n').replace(/\r/g, '\n'); // 处理换行符

        const enhancedRegex = new RegExp(/<\d*:\d*\.\d*>/)
        const mode = enhancedRegex.test(raw) ? 'enhanced' : 'normal';
        this.lyrics = new Lyrics(raw, mode);

        if (this.callback && typeof this.callback === 'function') this.callback();
        return;
    }
}

class Lyrics {
    /**
     * Handling lyrics parsing
     * @param {string} raw
     * @param {'enhanced'|'normal'} mode
     */
    constructor(raw, mode = 'normal') {
        this.raw = raw;
        this.mode = mode;
        this.parseRaw();
    }
    parseRaw() {
        if (this.mode === 'enhanced') {
            this.parsed = parseEnhanced(this.raw);
            this.parsed = this.parsed.filter(line => line.type === LineType.ENHANCED_LYRIC);
            this.plain = [];
            this.parsed.forEach(line => {
                let plain_line = '';
                line.words.forEach(word => {
                    plain_line += word.content;
                })
                this.plain.push(plain_line);
            })
        }
        else {
            this.parsed = parse(this.raw);
            this.parsed = this.parsed.filter(line => line.type === LineType.LYRIC);
            this.plain = [];
            this.parsed.forEach(line => {
                this.plain.push(line.content);
            })
        }
    }
}

class PlaywrightController {
    constructor(player) {
        this.player = player;
        this.songs = [];
        this.testMessage = 'Hello, playwright!'
    }
    async setup(config_path) {
        const config = await fetch(config_path).then(response => response.json());
        this.config = config;

        if (config.mode === 'single') {
            const song = new Song(config.title, config.artist, config.duration, config.lyrics);
            this.songs.push(song);
            this.player.Song = song;
        } else if (config.mode === 'playlist') {
        }
    }
    updateFrame(frame, frame_rate) {
        const time = frame / frame_rate;
        this.player.Time = time;
    }
}

const player = new Player();
const controller = new PlaywrightController(player);

function hookWindow(window) {
    window.lv = {
        controller, player, Player, Song, Lyrics
    }
}

window.lv = {
    controller, player, Player, Song, Lyrics
}