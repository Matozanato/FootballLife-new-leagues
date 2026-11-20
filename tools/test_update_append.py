r"""python tools/test_update_append.py <folder with the game's tables> [--against <git rev>]

An Update keeps the competition rows of the version before it (rowkeep.py, mato 18.11.2026: an
Update of a world must never break a career saved on the version before). Small worlds, offline:

  v1          two leagues, Build + export: the zip's ledger carries the rows of its tables
  no rows     v1's ledger as a ledger of before 18.11. (no "rows"): a Build of v2 without the
              recipe's id_tables warns and lays the tables out as before (the new league in the
              middle moves rows); with id_tables = the v1 zip it keeps them; id_tables of another
              version stops the Build
  v2          a new league put in the MIDDLE of the recipe and a new league under an old one that
              exchanges no clubs with it: every Competition / CompetitionRegulation /
              CompetitionEntry row of v1 at its index, every entry id of v1 the same club,
              competition and place, the new rows after them, new entry ids above v1's highest;
              the old league above is not linked down (its row as it was); export: careers of v1
              go on; Install: an Update that says the new leagues come only in a new Master League
  v3          two clubs new to the world entered in a league of v2: Build and export say careers
              of v2 do not go on; Install offers Replace (why "rows"); check_update_ids FAILs
  no version  --against <rev> (a revision before rowkeep.py): v1 built by that revision's tools is
              byte for byte the tables of v1 built now (no version before: nothing of rowkeep runs)

Temporary game folders, APPDATA and FL26_SAVE_ROOT of its own; no game is started.
"""
import json, os, shutil, subprocess, sys, tempfile, zipfile
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(errors="backslashreplace")      # a console of cp1252 and the summary's arrows
except (AttributeError, ValueError):
    pass
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
TMP = tempfile.mkdtemp(prefix="fl26-updappend-")
os.environ["APPDATA"] = os.path.join(TMP, "appdata")
os.environ.pop("FL26_LEDGER_STORE", None)
os.environ["FL26_SAVE_ROOT"] = os.path.join(TMP, "saves")

import leaguebuilder as B               # noqa: E402
import idledger as D                    # noqa: E402
import rowkeep as R                     # noqa: E402
import check_update_ids as C            # noqa: E402
from modstudio import installer as I    # noqa: E402
from modstudio.siderini import SiderIni  # noqa: E402
from modstudio.pages import builder as BP  # noqa: E402
from modstudio.pages import install as PI  # noqa: E402
import test_world_share as T            # noqa: E402

N = 0
WORLD = "_FL26AppendWorld"


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


def league(name, country, names, **kw):
    q = {"name": name, "country": country, "clubs": len(names), "legs": 2, "club_names": list(names)}
    q.update(kw)
    return q


def stub(g):
    return SimpleNamespace(ok=lambda: True, livecpk_dir=os.path.join(g, "SiderAddons", "livecpk"), folder=g)


def build(g, base, recipe):
    pl = BP.plan_of(recipe, base, stub(g))
    log = []
    B.build(pl, base, g, True, log=log.append)
    return plan_now(g), log


def plan_now(g):
    with open(os.path.join(g, "SiderAddons", "livecpk", WORLD, "leaguebuilder-plan.json"), encoding="utf-8") as f:
        return json.load(f)


def world_root(g):
    return os.path.join(g, "SiderAddons", "livecpk", WORLD)


def tables_of(g):
    return R.tables_dir(R.world_db(world_root(g)), R.TABLES + (R.TEAM,))


def export(g, version, out):
    info = I.export_world(os.path.join(g, "SiderAddons"), WORLD, out, version=version, test=False, keep_broken=True)
    info.pop("ledger_data", None)
    return info


def look(sd, src):
    work = tempfile.mkdtemp(prefix="ua_", dir=TMP)
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
    ini = SiderIni.load(os.path.join(sd, "sider.ini"))
    g = T.Game(sd)
    if update is not None:
        I.replace_world(g, ini, WORLD)
    rec = I.Installer(g, ini, "shared", replace_lines=True).run(parts)
    ini.save(backup=False)
    return rec


def strip_rows():
    """this PC's ledger of the latest version as one of before 18.11.2026 evening: no "rows" """
    path = D.store_files(WORLD)[-1][2]
    led = D.load(path, WORLD)
    led.pop(D.ROWS_KEY, None)
    D.save(led, path)
    return led


def comp_index(t, cid):
    rows = R._split(t[R.TABLES[0]], R.COMP)
    return next(i for i, r in enumerate(rows) if R.comp_cid(r) == cid)


