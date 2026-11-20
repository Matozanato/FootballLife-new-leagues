"""A world zip carries its author's words: the recipe's "notice" (19.11.2026).

    python tools/test_world_notice.py

Export writes the recipe's "notice" (kept in the world's plan, leaguebuilder.RECIPE_SETTINGS) as
NOTICE.txt at the top of the zip, and fl26worldpack.json names it. Install reads it and puts it
first in the summary of the zip. A world without a notice gets no NOTICE.txt.
"""
import json, os, shutil, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder
from modstudio import installer as I
from test_world_share import put, sider

WORLD = "_FL26Notice"
TEXT = "Please do not sell or repack this world.\nIt holds the work of many people."
N = [0]


def ok(name, cond):
    N[0] += 1
    assert cond, name
    print("ok %d - %s" % (N[0], name))


def world(tmp, name, settings):
    sd = sider(os.path.join(tmp, name))
    root = os.path.join(sd, "livecpk", WORLD)
    put(os.path.join(root, I.WORLD_FILE), "# fl26world 1\nworld %s\nleague 1 x\n" % WORLD)
    put(os.path.join(root, "common", "etc", "pesdb", "Team.bin"), "x")
    plan = {"world": WORLD, "free_ids": 1, "leagues": [{"name": "L One", "rid": 1}], "settings": settings}
    put(os.path.join(root, "leaguebuilder-plan.json"), json.dumps(plan))
    return sd


def main():
    ok("the plan keeps the recipe's notice", "notice" in leaguebuilder.RECIPE_SETTINGS)
    ok("world_notice: a text, a list of lines, nothing",
       I.world_notice({"notice": " a\n"}, None) == "a" and I.world_notice({"notice": ["a", "b"]}, None) == "a\nb"
       and I.world_notice({}, None) == "" and I.world_notice(None, None) == "")
    tmp = tempfile.mkdtemp(prefix="fl26_notice_")
    try:
        sd = world(tmp, "a", {"notice": TEXT.split("\n")})
        zp = os.path.join(tmp, "a.zip")
        I.export_world(sd, WORLD, zp, prev_ledger=None)
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            info = json.loads(z.read(I.WORLD_INFO))
            raw = z.read(I.WORLD_NOTICE) if I.WORLD_NOTICE in names else b""
        ok("Export: NOTICE.txt at the top of the zip, named in %s" % I.WORLD_INFO,
           I.WORLD_NOTICE in names and info.get("notice") == I.WORLD_NOTICE)
        ok("... with the notice's words, Windows line ends", raw.decode("utf-8") == TEXT.replace("\n", "\r\n") + "\r\n")
        ok("... a recipe given to Export wins over the plan's",
           I.world_notice({"notice": "other"}, os.path.join(sd, "livecpk", WORLD)) == "other")
        work = tempfile.mkdtemp(prefix="fl26_notice_w_", dir=tmp)
        top = I.unpack(zp, work)
        ok("Install reads it back", I.read_notice(top) == TEXT)
        with open(os.path.join(top, I.WORLD_NOTICE), "w") as f:
            f.write("x" * (I.NOTICE_MAX * 3))
        ok("... a long one is cut to what the window shows", len(I.read_notice(top)) == I.NOTICE_MAX + 4)
        os.remove(os.path.join(top, I.WORLD_NOTICE))
        parts = I.detect(top, "mod")
        ok("... and the zip is still one world", [p.kind for p in parts] == ["world"])

        sd2 = world(tmp, "b", {})
        zp2 = os.path.join(tmp, "b.zip")
        I.export_world(sd2, WORLD, zp2, prev_ledger=None)
        with zipfile.ZipFile(zp2) as z:
            names2, info2 = z.namelist(), json.loads(z.read(I.WORLD_INFO))
        top2 = I.unpack(zp2, tempfile.mkdtemp(prefix="fl26_notice_w2_", dir=tmp))
        ok("a world without a notice: no NOTICE.txt, nothing read",
           I.WORLD_NOTICE not in names2 and "notice" not in info2 and I.read_notice(top2) == "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("test_world_notice: ok (%d)" % N[0])


if __name__ == "__main__":
    main()
