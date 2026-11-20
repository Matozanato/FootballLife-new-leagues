r"""facecap.py -- the face pool's pictures from the game, unattended: fl26regen's capture mode and
Edit's player screen, one screenshot per pool face, each one checked (tools/facemini.py) as it is made.

  python tools/facecap.py run --player <id> --faces <a-b[,c-d,k] | list.txt | sample:N> --out <dir>
        [--game E:\FL\FL27\game] [--settle 2.0] [--no-flush] [--keep-game] [--stall 150] [--limit N]
  python tools/facecap.py status --out <dir>
  python tools/facecap.py compare <out A> <out B>
        the faces shot in both runs, picture against picture: the same face must give the same picture
  python tools/facecap.py list --ids <lo-hi> [--game ...]
        the database's players of those ids, each one's pool face and name (to pick the capture player)
  python tools/facecap.py run --player 1 --faces <...> --out <dir> --dry <shots dir>
        the same run without a game, on shots made before (mini_<k>.png): checks this script

Before "run" (the test session does it, this script never starts the game):
  * the game in English, started through its launcher WITH <game>\SiderAddons\modules\
    fl26regen_capture.txt there (sider.log: "fl26regen: CAPTURE MODE" and "face pack loaded, N faces");
  * Edit -> Edit Player -> the capture player's club -> the capture player opened: his Player Info
    and his 3D head on the right, the cursor on "Player Name". His kit must have no red (the menu
    is cut out by its red; a red shirt goes with it, and every shot is told "see-through").
  * nothing is ever saved in Edit while capturing.

For every face k not done yet (the run goes on where the last one stopped: progress.tsv):
"player <id> face <k>" into the capture file, the DLL's answer waited for (fl26regen_capture.ack),
the player closed, the next player in the list opened and closed, the capture player opened again
(Esc, Down, Enter, Esc, Up, Enter): the same player opened again at once keeps the head he had (the
06.11. shots: three faces with --no-flush gave three pictures of one head, a little moved, 3.9 apart
where two different faces are 4.1-25), the game's lookup of his appearance waited for, --settle
seconds for the head to be drawn, a shot. The shot is cut to the part around the head (its corner
kept in the PNG, facemini.CROP_KEY) and checked at once with facemini.portrait: a black or another
screen, no player, the head not where the box expects it, a see-through shirt, or the same picture
as the face before (closer than 2.0; the same face made twice is 0.2-0.8 apart). A bad shot is made
once more (2 s more);
still bad, it is written down as bad and the run goes on.

The run stops (and closes the game, unless --keep-game) when it is done, after --limit faces, when
the game is gone, or when no face has come out good for --stall seconds (the game is never left
running with nothing happening in it). Then:  python tools/facemini.py convert <out>\shots <dir>
(--box auto for another capture player) makes the .dds pictures and a contact sheet.

Keys and shots go through session1.py (the desktop session's helper of the test rig):
$FL26_SESSION1, default D:\dev\fl26-modding-research-wt\fast-season\tools.
"""
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, PngImagePlugin

import facemini as M

S1 = os.environ.get("FL26_SESSION1") or r"D:\dev\fl26-modding-research-wt\fast-season\tools"
TITLE = "SP Football Life 2027"
ESC, ENTER, DOWN, UP = 0x1B, 0x0D, 0x28, 0x26
CROP = (1380, 60, 1924, 760)       # kept of every shot: the box (facemini.BOX) with room around it
POOL = 32760


def session1():
    sys.path.insert(0, S1)
    import session1 as s
    return s


def arg(a, name, default=None):
    return a[a.index(name) + 1] if name in a else default


def face_list(spec, out):
    if spec.startswith("sample:"):
        n = int(spec[7:])
        rnd = random.Random(1811)
        return sorted(rnd.sample(range(POOL), n))
    if os.path.exists(spec):
        return [int(l.split()[0]) for l in open(spec, encoding="utf-8") if l.strip()[:1].isdigit()]
    out = []
    for part in spec.split(","):                     # "0-999", "61,1100,1420", "0-9,500-509"
        lo, _, hi = part.partition("-")
        out += list(range(int(lo), int(hi or lo) + 1))
    return out


def read_progress(out):
    done = {}
    p = os.path.join(out, "progress.tsv")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            t = line.rstrip("\n").split("\t")
            if len(t) >= 3 and t[0].isdigit():
                done[int(t[0])] = t[1]
    return done


