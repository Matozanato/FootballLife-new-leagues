"""python tools/test_first_afc.py -- the first-season AFC Champions League clubs (mato 05.11.;
b2y6421: Shabab Al Ahli, of a league added from the NewLife Database, had no AFC Champions League
in the first season -- the places of a league of ours give clubs only once it has a final table).

First-season European clubs has a fourth column now: the recipe's europe_first "afc", written to
the world file as `first 3 <team id> ...`; fl26swiss.lua passes competition 3 on, and the DLL
puts the clubs in the places of the game's pool clubs in the career's first year (cont_build).
Checked without a game: the plan, the world file line, the cap of 32, a club in two lists, and
the loader and the DLL taking competition 3.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %2d - %s" % (N, name))


def main():
    by_name = {"uae pro league": {"rid": 7, "clubs": 14}, "j2": {"rid": 9, "clubs": 20}}
    r = {"europe_first": {"ucl": [101], "afc": ["UAE Pro League/3", 164, "J2/0"]}}
    got = B.europe_first(r, by_name)
    ok("four lists, the AFC one last", len(got) == 4 and got[3] == [(7, 3), 164, (9, 0)] and got[0] == [101])
    pl = {"leagues": [{"rid": 7, "teams": [70000 + i for i in range(14)]}, {"rid": 9, "teams": []}],
          "europe_first": got}
    lines = B.first_lines(pl)
    ok("world file: first 3 with the new club's id and the game's (%s)" % lines,
       lines == ["first 0 101", "first 3 70003 164"])
    try:
        B.europe_first({"europe_first": {"afc": [str(1000 + i) for i in range(33)]}}, by_name)
        ok("33 AFC clubs refused", False)
    except B.BuildError as e:
        ok("33 AFC clubs refused (%s)" % e, "takes 32" in str(e))
    ok("36 for a UEFA league phase still", len(B.europe_first({"europe_first": {"ucl": list(range(1000, 1036))}}, by_name)[0]) == 36)
    try:
        B.europe_first({"europe_first": {"uecl": [164], "afc": [164]}}, by_name)
        ok("a club in the Conference League and the AFC list refused", False)
    except B.BuildError as e:
        ok("a club in the Conference League and the AFC list refused", "AFC Champions League" in str(e))
    root = os.path.dirname(HERE)
    lua = open(os.path.join(root, "sider", "experimental", "fl26swiss.lua"), encoding="utf-8").read()
    ok("fl26swiss.lua reads first 3", "tonumber(c) <= 3" in lua)
    c = open(os.path.join(HERE, "native", "fl26swiss.c"), encoding="utf-8").read()
    ok("fl26swiss.c takes competition 3 and has room for it",
       "if (comp > 3 ||" in c and "g_first[4][48]" in c and re.search(r"g_nfirst\[3\] && afc_first_season\(\)", c))
    print("all passed")


if __name__ == "__main__":
    main()
