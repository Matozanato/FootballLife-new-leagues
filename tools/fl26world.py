r"""python fl26world.py --root <livecpk world> [--base <pesdb dir>] [--countries FILE] [--out FILE]
                      [--uefa sider/fl26swiss.lua]
   python fl26world.py --show <fl26world.txt>

The world file: one plain-text description of the leagues a world adds, read by every module
that used to carry its own hard-coded list (fl26joindll, fl26chain, fl26comptab, fl26editlist,
fl26kickofflist, fl26catlist, fl26clubs, fl26slotnames, fl26swiss). The league builder writes
it when it builds a world; this writes it for a world that already exists, from the world's own
competition tables. See docs/developers/mod-studio.md.

    # fl26world 1
    world _FL26BiH
    league 11 cid=130 region=60 country=198 slot=28 tier=1 promote=0 demote=2 clubs=12 legs=3 name=Premijer Liga BiH
    league 49 cid=131 region=60 country=198 slot=49 tier=2 above=11 promote=2 demote=0 clubs=16 legs=2 name=Prva Liga FBiH
    split 109 regular=191 groups=192,193
    uefa 11 1 0 0

What comes from where:
  cid, region, tier, clubs, legs, name   the world's Competition / CompetitionRegulation rows
  above                                  the league whose relegation link (+0x00) names this one,
                                         shipped or ours (Ligue 2 is above France D3)
  splittotal                             under a shipped split season (Jupiler Pro League): the
                                         season's total row, which the game's season end runs on;
                                         fl26chain moves the clubs over it, fl26comptab counts it
  promote / demote                       3 over a link, 0 where there is none -- the counts every
                                         world so far has used
  slot                                   the Select Team slot the regulation id has in the exe
                                         (DEFAULT_SLOT: where fl26comptab puts it, or the exe's
                                         own row); an id not listed gets none
  country                                --countries, else guessed from the league's name against
                                         Country.bin (mkflags.py's rules)
  conf                                   the country's confederation (Country.bin +5: 2 UEFA, 3 AFC,
                                         4 CONMEBOL, 5 CAF, 6 CONCACAF, 7 OFC); the league builder
                                         writes it, this does not (a row built before Mod Studio 0.1.3 says
                                         UEFA whatever the country). fl26catlist gives a region
                                         29..127 that continent's icons on the League Info page
  kickoff                                the slot the league follows in the Kick Off / Edit team
                                         lists (fl26comptab; leaguebuilder kickoff_chain)
  split                                  a split season (tools/mksplit.py): the total's row is the
                                         league line, its phases (format 12 regular, 13..15
                                         groups, same competition) the split line; carry=0 =
                                         the groups start from zero points (Apertura/Clausura)
  gsplit                                 `gsplit <total> regular=<id> groups=<top>,<bottom>`: a
                                         split season of the game's own (the Scottish Premiership
                                         133 / 134 / 135, 136) that a league of the world stands
                                         under (splittotal=). A play-off place named on its
                                         regular phase is the final table's (fl26swiss, B425)
  uefa                                   the UEFA access list: one place per line, regulation,
                                         position, competition (0 UCL, 1 UEL, 2 UECL, 3..5 the
                                         other continents), alt -- fl26swiss's ACCESS format.
                                         --uefa copies the ACCESS table of a module file; with
                                         no uefa line fl26swiss uses the DLL's own list, which
                                         knows the shipped leagues only
  uecl                                   the Conference League's first-season entrants (team ids,
                                         mkuecl.py's pick from this world); written when the
                                         world has the Conference League
  group                                  on a league line: the league is one group of a division
                                         (GitHub #98), its exchange with the division above is the
                                         gset line's (fl26chain), not a chain pair of its own
  gset                                   a group set: the leagues of one division and the groups
                                         below them, `gset <k> up=<id>:<n>,... low=<id>:<n>:<pref>,...`
                                         -- n the clubs each sends (down from the upper ones, up
                                         from the groups), pref the upper league a group's
                                         promoted go to first (0 = none)
  ghome                                  `ghome <league> <team id>,...`: the clubs a group was
                                         built with and its zone_clubs (clubs above of its
                                         region); one relegated into the set goes there when
                                         it has a place, else it is a guest elsewhere and
                                         comes home as soon as a place there is free
  gborder                                `gborder <league> <team id>:<group>,...` (16.11.2026,
                                         the recipe's zone_border): clubs of a group that may
                                         move to the named neighbour group when a relegated
                                         club of the group's region needs the place; in order
  poff                                   a promotion / relegation play-off, `poff <cup> up=<id>
                                         low=<id> [hold=<id>:<place>] entry=<id>:<place>,...`: the
                                         cup's winner ends in up, the club it is played against
                                         (hold, the place's holder by the counts, or the other
                                         club of a tie of two) in low

"Ours" are the league regulations (type 4) the shipped tables do not have. --base is the folder
with the shipped tables (Competition*.bin, Country.bin); default FL26_PESDB, else out/base-pesdb.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import mkleague as M

FORMAT = "# fl26world 1"
KEYS = ("cid", "region", "country", "conf", "slot", "tier", "above", "splittotal", "promote", "demote", "clubs", "legs",
        "cup", "exhibition", "scup", "kickoff", "cupall", "cuptop", "cuplow", "cupn",
        "lcup", "lcuplow", "lcupn", "lcuptop", "cupthird", "pick", "group")
NO_SLOT = 123

# fl26chain.dll keeps this many cups to their leagues (fl26chain.c MAX_CUPS) and drops the rest;
# fl26chain.lua sends the national cups first and the league cups (lcup=) after them
MAX_CHAIN_CUPS = 512                # 16 until B178: eu5's 18th cup, the Greek Cup, played one round;
                                    # 128 until the league band (a cup or two for each of ~150 countries)


def chain_cups(leagues):
    """[(cup, top league, league below, both, cap)] fl26chain.lua's from_world makes of these
    league lines, in its order: the national cups (cup=), then the league cups (lcup=); only
    the first MAX_CHAIN_CUPS reach the DLL"""
    cups, lcups = [], []
    has = lambda L, *ks: all(L.get(k) is not None for k in ks)     # Lua: 0 is true, nil is not
    for L in leagues:
        if has(L, "cup", "cuptop", "cuplow"):
            cups.append((L["cup"], L["cuptop"], L["cuplow"], L.get("cupall") != 0, L.get("cupn")))
        elif has(L, "cup", "above"):
            cups.append((L["cup"], L["above"], L["id"], L.get("cupall") == 1, L.get("cupn")))
        if has(L, "lcup", "lcupn"):
            lcups.append((L["lcup"], L.get("lcuptop") or L["id"], L.get("lcuplow") or 0, True, L["lcupn"]))
    return cups + lcups


def cup_thirds(leagues):
    """[(cup, third division)] fl26chain.lua sends after the cups (fl26_chain_cupthird): a shipped
    cup of the game's two divisions that the first clubs of a new third one join, cupn in all (B228)"""
    return [(L["cup"], L["cupthird"]) for L in leagues
            if L.get("cupthird") and L.get("cup") is not None and L.get("cuptop") is not None]

