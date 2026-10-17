"""python tools/test_newlife_scale.py [<folder with the game's tables>]

NewLife 1.5b7 (17.10.): one rating method for every player, the game's own too, on the game's
scale (newlife.json "scale": "game"), and the game's players the release had as new rows now carry
their game id (B111: Alisson, Gabriel, Tsimikas -- 1.5b6 gave each a second, inflated copy).

Checks that:
  - same_player takes an id the release gives when the names fit as two databases write one man
    ("Alisson" / "Alisson Becker", "Gabriel" / "Gabriel Magalhaes", "Kostas Tsimikas" /
    "Konstantinos Tsimikas", "Ebere Eze" / "Eberechi Eze") and refuses another man;
  - game_scale leaves a release with "scale": "game" as it is, and still remaps one without it;
  - with the game's tables: the mover moves the game's Alisson (63474) for a row "Alisson" with
    that game_id, where it made a copy before (same_name refuses a one-word name).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "modstudio"))
import lbplayers as P
import playeredit as E
import newlife as NL

N = 0


def ok(cond, what):
    global N
    assert cond, what
    N += 1
    print("ok %d - %s" % (N, what))


def names():
    for a, b in (("Alisson", "Alisson Becker"), ("Gabriel", "Gabriel Magalhães"), ("Kostas Tsimikas", "Konstantinos Tsimikas"),
                 ("Ebere Eze", "Eberechi Eze"), ("Benjamin White", "Ben White"), ("Kenan Yıldız", "Kenan Yildiz"),
                 ("Yann Aurel Bisseck", "Yann Bisseck"), ("F. Niederlechner", "Florian Niederlechner")):
        ok(P.same_player(a, b) and P.same_player(b, a), "same_player: %s / %s" % (a, b))
    ok(not P.same_name("Alisson", "Alisson Becker"), "same_name still refuses a one-word name (by name alone)")
    for a, b in (("Alisson", "Ederson Moraes"), ("Theo Hernández", "Lucas Hernández"), ("Gabriel", "Gabi"),
                 ("Mario Pasalic", "Marko Pjaca"), ("Ze", "Ze Roberto"), ("", "Alisson Becker")):
        ok(not P.same_player(a, b), "same_player refuses: %r / %r" % (a, b))


class Rel:
    def __init__(self, meta, rows):
        self.meta, self.rows = meta, rows

    def squad(self, c):
        return self.rows


class Db:
    def __init__(self, rows):
        self.rows = rows
        self.index = {g: g for g in rows}

    def name(self, g):
        return self.rows[g]["name"]

    def row(self, g):
        return self.rows[g]


def row(name, level, gid=""):
    r = {n: str(level) for n, _b in E.ABILITIES}
    r.update({"name": name, "Registered Position": "CF", "game_id": str(gid)})
    return r


def scale():
    ours = [row("Player %d" % i, 60 + i % 30 + 4, 1000 + i) for i in range(80)]    # ours 4 above the game
    game = {1000 + i: row("Player %d" % i, 60 + i % 30) for i in range(80)}
    f = NL.game_scale(Rel({}, ours), Db(game), [1])
    ok(f(80) == 76, "no scale key: the release's 80 is the game's 76 (got %s)" % f(80))
    g = NL.game_scale(Rel({"scale": "game"}, ours), Db(game), [1])
    ok(all(g(o) == o for o in (45, 70, 80, 95)), "scale game: no remap")


def mover(base):
    info = {"base": base, "national": set()}
    mv, db = NL._movers({}, info)
    if 63474 not in db.index:
        print("skip: these tables have no 63474")
        return
    ok(db.name(63474).startswith("Alisson"), "the game's 63474 is %s" % db.name(63474))
    what, g, _x = mv({"game_id": "63474", "name": "Alisson"})
    ok((what, g) == ("move", "63474"), "B111: a row 'Alisson' with game_id 63474 moves the game's Alisson (%s)" % what)
    what, g, _x = mv({"game_id": "63474", "name": "Ederson"})
    ok(what == "copy", "another man under that id is still a copy")


if __name__ == "__main__":
    names()
    scale()
    base = sys.argv[1] if len(sys.argv) > 1 else r"C:\work\fl26base\ex_merged\common\etc\pesdb"
    if os.path.isdir(base):
        mover(base)
    else:
        print("skip: no game tables at %s" % base)
    print("1..%d" % N)