def reg_row(t, rid):
    return next(r for r in R._split(t[R.TABLES[1]], R.REG) if R.reg_id(r) == rid)


def kept_in_place(prev, t):
    """every row of prev at its index in tables t, every entry the same entry id, club, competition,
    place and flag (rows_of compares them whole)"""
    now = R.rows_of_tables(t)
    return all(now[k][:len(prev[k])] == prev[k] for k in R.KINDS)


def built_by(rev, base, recipe, appdata):
    """the pesdb tables of the world built from `recipe` by the tools of git revision `rev`"""
    src = os.path.join(TMP, "tools-" + rev.replace("/", "_"))
    os.makedirs(src)
    repo = os.path.dirname(HERE)
    tar = subprocess.run(["git", "-C", repo, "archive", rev, "tools"], check=True, capture_output=True).stdout
    tf = os.path.join(TMP, "tools.tar")
    with open(tf, "wb") as f:
        f.write(tar)
    import tarfile
    with tarfile.open(tf) as t:
        t.extractall(src)
    g = game_folder("against-" + rev.replace("/", "_"))
    rf = os.path.join(TMP, "against-recipe.json")
    with open(rf, "w", encoding="utf-8") as f:
        json.dump(recipe, f)
    code = r"""
import json, os, sys
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import leaguebuilder as B
from modstudio.pages import builder as BP
g, base = sys.argv[3], sys.argv[4]
recipe = json.load(open(sys.argv[2], encoding="utf-8"))
st = SimpleNamespace(ok=lambda: True, livecpk_dir=os.path.join(g, "SiderAddons", "livecpk"), folder=g)
B.build(BP.plan_of(recipe, base, st), base, g, True, log=lambda *a, **k: None)
"""
    # the user's site-packages (PySide6) is under the real APPDATA: site found it before this test set its own
    import site
    env = dict(os.environ, APPDATA=appdata, PYTHONIOENCODING="utf-8",
               PYTHONPATH=os.pathsep.join(x for x in (site.USER_SITE, os.environ.get("PYTHONPATH")) if x))
    subprocess.run([sys.executable, "-c", code, os.path.join(src, "tools"), rf, g, base], check=True, env=env,
                   cwd=TMP, stdout=subprocess.DEVNULL)
    return tables_of(g), g


