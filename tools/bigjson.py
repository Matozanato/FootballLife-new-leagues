"""json.load for the big files of a world (the GigaPack's plan is 286 MB, its recipe 260 MB), read
in small steps.

json.load is one call into C that keeps Python's lock from its first byte to its last: read in a
worker thread, the plan still stopped Mod Studio's window for 1.5 s and the recipe for 2.1 s
(hangwatch, 15.11.2026, "Switching _FL26Megapack on"). Here the two outer levels of the file are
walked in Python and each value below them is one short call of the same C scanner, so the window's
thread gets its turn every few milliseconds. The result is what json.load gives: same types, same
order of keys, same errors (ValueError).
"""
import contextlib
import gc
import json
import json.decoder
import json.scanner
import threading
import time

# the scanner json.loads itself uses for a plain JSONDecoder()
_SCAN = json.scanner.make_scanner(json.decoder.JSONDecoder())
_WS = " \t\n\r"
DEPTH = 3                       # containers this deep and deeper are one C call each
SMALL = 1 << 20                 # a text this short is not worth the walk

# B480: a thread that never stops still holds the window back while it paints. Every call Qt makes
# back into Python (a widget made from Python checks each of its methods there the first time) takes
# the lock back, and the window then waits one switch interval (1 ms) for it: a Select Team combo of
# Leagues took 154 ms instead of 0.8 ms next to one busy reader, 24 of them 3.7 s (the stall test of
# B480, 17.11.2026). So a reader in a worker thread also rests, as gentlejson's does: WORK seconds of
# reading, REST of sleep, in which the window runs alone. Off (False) outside Mod Studio's window:
# modstudio.app.main turns it on
GENTLE = False
WORK, REST = 0.003, 0.003
_next = [0.0]
_MAIN = threading.main_thread().ident


def _rest():
    if GENTLE and time.perf_counter() >= _next[0] and threading.get_ident() != _MAIN:
        time.sleep(REST)
        _next[0] = time.perf_counter() + WORK


_quiet_lock = threading.Lock()
_quiet_n = 0                    # loads under way: the collector is off while this is not 0
_quiet_was = False


@contextlib.contextmanager
def settled():
    """around the reading of a big file. Python's collector walks every container it knows on a full
    collection: after a recipe and a plan are read that is 800,000 of them, 0.3 s while they are in
    memory. When Windows has paged them out (a Build next to it takes the RAM) the same walk reads them
    back from the page file with Python's lock held: 8.7 s in the thread reading a recipe and 12.9 s in
    the window's own thread at the end of Build (hangstacks + "gc:" lines, 16.11.2026, B479/B480).
    So: no collection while the file is read, and what was read is set aside (gc.freeze) -- JSON
    values have no cycles, they go when the last name for them goes, the collector has nothing to
    find in them and never walks them again."""
    global _quiet_n, _quiet_was
    with _quiet_lock:
        if _quiet_n == 0:
            _quiet_was = gc.isenabled()
            if _quiet_was:
                gc.collect(1)   # the young cycles of before go now: frozen with the file they would stay
                gc.disable()
        _quiet_n += 1
    try:
        yield
    finally:
        with _quiet_lock:
            _quiet_n -= 1
            if _quiet_n == 0:
                gc.freeze()
                if _quiet_was:
                    gc.enable()


def loads(text, depth=DEPTH):
    if len(text) < SMALL:
        return _loads(text, depth)
    with settled():
        return _loads(text, depth)


def _loads(text, depth=DEPTH):
    if isinstance(text, (bytes, bytearray)):
        text = text.decode(json.detect_encoding(text), "surrogatepass")
    if text.startswith("﻿"):
        raise json.JSONDecodeError("Unexpected UTF-8 BOM (decode using utf-8-sig)", text, 0)
    if len(text) < SMALL:
        return json.loads(text)
    i = _skip(text, 0)
    value, i = _value(text, i, depth)
    i = _skip(text, i)
    if i != len(text):
        raise json.JSONDecodeError("Extra data", text, i)
    return value


def load(f, depth=DEPTH, chunk=1 << 22):
    """json.load(f) in small steps; f is a file open as text or as bytes. Read 4 MB at a time: one
    f.read() of a text file decodes all of it under Python's lock"""
    parts = []
    while True:
        b = f.read(chunk)
        if not b:
            break
        parts.append(b)
        _rest()
    if parts and isinstance(parts[0], (bytes, bytearray)):
        import codecs
        dec = codecs.getincrementaldecoder("utf-8")()
        parts = [dec.decode(b) for b in parts] + [dec.decode(b"", final=True)]
    return loads("".join(parts), depth)


