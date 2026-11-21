r"""python tools/uitour.py --exe <FL26ModStudio.exe> --profile <folder with FL26ModStudio\settings.json>
                          [--game <game folder>] [--langs en,es,fr,pt,hr] [--size 1920x1009]
                          [--out <folder>] [--open-max 700] [--stall-max 700] [--pages Leagues,Build]
                          [--allow <file>] [--timeout 900] [--name <label>] [--via <folder of uia.py>]
                          [--do '<json list of actions>'] [--film]

The UI tour of a release (hard rules 4 and 8): the exe walks its own window once per language
(FL26ModStudio.exe --selfcheck, tools/modstudio/selfcheck.py) and this script judges what it wrote.

One line per language, PASS or FAIL:
  crash      no report, or the walk did not finish inside --timeout seconds (the exe is killed)
  errors     an error a click raised (errors.log) or a Python error during the walk
  slow       a page that kept the window still for more than --open-max ms when it was opened, or a
             single stop longer than --stall-max ms while it filled itself, or one that never settled
  text       a label or button whose text does not fit, or a button outside the window
             (--allow: a file of lines "<page>|<text start>" that are known and fine)
  window     the window (or a menu) does not fit the screen at --size

The profile is copied to a temporary %APPDATA% first, so the tour never changes it; only the
language, the game folder and the window size are set in the copy. --exe python runs the source
(python modstudio_main.py) instead of an exe, for a quick look while developing.

--via (or FL26_UIA_DIR): start the exe through the desktop helper (uia.run({"op": "launch", ...})) when
this script runs where there is no screen (a service session); the walk needs the real desktop.

--film (with --exe python): the animations as film_*.gif in --out (pages, the world cards, buttons,
the status line), taken in the first language.

Pictures of every page and menu, a contact sheet per language (sheet_<lang>.png) and uitour.json /
uitour.md land in --out. Exit 0 when every language passed, 1 otherwise.
"""
import json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def sheet(folder, lang, shots, path):
    """the pictures of one language on one sheet, four across, the page's name under each"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    tw, cols, pad, cap = 640, 4, 8, 22
    tiles = []
    for name, f in shots:
        p = os.path.join(folder, f)
        if not os.path.isfile(p):
            continue
        im = Image.open(p).convert("RGB")
        if im.width > tw:
            im = im.resize((tw, max(1, im.height * tw // im.width)))
        tiles.append((name, im))
    if not tiles:
        return None
    th = max(im.height for _n, im in tiles)
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + cap + pad) + pad), (16, 18, 22))
    d = ImageDraw.Draw(out)
    for i, (name, im) in enumerate(tiles):
        x, y = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + cap + pad)
        out.paste(im, (x, y))
        d.text((x + 2, y + th + 4), "%s  %s" % (lang, name), fill=(230, 230, 230))
    out.save(path)
    return path


def judge(rep, open_max, stall_max, allow, after_max=60):
    """the reasons a walk fails: {kind: [lines]}"""
    bad = {}
    def add(kind, line):
        bad.setdefault(kind, []).append(line)
    if rep is None:
        add("crash", "no report.json")
        return bad
    if not rep.get("done"):
        add("crash", "the walk did not finish (last page: %s)" % (rep["pages"][-1]["page"] if rep.get("pages") else "none"))
    for a in rep.get("actions") or []:
        what = " ".join(a["do"])
        if not a.get("started"):
            add("crash", "%s: did not start" % what)
        elif not a.get("over"):
            add("slow", "%s: never finished" % what)
        if max(a["stall_ms"], a.get("settle_stall_ms") or 0) > stall_max:
            add("slow", "%s: the window stood still %d ms" % (what, max(a["stall_ms"], a.get("settle_stall_ms") or 0)))
        if a.get("started") and a.get("files_s") is None:
            add("crash", "%s: the files never got there" % what)
        if a.get("after_files_s") is not None and a["after_files_s"] > after_max:
            add("slow", "%s: the window kept saying it for %.1f s after the files were done (at %.1f s)"
                % (what, a["after_files_s"], a["files_s"]))
    for b in rep.get("dialogs") or []:
        if not b.get("in_action"):
            add("errors", "a box nobody asked for at %s: %s" % (b.get("at"), (b.get("text") or b.get("title") or "")[:160]))
    for e in rep.get("errors") or []:
        add("errors", "%s: %s" % (e.get("where"), (e.get("text") or "").strip().splitlines()[-1][:200]))
    st = rep.get("start") or {}
    if st and not st.get("settled"):
        add("slow", "the start never settled (%d ms)" % st.get("settle_ms", 0))
    for p in rep.get("pages") or []:
        where = "%s (round %d)" % (p["page"], p["round"])
        if p["open_ms"] > open_max:
            add("slow", "%s: stood still %d ms when opened" % (where, p["open_ms"]))
        if p["stall_ms"] > stall_max:
            add("slow", "%s: a stop of %d ms while it filled" % (where, p["stall_ms"]))
        if not p["settled"]:
            add("slow", "%s: never settled" % where)
        for kind, cls, name, text, need, have in p.get("misfits") or []:
            if any(a[0] in ("*", p["page"]) and text.startswith(a[1]) for a in allow):
                continue
            add("text", "%s: %s %s %r needs %d, has %d" % (p["page"], kind, cls + ("#" + name if name else ""), text, need, have))
    win = rep.get("window") or {}
    if win and not win.get("fits"):
        add("window", "the window %s does not fit the screen %s" % (win.get("frame"), win.get("screen")))
    for m in rep.get("menus") or []:
        if not m.get("fits"):
            add("window", "the menu %s runs off the screen" % m.get("menu"))
    return bad


def main():
    if "--exe" not in sys.argv or "--profile" not in sys.argv:
        print(__doc__)
        return 2
    exe, profile = arg("--exe"), os.path.abspath(arg("--profile"))
    langs = arg("--langs", "en,es,fr,pt,hr").split(",")
    size = [int(x) for x in arg("--size", "1920x1009").split("x")]
    out = os.path.abspath(arg("--out", os.path.join(tempfile.gettempdir(), "fl26-uitour")))
    open_max, stall_max = int(arg("--open-max", "700")), int(arg("--stall-max", "700"))
    timeout = int(arg("--timeout", "900"))
    allow = []
    if arg("--allow") and os.path.isfile(arg("--allow")):
        for line in open(arg("--allow"), encoding="utf-8"):
            line = line.rstrip("\n")
            if line.strip() and not line.startswith("#") and "|" in line:
                allow.append(tuple(line.split("|", 1)))
    src = os.path.join(profile, "FL26ModStudio")
    if not os.path.isfile(os.path.join(src, "settings.json")) and "--empty" not in sys.argv:
        print("no %s (give the folder that holds FL26ModStudio, or --empty for a new player's)" % os.path.join(src, "settings.json"))
        return 2
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="fl26-uitour-")
    app = os.path.join(tmp, "FL26ModStudio")
    results, code = [], 0
    try:
        if os.path.isdir(src):
            shutil.copytree(src, app, ignore=shutil.ignore_patterns("running.lock", "crash.log", "errors.log"))
        else:
            os.makedirs(app)
        sp = os.path.join(app, "settings.json")
        base = json.load(open(sp, encoding="utf-8")) if os.path.isfile(sp) else {}
        # the copy's own files: a last recipe or recipes folder inside the profile moves with it
        for k in ("last_recipe", "recipes", "export_dir"):
            v = base.get(k)
            if isinstance(v, str) and os.path.normcase(os.path.abspath(v)).startswith(os.path.normcase(src)):
                base[k] = os.path.join(app, os.path.relpath(os.path.abspath(v), src))
        if arg("--game"):
            base["game"] = os.path.abspath(arg("--game"))
        base["size"] = size
        base["tour"] = base.get("tour") or "0.2.4"
        for lang in langs:
            d = os.path.join(out, lang)
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d)
            base["lang"] = lang
            with open(sp, "w", encoding="utf-8") as f:
                json.dump(base, f, indent=1)
            env = dict(os.environ, APPDATA=tmp, FL26_NO_TOUR="1", FL26_NO_SPLASH="1", FL26_SELFCHECK_T0=repr(time.time()))
            env.pop("QT_QPA_PLATFORM", None)
            if arg("--pages"):
                env["FL26_SELFCHECK_PAGES"] = arg("--pages")
            env.pop("FL26_SELFCHECK_DO", None)
            if arg("--do") and lang == langs[0]:  # '[["activate", "_FL26MyWorld"]]': once, in the first language
                env["FL26_SELFCHECK_DO"] = arg("--do")
            if "--profile-pages" in sys.argv or arg("--profile-step"):
                env["FL26_SELFCHECK_PROFILE"] = arg("--profile-step") or "1"
            env.pop("FL26_SELFCHECK_FILM", None)
            if "--film" in sys.argv and lang == langs[0]:      # the animations in film_*.gif (python only)
                env["FL26_SELFCHECK_FILM"] = "1"
            if exe == "python":
                env.setdefault("PYTHONUSERBASE", os.path.join(os.environ.get("APPDATA", ""), "Python"))
                cmd = [sys.executable, os.path.join(HERE, "modstudio_main.py"), "--selfcheck", d]
            else:
                cmd = [exe, "--selfcheck", d]
            t0 = time.time()
            cwd = os.path.dirname(os.path.abspath(exe)) if exe != "python" else HERE
            via = arg("--via") or os.environ.get("FL26_UIA_DIR")
            if via:
                sys.path.insert(0, via) if via not in sys.path else None
                import uia
                keys = ("APPDATA", "FL26_NO_TOUR", "FL26_NO_SPLASH", "FL26_SELFCHECK_T0", "FL26_SELFCHECK_PAGES",
                        "FL26_SELFCHECK_PROFILE", "FL26_SELFCHECK_DO", "FL26_SELFCHECK_FILM", "PYTHONUSERBASE")
                got = uia.run({"op": "launch", "exe": cmd[0], "args": cmd[1:], "cwd": cwd,
                               "env": {k: env[k] for k in keys if k in env}}, 60)
                pid, rc = got.get("pid"), "timeout"
                if not got.get("ok") or not pid:
                    rc = "not started: %s" % got
                while pid and time.time() - t0 < timeout:
                    q = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"], capture_output=True, text=True).stdout
                    if str(pid) not in q:
                        rc = 0
                        break
                    # an exe built before the fix of 11.11. writes its report and stays open (its
                    # sys.stdout is None): the report is whole, the window is closed for it
                    rp0 = os.path.join(d, "report.json")
                    if os.path.isfile(rp0) and time.time() - os.path.getmtime(rp0) > 20:
                        try:
                            whole = json.load(open(rp0, encoding="utf-8")).get("done")
                        except Exception:
                            whole = False
                        if whole:
                            print("note: %s wrote its report and did not leave; closed" % lang, flush=True)
                            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
                            rc = 0
                            break
                    time.sleep(1)
                if rc == "timeout" and pid:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
            else:
                p = subprocess.Popen(cmd, env=env, cwd=cwd)
                try:
                    rc = p.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                    rc = "timeout"
            took = time.time() - t0
            rp = os.path.join(d, "report.json")
            rep = json.load(open(rp, encoding="utf-8")) if os.path.isfile(rp) else None
            bad = judge(rep, open_max, stall_max, allow)
            if rc == "timeout":
                bad.setdefault("crash", []).append("killed after %d s" % timeout)
            elif isinstance(rc, str):
                bad.setdefault("crash", []).append(rc)
            shots = []
            if rep:
                shots = [(p_["page"], p_["shot"]) for p_ in rep.get("pages") or [] if p_.get("shot")]
                shots += [("menu " + m["menu"], m["shot"]) for m in rep.get("menus") or []]
                sheet(d, lang, shots, os.path.join(out, "sheet_%s.png" % lang))
            pages = [p_ for p_ in (rep or {}).get("pages") or []]
            slow = max(pages, key=lambda p_: p_["open_ms"], default=None)
            stall = max(pages, key=lambda p_: p_["stall_ms"], default=None)
            results.append({"lang": lang, "ok": not bad, "bad": bad, "seconds": round(took, 1),
                            "pages": len({p_["page"] for p_ in pages}), "menus": len((rep or {}).get("menus") or []),
                            "slowest_open": [slow["page"], slow["open_ms"]] if slow else None,
                            "longest_stall": [stall["page"], stall["stall_ms"]] if stall else None,
                            "world": (rep or {}).get("world_walked") or (rep or {}).get("world"),
                            "actions": (rep or {}).get("actions"), "dialogs": (rep or {}).get("dialogs"),
                            "window_ms": (rep or {}).get("window_ms"),
                            "start": (rep or {}).get("start"), "version": (rep or {}).get("version"),
                            "frozen": (rep or {}).get("frozen")})
            if bad:
                code = 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    lines = ["# UI tour%s: %s" % (" " + arg("--name") if arg("--name") else "", time.strftime("%Y-%m-%d %H:%M")), "",
             "exe: `%s`  profile: `%s`  size: %dx%d  limits: open %d ms, stall %d ms" % (exe, profile, size[0], size[1], open_max, stall_max), "",
             "| lang | result | pages | menus | slowest open | longest stop | start | why |", "|---|---|---|---|---|---|---|---|"]
    for r in results:
        why = "; ".join("%s: %d" % (k, len(v)) for k, v in r["bad"].items()) or ""
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["lang"], "PASS" if r["ok"] else "FAIL", r["pages"], r["menus"],
            "%s %d ms" % tuple(r["slowest_open"]) if r["slowest_open"] else "-",
            "%s %d ms" % tuple(r["longest_stall"]) if r["longest_stall"] else "-",
            "%d ms" % r["start"]["settle_ms"] if r.get("start") else "-", why))
    lines.append("")
    for r in results:
        for a in r.get("actions") or []:
            lines.append("- %s did `%s`: %s s in all, files done at %s s, the window stood still at most %d ms" % (
                r["lang"], " ".join(a["do"]), a["total_s"], a.get("files_s"),
                max(a["stall_ms"], a.get("settle_stall_ms") or 0)))
        for b in r.get("dialogs") or []:
            lines.append("- %s box at %s: %s -> %s" % (
                r["lang"], b.get("at"), " ".join((b.get("text") or b.get("title") or "").split())[:160], b.get("answer")))
    for r in results:
        for kind, items in r["bad"].items():
            for it in items:
                lines.append("- %s %s: %s" % (r["lang"], kind, it))
    text = "\n".join(lines)
    with open(os.path.join(out, "uitour.md"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    with open(os.path.join(out, "uitour.json"), "w", encoding="utf-8") as f:
        json.dump({"exe": exe, "profile": profile, "size": size, "results": results}, f, indent=1, ensure_ascii=False)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode())
    print("\n%s  (%s)" % ("UI TOUR PASS" if not code else "UI TOUR FAIL", out))
    return code


if __name__ == "__main__":
    sys.exit(main())
