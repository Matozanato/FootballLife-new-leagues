r"""python tools/futve_logo.py --picture <png> [--install] [--game <folder>] [--cids 134,135]
       python tools/futve_logo.py --restore <backup folder>

The "Fase Final" logo of the Liga FUTVE's two play-offs. It writes the six emblem variants of
competitions 134 (Apertura) and 135 (Clausura) -- common\render\symbol\emblemLc\emb_<id><suffix>.png,
256 and 512 px -- the way a Build's league logo is made (tools/lbassets.py, lbassets.league_logo):
the picture fitted into a transparent square, never stretched, in colour in every variant.

  --install   writes the variants into the livecpk world (SiderAddons\livecpk\<world>, the name the
              loader's fl26world.txt gives) and backs up what it replaces under
              out/futve/logos/backup-<date>/; the game must be closed.
  --restore   puts a backup made by --install back (game closed).
  --dry       only generates the six variants under out/futve/logos/world and lists them.
  --cids      the two competitions, 134 and 135 by default (the world's play-off cup ids).
  --picture   the picture given (for the Liga FUTVE play-offs, G:\Downloads\playoff.png).

A Mod Studio Build regenerates the world's emblems: run the --install command again afterwards, as
for the world file itself (futve_world.py).

  python tools/futve_logo.py --picture "G:\Downloads\playoff.png" --dry
  python tools/futve_logo.py --picture "G:\Downloads\playoff.png" --install --game "G:\Games\SP Football Life 2026"
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lbassets

EMBLEM = ("common", "render", "symbol", "emblemLc")
OUT = os.path.join(REPO, "out", "futve", "logos")
SUFFIXES = tuple(s for s, _px in lbassets.mkemblems.VARIANTS)
TITLES = {134: "Liga FUTVE Apertura Playoffs", 135: "Liga FUTVE Clausura Playoffs"}


def game_open():
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                             errors="ignore", timeout=30).stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return False
    return any(n in out for n in ("fl_2026.exe", "sider.exe", "fl 2026 start.exe"))


def world_name(game):
    p = os.path.join(game, "SiderAddons", "modules", "fl26world.txt")
    try:
        for line in open(p, encoding="utf-8", errors="replace"):
            s = line.strip()
            if s.startswith("world "):
                return s.split()[1]
    except OSError:
        pass
    return "_FL26MyWorld"


def generate(picture, cids):
    root = os.path.join(OUT, "world")
    if os.path.isdir(root):
        shutil.rmtree(root)
    for cid in cids:
        lbassets.league_logo(root, cid, TITLES.get(cid, "Liga FUTVE Playoffs"), picture=picture)
    d = os.path.join(root, *EMBLEM)
    files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    for f in files:
        print("  %s (%d bytes)" % (f, os.path.getsize(os.path.join(d, f))))
    return d, files


def install(game, picture, cids):
    if not os.path.isdir(os.path.join(game, "SiderAddons")):
        raise SystemExit("no SiderAddons in %s; pass --game" % game)
    if game_open():
        raise SystemExit("the game is open; close it and run the command again")
    src, files = generate(picture, cids)
    world = os.path.join(game, "SiderAddons", "livecpk", world_name(game))
    dst = os.path.join(world, *EMBLEM)
    if not os.path.isdir(dst):
        raise SystemExit("no emblem folder at %s (is the world switched on?)" % dst)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_root = os.path.join(OUT, "backup-" + stamp)
    backup = os.path.join(backup_root, *EMBLEM)
    os.makedirs(backup, exist_ok=True)
    n = 0
    for f in files:
        t = os.path.join(dst, f)
        if os.path.isfile(t):
            shutil.copy2(t, os.path.join(backup, f))
        shutil.copy2(os.path.join(src, f), t)
        n += 1
    print("  %d emblem(s) of competitions %s written to %s" % (n, ",".join(map(str, cids)), dst))
    print("  the replaced variants are in %s" % backup_root)
    print("  restore: python tools/futve_logo.py --restore \"%s\" --game \"%s\"" % (backup_root, game))


def restore_into(game, backup):
    if game_open():
        raise SystemExit("the game is open; close it and run the command again")
    root = os.path.abspath(backup)
    cands = [os.path.join(root, *EMBLEM), root]
    if os.path.basename(root) == "emblemLc":
        cands.insert(0, root)
    src = next((c for c in cands if os.path.isdir(c)), None)
    if src is None:
        raise SystemExit("no emblem folder in the backup %s" % backup)
    world = os.path.join(game, "SiderAddons", "livecpk", world_name(game))
    dst = os.path.join(world, *EMBLEM)
    n = 0
    for f in sorted(os.listdir(src)):
        if not f.endswith(".png"):
            continue
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        n += 1
    print("  %d emblem(s) restored into %s" % (n, dst))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--picture")
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    ap.add_argument("--cids", default="134,135")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--restore", metavar="BACKUP")
    a = ap.parse_args()
    cids = [int(x) for x in a.cids.split(",") if x.strip()]
    if a.restore:
        if not a.game:
            raise SystemExit("--restore needs --game (or FL26_DIR)")
        restore_into(a.game, a.restore)
        return 0
    if not a.picture:
        raise SystemExit("pass --picture <png> (--dry alone generates it under out/futve/logos)")
    if not os.path.isfile(a.picture):
        raise SystemExit("no picture at %s" % a.picture)
    if a.install:
        if not a.game:
            raise SystemExit("--install needs --game (or FL26_DIR)")
        install(a.game, a.picture, cids)
        return 0
    generate(a.picture, cids)
    print("dry: nothing written to the game")
    return 0


if __name__ == "__main__":
    sys.exit(main())
