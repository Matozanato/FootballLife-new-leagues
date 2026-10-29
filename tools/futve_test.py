r"""python futve_test.py --phase 1|2 --game "<game folder>"
       python futve_test.py --restore <test folder>
       python futve_test.py --self-test

The sandbox of the in-game tests of this branch. One command per test:

  1. It checks that the game is closed.
  2. It backs up everything the test can modify: the files it installs (fl26swiss.dll, fl26swiss.lua,
     fl26world.txt in both places, the three Competition*.bin, the Táchira-99 Player.bin, the game's
     own cinematics.lua/cinematicsB.lua that give the finals their UEFA Europa League (261/262) and
     UEFA Champions League (263) final entrances and the Final atmosphere, the competition logos
     the plan stages -- the two play-offs and the three finals, 30 files, and for phase 3 the join
     module `fl26joindll.lua` that adds the finals' ids to the season builder), the game's own logs
     and caches, ReShade.ini/ReShade.log and sider.ini, and the whole save folder (the 2026 folder
     under Documents\KONAMI, where a career and fl26swiss-state.bin are written). It writes
     manifest.json with every size, mtime and sha256.
  3. It installs the DLL, the loader, the phase's world and the fixture, checks every hash and runs
     futve_fixture.py --check on the installed Player.bin (the 25 stats of the 30 Táchira players
     must be 99).
  4. It prints the checklist and WAITS. When you have closed the game and the test is over, type
     FIN and Enter: it copies the evidence (logs, new screenshots, manifest) to evidence/ and puts
     absolutely everything back -- files, save folder (the careers made during the test are
     removed), logs, caches -- and verifies the result against the manifest. ABORTAR restores at
     once; Ctrl+C restores nothing and prints the --restore command.

  --restore <test folder>   the same restore, non-interactive, for a crash or a Ctrl+C.
  --self-test               builds a fake game/save/artifacts tree in out/futve/tmp, runs the whole
                            snapshot-install-test-evidence-restore round trip and checks the tree
                            comes back byte for byte (nothing of the real game is touched).

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
PHASE_WORLD = {1: "world-phase1", 2: "world-phase2", 3: "world-finals"}
GAME_PROCS = ("fl_2026.exe", "sider.exe", "fl 2026 start.exe")
CHECKLISTS = {
    1: """
  1. Abre el juego y crea una carrera nueva con el Deportivo Táchira (Liga FUTVE).
  2. Mira la ficha de un jugador del Táchira: sus 25 stats deben estar a 99.
  3. Simula hasta el día 2 (fin de la fase regular del Apertura). Avanza al 3.
  4. En el calendario deben aparecer las 6 jornadas de grupo de la copa en los días
     3, 5, 7, 9, 11 y 13. Juégalas o simúlalas.
  5. Información de competiciones -> Liga FUTVE Apertura Playoffs -> las tablas de
     los dos grupos: A = 1.º, 4.º, 5.º y 8.º de la fase regular; B = 2.º, 3.º, 6.º y 7.º.
  6. Cierra el juego. Escribe FIN y Enter aquí.
""",
    2: """
  1. Abre el juego y crea una carrera nueva con el Deportivo Táchira (Liga FUTVE).
  2. Mira la ficha de un jugador del Táchira: sus 25 stats deben estar a 99.
  3. Simula hasta el día 2 (fin de la fase regular del Apertura); juega o simula las
     6 jornadas de grupo de los días 3, 5, 7, 9, 11 y 13.
  4. El día 15 debe jugarse la FINAL: los dos ganadores de grupo, a un partido, con el
     mejor clasificado de la fase regular como local. La final debe entrar con la
     presentación de final de la UEFA Europa League y el ambiente de Final.
  5. Comprueba el campeón en la copa y que el Clausura del día 16 sigue en pie.
  6. Cierra el juego. Escribe FIN y Enter aquí.
