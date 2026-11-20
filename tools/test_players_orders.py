r"""python tools/test_players_orders.py

The Players page's squad order (B331, B332; snellejelle_2, #support 05.11.2026, Mod Studio 0.3.0).

B331: Build stopped on "squad orders clash: club 71584: two players have squad order 25". The page
left an order out of the recipe where it equalled the player's "original" one -- the base squad's
order for his place, which the games number apart (FL26 1.3's 30 places run 0-23, 27-31, 33;
FL27's 0-26, 35-37) -- so a club ordered over FL26's tables had two players on one order in FL27.
The Squad order box wrote the number alone (Jong Genk: 26 twice); a player who left kept his
old order and had it back on top of another's; a player who joins took the squad's length as his
order, which a base squad with gaps has taken. Now every player of a club ordered here has his
order written out, the box moves the player to the place typed, and the page never writes one
order twice.

B332: with no game tables (a switch between FL26 and FL27, or before they are unpacked) a club
with players who join it crashed the page: 'NoneType' object has no attribute 'row' in joiner_row
(original <- view <- fill_squad <- club_picked <- ... <- BuilderPage._tables).

The page's own methods on a stand-in with no window; no game, no tables (offscreen).
"""
import collections, os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


FL26 = list(range(24)) + [27, 28, 29, 30, 31, 33]       # the base squad's orders by place: FL26 1.3's
FL27 = list(range(27)) + [35, 36, 37]


def rows(orders):
    pos = ["GK", "CB", "CB", "LB", "RB", "DMF", "CMF", "CMF", "LWF", "RWF", "CF"]
    return [{"player": str(k), "order": str(o), "shirt": str(k + 1), "name": "",
             "Registered Position": pos[k % len(pos)]} for k, o in enumerate(orders)]


def main():
    qa = QApplication.instance() or QApplication([])
    from modstudio.project import Project
    from modstudio.pages import players as PP

    class Page:
        pass
    for m in ("view", "original", "next_order", "joiner_row", "set_orders", "put_order", "shift", "undo_player",
              "edited", "changes", "ref_of", "moves", "is_national", "club_label", "new_names", "game_name",
              "home_of", "game_player", "auto_formation", "places", "lineup", "own_id"):
        if hasattr(PP.Players, m):               # 0.3.0 had no next_order / put_order
            setattr(Page, m, getattr(PP.Players, m))
    p = Project(types.SimpleNamespace(settings={}, save_settings=lambda: None))
    ok("no game tables: project.squads() is None", p.base is None and p.squads() is None)
    p.recipe["leagues"] = [{"name": "Belgian Challenger Pro League", "clubs": 2,
                            "club_names": ["Jong KAA Gent", "Jong Genk"]}]
    page = Page()
    page.project, page.app, page._filling = p, types.SimpleNamespace(settings={}, game=None), False
    page.fill_squad = lambda: None
    page.state = {}
    typed = {}
    page._get = lambda key: typed[key]
    page.say = lambda *a: None
    page._mark = page.update_row = lambda *a: None

    def put(key, place):
        """Squad order typed in the box for one player"""
        page.cur = key
        typed["order"] = str(place)
        page.edited("order")

    def orders(club=None):
        """{key: order} of the club's live players as the page shows them, and the gone ones'"""
        v = page.view()
        return ({k: m.get("order") for k, m, ch, g in v if not g}, {k: m.get("order") for k, m, ch, g in v if g})

    def distinct(v):
        return len(set(v.values())) == len(v) and all(str(o).isdigit() for o in v.values())

    def written():
        c = page.changes()
        return all("order" in (c.get("edits") or {}).get(k, {}) for k, m, ch, g in page.view())

    # ---- a new club ordered over FL26's tables, then FL27's ----
    page.club, page.rows = "Belgian Challenger Pro League/0", rows(FL26)
    put("25", 28)                                  # El Hadji Seck to 28, where FL26 has place 25
    put("24", 25)                                  # Alexandre Chaidron to 25
    live, _g = orders()
    seck = live["25"]
    ok("B331: the moved players stand where they were put (24 at 25; 25 at %s)" % seck,
       live["24"] == "25" and seck in ("27", "28"))
    ok("B331: every player has his order written out (none left to the base squad's)", written())
    page.rows = rows(FL27)                         # the same recipe on FL27's tables
    live, _g = orders()
    ok("B331: over FL27's tables no two players share an order (%s)" %
       sorted(o for o, n in collections.Counter(live.values()).items() if n > 1), distinct(live))
    ok("B331: and the order is the one set over FL26's", live["24"] == "25" and live["25"] == seck)

    # the box changes with every digit: 2, then 26 -- the player ends at 26, the rest as they were
    before = [k for k, o in sorted(orders()[0].items(), key=lambda x: int(x[1])) if k != "8"]
    page.cur = "8"
    for digits in ("2", "26"):
        typed["order"] = digits
        page.edited("order")
    live, _g = orders()
    after = [k for k, o in sorted(live.items(), key=lambda x: int(x[1])) if k != "8"]
    ok("B331: Squad order typed 2, 26: he stands at 26", live["8"] == "26")
    ok("B331: the others keep their order among themselves", after == before)
    ok("B331: still one order each", distinct(live))

    # a player who leaves, then is taken back
    c = page.changes(True)
    c["remove"] = ["3"]
    page.cur = "0"
    page.shift(1)                                  # an order set while 3 is out
    live, gone = orders()
    ok("B331: the order counts the players who stay, 0-%d" % (len(live) - 1),
       sorted(int(o) for o in live.values()) == list(range(len(live))))
    ok("B331: the one who leaves comes after them", gone == {"3": str(len(live))})
    c["remove"] = []
    live, _g = orders()
    ok("B331: taken back, he shares his order with nobody", distinct(live))

    # Undo for one player keeps his place in an order set here
    page.cur = "5"
    page.undo_player()
    live, _g = orders()
    ok("B331: Undo player keeps his place in the order", distinct(live) and written())

    # ---- a club of the game: a player who joins, with a base squad whose orders have gaps ----
    page.club, page.rows = "130", rows(FL26)
    p.players()["130"] = {"join": ["777777"]}
    live, _g = orders()
    ok("B331: one who joins comes after the squad's last order (34, not 30 which place 27 has): %s"
       % live["777777"], live["777777"] == "34" and distinct(live))
    put("777777", 0)
    live, _g = orders()
    ok("B331: he can be put first, everyone written out, one order each",
       live["777777"] == "0" and distinct(live) and written())

    # ---- B332: no game tables, a club with players who join it ----
    page.club, page.rows = "Belgian Challenger Pro League/1", []
    p.players()["Belgian Challenger Pro League/1"] = {
        "join": ["169611", "Belgian Challenger Pro League/0/4"],
        "edits": {"169611": {"order": "1"}, "Belgian Challenger Pro League/0/4": {"name": "Zion Henry"}}}
    try:
        v = page.view()
        crash = None
    except AttributeError as e:
        v, crash = [], e
    ok("B332: the squad shows with no game tables (%s)" % crash, crash is None)
    ok("B332: the players who join are listed",
       sorted(k for k, m, ch, g in v) == ["169611", "Belgian Challenger Pro League/0/4"])
    ok("B332: a game player not known without tables reads ?", next(m for k, m, ch, g in v if k == "169611")["name"] == "?")
    ok("B332: a new club's player keeps the recipe's name", next(
        m for k, m, ch, g in v if k == "Belgian Challenger Pro League/0/4")["name"] == "Zion Henry")
    ok("B332: game_player and home_of answer without tables",
       page.game_player("169611") is False and page.home_of("169611") is None)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
