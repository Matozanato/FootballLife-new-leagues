"""python test_build_apart.py <folder with the game's tables> -- Build runs in a process of its own
(exe test 15.10.: the Modpack's Build, then League packages and back to Build -> "Not Responding" for
minutes; the build was a thread of the window's process). The same world built here and apart gives
the same tables; the log lines and a BuildError come back to the window; and while it builds the
window's thread looks at files as fast as with nothing running."""
import os, shutil, sys, tempfile, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
from modstudio import apart

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def recipe(world):
    return {"world": world, "leagues": [{"name": "Apart Albania", "country": "Albania", "clubs": 16, "legs": 2},
                                        {"name": "Apart Andorra", "country": "Andorra", "clubs": 12, "legs": 2}]}


def tables(game, world):
    d = os.path.join(game, "SiderAddons", "livecpk", world, "common", "etc", "pesdb")
    return {f: open(os.path.join(d, f), "rb").read() for f in sorted(os.listdir(d))}


def slowest_look(busy):
    """the longest a burst of 300 file looks takes on this thread while busy() runs in another"""
    worst, t = [0.0], threading.Thread(target=busy)
    t.start()
    while t.is_alive():
        t0 = time.perf_counter()
        for _i in range(300):
            os.path.isdir(os.environ.get("TEMP", "."))
        worst[0] = max(worst[0], time.perf_counter() - t0)
        time.sleep(0.05)
    t.join()
    return worst[0]


def main(base):
    sys.setswitchinterval(0.005)          # Python's own: what the 0.2.4 exe test froze with
    game = tempfile.mkdtemp(prefix="fl26-apart-")
    try:
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        here_log, there_log = [], []
        here = slowest_look(lambda: B.build(B.plan(recipe("_FL26Here"), base), base, game, False,
                                            log=lambda t: here_log.append(str(t))))
        there = slowest_look(lambda: apart.build(B.plan(recipe("_FL26There"), base), base, game, False,
                                                 there_log.append))
        a, b = tables(game, "_FL26Here"), tables(game, "_FL26There")
        ok("the same tables built apart (%d files)" % len(a), sorted(a) == sorted(b)
           and all(a[f] == b[f] for f in a))
        ok("the log comes back line by line (%d lines)" % len(there_log), len(there_log) == len(here_log) > 5)
        print("# slowest burst of 300 looks: %.3f s with the build in this process, %.3f s apart" % (here, there))
        ok("the window's thread is not held up by the build", there < max(0.25, here / 4))
        bad = recipe("_FL26Bad")
        bad["leagues"][0]["clubs"] = 1
        try:
            apart.build(B.plan(bad, base), base, game, False, there_log.append)
            ok("a BuildError comes back as one", False)
        except B.BuildError as e:
            ok("a BuildError comes back as one: " + str(e)[:60], True)
        except Exception as e:
            ok("a BuildError comes back as one (got %r)" % e, False)
    finally:
        shutil.rmtree(game, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
