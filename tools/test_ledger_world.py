r"""python tools/test_ledger_world.py <folder with the game's tables>

A shared world updated without breaking careers (idledger.py, mato 17.11.2026: "every pack must be
updatable this way, not only ours"). A small world that is not the GigaPack goes the whole way, as
its author and a player do it:

  author   Build v1 -> Share world as zip (export_world: the zip carries fl26ids-ledger.json, its
           version and "careers": first) -> this PC keeps the ledger (recipes\ledgers\<world>.fl26ids)
           -> edit: a club renamed, a league added, a player taken out -> Build: pinned to v1's
           ledger, it STOPS on the player (LedgerProblems; the world in the game is not touched)
           -> the player retired (what the Build dialog writes into the recipe) -> Build goes
           through: the renamed club, every league, cup and player of v1 keep their ids, the new
           league takes ids nobody had -> export v2 ("careers": continue from v1)
  player   v1 installed, careers in the save folder (a save and fl26swiss-state.bin) -> the v2 zip:
           an Update ("Your careers stay and continue", no "start a new Master League") -> Install:
           the save folder byte for byte as it was, the world v2's
  and      a zip of a world of the same name whose ids are others: Replace and a warning; a zip
           without a ledger (before 17.11.): as before (no Update, no warning); a world installed
           from a zip without a ledger, whose ids the new zip keeps: an Update too.

Offline: temporary game folders (as test_team_ids_stable), APPDATA and FL26_SAVE_ROOT of their own,
QT_QPA_PLATFORM=offscreen; no game is started and no real save folder is looked at.
"""
import json, os, shutil, sys, tempfile, time, zipfile
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
TMP = tempfile.mkdtemp(prefix="fl26-ledgerworld-")
os.environ["APPDATA"] = os.path.join(TMP, "appdata")          # the author's Mod Studio keeps its ledgers here
SAVES = os.path.join(TMP, "KONAMI", "eFootball PES 2021 SEASON UPDATE", "2026")
os.environ["FL26_SAVE_ROOT"] = SAVES

import leaguebuilder as B
import idledger as D
from modstudio import installer as I, saves as SV
from modstudio.siderini import SiderIni
from modstudio.pages import builder as BP
from modstudio.pages import install as PI
try:
    import release                # tools/release.py: not in the public tree
except ImportError:
    release = None
import test_world_share as T

N = 0
WORLD = "_FL26LedgerWorld"
QUIET = lambda *a, **k: None


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def game_folder(name):
    g = os.path.join(TMP, name)
    for d in ("livecpk", "modules", "content"):
        os.makedirs(os.path.join(g, "SiderAddons", d))
    with open(os.path.join(g, "SiderAddons", "sider.ini"), "w") as f:
        f.write("[sider]\n")
    return g


def league(name, country, names, cups=False):
    q = {"name": name, "country": country, "clubs": len(names), "legs": 2, "club_names": list(names)}
    if cups:
        q.update(cup=True, supercup=True)
    return q


def stub(g):
    return SimpleNamespace(ok=lambda: True, livecpk_dir=os.path.join(g, "SiderAddons", "livecpk"), folder=g)


def build(g, base, recipe):
    """what Mod Studio's Build does: plan_of (the ledger of the version shared last, when there is
    one), then Build"""
    pl = BP.plan_of(recipe, base, stub(g))
    log = []
    B.build(pl, base, g, True, log=log.append)
    return plan_now(g), pl, log


def plan_now(g):
    with open(os.path.join(g, "SiderAddons", "livecpk", WORLD, "leaguebuilder-plan.json"), encoding="utf-8") as f:
        return json.load(f)


def player_ids(g):
    with open(os.path.join(g, "SiderAddons", "livecpk", WORLD, "fl26playerids.json"), encoding="utf-8") as f:
        return json.load(f)


def export(g, version, out, keep=True):
    """Share world as zip, as the Build page's do_export: the version shared last is this PC's ledger
    of the world (told by the built world's leagues and clubs, recipe_of_world); the new one goes
    into this PC's history unless it is a test zip (keep=False)"""
    sd = os.path.join(g, "SiderAddons")
    # review 2 (18.11.): export_world finds the version before and keeps the ledger itself, as
    # release.py's and coldstart.py's exports call it (no prev_ledger)
    info = I.export_world(sd, WORLD, out, version=version, test=not keep, keep_broken=keep)
    info.pop("ledger_data")
    return info


def stored(world=WORLD):
    """the latest version this PC's history keeps of the world"""
    files = D.store_files(world)
    return D.load(files[-1][2], world) if files else None


def tree(d):
    out = {}
    for top, _dirs, files in os.walk(d):
        for f in files:
            p = os.path.join(top, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, d)] = fh.read()
    return out


def look(sd, src):
    """Import your world's look(): the zip's parts, with p.update as the page's job sets it"""
    work = tempfile.mkdtemp(prefix="lw_", dir=TMP)
    parts = I.detect(I.unpack(src, work), "mod")
    g = T.Game(sd)
    for p in parts:
        if p.kind == "world":
            p.made = I.world_made(src)
            p.update = None
            if I.installed_as(sd, p.name) or I.ready_world(g, p.name):
                p.update = I.update_check(g, p.name, os.path.dirname(p.world_file))
    return parts


def page_texts(sd, src):
    parts = look(sd, src)
    page = SimpleNamespace(app=SimpleNamespace(game=T.Game(sd)), src=src)
    return parts, PI.Install.headline(page, parts), PI.Install.plain(page, parts)


