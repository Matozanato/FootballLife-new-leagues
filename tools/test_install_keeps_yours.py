"""python tools/test_install_keeps_yours.py

pop1806, 14.11.2026: "installing beta 2 over beta 1 deleted what I had set up". A newer zip of a
ready world takes the older one out first (installer.replace_world), and with it went the whole
livecpk\\<world> folder: a file the person had put there, and a file of the world they had changed
(a kit, a crest), were deleted without a word.

Now nothing of the person's is deleted (installer.keep_yours): before the older version goes out,
  - a file of livecpk\\<world> the install did not bring is MOVED to ModStudio\\kept\\<world>-<time>;
  - a file the install brought and that was changed since is COPIED there;
the same folders under it as they had. The new version still goes in clean.

Offline: a temporary Sider folder, no game, no window.
"""
import os, shutil, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import installer as I
from modstudio.siderini import SiderIni
import test_world_share as T

WORLD = T.WORLD
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def read(p):
    """the file's text; None when it is not there (a check fails, not the test)"""
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def later(p, seconds=120):
    """as if the person changed the file two minutes after the install"""
    t = time.time() + seconds
    os.utime(p, (t, t))


def older(p, days=30):
    """B487: as if a file of another pack, a month old, was copied over it (a copy keeps its time)"""
    t = time.time() - days * 86400
    os.utime(p, (t, t))


def files_under(d):
    return sorted(os.path.relpath(os.path.join(r, f), d).replace("\\", "/") for r, _d, fs in os.walk(d) for f in fs)