# The Select Team slot each regulation id mkworld hands out ends up on, in the exe's competition
# parameter table: the ones fl26comptab places (appended rows, and 49/74/100 moved, 76 reshaped)
# and the ones the exe's own row already puts somewhere visible (11 -> 28 and so on). Read off
# the comptab and editlist boot lines of sider.log, 2026-09-27. 145 and 190 share 112 on purpose
# (fl26comptab SHARED_OK); a world has one or the other.
DEFAULT_SLOT = {
    11: 28, 49: 49, 60: 40, 61: 41, 62: 42, 74: 74, 76: 80, 93: 61, 94: 62, 96: 64, 98: 66,
    100: 81, 109: 82, 110: 83, 111: 84, 112: 85, 113: 86, 114: 87, 121: 68, 138: 107, 139: 108,
    140: 109, 143: 110, 144: 111, 145: 112, 146: 113, 170: 22, 171: 29, 173: 43, 174: 69,
    176: 71, 178: 72, 179: 73, 180: 75, 181: 76, 182: 77, 190: 112,
}
# Regulation ids a world may still use, but with no Select Team slot: the league plays its season
# and is not in the Select Team / Kick Off list. Until 28 September these took slots 6, 5 and 4 --
# free in the parameter table, but the list keeps the Asia-Oceania national teams and the two
# Classic Teams entries there, so a 37th-39th league hid them (GitHub #26). fl26comptab refuses
# PROTECTED_SLOTS for the same reason, also in world files written before this.
NO_SLOT_IDS = (183, 184, 185)
PROTECTED_SLOTS = (4, 5, 6)
# Slots the Select Team list fills with a group of the game's own "other clubs" when no league
# sits there (fl26slotnames). Four of our ids land on them, so a big world hid those groups
# (GitHub #73: Other European and Other Latin American gone with 36 leagues). The builder hands
# these ids out last, in this order: the two small groups before the hidden ids above, the two
# big ones (Sparta Prague, APOEL ... / Penarol, LDU Quito ...) only after them.
POOL_SLOTS = {75: "Other Clubs (Africa)", 71: "Other", 73: "Other Latin American Teams",
              69: "Other European Leagues"}
POOL_BEFORE_HIDDEN = (75, 71)
POOL_AFTER_HIDDEN = (73, 69)
# a league's recipe "select_team": the group whose place it takes, whatever the order (vmican
# 02.11.: with a South American world the Other Latin American Teams are of no use)
POOL_PICK = {"europe": 69, "latam": 73, "africa": 75, "other": 71}
# Limits branch: past those, a league takes a regulation id from the top of the date table down
# (254, 253 ... 197) and a Select Team slot of its own above 123. Needs fl26slots250 (slots up
# to 249), fl26slot7 (a club's league slot is a whole byte, not 7 bits) and a caps set whose
# --date-keys include these ids (the shipped set dates 197..255). Handed out after the ids with
# a slot of their own and before the pool and no-slot ids, so no group of the game is hidden.
# 255 stays out: 0xff is "no league" in more than one place. 196 and below are taken: 191..196
# split-season phases (mksplit), 188/189 the Europa play-offs, 186/187 the Conference League,
# and the date stub (datecave.py) knew ids up to 255 only -- so 36 + 3 + 58 = 97 leagues was
# the ceiling of this layout.
EXTRA_IDS = tuple(range(254, 196, -1))
EXTRA_SLOT = {r: 124 + i for i, r in enumerate(EXTRA_IDS)}      # 254 -> 124 ... 197 -> 181
DEFAULT_SLOT.update(EXTRA_SLOT)
# Past the 97: the league band 320..499 (wall97.md, step 2). Above every regulation id a world
# of ours has used so far (cups went up to 309), so no old world or career sees an id change,
# and below 512 as a hedge against a 9-bit use of the base id. Needs the wide date stub
# (datecave.py, 1024-byte table) in a caps set whose --date-keys include the band, with the
# shifts of band_shift(). The first 68 take the last free Select Team slots, 182..249
# (fl26slots250, fl26slot7); the other 112 share a slot: the slot of their country's league that
# has one of its own (leaguebuilder.share_slots, fl26comptab lets two leagues of ours of one
# country share it), or none. Both come after every id above in the free list (id_rank), so a
# world of up to 97 leagues gets exactly the ids and slots it got before the band existed.
LEAGUE_BAND = range(320, 500)
EXTRA2_IDS = tuple(range(320, 388))
EXTRA2_SLOT = {r: 182 + i for i, r in enumerate(EXTRA2_IDS)}    # 320 -> 182 ... 387 -> 249
SHARED_IDS = tuple(range(388, 500))
DEFAULT_SLOT.update(EXTRA2_SLOT)
# B346 (07.11.): a league on a shared slot played its season with the clubs (and the count) of
# the slot's first league -- the game fills a league from its slot's list. So the shared ids get
# slots of their own too, 250..361 (fl26slots250 makes 362 slots; fl26slot7 leaves a club of
# such a league on 7, as a league with no slot); the name stays, for the worlds built before.
SHARED_SLOT = {r: 250 + i for i, r in enumerate(SHARED_IDS)}   # 388 -> 250 ... 499 -> 361
# mp40 (08.11.): slot 257 is the game's own "Other" heading too -- the pseudo-slot Select Team and
# Edit fill with six special teams (0x140cbb7a0, research-findings "fl26editlist"). National 1
# Groupe A of the Megapack sat on it (id 395) and the list showed it as "Other". So the id on
# 257 goes to no league: 111 shared ids, 379 leagues in all. No released world reaches it (166+).
OTHER_SLOT = 257
SKIP_IDS = tuple(r for r, s in SHARED_SLOT.items() if s == OTHER_SLOT)     # (395,)
for _r in SKIP_IDS:
    del SHARED_SLOT[_r]
SHARED_IDS = tuple(r for r in SHARED_IDS if r not in SKIP_IDS)
DEFAULT_SLOT.update(SHARED_SLOT)
# Past the 276 (band-wide, 07.11.; 277 before SKIP_IDS): the top band 920..1022, 103 more leagues, 379 in all. Not
# above the band: the cups have had 500.. since the band came (the Megapack's go up to ~710), so
# a league there would take the id of a cup a career already holds. The top of the base-id space
# (a regulation id is stage << 10 | base id, 1..1023) is the one stretch no world's cup can have
# reached -- free_comp_ids hands out 255..319, then 500 upward, and 920 is 486 cup ids away --
# and from now on no cup takes it. 1023 (all ten bits) stays out. The 512 hedge of the band above
# is spent: the cups of the 199-league FL27 world of B346's in-game check sit on 500..657, so the
# game takes a base id past 511 for a competition; a LEAGUE past 511 is for the in-game test. The cups keep 255..319,
# 500..919 and 1023: 486 ids, ~390 for the cups of 380 leagues. Ranked after every id above
# (id_rank), so a world of up to 277 leagues gets exactly the ids and slots it got before.
# Needs a caps set whose date stub dates 920..1022 (band_date_offsets; leaguebuilder.use_game
# turns the band on only then) and, for Select Team, slots past the 362: SLOT_COUNT is what the
# installed fl26slots makes, and a top id past it has no slot (NO_SLOT, as 183..185: the league
# plays its season and is not in the Select Team list). slots-wide (07.11., mato: every league in
# Select Team): FL 2027's fl26slots250.fl27.lua makes 465, so 920 -> 362 ... 1022 -> 464, a slot
# of its own for every top id; slots 0..361 keep their numbers. FL26's copy stays at 362 (FL26
# gets fixes only, and no FL26 caps set dates the top band, so no FL26 world has a league there).
TOP_BAND = range(920, 1023)
TOP_IDS = tuple(TOP_BAND)
# SLOT_COUNT is what the game's fl26slots makes, read at Build (leaguebuilder.slot_count ->
# set_slot_count): 465 with FL 2027's new module, 362 with FL26's or an FL 2027 one installed before
# slots-wide; 362 until then (no game: tests, the command line). A top id past it has no slot.
TOP_SLOT_FROM = 362     # the first slot past SHARED_SLOT's
SLOT_BASE = 362         # fl26slots250 since B346, FL26's copy still
SLOT_MAX = TOP_SLOT_FROM + len(TOP_IDS)      # 465: fl26slots250.fl27.lua (mkslots.py 465), comptab / editlist NSLOTS
SLOT_COUNT = SLOT_BASE
TOP_SLOT = {}


def set_slot_count(n):
    """the installed fl26slots makes `n` slots: the top ids below it get theirs (TOP_SLOT, in
    DEFAULT_SLOT: 920 -> 362 ... 1022 -> 464), the rest none. Returns TOP_SLOT"""
    global SLOT_COUNT, TOP_SLOT
    for r in TOP_SLOT:
        DEFAULT_SLOT.pop(r, None)
    SLOT_COUNT = max(SLOT_BASE, min(int(n), SLOT_MAX))
    TOP_SLOT = {r: TOP_SLOT_FROM + i for i, r in enumerate(TOP_IDS) if TOP_SLOT_FROM + i < SLOT_COUNT}
    DEFAULT_SLOT.update(TOP_SLOT)
    return TOP_SLOT


