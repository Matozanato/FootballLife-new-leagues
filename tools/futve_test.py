r"""python futve_test.py --world <built world folder> --game "<game folder>" [--save <folder>]
                        [--dll <fl26swiss.dll>] [--careers <folder>] [--no-fixture]
       python futve_test.py --restore <test folder>
       python futve_test.py --self-test

The sandbox of the in-game tests of a world Mod Studio built. One command per test:

  1. It checks that the game is closed.
  2. It backs up everything the test can modify: the files it installs -- the world's
     fl26world.txt (in livecpk\<world> and in modules), its three Competition*.bin and its
     competition emblems (common\render\symbol\emblemLc), the Táchira-99 Player.bin, the repo's
     fl26swiss.dll (or --dll), fl26swiss.lua, fl26joindll.lua and, for a world with `cine` lines,
     fl26cine.lua -- the game's own logs and caches, ReShade.ini/ReShade.log and sider.ini, and the
     whole save folder (the 2026 folder under Documents\KONAMI -- the Documents folder Windows gives
     the game, OneDrive\Documentos on a Spanish system -- where a career and fl26swiss-state.bin
     are written). It writes manifest.json with every size, mtime and sha256.
  3. It installs them, and the sandbox's own Master League careers (out/futve/careers-<world>/ML*,
     or --careers: at FIN every ML* the session made or changed goes back there, with its progress,
     and leaves the save folder), checks every hash and runs futve_fixture.py --check on the
     installed Player.bin (the 25 stats of the 30 Táchira players must be 99).
  4. It prints the checklist and WAITS. When you have closed the game and the test is over, type
     FIN and Enter: it copies the evidence (logs, new screenshots, manifest) to evidence/ and puts
     absolutely everything back -- files, save folder, logs, caches -- and verifies the result
     against the manifest. ABORTAR restores at once; Ctrl+C restores nothing and prints the
     --restore command.

  --world <folder>          a world as a Build writes it: the livecpk\<world> folder of a Build (a
                            Build into a copy of the game, or the world's own folder), with
                            fl26world.txt and common\etc\pesdb; installed as livecpk\<its name>
  --no-fixture              the world's own Player.bin (no Táchira 99)
  --restore <test folder>   the same restore, non-interactive, for a crash or a Ctrl+C.
  --self-test               builds a fake game/save/world tree in out/futve/tmp, runs the whole
                            snapshot-install-test-evidence-restore round trip and checks the tree
                            comes back byte for byte (nothing of the real game is touched).

Until fase 6 it installed the hand-made worlds of phases 1-5 (futve_world, futve_finals,
futve_calendar, futve_conmebol, futve_logo, futve_cinematics, futve_join); a Build makes all of
that now (docs/developers/fork/futve-playoff.md).

The command is meant to be run by you in your own terminal: it writes to the game folder and to
the save folder, so it is outside the agent's sandbox.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ART = os.path.join(REPO, "out", "futve")
CAREERS = os.path.join(ART, "careers")       # the store of a world: careers-<world> beside it
GAME_PROCS = ("fl_2026.exe", "sider.exe", "fl 2026 start.exe")
CHECKLIST = """
  LIGA FUTVE (receta tools/testdata/regress018/liga_futve.json). Carrera NUEVA con un club de la
  Liga FUTVE. La carrera empieza en agosto: hasta el febrero siguiente la Liga FUTVE no juega.
  Días del año (1 ene = 0). Avanza simulando; para en cada punto y apunta lo que veas.
  1. Primer año: ningún venezolano en la Libertadores (fases 1/2 días 6/13 y 18/25, fase 3 34/41)
     ni en la primera etapa de la Sudamericana (día 40); sus plazas, a clubes de otras ligas
     (sider.log: "first season", "goes to").
  2. ~31 ene (día 30): Supercopa (desde la 2.ª temporada).
  3. Apertura: sábados 44 .. 128. Cuadrangulares 132 .. 151. Final 157, un partido, CON ceremonia
     y la entrada de la final de la Libertadores. Palmarés: "Final del Apertura".
  4. Play-off de la Sudamericana: 144 / 161.
  5. Clausura: 205 .. 289. Cuadrangulares 293 .. 327. Final 335, CON ceremonia.
  6. Final del FUTVE (si no ganó el mismo club ambas): ida 342 SIN ceremonia, vuelta 345 CON ella.
     Palmarés: "Liga FUTVE" sólo para el campeón; nunca "Final del FUTVE".
  7. Copa Venezuela: 69, 97, 125, 174, 230, 251, 286 (las rondas que tenga).
  8. Segundo año, ~20 feb (día 50): Libertadores con el campeón y el mejor de la tabla acumulada
     (grupos), el subcampeón (fase 2) y el siguiente (fase 1); Sudamericana con los perdedores de
     las finales del Apertura y del Clausura y los dos siguientes. Recopa el día 55.
  9. Cierra el juego. Escribe FIN y Enter aquí.
