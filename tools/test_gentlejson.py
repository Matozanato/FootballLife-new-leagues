"""modstudio.gentlejson: the same result as json.loads, the same errors, and the window's thread
gets its turn while a big text is read in another one (11.11.: "read in the background" stood the
window still for as long as json.loads took)."""
import json, os, random, sys, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import gentlejson as G

n_ok = 0


def ok(name, cond):
    global n_ok
    if not cond:
        print("FAIL", name)
        sys.exit(1)
    n_ok += 1
    print("ok %d - %s" % (n_ok, name))


def some(rnd, depth=0):
    k = rnd.random()
    if depth > 5 or k < 0.25:
        return rnd.choice([None, True, False, 0, -1, 3.5, 1e20, "", "a", "č š \" \\ \n ☃", rnd.randint(-10**12, 10**12)])
    if k < 0.6:
        return {rnd.choice(["", "a", "b c", "ž", "k%d" % rnd.randint(0, 9)]): some(rnd, depth + 1) for _ in range(rnd.randint(0, 5))}
    return [some(rnd, depth + 1) for _ in range(rnd.randint(0, 5))]


SAMPLES = ['{}', '[]', ' { } ', ' [ ] ', '{"a":{}}', '{"a":[]}', '[[],{}]', '"x"', '12', 'null', ' true ',
           '{"a": 1, "a": 2}', '{"a":{"b":{"c":{"d":{"e":[1,{"f":[]}]}}}}}', '[1 , 2 ,3]', '{ "a" : [ 1 , { "b" : null } ] }',
           '\n{\n "world": "_FL26X",\n "leagues": [\n  {\n   "name": "A"\n  }\n ],\n "players": {\n  "A/0": [[1, "x"]]\n },\n "edits": {}\n}\n',
           '{"\\u00e9\\n": "\\ud83d\\ude00"}', '[1.0, -0.0, 1E5, 2e-3]']
for s in SAMPLES:
    ok("same as json.loads: %r" % s[:40], G.loads(s) == json.loads(s) and repr(G.loads(s)) == repr(json.loads(s)))

rnd = random.Random(1111)
same = True
for i in range(400):
    v = some(rnd)
    for text in (json.dumps(v), json.dumps(v, indent=1, ensure_ascii=False), json.dumps(v, separators=(",", ":"))):
        same = same and repr(G.loads(text)) == repr(json.loads(text))
ok("400 random values in three spellings: the same", same)

d = G.loads('{"b": 1, "a": {"z": 1, "y": 2}}')
ok("the order of the keys is the text's", list(d) == ["b", "a"] and list(d["a"]) == ["z", "y"])

BAD = ['', ' ', '{', '[', '{"a"}', '{"a":}', '{"a":1,}', '[1,]', '[1 2]', '{"a":1} x', '{a:1}', "{'a':1}", '[1,,2]',
       '{"a":1 "b":2}', '{"a":[1,}', 'nul', '{"a":{"b":[}}}', '["\t"]']
for s in BAD:
    try:
        json.loads(s)
        want = None
    except ValueError as e:
        want = str(e)
    try:
        G.loads(s)
        got = None
    except ValueError as e:
        got = str(e)
    ok("a bad text is refused with json's own words: %r" % s, want is not None and got == want)

