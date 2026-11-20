"""python tools/test_id_ledger.py

The id ledger of a shared world (idledger.py, mato 17.11.2026: "GigaPack updates must not break
existing careers"; then "every pack must be updatable this way, not only ours"). Offline, no game
and no tables:

  - a club renamed where it stands keeps its id, and the ledger says the careers go on;
  - a club, a player, a league or a cup that is gone stops it, unless the recipe's id_retire
    lists it (with a reason); a retired id given to somebody again stops it too;
  - a league added: the others keep their competition and regulation ids; a league whose
    competition id changed stops it; a renamed league's cup that kept its ids is the same cup;
  - a ledger keeps the retired ids from version to version (never reused), counts its versions,
    and forgets a retirement when the id is back;
  - lbplayers: a squad place the last Build left a placeholder (no name, no NewLife id) that the
    recipe names now keeps the place's id (the GigaPack's 91 "FL P" places, AFA Senior Male
    League/5 place 12 = 188745 "Akeem Baird"); a player renamed where he stands with the same birth
    date keeps his; a player who came from another club to a placeholder's place keeps his own;
  - find(): the recipe's id_ledger, this PC's copy of the version shared last (the later one wins),
    and the ledger a world from a zip brought; plan_warnings() for Check the plan;
  - LedgerProblems goes through a process boundary (pickle) as itself.
"""
import copy, json, os, pickle, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import idledger as D

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def league(name, rid, cid, teams, names, region=None, game_clubs=None):
    q = {"name": name, "rid": rid, "cid": cid, "region": region, "teams": list(teams), "club_names": list(names)}
    if game_clubs:
        q["game_clubs"] = game_clubs
    return q


def world_v1():
    plan = {"world": "_FL26LedgerUnit", "game": "fl26", "retired_tids": [],
            "cup_ids": {"cup:Alba": {"cid": 200, "reg": 210}, "super:Alba": {"cid": 201, "reg": 211},
                        "cup:Andor": {"cid": 202, "reg": 212}},
            "leagues": [league("Alba", 150, 140, [3000, 3001, 3002, 101], ["A0", "A1", "A2", "Game FC"],
                               region=1100, game_clubs={"3": {"id": 101}}),
                        league("Andor", 151, 141, [3003, 3004], ["D0", "D1"], region=1101)],
            "others": [], "away_leagues": []}
    pids = {"world": "_FL26LedgerUnit",
            "clubs": {"Alba/0": {"0": 50001, "1": 50002}, "Alba/1": {"0": 50003}, "Andor/0": {"0": 50004},
                      "101": {"+0": 50005, "3": 7}},      # a game club: its own player 7 is the game's
            "names": {"Alba/0": {"0": "Ivo", "1": ""}}, "retired": [49999]}
    return plan, pids