BASE_ID_LIMIT = 1024    # regulation base ids are 10 bits (the date stub's table, fl26join, comptab)
LEAGUE_IDS = tuple(LEAGUE_BAND) + TOP_IDS     # every id past the 97 a league may take


def band_shift(r):
    """the date stub's day shift (0..6) for an id of EXTRA_IDS, LEAGUE_BAND or TOP_BAND: 197 +2,
    198 +1, 199 +0, 200 +6 ... down by one a day, as the shipped sets date 197..255, and on through
    the bands (320 +5, 321 +4 ... 920 +0, 921 +6 ...). The caps set's --date-offsets for them."""
    return (199 - r) % 7


def band_date_offsets(top=True):
    """{regulation id: day shift} for the band 320..499 and (`top`) the top band 920..1022: what
    a caps set's --date-keys / --date-offsets add for them"""
    return {r: band_shift(r) for r in (LEAGUE_IDS if top else LEAGUE_BAND)}


def pool_rid(slot):
    """the regulation id whose Select Team slot is that group's (POOL_SLOTS)"""
    return next((r for r, s in DEFAULT_SLOT.items() if s == slot), None)


def id_rank(r):
    """sort key of a regulation id in the builder's free list: a slot of its own first, then the
    slots of the two small "other clubs" groups, the ids with no slot, the two big groups, then
    the league band: its ids with a slot of their own, then the ones that share one, then the
    top band (920..1022) last of all"""
    if r in EXTRA2_SLOT:
        return (4, 0)           # the band, after every id of the 97 ...
    if r in SHARED_IDS:
        return (5, 0)           # ... and the ids that share a slot after the ones with their own
    if r in TOP_BAND:
        return (6, 0 if r in TOP_SLOT else 1)   # ... and the top band after the whole 277
    s = DEFAULT_SLOT.get(r)
    if s is None:
        return (2, 0)
    if r in EXTRA_SLOT:
        return (0, 1)           # after the shipped slots, before any id that hides a group
    if s in POOL_BEFORE_HIDDEN:
        return (1, POOL_BEFORE_HIDDEN.index(s))
    if s in POOL_AFTER_HIDDEN:
        return (3, POOL_AFTER_HIDDEN.index(s))
    return (0, 0)


# The competitions of a uefa line (fl26swiss's ACCESS comment): the number is what the line
# carries, the name what a person picks.
COMPETITIONS = [(0, "Champions League"), (10, "Champions League qualifying"), (1, "Europa League"),
                (11, "Europa League qualifying"), (2, "Conference League"), (12, "Conference League qualifying"),
                (3, "Libertadores"), (4, "Libertadores qualifying"), (5, "AFC Champions League")]
# 10, 11, 12: the play-offs in August, sixteen clubs each. The Champions League's eight winners
# join it and its eight losers the Europa League; the Europa League's winners join it and its
# losers the Conference League; the Conference League's winners join it and its losers are out.
# So with all three, 28 / 20 / 20 direct entrants.
UCLQ, UELQ, UECLQ, PLAYOFF = 10, 11, 12, 16
# each play-off: (the competition its winners join, the one its losers drop to or None)
PLAYOFFS = {UCLQ: (0, 1), UELQ: (1, 2), UECLQ: (2, None)}
UEFA_LINE = {c for c, _n in COMPETITIONS}        # the ones a uefa line carries

# Logical Mod Studio access targets for the modern CONMEBOL stages.
# These are NOT competition ids from the game and deliberately are not
# part of UEFA_LINE. League Builder consumes them before fl26world.txt
# is written.
LIB_F1, LIB_F2, LIB_F3, SUD_FIRST = 16, 17, 18, 19

# logical id -> (UI name, legacy/native target, internal stage)
CONMEBOL_STAGE_TARGETS = {
    LIB_F1: ("Libertadores - Phase 1", 4, "phase1"),
    LIB_F2: ("Libertadores - Phase 2", 4, "phase2"),
    LIB_F3: ("Libertadores - Phase 3", 4, "phase3"),
    SUD_FIRST: ("Copa Sudamericana - First stage", 9, "first"),
}
CONMEBOL_STAGE_IDS = set(CONMEBOL_STAGE_TARGETS)
# In front of a play-off a world can have a third (stage 1) and a second qualifying round (stage
# 2), sixteen clubs each (`qround <competition> <round> <regulation>` lines, fl26swiss.dll's August
# qualifying rounds). A round's winners go to the next round of its competition; its losers drop
# as UEFA's do -- the Champions League's second qualifying round's to the Europa League's third,
# its third's to the Europa League's play-off; the Europa League's the same way into the
# Conference League; the Conference League's are out, and so is a loser whose round is missing.
# Each round takes sixteen less eight for each round that feeds it, so every round of the
# Conference League eliminates eight and costs eight more clubs: 116 in Europe with the three
# play-offs, 132 with all nine rounds. A round is (competition 0..2, stage 0..2; stage 3 the first
# qualifying round in July, FL 2027 only: Q1_CONFIG).
QSTAGES = ("play-off", "third qualifying round", "second qualifying round", "first qualifying round")
QROUND_NUMBER = {0: 0, 1: 3, 2: 2, 3: 1}         # stage -> the round a qround line names (0: C_CONFIG's play-offs)
_ALL = [(c, s) for s in range(3) for c in range(3)]
# the round sets the League Builder picks from, the most rounds first (pick_rounds): every one
# needs (Champions League, Europa League, Conference League) new qualifying clubs as noted
QCONFIGS = [
    _ALL,                                                            # 32 / 16 / 16
    [r for r in _ALL if r != (2, 2)],                                # 32 / 16 / 8
    [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (2, 0)],                # 32 / 8 / 8
    [(0, 0), (0, 1), (1, 0), (2, 0)],                                # 24 / 8 / 16
    [(0, 0), (1, 0), (2, 0)],                                        # 16 / 16 / 16: the play-offs
]
# FL 2027 only (mato 06.11., notes/uefa-q1-srpanj.md "Prijedlog A"): a first qualifying round
# (stage 3) in July for the Champions League and the Conference League, 32 clubs each, and their
# second qualifying rounds of 32 after it (q_size). No Europa League second qualifying round: the
# Champions League first round's losers go to the Conference League's second (q_down), and the
# Europa League's own qualifying places to the Conference League's first round (fl26swiss.dll).
# 56 / 0 / 32 new qualifying clubs, 88 in all; the play-offs and the league phases as ever. The
# League Builder picks it for an FL 2027 world only (leaguebuilder europe_rounds), whose places
# fill it (pick_rounds_q1); an FL 2026 world never has a stage 3. fl26swiss.dll plays the first
# round from a career's second summer; in the first, the second rounds take the clubs it would
# have sent them.
Q1_CONFIG = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (2, 0), (2, 1), (2, 2), (2, 3)]
# FL 2027 only, "Prijedlog C" (mato 07.11., notes/uefa-q1-srpanj.md), as UEFA's: first qualifying
# rounds in July for the Champions League (32) and the Europa League (16), every competition's
# second and third rounds, and the Europa League's and the Conference League's August play-offs
# of 32 -- regulations of their own (stage 0 rounds in the world file, `qround 11 0` / `qround 12
# 0`; 188 and 189 stay February's). Sizes C_SIZE (the rest sixteen); new clubs 56 / 40 / 16, 112
# in all; direct entrants 28 / 12 / 4 (direct_room). The losers of both first rounds go to the
# Conference League's second round. The League Builder picks it before Q1_CONFIG for an FL 2027
# world whose places fill it (pick_rounds_c; c_places moves Conference League qualifying places
# up to the Europa League's). fl26swiss.dll plays the first rounds from a career's second summer;
# in the first, the second rounds take their room and the qualifying places past it go to the
# Conference League's second round.
C_CONFIG = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2)]
C_SIZE = {(0, 2): 32, (0, 3): 32, (1, 0): 32, (1, 1): 32, (2, 0): 32, (2, 1): 32, (2, 2): 32}
# FL 2027 only, Prijedlog C with a wide Conference League (mato 07.11.: "kvalifikacije za europu
# prosiriti ako je to moguce"; PLACES.md: 20 places in it instead of ~110): C_CONFIG and a July
# first qualifying round for the Conference League too, every Conference League round as big as
# the game's tables and the DLL take -- 62 clubs (31 ties: the master's six-bit club count, 63 at
# most, and fl26swiss Q_MAX 64) for its first and second rounds, 40 for its third and its play-off.
# The Champions League's and the Europa League's rounds stay C's. New clubs 56 / 40 / 74 = 170 (C
# 112): the Conference League's 62 / 7 / 1 / 4 from the first round to the play-off; direct
# entrants 28 / 12 / 0 -- its league phase is the play-off's 20 winners and the Europa League
# play-off's 16 losers, and a place the list gives its league phase goes to its play-off, as the
# big leagues' sixth and seventh do at UEFA. The losers of its first round are out. The League
# Builder picks it before C_CONFIG for an FL 2027 world whose places fill it (pick_rounds_cw);
# its own rounds take regulation ids after C's (mkeuropo.qualifying), so a world built with C
# keeps those. fl26swiss.dll plays the first rounds from a career's second summer; in the first,
# the Conference League's second round takes the 62 new clubs its first would have sent it.
CW_CONFIG = C_CONFIG + [(2, 3)]
CW_SIZE = {(0, 2): 32, (0, 3): 32, (1, 0): 32, (1, 1): 32, (2, 0): 40, (2, 1): 40, (2, 2): 62, (2, 3): 62}
QROUND_MAX = 62                   # the most clubs a qualifying round takes (31 ties; mkeuropo _copy_ties)
C_TOPUP = 3                       # Champions League qualifying places C / CW may be short of (below)