class Rig:
    def __init__(self, game, out, log):
        self.s = session1()
        self.mods = os.path.join(game, "SiderAddons", "modules")
        self.cap = os.path.join(self.mods, "fl26regen_capture.txt")
        self.ack = os.path.join(self.mods, "fl26regen_capture.ack")
        self.game = game
        self.log = log
        self.hwnd = 0

    def setcap(self, text):
        tmp = self.cap + ".tmp"
        open(tmp, "w", newline="\n").write(text + "\n")
        os.replace(tmp, self.cap)

    def answer(self):
        """(face, served) of the ack's player line, or (None, 0)"""
        try:
            for line in open(self.ack, encoding="latin-1"):
                t = line.split()
                if len(t) >= 6 and t[0] == "player" and t[2] == "face" and t[4] == "served":
                    return int(t[3]), int(t[5])
        except OSError:
            pass
        return None, 0

    def wait(self, cond, secs):
        t0 = time.time()
        while time.time() - t0 < secs:
            if cond():
                return True
            time.sleep(0.1)
        return False

    def window(self):
        r = self.s.call({"cmd": "windows", "all": True})
        self.hwnd = next((w["hwnd"] for w in r.get("windows", []) if w.get("title") == TITLE), 0)
        return self.hwnd

    def alive(self):
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FL_2027.exe"], capture_output=True, text=True)
        return "FL_2027.exe" in r.stdout

    def keys(self, seq):
        self.s.call({"cmd": "keys", "seq": seq}, timeout=60)

    def shot(self, path):
        self.s.call({"cmd": "show", "hwnd": self.hwnd, "settle": 0.1})
        r = self.s.call({"cmd": "shot", "path": os.path.abspath(path), "hwnd": self.hwnd})
        return bool(r.get("ok"))

    def close_game(self):
        for exe in ("FL_2027.exe", "sider.exe"):
            subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True)


class DryRig(Rig):
    """--dry <shots dir>: the run without a game, on shots made before (mini_<k>.png): the capture
    file, the keys and the waits are skipped, the shot of face k is that file. Checks this script"""
    def __init__(self, src, out, log):
        self.src, self.log, self.k, self.hwnd = src, log, None, 1
        self.cap = os.path.join(out, "dry_capture.txt")

    def setcap(self, text):
        t = text.split()
        self.k = int(t[3]) if len(t) == 4 else None

    def answer(self):
        return self.k, 1

    def keys(self, seq):
        pass

    def alive(self):
        return True

    def shot(self, path):
        import shutil
        src = os.path.join(self.src, "mini_%d.png" % self.k)
        if not os.path.exists(src):
            return False
        shutil.copyfile(src, path)
        return True

    def close_game(self):
        pass


def keep(full, path):
    """the shot cut to CROP, its corner in the PNG's text (facemini reads it)"""
    im = Image.open(full)
    im.load()
    info = PngImagePlugin.PngInfo()
    info.add_text(M.CROP_KEY, "%d,%d" % CROP[:2])
    im.crop(CROP).save(path, "PNG", pnginfo=info)
    os.remove(full)
    return Image.open(path)


def preflight(rig, game, need):
    bad = []
    if not os.path.exists(rig.cap):
        bad.append("no %s: start the game with that file there (capture mode is read at the start)" % rig.cap)
    logs = [p for p in (os.path.join(game, "SiderAddons", "sider.log"), os.path.join(game, "sider.log")) if os.path.exists(p)]
    txt = open(max(logs, key=os.path.getmtime), encoding="utf-8", errors="replace").read() if logs else ""
    if "CAPTURE MODE" not in txt:
        bad.append("sider.log has no 'fl26regen: CAPTURE MODE'")
    import re
    m = re.findall(r"face pack loaded, (\d+) faces", txt)
    if not m or int(m[-1]) <= need:
        bad.append("sider.log: face pack %s, the run needs face %d" % (m[-1] if m else "not loaded", need))
    if not rig.alive():
        bad.append("FL_2027.exe is not running")
    elif not rig.window():
        bad.append("the window '%s' is not there" % TITLE)
    return bad


