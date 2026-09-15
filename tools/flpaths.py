r"""Local paths for every tool in this folder.

Nothing here hardcodes a real installation. Set environment variables, or edit the
defaults below:

    set FL26_DIR=E:\Football Life 2026          # game folder (holds FL_2026.exe)
    set FL26_PESDB=C:\work\exC\common\etc\pesdb  # extracted pesdb tables, newest first,
                                                 # ';'-separated for several CPKs
    set FL26_OUT=C:\work\fl26-out                # where tools write dumps and listings

Unpack the pesdb tables yourself from the game's data CPKs (see cpkx.py); no game
data is shipped in this repository.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

GAME_DIR  = os.environ.get("FL26_DIR",   r"C:\Football Life 2026")
EXE       = os.environ.get("FL26_EXE",   os.path.join(GAME_DIR, "FL_2026.exe"))
SIDER_DIR = os.environ.get("FL26_SIDER", os.path.join(GAME_DIR, "SiderAddons"))
SIDER_INI = os.path.join(SIDER_DIR, "sider.ini")
LIVECPK   = os.path.join(SIDER_DIR, "livecpk")

# Directories holding *extracted* pesdb tables, searched in order (newest CPK first).
PESDB_DIRS = [p for p in os.environ.get("FL26_PESDB", "").split(os.pathsep) if p]

OUT = os.environ.get("FL26_OUT", os.path.join(REPO, "out"))


def out_dir():
    os.makedirs(OUT, exist_ok=True)
    return OUT


def need_exe():
    if not os.path.isfile(EXE):
        raise SystemExit(
            "FL_2026.exe not found at %s\n"
            "Set FL26_DIR (game folder) or FL26_EXE (full path to the exe)." % EXE)
    return EXE
