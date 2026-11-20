"""The world file's `confgroups` line (FL 2027, fl26confgroups.dll): which Select Team slot and
which Competition Info region is in which confederation group -- 0 UEFA, 1 CONMEBOL, 2 CONCACAF,
3 AFC, 4 CAF, 5 OFC -- from the country's confederation.

    python tools/test_confgroups.py [<base pesdb folder>]

1. Without the game's tables (country_ids / slot_countries stood in): the game's own slots and
   regions get their country's group; ours get their country's (Australia AFC, Israel and
   Kazakhstan UEFA, as Country.bin has them); the pools get theirs unless a league of ours sits on
   the slot; the national teams, "Other", no slot, the club competitions and Classic Teams get
   none; a slot two confederations share gets none; FL26 gets no line; one group, no line.
   `countries`: a slot's Country.bin id (the game's slots by their country, ours by the league's),
   none for a pool slot or a slot of two countries; `confnames` the names of those countries;
   `cups`: the Club World Cup for every group, UCL / UEL (and the UECL with one) for UEFA, the
   Libertadores and the AFC Champions League, each continental cup of ours in its group -- never
   the game's ICC cups (100..102) nor the UEFA Super Cup (4).
2. With the base tables ($FL26_PESDB, the argument, or fl26-modding-research/out/base-pesdb): the
   real Country.bin's codes for Australia, Israel, Kazakhstan, Mexico and New Zealand, and the
   line of a world with them.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as LB
import fl26world

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1


def parse(line):
    head, _, rest = line.partition(" ")
    assert head == "confgroups", line
    out = {}
    for part in rest.split():
        k, _, v = part.partition("=")
        pairs = [(int(a), int(b)) for a, b in (e.split(":") for e in v.split(",") if e)]
        out[k] = pairs if k == "cups" else dict(pairs)
    return out


def names(line):
    head, _, rest = line.partition(" ")
    assert head == "confnames", line
    return {int(c): nm for c, _, nm in (e.partition(":") for e in rest.split("|"))}


# ---- 1. stood-in tables ----
FIDS = {"England": 1, "Spain": 2, "Brazil": 3, "Usa": 4, "Japan": 5, "Australia": 10, "Israel": 11,
        "Kazakhstan": 12, "Mexico": 13, "Nigeria": 14, "New Zealand": 15, "Peru": 16, "China": 17,
        "France": 18, "Italy": 19, "Congo (20)": 20, "Congo (21)": 21}
CONFED = {1: 2, 2: 2, 3: 4, 4: 6, 5: 3, 10: 3, 11: 2, 12: 2, 13: 6, 14: 5, 15: 7, 16: 4, 17: 3, 18: 2, 19: 2,
          20: 5, 21: 5}
real_ids, real_slots = LB.country_ids, LB.slot_countries
LB.country_ids = lambda base: sorted(FIDS.items())
LB.slot_countries = lambda base: dict(LB.SLOT_COUNTRY)


def league(country, slot, region):
    return {"country": FIDS[country], "slot": slot, "region": region, "rid": 300 + slot}


pl = {"leagues": [league("Australia", 182, 40), league("Israel", 183, 41), league("Kazakhstan", 184, 42),
                  league("Mexico", 185, 43), league("Nigeria", 186, 44), league("New Zealand", 187, 45),
                  league("Peru", 73, 46),                          # on the Latin American pool's slot
                  league("England", 69, 2),                        # England D3 on Other European's slot
                  {"country": FIDS["Spain"], "slot": fl26world.NO_SLOT, "region": 4, "rid": 400}]}
LB.FL27 = False
ok("FL26: no line", LB.confgroups_lines(pl, None, CONFED) == [])
LB.FL27 = True
lines = LB.confgroups_lines(pl, None, CONFED)
ok("two lines: confgroups, confnames", len(lines) == 2)
g = parse(lines[0])
S, R, C, CUP = g["slots"], g["regions"], g["countries"], g["cups"]
NM = names(lines[1])
ok("England's slots UEFA", S[7] == 0 and S[50] == 0)
ok("Brazil CONMEBOL, the MLS CONCACAF, Japan and China AFC, Germany UEFA",
   S[13] == 1 and S[17] == 2 and S[18] == 3 and S[102] == 3 and S[16] == 0)
ok("Australia AFC, Israel and Kazakhstan UEFA", S[182] == 3 and S[183] == 0 and S[184] == 0)
ok("Mexico CONCACAF, Nigeria CAF, New Zealand OFC", S[185] == 2 and S[186] == 4 and S[187] == 5)
ok("a league of ours on a pool slot: its own country", S[73] == 1 and S[69] == 0)
ok("the pools without a league of ours: their group", S[75] == 4 and S[70] == 3)
ok("no group for the national teams, Other, no slot, the game's 71 and 256",
   not any(s in S for s in list(range(7)) + [71, fl26world.NO_SLOT, fl26world.OTHER_SLOT, 256]))
g2 = parse(LB.confgroups_lines({"leagues": pl["leagues"] + [league("Japan", 71, 47), league("England", 256, 2)]},
                               None, CONFED)[0])["slots"]
ok("a league of ours on 71 or 256: its country's group", g2[71] == 3 and g2[256] == 0)
ok("regions: ours by country", R[40] == 3 and R[41] == 0 and R[42] == 0 and R[43] == 2 and R[44] == 4
   and R[45] == 5 and R[46] == 1)
ok("regions: the game's countries and groups", R[2] == 0 and R[16] == 1 and R[21] == 3 and R[28] == 3
   and R[22] == 0 and R[23] == 2 and R[24] == 3)
ok("no group for the club competitions and Classic Teams", not any(r in R for r in (1, 26, 25)))
ok("all six groups there", set(S.values()) == set(range(6)))
ok("countries: the game's slots by country", C[7] == 1 and C[50] == 1 and C[11] == 2 and C[13] == 3 and C[17] == 4)
ok("countries: ours by the league's", C[182] == 10 and C[187] == 15 and C[73] == 16 and C[69] == 1)
ok("countries: none for a pool slot of the game", not any(s in C for s in (70, 75)))
ok("countries: only grouped slots", set(C) <= set(S))
ok("confnames: the countries named", NM[1] == "England" and NM[10] == "Australia" and NM[4] == "USA"
   and set(NM) == set(C.values()))
ok("cups: the Club World Cup in every group", all((gg, 1) in CUP for gg in range(6)))
ok("cups: UCL, UEL for UEFA, the Libertadores, the AFC CL; no UECL without one",
   (0, 2) in CUP and (0, 3) in CUP and (1, 5) in CUP and (3, 8) in CUP and (0, LB.UECL_CID) not in CUP)
ok("cups: never the Super Cup nor the ICC", not any(c in (4, 100, 101, 102) for _g, c in CUP))
cu = parse(LB.confgroups_lines(dict(pl, uecl=True, ccups=[{"number": 9, "cid": 300}, {"number": 6, "cid": 301},
                                                           {"number": 14, "cid": 302}, {"number": 13}]),
                               None, CONFED)[0])["cups"]
ok("cups: the UECL with one, ours in their group, none without a cid",
   (0, LB.UECL_CID) in cu and (1, 300) in cu and (4, 301) in cu and (5, 302) in cu and len(cu) == len(CUP) + 4)
two = parse(LB.confgroups_lines({"leagues": pl["leagues"] + [league("France", 182, 47)]}, None, CONFED)[0])
ok("a slot of two countries: no country", 182 not in two["countries"])
dup = LB.confgroups_lines({"leagues": pl["leagues"] + [league("Congo (20)", 188, 48)]}, None, CONFED)
ok("a name the table has twice: without its id", names(dup[1])[20] == "Congo")

clash = {"leagues": [league("Mexico", 190, 50), league("Peru", 190, 51)]}
gc = parse(LB.confgroups_lines(clash, None, CONFED)[0])
ok("a slot of two confederations: no group", 190 not in gc["slots"] and gc["regions"][50] == 2)

# confederation logos (09.11.): `emblems` for the ones whose picture is there, and their emblem files
import tempfile
pic = os.path.join(tempfile.mkdtemp(), "uefa.png")
open(pic, "wb").write(b"png")
lg = dict(pl, confederation_logos={"UEFA": pic, "CAF": pic, "OFC": pic + ".gone"})
em = parse(LB.confgroups_lines(lg, None, CONFED)[0])
ok("emblems: UEFA and CAF on 9900 + group, a picture that is gone none",
   em["emblems"] == {0: LB.CONF_EMBLEM_CID, 4: LB.CONF_EMBLEM_CID + 4})
ok("emblems: none without logos", "emblems" not in parse(lines[0]))
# B447: a world from a zip built again -- the picture is gone, the world folder has the emblem
old = tempfile.mkdtemp()
for r in LB.logo_files(LB.CONF_EMBLEM_CID + 5):
    os.makedirs(os.path.dirname(os.path.join(old, r)), exist_ok=True)
    open(os.path.join(old, r), "wb").write(b"png")
lg2 = dict(lg)
ok("emblems: a gone picture whose emblem the world has is kept (OFC)", LB.conf_logos_kept(lg2, old) == ["OFC"]
   and parse(LB.confgroups_lines(lg2, None, CONFED)[0])["emblems"].get(5) == LB.CONF_EMBLEM_CID + 5)
gone = set()
jobs = [j for j in LB.picture_jobs({"leagues": [], "confederation_logos": lg2["confederation_logos"],
                                    LB.CONF_KEPT: lg2[LB.CONF_KEPT]}, None, log=lambda *a: None, gone=gone)[0]
        if j[1][0] == LB.CONF_EMBLEM_CID + 5]
ok("emblems: its files are named as gone, so the Build keeps the world's",
   len(jobs) == 1 and jobs[0][1][-1] is None and set(LB.logo_files(LB.CONF_EMBLEM_CID + 5)) <= gone)
ok("emblems: no world, no kept emblem", LB.conf_logos_kept(dict(lg), tempfile.mkdtemp()) == [])
LB.FL27 = False
ok("emblems: FL26 none", LB.conf_logos(lg) == {})
LB.FL27 = True
ok("emblems: a recipe setting (recipe_from_plan keeps it)", "confederation_logos" in LB.RECIPE_SETTINGS)
ok("emblems: above every competition id", LB.CONF_EMBLEM_CID > max(fl26world.LEAGUE_BAND))
jobs = [j for j in LB.picture_jobs({"leagues": [], "confederation_logos": {"UEFA": pic}}, None, log=lambda *a: None)[0]
        if j[1][0] == LB.CONF_EMBLEM_CID]
ok("emblems: Build writes UEFA's logo as emb_9900", len(jobs) == 1 and jobs[0][0] == "league_logo"
   and jobs[0][1][2] == pic and "common/render/symbol/emblemLc/emb_9900_l.png" in jobs[0][2])

LB.slot_countries = lambda base: {7: "England", 50: "England"}
saved = LB.SHIPPED_REGIONS, LB.POOL_SLOT_CONF
LB.SHIPPED_REGIONS = [r for r in saved[0] if r[2] in (0, 2, 9)]
LB.POOL_SLOT_CONF = {69: 2}
ok("one group only: no line", LB.confgroups_lines({"leagues": [league("Spain", 200, 4)]}, None, CONFED) == [])
LB.SHIPPED_REGIONS, LB.POOL_SLOT_CONF = saved
LB.country_ids, LB.slot_countries = real_ids, real_slots

# ---- 2. the game's tables ----
base = (sys.argv[1] if len(sys.argv) > 1 else None) or os.environ.get("FL26_PESDB") \
    or "D:/dev/fl26-modding-research/out/base-pesdb"
if os.path.exists(os.path.join(base, "Country.bin")) and os.path.exists(os.path.join(base, "CompetitionRegulation.bin")):
    confed = LB.confederations(base)
    fids = dict(LB.country_ids(base))
    want = {"Australia": 3, "Israel": 2, "Kazakhstan": 2, "Mexico": 6, "New Zealand": 7}
    for nm, code in want.items():
        ok("Country.bin: %s %d" % (nm, code), confed.get(fids.get(nm)) == code)
    real = {"leagues": [{"country": fids[nm], "slot": 182 + i, "region": 40 + i, "rid": 320 + i}
                        for i, nm in enumerate(want)]}
    gr = parse(LB.confgroups_lines(real, base, confed)[0])
    ok("the real tables: Australia AFC, Israel UEFA, Kazakhstan UEFA, Mexico CONCACAF, New Zealand OFC",
       [gr["slots"][182 + i] for i in range(5)] == [3, 0, 0, 2, 5])
    ok("the real tables: the game's slots", gr["slots"][7] == 0 and gr["slots"][13] == 1 and gr["slots"][17] == 2)
    print("base tables: %s" % base)
else:
    print("SKIPPED part 2: no base tables at %s" % base)
LB.FL27 = False
print("test_confgroups: %d checks OK" % N)
print("ok")