# install(): only big texts read off the main thread take the gentle way; the rest is json's own
G.install()
try:
    ok("installed: json.loads is the gentle one", json.loads is G._loads)
    ok("... a small text, main thread: as ever", json.loads('{"a": [1]}') == {"a": [1]})
    ok("... with arguments: json's own", json.loads('{"a": 1.5}', parse_float=str) == {"a": "1.5"})
    ok("... bytes: json's own", json.loads(b'{"a": 1}') == {"a": 1})
    big = {"world": "_FL26Big", "leagues": [{"name": "L%d" % i, "clubs": 20} for i in range(300)],
           "players": {"L%d/%d" % (i, k): [[n, "Player %d" % n, 70 + n % 20, "x" * 40] for n in range(60)]
                       for i in range(300) for k in range(20)}, "edits": {}}
    text = json.dumps(big, indent=1)
    ok("the big text is big (%d MB)" % (len(text) >> 20), len(text) >= 20 << 20)
    t = time.perf_counter()
    whole = G._real_loads(text)
    one_go = time.perf_counter() - t

    # the main thread ticks while another one reads: the longest silence between two ticks
    def silence(read):
        got, stop, worst = [], [False], [0.0]

        def job():
            got.append(read(text))
            stop[0] = True
        th = threading.Thread(target=job)
        last = time.perf_counter()
        th.start()
        while not stop[0]:
            time.sleep(0.001)
            now = time.perf_counter()
            worst[0] = max(worst[0], now - last)
            last = now
        th.join()
        return got[0], worst[0]

    got, quiet_gentle = silence(json.loads)
    ok("read in a thread: the same value", got == whole)
    _g, quiet_real = silence(G._real_loads)
    print("   json.loads in one go: %.2f s; the main thread's longest silence: %.3f s with it, %.3f s gentle"
          % (one_go, quiet_real, quiet_gentle))
    ok("the main thread is never silent for long (%.3f s; json's own %.3f s)" % (quiet_gentle, quiet_real),
       quiet_gentle < max(0.15, quiet_real / 4))
    with open(os.path.join(os.environ.get("TEMP", "."), "fl26-gentle-test.json"), "w", encoding="utf-8") as f:
        f.write(text)
    got = []
    th = threading.Thread(target=lambda: got.append(json.load(open(f.name, encoding="utf-8"))))
    th.start()
    th.join()
    os.remove(f.name)
    ok("json.load of a file in a thread: the same value", got and got[0] == whole)

    # ---- the text of a big file comes in pieces too (read_text), the same text as fp.read()
    tmp = os.path.join(os.environ.get("TEMP", "."), "fl26-gentle-test2.json")
    piece, big = G.PIECE, G.BIG
    G.PIECE, G.BIG = 7, 64            # pieces that cut the letters of more than one byte in two
    try:
        odd = json.dumps({"č š ž ☃ 😀 \u00e9": ["Ýokary liga", "x" * 50, {"ñ": "日本"}]}, ensure_ascii=False, indent=1)
        for label, data in (("plain", odd.encode("utf-8")), ("CRLF line ends", odd.replace("\n", "\r\n").encode("utf-8"))):
            with open(tmp, "wb") as f:
                f.write(data)
            with open(tmp, encoding="utf-8", newline="") as f:
                want = f.read()
            with open(tmp, encoding="utf-8") as f:
                got = G.read_text(f)
            ok("read_text, %s: the text of the file" % label, got == want and json.loads(got) == json.loads(odd))
        with open(tmp, encoding="utf-8") as f:
            f.read(1)
            ok("read_text: not for a file read already", G.read_text(f) is None)
        with open(tmp, "rb") as f:
            ok("read_text: not for a file opened as bytes", G.read_text(f) is None)
        with open(tmp, encoding="cp1250") as f:
            ok("read_text: not for another encoding", G.read_text(f) is None)
        with open(tmp, encoding="utf-8", errors="replace") as f:
            ok("read_text: not with errors= of one's own", G.read_text(f) is None)
        import io
        ok("read_text: not for a text in memory", G.read_text(io.StringIO(odd)) is None)
        G.BIG = 10 ** 9
        with open(tmp, encoding="utf-8") as f:
            ok("read_text: not for a small file", G.read_text(f) is None)
        G.BIG = 64

        def in_thread(fn):
            out = []

            def job():
                try:
                    out.append(("value", fn()))
                except Exception as e:
                    out.append(("error", type(e).__name__))
            th = threading.Thread(target=job)
            th.start()
            th.join()
            return out[0]

        def load(**kw):
            with open(tmp, encoding="utf-8") as f:
                return json.load(f, **kw)
        ok("json.load in a thread, small pieces: the same value", in_thread(load) == ("value", json.loads(odd)))
        ok("json.load in a thread with object_hook: json's own answer",
           in_thread(lambda: load(object_hook=lambda d: sorted(d))) == ("value", json.loads(odd, object_hook=lambda d: sorted(d))))
        for label, data, err in (("a BOM", b"\xef\xbb\xbf" + odd.encode("utf-8"), "JSONDecodeError"),
                                 ("bytes that are not UTF-8", odd.encode("utf-8")[:40] + b"\xff\xfe" + odd.encode("utf-8")[40:], "UnicodeDecodeError"),
                                 ("a text cut short", odd.encode("utf-8")[:-9], "JSONDecodeError"),
                                 ("a letter cut in two at the end", odd.encode("utf-8") + "č".encode("utf-8")[:1], "UnicodeDecodeError")):
            with open(tmp, "wb") as f:
                f.write(data)
            try:
                with open(tmp, encoding="utf-8") as f:
                    G._real_load(f)
                real = "value"
            except Exception as e:
                real = type(e).__name__
            ok("json.load in a thread, %s: %s, as json's own" % (label, err), in_thread(load)[1] == err == real)
        with open(tmp, "wb") as f:
            f.write(odd.encode("utf-8"))
        ok("json.load on the main thread: json's own", load() == json.loads(odd))
    finally:
        G.PIECE, G.BIG = piece, big
        if os.path.exists(tmp):
            os.remove(tmp)

    # ---- and no other thread waits long while the big text is read from its file
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)

    def reading(how):
        worst, stop, got = [0.0], [False], []

        def job():
            with open(tmp, encoding="utf-8") as f:
                got.append(how(f))
            stop[0] = True
        th = threading.Thread(target=job)
        last = time.perf_counter()
        th.start()
        while not stop[0]:
            time.sleep(0.001)
            now = time.perf_counter()
            worst[0] = max(worst[0], now - last)
            last = now
        th.join()
        return got[0], worst[0]
    whole_text, quiet_real = reading(lambda f: f.read())
    got, quiet_gentle = reading(G.read_text)
    os.remove(tmp)
    ok("read_text of the big file: json reads it to the same value", json.loads(got) == whole)
    print("   %d MB of text: the main thread's longest silence %.3f s with fp.read(), %.3f s in pieces"
          % (len(whole_text) >> 20, quiet_real, quiet_gentle))
    ok("the main thread is not silent for long while the file is read (%.3f s)" % quiet_gentle, quiet_gentle < 0.15)
finally:
    G.uninstall()
ok("uninstalled: json.loads is json's own again", json.loads is G._real_loads)
ok("uninstalled: json.load is json's own again", json.load is G._real_load)
print("test_gentlejson: ok (%d)" % n_ok)
