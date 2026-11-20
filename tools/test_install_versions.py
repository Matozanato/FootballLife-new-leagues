"""python tools/test_install_versions.py

E3-4 UI test of Import your world (16.11.2026), two things it said wrong:

Z3. A world zip OLDER than the installed world of the same name was called "a newer version of the
    world ... you have": Mod Studio did not compare versions at all. Now a world zip's time is when
    it was made (installer.world_made: export_world writes fl26worldpack.json into it at that
    moment), the install record keeps it ("made"), and installer.world_version tells the next zip
    of that world newer / older / the same; when it cannot be told (a folder, a record from before
    this) the headline says "another version".

Z1. Installing a newer version over an older one: the banner saying where the person's own files
    were kept (ModStudio\\kept\\<world>-<time>) was replaced ~40 s later by final_check's "ready to
    play", and the Ready to play box did not say it. Now the last banner and the box say it too.

Offline: a temporary Sider folder, no game; the page's methods run on a stand-in, no window.
"""
import os, shutil, sys, tempfile, zipfile
from types import SimpleNamespace

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


def retimed(src, dst, date_time):
    """a copy of zip src with fl26worldpack.json dated date_time: the same world, made at another time"""
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
        for m in zi.infolist():
            data = zi.read(m)
            if m.filename == I.WORLD_INFO:
                m = zipfile.ZipInfo(m.filename, date_time=date_time)
                m.compress_type = zipfile.ZIP_DEFLATED
            zo.writestr(m, data)
    return dst


def parts_of(src, work):
    """what Import your world's look() finds in src, with the zip's time on the world as it puts it"""
    parts = I.detect(I.unpack(src, work), "mod")
    for p in parts:
        if p.kind == "world":
            p.made = I.world_made(src)
    return parts


def install(sd, src, tmp):
    work = tempfile.mkdtemp(prefix="iv_", dir=tmp)
    parts = parts_of(src, work)
    ini = SiderIni.load(os.path.join(sd, "sider.ini"))
    rec = I.Installer(T.Game(sd), ini, "shared", replace_lines=True).run(parts)
    ini.save(backup=False)
    return rec


class Banner:
    def __init__(self):
        self.said, self.text = [], ""

    def say(self, text, kind="warn"):
        self.said.append((kind, text))

    def setText(self, t):
        self.text = t