def c_world(rounds):
    """rounds are C_CONFIG's (the Europa League's first qualifying round: Prijedlog C only), or
    CW_CONFIG's"""
    return rounds is not None and (1, 3) in rounds


def cw_world(rounds):
    """rounds are CW_CONFIG's: Prijedlog C with the Conference League's first qualifying round"""
    return c_world(rounds) and (2, 3) in rounds


def q_up(rounds, r):
    """where round r's winners go: the next round of its competition, None for the league phase"""
    c, s = r
    return next(((c, t) for t in range(s - 1, -1, -1) if (c, t) in rounds), None)


def q_down(rounds, r):
    """where round r's losers go: a round, "phase" for the league phase below, None out -- a first
    qualifying round's (Q1_CONFIG) to the Europa League's second, or without one the Conference
    League's second (fl26swiss q_down)"""
    c, s = r
    if c == 2:
        return None
    if s == 0:
        return "phase"
    if s == 3 and c_world(rounds):                 # Prijedlog C: both first rounds' to the UECL Q2
        return (2, 2)
    if s == 3 and (c + 1, 2) not in rounds:
        return (2, 2) if (2, 2) in rounds else None
    return (c + 1, s - 1) if (c + 1, s - 1) in rounds else None


def q_size(rounds, r):
    """the clubs round r holds: sixteen; 32 for a first qualifying round and for the second
    qualifying round of a competition that has one (fl26swiss q_n); C_CONFIG's C_SIZE, CW_CONFIG's
    CW_SIZE"""
    c, s = r
    if cw_world(rounds):
        return CW_SIZE.get(r, PLAYOFF)
    if c_world(rounds):
        return C_SIZE.get(r, PLAYOFF)
    return 2 * PLAYOFF if s == 3 or (s == 2 and (c, 3) in rounds) else PLAYOFF


def q_room(rounds, r):
    """round r's new clubs: its size (sixteen), less half the size of every round that feeds it
    (eight; sixteen from a round of 32)"""
    return q_size(rounds, r) - sum(q_size(rounds, j) // 2 for j in rounds
                                   if j != r and (q_up(rounds, j) == r or q_down(rounds, j) == r))


def qual_room(rounds):
    """{UCLQ / UELQ / UECLQ: new qualifying clubs} for a set of rounds"""
    return {q: sum(q_room(rounds, r) for r in rounds if r[0] == q - UCLQ) for q in PLAYOFFS}


def qual_places(out, rounds=None):
    """{UCLQ / UELQ / UECLQ: clubs the uefa lines out send to that competition's qualifying}: its
    own places and the direct places past the competition's direct entrants (direct_room)"""
    room = direct_room(out, rounds)
    return {q: sum(1 for e in out if e[2] == q) + max(0, sum(1 for e in out if e[2] == win) - room[win])
            for q, (win, _l) in PLAYOFFS.items()}


def pick_rounds(out, uecl=True):
    """the qualifying rounds a world with the uefa lines out gets: the set of QCONFIGS with the most
    rounds whose new clubs the listed places fill, each competition's -- only those of the
    competitions with qualifying places (and with uecl False, none of the Conference League's);
    the play-offs alone when none fits"""
    listed = {q - UCLQ for q in PLAYOFFS if any(e[2] == q for e in out)}
    if not uecl:
        listed.discard(2)
    have = qual_places(out)
    for cfg in QCONFIGS:
        rounds = [r for r in cfg if r[0] in listed]
        need = qual_room(rounds)
        if all(need[q] <= have[q] for q in PLAYOFFS if q - UCLQ in listed):
            return rounds
    return [r for r in QCONFIGS[-1] if r[0] in listed]


def pick_rounds_q1(out, uecl=True):
    """FL 2027: Q1_CONFIG when the uefa lines out fill it -- the Champions League's qualifying
    places its 56 new clubs, the Europa League's and the Conference League's together its 32 (the
    Europa League's go to the Conference League's first round) -- else None"""
    if not uecl:
        return None
    have, need = qual_places(out), qual_room(Q1_CONFIG)
    if have[UCLQ] >= need[UCLQ] and have[UELQ] + have[UECLQ] >= need[UELQ] + need[UECLQ]:
        return list(Q1_CONFIG)
    return None


def c_fills(out, rounds):
    """the uefa lines out (c_places' already) fill the new qualifying clubs of rounds (C_CONFIG or
    CW_CONFIG), each competition's -- the Champions League's up to C_TOPUP short: the European
    places of reality are 54 or 55 there and C takes 56, so fl26swiss tops the last up from the
    big five, as it does any round short of clubs (the count of before saw Belgium's shipped
    places of FL26, 155, next to FL 2027's 115 and passed a list three short; access_alias)"""
    have, need = qual_places(out, rounds), qual_room(rounds)
    return all(have[q] >= need[q] - (C_TOPUP if q == UCLQ else 0) for q in PLAYOFFS)


def pick_rounds_c(out, uecl=True):
    """FL 2027: C_CONFIG when the uefa lines out (c_places' already) fill each competition's new
    qualifying clubs, 56 / 40 / 16 (c_fills) -- else None"""
    if not uecl:
        return None
    if c_fills(out, C_CONFIG):
        return list(C_CONFIG)
    return None


def pick_rounds_cw(out, uecl=True):
    """FL 2027: CW_CONFIG when the uefa lines out (c_places(rounds=CW_CONFIG)'s already) fill each
    competition's new qualifying clubs, 56 / 40 / 74 (c_fills) -- else None"""
    if not uecl:
        return None
    if c_fills(out, CW_CONFIG):
        return list(CW_CONFIG)
    return None


