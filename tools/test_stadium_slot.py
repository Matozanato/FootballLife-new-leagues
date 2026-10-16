r"""python test_stadium_slot.py -> the stadium slot Mod Studio writes for a stadium folder (0.2.4, Discord
Erax: a stadium of the game, 'common\Estadio del Tauro', was dark in the match). Such a folder has no
model, only the lighting and nets for the game's own stadium, and its number is in its picture
(common\render\thumbnail\stadium\st055.dds); written under slot 009 the game drew it with nothing
lit. The picture's number comes first, then the AddOn folders, then the one model folder; the folder
on this PC beats the recipe's slot."""
import os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbstadiums as S
from modstudio import servers

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def make(root, *files):
    for f in files:
        p = os.path.join(root, *f.split("/"))
        if f.endswith("/"):
            os.makedirs(p, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").close()
    return root


with tempfile.TemporaryDirectory() as t:
    lib = os.path.join(t, "content", "stadium-server")
    tauro = make(os.path.join(lib, "common", "Estadio del Tauro"),
                 "common/render/thumbnail/stadium/st055.dds", "AddOn/Light/055/", "AddOn/fog/055/")
    ok("a stadium of the game: the picture's number (055)", S.stadium_slot(tauro) == "055")
    other = make(os.path.join(lib, "Europe", "Mixed"),
                 "common/render/thumbnail/stadium/ST031.DDS", "AddOn/Light/009/", "AddOn/fog/009/",
                 "AddOn/Cutscene/009/")
    ok("the picture beats the AddOn folders, any case (031)", S.stadium_slot(other) == "031")
    two = make(os.path.join(lib, "Europe", "Two pictures"),
               "common/render/thumbnail/stadium/st010.dds", "common/render/thumbnail/stadium/st011.dds",
               "AddOn/Light/012/", "AddOn/fog/012/", "AddOn/Cutscene/013/")
    ok("two pictures: the AddOn folders decide (012)", S.stadium_slot(two) == "012")
    addon = make(os.path.join(lib, "Europe", "AddOn only"), "AddOn/Light/009/", "AddOn/Large_hexagonal_net/009/")
    ok("AddOn folders only: as before (009)", S.stadium_slot(addon) == "009")
    model = make(os.path.join(lib, "Europe", "Model only"), "Asset/model/bg/st120/")
    ok("the one model folder (120)", S.stadium_slot(model) == "120")
    empty = make(os.path.join(lib, "Europe", "Nothing"), "readme.txt")
    ok("nothing names a slot: empty", S.stadium_slot(empty) == "")
    ok("no folder: empty", S.stadium_slot(os.path.join(lib, "nope")) == "")
    ok("Mod Studio's Choose stadium reads the same slot",
       [servers.stadium_id(f) for f in (tauro, other, two, addon, model, empty)]
       == [S.stadium_slot(f) for f in (tauro, other, two, addon, model, empty)])

    pl = {"leagues": [{"name": "Zelia", "teams": [900001, 900002, 900003, 900004]}],
          "players": {"Zelia/0": {"stadium": {"folder": r"common\Estadio del Tauro", "slot": "009"}},
                      "Zelia/1": {"stadium": {"folder": r"Europe\Nothing", "slot": "012"}},
                      "Zelia/2": {"stadium": {"folder": r"Europe\Nothing"}},
                      "Zelia/3": {"stadium": {"folder": r"Europe\Model only"}}}}
    log = []
    ok("four home stadiums written", S.write(pl, t, log.append) == 4)
    text = open(os.path.join(lib, "map_teams.txt"), encoding="utf-8").read()
    lines = {int(l.split(",")[0]): l for l in text.splitlines() if l[:1].isdigit()}
    ok("an old recipe's 009 for Estadio del Tauro is written as 055",
       lines[900001].split(",")[1].strip() == "055")
    ok("and the log says so", any("Estadio del Tauro is stadium 055, not 009" in l for l in log))
    ok("a folder that names no slot keeps the recipe's (012)", lines[900002].split(",")[1].strip() == "012")
    ok("no slot anywhere: 009, said in the log", lines[900003].split(",")[1].strip() == "009"
       and any("names no stadium slot" in l and "900003" in l for l in log))
    ok("no slot in the recipe: the folder's (120)", lines[900004].split(",")[1].strip() == "120")
print("all passed (%d)" % N)