""",
    3: """
  PRUEBA DE TEMPORADA COMPLETA (finales como competiciones aparte). Se corre dos veces:
  una con el mismo campeón y otra con distinto campeón (perdiendo una final a propósito).
  1. Abre el juego y crea una carrera nueva con el Deportivo Táchira (Liga FUTVE).
  2. Simula hasta el día 2; juega o simula las 6 jornadas de grupo del Apertura
     (días 3, 5, 7, 9, 11, 13).
  3. Día 15: Final del Apertura (competición 142, logo FINAL_APERTURA, entrada de final
     de UEFA Europa League). Gana con el Táchira.
  4. Simula el Clausura hasta el día 144; juega o simula las 6 jornadas de grupo
     (días 145, 148, 151, 154, 157, 160).
  5. Día 164: Final del Clausura (competición 129, logo FINAL_CLAUSURA, entrada UEL).
     - Caso A (mismo campeón): gana el Táchira.
     - Caso B (distinto campeón): pierde a propósito (autogoles o alineación floja).
  6. Día 167:
     - Caso A: la Final del FUTVE (175) NO debe jugarse; el DLL debe haber dado el
       título directo al Táchira. Comprueba el log/estado.
     - Caso B: debe jugarse la Final del FUTVE (144, logo FINAL_FUTVE, entrada de final
       de Champions) entre los dos campeones; juega o simula y mira el campeón.
  7. Comprueba que las tres finales son competiciones aparte (nombre y logo propios) y
     que 142/143/144 no salen como parte de los playoffs.
  8. Si puedes, simula hasta julio: el palmarés de temporada debe recoger los títulos
     (en el caso B también la Final del FUTVE). Mira si hay celebración de campeón
     después de las finales.
  9. Cierra el juego. Escribe FIN y Enter aquí.