def c_places(out, rank=None, rounds=None):
    """C_CONFIG's uefa lines: the Europa League's qualifying takes 40 new clubs, and a list made
    for 28 / 20 / 20 direct entrants (the shipped one: 16 / 24 / 32 for the rounds, with the direct
    places past 28 / 12 / 4) leaves it short and the Conference League's past its 16. The
    Conference League qualifying places it has no room for, the first of them (the strongest),
    become Europa League qualifying places, after the others (by rank when given, as uefa_places
    orders a qualifying). rounds: CW_CONFIG's room instead (74 in the Conference League's
    qualifying, so fewer move up). Returns (lines, the lines moved, as they were)"""
    rounds = rounds if cw_world(rounds) else C_CONFIG
    have, need = qual_places(out, rounds), qual_room(rounds)
    ecl = [i for i, e in enumerate(out) if e[2] == UECLQ]
    n = min(need[UELQ] - have[UELQ], have[UECLQ] - need[UECLQ], len(ecl))
    if n <= 0:
        return list(out), []
    moved = set(ecl[:n])
    up = [(e[0], e[1], UELQ, e[3]) for i, e in enumerate(out) if i in moved]
    rest = [e for i, e in enumerate(out) if i not in moved]
    at = max([i + 1 for i, e in enumerate(rest) if e[2] in (0, UCLQ, 1, UELQ)] or [0])
    block = [e for e in rest[:at] if e[2] == UELQ] + up
    if rank:
        block.sort(key=lambda e: rank.get(place_league(e), UNRANKED))
    head = [e for e in rest[:at] if e[2] != UELQ]
    return head + block + rest[at:], [out[i] for i in sorted(moved)]


def rounds_text(rounds):
    """'Champions League: second qualifying round, third qualifying round, play-off; ...'"""
    names = dict(COMPETITIONS)
    return "; ".join("%s: %s" % (names[c], ", ".join(QSTAGES[s] for s in (3, 2, 1, 0) if (c, s) in rounds))
                     for c in range(3) if any(r[0] == c for r in rounds))

# Continental cups the game does not have, built by tools/mkccup.py and run by fl26swiss.dll from
# the world file's ccup lines: groups of four, then a knockout of the winners and runners-up (or a
# straight knockout of four). A league place can lead to them like to the ones above. Each: number,
# name, competition code, confederation (Competition.bin +6), and the shipped leagues' places --
# (regulation, position), strongest first -- that fill the field when the world's own leagues do
# not. A cup is built only in a world where some league names it.
_J1, _CSL, _SPL, _MLS = 52, 120, 162, 51
_BRA, _ARG, _CHI, _COL = 29, 30, 67, 168
_COL_SEASON = 119                 # Colombia's whole season (168 + 169), when a world gives it places as one
CCUPS = [
    (6, "CAF Champions League", "FL_CAFCL", 5, []),
    (7, "CAF Confederation Cup", "FL_CAFCC", 5, []),
    (8, "AFC Champions League Two", "FL_AFCCL2", 3,
     [(r, p) for k in range(6) for r, p in ((_J1, 5 + k), (_CSL, 4 + k), (_SPL, 5 + k))]),
    (9, "Copa Sudamericana", "FL_SUDAM", 4,
     [(r, p) for k in range(8) for r, p in ((_BRA, 7 + k), (_ARG, 7 + k), (_CHI, 3 + k), (_COL, 3 + k))]),
    # 0.2.0: North and Central America and Oceania, asked for since 0.1.5 (#81: MLS to a CONCACAF
    # cup). The CONCACAF Champions Cup is a straight knockout, as the real one is (CCUP_KNOCKOUT);
    # MLS fills it from the top down after the world's own places. The OFC Champions League has
    # no league of the game to fill from, so it is the world's own clubs only, as the CAF cups are.
    (13, "CONCACAF Champions Cup", "FL_CONCACAF", 6, [(_MLS, p) for p in range(1, 13)]),
    (14, "OFC Champions League", "FL_OFCCL", 7, []),
    # 0.2.0: the AFC's third cup, under the Champions League Two (Discord, 2026-10-07: "acl, acl 2
    # and Challenge League"); the shipped Asian leagues fill it from the places after ACL Two's.
    (15, "AFC Challenge League", "FL_AFCCHL", 3,
     [(r, p) for k in range(4) for r, p in ((_J1, 11 + k), (_CSL, 10 + k), (_SPL, 11 + k))]),
]
CCUP_KNOCKOUT = {13}              # cups that play no groups: a knockout of 16 (or 8, 4) from the start
COMPETITIONS += [(c, n) for c, n, _code, _conf, _fill in CCUPS]
COMPETITIONS += [(c, v[0]) for c, v in CONMEBOL_STAGE_TARGETS.items()]
# The shipped leagues that fill the cups above, by regulation (for Check the plan).
FILL_NAMES = {_BRA: "Brasileirão Série A (Brazil)", _ARG: "Liga Profesional (Argentina)",
              _CHI: "Liga de Primera (Chile)", _COL: "Liga BetPlay (Colombia)", _J1: "J1 League (Japan)",
              _CSL: "Chinese Super League (China)", _SPL: "Saudi Pro League (Saudi Arabia)",
              _MLS: "Major League Soccer (USA)"}
# The game's own Libertadores places of its South American leagues: the rows of the exe's rights
# table (0x1434f1fa0, targets 3 and 4 -- regulation 9, the group stage, and 8, the qualifying
# round), which the game's Competition Info shows as the Libertadores' criteria. (league, group
# stage, qualifying round)
SAM_GAME = [
    (_BRA, "1st-4th and the Copa do Brasil winner", "5th-6th"),
    (_ARG, "1st-4th and the Copa Argentina winner", "5th"),
    (_CHI, "1st and the Copa Chile winner", "2nd-3rd"),
    (_COL, "the winners of the two playoffs (I and II)", "the Copa BetPlay winner"),
]
FIELD = 36                        # clubs in each UEFA league phase; places past it get nothing

# The DLL's own access list (tools/native/fl26swiss.c, ACCESS): the shipped leagues' European
# places, which every world has under the same regulation ids. A world file with uefa lines
# replaces the DLL's list outright, so a world that adds places for its own leagues writes these
# first and its own after them (uefa_places) -- otherwise the Netherlands, Portugal, Belgium ...
# would lose their places and the big five would fill the gaps. Keep it in step with the C file.
_ENG, _ITA, _ESP, _FRA, _NED, _POR, _GER = 17, 18, 19, 20, 21, 22, 50
_GRE, _TUR, _SCO, _DEN, _BEL = 117, 118, 134, 147, 155
# The title holders first, as in the C list: the Champions League and Europa League winners
# (knockout regs 4 and 6) to the Champions League, the Conference League winner (187) to the
# Europa League; alt = the big-five league whose next club takes a place no holder is known for.
HOLDERS = [(4, 0, 0, _ENG), (6, 0, 0, _ESP), (187, 0, 1, _ITA)]
SHIPPED_ACCESS = sorted(HOLDERS + [(r, n, c, 0) for r, n, c in (
    # Champions League
    (_ENG, 1, 0), (_ITA, 1, 0), (_ESP, 1, 0), (_GER, 1, 0), (_FRA, 1, 0), (_NED, 1, 0), (_POR, 1, 0),
    (_BEL, 1, 0), (_TUR, 1, 0),
    (_ENG, 2, 0), (_ITA, 2, 0), (_ESP, 2, 0), (_GER, 2, 0), (_FRA, 2, 0), (_NED, 2, 0),
    (_ENG, 3, 0), (_ITA, 3, 0), (_ESP, 3, 0), (_GER, 3, 0), (_FRA, 3, 0),
    (_ENG, 4, 0), (_ITA, 4, 0), (_ESP, 4, 0), (_GER, 4, 0),
    (_ENG, 5, 0), (_ESP, 5, 0),
    # the Champions League play-off
    (_POR, 2, 10), (_SCO, 1, 10), (_GRE, 1, 10), (_FRA, 4, 10), (_NED, 3, 10), (_BEL, 2, 10),
    (_DEN, 1, 10), (_TUR, 2, 10), (_SCO, 2, 10), (_GRE, 2, 10), (_POR, 3, 10), (_BEL, 3, 10),
    (_NED, 4, 10), (_DEN, 2, 10), (_TUR, 3, 10), (_SCO, 3, 10),
    # Europa League
    (_ENG, 6, 1), (_ITA, 5, 1), (_ESP, 6, 1), (_GER, 5, 1), (_FRA, 5, 1),
    (_ENG, 7, 1), (_ITA, 6, 1), (_ESP, 7, 1), (_GER, 6, 1), (_FRA, 6, 1),
    (_NED, 5, 1), (_POR, 4, 1), (_BEL, 4, 1),
    (_TUR, 4, 1), (_SCO, 4, 1), (_GRE, 3, 1), (_DEN, 3, 1), (_NED, 6, 1), (_POR, 5, 1),
    # the Europa League play-off
    (_ENG, 8, 11), (_ITA, 7, 11), (_ESP, 8, 11), (_GER, 7, 11), (_FRA, 7, 11),
    (_BEL, 5, 11), (_TUR, 5, 11), (_SCO, 5, 11), (_GRE, 4, 11), (_DEN, 4, 11),
    (_NED, 7, 11), (_POR, 6, 11), (_BEL, 6, 11), (_TUR, 6, 11), (_GRE, 5, 11), (_DEN, 5, 11),
    # Conference League
    (_ENG, 9, 2), (_ITA, 8, 2), (_ESP, 9, 2), (_GER, 8, 2), (_FRA, 8, 2),
    (_NED, 8, 2), (_POR, 7, 2), (_BEL, 7, 2), (_TUR, 7, 2), (_SCO, 6, 2), (_GRE, 6, 2), (_DEN, 6, 2),
    (_NED, 9, 2), (_POR, 8, 2), (_BEL, 8, 2), (_TUR, 8, 2), (_GRE, 7, 2), (_SCO, 7, 2), (_DEN, 7, 2),
    (_ENG, 10, 2),
    # the Conference League play-off
    (_ITA, 9, 12), (_ESP, 10, 12), (_GER, 9, 12), (_FRA, 9, 12), (_NED, 10, 12), (_POR, 9, 12),
    (_BEL, 9, 12), (_TUR, 9, 12), (_GRE, 8, 12), (_SCO, 8, 12), (_DEN, 8, 12), (_ENG, 11, 12),
    (_ITA, 10, 12), (_ESP, 11, 12), (_GER, 10, 12), (_FRA, 10, 12),
)], key=lambda e: [c for c, _n in COMPETITIONS].index(e[2]))   # stable: each section's holders stay first