def main():
    tmp = tempfile.mkdtemp(prefix="fl26_keep_")
    try:
        # the PC that built the world: a kit and a scoreboard of its own go into the zip
        a = T.sider(os.path.join(tmp, "a"))
        T.put(os.path.join(a, "livecpk", WORLD, I.WORLD_FILE), T.TEXT)
        T.put(os.path.join(a, "livecpk", WORLD, "common", "etc", "pesdb", "Team.bin"), "team v1")
        T.put(os.path.join(a, "livecpk", WORLD, "common", "crest", "e_072001.ftex"), "crest v1")
        T.put(os.path.join(a, "livecpk", WORLD, ".modstudio"), "x")
        for k in (1, 2, 3):                                # B487: faces of the world's new players
            T.put(os.path.join(a, "livecpk", WORLD, "common", "faces", "f_%d.bin" % k), "face %d v1" % k)
        T.put(os.path.join(a, "content", "kit-server", "map.txt"),
              '72001, "%s\\L One\\Club A"   %s L One/0 made\n' % (WORLD, I.OUR_LINE))
        T.put(os.path.join(a, "content", "kit-server", WORLD, "L One", "Club A", "p1", "u0001p1.ftex"), "kit v1")
        # lbservers' cache of the kits' stamps (lbservers.INDEX): Build writes it, the zip carries it
        T.put(os.path.join(a, "content", "kit-server", WORLD, "kitmaker-index.json"), "{}")
        z1 = os.path.join(tmp, WORLD + "-v1.zip")
        I.export_world(a, WORLD, z1)
        T.put(os.path.join(a, "livecpk", WORLD, "common", "etc", "pesdb", "Team.bin"), "team v2")
        T.put(os.path.join(a, "livecpk", WORLD, "common", "crest", "e_072001.ftex"), "crest v2")
        T.put(os.path.join(a, "content", "kit-server", WORLD, "L One", "Club A", "p1", "u0001p1.ftex"), "kit v2")
        z2 = os.path.join(tmp, WORLD + "-v2.zip")
        I.export_world(a, WORLD, z2)

        # ---- a player's PC: v1 installed, nothing touched, v2 over it ----
        b = T.sider(os.path.join(tmp, "b"))
        g = T.Game(b)
        rec1, ini = T.install(b, z1)
        ok("the install record says when the install was done", I._rec_time(rec1.get("done")) is not None)
        # B487: every file it copied is stamped -- size, modified time, and the crc32 the zip gave
        import zlib
        stamps = I.stamps_of(b, rec1)
        copied = [r for r in rec1["created"] if os.path.basename(r) != ".modstudio"]
        ok("a new record stamps every file it copied", copied and all(stamps.get(r) for r in copied))
        sp = I.stamps_path(b, rec1)
        ok("the stamps are beside installed.json (ModStudio\\stamps), not in it",
           sp and os.path.isfile(sp) and os.path.dirname(sp) == os.path.join(I.home(b), I.STAMPS)
           and all(isinstance(r.get("stamps"), str) for r in I.records(b)))
        face = os.path.join(b, "livecpk", WORLD, "common", "faces", "f_1.bin")
        st = os.stat(face)
        with open(face, "rb") as f:
            crc = zlib.crc32(f.read())
        ok("a stamp is the file's size, its time and the zip's crc32 of it",
           stamps[os.path.relpath(face, b)] == (st.st_size, st.st_mtime_ns, crc))
        ok("an old record has no stamps: none is read", I._stamp(None) is None and I._stamp("x y") is None
           and I.stamps_of(b, dict(rec1, stamps=None)) == {} and I.stamps_of(b, dict(rec1, stamps="..\\x")) == {})
        ok("a stamps list that no longer fits the record's files is not read",
           I.stamps_of(b, dict(rec1, created=rec1["created"][:-1])) == {})
        kept = []
        notes = I.replace_world(g, SiderIni.load(os.path.join(b, "sider.ini")), WORLD, kept=kept)
        ok("nothing added, nothing changed: nothing kept, no folder made",
           not notes and kept == [] and not os.path.exists(os.path.join(I.home(b), I.KEPT)))
        ok("the record's stamps went out with it", not os.path.exists(sp))
        ok("and the older world is out, as before", not os.path.exists(os.path.join(b, "livecpk", WORLD)))

        # ---- v1 again; the player adds a file, changes a crest and a kit; v2 over it ----
        rec1, ini = T.install(b, z1)
        mine = os.path.join(b, "livecpk", WORLD, "common", "faces", "my_face.bin")
        T.put(mine, "my own face")
        crest = os.path.join(b, "livecpk", WORLD, "common", "crest", "e_072001.ftex")
        T.put(crest, "my crest")
        later(crest)
        kit = os.path.join(b, "content", "kit-server", WORLD, "L One", "Club A", "p1", "u0001p1.ftex")
        T.put(kit, "my kit")
        later(kit)
        extra_kit = os.path.join(b, "content", "kit-server", WORLD, "L One", "Club A", "p9", "mine.ftex")
        T.put(extra_kit, "my fourth kit")
        # B487 (pop1806 16.11.): faces of another pack copied over the world's keep THEIR time, older
        # than the install: one of another size, one of the same size; one face only touched
        faces = os.path.join(b, "livecpk", WORLD, "common", "faces")
        T.put(os.path.join(faces, "f_1.bin"), "a face of another pack, bigger")
        older(os.path.join(faces, "f_1.bin"))
        T.put(os.path.join(faces, "f_2.bin"), "face 2 v9")
        older(os.path.join(faces, "f_2.bin"))
        later(os.path.join(faces, "f_3.bin"))
        # what Mod Studio writes into the world itself after the install is not "yours"
        T.put(os.path.join(b, "livecpk", WORLD, I.EDITS if hasattr(I, "EDITS") else "fl26stadiums.json"), "{}")
        wf = os.path.join(b, "livecpk", WORLD, I.WORLD_FILE)
        later(wf)
        # 16.11. (E3-4 Z2): the Switch on after the install writes the kits' stamp cache again; it was
        # kept as "changed by you" and counted in the banner's files
        import lbservers
        index = os.path.join(b, "content", "kit-server", WORLD, lbservers.INDEX)
        ok("the zip brought the stamp cache, and the install record has it",
           os.path.isfile(index) and os.path.relpath(index, b) in rec1["created"])
        T.put(index, '{"L One\\\\Club A\\\\kitmaker.txt": [1, 2, ["a", "b", "c", "d"]]}')
        later(index)
        ok("kitmaker-index.json is Mod Studio's own (NOT_YOURS)", lbservers.INDEX in I.NOT_YOURS)
        kept, log = [], []
        ini = SiderIni.load(os.path.join(b, "sider.ini"))
        notes = I.replace_world(g, ini, WORLD, log=log.append, kept=kept)
        ini.save(backup=False)
        ok("the older version went out without a problem", not notes)
        ok("one world's files were kept, and the caller is told where", len(kept) == 1 and kept[0][0] == WORLD
           and os.path.isdir(kept[0][1]) and kept[0][1].startswith(os.path.join(I.home(b), I.KEPT)))
        where = kept[0][1]
        ok("the file the player added is there, in its own folder",
           read(os.path.join(where, "livecpk", WORLD, "common", "faces", "my_face.bin")) == "my own face")
        ok("the crest the player changed is there, as the player made it",
           read(os.path.join(where, "livecpk", WORLD, "common", "crest", "e_072001.ftex")) == "my crest")
        ok("the kit the player changed (content\\kit-server) too",
           read(os.path.join(where, "content", "kit-server", WORLD, "L One", "Club A", "p1", "u0001p1.ftex")) == "my kit")
        ok("B487: a face copied over with an OLD time is kept, as the player put it",
           read(os.path.join(where, "livecpk", WORLD, "common", "faces", "f_1.bin")) == "a face of another pack, bigger")
        ok("B487: and one of the same size too (its bytes are not the zip's)",
           read(os.path.join(where, "livecpk", WORLD, "common", "faces", "f_2.bin")) == "face 2 v9")
        ok("B487: a face only touched (the same bytes) is not kept",
           not os.path.exists(os.path.join(where, "livecpk", WORLD, "common", "faces", "f_3.bin")))
        ok("counted: 1 added, 4 changed", kept[0][2:] == (1, 4))
        ok("nothing else was copied (the world's own files, Mod Studio's own)",
           files_under(where) == sorted(["livecpk/%s/common/faces/my_face.bin" % WORLD,
                                         "livecpk/%s/common/crest/e_072001.ftex" % WORLD,
                                         "livecpk/%s/common/faces/f_1.bin" % WORLD,
                                         "livecpk/%s/common/faces/f_2.bin" % WORLD,
                                         "content/kit-server/%s/L One/Club A/p1/u0001p1.ftex" % WORLD]))
        ok("Z2: the stamp cache Mod Studio wrote again is not kept, nor counted",
           not os.path.exists(os.path.join(where, "content", "kit-server", WORLD, lbservers.INDEX)))
        ok("the log says it", any("kept in" in t for t in log))
        ok("the older world's folder is gone: the new version goes in clean",
           not os.path.exists(os.path.join(b, "livecpk", WORLD)))
        ok("a kit folder the player added beside the world's kits was never touched", read(extra_kit) == "my fourth kit")
        rec2, ini = T.install(b, z2)
        ok("the new version is in, with its own files",
           read(os.path.join(b, "livecpk", WORLD, "common", "etc", "pesdb", "Team.bin")) == "team v2"
           and read(crest) == "crest v2" and read(kit) == "kit v2" and not os.path.exists(mine))
        ok("one record of the world, and it is a ready world", len(I.installed_as(b, WORLD)) == 1 and I.ready_world(g, WORLD))

        # ---- records of an older Mod Studio, on players' PCs today: no stamps (beta 4: "done"; beta 3
        # and older: neither). B487: a changed file was kept only with "done" and a later time ----
        for what, drop in (("beta 4 (done, no stamps)", ("stamps",)), ("beta 3 (no done, no stamps)", ("stamps", "done"))):
            c = T.sider(os.path.join(tmp, "c" + str(len(drop))))
            gc = T.Game(c)
            rec, ini = T.install(c, z1)
            rows = I.records(c)
            for r in rows:
                for k in drop:
                    r.pop(k, None)
            I._save(c, rows)
            wc = os.path.join(c, "livecpk", WORLD)
            T.put(os.path.join(wc, "mine.txt"), "mine")
            later(os.path.join(wc, "common", "crest", "e_072001.ftex"))
            T.put(os.path.join(wc, "common", "faces", "f_1.bin"), "face 1 v9")     # the same size, an old time
            older(os.path.join(wc, "common", "faces", "f_1.bin"))
            kept = []
            I.replace_world(gc, SiderIni.load(os.path.join(c, "sider.ini")), WORLD, kept=kept)
            got = files_under(kept[0][1]) if kept else []
            ok("%s: the added file kept, the crest changed later kept, the face copied over with an old time kept"
               % what, len(kept) == 1 and kept[0][2:] == (1, 2) and read(os.path.join(kept[0][1], "livecpk", WORLD, "mine.txt")) == "mine"
               and read(os.path.join(kept[0][1], "livecpk", WORLD, "common", "faces", "f_1.bin")) == "face 1 v9")
            ok("%s: the files nobody touched are not kept" % what,
               got == sorted(["livecpk/%s/mine.txt" % WORLD, "livecpk/%s/common/crest/e_072001.ftex" % WORLD,
                              "livecpk/%s/common/faces/f_1.bin" % WORLD]))

        # ---- the unpack's run of times (an old record's own files) ----
        run = I.unpack_run([1000.0, 1001.5, 1003, 1290, 500, 50, 2000], start=1300)
        ok("unpack_run: the longest run with no gap over RUN_GAP, none after the start",
           run == (1000.0, 1290))
        ok("unpack_run: of two as long, the later", I.unpack_run([10, 11, 5000, 5001]) == (5000, 5001))
        ok("unpack_run: no times, no run", I.unpack_run([]) is None and I.unpack_run([9999], start=10) is None)

        # ---- a folder installed (no zip, no crc32): a file only touched is kept, as it cannot be told ----
        e = T.sider(os.path.join(tmp, "e"))
        work = os.path.join(tmp, "unz")
        I.unpack(z1, work)
        I._UNPACKED.clear()                                 # as if the folder were the player's own
        parts = I.detect(work, "mod")
        inst = I.Installer(T.Game(e), SiderIni.load(os.path.join(e, "sider.ini")), "folder", replace_lines=True)
        rec = inst.run(parts)
        we = os.path.join(e, "livecpk", WORLD)
        ok("a folder's install stamps size and time, no crc32",
           I.stamps_of(e, rec)[os.path.relpath(os.path.join(we, "common", "faces", "f_3.bin"), e)][2] is None)
        later(os.path.join(we, "common", "faces", "f_3.bin"))
        kept = []
        I.replace_world(T.Game(e), SiderIni.load(os.path.join(e, "sider.ini")), WORLD, kept=kept)
        ok("a folder's install: the touched file is kept, the others are not",
           kept and files_under(kept[0][1]) == ["livecpk/%s/common/faces/f_3.bin" % WORLD])

        # ---- Remove the mod is not a new version: it keeps nothing, deletes only its own files ----
        d = T.sider(os.path.join(tmp, "d"))
        rec, ini = T.install(d, z1)
        T.put(os.path.join(d, "livecpk", WORLD, "mine.txt"), "mine")
        I.uninstall(T.Game(d), ini, rec)
        ok("Remove the mod leaves a file the player added where it is",
           read(os.path.join(d, "livecpk", WORLD, "mine.txt")) == "mine")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)
    print("all passed")


if __name__ == "__main__":
    os.environ["FL26_LEDGER_STORE"] = tempfile.mkdtemp(prefix="fl26ledgers-")   # review 3, 18.11.2026: never the real history
    main()
