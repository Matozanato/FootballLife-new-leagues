r"""python tools/test_zone_colours.py [<folder with the game's tables>] [--keep]

The standings' zone strip colours every continental place (mato 08.11.2026: a tester's Brazil in
a modern CONMEBOL world, FL27 -- places 1-4, the Libertadores groups, were blue, but 5-6, phase 2
of its qualifying, and 7-12, the Copa Sudamericana, had no colour). A confederation's top cup is
blue, the one below orange, the third teal:

  blue    0 / 10 Champions League and its play-off, 3 / 4 Libertadores and its qualifying, 16 / 17
          its modern phases 1 and 2, 5 AFC Champions League (Elite), 6 CAF Champions League,
          13 CONCACAF Champions Cup, 14 OFC Champions League
  orange  1 / 11 Europa League and its play-off, 9 Copa Sudamericana, 19 its first stage, 7 CAF
          Confederation Cup, 8 AFC Champions League Two
  teal    2 / 12 Conference League and its play-off, 15 AFC Challenge League

A place reaches fl26swiss.dll three ways, all checked here: the world file's uefa lines (0..5,
10..12: fl26_swiss_access), the ccup lines of our own continental cups (their entry= places and,
new, comp=<n>: fl26_swiss_ccup_zone; a world built before comp= is known by the cup's default
name) and the lpre lines (cup=0: a Libertadores phase, else the pre-round of the cup it names --
the Sudamericana's first stage). A cup winner's place (position 0) is no row of a table.

Each world file is read by fl26swiss.lua's own read_world (LuaJIT through lupa), handed to
fl26swiss.c built natively (tools/native/test_zone_colours.c) in the loader's buffers, and every
place of every list is asked for its colour (zone_access), plus the rows around them for none:
  - the _FL26Megapack world built under E:/FL/FL27/game (FL27, modern CONMEBOL; read only, copied),
    and Brazil's 1-4 / 5-6 / 7-12 exactly as the tester's screenshot should have them;
  - FL26 worlds under E: when there (_FL26Conmebolv15: modern CONMEBOL, _FL26M2400S);
  - worlds built offline from <folder> into a temporary game folder: classic CONMEBOL (3 / 4 / 9),
    modern (16 / 17 / 19), and new leagues in Africa, Asia, CONCACAF and the OFC (5, 6, 7, 8, 13,
    14, 15) -- their ccup lines carry comp=; the same file with comp= taken out (a world of
    before) by the default names, and a renamed cup without comp= gets no colour.

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe) and lupa; without either the test says so
and is skipped. Without <folder> (default D:/dev/fl26-modding-research/out/base-pesdb) the
offline worlds are skipped.
"""
import glob, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
REPO = os.path.dirname(HERE)
LUA = os.path.join(REPO, "sider", "experimental", "fl26swiss.lua")
sys.path.insert(0, HERE)

BLUE, ORANGE, TEAL, NONE = 0, 1, 2, -1
COLOUR = {0: BLUE, 10: BLUE, 3: BLUE, 4: BLUE, 5: BLUE, 6: BLUE, 13: BLUE, 14: BLUE, 16: BLUE, 17: BLUE,
          1: ORANGE, 11: ORANGE, 7: ORANGE, 8: ORANGE, 9: ORANGE, 19: ORANGE,
          2: TEAL, 12: TEAL, 15: TEAL}
DEFAULT_NAMES = {"CAF Champions League": 6, "CAF Confederation Cup": 7, "AFC Champions League Two": 8,
                 "Copa Sudamericana": 9, "CONCACAF Champions Cup": 13, "OFC Champions League": 14,
                 "AFC Challenge League": 15}
COMPILED_REGS = {17, 18, 19, 20, 21, 22, 50, 117, 118, 134, 147, 155}   # fl26swiss.c ACCESS
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


