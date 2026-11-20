r"""python tools/test_b335_argentina_calendar.py [--fl26 <game folder>] [--fl27 <game folder>]
                                              [--tables26 <pesdb>] [--tables27 <pesdb>]

B335 (Quemer07 on Evoweb, Frosscar #support 05.11.2026): FL 2027 plays Argentina (region 17)
February to December. Mod Studio 0.3.0 had FL26's list of calendar-year regions (17 is type 3
there, August-May dates), so a division of ours under the Liga Profesional was dated August-May:
the region's season took it in at New Year with the first rounds gone (matchday 14 or 21).

Checked here, without starting a game (the exes are only read):
  1. the region table read off each exe: FL26's calendar-year regions are the set 0.3.0 had,
     FL27's the same plus 17;
  2. that table agrees with the exe's own league dates (caltab): every shipped league of a type-1
     region plays within one calendar year, every one of a type-0 region runs across New Year --
     so the move is found from the game, not from a list of countries;
  3. game_calendar_regions on made-up exes: an FL27 table with other types is taken as it is, an
     unreadable FL27 exe gives the fallback, an FL26 folder never reads its exe;
  4. plan() on FL26's tables (FL26 folder): a division under reg 30 stays August-May, no season
     line, as before; one under Colombia's Liga BetPlay still follows its calendar;
  5. plan() on FL27's tables (FL27 folder): the division under reg 30 follows the February-
     December season, the world file gets `season 17 1` (fl26joindll/fl26swiss then close and
     date it with the region), its real calendar starts after the day-41 join (matchday 1 is
     played) and ends before New Year; Mod Studio's season box (shipped_calendar) shows it.
Defaults: FL26_DIR or flpaths' game folder, FL27_DIR or E:\FL\FL27\game, and Mod Studio's unpacked
tables in %APPDATA%\FL26ModStudio\tables and tables27. A part whose game or tables are missing
is skipped with a line saying so.
"""
import os, struct, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import flpaths

N = 0
SKIPPED = []


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %2d - %s" % (N, name))


def skip(why):
    SKIPPED.append(why)
    print("skip   - %s" % why)


def arg(k, default):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a else default


def tables(name):
    p = os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", name, "common", "etc", "pesdb")
    return p if os.path.isfile(os.path.join(p, "CompetitionRegulation.bin")) else None


