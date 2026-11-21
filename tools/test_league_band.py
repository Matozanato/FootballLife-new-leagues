r"""python tools/test_league_band.py [folder with the game's tables]

The league band, regulation ids 320..499 (wall97: the 97-league wall). Past the 97 ids a world of
ours had -- 36 with a slot of their own, 3 with none, 58 on 197..254 -- a league takes an id of the
band: 320..387 on the last free Select Team slots 182..249, then 388..499 on slots 250..361 (B346).
Past those 277 the top band, 920..1022 (band-wide): 103 more, 380 leagues, on when the game's caps
set dates it (leaguebuilder.TOP_BAND); on Select Team slots 362..464 (slots-wide: FL 2027's
fl26slots250.fl27.lua makes 465).

Offline:
  1. datecave: a set whose date keys all stay below 256 gets the stub it always had, byte for byte
     (the one in sider/fl26caps.lua and sider/fl26caps.fl27.lua); a key of the band makes the
     table 1024 bytes and changes `cmp eax, 256` to 1024 and nothing else, ids 1..255 keep their
     bytes, the stub still fits its page, and both bands are dated; 1024 and up are refused;
  2. fl26world: the band's ids and slots, no slot used twice, the band ranked after every id of the
     97 and the top band after the band; band_shift is the day shift the shipped sets give 197..255;
     leaguebuilder.dates_top_band tells a caps module that dates the top band from one that does not;
  3. leaguebuilder.DATE_SHIFT knows every league key of both tracked caps sets with the set's own
     shift, and the band; plan()'s European-day choice still sees 197..254 as before;
  4. the modules: fl26comptab's row guard is 1024 and lets two leagues of ours of one country
     share a slot; fl26join keeps its per-id memory for ids up to 1023; fl26chain's caps agree with
     fl26chain.lua; fl26slots: FL 2027's module makes SLOT_COUNT slots on one allocation, the
     NSLOTS of fl26comptab / fl26editlist agree, FL26's stays at 362, and mkslots still makes
     the 362-slot modules byte for byte (their careers);
With the tables (default %APPDATA%\FL26ModStudio\tables), plan level, no game:
  5. a world of up to 97 leagues gets exactly the ids, slots and competition ids it gets without the
     band (the recipes of testdata\ and a 97-league one);
  6. the 98th league takes 320 on slot 182; a world of 250 (the competition id pool widened for the
     test -- cids are the next wall) uses 320..387 on 182..249, then the shared ids, each on its
     country's own slot or none, a country's lower divisions on shared ids first so every top league
     keeps a slot of its own; Build's room message counts 277;
  7. free_comp_ids gives a cup no id of either band (255..319, 500..919, 1023);
  8. the top band: it changes nothing for a world of up to 277 leagues (the recipes, 250); 380
     leagues use 920..1022, each on its own slot 362..464, every league in Select Team but the
     ones on 183..185; Build's room message counts 380; a 272-league world grown to 380 keeps every id it
     had (the hard rule: only new leagues take new ids); a league on 920.. with the band off stops
     the Build instead of moving; an old world's cup on 920.. keeps its id and no league takes it;
  9. the slots the game has (leaguebuilder.slot_count, fl26world.set_slot_count): read from the
     installed fl26slots250.lua and the pack's copy (the fewer), 362 without either, FL26_SLOTS
     says it; a 380-league world built with 362 slots and Built again with 465 keeps every id and
     its top-band leagues get their slots; 465 slots with the band off still leave room for 277
     (slots alone do not turn the band on); with 400 the slotted top ids go first.
From section 2 on the run is FL 2027 with its new fl26slots (set_slot_count(465)).
"""
import contextlib, copy, glob, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import datecave
import fl26world as W
import leaguebuilder as B

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def stub_of(lua):
    """(stub bytes, {id: calendar byte}) of the date-stub patch in a caps module"""
    p = os.path.join(ROOT, "sider", lua)
    if not os.path.exists(p):                # an old set kept as a test fixture (mszip ships sider's sets only)
        p = os.path.join(ROOT, "tools", "testdata", "caps", lua)
    s = open(p, encoding="utf-8").read()
    m = re.search(r'\{va=0x163000000, old="0*", new="([0-9a-f]+)", why="[^"]*\(([^)]*)\)"', s)
    offs = {}
    for part in m.group(2).split(", "):
        k, v = part.split(":")
        kind, sh = v.split("+")
        offs[int(k)] = (datecave.CUP_BIT if kind == "cup" else 0) | int(sh)
    return bytes.fromhex(m.group(1)), offs


