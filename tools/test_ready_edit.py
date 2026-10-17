"""offline test of editing a ready world from a zip in place (B85, branch editpack): a fake game folder
with a small world marked .modstudio, then
  1. worlds.make_editable: a world backup "edited" with all of the world, .modstudio -> .modstudio-edited
  2. leaguebuilder.keep_added with `gone`: the world's own crest/logo files kept byte for byte, the
     edited mark carried, .modstudio not
  3. worlds.backup "built" + restore: the world as it was, the folder there before in replaced\\,
     carried map lines a Build took out back (on when the world is in the game, else off)
  4. installer.keep_edited: a backup "updated" before Remove the mod / a newer zip
Nothing outside a temp folder is written."""
import json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbservers
from modstudio import worlds as WL, installer as I
from modstudio.game import Game

W = "_FL26TestReady"
fails = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def write(p, data, mode="w"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        f.write(data)


tmp = tempfile.mkdtemp(prefix="fl26-readyedit-")
try:
    game = os.path.join(tmp, "game")
    sd = os.path.join(game, "SiderAddons")
    write(os.path.join(game, "FL_2026.exe"), "")
    write(os.path.join(sd, "sider.ini"), "[cpk]\ncpk.root = .\\livecpk\\%s\n" % W)
    root = os.path.join(sd, "livecpk", W)
    crest = "common/render/symbol/flag/e_104618_r.png"
    write(os.path.join(root, crest), b"AUTHOR-CREST", "wb")
    write(os.path.join(root, ".modstudio"), "FL26 Modpack r10")
    write(os.path.join(root, "leaguebuilder-plan.json"), json.dumps({"world": W, "leagues": [], "others": []}))
    write(os.path.join(sd, "content", "kit-server", W, "Test\\club\\kitmaker.txt".replace("\\", os.sep)), "x\n")
    mp = os.path.join(sd, "content", "kit-server", "map_teams.txt")
    carried = "104618,\"%s\\_kits\\club\" %s\n" % (W, lbservers.TAG)
    write(mp, "1,\"mine\\a\"\n" + carried)
    g = Game(game)
    check(I.ready_world(g, W), "the fake world is a ready world")

    folder = WL.make_editable(g, W)
    check(os.path.isdir(os.path.join(folder, "files", "livecpk", W)), "backup has livecpk\\world")
    check(os.path.isdir(os.path.join(folder, "files", "content", "kit-server", W)), "backup has the kit library folder")
    check(os.path.isfile(os.path.join(folder, "before", "content", "kit-server", "map_teams.txt")), "backup has the map file")
    check(not I.ready_world(g, W) and WL.edited_world(g, W), ".modstudio -> .modstudio-edited")
    check(os.path.isfile(os.path.join(folder, "files", "livecpk", W, ".modstudio")), "backup keeps .modstudio (it is the ready world)")
    check(WL._load_info(folder)["kind"] == "edited", "backup kind edited")
    check(any(f == folder for f, _i in WL.backups_of(sd)), "Restore points lists it")

    # 2. a Build of it: the new folder draws a badge for the gone crest; keep_added keeps the author's
    new = os.path.join(tmp, "new")
    write(os.path.join(new, crest), b"DRAWN-BADGE", "wb")
    write(os.path.join(new, B.MANIFEST), "")
    B.keep_added(root, new, log=lambda t: None, gone={crest})
    check(open(os.path.join(new, crest), "rb").read() == b"AUTHOR-CREST", "the world's own crest kept byte for byte")
    check(os.path.isfile(os.path.join(new, WL.EDITED)), "the edited mark carried into the new build")
    check(not os.path.exists(os.path.join(new, ".modstudio")), ".modstudio not carried")
    new2 = os.path.join(tmp, "new2")
    write(os.path.join(new2, crest), b"DRAWN-BADGE", "wb")
    write(os.path.join(new2, B.MANIFEST), "%s\tdeadbeef\n" % crest)
    B.keep_added(root, new2, log=lambda t: None)
    check(open(os.path.join(new2, crest), "rb").read() == b"DRAWN-BADGE", "without gone: a picture this Build writes is not replaced")

    # 3. backup "built", the world changed by a "Build", then put back
    b2 = WL.backup(g, W, "built")
    write(os.path.join(root, crest), b"CHANGED", "wb")
    write(mp, "1,\"mine\\a\"\n")                                   # the Build took the carried line out
    check(WL.restore(g, b2) == W, "restore of the built backup")
    check(open(os.path.join(root, crest), "rb").read() == b"AUTHOR-CREST", "the world as it was before the Build")
    check(os.path.isfile(os.path.join(b2, "replaced", "livecpk", W, crest)), "the changed world kept in replaced\\")
    check(W in WL.live(g), "the world is in the game (sider.ini)")
    lines = open(mp, encoding="utf-8").read().splitlines()
    check(any(not l.startswith("#") and "%s\\_kits\\club" % W in l for l in lines),
          "carried kit line back, on (the world is in the game)")
    check(lines[0] == "1,\"mine\\a\"", "the user's own map line untouched")
    try:
        WL.restore(g, b2)
        check(False, "a backup put back twice is refused")
    except WL.WorldError:
        check(True, "a backup put back twice is refused")

    # the same with the world out of the game: the line comes back switched off
    b3 = WL.backup(g, W, "built")
    write(os.path.join(sd, "sider.ini"), "[cpk]\n")
    write(mp, "1,\"mine\\a\"\n")
    check(W not in WL.live(g) and WL.restore(g, b3) == W, "restore of a world out of the game")
    lines = open(mp, encoding="utf-8").read().splitlines()
    check(any(l.startswith("#") and "%s\\_kits\\club" % W in l for l in lines), "carried kit line back, switched off")
    check(sum(1 for l in lines if "%s\\_kits\\club" % W in l) == 1, "the carried line once, not twice")

    # 4. keep_edited before Remove the mod / a newer zip
    n = len(WL.backups_of(sd))
    I.keep_edited(g, [W])
    kinds = [i.get("kind") for _f, i in WL.backups_of(sd) if i.get("world") == W]
    check("updated" in kinds, "a backup 'updated' before the world is taken out")
    check(len(kinds) <= WL.KEEP, "no more than KEEP backups of one world (%d)" % len(kinds))
    I.keep_edited(g, ["_FL26NotEdited"])
    check(len(WL.backups_of(sd)) <= n + 1, "no backup of a world that is not edited")
    check(I.worlds_of({"world": "A", "parts": [["world", "B"], ["root", "C"]]}) == ["A", "B"], "worlds_of")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("FAILED: %d" % len(fails) if fails else "all ok")
sys.exit(1 if fails else 0)
