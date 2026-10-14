"""python modstudio_main.py  -> FL26 Mod Studio (the window: tools/modstudio/app.py)"""
import multiprocessing
import sys


def selftest_build(base, out):
    """--selftest-build <tables> <report>: a small world built in a temporary game folder the way the
    Build button builds (a process of its own), so the release check can try it on the exe itself"""
    import os, shutil, tempfile, traceback
    game = tempfile.mkdtemp(prefix="fl26-selftest-")
    try:
        import leaguebuilder as B
        from modstudio import apart
        for d in ("livecpk", "modules", "content"):
            os.makedirs(os.path.join(game, "SiderAddons", d))
        with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
            f.write("[sider]\n")
        said = []
        pl = B.plan({"world": "_FL26Selftest", "leagues": [
            {"name": "Selftest Albania", "country": "Albania", "clubs": 12, "legs": 2}]}, base)
        apart.build(pl, base, game, False, said.append)
        d = os.path.join(game, "SiderAddons", "livecpk", "_FL26Selftest", "common", "etc", "pesdb")
        text = "ok: %d log lines, %d tables\n%s" % (len(said), len(os.listdir(d)), "\n".join(said))
    except BaseException:
        text = "failed:\n" + traceback.format_exc()
    finally:
        shutil.rmtree(game, ignore_errors=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    # 0.2.4: Build runs in a process of its own (modstudio/apart.py); in the exe that process is
    # the exe again, and this sends it to the build instead of opening a second window
    multiprocessing.freeze_support()
    if "--selftest-build" in sys.argv:
        i = sys.argv.index("--selftest-build")
        selftest_build(sys.argv[i + 1], sys.argv[i + 2])
        sys.exit(0)
    from modstudio.app import main
    main()
