r"""python tools/test_b480_live_write.py

B480 (16.11.2026): at the end of a world zip install Mod Studio reads the world's recipe back from
its plan and keeps a copy of it (Main.live_recipe, in a worker). The text was made in steps
already (B479), but written with one f.write of the whole text: encoding it and turning \n into
\r\n holds Python's lock, and the window stood still 0.95 s (the stall probe on a copy of the
GigaPack, offscreen, Mod Studio 64a80c3). It is written in 4 MB pieces now.

Here: Main.live_recipe itself in a worker thread, on a stand-in of the window (a world in a fake
game folder, the recipe read back from the plan replaced by one of about 200 MB of text in 13
million lines, the GigaPack's is 260 MB), while this thread counts how long it waits between
its turns, as the window's thread does. Checks: no wait over 0.5 s; the copy is byte for byte the text json.dumps
gives (indent 1, not ASCII, \r\n); the recipe comes back. No game, no Qt.
"""
import json, os, shutil, sys, tempfile, threading, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
T = tempfile.mkdtemp(prefix="b480live-")
LIMIT = 0.5
PLAYERS = int(os.environ.get("B480_PLAYERS", "220000"))
N = 0
FAILED = []
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    N += 1
    print("%s %d - %s" % ("ok" if cond else "FAIL", N, name))
    if not cond:
        FAILED.append(name)


def main():
    try:
        run()
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("all passed" if not FAILED else "%d failed" % len(FAILED))
    sys.exit(1 if FAILED else 0)


def run():
    sys.setswitchinterval(0.001)                      # as modstudio.app.main
    from modstudio import app as A
    from modstudio.pages import builder as PB
    import leaguebuilder
    world = "_FL26Gap"
    livecpk = os.path.join(T, "livecpk")
    os.makedirs(os.path.join(livecpk, world))
    with open(os.path.join(livecpk, world, "leaguebuilder-plan.json"), "w", encoding="utf-8") as f:
        f.write("{}")
    copies = os.path.join(T, "copies")
    rec = {"world": world, "leagues": [{"name": "Gap League", "country": "Croatia", "clubs": 2}],
           "players": {str(100000 + i): {"edits": {"name": "Igrač %d " % i + "x" * 300, "ovr": 70,
                                                    "stats": list(range(i % 7, i % 7 + 60))}}
                       for i in range(PLAYERS)}}
    leaguebuilder.recipe_from_plan = lambda plan, base: rec
    PB.warm = lambda *a, **k: None                    # (no logos here)
    project = types.SimpleNamespace(live_worlds=lambda: [world], base=T, copies_dir=lambda: copies)
    me = types.SimpleNamespace(project=project, game=types.SimpleNamespace(livecpk_dir=livecpk),
                               _live_open=lambda live: False)

    got = {}

    def work():
        try:
            got["out"] = A.Main.live_recipe(me)
        except Exception as e:
            got["error"] = repr(e)
        got["done"] = True
    t = threading.Thread(target=work, daemon=True)
    worst, last = 0.0, time.perf_counter()
    t.start()
    while not got.get("done"):
        time.sleep(0.005)
        now = time.perf_counter()
        worst, last = max(worst, now - last - 0.005), now
    t.join()
    kept = os.path.join(copies, world + ".json")
    size = os.path.getsize(kept) if os.path.isfile(kept) else 0
    ok("live_recipe kept a copy of the recipe (%.0f MB)%s" % (size / 2**20, got.get("error", "")),
       size > 0 and "error" not in got)
    ok("this thread's longest wait for its turn while it ran: %.2f s (limit %.1f)" % (worst, LIMIT),
       worst < LIMIT)
    want = json.dumps(rec, indent=1, ensure_ascii=False).replace("\n", "\r\n").encode("utf-8")
    with open(kept, "rb") as f:
        ok("the copy is byte for byte json.dumps' text (%d bytes)" % len(want), f.read() == want)
    out = got.get("out")
    ok("... and the recipe came back from it", bool(out) and len(out[2]["players"]) == PLAYERS
       if isinstance(out, tuple) and len(out) > 2 and isinstance(out[2], dict) else bool(out))


if __name__ == "__main__":
    main()
