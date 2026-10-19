r"""python tools/test_twin_ids.py

B155b (pepponeee98, 19.10.2026): the same recipe built under a new name gave the new clubs' players
other ids, so an Edit made with the old world showed other people. A world built for the first
time now takes the ids file of the world built from the same leagues (leaguebuilder.twin_build_ids):
  - a world with its own file keeps it (last_build_ids first, nothing else read);
  - the twin is the world with the same new clubs, both ways (TWIN_SHARE);
  - a world that only shares some leagues (a bigger pack) is not a twin, nor one whose NewLife
    clubs at the same places are others;
  - a world being built (.building) or put aside (.old) is never read;
  - of two twins, the one with more clubs in common;
  - a file of 0.2.3 lists only the clubs the recipe gives players (229 of pepponeee98's 262 new
    clubs), one of 0.2.4 every new club: both are the twin.

Fake game folders in a temp folder. No game.
"""
import json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.pop("FL26_DIR", None)

import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def plan(leagues, nl=None):
    return {"leagues": [{"name": n, "teams": list(range(c)),
                         **({"newlife": {"clubs": nl[n]}} if nl and n in nl else {})} for n, c in leagues]}


def ids_file(sd, world, leagues, nl=None, extra=None):
    clubs = {"%s/%d" % (n, k): {"0": 200000 + i * 40 + k} for i, (n, c) in enumerate(leagues) for k in range(c)}
    clubs["101"] = {"+0": 210000}
    body = {"world": world, "clubs": clubs}
    if nl:
        body["club_nl"] = {"%s/%d" % (n, k): str(v) for n, vs in nl.items() for k, v in enumerate(vs)}
    body.update(extra or {})
    d = os.path.join(sd, "livecpk", world)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, B.PLAYER_IDS), "w", encoding="utf-8") as f:
        json.dump(body, f)


def main():
    t = tempfile.mkdtemp(prefix="fl26twin-")
    try:
        game = os.path.join(t, "game")
        sd = os.path.join(game, "SiderAddons")
        os.makedirs(sd)
        open(os.path.join(game, "FL_2026.exe"), "wb").write(b"MZ")
        open(os.path.join(sd, "sider.ini"), "w").write("lua.enabled = 1\n")
        mine = [("Serie C", 20), ("Serie D", 18)]
        nl = {"Serie C": [str(5000 + k) for k in range(20)]}
        ids_file(sd, "_FL26MyWorld 1.4B", mine, nl)
        ids_file(sd, "_FL26Pack", mine + [("Liga %d" % i, 20) for i in range(10)])
        ids_file(sd, "_FL26Other", mine, {"Serie C": [str(9000 + k) for k in range(20)]})
        ids_file(sd, "_FL26New.building", mine, nl)
        said = []
        got = B.twin_build_ids(game, "_FL26MyWorld 1.5", plan(mine, nl), said.append)
        ok("the world of the same leagues is the twin", got.get("world") == "_FL26MyWorld 1.4B")
        ok("its ids come whole, the game clubs' too", got["clubs"]["Serie D/17"] == {"0": 200057}
           and got["clubs"]["101"] == {"+0": 210000})
        ok("the log names the world the ids come from", said and "_FL26MyWorld 1.4B" in said[0]
           and "38 of 38" in said[0])
        ok("a world with its own file reads only it",
           B.last_build_ids(game, "_FL26MyWorld 1.4B").get("world") == "_FL26MyWorld 1.4B")
        ok("a world sharing only some leagues is no twin",
           B.twin_build_ids(game, "_FL26X", plan(mine + [("Liga %d" % i, 20) for i in range(3)])) == {})
        shutil.rmtree(os.path.join(sd, "livecpk", "_FL26MyWorld 1.4B"))
        ok("other NewLife clubs at the same places: no twin",
           B.twin_build_ids(game, "_FL26MyWorld 1.5", plan(mine, nl)) == {})
        ok("a world being built is never read",
           B.twin_build_ids(game, "_FL26MyWorld 1.5", plan(mine, nl)) == {})
        ids_file(sd, "_FL26A", mine)
        ids_file(sd, "_FL26B", [("Serie C", 20), ("Serie D", 17)])
        ok("of two twins, the one with more clubs in common",
           B.twin_build_ids(game, "_FL26Y", plan(mine)).get("world") == "_FL26A")
        for w in ("_FL26A", "_FL26B", "_FL26Pack", "_FL26Other"):
            shutil.rmtree(os.path.join(sd, "livecpk", w))
        big = [("Liga MX", 18), ("PKO", 18), ("Serie C", 20)]
        given = plan(big)
        given["players"] = {"%s/%d" % (n, k): {} for n, c in big for k in range(c) if not (n == "PKO" and k < 5)}
        given["players"]["101"] = {}
        ids_file(sd, "_FL26Old 023", [("Liga MX", 18), ("Serie C", 20)])
        with open(os.path.join(sd, "livecpk", "_FL26Old 023", B.PLAYER_IDS), encoding="utf-8") as f:
            body = json.load(f)
        for k in range(5, 18):
            body["clubs"]["PKO/%d" % k] = {"0": 230000 + k}
        with open(os.path.join(sd, "livecpk", "_FL26Old 023", B.PLAYER_IDS), "w", encoding="utf-8") as f:
            json.dump(body, f)
        said = []
        ok("a file of 0.2.3 (only the clubs with players of the recipe, 51 of 56) is the twin",
           B.twin_build_ids(game, "_FL26New 024", given, said.append).get("world") == "_FL26Old 023"
           and "51 of 51" in said[0])
        shutil.rmtree(os.path.join(sd, "livecpk", "_FL26Old 023"))
        ids_file(sd, "_FL26Old 024", big)
        ok("a file of 0.2.4 (every new club) is the twin",
           B.twin_build_ids(game, "_FL26New 024", given).get("world") == "_FL26Old 024")
        ok("a plan of no new clubs takes nothing", B.twin_build_ids(game, "_FL26Z", {"leagues": []}) == {})
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