# the countries of the access list's regulations, as uefakey.DEFAULT_ORDER names them: the
# association rank of a shipped place (uefa_places, rank)
ACCESS_COUNTRY = {_ENG: "England", _ITA: "Italy", _ESP: "Spain", _FRA: "France", _NED: "Netherlands",
                  _POR: "Portugal", _GER: "Germany", _GRE: "Greece", _TUR: "Turkey", _SCO: "Scotland",
                  _DEN: "Denmark", _BEL: "Belgium"}
UNRANKED = 999                    # a place whose league has no association rank: after the ranked ones

# Request #5 (06.11.): FL 2027 plays Belgium's top division as one league of 18, regulation
# 115, with no split -- the access list's 155 (FL26's regular phase) is not in its tables, the DLL
# found no table for it and Belgium had no European club in an FL 2027 world. Where the tables in
# use have no 155 the places go to 115 (leaguebuilder.access_alias), as uefa lines of the world.
ACCESS_FALLBACK = {_BEL: 115}


def shipped_access(alias=None):
    """SHIPPED_ACCESS with the regulations of alias ({regulation: in its place}, the plan's
    access_alias) swapped"""
    if not alias:
        return SHIPPED_ACCESS
    a = {int(k): int(v) for k, v in alias.items()}
    return [(a.get(r, r), n, c, alt) for r, n, c, alt in SHIPPED_ACCESS]


def place_league(e):
    """the regulation a uefa place belongs to: its own, or for a cup winner's place (position 0)
    the league in alt"""
    return e[0] if e[1] else e[3]


def uefa_places(own, replace=(), uecl=True, rank=None, alias=None, extra=(), rounds=None):
    """the uefa lines of a world whose own leagues have places: the shipped list and the world's
    places, competition by competition (Champions League first, as fl26swiss hands them out in
    list order), each competition's shipped places before the world's -- except the play-off,
    where the world's come first and push the weakest shipped ones out. own: (regulation,
    position, competition, alt) tuples. Empty when own is: no lines, and the DLL's list stands.
    Second result: {competition: (places listed, room)} for those past their room (the last get
    nothing; for the play-off, the world's own places and the Champions League places past the
    28 direct ones, which fl26swiss sends there). replace: regulations of the game whose shipped
    places are dropped -- the world lists its own for them (the recipe's game_europe). The room of
    each competition's qualifying is that of the rounds pick_rounds gives (uecl: with the
    Conference League).

    rank: {regulation: association rank} (a world with no UEFA ranking of its own: leaguebuilder
    assoc_rank). The qualifying's places then go in that order, the world's and the shipped ones
    alike, so the places past the room are the weakest associations' (B250, monkusgigus 26.10.:
    the 31 Champions League qualifying places of the Europack's new leagues came first and left
    no room for the Greek champion, Portugal's second or Belgium's).

    alias: shipped regulations the tables in use do not have, and the one in each's place (request #5,
    FL 2027's Belgium): the shipped list is written with those, even for a world with no places
    of its own, as the DLL's own list names the missing one.
    extra: Champions League qualifying places listed after all the others -- FL 2027's first
    qualifying round, the champions of the European leagues with no place of their own
    (leaguebuilder europe_rounds). rounds: the qualifying rounds whose room counts (default
    pick_rounds); C_CONFIG's also move Conference League qualifying places up (c_places)."""
    own = [tuple(int(x) for x in e) for e in own]
    extra = [tuple(int(x) for x in e) for e in extra]
    replace = set(replace)
    if not own and not replace and not alias and not extra:
        return [], {}
    out = []
    for c, _n in COMPETITIONS:
        if c in UEFA_LINE:
            mine = [e for e in own if e[2] == c]
            shipped = [e for e in shipped_access(alias) if e[2] == c and e[0] not in replace]
            if c in PLAYOFFS and rank:
                out += sorted(mine + shipped, key=lambda e: rank.get(place_league(e), UNRANKED))
            else:
                out += mine + shipped if c in PLAYOFFS else shipped + mine
            if c == UCLQ:
                out += extra
    own = own + extra
    if c_world(rounds):
        out, moved = c_places(out, rank, rounds)
        for e in moved:                              # the world's own moved up count as the Europa League's
            if e in own:
                own[own.index(e)] = (e[0], e[1], UELQ, e[3])
    return out, crowded(out, own, pick_rounds(out, uecl) if rounds is None else rounds)


def direct_room(out, rounds=None):
    """{competition: direct entrants} for the uefa lines out: 36, less eight for every play-off
    (listed in out) whose winners join it or whose losers drop into it -- with C_CONFIG's rounds
    half each play-off's size, all three in: 28 / 12 / 4"""
    room = {0: FIELD, 1: FIELD, 2: FIELD}
    cw = c_world(rounds)
    for q, (win, lose) in PLAYOFFS.items():
        if cw or any(e[2] == q for e in out):
            half = q_size(rounds, (q - UCLQ, 0)) // 2 if cw else PLAYOFF // 2
            room[win] -= half
            if lose is not None:
                room[lose] -= half
    return room


def europe_count(comps, uecl=True, rounds=None):
    """the European places counter (pepponeee 29.10.): {competition: (places, room)} for the
    league phases -- comps is the competition of every place of the world (the title holders'
    too), room the clubs each takes straight in (direct_room: 36, less eight for each play-off
    feeding it; with FL 2027's rounds, Prijedlog C's 28 / 12 / 4 or 0). Fewer places than room:
    the game fills the rest with the next clubs of the big five; more: the last go to the
    competition's qualifying, or get none"""
    comps = [int(c) for c in comps]
    room = direct_room([(0, 0, c, 0) for c in comps], rounds)
    return {c: (comps.count(c), room[c]) for c in ((0, 1, 2) if uecl else (0, 1))}