def install(sd, parts, update):
    """the Install button's job: the version installed out first, then this one"""
    ini = SiderIni.load(os.path.join(sd, "sider.ini"))
    g = T.Game(sd)
    if update is not None:
        I.replace_world(g, ini, WORLD)
    rec = I.Installer(g, ini, "shared", replace_lines=True).run(parts)
    ini.save(backup=False)
    return rec


def without_ledger(src, dst):
    """a copy of the zip as export made it before 17.11.: no ledger, no version"""
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
        for m in zi.infolist():
            if m.filename.endswith(D.LEDGER):
                continue
            data = zi.read(m)
            if m.filename == I.WORLD_INFO:
                info = json.loads(data)
                for k in ("pack_version", "ledger", "careers"):
                    info.pop(k, None)
                data = json.dumps(info, indent=1).encode()
            zo.writestr(m, data)
    return dst


def main(base):
    try:
        A = ["Alba %d" % i for i in range(11)]
        Dn = ["Andor %d" % i for i in range(10)]
        squad = {str(k): {"name": "Ledger Player %d" % k, "Registered Position": "CF" if k else "GK", "Age": "24",
                          "birth_date": "2001-02-%02d" % (k + 1)} for k in range(18)}
        recipe = {"world": WORLD, "leagues": [league("Ledger Albania", "Albania", A, True), league("Ledger Andorra", "Andorra", Dn)],
                  "players": {"Ledger Albania/0": {"edits": squad}}}
        # ---- the author: v1
        a = game_folder("author")
        pl1, _p, _log = build(a, base, recipe)
        ids1 = player_ids(a)
        z1 = os.path.join(TMP, WORLD + "-v1.zip")
        info1 = export(a, "Ledger 1", z1)
        with zipfile.ZipFile(z1) as z:
            names = z.namelist()
            zinfo = json.loads(z.read(I.WORLD_INFO))
            zled = json.loads(z.read("SiderAddons/livecpk/%s/%s" % (WORLD, D.LEDGER)))
        ok("export v1: the zip carries the ledger, its version and 'first'",
           "SiderAddons/livecpk/%s/%s" % (WORLD, D.LEDGER) in names and zinfo["pack_version"] == "Ledger 1"
           and zinfo["careers"] == {"continue_from": None, "first": True} and zled["number"] == 1)
        ok("export v1: the ledger is the world's ids (21 clubs, 2 leagues, every player of its new clubs)",
           len(D.ids_of(zled["plan"], zled["players"])["clubs"]) == 21
           and len(D.ids_of(zled["plan"], zled["players"])["leagues"]) == 2
           and set(D.ids_of(zled["plan"], zled["players"])["players"])
           == {int(v) for c, ks in ids1["clubs"].items() for v in ks.values()})
        ok("export v1: no path of this PC in the ledger", TMP.replace("\\", "/").lower() not in json.dumps(zled).lower()
           and TMP.lower() not in json.dumps(zled).lower())
        ok("this PC keeps the ledger of the version shared last", stored()["version"] == "Ledger 1")

        # ---- a player: v1 installed, a career on it
        p = T.sider(os.path.join(TMP, "player"))
        install(p, look(p, z1), None)
        ok("the player has v1 (a ready world from a zip, with its ledger)",
           I.ready_world(T.Game(p), WORLD) and os.path.isfile(os.path.join(p, "livecpk", WORLD, D.LEDGER)))
        save = os.path.join(SAVES, SV.ACTIVE)
        os.makedirs(save)
        for n, data in (("MLSAVE0001", b"career of v1" * 100), ("fl26swiss-state.bin", b"\x01\x02state" * 50),
                        ("EDIT00000000", b"edit"), ("EDIT00000000.fl26x", b"side")):
            with open(os.path.join(save, n), "wb") as f:
                f.write(data)
        os.makedirs(os.path.join(SAVES, SV.PREFIX + WORLD + "-other"))
        before = tree(os.path.join(SAVES))

        # ---- the author edits: a club renamed, a league added, a player taken out
        r2 = json.loads(json.dumps(recipe))
        r2["leagues"][0]["club_names"][3] = "Alba Three FC"
        r2["leagues"].append(league("Ledger Bosnia", "Bosnia and Herzegovina", ["Bos %d" % i for i in range(10)]))
        r2["players"]["Ledger Albania/0"]["remove"] = ["5"]
        r2["leagues"][1]["legs"] = 1                  # review 8: played another way (a warning, no stop)
        gone_pid = int(ids1["clubs"]["Ledger Albania/0"]["5"])
        plan_mtime = os.path.getmtime(os.path.join(a, "SiderAddons", "livecpk", WORLD, "leaguebuilder-plan.json"))
        try:
            build(a, base, r2)
            ok("a player taken out, not retired: Build stops", False)
        except B.LedgerProblems as e:
            ok("a player taken out, not retired: Build stops and names him (%s)" % D.summary(e.gone),
               [x[0] for x in e.gone.get("players", [])] == [gone_pid] and set(e.gone) == {"players"}
               and e.version == "Ledger 1")
            ok("... the world in the game is still v1", os.path.getmtime(os.path.join(
                a, "SiderAddons", "livecpk", WORLD, "leaguebuilder-plan.json")) == plan_mtime)
            added = D.add_retire(r2, D.retire_entries(e.gone, "taken out in the test"))   # "Retire these"
            ok("Retire these writes him into the recipe's id_retire", added == 1
               and r2["id_retire"] == {"players": {str(gone_pid): "taken out in the test"}})
        w = D.plan_warnings(BP.plan_of(r2, base, stub(a)), stored(), r2.get("id_retire"))
        ok("Check the plan: nothing of v1 dropped by the plan (%s)" % (D.summary(w) or "nothing"), w == {})
        pl2, used, log2 = build(a, base, r2)
        ids2 = player_ids(a)
        ok("retired: Build goes through and says every id is kept",
           any("keeps its id (1 retired by the recipe, 1 clubs with another name)" in l for l in log2))
        t1 = {n: t for q in pl1["leagues"] for n, t in zip(q["club_names"], q["teams"])}
        t2 = {n: t for q in pl2["leagues"] for n, t in zip(q["club_names"], q["teams"])}
        ok("the renamed club keeps its id", t2["Alba Three FC"] == t1["Alba 3"])
        ok("every club of v1 keeps its id", all(t2.get(n, t2.get("Alba Three FC")) == t
                                                for n, t in t1.items() if n != "Alba 3"))
        l1 = {q["name"]: (q["rid"], q["cid"]) for q in pl1["leagues"]}
        l2 = {q["name"]: (q["rid"], q["cid"]) for q in pl2["leagues"]}
        ok("a league added: the leagues of v1 keep their regulation and competition ids", all(l2[n] == l1[n] for n in l1))
        ok("... the new league takes ids no league of v1 had", l2["Ledger Bosnia"][0] not in {x[0] for x in l1.values()}
           and l2["Ledger Bosnia"][1] not in {x[1] for x in l1.values()})
        c1, c2 = pl1.get("cup_ids") or {}, pl2.get("cup_ids") or {}
        ok("the cups of v1 keep their ids (%s)" % sorted(c1), c1 and all(c2.get(k) == v for k, v in c1.items()))
        p1 = {int(v) for ks in ids1["clubs"].values() for v in ks.values()}
        p2 = {int(v) for ks in ids2["clubs"].values() for v in ks.values()}
        ok("every player of v1 but the retired one keeps his id", p1 - p2 == {gone_pid})
        ok("the retired id is nobody's", gone_pid not in p2 and gone_pid in ids2["retired"])
        ok("the new league's players take ids v1 never gave", not (p2 - p1) & (p1 | set(ids1.get("retired") or [])))
        ok("the plan names the ledger's version, no path", pl2.get("id_ledger_of", {}).get("version") == "Ledger 1"
           and "id_ledger" not in pl2 and pl2["settings"].get("id_retire") == r2["id_retire"])
        z2 = os.path.join(TMP, WORLD + "-v2.zip")
        info2 = export(a, "Ledger 2", z2)
        ok("export v2: careers of Ledger 1 continue", info2["careers"]["continue_from"] == "Ledger 1"
           and info2["ledger"]["number"] == 2)
        led2 = stored()
        ok("the ledger of v2 keeps the retirement", led2["retire"]["players"] == {str(gone_pid): "taken out in the test"})
        # a Build after the export pins to v2 (this PC's copy of the version shared last)
        _p, now = D.find(r2, None, os.path.join(a, "SiderAddons", "livecpk"))
        ok("the next Build pins to v2", now["version"] == "Ledger 2")

        # ---- the player: the v2 zip is an Update
        parts, head, plain = page_texts(p, z2)
        up = next(x for x in parts if x.kind == "world").update
        ok("update_check: v2 keeps every id of v1 (%r)" % up, up and up["ok"] and up["from"] == "Ledger 1"
           and up["to"] == "Ledger 2" and up["retired"] == {"players": 1} and up["match"] == "lineage"
           and up["reasons"] == ["taken out in the test"])
        ok("headline: an update (%r)" % head, head == "%s: an update of the world %s you have (Ledger 1 → Ledger 2)"
           % (os.path.basename(z2), WORLD))
        ok("summary: the careers stay, no 'start a new Master League'; the player retired with the author's "
           "reason; the league played another way, not checked in the game (%r)" % plain,
           "Your careers stay" in plain and "new Master League with this one" not in plain
           and "stand-in" in plain and "taken out in the test" in plain and "two copies" not in plain
           and "Ledger Andorra" in plain and "not checked in the game" in plain)
        gp = T.Game(p)
        gp.ini_path = os.path.join(p, "sider.ini")
        sw = SV.Switch({}, gp, WORLD)
        ok("the world in the game is %s; the save folder needs no switch for its Update (%s)"
           % (SV.in_game(gp), sw.needed()), SV.in_game(gp) == WORLD and not sw.needed())
        install(p, parts, up)
        ok("Update: the save folder byte for byte as it was (careers, fl26swiss-state.bin, Edit save)",
           tree(SAVES) == before)
        ok("Update: the world is v2 now", D.load(os.path.join(p, "livecpk", WORLD, D.LEDGER))["version"] == "Ledger 2")
        # review 7: an Update still asks about the old Edit save, in its own words (keep it for the career)
        asked = []
        page = SimpleNamespace(t_install=time.time() + 60, ask_edit=lambda update: asked.append(update) or False)
        PI.Install.edit_check(page, WORLD, True)
        ok("review 7: an Update asks about the Edit save too, as an Update (%s)" % asked, asked == [True])
        src = open(PI.__file__, encoding="utf-8").read()
        ok("... keep it to continue the career, move it aside for a new Master League (Keep it is the default)",
           "To continue your career: keep it" in src and "box.setDefaultButton(keep)" in src
           and "self.edit_check(w, updated)" in src)
        # review 9: the older zip over the newer one: never an Update
        parts, head, plain = page_texts(p, z1)
        up = next(x for x in parts if x.kind == "world").update
        ok("review 9: v1 over v2: not an Update, an older version (%r / %r)" % (up and up["why"], head),
           up and not up["ok"] and up["why"] == "older" and "an older version" in head and "an update" not in head
           and "older version (Ledger 1) than the one you have (Ledger 2)" in plain)

        # ---- the player makes it editable (worlds.make_editable keeps its ledger) and shares it again
        from modstudio import worlds as WL
        os.environ["APPDATA"] = os.path.join(TMP, "appdata-player")
        ok("Make it editable: the zip's ledger goes into this PC's history, its lineage with it",
           WL.keep_ledger(os.path.join(p, "livecpk", WORLD), WORLD)
           and stored()["version"] == "Ledger 2" and stored()["lineage"] == led2["lineage"])
        ok("... once: a second time changes nothing", not WL.keep_ledger(os.path.join(p, "livecpk", WORLD), WORLD))
        zp = os.path.join(TMP, WORLD + "-player.zip")
        infop = I.export_world(p, WORLD, zp, version="Player 3", prev_ledger=stored())
        with zipfile.ZipFile(zp) as z:
            lz = [n for n in z.namelist() if n.endswith(D.LEDGER)]
            zl = json.loads(z.read(lz[0]))
        ok("shared again: one ledger in the zip, the new one, after Ledger 2, the same lineage (%s)" % infop["careers"],
           len(lz) == 1 and zl["version"] == "Player 3" and zl["number"] == 3
           and infop["careers"]["continue_from"] == "Ledger 2" and zl["lineage"] == led2["lineage"])
        os.environ["APPDATA"] = os.path.join(TMP, "appdata")

        # ---- the same name, other ids: Replace and a warning
        o = game_folder("other-author")
        os.environ["APPDATA"] = os.path.join(TMP, "appdata-other")
        build(o, base, {"world": WORLD, "leagues": [league("Other Albania", "Albania", ["X %d" % i for i in range(12)])]})
        zo = os.path.join(TMP, WORLD + "-other.zip")
        export(o, "Other 1", zo)
        os.environ["APPDATA"] = os.path.join(TMP, "appdata")
        parts, head, plain = page_texts(p, zo)
        up = next(x for x in parts if x.kind == "world").update
        ok("another world of the same name: not an Update (%s)" % up.get("why"), up and not up["ok"] and up["why"] == "other")
        ok("... Replace as before, and a warning (%r / %r)" % (head, plain),
           "start a new Master League with this one" in plain and "another world with the same name" in plain
           and "an update" not in head and "not a later version of it" in head)
        # ---- a zip from before the ledger: as before
        zb = without_ledger(z2, os.path.join(TMP, WORLD + "-noledger.zip"))
        parts, head, plain = page_texts(p, zb)
        ok("a zip without a ledger: no Update, no warning, as before (%r)" % head,
           next(x for x in parts if x.kind == "world").update is None and "an update" not in head
           and "start a new Master League with this one" in plain and "does not keep" not in plain)
        # ---- a world installed from a zip without a ledger, the new zip keeps its ids: an Update
        q = T.sider(os.path.join(TMP, "player-old"))
        install(q, look(q, without_ledger(z1, os.path.join(TMP, WORLD + "-v1-noledger.zip"))), None)
        ok("the old world has no ledger", not os.path.exists(os.path.join(q, "livecpk", WORLD, D.LEDGER)))
        parts, head, plain = page_texts(q, z2)
        up = next(x for x in parts if x.kind == "world").update
        ok("an installed world without a ledger whose ids v2 keeps: an Update (%r)" % up,
           up and up["ok"] and up["from"] == "Ledger 1" and "Your careers stay" in plain)
        ok("... named by the version of the chain with its ids (review 3, 18.11.) (%r)" % head,
           head.endswith("(Ledger 1 → Ledger 2)"))
        from modstudio import i18n
        try:
            i18n.set_language("hr")
            _parts, head_hr, plain_hr = page_texts(q, z2)
            ok("and in Croatian (%r / %r)" % (head_hr, plain_hr), "→ Ledger 2" in head_hr and head_hr != head
               and "Your careers" not in plain_hr and "karijer" in plain_hr.lower())
        finally:
            i18n.set_language("en")
        probes(base)
        probes2(base)
        probes3(base)
        print("%d cases passed" % N)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)