def load_path(path, depth=DEPTH):
    return loads(read_text(path), depth)


def read_text(path, chunk=1 << 22):
    """the file's text, UTF-8, read and decoded 4 MB at a time: open(path, encoding="utf-8").read()
    decodes the whole file in one call under Python's lock (0.3-0.6 s of a stopped window on the
    GigaPack's files)"""
    import codecs
    dec = codecs.getincrementaldecoder("utf-8")()
    parts = []
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            parts.append(dec.decode(b))
            _rest()
    parts.append(dec.decode(b"", final=True))
    return "".join(parts)


def dumps(obj, indent=1, ensure_ascii=False, depth=DEPTH):
    """json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii), the same text, in small steps.
    With an indent json.dumps is still one call into C (Python 3.13 on): written in a worker, the
    GigaPack's recipe stopped the window for 1.4 s after Switch on (15.11.2026, app.live_recipe).
    The outer levels are written here and each value below them is one short call of json.dumps,
    moved right by its level"""
    if not isinstance(indent, int) or isinstance(indent, bool) or indent < 0:
        return json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii)
    parts = []
    _put(obj, 0, depth, " " * indent, indent, ensure_ascii, parts)
    return "".join(parts)


def _put(v, level, depth, ind, indent, ascii_, parts):
    t = type(v)
    if depth > 0 and t is dict and v and all(type(k) is str for k in v):
        pad = "\n" + ind * (level + 1)
        first = True
        for k, x in v.items():
            parts.append(("{" if first else ",") + pad + json.dumps(k, ensure_ascii=ascii_) + ": ")
            first = False
            _put(x, level + 1, depth - 1, ind, indent, ascii_, parts)
            _rest()
        parts.append("\n" + ind * level + "}")
    elif depth > 0 and t is list and v:
        pad = "\n" + ind * (level + 1)
        first = True
        for x in v:
            parts.append(("[" if first else ",") + pad)
            first = False
            _put(x, level + 1, depth - 1, ind, indent, ascii_, parts)
            _rest()
        parts.append("\n" + ind * level + "]")
    else:
        text = json.dumps(v, indent=indent, ensure_ascii=ascii_)
        # (a string's own line ends are written \n by json: every real one here is the layout's)
        parts.append(text.replace("\n", "\n" + ind * level) if level and "\n" in text else text)


def _skip(text, i):
    n = len(text)
    while i < n and text[i] in _WS:
        i += 1
    return i


def _once(text, i):
    try:
        return _SCAN(text, i)
    except StopIteration as e:
        raise json.JSONDecodeError("Expecting value", text, e.value) from None


def _value(text, i, depth):
    c = text[i:i + 1]
    if depth > 0 and c == "{":
        return _object(text, i + 1, depth - 1)
    if depth > 0 and c == "[":
        return _array(text, i + 1, depth - 1)
    return _once(text, i)


def _object(text, i, depth):
    out = {}
    i = _skip(text, i)
    if text[i:i + 1] == "}":
        return out, i + 1
    while True:
        if text[i:i + 1] != '"':
            raise json.JSONDecodeError("Expecting property name enclosed in double quotes", text, i)
        key, i = _once(text, i)
        i = _skip(text, i)
        if text[i:i + 1] != ":":
            raise json.JSONDecodeError("Expecting ':' delimiter", text, i)
        i = _skip(text, i + 1)
        out[key], i = _value(text, i, depth)
        _rest()
        i = _skip(text, i)
        c = text[i:i + 1]
        if c == "}":
            return out, i + 1
        if c != ",":
            raise json.JSONDecodeError("Expecting ',' delimiter", text, i)
        i = _skip(text, i + 1)


def _array(text, i, depth):
    out = []
    i = _skip(text, i)
    if text[i:i + 1] == "]":
        return out, i + 1
    while True:
        value, i = _value(text, i, depth)
        out.append(value)
        _rest()
        i = _skip(text, i)
        c = text[i:i + 1]
        if c == "]":
            return out, i + 1
        if c != ",":
            raise json.JSONDecodeError("Expecting ',' delimiter", text, i)
        i = _skip(text, i + 1)