"""


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def list_files(d, pats):
    try:
        names = os.listdir(d)
    except OSError:
        return []
    return sorted(n for n in names
                  if os.path.isfile(os.path.join(d, n)) and any(fnmatch.fnmatch(n.lower(), p.lower()) for p in pats))


def managed_dirs(game):
    sider = os.path.join(game, "SiderAddons")
    return [(sider, ["*.log", "*.cache", "sider.ini", "fl26cer_*.bin"]),   # fl26cer_*: the DLL's ceremony dumps
            (os.path.join(sider, "modules"), ["*.log"]),
            (game, ["ReShade.ini", "ReShade.log"])]


def is_ro(p):
    try:
        return not bool(os.stat(p).st_mode & stat.S_IWRITE)
    except OSError:
        return False


def clear_ro(p):
    """a read-only file is made writable for a copy; its own state is put back on restore"""
    try:
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def set_ro(p, ro):
    try:
        os.chmod(p, stat.S_IREAD if ro else (stat.S_IWRITE | stat.S_IREAD))
    except OSError:
        pass


def game_running(game):
    """the name of a game process (a failed copy is reported as it happens if one is not named)"""
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                             errors="ignore", timeout=30).stdout.lower()
        for n in GAME_PROCS:
            if n in out:
                return n
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def copy_back(src, dest, mtime=None, ro=None):
    if os.path.exists(dest):
        clear_ro(dest)
    shutil.copyfile(src, dest)
    if mtime is not None:
        try:
            os.utime(dest, (mtime, mtime))
        except OSError:
            pass
    if ro is not None:
        set_ro(dest, ro)


def wait_closed(game, ask=True):
    while True:
        r = game_running(game)
        if not r:
            return True
        print("  el juego sigue abierto (%s)." % r)
        if not ask:
            return False
        try:
            input("  ciérralo y pulsa Enter para reintentar (o escribe ABORTAR): ")
        except EOFError:
            return False


def documents_folder():
    """the Documents folder Windows hands the game (FOLDERID_Documents), wherever OneDrive or the
    language put it: OneDrive\\Documentos on a Spanish system. None off Windows or on failure."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        class GUID(ctypes.Structure):
            _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD), ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]
        fid = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
        out = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(out)):
            return None
        path = out.value
        ctypes.windll.ole32.CoTaskMemFree(out)
        return path
    except Exception:
        return None


GAME_SAVE = os.path.join("KONAMI", "eFootball PES 2021 SEASON UPDATE", "2026")


def find_save(args):
    """the 2026 folder the game writes its careers to. 31.10.: it was looked for under
    Documents only, and on Felix's machine (OneDrive\\Documentos) that is another folder with an
    old EDIT file in it -- the sandbox saved and restored the wrong one. Now Windows' own Documents
    folder first; then the usual names, the one whose save folder was written last."""
    if args.save:
        s = os.path.abspath(args.save)
        return os.path.dirname(s) if os.path.basename(s).lower() == "save" else s
    home = os.path.expanduser("~")
    known = documents_folder()
    cands = []
    for base in ([known] if known else []) + [os.path.join(home, d) for d in ("Documents", "Documentos")] + \
                [os.path.join(home, "OneDrive", d) for d in ("Documents", "Documentos")]:
        c = os.path.join(base, GAME_SAVE)
        if os.path.isdir(os.path.join(c, "save")) and c not in cands:
            cands.append(c)
    if not cands:
        return None
    if known and cands[0].startswith(known):
        pick = cands[0]
    else:
        def last_write(c):
            sv = os.path.join(c, "save")
            return max([os.path.getmtime(os.path.join(sv, n)) for n in os.listdir(sv)] or [0])
        pick = max(cands, key=last_write)
    others = [c for c in cands if c != pick]
    if others:
        print("  aviso: hay otra(s) carpeta(s) de partidas que el juego no usa: %s" % "; ".join(others))
    return pick