def review_cases(plan1, pids1, led1, plan2, pids2, led2):
    """the review of 17.11.2026 (probes 1-3 and items 1-10), offline"""
    ids2 = D.of_ledger(led2)
    # item 1: lineage, digest, chain
    ok("review 1: a ledger has a lineage, kept by the next version; a digest; the chain of the versions before",
       len(led1["lineage"]) == 32 and led2["lineage"] == led1["lineage"] and led2["chain"][0]["number"] == 1
       and led2["chain"][0]["digest"] == led1["digest"] and led1["digest"] != led2["digest"])
    other = D.make(plan1, pids1, "_FL26LedgerUnit", "Other 1")
    ok("... another author's first version has a lineage of its own, though its ids are the same",
       other["lineage"] != led1["lineage"] and other["digest"] == led1["digest"])
    v = D.update_verdict(D.of_ledger(led1), led1, D.make(plan2, pids2, "_FL26LedgerUnit", "Other 2", prev=other))
    ok("update_verdict: another lineage is another world, whatever its ids (%s)" % v["why"], not v["ok"] and v["why"] == "other")
    v = D.update_verdict(D.of_ledger(led1), led1, led2)
    ok("update_verdict: the next version of the lineage that keeps every id: an Update", v["ok"] and v["match"] == "lineage")
    v = D.update_verdict(D.of_ledger(led2), led2, led1)
    ok("review 9: an older version over a newer one: never an Update (%s)" % v["why"], not v["ok"] and v["why"] == "older")
    v = D.update_verdict(D.of_ledger(led2), led2, led2)
    ok("... the same version: not an Update either (%s)" % v["why"], not v["ok"] and v["why"] == "same")
    # a world installed from a zip without a ledger
    v = D.update_verdict(D.ids_of(plan1, pids1), None, led2)
    ok("no ledger installed, its ids a version in the new one's chain: an Update (%s)" % v["match"],
       v["ok"] and v["match"] == "digest")
    plan1b = copy.deepcopy(plan1)
    plan1b["leagues"][0]["club_names"] = ["K0", "K1", "K2", "Game FC"]
    v = D.update_verdict(D.ids_of(plan1b, pids1), None, led2)
    ok("no ledger installed, other club names under the same ids: another world (%s)" % (v.get("same_names"),),
       not v["ok"] and v["why"] == "other")
    pids1c = copy.deepcopy(pids1)
    pids1c["clubs"]["Alba/1"]["1"] = 50099
    v = D.update_verdict(D.ids_of(plan1, pids1c), None, D.make(plan1, pids1, "_FL26LedgerUnit", "1b", prev=led1))
    ok("no ledger installed, not in the chain, its clubs' and leagues' names the same: told by the names, and its "
       "player who is gone breaks it (%s)" % v["why"], v["match"] == "names" and v["why"] == "broken")
    # item 2: a league replaced by another: its ids are spent, never handed out again
    plan3 = copy.deepcopy(plan2)
    plan3["leagues"][1] = league("Kosovo", 151, 141, [3020, 3021], ["K0", "K1"], region=1103)
    plan3["cup_ids"].pop("cup:Andor")
    plan3["cup_ids"]["cup:Kosovo"] = {"cid": 202, "reg": 212}
    p3 = D.compare(ids2, D.ids_of(plan3, pids2))
    ok("review 2: another league on the old one's regulation and competition id: not the same league (%s)"
       % D.summary(p3), any(k == 151 and "Kosovo" in why for k, _w, why in p3.get("leagues", []))
       and D.retire_entries(p3, "x").get("leagues") is None)
    ok("... and its cup on the old cup's ids is reported as an id given again",
       any("cup:Kosovo" in k for k, _w, _y in p3.get("reused", [])))
    r = D.retire_of({"leagues": {"151": "x"}, "cups": {"cup:Andor": "x"}, "clubs": {"3003": "x", "3004": "x"}})
    p3b = D.compare(ids2, D.ids_of(plan3, pids2), r)
    ok("... retired, the old league's ids are still nobody else's: 'reused' (%s)" % D.summary(p3b),
       p3b.get("reused") and not p3b.get("leagues"))
    led_sp = D.make(plan3, pids2, "_FL26LedgerUnit", "3", prev=led2, retire=r)
    ok("spent: every regulation and competition id a version had, versions after it too",
       {150, 151, 152, 210, 211, 212, 213} <= set(led_sp["spent"]["rids"])
       and {140, 141, 142, 200, 201, 202, 203} <= set(led_sp["spent"]["cids"]))
    ok("pinned_recipe hands them to plan() (_id_spent)", D.pinned_recipe({}, led_sp)[D.SPENT_KEY]["rids"]
       == led_sp["spent"]["rids"])
    plan4 = copy.deepcopy(plan2)
    plan4["leagues"][1] = league("Kosovo", 160, 170, [3020, 3021], ["K0", "K1"], region=1103)
    plan4["cup_ids"].pop("cup:Andor")
    plan4["cup_ids"]["cup:Kosovo"] = {"cid": 204, "reg": 214}
    p4 = D.compare(ids2, D.ids_of(plan4, pids2), r)
    ok("a league replaced, the old one retired, the new one on fresh ids: nothing to say (%s)" % D.summary(p4), p4 == {})
    plan5 = copy.deepcopy(plan2)
    plan5["leagues"][0]["region"] = 1199
    ok("the same league under its regulation id in another country: reported",
       "region 1100 -> 1199" in str(D.compare(ids2, D.ids_of(plan5, pids2))))
    # a renamed league (built_as) is the same league
    plan6 = copy.deepcopy(plan2)
    plan6["leagues"][1]["name"] = "Andorra Primera"
    plan6["leagues"][1]["built_as"] = ["Andor"]
    plan6["cup_ids"]["cup:Andorra Primera"] = plan6["cup_ids"].pop("cup:Andor")
    ok("a league renamed in Mod Studio (built_as): the same league, its cup too",
       D.compare(ids2, D.ids_of(plan6, pids2)) == {})
    # item 5: only "gone" can be retired, every kind
    plan7 = copy.deepcopy(plan2)
    plan7["cup_ids"]["cup:Alba"] = {"cid": 299, "reg": 210}
    p7 = D.compare(ids2, D.ids_of(plan7, pids2))
    ok("review 5: a cup whose competition id changed cannot be retired", p7.get("cups") and D.retire_entries(p7, "x") == {})
    # item 8: structure
    plan8 = copy.deepcopy(plan2)
    plan8["leagues"][1]["legs"] = 4
    plan8["leagues"][1]["relegate"] = 2
    led2s = copy.deepcopy(led2)
    led2s["plan"]["leagues"][1].update(legs=2, relegate=1)
    sc = D.structure_changes(D.of_ledger(led2s), D.ids_of(plan8, pids2))
    ok("review 8: a league played another way is listed with what changed (%s)" % sc,
       sc == [(151, "Andor", ["legs", "relegate"])])
    ok("... promo (a play-off) is kept in the slim plan", "promo" in D._DICT_KEYS)
    # item 10: id_retire of an id the ledger never had
    un = D.unknown_retire({"players": {"999999": "typo", "50001": "real"}, "clubs": {"1": "x"}}, ids2, led2["retire"])
    ok("review 10: id_retire entries the ledger never had are told apart (%s)" % un,
       un == {"players": ["999999"], "clubs": ["1"]})
    # item 3: a club still there that lost its squad
    gone = {"players": [(50001 + k, "Alba/0", "gone") for k in range(2)]}
    ok("mass_losses: too few players to say", D.mass_losses(gone, led2, ids2) == [])
    led_m = copy.deepcopy(led2)
    led_m["players"]["clubs"]["Alba/0"] = {str(k): 60000 + k for k in range(10)}
    gone = {"players": [(60000 + k, "Alba/0", "gone") for k in range(8)]}
    ok("mass_losses: 8 of 10 players of a club still there", D.mass_losses(gone, led_m, D.of_ledger(led_m))
       == [(3000, "A0", 8, 10)])

    # lbplayers: _named_places only for a club whose team id is the same; weak dates; respelling
    import collections
    import lbplayers as L
    W = L._who
    lo = {("C/0", "0"): W("", "", ""), ("C/0", "1"): W("Ivan Horvat", "", "2000-01-01"),
          ("C/0", "2"): W("Jon Smith", "", ""), ("C/1", "0"): W("", "", "")}
    ln = {("C/0", "0"): W("Named Now", "", ""), ("C/0", "1"): W("Marko Maric", "", "2000-01-01"),
          ("C/0", "2"): W("John Smith", "", ""), ("C/1", "0"): W("Somebody", "", "")}
    got = L._named_places(dict(lo), dict(ln), collections.Counter(), same={"C/0"})
    ok("review 3: a placeholder named now keeps the place's id only where the club's team id is the one "
       "before (%s)" % got, (("C/0", "0"), ("C/0", "0")) in got and not any(c[0][0] == "C/1" for c in got))
    ok("review 10: the 1st of January says nothing about who he is (another name, a new id)",
       not any(c[0] == ("C/0", "1") for c in got))
    ok("review 10: a respelt name in his place without a birth date keeps his id (Jon -> John Smith)",
       any(c[0] == ("C/0", "2") for c in got))
    weak = L._weak_dates({("C", "a"): W("A", "", "1999-05-05"), ("C", "b"): W("B", "", "1999-05-05")})
    ok("a birth date two players of a club have says nothing either", ("C", "1999-05-05") in weak)

    # leaguebuilder.follow_tids: the players' ids go with their clubs' team ids
    import leaguebuilder as B
    last = {"clubs": {"Liga/0": {"0": 1}, "Liga/1": {"0": 2}, "101": {"+0": 3}}, "names": {"Liga/1": {"0": "Y"}}}
    before = {"Liga/0": 7000, "Liga/1": 7001}
    moved, same = B.follow_tids(last, before, {"Liga/0": 7001})
    ok("follow_tids: the first club taken out -- the second's players under its key now, the first's gone",
       moved["clubs"]["Liga/0"] == {"0": 2} and moved["clubs"]["gone:Liga/0"] == {"0": 1}
       and moved["names"]["Liga/0"] == {"0": "Y"} and "Liga/0" in same and moved["clubs"]["101"] == {"+0": 3})
    moved, same = B.follow_tids(last, before, {"Shqiperia/0": 7000, "Shqiperia/1": 7001})
    ok("follow_tids: a league renamed -- every club's players under the new name",
       moved["clubs"]["Shqiperia/0"] == {"0": 1} and moved["clubs"]["Shqiperia/1"] == {"0": 2}
       and same >= {"Shqiperia/0", "Shqiperia/1"})
    ok("follow_tids: without the plan before, as it was", B.follow_tids(last, {}, {"Liga/0": 7001}) == (last, None))

    # keep_added: the zip's ledger is not "a file you added"
    t = tempfile.mkdtemp(prefix="fl26ka-")
    try:
        old, new = os.path.join(t, "old"), os.path.join(t, "new")
        os.makedirs(old)
        os.makedirs(new)
        for n in (D.LEDGER, "mine.png"):
            with open(os.path.join(old, n), "w") as f:
                f.write("x")
        kept = B.keep_added(old, new, log=lambda *a: None)
        ok("review 10: keep_added leaves the zip's fl26ids-ledger.json out (%s)" % (kept,),
           D.LEDGER not in (kept or []) and not os.path.exists(os.path.join(new, D.LEDGER)))
        # worlds.keep_ledger: a store that cannot be written does not stop Make it editable
        from modstudio import worlds as WL
        D.save(led1, os.path.join(old, D.LEDGER))
        real = D.store_save

        def full(led):
            raise OSError("disk full")
        D.store_save = full
        said = []
        try:
            ok("review 10: keep_ledger with a store it cannot write: no error, said in the log",
               WL.keep_ledger(old, "_FL26LedgerUnit", said.append) is False and any("disk full" in x for x in said))
        finally:
            D.store_save = real
    finally:
        shutil.rmtree(t, ignore_errors=True)


