"""python test_club_order.py [<folder with the game's tables>] -- request #6 (06.11.2026, FL 2027
only): a league's clubs in Select Team in an order of yours.

Select Team (and Edit) lists a league's clubs in the order of its entries: the heading builder
0x140c93780 takes the slot's list through 0x141518610 as it is, with no sort, and fl26clubs.dll
serves our slots from the regulation's clubs. Build enters the clubs of our leagues A-Z
(club_order); a league's club_order (places, from 0) puts those first, in that order, and the
rest after them A-Z. FL26 refuses the key and keeps A-Z. Remove club / Insert club in Mod
Studio move the places in club_order with the clubs. Without the tables only the plan-free
parts run."""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import mkleague as M

N = 0
NAMES = ["Zeta", "Alpha", "Mike", "FC Bravo", "Echo", "Kilo", "Delta", "Hotel", "Golf", "India", "Lima", "Juliet"]


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def raises(fn, part):
    try:
        fn()
    except B.BuildError as e:
        return part in str(e)
    return False


def offline():
    ok("places kept in their order", B.select_order([5, 2, 11], 12, "L") == [5, 2, 11])
    ok("a place past the league's clubs is dropped", B.select_order([5, 14, 2], 12, "L") == [5, 2])
    ok("a place twice is refused", raises(lambda: B.select_order([1, 1], 12, "L"), "twice"))
    ok("a name is refused", raises(lambda: B.select_order(["Alpha"], 12, "L"), "not a club's place"))
    ok("not a list is refused", raises(lambda: B.select_order("az", 12, "L"), "is a list"))
    from modstudio.project import Project
    p = Project(None)
    p.recipe["leagues"] = [{"name": "L", "clubs": 12, "club_names": list(NAMES), "club_order": [5, 2, 11, 0]}]
    L = p.recipe["leagues"][0]
    ok("Remove club takes its place out and moves the ones after it", p.shift_places("L", 2, -1)
       and L["club_order"] == [4, 10, 0])
    ok("Insert club moves the places after it", p.shift_places("L", 0, 1) and L["club_order"] == [5, 11, 1])
    p.recipe["leagues"][0]["club_order"] = [3]
    ok("the last place of it removed: no club_order left", p.shift_places("L", 3, -1) and "club_order" not in L)


def game_dir():
    game = tempfile.mkdtemp(prefix="fl26-cluborder-")
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(game, "SiderAddons", d))
    with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]\n")
    return game


def entry_order(recipe, base):
    """the plan, and the league's clubs as places, in the order of the world's entries"""
    game, fl27 = game_dir(), B.FL27
    try:
        pl = B.plan(recipe, base)
        B.build(pl, base, game, False, log=lambda t: None)
        world = os.path.join(game, "SiderAddons", "livecpk", recipe["world"])
        entf = [os.path.join(r, f) for r, _d, fs in os.walk(world) for f in fs if f == "CompetitionEntry.bin"]
        ents = M.load(os.path.dirname(entf[0]), "CompetitionEntry.bin")
        p = pl["leagues"][0]
        rows = [i for i in range(0, len(ents) - M.ENT + 1, M.ENT) if M.ent_cid(ents, i) == p["cid"]]
        rows.sort(key=lambda i: ents[i + M.E_ORDER])
        place = {t: k for k, t in enumerate(p["teams"])}
        return pl, [place[int.from_bytes(ents[i + M.E_TEAM:i + M.E_TEAM + 4], "little")] for i in rows]
    finally:
        B.FL27 = fl27
        shutil.rmtree(game, ignore_errors=True)


def recipe(order=None):
    L = {"name": "Zel Order", "country": "San Marino", "clubs": 12, "legs": 2, "exchange": 0,
         "club_names": list(NAMES)}
    if order is not None:
        L["club_order"] = order
    return {"world": "_FL26ClubOrder", "leagues": [L]}


def built(base):
    az = sorted(range(12), key=lambda k: B.club_sort_key(NAMES[k]))
    ok("A-Z files FC Bravo under B", NAMES[az[1]] == "FC Bravo")
    fl27 = B.FL27
    B.FL27 = False
    try:
        ok("FL26: an own club order is refused", raises(lambda: B.plan(recipe([5, 2]), base), "FL 2027 only"))
        _pl, got = entry_order(recipe(), base)
        ok("FL26 / no club_order: the clubs A-Z (%s)" % [NAMES[k] for k in got], got == az)
        B.FL27 = True
        pl, got = entry_order(recipe([5, 2, 11]), base)
        ok("FL 2027: Kilo, Mike, Juliet first, then A-Z (%s)" % [NAMES[k] for k in got],
           got == [5, 2, 11] + [k for k in az if k not in (5, 2, 11)])
        B.FL27 = True
        ok("the recipe keeps it", B.recipe_from_plan(pl, base)["leagues"][0].get("club_order") == [5, 2, 11])
        whole = list(reversed(az))
        _pl, got = entry_order(recipe(whole), base)
        ok("every place named: exactly that order", got == whole)
    finally:
        B.FL27 = fl27


if __name__ == "__main__":
    offline()
    if len(sys.argv) > 1:
        built(sys.argv[1])
    print("1..%d" % N)