def europe_count_text(counts):
    """'Champions League 26/28, Europa League 20/20 ...' with what happens to the difference"""
    names = dict(COMPETITIONS)
    out = []
    for c, (n, r) in sorted(counts.items()):
        s = "%s %d/%d" % (names[c], n, r)
        if n < r:
            s += " (%d more from the big five)" % (r - n)
        elif n > r:
            s += " (%d over)" % (n - r)
        out.append(s)
    return ", ".join(out)


def crowded(out, own, rounds=None):
    """{competition: (places listed, room)} for those of out past their room. A competition's
    places past its direct entrants go to its own qualifying when it has one (fl26swiss), ahead of
    the qualifying's shipped places; only the world's own count against its room -- sixteen with
    the play-offs alone, that of the rounds (pick_rounds) when given"""
    over, room = {}, direct_room(out, rounds)
    qroom = qual_room(rounds) if rounds is not None else {q: PLAYOFF for q in PLAYOFFS}
    # FL 2027's first qualifying round: the Europa League's qualifying places go to the Conference
    # League's first round (fl26swiss) and count against its room
    merge = rounds is not None and (2, 3) in rounds and not qroom[UELQ]
    cw = c_world(rounds)                              # C_CONFIG: every qualifying on, listed or not
    for q, (win, _lose) in PLAYOFFS.items():
        if not (cw or any(e[2] == q for e in out)) or (merge and q == UELQ):
            continue
        spill = max(0, sum(1 for e in out if e[2] == win) - room[win])
        n = spill + sum(1 for e in own if e[2] == q)
        if merge and q == UECLQ:
            n += max(0, sum(1 for e in out if e[2] == 1) - room[1]) + sum(1 for e in own if e[2] == UELQ)
        if n > qroom[q]:
            over[q] = (n, qroom[q])
    for c in (0, 1, 2):
        q = [k for k, (w, _l) in PLAYOFFS.items() if w == c][0]
        n = sum(1 for e in out if e[2] == c)
        if n > room[c] and not (cw or any(e[2] == q for e in out)):
            over[c] = (n, room[c])
    return over


def read_uefa(path):
    """the uefa lines of a world file, read as fl26swiss.lua reads them:
    ^%s*uefa%s+(%d+)%s+(%d+)%s+(%d+)%s+(%d+)"""
    import re
    pat = re.compile(r"^\s*uefa\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)")
    out = []
    for line in open(path, encoding="utf-8"):
        m = pat.match(line)
        if m:
            out.append(tuple(int(x) for x in m.groups()))
    return out


# names a league is called by that Country.bin spells differently
ALIASES = {"SOUTH KOREA": "Republic of Korea", "KOREA REPUBLIC": "Republic of Korea"}


def write_world(path, name, leagues, splits=(), uefa=(), uecl=(), ccups=(), qrounds=(), groups=()):
    """leagues: list of dicts with 'id', any of KEYS, and 'name'; splits: (total, regular,
    [groups]) for the split seasons among them; uefa: (regulation, position, competition, alt)
    places; uecl: the Conference League's first-season team ids; ccups: the ccup lines as
    tools/mkccup.py prints them; qrounds: (competition 10..12, round 3, 2 or 1, regulation) of the
    qualifying rounds in front of the play-offs; groups: the gset, ghome and poff lines
    (group_lines)"""
    lines = [FORMAT, "world %s" % name]
    for L in leagues:
        parts = ["league %d" % L["id"]]
        parts += ["%s=%d" % (k, L[k]) for k in KEYS if L.get(k) is not None]
        if L.get("name"):
            parts.append("name=%s" % L["name"].replace("\n", " ").strip())
        lines.append(" ".join(parts))
    seen = set()
    for L in leagues:                    # B425: a split season of the game's own a league stands under
        g = L.get("gsplit")
        if g and g[0] not in seen:
            seen.add(g[0])
            lines.append("gsplit %d regular=%d groups=%s" % (g[0], g[1], ",".join(map(str, g[2]))))
    for s in splits:                     # (total, regular, [groups], extra words ...)
        total, regular, phases = s[:3]
        lines.append("split %d regular=%d groups=%s%s" % (total, regular, ",".join(map(str, phases)),
                                                          "".join(" " + w for w in s[3:])))
    for e in uefa:
        lines.append("uefa %d %d %d %d" % tuple(e))
    if uecl:
        lines.append("uecl " + " ".join(map(str, uecl)))
    for q in qrounds:
        lines.append("qround %d %d %d" % tuple(q))
    lines += list(ccups)
    lines += list(groups)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")


def group_lines(gsets=(), homes=(), poffs=(), borders=None):
    """The world file's lines for GitHub #98. gsets: [(ups [(id, n)], lows [(id, n, pref id or 0)])];
    homes: {league: [team ids]}; poffs: [(cup, up, low, hold (id, place) or None, [(id, place)])];
    borders (16.11.2026, zone_border): {group: [(team id, neighbour group)]} in the recipe's order"""
    out = []
    for k, (ups, lows) in enumerate(gsets):
        out.append("gset %d up=%s low=%s" % (k, ",".join("%d:%d" % tuple(u) for u in ups),
                                             ",".join("%d:%d:%d" % tuple(l) for l in lows)))
    for lid in sorted(homes):
        if homes[lid]:
            out.append("ghome %d %s" % (lid, ",".join(str(t) for t in homes[lid])))
    for cup, up, low, hold, entry in poffs:
        out.append("poff %d up=%d low=%d%s entry=%s" % (cup, up, low, " hold=%d:%d" % tuple(hold) if hold else "",
                                                       ",".join("%d:%d" % tuple(e) for e in entry)))
    for lid in sorted(borders or {}):
        if borders[lid]:
            out.append("gborder %d %s" % (lid, ",".join("%d:%d" % tuple(e) for e in borders[lid])))
    return out


def read_borders(path):
    """{group: [(team id, neighbour group)]} of a world file's gborder lines, as fl26chain.lua reads
    them; {} for a world without them (every world built before 16.11.2026)"""
    out = {}
    for line in open(path, encoding="utf-8"):
        w = line.split()
        if len(w) >= 3 and w[0] == "gborder" and w[1].isdigit():
            out.setdefault(int(w[1]), []).extend(tuple(int(x) for x in e.split(":")) for e in w[2].split(",") if e)
    return out


def read_groups(path):
    """(gsets, homes, poffs) of a world file, as group_lines takes them -- the reading fl26chain.lua does"""
    gsets, homes, poffs = [], {}, []
    pairs = lambda v: [tuple(int(x) for x in e.split(":")) for e in v.split(",") if e]
    for line in open(path, encoding="utf-8"):
        w = line.split()
        if not w:
            continue
        kv = dict(b.partition("=")[::2] for b in w[2:] if "=" in b)
        if w[0] == "gset" and "up" in kv and "low" in kv:
            gsets.append((pairs(kv["up"]), pairs(kv["low"])))
        elif w[0] == "ghome" and len(w) >= 3:
            homes[int(w[1])] = [int(t) for t in w[2].split(",") if t]
        elif w[0] == "poff" and "entry" in kv:
            hold = tuple(int(x) for x in kv["hold"].split(":")) if "hold" in kv else None
            poffs.append((int(w[1]), int(kv["up"]), int(kv["low"]), hold, pairs(kv["entry"])))
    return gsets, homes, poffs


def read_world(path):
    """(world name, [league dicts]) -- the same reading the Lua modules do"""
    name, leagues = None, []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("world "):
            name = line[6:].strip()
        if not line.startswith("league "):
            continue
        head, _, nm = line.partition(" name=")
        bits = head.split()
        L = {"id": int(bits[1])}
        for b in bits[2:]:
            k, _, v = b.partition("=")
            if v.lstrip("-").isdigit():
                L[k] = int(v)
        if nm:
            L["name"] = nm.strip()
        leagues.append(L)
    return name, leagues