def review2_cases():
    """the second review of 18.11.2026 (scratchpad ledgerreview2: p1_diverge, p2_lineage, p3_store,
    p4_scale, p5_similar; items 1, 2, 4, 5, 6, 8, 9, 10, 11), offline, in an APPDATA of its own"""
    was = os.environ.get("APPDATA")
    tmp = tempfile.mkdtemp(prefix="fl26ledger2-")
    os.environ["APPDATA"] = os.path.join(tmp, "appdata")
    try:
        _review2(tmp)
    finally:
        if was is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = was
        shutil.rmtree(tmp, ignore_errors=True)


def _plan(names, world="W", swap=None):
    lg = {"name": "Liga", "rid": 200, "cid": 300, "region": 1, "teams": [5000 + i for i in range(len(names))],
          "club_names": list(names), "clubs": len(names)}
    if swap:
        lg["game_clubs"] = swap
    return {"world": world, "leagues": [lg], "others": [], "away_leagues": [], "cup_ids": {}}


def _pids(n, per=3):
    return {"clubs": {"Liga/%d" % c: {str(k): 100000 + c * per + k for k in range(per)} for c in range(n)}}


def _raises(fn):
    try:
        fn()
    except Exception as e:                # noqa: BLE001
        return e
    return None


def _review2(tmp):
    import collections
    from types import SimpleNamespace
    import lbplayers as LP
    from modstudio import installer as I
    from modstudio.pages import install as IP
    LIN = "ab" * 16
    # ---- item 1 (p1): two zips of one lineage after v3, a test zip and the real one
    v3 = D.make(_plan(["A", "B", "C"]), _pids(3), "W", "v3", number=3, lineage=LIN)
    t4 = D.make(_plan(["A", "B", "C", "D"]), _pids(4), "W", "v4 test", prev=v3, test=True)
    r4 = D.make(_plan(["A", "B", "C", "E"]), _pids(4), "W", "v4", prev=v3)
    v = D.update_verdict(D.of_ledger(t4), t4, r4)
    ok("review2 1 (p1): test zip v4 -> the real v4 of the same lineage: not an Update, diverged (%s)" % v["why"],
       not v["ok"] and v["why"] == "diverged" and v.get("test"))
    r5 = D.make(_plan(["A", "B", "C", "D", "F"]), _pids(5), "W", "v5", prev=t4)
    v = D.update_verdict(D.of_ledger(t4), t4, r5)
    ok("review2 1: ... a version made from the one installed (its digest in the chain): an Update",
       v["ok"] and v["match"] == "lineage")
    v = D.update_verdict(D.of_ledger(v3), v3, r4)
    ok("review2 1: ... v3 -> v4 (v3 in its chain): an Update, no club renamed (%s)" % v.get("renamed"),
       v["ok"] and v["renamed"] == [])
    r4b = D.make(_plan(["A", "B2", "C", "E"]), _pids(4), "W", "v4b", prev=v3)
    v = D.update_verdict(D.of_ledger(v3), v3, r4b)
    ok("review2 1c: a kept team id whose name changed is listed for Install (%s)" % v["renamed"],
       v["ok"] and v["renamed"] == [(5001, "B", "B2")])
    ok("review2 1c: ... and the Update's text says so", "B → B2" in IP.update_text(v))
    ok("review2 1: ... Install says what diverged means",
       "is not one this version was made from" in IP.no_update_text({"why": "diverged", "to": "v4", "from": "v4 test"}))
    ok("review2 1: a test zip's ledger says test, and is never kept as a version shared",
       t4.get("test") is True and _raises(lambda: D.store_save(t4)) and not D.store_files("W"))

    # ---- item 5: a number is never given twice (issued: test zips and zips not kept count)
    D.store_save(v3)
    D.note_issued(t4)                     # the test zip's export spent 4
    ok("review2 5: after v3 and a test zip numbered 4, the next export is number 5 (%d)" % D.next_number("W", v3),
       D.next_number("W", v3) == 5)
    D.note_issued(dict(t4, number=7))     # a zip not kept (careers broke) spent 7
    ok("review2 5: ... a number spent by a zip not kept counts too (%d)" % D.next_number("W", v3),
       D.next_number("W", v3) == 8)

    # ---- item 4 (p3): the newest file of the lineage cannot be read: Build and export stop, with its path
    v8 = D.make(_plan(["A", "B", "C", "G"]), _pids(4), "W", "v8", number=8, prev=v3)
    p8 = D.store_save(v8)
    with open(p8, "r+b") as f:
        f.truncate(100)
    e = _raises(lambda: D.find({"world": "W", "id_lineage": LIN}, None, None, []))
    ok("review2 4 (p3): a truncated newest version stops find, naming its file (%s)" % (e,),
       e is not None and p8 in str(e) and "newest version" in str(e))
    os.remove(p8)
    # ---- item 11 (p4): only the newest readable version is read
    for n in (4, 5, 6):
        D.store_save(dict(v3, number=n, version="v%d" % n))
    loads = []
    real = D.load
    D.load = lambda path, world=None: loads.append(path) or real(path, world)
    try:
        _p, got = D.find({"world": "W", "id_lineage": LIN}, None, None, [])
    finally:
        D.load = real
    ok("review2 11 (p4): find reads one file of four, the newest (%d read, %s)" % (len(loads), got and got["version"]),
       len(loads) == 1 and got["version"] == "v6")
    ok("review2 2: the world's name in another case finds its ledgers (%s)" % [n for n, _l, _p in D.store_files("w")],
       len(D.store_files("w")) == 4 and D.find({"world": "w", "id_lineage": LIN}, None, None, [])[1]["version"] == "v6")
    # a test ledger in the history (a world from a test zip made editable) is never the base
    D.save(dict(v3, number=9, version="t9", test=True), D.store_file(dict(v3, number=9)))
    notes = []
    _p, got = D.find({"world": "W", "id_lineage": LIN}, None, None, notes)
    ok("review2 1: find passes a test zip's ledger by (%s)" % notes,
       got["version"] == "v6" and any("is a test zip" in t for t in notes))
    os.remove(D.store_file(dict(v3, number=9)))

    # ---- item 2 (p2): a recipe with id_lineage and no ledger of it: stop, say where to put it
    e = _raises(lambda: D.find({"world": "Z", "id_lineage": "cd" * 16, "leagues": []}, None, None, []))
    ok("review2 2 (p2): id_lineage without a ledger of it on this PC: find stops and says where (%s)" % (e,),
       e is not None and "has no id ledger of it" in str(e) and D.store_dir() in str(e) and "take id_lineage out" in str(e))
    # ---- item 9: the between zone asks; "A different world" (id_not_lineages) leaves it out
    half = D.make({"world": "H", "leagues": [{"name": n, "rid": 300 + i, "teams": [6000 + i], "club_names": ["h%d" % i]}
                                             for i, n in enumerate("abcd")], "others": [], "away_leagues": [],
                   "cup_ids": {}}, {}, "H", "H1")
    D.store_save(half)
    rec = {"world": "H", "leagues": [{"name": "a", "club_names": ["h0"]}, {"name": "b", "club_names": ["h1"]},
                                     {"name": "x", "club_names": ["x0"]}, {"name": "y", "club_names": ["x1"]}]}
    e = _raises(lambda: D.find(rec, None, None, []))
    ok("review2 9: half the leagues: LedgerAsk with the lineage and version (%s)" % (e,),
       isinstance(e, D.LedgerAsk) and e.lineage == half["lineage"] and e.version == "H1"
       and pickle.loads(pickle.dumps(e)).lineage == half["lineage"])
    notes = []
    _p, got = D.find(dict(rec, id_not_lineages=[half["lineage"]]), None, None, notes)
    ok("review2 9: ... \"A different world\": left out, the Build starts its own (%s)" % notes, got is None)
    _p, got = D.find(dict(rec, id_lineage=half["lineage"]), None, None, [])
    ok("review2 9: ... \"It is that world\": pinned to it", got is not None and got["version"] == "H1")
    root = os.path.join(tmp, "livecpk", "H")
    os.makedirs(root)
    with open(os.path.join(root, D.PLAN), "w", encoding="utf-8") as f:
        json.dump({"world": "H", "leagues": [], "settings": {}}, f)
    ok("review2 9: stamp_plan writes the lineage into a built world's plan, recipe_of_world reads it",
       D.stamp_plan(root, {D.LINEAGE_KEY: half["lineage"]}) and not D.stamp_plan(root, {D.LINEAGE_KEY: half["lineage"]})
       and D.recipe_of_world(os.path.join(tmp, "livecpk"), "H")[D.LINEAGE_KEY] == half["lineage"])

    # ---- item 10 (p3): a ledger that is JSON but not whole
    for bad, what in ((dict(v3, chain=["x"]), "chain"), (dict(v3, retire={"clubs": ["x"]}), "retire"),
                      (dict(v3, spent=[1]), "spent"), (dict(v3, lineage=5), "lineage")):
        p = os.path.join(tmp, "bad.json")
        D.save(bad, p)
        e = _raises(lambda: D.load(p))
        ok("review2 10: a ledger whose %s is not what it should be: LedgerError, not a crash (%s)" % (what, e),
           isinstance(e, D.LedgerError))
    g = os.path.join(tmp, "game")
    os.makedirs(os.path.join(g, "W"))
    D.save(v3, os.path.join(g, "W", D.LEDGER))
    newz = os.path.join(tmp, "newzip")
    os.makedirs(newz)
    with open(os.path.join(newz, D.LEDGER), "w", encoding="utf-8") as f:
        json.dump(dict(r4, chain=["x"]), f)
    ok("review2 10: update_check of a zip with such a ledger: None (Install as before), no exception",
       I.update_check(SimpleNamespace(livecpk_dir=g), "W", newz) is None)

    # ---- item 6 (p3): a world of before the ledger, 3 of 20 clubs renamed, every id kept
    names = ["Club %d" % i for i in range(20)]
    new = list(names)
    new[0:3] = ["FK Club 0", "NK Club 1", "Club 2 FC"]
    old = D.ids_of(_plan(names), {})
    v = D.update_verdict(old, None, D.make(_plan(new), {}, "W", "first", number=1))
    ok("review2 6 (p3): 3 of 20 clubs renamed, every id kept: an Update, the renames listed (%s %s)"
       % (v["why"], v.get("same_names")), v["ok"] and v["match"] == "ids" and len(v["renamed"]) == 3)
    v = D.update_verdict(old, None, D.make(_plan(new[:19]), {}, "W", "first", number=1))
    ok("review2 6: ... and with a club gone too: not an Update (%s)" % v["why"], not v["ok"] and v["why"] == "other")
    ok("review2 6: Install's \"other\" text does not claim it is another world",
       "or one its author made again" in IP.no_update_text({"why": "other"}))

    # ---- item 3: a swap club (a new club taking a game club's places) is the world's own club
    sw = D.ids_of(_plan(["A"], swap={"1": {"id": 101, "swap": {"name": "Swap FC"}, "swap_id": 71581}}), {})
    ok("review2 3: ids_of has the swap club under its id (%s)" % (sw["clubs"].get(71581),),
       sw["clubs"].get(71581) == ("Swap FC", "in place of 101"))

    # ---- item 8 (p5): different players are not one by a share of like letters
    for a, b in (("Marko Marić", "Mario Marić"), ("Luka Ivanović", "Luka Jovanović"),
                 ("Ivan Petrović", "Ivan Petković"), ("Daniel Silva", "Danilo Silva")):
        ok("review2 8 (p5): %s and %s are two players" % (a, b), not LP._respelling(LP._letters(a), LP._letters(b)))
    for a, b in (("Luka Modrić", "Luka Modric"), ("Mohamed Salah", "Mohammed Salah"), ("Jon Smith", "John Smith"),
                 ("Ivan Perisic", "Ivan Peirsic")):
        ok("review2 8: %s and %s: one name spelt two ways" % (a, b), LP._respelling(LP._letters(a), LP._letters(b)))
    merged = []
    lo = {("Liga/0", "7"): LP._who("Jon Smith", "", ""), ("Liga/0", "8"): LP._who("Marko Marić", "", "")}
    ln = {("Liga/0", "7"): LP._who("John Smith", "", ""), ("Liga/0", "8"): LP._who("Mario Marić", "", "")}
    got = LP._named_places(lo, ln, collections.Counter(), None, set(), merged)
    ok("review2 8: _named_places keeps Jon -> John, not Marko -> Mario, and says which it merged (%s)" % merged,
       [c[0] for c in got] == [("Liga/0", "7")] and merged == [("Jon Smith", "John Smith")])

    # ---- item 1: Make it editable of a test zip's world: its ledger is not kept, and making it editable goes on
    from modstudio import worlds as WS
    root = os.path.join(tmp, "livecpk-test-zip")
    os.makedirs(root)
    tz = D.make(_plan(["A", "B"], world="WT"), _pids(2), "WT", "WT test", number=1, lineage="cd" * 16, test=True)
    D.save(tz, os.path.join(root, D.LEDGER))
    said = []
    e = _raises(lambda: said.append(WS.keep_ledger(root, "WT", said.append)))
    ok("review2 1: Make it editable of a test zip's world does not stop, and keeps no ledger (%s)" % (e or said),
       e is None and said[-1] is False and any("is not kept" in str(s) for s in said[:-1])
       and not D.store_files("WT"))