def probes(base):
    """the review's probes of 17.11.2026 (scratchpad ledgerreview/probe1-3.py), as cases"""
    from modstudio.project import Project, rename_in
    A = ["Alba %d" % i for i in range(11)]
    Dn = ["Andor %d" % i for i in range(10)]
    named = {str(k): {"name": "Named Y%d" % k, "Registered Position": "CF" if k else "GK", "Age": "24"} for k in range(18)}
    recipe = {"world": WORLD, "leagues": [league("Ledger Albania", "Albania", A, True), league("Ledger Andorra", "Andorra", Dn)],
              "players": {"Ledger Albania/1": {"edits": named}}}
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-probes")
    a = game_folder("probe-author")
    pl1, _p, _l = build(a, base, recipe)
    ids1 = player_ids(a)
    z1 = os.path.join(TMP, "probe-v1.zip")
    export(a, "Ledger 1", z1)
    led1 = stored()
    p = T.sider(os.path.join(TMP, "probe-player"))
    install(p, look(p, z1), None)

    # probe 1a: another author, the same name and the same shape (its ids are the same: ids are given in order)
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-probe-other")
    o = game_folder("probe-other")
    ro = {"world": WORLD, "leagues": [league("Kosovo Superliga X", "Albania", ["Prishtina %d" % i for i in range(11)], True),
                                       league("Other Andorra", "Andorra", ["Other %d" % i for i in range(10)])]}
    plo, _p, _l = build(o, base, ro)
    ok("probe 1a: another author's world of the same shape has the same team ids (why a lineage is needed)",
       [q["teams"] for q in plo["leagues"]] == [q["teams"] for q in pl1["leagues"]])
    zo = os.path.join(TMP, "probe-other.zip")
    export(o, "Other 1", zo)
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-probes")
    parts, head, plain = page_texts(p, zo)
    up = next(x for x in parts if x.kind == "world").update
    ok("probe 1a: ... Install offers no Update over it -- another world with the same name (%r)" % (up,),
       up and not up["ok"] and up["why"] == "other" and "an update" not in head and "Your careers stay" not in plain)
    _p2, got = D.find(ro, None, os.path.join(a, "SiderAddons", "livecpk"))
    ok("probe 1a: ... and the author's Build of that recipe pins to none of his ledgers", got is None)

    # probe 3 (c1): a league renamed the Mod Studio way: every player keeps his id, no retirement
    r3 = json.loads(json.dumps(recipe))
    r3["leagues"][0]["name"] = "Ledger Shqiperia"
    rename_in(r3, "Ledger Albania", "Ledger Shqiperia")
    pl3, _p, log3 = build(a, base, r3)
    ids3 = player_ids(a)
    p1 = {int(v) for ks in ids1["clubs"].values() for v in ks.values()}
    p3 = {int(v) for ks in ids3["clubs"].values() for v in ks.values()}
    ok("probe 3: a league renamed: Build goes through, every player id kept (%d of %d)" % (len(p1 & p3), len(p1)),
       p1 <= p3 and any("keeps its id (0 retired" in l for l in log3))
    ok("probe 3: ... its regulation and competition ids too",
       {(q["rid"], q["cid"]) for q in pl3["leagues"]} == {(q["rid"], q["cid"]) for q in pl1["leagues"]})

    # probe 2 (c2): the first club taken out the Mod Studio way (shift_places): only it and its players go
    r2 = json.loads(json.dumps(recipe))
    pr = SimpleNamespace(recipe=r2, touch=lambda: None, PLACE_LISTS=Project.PLACE_LISTS)
    pr.league = lambda n: Project.league(pr, n)
    pr.players = lambda: Project.players(pr)
    pr.club_keyed = lambda: Project.club_keyed(pr)          # D17 (20.11.2026): shift_places moves club_money too
    Project.shift_places(pr, "Ledger Albania", 0, -1)
    r2["leagues"][0]["clubs"] = 10
    x_tid = pl1["leagues"][0]["teams"][0]
    x_ids = {int(v) for v in ids1["clubs"]["Ledger Albania/0"].values()}
    y_ids = ids1["clubs"]["Ledger Albania/1"]
    try:
        build(a, base, r2)
        ok("probe 2: the first club taken out: Build stops", False)
    except B.LedgerProblems as e:
        gone_p = {x[0] for x in e.gone.get("players", [])}
        ok("probe 2: the first club taken out: Build stops on it and its players only (%s)" % D.summary(e.gone),
           [x[0] for x in e.gone.get("clubs", [])] == [x_tid] and gone_p == x_ids and not e.mass)
        D.add_retire(r2, D.retire_entries(e.gone, "club taken out in the test"))
    pl2, _p, _l = build(a, base, r2)
    ids2 = player_ids(a)
    ynow = ids2["clubs"]["Ledger Albania/0"]
    ok("probe 2: ... the next club, now in its place, keeps its named players' ids (%s)" % [ynow[str(k)] for k in range(3)],
       all(ynow[str(k)] == y_ids[str(k)] for k in range(18)) and not x_ids & {int(v) for v in ynow.values()})

    # probe 1b: a league replaced by another: it takes ids no version had; the old one retired
    rb = json.loads(json.dumps(recipe))
    rb["leagues"][1] = league("Ledger Bosnia", "Bosnia and Herzegovina", ["Bos %d" % i for i in range(10)])
    try:
        D.find(rb, None, os.path.join(a, "SiderAddons", "livecpk"))
        ok("probe 1b: half the leagues replaced, no id_lineage: find stops, it does not leave the ledger out", False)
    except D.LedgerError as e:
        # review 2 (18.11.): the question Build asks (LedgerAsk: its two buttons write the lineage)
        ok("probe 1b: half the leagues replaced, no id_lineage: find stops and asks which world it is (%s)" % e,
           isinstance(e, D.LedgerAsk) and e.lineage == led1["lineage"] and e.version == "Ledger 1"
           and "another world of the same name?" in str(e))
    rb[D.LINEAGE_KEY] = led1["lineage"]              # "It is that world" (BuildPage.ask_lineage)
    try:
        build(a, base, rb)
        ok("probe 1b: a league replaced: Build stops", False)
    except B.LedgerProblems as e:
        ok("probe 1b: a league replaced: Build stops on the old league, its clubs and players (%s)" % D.summary(e.gone),
           [x[0] for x in e.gone.get("leagues", [])] == [q["rid"] for q in pl1["leagues"] if q["name"] == "Ledger Andorra"]
           and len(e.gone.get("clubs", [])) == 10 and not e.gone.get("reused"))
        D.add_retire(rb, D.retire_entries(e.gone, "league replaced in the test"))
    plb, _p, logb = build(a, base, rb)
    old = {(q["rid"], q["cid"]) for q in pl1["leagues"]}
    bos = next(q for q in plb["leagues"] if q["name"] == "Ledger Bosnia")
    spent = led1["spent"]
    ok("probe 1b: ... the new league takes a regulation and competition id no version had (%s/%s; Andorra had %s)"
       % (bos["rid"], bos["cid"], [x for x in old if x not in {(q["rid"], q["cid"]) for q in plb["leagues"]}]),
       bos["rid"] not in spent["rids"] and bos["cid"] not in spent["cids"])
    ok("probe 1b: ... and its cups none either", all(
        w.get("cid") not in spent["cids"] or (pl1.get("cup_ids") or {}).get(k) == w for k, w in (plb.get("cup_ids") or {}).items()))
    zb = os.path.join(TMP, "probe-v2.zip")
    infob = export(a, "Ledger 2", zb)
    ok("probe 1b: export: careers of Ledger 1 do not go on (a league retired) (%s)" % infob["careers"],
       infob["careers"]["continue_from"] is None and infob["careers"]["retired"].get("leagues") == 1)
    parts, head, plain = page_texts(p, zb)
    up = next(x for x in parts if x.kind == "world").update
    ok("review 4: retired clubs and a league: Replace, not Update, with the list and the author's reason (%r)" % plain,
       up and not up["ok"] and up["why"] == "retired" and "Ledger Andorra" in plain
       and "league replaced in the test" in plain and "Your careers stay" not in plain)

    # review 6: a test zip is not kept as the version shared last
    zt = os.path.join(TMP, "probe-test.zip")
    before = [n for n, _l, _p in D.store_files(WORLD)]
    export(a, "Test 3", zt, keep=False)
    ok("review 6: a test zip: this PC's history unchanged (%s)" % before,
       [n for n, _l, _p in D.store_files(WORLD)] == before and stored()["version"] == "Ledger 2")
    src = open(BP.__file__, encoding="utf-8").read()
    ok("review 6: Export reads the ledger in a worker, stops on one it cannot read, asks before keeping a "
       "version that breaks careers, keeps a version by its number (store_save)",
       "run_job(look, looked, not_found)" in src and "The export stopped: the ids of the version shared before" in src
       and "Keep %s as the version you shared last anyway?" in src and "idledger.store_save(led)" in src
       and "store_path" not in src)
    os.environ["APPDATA"] = os.path.join(TMP, "appdata")