def access_from_lua(path):
    """the { regulation, position, competition, alt } rows of `local ACCESS = {` in a module"""
    import re
    src = open(path, encoding="utf-8").read()
    m = re.search(r"^local ACCESS = \{\r?\n(.*?)^\}", src, re.S | re.M)
    if not m:
        raise SystemExit("no `local ACCESS = {` table in %s" % path)
    body = re.sub(r"--[^\n]*", "", m.group(1))
    return [tuple(int(x) for x in e) for e in re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", body)]


def base_dir(opt):
    for d in (opt, os.environ.get("FL26_PESDB"), os.path.join(HERE, "..", "out", "base-pesdb")):
        if d and os.path.exists(os.path.join(d, "CompetitionRegulation.bin")):
            return d
    raise SystemExit("no shipped tables: pass --base <folder with CompetitionRegulation.bin>")


def load(d, n):
    raw = open(os.path.join(d, n), "rb").read()
    return bytearray(pesdb.wesys_unpack(raw) if raw[3:8] == b"WESYS" else raw)


SPLIT_TOTAL, F_TOTAL, F_REGULAR, F_GROUPS = 9, 11, 12, (13, 14, 15)
# A season of two tournaments of the game (Colombia 119 = 168 + 169, the MLS 51 = 166 + 167): a total
# of type 5, format 6, and its halves of type 4, format 7 and 8, whose +0x06 names the total
# (leaguebuilder.game_season_totals, the world file's seasonsum line)
SEASON_TOTAL, F_SEASON_TOTAL, F_SEASON_HALVES = 5, 6, (7, 8)


def fmt(g):
    return (int.from_bytes(g[0x0c:0x10], "little") >> 12) & 0x3f


def from_tables(root, base, countries_file=None):
    """([league dicts], [splits]) for the leagues <root> adds, in regulation id order. A split
    season (tools/mksplit.py) is one league line for its total -- the row every module keys on --
    and a split line naming its phases, which are not leagues of their own to the modules."""
    p = os.path.join(root, "common", "etc", "pesdb")
    comp, regs = load(p, "Competition.bin"), load(p, "CompetitionRegulation.bin")
    shipped = {int.from_bytes(load(base, "CompetitionRegulation.bin")[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little")
               for i in range(len(load(base, "CompetitionRegulation.bin")) // M.REG)}
    region = {M.comp_cid(comp, i * M.COMP): M.dec_region(comp[i * M.COMP + M.REGION_OFF])
              for i in range(len(comp) // M.COMP)}
    rows = [regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)]
    rid = lambda g: int.from_bytes(g[M.R_ID:M.R_ID + 2], "little")
    below = {rid(g): int.from_bytes(g[M.R_BELOW:M.R_BELOW + 2], "little") for g in rows if g[M.R_TYPE] == 4}
    above = {b: a for a, b in below.items() if b}

    leagues, phases = [], {}
    for g in rows:
        i = rid(g)
        if i in shipped or g[M.R_TYPE] not in (4, SPLIT_TOTAL):
            continue
        if g[M.R_TYPE] == 4 and fmt(g) in (F_REGULAR,) + F_GROUPS:
            phases.setdefault(M.reg_cid(g), []).append((fmt(g), i))
            continue
        legs = (int.from_bytes(g[0x10:0x14], "little") >> 12) & 7
        L = {"id": i, "cid": M.reg_cid(g), "region": region.get(M.reg_cid(g)), "tier": M.get_tier(g),
             "clubs": g[M.R_TEAMS] & 0x3f, "legs": legs or None,
             "name": pesdb.cstr(g[M.R_NAME:M.R_NAME + M.NAME_SLOT]) if hasattr(pesdb, "cstr")
                     else bytes(g[M.R_NAME:M.R_NAME + M.NAME_SLOT]).split(b"\0")[0].decode("utf-8", "replace")}
        # a link counts only downwards: the shipped J1 (52) still names 145, the old J2, as the
        # league below it, and a first division of ours on 145 must not take J1's relegated clubs
        up = above.get(i)
        if up and M.get_tier(g) >= 2:
            L["above"] = up
        L["promote"] = 3 if "above" in L else 0
        L["demote"] = 3 if below.get(i) else 0
        if i in DEFAULT_SLOT:
            L["slot"] = DEFAULT_SLOT[i]
        leagues.append(L)
    leagues.sort(key=lambda L: L["id"])
    # B92 (Belgium, 2026-10-16): a league of ours under the regular phase of a SHIPPED split
    # season (Challenger Pro League under 155, the Jupiler Pro League's regular phase) names
    # that season's total as splittotal=. The game's season end runs on the total (115), whose
    # relegation link stays empty, so fl26chain moves the clubs itself, as for a split of ours,
    # and fl26comptab raises the total's relegation count too (the League Info panel).
    byid = {rid(g): g for g in rows}
    for L in leagues:
        up = byid.get(L.get("above"))
        if L.get("above") in shipped and up is not None and up[M.R_TYPE] == 4 and fmt(up) == F_REGULAR:
            tot = next((rid(h) for h in rows if h[M.R_TYPE] == SPLIT_TOTAL and M.reg_cid(h) == M.reg_cid(up)), None)
            if tot is not None:
                L["splittotal"] = tot
                # B425: the season's groups too (formats 13 and 14: the top and the bottom one), for
                # the `gsplit` line -- a play-off's place of the regular phase is the final table's
                grp = [next((rid(h) for h in rows if h[M.R_TYPE] == 4 and M.reg_cid(h) == M.reg_cid(up) and fmt(h) == f), None)
                       for f in F_GROUPS[:2]]
                if None not in grp:
                    L["gsplit"] = (tot, L["above"], grp)
    splits = []
    for L in leagues:
        ph = sorted(phases.get(L["cid"], []))
        if ph and ph[0][0] == F_REGULAR and len(ph) > 1:
            splits.append((L["id"], ph[0][1], [p[1] for p in ph[1:4]]))

    # countries: the file first, then a guess from the name
    try:
        import mkflags
        cty = mkflags.countries(mkflags.table("Country", [base]))
    except SystemExit as e:
        print("  note: no Country.bin (%s) -- no countries" % e)
        return leagues, splits
    rules = mkflags.read_countries_file(countries_file, cty) if countries_file else []
    for L in leagues:
        fid = None
        for kind, key, f in rules:
            if (kind == "id" and key == L["id"]) or (kind == "region" and key == L.get("region")) \
                    or (kind == "name" and key == (L.get("name") or "").upper()):
                fid = f
        for alias, country in ALIASES.items():
            if fid is None and alias in (L.get("name") or "").upper():
                fid = mkflags.by_name(cty, country)
        if fid is None:
            fid, why = mkflags.guess(cty, L.get("name") or "")
            if fid is None:
                print("  %3d %-24s no country: %s" % (L["id"], L.get("name"), why))
        if fid is not None:
            L["country"] = fid
    return leagues, splits


def main():
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    if get("--show"):
        name, leagues = read_world(get("--show"))
        print("world %s, %d leagues" % (name, len(leagues)))
        for L in leagues:
            print("  " + "  ".join("%s=%s" % (k, L[k]) for k in ("id",) + KEYS + ("name",) if k in L))
        return 0
    root = get("--root")
    if not root:
        print(__doc__)
        return 1
    leagues, splits = from_tables(root, base_dir(get("--base")), get("--countries"))
    out = get("--out") or os.path.join(root, "fl26world.txt")
    uefa = access_from_lua(get("--uefa")) if get("--uefa") else []
    write_world(out, os.path.basename(os.path.normpath(root)), leagues, splits, uefa)
    print("%d leagues -> %s" % (len(leagues), out))
    for L in leagues:
        print("  %3d  region %2s  tier %s  slot %3s  country %4s  %2d clubs x%s  above %-4s %s"
              % (L["id"], L.get("region"), L.get("tier"), L.get("slot", "-"), L.get("country", "-"),
                 L["clubs"], L.get("legs"), L.get("above", "-"), L.get("name")))
    for total, regular, groups in splits:
        print("  split %d: regular phase %d, groups %s" % (total, regular, " ".join(map(str, groups))))
    if uefa:
        print("  %d UEFA places" % len(uefa))
    return 0


if __name__ == "__main__":
    sys.exit(main())