def review3_cases():
    """the third review of 18.11.2026 (scratchpad ledgerreview3: p3_store_name, p4_respell, p5_b4sim;
    items 1, 2, 3, 4, 6 and the Update's "from"), offline, in an APPDATA of its own"""
    was = os.environ.get("APPDATA")
    was_store = os.environ.pop("FL26_LEDGER_STORE", None)
    tmp = tempfile.mkdtemp(prefix="fl26ledger3-")
    os.environ["APPDATA"] = os.path.join(tmp, "appdata")
    try:
        _review3(tmp)
    finally:
        if was is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = was
        if was_store is not None:
            os.environ["FL26_LEDGER_STORE"] = was_store
        shutil.rmtree(tmp, ignore_errors=True)


def _review3(tmp):
    import collections
    import leaguebuilder as B
    import lbplayers as LP
    try:
        import release
    except ImportError:            # the public tree has no release.py
        release = None
    from modstudio.pages import install as IP
    LIN = "ef" * 16
    v3 = D.make(_plan(["A", "B", "C"]), _pids(3), "W", "v3", number=3, lineage=LIN)

    # ---- item 2 (p3 b): a ledger copied into the folder under a name of its own counts
    os.makedirs(D.store_dir(), exist_ok=True)
    own = os.path.join(D.store_dir(), "W-beta3 copy.fl26ids")
    D.save(v3, own)
    other = D.make(_plan(["X", "Y"], world="W2"), _pids(2), "W2", "w2", number=7, lineage="12" * 16)
    D.save(other, os.path.join(D.store_dir(), "something.fl26ids"))
    with open(os.path.join(D.store_dir(), "notes.fl26ids"), "w", encoding="utf-8") as f:
        f.write("not a ledger")
    got = D.store_files("W")
    ok("review3 2 (p3 b): a ledger under its own name is in the history by what it says (%s)" % got,
       got == [(3, LIN[:12], own)])
    p, led = D.find({"world": "W", D.LINEAGE_KEY: LIN, "leagues": []})
    ok("review3 2: ... and Build and export of the recipe that names its lineage pin to it (%s)" % p,
       p == own and led["version"] == "v3")
    # a ledger written by hand (indented, its keys in another order) is read whole
    pretty = os.path.join(D.store_dir(), "hand.fl26ids")
    with open(pretty, "w", encoding="utf-8") as f:
        json.dump(dict([("plan", v3["plan"]), ("players", v3["players"])] +
                       [(k, v) for k, v in v3.items() if k not in ("plan", "players")]), f, indent=2)
    ok("review3 2: ... also one whose start does not say its world (%s)" % D._head(pretty),
       (D._head(pretty) or {}).get("world") == "W" and pretty in [x[2] for x in D.store_files("W")])
    os.remove(pretty)
    ok("review3 2: next_number counts the file under its own name", D.next_number("W", dict(v3, number=2)) == 4)
    os.remove(own)

    # ---- item 3 (p5): a world installed from a zip without a ledger, a newer zip with the same ids
    old = D.of_ledger(v3)
    fix = D.make(_plan(["A", "B", "C"]), _pids(3), "W", "v3.1", prev=v3)
    v = D.update_verdict(old, None, fix)
    ok("review3 3 (p5): same ids, a later number (a fix of kits or crests): an Update, from %s (%s)"
       % (v.get("from"), v["why"]), v["ok"] and v["match"] == "digest" and v["from"] == "v3")
    first = D.make(_plan(["A", "B", "C"]), _pids(3), "W", "first", number=1)
    v = D.update_verdict(old, None, first)
    ok("review3 3: ... the same ids as a first version: the same world (%s)" % v["why"],
       not v["ok"] and v["why"] == "same")
    v4 = D.make(_plan(["A", "B", "C", "D"]), _pids(4), "W", "v4", prev=v3)
    v = D.update_verdict(old, None, v4)
    ok("review3 cosmetic: an Update over a world without a ledger names its version (%s)" % v.get("from"),
       v["ok"] and v["from"] == "v3")
    text = IP.update_text(v)
    ok("review3 cosmetic: ... and Install says it (%r)" % text[:60],
       "v3 → v4" in text and "the version you have →" not in text)

    # ---- item 4 (p4): a respelling with the same weak date on both sides is the same player
    def kept(a, b, da, db, extra=()):
        lo = {("C", "3"): LP._who(a, "", da)}
        ln = {("C", "3"): LP._who(b, "", db)}
        for i, (n, d) in enumerate(extra):
            lo[("C", "x%d" % i)] = LP._who(n, "", d)
        return bool(LP._named_places(lo, ln, collections.Counter(), None, None, []))
    ok("review3 4 (p4): Mohamed Salah -> Mohammed Salah, 1 January on both: the same player",
       kept("Mohamed Salah", "Mohammed Salah", "1992-01-01", "1992-01-01"))
    ok("review3 4: ... a date two of the club share, on both: the same player",
       kept("Mohamed Salah", "Mohammed Salah", "1990-05-05", "1990-05-05", [("Other", "1990-05-05")]))
    ok("review3 4: ... another name with a 1 January date is still another player",
       not kept("Luka Modric", "Ivan Rakitic", "1990-01-01", "1990-01-01"))
    ok("review3 4: ... and a respelling with two different dates too",
       not kept("Mohamed Salah", "Mohammed Salah", "1992-06-15", "1993-06-15"))

    # ---- item 1: the export without the recipe finds the ledger the recipe named
    ok("review3 1: id_ledger is a recipe key the built plan keeps", "id_ledger" in B.RECIPE_SETTINGS)
    elsewhere = os.path.join(tmp, "shared", "W-v3.fl26ids")
    D.save(v3, elsewhere)
    rpath = os.path.join(tmp, "shared", "_FL26W.json")
    r = D.absolute_ledger({"world": "W", D.LEDGER_KEY: "W-v3.fl26ids"}, rpath)
    ok("review3 1: absolute_ledger makes the recipe's id_ledger the path find takes (%s)" % r[D.LEDGER_KEY],
       r[D.LEDGER_KEY] == os.path.abspath(elsewhere))
    lc = os.path.join(tmp, "livecpk")
    os.makedirs(os.path.join(lc, "W"))
    with open(os.path.join(lc, "W", D.PLAN), "w", encoding="utf-8") as f:
        json.dump(dict(_plan(["A", "B", "C"]), settings={D.LINEAGE_KEY: LIN, D.LEDGER_KEY: os.path.abspath(elsewhere)}), f)
    like = D.recipe_of_world(lc, "W")
    p, led = D.find(like, None, lc, [])
    ok("review3 1: an export by the world's plan finds the ledger of its id_ledger (%s)" % p,
       p == os.path.abspath(elsewhere) and led["number"] == 3)
    with open(os.path.join(lc, "W", D.PLAN), "w", encoding="utf-8") as f:
        json.dump(dict(_plan(["A", "B", "C"]), settings={D.LINEAGE_KEY: LIN, D.LEDGER_KEY: "source/d001/W-v3.fl26ids"}), f)
    ok("review3 1: ... a path the export cut (a zip of another PC) is not a stop",
       D.LEDGER_KEY not in D.recipe_of_world(lc, "W"))
    if release is None:
        print("skip  review3 1: release.py's export -- release.py not in this tree")
    else:
        cmd = " ".join(release.DEFAULT_CMDS["export"])
        ok("review3 1: release.py's export passes the recipe and its path", "recipe=" in cmd and "recipe_path=" in cmd)

    # ---- item 6: the tests keep the ledgers they make out of this PC's history
    os.environ["FL26_LEDGER_STORE"] = os.path.join(tmp, "store6")
    ok("review3 6: FL26_LEDGER_STORE moves the history", D.store_dir() == os.path.join(tmp, "store6"))
    os.environ.pop("FL26_LEDGER_STORE")
    here = os.path.dirname(os.path.abspath(__file__))
    lack = [f for f in ("test_continental_emblems.py", "test_export_no_local_paths.py", "test_install_keeps_yours.py",
                        "test_install_long_paths.py", "test_install_versions.py", "test_ready_edit.py",
                        "test_world_game.py", "test_world_share.py", "test_write_access.py")
            if "FL26_LEDGER_STORE" not in open(os.path.join(here, f), encoding="utf-8").read()]
    ok("review3 6: every test that exports or makes a world editable without an APPDATA of its own "
       "keeps its ledgers apart (%s)" % (lack or "all"), not lack)