def probes2(base):
    """the second review's probes of 18.11.2026 (scratchpad ledgerreview2: p6_build, p2_lineage, the
    release.py export; item 12), with real Builds"""
    import subprocess
    from test_world_roundtrip import free_game_clubs
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-review2")
    _idle, busy = free_game_clubs(B, base, 2)
    A = ["Alba %d" % i for i in range(10)]
    r1 = {"world": WORLD, "leagues": [league("Ledger Albania", "Albania", A)]}
    a = game_folder("review2-author")
    pl1, _p, _l = build(a, base, r1)
    info1 = export(a, "R1", os.path.join(TMP, "r1.zip"))
    t1 = dict(zip(pl1["leagues"][0]["club_names"], pl1["leagues"][0]["teams"]))
    ok("review2 2: export_world (no prev_ledger, as release.py calls it) kept v1 in the history (%s)" % info1.get("stored"),
       info1.get("stored") and stored()["version"] == "R1" and stored()["number"] == 1)
    ok("review2 9: ... and wrote its lineage into the world's plan",
       (plan_now(a).get("settings") or {}).get(D.LINEAGE_KEY) == stored()["lineage"])

    # (a) p6: a league with a club of the game whose places a new club takes (a swap)
    r2 = json.loads(json.dumps(r1))
    r2["leagues"].append(dict(league("Ledger Andorra", "Andorra", ["And %d" % i for i in range(10)]),
                              game_clubs=[{"at": 9, "id": busy[0], "swap": {"name": "Swap FC"}}]))
    try:
        pl2, _p, _l = build(a, base, r2)
        err = None
    except B.LedgerProblems as e:
        pl2, err = None, e
    ok("review2 3 (p6 a): a swap added: Build goes through (%s)" % (err and D.summary(err.gone)), err is None)
    t2 = dict(zip(pl2["leagues"][0]["club_names"], pl2["leagues"][0]["teams"]))
    sid = [g.get("swap_id") for q in pl2["leagues"] for g in (q.get("game_clubs") or {}).values() if g.get("swap_id")]
    ok("review2 3: ... every club of v1 keeps its id, the swap takes one no club had (%s; v1 %s..%s)"
       % (sid, min(t1.values()), max(t1.values())),
       t2 == t1 and len(sid) == 1 and sid[0] not in t1.values() and sid[0] not in set(pl1.get("retired_tids") or []))
    info2 = export(a, "R2", os.path.join(TMP, "r2.zip"))
    # 18.11.2026 evening (rowkeep.py): the swap is a club new to the world in the places of a game
    # competition R1 has -- a career of R1 has none of its players: careers of R1 do not go on
    ok("review2 3: ... the swap club is in the ledger; it plays in a competition of R1, so careers of R1 do not "
       "go on (%s, %s)" % (D.of_ledger(stored())["clubs"].get(sid[0]), info2["careers"].get("rows")),
       D.of_ledger(stored())["clubs"].get(sid[0]) == ("Swap FC", "in place of %d" % busy[0])
       and info2["careers"]["continue_from"] is None and info2["careers"]["rows"]["ok"] is False
       and info2["careers"]["rows"]["other_club"] >= 1)
    pl2b, _p, _l = build(a, base, r2)
    sid2 = [g.get("swap_id") for q in pl2b["leagues"] for g in (q.get("game_clubs") or {}).values() if g.get("swap_id")]
    ok("review2 3: ... and the next Build gives the swap the same id (%s)" % sid2, sid2 == sid)

    # (b) p6: a club replaced in its place keeps the id: Build lists it, Install says it
    r3 = json.loads(json.dumps(r2))
    r3["leagues"][0]["club_names"][9] = "Other FC"
    pl3, _p, log3 = build(a, base, r3)
    ok("review2 7 (p6 b): a club with another name in its place: the Build log names it (%s)"
       % [l for l in log3 if "is Other FC now" in l],
       any("club %d Alba 9 is Other FC now" % t1["Alba 9"] in l for l in log3))
    z3 = os.path.join(TMP, "r3.zip")
    export(a, "R3", z3)
    p = T.sider(os.path.join(TMP, "review2-player"))
    install(p, look(p, os.path.join(TMP, "r2.zip")), None)
    parts, head, plain = page_texts(p, z3)
    up = next(x for x in parts if x.kind == "world").update
    ok("review2 7: ... and the Update over R2 says so (%r)" % plain,
       up and up["ok"] and "Alba 9 → Other FC" in plain)

    # item 5: a test zip spends its number; the real one after it is not given the same
    zt = os.path.join(TMP, "r4-test.zip")
    infot = export(a, "R4 test", zt, keep=False)
    with zipfile.ZipFile(zt) as z:
        tl = json.loads(z.read("SiderAddons/livecpk/%s/%s" % (WORLD, D.LEDGER)))
    rl = None
    if release is None:
        print("skip  review2 1/5: release.py's export after the test zip -- release.py not in this tree")
    else:
        z5 = os.path.join(TMP, "r5.zip")
        # release.py's export, as its DEFAULT_CMDS run it (a process of its own)
        cmd = [c.format(python=sys.executable, tools=HERE, sider=os.path.join(a, "SiderAddons"), world=WORLD, artifact=z5,
                        recipe="")
               for c in release.DEFAULT_CMDS["export"]]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        with zipfile.ZipFile(z5) as z:
            rl = json.loads(z.read("SiderAddons/livecpk/%s/%s" % (WORLD, D.LEDGER)))
        ok("review2 1/5: a test zip says test and spends number %d; release.py's export after it is number %d, "
           "follows R3 and keeps it (%s)" % (tl["number"], rl["number"], r.stdout.strip().splitlines()[-1:]),
           r.returncode == 0 and tl.get("test") is True and infot.get("stored") is None and rl["number"] == tl["number"] + 1
           and rl["after"]["version"] == "R3" and stored()["number"] == rl["number"] and not rl.get("test"))
        parts, head, plain = page_texts(p, z5)            # the player has R2: R5's chain has it
        ok("review2 1: ... the player of R2 gets an Update to it", next(x for x in parts if x.kind == "world").update["ok"])

    # item 2 (p2): another PC (an empty APPDATA): export and Build stop, nothing is written
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-review2-new-pc")
    z6 = os.path.join(TMP, "r6.zip")
    try:
        I.export_world(os.path.join(a, "SiderAddons"), WORLD, z6)
        e = None
    except D.LedgerError as x:
        e = x
    ok("review2 2 (p2): on a PC without the world's ledgers, export stops and says where to put it (%s)" % e,
       e is not None and "has no id ledger of it" in str(e) and not os.path.exists(z6) and not os.path.exists(z6 + ".part"))
    r6 = dict(json.loads(json.dumps(r3)), **{D.LINEAGE_KEY: (rl or tl)["lineage"]})
    try:
        build(a, base, r6)
        e = None
    except B.BuildError as x:
        e = x
    ok("review2 2: ... and so does the Build of the recipe that names the lineage (%s)" % e,
       e is not None and "has no id ledger of it" in str(e))
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-review2")

    # item 12: a NewLife club new to the recipe never takes an id a club of the world had
    own = lambda n: {"name": "L1", "clubs": n}
    m1, _f = B.newlife_tids([own(10), {"name": "L2", "clubs": 1, "newlife": {"clubs": [98400]}}], base)
    gave = list(range(m1[98400] - 10, m1[98400] + 1))
    m3, _f = B.newlife_tids([own(9), {"name": "L2", "clubs": 2, "newlife": {"clubs": [98400, 98402]}}], base,
                            {"98400": m1[98400]}, new_avoid=gave)
    ok("review2 12: a club of the world taken out, a NewLife club added: it takes a fresh id (%d; the world's "
       "were %d..%d), the NewLife club before keeps its own" % (m3[98402], gave[0], gave[-1]),
       m3[98402] not in gave and m3[98400] == m1[98400])
    src = open(B.__file__, encoding="utf-8").read()
    ok("review2 12: ... plan() steps every NewLife club without a pin round the ids an earlier Build gave",
       "new_avoid=used_tids(prev)" in src)