# the sets below 256 the band is laid over. The FL27 install copy is the wide set itself since
# 6fc38dd (cidwide, regions: the one the game runs), so the old FL27 set stands in for it here.
NARROW = ("fl26caps.lua", "fl26caps.teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar.fl27.lua")


def offline():
    # 1. datecave
    for lua in NARROW:
        shipped, offs = stub_of(lua)
        code, code_len = datecave.build(offs)
        ok("1. %s: the stub of a set below 256 is the one it always had" % lua, code == shipped)
        wide = dict(offs)
        wide.update(W.band_date_offsets())
        c2, l2 = datecave.build(wide)
        ok("1. %s with the band: code 0x64 + table 1024 = 0x%x, still on its page" % (lua, len(c2)),
           l2 == code_len == 0x64 and len(c2) == 0x464 and datecave.CAVE + len(c2) <= datecave.CAVE_END)
        ok("1. %s with the band: only the cmp's imm32 changes in the code (256 -> 1024)" % lua,
           [i for i in range(l2) if c2[i] != code[i]] == [5] and c2[4:8] == (1024).to_bytes(4, "little"))
        ok("1. %s with the bands: ids 1..255 keep their bytes, 256..319, 500..919 and 1023 have no calendar" % lua,
           c2[l2:l2 + 256] == code[code_len:]
           and all(c2[l2 + k] == datecave.NO_CALENDAR
                   for k in list(range(256, 320)) + list(range(500, 920)) + [1023]))
        ok("1. %s with the bands: 320..499 and 920..1022 carry band_shift" % lua,
           all(c2[l2 + k] == W.band_shift(k) for k in W.LEAGUE_IDS) and len(W.LEAGUE_IDS) == 283)
    try:
        datecave.build({1024: 0})
        refused = False
    except SystemExit as e:
        refused = "1..1023" in str(e)
    ok("1. an id of 1024 is refused (a stage, not a base id)", refused)

    # 2. fl26world
    ok("2. the band: 320..387 with a slot of their own, 388..499 shared but 395 (slot 257)",
       W.EXTRA2_IDS == tuple(range(320, 388)) and W.SHARED_IDS == tuple(r for r in range(388, 500) if r != 395)
       and set(W.EXTRA2_IDS) | set(W.SHARED_IDS) | {395} == set(W.LEAGUE_BAND))
    ok("2. mp40: no league on slot 257, the game's own \"Other\" heading (395 goes to none)",
       W.SKIP_IDS == (395,) and 257 not in W.DEFAULT_SLOT.values() and 395 not in W.DEFAULT_SLOT)
    ok("2. 320 -> slot 182 ... 387 -> 249 (the last ones fl26slots250 has)",
       W.EXTRA2_SLOT[320] == 182 and W.EXTRA2_SLOT[387] == 249 and W.DEFAULT_SLOT[387] == 249)
    shared_ok = {49, 112}           # fl26comptab SHARED_OK: 49 with 177, 145 and 190 on 112
    used = [s for r, s in W.DEFAULT_SLOT.items() if s not in shared_ok]
    ok("2. no Select Team slot is handed out twice", len(used) == len(set(used)))
    ok("2. B346: the shared ids have slots of their own too, 388 -> 250 ... 499 -> 361 (fl26slots250's 362), 257 left out",
       [W.DEFAULT_SLOT[r] for r in W.SHARED_IDS] == [s for s in range(250, 362) if s != 257])
    old = [r for r in list(W.DEFAULT_SLOT) + list(W.NO_SLOT_IDS) if r not in W.LEAGUE_BAND and r not in W.TOP_BAND]
    ok("2. the band ranks after every id of the 97, its shared ids last",
       max(W.id_rank(r) for r in old) < min(W.id_rank(r) for r in W.EXTRA2_IDS)
       and max(W.id_rank(r) for r in W.EXTRA2_IDS) < min(W.id_rank(r) for r in W.SHARED_IDS))
    ok("2. band_shift is the shipped sets' 197..255 (197 +2, 199 +0, 200 +6, 255 +0)",
       [W.band_shift(r) for r in (197, 198, 199, 200, 255)] == [2, 1, 0, 6, 0])
    ok("2. the top band: 920..1022, 103 ids, none of the 277 nor 1023, all below the 10-bit wall",
       W.TOP_IDS == tuple(range(920, 1023)) and not set(W.TOP_IDS) & (set(W.DEFAULT_SLOT) - set(W.TOP_SLOT))
       and not set(W.TOP_IDS) & set(W.LEAGUE_BAND) and max(W.TOP_IDS) < W.BASE_ID_LIMIT - 1)
    ok("2. without a game the slots are fl26slots' 362 (SLOT_BASE): the top band has none",
       W.SLOT_COUNT == W.SLOT_BASE == 362 and W.TOP_SLOT == {} and not any(r in W.DEFAULT_SLOT for r in W.TOP_IDS))
    W.set_slot_count(W.SLOT_MAX)            # the rest of the run: FL 2027 with its 465-slot fl26slots
    ok("2. slots-wide: the top band has slots of its own, 920 -> 362 ... 1022 -> 464 (SLOT_COUNT 465)",
       W.SLOT_COUNT == 465 and [W.DEFAULT_SLOT[r] for r in W.TOP_IDS] == list(range(362, 465))
       and W.TOP_SLOT == {r: W.DEFAULT_SLOT[r] for r in W.TOP_IDS}
       and max(W.DEFAULT_SLOT.values()) == W.SLOT_COUNT - 1)
    ok("2. slots-wide: every id below the top band keeps the slot it had (0..361)",
       all(s < 362 for r, s in W.DEFAULT_SLOT.items() if r not in W.TOP_BAND)
       and [W.DEFAULT_SLOT[r] for r in W.SHARED_IDS] == [s for s in range(250, 362) if s != 257]
       and [W.DEFAULT_SLOT[r] for r in W.EXTRA_IDS] == list(range(124, 182)))
    ok("2. the top band ranks after the whole band",
       max(W.id_rank(r) for r in W.LEAGUE_BAND) < min(W.id_rank(r) for r in W.TOP_IDS))
    # the FL27 install copy dates both bands since limits-headroom (07.11.); the set before it,
    # d7699e7a (the Megapack season's), the band 320..499 only
    lua27 = os.path.join(ROOT, "sider", "fl26caps.fl27.lua")
    _, offs_now = stub_of("fl26caps.fl27.lua")
    ok("2. dates_top_band: the FL27 install copy dates the top band, both bands at their shifts",
       B.dates_top_band(lua27) and all(offs_now.get(r) == W.band_shift(r) for r in W.LEAGUE_IDS))
    old27 = ("fl26caps.teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar-pk32-standings"
             "-cidwide-regions.fl27.elem4.teams8000.coaches10000.m131000.f30000.lua")
    _, offs27 = stub_of(old27)
    ok("2. dates_top_band: the FL27 set before it (the band 320..499 only) does not date the top band",
       offs27.get(499) == W.band_shift(499) and not B.dates_top_band(os.path.join(ROOT, "tools", "testdata", "caps", old27)))
    wide = dict(offs27)
    wide.update(W.band_date_offsets())
    code, _ = datecave.build(wide)
    tmp = os.path.join(os.environ.get("TEMP") or os.environ.get("TMP") or ".", "test_league_band_caps.lua")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write('  {va=0x163000000, old="%s", new="%s", why="fixture dates"},\n' % ("00" * len(code), code.hex()))
    try:
        ok("2. dates_top_band: a set whose stub dates 920..1022 does", B.dates_top_band(tmp))
    finally:
        os.remove(tmp)

    # 3. DATE_SHIFT
    for lua in NARROW:
        _, offs = stub_of(lua)
        leagues = {k: v for k, v in offs.items() if not v & datecave.CUP_BIT and k in B.DATE_SHIFT}
        missing = [k for k, v in offs.items() if not v & datecave.CUP_BIT and k not in B.DATE_SHIFT]
        ok("3. DATE_SHIFT has the shift of every league key of %s (%d), none missing but 186..196 and"
           " 255 (never handed out)" % (lua, len(leagues)),
           all(B.DATE_SHIFT[k] == v for k, v in leagues.items())
           and all(186 <= k <= 196 or k == 255 for k in missing))
    ok("3. DATE_SHIFT knows both bands", all(B.DATE_SHIFT[r] == W.band_shift(r) for r in W.LEAGUE_IDS))
    ok("3. league_days now has days for 197..254, plan()'s European choice still none",
       B.league_days(200, 30) and not B.pick_days(200, 30) and B.pick_days(320, 30) == B.league_days(320, 30))

    # 4. the modules
    lua = open(os.path.join(ROOT, "sider", "experimental", "fl26comptab.lua"), encoding="utf-8").read()
    ok("4. fl26comptab: the row guard is 1024, not 255",
       "local MAX_ROWS = 1024" in lua and "if n > MAX_ROWS then" in lua and "n > 255" not in lua)
    ok("4. fl26comptab: two leagues of ours of one country may share a slot, others still abort",
       "ID_COUNTRY[id] == ID_COUNTRY[mine[sl]]" in lua and "asked for twice" in lua)
    join = open(os.path.join(HERE, "native", "fl26join.c"), encoding="utf-8").read()
    ok("4. fl26join: per-id memory for every base id, no 256 guard left",
       "#define ID_SLOTS  1024" in join and "[256]" not in join and "< 256" not in join
       and re.search(r"#define MAX_IDS\s+1024", join) and re.search(r"#define MAX_LIST\s+8192", join))
    chain = open(os.path.join(HERE, "native", "fl26chain.c"), encoding="utf-8").read()
    chlua = open(os.path.join(ROOT, "sider", "experimental", "fl26chain.lua"), encoding="utf-8").read()
    for k in ("MAX_CUPS", "MAX_CHAINS"):
        ok("4. fl26chain: %s the same in the DLL and the module" % k,
           re.search(r"#define %s\s+(\d+)" % k, chain).group(1) == re.search(r"^local %s = (\d+)" % k, chlua, re.M).group(1))
    swiss = open(os.path.join(HERE, "native", "fl26swiss.c"), encoding="utf-8").read()
    ok("4. fl26swiss: MAX_OUR_LEAGUES, MAX_JULY and MAX_RCAL hold 250 leagues with room",
       all(int(re.search(r"#define %s\s+(\d+)" % k, swiss).group(1)) >= 512 for k in ("MAX_OUR_LEAGUES", "MAX_JULY", "MAX_RCAL")))

    # fl26slots (slots-wide)
    import mkslots
    exp = os.path.join(ROOT, "sider", "experimental")
    s27 = open(os.path.join(exp, "fl26slots250.fl27.lua"), encoding="utf-8").read()
    s26 = open(os.path.join(exp, "fl26slots250.lua"), encoding="utf-8").read()
    n27 = int(re.search(r"competition slots 123 -> (\d+)", s27).group(1))
    n26 = int(re.search(r"competition slots 123 -> (\d+)", s26).group(1))
    size = re.search(r'VirtualAlloc\(ffi\.cast\("void\*", page\), (0x[0-9a-f]+), kind', s27).group(1)
    ok("4. fl26slots: FL 2027's module makes SLOT_COUNT (465) slots, its tables on one allocation of "
       "0x2000 from 0x163400000; FL26's stays at 362",
       n27 == W.SLOT_COUNT == 465 and n26 == 362 and int(size, 16) == mkslots.tables_at(465)[2] == 0x2000
       and "local PAGES = { 0x163400000 }" in s27)
    nsl = [int(re.search(r"^local NSLOTS = (\d+)", open(os.path.join(exp, f), encoding="utf-8").read(), re.M).group(1))
           for f in ("fl26comptab.lua", "fl26editlist.lua")]
    ok("4. fl26comptab / fl26editlist: NSLOTS is SLOT_COUNT", nsl == [W.SLOT_COUNT] * 2)
    ok("4. leaguebuilder.slots_in reads what each module makes: FL 2027's 465 (SLOT_MAX), FL26's 362",
       B.slots_in(os.path.join(exp, "fl26slots250.fl27.lua")) == W.SLOT_MAX == 465
       and B.slots_in(os.path.join(exp, "fl26slots250.lua")) == 362 and B.slots_in(os.path.join(exp, "nope.lua")) is None)
    ok("4. mkslots: 362 slots still on one page with the tables at +0x300 (the bytes B346 shipped), "
       "416 the last that fits one page, past 379 the sentinel test takes the whole register",
       mkslots.tables_at(362) == (mkslots.PAGE + 0x300, mkslots.PAGE + 0x300 + 0x5b0, 0x1000)
       and mkslots.tables_at(416)[2] == 0x1000 and mkslots.tables_at(417)[2] == 0x2000
       and "83f87b" in s27.split("get accessor body")[0].split("{va=0x163400000")[-1]
       and "3c7b" in s26.split("get accessor body")[0].split("{va=0x163400000")[-1])


