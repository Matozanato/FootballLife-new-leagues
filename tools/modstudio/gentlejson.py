"""json.loads that lets the window breathe (0.3.1, 11.11.).

A big world's recipe is 255 MB of JSON and its plan 128 MB. json.loads reads a text in one call of
C code that keeps Python's lock for the whole of it, so "read in the background" still stood the
window still: 2-3 s at every Put in the game and at every start with such a world, however many
threads there were. loads() here reads the same text piece by piece -- the members of the top
object, and theirs, each with the same C reader -- so the lock comes free between two pieces and
the window goes on painting. The result is the one json.loads gives; a text it does not read to
the end goes to json.loads itself, which then says what is wrong with it as it always did.

install() puts it in place of json.loads (json.load calls that) for big texts read off the window's
thread, so the world builder's own reads (leaguebuilder, lbservers ...) are gentle too.

The text itself comes in pieces as well (read_text, in place of json.load's fp.read()): turning
244 MB of UTF-8 into a str is one call too, 0.6 s with the lock kept, and that was the longest stop
left in Put in the game with the big world (the UI tour of the exe, 11.11.: My world's page stood
1.1 s while a thread was in fp.read()).
"""
import codecs
import io
import json
import os
import threading
import time
from json.decoder import WHITESPACE, scanstring

BIG = 2 * 1024 * 1024        # characters: under this json.loads is over before anyone notices
DEPTH = 3                    # how deep the pieces go: the recipe's players are two levels down

PIECE = 4 * 1024 * 1024      # bytes of a file turned into text at a time
# Free between two pieces is not enough for a window that is busy itself: every call it makes into Qt
# gives the lock away, and it then waits a millisecond or two to get it back from a thread that
# never stops -- My world's page, 0.04 s of work, took 0.5-0.8 s to fill while the big recipe was
# read (the UI tour, 11.11.). So the reader also rests: WORK seconds of reading, REST of sleep, in
# which the window runs alone. The big recipe takes 3 s instead of 2, behind a window that moves
WORK, REST = 0.003, 0.003


def _breathe(clock):
    if time.perf_counter() >= clock[0]:
        time.sleep(REST)
        clock[0] = time.perf_counter() + WORK

_real_loads = json.loads
_real_load = json.load
_decoder = json.JSONDecoder()


class _Odd(Exception):
    """not what this reader expects: json.loads reads the text instead"""


def _value(text, i, depth, clock):
    """(value, index after it) of the JSON value at text[i:]"""
    i = WHITESPACE.match(text, i).end()
    c = text[i:i + 1]
    if depth > 0 and c == "{":
        out = {}
        i = WHITESPACE.match(text, i + 1).end()
        if text[i:i + 1] == "}":
            return out, i + 1
        while True:
            if text[i:i + 1] != '"':
                raise _Odd()
            key, i = scanstring(text, i + 1, True)
            i = WHITESPACE.match(text, i).end()
            if text[i:i + 1] != ":":
                raise _Odd()
            out[key], i = _value(text, i + 1, depth - 1, clock)
            _breathe(clock)
            i = WHITESPACE.match(text, i).end()
            c = text[i:i + 1]
            if c == ",":
                i = WHITESPACE.match(text, i + 1).end()
            elif c == "}":
                return out, i + 1
            else:
                raise _Odd()
    if depth > 0 and c == "[":
        out = []
        i = WHITESPACE.match(text, i + 1).end()
        if text[i:i + 1] == "]":
            return out, i + 1
        while True:
            v, i = _value(text, i, depth - 1, clock)
            out.append(v)
            _breathe(clock)
            i = WHITESPACE.match(text, i).end()
            c = text[i:i + 1]
            if c == ",":
                i += 1
            elif c == "]":
                return out, i + 1
            else:
                raise _Odd()
    return _decoder.raw_decode(text, i)


def loads(text):
    """json.loads(text) for a str, read in pieces"""
    import bigjson
    with bigjson.settled():               # no full collection over what is read, now or later (B479)
        try:
            value, end = _value(text, 0, DEPTH, [time.perf_counter() + WORK])
            if WHITESPACE.match(text, end).end() != len(text):
                raise _Odd()
            return value
        except (_Odd, ValueError, IndexError, RecursionError):
            return _real_loads(text)


def _loads(s, **kw):
    if (isinstance(s, str) and len(s) >= BIG and not any(v is not None for v in kw.values())
            and threading.current_thread() is not threading.main_thread()):
        return loads(s)
    if isinstance(s, (str, bytes, bytearray)) and len(s) >= BIG:
        import bigjson                    # read in one call (the window's thread, or with options): set aside too
        with bigjson.settled():
            return _real_loads(s, **kw)
    return _real_loads(s, **kw)


def read_text(fp):
    """fp.read() for a big UTF-8 file opened as text and not read yet, in pieces; None when fp is
    anything else (the caller then reads it as ever). Line ends stay as they are in the file,
    which is the same to JSON"""
    try:
        if (not isinstance(fp, io.TextIOWrapper) or codecs.lookup(fp.encoding).name != "utf-8"
                or (fp.errors or "strict") != "strict" or fp.tell() != 0):
            return None
        raw = fp.buffer
        if os.fstat(raw.fileno()).st_size < BIG:
            return None
    except (OSError, ValueError, LookupError, AttributeError):
        return None
    decode = codecs.getincrementaldecoder("utf-8")().decode
    parts = []
    try:
        while True:
            piece = raw.read(PIECE)
            if not piece:
                break
            parts.append(decode(piece))
            time.sleep(REST)
        parts.append(decode(b"", True))
    except UnicodeDecodeError:
        # what fp.read() itself would say about this file
        raw.seek(0)
        return raw.read().decode("utf-8")
    return "".join(parts)


def _load(fp, **kw):
    if threading.current_thread() is not threading.main_thread():
        text = read_text(fp)
        if text is not None:
            return json.loads(text, **kw)
    return _real_load(fp, **kw)


def install():
    if json.loads is not _loads:
        json.loads = _loads
    if json.load is not _load:
        json.load = _load


def uninstall():
    if json.loads is _loads:
        json.loads = _real_loads
    if json.load is _load:
        json.load = _real_load