def run(a):
    out = arg(a, "--out")
    pid = int(arg(a, "--player"))
    game = arg(a, "--game", r"E:\FL\FL27\game")
    settle = float(arg(a, "--settle", "2.0"))
    flush = "--no-flush" not in a
    stall = float(arg(a, "--stall", "150"))
    limit = int(arg(a, "--limit", "0")) or None
    box = M.parse_box(a) if "--box" in a else M.BOX
    shots = os.path.join(out, "shots")
    os.makedirs(shots, exist_ok=True)
    logf = open(os.path.join(out, "capture.log"), "a", encoding="utf-8")

    def log(msg, echo=True):
        line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
        logf.write(line + "\n"); logf.flush()
        if echo:
            print(line, flush=True)

    faces = face_list(arg(a, "--faces"), out)
    done = read_progress(out)
    todo = [k for k in faces if done.get(k) != "ok"]
    dry = arg(a, "--dry")
    rig = DryRig(dry, out, log) if dry else Rig(game, out, log)
    bad = [] if dry else preflight(rig, game, max(todo) if todo else 0)
    if bad:
        for b in bad:
            log("NOT STARTED: " + b)
        return 2
    prog = open(os.path.join(out, "progress.tsv"), "a", encoding="utf-8")
    log("run: player %d, %d faces (%d done before), settle %.1f, flush %s, box %s"
        % (pid, len(todo), len(faces) - len(todo), settle, flush, box))
    t0 = last_good = time.time()
    n = nok = 0
    prev = None
    reason = "done"
    for k in todo:
        if limit and n >= limit:
            reason = "--limit %d" % limit
            break
        if not rig.alive():
            reason = "the game is gone"
            break
        if time.time() - last_good > stall:
            reason = "no good face for %d s" % stall
            break
        t1 = time.time()
        note = status = ""
        for attempt in (0, 1):
            rig.setcap("player %d face %d" % (pid, k))
            if not rig.wait(lambda: rig.answer()[0] == k, 5):
                status, note = "bad", "no answer from the DLL"
                continue
            heavy = flush or attempt == 1
            rig.keys([ESC, -0.7, DOWN, -0.5, ENTER, -1.5, ESC, -0.7, UP, -0.5, ENTER] if heavy else [ESC, -0.7, ENTER])
            looked = rig.wait(lambda: rig.answer()[1] > 0, 4)
            if not dry:
                time.sleep(settle + 2 * attempt)
            full = os.path.join(shots, "full_%d.png" % k)
            path = os.path.join(shots, "mini_%d.png" % k)
            if not rig.shot(full) or not os.path.exists(full):
                status, note = "bad", "no shot"
                continue
            im, notes = M.portrait(keep(full, path), box)
            a8 = np.asarray(im).astype(np.int16)
            if "bad" not in notes and prev is not None and np.abs(a8 - prev).mean() < 2.0:
                notes["bad"] = "the same picture as the face before: the head was not drawn again"
            if not looked and "bad" not in notes:
                notes["bad"] = "the game did not look him up after the reopen"
            if "bad" in notes:
                status, note = "bad", notes["bad"]
                continue
            status, note = "ok", "neck %s headw %s" % (notes.get("neck"), notes.get("headw"))
            prev = a8
            break
        n += 1
        secs = time.time() - t1
        prog.write("%d\t%s\t%.1f\t%s\n" % (k, status, secs, note)); prog.flush()
        if status == "ok":
            nok += 1
            last_good = time.time()
        else:
            log("face %d: %s" % (k, note))
        if n % 10 == 0:
            el = time.time() - t0
            left = (len(todo) - n) * el / n
            log("%d faces (%d good) in %.0f s, %.1f s a face, %.1f h left" % (n, nok, el, el / n, left / 3600.0))
    rig.setcap("off")
    el = time.time() - t0
    log("stop (%s): %d faces, %d good, %.0f s, %.1f s a face" % (reason, n, nok, el, el / max(n, 1)))
    if "--keep-game" not in a and not dry:
        rig.close_game()
        log("game closed")
    return 0 if reason.startswith(("done", "--limit")) else 4


def listing(a):
    """the database's players of ids lo-hi: the pool face each one wears and his name (the DLL's
    answer to "faces lo-hi"), to pick the capture player"""
    rig = Rig(arg(a, "--game", r"E:\FL\FL27\game"), None, print)
    rig.setcap("faces %s" % arg(a, "--ids"))
    time.sleep(2.5)
    print(open(rig.ack, encoding="latin-1").read())
    rig.setcap("off")
    return 0


def compare(a):
    """compare <dir A> <dir B>: the faces shot in both runs, picture against picture (the same face
    made twice is 0.2-0.8 apart; above 2 the head was not the face's, in one of the runs)"""
    import glob
    A, B = a[1], a[2]
    worst = []
    for p in sorted(glob.glob(os.path.join(B, "shots", "mini_*.png"))):
        q = os.path.join(A, "shots", os.path.basename(p))
        if not os.path.exists(q):
            continue
        x = np.asarray(M.portrait(Image.open(p))[0]).astype(int)
        y = np.asarray(M.portrait(Image.open(q))[0]).astype(int)
        worst.append((float(np.abs(x - y).mean()), os.path.basename(p)))
    for d, n in sorted(worst, reverse=True):
        print("%-16s %.2f %s" % (n, d, "OK" if d < 2.0 else "NOT THE SAME"))
    return 0 if worst and max(worst)[0] < 2.0 else 1


def status(a):
    out = arg(a, "--out")
    p = os.path.join(out, "progress.tsv")
    rows = [l.rstrip("\n").split("\t") for l in open(p, encoding="utf-8")] if os.path.exists(p) else []
    last = {}
    for r in rows:
        if len(r) >= 3 and r[0].isdigit():
            last[int(r[0])] = r
    ok = [r for r in last.values() if r[1] == "ok"]
    bad = [r for r in last.values() if r[1] != "ok"]
    secs = [float(r[2]) for r in last.values()]
    print("%d faces: %d good, %d bad; %.1f s a face (median %.1f)" % (len(last), len(ok), len(bad),
          np.mean(secs) if secs else 0, np.median(secs) if secs else 0))
    for r in bad[:30]:
        print("  face %s: %s" % (r[0], r[3] if len(r) > 3 else ""))
    return 0


def main(a):
    if a and a[0] == "compare" and len(a) == 3:
        return compare(a)
    if a and a[0] == "list" and "--ids" in a:
        return listing(a)
    if not a or a[0] not in ("run", "status") or "--out" not in a or (a[0] == "run" and ("--player" not in a or "--faces" not in a)):
        print(__doc__)
        return 2
    return run(a) if a[0] == "run" else status(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