""",
}


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
    return [(sider, ["*.log", "*.cache", "sider.ini"]),
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


def find_save(args):
    if args.save:
        s = os.path.abspath(args.save)
        return os.path.dirname(s) if os.path.basename(s).lower() == "save" else s
    home = os.path.expanduser("~")
    for base in (os.path.join(home, "Documents", "KONAMI"),
                 os.path.join(home, "OneDrive", "Documents", "KONAMI")):
        if not os.path.isdir(base):
            continue
        for root, _dirs, _files in os.walk(base):
            if (os.path.basename(root).lower() == "save"
                    and "eFootball PES 2021 SEASON UPDATE" in root):
                return os.path.dirname(root)
    return None


def build_installs(phase, game):
    w = os.path.join(ART, PHASE_WORLD[phase])
    dll = os.path.join(ART, "bin", "fl26swiss.dll")
    lua = os.path.join(REPO, "sider", "experimental", "fl26swiss.lua")
    fix = os.path.join(ART, "fixtures", "Player.bin")
    txt = os.path.join(w, "fl26world.txt")
    bins = os.path.join(w, "common", "etc", "pesdb")
    world = "SiderAddons/livecpk/_FL26MyWorld/common/etc/pesdb/"
    out = [
        ("SiderAddons/modules/fl26swiss.dll", dll),
        ("SiderAddons/modules/fl26swiss.lua", lua),
        ("SiderAddons/modules/fl26world.txt", txt),
        ("SiderAddons/livecpk/_FL26MyWorld/fl26world.txt", txt),
        (world + "Competition.bin", os.path.join(bins, "Competition.bin")),
        (world + "CompetitionRegulation.bin", os.path.join(bins, "CompetitionRegulation.bin")),
        (world + "CompetitionEntry.bin", os.path.join(bins, "CompetitionEntry.bin")),
        (world + "Player.bin", fix),
    ]
    # The game's own cinematics modules: the final competitions take the UEFA Europa League
    # final's entrance (261/262) or the UEFA Champions League final's (263), and the Final stadium
    # scene (cinematicsB.lua). They are the game's files, so the sandbox backs them up and puts them
    # back at the end like everything else.
    cin = os.path.join(ART, "cinematics")
    r = subprocess.run([sys.executable, os.path.join(HERE, "futve_cinematics.py"), "--make",
                        "--game", game], capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise SystemExit("no se pudieron preparar las cinemáticas:\n%s\n%s" % (r.stdout, r.stderr))
    out += [
        ("SiderAddons/modules/common/cinematics.lua", os.path.join(cin, "cinematics.lua")),
        ("SiderAddons/modules/common/cinematicsB.lua", os.path.join(cin, "cinematicsB.lua")),
    ]
    # The logos of the competitions in futve_logo.py's plan: the two play-offs (134/135) and the
    # three finals (142/143/144). The sandbox installs exactly what the plan lists and restores the
    # game's emblems at the end.
    logo = os.path.join(ART, "logos", "world", "common", "render", "symbol", "emblemLc")
    r = subprocess.run([sys.executable, os.path.join(HERE, "futve_logo.py"), "--make"],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise SystemExit("no se pudieron preparar los logos:\n%s\n%s" % (r.stdout, r.stderr))
    try:
        names = json.load(open(os.path.join(ART, "logos", "files.json"), encoding="utf-8"))["files"]
    except (OSError, ValueError, KeyError) as e:
        raise SystemExit("no se pudo leer la lista de logos: %s" % e)
    out += [("SiderAddons/livecpk/_FL26MyWorld/common/render/symbol/emblemLc/" + n,
             os.path.join(logo, n)) for n in names]
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


def fixture_check(game):
    world = os.path.join(game, "SiderAddons", "livecpk", "_FL26MyWorld", "common", "etc", "pesdb")
    r = subprocess.run([sys.executable, os.path.join(HERE, "futve_fixture.py"), "--check",
                        os.path.join(world, "Player.bin"), "--assignments",
                        os.path.join(world, "PlayerAssignment.bin")],
                       capture_output=True, text=True, errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


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
    installs = build_installs(a.phase, game)
    if game_running(game):
        raise SystemExit("el juego está abierto; ciérralo y vuelve a ejecutar el comando")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    test_dir = os.path.join(ART, "tests", stamp)
    backup = os.path.join(test_dir, "backup")
    os.makedirs(test_dir, exist_ok=True)
    print("  juego    %s" % game)
    print("  partidas %s" % save)
    print("  prueba   fase %d, %s" % (a.phase, test_dir))
    man = snapshot(installs, game, save, backup)
    man.update(phase=a.phase, test_dir=test_dir)
    with open(os.path.join(test_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    print("  respaldados %d archivo(s) instalables, %d del juego, %d de partidas"
          % (len(man["install"]), len(man["managed"]), len(man["save_files"])))
    try:
        install(installs, game)
        rc, out = fixture_check(game)
        label = out.splitlines()[-1] if out else "?"
        print("  fixture Táchira 99: %s" % label)
        if rc:
            raise SystemExit("el fixture no está a 99 en el mundo instalado:\n%s" % out)
        print(CHECKLISTS[a.phase])
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
        report = {"phase": a.phase, "test_dir": test_dir, "evidence": ev, "finished": now(),
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
    _w(os.path.join(game, "Capturas", "old.png"), b"png")
    # the artifacts of the branch
    _w(os.path.join(art, "bin", "fl26swiss.dll"), b"new dll")
    _w(os.path.join(art, "bin", "fl26swiss.lua"), b"-- new lua")
    _w(os.path.join(art, "fixtures", "Player.bin"), pesdb.wesys_pack(_fake_player(99)))
    for n in (1, 2):
        d = os.path.join(art, PHASE_WORLD[n], "common", "etc", "pesdb")
        for b in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"):
            _w(os.path.join(d, b), b"new " + b.encode())
        _w(os.path.join(art, PHASE_WORLD[n], "fl26world.txt"), b"new world %d\n" % n)
    installs = [
        ("SiderAddons/modules/fl26swiss.dll", os.path.join(art, "bin", "fl26swiss.dll")),
        ("SiderAddons/modules/fl26swiss.lua", os.path.join(art, "bin", "fl26swiss.lua")),
        ("SiderAddons/modules/fl26world.txt", os.path.join(art, PHASE_WORLD[1], "fl26world.txt")),
        ("SiderAddons/livecpk/_FL26MyWorld/fl26world.txt", os.path.join(art, PHASE_WORLD[1], "fl26world.txt")),
        ("SiderAddons/livecpk/_FL26MyWorld/common/etc/pesdb/Competition.bin",
         os.path.join(art, PHASE_WORLD[1], "common", "etc", "pesdb", "Competition.bin")),
        ("SiderAddons/livecpk/_FL26MyWorld/common/etc/pesdb/CompetitionRegulation.bin",
         os.path.join(art, PHASE_WORLD[1], "common", "etc", "pesdb", "CompetitionRegulation.bin")),
        ("SiderAddons/livecpk/_FL26MyWorld/common/etc/pesdb/CompetitionEntry.bin",
         os.path.join(art, PHASE_WORLD[1], "common", "etc", "pesdb", "CompetitionEntry.bin")),
        ("SiderAddons/livecpk/_FL26MyWorld/common/etc/pesdb/Player.bin",
         os.path.join(art, "fixtures", "Player.bin")),
    ]
    before = _tree([game, save], ("Capturas",))
    before_ro = is_ro(os.path.join(mods, "fl26swiss.dll"))
    assert before_ro, "the fake installed DLL is not read-only"
    test_dir = os.path.join(root, "tests", "t1")
    man = snapshot(installs, game, save, os.path.join(test_dir, "backup"))
    man.update(phase=1, test_dir=test_dir)
    os.makedirs(test_dir, exist_ok=True)
    with open(os.path.join(test_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    install(installs, game)
    assert not is_ro(os.path.join(mods, "fl26swiss.dll")), "the read-only DLL was not replaced"
    rc, out = fixture_check(game)
    assert rc == 0, "the fixture check failed on the installed fake world: %s" % out
    # what a test session does
    with open(os.path.join(game, "SiderAddons", "sider.log"), "ab") as f:
        f.write(b"test session\n")
    with open(os.path.join(game, "SiderAddons", "sider.ini"), "ab") as f:
        f.write(b"changed by the test\n")
    _w(os.path.join(save, "save", "ML00000000"), b"a career of the test")
    _w(os.path.join(save, "save", "fl26swiss-state.bin"), b"state")
    _w(os.path.join(mods, "newmodule.log"), b"new log")
    _w(os.path.join(game, "SiderAddons", "new.cache"), b"new cache")
    _w(os.path.join(game, "Capturas", "new.png"), b"new png")
    started = time.mktime(time.strptime(man["started"], "%Y-%m-%dT%H:%M:%S"))
    ev = evidence(test_dir, game, save, started)
    assert os.path.isfile(os.path.join(ev, "SiderAddons_sider.log")), "no sider.log in the evidence"
    assert os.path.isfile(os.path.join(ev, "new.png")), "no new screenshot in the evidence"
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
    man2.update(phase=2, test_dir=test_dir)
    with open(os.path.join(test_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man2, f, indent=2)
    install(installs, game)
    with open(os.path.join(test_dir, "manifest.json"), encoding="utf-8") as f:
        man3 = json.load(f)
    restore(man3, game, save)
    assert not verify(man3, game, save), "the --restore round trip did not restore"
    assert _tree([game, save], ("Capturas",)) == before, "the --restore round trip left a difference"
    print("self-test: ok (snapshot, install, fixture check, test writes, evidence, restore, --restore)")
    shutil.rmtree(root, ignore_errors=True)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", type=int, choices=(1, 2, 3))
    ap.add_argument("--game")
    ap.add_argument("--save")
    ap.add_argument("--restore", metavar="TEST_DIR")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test(a)
    if a.restore:
        return run_restore(a)
    if a.phase not in (1, 2, 3):
        raise SystemExit("pass --phase 1|2|3 (or --restore <dir> / --self-test)")
    return run_test(a)


if __name__ == "__main__":
    sys.exit(main())