def lua_reader():
    """fl26swiss.lua's read_world, run in LuaJIT (lupa); None without lupa"""
    try:
        from lupa import luajit21 as lj
    except ImportError:
        try:
            from lupa import lua54 as lj
        except ImportError:
            return None
    with open(LUA, encoding="utf-8") as f:
        src = f.read()
    blk = re.search(r"^local confed = \{\}.*?^  return leagues, splits, uefa, ccups, dlike, qrounds, lpres\nend\n",
                    src, re.S | re.M)
    assert blk, "read_world not found in fl26swiss.lua"
    lua = lj.LuaRuntime()
    return lua, lua.execute(blk.group(0) + "\nreturn read_world")


def lua_world(reader, text):
    """the loader's buffers for this world file, as fl26swiss.lua packs them, and its ccups' comp"""
    lua, read_world = reader
    tmp = tempfile.mkdtemp(prefix="fl26-zone-")
    try:
        os.makedirs(os.path.join(tmp, "modules"))
        with open(os.path.join(tmp, "modules", "fl26world.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        out = read_world(lua.table_from({"sider_dir": tmp}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    uefa, ccups, lpres = out[2], out[3], out[6]          # read_world's 3rd, 4th and 7th results
    L = lambda t: [t[i] for i in range(1, len(t) + 1)]
    secs = []
    acc = [v for e in L(uefa) for v in L(e)]
    if acc:
        secs.append(("access", len(L(uefa)), acc))
    like = [v for c in L(ccups) if c["like"] is not None for v in (c[2], c["like"])]
    if like:                                         # before fl26_swiss_ccup, as the loader
        secs.append(("like", len(like) // 2, like))
    cbuf, zone, comps = [], [], []
    for c in L(ccups):
        ents = L(c[4])
        cbuf += [c[1], c[2], c[3], len(ents)] + [v for e in ents for v in (e[1], e[2])]
        comps.append((c[2], c["comp"]))
        if c["comp"] is not None:
            zone += [c[2], c["comp"]]
    if cbuf:
        secs.append(("ccup", len(L(ccups)), cbuf))
    if zone:
        secs.append(("zone", len(zone) // 2, zone))
    lbuf = []
    for p in L(lpres):
        ents = L(p[5])
        lbuf += [p[1], p[2], p[3], p[4][1], p[4][2], len(ents)] + [v for e in ents for v in (e[1], e[2])]
    if lbuf:
        secs.append(("lpre", len(L(lpres)), lbuf))
    return secs, dict(comps)


def entries(rest, key="entry"):
    m = re.search(r"\b%s=([\d:,]+)" % key, rest)
    return [tuple(map(int, e.split(":"))) for e in m.group(1).split(",") if e] if m else []


def expected(text):
    """{(reg, position): colour} from the world file's lines, read here independently of the
    module: uefa first, then the ccups (comp=, or else the default name), then the lpre
    lines -- the order zone_access asks them in. Second: {ko: competition} of the ccups; third:
    the competition codes seen"""
    want, kos, seen = {}, {}, set()

    def put(reg, rank, comp):
        if 0 < rank <= 40 and reg < 1024 and (reg, rank) not in want:
            want[(reg, rank)] = COLOUR[comp]
            seen.add(comp)
    lines = text.splitlines()
    for l in lines:
        m = re.match(r"\s*uefa\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", l)
        if m and int(m.group(3)) in COLOUR:
            put(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    for l in lines:
        m = re.match(r"\s*ccup\s+(\d+)(.*)$", l)
        if not m:
            continue
        rest = m.group(2)
        head = rest.split(" name=")[0]
        name = rest.split(" name=")[1].strip() if " name=" in rest else ""
        ko = int(re.search(r"\bko=(\d+)", rest).group(1)) if re.search(r"\bko=(\d+)", rest) else 0
        cm = re.search(r"\scomp=(\d+)", head)
        comp = int(cm.group(1)) if cm else DEFAULT_NAMES.get(name)
        if not ko:
            continue
        kos[ko] = comp
        if comp is not None:
            for r, p in entries(head):
                put(r, p, comp)
    for l in lines:
        m = re.match(r"\s*lpre\s+(\d+)(.*)$", l)
        if not m:
            continue
        rest = m.group(2)
        cup = int(re.search(r"\bcup=(\d+)", rest).group(1))
        if cup == 0:
            comp = 17 if re.search(r"\sfeed=8", rest) else 16
        else:
            comp = 19 if kos.get(cup) == 9 else kos.get(cup)
        if comp is None:
            continue
        for r, p in entries(rest):
            put(r, p, comp)
    return want, kos, seen


class Native:
    def __init__(self, zig, tmp):
        self.exe = os.path.join(tmp, "test_zone_colours.exe")
        self.tmp = tmp
        subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w", os.path.join(NATIVE, "test_zone_colours.c"),
                        "-o", self.exe], check=True, cwd=NATIVE)

    def run(self, secs, checks):
        data = os.path.join(self.tmp, "zone.txt")
        with open(data, "w") as f:
            for name, n, v in secs:
                f.write("%s %d %d\n%s\n" % (name, n, len(v), " ".join(map(str, v))))
            for (reg, rank), z in sorted(checks.items()):
                f.write("expect %d %d %d\n" % (reg, rank, z))
        r = subprocess.run([self.exe, data], capture_output=True, text=True, timeout=120, cwd=self.tmp)
        said = [l for l in r.stdout.splitlines() if not l.startswith("fl26swiss:")]
        return r.returncode, said


def check_world(native, reader, label, text, must=None, codes=None):
    """every place of the world's lists has its colour and the rows around them none"""
    want, kos, seen = expected(text)
    secs, comps = lua_world(reader, text)
    lua_kos = {ko: c for ko, c in comps.items() if ko in kos}
    ok("%s: fl26swiss.lua reads each continental cup's competition (%d cups)" % (label, len(kos)),
       all(lua_kos.get(ko) == c for ko, c in kos.items()))
    checks = dict(want)
    has_uefa = any(n == "access" for n, _n, _v in secs)
    for reg in {r for r, _p in want}:
        top = max(p for r, p in want if r == reg)
        for p in range(1, top + 4):
            if (reg, p) not in checks and (has_uefa or reg not in COMPILED_REGS):
                checks[(reg, p)] = NONE
    for k, v in (must or {}).items():
        ok("%s: the world's lists give reg %d place %d colour %d" % (label, k[0], k[1], v), want.get(k, NONE) == v)
        checks[k] = v
    rc, said = native.run(secs, checks)
    print("\n".join("#   " + l for l in said))
    ok("%s: fl26swiss.dll colours all %d places (%s), the rest none"
       % (label, len(want), ", ".join(str(c) for c in sorted(seen))), rc == 0 and "all checks passed" in said)
    if codes:
        ok("%s: competitions %s all among them" % (label, sorted(codes)), set(codes) <= seen)
    return seen


def build(B, base, game, recipe):
    log = []
    try:
        B.build(B.plan(recipe, base), base, game, False, log=log.append)
    except Exception:
        print("\n".join("# " + l for l in log[-30:]))
        raise
    with open(os.path.join(game, "SiderAddons", "livecpk", recipe["world"], "fl26world.txt"), encoding="utf-8") as f:
        return f.read()


def others():
    return {"world": "_TestZoneOthers",
            "leagues": [
                {"name": "ZN Nigeria", "country": "Nigeria", "clubs": 12, "legs": 2,
                 "europe": [[1, 6], [2, 6], [3, 6], [4, 6], [5, 7], [6, 7], [7, 7], [8, 7]]},
                {"name": "ZN Thailand", "country": "Thailand", "clubs": 16, "legs": 2,
                 "europe": [[1, 5], [2, 8], [3, 15], [4, 15]]},
                {"name": "ZN Costa Rica", "country": "Costa Rica", "clubs": 12, "legs": 2,
                 "europe": [[1, 13], [2, 13]]},
                {"name": "ZN New Zealand", "country": "New Zealand", "clubs": 10, "legs": 2,
                 "europe": [[1, 14], [2, 14], [3, 14], [4, 14]]}]}


def main(base, keep=False):
    zig = find_zig()
    reader = lua_reader()
    if not zig or not reader:
        print("SKIPPED: %s" % ("no zig (set ZIG to zig.exe)" if not zig else "no Lua runtime (pip install lupa)"))
        return
    import leaguebuilder as B
    line = "ccup 615 ko=616 groups=1 entry=11:1,11:2,11:3,11:4 alt=1:11:2 name=CAF Champions League"
    ok("ccup_comp: comp= before name= for a continental cup",
       B.ccup_comp(line, {"number": 6}) == line.replace(" name=", " comp=6 name="))
    ok("ccup_comp: nothing for a super cup, the Recopa or a league cup",
       all(B.ccup_comp(line, c) == line for c in ({"number": 0}, {"number": -1}, {})))
    tmp = tempfile.mkdtemp(prefix="fl26-zonecol-")
    game = None
    try:
        native = Native(zig, tmp)
        mega = "E:/FL/FL27/game/SiderAddons/livecpk/_FL26Megapack/fl26world.txt"
        if os.path.exists(mega):
            with open(mega, encoding="utf-8") as f:
                text = f.read()
            bra = {(29, p): BLUE for p in range(1, 7)}
            bra.update({(29, p): ORANGE for p in range(7, 13)})
            bra[(29, 13)] = NONE
            check_world(native, reader, "FL27 _FL26Megapack", text, must=bra,
                        codes=[0, 1, 2, 3, 6, 7, 8, 9, 13, 14, 15, 16, 17, 19])
        else:
            print("# no _FL26Megapack world under E:/FL/FL27/game: skipped")
        for w in ("_FL26Conmebolv15", "_FL26M2400S"):
            p = "E:/FL/FL26/game/SiderAddons/livecpk/%s/fl26world.txt" % w
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    check_world(native, reader, "FL26 " + w, f.read())
        if base and os.path.isdir(base):
            import test_conmebol_modern as TC
            game = tempfile.mkdtemp(prefix="fl26-zoneworld-")
            classic = build(B, base, game, TC.classic())
            ok("classic: its Copa Sudamericana line has comp=9",
               re.search(r"^ccup .* comp=9 name=Copa Sudamericana$", classic, re.M))
            check_world(native, reader, "classic CONMEBOL", classic, codes=[3, 4, 9],
                        must={(TC.CHI, 1): BLUE, (TC.CHI, 2): BLUE, (TC.CHI, 3): ORANGE})
            modern = build(B, base, game, TC.modern())
            check_world(native, reader, "modern CONMEBOL", modern, codes=[3, 9, 16, 17, 19])
            other = build(B, base, game, others())
            ok("others: comp= on each continental cup's line, none on the CAF Super Cup",
               all(re.search(r"^ccup .* comp=%d name=" % c, other, re.M) for c in (6, 7, 8, 13, 14, 15))
               and not re.search(r"^ccup .* comp=\d+ name=CAF Super Cup", other, re.M))
            check_world(native, reader, "Africa, Asia, CONCACAF, OFC", other, codes=[5, 6, 7, 8, 13, 14, 15])
            old = re.sub(r" comp=\d+(?= name=)", "", other)
            check_world(native, reader, "the same world built before comp= (default names)", old,
                        codes=[5, 6, 7, 8, 13, 14, 15])
            renamed = old.replace("name=AFC Challenge League", "name=My Challenge Cup")
            seen = check_world(native, reader, "... a renamed cup without comp=", renamed)
            ok("... its places get no colour", 15 not in seen)
        else:
            print("# no folder with the game's tables (%s): the offline worlds skipped" % base)
    finally:
        if keep:
            print("# kept %s %s" % (tmp, game or ""))
        else:
            shutil.rmtree(tmp, ignore_errors=True)
            if game:
                shutil.rmtree(game, ignore_errors=True)
    print("1..%d" % N)
    print("all passed")


if __name__ == "__main__":
    a = sys.argv[1:]
    base = next((x for x in a if not x.startswith("-")), "D:/dev/fl26-modding-research/out/base-pesdb")
    main(base, "--keep" in a)
