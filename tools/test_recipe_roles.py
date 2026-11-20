"""python tools/test_recipe_roles.py <pesdb>

A recipe's captain and set-piece takers (players[club]["roles"], lbplayers.role_refs and
recipe_roles) and its managers' nationality (league "club_coach_countries",
leaguebuilder.coach_countries, mkcoaches.add_coaches nats). On a copy of the game's tables:
every role the recipe names goes to that player and only to him, the ones it leaves out are
picked as for a club with none, set_roles leaves the club alone afterwards, a player the club
does not have is picked instead; a manager gets the nationality the recipe gives, a club without
one keeps its own country's.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbplayers as L
import leaguebuilder as B
import mkcoaches as C
import pesdb

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1


base = sys.argv[1]

# role_refs: the recipe's keys to player ids (pure)
changes = {"Liga X/0": {"roles": {"captain": "4", "penalties": "+0", "bogus": "1", "short free kicks": "29"}},
           "72318": {"roles": {"captain": "180590"}},
           "Liga X/9": {"roles": {"captain": "1"}},
           "Liga X/1": {"edits": {"0": {"name": "A B"}}}}
got, bad = L.role_refs(changes, {"Liga X/0": 80000, "Liga X/1": 80001}, {"Liga X/0": {"4": 111, "+0": 222}})
ok("places and added players resolve", got.get(80000) == {"captain": 111, "penalties": 222})
ok("a club of the game names his players by id", got.get(72318) == {"captain": 180590})
ok("a club with no roles is not in it", 80001 not in got and len(got) == 2)
ok("an unknown role, a missing player and an unknown club are problems",
   len(bad) == 3 and any("bogus" in b for b in bad) and any("no player 29" in b for b in bad)
   and any("Liga X/9" in b for b in bad))
ok("new_club_keys skips the game's clubs",
   B.new_club_keys({"leagues": [{"name": "Liga X", "teams": [80000, 101, 80002], "game_clubs": {"1": {"id": 101}}}]})
   == {"Liga X/0": 80000, "Liga X/2": 80002})

tmp = tempfile.mkdtemp(prefix="rroles-")
try:
    for n in ("Player.bin", "PlayerAssignment.bin"):
        shutil.copy(os.path.join(base, n), tmp)
    sq = L.Squads(tmp)
    clubs = [t for t, v in sorted(sq.by_club.items()) if len(v) >= 20 and all(p in sq.index for _o, p, _s, _x in v)][:3]
    t1, t2, t3 = clubs
    by_order = {t: {order: pid for order, pid, _s, _o in sq.by_club[t]} for t in clubs}
    cap, pen = by_order[t1][15], by_order[t1][0]          # a substitute captain, the keeper on penalties
    stranger = by_order[t3][5]
    before = L.Squads(tmp)
    done = L.recipe_roles(tmp, {t1: {"captain": cap, "penalties": pen}, t2: {"captain": stranger}},
                          log=lambda *x: None)
    after = L.Squads(tmp)
    for t in (t1, t2):
        count = [0] * len(L.ROLES)
        for *_x, o in after.by_club[t]:
            f = L.u32(after.assigns, o + 12) >> L.ROLE_SHIFT
            for k in range(len(L.ROLES)):
                count[k] += f >> k & 1
        ok("club %d: one player for each role" % t, count == [1] * len(L.ROLES))
        ok("club %d: orders and shirts unchanged" % t,
           [x[:3] for x in after.by_club[t]] == [x[:3] for x in before.by_club[t]])
        ok("club %d: no bits but the roles moved" % t,
           [L.u32(after.assigns, o + 12) & ((1 << L.ROLE_SHIFT) - 1) for *_x, o in after.by_club[t]]
           == [L.u32(before.assigns, o + 12) & ((1 << L.ROLE_SHIFT) - 1) for *_x, o in before.by_club[t]])

    def holder(sqd, t, role):
        k = L.ROLES.index(role)
        return [p for _o, p, _s, o in sqd.by_club[t] if L.u32(sqd.assigns, o + 12) >> (L.ROLE_SHIFT + k) & 1]

    ok("the recipe's captain", holder(after, t1, "captain") == [cap] and done[t1]["captain"] == cap)
    ok("the recipe's penalty taker, a keeper too", holder(after, t1, "penalties") == [pen])
    ok("the rest picked from the eleven", all(by_order[t1] and holder(after, t1, r)[0] in
                                                 [by_order[t1][i] for i in range(11)]
                                                 for r in L.ROLES if r not in ("captain", "penalties")))
    ok("a player of another club is not made captain", holder(after, t2, "captain") != [stranger]
       and holder(after, t2, "captain")[0] in by_order[t2].values())
    ok("the third club untouched", [L.u32(after.assigns, o + 12) for *_x, o in after.by_club[t3]]
       == [L.u32(before.assigns, o + 12) for *_x, o in before.by_club[t3]])
    rest = L.set_roles(tmp, [t1, t2], log=lambda *x: None)
    ok("set_roles leaves the recipe's clubs alone", rest == {} and holder(L.Squads(tmp), t1, "captain") == [cap])
    ok("nothing wanted, nothing written", L.recipe_roles(tmp, {}, log=lambda *x: None) == {})
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# managers' nationality
teams = bytearray(pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read()))
coaches = pesdb.wesys_unpack(open(os.path.join(base, "Coach.bin"), "rb").read())
recs = bytearray()
for n, o in enumerate((0, C.T_REC)):
    r = bytearray(teams[o:o + C.T_REC])
    r[C.T_ID:C.T_ID + 4] = (C.FIRST_NEW_ID + n).to_bytes(4, "little")
    r[C.T_COACH:C.T_COACH + 4] = (990000 + n).to_bytes(4, "little")
    recs += r
spain = dict((nm.casefold(), fid) for nm, fid in B.country_ids(base)).get("spain")
ok("Spain is a country of the table", isinstance(spain, int))
pl = {"leagues": [{"name": "Liga X", "teams": [C.FIRST_NEW_ID, C.FIRST_NEW_ID + 1, 101, 80003],
                   "game_clubs": {"2": {"id": 101}},
                   "club_coach_countries": ["spain", "", "236", "Nowhere"]}]}
nats, bad = B.coach_countries(pl, base)
ok("names and ids, blanks and the game's clubs left out", nats == {C.FIRST_NEW_ID: spain})
ok("an unknown country is a problem", len(bad) == 1 and "Nowhere" in bad[0])
add, st = C.add_coaches(coaches, bytes(recs), C.FIRST_NEW_ID, names={C.FIRST_NEW_ID: "Ivan Primjer"}, nats=nats)
ok("two managers", st["added"] == 2)
ok("the given nationality", C.u32(add, C.C_BITS) & 0x1ff == spain)
ok("the club's country without one", C.u32(add, C.C_REC + C.C_BITS) & 0x1ff == C.club_country(recs[C.T_REC:]))
ok("the name as given", pesdb.cstr(add[C.C_NAME1:C.C_NAME1 + C.C_NAME_LEN]) == "Ivan Primjer")
add0, _st = C.add_coaches(coaches, bytes(recs), C.FIRST_NEW_ID)
ok("without nats as before", C.u32(add0, C.C_BITS) & 0x1ff == C.club_country(recs[:C.T_REC]))

# one world built in a temporary game folder (never the game's own): the recipe's roles and the
# managers' nationality land in the built tables
WORLD = "_FL26RecipeRoles"
game = tempfile.mkdtemp(prefix="fl26-rroles-")
try:
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(game, "SiderAddons", d))
    with open(os.path.join(game, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]" + chr(10))
    recipe = {"world": WORLD,
              "players": {"Roles Albania/0": {"roles": {"captain": "7", "left corners": "3"}},
                          "Roles Albania/1": {"edits": {"0": {"name": "Ivan Primjer"}},
                                              "roles": {"captain": "12", "nothing": "1"}}},
              "leagues": [{"name": "Roles Albania", "country": "Albania", "clubs": 10, "legs": 2,
                           "club_coaches": ["Ivan Trener", "", "Marko Trener"],
                           "club_coach_countries": ["Spain", "236", "", "Nowhere"]}]}
    said = []
    pl = B.plan(recipe, base)
    B.build(pl, base, game, False, log=said.append)
    said = chr(10).join(str(x) for x in said)
    db = os.path.join(game, "SiderAddons", "livecpk", WORLD, "common", "etc", "pesdb")
    ids = B.last_build_ids(game, WORLD).get("clubs") or {}
    a = pl["leagues"][0]["teams"]
    sq = L.Squads(db)

    def holder(t, role):
        k = L.ROLES.index(role)
        return [p for _o, p, _s, o in sq.by_club[t] if L.u32(sq.assigns, o + 12) >> (L.ROLE_SHIFT + k) & 1]

    ok("build: the ids file keys the new clubs' players by place", ids.get("Roles Albania/0", {}).get("7"))
    ok("build: the recipe's captain", holder(a[0], "captain") == [ids["Roles Albania/0"]["7"]])
    ok("build: the recipe's left corners", holder(a[0], "left corners") == [ids["Roles Albania/0"]["3"]])
    ok("build: a second club's captain", holder(a[1], "captain") == [ids["Roles Albania/1"]["12"]])
    ok("build: every role taken once at the named clubs",
       all(len(holder(t, r)) == 1 for t in a[:2] for r in L.ROLES))
    ok("build: the other clubs get a captain as before", all(len(holder(t, "captain")) == 1 for t in a[2:]))
    ok("build: an unknown role is said", "no role 'nothing'" in said)
    ok("build: an unknown country is said", "no country 'Nowhere'" in said)
    tm = pesdb.wesys_unpack(open(os.path.join(db, "Team.bin"), "rb").read())
    co = pesdb.wesys_unpack(open(os.path.join(db, "Coach.bin"), "rb").read())
    trec = {C.u32(tm, o + C.T_ID): tm[o:o + C.T_REC] for o in range(0, len(tm), C.T_REC)}
    crec = {C.u32(co, o): co[o:o + C.C_REC] for o in range(0, len(co), C.C_REC)}
    coach = lambda t: crec[C.u32(trec[t], C.T_COACH)]
    ok("build: the named manager", pesdb.cstr(coach(a[0])[C.C_NAME1:C.C_NAME1 + C.C_NAME_LEN]) == "Ivan Trener")
    ok("build: his nationality by name", C.u32(coach(a[0]), C.C_BITS) & 0x1ff == spain)
    ok("build: a nationality by id", C.u32(coach(a[1]), C.C_BITS) & 0x1ff == 236)
    ok("build: no nationality, the club's country",
       all(C.u32(coach(t), C.C_BITS) & 0x1ff == C.club_country(trec[t]) for t in a[2:]))
finally:
    shutil.rmtree(game, ignore_errors=True)
print("test_recipe_roles: %d ok" % N)