def fake_exe(folder, name, types):
    """a file with just a PE header and the region table at STYPE_RDATA (types: {region: type})"""
    sva, size, raw = 0x298b000, 0x1000, 0x400
    head = bytearray(raw)
    struct.pack_into("<I", head, 0x3c, 0x80)
    head[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", head, 0x84, 0x8664, 1)                # machine, one section
    struct.pack_into("<H", head, 0x80 + 20, 0xf0)                  # optional header size
    sec = 0x80 + 24 + 0xf0
    head[sec:sec + 8] = b".rdata\0\0"
    struct.pack_into("<IIII", head, sec + 8, size, sva, size, raw)
    body = bytearray(size)
    regions = list(B.STYPE_REGIONS)
    for i, rva in enumerate(B.STYPE_RDATA):
        for j in range(2):
            r = regions[2 * i + j]
            struct.pack_into("<II", body, rva - sva + 8 * j, r, types.get(r, 0))
    p = os.path.join(folder, name)
    with open(p, "wb") as f:
        f.write(bytes(head) + bytes(body))
    return p


def recipe(above, country):
    return {"world": "_TestB335", "leagues": [{"name": "B335 Test Division", "country": country,
                                                "clubs": 16, "legs": 2, "above": above}]}


def plan_one(base, above, country):
    pl = B.plan(recipe(above, country), base)
    p = pl["leagues"][0]
    rcal = B.rcal_lines(pl, base, B.confederations(base))
    return pl, p, B.season_lines(pl, None), rcal


def rcal_days(lines):
    w = lines[0].split()
    return int(w[2]), int(w[3])


def check_exe(label, game, want):
    exe = flpaths.game_exe(game)
    types = B.exe_season_types(exe)
    ok("%s: the exe's region table reads (%s)" % (label, exe), types is not None)
    cal = {r for r, t in types.items() if t == 1}
    ok("%s: its February-December regions are %s" % (label, sorted(want)), cal == want)
    ok("%s: game_calendar_regions gives the same" % label, B.game_calendar_regions(game) == want)
    return exe, types


def check_dates(label, exe, types, base):
    """the region table against the exe's own league dates"""
    try:
        import caltab
        old = flpaths.EXE
        flpaths.EXE = exe
        try:
            img = caltab.Image()
            cs, idc = caltab.cases(img), caltab.id_case(img)
        finally:
            flpaths.EXE = old
    except (ImportError, SystemExit, OSError) as e:
        skip("%s: the exe's dates could not be read (%s)" % (label, e))
        return
    M = B.M
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    region = {M.comp_cid(comp, i * M.COMP): M.dec_region(comp[i * M.COMP + M.REGION_OFF])
              for i in range(len(comp) // M.COMP)}
    seen, bad = 0, []
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        rid = struct.unpack_from("<H", g, M.R_ID)[0]
        if g[M.R_TYPE] != 4 or rid > caltab.LAST_ID:
            continue
        t = types.get(region.get(M.reg_cid(g)))
        c = idc.get(rid)
        d = cs[c][2] if c in cs and c != caltab.CASE_EMPTY else []
        if t not in (0, 1) or not d:
            continue
        seen += 1
        wraps = any(b < a for a, b in zip(d, d[1:]))
        if wraps != (t == 0):
            bad.append((rid, t, d[0], d[-1]))
    ok("%s: %d shipped leagues -- type 1 plays in one year, type 0 across New Year (%s)"
       % (label, seen, bad or "all agree"), seen >= 20 and not bad)
    return idc, cs


def main():
    fl26 = arg("--fl26", os.environ.get("FL26_DIR") or flpaths.GAME_DIR)
    fl27 = arg("--fl27", os.environ.get("FL27_DIR") or r"E:\FL\FL27\game")
    t26, t27 = arg("--tables26", tables("tables")), arg("--tables27", tables("tables27"))
    have26 = os.path.isfile(os.path.join(fl26, "FL_2026.exe"))
    have27 = os.path.isfile(os.path.join(fl27, "FL_2027.exe"))

    # 1-2: the exes
    if have26:
        exe, types = check_exe("FL26", fl26, set(B.FL26_CALENDAR_REGIONS))
        ok("FL26: Argentina (17) is type 3 there", types.get(17) == 3)
        if t26:
            idc, cs = check_dates("FL26", exe, types, t26) or (None, None)
            if idc:
                d = cs[idc[30]][2]
                ok("FL26: the Liga Profesional (30) runs August-May (day %d to %d)" % (d[0], d[-1]),
                   d[0] > 180 and d[-1] < 180)
    else:
        skip("no FL_2026.exe in %s" % fl26)
    if have27:
        exe, types = check_exe("FL27", fl27, set(B.FL26_CALENDAR_REGIONS) | {17})
        if t27:
            idc, cs = check_dates("FL27", exe, types, t27) or (None, None)
            if idc:
                d = cs[idc[30]][2]
                ok("FL27: the Liga Profesional (30) runs January-December (day %d to %d)" % (d[0], d[-1]),
                   d[0] < 60 and d[-1] > 300)
    else:
        skip("no FL_2027.exe in %s" % fl27)

    # 3: made-up exes
    d = tempfile.mkdtemp()
    f27 = os.path.join(d, "fl27")
    os.makedirs(f27)
    fake_exe(f27, "FL_2027.exe", {16: 1, 13: 1, 17: 0, 20: 3})
    ok("a made-up FL27 table is taken as it says (13 and 16, with 24)",
       B.game_calendar_regions(f27) == {13, 16, 24})
    open(os.path.join(f27, "FL_2027.exe"), "wb").close()
    ok("an FL27 exe that cannot be read: FL26's set and Argentina",
       B.game_calendar_regions(f27) == set(B.FL26_CALENDAR_REGIONS) | {17})
    f26 = os.path.join(d, "fl26")
    os.makedirs(f26)
    fake_exe(f26, "FL_2026.exe", {16: 1, 13: 1, 17: 1})
    ok("an FL26 folder keeps FL26's set, whatever its exe holds",
       B.game_calendar_regions(f26) == set(B.FL26_CALENDAR_REGIONS))
    ok("no game folder: FL26's set", B.game_calendar_regions(None) == set(B.FL26_CALENDAR_REGIONS))
    B.use_game(f27)
    ok("use_game(FL27 folder) puts its set in CALENDAR_REGIONS", 17 in B.CALENDAR_REGIONS)
    B.use_game(f26)
    ok("use_game(FL26 folder) puts FL26's back", B.CALENDAR_REGIONS == set(B.FL26_CALENDAR_REGIONS))

    # 4: FL26 tables and folder -- as 0.3.0
    if t26:
        B.use_game(fl26 if have26 else f26)
        ok("FL26: shipped_calendar has no Argentine league", 30 not in B.shipped_calendar(t26))
        pl, p, seasons, rcal = plan_one(t26, 30, "Argentina")
        ok("FL26: a division under reg 30 is in region 17, division 2", (p["region"], p["tier"]) == (17, 2))
        ok("FL26: ... and plays August-May (no follows_calendar)", not p.get("follows_calendar"))
        ok("FL26: ... no season line", seasons == [])
        first, last = rcal_days(rcal)
        ok("FL26: ... its real calendar runs across New Year (%s)" % rcal[0], first > last)
        pl, p, seasons, rcal = plan_one(t26, 168, "Colombia")
        ok("FL26: a division under Liga BetPlay still follows its calendar, no season line (FL26's list has 19)",
           p.get("follows_calendar") and seasons == [])
    else:
        skip("no FL26 tables (Mod Studio's tables folder)")

    # 5: FL27 tables and folder
    if t27:
        B.use_game(fl27 if have27 else f27)
        if not have27:            # the made-up exe is the empty one now: the fallback has 17
            ok("FL27 (fallback): 17 is a calendar region", 17 in B.CALENDAR_REGIONS)
        ok("FL27: shipped_calendar has the Liga Profesional (the season box shows February-December)",
           30 in B.shipped_calendar(t27))
        pl, p, seasons, rcal = plan_one(t27, 30, "Argentina")
        ok("FL27: a division under reg 30 is in region 17, division 2", (p["region"], p["tier"]) == (17, 2))
        ok("FL27: ... and follows the February-December season", p.get("follows_calendar") is True)
        ok("FL27: ... the world file says `season 17 1` (%s)" % seasons, seasons == ["season 17 1"])
        first, last = rcal_days(rcal)
        ok("FL27: ... its real calendar starts after the day-41 join and ends before New Year (%s)" % rcal[0],
           41 < first < last < 360)
        ok("FL27: ... the plan says it plays February to December",
           "plays February to December with the league above it" in B.describe(pl))
        pl, p, seasons, rcal = plan_one(t27, 168, "Colombia")
        ok("FL27: a division under Liga BetPlay as before: follows, no season line",
           p.get("follows_calendar") and seasons == [])
    else:
        skip("no FL27 tables (Mod Studio's tables27 folder)")

    B.use_game(None)
    print("all passed (%d)%s" % (N, "; skipped: " + "; ".join(SKIPPED) if SKIPPED else ""))


if __name__ == "__main__":
    main()
