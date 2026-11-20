"""bigjson: the same result as json.load, and the main thread is not held while a worker reads a
big file (B479: the window stood still 1.4 s during "Switching _FL26Megapack on", 15.11.2026)"""
import io, json, os, random, sys, tempfile, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bigjson

FAILS = []


def ok(what, cond):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


def rnd(r, depth=0):
    k = r.randrange(9 if depth < 5 else 6)
    if k == 0: return None
    if k == 1: return r.choice([True, False])
    if k == 2: return r.randrange(-10**12, 10**12)
    if k == 3: return r.random() * 1e6
    if k in (4, 5): return "".join(r.choice('aZ9 "\\/\n\téš中\U0001f600{}[],:') for _ in range(r.randrange(12)))
    if k in (6, 7): return [rnd(r, depth + 1) for _ in range(r.randrange(6))]
    return {str(r.randrange(50)) + "k": rnd(r, depth + 1) for _ in range(r.randrange(6))}


def same(a, b):
    return a == b and json.dumps(a) == json.dumps(b)      # the order of keys and the types too


def main():
    r = random.Random(1511)
    bigjson.SMALL = 0                                      # walk every text, not only the big ones
    bad = 0
    for i in range(400):
        v = rnd(r)
        for text in (json.dumps(v), json.dumps(v, indent=r.choice([None, 1, 3]), ensure_ascii=False),
                     " \r\n\t" + json.dumps(v, separators=(",", ":")) + "\n"):
            for d in (0, 1, 2, 3, 9):
                if not same(bigjson.loads(text, d), json.loads(text)):
                    bad += 1
    ok("400 random documents x 3 layouts x 5 depths give what json.loads gives", bad == 0)
    bad = 0
    r2 = random.Random(1512)
    for i in range(400):
        v = rnd(r2)
        for ind in (0, 1, 2, 4):
            for asc in (False, True):
                for d in (0, 1, 2, 3, 9):
                    if bigjson.dumps(v, ind, asc, d) != json.dumps(v, indent=ind, ensure_ascii=asc):
                        bad += 1
    for v in ({}, [], {"a": {}}, [[], {}], {"a": [(1, 2), {3: "x", None: 1, True: 2, 1.5: 3}]}, "š\n", 1.5, None,
              {"t": (1, [2, {"k": (3,)}])}):
        for d in (0, 1, 3):
            if bigjson.dumps(v, 1, False, d) != json.dumps(v, indent=1, ensure_ascii=False):
                bad += 1
    ok("dumps: 400 random documents x 4 indents x 2 x 5 depths and the odd ones give json.dumps' text", bad == 0)
    ok("dumps: no indent or a text indent is json.dumps itself",
       bigjson.dumps({"a": [1]}, None) == json.dumps({"a": [1]}) and
       bigjson.dumps({"a": [1]}, "\t") == json.dumps({"a": [1]}, indent="\t", ensure_ascii=False))
    ok("bytes in, UTF-8",bigjson.loads('{"a": ["š", 1]}'.encode("utf-8")) == {"a": ["š", 1]})
    ok("a file open as text", bigjson.load(io.StringIO('[1, {"b": [2, 3]}]')) == [1, {"b": [2, 3]}])
    ok("a file open as bytes", bigjson.load(io.BytesIO('{"č": "ž"}'.encode("utf-8"))) == {"č": "ž"})
    ok("a repeated key keeps the last value, as json does",
       bigjson.loads('{"a": 1, "a": {"x": 2}}') == json.loads('{"a": 1, "a": {"x": 2}}'))
    wrong = 0
    for text in ("", "   ", "{", "[1, 2", '{"a" 1}', '{"a": 1,}', "[1,]", '{"a": 1} x', "[1 2]", "{1: 2}", '{"a": }',
                 chr(0xfeff) + '{"a": 1}', "nul", '["\x01"]', '{"a": [1, {"b": tru}]}'):
        for d in (1, 3):
            try:
                bigjson.loads(text, d)
                wrong += 1
            except ValueError:
                pass
            try:
                json.loads(text)
                wrong += 1                                 # the test itself: json must refuse it too
            except ValueError:
                pass
    ok("15 broken texts are refused with ValueError, as json refuses them", wrong == 0)

    # a file the size class of a big world: a worker reads it, the main thread keeps its turn
    bigjson.SMALL = 1 << 20
    doc = {"leagues": [{"id": i, "name": "League %d" % i,
                        "clubs": [{"id": i * 100 + c, "name": "Club š %d" % c,
                                   "players": [{"id": i * 10000 + c * 100 + p, "name": "Player %d" % p,
                                                "v": list(range(40))} for p in range(26)]} for c in range(18)]}
                       for i in range(160)]}
    tmp = tempfile.mkdtemp(prefix="bigjson_")
    path = os.path.join(tmp, "big.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)
    size = os.path.getsize(path)

    def gap(fn):
        out = {}
        t = threading.Thread(target=lambda: out.setdefault("r", fn()))
        worst, last = 0.0, time.perf_counter()
        t.start()
        while t.is_alive():
            time.sleep(0.005)
            now = time.perf_counter()
            worst, last = max(worst, now - last), now
        return worst, out.get("r")

    def plain():
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def stepped():
        with open(path, encoding="utf-8") as f:
            return bigjson.load(f)
    wj, a = gap(plain)
    wb, b = gap(stepped)
    wp, c = gap(lambda: bigjson.load_path(path))
    print("     %.0f MB: json.load holds the main thread %.2f s, bigjson.load %.2f s, load_path %.2f s"
          % (size / 1e6, wj, wb, wp))
    wd, t1 = gap(lambda: json.dumps(doc, indent=1, ensure_ascii=False))
    ws, t2 = gap(lambda: bigjson.dumps(doc, 1, False))
    print("     writing it: json.dumps holds the main thread %.2f s, bigjson.dumps %.2f s" % (wd, ws))
    ok("the big file: dumps gives json.dumps' text", t1 == t2)
    ok("the big file: dumps lets the main thread in under 0.5 s (json.dumps: %.2f s)" % wd, ws < 0.5)
    ok("the big file: the same document", a == b == c == doc)
    ok("the big file: the main thread waits under 0.5 s (json.load: %.2f s)" % wj, wb < 0.5 and wp < 0.5)
    # B480 (17.11.): with GENTLE (Mod Studio's window) a reader in a worker rests between its steps.
    # The main thread here takes the lock back 300 times, as a window does at each call Qt makes
    # into Python: next to a reader that never stops each of them waits a switch interval
    def handbacks(gentle):
        bigjson.GENTLE = gentle
        got, go = {}, threading.Event()

        def reader():
            go.set()
            got["v"] = bigjson.loads(text_big)
        th = threading.Thread(target=reader)
        th.start()
        go.wait()
        time.sleep(0.02)
        t0 = time.perf_counter()
        for _ in range(300):
            time.sleep(0)
        took = time.perf_counter() - t0
        th.join()
        bigjson.GENTLE = False
        return took, got["v"]
    was_iv = sys.getswitchinterval()
    sys.setswitchinterval(0.001)                      # as modstudio.app.main
    text_big = json.dumps({"l": [{"k": [i, {"n": str(i) * 20}], "m": i} for i in range(400000)]})
    hard, v1 = handbacks(False)
    soft, v2 = handbacks(True)
    sys.setswitchinterval(was_iv)
    ok("GENTLE: a worker's read gives the same document", v1 == v2 and json.dumps(v2) == text_big)
    ok("GENTLE: 300 hand-backs of the lock to the main thread took %.3f s next to the reader (%.3f s "
       "without GENTLE)" % (soft, hard), soft < hard / 2)
    bigjson.GENTLE = True
    t0 = time.perf_counter()
    v3 = bigjson.loads(text_big)
    on_main = time.perf_counter() - t0
    bigjson.GENTLE = False
    t0 = time.perf_counter()
    bigjson.loads(text_big)
    plain = time.perf_counter() - t0
    ok("GENTLE: on the main thread itself nothing rests (%.2f s, %.2f s without)" % (on_main, plain),
       v3 == v1 and on_main < plain * 1.5 + 0.05)
    del v1, v2, v3, text_big
    # B479/B480 (16.11.): what a big file gave is set aside from the collector, which stays on
    import gc
    text = json.dumps({"l": [{"k": [i, {"n": str(i)}]} for i in range(60000)]})
    gc.collect(); gc.unfreeze(); gc.collect()
    before, big = gc.get_freeze_count(), bigjson.loads(text)
    kept = gc.get_freeze_count() - before
    ok("a big text: its containers are set aside (%d frozen)" % kept, kept >= 120000)
    ok("a big text: the collector is on again after it", gc.isenabled())
    ok("a big text: a full collection walks nothing of it", not any(o is big["l"] for o in gc.get_objects()))
    with bigjson.settled():
        with bigjson.settled():
            inner = gc.isenabled()
        mid = gc.isenabled()
    ok("settled inside settled: off until the outer one ends, then on", not inner and not mid and gc.isenabled())
    gc.disable()
    bigjson.loads(text)
    ok("a caller that had the collector off keeps it off", not gc.isenabled())
    gc.enable()
    n = gc.get_freeze_count(); bigjson.loads("[1, 2]")
    ok("a small text freezes nothing", gc.get_freeze_count() == n)
    del big
    os.remove(path)
    os.rmdir(tmp)
    print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