def main():
    plan1, pids1 = world_v1()
    led1 = D.make(plan1, pids1, "_FL26LedgerUnit", "1")
    ids1 = D.ids_of(led1["plan"], led1["players"])
    ok("ids_of: the world's own clubs, not a game club in its league",
       set(ids1["clubs"]) == {3000, 3001, 3002, 3003, 3004})
    ok("ids_of: the new clubs' players and the ones added to a game club, not the game's own",
       set(ids1["players"]) == {50001, 50002, 50003, 50004, 50005})
    ok("ids_of: leagues by regulation id with their competition id; cups by key",
       ids1["leagues"][150]["cid"] == 140 and set(ids1["cups"]) == {"cup:Alba", "super:Alba", "cup:Andor"})
    ok("make: version 1, number 1, nothing retired, no path of this PC in it",
       led1["version"] == "1" and led1["number"] == 1 and not any(led1["retire"].values())
       and "world" not in led1["players"])
    slim = json.dumps(led1["plan"])
    ok("slim_plan keeps what Build pins by (names, teams, rid, cid, region, game_clubs, cup_ids)",
       all(k in slim for k in ('"teams"', '"club_names"', '"rid"', '"cid"', '"region"', '"game_clubs"', '"cup_ids"')))

    # ---- v2: a club renamed where it stands, a league added (the others keep their ids)
    plan2 = copy.deepcopy(plan1)
    plan2["leagues"][0]["club_names"][1] = "A1 United"
    plan2["leagues"].append(league("Bosna", 152, 142, [3005, 3006], ["B0", "B1"], region=1102))
    plan2["cup_ids"]["cup:Bosna"] = {"cid": 203, "reg": 213}
    pids2 = copy.deepcopy(pids1)
    pids2["clubs"]["Bosna/0"] = {"0": 50006}
    led2 = D.make(plan2, pids2, "_FL26LedgerUnit", "2", prev=led1)
    ids2 = D.ids_of(led2["plan"], led2["players"])
    ok("a renamed club and an added league: careers of 1 go on", D.compare(ids1, ids2) == {})
    ok("the renamed club is listed as renamed, same id", D.renamed(ids1, ids2) == [(3001, "A1", "A1 United")])
    ok("number 2, after version 1", led2["number"] == 2 and led2["after"]["version"] == "1")
    ok("an added league: the others' competition and regulation ids unchanged",
       all(ids2["leagues"][r]["cid"] == ids1["leagues"][r]["cid"] for r in ids1["leagues"]))

    # ---- v3: a club, a player, a league and its cup gone
    plan3 = copy.deepcopy(plan2)
    plan3["leagues"][0]["teams"][2] = 3007                # A2 replaced by a new club: 3002 gone
    plan3["leagues"][0]["club_names"][2] = "A2 New"
    plan3["leagues"] = [q for q in plan3["leagues"] if q["name"] != "Andor"]
    del plan3["cup_ids"]["cup:Andor"]
    pids3 = copy.deepcopy(pids2)
    del pids3["clubs"]["Alba/0"]["1"]                     # player 50002 gone
    del pids3["clubs"]["Andor/0"]                         # with the league
    ids3 = D.ids_of(plan3, pids3)
    probs = D.compare(ids2, ids3)
    ok("gone without a retirement: club 3002 and Andor's two, player 50002 and 50004, league 151, its cup",
       {k: sorted(x[0] for x in v) for k, v in probs.items()}
       == {"clubs": [3002, 3003, 3004], "players": [50002, 50004], "leagues": [151], "cups": ["cup:Andor"]})
    ok("problem_lines names each, summary counts them",
       any("club 3002: A2 (Alba) -- gone" == l for l in D.problem_lines(probs))
       and D.summary(probs) == "1 league, 1 cup, 3 clubs, 2 players")
    entries = D.retire_entries(probs, "taken out on purpose")
    recipe = {"world": "_FL26LedgerUnit"}
    ok("retire_entries + add_retire: all 7 into the recipe's id_retire",
       D.add_retire(recipe, entries) == 7 and recipe["id_retire"]["players"]["50002"] == "taken out on purpose")
    ok("... and a second time adds nothing", D.add_retire(recipe, entries) == 0)
    ok("retired in the recipe: careers of 2 go on in 3", D.compare(ids2, ids3, D.retire_of(recipe["id_retire"])) == {})
    led3 = D.make(plan3, pids3, "_FL26LedgerUnit", "3", prev=led2, retire=recipe["id_retire"])
    ok("the ledger of 3 keeps the retirements", led3["retire"]["players"] == {"50002": "taken out on purpose",
                                                                              "50004": "taken out on purpose"})
    # ---- v4: a retired id given to somebody again
    plan4, pids4 = copy.deepcopy(plan3), copy.deepcopy(pids3)
    pids4["clubs"]["Alba/1"]["1"] = 50002
    ids3l = D.ids_of(led3["plan"], led3["players"])
    p4 = D.compare(ids3l, D.ids_of(plan4, pids4), D.retire_of(led3["retire"]))
    ok("a retired player id given to somebody again: stopped (never reused)",
       list(p4) == ["reused"] and p4["reused"][0][0] == "player 50002")
    led4 = D.make(plan3, pids3, "_FL26LedgerUnit", "4", prev=led3)
    ok("the retirements go on into the next version (cumulative)", led4["retire"]["players"] == led3["retire"]["players"]
       and led4["retire"]["clubs"] == led3["retire"]["clubs"] and led4["number"] == 4)
    back = copy.deepcopy(pids3)
    back["clubs"]["Alba/0"]["1"] = 50002
    led5 = D.make(plan3, back, "_FL26LedgerUnit", "5", prev=led4)
    ok("an id that is back is not retired any more", "50002" not in led5["retire"]["players"]
       and "50004" in led5["retire"]["players"])
    # ---- a league's competition id changed; a renamed league's cup that kept its ids
    plan6 = copy.deepcopy(plan2)
    plan6["leagues"][1]["cid"] = 160
    p6 = D.compare(ids2, D.ids_of(plan6, pids2))
    ok("a league whose competition id changed: stopped", list(p6) == ["leagues"] and "140" not in p6["leagues"][0][2]
       and "141 -> 160" in p6["leagues"][0][2])
    ok("... and that cannot be retired: only an id that is gone can go (review 5)",
       D.retire_entries(p6, "x") == {})
    plan7 = copy.deepcopy(plan2)
    plan7["leagues"][0]["name"] = "Alba Superliga"
    plan7["cup_ids"]["cup:Alba Superliga"] = plan7["cup_ids"].pop("cup:Alba")
    ok("a league under its regulation id with another name it was never built as: reported (review 2)",
       "its regulation id is Alba Superliga's now" in str(D.compare(ids2, D.ids_of(plan7, pids2))))
    plan7["leagues"][0]["built_as"] = ["Alba"]          # what Mod Studio's Edit league... writes
    ok("a league renamed in Mod Studio (built_as) whose cup kept its ids under the new name: careers go on",
       D.compare(ids2, D.ids_of(plan7, pids2)) == {})

    # ---- find, store, load
    tmp = tempfile.mkdtemp(prefix="fl26ledger-")
    old_appdata = os.environ.get("APPDATA")
    try:
        os.environ["APPDATA"] = os.path.join(tmp, "appdata")
        rdir = os.path.join(tmp, "recipes")
        os.makedirs(rdir)
        rpath = os.path.join(rdir, "_FL26LedgerUnit.json")
        ok("no ledger anywhere: (None, None)", D.find({"world": "_FL26LedgerUnit"}, rpath) == (None, None))
        D.save(led1, os.path.join(rdir, "beta1.fl26ids"))
        p, got = D.find({"world": "_FL26LedgerUnit", "id_ledger": "beta1.fl26ids"}, rpath)
        ok("the recipe's id_ledger, next to the recipe", got["version"] == "1" and p.endswith("beta1.fl26ids"))
        try:
            D.find({"world": "_FL26LedgerUnit", "id_ledger": "nowhere.fl26ids"}, rpath)
            ok("a recipe's id_ledger that is not there: an error", False)
        except D.LedgerError as e:
            ok("a recipe's id_ledger that is not there: an error (%s)" % e, "not there" in str(e))
        D.store_save(led2)
        p, got = D.find({"world": "_FL26LedgerUnit", "id_ledger": "beta1.fl26ids"}, rpath)
        ok("this PC's copy of a later version of the same lineage wins over the recipe's older one",
           got["version"] == "2" and p == D.store_file(led2))
        ok("the copy is not .json (no recipe list takes it), one file a version (history)",
           not p.lower().endswith(".json") and os.path.basename(p) == "_FL26LedgerUnit.%s.2.fl26ids" % led2["lineage"][:12]
           and os.path.dirname(p) == os.path.join(os.environ["APPDATA"], "FL26ModStudio", "recipes", "ledgers"))
        D.store_save(led1)
        ok("history: every version shared stays (1 and 2)", [n for n, _l, _p in D.store_files("_FL26LedgerUnit")] == [1, 2])
        for _n, _l, f in D.store_files("_FL26LedgerUnit"):
            os.remove(f)
        live = os.path.join(tmp, "livecpk")
        D.save(led3, os.path.join(live, "_FL26LedgerUnit", D.LEDGER))
        like = {"world": "_FL26LedgerUnit", "leagues": [{"name": "Alba"}, {"name": "Bosna"}]}
        notes = []
        p, got = D.find(like, rpath, live, notes)
        ok("a world from a zip, made editable: the ledger its zip brought, and the log says so (%s)" % notes,
           got["version"] == "3" and any("pinned to the ledger its zip brought" in t for t in notes))
        # review 1: another author's world of the same name pins nothing
        stranger = D.make(plan2, pids2, "_FL26LedgerUnit", "S1")
        D.store_save(stranger)
        notes = []
        try:
            D.find({"world": "_FL26LedgerUnit", "id_lineage": led1["lineage"],
                    "leagues": [{"name": "Alba"}]}, rpath, None, notes)
            err = None
        except D.LedgerError as e:
            err = str(e)
        # review 2 (18.11.): ... and, with none of its own lineage, stops (no new lineage taken silently)
        ok("find: a recipe of one lineage takes no ledger of another, and stops when it has none of its own (%s)"
           % notes, any("another lineage" in t for t in notes) and err and "has no id ledger of it" in err
           and D.store_dir() in err)
        notes = []
        p, got = D.find({"world": "_FL26LedgerUnit", "leagues": [{"name": "Kosovo", "club_names": ["K1"]}]},
                        rpath, None, notes)
        ok("find: a recipe of no lineage takes no ledger whose leagues and clubs are not its own (%s)" % notes,
           got is None and any("another world of the same name" in t for t in notes))
        p, got = D.find({"world": "_FL26LedgerUnit", "leagues": [{"name": "Alba"}, {"name": "Andor"}]}, rpath)
        ok("... and does take one whose leagues are its own", got is not None and got["version"] == "S1")
        for _n, _l, f in D.store_files("_FL26LedgerUnit"):
            os.remove(f)
        try:
            D.load(os.path.join(live, "_FL26LedgerUnit", D.LEDGER), "_FL26Other")
            ok("another world's ledger: refused", False)
        except D.LedgerError:
            ok("another world's ledger: refused", True)
        with open(os.path.join(tmp, "bad.fl26ids"), "w") as f:
            f.write('{"format": "something"}')
        try:
            D.load(os.path.join(tmp, "bad.fl26ids"))
            ok("not a ledger: refused", False)
        except D.LedgerError:
            ok("not a ledger: refused", True)
        # review 10: a ledger without its parts, or of a newer Mod Studio, is refused as one
        for what, bad in (("no players", dict(led1, players=None)), ("number as text", dict(led1, number="1")),
                          ("format_version 99", dict(led1, format_version=99)), ("no plan", {k: v for k, v in led1.items() if k != "plan"})):
            D.save(bad, os.path.join(tmp, "half.fl26ids"))
            try:
                D.load(os.path.join(tmp, "half.fl26ids"))
                ok("a ledger with %s: refused" % what, False)
            except D.LedgerError as e:
                ok("a ledger with %s: refused (%s)" % (what, e), True)
        D.save(dict(led1, format_version=1), os.path.join(tmp, "v1.fl26ids"))
        ok("a ledger of format 1 still reads", D.load(os.path.join(tmp, "v1.fl26ids"))["number"] == 1)
        ok("default_version: the recipe's pack_version, else the next number and the date",
           D.default_version({"pack_version": "GigaPack beta 4"}, led3) == "GigaPack beta 4"
           and D.default_version({}, led3).startswith("4 (") and D.default_version({}, None).startswith("1 ("))
    finally:
        if old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = old_appdata
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- Check the plan: a plan whose club is gone, and the NewLife pins of the ledger
    pl = copy.deepcopy(plan2)
    for q in pl["leagues"]:
        q["prev_teams"], q["prev_names"] = list(q["teams"]), [x.lower() for x in q["club_names"]]
    ok("plan_warnings: a plan that keeps everything says nothing", D.plan_warnings(pl, led2) == {})
    pl["leagues"][0]["club_names"][2] = "Somebody else"
    pl["leagues"][0]["club_names"].append("A2")     # A2 is still in the world, so its place is not its own
    pl["leagues"] = [q for q in pl["leagues"] if q["name"] != "Bosna"]
    w = D.plan_warnings(pl, led2)
    ok("plan_warnings: a league gone and its clubs (%s)" % D.summary(w),
       [x[0] for x in w.get("leagues", [])] == [152] and {3005, 3006} <= {x[0] for x in w.get("clubs", [])})
    nl = {"leagues": [dict(league("N", 153, 143, [3010], ["N0"]), newlife_tid={"7001": 3010})]}
    ok("pinned_recipe: the ledger's NewLife clubs keep their ids (newlife_ids), the recipe untouched",
       D.pinned_recipe({"newlife_ids": {"7002": 3011}}, {"plan": nl})["newlife_ids"] == {"7002": 3011, "7001": 3010})

    # ---- lbplayers: a placeholder place named now keeps its id (the 91 FL P places of the GigaPack)
    import test_keep_ids_people as KP
    named = [("Igrac %02d" % n, {"newlife_id": str(600 + n)}) for n in range(20)]   # places 20..29: placeholders
    _db, a, _l = KP.build(KP.plan(named), retired=set())
    ok("placeholders at places 20..29 have ids and no names", all(str(k) in a["clubs"]["Liga/0"] for k in range(20, 30))
       and not any((a["names"].get("Liga/0") or {}).get(str(k)) for k in range(20, 30)))
    more = named + [("Igrac 20", {})] * 0
    pl2 = KP.plan(named)
    pl2["players"]["Liga/0"]["edits"]["22"] = {"name": "Akeem Baird", "Registered Position": "CF", "Age": "25"}
    _db, b, log = KP.build(pl2, a, retired=set())
    ok("a placeholder place named now keeps the place's id (%s -> %s)" % (a["clubs"]["Liga/0"]["22"],
                                                                          b["clubs"]["Liga/0"]["22"]),
       a["clubs"]["Liga/0"]["22"] == b["clubs"]["Liga/0"]["22"])
    ok("... and nobody else's id moved", all(a["clubs"]["Liga/0"][k] == b["clubs"]["Liga/0"][k]
                                            for k in a["clubs"]["Liga/0"]))
    ok("... and nothing was retired", not (set(a["clubs"]["Liga/0"].values()) & set(b.get("retired") or [])))
    # renamed where he stands, the same birth date: the same one
    born = [("Pero %02d" % n, {"birth_date": "2000-01-%02d" % (n + 1)}) for n in range(20)]
    _db, c, _l = KP.build(KP.plan(born), retired=set())
    ren = copy.deepcopy(born)
    ren[4] = ("Petar Peric", {"birth_date": "2000-01-05"})
    _db, d, _l = KP.build(KP.plan(ren), c, retired=set())
    ok("a player renamed where he stands, his birth date the same: keeps his id",
       c["clubs"]["Liga/0"]["4"] == d["clubs"]["Liga/0"]["4"])
    other = copy.deepcopy(born)
    other[4] = ("Novi Netko", {"birth_date": "1990-03-03"})
    _db, e, _l = KP.build(KP.plan(other), c, retired=set())
    ok("another name and another birth date in that place: a new id, the old one retired",
       c["clubs"]["Liga/0"]["4"] != e["clubs"]["Liga/0"]["4"] and c["clubs"]["Liga/0"]["4"] in e["retired"])

    review_cases(plan1, pids1, led1, plan2, pids2, led2)
    review2_cases()
    review3_cases()

    # ---- LedgerProblems over a process boundary (apart.py pickles what Build raises)
    import leaguebuilder as B
    err = B.ledger_problems({"players": [(50002, "Alba/0", "gone")]}, "GigaPack beta 3", [(3000, "A0", 18, 20)])
    back = pickle.loads(pickle.dumps(err))
    ok("LedgerProblems pickles as itself, with what is gone, the version and the clubs that lost their squad",
       isinstance(back, B.LedgerProblems) and isinstance(back, B.BuildError) and back.version == "GigaPack beta 3"
       and back.gone == err.gone and "player 50002" in str(back) and "id_retire" in str(back)
       and back.mass == [(3000, "A0", 18, 20)] and "A0 (18 of 20)" in str(back))
    # review 10: Build's ledger lines in the window's language (lang/<code>.json "log" rules, i18n.tr)
    from modstudio import i18n
    try:
        for code, words in (("hr", ("igrač 50002", "više ne postoji", "Vrati ih", "A0 (18/20)")),
                            ("es", ("jugador 50002", "ya no está", "Vuelve a ponerlos")),
                            ("fr", ("joueur 50002", "disparu", "Remettez-les")),
                            ("pt", ("jogador 50002", "desapareceu", "Volte a pô-los"))):
            i18n.set_language(code)
            t = i18n.tr(str(back))
            ok("review 10: the Build's ledger problems in %s (%r)" % (code, t[:90]),
               all(w in t for w in words) and "would break" not in t and "-- gone" not in t)
        i18n.set_language("hr")
        t = i18n.tr("ids: x.fl26ids is left out: another lineage of _W, not this recipe's")
        ok("... and find's notes (%r)" % t, "druga loza" in t)
    finally:
        i18n.set_language("en")
    print("%d cases passed" % N)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
