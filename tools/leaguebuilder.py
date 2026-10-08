r"""python leaguebuilder.py plan  <recipe.json> [--base <pesdb dir>]
   python leaguebuilder.py build <recipe.json> [--base <pesdb dir>] [--game <dir>] [--replace]
   python leaguebuilder.py on    <world name> [--game <dir>]
   python leaguebuilder.py check [--game <dir>]

The league builder's core: one recipe in, one finished world out. The window (stage C,
docs/mod-studio.md) calls these same functions; this command line is for tests.

A recipe says what a person would say -- which country, how many clubs, how often they meet,
which league sits above -- and nothing about ids:

    { "world": "_FL26BiH",
      "leagues": [
        { "name": "Premijer Liga BiH", "country": "Bosnia and Herzegovina",
          "clubs": 12, "legs": 3,
          "club_names": ["FK Sarajevo", "Zeljeznicar", ...] },
        { "name": "Prva Liga FBiH", "country": "Bosnia and Herzegovina",
          "clubs": 16, "legs": 2, "above": "Premijer Liga BiH", "exchange": 2 },
        { "name": "Split League", "country": "Bosnia and Herzegovina", "clubs": 12,
          "split": { "legs": 2, "groups": [6, 6], "group_legs": 2 } }
      ],
      "uecl": true }

  country     a Country.bin name (flag, Competition Info name, the region's country)
  flag        optional picture of the country's flag; replaces the game's own flag of that
              country (Select Team, nationality) while the world is on
  clubs       10..24, the range seasons have been played with
  legs        how many times each pair meets, 1..4
  above       a league of this recipe (by name) or a shipped regulation id (e.g. 81, Ligue 2);
              the league becomes the division below it, in its region, promotion both ways
  exchange    clubs going up and down between the two (default 3)
  split       Scottish style: a regular phase, then top/bottom groups that keep their points
              (tools/mksplit.py); "groups" are club counts adding up to "clubs"
  apertura    optional, true or {"playoff": 8}: the season is two tournaments, Apertura
              (August to December) and Clausura (January to May), each club meeting every
              other once in each, both starting from zero points; the whole season's table
              stays for promotion and relegation. "playoff" 8 or 4 (default 8, 0 = none): the
              first clubs of each tournament then play a knockout, two legs a round and a
              one-match final (fl26swiss.dll fills it from that tournament's table the day
              after its last round; "playoff_logo" is the picture of both playoffs). Built as a split (mksplit, one group of all the clubs, the
              world file's carry=0); 18 clubs at most, 35 dates a season. Not with "split"
  season      optional, a top division of a new country only: "calendar" plays the country's
              season February to December, like Brazil, Japan or Saudi Arabia, promotion and
              relegation at New Year; the default, "august", plays August to May. It is the
              region's (the country's) season type, so every division below it follows it: the
              world file's `season <region> 1` line (fl26join.dll gives the region its type,
              fl26joindll/fl26swiss treat its leagues as calendar-year ones). Not with a split,
              Apertura/Clausura, a national cup, super cup or league cup anywhere in the
              country: their dates are European ones
  club_names  optional; missing names become "<league> 01", "<league> 02", ...
  game_clubs  optional, clubs the game already has in places of the league:
              [{"at": place (from 0), "id": team id, "swap": ...}, ...]. The club keeps its
              name, crest, kits, manager and players, and plays in this league only. One that
              plays anywhere in the game (a league, a cup, a continental competition) needs
              "swap", the club that takes all its places there: a team id of a club of the game
              in no competition at all, or {"name": ...} for a new club (placeholder squad, a
              numbered badge). So no competition of the game changes its number of clubs --
              the shipped leagues' dates and shapes follow that number. "keep": true and the
              club keeps its places in the continental competitions (CONTINENTAL_CIDS): a
              swap then takes only the rest, and a club the continent is all it plays needs
              none (#84). National teams, the
              special teams and squads under MIN_GAME_SQUAD are refused (game_club_checks).
              The world's nopool line keeps them out of the Master League's other-clubs
              groups (fl26clubs.dll)
  club_ids    optional, the team id of each club ("" or null = the next free one): an id a kit,
              crest or face pack was made for; above the game's clubs, at most CLUB_ID_MAX
  europe      optional European places: [[position, competition], ...], competition 0 Champions
              League, 10 its play-off in August (the winners go on, the losers to the Europa
              League), 1 Europa League, 11 its play-off (the winners go on, the losers to the
              Conference League), 2 Conference League, 12 its play-off (the losers are out),
              3 Libertadores, 4 its qualifying round, 5 AFC Champions League, or one of the cups the game has not got: 6 CAF
              Champions League, 7 CAF Confederation Cup, 8 AFC Champions League Two, 9 Copa
              Sudamericana, 13 CONCACAF Champions Cup, 14 OFC Champions League, 15 AFC Challenge League
              (fl26world.COMPETITIONS); each position once, and only the league's own
              (1..clubs), or 0 (CUP_WINNER) for the winner of the league's national cup ("cup"
              below; for game_europe the country's cup in the game), its place going down the
              league when the winner already has one or there is none yet -- for 6..14 too since
              0.2.0 (#95). 0..5 and 10..12 are written as uefa lines of the world file, after the shipped
              leagues' places (fl26world.uefa_places); 6..9, 13..15 build that cup (see ccup_plan)
  cup         optional, a top division of a new country only: true gives the country a national
              cup (a knockout copied from a shipped one, see NATIONAL_CUPS). The game fills a
              domestic cup with the region's first league and the league below it, and a cup's
              round dates come from the cup it was copied from, so the copy is picked by that
              count: a shipped cup of exactly that size, else the English one, which dates any
              field up to NATIONAL_CUP_MAX (national_cup); past that the cup keeps the top
              division's clubs only (fl26chain, cup= on the second division's line).
              "cup_name" names it (default "<league> Cup"), "cup_logo" is its picture
  supercup    optional, with cup: true also a super cup, the league's champion v the cup's winner
              in one match before the season (copied from SUPER_CUP_LIKE); "supercup_name",
              "supercup_logo"
  exhibition  optional, true: the league is for Kick Off and exhibition matches only -- its clubs
              are in the Select Team list under it, but it never enters a Master League season
              (a historical league, a league of legends ...). It stands alone: no division above
              or below it, no European places, no cups. Its regulation id is one the season
              builder does not take in at creation (CREATION_IDS), and fl26joindll leaves it out
  others      optional, "europe", "latam", "asia", "africa" or "classic": no league at all -- the
              clubs (1..OTHERS_MAX) go in the game's Other European / Latin American / Asia-
              Oceania / Africa teams, or Classic Teams, where the game files its own clubs that
              play in no league. Names, crests, kits, managers and players as in a league; no
              division, season, cups or European places. The "league" is only the recipe's way
              of holding them (pl["others"] after plan(), never pl["leagues"])
  league_cup  optional, a top division of a new country only: true gives the country a league
              cup, a straight knockout (two legs a round, the final one match) of 16, 8 or 4
              clubs -- the top division's by league position, then the division below's --
              the strongest v the weakest, played September to December (LEAGUE_CUP_DAYS);
              the clubs past it play a pre-round in late September (cup_field, `lpre` line).
              fl26swiss.dll fills and dates it (the ccup line's options); "league_cup_name",
              "league_cup_logo"
  preseason_cups  (the recipe, not a league) [{"name": ..., "clubs": [...]}]: a knockout of
              4 or 8 invited clubs in July, before the season (PRESEASON_DAYS), paired in the
              order given (first v second ...). A club is "<league>/<k>" (the k-th club of a
              league of the recipe, from 0) or a club id of the game; at least one from a
              league of the recipe (the cup is hosted by its country). A club of the game must
              play in a league that season, or the cup is not filled. "logo": its picture.
              A cup without a picture gets an emblem drawn from its name (mkemblems.py)
  formation   optional, the league's clubs' formation: a label of formations(base) ("4-2-3-1",
              "4-1-2-3 (<club name>)" ...) or the id of a club of the game; the clubs get a copy
              of that club's tactics (mktactics.py) and their best eleven follows its places.
              "club_formations" gives single clubs another one ("" = the league's). Without
              either the engine lines a club up in its fixed 4-2-3-1 (lbplayers.LINEUP)
  game_seasons  (the recipe, not a league) EXPERIMENTAL, a list of the game's countries that play
              February to December -- Brazil, Chile, China, Japan, Saudi Arabia -- to play
              August to May instead (GAME_SEASONS): `season <region> 0`, the leagues dated on
              the European calendar and the cups as an August-May cup of their shape. A
              division of ours below one of them plays August to May with it. The older
              saudi_august: true is ["Saudi Arabia"]
  uecl        (the recipe, not a league) true, the default: the world gets the Conference
              League, cloned from the reshaped Europa League (mkuecl.py: competition 174,
              regulations 186/187, group 1210), and its play-off (mkeuropo.py: 189), the ids
              fl26swiss.dll and the fixture dates know. false: no Conference League. Either
              way the Champions League and Europa League league phase is reshaped to one group
              of 36 (mkreshape.py) and the Europa League gets its play-off (188): fl26swiss.dll
              runs regulations 1027/1029 as that league phase in every world, and on the game's
              own groups of four it would put 36 clubs into group A (issue #33).
              "uecl_logo" is the Conference League's picture; without one it gets a drawn
              UECL emblem (the game has none for 174, issue #36). "uecl_name" is its name in
              the game; without one, "FL Conference League"
  europe_first (the recipe, not a league) the clubs of the European league phases in a new
              career's first season, picked by hand (Mod Studio: First-season European clubs):
              {"ucl": [...], "uel": [...], "uecl": [...]}, a club "<league>/<k>" or a club id of
              the game, as preseason_cups. Each list goes in first, the automatic choice fills
              the rest; from the second season the places decide again. fl26swiss.dll, the world
              file's `first <0|1|2> <team id> ...` lines
  game_europe (the recipe, not a league) the European places of leagues of the game, in place of
              the shipped ones: {"<regulation id of a top division of the game>": [[position,
              competition], ...]}, competitions as europe above (UEFA and Libertadores ones). An
              empty list sends the league nobody; a league not named keeps the shipped places
  uefa_rank   (the recipe, not a league) the UEFA key's ranking (tools/uefakey.py, Mod Studio's
              UEFA ranking dialog): ["g<regulation of the game>" or a new league's name, ...],
              strongest first. Applying it writes "europe", "game_europe" and "uefa_seed";
              Build reads only those, so places changed by hand afterwards stand
  uefa_seed   (the recipe, not a league) [[league, position, competition], ...] in the order
              fl26swiss hands the places out (the key's: tier by tier, then by rank), league as in
              uefa_rank: a competition's qualifying places go to its rounds in list order, the
              strongest to the round nearest the league phase. Places not in it come after
  game_cups   (the recipe, not a league) cups for countries of the game: [{"league": <the
              regulation id of a top division of the game>, "league_cup": true, "super_cup":
              false, "name", "logo", "super_name", "super_logo"}, ...]. A league cup is the one a
              new top division gets (league_cup above): 16 clubs of that league and the one
              below it, by position, the rest through a pre-round; fl26swiss fills and dates it. A super cup -- the champion v
              the cup winner, one match in late July -- only where the game has none (Brazil,
              Chile, Scotland, Greece, the USA); a cup nobody has won yet (a new career) leaves
              it unplayed that summer
  edits.competitions  (the recipe) new names and emblems for the game's competitions that are
              not leagues -- cups, super cups, the Champions League, the Libertadores ...:
              {"<competition id>": {"name": ..., "logo": ...}}; every regulation of that
              competition (stages, groups) takes the name. game_competitions() lists them
  ccup_names, ccup_logos  (the recipe) names and pictures of the continental cups the world
              builds: {"6": "CAF Champions League", "7", "8", "9", "0" (the CAF Super Cup)}
  caf_super_cup  (the recipe, not a league) true, the default: a world that builds both the CAF
              Champions League and the Confederation Cup also gets the CAF Super Cup, one match
              of the two winners in late July (CAF_SUPER_DAYS), a two-club knockout whose
              entries are the cups' winners (<knockout>:0, fl26swiss.dll). Nobody has won
              either cup in a new career's first season, so it is first played in the second.
              false: none. "caf_super_cup_logo" is its picture
  editable_kits  (the recipe) true: the new clubs get no kit lent from a club of the game. A lent
              kit is a licensed one (<key>_1st_realUni.bin) and Edit mode refuses it ("You cannot
              edit this strip"). Instead each club gets plain 1st/2nd/GK definitions of its own
              (mkkits --plain: the 96-byte kind unlicensed clubs carry), which Edit > Teams >
              Strip edits like any unlicensed club's, Paste Image included. Before 0.2.0 it got
              none and wore team 0's fallback, where Paste Image did not stick (#112). Default
              false: lent kits

What plan() decides, so that nothing is left to a person to get wrong:

  regulation ids   mkworld's free list, taking ids that have a Select Team slot
                   (fl26world.DEFAULT_SLOT) -- 11, 49, 60, 61, ... -- first, then the three
                   without one (fl26world.NO_SLOT_IDS: those leagues play, but are not in the
                   Select Team list); never one of BAD_REG
  competition ids  from 130 up, the range FL's own added leagues use, never 174 (the
                   Conference League's)
  team ids         a league's "club_ids" where it gives one; every other club counts up from
                   the last shipped one, at most CLUB_ID_MAX
  regions         a league with "above" takes its parent's; a new country gets the next
                   region from 29 up that nothing uses (sider/fl26reg64.lua reads 29..63)
  tier             1, or the parent's plus one
  split phases     mksplit's ids from 191 up (the range split seasons were tested on)

build() writes the world folder: Team/Coach/Competition* tables (mkleague.add_league, as
mkworld does), squads (mkplayers.py), splits (mksplit.py), the Conference League (above), and
fl26world.txt in the folder -- the world file every module reads, with the uefa lines of the
leagues' European places. on() makes it the live world: the one active _FL26
cpk.root in sider.ini (siderroot.py) and the world file copied to modules\. check() reads
sider.log after a start and says, module by module, whether the world file was taken.
"""
import contextlib, glob, io, json, os, re, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import mkleague as M
import mkworld as W
import mkcoaches
import mkuecl
import fl26world
import siderdir

GAME = os.environ.get("FL26_DIR", r"C:\Football Life 2026")
R_ABOVE = 0x04
LEGS_SHIFT, LEGS_MASK = 12, 7
CLUBS_MIN, CLUBS_MAX, LEGS_MAX = 10, 24, 4
# "others": the game's groups of clubs in no league, by the nibble at T_POOL of a club's record
# (Team.bin: 1 Classic Teams, 2 Other European, 3 Other Asia-Oceania, 6 Other Latin American,
# 7 Other Africa; 5 holds the three "ML Default" clubs). The Discord request of 2026-10-06:
# one club, BATE Borisov, without a league around it.
OTHERS = {"europe": 2, "latam": 6, "asia": 3, "africa": 7, "classic": 1}
OTHERS_MAX = 24                          # clubs in one such group of the recipe
OTHERS_NAMES = {2: "Other European", 6: "Other Latin American", 3: "Other Asia-Oceania",
                7: "Other Africa", 1: "Classic Teams"}
REGION_FIRST, REGION_LAST = 29, 63
CID_FROM = 130
SQUAD, PLAYER_CAP = 30, 51729            # tools/mkplayers.py --per / --cap, as the guide uses
TEAM_CAP = 1536                          # clubs in all, shipped ones included
MAX_SPLITS = 2                           # split seasons tested so far: two at a time (191..196)
# national cups to copy, by the clubs the game puts in them: the top division alone, or the top
# division and the one below. European ones only -- a new country plays the European calendar,
# and a cup's round dates are its prototype's. (code, bracket)
NATIONAL_CUPS = {12: ("SCOTLAND_CUP", 12), 16: ("BELGIUM_CUP", 16), 18: ("NETHERLANDS_D1_CUP", 18),
                 20: ("ENGLAND_D1_CUP", 44)}
# Two divisions always go on a bracket of the whole field. The Coupe de France (36 clubs on a
# bracket of 18) and the Coppa Italia (40 on 20) were copied with their own brackets until
# 0.1.7, and a Polish cup of 18 + 18 built on the French one played a first round of 32 and then
# a round of 32 with only its 16 winners in it, the four clubs left over never drawn and the
# final played between two clubs of the same half (Discord, 2026-10-01) -- the DFB-Pokal's
# shipped bracket of 24 lost its round of 16 the same way (#21).
NATIONAL_CUPS_TWO = {44: ("ENGLAND_D1_CUP", 44)}
# Any other number of clubs: the English cup. Its calendar (exe case 6, shared by the Italian,
# Spanish, French, Dutch, Portuguese, German, Russian and Turkish cups) dates round ids 0x2e,
# 0x2f, 0x30 and 0x33..0x35, and the game numbers a knockout's rounds from 0x2e up to the
# quarter-final, which is 0x33 (read from the shipped tables 2026-09-29: 44, 42, 41, 40, 36, 18
# and 16 entries all on that calendar, a 20-club cup of ours measured on it 2026-09-18). So every
# field of 9 to 64 clubs has all its rounds dated; the byes of a field that is not a power of two
# are the game's own (Brazil's 41, Spain's 42).
# The bracket a cup is built with is then always its field (national_cup), whatever the
# prototype's: the game takes the number of rounds from the larger of bracket and field, and
# the first round is the clubs past the round after it. 22 clubs on the FA Cup's bracket of 44
# got six rounds, all 22 played the first and 11 winners went into a round of 32 (#74, measured
# 2026-10-01: 11 matches, then 5); every shipped cup whose bracket equals its field (44, 30,
# 20, 18, 16) plays clean, and Greece's 14 on 16 does too, as 16 makes no extra round.
# Fields of 32 or fewer the bracket screen can show: 0x140b33340 returns a bye layout for 2-16,
# 18, 20, 24, 28 and 30 (32 needs none) and NULL for the rest, which 0x140b34501 then reads
# (#74, a cup of 22, 2026-10-01). Every shipped cup of 32 or fewer is one of these sizes.
# The entry list alone does not do it: the game fills the cup from both leagues (22 again,
# 2026-10-02), so the world file names the field for fl26chain (cupn=).
BRACKET_SIZES = set(range(2, 17)) | {18, 20, 24, 28, 30, 32}
NATIONAL_CUP_ANY = ("ENGLAND_D1_CUP", 44)
NATIONAL_CUP_MAX = 44                    # the FA Cup's 44: no shipped cup has a bigger field
# The round ids each shipped domestic cup's calendar dates (tools/caltab.py, 2026-09-29), for a
# second division of ours under a shipped top flight (GitHub #32): the country's cup then takes
# both divisions, as the real DFB-Pokal does, when its calendar dates every round of that field
# (cup_rounds). A 38-club DFB-Pokal on its shipped bracket of 24 lost its round of 16 (#21), so
# the bracket is set to the field (until 0.1.7 it was raised to 44, which leaves a field of 32 or
# fewer without its first round's byes -- see NATIONAL_CUP_ANY, #74).
_CASE6 = {0x2e, 0x2f, 0x30, 0x33, 0x34, 0x35}
CUP_DATED = {23: _CASE6, 24: _CASE6, 25: _CASE6, 26: _CASE6, 27: _CASE6, 28: _CASE6, 53: _CASE6,
             123: _CASE6, 125: _CASE6, 31: _CASE6, 68: _CASE6,
             54: {0x2e, 0x2f, 0x33, 0x34, 0x35}, 55: {0x2e, 0x2f, 0x33, 0x34, 0x35},
             59: {0x2e, 0x2f, 0x33, 0x34, 0x35}, 126: {0x2e, 0x2f, 0x33, 0x34, 0x35},
             127: {0x2e, 0x2f, 0x33, 0x34, 0x35}, 164: {0x2e, 0x2f, 0x33, 0x34, 0x35},
             122: {0x2e, 0x33, 0x34, 0x35}, 124: {0x2e, 0x33, 0x34, 0x35},
             137: {0x2e, 0x33, 0x34, 0x35}, 142: {0x2e, 0x33, 0x34, 0x35}}
SUPER_CUP_LIKE = "BELGIUM_SUPER_CUP"      # two clubs, one match, a European date
LIBQ_ROOM = 6                             # Libertadores qualifying: 8 places, fl26swiss keeps 2 of the game's
SEASONS = ("august", "calendar")           # a new country's season: August-May, February-December
# the shipped regions whose season is the calendar year, type 1 in the exe's region table
# (0x141576140, read from FL_2026.exe 2026-10-04: 16 18 19 21 23 28, and 24): Brazil, Argentina,
# Colombia, China, Chile, Japan, Saudi Arabia. A new division under one of their leagues plays
# February to December with it (GitHub #86: the Saudi First Division "started in February")
CALENDAR_REGIONS = {16, 18, 19, 21, 23, 24, 28}
SAUDI_REGION, SAUDI_CUP, SAUDI_SUPER_CUP = 28, 164, 165    # the region holds KSA's 162/164/165 only
# The game's February-December countries a recipe can move to August-May ("game_seasons",
# Gu 2026-10-07: the J.League goes to August-May from 2026/27): country -> (region, its leagues,
# {cup: the shipped cup whose dates it takes}). The region's season line makes the game run it
# August-May (fl26join), fl26swiss dates the leagues on the European league calendar
# (SHIPPED_REGION_LEAGUES there) and the cups take an August-May cup's dates, one of the same
# bracket where there is one (the English cup's calendar dates every round of 9 to 64 clubs).
# Brazil's and Chile's cups are on the English cup's calendar already. Colombia and the USA
# play Apertura and Clausura and stay as they are.
GAME_SEASONS = {
    "Brazil": (16, (29, 163), {}),
    "Chile": (18, (67,), {}),
    "China": (21, (120,), {127: "BELGIUM_CUP", 132: SUPER_CUP_LIKE}),
    "Japan": (24, (52,), {55: "ENGLAND_D1_CUP", 97: SUPER_CUP_LIKE}),
    "Saudi Arabia": (28, (162,), {SAUDI_CUP: "BELGIUM_CUP", SAUDI_SUPER_CUP: SUPER_CUP_LIKE}),
}
CCUP_SIZES = (32, 16, 8, 4)              # the fields a continental cup can have (fl26swiss.dll)
CCUP_REG_FROM = 197                      # its regulation ids: past the split phases' 191..196
CCUP_KEEP = set(range(186, 197))         # the Conference League's 186..189, 190 (moved 145), splits
MAX_CCUP = 16                            # cups fl26swiss.dll takes from the world file (MAX_CCUP)
CCUP_KNOCKOUT_MAX = 16                   # a cup with no groups: four two-legged rounds at most
# the ids the season builder 0x1413156e0 admits at creation, whatever fl26joindll says (its
# include list as fl26join.log printed it on 2026-09-28): an exhibition league must not be one
CREATION_IDS = {2, 3, 4, 5, 6, 7, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 49, 50, 53,
                59, 60, 61, 62, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 95, 115, 116,
                117, 118, 122, 123, 124, 125, 128, 129, 130, 133, 134, 135, 136, 137, 141, 142, 147,
                148, 151, 155, 156, 159, 172, 175}
# the last id of the case table the game reads its in-play registrations from (fl26join.c)
REG_CASE_MAX = 175
# A league of ours plays on the big-league calendar (case 5) shifted by its regulation id's day
# (datecave.py; the patch set's date_offsets, patches/...-fixtures.json), resampled to its rounds
# by fl26swiss's league_dates. The shift was there to spread the 280 matches a day, and knows
# nothing of Europe: Romania on 93 (+6) played a league round on five Conference League days, the
# result written to both tables (GitHub #54). So a league with European places takes, of the ids
# left with a slot, the one whose days miss EURO_DAYS (plan()); +2 misses nearly all, +4 next.
BIG_LEAGUE_DAYS = [233, 240, 261, 265, 268, 275, 296, 300, 303, 310, 321, 324, 331, 335, 338, 345,
                   356, 359, 363, 2, 13, 16, 20, 23, 31, 34, 37, 51, 58, 65, 72, 79, 100, 107, 114,
                   121, 128, 142]
DATE_SHIFT = {11: 1, 49: 2, 60: 1, 61: 2, 62: 5, 74: 5, 76: 2, 93: 6, 94: 2, 96: 2, 98: 4, 100: 1,
              109: 1, 110: 1, 111: 1, 112: 4, 113: 5, 114: 2, 121: 2, 138: 2, 139: 2, 140: 2, 143: 5,
              144: 2, 145: 2, 146: 6, 170: 4, 171: 6, 173: 1, 174: 0, 176: 1, 178: 6, 179: 4, 180: 0,
              181: 1, 182: 5, 183: 1, 184: 6, 185: 1, 190: 2}     # 190 has 145's (mkworld MOVED_REG)
# fl26swiss.c: the Champions League's and the Europa League's league phase (SWISS_DAYS, the same
# days since #54), the Conference League's (UECL_DAYS), the knockouts (KO_DAYS), qualifying
# (QR_DAYS) and the play-offs (reg 2's moved to 241/248, the Europa/Conference League's 49/56).
# fl26swiss also moves any round of ours still on one of these days (declash), so this only
# steers the choice of id.
_SWISS = [257, 258, 271, 272, 292, 293, 306, 307, 327, 328, 341, 342, 19, 20, 26, 27]
EURO_DAYS = (set(_SWISS)
             | {272, 273, 293, 294, 307, 308, 328, 329, 342, 343, 349, 350}
             | {68, 75, 96, 103, 117, 124, 149, 70, 77, 98, 105, 119, 126, 139, 146}
             | {242, 247, 229, 236, 220, 225, 241, 248, 47, 54, 49, 56})
# The days of the year the domestic knockouts are played on, one per record of the knockout
# fl26swiss borrows (two legs of the last 16, quarter-finals, semi-finals, then the final):
# always seven, a smaller field leaves the first ones unused. A league cup's run September to
# December on Mondays and midweek days chosen so that fl26swiss.rest_dates can keep two free days
# around every round of a 36- or 38-round league as well (the old Mondays every fortnight, 263 +
# 14n, left it no room and every such league fell back to ignoring its cup); a pre-season
# cup's run from early July, after the season's July turn, filled on PRESEASON_FILL.
LEAGUE_CUP_DAYS = [256, 287, 291, 314, 326, 340, 356]
PRESEASON_FILL = 183
PRESEASON_DAYS = [186, 189, 192, 195, 198, 201, 205]
# The CAF Super Cup: filled with the pre-season cups, the day after the July teardown, from the
# winners kept there; the knockout is handed seven days like every one, and a field of two plays
# the last, the final, on 26 July -- after the pre-season cups, before the new season is built
CAF_SUPER_DAYS = [187, 190, 193, 196, 199, 202, 207]
CAF_CL, CAF_CC = 6, 7                    # fl26world.CCUPS numbers of the two cups it takes
LEAGUE_CUP_SIZES = (16, 8, 4)
# A league cup's clubs past its 16, 8 or 4 play a pre-round first: the last 2x places of the
# field, the strongest v the weakest, home and away; the x winners take the knockout's last x
# places, so nobody is left out (GitHub #70: 4 of 20 clubs never played). The pre-round is a copy
# of reg 2 (mkeuropo.prerounds), eight ties at most; fl26swiss fills it from LEAGUE_PRE_FILL,
# plays it on LEAGUE_PRE_DAYS (246 and 249: the first tie is 21 September, #93), between the
# 250/251), and fills the knockout from LEAGUE_CUP_FILL, before its first day.
LEAGUE_PRE_MAX = 8
LEAGUE_PRE_FILL = 226
LEAGUE_PRE_DAYS = [246, 249]
LEAGUE_CUP_FILL = 253
# Apertura/Clausura: fl26swiss dates a split's phases on the Scottish season's 38 dates,
# resampled to its rounds (fl26swiss.c SCOT_DAYS, split_dates); split_days() does the same sums,
# so the playoffs can be put between the league days. Continental cup days (CCUP_GROUP_DAYS,
# CCUP_KO_DAYS there) are kept free when the league has European places.
# 257 is the shipped 254 moved off the national cups' first round (case 6: 251, 254), #70.
SPLIT_LINE = [226, 233, 240, 257, 261, 268, 275, 296, 300, 303, 310, 321, 324, 331, 338, 345, 356,
              359, 363, 2, 13, 16, 20, 23, 31, 34, 37, 51, 58, 65, 72, 79, 100, 107, 114, 121, 128, 142]
