// https://github.com/mebtte/clrc
// clrc - Parser for LRC and enhanced LRC.
// MIT License
// Copyright (c) 2021 Mebtte Pan

// eslint-disable-next-line no-shadow
var LineType;
(function (LineType) {
    LineType["INVALID"] = "invalid";
    LineType["METADATA"] = "metadata";
    LineType["LYRIC"] = "lyric";
    LineType["ENHANCED_LYRIC"] = "enhanced_lyric";
})(LineType || (LineType = {}));

var TIMESTAMP = /^(\d{2,}):(\d{2})(?:\.(\d{2,3}))?$/; // 00:00.000 | 00:00.00 | 00:00
function timestampToMillisecond(timestamp) {
    var _a;
    var timeMatch = timestamp.match(TIMESTAMP);
    if (timeMatch === null) {
        return 0;
    }
    var minute = timeMatch[1];
    var second = timeMatch[2];
    var centisecond = (_a = timeMatch[3]) !== null && _a !== void 0 ? _a : '00'; // compatible with [00:00]
    var centisecondNumber = centisecond.length === 3 ? +centisecond : +centisecond * 10; // // compatible with [00:00.000]
    return +minute * 60 * 1000 + +second * 1000 + centisecondNumber;
}

var LYRIC_LINE = /^((?:\[\d{2,}:\d{2}(?:\.\d{2,3})?\])+)(.*)$/; // [time]content | [time][time][...]content
var METADATA_LINE = /^\[(.+?):(.*?)\]$/; // [key:value]
/**
 * parse lrc string
 * @author mebtte<hi@mebtte.com>
 */
function parse(lrc) {
    var parsedLines = [];
    var lines = lrc.split('\n');
    for (var i = 0, length = lines.length; i < length; i += 1) {
        var raw = lines[i];
        /** lyric */
        var lyricMatch = raw.match(LYRIC_LINE);
        if (lyricMatch !== null) {
            var timesPart = lyricMatch[1]; // [time][time]content --> [time][time]
            var times = timesPart.split(']['); // [time1][time2] --> [time1 | time2]
            for (var _i = 0, times_1 = times; _i < times_1.length; _i++) {
                var time = times_1[_i];
                var lyricLine = {
                    lineNumber: i,
                    raw: raw,
                    type: LineType.LYRIC,
                    startMillisecond: timestampToMillisecond(time.replace(/[[\]]/g, '')),
                    content: lyricMatch[2],
                };
                parsedLines.push(lyricLine);
            }
            continue;
        }
        /** metadata */
        var metadataMatch = raw.match(METADATA_LINE);
        if (metadataMatch !== null) {
            var key = metadataMatch[1];
            var value = metadataMatch[2];
            var metadataLine = {
                lineNumber: i,
                raw: raw,
                type: LineType.METADATA,
                key: key,
                value: value,
            };
            parsedLines.push(metadataLine);
            continue;
        }
        /** invalid line */
        parsedLines.push({
            lineNumber: i,
            raw: raw,
            type: LineType.INVALID,
        });
    }
    return parsedLines;
}

/******************************************************************************
Copyright (c) Microsoft Corporation.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
***************************************************************************** */
/* global Reflect, Promise, SuppressedError, Symbol */


var __assign = function() {
    __assign = Object.assign || function __assign(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};

typeof SuppressedError === "function" ? SuppressedError : function (error, suppressed, message) {
    var e = new Error(message);
    return e.name = "SuppressedError", e.error = error, e.suppressed = suppressed, e;
};

/**
 * <00:00.000>
 * <00:00.00>
 * <00:00>
 */
var ENHANCED_TIME = /<\d{2,}:\d{2}(?:\.(?:\d{2,3}))?>/g;
function parseEnhanced(lrc) {
    var lines = parse(lrc);
    return lines.map(function (line) {
        if (line.type === LineType.LYRIC) {
            var words = [];
            var wordTimeTagMatch = line.content.match(ENHANCED_TIME);
            if (wordTimeTagMatch === null) {
                /**
                 * no time tag but having content is invalid
                 * like [time] xxxxx
                 * @author mebtte<hi@mebtte.com>
                 */
                if (line.content.trim().length > 0) {
                    var invalidLine = {
                        type: LineType.INVALID,
                        lineNumber: line.lineNumber,
                        raw: line.raw,
                    };
                    return invalidLine;
                }
            }
            else {
                var wordContents = line.content.split(ENHANCED_TIME);
                /**
                 * ignore first emptiness or only-space
                 * @author mebtte<hi@mebtte.com>
                 */
                if (wordContents[0].trim().length === 0) {
                    wordContents.shift();
                }
                /**
                 * time tag' length should equal to content's length
                 * @author mebtte<hi@mebtte.com>
                 */
                if (wordTimeTagMatch.length !== wordContents.length) {
                    var invalidLine = {
                        type: LineType.INVALID,
                        lineNumber: line.lineNumber,
                        raw: line.raw,
                    };
                    return invalidLine;
                }
                for (var i = 0; i < wordTimeTagMatch.length; i += 1) {
                    var timestamp = wordTimeTagMatch[i];
                    var content = wordContents[i];
                    words.push({
                        index: i,
                        raw: "".concat(timestamp).concat(content),
                        startMillisecond: timestampToMillisecond(timestamp.replace(/[<>]/g, '')),
                        content: content,
                    });
                }
            }
            return __assign(__assign({}, line), { type: LineType.ENHANCED_LYRIC, words: words });
        }
        return line;
    });
}

export { LineType, parse, parseEnhanced };