def world_files(world):
    """the files of a built world the sandbox installs: (path under the world folder, source)"""
    out = [("fl26world.txt", os.path.join(world, "fl26world.txt"))]
    for n in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"):
        out.append(("common/etc/pesdb/" + n, os.path.join(world, "common", "etc", "pesdb", n)))
    emb = os.path.join(world, "common", "render", "symbol", "emblemLc")
    for n in list_files(emb, ["emb_*.png"]):
        out.append(("common/render/symbol/emblemLc/" + n, os.path.join(emb, n)))
    return out


def build_installs(world, game, dll=None, fixture=True, art=ART):
    """what a test of the built world `world` installs: [(path under the game folder, source)]"""
    world = os.path.abspath(world)
    txt = os.path.join(world, "fl26world.txt")
    if not os.path.isfile(txt) or not os.path.isdir(os.path.join(world, "common", "etc", "pesdb")):
        raise SystemExit("%s no es un mundo de un Build (falta fl26world.txt o common\\etc\\pesdb)" % world)
    name = os.path.basename(world.rstrip("/\\"))
    live = "SiderAddons/livecpk/%s/" % name
    sider = os.path.join(REPO, "sider")
    out = [("SiderAddons/modules/fl26swiss.dll", dll or os.path.join(sider, "experimental", "fl26swiss.dll")),
           ("SiderAddons/modules/fl26swiss.lua", os.path.join(sider, "experimental", "fl26swiss.lua")),
           ("SiderAddons/modules/fl26joindll.lua", os.path.join(sider, "fl26joindll.lua")),
           ("SiderAddons/modules/fl26world.txt", txt)]
    out += [(live + rel, src) for rel, src in world_files(world)]
    if fixture:
        out.append((live + "common/etc/pesdb/Player.bin", os.path.join(art, "fixtures", "Player.bin")))
    with open(txt, encoding="utf-8", errors="replace") as f:
        cine = any(l.startswith("cine ") for l in f)
    if cine:
        out.append(("SiderAddons/modules/fl26cine.lua", os.path.join(sider, "experimental", "fl26cine.lua")))
        ini = os.path.join(game, "SiderAddons", "sider.ini")
        try:
            has = "fl26cine" in open(ini, encoding="utf-8", errors="replace").read()
        except OSError:
            has = False
        if not has:
            print("  AVISO: el mundo tiene cinemáticas (líneas cine) y sider.ini no carga fl26cine.lua: "
                  "instala los módulos con Mod Studio antes de la prueba")
    for rel, src in out:
        if not os.path.isfile(src):
            raise SystemExit("falta el artefacto de %s: %s" % (rel, src))
    return out