# fl26swiss starts our splits on the fourth date (SPLIT_SKIP there): the first three are behind
# a league that joins its season through register_all, and a round dated there went a year on.
SPLIT_SKIP = 3
SPLIT_MAX_ROUNDS = 46                    # a split's rounds, both phases: the Championship's calendar
# fl26swiss.c CCUP_GROUP_DAYS + CCUP_KO_DAYS: the champions' cups on Tuesdays, the cups below
# them on the Wednesdays of the same weeks (#70)
CCUP_DAYS = [327, 334, 26, 33, 40, 47, 75, 82, 96, 103, 117, 124, 138,
             328, 335, 27, 34, 41, 48, 76, 83, 97, 104, 118, 125, 139]
PLAYOFF_SIZES = (8, 4)
SEASON_TURN = 182                        # the season's July turn: day-of-year order starts here
# The Kick Off and Edit team lists are ordered by a fixed list of 89 slots in the exe (0x1427d5920,
# read by 0x140ead990): a slot that is not on it sorts last, after Classic Teams -- Peru on slot 49
# did (2026-09-28). fl26comptab rebuilds the list with each league of ours after the slot its
# world line names (kickoff=): the league above it, else the end of its continent's leagues in
# the shipped order (read live 2026-09-28: Europe 0..27 ending on the European cups' slot 25,
# South America 28..40 ending on the Sudamericana's 67, Asia 44..49 ending on 70). Shipped
# leagues' slots from the same reading of the parameter table.
# CONCACAF (6) goes after MLS (slot 17, in the Americas block of the exe's list: ... 99, 17, 26,
# 27, 28, 67 ...), so Mexico sits next to the USA, not behind Asia (GitHub #47)
# AFC goes after the J1 League (slot 18), the last Asian league before Other Clubs (Asia) on 70 in
# the exe's list (... 102, 119, 30, 18, 70, 22 ...), so the new Asian leagues sit with the game's
# own and the "Other" entry stays last (GitHub #38, #43); CAF and OFC follow that entry
# CONMEBOL (4) goes after Colombia (slot 99, the game's last South American league before MLS in
# that block) and after any division of the world below it, so the new South American leagues
# sit with the game's own, before MLS and CONCACAF (GitHub #38); it used to be the end of the
# block, after the Sudamericana's slot 67
KICKOFF_AFTER = {2: 25, 4: 99, 3: 18, 6: 17}     # UEFA, CONMEBOL, AFC, CONCACAF
COLOMBIA = 168
KICKOFF_OTHER = 70                        # CAF, OFC: no club list of their own, after Asia
SHIPPED_SLOT = {17: 7, 79: 50, 20: 8, 81: 52, 18: 9, 82: 53, 21: 10, 22: 12, 116: 91, 133: 114,
                19: 11, 80: 51, 117: 94, 118: 96, 50: 16, 30: 14, 29: 13, 163: 122, 67: 15, 119: 99,
                51: 17, 120: 102, 162: 119, 52: 18,
                # the league rows a division can be put under when the game's league is two
                # rows: MLS First/Second Round (51's slot), Colombia's I/II (119's slot) -- #38 --
                # and the regular season of the split leagues: Belgium 88, Denmark 105 (the first
                # two entries of the exe's list), Scotland's first phase (133's slot)
                166: 17, 167: 17, 168: 99, 169: 99, 155: 88, 147: 105, 134: 114}
UECL_CID = mkuecl.CID                    # the Conference League's competition id: no league takes it
# the league phase of the Champions League (phase 2) and Europa League (phase 1) as one group of
# 36, the shape fl26swiss.dll draws and the Conference League is cloned from (mkreshape.py)
RESHAPE = ["UEFA_CHAMPIONS_LEAGUE:2:groups:36:1:-", "UEFA_EUROPE_LEAGUE:1:groups:36:1:-"]
UNIPAR = "common/character0/model/character/uniform/team/UniformParameter.bin"
KIT_TEXTURES = "kit-textures.txt"
# a club id of the recipe's own (a league's "club_ids", so a kit, crest or face pack made for
# that id finds the club): above the game's last club and at most 81919, the end of the id block
# whose kits the engine names <id-65536>_ACL_ (mkkits.kit_key) -- the block the builder's own
# clubs count up in, and new clubs are added at the end of Team.bin in id order
CLUB_ID_MAX = 81919
# a club from the NewLife Database (the league's "newlife": {"clubs": [id, ...]}, which Mod
# Studio's NewLife page writes) keeps its NewLife id, one id in every mod that uses the database;
# kits for them are named <id & 0x23fff>_SDN_ (mkkits.kit_key)
NEWLIFE_TEAMS = (98304, 114687)
MARK = "fl26world.txt"                   # a folder holding one was built by this; nothing else is replaced

# the modules that read the world file, and the line each logs when it does (sider.log)
READERS = ["fl26joindll", "fl26chain", "fl26comptab", "fl26editlist", "fl26catlist",
           "fl26clubs", "fl26slotnames", "fl26swiss"]


class BuildError(Exception):
    pass


def call(mod, args):
    """run a tool's main() in this process (so the frozen .exe needs no Python), return its output"""
    old, buf = sys.argv, io.StringIO()
    sys.argv = [mod.__name__ + ".py"] + [str(a) for a in args]
    try:
        with contextlib.redirect_stdout(buf):
            rc = mod.main()
    except SystemExit as e:
        raise BuildError("%s: %s\n%s" % (mod.__name__, e, buf.getvalue()))
    finally:
        sys.argv = old
    if rc:
        raise BuildError("%s returned %s\n%s" % (mod.__name__, rc, buf.getvalue()))
    return buf.getvalue()


def base_dir(opt=None):
    try:
        return fl26world.base_dir(opt)
    except SystemExit as e:
        raise BuildError(str(e))


_FORMATIONS = {}


def formations(base):
    """[{label, name, club, places, clubs}] -- the formations the game's clubs use, most used
    first (mktactics.catalogue, labels naming a club where two shapes share a name); [] when the
    tables have no Tactics.bin"""
    key = os.path.normcase(os.path.abspath(base))
    if key not in _FORMATIONS:
        import mktactics
        try:
            rows, forms, _h = mktactics.read(base)
        except (OSError, ValueError, AssertionError):
            _FORMATIONS[key] = []
        else:
            names = {t: n for t, (n, _a) in game_clubs(base).items()}
            raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
            national = {int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little")
                        for o in range(0, len(raw), W.T_REC) if raw[o + T_NATIONAL] & 0x80}
            _FORMATIONS[key] = mktactics.catalogue(rows, forms, names, skip=national)
    return _FORMATIONS[key]


def formation_club(base, want):
    """the club of the game whose tactics give formation `want` (a label or a club id), or None"""
    w = str(want or "").strip()
    for e in formations(base):
        if w == e["label"]:
            return e["club"]
    if w.isdigit() and any(e["club"] == int(w) for e in formations(base)):
        return int(w)
    if w.isdigit():
        import mktactics
        rows, _f, _h = mktactics.read(base)
        return int(w) if any(c == int(w) for _k, c, _s in rows) else None
    return None


def club_formations(pl):
    """{new club id: formation} of the clubs that have one"""
    out = {}
    for p in pl["leagues"]:
        own = p.get("club_formations") or []
        gp = game_places(p)
        for k, t in enumerate(p.get("teams") or []):
            if k in gp:                      # a club of the game keeps its own tactics
                continue
            f = (own[k] if k < len(own) else "") or p.get("formation") or ""
            if f:
                out[t] = f
    return out


def unpack_tables(game, out, log=print):
    """unpack the game's tables (download/data_s2526*.cpk and the update's data_extra*.cpk, the
    later ones over the earlier, as the game layers them) into <out>; returns the folder with
    Team.bin -- the --base of the rest"""
    import cpkread
    cpks = sorted(glob.glob(os.path.join(game, "download", "data_s2526*.cpk")))
    if not cpks:
        raise BuildError("no download/data_s2526*.cpk in %s -- is that the game folder?" % game)
    # the update's tables ("National selection 2.2") go over the ones above, as the game layers
    # them: an edit file made for the updated database matches what we unpack then (#75, #63)
    cpks += sorted(glob.glob(os.path.join(game, "download", "data_extra*.cpk")))
    for c in cpks:
        n = cpkread.extract(c, out, ["common/etc/pesdb/", UNIPAR])
        log("  %-20s %d tables" % (os.path.basename(c), n))
    base = os.path.join(out, "common", "etc", "pesdb")
    if not os.path.exists(os.path.join(base, "Team.bin")):
        raise BuildError("the archives held no Team.bin")
    # the kit textures the game has: a kit lent without its texture shows as a blank one
    import re
    tex = set()
    for c in glob.glob(os.path.join(game, "Data", "*.cpk")) + cpks:
        try:
            tex |= {m for n in cpkread.names(c) for m in re.findall(r"(u\d{4,5}[a-z]\d)\.ftex", n)}
        except (OSError, ValueError, KeyError):
            pass
    with open(os.path.join(out, KIT_TEXTURES), "w") as f:
        f.write("".join("%s.ftex\n" % t for t in sorted(tex)))
    log("  %d kit textures" % len(tex))
    with open(os.path.join(out, UNPACKED), "w", encoding="utf-8") as f:
        json.dump(_table_cpks(game), f, indent=1)
    return base


UNPACKED = "fl26-unpacked.json"        # the archives an unpack read: {file name: [size, mtime]}


def _table_cpks(game):
    d = os.path.join(game, "download")
    return {os.path.basename(c): [os.path.getsize(c), int(os.path.getmtime(c))]
            for c in sorted(glob.glob(os.path.join(d, "data_s2526*.cpk")) + glob.glob(os.path.join(d, "data_extra*.cpk")))}


def tables_stale(game, out):
    """why the tables unpacked into <out> are older than the game's archives, or None: a game
    update added or changed a data_*.cpk since (GitHub #63: tables without the update's
    data_extra changed the starting elevens of the game's clubs). An unpack of an older Mod
    Studio left no record; it counts as stale when the game has a data_extra archive."""
    try:
        now = _table_cpks(game)
    except OSError:
        return None
    if not now or not os.path.isdir(out):
        return None
    try:
        was = json.load(open(os.path.join(out, UNPACKED), encoding="utf-8"))
    except (OSError, ValueError):
        return ("unpacked by an older Mod Studio, before the game's update archives were read"
                if any(k.startswith("data_extra") for k in now) else None)
    new = [k for k in now if k not in was]
    changed = [k for k in now if k in was and list(was[k]) != now[k]]
    if new or changed:
        return "the game was updated since (%s)" % ", ".join(new + changed)
    return None


def tables_root(base):
    """the unpack folder that holds <base> (…/common/etc/pesdb), or None"""
    parts = os.path.normpath(base).split(os.sep)
    return os.sep.join(parts[:-3]) if parts[-3:] == ["common", "etc", "pesdb"] else None


def load_recipe(path):
    r = json.load(open(path, encoding="utf-8"))
    if not r.get("world", "").startswith("_FL26"):
        raise BuildError("the world name must start with _FL26 (sider.ini roots are found by it)")
    r.setdefault("leagues", [])
    if not r["leagues"] and not has_edits(r):
        raise BuildError("the recipe adds no league and changes nothing")
    return r


def has_edits(r):
    """whether the recipe changes anything Build writes: the edit tab, the players, or a
    recipe-level key plan() reads. A false uecl or caf_super_cup turns one off, so it counts
    too. uefa_rank does not: applying it writes europe/game_europe/uefa_seed, the ones Build
    reads."""
    e = r.get("edits") or {}
    import lbplayers
    return bool(e.get("leagues") or e.get("clubs") or e.get("competitions") or e.get("swaps")) \
        or lbplayers.has_players(r) \
        or bool(r.get("game_cups") or r.get("game_europe") or r.get("uefa_seed")
                or r.get("preseason_cups") or r.get("ccup_names") or r.get("ccup_logos")
                or any((r.get("europe_first") or {}).values())
                or r.get("uecl_name") or r.get("uecl_logo") or r.get("caf_super_cup_logo")
                or r.get("saudi_august") or r.get("game_seasons") or r.get("editable_kits") or r.get("country_order")) \
        or r.get("uecl") is False or r.get("caf_super_cup") is False


# ---- what the game already has: its leagues and clubs, for the edit tab ----

def text(b):
    b = bytes(b).split(bytes(1))[0]
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("latin-1")