def main(base, against):
    try:
        A = ["Alba %d" % i for i in range(12)]
        An = ["Andor %d" % i for i in range(10)]
        Bo = ["Bos %d" % i for i in range(10)]
        A2 = ["Andor B %d" % i for i in range(10)]
        r1 = {"world": WORLD, "leagues": [league("Append Albania", "Albania", A, cup=True, supercup=True),
                                          league("Append Andorra", "Andorra", An)]}
        # ---- v1, and the same world by the code of before (no version before: unchanged)
        a = game_folder("author")
        pl1, log1 = build(a, base, r1)
        t1 = tables_of(a)
        ok("v1: no version before, nothing of rowkeep in the log", not any("rows:" in l for l in log1)
           and "rows_kept" not in pl1)
        if against:
            th, _g = built_by(against, base, r1, os.path.join(TMP, "appdata-against"))
            ok("v1 built by %s: Competition, CompetitionRegulation, CompetitionEntry and Team byte for byte the "
               "same as now" % against, all(th[n] == t1[n] for n in R.TABLES + (R.TEAM,)))
        z1 = os.path.join(TMP, WORLD + "-v1.zip")
        info1 = export(a, "Append 1", z1)
        with zipfile.ZipFile(z1) as z:
            zled = json.loads(z.read("SiderAddons/livecpk/%s/%s" % (WORLD, D.LEDGER)))
        rows1 = zled.get(D.ROWS_KEY)
        ok("export v1: the ledger carries the rows of its tables (%d competitions, %d regulations, %d entries)"
           % tuple(len((rows1 or {}).get(k) or []) for k in R.KINDS),
           R.valid(rows1) and rows1 == R.rows_of_tables(t1) and info1["careers"]["first"])
        ok("... and the digest is the ids' as before (rows are not ids)",
           zled["digest"] == D.digest(D.ids_of(zled["plan"], zled["players"])))

        # ---- v2's recipe: a league in the middle, one under an old league with no exchange
        r2 = json.loads(json.dumps(r1))
        r2["leagues"].insert(1, league("Append Bosnia", "Bosnia and Herzegovina", Bo))
        r2["leagues"].append(league("Append Andorra 2", "Andorra", A2, above="Append Andorra", exchange=0))

        # a ledger of before 18.11. evening (beta 3, beta 4): no rows
        led1 = strip_rows()
        ok("v1's ledger without rows (as beta 3 / beta 4's)", D.ROWS_KEY not in led1)
        plw, logw = build(a, base, r2)
        tw = tables_of(a)
        ok("no rows, no id_tables: Build warns that the order is not known",
           any("warning: rows: the order of the competition tables of Append 1 is not known" in l for l in logw)
           and "rows_kept" not in plw)
        bos = next(q for q in plw["leagues"] if q["name"] == "Append Bosnia")
        ok("... and lays the tables out as before: the new league in the middle moves rows of v1 (Bosnia row %d of "
           "%d old)" % (comp_index(tw, bos["cid"]), len(rows1["competitions"])),
           comp_index(tw, bos["cid"]) < len(rows1["competitions"]) and not kept_in_place(rows1, tw))
        r2t = dict(r2, id_tables=z1)
        pl2, log2 = build(a, base, r2t)
        t2 = tables_of(a)
        ok("id_tables = the v1 zip: Build reads v1's rows there",
           any("rows:" in l and "keep their places (from %s)" % z1 in l for l in log2))

        # ---- v2: what is kept
        n_c, n_r, n_e = (len(rows1[k]) for k in R.KINDS)
        bos = next(q for q in pl2["leagues"] if q["name"] == "Append Bosnia")
        an2 = next(q for q in pl2["leagues"] if q["name"] == "Append Andorra 2")
        an = next(q for q in pl2["leagues"] if q["name"] == "Append Andorra")
        ok("v2: every Competition / Regulation / Entry row of v1 at its index, the same entry id, club, "
           "competition and place", kept_in_place(rows1, t2))
        ok("... the league put in the middle of the recipe goes after them (competition row %d >= %d)"
           % (comp_index(t2, bos["cid"]), n_c), comp_index(t2, bos["cid"]) >= n_c
           and comp_index(t2, an2["cid"]) >= n_c)
        now = R.rows_of_tables(t2)
        new_e = now["entries"][n_e:]
        top1 = max(e[0] for e in rows1["entries"])
        ok("... new entry ids above v1's highest (%d): %d new entries, %d..%d"
           % (top1, len(new_e), min(e[0] for e in new_e), max(e[0] for e in new_e)),
           new_e and min(e[0] for e in new_e) > top1 and len({e[0] for e in now["entries"]}) == len(now["entries"]))
        ok("... no entry of a new league in a competition of v1",
           not {e[2] for e in new_e} & {c[0] for c in rows1["competitions"]})
        ok("... the league under an old one with no exchange is not linked: the old league's row as v1's",
           any("Append Andorra 2 is not linked below Append Andorra" in l for l in log2)
           and R.crc(reg_row(t2, an["rid"])) == next(r[2] for r in rows1["regulations"] if r[0] == an["rid"])
           and int.from_bytes(reg_row(t2, an2["rid"])[4:6], "little") == 0)
        ok("... the plan says so (rows_kept of Append 1: ok, 2 new competitions)", pl2.get("rows_kept", {}).get("ok")
           and pl2["rows_kept"]["of"]["version"] == "Append 1" and pl2["rows_kept"]["new_competitions"] >= 2)
        rep = R.check(rows1, t2[R.TABLES[0]], t2[R.TABLES[1]], t2[R.TABLES[2]], R.team_ids(t1[R.TEAM]))
        ok("... rowkeep.check of v1 against v2: careers go on, nothing moved (%s)" % R.summary(rep),
           rep["ok"] and not any(rep["moved"].values()) and len(rep["new_clubs_new"]) == 20)

        # id_tables of another version: the Build stops
        try:
            build(a, base, dict(r2, id_tables=os.path.join(TMP, "nothing.zip")))
            ok("id_tables that cannot be read: Build stops", False)
        except B.BuildError as e:
            ok("id_tables that cannot be read: Build stops (%s)" % str(e)[:80], "id_tables" in str(e))
        zx = os.path.join(TMP, "other-version.zip")
        _rewrite_ledger(z1, zx, number=7)
        try:
            build(a, base, dict(r2, id_tables=zx))
            ok("id_tables of another version: Build stops", False)
        except B.BuildError as e:
            ok("id_tables of another version: Build stops (%s)" % str(e)[:100], "wrong version" in str(e))
        pl2, log2 = build(a, base, r2t)           # v2 again, as it is shared
        t2 = tables_of(a)

        z2 = os.path.join(TMP, WORLD + "-v2.zip")
        info2 = export(a, "Append 2", z2)
        ok("export v2 after a ledger without rows: careers of Append 1 go on (the Build's rows_kept: %s)"
           % info2["careers"].get("rows"), info2["careers"]["continue_from"] == "Append 1"
           and (info2["careers"].get("rows") or {}).get("ok"))
        c = C.check(z1, z2)
        ok("check_update_ids v1 -> v2: the competitions pass; it fails only on the 20 new clubs that play only in "
           "the new leagues (%s)" % c["fail"], len(c["fail"]) == 1
           and c["fail"][0].startswith("Team.bin: 20 new clubs play only in competitions prev does not have"))

        # ---- the player: v1 installed, v2 is an Update that names the new leagues
        p = T.sider(os.path.join(TMP, "player"))
        install(p, look(p, z1), None)
        parts, head, plain = page_texts(p, z2)
        up = next(x for x in parts if x.kind == "world").update
        ok("Install v2 over v1: an Update (%s)" % {k: up.get(k) for k in ("ok", "why", "new_leagues", "new_cups", "rows")},
           up["ok"] and up["new_leagues"] == 2 and up["rows"]["ok"])
        ok("... the summary says the new leagues come only in a new Master League (%r)" % plain,
           "2 new league(s) and cup(s) appear only in a new Master League; your careers go on without them." in plain)
        install(p, parts, up)

        # ---- v3: two clubs new to the world in a league v2 has
        r3 = json.loads(json.dumps(r2))
        r3["leagues"][2]["club_names"] += ["Andor New 1", "Andor New 2"]
        r3["leagues"][2]["clubs"] += 2
        pl3, log3 = build(a, base, r3)
        t3 = tables_of(a)
        ok("v3: Build says the new clubs in Append Andorra break careers of Append 2",
           any("warning: rows:" in l and "clubs new to the world" in l and "do not go on" in l for l in log3)
           and pl3["rows_kept"]["ok"] is False and pl3["rows_kept"]["new_clubs_old"] == 2)
        ok("... from Append 2's own ledger now", any("keep their places (from its id ledger)" in l for l in log3))
        z3 = os.path.join(TMP, WORLD + "-v3.zip")
        info3 = export(a, "Append 3", z3)
        ok("export v3: careers of Append 2 do not go on (%s)" % info3["careers"].get("rows"),
           info3["careers"]["continue_from"] is None and info3["careers"]["rows"]["ok"] is False)
        parts, head, plain = page_texts(p, z3)
        up = next(x for x in parts if x.kind == "world").update
        ok("Install v3 over v2: Replace, why rows (%s / %r)" % (up.get("why"), head),
           not up["ok"] and up["why"] == "rows" and "careers do not go on" in head
           and "a club new to the world" in plain and "taken out first" in plain)
        c = C.check(z2, z3)
        ok("check_update_ids v2 -> v3: FAIL, 2 new clubs in a competition prev has (%s)" % c["fail"],
           c["result"] == "FAIL" and any("2 new clubs play in competitions prev has" in f for f in c["fail"]))

        # ---- rows from the world in the game (installed from the zip, not built again)
        led2 = D.load(os.path.join(p, "livecpk", WORLD, D.LEDGER), WORLD)
        bare = dict(led2)
        bare.pop(D.ROWS_KEY)
        rows, teams, where = R.prev_rows(bare, None, os.path.join(p, "livecpk", WORLD))
        ok("prev_rows: a world installed from the zip of the version followed gives its rows",
           rows == led2[D.ROWS_KEY] and where == os.path.join(p, "livecpk", WORLD) and teams)
        notes = []
        other = dict(bare, number=99)
        ok("... not of another version (a note, no rows)", R.prev_rows(other, None, os.path.join(p, "livecpk", WORLD), notes)
           == (None, None, None) and notes and "left out" in notes[0])
        print("%d cases passed" % N)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)


def _rewrite_ledger(src, dst, **change):
    """a copy of zip src whose ledger says another version (number)"""
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
        for m in zi.infolist():
            data = zi.read(m)
            if m.filename.endswith(D.LEDGER):
                led = json.loads(data)
                led.update(change)
                data = json.dumps(led).encode()
            zo.writestr(m, data)


if __name__ == "__main__":
    args = sys.argv[1:]
    rev = None
    if "--against" in args:
        i = args.index("--against")
        rev = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(__doc__)
        sys.exit(2)
    main(args[0], rev)