def _release_export(sider, zpath, recipe=""):
    """release.py's export, as its DEFAULT_CMDS run it (a process of its own)"""
    import subprocess
    cmd = [c.format(python=sys.executable, tools=HERE, sider=sider, world=WORLD, artifact=zpath, recipe=recipe)
           for c in release.DEFAULT_CMDS["export"]]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))


def probes3(base):
    """the third review's probes of 18.11.2026 (scratchpad ledgerreview3: p3_store_name (a), the
    export's order around os.replace), with real Builds and release.py's export"""
    os.environ.pop("FL26_LEDGER_STORE", None)
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-review3")
    A = ["Gamma %d" % i for i in range(10)]
    r1 = {"world": WORLD, "leagues": [league("Ledger Montenegro", "Montenegro", A)]}
    a = game_folder("review3-author")
    sd = os.path.join(a, "SiderAddons")
    build(a, base, r1)
    export(a, "G1", os.path.join(TMP, "g1.zip"))
    lin = stored()["lineage"]
    shared = os.path.join(TMP, "review3-shared")
    os.makedirs(shared)
    copy = os.path.join(shared, WORLD + "-G1.fl26ids")           # the author's copy, under a name of its own
    shutil.copy(D.store_file(stored()), copy)

    # ---- item 1 (p3 a): another PC; the recipe names its ledger (GigaPack: id_ledger + id_lineage)
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-review3-pc2")
    r2 = dict(json.loads(json.dumps(r1)), **{D.LINEAGE_KEY: lin, D.LEDGER_KEY: copy})
    build(a, base, r2)
    ok("review3 1 (p3 a): the built plan keeps the recipe's id_ledger as an absolute path (%s)"
       % (plan_now(a).get("settings") or {}).get(D.LEDGER_KEY),
       (plan_now(a).get("settings") or {}).get(D.LEDGER_KEY) == os.path.abspath(copy))
    if release is None:
        print("skip  review3 1: release.py's export without --recipe -- release.py not in this tree")
    else:
        z2 = os.path.join(TMP, "g2.zip")
        r = _release_export(sd, z2)
        tail = r.stdout.strip().splitlines()[-1:] + r.stderr.strip().splitlines()[-1:]
        ok("review3 1: release.py's export without --recipe goes on from G1 (%s)" % tail,
           r.returncode == 0 and os.path.isfile(z2) and stored()["after"]["version"] == "G1")
        with zipfile.ZipFile(z2) as z:
            cut = json.loads(z.read("SiderAddons/livecpk/%s/leaguebuilder-plan.json" % WORLD))
        st = cut.get("settings") or {}
        ok("review3 1: ... the zip's plan names no folder of this PC (%s)" % st.get(D.LEDGER_KEY),
           not os.path.isabs(str(st.get(D.LEDGER_KEY) or "")))
        rec = B.recipe_from_plan(cut, base)
        ok("review3 1: ... and the recipe Make it editable reads back from it has no id_ledger to stop on",
           D.LEDGER_KEY not in rec and rec.get(D.LINEAGE_KEY) == lin)

    # ... a third PC, the recipe in a file with id_ledger next to it (relative), the plan without one
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-review3-pc3")
    D.stamp_plan(os.path.join(sd, "livecpk", WORLD), {D.LEDGER_KEY: None})
    rpath = os.path.join(shared, WORLD + ".json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(dict(r2, **{D.LEDGER_KEY: os.path.basename(copy)}), f)
    if release is None:
        print("skip  review3 1: release.py's export with and without --recipe -- release.py not in this tree")
    else:
        z3 = os.path.join(TMP, "g3.zip")
        r = _release_export(sd, z3)
        ok("review3 1: ... without --recipe and a plan without id_ledger: the export stops (%s)"
           % (r.stdout + r.stderr).strip().splitlines()[-1:],
           r.returncode != 0 and "has no id ledger of it" in r.stdout + r.stderr and not os.path.exists(z3))
        r = _release_export(sd, z3, rpath)
        tail = r.stdout.strip().splitlines()[-1:] + r.stderr.strip().splitlines()[-1:]
        ok("review3 1: ... with --recipe it finds the ledger the recipe names and goes on from G1 (%s)" % tail,
           r.returncode == 0 and os.path.isfile(z3) and stored()["after"]["version"] == "G1")

    # ---- item 5: a failure on the way leaves no .part, no zip and no version in the history
    have = [x[0] for x in D.store_files(WORLD)]
    gave = sorted(D.issued(WORLD, lin))
    real = os.replace

    def no_replace(src, dst, *k, **kw):
        if str(src).endswith(".part"):
            raise OSError("disk full (a test)")
        return real(src, dst, *k, **kw)
    z5 = os.path.join(TMP, "g5.zip")
    os.replace = no_replace
    try:
        e = _raises(lambda: I.export_world(sd, WORLD, z5, version="G5", recipe=r2, recipe_path=None))
    finally:
        os.replace = real
    spent = sorted(D.issued(WORLD, lin))
    ok("review3 5: os.replace of the zip fails: the export stops, no .part, no zip, no version kept, its "
       "number spent (%s; %s -> %s)" % (e, gave, spent),
       isinstance(e, OSError) and not os.path.exists(z5 + ".part") and not os.path.exists(z5)
       and [x[0] for x in D.store_files(WORLD)] == have and len(spent) == len(gave) + 1)
    was = D.store_save

    def no_store(led):
        raise OSError("no room for the ledger (a test)")
    D.store_save = no_store
    try:
        e = _raises(lambda: I.export_world(sd, WORLD, z5, version="G6", recipe=r2))
    finally:
        D.store_save = was
    ok("review3 5: the ledger cannot be kept: the zip is taken away again (%s)" % e,
       isinstance(e, OSError) and not os.path.exists(z5) and not os.path.exists(z5 + ".part")
       and [x[0] for x in D.store_files(WORLD)] == have)
    nlp = I.no_local_paths

    def broken(text):
        raise RuntimeError("a bug (a test)")
    I.no_local_paths = broken
    try:
        e = _raises(lambda: I.export_world(sd, WORLD, z5, version="G7", recipe=r2))
    finally:
        I.no_local_paths = nlp
    ok("review3 5: any error while the zip is written takes the .part away (%s)" % e,
       isinstance(e, RuntimeError) and not os.path.exists(z5 + ".part") and not os.path.exists(z5))
    os.environ["APPDATA"] = os.path.join(TMP, "appdata-review3")


def _raises(fn):
    try:
        fn()
    except Exception as e:                # noqa: BLE001
        return e
    return None


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