def game_leagues(base):
    """[(reg id, competition id, name, [team ids])] of every league in the tables -- the
    regulations of type 4 that are not a split phase, with the clubs entered in them"""
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    by_cid = {}
    for i in range(len(ents) // M.ENT):
        e = ents[i * M.ENT:(i + 1) * M.ENT]
        by_cid.setdefault(e[M.E_CID], []).append((e[M.E_ORDER], int.from_bytes(e[M.E_TEAM:M.E_TEAM + 4], "little")))
    out, seen = [], set()
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        if g[M.R_TYPE] not in (4, fl26world.SPLIT_TOTAL) or fl26world.fmt(g) in (fl26world.F_REGULAR,) + fl26world.F_GROUPS:
            continue
        cid = g[M.R_CID]
        if cid in seen:
            continue
        seen.add(cid)
        teams = [t for _, t in sorted(by_cid.get(cid, []))]
        if teams:                            # "League 0" has none: nothing to show or change
            out.append((u16(g, M.R_ID), cid, text(g[M.R_NAME:M.R_NAME + M.NAME_SLOT]), teams))
    return sorted(out, key=lambda x: x[2].lower())


def game_clubs(base):
    """{team id: (name, short name)} of Team.bin"""
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    out = {}
    for i in range(len(raw) // W.T_REC):
        r = raw[i * W.T_REC:(i + 1) * W.T_REC]
        out[int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")] = (
            text(r[W.T_NAME:W.T_NAME + W.T_NAME_LEN]), text(r[W.T_ABBR:W.T_ABBR + W.T_ABBR_LEN]))
    return out


T_NATIONAL = 0x53                           # top bit set on the 144 national teams, never on a club
T_COUNTRY = 0x46                            # the country: 9 bits from bit 2 (lbplayers.T_COUNTRY, clubnation.py)
T_POOL = 0x4f                               # high nibble: the game's "Other ..." group the club is filed in at
                                            # boot (2 Other European, 6 Other Latin American, 7 Africa, 0 none)


def game_others(base, leagues):
    """(national team ids, other club ids): the teams in no league -- the game's "Others"
    sections, clubs that only play a cup or a continental competition, or nothing at all"""
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    inl = {t for *_, ts in leagues for t in ts}
    nat, other = [], []
    for i in range(len(raw) // W.T_REC):
        r = raw[i * W.T_REC:(i + 1) * W.T_REC]
        tid = int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")
        if tid not in inl:
            (nat if r[T_NATIONAL] & 0x80 else other).append(tid)
    return sorted(nat), sorted(other)


def recipe_from_plan(pl, base):
    """the recipe a built world was made from, read back from its leaguebuilder-plan.json: for a
    world whose recipe was never saved (Mod Studio opens the live world, 0.1.8). The plan holds
    everything the recipe said about the leagues; the ids it adds (rid, cid, slot, teams ...) are
    left out, so the next Build gives them again."""
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    name_of_rid = {L["rid"]: L["name"] for L in pl.get("leagues") or []}
    out = []
    for L in (pl.get("leagues") or []) + (pl.get("others") or []):
        en = (cty.get(L.get("country")) or ("", None))[0]
        r = {"name": L["name"], "country": mkflags.title(en) if en else "", "clubs": L["clubs"]}
        if L.get("others"):
            r["others"] = next(k for k, v in OTHERS.items() if v == L["others"])
        else:
            r["legs"], r["exchange"] = L.get("legs", 2), L.get("exchange", 3)
        for k in ("logo", "flag", "formation"):
            if L.get(k):
                r[k] = L[k]
        for k in ("club_names", "club_crests", "club_abbrs", "club_coaches", "club_formations",
                  "club_kits", "club_away_kits"):
            if any(L.get(k) or []):
                r[k] = list(L[k])
        if any(x is not None for x in L.get("club_ids") or []):
            r["club_ids"] = ["" if x is None else str(x) for x in L["club_ids"]]
        if (L.get("newlife") or {}).get("clubs"):
            r["newlife"] = {"clubs": list(L["newlife"]["clubs"])}
        if L.get("europe"):
            r["europe"] = [list(e) for e in L["europe"]]
        if L.get("exhibition"):
            r["exhibition"] = True
        gc = []
        for at, e in sorted((L.get("game_clubs") or {}).items(), key=lambda x: int(x[0])):
            g = {"at": int(at), "id": e["id"]}
            if e.get("swap") is not None:
                g["swap"] = e["swap"]
            if e.get("keep"):
                g["keep"] = True
            gc.append(g)
        if gc:
            r["game_clubs"] = gc
        up = L.get("above")
        if up is not None:
            r["above"] = name_of_rid.get(up, up)
        oc = L.get("own_cup")
        if oc and L.get("above") is None:
            r["cup"] = True
            r["cup_name"] = oc.get("name") or ""
            if oc.get("logo"):
                r["cup_logo"] = oc["logo"]
            if oc.get("super"):
                r["supercup"] = True
                r["supercup_name"] = oc["super"]
                if oc.get("super_logo"):
                    r["supercup_logo"] = oc["super_logo"]
        lc = L.get("league_cup")
        if lc:
            r["league_cup"] = True
            r["league_cup_name"] = lc.get("name") or ""
            if lc.get("logo"):
                r["league_cup_logo"] = lc["logo"]
        if L.get("calendar"):
            r["season"] = "calendar"
        if L.get("split"):
            r["split"] = L["split"]
        out.append(r)
    rec = {"world": pl["world"], "leagues": out, "edits": pl.get("edits") or {},
           "players": pl.get("players") or {}}
    for k in ("uecl", "uecl_logo", "uecl_name", "editable_kits", "game_seasons", "cafsc"):
        if pl.get(k) not in (None, "", False) or k == "uecl":
            rec[k] = pl.get(k)
    return rec


def game_league_confeds(base, leagues):
    """{competition id: confederation code} of the game's leagues -- the code most of its
    clubs' countries have (Team.bin T_COUNTRY, Country.bin); 0 when nothing is known"""
    import collections
    conf = confederations(base)
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    of = {}
    for i in range(len(raw) // W.T_REC):
        r = raw[i * W.T_REC:(i + 1) * W.T_REC]
        of[int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")] = conf.get(
            (int.from_bytes(r[T_COUNTRY:T_COUNTRY + 2], "little") >> 2) & 0x1ff, 0)
    out = {}
    for rid, cid, name, teams in leagues:
        c = collections.Counter(of.get(t, 0) for t in teams if of.get(t, 0))
        out[cid] = c.most_common(1)[0][0] if c else 0
    return out


# A club of the game in a league of ours (the league's "game_clubs"): it needs a squad that can
# field a side (lbplayers.MIN_SQUAD), and it keeps its id, name, crest, kits, manager and players.
MIN_GAME_SQUAD = 18
_GAME_INFO = {}


def game_info(base):
    """what the tables say about the game's own teams, for picking clubs of the game:
    {"clubs": {id: (name, short)}, "national": {ids}, "entries": {id: [competition ids]},
     "squads": {id: players}, "league_cids": {competition ids of leagues},
     "comp_names": {competition id: name}, "league_of": {id: league name},
     "friendly_cids": {competition ids of pre-season tournaments}}"""
    key = os.path.normcase(os.path.abspath(base))
    if key in _GAME_INFO:
        return _GAME_INFO[key]
    import collections
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    national = {int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little")
                for o in range(0, len(raw), W.T_REC) if raw[o + T_NATIONAL] & 0x80}
    ents = M.load(base, "CompetitionEntry.bin")
    entries = {}
    for i in range(len(ents) // M.ENT):
        o = i * M.ENT
        entries.setdefault(int.from_bytes(ents[o + M.E_TEAM:o + M.E_TEAM + 4], "little"), []).append(ents[o + M.E_CID])
    asg = pesdb.wesys_unpack(open(os.path.join(base, "PlayerAssignment.bin"), "rb").read())
    squads = collections.Counter(int.from_bytes(asg[o + 8:o + 12], "little") for o in range(0, len(asg), 16))
    regs = M.load(base, "CompetitionRegulation.bin")
    names = {}
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        names.setdefault(g[M.R_CID], text(g[M.R_NAME:M.R_NAME + M.NAME_SLOT]))
    leagues = game_leagues(base)
    friendly = friendly_cids(leagues)
    leagues = [L for L in leagues if L[1] not in friendly]
    info = {"clubs": game_clubs(base), "national": national, "entries": entries, "squads": squads,
            "league_cids": {c for _r, c, _n, _t in leagues}, "comp_names": names,
            "league_of": {t: n for _r, _c, n, ts in leagues for t in ts}, "base": base,
            "friendly_cids": friendly}
    _GAME_INFO[key] = info
    return info


def special_team(name):
    """the teams in no league that are not clubs: the Master League's default squads, the
    classic teams and the all-star selection -- they sit with the other clubs in the tables"""
    n = (name or "").strip()
    return n.startswith("ML Default") or n.endswith(" Classics") or n == "World Selection"


def game_club_problem(info, tid):
    """why club tid of the game cannot play in a league of ours, or None"""
    if tid not in info["clubs"]:
        return "the game has no club %d" % tid
    name = info["clubs"][tid][0] or str(tid)
    if tid in info["national"]:
        return "%s is a national team" % name
    if special_team(name):
        return "%s is one of the game's special teams, not a club" % name
    if info["squads"].get(tid, 0) < MIN_GAME_SQUAD:
        return "%s has %d players; a club needs %d to play" % (name, info["squads"].get(tid, 0), MIN_GAME_SQUAD)
    return None


def friendly_cids(leagues):
    """the competitions of game_leagues that are pre-season tournaments, not leagues: their
    clubs also play in two or more other leagues (SPFL26's three Pre-season friendly Cups hold
    clubs of the Premier League, Serie A, LaLiga ...). A club there keeps its place when it moves
    to a new league, as the Premier League's clubs do."""
    import collections
    of = collections.defaultdict(set)
    for _r, c, _n, ts in leagues:
        for t in ts:
            of[t].add(c)
    return {c for _r, c, _n, ts in leagues
            if len(set().union(*(of[t] for t in ts)) - {c}) >= 2}


# the continental club competitions of the game (Club World Cup, Champions League, Europa League,
# UEFA Super Cup, Libertadores, AFC Champions League and the two ids between): a moved club of
# the game can keep its places there ("keep", #84)
CONTINENTAL_CIDS = frozenset(range(1, 9))


def game_club_where(info, tid, keep=False):
    """the names of the competitions the tables put club tid in, its league first ([] = none);
    a pre-season tournament is left out (the club keeps playing it), and with keep its
    continental competitions too"""
    cids = sorted(set(info["entries"].get(tid) or []) - info.get("friendly_cids", set())
                  - (CONTINENTAL_CIDS if keep else set()),
                  key=lambda c: (c not in info["league_cids"], c))
    return [info["comp_names"].get(c, "competition %d" % c) for c in cids]


def game_places(p):
    """{place (0-based): {"id": team id, "swap": ...}} of the clubs of the game in league p"""
    return {int(k): v for k, v in (p.get("game_clubs") or {}).items()}


def new_club_count(L):
    """the clubs a build makes for recipe league L: its places less the clubs of the game, plus
    one for every club of the game whose place in the game a new club takes"""
    gc = L.get("game_clubs") or []
    return int(L.get("clubs", 0) or 0) - len(gc) + sum(1 for e in gc if isinstance(e.get("swap"), dict))


# letters a decomposition does not take apart (Đ is not D + a mark)
FOLD = {"Đ": "D", "đ": "D", "Ł": "L", "ł": "L", "Ø": "O", "ø": "O", "ß": "SS", "Æ": "AE", "æ": "AE",
        "Œ": "OE", "œ": "OE", "Þ": "TH", "þ": "TH", "ı": "I"}


def ascii_letters(txt):
    """the letters and digits of a name in capitals, marks taken off: Željezničar -> ZELJEZNICAR.
    A short name is three bytes and the game's own are all A-Z and 0-9; the full name keeps
    its letters (UTF-8, as the game's Bayern München)."""
    import unicodedata
    txt = "".join(FOLD.get(c, c) for c in txt)
    txt = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in txt.upper() if c.isalnum() and c.isascii())


def short_name(txt):
    return ascii_letters(txt)[:W.T_ABBR_LEN]


def apply_edits(edits, raw, regs, log=print):
    """the recipe's changes to the game's own clubs and leagues, in the world's tables"""
    clubs = {int(k): v for k, v in (edits.get("clubs") or {}).items()}
    n = 0
    for i in range(len(raw) // W.T_REC):
        o = i * W.T_REC
        e = clubs.get(int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little"))
        if not e:
            continue
        if e.get("name"):
            M.put(raw, o + W.T_NAME, e["name"], W.T_NAME_LEN)
        if e.get("abbr"):
            raw[o + W.T_ABBR:o + W.T_ABBR + W.T_ABBR_LEN] = short_name(e["abbr"]).ljust(W.T_ABBR_LEN, bytes(1).decode()).encode("ascii")
        n += 1
    leagues = {int(k): v for k, v in (edits.get("leagues") or {}).items()}
    m = 0
    for i in range(len(regs) // M.REG):
        o = i * M.REG
        e = leagues.get(u16(regs[o:], M.R_ID))
        if e and e.get("name"):
            rename_reg(regs, o, e["name"])
            m += 1
    if n or m:
        log("  changed %d of the game's clubs and %d of its leagues" % (n, m))


NAME_CODE_SLOT = 9         # the tenth name is an internal label (ENGLAND_D1_LEAGUE,
                           # UEFA_CHAMPIONS_LEAGUE_PLAYOFF), not a language: a rename keeps it


def rename_reg(regs, o, name):
    """the regulation at regs[o:] called `name` in every language"""
    M.put_names(regs, o, name, skip=(NAME_CODE_SLOT,))


def swap_problems(recipe, base):
    """why the recipe's swaps (edits.swaps: [[team id, team id], ...], two clubs of the game's
    leagues trading places) cannot be built, as sentences"""
    pairs = (recipe.get("edits") or {}).get("swaps") or []
    if not pairs:
        return []
    info = game_info(base)
    taken = set()
    for L in recipe.get("leagues") or []:
        for g in L.get("game_clubs") or []:
            taken.add(int(g["id"]))
            if g.get("swap") not in (None, "") and not isinstance(g["swap"], dict):
                taken.add(int(g["swap"]))
    err, seen = [], set()
    for pair in pairs:
        try:
            a, b = (int(x) for x in pair)
        except (TypeError, ValueError):
            err.append("swap %r: two team ids" % (pair,))
            continue
        for t in (a, b):
            if t not in info["league_of"]:
                err.append("swap %d <-> %d: club %d plays in no league of the game" % (a, b, t))
            if t in seen:
                err.append("club %d is in two swaps" % t)
            if t in taken:
                err.append("club %d plays in a new league of the recipe; it cannot also swap" % t)
            seen.add(t)
        if a == b or (a in info["league_of"] and info["league_of"].get(a) == info["league_of"].get(b)):
            err.append("swap %d <-> %d: the two clubs play in the same league" % (a, b))
    return err


def exchange_entries(ents, a, b):
    """teams a and b trade every CompetitionEntry row: each takes the other's places in the
    league, the cups and the continental competitions; returns (rows of a, rows of b)"""
    na = nb = 0
    for i in range(len(ents) // M.ENT):
        o = i * M.ENT
        t = int.from_bytes(ents[o + M.E_TEAM:o + M.E_TEAM + 4], "little")
        if t == a:
            ents[o + M.E_TEAM:o + M.E_TEAM + 4] = b.to_bytes(4, "little")
            na += 1
        elif t == b:
            ents[o + M.E_TEAM:o + M.E_TEAM + 4] = a.to_bytes(4, "little")
            nb += 1
    return na, nb


def swap_entries(ents, old, new, skip=()):
    """every CompetitionEntry row of team `old` given to team `new`, but those of the
    competitions in skip; returns how many"""
    n = 0
    for i in range(len(ents) // M.ENT):
        o = i * M.ENT
        if int.from_bytes(ents[o + M.E_TEAM:o + M.E_TEAM + 4], "little") == old and ents[o + M.E_CID] not in skip:
            ents[o + M.E_TEAM:o + M.E_TEAM + 4] = new.to_bytes(4, "little")
            n += 1
    return n


def u16(g, off):
    return int.from_bytes(g[off:off + 2], "little")


# ---- what the window offers to choose from ----

def country_names(base):
    """the country names of Country.bin, title case, sorted, each once"""
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    return sorted({mkflags.title(en) for fid, (en, names) in cty.items()
                   if en and mkflags.by_name(cty, en) == fid})


# the everyday name of a country the game's table names otherwise. The League window lists these
# too, as "South Korea (Republic of Korea)", so a country is found under the name people look for
COUNTRY_ALIASES = {
    "South Korea": "Republic of Korea", "Korea Republic": "Republic of Korea", "North Korea": "Korea Dpr",
    "DR Congo": "Congo Dr", "Ivory Coast": "Côte D'ivoire", "Taiwan": "Chinese Taipei",
    "United States": "Usa", "Czechia": "Czech Republic", "Cape Verde": "Cabo Verde",
    "Brunei": "Brunei Darussalam", "East Timor": "Timor-leste", "Swaziland": "Eswatini",
}


def country_choices(names):
    """[(label, country)] for a country list: every name of `names`, plus an entry per alias whose
    country is there, sorted by label"""
    out = [(n, n) for n in names]
    out += [("%s (%s)" % (a, n), n) for a, n in COUNTRY_ALIASES.items() if n in names]
    return sorted(out, key=lambda x: x[0].lower())


def country_of(text, names):
    """the country `text` means: a name of `names`, a label of country_choices, or an alias;
    anything else comes back as it is"""
    t = (text or "").strip()
    low = {n.lower(): n for n in names}
    for label, n in country_choices(names):
        low.setdefault(label.lower(), n)
    for a, n in COUNTRY_ALIASES.items():
        if n in names:
            low.setdefault(a.lower(), n)
    return low.get(t.lower(), t)


PLAYER_IDS = "fl26playerids.json"     # in the world folder: {club: {player key: id}} of the last Build


def player_ids(game, world):
    """{club: {player key: player id}} the last Build of `world` gave, or {}"""
    import siderdir
    try:
        with open(os.path.join(siderdir.find(game), "livecpk", world, PLAYER_IDS), encoding="utf-8") as f:
            return json.load(f).get("clubs") or {}
    except (OSError, ValueError):
        return {}


def country_ids(base):
    """[(name, Country.bin id)] sorted by name: a player's Nationality is this id (measured: 146
    Brazil, 144 Argentina, 236 Spain on the game's own players). A name the table has twice
    carries its id, so each entry says which one it is."""
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    seen = {}
    for fid, (en, names) in cty.items():
        if en:
            seen.setdefault(mkflags.title(en), []).append(fid)
    out = []
    for nm, ids in seen.items():
        for fid in ids:
            out.append((nm if len(ids) == 1 else "%s (%d)" % (nm, fid), fid))
    return sorted(out, key=lambda x: x[0].lower())


def shipped_parents(base):
    """[(regulation id, name)] of the shipped divisions (Competition code *_D<n>_LEAGUE) that
    have no league below them yet -- the ones a new division can go under. A link to a
    regulation the tables do not have counts as none: J1 League's points at 145, the old J2"""
    import re
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    code = {comp[i * M.COMP + M.CID_OFF]:
            bytes(comp[i * M.COMP + M.CODE_OFF:(i + 1) * M.COMP]).split(b"\0")[0].decode("latin-1")
            for i in range(len(comp) // M.COMP)}
    rows = {u16(regs[i * M.REG:(i + 1) * M.REG], M.R_ID): regs[i * M.REG:(i + 1) * M.REG]
            for i in range(len(regs) // M.REG)}

    def name(g):
        raw = bytes(g[M.R_NAME:M.R_NAME + M.NAME_SLOT]).split(b"\0")[0]
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")
    out, halves = [], set()
    for rid in sorted(rows):
        g = rows[rid]
        if g[M.R_TYPE] != 4 or u16(g, M.R_BELOW) in rows or fl26world.fmt(g) in (12, 13, 14, 15):
            continue
        if not re.search(r"_D\d_LEAGUE$", code.get(g[M.R_CID], "")):
            continue
        # a shipped Apertura/Clausura season is a total (type 5) and its two halves (format 7, 8,
        # +0x06 the total): Liga BetPlay DIMAYOR I and II, MLS First and Second Round. Both halves
        # were listed, and Colombia read as two first divisions (GitHub #79): one entry now, the
        # first half under the season's name, as before the link goes on that half
        parent = u16(g, 0x06)
        if fl26world.fmt(g) in (7, 8) and parent in rows:
            if parent in halves:
                continue
            halves.add(parent)
            out.append((rid, name(rows[parent])))
            continue
        out.append((rid, name(g)))
    return sorted(out, key=lambda x: x[1].lower())


def shipped_calendar(base):
    """regulation ids of the game's leagues whose country plays February to December
    (CALENDAR_REGIONS): a division below one follows that season"""
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    region = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
              for i in range(len(comp) // M.COMP)}
    return {u16(regs[i * M.REG:(i + 1) * M.REG], M.R_ID) for i in range(len(regs) // M.REG)
            if regs[i * M.REG + M.R_TYPE] == 4 and region.get(regs[i * M.REG + M.R_CID]) in CALENDAR_REGIONS}


def shipped_tiers(base):
    """{regulation id: division} of the game's leagues (1 = top), for saying which division a
    new league below one of them becomes"""
    regs = M.load(base, "CompetitionRegulation.bin")
    return {u16(regs[i * M.REG:(i + 1) * M.REG], M.R_ID): M.get_tier(regs[i * M.REG:(i + 1) * M.REG])
            for i in range(len(regs) // M.REG)}


def cup_field_of_region(regrow, region_of_cid, region, up):
    """(cup, top league, second league) for a new division 3 or lower under shipped league up, or
    None. The game fills a domestic cup from the region's first league -- the lowest regulation id
    -- and the league linked below it, and a new league gets a low id: England with League One,
    League Two and the National League added under the Championship (Evo-Web, 2026-10-01) played
    the FA Cup between League One and League Two only. fl26chain gives the cup back the two
    shipped divisions it has in the game (cuptop/cuplow on the league line)."""
    cup = home_cup(regrow, region_of_cid, region)
    r, seen = up, 0
    while r in regrow and M.get_tier(regrow[r]) > 1 and seen < 8:
        r, seen = u16(regrow[r], R_ABOVE), seen + 1
    low = u16(regrow[r], M.R_BELOW) if r in regrow else 0
    if not cup or r not in regrow or M.get_tier(regrow[r]) != 1 or low not in regrow:
        return None
    return cup, r, low


def home_cup(regrow, region_of_cid, region):
    """the domestic cup of a region (a knockout, not a two-club super cup), or None.

    GitHub #21. The game fills a domestic cup from the region's first league and the league
    linked below it. A shipped cup built for one division (the DFB-Pokal's 18, the Russian
    Cup's 16) does not survive that: with a new second division under its league it gets 38
    or 36 clubs, or only the new league's clubs when that league has the lower regulation id,
    and its bracket loses rounds. fl26chain puts the top league's clubs back; this names the
    cup it has to watch."""
    cups = sorted(rid for rid, g in regrow.items()
                  if rid < 1024 and g[M.R_TYPE] == 3 and g[M.R_TEAMS] & 0x3f > 2
                  and region_of_cid.get(g[M.R_CID]) == region)
    return cups[0] if cups else None


def entries_of(base, cid):
    """how many clubs the shipped tables enter in competition cid (CompetitionEntry.bin): the
    clubs a league plays with, which its regulation's count need not say (Bundesliga: 20 v 18)"""
    ents = M.load(base, "CompetitionEntry.bin")
    return sum(1 for i in range(len(ents) // M.ENT) if ents[i * M.ENT + M.E_CID] == cid)


def comp_conf(base, cid):
    """the confederation of the game's competition cid (Competition.bin +6, low three bits, see
    CONFED_OFF), or None"""
    comp = M.load(base, "Competition.bin")
    for i in range(len(comp) // M.COMP):
        c = comp[i * M.COMP:(i + 1) * M.COMP]
        if c[M.CID_OFF] == cid and 2 <= c[M.FLAG_OFF] & 7 <= 7:
            return c[M.FLAG_OFF] & 7
    return None


def home_supercup(regrow, region_of_cid, region):
    """the super cup of a region (a two-club cup), or None. GitHub #29: the new second division
    under a shipped top flight also put one of its clubs into it; fl26chain swaps it out."""
    cups = sorted(rid for rid, g in regrow.items()
                  if rid < 1024 and g[M.R_TYPE] == 3 and g[M.R_TEAMS] & 0x3f == 2
                  and region_of_cid.get(g[M.R_CID]) == region)
    return cups[0] if cups else None


# ---- plan: every id, region and link decided, nothing written ----

def clubs_room(base):
    """how many new clubs fit: the club table stops at TEAM_CAP (the wall a 1536th club met,
    fl26-800-klubova-igra), and every new club takes SQUAD of the PLAYER_CAP player records
    the installed patch set allows -- with the shipped tables both come to 793"""
    n = lambda f, rec: len(pesdb.wesys_unpack(open(os.path.join(base, f), "rb").read())) // rec
    return min(TEAM_CAP - n("Team.bin", W.T_REC), (PLAYER_CAP - n("Player.bin", 312)) // SQUAD)


def august_countries(recipe):
    """the game's countries the recipe moves from February-December to August-May
    ("game_seasons", 0.2.0; the older "saudi_august" is Saudi Arabia)"""
    got = [c for c in recipe.get("game_seasons") or [] if c in GAME_SEASONS]
    if recipe.get("saudi_august") and "Saudi Arabia" not in got:
        got.append("Saudi Arabia")
    return sorted(got)


def august_regions(recipe):
    return {GAME_SEASONS[c][0] for c in august_countries(recipe)}


def august_leagues(recipe):
    """regulation ids of the game's leagues the recipe moves to August-May"""
    return {r for c in august_countries(recipe) for r in GAME_SEASONS[c][1]}


def pl_saudi_august(recipe, region):
    """whether the recipe moves the game's calendar-year region `region` to August-May"""
    return region in august_regions(recipe)


def plan(recipe, base):
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    regrow = {u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG:(i + 1) * M.REG]
              for i in range(len(regs) // M.REG)}
    region_of_cid = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
                     for i in range(len(comp) // M.COMP)}
    used_cid = set(region_of_cid)
    used_region = set(region_of_cid.values())

    names = [L.get("name", "").strip() for L in recipe["leagues"]]
    if not all(names) or len(set(n.lower() for n in names)) != len(names):
        raise BuildError("every league needs a name, and no two the same")
    # clubs in no league go their own way from here: no regulation, no competition, no region
    others = others_plan([L for L in recipe["leagues"] if L.get("others")], base, cty)
    full = recipe
    recipe = dict(recipe, leagues=[L for L in recipe["leagues"] if not L.get("others")])
    leagues = recipe["leagues"]
    names = [L.get("name", "").strip() for L in leagues]

    # mkworld's order (the free list, 145 moved to 190), keeping only ids with a slot
    free = []
    for r in range(1, W.REG_MAX + 1):
        if r in regrow or r in W.BAD_REG or r in W.MOVED_REG.values():
            continue
        r = W.MOVED_REG.get(r, r)
        if (r in fl26world.DEFAULT_SLOT or r in fl26world.NO_SLOT_IDS) and r not in regrow:
            free.append(r)
    free.sort(key=fl26world.id_rank)     # slotted ids first, the game's "other" groups last (#73)
    if leagues and len(leagues) > len(free):
        raise BuildError("%d leagues, but the game has room for %d (see docs/mod-studio.md)"
                         % (len(leagues), len(free)))
    cids = [c for c in range(CID_FROM, W.CID_MAX + 1) if c not in used_cid and c != UECL_CID][:len(leagues)]
    if len(cids) < len(leagues):
        raise BuildError("no free competition ids left")
    room = clubs_room(base)
    total = sum(new_club_count(L) for L in full["leagues"])
    if total > room:
        raise BuildError("%d new clubs, but the game has room for %d more (a full squad each)"
                         % (total, room))

    out, by_name, country_region = [], {}, {}
    order = order_by_parents(leagues)
    # an exhibition league first takes an id the season builder leaves alone; the others then
    # take what is left, in the usual order
    rid_of, left = {}, list(free)
    for i in order:
        if leagues[i].get("exhibition"):
            # above REG_CASE_MAX first: the game also enters ids up to it into a running season
            # on their registration day (fl26join.c), and 11, the first id outside CREATION_IDS,
            # was played in the background of a career (GitHub #53, enter_season(11))
            # (not 190: it stands in for 145, the league J1 relegates into)
            r = next((r for r in left if r > REG_CASE_MAX and r in fl26world.DEFAULT_SLOT
                      and r not in W.MOVED_REG.values()), None)
            if r is None:
                r = next((r for r in left if r not in CREATION_IDS), None)
            if r is None:
                raise BuildError("%s: no free regulation id outside Master League for an exhibition "
                                 "league" % names[i])
            rid_of[i] = r
            left.remove(r)
    # leagues with European places next: of the ids as good as the first one left (a slot of
    # their own), the one whose days clash least with the European ones (GitHub #54)
    for i in order:
        L = leagues[i]
        if i in rid_of or not L.get("europe") or not left:
            continue
        rounds = rounds_of(int(L.get("clubs", 0) or 0)) * int(L.get("legs", 2) or 2)
        # European days first: a clash with a league-cup date only breaks a tie (#54: an 18-club
        # league with a league cup took reg 98, 3 European clashes, to dodge two cup dates)
        cup = set(LEAGUE_CUP_DAYS) if L.get("league_cup") else set()
        best = fl26world.id_rank(left[0])
        r = min((r for r in left if fl26world.id_rank(r) == best),
                key=lambda r: (len(set(league_days(r, rounds)) & EURO_DAYS),
                               len(set(league_days(r, rounds)) & cup), left.index(r)))
        rid_of[i] = r
        left.remove(r)
    for i in order:
        if i not in rid_of:
            rid_of[i] = left.pop(0)
    for k, i in enumerate(order):
        L = leagues[i]
        name = names[i]
        n, legs = int(L.get("clubs", 0)), int(L.get("legs", 2))
        if not CLUBS_MIN <= n <= CLUBS_MAX:
            raise BuildError("%s: %d clubs -- a league has %d..%d" % (name, n, CLUBS_MIN, CLUBS_MAX))
        if not 1 <= legs <= LEGS_MAX:
            raise BuildError("%s: clubs meet 1..%d times, not %d" % (name, LEGS_MAX, legs))
        fid = mkflags.by_name(cty, L.get("country", ""))
        if fid is None:
            raise BuildError("%s: no country called %r in Country.bin" % (name, L.get("country")))
        p = {"name": name, "country": fid, "clubs": n, "legs": legs, "rid": rid_of[i], "cid": cids[k],
             "slot": fl26world.DEFAULT_SLOT.get(rid_of[i], fl26world.NO_SLOT), "club_names": list(L.get("club_names") or []),
             "exhibition": bool(L.get("exhibition")),
             "logo": L.get("logo") or None, "flag": L.get("flag") or None,
             "club_crests": list(L.get("club_crests") or []),
             "club_abbrs": list(L.get("club_abbrs") or []),
             "club_coaches": list(L.get("club_coaches") or []),     # managers' names, "" = made up (mkcoaches)
             "formation": str(L.get("formation") or "").strip(),
             "club_formations": [str(x or "").strip() for x in (L.get("club_formations") or [])],
             "club_ids": [int(x) if str(x or "").strip().isdigit() else None
                          for x in (L.get("club_ids") or [])][:n],     # ids of the recipe's own
             "club_kits": list(L.get("club_kits") or []),     # shirt words (shieldcrest) for crests
             "club_away_kits": list(L.get("club_away_kits") or []),   # and for picking kits (mkkits)
             "newlife": {"clubs": [int(i) for i in (L.get("newlife") or {}).get("clubs") or []]},
             "exchange": int(L.get("exchange", 3)), "above": None, "tier": 1,
             "europe": [[int(a), int(b)] for a, b in (L.get("europe") or [])]}
        for f in [p["formation"]] + p["club_formations"]:
            if f and formation_club(base, f) is None:
                raise BuildError("%s: no formation %r (the Formation list has them)" % (name, f))
        bad = europe_problems(n, L.get("europe") or [], bool(L.get("cup")))
        if bad:
            raise BuildError("%s: European places: %s" % (name, "; ".join(bad)))
        gc = {}
        for e in L.get("game_clubs") or []:
            try:
                at, tid = int(e.get("at", -1)), int(e.get("id", 0))
            except (TypeError, ValueError, AttributeError):
                raise BuildError("%s: a club of the game is written wrong: %r" % (name, e))
            if not 0 <= at < n:
                raise BuildError("%s: a club of the game at place %d, but the league has %d clubs"
                                 % (name, at + 1, n))
            if at in gc:
                raise BuildError("%s: two clubs of the game at place %d" % (name, at + 1))
            gc[at] = {"id": tid, "swap": e.get("swap"), "keep": bool(e.get("keep"))}
        p["game_clubs"] = gc
        if len(p["club_names"]) > n:
            raise BuildError("%s: %d club names for %d clubs" % (name, len(p["club_names"]), n))
        up = L.get("above")
        if up not in (None, ""):
            if isinstance(up, str) and not up.isdigit():
                parent = by_name.get(up.strip().lower())
                if parent is None:
                    raise BuildError("%s: no league called %r above it" % (name, up))
                p["above"], p["tier"], p["region"] = parent["rid"], parent["tier"] + 1, parent["region"]
                p["follows_calendar"] = bool(parent.get("calendar") or parent.get("follows_calendar"))
            else:
                pr = regrow.get(int(up))
                if pr is None or pr[M.R_TYPE] != 4:
                    raise BuildError("%s: regulation %s is not a shipped league" % (name, up))
                if u16(pr, M.R_BELOW) in regrow:
                    raise BuildError("%s: regulation %s already has a league below it (%d)"
                                     % (name, up, u16(pr, M.R_BELOW)))
                p["above"], p["tier"] = int(up), M.get_tier(pr) + 1
                p["region"] = region_of_cid[pr[M.R_CID]]
                p["follows_calendar"] = p["region"] in CALENDAR_REGIONS and not pl_saudi_august(recipe, p["region"])
                if p["tier"] >= 3:
                    p["cupfield"] = cup_field_of_region(regrow, region_of_cid, p["region"], int(up))
                    # the super cup is filled the same way, from the region's lowest regulation
                    # id: League One 01 played the Community Shield against Liverpool in the
                    # first July (2026-10-01). fl26chain swaps such a club out, as for #29.
                    if p["cupfield"]:
                        p["scup"] = home_supercup(regrow, region_of_cid, p["region"])
                if p["tier"] == 2:
                    p["cup"] = home_cup(regrow, region_of_cid, p["region"])
                    p["scup"] = home_supercup(regrow, region_of_cid, p["region"])
                    if p["cup"] and not L.get("cup_top_only"):
                        top = entries_of(base, pr[M.R_CID])
                        p["cup_all"] = top + n if cup_takes_both(p["cup"], top + n) else 0
            if p["tier"] > 7:
                raise BuildError("%s: division %d -- the rank field stops at 7" % (name, p["tier"]))
        else:
            key = fid
            if key not in country_region:
                reg = next((r for r in range(REGION_FIRST, REGION_LAST + 1) if r not in used_region), None)
                if reg is None:
                    raise BuildError("no free region left for %s" % L.get("country"))
                used_region.add(reg)
                country_region[key] = reg
            p["region"] = country_region[key]
            if L.get("cup"):
                p["own_cup"] = {"name": (L.get("cup_name") or "").strip() or name + " Cup",
                                "logo": L.get("cup_logo") or None}
                if L.get("supercup"):
                    p["own_cup"]["super"] = (L.get("supercup_name") or "").strip() or name + " Super Cup"
                    p["own_cup"]["super_logo"] = L.get("supercup_logo") or None
            elif L.get("supercup"):
                raise BuildError("%s: a super cup comes with the national cup (cup: true)" % name)
            if L.get("league_cup"):
                p["league_cup"] = {"name": (L.get("league_cup_name") or "").strip() or name + " League Cup",
                                   "logo": L.get("league_cup_logo") or None}
            season = str(L.get("season") or SEASONS[0]).strip().lower()
            if season not in SEASONS:
                raise BuildError("%s: the season is %s, not %r" % (name, " or ".join(SEASONS), L.get("season")))
            if season == "calendar":
                if p["exhibition"]:
                    raise BuildError("%s: an exhibition league plays no season" % name)
                p["calendar"] = True
        if L.get("season") and str(L.get("season")).strip().lower() != SEASONS[0] and p["above"]:
            raise BuildError("%s: the season belongs to the country's top division; the divisions "
                             "below it follow it" % name)
        if L.get("league_cup") and p["above"]:
            raise BuildError("%s: a league cup belongs to a country's top division" % name)
        if p["exhibition"]:
            bad = [w for w, on in (("the division above it", p["above"]), ("the European places", p["europe"]),
                                   ("the national cup", L.get("cup")), ("the league cup", L.get("league_cup")),
                                   ("the split", L.get("split")), ("the Apertura/Clausura", L.get("apertura"))) if on]
            if bad:
                raise BuildError("%s: an exhibition league stands alone -- take off %s" % (name, ", ".join(bad)))
        sp = L.get("split")
        if sp:
            groups = [int(x) for x in sp.get("groups", [])]
            if len(groups) < 2 or len(groups) > 3 or sum(groups) != n:
                raise BuildError("%s: split groups %s must be 2 or 3 counts adding up to %d" % (name, groups, n))
            p["split"] = {"legs": int(sp.get("legs", legs)), "groups": groups,
                          "group_legs": int(sp.get("group_legs", 1))}
            # fl26swiss dates the whole split on one line: the regular phase and the longest
            # group back to back, up to 38 rounds on the Premier League's calendar and up to 46
            # on the Championship's (split_dates, LONG_CAL_REG). Past that it dates nothing and
            # the league never plays (#54: 16 clubs twice, then 6 / 10 twice = 30 + 18 = 48).
            t = (p["split"]["legs"] * rounds_of(n)
                 + p["split"]["group_legs"] * max(rounds_of(g) for g in groups))
            if t > SPLIT_MAX_ROUNDS:
                raise BuildError("%s: the split is %d rounds (%d before the split, %d after), a season has "
                                 "%d dates at most -- fewer clubs in the biggest group, or its groups "
                                 "once instead of twice" % (name, t, p["split"]["legs"] * rounds_of(n),
                                                            t - p["split"]["legs"] * rounds_of(n),
                                                            SPLIT_MAX_ROUNDS))
        ap = L.get("apertura")
        if ap:
            if sp:
                raise BuildError("%s: a league is split or Apertura/Clausura, not both" % name)
            try:
                po = int((ap if isinstance(ap, dict) else {}).get("playoff", PLAYOFF_SIZES[0]))
            except (TypeError, ValueError):
                raise BuildError("%s: the playoff is 8, 4 or 0 clubs" % name)
            if po not in (0,) + PLAYOFF_SIZES:
                raise BuildError("%s: the playoff is 8, 4 or 0 clubs, not %d" % (name, po))
            if 2 * rounds_of(n) > len(SPLIT_LINE) - SPLIT_SKIP:
                raise BuildError("%s: Apertura and Clausura of %d rounds each need %d dates, a season has %d"
                                 " -- 18 clubs at most" % (name, rounds_of(n), 2 * rounds_of(n),
                                                           len(SPLIT_LINE) - SPLIT_SKIP))
            p["split"] = {"legs": 1, "groups": [n], "group_legs": 1, "apertura": True}
            p["apertura"] = {"playoff": po, "logo": L.get("playoff_logo") or None}
        by_name[name.lower()] = p
        out.append(p)
    game_club_checks(out, base)
    if sum(1 for p in out if p.get("split")) > MAX_SPLITS:
        raise BuildError("at most %d split leagues for now (the phase ids tested are 191..196)" % MAX_SPLITS)
    for p in out:
        # the points carry goes by the country's competition key, not by league (fl26swiss.c
        # split_keys): a Scottish split there would make the Clausura carry its points too
        q = next((q for q in out if p.get("apertura") and q.get("split") and not q.get("apertura")
                  and q["region"] == p["region"]), None)
        if q:
            raise BuildError("%s and %s: a country has Apertura/Clausura or a split that keeps its"
                             " points, not both" % (p["name"], q["name"]))
    for p in out:
        # the game finds a split's phases by the country's competition key too (0x1414ce270
        # under 0x14134a540): Iceland with Apertura/Clausura in both divisions (GitHub #45, 0.1.3.1)
        # showed all 20 clubs under the first division and played no match in either
        q = next((q for q in out if q is not p and p.get("split") and q.get("split")
                  and q["region"] == p["region"]), None)
        if q:
            raise BuildError("%s and %s: only one league of a country can be split or Apertura/Clausura"
                             " for now -- with two, the game mixes up their phases and neither plays"
                             % (p["name"], q["name"]))
    for p in out:
        if not (p.get("calendar") or p.get("follows_calendar")):
            continue
        # the whole country plays February to December: its cups and phases have European dates.
        # A division under the game's own Feb-Dec league (Colombia's) too (Discord, aaron 07.10.)
        bad = [w for q in out if q["region"] == p["region"]
               for w, on in (("a split (%s)" % q["name"], q.get("split") and not q.get("apertura")),
                             ("Apertura/Clausura (%s)" % q["name"], q.get("apertura")),
                             ("the national cup", q.get("own_cup")),
                             ("the league cup", q.get("league_cup"))) if on]
        if bad:
            raise BuildError("%s: a country playing February to December cannot have %s yet -- take it off"
                             % (p["name"], ", ".join(bad)))
    for p in out:
        below = [q for q in out if q["above"] == p["rid"]]
        if below and p["exhibition"]:
            raise BuildError("%s: an exhibition league has no league below it (%s)" % (p["name"], below[0]["name"]))
        if len(below) > 1:
            raise BuildError("%s has %d leagues below it; the game follows one link"
                             % (p["name"], len(below)))
    # the same under a league of the game (GitHub #98: three Serie C groups under Serie B put the
    # same relegated clubs into all three and lost the promoted ones)
    ours = {p["rid"] for p in out}
    gname = dict(shipped_parents(base))
    for g in sorted({p["above"] for p in out if p["above"] and p["above"] not in ours}):
        below = [p["name"] for p in out if p["above"] == g]
        if len(below) > 1:
            raise BuildError("%s are all under %s; the game follows one link down from a league, so only "
                             "one of them can be under it -- groups of one division are not possible yet"
                             % (", ".join(below), gname.get(g, "regulation %d" % g)))
    for p in out:
        if p.get("own_cup"):
            national_cup(p, next((q for q in out if q["above"] == p["rid"]), None))
    bad = club_id_problems(out + others, base)
    if bad:
        raise BuildError("club ids:\n  " + "\n  ".join(bad[:20]))
    nlt, free_ids = newlife_tids(full.get("leagues") or [], base, full.get("newlife_ids"))   # #90 / #88
    for p in out + others:
        p["newlife_tid"] = nlt
    import lbplayers
    bad = lbplayers.check(full)
    if bad:
        raise BuildError("player changes:\n  " + "\n  ".join(bad[:20]))
    ge, gr, gn, gcc = game_europe(recipe, regrow, region_of_cid, base)
    room = {p["rid"]: p["clubs"] for p in out}
    room.update({r: entries_of(base, regrow[r][M.R_CID]) for r, _p, _c, _a in gcc})
    cups, notes = ccup_plan([(p["rid"], pos, comp, 0) for p in out for pos, comp in p["europe"]] + gcc, room)
    for c in cups:            # a game league's cup winner: its national cup is the game's (#95)
        c["winners"] = [[e[1], home_cup(regrow, region_of_cid, region_of_cid.get(regrow[e[1]][M.R_CID]))]
                        for e in c["entry"] if e[0] == "cup" and e[1] in regrow
                        and e[1] not in {p["rid"] for p in out}]
    home = [league_cup(p, out) for p in out if p.get("league_cup")]
    home += game_cups(recipe, regrow, region_of_cid, base, out)
    home += [c for p in out if p.get("apertura") for c in playoff_cups(p)]
    home += [preseason_cup(c, k, by_name) for k, c in enumerate(recipe.get("preseason_cups") or [])]
    if recipe.get("caf_super_cup", True) and {CAF_CL, CAF_CC} <= {c["number"] for c in cups}:
        cups.append(caf_super_cup(recipe))
    for c in cups:
        k = str(c["number"])
        c["name"] = ((recipe.get("ccup_names") or {}).get(k) or "").strip() or c["name"]
        c["logo"] = (recipe.get("ccup_logos") or {}).get(k) or c.get("logo")
        if "|" in c["name"]:
            raise BuildError("%s: a name cannot have a | in it" % c["name"])
    bad = swap_problems(recipe, base)
    if bad:
        raise BuildError("clubs that swap leagues:\n  " + "\n  ".join(bad))
    bad = competition_problems(recipe.get("edits") or {}, base)
    if bad:
        raise BuildError("competition names:\n  " + "\n  ".join(bad))
    if len(cups) + len(home) > MAX_CCUP:
        raise BuildError("%d continental, league and pre-season cups -- fl26swiss.dll takes %d"
                         % (len(cups) + len(home), MAX_CCUP))
    return {"world": recipe["world"], "leagues": out, "others": others, "edits": recipe.get("edits") or {},
            "free_ids": free_ids, "players": recipe.get("players") or {}, "uecl": bool(recipe.get("uecl", True)),
            "uecl_logo": recipe.get("uecl_logo") or None,
            "uecl_name": (recipe.get("uecl_name") or "").strip() or None,
            "game_europe": ge, "game_replace": gr, "game_names": gn,
            "uefa_seed": uefa_seed(recipe, out, regrow, region_of_cid),
            "ccups": cups, "ccup_notes": notes, "home_cups": home,
            "europe_first": europe_first(recipe, by_name),
            "game_seasons": august_countries(recipe),
            "editable_kits": bool(recipe.get("editable_kits")),
            "country_order": recipe.get("country_order") or None,
            "cup_draw": cup_draw(recipe)}


CUP_DRAWS = ("seeded", "random", "off")


def cup_draw(recipe):
    """how the country cups are drawn: "seeded" (the default) puts the top division's clubs into
    the later rounds and spreads them over both halves, so they meet the lower leagues' clubs
    and not each other early; "random" draws the bracket blind; "off" leaves it as the game
    fills it, in list order -- every top club on one side (in game, 07.10.)"""
    v = (recipe.get("cup_draw") or "seeded").strip().lower()
    if v not in CUP_DRAWS:
        raise BuildError("cup_draw %r: one of %s" % (v, ", ".join(CUP_DRAWS)))
    return v


def others_plan(groups, base, cty):
    """the plan of the recipe's clubs in no league (the "others" key): what plan() makes of a
    league, less everything that belongs to a competition"""
    import mkflags
    out = []
    for L in groups:
        name = L["name"].strip()
        pool = OTHERS.get(str(L.get("others")).strip().lower())
        if pool is None:
            raise BuildError("%s: others is %s, not %r" % (name, ", ".join(OTHERS), L.get("others")))
        n = int(L.get("clubs", 0) or 0)
        if not 1 <= n <= OTHERS_MAX:
            raise BuildError("%s: %d clubs -- a group of clubs in no league has 1..%d" % (name, n, OTHERS_MAX))
        fid = mkflags.by_name(cty, L.get("country", ""))
        if fid is None:
            raise BuildError("%s: no country called %r in Country.bin" % (name, L.get("country")))
        bad = [w for w, on in (("the division above it", L.get("above") not in (None, "")),
                               ("the European places", L.get("europe")), ("the national cup", L.get("cup")),
                               ("the league cup", L.get("league_cup")), ("the split", L.get("split")),
                               ("the Apertura/Clausura", L.get("apertura")), ("exhibition", L.get("exhibition")),
                               ("clubs of the game", L.get("game_clubs"))) if on]
        if bad:
            raise BuildError("%s: clubs in no league have no league around them -- take off %s"
                             % (name, ", ".join(bad)))
        p = {"name": name, "others": pool, "country": fid, "clubs": n,
             "club_names": list(L.get("club_names") or []),
             "club_crests": list(L.get("club_crests") or []),
             "club_abbrs": list(L.get("club_abbrs") or []),
             "club_coaches": list(L.get("club_coaches") or []),
             "formation": str(L.get("formation") or "").strip(),
             "club_formations": [str(x or "").strip() for x in (L.get("club_formations") or [])],
             "club_ids": [int(x) if str(x or "").strip().isdigit() else None
                          for x in (L.get("club_ids") or [])][:n],
             "club_kits": list(L.get("club_kits") or []),
             "club_away_kits": list(L.get("club_away_kits") or []),
             "newlife": {"clubs": [int(i) for i in (L.get("newlife") or {}).get("clubs") or []]},
             "game_clubs": {}}
        if len(p["club_names"]) > n:
            raise BuildError("%s: %d club names for %d clubs" % (name, len(p["club_names"]), n))
        for f in [p["formation"]] + p["club_formations"]:
            if f and formation_club(base, f) is None:
                raise BuildError("%s: no formation %r (the Formation list has them)" % (name, f))
        out.append(p)
    return out


def game_club_checks(out, base):
    """the clubs of the game the leagues of plan `out` take (game_places): each usable, each in
    one place only, and each that plays anywhere in the game (a league, a cup, a continental
    competition) with a club to take its place there -- one in no competition at all, or a new
    one ({"name": ...}), so every competition keeps its number of clubs. Normalises "swap" to
    None, a team id or {"name": ...}."""
    if not any(p.get("game_clubs") for p in out):
        return
    info = game_info(base)
    used = {}
    for p in out:
        for at, g in sorted(p["game_clubs"].items()):
            tid = g["id"]
            bad = game_club_problem(info, tid)
            if bad:
                raise BuildError("%s, club %d: %s" % (p["name"], at + 1, bad))
            if tid in used:
                raise BuildError("%s is in %s and in %s: a club plays in one league"
                                 % (info["clubs"][tid][0], used[tid], p["name"]))
            used[tid] = p["name"]
    for p in out:
        for at, g in sorted(p["game_clubs"].items()):
            tid, sw = g["id"], g.get("swap")
            name = info["clubs"][tid][0]
            where = game_club_where(info, tid, g.get("keep"))
            if not where:
                g["swap"] = None                     # nothing to hand over
                continue
            if sw in (None, "", {}, 0):
                cont = not game_club_where(info, tid, True)
                raise BuildError("%s, club %d: %s plays in %s -- pick the club that takes its place there%s"
                                 % (p["name"], at + 1, name, ", ".join(where),
                                    " (or tick 'It keeps its places in continental competitions' in Club of "
                                    "the game)" if cont else ""))
            if isinstance(sw, dict):
                nm = str(sw.get("name") or "").strip()
                if not nm:
                    raise BuildError("%s, club %d: the new club taking %s's place needs a name"
                                     % (p["name"], at + 1, name))
                g["swap"] = {"name": nm}
                continue
            try:
                sid = int(sw)
            except (TypeError, ValueError):
                raise BuildError("%s, club %d: %r is not a club of the game" % (p["name"], at + 1, sw))
            bad = game_club_problem(info, sid)
            if bad:
                raise BuildError("%s, club %d: the club taking %s's place: %s" % (p["name"], at + 1, name, bad))
            if info["entries"].get(sid):
                raise BuildError("%s, club %d: %s already plays in %s; the club taking %s's place must be one"
                                 " that plays in nothing" % (p["name"], at + 1, info["clubs"][sid][0],
                                                            ", ".join(game_club_where(info, sid)), name))
            if sid in used:
                raise BuildError("%s is used twice (%s)" % (info["clubs"][sid][0], used[sid]))
            used[sid] = "%s, in %s's place" % (p["name"], name)
            g["swap"] = sid


def newlife_tids(leagues, base, pins=None):
    """({NewLife club id: world id}, free ids left in the new-club block) for every NewLife club
    of the recipe's leagues that is built as a new club. Counting up after the ids the builder
    gives its own clubs and after any recipe club_ids, in a fixed order (leagues in recipe order,
    clubs in league order), so the same recipe always gives the same ids (#90 / #88). The
    NewLife id of a club the game already has is not here: that club keeps the game's id.
    pins (the recipe's "newlife_ids", {NewLife id as text: world id}) are the ids clubs had at
    an earlier Build: a club keeps its own when a league before it changes, is removed or is
    updated to a newer NewLife, and a Kit Server map.txt keyed on it keeps working (0.1.8)."""
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    have = {int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little") for o in range(0, len(raw), W.T_REC)}
    taken = set(have)
    rows = []
    for L in leagues:
        n = int(L.get("clubs") or 0)
        gc = set()
        for e in L.get("game_clubs") or []:
            try:
                gc.add(int(e.get("at", -1)))
            except (TypeError, ValueError, AttributeError):
                pass
        ids = [int(x) if str(x or "").strip().isdigit() else None for x in (L.get("club_ids") or [])][:n]
        nl = [int(x) if str(x or "").strip().isdigit() else None
              for x in ((L.get("newlife") or {}).get("clubs") or [])][:n]
        rows.append((n, gc, ids + [None] * (n - len(ids)), nl + [None] * (n - len(nl))))
        taken |= {t for t in ids if t}
    top = max(have) if have else 0
    nxt = top + 1
    present = {x for _n, _gc, _ids, nl in rows for x in nl if x is not None}
    pinned = {}                                 # NewLife id -> its pinned world id, one club per id
    for k, v in sorted((pins or {}).items(), key=lambda kv: str(kv[0])):
        k, v = int(k) if str(k).isdigit() else None, int(v) if str(v).isdigit() else None
        if k in present and v and top < v <= CLUB_ID_MAX and v not in taken and v not in pinned.values():
            pinned[k] = v
    taken |= set(pinned.values())

    def take():
        nonlocal nxt
        while nxt in taken:
            nxt += 1
        if nxt > CLUB_ID_MAX:
            raise BuildError("no team ids left up to %d: the new-club block %d..%d is full"
                             % (CLUB_ID_MAX, top + 1, CLUB_ID_MAX))
        v = nxt
        taken.add(v)
        nxt += 1
        return v

    def is_newlife(nl, k):
        return k < len(nl) and nl[k] is not None and NEWLIFE_TEAMS[0] <= nl[k] <= NEWLIFE_TEAMS[1]

    for n, gc, ids, nl in rows:                 # the builder's own clubs first
        for k in range(n):
            if k in gc or (k < len(ids) and ids[k]) or is_newlife(nl, k):
                continue
            take()
    m = {}
    for n, gc, ids, nl in rows:                 # then the NewLife clubs, in the same order
        for k in range(n):
            if not is_newlife(nl, k):
                continue
            m[nl[k]] = pinned[nl[k]] if nl[k] in pinned else take()
    return m, max(CLUB_ID_MAX - max([nxt - 1] + list(pinned.values())), 0)


def pin_newlife(recipe, base):
    """write the world id every NewLife club of the recipe gets into recipe["newlife_ids"], so
    the next Build gives it the same one (newlife_tids). A pin stays when its club leaves the
    recipe: the club takes it back when it returns. True when the recipe changed."""
    pins = recipe.setdefault("newlife_ids", {})
    m, _free = newlife_tids(recipe.get("leagues") or [], base, pins)
    new = {str(k): v for k, v in m.items() if pins.get(str(k)) != v}
    pins.update(new)
    if not pins:
        recipe.pop("newlife_ids")
    return bool(new)



def club_id_problems(out, base):
    """problems with the club ids the recipe gives its own clubs, as sentences"""
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    have = {int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little") for o in range(0, len(raw), W.T_REC)}
    lo = max(have) + 1
    err, seen = [], {}
    for p in out:
        for k, tid in enumerate(p.get("club_ids") or []):
            if tid is None:
                continue
            who = "%s, club %d" % (p["name"], k + 1)
            if tid in have:
                err.append("%s: id %d is a club of the game" % (who, tid))
            elif not lo <= tid <= CLUB_ID_MAX:
                err.append("%s: id %d -- a new club's id is %d..%d" % (who, tid, lo, CLUB_ID_MAX))
            elif tid in seen:
                err.append("%s: id %d is also %s's" % (who, tid, seen[tid]))
            seen[tid] = who
    return err


def cup_field(field):
    """a league cup of `field` (league places, the strongest first): the biggest of
    LEAGUE_CUP_SIZES there are clubs for, and the clubs past it in a pre-round -- the last 2x
    places, the strongest v the weakest, the weaker at home first; the winner of tie k takes
    the knockout's place size - x + k. Returns (knockout entries, pre-round entries), the
    knockout paired the strongest v the weakest and a pre-round winner as ("pre", k); (None, [])
    when there are fewer than LEAGUE_CUP_SIZES[-1] clubs."""
    size = next((s for s in LEAGUE_CUP_SIZES if s <= len(field)), None)
    if size is None:
        return None, []
    x = min(len(field) - size, LEAGUE_PRE_MAX, size)
    pre = field[size - x:size + x]
    pre = [pre[j] for i in range(x) for j in (2 * x - 1 - i, i)]
    main = field[:size - x] + [("pre", k) for k in range(x)]
    return [main[j] for i in range(size // 2) for j in (i, size - 1 - i)], pre


def cup_opts(pre):
    """a league cup's options: filled with the August play-off, or after its pre-round"""
    o = {"fill": LEAGUE_CUP_FILL if pre else 0, "national": 1, "days": LEAGUE_CUP_DAYS}
    if pre:
        o["pre"] = {"entry": pre, "fill": LEAGUE_PRE_FILL, "days": LEAGUE_PRE_DAYS}
    return o


def league_cup(p, out):
    """the league cup of top division p: the biggest of LEAGUE_CUP_SIZES its division and the
    ones below it (the recipe's) have clubs for, by league position, the strongest v the weakest,
    the clubs past it through a pre-round (cup_field)"""
    field, q = [], p
    while q and len(field) < LEAGUE_CUP_SIZES[0]:
        field += [(q["rid"], pos) for pos in range(1, q["clubs"] + 1)]
        q = next((b for b in out if b["above"] == q["rid"]), None)
    field, pre = cup_field(field)
    return {"name": p["league_cup"]["name"], "code": "FL_%03d_LCUP" % p["rid"], "kind": "league",
            "logo": p["league_cup"].get("logo"),
            "country": p["country"], "region": p["region"], "groups": 0, "entry": field,
            "opts": cup_opts(pre)}


def game_tops(base):
    """[(reg id, name, has a super cup)] of the game's top divisions, for game_cups"""
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    regrow = {u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG:(i + 1) * M.REG]
              for i in range(len(regs) // M.REG)}
    region_of_cid = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
                     for i in range(len(comp) // M.COMP)}
    return [(r, n, bool(home_supercup(regrow, region_of_cid, region_of_cid[c])))
            for r, c, n, _t in game_leagues(base) if M.get_tier(regrow[r]) == 1]


def access_reg(rid, regrow, region_of_cid):
    """the regulation the access list names for top division rid: itself, or for a league the
    game splits (Scotland, Belgium, Denmark) the phase of the same region the list names"""
    shipped = {e[0] for e in fl26world.SHIPPED_ACCESS if e[0] < 1024}
    if rid in shipped:
        return rid
    reg = region_of_cid.get(regrow[rid][M.R_CID])
    return next((r for r in sorted(shipped) if r in regrow
                 and region_of_cid.get(regrow[r][M.R_CID]) == reg), rid)


def game_europe(recipe, regrow, region_of_cid, base):
    """the recipe's game_europe: (regulation, position, competition, 0) places for leagues of the
    game, the regulations whose shipped places they replace, their names, and the places in the
    League Builder's continental cups (competitions 6..9, 13..15), which go to ccup_plan"""
    ge = recipe.get("game_europe") or {}
    if not ge:
        return [], [], {}, []
    tops = {r: n for r, _c, n, _t in game_leagues(base)}
    ccups = {c: n for c, n, _code, _conf, _fill in fl26world.CCUPS}
    places, replace, names, cc = [], [], {}, []
    for key, europe in sorted(ge.items(), key=lambda kv: str(kv[0])):
        try:
            rid = int(key)
        except (TypeError, ValueError):
            raise BuildError("European places: %r is not a league of the game" % (key,))
        if rid not in tops or M.get_tier(regrow[rid]) != 1:
            raise BuildError("European places: regulation %d is not a top division of the game" % rid)
        clubs = entries_of(base, regrow[rid][M.R_CID])
        cup = home_cup(regrow, region_of_cid, region_of_cid.get(regrow[rid][M.R_CID]))
        bad = europe_problems(clubs, europe or [], cup is not None)
        bad += ["competition %d is not one a league's place can lead to" % int(e[1])
                for e in europe or [] if str(e[1]).isdigit()
                and int(e[1]) not in fl26world.UEFA_LINE and int(e[1]) not in ccups]
        if bad:
            raise BuildError("European places of %s: %s" % (tops[rid], "; ".join(bad)))
        # a place in a continental cup of the League Builder's (AFC Champions League Two, Copa
        # Sudamericana ...) joins that cup with the new leagues' places; the shipped places of
        # the league stay as they are (B2Y, #86: Saudi Pro League places in the ACL Two)
        cc += [(rid, int(pos), int(comp), 0) for pos, comp in europe or [] if int(comp) in ccups]
        europe = [e for e in europe or [] if int(e[1]) not in ccups]
        if not europe:
            continue
        r = access_reg(rid, regrow, region_of_cid)
        replace.append(r)
        names[str(r)] = tops[rid]
        places += [(cup, 0, int(comp), r) if int(pos) == CUP_WINNER else (r, int(pos), int(comp), 0)
                   for pos, comp in europe]
    return places, replace, names, cc


def uefa_seed(recipe, out, regrow, region_of_cid):
    """the recipe's uefa_seed as (regulation the access list names, position, competition)"""
    rid = {p["name"]: p["rid"] for p in out}
    seed = []
    for e in recipe.get("uefa_seed") or []:
        try:
            lg, pos, comp = str(e[0]), int(e[1]), int(e[2])
        except (TypeError, ValueError, IndexError):
            continue
        if lg.startswith("g") and lg[1:].isdigit() and int(lg[1:]) in regrow:
            seed.append([access_reg(int(lg[1:]), regrow, region_of_cid), pos, comp])
        elif lg in rid:
            seed.append([rid[lg], pos, comp])
    return seed


def all_places(pl):
    """the world's European places, the new leagues' and game_europe's, as uefa_places takes them:
    in uefa_seed's order where the plan has one (a place's league: its regulation, or for a cup
    winner's place the league in alt), the rest after it as they come"""
    places = own_places(pl) + [tuple(e) for e in pl.get("game_europe") or []]
    order = {tuple(s): k for k, s in enumerate(pl.get("uefa_seed") or [])}
    if not order:
        return places
    key = lambda e: order.get((e[0] if e[1] else e[3], e[1], e[2]), len(order))
    return sorted(places, key=key)


def game_europe_tops(base):
    """[(reg id, name, clubs, [[position, competition], ...] shipped)] of the game's top
    divisions, for the European places dialog"""
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    regrow = {u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG:(i + 1) * M.REG]
              for i in range(len(regs) // M.REG)}
    region_of_cid = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
                     for i in range(len(comp) // M.COMP)}
    out = []
    for r, c, n, _t in game_leagues(base):
        if M.get_tier(regrow[r]) != 1:
            continue
        a = access_reg(r, regrow, region_of_cid)
        out.append((r, n, entries_of(base, c),
                    sorted([e[1], e[2]] for e in fl26world.SHIPPED_ACCESS if e[0] == a)))
    return out


ENGLISH = 4                # the regulation's English name (the first is Korean on national-team rows)


def game_competitions(base):
    """[(competition id, name, [regulation ids])] of the game's competitions that are not
    leagues (cups, super cups, continental and national-team ones), by id"""
    regs = M.load(base, "CompetitionRegulation.bin")
    leagues = {c for _r, c, _n, _t in game_leagues(base)}
    out = {}
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        c = g[M.R_CID]
        if c in leagues or g[M.R_TYPE] in (4, fl26world.SPLIT_TOTAL):
            continue
        name = text(g[M.R_NAME + ENGLISH * M.NAME_SLOT:M.R_NAME + (ENGLISH + 1) * M.NAME_SLOT])             or text(g[M.R_NAME:M.R_NAME + M.NAME_SLOT])
        if name:
            out.setdefault(c, [name, []])[1].append(u16(g, M.R_ID))
    return [(c, n, r) for c, (n, r) in sorted(out.items())]


def competition_problems(edits, base):
    """what is wrong with the recipe's edits.competitions"""
    want = edits.get("competitions") or {}
    if not want:
        return []
    have = {c: n for c, n, _r in game_competitions(base)}
    out = []
    for k, v in want.items():
        if not str(k).isdigit() or int(k) not in have:
            out.append("%s is not a competition of the game (a league is renamed with the leagues)" % (k,))
        elif not (v.get("name") or "").strip() and not v.get("logo"):
            out.append("%s: no new name and no logo" % have[int(k)])
    return out


def rename_competitions(pl, db, log=print):
    """edits.competitions into the world's regulation table: every regulation of a renamed
    competition, once the cups that copy regulations (europe, continental) are built"""
    want = {int(k): v["name"].strip() for k, v in ((pl.get("edits") or {}).get("competitions") or {}).items()
            if (v.get("name") or "").strip()}
    if not want:
        return
    path = os.path.join(db, "CompetitionRegulation.bin")
    regs = M.load(db, "CompetitionRegulation.bin")
    n = 0
    for i in range(len(regs) // M.REG):
        o = i * M.REG
        name = want.get(regs[o + M.R_CID])
        if name:
            rename_reg(regs, o, name)
            n += 1
    open(path, "wb").write(pesdb.wesys_pack(bytes(regs)))
    log("  renamed %d of the game's competitions (%d regulations)" % (len(want), n))


def game_cups(recipe, regrow, region_of_cid, base, out):
    """the recipe's game_cups: league cups (and super cups where the region has none) for top
    divisions of the game, the same fl26swiss cups league_cup() gives a new country"""
    res, seen = [], set()
    tops = {r for r, _c, _n, _t in game_leagues(base)} if recipe.get("game_cups") else set()
    for c in recipe.get("game_cups") or []:
        try:
            rid = int(c.get("league"))
        except (TypeError, ValueError):
            raise BuildError("game cups: %r is not a league of the game" % (c.get("league"),))
        g = regrow.get(rid)
        if g is None or rid not in tops or M.get_tier(g) != 1:
            raise BuildError("game cups: regulation %d is not a top division of the game" % rid)
        if rid in seen:
            raise BuildError("game cups: league %d is listed twice" % rid)
        seen.add(rid)
        league = text(g[M.R_NAME:M.R_NAME + M.NAME_SLOT])
        region = region_of_cid[g[M.R_CID]]
        # the league's own confederation: with none, the cup kept the CONMEBOL of the row it is
        # copied from (MiMo 03.10.), and an English league cup sat with South America's cups
        conf = comp_conf(base, g[M.R_CID])
        if c.get("league_cup", True):
            field, q = [], rid
            while q and len(field) < LEAGUE_CUP_SIZES[0]:
                mine = next((p for p in out if p["rid"] == q), None)
                n = mine["clubs"] if mine else entries_of(base, regrow[q][M.R_CID])
                field += [(q, pos) for pos in range(1, n + 1)]
                below = u16(regrow[q], M.R_BELOW) if q in regrow else 0
                q = (below if below in regrow else 0) or next((p["rid"] for p in out if p["above"] == q), None)
            n = len(field)
            field, pre = cup_field(field)
            if field is None:
                raise BuildError("game cups: %s has %d clubs, a league cup needs %d"
                                 % (league, n, LEAGUE_CUP_SIZES[-1]))
            res.append({"name": (c.get("name") or "").strip() or league + " League Cup",
                        "code": "FL_G%03d_LCUP" % rid, "kind": "league", "logo": c.get("logo") or None,
                        "country": None, "conf": conf, "region": region, "groups": 0, "entry": field,
                        "opts": cup_opts(pre)})
        if c.get("super_cup"):
            if home_supercup(regrow, region_of_cid, region):
                raise BuildError("game cups: %s already has a super cup in the game" % league)
            cup = home_cup(regrow, region_of_cid, region)
            res.append({"name": (c.get("super_name") or "").strip() or league + " Super Cup",
                        "code": "FL_G%03d_SCUP" % rid, "kind": "super", "logo": c.get("super_logo") or None,
                        "country": None, "conf": conf, "region": region, "groups": 0,
                        "entry": [(rid, 1), (cup, 0)] if cup else [(rid, 1), (rid, 2)],
                        "opts": {"fill": PRESEASON_FILL, "national": 1, "days": CAF_SUPER_DAYS}})
    return res


def rounds_of(clubs):
    """a single round robin's rounds"""
    return clubs if clubs % 2 else clubs - 1


def league_days(rid, rounds):
    """the days of the year a league of ours on regulation `rid` plays its `rounds` on, as
    datecave and fl26swiss's league_dates make them; [] when that is not the big-league calendar
    (no shift for the id, or more rounds than it has: the Championship's is borrowed)"""
    s, have = DATE_SHIFT.get(rid), len(BIG_LEAGUE_DAYS)
    if s is None or not 2 <= rounds <= have:
        return []
    days = [(d + s) % 365 for d in BIG_LEAGUE_DAYS]
    return [days[(i * (have - 1) * 2 + (rounds - 1)) // (2 * (rounds - 1))] for i in range(rounds)]


def season_ord(day):
    """a day of the year as a place in the season, which turns in July (SEASON_TURN)"""
    return day - SEASON_TURN if day >= SEASON_TURN else day + 365 - SEASON_TURN


def season_day(o):
    d = o + SEASON_TURN
    return d - 365 if d > 365 else d


def split_days(n1, n2):
    """the days fl26swiss gives a split's rounds (split_dates, up to 38 rounds): the regular
    phase's n1 and the group's n2"""
    t = n1 + n2
    line = SPLIT_LINE[min(SPLIT_SKIP, len(SPLIT_LINE) - t):]
    last = len(line) - 1
    at = lambda i: line[(i * last * 2 + (t - 1)) // (2 * (t - 1))]
    return [at(i) for i in range(n1)], [at(i) for i in range(n1, t)]


def playoff_days(after, busy, count=7):
    """`count` days after day `after`, in season order: none the day before, of or after a busy
    day, three days apart, the first three days after `after` (the fill window)"""
    b = {season_ord(d) for d in busy}
    out, o = [], season_ord(after) + 3
    while len(out) < count:
        if o > 364:
            raise BuildError("no free days for a playoff after day %d" % after)
        if not any(abs(o - x) <= 1 for x in b) and (not out or o - out[-1] >= 3):
            out.append(o)
        o += 1
    return [season_day(o) for o in out]


def playoff_cups(p):
    """the Apertura and Clausura playoffs of league p: the first `playoff` clubs of each phase,
    the strongest v the weakest, filled the day after the phase's last round and played on
    free days after it. The entries name the league until build() has the phase ids (mksplit)."""
    k = p["apertura"]["playoff"]
    if not k:
        return []
    ap, cl = split_days(rounds_of(p["clubs"]), rounds_of(p["clubs"]))
    busy = ap + cl + (CCUP_DAYS if p.get("europe") else []) + (LEAGUE_CUP_DAYS if p.get("league_cup") else [])
    out = []
    for part, (days_of, tag) in enumerate(((ap, "Apertura"), (cl, "Clausura"))):
        days = playoff_days(days_of[-1], busy)
        busy = busy + days
        order = [pos for i in range(k // 2) for pos in (i + 1, k - i)]
        out.append({"name": "%s %s Playoffs" % (p["name"], tag), "code": "FL_%03d_%sPO" % (p["rid"], tag[0]),
                    "kind": "playoff", "logo": p["apertura"].get("logo"),
                    "country": p["country"], "region": p["region"], "groups": 0,
                    "league": p["rid"], "phase": part, "entry": [(p["rid"], pos) for pos in order],
                    "opts": {"fill": season_day(season_ord(days_of[-1]) + 1), "national": 1, "days": days}})
    return out


def preseason_cup(c, k, by_name):
    """a pre-season cup of the recipe's preseason_cups: its invited clubs, as references until
    build() knows the new clubs' ids, and its host -- the league of its first new club"""
    name = str(c.get("name") or "").strip() or "Pre-season Cup %d" % (k + 1)
    refs, host = [], None
    for x in c.get("clubs") or []:
        s = str(x).strip()
        if s.isdigit():
            refs.append(int(s))
            continue
        lg, _sl, i = s.rpartition("/")
        p = by_name.get(lg.strip().lower())
        if p is None or not i.isdigit() or int(i) >= p["clubs"]:
            raise BuildError("%s: no club %r (a league of the recipe and its club, from 0, or a "
                             "club id of the game)" % (name, s))
        refs.append((p["rid"], int(i)))
        host = host or p
    if len(refs) not in (4, 8):
        raise BuildError("%s: %d clubs -- a pre-season cup has 4 or 8" % (name, len(refs)))
    if len(set(refs)) != len(refs):
        raise BuildError("%s: a club is invited twice" % name)
    if host is None:
        raise BuildError("%s: at least one club from a league of the recipe (the host)" % name)
    return {"name": name, "code": "FL_PRE%d" % (k + 1), "kind": "preseason", "logo": c.get("logo") or None,
            "country": host["country"], "region": host["region"], "groups": 0,
            "entry": [(host["rid"], pos) for pos in range(1, len(refs) + 1)], "refs": refs,
            "opts": {"fill": PRESEASON_FILL, "national": 1, "days": PRESEASON_DAYS}}


EUROPE_FIRST = (("ucl", "Champions League"), ("uel", "Europa League"), ("uecl", "Conference League"))
FIRST_MAX = 36


def europe_first(recipe, by_name):
    """the recipe's europe_first as [[club, ...] for the Champions, Europa and Conference League],
    a club a team id of the game or (league id, place) until build() knows the new clubs' ids"""
    got = recipe.get("europe_first") or {}
    out, seen = [], {}
    for key, title in EUROPE_FIRST:
        refs = []
        for x in got.get(key) or []:
            s = str(x).strip()
            if s.isdigit():
                ref = int(s)
            else:
                lg, _sl, i = s.rpartition("/")
                p = by_name.get(lg.strip().lower())
                if p is None or not i.strip().isdigit() or int(i) >= p["clubs"]:
                    raise BuildError("First-season European clubs, %s: no club %r (a league of the recipe "
                                     "and its club, from 0, or a club id of the game)" % (title, s))
                ref = (p["rid"], int(i))
            if ref in seen:
                raise BuildError("First-season European clubs: %r is in the %s and the %s" % (s, seen[ref], title))
            seen[ref] = title
            refs.append(ref)
        if len(refs) > FIRST_MAX:
            raise BuildError("First-season European clubs, %s: %d clubs -- a league phase has %d"
                             % (title, len(refs), FIRST_MAX))
        out.append(refs)
    return out


def first_lines(pl):
    """world file lines `first <0|1|2> <team id> ...` from the plan's europe_first, the new clubs'
    ids known now (build() handed them out)"""
    teams = {p["rid"]: p.get("teams") or [] for p in pl["leagues"]}
    out = []
    for c, refs in enumerate(pl.get("europe_first") or []):
        ids = []
        for ref in refs:
            if isinstance(ref, (list, tuple)):
                rid, k = ref
                if k < len(teams.get(rid, [])):
                    ids.append(teams[rid][k])
            else:
                ids.append(int(ref))
        if ids:
            out.append("first %d %s" % (c, " ".join(str(t) for t in ids)))
    return out


def caf_super_cup(recipe):
    """the CAF Super Cup: a knockout of two whose entries are the winners of the CAF Champions
    League and the Confederation Cup -- ("ko", number) until continental() has their ids"""
    return {"number": 0, "name": "CAF Super Cup", "code": "FL_CAFSC", "conf": 5, "groups": 0,
            "kind": "super", "logo": recipe.get("caf_super_cup_logo") or None,
            "entry": [("ko", CAF_CL), ("ko", CAF_CC)],
            "opts": {"fill": PRESEASON_FILL, "national": 1, "days": CAF_SUPER_DAYS}}


def cup_rounds(n):
    """the round ids a knockout of n clubs plays: the first is 0x2e, the ones after it count up
    to the quarter-final, which is 0x33 (then 0x34, 0x35) -- a field of eight or fewer starts on
    0x2e and goes straight to 0x34 (Copa America, Asian Cup)"""
    total = max(1, (n - 1).bit_length())
    if total <= 3:
        return {0x2e} | set(range(0x36 - total + 1, 0x36))
    return set(range(0x2e, 0x2e + total - 3)) | {0x33, 0x34, 0x35}


def cup_takes_both(cup, n):
    """whether a shipped domestic cup can take a field of n clubs: every round dated, n <= 44"""
    dated = CUP_DATED.get(cup)
    # only a size the bracket screen draws: 32 or fewer in BRACKET_SIZES, above it 44 alone (#95)
    return bool(dated) and n <= NATIONAL_CUP_MAX and cup_rounds(n) <= dated \
        and (n == NATIONAL_CUP_MAX or n in BRACKET_SIZES)


def national_cup(p, below):
    """pick the shipped cup to copy for league p's national cup (p["own_cup"]), with the league
    below it (or None). The game fills the cup with both divisions, and so does this: a shipped
    cup of exactly that many clubs when there is one (NATIONAL_CUPS_TWO, NATIONAL_CUPS), else the
    English one, whose calendar dates every round of any field up to NATIONAL_CUP_MAX clubs.
    keep_top (fl26chain keeps the second division out) is left for a field past that."""
    c = p["own_cup"]
    n = p["clubs"] + (below["clubs"] if below else 0)
    exact = NATIONAL_CUPS_TWO if below else NATIONAL_CUPS
    if n in exact:
        c["like"], c["bracket"] = exact[n]
        c["clubs"], c["keep_top"] = n, False
    elif n <= NATIONAL_CUP_MAX:
        c["like"], c["bracket"] = NATIONAL_CUP_ANY
        c["clubs"], c["keep_top"] = n, False
    elif p["clubs"] in NATIONAL_CUPS:
        c["like"], c["bracket"] = NATIONAL_CUPS[p["clubs"]]
        c["clubs"], c["keep_top"] = p["clubs"], True
    else:
        c["like"], c["bracket"] = NATIONAL_CUP_ANY
        c["clubs"], c["keep_top"] = p["clubs"], True
    if c["clubs"] <= 32 and c["clubs"] not in BRACKET_SIZES:
        # the bracket screen has a bye layout for these fields only (0x140b33340: none for
        # 17, 19, 21-23, 25-27, 29); a cup of 22 crashed it at 0x140b34501 (#74). The cup takes
        # the largest field it can draw: the top division and the first clubs of the one below
        c["clubs"] = max(k for k in BRACKET_SIZES if k <= c["clubs"])
    elif 32 < c["clubs"] < NATIONAL_CUP_MAX and c["clubs"] not in exact:
        # the same for a field of 33..43 that no shipped cup has exactly: no bye layout for it
        # either, so the cup takes the 32 the screen draws (#95) and cupn names it (#74)
        c["clubs"] = 32
    c["bracket"] = c["clubs"]           # the field, not the prototype's bracket (#74)
    c["below"] = below["rid"] if below else None


def ccup_short(own, clubs, notes):
    """{cup number: [(league, position)]} of the world's own places, with a cup of a continent the
    game has no leagues to fill from (CAF) brought up to the four clubs a cup needs when it has
    fewer: first the best places of that confederation's next cup of the same kind (2 CAF
    Champions League and 2 Confederation Cup places, Alikhaled_727 2026-09-29: neither cup was
    built, now the Champions League takes all four), then the next positions of its own leagues
    that no place of any competition claims, a league at a time (`clubs`: {league: its clubs})"""
    places = {c: sorted((ccup_entry(r, pos, a) for r, pos, comp, a in own if comp == c), key=entry_key)
              for c, _n, _code, _conf, _fill in fl26world.CCUPS}
    claimed = {}
    for r, pos, _comp, _a in own:
        if pos != CUP_WINNER:
            claimed.setdefault(r, set()).add(pos)
    for i, (c, name, _code, conf, fill) in enumerate(fl26world.CCUPS):
        if fill or not 0 < len(places[c]) < 4:
            continue
        for c2, name2, _code2, conf2, fill2 in fl26world.CCUPS[i + 1:]:
            take = places[c2][:4 - len(places[c])] if conf2 == conf and not fill2 else []
            if take:
                places[c] = sorted(places[c] + take, key=entry_key)
                places[c2] = places[c2][len(take):]
                notes.append("%s: %d place(s) of the %s moved up to it -- a cup needs 4 clubs"
                             % (name, len(take), name2))
            if len(places[c]) >= 4:
                break
        if len(places[c]) >= 4:
            continue
        leagues = []
        for e in places[c]:
            if entry_league(e) not in leagues:
                leagues.append(entry_league(e))
        nxt, pad = {r: max(claimed.setdefault(r, {0})) for r in leagues}, []
        while len(places[c]) + len(pad) < 4:
            before = len(pad)
            for r in leagues:
                if len(places[c]) + len(pad) >= 4:
                    break
                pos = nxt[r] + 1
                while pos in claimed[r]:
                    pos += 1
                if pos <= clubs.get(r, 0):
                    nxt[r] = pos
                    pad.append((r, pos))
            if len(pad) == before:
                break
        if len(places[c]) + len(pad) >= 4:
            for r, pos in pad:
                claimed[r].add(pos)
            places[c] += pad
            notes.append("%s: filled up to 4 clubs with the next places of the same league(s) (%s)"
                         % (name, ", ".join(str(pos) for _r, pos in pad)))
    return places


def ccup_entry(r, pos, alt):
    """a place in one of fl26world.CCUPS as ccup_plan's entry: (league, position), or for a cup
    winner's place ("cup", league) -- the national cup's regulation is known only once Build has
    made it, so continental() puts it in (cup_winners), with the league as the place to fall back
    on: the next club of that league when the cup has no winner yet (a new career) or its winner
    already plays (fl26swiss ccup alt=)"""
    return ("cup", alt or r) if pos == CUP_WINNER else (r, pos)


def entry_league(e):
    return e[1] if e[0] == "cup" else e[0]


def entry_key(e):
    """a league's places best first, its cup winner's after them (the League dialog's order)"""
    return 1000 if e[0] == "cup" else e[1]


def apart(field):
    """a knockout's pairs (first v second, third v fourth ...) with no two clubs of one league
    in a tie where a swap of the second clubs of two ties can avoid it (a cup winner and the
    champion of its league met in the first round)"""
    field = list(field)
    ties = len(field) // 2
    for t in range(ties):
        if entry_league(field[2 * t]) != entry_league(field[2 * t + 1]):
            continue
        for u in sorted(range(ties), key=lambda u: abs(u - t)):
            a, b = field[2 * t], field[2 * u + 1]
            if u != t and entry_league(a) != entry_league(b) and entry_league(field[2 * u]) != entry_league(field[2 * t + 1]):
                field[2 * t + 1], field[2 * u + 1] = field[2 * u + 1], field[2 * t + 1]
                break
    return field


def ccup_plan(own, clubs=None):
    """the continental cups the new leagues' places lead to (competitions 6..9, 13..15: fl26world.CCUPS),
    each only when some place names it. The field is the places of the world's own leagues and,
    where the cup has them, shipped leagues' places after those: the biggest of 32/16/8/4 clubs
    that there are clubs for, the world's own always in. Pots in the order a league's places
    come -- every league's best place in pot 1, then the next ... -- so two clubs of a league do
    not start in the same pot. 8 or more clubs play groups of four, then a knockout of the first
    two; 4 play a knockout. A cup short of four is helped first (ccup_short). Returns
    ([{number, name, code, conf, groups, entry}], notes)."""
    cups, notes = [], []
    places = ccup_short(own, clubs or {}, notes)
    for c, name, code, conf, fill in fl26world.CCUPS:
        mine = places[c]
        if not mine:
            continue
        size = next((s for s in CCUP_SIZES if s <= len(mine) + len(fill)
                     and (s <= CCUP_KNOCKOUT_MAX or c not in fl26world.CCUP_KNOCKOUT)), 0)
        if not size:
            notes.append("%s: %d place(s), and a cup needs 4 clubs -- not built" % (name, len(mine)))
            continue
        if len(mine) > size:
            notes.append("%s: %d places, the cup takes %d -- the last %d get none"
                         % (name, len(mine), size, len(mine) - size))
            mine = mine[:size]
        field = mine + [e for e in fill if e not in mine][:size - len(mine)]
        seen, ranked = {}, []
        for i, e in enumerate(field):
            r = entry_league(e)
            seen[r] = seen.get(r, -1) + 1
            ranked.append((seen[r], i, tuple(e)))
        field = [e for _k, _i, e in sorted(ranked, key=lambda x: (x[0], x[1]))]
        knockout = size < 8 or c in fl26world.CCUP_KNOCKOUT
        if knockout:            # a knockout pairs entries in order: the strongest v the weakest
            field = apart([field[j] for i in range(size // 2) for j in (i, size - 1 - i)])
        cups.append({"number": c, "name": name, "code": code, "conf": conf,
                     "groups": 0 if knockout else size // 4, "entry": field})
    return cups, notes


CUP_WINNER = 0           # a European place's position 0: the country's cup winner


def europe_problems(clubs, europe, cup=True):
    """what is wrong with a league's European places ([[position, competition], ...]): each a
    position of the league's own, 1..clubs, none twice, and a competition fl26swiss knows.
    Position 0 is the cup winner (CUP_WINNER): only for a league whose country has a cup (cup),
    -- fl26swiss gives it to the cup winner, or, when the winner already has a place through the
    league (or a new career has no winner yet), to the league's next club. Since 0.2.0 that holds
    for the League Builder's continental cups too (GitHub #95: the cup winner to the Copa
    Sudamericana, the Confederation Cup, the AFC Champions League Two)"""
    out, seen = [], set()
    comps = {c for c, _n in fl26world.COMPETITIONS}
    for e in europe:
        try:
            pos, comp = int(e[0]), int(e[1])
        except (TypeError, ValueError, IndexError):
            out.append("%r is not a position and a competition" % (e,))
            continue
        if pos == CUP_WINNER:
            if not cup:
                out.append("a cup winner's place, but the country has no cup")
        elif not 1 <= pos <= clubs:
            out.append("position %d -- the league has %d clubs" % (pos, clubs))
        if pos in seen:
            out.append("position %d is listed twice" % pos)
        seen.add(pos)
        if comp not in comps:
            out.append("competition %d is not one of %s" % (comp, ", ".join(str(c) for c in sorted(comps))))
    return out


def own_places(pl):
    """(regulation, position, competition, alt) for the new leagues' European places; a cup
    winner's place is (the national cup's regulation, 0, competition, the league) -- the
    regulation is known once national_cups() has made the cup, 0 before"""
    return [((p.get("own_cup") or {}).get("reg", 0), 0, comp, p["rid"]) if pos == CUP_WINNER
            else (p["rid"], pos, comp, 0) for p in pl["leagues"] for pos, comp in p.get("europe") or []]


def order_by_parents(leagues):
    """recipe indices, every league after the league named above it"""
    names = {L.get("name", "").strip().lower(): i for i, L in enumerate(leagues)}
    done, order = set(), []

    def visit(i, path):
        if i in done:
            return
        if i in path:
            raise BuildError("the leagues above each other go round in a circle: %s"
                             % " -> ".join(leagues[j]["name"] for j in path + [i]))
        up = leagues[i].get("above")
        if isinstance(up, str) and up.strip().lower() in names:
            visit(names[up.strip().lower()], path + [i])
        done.add(i)
        order.append(i)
    for i in range(len(leagues)):
        visit(i, [])
    return order


def place_name(pos, comp):
    return "cup winner %s" % comp if pos == CUP_WINNER else "%d. %s" % (pos, comp)


def nth(n):
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def fill_share(cup):
    """{shipped league: [positions]} of a continental cup's entries the game's leagues fill
    (fl26world.CCUPS: after the world's own places, one of each league in turn)"""
    out = {}
    for r, pos in cup["entry"]:
        if r in fl26world.FILL_NAMES and pos:
            out.setdefault(r, []).append(pos)
    return out


def samerica_lines(own, names, cups):
    """Check the plan's list of every South American league's places (GitHub #71): the game's
    leagues -- their Libertadores places (fl26world.SAM_GAME) and the share of the Copa
    Sudamericana they fill -- then the world's own leagues with a Libertadores or Sudamericana
    place. own: (league, position, competition, alt) as own_places gives them, names: {league:
    name}, cups: ccup_plan's. A Sudamericana entry takes the club at that position or, when it
    already plays a continental cup, the next one of its league (fl26swiss ccup_taken)."""
    sud = next((c for c in cups if c["number"] == 9), None)
    share = fill_share(sud) if sud else {}
    lines = ["  South American places (Copa Libertadores, its qualifying round, Copa Sudamericana):"]
    for r, lib, libq in fl26world.SAM_GAME:
        s = sorted(share.get(r) or [])
        lines.append("    %s, a league of the game: Libertadores %s; qualifying %s; %s" % (
            fl26world.FILL_NAMES[r], lib, libq,
            "Copa Sudamericana %d clubs from %s down" % (len(s), nth(s[0])) if s
            else "Copa Sudamericana: none" if sud else "no Copa Sudamericana in this world"))
    cn = {3: "Libertadores", 4: "qualifying", 9: "Copa Sudamericana"}
    mine = {}
    for r, pos, comp, alt in own:
        if comp in cn:
            league = alt if pos == CUP_WINNER and alt else r
            mine.setdefault(league, []).append((comp, pos))
    for league, places in mine.items():
        lines.append("    %s: %s" % (names.get(league, league), "; ".join(
            "%s %s" % (cn[c], ", ".join("cup winner" if p == CUP_WINNER else nth(p)
                                        for cc, p in sorted(places, key=lambda e: e[1]) if cc == c))
            for c in (3, 4, 9) if any(cc == c for cc, _p in places))))
    if any(c == 4 for v in mine.values() for c, _p in v):
        lines.append("    the world's qualifying places take those of the game's leagues: of the league with the "
                     "most clubs in the round, its lowest place first; two stay the game's")
    if sud:
        lines.append("    a Sudamericana club that already plays the Libertadores or its qualifying gives way "
                     "to the next one of its league")
    return lines


LONGEST_NAME = 38       # characters: the longest name of a shipped regulation (its Russian, Greek, Dutch)


def describe(pl):
    e = pl.get("edits") or {}
    lines = ["world %s: %d new leagues, changes to %d of the game's leagues and %d of its clubs"
             % (pl["world"], len(pl["leagues"]), len(e.get("leagues") or {}), len(e.get("clubs") or {}))]
    if pl.get("free_ids") is not None:
        lines.append("  team ids: %d free in the new-club block (%d..%d)"
                     % (pl["free_ids"], CLUB_ID_MAX - pl["free_ids"] + 1, CLUB_ID_MAX))
    for a, b in e.get("swaps") or []:
        lines.append("  clubs %s and %s swap leagues" % (a, b))
    for cid, v in sorted((e.get("competitions") or {}).items(), key=lambda kv: int(kv[0])):
        lines.append("  competition %s: %s%s" % (cid, v.get("name") or "(its own name)",
                                                 ", own logo" if v.get("logo") else ""))
    lines.append("  Conference League: %s" % ("yes (competition %d, regulations %d/%d)"
                                              % (UECL_CID, mkuecl.REG, mkuecl.KO) if pl.get("uecl") else "no"))
    squads = pl.get("players") or {}
    if squads:
        lines.append("  player changes in %d clubs" % len(squads))
    cnames = dict(fl26world.COMPETITIONS)
    for r in pl.get("game_replace") or []:
        mine = sorted((e[1], e[2]) for e in pl.get("game_europe") or [] if e[0] == r or (e[1] == CUP_WINNER and e[3] == r))
        lines.append("  European places of %s (a league of the game): %s" % (
            (pl.get("game_names") or {}).get(str(r), r), ", ".join(place_name(pos, cnames.get(c, c)) for pos, c in mine) or "none"))
    for p in pl.get("others") or []:
        lines.append("  %-26s no league: %d club(s) in the game's %s teams"
                     % (p["name"], p["clubs"], OTHERS_NAMES[p["others"]]))
    for p in pl["leagues"]:
        shape = "%d clubs x%d" % (p["clubs"], p["legs"])
        if p.get("apertura"):
            shape = "Apertura + Clausura, %d clubs x1 each" % p["clubs"]
        elif p.get("split"):
            s = p["split"]
            shape = "%d clubs x%d, then %s x%d" % (p["clubs"], s["legs"], " / ".join(map(str, s["groups"])),
                                                    s["group_legs"])
        lines.append("  %-26s reg %3d  comp %3d  region %2d  slot %3s  division %d%s  %s%s"
                     % (p["name"], p["rid"], p["cid"], p["region"],
                        "-" if p["slot"] == fl26world.NO_SLOT else p["slot"], p["tier"],
                        "  below %d (%d up/down)" % (p["above"], p["exchange"]) if p["above"] else "",
                        shape, "  EXHIBITION ONLY (not in Master League)" if p.get("exhibition") else ""))
        if p.get("calendar"):
            lines.append("      plays February to December, promotion and relegation at New Year")
        elif p.get("follows_calendar"):
            lines.append("      plays February to December with the league above it (the game's season for "
                         "that country), promotion and relegation at New Year")
        if p.get("europe"):
            names = dict(fl26world.COMPETITIONS)
            lines.append("      European places: %s" % ", ".join(
                place_name(pos, names.get(comp, comp)) for pos, comp in sorted(p["europe"])))
    if pl.get("game_seasons"):
        lines.append("  EXPERIMENTAL: the game's leagues of %s play August to May"
                     % ", ".join(pl["game_seasons"]))
    if pl["leagues"] and not own_places(pl):
        lines.append("  no European places: the new leagues send nobody to Europe")
    if not pl.get("uecl") and any(e[2] in (2, 12) for e in own_places(pl)):
        lines.append("  NOTE: Conference League places, but the world gets no Conference League")
    for p in pl["leagues"]:
        if len(p["name"]) > LONGEST_NAME:
            # "Paraguay First Division Primera División" (40) was a blank row in Kick Off's league
            # list, "Paraguay First Division" showed (#101); measured 06.10.: 38 characters show
            # (accented letters count once), 39 are blank
            lines.append("  NOTE: %s is %d characters; Kick Off shows at most %d, a longer name is blank there"
                         % (p["name"], len(p["name"]), LONGEST_NAME))
    unlisted = [p["name"] for p in pl["leagues"] if p["slot"] == fl26world.NO_SLOT and not p.get("exhibition")]
    if unlisted:
        # the Select Team list has room for 36 new leagues; the ids past it play but have no place (#39)
        lines.append("  NOTE: no place in Select Team for %s: they play, but no career can start in them"
                     % ", ".join(unlisted))
    for p in pl["leagues"]:
        if p["slot"] in fl26world.POOL_SLOTS and not p.get("exhibition"):
            # the group the game shows on that slot is gone from Select Team (#73)
            lines.append("  NOTE: %s takes the place of the game's \"%s\" group in Select Team"
                         % (p["name"], fl26world.POOL_SLOTS[p["slot"]]))
    names = dict(fl26world.COMPETITIONS)
    rounds = qual_rounds(pl)
    if any(s for _c, s in rounds):
        lines.append("  August qualifying: %s" % fl26world.rounds_text(rounds))
    for c, (n, room) in sorted(fl26world.uefa_places(all_places(pl),
                                                     pl.get("game_replace") or [], bool(pl.get("uecl")))[1].items()):
        lines.append("  NOTE: %s has %d places listed for %d clubs; the last %d get none"
                     % (names[c], n, room, n - room))
    libq = sum(1 for e in own_places(pl) if e[2] == 4)
    if libq > LIBQ_ROOM:
        # fl26swiss gives the new leagues all but two of the round's eight places (GitHub #66)
        lines.append("  NOTE: Libertadores qualifying has %d places listed, the round takes %d of them; "
                     "the leagues listed last get none" % (libq, LIBQ_ROOM))
    for p in pl["leagues"]:
        if p.get("cup"):
            lines.append("  %s: the country's cup (regulation %d) %s" % (
                p["name"], p["cup"], "takes both divisions, %d clubs" % p["cup_all"] if p.get("cup_all")
                else "keeps the top division's clubs only"))
        f = p.get("cupfield")
        if f:
            lines.append("  %s: the country's cup (regulation %d) keeps the game's divisions %d and %d"
                         % (p["name"], f[0], f[1], f[2]))
        c = p.get("own_cup")
        if c:
            total = p["clubs"] + sum(q["clubs"] for q in pl["leagues"] if c.get("below") and q.get("rid") == c["below"])
            lines.append("  %s: national cup of %d clubs (a cup of its own; its rounds and dates follow %s)%s" % (
                c["name"], c["clubs"], c["like"], ", the top division only" if c["keep_top"] else
                ", not all %d of the two divisions: the cup screens draw only some field sizes" % total
                if c["clubs"] < total else ""))
            if c.get("super"):
                lines.append("  %s: super cup, the champion v the cup winner (its date follows %s)"
                             % (c["super"], SUPER_CUP_LIKE))
    for cup in pl.get("ccups") or []:
        if cup.get("kind") == "super":
            lines.append("  %s: the winners of the CAF Champions League and the Confederation Cup, one "
                         "match in late July (first played in a career's second season)" % cup["name"])
            continue
        lines.append("  %s: %d clubs, %s" % (cup["name"], len(cup["entry"]),
                                             "%d groups of four, then a knockout of %d"
                                             % (cup["groups"], 2 * cup["groups"]) if cup["groups"]
                                             else "a knockout"))
    for note in pl.get("ccup_notes") or []:
        lines.append("  NOTE: " + note)
    own = own_places(pl)
    if any(c["number"] == 9 for c in pl.get("ccups") or []) or any(e[2] in (3, 4, 9) for e in own):
        lines += samerica_lines(own, {p["rid"]: p["name"] for p in pl["leagues"]}, pl.get("ccups") or [])
    for cup in pl.get("home_cups") or []:
        what = {"league": "league cup", "playoff": "playoff, filled on day %d" % cup["opts"]["fill"],
                "super": "super cup in late July"}
        pre = cup["opts"].get("pre")
        lines.append("  %s: %s, a knockout of %d clubs%s" % (
            cup["name"], what.get(cup["kind"], "pre-season cup in July"), len(cup["entry"]),
            ", %d of them from a pre-round of %d clubs in late September"
            % (len(pre["entry"]) // 2, len(pre["entry"])) if pre else ""))
    return "\n".join(lines)


# ---- build: tables, squads, splits, world file ----

def club_name(p, k):
    names = p["club_names"]
    if k < len(names) and names[k].strip():
        return names[k].strip()
    return "%s %02d" % (p["name"][:M.NAME_SLOT - 4], k + 1)


def abbr(name, used):
    letters = ascii_letters(name)
    for cand in (letters[:3], letters[:2] + letters[-1:], letters[:1] + letters[-2:]):
        if len(cand) == 3 and cand not in used:
            used.add(cand)
            return cand
    for n in range(1000):
        cand = "%s%02d" % (letters[:1] or "C", n % 100)
        if cand not in used:
            used.add(cand)
            return cand
    return "CLB"


# Country.bin +5 is the country's confederation, in the code Competition.bin +6 uses in its low
# three bits: 2 UEFA, 3 AFC, 4 CONMEBOL, 5 CAF, 6 CONCACAF, 7 OFC (Croatia 2, Japan and the UAE 3,
# Peru 4, Egypt 5, Mexico 6, New Zealand 7). Every league used to be copied from the Premier
# League's row and so came out UEFA wherever it was: a UAE league sat in the Champions League's
# Select Team list and a Peruvian one showed UEFA competitions (Evo-Web, 2026-09-28).
CONFED_OFF, CONFED_MASK = 5, 7
FIRST_OWN_REGION = 29            # regions 0-28 are the game's own, with their own season groups


def kickoff_after(p, mine, confed):
    """the slot league p follows in the Kick Off list: the league above it, else the end of its
    continent's leagues (KICKOFF_AFTER)"""
    up = p.get("above")
    if up:
        q = mine.get(up)
        if q and q.get("slot") not in (None, fl26world.NO_SLOT):
            return q["slot"]
        if up in SHIPPED_SLOT:
            return SHIPPED_SLOT[up]
    conf = confed.get(p["country"])
    if conf == 4:
        # after Colombia's own divisions of this world too, so Torneo BetPlay stays next to the
        # Liga BetPlay: the deepest league of the world under the Colombian top division
        at, cur = KICKOFF_AFTER[4], COLOMBIA
        for _ in range(8):
            q = next((q for q in mine.values() if q.get("above") == cur and q is not p
                      and q.get("slot") not in (None, fl26world.NO_SLOT)), None)
            if not q:
                break
            at, cur = q["slot"], q["rid"]
        return at
    return KICKOFF_AFTER.get(conf, KICKOFF_OTHER)


def confederations(base):
    """{flag id: confederation code} from Country.bin"""
    path = os.path.join(base, "Country.bin")
    if not os.path.exists(path):
        return {}
    raw = pesdb.wesys_unpack(open(path, "rb").read())
    out = {}
    for r in pesdb.rows(raw, 1420):
        fid = (int.from_bytes(r[:4], "little") >> 10) & 0x1ff
        if 2 <= r[CONFED_OFF] <= 7:
            out[fid] = r[CONFED_OFF]
    return out


def confed_line(confed):
    """the world file's confed line: each country's confederation, flag id:code, so fl26swiss
    can put a continental champion of ours into the game's own Club World Cup in place of a
    club of the champion's own confederation (0.2.0; until then always an African one)"""
    return "confed " + ",".join("%d:%d" % fc for fc in sorted(confed.items()))


def country_confederations(base):
    """{country name as country_names() gives it: confederation code} -- 2 UEFA, 3 AFC, 4 CONMEBOL,
    5 CAF, 6 CONCACAF, 7 OFC"""
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    conf = confederations(base)
    return {mkflags.title(en): conf[fid] for fid, (en, names) in cty.items()
            if en and fid in conf and mkflags.by_name(cty, en) == fid}


def id_spans(ids):
    """"71578-71587", or "75001-75002, 71580-71587" when a league has ids of its own"""
    out = []
    for t in ids:
        if out and t == out[-1][1] + 1:
            out[-1][1] = t
        else:
            out.append([t, t])
    return ", ".join("%d" % a if a == b else "%d-%d" % (a, b) for a, b in out)

def build(pl, base, game, replace=False, log=print):
    out = os.path.join(siderdir.find(game), "livecpk", pl["world"])
    if os.path.exists(out):
        if not replace:
            raise BuildError("%s exists -- build with replace to rebuild it" % out)
        if not os.path.exists(os.path.join(out, MARK)):
            raise BuildError("%s was not made by the league builder (no %s) -- left alone" % (out, MARK))
    tmp = out + ".building"
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    db = os.path.join(tmp, "common", "etc", "pesdb")
    os.makedirs(db)

    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    raw = bytearray(pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read()))
    nteam = len(raw) // W.T_REC
    have = {int.from_bytes(raw[i * W.T_REC + W.T_ID:i * W.T_REC + W.T_ID + 4], "little") for i in range(nteam)}
    top_id = max(have)
    top_alt = max(int.from_bytes(raw[i * W.T_REC + W.T_ALT:i * W.T_REC + W.T_ALT + 4], "little") for i in range(nteam))
    proto = raw[(nteam - 1) * W.T_REC:nteam * W.T_REC]
    made, own, used_abbr, added = 0, 0, set(), []
    confed = confederations(base)
    calendar_regions = {p["region"] for p in pl["leagues"] if p.get("calendar")}
    mine = {t for p in pl["leagues"] for t in p.get("club_ids") or [] if t}
    have |= mine                               # a club id of the recipe's own is nobody else's

    # clubs of the game in our leagues (game_club_checks): a club that plays somewhere in the
    # game hands every place it has there -- league, cups, continental -- to the club named to
    # take it, a club of the game in no competition or a new one made here, so no competition
    # of the game changes size; then it is entered in our league alone. The world file's nopool
    # line keeps them (and a club taking a league place) out of the game's other-clubs pools.
    game_row = {int.from_bytes(raw[i * W.T_REC + W.T_ID:i * W.T_REC + W.T_ID + 4], "little"): i * W.T_REC
                for i in range(nteam)}
    nopool = []
    # a NewLife club's id is pinned by plan() (newlife_tids) and sits just above the game's, so
    # every id handed out here steps round those: the club taking a game club's places once got
    # a NewLife club's id, the two shared one squad record and Build stopped on "57 players -- a
    # club has at most 40" (Discord, rwee and capital030, 0.1.8)
    others = pl.get("others") or []
    nl_ids = {t for p in pl["leagues"] + others for t in (p.get("newlife_tid") or {}).values()}
    if any(game_places(p) for p in pl["leagues"]):
        info = game_info(base)
        for p in pl["leagues"]:
            for at, g in sorted(game_places(p).items()):
                sw, tid = g.get("swap"), g["id"]
                if isinstance(sw, dict):
                    r = bytearray(proto)
                    sid = top_id + 1 + own
                    own += 1
                    while sid in have or sid in nl_ids:
                        sid = top_id + 1 + own
                        own += 1
                    if sid > CLUB_ID_MAX:
                        raise BuildError("no team ids left up to %d" % CLUB_ID_MAX)
                    have.add(sid)
                    r[W.T_ID:W.T_ID + 4] = sid.to_bytes(4, "little")
                    r[W.T_ALT:W.T_ALT + 4] = (top_alt + 1 + made).to_bytes(4, "little")
                    M.put(r, W.T_NAME, sw["name"], W.T_NAME_LEN)
                    short = abbr(sw["name"], used_abbr)
                    r[W.T_ABBR:W.T_ABBR + W.T_ABBR_LEN] = short.ljust(W.T_ABBR_LEN, bytes(1).decode()).encode("ascii")
                    added.append(r)
                    made += 1
                    g["swap_id"], g["swap_abbr"] = sid, short
                else:
                    g["swap_id"] = sw or None
                nopool.append(tid)
                # #60: the game files a club into an "Other ..." group by a nibble of its own record,
                # at boot, whatever the competitions say -- so a moved club showed up there as well
                raw[game_row[tid] + T_POOL] &= 0x0f
                kept = sorted(set(info["entries"].get(tid) or []) & CONTINENTAL_CIDS) if g.get("keep") else []
                if kept:
                    log("  %s keeps its place in %s" % (info["clubs"][tid][0],
                                                       ", ".join(info["comp_names"].get(c, str(c)) for c in kept)))
                if g["swap_id"]:
                    n = swap_entries(ents, tid, g["swap_id"], CONTINENTAL_CIDS if g.get("keep") else ())
                    played_league = any(c in info["league_cids"] for c in info["entries"].get(tid) or [])
                    if played_league and not isinstance(sw, dict):
                        nopool.append(g["swap_id"])
                        raw[game_row[g["swap_id"]] + T_POOL] &= 0x0f
                    log("  %s moves to %s; %s takes its %d place(s) in %s"
                        % (info["clubs"][tid][0], p["name"],
                           sw["name"] if isinstance(sw, dict) else info["clubs"][g["swap_id"]][0], n,
                           ", ".join(game_club_where(info, tid, g.get("keep")))))
                elif kept:
                    log("  %s moves to %s" % (info["clubs"][tid][0], p["name"]))
                elif set(info["entries"].get(tid) or []) & info["friendly_cids"]:
                    log("  %s moves to %s and keeps its place in the pre-season tournament"
                        % (info["clubs"][tid][0], p["name"]))
                else:
                    log("  %s (in no competition of the game) moves to %s" % (info["clubs"][tid][0], p["name"]))

    def new_club(p, k):
        """a new club's Team.bin record, the k-th of league (or group) p: [record, id, abbr]"""
        nonlocal own, made
        r = bytearray(proto)
        ids = p.get("club_ids") or []
        nl = (p.get("newlife") or {}).get("clubs") or []
        if k < len(ids) and ids[k]:
            tid = ids[k]                   # checked by plan(): free, in the block
        elif k < len(nl) and NEWLIFE_TEAMS[0] <= nl[k] <= NEWLIFE_TEAMS[1] and nl[k] not in have:
            # 0.1.8 (#90 / #88): a NewLife Database club gets a world id of its own, the one
            # plan() gave it; the NewLife id is only how the recipe names the club
            tid = (p.get("newlife_tid") or {}).get(nl[k])
            if tid is None:
                raise BuildError("%s, club %d: no world id for the NewLife club %d"
                                 % (p["name"], k + 1, nl[k]))
        else:
            tid = top_id + 1 + own
            own += 1
            while tid in have or tid in nl_ids:    # a NewLife club's pinned id may sit lower
                tid = top_id + 1 + own
                own += 1
            if tid > CLUB_ID_MAX:
                raise BuildError("no team ids left up to %d" % CLUB_ID_MAX)
        have.add(tid)
        r[W.T_ID:W.T_ID + 4] = tid.to_bytes(4, "little")
        r[W.T_ALT:W.T_ALT + 4] = (top_alt + 1 + made).to_bytes(4, "little")
        M.put(r, W.T_NAME, club_name(p, k), W.T_NAME_LEN)
        # the club's country is its league's: the clone is Selangor FC, so without this every
        # new club, and its manager (mkcoaches takes the club's), was Malaysian (Amir, FK Sloboda)
        c = struct.unpack_from("<H", r, T_COUNTRY)[0]
        struct.pack_into("<H", r, T_COUNTRY, (c & ~(0x1ff << 2)) | ((p["country"] & 0x1ff) << 2))
        mine = (p.get("club_abbrs") or [])[k:k + 1]
        if mine and mine[0].strip():
            short = short_name(mine[0])
            used_abbr.add(short)
        else:
            short = abbr(club_name(p, k), used_abbr)
        r[W.T_ABBR:W.T_ABBR + W.T_ABBR_LEN] = short.ljust(W.T_ABBR_LEN, bytes(1).decode()).encode("ascii")
        added.append(r)
        made += 1
        return r, tid, r[W.T_ABBR:W.T_ABBR + W.T_ABBR_LEN].split(bytes(1))[0].decode("ascii")

    for p in pl["leagues"]:
        teams, p["abbrs"] = [], []
        gp = game_places(p)
        for k in range(p["clubs"]):
            if k in gp:
                tid = gp[k]["id"]
                o = game_row[tid]
                teams.append(tid)
                p["abbrs"].append(text(raw[o + W.T_ABBR:o + W.T_ABBR + W.T_ABBR_LEN]))
                continue
            _r, tid, short = new_club(p, k)
            teams.append(tid)
            p["abbrs"].append(short)
        p["teams"] = teams
        M.add_league(comp, regs, ents, p["cid"], p["rid"], M.enc_region(p["region"]), p["name"],
                     "FL_%03d_LEAGUE" % p["rid"], teams, quiet=True, tier=p["tier"])
        conf = confed.get(p["country"])
        # ... except a league of our own regions (29 and up) that plays August to May. The
        # season-end filter 0x141365c50 wants UEFA in July for the region group fl26augseason
        # gives ours, and a league it passes over is neither closed nor let into the next
        # season: a Peruvian first division coded CONMEBOL promoted nobody, and an Egyptian,
        # Moroccan or Venezuelan league on its own played no second season at all (door "no",
        # 2026-09-29). The League Info icons come from the world file's conf= instead. A
        # February-December country is closed at New Year and keeps its own code.
        if conf and p["region"] >= FIRST_OWN_REGION and p["region"] not in calendar_regions:
            conf = None
        if conf:
            co = len(comp) - M.COMP + M.FLAG_OFF          # the row add_league just appended
            comp[co] = (comp[co] & ~CONFED_MASK) | conf
        rows = {u16(regs[i * M.REG:], M.R_ID): i for i in range(len(regs) // M.REG)}
        o = rows[p["rid"]] * M.REG
        g = regs[o:o + M.REG]
        if p.get("cup_all"):
            # the bracket is the whole field: 44 left a field of 32 or fewer without its
            # first round's byes, as 22 on 44 did (#74)
            co = rows[p["cup"]] * M.REG + M.R_TEAMS
            regs[co] = (regs[co] & 0xc0) | p["cup_all"]
        if p["above"]:
            po = rows[p["above"]] * M.REG
            # the child takes its parent's calendar shape, as deepen.py does, then its own
            # division and legs; the link is written both ways
            struct.pack_into("<I", g, 0x10, struct.unpack_from("<I", regs, po + 0x10)[0])
            M.set_tier(g, p["tier"])
            g[R_ABOVE:R_ABOVE + 2] = p["above"].to_bytes(2, "little")
            regs[po + M.R_BELOW:po + M.R_BELOW + 2] = p["rid"].to_bytes(2, "little")
        rules = int.from_bytes(g[0x10:0x14], "little")
        rules = (rules & ~(LEGS_MASK << LEGS_SHIFT)) | (p["legs"] << LEGS_SHIFT)
        g[0x10:0x14] = rules.to_bytes(4, "little")
        regs[o:o + M.REG] = g
        log("  %-26s reg %d, %d clubs %s%s" % (p["name"], p["rid"], len(teams), id_spans(teams),
                                             ", %d of them the game's" % len(gp) if gp else ""))

    # clubs in no league: the game files a club into an "Other ..." group by the nibble at T_POOL,
    # at boot, with no competition behind it -- as its own Dynamo Kyiv or Wydad Casablanca
    for p in others:
        p["teams"], p["abbrs"] = [], []
        for k in range(p["clubs"]):
            r, tid, short = new_club(p, k)
            r[T_POOL] = (r[T_POOL] & 0x0f) | (p["others"] << 4)
            p["teams"].append(tid)
            p["abbrs"].append(short)
        log("  %-26s %d club(s) in no league, %s %s" % (p["name"], len(p["teams"]),
                                                       OTHERS_NAMES[p["others"]], id_spans(p["teams"])))
    clubs = dict(pl, leagues=pl["leagues"] + others)    # every new club, for what goes by club

    # the new clubs go in in id order, as the shipped ones are
    for r in sorted(added, key=lambda r: int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")):
        raw += r
    apply_edits(pl.get("edits") or {}, raw, regs, log)
    swaps = (pl.get("edits") or {}).get("swaps") or []
    if swaps:                                          # two clubs of the game's leagues trade places
        info = game_info(base)
        for a, b in ((int(x), int(y)) for x, y in swaps):
            na, nb = exchange_entries(ents, a, b)
            log("  %s (%s) and %s (%s) swap leagues: %d and %d place(s)"
                % (info["clubs"].get(a, (a,))[0], info["league_of"].get(a, "?"),
                   info["clubs"].get(b, (b,))[0], info["league_of"].get(b, "?"), na, nb))
    open(os.path.join(db, "Team.bin"), "wb").write(pesdb.wesys_pack(bytes(raw)))
    cpath = os.path.join(base, "Coach.bin")
    if os.path.exists(cpath):
        craw = open(cpath, "rb").read()
        coaches = pesdb.wesys_unpack(craw)
        named = {t: (p.get("club_coaches") or [])[k].strip() for p in clubs["leagues"]
                 for k, t in enumerate(p["teams"])
                 if k < len(p.get("club_coaches") or []) and (p["club_coaches"][k] or "").strip()
                 and k not in game_places(p)}
        ppath = os.path.join(base, "Player.bin")
        pool = (mkcoaches.name_pool(pesdb.wesys_unpack(open(ppath, "rb").read()))
                if os.path.exists(ppath) else None)
        add, st = mkcoaches.add_coaches(coaches, bytes(raw), top_id + 1, names=named, pool=pool)
        open(os.path.join(db, "Coach.bin"), "wb").write(pesdb.wesys_pack(coaches + add, craw[:3]))
        log("  %d managers" % st["added"])
    lineups = {}
    wanted = club_formations(clubs)
    if wanted:
        import mktactics
        donors = {t: formation_club(base, f) for t, f in wanted.items()}
        shown = mktactics.write(base, db, donors)
        lineups = {t: mktactics.roles(places) for t, places in shown.items()}
        log("  formations for %d clubs" % len(shown))
    with contextlib.redirect_stdout(io.StringIO()):
        M.write_tables(tmp, comp, regs, ents)

    if made:
        import mkplayers
        call(mkplayers, ["--base", base, "--out", tmp, "--per", SQUAD, "--cap", PLAYER_CAP])
        log("  squads of %d for %d clubs" % (SQUAD, made))
    import lbplayers
    faces, ids, portraits = [], {}, []
    try:
        filled = dict(clubs, players=lbplayers.fill_newlife(clubs, base, log))   # the plan kept as it was
        filled["players"] = lbplayers.fill_tiers(filled, base, log)
        lbplayers.apply(filled, base, db, PLAYER_CAP, log, faces, lineups=lineups, ids=ids, portraits=portraits)
    except lbplayers.Error as e:
        raise BuildError(str(e))
    if ids:                                            # for Mod Studio's Players page and its CSV
        with open(os.path.join(tmp, PLAYER_IDS), "w", encoding="utf-8") as f:
            json.dump({"world": pl["world"], "clubs": ids}, f, indent=1, sort_keys=True)
    if faces:
        import lbfaces
        for n, (pid, folder) in enumerate(faces):
            lbfaces.install(tmp, pid, folder, n, log)
    lbplayers.player_portraits(portraits, tmp, log)
    lbplayers.coach_portraits(clubs, tmp, log)
    newfaces = lbplayers.new_face_lines(base, db, faces, portraits)   # fl26regen: pack faces (#52)

    splits = [p for p in pl["leagues"] if p.get("split")]
    if splits:
        import mksplit
        args = ["--base", db, "--out", tmp]
        for p in splits:
            s = p["split"]
            args += ["--split", "%d:%dx%d:%s%s" % (p["rid"], p["clubs"], s["legs"],
                                                   ":".join("%dx%d" % (c, s["group_legs"]) for c in s["groups"]),
                                                   "@Apertura,Clausura" if s.get("apertura") else "")]
        said = call(mksplit, args)
        log("  %d split season(s)" % len(splits))
        import re
        phases = {int(m.group(1)): [int(x) for x in m.group(2).split(",")] for m in
                  re.finditer(r"^reg (\d+) .*-> split total over \d+ clubs, phases ([\d,]+)", said, re.M)}
        for cup in pl.get("home_cups") or []:
            if cup.get("kind") == "playoff":
                ph = phases.get(cup["league"]) or []
                if len(ph) < 2:
                    raise BuildError("mksplit gave %d no Apertura and Clausura:\n%s" % (cup["league"], said))
                cup["entry"] = [(ph[cup["phase"]], pos) for _r, pos in cup["entry"]]

    rounds = qual_rounds(pl)
    uecl, qlines = europe(tmp, db, log, bool(pl.get("uecl")), pl.get("uecl_name"), rounds)
    national_cups(pl, tmp, db, log)
    hc = home_cups(pl, confed)
    own_cup = {p["rid"]: (p.get("own_cup") or {}).get("reg") for p in pl["leagues"]}
    for c in pl.get("ccups") or []:
        c["winners"] = list(c.get("winners") or []) + [[r, own_cup[r]] for r in
                                                       {e[1] for e in c["entry"] if e[0] == "cup"} if own_cup.get(r)]
    ccups = continental((pl.get("ccups") or []) + hc, tmp, db, log, alt_from(pl))
    # the confed line also tells fl26swiss which of our clubs the board sends to the AFC
    # Champions League or the Libertadores instead of the Champions League (GitHub #43), so a
    # world with a league outside UEFA gets it even with no continental cup
    if confed and (pl.get("ccups") or any(confed.get(p["country"], 2) != 2 for p in pl["leagues"])):
        ccups.append(confed_line(confed))
    for c, h in zip(hc, pl.get("home_cups") or []):
        h["cid"] = c["cid"]                            # for its emblem (pictures)
    rename_competitions(pl, db, log)

    # the world file: the tables' own reading (fl26world.from_tables), with what the recipe
    # knows better -- the country chosen, and how many clubs go up and down
    with contextlib.redirect_stdout(io.StringIO()):
        leagues, split_lines = fl26world.from_tables(tmp, base)
    # Apertura/Clausura: the Clausura starts from zero (fl26swiss leaves its key out of the carry)
    ap_ids = {p["rid"] for p in pl["leagues"] if p.get("apertura")}
    split_lines = [tuple(s) + ("carry=0",) if s[0] in ap_ids else s for s in split_lines]
    mine = {p["rid"]: p for p in pl["leagues"]}
    for L in leagues:
        p = mine.get(L["id"])
        if not p:
            continue
        L["country"] = p["country"]
        if confed.get(p["country"]):
            L["conf"] = confed[p["country"]]           # fl26catlist: the League Info icons (#33)
        L["slot"] = p["slot"]
        if p["slot"] != fl26world.NO_SLOT:
            L["kickoff"] = kickoff_after(p, mine, confed)
        if p.get("exhibition"):
            L["exhibition"] = 1                        # fl26joindll leaves it out of the season
        if p["above"]:
            L["above"], L["promote"] = p["above"], p["exchange"]
        else:
            L.pop("above", None)
            L["promote"] = 0
        below = next((q for q in pl["leagues"] if q["above"] == p["rid"]), None)
        L["demote"] = below["exchange"] if below else 0
        if p.get("cup"):
            L["cup"] = p["cup"]
            if p.get("cup_all"):
                L["cupall"] = 1                        # fl26chain: the cup takes both leagues (#32)
        if p.get("scup"):
            L["scup"] = p["scup"]
        f = p.get("cupfield")
        if f and not any(q.get("cupfield") == f for q in pl["leagues"][:pl["leagues"].index(p)]):
            L["cup"], L["cuptop"], L["cuplow"], L["cupall"] = f[0], f[1], f[2], 1
        up = mine.get(p["above"]) if p["above"] else None
        if up and up.get("own_cup", {}).get("keep_top"):
            L["cup"] = up["own_cup"]["reg"]            # fl26chain keeps the cup to the top league
            if up["own_cup"]["clubs"] < up["clubs"]:
                L["cupn"] = up["own_cup"]["clubs"]     # and to a field the bracket screen draws (#74)
        c = p.get("own_cup")
        if c and c.get("reg") and not c["keep_top"] and (below or c["clubs"] < p["clubs"]):
            # the game fills the cup from both leagues whatever its entry list says, so fl26chain
            # writes the top league's clubs and the first ones below, a field the bracket screen
            # draws (#74: a cup of 22 crashed Competition Info -> Fixtures). Also when the two
            # leagues fill the bracket exactly (20 + 12 = 32): left alone, a split top league put
            # only its own 20 into the cup of 32
            L["cup"], L["cuptop"], L["cuplow"], L["cupall"] = c["reg"], p["rid"], below["rid"] if below else 0, 1
            L["cupn"] = c["clubs"]
    uefa, over = fl26world.uefa_places(all_places(pl),
                                       pl.get("game_replace") or [], bool(pl.get("uecl")))
    names = dict(fl26world.COMPETITIONS)
    for c, (n, room) in sorted(over.items()):
        log("  NOTE: %s has %d places listed for %d clubs; the last %d get none"
            % (names[c], n, room, n - room))
    if uefa:
        log("  European places: %d of the new leagues, %d in all"
            % (sum(1 for e in own_places(pl) if e[2] in fl26world.UEFA_LINE), len(uefa)))
    fl26world.write_world(os.path.join(tmp, MARK), pl["world"], leagues, split_lines, uefa, uecl,
                          ccups + dates_lines(pl, db) + season_lines(pl, db) + july_lines(pl, base) + first_lines(pl)
                          + order_lines(pl, base, confed)
                          + kickorder_lines(pl, base, confed)
                          + (["nopool " + " ".join(str(t) for t in nopool)] if nopool else []) + newfaces
                          + ["cupdraw %s" % pl.get("cup_draw", "seeded")],
                          qlines)
    json.dump(pl, open(os.path.join(tmp, "leaguebuilder-plan.json"), "w", encoding="utf-8"), indent=1)

    pictures(pl, tmp, base, log)
    region_modules(pl, tmp, game, log)

    write_manifest(tmp)                   # before keep_added: what this Build wrote, not what it kept
    if os.path.exists(out):
        keep_added(out, tmp, log)
        shutil.rmtree(out)
    os.rename(tmp, out)
    log("built %s: %d leagues, %d clubs" % (out, len(pl["leagues"]), made))
    if is_live(pl["world"], game):
        # GitHub #69: the modules read SiderAddons/modules/fl26world.txt, a copy Switch on makes.
        # A world built again while it was already on kept the old copy, and a change (February
        # to December) never reached the game until Switch on was pressed once more.
        log("%s is the live world: switching it on again, so the game reads what was just built" % pl["world"])
        switch_on(pl["world"], game, log)
    return out


MANIFEST = "leaguebuilder-files.txt"      # the files a Build wrote: path, and a hash for pictures
ADDED_DIRS = ("common/render/",)          # crests and logos: where people put pictures by hand


def built_files(root):
    """relative paths (with /) of every file under root"""
    out = set()
    for d, _dirs, files in os.walk(root):
        for f in files:
            out.add(os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/"))
    return out


def picture(rel):
    return rel.lower().startswith(ADDED_DIRS) and rel.lower().endswith((".png", ".dds"))


def file_hash(path):
    import hashlib
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def write_manifest(root):
    lines = []
    for rel in sorted(built_files(root) - {MANIFEST}):
        lines.append(rel + ("\t" + file_hash(os.path.join(root, rel)) if picture(rel) else ""))
    with open(os.path.join(root, MANIFEST), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def keep_added(old, new, log=print):
    """carry into the new build the pictures someone put in the old world folder by hand (a crest
    in common/render/symbol/flag, Xxspedd 04.10.): a Build replaces the whole folder.
    - a file the last Build did not write, and this one does not either: copied over
    - a picture the last Build wrote and someone replaced: theirs stays, as long as this Build
      writes the same picture as the last one (a crest set in the recipe since then wins)
    A world built before the manifest existed keeps only the pictures this Build does not write."""
    ours = {}
    try:
        with open(os.path.join(old, MANIFEST), encoding="utf-8") as f:
            for line in f:
                rel, _t, h = line.rstrip("\n").partition("\t")
                if rel:
                    ours[rel] = h
        known = True
    except OSError:
        known = False
    made = built_files(new)
    kept = []
    for rel in sorted(built_files(old) - {MANIFEST}):
        src, dst = os.path.join(old, rel), os.path.join(new, rel)
        if rel not in made:
            if (rel not in ours) if known else picture(rel):
                kept.append(rel)
        elif known and ours.get(rel) and picture(rel):
            if file_hash(src) != ours[rel] and file_hash(dst) == ours[rel]:
                kept.append(rel)
    for rel in kept:
        dst = os.path.join(new, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(old, rel), dst)
    if kept:
        log("  kept %d file(s) you added to the world folder (%s%s); Import crests puts them in the recipe"
            % (len(kept), ", ".join(kept[:3]), " ..." if len(kept) > 3 else ""))
    return kept


def is_live(world, game):
    """is <world> the one the modules read now (the world line of modules/fl26world.txt)?"""
    try:
        with open(os.path.join(siderdir.find(game), "modules", MARK), encoding="utf-8", errors="replace") as f:
            # the file opens with its "# fl26world 1" header; the name is on the "world" line
            for line in f:
                w = line.split()
                if w[:1] == ["world"]:
                    return w[1:2] == [world]
        return False
    except (OSError, BuildError):
        return False


def qual_rounds(pl):
    """the August qualifying rounds the world gets (fl26world.pick_rounds): as many as the European
    places it lists fill -- the play-offs alone with the game's own places"""
    uefa, _over = fl26world.uefa_places(all_places(pl),
                                        pl.get("game_replace") or [], bool(pl.get("uecl")))
    return fl26world.pick_rounds(uefa, bool(pl.get("uecl")))


def europe(root, db, log=print, uecl=True, name=None, rounds=()):
    """the European cups of the world being built (tables in <db>, the world folder <root>): the
    Champions League and Europa League league phase as one group of 36, then (uecl) mkuecl's
    clone of the Europa League, mkeuropo's play-offs, and the qualifying rounds in front of them
    of rounds ((competition, stage) pairs, qual_rounds), each in place. Returns the Conference
    League's entrants ([] without it) and the world file's qround lines.

    The league phase is built with the Conference League off too: fl26swiss.dll always runs
    1027/1029 as a league phase of 36 (the access list, the draw, the top 16 into the knockout),
    and in the game's own format those are group A of the Champions League and of the Europa
    League -- it tops group A up to 36 clubs and hands its top 16 to the round of 16 (issue #33:
    "if the Conference League is off, the Champions League and Europa League break")."""
    import mkreshape, mkeuropo
    args = ["--base", db, "--out", root]
    for r in RESHAPE:
        args += ["--reshape", r]
    said = call(mkreshape, args)
    for row in (1027, 1029):
        if "replica %d kept: 36 clubs" % row not in said:
            raise BuildError("the league phase reshape did not give group %d 36 clubs:\n%s" % (row, said))
    log("  Champions League and Europa League: league phase of 36 (groups 1027, 1029)")
    try:
        clubs = mkuecl.build(db, root, log=log, name=name) if uecl else []
        mkeuropo.build(db, root, log=log, uecl=uecl)
    except SystemExit as e:
        raise BuildError("%s: %s" % ("Conference League" if uecl else "Europa League play-off", e))
    extra = [r for r in rounds if r[1] and (uecl or r[0] != 2)]
    qlines = []
    if extra:
        try:
            qlines = mkeuropo.qualifying(db, root, extra, free_comp_ids(db)[1], log=log)
        except SystemExit as e:
            raise BuildError("qualifying rounds: %s" % e)
    return clubs, qlines


def free_comp_ids(db, reserved=()):
    """competition ids and regulation ids (from CCUP_REG_FROM) nothing in the world's tables in
    <db> uses, nor anything kept for later"""
    comp, regs = M.load(db, "Competition.bin"), M.load(db, "CompetitionRegulation.bin")
    used_cid = {comp[i + M.CID_OFF] for i in range(0, len(comp), M.COMP)}
    used_reg = {u16(regs[i:], M.R_ID) & 0x3ff for i in range(0, len(regs), M.REG)}
    taken = (used_reg | CCUP_KEEP | W.BAD_REG | set(W.MOVED_REG.values()) | set(fl26world.DEFAULT_SLOT)
             | set(fl26world.NO_SLOT_IDS) | set(reserved))
    return ([c for c in range(CID_FROM, W.CID_MAX + 1) if c not in used_cid and c != UECL_CID],
            [r for r in range(CCUP_REG_FROM, 1024) if r not in taken])


def like_reg(db, code):
    """the regulation id of the shipped competition coded `code` (its first row)"""
    comp, regs = M.load(db, "Competition.bin"), M.load(db, "CompetitionRegulation.bin")
    row = M.find_code(comp, code)        # by code, or by its shipped id (GitHub #54)
    cid = None if row is None else comp[row * M.COMP + M.CID_OFF]
    return next((u16(regs[i * M.REG:], M.R_ID) for i in range(len(regs) // M.REG)
                 if cid is not None and regs[i * M.REG + M.R_CID] == cid), None)


# The Select Team list is ordered by region first, in the order of a list of 28 region ids in
# the exe (0x1427d5760; the comparator 0x140eadae0): the club competitions, then Europe, Latin
# America and Asia, each alphabetical with its "other" group last. fl26catlist.lua copies that
# list and appended our regions 29..63 after it, so a new country came after Thailand whatever
# its name. The `order` line puts each of our countries in its continent, by name.
SHIPPED_REGIONS = [                       # (region, name, confederation); None = a group
    (1, None, 0), (26, None, 0),
    (8, "Belgium", 2), (12, "Denmark", 2), (2, "England", 2), (3, "France", 2), (5, "Italy", 2),
    (7, "Netherlands", 2), (6, "Portugal", 2), (9, "Russia", 2), (15, "Scotland", 2),
    (4, "Spain", 2), (10, "Switzerland", 2), (27, "Turkey", 2), (22, None, 2),
    (17, "Argentina", 4), (16, "Brazil", 4), (18, "Chile", 4), (19, "Colombia", 4), (23, None, 4),
    (21, "China", 3), (28, "Saudi Arabia", 3), (24, None, 3),
    (25, None, 9),
]
CONTINENT = {2: 2, 3: 3, 4: 4, 6: 4, 7: 3, 5: 5}   # confederation -> block: CONCACAF with the
                                                    # Americas, OFC with Asia, CAF a block of its own


# The recipe's "country_order" (Mod Studio's League order, 0.2.0): left out, the countries go by
# continent as above; "az", every country A-Z; a list of country names, that order (a country
# it does not name goes after them, by continent). The countries then come first as one run in
# that order, and the club competitions, the "other" groups and Classic Teams after them in
# their own order -- in Select Team (the `order` line, the club competitions still at the top)
# and in the Kick Off / Edit list (the `kickorder` line, fl26comptab), where a country's
# leagues stay together in the order they had.
# (Not "league_order": that is the Leagues page's drag order of Mod Studio's own list since 0.1.8,
# a list of league keys -- read as country names it matched none and reordered Kick Off anyway.)
# The game's league slots in the Kick Off list (SHIPPED_SLOT's) and their countries; Germany,
# the USA and Japan have no region of their own in Select Team (they sit in the "other" groups),
# so they move only in Kick Off. Saudi Arabia has Thailand's old region 28 (Discord, LaraCroft).
SLOT_COUNTRY = {7: "England", 50: "England", 8: "France", 52: "France", 9: "Italy", 53: "Italy",
                10: "Netherlands", 11: "Spain", 51: "Spain", 12: "Portugal", 13: "Brazil", 122: "Brazil",
                14: "Argentina", 15: "Chile", 16: "Germany", 17: "Usa", 18: "Japan", 88: "Belgium",
                91: "Russia", 94: "Switzerland", 96: "Turkey", 99: "Colombia", 102: "China",
                105: "Denmark", 114: "Scotland", 119: "Saudi Arabia"}
OTHER_CONFED = {"Germany": 2, "Usa": 6, "Japan": 3}


def order_countries(pl, base, confed):
    """[(country name, continent block)] of every country with a league in the game or the
    world, in the default order (by continent, A-Z within it) -- the League order dialog's list"""
    ids = country_ids(base)
    names, fids = dict((fid, nm) for nm, fid in ids), dict(ids)
    got = {nm: c for _r, nm, c in SHIPPED_REGIONS if nm}
    for nm, c in OTHER_CONFED.items():
        got.setdefault(nm, c)
    for p in pl.get("leagues") or []:
        c = p.get("country")                # an id once planned, the recipe's name before
        nm = c if isinstance(c, str) else names.get(c)
        if nm:
            got.setdefault(nm, CONTINENT.get(confed.get(fids.get(nm, c)), 5))
    blocks = (2, 4, 3, 5)
    return sorted(((nm, CONTINENT.get(c, c)) for nm, c in got.items()),
                  key=lambda x: (blocks.index(x[1]) if x[1] in blocks else 9, x[0].lower()))


def country_rank(pl, base, confed):
    """{country name: place} for the recipe's country_order, None for the default"""
    want = pl.get("country_order")
    if not want:
        return None
    every = [nm for nm, _c in order_countries(pl, base, confed)]
    if want == "az":
        seq = sorted(every, key=str.lower)
    else:
        seq = [nm for nm in want if nm in every]
        seq += [nm for nm in every if nm not in seq]
    return {nm: i for i, nm in enumerate(seq)}


def reorder_named(seq, name_of, rank):
    """seq with the entries that have a name (name_of) in rank order, together where the first
    of them was; the others keep their order around them"""
    at = [i for i, x in enumerate(seq) if name_of(x) in rank]
    if not at:
        return list(seq)
    moved = sorted((seq[i] for i in at), key=lambda x: (rank[name_of(x)], seq.index(x)))
    rest = [x for x in seq if name_of(x) not in rank]
    return rest[:at[0]] + moved + rest[at[0]:]


def kickorder_lines(pl, base, confed):
    """the world file's `kickorder <regulation>:<place>,...` line (fl26comptab): the Kick Off /
    Edit list's leagues by country, when the recipe has a country_order"""
    rank = country_rank(pl, base, confed)
    if rank is None:
        return []
    names = dict((fid, nm) for nm, fid in country_ids(base))
    out, slots = [], set()
    for reg, slot in sorted(SHIPPED_SLOT.items()):
        nm = SLOT_COUNTRY.get(slot)
        if nm in rank and slot not in slots:
            slots.add(slot)
            out.append((reg, rank[nm]))
    for p in pl["leagues"]:
        nm = names.get(p["country"])
        if nm in rank and p.get("slot", fl26world.NO_SLOT) != fl26world.NO_SLOT:
            out.append((p["rid"], rank[nm]))
    return ["kickorder " + ",".join("%d:%d" % x for x in out)] if out else []


def order_lines(pl, base, confed):
    """the world file's `order` line: the Select Team list's region order with our countries
    in it (see SHIPPED_REGIONS), in the recipe's country_order when it has one"""
    names = dict((fid, nm) for nm, fid in country_ids(base))
    shipped = {r for r, _, _ in SHIPPED_REGIONS}
    rank = country_rank(pl, base, confed)
    ours = {}
    # Exhibition leagues too: they have no Select Team entry, but Competition Info lists every
    # region with a live regulation, and a region the line leaves out goes after all the others
    # -- a Polish exhibition league sat below Classic Teams (evoweb, NadnyNick999, 0.1.3).
    for p in pl["leagues"]:
        r = p["region"]
        if r in shipped or r in ours:
            continue
        ours[r] = (names.get(p["country"], "~"), CONTINENT.get(confed.get(p["country"]), 5))
    if not ours and rank is None:
        return []
    out = []
    for block in (2, 4, 3, 5):
        named = [(nm, r) for r, nm, c in SHIPPED_REGIONS if c == block and nm]
        named += [(nm, r) for r, (nm, c) in ours.items() if c == block]
        group = [r for r, nm, c in SHIPPED_REGIONS if c == block and not nm]
        out += [r for nm, r in sorted(named, key=lambda x: x[0].lower())] + group
        if block == 2:
            out = [1, 26] + out
    out.append(25)
    if rank is not None:
        region_name = {r: nm for r, nm, _c in SHIPPED_REGIONS if nm}
        region_name.update((r, nm) for r, (nm, _c) in ours.items())
        out = reorder_named(out, region_name.get, rank)
    return ["order " + ",".join(map(str, out))]


def dates_lines(pl, db):
    """world file lines `dates <our cup> like=<shipped cup>`: the game dates a cup's rounds by its
    regulation id, in a switch over the shipped ids 2..175, so a national cup or super cup of
    ours (id 176 and up) got its draw but not one date, and was never played (CUPT world,
    2026-09-28: 197 and 198, 20 records, all undated). fl26swiss.dll asks the game for the dates
    of the cup it was copied from instead."""
    out = []
    for p in pl["leagues"]:
        c = p.get("own_cup")
        if not c or not c.get("reg"):
            continue
        for reg, code in ((c["reg"], c["like"]), (c.get("super_reg"), SUPER_CUP_LIKE if c.get("super") else None)):
            like = like_reg(db, code) if reg and code else None
            if like:
                out.append("dates %d like=%d" % (reg, like))
    return out


def season_lines(pl, db):
    """world file lines `season <region> <type>`: the game gives each region a season type
    (0x141576140, a table of 25 regions: 0 August-May, 1 January-December ...), and a region it
    has not got plays August-May (fl26augseason). fl26join.dll puts the world file's types in
    front of that table, and fl26joindll/fl26swiss take a type-1 region's leagues for
    calendar-year ones (registration, New Year promotion, round dates)"""
    out = ["season %d 1" % r for r in sorted({p["region"] for p in pl["leagues"] if p.get("calendar")})]
    for c in pl.get("game_seasons") or []:
        # the moved country's cups keep their calendar-year dates otherwise (GAME_SEASONS)
        region, _leagues, cups = GAME_SEASONS[c]
        out.append("season %d 0" % region)
        for reg, code in sorted(cups.items()):
            like = like_reg(db, code)
            if like:
                out.append("dates %d like=%d" % (reg, like))
    return out


# The day a country's league really kicks off, as the Saturday of 2026 (day of the year, 1
# January = 0): 191 = 11 July, 198 = 18 July, 205 = 25 July, 212 = 1 August, 219 = 8 August,
# 226 = 15 August. The game starts every league on the big leagues' calendar (about 22 August),
# and the first three weeks of July had no match at all. Countries not listed keep that.
JULY_START = {
    "Romania": 191, "Poland": 198, "Denmark": 198, "Serbia": 198, "Slovenia": 198, "Slovakia": 198,
    "Czechia": 198, "Czech Republic": 198, "Russia": 198, "Bulgaria": 198,
    "Bosnia and Herzegovina": 198, "Croatia": 205, "Hungary": 205, "Austria": 205,
    "Switzerland": 205, "Belgium": 205, "Montenegro": 205, "North Macedonia": 212,
    "Ukraine": 212, "Scotland": 212, "Netherlands": 219, "Portugal": 219, "Turkey": 219,
    "France": 226,
}


def july_lines(pl, base):
    """world file lines `july <reg> <day>`: a league of a country that kicks off before the big
    leagues has its rounds before New Year brought forward by whole weeks, the first onto that
    day (fl26swiss.dll, from the second season: a new career starts on 4 August)"""
    import mkflags
    import uefakey
    cty = mkflags.countries(mkflags.table("Country", [base]))
    out, seen = [], set()
    for p in pl["leagues"]:
        if p.get("calendar") or p.get("split") or p.get("apertura") or p.get("exhibition"):
            continue
        en = mkflags.title((cty.get(p.get("country")) or ("", None))[0] or "")
        day = JULY_START.get(en)
        if day and p.get("rid") and p["rid"] not in seen:
            seen.add(p["rid"])
            out.append("july %d %d" % (p["rid"], day))
    for rid, country in sorted(uefakey.GAME_LEAGUES.items()):
        day = JULY_START.get(country)
        if day and rid not in seen and country != "Scotland":     # Scotland is a split (133-136)
            seen.add(rid)
            out.append("july %d %d" % (rid, day))
    return out


def cup_seeding(teams, top):
    """the entry order of a national cup, which is its first-round draw (mkcup: entry n meets
    entry n+1): the top division and the one below taken in turn, so a first round pairs a club
    from each instead of the top division among itself (San Marino, 06.10.)"""
    hi, lo = teams[:top], teams[top:]
    out = []
    for i in range(max(len(hi), len(lo))):
        out += hi[i:i + 1] + lo[i:i + 1]
    return out


def national_cups(pl, root, db, log=print):
    """the national cups planned (national_cup) into the world's tables, one mkcup.py each"""
    import mkcup
    for p in pl["leagues"]:
        c = p.get("own_cup")
        if not c:
            continue
        cids, regs = free_comp_ids(db)
        if not cids or not regs:
            raise BuildError("no free competition or regulation ids left for %s" % c["name"])
        teams = list(p["teams"])
        if not c["keep_top"] and c["below"]:
            teams += next(q["teams"] for q in pl["leagues"] if q["rid"] == c["below"])
        teams = teams[:c["clubs"]]           # a field cut to a size the bracket screen draws (#74)
        teams = cup_seeding(teams, len(p["teams"]))
        c["cid"], c["reg"] = cids[0], regs[0]
        call(mkcup, ["--base", db, "--out", root, "--teams", ",".join(map(str, teams)),
                     "--cid", c["cid"], "--reg", c["reg"], "--region", p["region"], "--name", c["name"],
                     "--code", "FL_%03d_CUP" % p["rid"], "--like", c["like"], "--bracket", c["bracket"]])
        log("  %s: competition %d, regulation %d, %d clubs (copied from %s)"
            % (c["name"], c["cid"], c["reg"], len(teams), c["like"]))
        if c.get("super"):
            cids, regs = free_comp_ids(db)
            c["super_cid"], c["super_reg"] = cids[0], regs[0]
            call(mkcup, ["--base", db, "--out", root, "--teams", ",".join(map(str, p["teams"][:2])),
                         "--cid", cids[0], "--reg", regs[0], "--region", p["region"], "--name", c["super"],
                         "--code", "FL_%03d_SUPER" % p["rid"], "--like", SUPER_CUP_LIKE, "--bracket", 2])
            log("  %s: competition %d, regulation %d (copied from %s)"
                % (c["super"], cids[0], regs[0], SUPER_CUP_LIKE))


def continental(cups, root, db, log=print, start=None):
    """build the planned continental cups (ccup_plan) with mkccup.py into the world's tables in
    <db>, with ids nothing in them uses; returns the world file's ccup lines"""
    if not cups:
        return []
    import mkccup
    cids, free = free_comp_ids(db)
    pres = [c for c in cups if (c.get("opts") or {}).get("pre")]
    if len(cids) < len(cups) or len(free) < sum(2 if c["groups"] else 1 for c in cups) + len(pres):
        raise BuildError("no free competition or regulation ids left for the continental cups")
    args = ["--base", db, "--out", root]
    rounds = []
    for cup in cups:
        cup_winners(cup, start)
    for k, cup in enumerate(cups):
        reg = free.pop(0)
        ko = free.pop(0) if cup["groups"] else reg        # a straight knockout is one regulation
        cup.update(cid=cids[k], reg=reg, ko=ko)
        ko_of = {c.get("number"): c.get("ko") for c in cups[:k]}
        cup["entry"] = [(ko_of[e[1]], 0) if e[0] == "ko" else e for e in cup["entry"]]
        if (cup.get("opts") or {}).get("pre"):         # its ties are <pre> + 1024 * (k + 1)
            cup["pre_reg"] = pre = free.pop(0)
            rounds.append((pre, cids[k], cup["name"], len(cup["opts"]["pre"]["entry"]) // 2))
            cup["entry"] = [(pre + 1024 * (e[1] + 1), 0) if e[0] == "pre" else e for e in cup["entry"]]
        args += ["--cup", "|".join(str(x) for x in (
            cup["name"], cup["code"], cids[k], reg, ko, cup["groups"],
            ",".join("%d:%d" % tuple(e) for e in cup["entry"]),
            "" if cup.get("conf") is None else cup["conf"], cup.get("region", "")))]
    if rounds:                                         # before mkccup, which wants the ties there
        import mkeuropo
        try:
            mkeuropo.prerounds(db, root, rounds, log=log)
        except SystemExit as e:
            raise BuildError("league cup pre-rounds: %s" % e)
    said = call(mkccup, args)
    lines = [l.strip() for l in said.splitlines() if l.startswith("ccup ")]
    if len(lines) != len(cups):
        raise BuildError("mkccup made %d of %d continental cups:\n%s" % (len(lines), len(cups), said))
    lines = [ccup_options(l, cup) for l, cup in zip(lines, cups)]
    lines = [l if not cup.get("alt") else ccup_alt(l, cup["alt"]) for l, cup in zip(lines, cups)]
    for cup in pres:
        pre = cup["opts"]["pre"]
        lines.append("lpre %d cup=%d fill=%d days=%s entry=%s" % (
            cup["pre_reg"], cup["ko"], pre["fill"], ",".join(map(str, pre["days"])),
            ",".join("%d:%d" % tuple(e) for e in pre["entry"])))
    for cup in cups:
        log("  %s: competition %d, %d clubs, %s" % (
            cup["name"], cup["cid"], len(cup["entry"]),
            "groups %d, knockout %d" % (cup["reg"], cup["ko"]) if cup["groups"] else "knockout %d" % cup["ko"]))
    return lines


def home_cups(pl, confed):
    """the league and pre-season cups planned, ready for continental(): the country's
    confederation, and the invited clubs' team ids now that build() has given them out"""
    teams = {p["rid"]: p["teams"] for p in pl["leagues"]}
    out = []
    for cup in pl.get("home_cups") or []:
        c = dict(cup, conf=cup["conf"] if cup.get("conf") else confed.get(cup["country"]),
                 opts=dict(cup["opts"]))
        if cup.get("refs"):
            c["opts"]["clubs"] = [r if isinstance(r, int) else teams[r[0]][r[1]] for r in cup["refs"]]
        out.append(c)
    return out


def alt_from(pl):
    """{league: the first position no competition takes}, where a cup winner's place falls back
    to (cup_winners): a new league's past its European places, a league of the game's past where
    its places in fl26world.CCUPS begin (the ones above go to the game's own cups)"""
    start = {}
    for _n, _name, _code, _conf, fill in fl26world.CCUPS:
        for r, p in fill:
            start[r] = min(start.get(r, p), p)
    for p in pl.get("leagues") or []:
        pos = [q for q, _comp in p.get("europe") or [] if q != CUP_WINNER]
        start[p["rid"]] = max(pos) + 1 if pos else 1
    return start


def cup_winners(cup, start=None):
    """a cup winner's entry ("cup", league) of a continental cup (ccup_entry) -> (the league's
    national cup's regulation, 0), the league kept in cup["alt"] as (entry index, league, the
    position to start at -- alt_from): the world file's alt=, which fl26swiss follows when the
    cup has no winner to send, from that position down so as not to take a club another
    competition takes"""
    regs = {int(r): reg for r, reg in cup.get("winners") or []}
    entry, alt = [], []
    for i, e in enumerate(cup["entry"]):
        if e[0] == "cup":
            if not regs.get(int(e[1])):
                raise BuildError("%s: the cup winner of league %s, but its country has no cup" % (cup["name"], e[1]))
            alt.append((i, int(e[1]), min((start or {}).get(int(e[1]), 1), 63)))
            e = (regs[int(e[1])], 0)
        entry.append(e)
    cup["entry"], cup["alt"] = entry, alt


def ccup_alt(line, alt):
    """a world file ccup line with its cup winners' leagues (cup_winners):
    alt=<entry>:<league>:<first position>,..."""
    head, sep, name = line.partition(" name=")
    return "%s alt=%s%s%s" % (head, ",".join("%d:%d:%d" % a for a in alt), sep, name)


def ccup_options(line, cup):
    """a world file ccup line with a domestic cup's options (fl26swiss.lua reads them): the day
    it is filled on, national (no continental rule on who may play), its days, invited clubs"""
    o = cup.get("opts")
    if not o:
        return line
    words = ["fill=%d" % o["fill"], "national=%d" % o["national"],
             "days=" + ",".join(map(str, o["days"]))]
    if o.get("clubs"):
        words.append("clubs=" + ",".join(map(str, o["clubs"])))
    head, sep, name = line.partition(" name=")
    return "%s %s%s%s" % (head, " ".join(words), sep, name)


def pictures(pl, root, base, log=print):
    """league logos, club crests and kits for the new leagues (tools/lbassets.py)"""
    import lbassets
    flags = {}
    for p in pl["leagues"] + (pl.get("others") or []):
        if not p.get("others"):              # clubs in no league: no competition, no logo
            lbassets.league_logo(root, p["cid"], p["name"], p.get("logo"))
        if p.get("flag") and p["country"] not in flags:
            flags[p["country"]] = p["flag"]
            lbassets.country_flag(root, p["country"], p["flag"])
        crests, kits = p.get("club_crests") or [], p.get("club_kits") or []
        gp = game_places(p)
        for k, tid in enumerate(p["teams"]):
            if k in gp:                      # a club of the game keeps its crest
                continue
            pic = crests[k] if k < len(crests) else None
            lbassets.club_crest(root, tid, p["abbrs"][k], pic, kits[k] if k < len(kits) else None)
        for g in gp.values():                # a new club taking a game club's place: a badge
            if isinstance(g.get("swap"), dict) and g.get("swap_id"):
                lbassets.club_crest(root, g["swap_id"], g.get("swap_abbr") or "", None)
    e = pl.get("edits") or {}
    cid_of = {}
    for rid, v in (e.get("leagues") or {}).items():
        if v.get("logo"):
            if not cid_of:
                cid_of = {r: c for r, c, _, _ in game_leagues(base)}
            if int(rid) in cid_of:
                lbassets.league_logo(root, cid_of[int(rid)], v.get("name") or "", v["logo"])
    for cid, v in (e.get("competitions") or {}).items():
        if v.get("logo"):
            lbassets.league_logo(root, int(cid), v.get("name") or "", v["logo"])
    for tid, v in (e.get("clubs") or {}).items():
        if v.get("crest"):
            lbassets.club_crest(root, int(tid), "", v["crest"])
    cups = cup_emblems(pl)
    for cid, name, logo in cups:
        lbassets.league_logo(root, cid, name, logo)
    log("  %d league logos, %d cup logos, %d club crests%s" % (
        len(pl["leagues"]), len(cups), sum(len(p["teams"]) - len(game_places(p))
                                           for p in pl["leagues"] + (pl.get("others") or [])),
        ", %d country flags" % len(flags) if flags else ""))
    if not any(p["teams"] for p in pl["leagues"] + (pl.get("others") or [])):
        return
    plain = bool(pl.get("editable_kits"))
    t = tables_root(base)
    unipar = os.path.join(t, UNIPAR.replace("/", os.sep)) if t else None
    if not unipar or not os.path.exists(unipar):
        log("  no kits: the game's UniformParameter.bin was not unpacked (Unpack from game)")
        return
    import mkkits
    ours = []                       # the clubs this Build made: their ids depend on the database (#54)
    for p in pl["leagues"] + (pl.get("others") or []):
        gp = game_places(p)
        ours += [tid for k, tid in enumerate(p["teams"]) if k not in gp]
        ours += [g["swap_id"] for g in gp.values() if isinstance(g.get("swap"), dict) and g.get("swap_id")]
    if not ours:
        return
    args = ["mkkits.py", "--team-bin", os.path.join(root, "common", "etc", "pesdb", "Team.bin"),
            "--unipar", unipar, "--root", root, "--archive", "--clubs", ",".join(map(str, ours))]
    if plain:
        # editable_kits: no licensed kit lent; each club gets plain 1st/2nd/GK definitions of its
        # own, the kind Edit > Teams > Strip paints (Paste Image too).  Without them a club wore
        # team 0's fallback and Paste Image did not stick (GitHub #112)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mkkits.build(args + ["--plain"])
        if rc:
            raise BuildError("kits: %s" % buf.getvalue())
        log("  kits: plain, editable in Edit > Teams > Strip -- " + next(
            (l.strip() for l in buf.getvalue().splitlines() if l.startswith("wrote") and "kit" in l), "written"))
        return
    colours = {}                    # NewLife clubs: the shipped kit nearest their own colours
    for p in pl["leagues"] + (pl.get("others") or []):
        home, away = p.get("club_kits") or [], p.get("club_away_kits") or []
        for k, tid in enumerate(p["teams"]):
            if k < len(home) and home[k]:
                colours[tid] = [home[k], away[k] if k < len(away) else ""]
    if colours:
        cj = os.path.join(root, "kit-colours.json.tmp")
        json.dump(colours, open(cj, "w", encoding="utf-8"))
        args += ["--colours", cj]
    if os.path.exists(os.path.join(t, KIT_TEXTURES)):
        args += ["--textures", os.path.join(t, KIT_TEXTURES)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mkkits.build(args)
    if colours:
        os.remove(cj)
    if rc:
        raise BuildError("kits: %s" % buf.getvalue())
    log("  kits: " + next((l.strip() for l in buf.getvalue().splitlines() if l.startswith("wrote") and "kit" in l), "written"))


def cup_emblems(pl):
    """[(competition id, name, picture or None)] of the cups the world gets: national and super
    cups, league, play-off and pre-season cups, the continental ones, and the Conference League
    (the game has no emblem for 174 -- a cup without one shows a blank in Select Team and the
    fixtures, issue #36). The label of a drawn one is the initials of its name."""
    out = []
    for p in pl["leagues"]:
        c = p.get("own_cup") or {}
        if c.get("cid"):
            out.append((c["cid"], c["name"], c.get("logo")))
        if c.get("super_cid"):
            out.append((c["super_cid"], c["super"], c.get("super_logo")))
    for c in (pl.get("ccups") or []) + (pl.get("home_cups") or []):
        if c.get("cid"):
            out.append((c["cid"], c["name"], c.get("logo")))
    if pl.get("uecl"):
        out.append((UECL_CID, "UECL", pl.get("uecl_logo")))
    return out


def region_modules(pl, root, game, log=print):
    """fl26regions.lua and fl26regnames.lua for this world, into <world>/modules/.

    Both patch the exe with tables that name competitions and regions, so they are made per
    world (tools/mkregioncats.py, tools/mkregnames.py) and switch_on() puts them in place: the
    new leagues get their heading in the competition list, a new country a region heading of
    its own instead of the previous country's -- its own flag, drawn into the world's copy of
    the category menu by tools/mkcatflags.py. Each generator checks every byte it will
    change against the game's own exe first, so a different exe gives no module, not a bad one.
    """
    comps = sorted({p["cid"] for p in pl["leagues"]})
    if not comps:
        return
    exe = os.path.join(game, "FL_2026.exe")
    if not os.path.exists(exe):
        log("  no region headings: no %s" % exe)
        return
    import flpaths
    flpaths.EXE = exe
    d = os.path.join(root, "modules")
    os.makedirs(d, exist_ok=True)
    import mkregioncats, mkregnames, mkcatflags
    try:
        # the flag of each new country as its heading picture; mkregnames then points the
        # region at it (a country with no flag picture gets the plain international flag)
        call(mkcatflags, ["--root", root, "--game", game])
    except BuildError as e:
        log("  no flag headings: %s" % str(e).strip().splitlines()[0])
    try:
        call(mkregioncats, ["--root", root, "--comps", ",".join(map(str, comps)),
                            "--out", os.path.join(d, "fl26regions.lua"), "--write"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mkregnames.main(["--root", root, "--out", os.path.join(d, "fl26regnames.lua")])
        if rc:
            raise BuildError("mkregnames returned %s: %s" % (rc, buf.getvalue()))
    except (BuildError, SystemExit) as e:
        log("  no region headings: %s" % str(e).strip().splitlines()[0])
        return
    log("  region headings for %d leagues" % len(comps))


# ---- install: the modules that read a world ----

def pack_dir():
    """the module pack (tools/lbpack.py): next to the program, inside it, or the repo's build"""
    for d in (os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "pack"),
              os.path.join(getattr(sys, "_MEIPASS", HERE), "pack"),
              os.path.join(os.path.dirname(HERE), "out", "lbpack")):
        if os.path.exists(os.path.join(d, "modules.txt")):
            return d
    raise BuildError("the module pack is missing (a folder called pack next to the program)")


def ini_lines(game):
    ini = os.path.join(siderdir.find(game), "sider.ini")
    if not os.path.exists(ini):
        raise BuildError("no %s -- is Sider installed in this game folder?" % ini)
    return ini, open(ini, encoding="utf-8", errors="replace").read().splitlines()


def module_of(line):
    """the module a lua.module line names, commented out or not, and whether it is live"""
    s = line.strip()
    live = not s.startswith((";", "#"))
    s = s.lstrip(";#").strip()
    if not s.startswith("lua.module"):
        return None, False
    name = s.split("=", 1)[1].split(";")[0].strip().strip('"').lower()
    return (name[:-4] if name.endswith(".lua") else name), live


# Modules of ours a player may switch off for good (Gu, 2026-10-07: "can the regen system be
# disabled completely?"). Unticking one on the Lua modules page lists it in modulesl26-off.txt,
# and Build / Install / switching worlds then leave its line switched off instead of turning it
# back on as they do every other module of the pack.
OPTIONAL_MODULES = ("fl26regen",)
OFF_FILE = "fl26-off.txt"


def modules_off(mdir):
    """the optional modules the player switched off (OFF_FILE in the modules folder `mdir`)"""
    try:
        with open(os.path.join(mdir, OFF_FILE), encoding="utf-8") as f:
            return {l.strip() for l in f if l.strip() in OPTIONAL_MODULES}
    except OSError:
        return set()


def set_modules_off(mdir, off):
    """write OFF_FILE: the optional modules in `off` stay off; none left removes the file"""
    path = os.path.join(mdir, OFF_FILE)
    off = sorted(m for m in set(off) if m in OPTIONAL_MODULES)
    if off:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# switched off on the Lua modules page; Build leaves them off\n" + "\n".join(off) + "\n")
    elif os.path.exists(path):
        os.remove(path)


def retired_modules():
    """{old module: the bundle that replaced it} (the pack's retired.txt, lbpack.BUNDLES)"""
    try:
        with open(os.path.join(pack_dir(), "retired.txt"), encoding="utf-8") as f:
            return dict(l.split()[:2] for l in f if len(l.split()) >= 2)
    except (OSError, BuildError):
        return {}


def ensure_modules(game, order, want, log=print):
    """make every module in `want` a live lua.module line of sider.ini, in `order`'s order.

    A commented-out line is switched back on where it is; a missing one goes in after the
    nearest module before it in `order` that the file already loads (or before the first after
    it). Nothing else in the file moves. Returns the modules it touched.

    A line that loads one of these modules out of a before-builder-<n> folder -- the copies
    install_modules keeps of what it replaced -- is pointed back at the module itself: the
    old copy is out of date, and its Lua looks for its DLL in modules, not next to itself
    (evo-web, 2026-09-29: every fl26 line read before-builder-1/..., LoadLibraryA failed
    with error 126 for all four DLLs, and the diagnostics said none of them was loaded)."""
    off = modules_off(os.path.join(siderdir.find(game), "modules"))
    if off & set(want):
        log("sider.ini: left off as you switched them off: %s" % ", ".join(sorted(off & set(want))))
    want = [m for m in want if m not in off]
    ini, lines = ini_lines(game)
    # a module 0.2.0 bundled (fl26nullguard ... -> fl26guards): its own line goes off, or the
    # fix would be applied twice and the second time refuse the already patched bytes
    # only when the bundle is loaded too: Switch on hands in the world's modules alone, and turned
    # the guards off with no fl26guards line in the file (07.10., the modpack world)
    retired, gone = retired_modules(), []
    have = set(want) | {module_of(l)[0].replace("/", "\\").rpartition("\\")[2]
                        for l in lines if module_of(l)[0] and module_of(l)[1]}
    for i, l in enumerate(lines):
        m, live = module_of(l)
        base = m.replace("/", "\\").rpartition("\\")[2] if m else None
        if live and base in retired and retired[base] in have:
            lines[i] = ";" + l.strip()
            gone.append(m)
    fixed, plain = [], {module_of(l)[0] for l in lines}
    for i, l in enumerate(lines):
        m, live = module_of(l)
        if not m or "\\" not in m.replace("/", "\\"):
            continue
        folder, _, base = m.replace("/", "\\").rpartition("\\")
        if base in order and folder.split("\\")[-1].startswith("before-builder"):
            # the module's own line already there: the old copy's line is only switched off
            lines[i] = ('' if live and base not in plain else ';') + 'lua.module = "%s.lua"' % base
            plain.add(base)
            fixed.append(base)
    where = {}
    for i, l in enumerate(lines):
        m, live = module_of(l)
        if m and (m not in where or live):
            where[m] = (i, live)
    done = []
    for m in [x for x in order if x in want]:
        if m in where and where[m][1]:
            continue
        if m in where:
            lines[where[m][0]] = 'lua.module = "%s.lua"' % m
        else:
            k = order.index(m)
            before = [where[x][0] for x in order[:k] if x in where and where[x][1]]
            after = [where[x][0] for x in order[k + 1:] if x in where and where[x][1]]
            if before:
                at = max(before) + 1
            elif after:
                at = min(after)
            else:
                mods = [i for i, l in enumerate(lines) if module_of(l)[0]]
                at = (mods[0] if mods else len(lines))
            lines.insert(at, 'lua.module = "%s.lua"' % m)
            where = {x: ((i + 1 if i >= at else i), lv) for x, (i, lv) in where.items()}
        where[m] = (lines.index('lua.module = "%s.lua"' % m), True)
        done.append(m)
    ext = [i for i, l in enumerate(lines) if l.strip().lstrip(";#").strip().startswith("luajit.ext.enabled")]
    if not ext or lines[ext[0]].replace(" ", "") != "luajit.ext.enabled=1":
        if ext:
            lines[ext[0]] = "luajit.ext.enabled = 1"
        else:
            on = [i for i, l in enumerate(lines) if l.replace(" ", "").startswith("lua.enabled=")]
            lines.insert(on[0] + 1 if on else len(lines), "luajit.ext.enabled = 1")
        done.append("luajit.ext.enabled")
    if gone:
        log("sider.ini: switched off %s -- %s has them now" % (", ".join(gone), ", ".join(
            sorted({retired[g.replace("/", "\\").rpartition("\\")[2]] for g in gone}))))
    if fixed:
        log("sider.ini: %d module(s) were loaded from a before-builder folder, now from modules: %s"
            % (len(fixed), ", ".join(fixed)))
        done += [m for m in fixed if m not in done]
    if done or gone:
        shutil.copy2(ini, ini + ".before-builder") if not os.path.exists(ini + ".before-builder") else None
        open(ini, "w", encoding="utf-8", newline="\r\n").write("\n".join(lines) + "\n")
        if done:
            log("sider.ini: switched on %s" % ", ".join(done))
    return done + gone


def install_modules(game, log=print):
    """put the pack's modules in the Sider folder's modules and load them from sider.ini.

    Every file it would replace is copied first into modules\\before-builder-<n>\\, and
    sider.ini into sider.ini.before-builder, so the install can be undone by hand."""
    pack = pack_dir()
    order = open(os.path.join(pack, "modules.txt"), encoding="utf-8").read().split()
    ini, _ = ini_lines(game)
    dst = os.path.join(siderdir.find(game), "modules")
    if not os.path.isdir(dst):
        raise BuildError("no %s -- is Sider installed in this game folder?" % dst)
    src = os.path.join(pack, "modules")
    changed, same, keep = [], 0, None
    for f in sorted(os.listdir(src)):
        a, b = os.path.join(src, f), os.path.join(dst, f)
        if os.path.exists(b) and open(a, "rb").read() == open(b, "rb").read():
            same += 1
            continue
        changed.append(f)
    if changed:
        for f in changed:
            b = os.path.join(dst, f)
            if os.path.exists(b):
                if not keep:
                    n = 1
                    while os.path.exists(os.path.join(dst, "before-builder-%d" % n)):
                        n += 1
                    keep = os.path.join(dst, "before-builder-%d" % n)
                    os.makedirs(keep)
                shutil.copy2(b, os.path.join(keep, f))
            shutil.copy2(os.path.join(src, f), b)
        log("modules: %d copied, %d already there%s" % (len(changed), same,
            ("; the old ones are in " + keep) if keep else ""))
    else:
        log("modules: all %d already there" % same)
    old = [m for m in retired_modules() if os.path.exists(os.path.join(dst, m + ".lua"))]
    if old:
        # the single files a bundle replaced go with the other old copies
        n = 1
        while os.path.exists(os.path.join(dst, "before-builder-%d" % n)):
            n += 1
        keep = keep or os.path.join(dst, "before-builder-%d" % n)
        os.makedirs(keep, exist_ok=True)
        for m in old:
            shutil.move(os.path.join(dst, m + ".lua"), os.path.join(keep, m + ".lua"))
        log("modules: %s now ship bundled; the single files are in %s" % (", ".join(old), keep))
    have = {f[:-4] for f in os.listdir(dst) if f.endswith(".lua")}
    ensure_modules(game, order, [m for m in order if m in have], log)
    roots = os.path.join(pack, "livecpk")
    for r in sorted(os.listdir(roots)) if os.path.isdir(roots) else []:
        install_root(game, os.path.join(roots, r), log)
    return changed


def install_root(game, src, log=print):
    """a livecpk root of the pack (the regen portraits): copied into the Sider folder's livecpk,
    replacing an older copy, and loaded by a cpk.root line of its own. The line goes above the
    first cpk.root there is; its name has no _FL26, so switching worlds (siderroot) leaves it."""
    name = os.path.basename(src)
    dst = os.path.join(siderdir.find(game), "livecpk", name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    n = sum(len(fs) for _, _, fs in os.walk(dst))
    ini, lines = ini_lines(game)
    want = r'cpk.root = ".\livecpk\%s"' % name
    key = lambda l: l.strip().lstrip(";#").strip().replace(" ", "").lower()
    at = [i for i, l in enumerate(lines) if key(l) == key(want)]
    if at and lines[at[0]].strip() == want:
        log("livecpk: %s (%d files), already loaded" % (name, n))
        return
    if at:
        lines[at[0]] = want
    else:
        roots = [i for i, l in enumerate(lines) if l.strip().startswith("cpk.root")]
        mods = [i for i, l in enumerate(lines) if module_of(l)[0]]
        lines.insert(roots[0] if roots else (mods[0] if mods else len(lines)), want)
    shutil.copy2(ini, ini + ".before-builder") if not os.path.exists(ini + ".before-builder") else None
    open(ini, "w", encoding="utf-8", newline="\r\n").write("\n".join(lines) + "\n")
    log("livecpk: %s (%d files), sider.ini loads it" % (name, n))


# ---- on: the live world ----

def switch_on(world, game, log=print):
    root = os.path.join(siderdir.find(game), "livecpk", world)
    wf = os.path.join(root, MARK)
    if not os.path.exists(wf):
        raise BuildError("%s has no %s -- not a league builder world" % (root, MARK))
    import siderroot
    siderroot.INI = os.path.join(siderdir.find(game), "sider.ini")
    if not os.path.exists(siderroot.INI):
        raise BuildError("no %s -- is Sider installed in this game folder?" % siderroot.INI)
    log(call(siderroot, [world]).strip())
    dst = os.path.join(siderdir.find(game), "modules", MARK)
    if os.path.exists(dst):
        shutil.copy2(dst, dst + ".prev")
    shutil.copy2(wf, dst)
    log("world file -> %s" % dst)
    try:                                               # Edit club > Home stadium (Stadium Server)
        with open(os.path.join(root, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            built = json.load(f)
    except (OSError, ValueError):
        built = None
    if built is not None:
        import lbstadiums
        lbstadiums.write(built, siderdir.find(game), log)
    mods = os.path.join(root, "modules")
    for f in sorted(os.listdir(mods)) if os.path.isdir(mods) else []:
        dst = os.path.join(siderdir.find(game), "modules", f)
        if os.path.exists(dst) and not os.path.exists(dst + ".before-builder"):
            shutil.copy2(dst, dst + ".before-builder")
        shutil.copy2(os.path.join(mods, f), dst)
        log("%s -> %s" % (f, dst))
    if os.path.isdir(mods):
        import lbpack
        ensure_modules(game, lbpack.ORDER, [f[:-4] for f in os.listdir(mods) if f.endswith(".lua")], log)
    commonlib_leagues(game, world, wf, log)
    missing = modules_missing(game)
    if missing:
        log("NOTE: sider.ini does not load %s -- those parts of the world will not work"
            % ", ".join(missing))


COMMONLIB_TAG = "-- FL26 world"


def commonlib_leagues(game, world, wf, log=print):
    """the world's leagues into lib\\CommonLib.lua's playable league list. Scoreboard, menu and
    ball servers pick a Kick Off match's competition only when both clubs are of one league on
    that list, and it knows the game's leagues alone: a Kick Off between two clubs of a new league
    got the exhibition scoreboard and menu (in game, 07.10.). One line of ours, replaced on every
    Switch on; nothing else in the file is touched."""
    path = os.path.join(siderdir.find(game), "modules", "lib", "CommonLib.lua")
    if not os.path.exists(path):
        return
    try:
        cids = sorted({int(L["cid"]) for L in fl26world.read_world(wf)[1] if L.get("cid")})
    except Exception as e:                       # an old world file: leave the list as it is
        log("CommonLib: world file not read (%s), playable list left as it is" % e)
        return
    text = open(path, encoding="utf-8", errors="replace", newline="").read()
    m = re.search(r"local\s+playable_league_comp_ids\s*=\s*\{(.*?)\n(\s*)\}", text, re.S)
    if not m:
        log("CommonLib: no playable_league_comp_ids list found, left as it is")
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    body = [l for l in m.group(1).split("\n") if COMMONLIB_TAG not in l]
    if cids:
        body.append("                             %s, %s %s (Mod Studio, Switch on)%s"
                    % (", ".join(map(str, cids)), COMMONLIB_TAG, world, "\r" if nl == "\r\n" else ""))
    new = text[:m.start(1)] + "\n".join(body) + text[m.end(1):]
    if new != text:
        if not os.path.exists(path + ".before-builder"):
            shutil.copy2(path, path + ".before-builder")
        open(path, "w", encoding="utf-8", newline="").write(new)
    log("CommonLib: %d league(s) of %s in the Kick Off league list" % (len(cids), world))


def modules_missing(game):
    ini = open(os.path.join(siderdir.find(game), "sider.ini"), encoding="utf-8-sig", errors="replace").read()
    # a line may carry a comment after the value, no quotes, or a folder (GitHub #65: every
    # module reported missing while sider.log showed them all loaded)
    live = set()
    for l in ini.splitlines():
        m = re.match(r'\s*lua\.module\s*=\s*"([^"]*)"|\s*lua\.module\s*=\s*([^\s;#]+)', l)
        if m:
            live.add(os.path.basename((m.group(1) or m.group(2)).replace("\\", "/")).lower())
    return [m for m in READERS if m + ".lua" not in live]


# ---- check: did the modules take the world file? ----

def check(game, log=print):
    path = os.path.join(siderdir.find(game), "sider.log")
    wf = os.path.join(siderdir.find(game), "modules", MARK)
    want = len(fl26world.read_world(wf)[1]) if os.path.exists(wf) else None
    if not os.path.exists(path):
        raise BuildError("no %s yet -- start the game once with the world switched on" % path)
    if os.path.exists(wf) and os.path.getmtime(path) < os.path.getmtime(wf):
        # the log is of a game started before the world was switched on (GitHub #94: every
        # module "not loaded" right after Build)
        log("  sider.log is older than the world switched on -- start the game to the main menu, then check again")
        return False
    text = open(path, encoding="utf-8", errors="replace").read().splitlines()
    ok = True
    # a module that refused the game's exe (GitHub #62: fl26caps ABORTED on another exe while the
    # rest added the leagues, and the check said all was well)
    for l in text:
        m = re.match(r"^\[([\w.-]+)\.lua\] .*\bABORTED\b", l)
        if m:
            log("  %-14s refused the game's exe: %s" % (m.group(1), l.split("] ", 1)[-1].strip()))
            ok = False
    for m in READERS:
        mine = [l for l in text if l.startswith("[%s.lua]" % m)]
        took = [l for l in mine if "world file --" in l]
        # the line with the league count: fl26swiss writes its qualifying rounds' line first
        # (Discord, Risto: "6 qualifying round(s) ... <- the file has 39")
        took = [l for l in took if re.search(r"world file -- \d+ leagues?\b", l)] or took
        bad = [l for l in mine if any(w in l for w in ("aborting", "nothing written", "FAILED", "left alone"))]
        if not mine:
            log("  %-14s not loaded" % m)
            ok = False
        elif not took:
            log("  %-14s did NOT read the world file" % m)
            ok = False
        else:
            n = took[0].split("world file --", 1)[1].split()[0]
            same = want is None or n == str(want)
            log("  %-14s %s%s" % (m, took[0].split("world file --", 1)[1].strip(),
                                  "" if same else "   <- the file has %s" % want))
            ok = ok and same
        for l in bad:
            log("      " + l.split("] ", 1)[-1])
    log("the world works as built" if ok else "something is wrong -- see the lines above")
    return ok


def main():
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    if not a or a[0] not in ("plan", "build", "on", "check"):
        print(__doc__)
        return 1
    game = get("--game") or GAME
    try:
        if a[0] == "check":
            return 0 if check(game) else 2
        if a[0] == "on":
            switch_on(a[1], game)
            return 0
        base = base_dir(get("--base"))
        pl = plan(load_recipe(a[1]), base)
        print(describe(pl))
        if a[0] == "build":
            build(pl, base, game, "--replace" in a)
        return 0
    except BuildError as e:
        print("error: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
