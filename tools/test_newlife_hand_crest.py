"""python test_newlife_hand_crest.py <NewLife folder> <folder with the game's tables> -- B196: a
crest (or any change) the person sets on a place "Bring the game's leagues to this season" gave
another club stays with that club when the leagues are brought again (a newer release): the place
goes to the same club again, crest and all. Before, the place counted as changed by hand once the
earlier refresh was undone, was skipped, and the game's old club came back under the other club's
crest (the Worldpack's 44 crests of B126: Bolton, Lanerossi Vicenza ... back to the game's clubs)."""
import copy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
from modstudio import newlife as N

N_OK = 0


def ok(name, cond):
    global N_OK
    assert cond, name
    N_OK += 1
    print("ok %d - %s" % (N_OK, name))


def main(folder, base):
    rel = N.Release(folder)
    info = B.game_info(base)
    cids = [p["cid"] for p in N.game_league_plan({"leagues": []}, rel, info)]
    r = {"leagues": []}
    first = N.refresh_game_leagues(r, rel, info, cids)
    rep = dict(r["newlife_game"]["replaced"])
    ok("the release gives places of the game's leagues to other clubs (%d)" % len(rep), len(rep) >= 3)
    places = sorted(rep, key=int)[:3]
    a, b, c = places
    r["edits"]["clubs"][a]["crest"] = r"C:\mine\crest-a.png"            # a crest of the person's own
    r["edits"]["clubs"][b]["stadium"] = "Mine"                          # another change of theirs
    again = copy.deepcopy(r)
    n = N.refresh_game_leagues(again, rel, info, cids)
    rep2 = again["newlife_game"]["replaced"]
    ok("brought again: as many places given away (%d, was %d)" % (n["replaced"], first["replaced"]),
       n["replaced"] == first["replaced"] and set(rep2) == set(rep))
    ok("the place with the person's crest went to the same club (%s)" % rep2.get(a, {}).get("name"),
       rep2.get(a, {}).get("name") == rep[a]["name"])
    ok("the person's crest is kept on it", again["edits"]["clubs"][a].get("crest") == r"C:\mine\crest-a.png")
    ok("its name and shirt are the release's", again["edits"]["clubs"][a].get("name") == rep[a]["name"]
       and again["edits"]["clubs"][a].get("kit") == rep[a]["kit"])
    ok("another change of the person's is kept too", again["edits"]["clubs"][b].get("stadium") == "Mine")
    ok("nothing lost", n.get("hand_lost") == 0)
    ok("the record holds the release's crest, not the person's (undo takes back only its own)",
       rep2[a].get("crest") != r"C:\mine\crest-a.png")
    # the place held another club before (an older release): the person's change was that club's
    older = copy.deepcopy(r)
    older["newlife_game"]["replaced"][c] = dict(rep[c], name="Some Club Of Before")
    older["edits"]["clubs"][c].update(name="Some Club Of Before", crest=r"C:\mine\before.png")
    m = N.refresh_game_leagues(older, rel, info, cids)
    ok("a place whose club changes gets the release's club (%s)" % older["edits"]["clubs"][c].get("name"),
       older["newlife_game"]["replaced"][c]["name"] == rep[c]["name"]
       and older["edits"]["clubs"][c].get("name") == rep[c]["name"])
    ok("and not the crest set for the club before; the count says one change went",
       older["edits"]["clubs"][c].get("crest") != r"C:\mine\before.png" and m.get("hand_lost") == 1)
    # undo after a refresh that kept the crest: only the person's change is left
    N.undo_game_leagues(again)
    left = (again.get("edits") or {}).get("clubs") or {}
    ok("undo leaves only the person's own changes", left.get(a) == {"crest": r"C:\mine\crest-a.png"}
       and left.get(b) == {"stadium": "Mine"})
    print("1..%d" % N_OK)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
