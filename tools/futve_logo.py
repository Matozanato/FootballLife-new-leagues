r"""python tools/futve_logo.py [--make] [--source <folder>]
       python tools/futve_logo.py --check
       python tools/futve_logo.py --install --game <folder>
       python tools/futve_logo.py --restore <backup folder> --game <folder>

The competition logos of the Liga FUTVE's play-offs and finals:

  134  Liga FUTVE Apertura Playoffs   PLAYOFF_APERTURA.png
  135  Liga FUTVE Clausura Playoffs   PLAYOFF_CLAUSURA.png
  142  Final del Apertura             FINAL_APERTURA.png
  129  Final del Clausura             FINAL_CLAUSURA.png
  175  Gran Final del FUTVE           FINAL_FUTVE.png

Six variants of each competition's emblem (256 and 512 px) are made the way a Build's league logo is
(tools/lbassets.py, lbassets.league_logo): the picture fitted into a transparent square, never
stretched, in colour in every variant.

The finals' competitions take **142, 129 and 175**, ids the exe's builder 1 include list gives a
case (129 replaces the base's own competition of that id; 175 is free; 136 is the UEFA Conference
League's reserved one, 143/144 have no case, and 10342 is a team id).

  --make      stage the 12 emblems under out/futve/logos/world (what futve_test.py installs; the
              sandbox backs up the game's emblems and puts them back at the end).
  --check     verify the staged files and their sizes.
  --install   write the staged set into the livecpk world (SiderAddons\livecpk\<world>) and back up
              what it replaces under out/futve/logos/backup-<date>/; the game must be closed. This is
              for keeping the logos after a Build; the sandbox installs the staged copies itself.
  --restore   put a backup made by --install back (game closed).

The pictures live in `--source`, `G:\Downloads` by default (or `FL26_LOGOS`). A Mod Studio Build
regenerates the world's emblems: run `--install` again afterwards, as for the world file itself.

  python tools/futve_logo.py --make
  python tools/futve_logo.py --check
  python tools/futve_logo.py --install --game "G:\Games\SP Football Life 2026"
"""
import argparse
import json
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
STAGED = os.path.join(OUT, "world")
SUFFIXES = tuple(s for s, _px in lbassets.mkemblems.VARIANTS)
PLAN = (
    (134, "PLAYOFF_APERTURA.png", "Liga FUTVE Apertura Playoffs"),
    (135, "PLAYOFF_CLAUSURA.png", "Liga FUTVE Clausura Playoffs"),
    (142, "FINAL_APERTURA.png", "Final del Apertura"),
    (129, "FINAL_CLAUSURA.png", "Final del Clausura"),
    (175, "FINAL_FUTVE.png", "Gran Final del FUTVE"),
)


def emblem_dir(root):
    return os.path.join(root, *EMBLEM)


def expected(root=STAGED):
    d = emblem_dir(root)
    return [os.path.join(d, "emb_%04d%s.png" % (cid, suf)) for cid, _f, _n in PLAN for suf in SUFFIXES]


def make(source):
    if os.path.isdir(STAGED):
        shutil.rmtree(STAGED)
    for cid, picture, name in PLAN:
        p = os.path.join(source, picture)
        if not os.path.isfile(p):
            raise SystemExit("no picture %s (pass --source)" % p)
        lbassets.league_logo(STAGED, cid, name, picture=p)
        print("  %d %s <- %s" % (cid, name, p))
    files = [os.path.basename(p) for p in expected()]
    # what futve_test.py installs: every competition of PLAN, never a guessed id
    with open(os.path.join(OUT, "files.json"), "w", encoding="utf-8") as f:
        json.dump({"competitions": [cid for cid, _f, _n in PLAN], "files": files}, f, indent=1)
    print("  staged %d emblem(s) under %s" % (len(files), emblem_dir(STAGED)))


def check():
    from PIL import Image
    bad = 0
    for cid, _f, _n in PLAN:
        for suf in SUFFIXES:
            px = 512 if suf.endswith("_ll") else 256
            p = os.path.join(emblem_dir(STAGED), "emb_%04d%s.png" % (cid, suf))
            if not os.path.isfile(p):
                print("  missing %s" % p)
                bad += 1
                continue
            try:
                w, h = Image.open(p).size
            except OSError as e:
                print("  %s: %s" % (p, e))
                bad += 1
                continue
            if (w, h) != (px, px):
                print("  %s: %dx%d, wanted %d" % (p, w, h, px))
                bad += 1
    if bad:
        print("  %d problem(s); run --make" % bad)
        return False
    man = os.path.join(OUT, "files.json")
    try:
        listed = set(json.load(open(man, encoding="utf-8"))["files"])
    except (OSError, ValueError, KeyError):
        print("  no files.json (run --make)")
        return False
    if listed != {os.path.basename(p) for p in expected()}:
        print("  files.json does not list the plan's files (run --make)")
        return False
    print("  %d staged emblem(s), all present and the right size" % len(expected()))
    return True


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


def install(game):
    if not check():
        raise SystemExit("the staged emblems are not ready")
    if not os.path.isdir(os.path.join(game, "SiderAddons")):
        raise SystemExit("no SiderAddons in %s; pass --game" % game)
    if game_open():
        raise SystemExit("the game is open; close it and run the command again")
    world = os.path.join(game, "SiderAddons", "livecpk", world_name(game))
    dst = emblem_dir(world)
    if not os.path.isdir(dst):
        raise SystemExit("no emblem folder at %s (is the world switched on?)" % dst)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup_root = os.path.join(OUT, "backup-" + stamp)
    backup = emblem_dir(backup_root)
    os.makedirs(backup, exist_ok=True)
    n = 0
    for p in expected():
        name = os.path.basename(p)
        t = os.path.join(dst, name)
        if os.path.isfile(t):
            shutil.copy2(t, os.path.join(backup, name))
        shutil.copy2(p, t)
        n += 1
    print("  %d emblem(s) written to %s" % (n, dst))
    print("  the replaced variants are in %s" % backup_root)
    print("  restore: python tools/futve_logo.py --restore \"%s\" --game \"%s\"" % (backup_root, game))


def restore_into(game, backup):
    if game_open():
        raise SystemExit("the game is open; close it and run the command again")
    root = os.path.abspath(backup)
    cands = [emblem_dir(root), root]
    if os.path.basename(root) == "emblemLc":
        cands.insert(0, root)
    src = next((c for c in cands if os.path.isdir(c)), None)
    if src is None:
        raise SystemExit("no emblem folder in the backup %s" % backup)
    world = os.path.join(game, "SiderAddons", "livecpk", world_name(game))
    dst = emblem_dir(world)
    n = 0
    for f in sorted(os.listdir(src)):
        if f.endswith(".png"):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
            n += 1
    print("  %d emblem(s) restored into %s" % (n, dst))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=os.environ.get("FL26_LOGOS", r"G:\Downloads"))
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    ap.add_argument("--make", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--restore", metavar="BACKUP")
    a = ap.parse_args()
    if a.restore:
        if not a.game:
            raise SystemExit("--restore needs --game (or FL26_DIR)")
        restore_into(a.game, a.restore)
        return 0
    if a.check:
        return 0 if check() else 1
    if a.install:
        if not a.game:
            raise SystemExit("--install needs --game (or FL26_DIR)")
        install(a.game)
        return 0
    make(a.source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