def snapshot(installs, game, save, backup):
    os.makedirs(backup, exist_ok=True)
    man = {"started": now(), "game": game, "save": save, "backup": backup,
           "install": [], "managed": [], "save_files": [], "save_dirs": [], "scan": {}}
    for rel, src in installs:
        dest = os.path.join(game, rel.replace("/", os.sep))
        e = {"rel": rel, "src": src, "dest": dest, "existed": os.path.isfile(dest)}
        if e["existed"]:
            b = os.path.join(backup, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copy2(dest, b)
            e.update(size=os.path.getsize(dest), mtime=os.path.getmtime(dest), sha256=sha(dest),
                     ro=is_ro(dest), backup=b)
        man["install"].append(e)
    for d, pats in managed_dirs(game):
        for n in list_files(d, pats):
            p = os.path.join(d, n)
            rel = os.path.relpath(p, game).replace(os.sep, "/")
            b = os.path.join(backup, "game", rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copy2(p, b)
            man["managed"].append({"rel": rel, "name": n, "dir": d, "backup": b, "size": os.path.getsize(p),
                                   "mtime": os.path.getmtime(p), "sha256": sha(p), "ro": is_ro(p)})
    for d, _p in managed_dirs(game) + [(game, None)]:
        try:
            for n in os.listdir(d):
                p = os.path.join(d, n)
                if os.path.isfile(p):
                    man["scan"][os.path.relpath(p, game).replace(os.sep, "/")] = [os.path.getsize(p),
                                                                                  int(os.path.getmtime(p) * 1000)]
        except OSError:
            pass
    for root, _dirs, files in os.walk(save):
        man["save_dirs"].append(os.path.relpath(root, save).replace(os.sep, "/"))
        for n in files:
            p = os.path.join(root, n)
            rel = os.path.relpath(p, save).replace(os.sep, "/")
            b = os.path.join(backup, "save", rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copy2(p, b)
            man["save_files"].append({"rel": rel, "backup": b, "size": os.path.getsize(p),
                                      "mtime": os.path.getmtime(p), "sha256": sha(p), "ro": is_ro(p)})
    return man


def install(installs, game):
    for rel, src in installs:
        dest = os.path.join(game, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest):
            clear_ro(dest)
        shutil.copyfile(src, dest)
        if sha(dest) != sha(src):
            raise SystemExit("la copia de %s no coincide con el artefacto" % rel)
        print("  instalado %s" % rel)


def fixture_check(game, name="_FL26MyWorld"):
    world = os.path.join(game, "SiderAddons", "livecpk", name, "common", "etc", "pesdb")
    r = subprocess.run([sys.executable, os.path.join(HERE, "futve_fixture.py"), "--check",
                        os.path.join(world, "Player.bin"), "--assignments",
                        os.path.join(world, "PlayerAssignment.bin")],
                       capture_output=True, text=True, errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


def is_career(rel):
    return os.path.basename(rel).upper().startswith("ML")


def careers_install(store, save):
    """31.10.: the sandbox's own Master League careers. They live in out/futve/careers, the start
    of a test puts them in the save folder (the snapshot has the user's own first, so a career of
    his with the same name comes back at FIN), FIN takes them out again."""
    n = 0
    if store and os.path.isdir(store):
        for name in sorted(os.listdir(store)):
            src = os.path.join(store, name)
            if os.path.isfile(src) and is_career(name):
                dst = os.path.join(save, "save", name)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.isfile(dst):
                    clear_ro(dst)
                shutil.copy2(src, dst)
                n += 1
    return n


def careers_keep(man, save):
    """before the restore: every ML* the test session made or changed (not the user's own, which
    the snapshot has unchanged) goes to the sandbox's store, replacing the copy there. The restore
    then removes it from the save folder; the next test puts it back with its progress."""
    store = man.get("careers")
    if not store:
        return []
    snap = {f["rel"]: f["sha256"] for f in man["save_files"]}
    kept = []
    sdir = os.path.join(save, "save")
    if os.path.isdir(sdir):
        for name in sorted(os.listdir(sdir)):
            p = os.path.join(sdir, name)
            rel = "save/" + name
            if os.path.isfile(p) and is_career(name) and snap.get(rel) != sha(p):
                os.makedirs(store, exist_ok=True)
                dst = os.path.join(store, name)
                if os.path.isfile(dst):
                    clear_ro(dst)
                shutil.copy2(p, dst)
                kept.append(name)
    return kept


def restore(man, game, save):
    for e in man["install"]:
        dest = e["dest"]
        if e["existed"]:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            copy_back(e["backup"], dest, e["mtime"], e.get("ro", False))
        elif os.path.isfile(dest):
            clear_ro(dest)
            os.remove(dest)
    managed = {(m["dir"], m["name"]) for m in man["managed"]}
    for d, pats in managed_dirs(game):
        for n in list_files(d, pats):
            if (d, n) not in managed:
                try:
                    clear_ro(os.path.join(d, n))
                    os.remove(os.path.join(d, n))
                except OSError:
                    pass
    for m in man["managed"]:
        p = os.path.join(game, m["rel"].replace("/", os.sep))
        copy_back(m["backup"], p, m["mtime"], m.get("ro", False))
    want = {f["rel"] for f in man["save_files"]}
    for root, _dirs, files in os.walk(save, topdown=False):
        for n in files:
            p = os.path.join(root, n)
            rel = os.path.relpath(p, save).replace(os.sep, "/")
            if rel not in want:
                try:
                    clear_ro(p)
                    os.remove(p)
                except OSError:
                    pass
    dirs_before = {d for d in man["save_dirs"] if d}
    for root, _dirs, _files in os.walk(save, topdown=False):
        rel = os.path.relpath(root, save).replace(os.sep, "/")
        if rel not in dirs_before and rel != ".":
            try:
                os.rmdir(root)
            except OSError:
                pass
    for f in man["save_files"]:
        p = os.path.join(save, f["rel"].replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        copy_back(f["backup"], p, f["mtime"], f.get("ro", False))


def verify(man, game, save):
    bad = []
    for e in man["install"]:
        dest = e["dest"]
        if e["existed"]:
            if not os.path.isfile(dest) or sha(dest) != e["sha256"]:
                bad.append("no restaurado: %s" % e["rel"])
        elif os.path.exists(dest):
            bad.append("sigue ahí: %s" % e["rel"])
    managed = {m["rel"]: m for m in man["managed"]}
    for m in man["managed"]:
        p = os.path.join(game, m["rel"].replace("/", os.sep))
        if not os.path.isfile(p) or sha(p) != m["sha256"]:
            bad.append("no restaurado: %s" % m["rel"])
    for d, pats in managed_dirs(game):
        for n in list_files(d, pats):
            rel = os.path.relpath(os.path.join(d, n), game).replace(os.sep, "/")
            if rel not in managed:
                bad.append("nuevo sin borrar: %s" % rel)
    want = {f["rel"]: f for f in man["save_files"]}
    for f in man["save_files"]:
        p = os.path.join(save, f["rel"].replace("/", os.sep))
        if not os.path.isfile(p) or sha(p) != f["sha256"]:
            bad.append("no restaurado: save/%s" % f["rel"])
    for root, _dirs, files in os.walk(save):
        for n in files:
            rel = os.path.relpath(os.path.join(root, n), save).replace(os.sep, "/")
            if rel not in want:
                bad.append("nuevo sin borrar: save/%s" % rel)
    return bad


def outside(man, game):
    """files changed under the scanned folders that the sandbox does not manage (a report)"""
    known = {e["rel"] for e in man["install"]} | {m["rel"] for m in man["managed"]}
    out = []
    for d, _p in managed_dirs(game) + [(game, None)]:
        try:
            for n in os.listdir(d):
                p = os.path.join(d, n)
                if not os.path.isfile(p):
                    continue
                rel = os.path.relpath(p, game).replace(os.sep, "/")
                if rel in known:
                    continue
                cur = [os.path.getsize(p), int(os.path.getmtime(p) * 1000)]
                if man["scan"].get(rel) != cur:
                    out.append(rel)
        except OSError:
            pass
    return sorted(set(out))


def evidence(test_dir, game, save, started):
    ev = os.path.join(test_dir, "evidence")
    os.makedirs(ev, exist_ok=True)
    for rel in ("SiderAddons/sider.log", "SiderAddons/sider-app.log", "SiderAddons/fl26join.log",
                "SiderAddons/goal-commentary.log", "SiderAddons/modules/fl26compcache.log", "ReShade.log"):
        p = os.path.join(game, rel.replace("/", os.sep))
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(ev, rel.replace("/", "_")))
    # 31.10.: fl26swiss.lua's per-session logs and the DLL's ceremony dumps (FIN removes them)
    sa = os.path.join(game, "SiderAddons")
    if os.path.isdir(sa):
        for n in os.listdir(sa):
            if (n.startswith("fl26swiss-session-") and n.endswith(".log")) or (n.startswith("fl26cer_") and n.endswith(".bin")):
                try:
                    shutil.copy2(os.path.join(sa, n), os.path.join(ev, n))
                except OSError:
                    pass
    # the career of the test, for the diagnosis of what the game recorded (the club palmarés, the
    # competition's winner): EDIT00000000 is the edit data, not the career, and stays out
    nsave = 0
    for root, _dirs, files in os.walk(save):
        for n in files:
            if n.upper() == "EDIT00000000":
                continue
            p = os.path.join(root, n)
            rel = os.path.relpath(p, save)
            dst = os.path.join(ev, "save", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                shutil.copy2(p, dst)
                nsave += 1
            except OSError:
                pass
    cap = os.path.join(game, "Capturas")
    ncap = 0
    if os.path.isdir(cap):
        for n in os.listdir(cap):
            p = os.path.join(cap, n)
            try:
                if os.path.isfile(p) and os.path.getmtime(p) >= started - 300:
                    shutil.copy2(p, os.path.join(ev, n))
                    ncap += 1
            except OSError:
                pass
    shutil.copy2(os.path.join(test_dir, "manifest.json"), os.path.join(ev, "manifest.json"))
    print("  evidencia en %s (%d captura(s), %d archivo(s) de la carrera)" % (ev, ncap, nsave))
    return ev


def wait_for_fin():
    print("  Escribe FIN y Enter cuando hayas cerrado el juego y terminado la prueba;")
    print("  ABORTAR la cancela y lo restaura todo ahora. Ctrl+C no restaura nada.")
    while True:
        try:
            line = input("> ").strip().lower()
        except EOFError:
            return "fin"
        if line in ("fin", "fin.", "finish", "listo", "ok", "hecho"):
            return "fin"
        if line in ("abortar", "abort", "restaurar", "restore"):
            return "abort"
        print("  FIN para terminar, ABORTAR para restaurar.")


def do_restore(man, game, save):
    kept = careers_keep(man, save)
    if kept:
        print("  carreras del sandbox guardadas en %s: %s" % (man["careers"], ", ".join(kept)))
    print("  restaurando...")
    restore(man, game, save)
    bad = verify(man, game, save)
    if bad:
        print("  RESTAURACIÓN INCOMPLETA (%d):" % len(bad))
        for b in bad[:30]:
            print("    " + b)
        print("  el snapshot queda en %s para --restore" % man.get("test_dir", man["backup"]))
        return False
    print("  restauración verificada: todo está como antes de la prueba (sha256).")
    return True


def run_test(a):
    game = os.path.abspath(a.game) if a.game else os.path.abspath(os.environ.get("FL26_DIR", ""))
    if not game or not os.path.isfile(os.path.join(game, "FL_2026.exe")):
        raise SystemExit("no encuentro FL_2026.exe; pasa --game \"G:\\...\" o FL26_DIR")
    save = find_save(a)
    if not save or not os.path.isdir(save):
        raise SystemExit("no encuentro la carpeta de partidas; pasa --save \"...\\KONAMI\\...\\2026\"")
    name = os.path.basename(os.path.abspath(a.world).rstrip("/\\"))
    installs = build_installs(a.world, game, a.dll, not a.no_fixture)
    if game_running(game):
        raise SystemExit("el juego está abierto; ciérralo y vuelve a ejecutar el comando")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    test_dir = os.path.join(ART, "tests", stamp)
    backup = os.path.join(test_dir, "backup")
    os.makedirs(test_dir, exist_ok=True)
    print("  juego    %s" % game)
    print("  partidas %s" % save)
    print("  prueba   mundo %s, %s" % (name, test_dir))
    man = snapshot(installs, game, save, backup)
    careers = os.path.abspath(a.careers) if a.careers else CAREERS + "-" + name
    man.update(world=name, test_dir=test_dir, careers=careers)
    with open(os.path.join(test_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    print("  respaldados %d archivo(s) instalables, %d del juego, %d de partidas"
          % (len(man["install"]), len(man["managed"]), len(man["save_files"])))
    try:
        install(installs, game)
        nc = careers_install(careers, save)
        print("  carreras del sandbox puestas: %d (%s)" % (nc, careers))
        label = "sin fixture (el Player.bin del mundo)"
        if not a.no_fixture:
            rc, out = fixture_check(game, name)
            label = out.splitlines()[-1] if out else "?"
            print("  fixture Táchira 99: %s" % label)
            if rc:
                raise SystemExit("el fixture no está a 99 en el mundo instalado:\n%s" % out)
        print(CHECKLIST)
        what = wait_for_fin()
        if what == "abort":
            if not wait_closed(game):
                raise SystemExit("no puedo restaurar con el juego abierto; ciérralo y usa --restore %s" % test_dir)
            do_restore(man, game, save)
            return 0
        if not wait_closed(game):
            raise SystemExit("el juego sigue abierto; ciérralo y usa --restore %s" % test_dir)
        started = time.mktime(time.strptime(man["started"], "%Y-%m-%dT%H:%M:%S"))
        ev = evidence(test_dir, game, save, started)
        report = {"world": name, "test_dir": test_dir, "evidence": ev, "finished": now(),
                  "fixture": label, "outside": outside(man, game),
                  "installed": [os.path.relpath(e["src"], REPO).replace(os.sep, "/") for e in man["install"]]}
        with open(os.path.join(ev, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        if report["outside"]:
            print("  AVISO: cambiaron archivos fuera del conjunto respaldado: %s" % ", ".join(report["outside"]))
        ok = do_restore(man, game, save)
        print("  prueba terminada (%s). Evidencia: %s" % ("OK" if ok else "REVISAR", ev))
        return 0 if ok else 1
    except KeyboardInterrupt:
        print("\n  Ctrl+C: no se restauró nada. Cierra el juego y ejecuta:")
        print("  python tools/futve_test.py --restore \"%s\"" % test_dir)
        return 2
    except SystemExit as e:
        print("  ERROR: %s" % e)
        if wait_closed(game):
            do_restore(man, game, save)
        else:
            print("  cierra el juego y ejecuta --restore \"%s\"" % test_dir)
        return 1
    except BaseException:
        traceback.print_exc()
        print("  error inesperado; restaurando el respaldo")
        if wait_closed(game):
            do_restore(man, game, save)
        else:
            print("  cierra el juego y ejecuta --restore \"%s\"" % test_dir)
        return 1


def run_restore(a):
    d = os.path.abspath(a.restore)
    mpath = os.path.join(d, "manifest.json")
    if not os.path.isfile(mpath):
        raise SystemExit("no manifest.json in %s" % d)
    with open(mpath, encoding="utf-8") as f:
        man = json.load(f)
    if game_running(man["game"]):
        raise SystemExit("el juego está abierto; ciérralo y reintenta")
    ok = do_restore(man, man["game"], man["save"])
    return 0 if ok else 1


# ---- the self-test: a fake tree, the whole round trip, byte for byte ----

def _w(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _fake_player(val):
    sys.path.insert(0, HERE)
    import playeredit as E
    rec = bytearray(312)
    rec[8:12] = (91324).to_bytes(4, "little")
    for name in [n for n, _b in E.ABILITIES]:
        E.setf(rec, name, val)
    return bytes(rec)


def _fake_assign():
    a = bytearray(16)
    a[0:4] = (1).to_bytes(4, "little")
    a[4:8] = (91324).to_bytes(4, "little")
    a[8:12] = (71606).to_bytes(4, "little")
    a[12:16] = (0).to_bytes(4, "little")
    return bytes(a)


def _tree(roots, skip_names=()):
    out = {}
    for root in roots:
        for r, ds, fs in os.walk(root):
            ds[:] = [d for d in ds if d not in skip_names]
            for n in fs:
                p = os.path.join(r, n)
                out[os.path.abspath(p)] = (os.path.getsize(p), sha(p))
    return out


def self_test(a):
    sys.path.insert(0, HERE)
    import pesdb
    os.makedirs(os.path.join(ART, "tmp"), exist_ok=True)
    root = tempfile.mkdtemp(prefix="futve-selftest-", dir=os.path.join(ART, "tmp"))
    game = os.path.join(root, "game")
    save = os.path.join(root, "save", "KONAMI", "eFootball PES 2021 SEASON UPDATE", "2026")
    art = os.path.join(root, "art")
    world = os.path.join(game, "SiderAddons", "livecpk", "_FL26MyWorld", "common", "etc", "pesdb")
    mods = os.path.join(game, "SiderAddons", "modules")
    # the game as it is before the test
    _w(os.path.join(game, "FL_2026.exe"), b"exe")
    _w(os.path.join(mods, "fl26swiss.dll"), b"old dll")
    os.chmod(os.path.join(mods, "fl26swiss.dll"), stat.S_IREAD)     # a read-only file, as a Build can leave one
    _w(os.path.join(mods, "fl26swiss.lua"), b"-- old lua")
    _w(os.path.join(mods, "fl26world.txt"), b"old world\n")
    _w(os.path.join(game, "SiderAddons", "livecpk", "_FL26MyWorld", "fl26world.txt"), b"old world\n")
    for n in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"):
        _w(os.path.join(world, n), b"old " + n.encode())
    _w(os.path.join(world, "Player.bin"), pesdb.wesys_pack(_fake_player(50)))
    _w(os.path.join(world, "PlayerAssignment.bin"), pesdb.wesys_pack(_fake_assign()))
    _w(os.path.join(game, "SiderAddons", "sider.log"), b"old log\n")
    _w(os.path.join(game, "SiderAddons", "sider.ini"), b"old ini\n")
    _w(os.path.join(game, "SiderAddons", "camera.cache"), b"old cache")
    _w(os.path.join(mods, "fl26compcache.log"), b"old compcache\n")
    _w(os.path.join(game, "ReShade.ini"), b"old reshade ini")
    _w(os.path.join(game, "ReShade.log"), b"old reshade log")
    _w(os.path.join(save, "save", "EDIT00000000"), b"edit data")
    _w(os.path.join(save, "save", "ML00000005"), b"a career of the user")
    _w(os.path.join(game, "Capturas", "old.png"), b"png")
    # the artifacts: a dll, the fixture and a world as a Build writes it (with a cine line: the
    # cinematics module goes in too); the loader and the modules are the repo's
    _w(os.path.join(art, "bin", "fl26swiss.dll"), b"new dll")
    _w(os.path.join(art, "fixtures", "Player.bin"), pesdb.wesys_pack(_fake_player(99)))
    built = os.path.join(art, "build", "_FL26MyWorld")
    for b in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"):
        _w(os.path.join(built, "common", "etc", "pesdb", b), b"new " + b.encode())
    _w(os.path.join(built, "common", "render", "symbol", "emblemLc", "emb_0134_l.png"), b"new logo")
    _w(os.path.join(built, "fl26world.txt"), b"new world\ncine 261 all LIB\n")
    installs = build_installs(built, game, os.path.join(art, "bin", "fl26swiss.dll"), art=art)
    rels = [r for r, _s in installs]
    assert "SiderAddons/modules/fl26cine.lua" in rels and "SiderAddons/modules/fl26joindll.lua" in rels, rels
    assert "SiderAddons/livecpk/_FL26MyWorld/common/render/symbol/emblemLc/emb_0134_l.png" in rels, rels
    assert len(installs) == 11, rels
    try:
        build_installs(os.path.join(art, "build"), game, art=art)
        raise AssertionError("a folder with no world taken")
    except SystemExit:
        pass
    before = _tree([game, save], ("Capturas",))
    before_ro = is_ro(os.path.join(mods, "fl26swiss.dll"))
    assert before_ro, "the fake installed DLL is not read-only"
    test_dir = os.path.join(root, "tests", "t1")
    man = snapshot(installs, game, save, os.path.join(test_dir, "backup"))
    store = os.path.join(art, "careers")
    _w(os.path.join(store, "ML00000001"), b"a sandbox career")
    man.update(world="_FL26MyWorld", test_dir=test_dir, careers=store)
    os.makedirs(test_dir, exist_ok=True)
    with open(os.path.join(test_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    install(installs, game)
    assert not is_ro(os.path.join(mods, "fl26swiss.dll")), "the read-only DLL was not replaced"
    assert careers_install(store, save) == 1, "the sandbox career was not put in the save folder"
    rc, out = fixture_check(game)
    assert rc == 0, "the fixture check failed on the installed fake world: %s" % out
    # what a test session does
    with open(os.path.join(game, "SiderAddons", "sider.log"), "ab") as f:
        f.write(b"test session\n")
    with open(os.path.join(game, "SiderAddons", "sider.ini"), "ab") as f:
        f.write(b"changed by the test\n")
    _w(os.path.join(save, "save", "ML00000000"), b"a career of the test")
    _w(os.path.join(save, "save", "ML00000001"), b"a sandbox career, played")
    _w(os.path.join(save, "save", "fl26swiss-state.bin"), b"state")
    _w(os.path.join(mods, "newmodule.log"), b"new log")
    _w(os.path.join(game, "SiderAddons", "new.cache"), b"new cache")
    _w(os.path.join(game, "Capturas", "new.png"), b"new png")
    started = time.mktime(time.strptime(man["started"], "%Y-%m-%dT%H:%M:%S"))
    ev = evidence(test_dir, game, save, started)
    assert os.path.isfile(os.path.join(ev, "SiderAddons_sider.log")), "no sider.log in the evidence"
    assert os.path.isfile(os.path.join(ev, "new.png")), "no new screenshot in the evidence"
    assert careers_keep(man, save) == ["ML00000000", "ML00000001"], "the careers were not kept"
    with open(os.path.join(store, "ML00000001"), "rb") as f:
        assert f.read() == b"a sandbox career, played", "the store has not the played career"
    assert not os.path.exists(os.path.join(store, "ML00000005")), "the user's career went to the store"
    restore(man, game, save)
    bad = verify(man, game, save)
    assert not bad, "restore verification: %s" % bad[:5]
    after = _tree([game, save], ("Capturas",))
    assert before == after, ("the tree is not as it was: %d -> %d files, %d differ"
                             % (len(before), len(after),
                                len([k for k in before if after.get(k) != before[k]])))
    assert is_ro(os.path.join(mods, "fl26swiss.dll")) == before_ro, "the read-only state was not restored"
    # a second round with --restore (a crash after the install)
    os.remove(os.path.join(test_dir, "manifest.json"))
    man2 = snapshot(installs, game, save, os.path.join(test_dir, "backup2"))
    man2.update(world="_FL26MyWorld", test_dir=test_dir)
    with open(os.path.join(test_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man2, f, indent=2)
    install(installs, game)
    with open(os.path.join(test_dir, "manifest.json"), encoding="utf-8") as f:
        man3 = json.load(f)
    restore(man3, game, save)
    assert not verify(man3, game, save), "the --restore round trip did not restore"
    assert _tree([game, save], ("Capturas",)) == before, "the --restore round trip left a difference"
    print("self-test: ok (a built world's installs, snapshot, install, fixture check, test writes, evidence, "
          "restore, --restore)")
    shutil.rmtree(root, ignore_errors=True)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--world")
    ap.add_argument("--game")
    ap.add_argument("--dll")
    ap.add_argument("--careers")
    ap.add_argument("--no-fixture", action="store_true")
    ap.add_argument("--save")
    ap.add_argument("--restore", metavar="TEST_DIR")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test(a)
    if a.restore:
        return run_restore(a)
    if not a.world:
        raise SystemExit("pass --world <built world folder> (or --restore <dir> / --self-test)")
    return run_test(a)


if __name__ == "__main__":
    sys.exit(main())
