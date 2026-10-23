r"""python test_unipar_data.py -- Unpack the game's tables takes the kits file (UniformParameter.bin)
from the game's Data\*.cpk when download\ has none, the download's one still over it, and tables
unpacked by 0.2.4 without that file count as stale (B153: FL26 1.0 without the game's updates,
Build drew no kit: "the game's UniformParameter.bin was not unpacked"). With your own tables over
the game's (Settings > Use another tables folder) Build finds the kits file beside them (B143).
The archives are faked: cpkread.names and cpkread.extract are replaced, nothing of the game is read."""
import json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpkread
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


TEAM = "common/etc/pesdb/Team.bin"


def fake(game, archives):
    """archives: {path under the game: {file in the cpk: bytes}}"""
    for rel in archives:
        p = os.path.join(game, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(b"CPK ")
    by = {os.path.normcase(os.path.abspath(os.path.join(game, rel))): files for rel, files in archives.items()}

    def names(path):
        return list(by[os.path.normcase(os.path.abspath(path))])

    def extract(path, out, parts=(), log=None):
        n = 0
        for f, data in by[os.path.normcase(os.path.abspath(path))].items():
            if parts and not any(p in f for p in parts):
                continue
            op = os.path.join(out, f.replace("/", os.sep))
            os.makedirs(os.path.dirname(op), exist_ok=True)
            open(op, "wb").write(data)
            n += 1
        return n
    cpkread.names, cpkread.extract = names, extract


def unipar(out):
    p = os.path.join(out, B.UNIPAR.replace("/", os.sep))
    return open(p, "rb").read() if os.path.exists(p) else None


def main():
    root = tempfile.mkdtemp(prefix="fl26unipar-")
    keep = cpkread.names, cpkread.extract
    try:
        # FL26 1.0: the tables in download\, the kits file only in Data\
        game, out = os.path.join(root, "g10"), os.path.join(root, "t10")
        fake(game, {"download/data_s2526.cpk": {TEAM: b"team"},
                    "Data/dt30_g4.cpk": {"common/x/y.bin": b"-"},
                    "Data/dt34_g4.cpk": {B.UNIPAR: b"base kits"}})
        B.unpack_tables(game, out, log=lambda *a: None)
        ok("FL26 1.0: the kits file comes from Data/dt34_g4.cpk", unipar(out) == b"base kits")
        rec = json.load(open(os.path.join(out, B.UNPACKED), encoding="utf-8"))
        ok("the unpack says it found the kits file", rec.get(B.UNIPAR_SEEN) == [1, 0])
        ok("and the tables are not stale", B.tables_stale(game, out) is None)

        # the game's update brings its own kits file: that one goes over the base one
        game, out = os.path.join(root, "g22"), os.path.join(root, "t22")
        fake(game, {"download/data_s2526.cpk": {TEAM: b"team"},
                    "download/data_s2526c.cpk": {B.UNIPAR: b"update kits"},
                    "Data/dt34_g4.cpk": {B.UNIPAR: b"base kits"}})
        B.unpack_tables(game, out, log=lambda *a: None)
        ok("an updated game: the update's kits file wins", unipar(out) == b"update kits")

        # 0.2.4 unpacked FL26 1.0: no kits file and no word of it in fl26-unpacked.json
        game, out = os.path.join(root, "g10"), os.path.join(root, "t10")
        rec.pop(B.UNIPAR_SEEN)
        json.dump(rec, open(os.path.join(out, B.UNPACKED), "w", encoding="utf-8"))
        os.remove(os.path.join(out, B.UNIPAR.replace("/", os.sep)))
        why = B.tables_stale(game, out)
        ok("tables of 0.2.4 without the kits file are stale: %s" % why,
           why == "unpacked without the game's kits file (UniformParameter.bin)")
        from modstudio import i18n
        said = {}
        for code in ("hr", "es", "fr", "pt"):
            i18n.set_language(code)
            said[code] = i18n.tr(why)
        i18n.set_language("en")
        ok("Build says why in every language: %s" % said["hr"], all(t != why for t in said.values()))

        # a game with no kits file anywhere: one unpack, then never asked again
        game, out = os.path.join(root, "gnone"), os.path.join(root, "tnone")
        fake(game, {"download/data_s2526.cpk": {TEAM: b"team"}, "Data/dt30_g4.cpk": {"a/b.bin": b"-"}})
        B.unpack_tables(game, out, log=lambda *a: None)
        rec = json.load(open(os.path.join(out, B.UNPACKED), encoding="utf-8"))
        ok("no kits file anywhere: recorded as not found", rec.get(B.UNIPAR_SEEN) == [0, 0])
        ok("and not stale after that unpack", B.tables_stale(game, out) is None)

        # B143: your own tables (only Team.bin) over the game's unpacked ones
        from modstudio import project
        tables = os.path.join(root, "tables")
        for rel, data in ((TEAM, b"game team"), ("common/etc/pesdb/CompetitionRegulation.bin", b"reg"),
                          (B.UNIPAR, b"game kits")):
            f = os.path.join(tables, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(f), exist_ok=True)
            open(f, "wb").write(data)
        ok("the game's unpacked tables: their kits file is found",
           B.kits_file(os.path.join(tables, "common", "etc", "pesdb")) is not None)
        P = project.Project.__new__(project.Project)
        P.tables_dir = lambda: tables
        mine = os.path.join(root, "mine", "pesdb")
        os.makedirs(mine)
        open(os.path.join(mine, "Team.bin"), "wb").write(b"my team")
        base = P._tables_of(os.path.join(root, "mine"))
        k = B.kits_file(base)
        ok("your own tables over the game's: Build finds the game's kits file beside them (%s)" % base,
           k is not None and open(k, "rb").read() == b"game kits"
           and open(os.path.join(base, "Team.bin"), "rb").read() == b"my team")
        f = os.path.join(root, "mine", B.UNIPAR.replace("/", os.sep))
        os.makedirs(os.path.dirname(f))
        open(f, "wb").write(b"my kits, longer")
        k = B.kits_file(P._tables_of(os.path.join(root, "mine")))
        ok("a tables folder with a kits file of its own: that one", open(k, "rb").read() == b"my kits, longer")
        ok("no kits file anywhere: None (Build says to unpack)",
           B.kits_file(os.path.join(root, "gnone", "download")) is None)

        # B218 (Aleperfe87 23.10.): a whole database mod in livecpk as the tables: read where it is,
        # no kits file beside it; Build falls back on the game's unpacked one, else on a mod's
        game = os.path.join(root, "g218")
        live = os.path.join(game, "SiderAddons", "livecpk")
        db = os.path.join(live, "UML_Database", "common", "etc", "pesdb")
        os.makedirs(db)
        for n in ("Team.bin", "CompetitionRegulation.bin"):
            open(os.path.join(db, n), "wb").write(b"uml")
        f = os.path.join(live, "UML_Kits", B.UNIPAR.replace("/", os.sep))
        os.makedirs(os.path.dirname(f))
        open(f, "wb").write(b"uml kits")
        open(os.path.join(game, "SiderAddons", "sider.ini"), "w").write(
            '[sider]\ncpk.root = "livecpk\\UML_Kits"\ncpk.root = "livecpk\\UML_Database"\n')
        base = P._tables_of(os.path.join(live, "UML_Database"))
        ok("a whole database mod: its own folder is the tables", os.path.samefile(base, db))
        ok("and it has no kits file beside it", B.kits_file(base) is None)
        keep_fb = list(B.KITS_FALLBACK)
        try:
            B.KITS_FALLBACK[:] = [os.path.join(tables, B.UNIPAR.replace("/", os.sep))]
            k = B.kits_for(base, game)
            ok("Build draws on the game's unpacked kits file", k and open(k, "rb").read() == b"game kits")
            B.KITS_FALLBACK[:] = [os.path.join(root, "nothing", B.UNIPAR.replace("/", os.sep))]
            k = B.kits_for(base, game)
            ok("none unpacked: on the kits file of the mod sider.ini serves (%s)" % k,
               k and open(k, "rb").read() == b"uml kits")
            ok("no game folder and nothing unpacked: None (Build warns)", B.kits_for(base, None) is None)
            ok("kits beside the tables still come first",
               open(B.kits_for(os.path.join(tables, "common", "etc", "pesdb"), game), "rb").read() == b"game kits")
        finally:
            B.KITS_FALLBACK[:] = keep_fb
    finally:
        cpkread.names, cpkread.extract = keep
        shutil.rmtree(root, ignore_errors=True)
    print("1..%d" % N)


if __name__ == "__main__":
    main()