def main():
    from modstudio.pages import install as PI
    tmp = tempfile.mkdtemp(prefix="fl26_iv_")
    try:
        a = T.sider(os.path.join(tmp, "a"))
        T.put(os.path.join(a, "livecpk", WORLD, I.WORLD_FILE), T.TEXT)
        T.put(os.path.join(a, "livecpk", WORLD, "common", "etc", "pesdb", "Team.bin"), "x")
        z = os.path.join(tmp, WORLD + ".zip")
        I.export_world(a, WORLD, z)
        made = I.world_made(z)
        with zipfile.ZipFile(z) as zz:
            dt = zz.getinfo(I.WORLD_INFO).date_time
        ok("Z3: a world zip's time is when export_world wrote it (%s)" % made,
           made == "%04d%02d%02d-%02d%02d%02d" % dt and len(made) == 15)
        beta1 = retimed(z, os.path.join(tmp, WORLD + "-beta1.zip"), (2026, 11, 8, 10, 0, 0))
        beta2 = retimed(z, os.path.join(tmp, WORLD + "-beta2.zip"), (2026, 11, 12, 18, 30, 0))
        ok("Z3: the two copies tell their times", I.world_made(beta1) == "20261108-100000"
           and I.world_made(beta2) == "20261112-183000")
        bare = os.path.join(tmp, "bare.zip")
        with zipfile.ZipFile(bare, "w") as zz:
            zz.writestr("SiderAddons/livecpk/%s/%s" % (WORLD, I.WORLD_FILE), T.TEXT)
        ok("Z3: no time for a folder, a zip without fl26worldpack.json, a file that is not there",
           I.world_made(os.path.join(a, "livecpk", WORLD)) is None and I.world_made(bare) is None
           and I.world_made(os.path.join(tmp, "nowhere.zip")) is None)

        # ---- a player's PC: beta 2 in the game ----
        b = T.sider(os.path.join(tmp, "b"))
        g = T.Game(b)
        ok("Z3: nothing installed: nothing to compare", I.world_version(b, WORLD, "20261108-100000") is None)
        rec = install(b, beta2, tmp)
        ok("Z3: the install record keeps the zip's time", rec.get("made") == "20261112-183000"
           and I.installed_as(b, WORLD)[-1].get("made") == "20261112-183000")
        ok("Z3: beta 1 is older, beta 2 the same, a later one newer, no time: cannot be told",
           I.world_version(b, WORLD, "20261108-100000") == "older"
           and I.world_version(b, WORLD, "20261112-183000") == "same"
           and I.world_version(b, WORLD, "20261115-090000") == "newer"
           and I.world_version(b, WORLD, None) is None)

        # the page's headline, on a stand-in for the page
        page = SimpleNamespace(app=SimpleNamespace(game=g), src=None)

        def headline(src):
            page.src = src
            return PI.Install.headline(page, parts_of(src, tempfile.mkdtemp(prefix="iv_", dir=tmp)))
        h1 = headline(beta1)
        ok("Z3: beta 1 over beta 2 is an older version, not a newer one: %r" % h1,
           h1 == "%s: an older version of the world %s than the one you have" % (os.path.basename(beta1), WORLD))
        h2 = headline(beta2)
        ok("Z3: beta 2 again: the same version: %r" % h2,
           h2 == "%s: the same version of the world %s you have" % (os.path.basename(beta2), WORLD))
        beta3 = retimed(z, os.path.join(tmp, WORLD + "-beta3.zip"), (2026, 11, 16, 7, 0, 0))
        h3 = headline(beta3)
        ok("Z3: beta 3: a newer version: %r" % h3,
           h3 == "%s: a newer version of the world %s you have" % (os.path.basename(beta3), WORLD))
        from modstudio import i18n
        try:
            i18n.set_language("hr")
            h7 = headline(beta1)
            ok("Z3: and in Croatian: %r" % h7,
               h7 == "%s: starija verzija svijeta %s od one koju imaš" % (os.path.basename(beta1), WORLD))
        finally:
            i18n.set_language("en")
        unpacked = os.path.join(tmp, "unpacked")
        with zipfile.ZipFile(beta1) as zz:
            zz.extractall(unpacked)
        h4 = headline(unpacked)
        ok("Z3: the same world from a folder (no zip time): another version: %r" % h4,
           h4 == "%s: another version of the world %s you have" % ("unpacked", WORLD))
        rows = I.records(b)
        for r in rows:
            r.pop("made", None)
        I._save(b, rows)
        h5 = headline(beta3)
        ok("Z3: installed by a Mod Studio that kept no time: another version: %r" % h5,
           h5 == "%s: another version of the world %s you have" % (os.path.basename(beta3), WORLD))
        c = T.sider(os.path.join(tmp, "c"))
        page.app.game = T.Game(c)
        h6 = headline(beta1)
        ok("Z3: not installed: a ready world to play: %r" % h6,
           h6 == "%s: a ready world to play (%s)" % (os.path.basename(beta1), WORLD))

        # ---- Z1: what was kept, and where, stays in the last banner and in the Ready to play box ----
        folder = os.path.join(I.home(b), I.KEPT, WORLD + "-20261116-063921")
        note = PI.Install.kept_text([(WORLD, folder, 1, 1)])
        ok("Z1: the note names the world, the count and the folder: %r" % note,
           note.startswith(WORLD + ": 2 file(s)") and note.endswith("kept in " + folder))
        ok("Z1: nothing kept: no note", PI.Install.kept_text([]) == "")
        boxes = []
        real_info = PI.info
        PI.info = lambda parent, title, text: boxes.append((title, text))
        try:
            def checked(kept_note, rows):
                ban = Banner()
                fake = SimpleNamespace(kept_note=kept_note, ready_rows=(WORLD, rows), say=ban.say, what=ban,
                                       edit_check=lambda w, update=False: None, show_fix=lambda: boxes.append(("fix", fake.fix_text)))
                del boxes[:]
                PI.Install.final_check(fake, WORLD)
                return fake, ban
            fake, ban = checked(note, [("ok", "the world's modules are in the game")])
            ok("Z1: ready to play: the last banner still says where the files are: %r" % ban.said,
               len(ban.said) == 1 and ban.said[0][0] == "ok" and "is ready to play" in ban.said[0][1]
               and folder in ban.said[0][1])
            ok("Z1: and the Ready to play box does: %r" % boxes,
               len(boxes) == 1 and boxes[0][0] == "Ready to play" and boxes[0][1].endswith(note)
               and "NEW Master League" in boxes[0][1])
            ok("Z1: said once: the note is spent", fake.kept_note == "")
            fake, ban = checked("", [("ok", "the world's modules are in the game")])
            ok("Z1: nothing kept in this install: the box and banner as before",
               folder not in ban.said[0][1] and folder not in boxes[0][1] and "kept in" not in boxes[0][1])
            fake, ban = checked(note, [("err", "a module is missing")])
            ok("Z1: not ready yet: the red banner and the list of what to fix say it too",
               ban.said[0][0] == "err" and 'href="fix"' in ban.said[0][1] and folder in ban.said[0][1]
               and boxes == [("fix", fake.fix_text)] and fake.fix_text.endswith(note))
        finally:
            PI.info = real_info
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("1..%d" % N)
    print("all passed")


if __name__ == "__main__":
    os.environ["FL26_LEDGER_STORE"] = tempfile.mkdtemp(prefix="fl26ledgers-")   # review 3, 18.11.2026: never the real history
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
