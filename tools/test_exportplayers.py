"""exportplayers.py: every player of a world in one CSV (Players > More > Export all players)

    python tools/test_exportplayers.py

1. A small world made here (a world folder as a zip brings it: common\\etc\\pesdb and
   fl26playerids.json) and game tables beside it: every player once, his club, the free agent
   marked, a national team no club, game / new, UTF-8 with BOM.
2. The Europack eu4 tables (the folder in FL26_EU4; skipped when it is not set):
   59,910 players, Nicolás González 214662 at Juventus, 116541 without a club.
"""
import csv, json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import playeredit as E
import exportplayers as X

EU4 = os.environ.get("FL26_EU4") or ""
FAILS = []


def ok(what, cond):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def player(pid, name, nat=7, age=25, height=180, pos="CF"):
    rec = bytearray(E.P_REC)
    rec[E.P_ID:E.P_ID + 4] = pid.to_bytes(4, "little")
    rec[E.P_NAME:E.P_NAME + E.P_NAME_LEN * E.P_NAME_SLOTS] = E.name_slots(name)
    for n, v in (("Nationality", nat), ("Age", age), ("Height (cm)", height),
                 ("Registered Position", E.POSITIONS.index(pos))):
        E.setf(rec, n, v)
    for n, _b in E.ABILITIES:
        E.setf(rec, n, 70)
    return bytes(rec)


def team(tid, name, national=False):
    rec = bytearray(E.T_REC)
    rec[E.T_ID:E.T_ID + 4] = tid.to_bytes(4, "little")
    b = name.encode("utf-8")
    rec[E.T_NAME:E.T_NAME + len(b)] = b
    if national:
        rec[0x53] |= 0x80
    return bytes(rec)


def assign(eid, pid, tid, order):
    return b"".join(x.to_bytes(4, "little") for x in (eid, pid, tid, order << E.ORDER_SHIFT))


def put(d, name, raw):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f:
        f.write(pesdb.wesys_pack(raw))


def run(*args):
    p = subprocess.run([sys.executable, "-W", "ignore", os.path.join(HERE, "exportplayers.py")] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def read(path):
    with open(path, "rb") as f:
        bom = f.read(3) == b"\xef\xbb\xbf"
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    return bom, rows[0], {r[0]: dict(zip(rows[0], r)) for r in rows[1:]}, len(rows) - 1


def small():
    tmp = tempfile.mkdtemp(prefix="exportplayers-")
    try:
        world = os.path.join(tmp, "livecpk", "_FL26Small")
        db = os.path.join(world, "common", "etc", "pesdb")
        base = os.path.join(tmp, "tables")
        game = [player(100, "Luka Modrić", nat=50, age=39, height=172, pos="CMF"),
                player(101, "Ivan Bez Kluba", pos="GK")]
        mine = [player(200000, "Novi Igrač", age=19, height=190, pos="CB")]
        put(base, "Player.bin", b"".join(game))
        put(db, "Player.bin", b"".join(game + mine))
        put(db, "Team.bin", team(500, "NK Primjer") + team(9, "Croatia", national=True))
        # Modrić at the club and in the national team, the new player at the club, 101 nowhere
        put(db, "PlayerAssignment.bin", assign(1, 100, 9, 0) + assign(2, 100, 500, 0) + assign(3, 200000, 500, 1))
        with open(os.path.join(world, "fl26playerids.json"), "w", encoding="utf-8") as f:
            json.dump({"world": "_FL26Small", "clubs": {"Liga/0": {"0": 200000}}}, f)
        out = os.path.join(tmp, "out.csv")
        code, said = run(world, out, "--base", base)
        ok("small: the CLI ends well", code == 0)
        if code:
            print(said)
            return
        bom, head, by, n = read(out)
        ok("small: UTF-8 with BOM", bom)
        ok("small: the columns", head == X.COLUMNS)
        ok("small: 3 players, each once (Modrić is in a national team too)", n == 3)
        m = by.get("100", {})
        ok("small: Modrić at NK Primjer, a game player", m.get("club") == "NK Primjer" and m.get("club_id") == "500"
           and m.get("source") == "game")
        ok("small: the accents and the shirt name", m.get("name") == "Luka Modrić" and m.get("shirt_name") == "MODRIĆ")
        ok("small: age, height, position", (m.get("age"), m.get("height"), m.get("position")) == ("39", "172", "CMF"))
        ok("small: a rating", m.get("rating", "").isdigit())
        f = by.get("101", {})
        ok("small: 101 a free agent", f.get("club_id") == "" and f.get("club") == X.FREE and f.get("source") == "game")
        ok("small: 200000 new (fl26playerids.json)", by.get("200000", {}).get("source") == "new")
        ok("small: the free agent last", list(by)[-1] == "101")
        # the same tables read as the game's own (no world): every player is the game's
        code, said = run(db, out, "--base", db)
        _b, _h, by, n = read(out) if code == 0 else (0, 0, {}, 0)
        ok("small: the tables as the game's own: all game", code == 0 and n == 3
           and {r["source"] for r in by.values()} == {"game"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def eu4():
    if not EU4 or not os.path.isfile(os.path.join(EU4, "Player.bin")):
        print("skip  eu4: no tables at %s (set FL26_EU4)" % EU4 if EU4 else "skip  eu4: FL26_EU4 not set")
        return
    out = os.path.join(tempfile.gettempdir(), "test_exportplayers_eu4.csv")
    t = time.time()
    code, said = run(EU4, out)
    took = time.time() - t
    ok("eu4: the CLI ends well", code == 0)
    print("      " + said.strip().replace("\n", "\n      "))
    if code:
        return
    _bom, _h, by, n = read(out)
    count = len(pesdb.load("Player", EU4)) // E.P_REC
    ok("eu4: every player of Player.bin (%d rows, %d records)" % (n, count), n == count == 59910)
    g = by.get("214662", {})
    ok("eu4: Nicolás González 214662 at Juventus (%s)" % g.get("club"),
       g.get("name") == "Nicolás González" and "Juventus" in g.get("club", "") and g.get("club_id") == "120")
    ok("eu4: Juventus in Serie A TIM, Italy", g.get("league") == "Serie A TIM" and g.get("club_country") == "Italy")
    f = by.get("116541", {})
    ok("eu4: 116541 has no club", f.get("club_id") == "" and f.get("club") == X.FREE)
    ok("eu4: under 30 s (%.1f s)" % took, took < 30)
    os.remove(out)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    small()
    eu4()
    print("%d failed" % len(FAILS) if FAILS else "all passed")
    sys.exit(1 if FAILS else 0)