def band_off():
    """fl26world as it was before the band: what a world of the 97 must not tell apart"""
    saved = (dict(W.DEFAULT_SLOT), W.SHARED_IDS)
    for r in list(W.EXTRA2_SLOT) + list(W.SHARED_SLOT):
        W.DEFAULT_SLOT.pop(r, None)
    W.SHARED_IDS = ()
    return saved


def band_on(saved):
    W.DEFAULT_SLOT.clear()
    W.DEFAULT_SLOT.update(saved[0])
    W.SHARED_IDS = saved[1]


def ids(recipe, base):
    with contextlib.redirect_stdout(io.StringIO()):
        pl = B.plan(copy.deepcopy(recipe), base)
    return {p["name"]: (p["rid"], p["slot"], p["cid"]) for p in pl["leagues"]}, pl


def names_of(base):
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    return sorted({en for fid, (en, _) in cty.items() if en and mkflags.by_name(cty, en) == fid})


def synthetic(n, countries, per=1):
    """n ten-club leagues, `per` divisions in each country (the top one first)"""
    L = []
    for i in range(n):
        L.append({"name": "Band %03d" % i, "country": countries[i // per], "clubs": 10, "legs": 2})
        if i % per:
            L[-1]["above"] = "Band %03d" % (i - 1)
    return {"world": "_FL26Band", "leagues": L}


def with_tables(tables):
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    countries = names_of(base)

    # 5. a world of the 97 does not see the band
    recipes = sorted(glob.glob(os.path.join(HERE, "testdata", "*", "*.json")))
    for path in recipes:
        r = json.load(open(path, encoding="utf-8"))
        with_band, _ = ids(r, base)
        saved = band_off()
        try:
            without, _ = ids(r, base)
        finally:
            band_on(saved)
        ok("5. %s: the same ids, slots and cids with the band and without" % os.path.basename(path),
           with_band == without)
    r97 = synthetic(97, countries)
    with_band, _ = ids(r97, base)
    saved = band_off()
    try:
        without, _ = ids(r97, base)
    finally:
        band_on(saved)
    ok("5. 97 leagues: the same ids, slots and cids with the band and without, none in the band",
       with_band == without and not any(v[0] in W.LEAGUE_BAND for v in with_band.values()))

    # 6. past the 97
    got, _ = ids(synthetic(98, countries), base)
    ok("6. the 98th league takes 320, on slot 182", got["Band 097"][:2] == (320, 182))
    pool, room = B.W.cid_pool, B.clubs_room
    B.W.cid_pool = lambda *a, **k: list(range(130, 1000))      # cids are the next wall, not this one
    B.clubs_room = lambda base: 10 ** 6
    try:
        _g, few = ids(synthetic(160, countries, per=3), base)
        got, pl = ids(synthetic(250, countries, per=3), base)
        try:
            ids(synthetic(277, countries, per=3), base)
            stop = ""
        except B.BuildError as e:
            stop = str(e)
    finally:
        B.W.cid_pool, B.clubs_room = pool, room
    rid = {p["rid"]: p for p in pl["leagues"]}
    own = {r: rid[r]["slot"] for r in W.EXTRA2_IDS if r in rid}
    ok("6. 250 leagues: the band's own ids from 320 up, each on its own slot (182 ...)",
       own and own == {r: W.EXTRA2_SLOT[r] for r in W.EXTRA2_IDS[:len(own)]})
    first = {}
    for p in pl["leagues"]:
        first.setdefault(p["country"], p)
    late = [p for p in first.values() if p["rid"] in W.LEAGUE_BAND]
    ok("6. 250 leagues (84 countries, three divisions each): the %d top leagues past the 97 each have a "
       "slot of its own, and so do their divisions (B346)" % len(late),
       late and all(p["slot"] not in (W.NO_SLOT, None) for p in late))
    shared = [rid[r] for r in W.SHARED_IDS if r in rid]
    slots = [p["slot"] for p in pl["leagues"] if p["slot"] not in (W.NO_SLOT, 112, 49)]
    ok("6. 250 leagues: %d on the last ids, 97 + %d + %d = 250, each on a slot of its own (B346)"
       % (len(shared), len(own), len(shared)),
       97 + len(own) + len(shared) == 250 and shared
       and all(p["slot"] == W.SHARED_SLOT[p["rid"]] for p in shared) and len(slots) == len(set(slots)))
    ok("6. 160 leagues (own slots for all): none on a shared id (B346: a shared slot plays the first league's clubs)",
       not [p for p in few["leagues"] if p["rid"] in W.SHARED_IDS])
    ok("6. 250 leagues: no league outside the dated ids (1..255 of the 97, the band)",
       all(r in W.DEFAULT_SLOT or r in W.NO_SLOT_IDS or r in W.SHARED_IDS for r in rid))
    ok("6. 277 leagues: Build says the game has room for 276 (the top band off)", "has room for 276" in stop)

    # 7. cups
    _cids, regs = B.free_comp_ids(base)
    ok("7. a cup gets no id of either band (255..319 first, then 500..919, 1023)",
       not set(regs) & set(W.LEAGUE_IDS) and regs[0] == 255 and 500 in regs and 919 in regs
       and 1023 in regs and len([r for r in regs if r >= 500]) == 421)

    # 8. the top band
    B.W.cid_pool = lambda *a, **k: list(range(130, 1000))
    B.clubs_room = lambda base: 10 ** 6
    try:
        B.TOP_BAND = True
        on250, _ = ids(synthetic(250, countries, per=3), base)
        on_recipes = [ids(json.load(open(p, encoding="utf-8")), base)[0] for p in recipes]
        _g, pl272 = ids(synthetic(272, countries, per=4), base)
        _g, pl380 = ids(synthetic(379, countries, per=4), base)
        with contextlib.redirect_stdout(io.StringIO()):
            pl_grown = B.plan(copy.deepcopy(synthetic(379, countries, per=4)), base, prev=pl272)
        try:
            ids(synthetic(380, countries, per=4), base)
            stop = ""
        except B.BuildError as e:
            stop = str(e)
        old_cup = dict(pl272, cup_ids={"cup:Band 000": {"cid": 990, "reg": 930}})
        with contextlib.redirect_stdout(io.StringIO()):
            pl_cup = B.plan(copy.deepcopy(synthetic(378, countries, per=4)), base, prev=old_cup)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                B.plan(copy.deepcopy(synthetic(379, countries, per=4)), base, prev=old_cup)
            cup_stop = ""
        except B.BuildError as e:
            cup_stop = str(e)
        B.TOP_BAND = False
        off250, _ = ids(synthetic(250, countries, per=3), base)
        off_recipes = [ids(json.load(open(p, encoding="utf-8")), base)[0] for p in recipes]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                B.plan(copy.deepcopy(synthetic(379, countries, per=4)), base, prev=pl380)
            refused = ""
        except B.BuildError as e:
            refused = str(e)
    finally:
        B.TOP_BAND = False
        B.W.cid_pool, B.clubs_room = pool, room
    ok("8. the top band changes nothing for a world of up to 277 (250 leagues, %d recipes)" % len(recipes),
       on250 == off250 and on_recipes == off_recipes and not any(v[0] in W.TOP_BAND for v in on250.values()))
    top = [p for p in pl380["leagues"] if p["rid"] in W.TOP_BAND]
    ok("8. 379 leagues: 920..1022 all taken, 103 leagues there, each on its own slot 362..464",
       sorted(p["rid"] for p in top) == list(W.TOP_IDS)
       and sorted(p["slot"] for p in top) == list(range(362, 465))
       and all(p["slot"] == W.DEFAULT_SLOT[p["rid"]] for p in top))
    ok("8. 379 leagues: every league in Select Team (no league on the no-slot value past the 97's 183..185)",
       all(p["slot"] != W.NO_SLOT or p["rid"] in W.NO_SLOT_IDS for p in pl380["leagues"]))
    first = {}
    for p in pl380["leagues"]:
        first.setdefault(p["country"], p)
    ok("8. 379 leagues (95 countries, four divisions): no country's top league is slotless (only on the "
       "ids of the 97 that never had a slot, 183..185)",
       all(p["rid"] in W.NO_SLOT_IDS for p in first.values() if p["slot"] == W.NO_SLOT))
    slots = [p["slot"] for p in pl380["leagues"] if p["slot"] not in (W.NO_SLOT, 112, 49)]
    ok("8. 379 leagues: no slot handed out twice, every league on a dated id",
       len(slots) == len(set(slots)) and all(B.DATE_SHIFT.get(p["rid"]) is not None for p in pl380["leagues"]))
    ok("8. 380 leagues: Build says the game has room for 379", "has room for 379" in stop)
    was = {p["name"]: (p["rid"], p["cid"]) for p in pl272["leagues"]}
    now = {p["name"]: (p["rid"], p["cid"]) for p in pl_grown["leagues"]}
    new = [now[n][0] for n in now if n not in was]
    ok("8. 272 leagues grown to 379: all 272 keep their regulation and competition ids, the 107 new take "
       "the rest",
       len(was) == 272 and all(now[n] == was[n] for n in was) and len(new) == 107
       and set(W.TOP_IDS) <= set(new) and not set(new) & {v[0] for v in was.values()})
    ok("8. a league on 920.. with the band off: the Build stops, nothing moves",
       "920..1022" in refused and "does not date" in refused)
    _c, kept = B.free_comp_ids(base, keep={930, 2})
    ok("8. a cup of the last Build on the top band (930, cups took 500..1023 before) keeps it; the "
       "rest of the band stays for leagues",
       930 in kept and not set(kept) & (set(W.TOP_BAND) - {930}) and 2 not in kept)
    ok("8. ... and no league takes it: 378 leagues fit around it, the 379th finds the room is 378",
       930 not in [p["rid"] for p in pl_cup["leagues"]] and "has room for 378" in cup_stop)

    # 9. the slots the game has
    was_env = os.environ.get("FL26_SLOTS")
    os.environ["FL26_SLOTS"] = "400"
    try:
        ok("9. slot_count: FL26_SLOTS says it without a game", B.slot_count(None) == 400)
    finally:
        if was_env is None:
            os.environ.pop("FL26_SLOTS", None)
        else:
            os.environ["FL26_SLOTS"] = was_env
    B.W.cid_pool = lambda *a, **k: list(range(130, 1000))
    B.clubs_room = lambda base: 10 ** 6
    try:
        B.TOP_BAND = True
        W.set_slot_count(W.SLOT_BASE)
        none362 = dict(W.TOP_SLOT)
        _g, p362 = ids(synthetic(379, countries, per=4), base)
        W.set_slot_count(W.SLOT_MAX)
        with contextlib.redirect_stdout(io.StringIO()):
            again = B.plan(copy.deepcopy(synthetic(379, countries, per=4)), base, prev=p362)
        B.TOP_BAND = False
        try:
            ids(synthetic(277, countries, per=4), base)
            off_stop = ""
        except B.BuildError as e:
            off_stop = str(e)
        B.TOP_BAND = True
        W.set_slot_count(400)
        top400 = dict(W.TOP_SLOT)
        _g, s400 = ids(synthetic(379, countries, per=4), base)
        _g, s300 = ids(synthetic(300, countries, per=4), base)
    finally:
        B.TOP_BAND = False
        W.set_slot_count(W.SLOT_MAX)
        B.W.cid_pool, B.clubs_room = pool, room
    ok("9. 362 slots (an FL 2027 fl26slots from before slots-wide): 379 leagues still take all 103 top ids, "
       "on no slot",
       none362 == {} and sorted(p["rid"] for p in p362["leagues"] if p["rid"] in W.TOP_BAND) == list(W.TOP_IDS)
       and all(p["slot"] == W.NO_SLOT for p in p362["leagues"] if p["rid"] in W.TOP_BAND))
    ok("9. built with 362 slots, Built again with 465: every regulation and competition id kept, the top "
       "band's leagues on 362..464",
       [(p["name"], p["rid"], p["cid"]) for p in again["leagues"]]
       == [(p["name"], p["rid"], p["cid"]) for p in p362["leagues"]]
       and sorted(p["slot"] for p in again["leagues"] if p["rid"] in W.TOP_BAND) == list(range(362, 465)))
    ok("9. 465 slots but the top band off (no dates): 277 leagues find room for 276 -- slots alone do not "
       "turn the band on", "has room for 276" in off_stop)
    t400 = [p for p in s400["leagues"] if p["rid"] in W.TOP_BAND]
    ok("9. 400 slots: 920..957 on 362..399, 958..1022 none; 379 leagues still take all 103 ids",
       top400 == {r: 362 + i for i, r in enumerate(W.TOP_IDS[:38])} and len(t400) == 103
       and sum(p["slot"] != W.NO_SLOT for p in t400) == 38)
    ok("9. 400 slots, 300 leagues: the 24 past 276 take the slotted top ids first (920..943)",
       sorted(p["rid"] for p in s300["leagues"] if p["rid"] in W.TOP_BAND) == list(range(920, 944)))


def main(argv):
    offline()
    tables = argv[1] if len(argv) > 1 else os.path.expandvars(r"%APPDATA%\FL26ModStudio\tables")
    if os.path.isdir(tables):
        with_tables(tables)
    else:
        print("skip - the plan checks (give the folder with the game's tables)")
    print("all passed (%d)" % N)


if __name__ == "__main__":
    main(sys.argv)
