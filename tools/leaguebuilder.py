r"""python leaguebuilder.py plan  <recipe.json> [--base <pesdb dir>]
   python leaguebuilder.py build <recipe.json> [--base <pesdb dir>] [--game <dir>] [--replace]
   python leaguebuilder.py on    <world name> [--game <dir>]
   python leaguebuilder.py check [--game <dir>]

The league builder's core: one recipe in, one finished world out. The window (stage C,
docs/developers/mod-studio.md) calls these same functions; this command line is for tests.

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
  real_calendar  optional (0.2.0): the league's own season dates, {"first": "07-25", "last":
              "05-23", "break": ["12-21", "01-22"] or null, "days": "sat sun", "also": "fri"}
              (month-day, weekday names), or false for the old calendar; without it the
              country's real calendar (tools/realcal.py COUNTRY, by tier), else its
              confederation's. fl26swiss.dll dates the rounds from it (the world's rcal line)
  league_cup  optional, a top division of a new country only: true gives the country a league
              cup (0.2.0, league_ko_cup): the top division and the one below it, as many clubs
              as the bracket screen draws up to 44 (BRACKET_SIZES), one match a round on a copy
              of the FA Cup's shape (LEAGUE_KO_LIKE) -- byes where the field is not a power of
              two go to the top division, every tie drawn at random (cupdraw byes) -- played
              late August to mid-March on the Carabao Cup's weeks (LEAGUE_KO_DAYS; a
              calendar-year league's September to December), the semi-final and the final
              one match too. fl26swiss.dll fills and dates it (the ccup line's
              options, like= and draw=); "league_cup_name", "league_cup_logo"
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
              either Build picks the formation the club's squad fits best (0.2.4,
              lbplayers.pick_formation); a club whose squad order the recipe sets keeps the
              engine's fixed 4-2-3-1 (lbplayers.LINEUP)
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
  game_europe (the recipe, not a league) the continental places of leagues of the game, in place of
              the shipped ones: {"<regulation id of a top division of the game>": [[position,
              competition], ...]}, competitions as europe above plus, with "conmebol" below, the
              modern CONMEBOL ones: 16 Libertadores phase 1, 17 phase 2 and 19 Sudamericana first
              stage (18, phase 3, is filled by the eight phase-2 winners, never by a league)
  conmebol    (the recipe, not a league) "modern": the modern CONMEBOL competitions (PR #146,
              vmardonesdev): Libertadores qualifying in three phases, a Copa Sudamericana of 32
              group clubs with a first stage and a play-off, and the Recopa Sudamericana. Mod
              Studio: South American places > Modern CONMEBOL competitions. Places in phase 1,
              phase 2 or the Sudamericana's first stage, or conmebol_associations, also mean it.
              Left out, a world keeps the classic Libertadores (its places 3 and 4) and Copa
              Sudamericana (9) exactly as worlds before 0.2.5 had them, even with such places.
              With it the game's South American leagues lose their shipped Libertadores places
              unless game_europe gives them their own, and Build wants the whole field: 26
              Libertadores group places, 13 phase 2, 6 phase 1, 12 Sudamericana group places and
              32 first stage, spread over the South American leagues however you like
  sudamericana_calendar (the recipe, not a league) true: the classic Copa Sudamericana (without
              "conmebol") plays February to December on the Libertadores' days, filled in February
              from the same tables as the Libertadores (other places of them), instead of August
              to May
  conmebol_associations (the recipe, not a league) dynamic places for a CONMEBOL association,
              still in the normal two-field schema: {"Bolivia": [[1,3],[2,3],[3,17],[4,16],
              [5,19],...]}. The first number is an association rank, never a team id. If this world
              has that country's top division, the ranks resolve through its table; otherwise
              fl26swiss ranks the country's real Other Latin American clubs at runtime. Missing
              ranks stay unresolved and never take another association's berth
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
              the cup winner, one match -- only where the game has none (Brazil, Chile, Scotland,
              Greece, the USA): the same two-club copy of SUPER_CUP_LIKE a new league's super
              cup is (game_super_cups), which the game fills itself; dated as SUPER_CUP_LIKE
              (July), in a February-December country at the end of January after the season
              (CALENDAR_SUPER_DATE_LIKE), where the world file's gsuper line puts it into the
              New Year season (fl26joindll) and has the champion and the cup winner of the
              season just ended fill it (fl26swiss). 0.2.3 built it on the FA Cup's row, and
              the game filled that with every club of the country (Vicentico 13.10.)
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
  samerica_super_cup  (the recipe, not a league) true, the default: a world that builds
              the modern Copa Sudamericana also gets the Recopa Sudamericana, one match in late
              February between the previous Libertadores and Sudamericana winners. Both winners
              are retained at the calendar-year rollover by fl26swiss.dll. A new career has no
              previous-season winners, so its first Recopa is normally left unplayed; optional
              "samerica_super_cup_first": [libertadores_team_id, sudamericana_team_id] supplies
              those two clubs without hard-coding them in the builder. false: no Recopa.
              "samerica_super_cup_logo" is its picture
  make_kits   (the recipe) false: no kit is made. Otherwise, with Kit Server installed, every new
              club without a Kit Server folder of its own gets a kit made when the world is switched
              on (lbservers, kitmaker): home, away, third and goalkeeper in its shirt colours
              (club_kits / club_away_kits, NewLife's), or its crest's, with its crest on the chest.
  replaced_kits  (the recipe) false: a club of the game whose place the world gave another club
              (NewLife's "Bring the game's leagues to this season") gets no kit made in the new
              club's colours; the game's kit, or a kit pack's line for its id, stays (B176).
  pack_faces  (the recipe) false: the world's new players get no face of the regen face pack (no
              newfaces lines), so the look the game gives them, or one set in the game's Edit mode,
              stays (Jabo9, 11.10.: Edit-mode looks covered by pack faces in Master League).
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
                   region from 29 up that nothing uses (sider/fl26reg128.lua reads 29..127)
  tier             1, or the parent's plus one
  split phases     mksplit's ids from 191 up (the range split seasons were tested on)

build() writes the world folder: Team/Coach/Competition* tables (mkleague.add_league, as
mkworld does), squads (mkplayers.py), splits (mksplit.py), the Conference League (above), and
fl26world.txt in the folder -- the world file every module reads, with the uefa lines of the
leagues' European places. on() makes it the live world: the one active _FL26
cpk.root in sider.ini (siderroot.py) and the world file copied to modules\. check() reads
sider.log after a start and says, module by module, whether the world file was taken.
"""
import contextlib, copy, glob, io, json, os, re, shutil, struct, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import mkleague as M
import mkworld as W
import mkcoaches
import mkuecl
import fl26world
import siderdir
import flpaths

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
REGION_FIRST, REGION_LAST = 29, M.REGION_MAX
CID_FROM = 130
SQUAD, PLAYER_CAP = 30, 61905            # a new club's squad, and the player records of the lim2400 layout
SQUAD_FIT = 22                           # only a world with more new clubs than 30 each leave room for takes
                                         # fewer, down to this (0.2.2/0.2.3 gave every world 22: not agreed, 14.10.2026)
TEAM_CAP = 2400                          # clubs in all, shipped ones included (1536 up to 0.2.1)
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

# Calendar-year domestic cups. The English cup carries all seven case-6 knockout
# round ids needed by fields up to NATIONAL_CUP_MAX. Give those records explicit
# March-November dates: its last two round ids share the same shipped dates.
# The super cup gets its two records at the end of January.
CALENDAR_CUP_DATE_LIKE = "ENGLAND_D1_CUP"
CALENDAR_CUP_DATE_DAYS = (65, 107, 149, 191, 233, 275, 317)
CALENDAR_SUPER_DATE_LIKE = "JAPAN_SUPER_CUP"
CALENDAR_SUPER_DATE_DAYS = (30,)
LIBQ_ROOM = 6                             # Libertadores qualifying: 8 places, fl26swiss keeps 2 of the game's
# Modern CONMEBOL Libertadores qualifying.
# F1: 6 clubs -> 3 winners
# F2: 13 domestic clubs + 3 F1 winners -> 8 winners
# F3: the game's native Libertadores qualifying regulation 8 -> 4 winners.
LIBQ_NAME, LIBQ_CODE = "Pre-Libertadores", "FL_LIBQ"
GAME_LIBERTADORES = 5          # the game's Copa Libertadores (Competition.bin): its emblem is emb_0005
LIBQ_P1 = {"fill": 2, "days": [6, 13]}
# B227 (antonimus, 24.10.): phase 2 was on 20 and 27, two of the days the exe ships for Copa Chile and
# Copa do Brasil (16 20 23 27 31 37 44 ..., cupdays_lines), so a Chilean club in it had both on one day.
# 18 and 25 are two days from each of them; 6 and 13 come before the cups start.
LIBQ_P2 = {"fill": 14, "days": [18, 25]}
LIB_QUAL = 8
LIB_ROOM = 8                              # Libertadores group stage: the pool clubs (73) ours replace, 8 (GitHub #127)
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
# (QR_DAYS) and the play-offs (reg 2's moved to 241/248, the Europa/Conference League's 49/56);
# the Champions League's knockouts on Wednesdays since 0.2.0 (69 ..., its play-off 48/55).
# fl26swiss also moves any round of ours still on one of these days (declash), so this only
# steers the choice of id.
_SWISS = [257, 258, 271, 272, 292, 293, 306, 307, 327, 328, 341, 342, 19, 20, 26, 27]
EURO_DAYS = (set(_SWISS)
             | {272, 273, 293, 294, 307, 308, 328, 329, 342, 343, 349, 350}
             | {69, 76, 97, 104, 118, 125, 149, 70, 77, 98, 105, 119, 126, 139, 146}
             | {242, 247, 229, 236, 220, 225, 241, 248, 48, 55, 49, 56})
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
SUDAM = 9                                # fl26world.CCUPS number of Copa Sudamericana
# the national first stage: 40, not 44 -- 44 is a Copa Chile / Copa do Brasil day too (B227); 40 is three
# days from 37 and four from 44, and not the Libertadores phase 3 day 41
SAM_FIRST_FILL, SAM_FIRST_DAY = 36, 40
SAM_GROUP_FILL = 49                      # draw groups just after the national first stage
SAM_FIRST_TIES = 16                      # 32 clubs -> 16 national one-match ties
SAM_FIRST_NAME, SAM_FIRST_CODE = "Copa Sudamericana", "FL_SUDA1"
SAM_LIB_LOSERS = 4
LIB_QUAL, QUAL_LOSER = 8, 255
LIBERTADORES_KO = 10                      # native Libertadores final/knockout regulation
SAM_SUPER_FILL = 42                       # fill after both previous-year winners are retained
SAM_SUPER_DAYS = (49, 50, 51, 52, 53, 54, 55)  # field of two uses the last: 24 February
# Modern Sudamericana post-group play-off: 8 group runners-up v 8 Libertadores
# group thirds, two legs. Its eight winners join the eight Suda group winners
# in the round of 16.
SPO_NAME, SPO_CODE = "Copa Sudamericana", "FL_SUDAPO"
SPO_FILL, SPO_DAYS = 140, (146, 153)
LIB_GROUPS = 9
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
# The league cup since 0.2.0: one match a round, the way the Carabao Cup, the Taca da Liga and the
# J.League Cup are played, instead of the two-legged knockout of 16 with its pre-round above
# (cup_field, kept for the ids: league_ko_cup). The knockout row is a copy of the FA Cup's
# (ENGLAND_D1_CUP, reg 23: format 2, a single match a round, the bracket = the field), whose
# calendar (exe case 6) dates every round of a field of 9 to 64 -- round ids 0x2e, 0x2f, 0x30
# and the quarter-final 0x33, 0x34, 0x35; fl26swiss moves them to LEAGUE_KO_DAYS, one day a
# round, the last the final. The field is the top division and the one below it, top first, cut
# to the largest size the bracket screen draws (BRACKET_SIZES, 44 above 32: Premier League +
# Championship); where it is not a power of two the game lets the first places through to the
# second round and the cup draw (`draw=byes`) gives those to the top division and draws every
# tie at random. The days are midweek (Tuesday d % 7 == 5, Wednesday 6 on the big leagues'
# grid), at least three days from every European day (EURO_DAYS) and national cup day
# (calendar case 6: 251/254, 286/289), after the fill day and inside September to December, so
# a calendar-year season holds them as well as an August-May one.
LEAGUE_KO_LIKE = 23
LEAGUE_KO_CAL_DAYS = [265, 279, 300, 321, 335, 356]
# 0.2.0: an August-May league's cup on the Carabao Cup's real weeks, one day a round (the first
# rounds a smaller field skips): 27 August, 23 September, 28 October, the quarter-final 23
# December, the semi-final 14 January, the final Sunday 15 March -- midweek clear of the European
# days by two days or more and of the national cups' by three, filled on 15 August. A
# calendar-year league's cup (the J.League's) keeps LEAGUE_KO_CAL_DAYS, inside its season.
LEAGUE_KO_DAYS = [238, 265, 300, 356, 13, 73]
LEAGUE_KO_FILL = 226
LEAGUE_KO_SIZES = sorted(s for s in BRACKET_SIZES | {NATIONAL_CUP_MAX} if s >= 4)
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
# them on the Wednesdays of the same weeks (#70). Since B35 (0.2.4) three tables -- a cup whose
# leagues reach the game's Libertadores or AFC Champions League plays in the weeks that one
# leaves free -- and the league here does not say which, so all three
CCUP_DAYS = sorted({327, 334, 26, 33, 40, 47, 75, 82, 96, 103, 117, 124, 138,          # CR_NONE
                    328, 335, 27, 34, 41, 48, 76, 83, 97, 104, 118, 125, 139,
                    19, 54, 68, 89, 110, 131, 145,                                    # CR_LIB
                    20, 55, 69, 90, 111, 132, 146,
                    12, 13})                                                          # CR_AFC
PLAYOFF_SIZES = (8, 4)
SHARED_SLOT_REG = 49                     # shares Select Team slot 49 with the Copa Libertadores (177)
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
# the game takes a club as the same club when its id & 0x23fff is (0x1414bdb20: bits 14-16 dropped),
# and the lists of 0x1412659c0 keep only the first of two such: the builder's 71580 was Nam Dinh's
# 6044, 71587 Brunei's 6051 (B63, Nissin 16.10.).  The game's own ids never meet so; a new club's
# id steps round the ones that would (ID_MASK_CLASH), an id it had at an earlier Build stays
ID_MASK = 0x23fff


def id_mask_clash(have):
    """the ids of the new-club block whose id & ID_MASK is a game club's: a new club never gets one"""
    seen = {t & ID_MASK for t in have}
    return {t for t in range(max(have) + 1 if have else 1, CLUB_ID_MAX + 1) if t & ID_MASK in seen}
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


class PlanProblems(BuildError):
    """every problem plan() found, at once (jibibi, vmican 19.10.: Build stopped at the first one,
    and the next came only after it was put right): problems is [(text, where)], where says what
    to open for it -- {"league": name, "place": k}, {"league": name}, {"club": team id},
    {"players": recipe key} or {}"""

    def __init__(self, problems):
        self.problems = list(problems)
        if len(self.problems) == 1:
            text = self.problems[0][0]
        else:
            text = "%d problems:\n  " % len(self.problems) + "\n  ".join(t for t, _w in self.problems)
        super().__init__(text)


class _Below(BuildError):
    """a league under one that has a problem already: left out, not reported again"""


def club_label(info, tid):
    """a club of the game as Build's messages name it: its name and its team id, both (mato
    21.10.: the ids stay visible everywhere)"""
    name = (info["clubs"].get(tid) or ("",))[0]
    return "%s (%d)" % (name, tid) if name else "club %d" % tid


def problem_where(text, leagues):
    """what a problem's text is about, for Go there: a league of the recipe and a place in it
    ("Liga 2, club 4: ..."), a league ("Liga 2: ..."), the players of a club ("players of 101",
    "players of Liga 2/3"), or {}"""
    m = re.match(r"(?:players|manager|home stadium) of (.+?)(?::|, (?:new )?player)", text)
    if m:
        return {"players": m.group(1)}
    for nm in sorted(leagues, key=len, reverse=True):
        if text.startswith(nm + ", club "):
            m = re.match(r"\d+", text[len(nm) + 7:])
            if m:
                return {"league": nm, "place": int(m.group(0)) - 1}
        if text.startswith(nm + ":") or text.startswith(nm + " "):
            return {"league": nm}
    m = re.search(r"\((\d+)\)", text)            # a club of the game, "Fortaleza (1712)"
    if m:
        return {"club": int(m.group(1))}
    return {}


def _problem(errs, names, text):
    errs.append((text, problem_where(text, names)))


def stale_swaps(recipe, base):
    """the recipe's swaps (edits.swaps) that the game's tables have made out of date: the two
    clubs play in the same league there now (jibibi 19.10.: Fortaleza and Remo, swapped in a
    world made before, are both in the game's Serie A of the update). Build leaves them out and
    says so instead of stopping. [(pair, note)]"""
    pairs = (recipe.get("edits") or {}).get("swaps") or []
    if not pairs:
        return []
    info = game_info(base)
    out = []
    for pair in pairs:
        try:
            a, b = (int(x) for x in pair)
        except (TypeError, ValueError):
            continue
        lg = info["league_of"].get(a)
        if a != b and lg is not None and lg == info["league_of"].get(b):
            out.append((pair, "the swap of %s and %s is left out: the game's tables have both in the same league "
                              "now (remove it on Leagues to stop this note)" % (club_label(info, a), club_label(info, b))))
    return out


def squads_cut(said):
    """(clubs given a squad, new clubs) when mkplayers' output says the player cap left it room
    for only some of the new clubs; None when every club got one"""
    m = re.search(r"so (\d+) of the (\d+) new clubs get squads", said or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


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


def known_formations(p, base, name):
    """B105: a formation these tables do not have (a league from a pack made over other tables)
    stops nothing: it goes, and the clubs play the one their squad fits ("Picked from each club's
    squad"). Returns the notes for the log."""
    notes = []
    if p["formation"] and formation_club(base, p["formation"]) is None:
        notes.append("%s: no formation %r in these tables -- each club plays the one its squad fits"
                     % (name, p["formation"]))
        p["formation"] = ""
    for i, f in enumerate(p["club_formations"]):
        if f and formation_club(base, f) is None:
            notes.append("%s: club %d's formation %r is not in these tables -- it plays the one its squad fits"
                         % (name, i + 1, f))
            p["club_formations"][i] = ""
    return notes


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


def cpk_key(path):
    """the order the game layers download\\data_s*.cpk in, for sorted(): data_s2526, a, b, c, d,
    then the 2.2 update's data_s25262b -- the alphabet puts "25262b" before "2526b", so its
    tables (the newest) would be covered by the older ones (13.10.)"""
    m = re.match(r"data_s(\d{4})(\d*)([a-z]*)\.cpk$", os.path.basename(path).lower())
    if not m:
        return (1, 0, 0, os.path.basename(path).lower())
    return (0, int(m.group(1)), int(m.group(2) or 0), m.group(3))


def unpack_tables(game, out, log=print):
    """unpack the game's tables (download/data_s2526*.cpk and the update's data_extra*.cpk, the
    later ones over the earlier, as the game layers them) into <out>; returns the folder with
    Team.bin -- the --base of the rest"""
    import cpkread
    cpks = sorted(glob.glob(os.path.join(game, "download", "data_s2526*.cpk")), key=cpk_key)
    if not cpks:
        raise BuildError("no download/data_s2526*.cpk in %s -- is that the game folder?" % game)
    # the update's tables ("National selection 2.2") go over the ones above, as the game layers
    # them: an edit file made for the updated database matches what we unpack then (#75, #63)
    cpks += sorted(glob.glob(os.path.join(game, "download", "data_extra*.cpk")))
    data = sorted(glob.glob(os.path.join(game, "Data", "*.cpk")))
    toc = {}
    for c in data + cpks:
        try:
            toc[c] = cpkread.names(c)
        except (OSError, ValueError, KeyError):
            toc[c] = []
    # the kits file of the game as it came (Data\*.cpk) under the download's: FL26 1.0 without
    # the game's updates has none in download\, and Build then drew no kit (B153)
    for c in data:
        if UNIPAR in toc[c]:
            cpkread.extract(c, out, [UNIPAR])
            log("  %-20s the kits file (UniformParameter.bin)" % os.path.basename(c))
    for c in cpks:
        n = cpkread.extract(c, out, ["common/etc/pesdb/", UNIPAR])
        log("  %-20s %d tables" % (os.path.basename(c), n))
    base = os.path.join(out, "common", "etc", "pesdb")
    if not os.path.exists(os.path.join(base, "Team.bin")):
        raise BuildError("the archives held no Team.bin")
    # the kit textures the game has: a kit lent without its texture shows as a blank one
    import re
    tex = set()
    for c in data + cpks:
        tex |= {m for n in toc[c] for m in re.findall(r"(u\d{4,5}[a-z]\d)\.ftex", n)}
    with open(os.path.join(out, KIT_TEXTURES), "w") as f:
        f.write("".join("%s.ftex\n" % t for t in sorted(tex)))
    log("  %d kit textures" % len(tex))
    rec = _table_cpks(game)
    rec[UNIPAR_SEEN] = [int(os.path.exists(os.path.join(out, UNIPAR.replace("/", os.sep)))), 0]
    with open(os.path.join(out, UNPACKED), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
    return base


UNPACKED = "fl26-unpacked.json"        # the archives an unpack read: {file name: [size, mtime]}
UNIPAR_SEEN = "UniformParameter.bin"   # in UNPACKED: [1, 0] when that unpack found the kits file (B153)


def _table_cpks(game):
    d = os.path.join(game, "download")
    return {os.path.basename(c): [os.path.getsize(c), int(os.path.getmtime(c))]
            for c in sorted(glob.glob(os.path.join(d, "data_s2526*.cpk")), key=cpk_key) +
            sorted(glob.glob(os.path.join(d, "data_extra*.cpk")))}


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
    if UNIPAR_SEEN not in was and not os.path.exists(os.path.join(out, UNIPAR.replace("/", os.sep))):
        # unpacked by 0.2.4 or older from FL26 1.0 without the game's updates: no kits file (B153)
        return "unpacked without the game's kits file (UniformParameter.bin)"
    new = [k for k in now if k not in was]
    changed = [k for k in now if k in was and list(was[k]) != now[k]]
    if new or changed:
        return "the game was updated since (%s)" % ", ".join(new + changed)
    return None


def tables_root(base):
    """the unpack folder that holds <base> (…/common/etc/pesdb), or None"""
    parts = os.path.normpath(base).split(os.sep)
    return os.sep.join(parts[:-3]) if parts[-3:] == ["common", "etc", "pesdb"] else None


def kits_file(base):
    """the game's UniformParameter.bin for the tables in <base>, or None: in the unpack folder that
    holds them, else in a folder above <base> -- your own tables over the game's (Settings > Use
    another tables folder) sit in ...-with-your-database/pesdb with the game's kits file beside
    it (B143: there Build drew no kit at all)"""
    d = os.path.normpath(base)
    for _up in range(4):
        f = os.path.join(d, UNIPAR.replace("/", os.sep))
        if os.path.isfile(f):
            return f
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    return None


# kits files to fall back on when the tables folder has none beside it: Mod Studio puts the
# game's unpacked one here (APPDIR	ables)
KITS_FALLBACK = []


def kits_for(base, game):
    """the kits file Build draws the new clubs' kits from: the one beside the tables (kits_file),
    else the game's unpacked one, else the one of the mod sider.ini serves first. B218
    (Aleperfe87 23.10.): with a whole database mod in livecpk as the tables folder there was
    none beside it, and the world got no kits file, so its new clubs were "unlicensed" and
    wore no kit"""
    k = kits_file(base)
    if k:
        return k
    for f in KITS_FALLBACK:
        if os.path.isfile(f):
            return f
    over = other_uniforms(game)
    return over[-1] if over else None


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
    lbplayers.SQUAD = SQUAD                # a new club's places: the squads Build makes
    return bool(e.get("leagues") or e.get("clubs") or e.get("competitions") or e.get("swaps")) \
        or lbplayers.has_players(r) \
        or bool(r.get("game_cups") or r.get("game_europe") or r.get("conmebol_associations") or r.get("uefa_seed")
                or r.get("preseason_cups") or r.get("ccup_names") or r.get("ccup_logos")
                or any((r.get("europe_first") or {}).values())
                or r.get("uecl_name") or r.get("uecl_logo") or r.get("caf_super_cup_logo")
                or r.get("samerica_super_cup_logo") or r.get("samerica_super_cup_first")
                or r.get("saudi_august") or r.get("game_seasons") or r.get("editable_kits") or r.get("country_order")
                or r.get("conmebol")) \
        or r.get("uecl") is False or r.get("caf_super_cup") is False or r.get("samerica_super_cup") is False


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


def national_teams(base):
    """the team ids of Team.bin's national teams"""
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    return {int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little")
            for o in range(0, len(raw), W.T_REC) if raw[o + T_NATIONAL] & 0x80}
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


# the recipe's own keys that plan() reads in another form, or not at all (the UEFA ranking, the
# order of the League list, NewLife's bookkeeping, what came from which league package): the plan
# keeps them as the recipe had them ("settings"), so recipe_from_plan gives them back exactly and a
# world made editable again builds the same (0.2.4, editing a ready world)
RECIPE_SETTINGS = ("game_europe", "uefa_seed", "uefa_rank", "europe_first", "game_cups", "preseason_cups",
                   "ccup_names", "ccup_logos", "caf_super_cup", "caf_super_cup_logo", "cup_draw",
                   "country_order", "game_seasons", "saudi_august", "newlife_ids", "newlife_game",
                   "league_order", "packs", "conmebol", "conmebol_associations", "samerica_super_cup",
                   "samerica_super_cup_logo", "samerica_super_cup_first", "sudamericana_calendar")


def is_plan(r):
    """whether a json read as a recipe is a built world's leaguebuilder-plan.json: the plan has
    the ids Build gave (free_ids, and a rid for every league), a recipe never does"""
    return isinstance(r.get("free_ids"), int) or any(
        isinstance(L, dict) and "rid" in L for L in r.get("leagues") or [])


def recipe_from_plan(pl, base):
    """the recipe a built world was made from, read back from its leaguebuilder-plan.json: for a
    world whose recipe was never saved (Mod Studio opens the live world, 0.1.8), or a ready world
    from a zip made editable (0.2.4). The plan holds everything the recipe said about the leagues;
    the ids it adds (rid, cid, slot, teams ...) are left out: built over that same plan (the world
    folder's leaguebuilder-plan.json, prev_pins) the leagues and clubs get them back. NewLife
    clubs keep theirs through newlife_ids, rebuilt from the plan's newlife_tid."""
    import mkflags
    cty = mkflags.countries(mkflags.table("Country", [base]))
    name_of_rid = {L["rid"]: L["name"] for L in pl.get("leagues") or []}
    out = []
    for L in (pl.get("leagues") or []) + (pl.get("others") or []):
        en = (cty.get(L.get("country")) or ("", None))[0]
        country = mkflags.title(en) if en else ""
        if en and mkflags.by_name(cty, country) != L["country"]:
            # a name two countries share: one only this country has, or the league would take
            # another flag id, and with it another region (plan: the pin wants the same country)
            country = next((n for n in sorted(cty[L["country"]][1]) if mkflags.by_name(cty, n) == L["country"]),
                           country)
        r = {"name": L["name"], "country": country, "clubs": L["clubs"]}
        if L.get("others"):
            r["others"] = next(k for k, v in OTHERS.items() if v == L["others"])
        else:
            r["legs"], r["exchange"] = L.get("legs", 2), L.get("exchange", 3)
        for k in ("logo", "flag", "formation", "scoreboard"):
            if L.get(k):
                r[k] = L[k]
        for k in ("club_names", "club_crests", "club_abbrs", "club_coaches", "club_formations",
                  "club_kits", "club_away_kits", "kit_folders"):
            if L.get(k):                # as the recipe had it, a list of blanks too
                r[k] = list(L[k])
        if any(x is not None for x in L.get("club_ids") or []):
            r["club_ids"] = ["" if x is None else str(x) for x in L["club_ids"]]
        nl = L.get("newlife") or {}
        if nl.get("clubs") or any(k != "clubs" for k in nl):
            # the release's version and league key go with the clubs (the NewLife page updates by them)
            r["newlife"] = dict(copy.deepcopy(nl), clubs=list(nl.get("clubs") or []))
        if L.get("europe"):
            r["europe"] = [list(e) for e in L["europe"]]
        if L.get("exhibition"):
            r["exhibition"] = True
        if L.get("real_calendar") is not None:          # false (the old calendar) counts too
            r["real_calendar"] = copy.deepcopy(L["real_calendar"])
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
        if L.get("cup_top_only") or (L.get("tier") == 2 and up is not None and up not in name_of_rid
                                     and L.get("cup") and "cup_all" not in L):
            r["cup_top_only"] = True        # (an older plan says so only by the cup_all it has not)
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
        ap = L.get("apertura")
        if ap:
            # plan() writes Apertura/Clausura as a split of one group: given back as a split, it
            # was refused ("split groups [n] must be 2 or 3 counts")
            r["apertura"] = {"playoff": int(ap.get("playoff", PLAYOFF_SIZES[0]))}
            if ap.get("logo"):
                r["playoff_logo"] = ap["logo"]
        elif L.get("split"):
            r["split"] = {k: copy.deepcopy(v) for k, v in L["split"].items() if k in ("legs", "groups", "group_legs")}
        out.append(r)
    rec = {"world": pl["world"], "leagues": out, "edits": pl.get("edits") or {},
           "players": pl.get("players") or {}}
    if pl.get("conmebol_associations_recipe"):
        rec["conmebol_associations"] = pl["conmebol_associations_recipe"]
    for k in ("uecl", "uecl_logo", "uecl_name", "editable_kits", "game_seasons", "cafsc"):
        if pl.get(k) or k == "uecl":       # (an empty game_seasons is no setting)
            rec[k] = pl.get(k)
    # a trophy folder on another PC (a world from a zip) is not one this Build can copy
    trophies = {c: f for c, f in (pl.get("trophies") or {}).items() if f and os.path.isdir(f)}
    if trophies:
        rec["trophies"] = trophies
    if pl.get("make_kits") is False:
        rec["make_kits"] = False
    if pl.get("replaced_kits") is False:
        rec["replaced_kits"] = False
    if pl.get("pack_faces") is False:
        rec["pack_faces"] = False
    st = pl.get("settings")
    if isinstance(st, dict):
        rec.update({k: copy.deepcopy(st[k]) for k in RECIPE_SETTINGS if k in st})
    else:
        rec.update(settings_from_plan(pl, base))
    # every NewLife club keeps the world id it was built with, whatever is added or taken out
    # in front of it (newlife_tids); a pin of a club no longer in the world stays as it was
    nlt = next((p["newlife_tid"] for p in (pl.get("leagues") or []) + (pl.get("others") or [])
                if p.get("newlife_tid")), None) or {}
    if nlt:
        pins = dict(rec.get("newlife_ids") or {})
        pins.update({str(k): int(v) for k, v in nlt.items()})
        rec["newlife_ids"] = pins
    return rec


def game_access_regs(base):
    """{the regulation the access list names (access_reg): the top division of the game it stands for}"""
    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    regrow = {u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)}
    region_of_cid = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
                     for i in range(len(comp) // M.COMP)}
    out = {}
    for r, _c, _n, _t in game_leagues(base):
        if r in regrow and M.get_tier(regrow[r]) == 1:
            out.setdefault(access_reg(r, regrow, region_of_cid), r)
    return out


def settings_from_plan(pl, base):
    """RECIPE_SETTINGS of a plan from before plan() kept them (0.2.4 and older, the FL26 Modpack
    r6), read back from what plan() made of them. Not in such a plan, so lost: uefa_rank,
    league_order, packs and newlife_game (Build never read them), and newlife_ids pins of clubs
    no longer in the world, and the order of game_cups (a league cup and a super cup are kept
    apart). A game league's place in a continental cup of ours that is also a place the cup fills
    itself from (fl26world.CCUPS) is found by the field's order (ccup_given); one that the order
    does not tell is lost."""
    out = {}
    name_of = {p["rid"]: p["name"] for p in pl.get("leagues") or []}

    def club(ref):
        if isinstance(ref, (list, tuple)):
            return "%s/%d" % (name_of[ref[0]], ref[1])
        return int(ref)
    first = {key: [club(x) for x in refs] for (key, _t), refs in zip(EUROPE_FIRST, pl.get("europe_first") or [])
             if refs}
    if first:
        out["europe_first"] = first
    if pl.get("cup_draw") and pl["cup_draw"] != CUP_DRAWS[0]:
        out["cup_draw"] = pl["cup_draw"]
    if pl.get("country_order"):
        out["country_order"] = copy.deepcopy(pl["country_order"])
    cups = pl.get("ccups") or []
    numbers = {c.get("number") for c in cups}
    if {CAF_CL, CAF_CC} <= numbers and 0 not in numbers:
        out["caf_super_cup"] = False
    default = {c: n for c, n, _code, _conf, _fill in fl26world.CCUPS}
    default[0] = caf_super_cup({})["name"]
    names = {str(c["number"]): c["name"] for c in cups if c.get("number") in default
             and c.get("name") and c["name"] != default[c["number"]]}
    logos = {str(c["number"]): c["logo"] for c in cups if c.get("number") in default and c.get("logo")}
    if names:
        out["ccup_names"] = names
    if logos:
        out["ccup_logos"] = logos
    pre = [c for c in pl.get("home_cups") or [] if c.get("kind") == "preseason"]
    if pre:
        out["preseason_cups"] = [dict({"name": c["name"], "clubs": [club(x) for x in c.get("refs") or []]},
                                      **({"logo": c["logo"]} if c.get("logo") else {})) for c in pre]
    # game_cups: the league cups (home_cups, FL_G<rid>_LCUP) and super cups (game_supers), in
    # the order both lists had them
    lcup = [(int(c["code"][4:7]), c) for c in pl.get("home_cups") or []
            if c.get("kind") == "league" and re.fullmatch(r"FL_G\d{3}_LCUP", str(c.get("code") or ""))]
    scup = [(int(c["league"]), c) for c in pl.get("game_supers") or []]
    order, a, b = [], [r for r, _c in lcup], [r for r, _c in scup]
    while a or b:
        if a and b and a[0] == b[0]:
            order.append(a.pop(0))
            b.pop(0)
        elif a and a[0] not in b:
            order.append(a.pop(0))
        else:
            order.append(b.pop(0))
    lc, sc = dict(lcup), dict(scup)
    gcups = []
    for r in order:
        g = {"league": r, "league_cup": r in lc, "super_cup": r in sc}
        if r in lc:
            g["name"] = lc[r]["name"]
            if lc[r].get("logo"):
                g["logo"] = lc[r]["logo"]
        if r in sc:
            g["super_name"] = sc[r]["name"]
            if sc[r].get("logo"):
                g["super_logo"] = sc[r]["logo"]
        gcups.append(g)
    if gcups:
        out["game_cups"] = gcups
    ge, seed = {}, []
    if pl.get("game_europe") or pl.get("uefa_seed") or any(c.get("number") in default for c in cups):
        top = game_access_regs(base)
        for a, pos, comp, alt in pl.get("game_europe") or []:
            rid = top.get(alt or a)
            if rid is not None:
                ge.setdefault(str(rid), []).append([CUP_WINNER if alt else int(pos), int(comp)])
        # a game league's places in our continental cups: the cup's entries of leagues not ours.
        # One the cup does not take by itself is one; one it also fills itself from (CCUPS) is
        # told by the order: ccup_plan puts the places it was given before the ones it fills, so
        # the fewest such entries that give the cup's field back are the ones it was given
        tops = set(top.values())
        ours = [(p["rid"], pos, comp, 0) for p in pl.get("leagues") or [] for pos, comp in p.get("europe") or []]
        for c in cups:
            n = c.get("number")
            fill = next((set(map(tuple, f)) for c2, _n, _code, _conf, f in fl26world.CCUPS if c2 == n), None)
            if fill is None:
                continue
            given, maybe = [], []
            for e in map(tuple, c.get("entry") or []):
                lg = entry_league(e)
                if e[0] == "ko" or lg in name_of or lg not in tops:
                    continue
                (maybe if e in fill else given).append(e)
            if maybe:
                given += ccup_given(n, c.get("entry") or [], ours, given, maybe)
            for e in given:
                ge.setdefault(str(entry_league(e)), []).append([CUP_WINNER if e[0] == "cup" else int(e[1]), int(n)])
        for lg, pos, comp in pl.get("uefa_seed") or []:
            if lg in name_of:
                seed.append([name_of[lg], int(pos), int(comp)])
            elif lg in top:
                seed.append(["g%d" % top[lg], int(pos), int(comp)])
    if ge:
        out["game_europe"] = ge
    if seed:
        out["uefa_seed"] = seed
    return out


def ccup_given(n, field, ours, given, maybe, tries=20000):
    """settings_from_plan: which of a continental cup's entries that are also places it fills
    itself from (maybe) were game_europe places too -- the fewest that, with the world's own
    places (ours) and the game's places it surely was given, make ccup_plan build cup n with
    this field; [] when none does within `tries` (that place is then lost)"""
    import itertools
    want = [list(e) for e in field]
    as_place = lambda e: (e[1], CUP_WINNER, n, 0) if e[0] == "cup" else (e[0], e[1], n, 0)
    mine = [x for x in ours if x[2] == n]
    for k in range(len(maybe) + 1):
        for sub in itertools.combinations(maybe, k):
            tries -= 1
            if tries < 0:
                return []
            # game_europe's places go after the world's own, a league at a time (game_europe)
            own = mine + sorted((as_place(e) for e in list(given) + list(sub)), key=lambda x: str(x[0]))
            cup = next((c for c in ccup_plan(own)[0] if c["number"] == n), None)
            if cup and [list(e) for e in cup["entry"]] == want:
                return list(sub)
    return []


def club_countries(base):
    """{team id: Country.bin id} of every team in Team.bin (T_COUNTRY)"""
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    out = {}
    for i in range(len(raw) // W.T_REC):
        r = raw[i * W.T_REC:(i + 1) * W.T_REC]
        out[int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")] = \
            (int.from_bytes(r[T_COUNTRY:T_COUNTRY + 2], "little") >> 2) & 0x1ff
    return out


def game_league_confeds(base, leagues):
    """{competition id: confederation code} of the game's leagues -- the code most of its
    clubs' countries have (Team.bin T_COUNTRY, Country.bin); 0 when nothing is known"""
    import collections
    conf = confederations(base)
    of = {t: conf.get(c, 0) for t, c in club_countries(base).items()}
    out = {}
    for rid, cid, name, teams in leagues:
        c = collections.Counter(of.get(t, 0) for t in teams if of.get(t, 0))
        out[cid] = c.most_common(1)[0][0] if c else 0
    return out


# The country each league of the game has as shipped, by regulation (measured on the plain tables
# 2026-10-14: every club entered in it is of that country, MLS's two Canadian ones aside). It is
# not what a league is -- game_league_countries reads that from the tables in use -- but what
# the regulation held before a database mod put another country's league in it, for the answers
# that were written for the shipped league (SLOT_COUNTRY's).
SHIPPED_COUNTRY = {17: "England", 18: "Italy", 19: "Spain", 20: "France", 21: "Netherlands",
                   22: "Portugal", 29: "Brazil", 30: "Argentina", 50: "Germany", 52: "Japan",
                   67: "Chile", 79: "England", 80: "Spain", 81: "France", 82: "Italy",
                   115: "Belgium", 116: "Russia", 117: "Greece", 118: "Turkey", 120: "China",
                   133: "Scotland", 141: "Denmark", 162: "Saudi Arabia", 163: "Brazil",
                   166: "Usa", 168: "Colombia"}


def game_league_countries(base, leagues=None):
    """{regulation id: country name (country_ids' spelling)} of the game's leagues (game_leagues,
    or leagues), read from the tables in use: the country most of the clubs entered in the
    league are of (Team.bin T_COUNTRY), as game_league_confeds finds its confederation. A
    league none of whose clubs has a country the tables name is left out.
    Competition.bin has no country of its own, only the region byte, which picks the menu
    heading the exe draws (regions-plan.md) and stays with the slot. A database mod moves
    leagues into other leagues' slots -- UML 2026 v3 has Ligue 1 where the Russian Premier Liga
    was -- so a table of regulation ids named the wrong country (Yanis, 14.10.)."""
    import collections
    names = dict((fid, nm) for nm, fid in country_ids(base))
    of = club_countries(base)
    out = {}
    for rid, _cid, _name, teams in (game_leagues(base) if leagues is None else leagues):
        c = collections.Counter(of[t] for t in teams if of.get(t) in names)
        if c:
            out[rid] = names[c.most_common(1)[0][0]]
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
     "friendly_cids": {competition ids of pre-season tournaments},
     "club_country": {id: Country.bin id}}"""
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
            "friendly_cids": friendly, "club_country": club_countries(base)}
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
    if isinstance(gc, dict):                # a plan's league keeps them by place (game_places)
        gc = list(gc.values())
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


def game_league_edits(pl):
    """edits.leagues of the game's leagues the world still has: a regulation id a new league
    took over (the game's league dropped, its slot reused) keeps the new league's own name and
    logo, not an old rename of the league that left (Matheus 12.10.: Serie C as rid 11 came
    out "Campeonato Carioca")"""
    taken = {p["rid"] for p in pl.get("leagues") or [] if "rid" in p}
    return {int(k): v for k, v in ((pl.get("edits") or {}).get("leagues") or {}).items()
            if int(k) not in taken}


def apply_edits(edits, raw, regs, log=print, leagues=None):
    """the recipe's changes to the game's own clubs and leagues, in the world's tables;
    `leagues` (game_league_edits) in place of edits.leagues"""
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
    if leagues is None:
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
        ab = "%s <-> %s" % (club_label(info, a), club_label(info, b))
        for t in (a, b):
            if t not in info["league_of"]:
                err.append("swap %s: %s plays in no league of the game" % (ab, club_label(info, t)))
            if t in seen:
                err.append("%s is in two swaps" % club_label(info, t))
            if t in taken:
                err.append("%s plays in a new league of the recipe; it cannot also swap" % club_label(info, t))
            seen.add(t)
        if a == b or (a in info["league_of"] and info["league_of"].get(a) == info["league_of"].get(b)):
            err.append("swap %s: the two clubs play in the same league" % ab)
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


def clear_league_pools(raw, ents, cids):
    """the "Other ..." nibble (T_POOL) cleared on every club of Team.bin `raw` with a place in
    one of the competitions `cids` (the world's leagues); returns the ids it cleared. The game
    files a club into an "Other ..." group by that nibble at boot, whatever the competitions say
    (#60), so a club of the game renamed into another (edits.clubs, NewLife's replaced places)
    or swapped into a league (edits.swaps) from a place filed in Otros latinoamericanos showed
    up in its league and in the Others list as well (B65, Estudiantes de Rio Cuarto)"""
    row = {int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little"): o
           for o in range(0, len(raw) - len(raw) % W.T_REC, W.T_REC)}
    out = []
    for i in range(len(ents) // M.ENT):
        o = i * M.ENT
        t = int.from_bytes(ents[o + M.E_TEAM:o + M.E_TEAM + 4], "little")
        if ents[o + M.E_CID] in cids and t in row and raw[row[t] + T_POOL] & 0xf0:
            raw[row[t] + T_POOL] &= 0x0f
            out.append(t)
    return out


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
    "Democratic Republic of the Congo": "Congo Dr", "Central African Republic": "Central African Rep.",
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


def last_build_ids(game, world):
    """the whole fl26playerids.json of the last Build of `world` ({"clubs": ..., "names": ...}), or {}:
    Build gives the world's own players those ids again (GitHub #126)"""
    import siderdir
    try:
        with open(os.path.join(siderdir.find(game), "livecpk", world, PLAYER_IDS), encoding="utf-8") as f:
            got = json.load(f)
        return got if isinstance(got, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


TWIN_SHARE = 0.9      # twin_build_ids: the share of new clubs two worlds must have in common


def twin_build_ids(game, world, plan, log=None):
    """the ids file of another world built from the same leagues, for a world built for the first
    time ({} when there is none): B155b, pepponeee98 19.10.2026. His Edit (EDIT00000000) went with
    a world of 0.2.3; 0.2.4 makes 30 players a new club, not 22, so the same recipe built under a
    new name numbered the new clubs' players afresh -- 6 of 4625 kept their id -- and the Edit
    showed other people. Only the world's own file (last_build_ids) was read. Now a world with no
    file of its own takes the file of the world whose new clubs are this plan's: nearly all of
    its clubs are new clubs of this plan, and it has nearly all of the plan's clubs the recipe
    gives players (TWIN_SHARE; a file of 0.2.3 lists only those, 229 of pepponeee98's 262), with
    the same NewLife clubs where both files say; the most alike first."""
    log = log or (lambda *_a: None)
    mine = {"%s/%d" % (p["name"], k) for p in plan.get("leagues") or [] for k in range(len(p.get("teams") or []))}
    if not mine:
        return {}
    told = mine & set(plan.get("players") or {}) or mine        # the clubs a recipe gives players
    now = club_newlife(plan)
    root = os.path.join(siderdir.find(game), "livecpk")
    best = None
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return {}
    for w in names:
        if w == world or w.lower().endswith((".building", ".old")):
            continue
        got = last_build_ids(game, w)
        theirs = {k for k in got.get("clubs") or {} if "/" in k}
        both = told & theirs
        if not theirs or len(mine & theirs) < TWIN_SHARE * len(theirs) or len(both) < TWIN_SHARE * len(told):
            continue
        was = got.get("club_nl") if isinstance(got.get("club_nl"), dict) else {}
        said = [k for k in both if k in was and k in now]
        if said and sum(was[k] == now[k] for k in said) < TWIN_SHARE * len(said):
            continue
        score = (len(both), os.path.getmtime(os.path.join(root, w, PLAYER_IDS)))
        if best is None or score > best[0]:
            best = (score, w, got)
    if not best:
        return {}
    log("  player ids: %s has none of its own yet, so it keeps those of %s, built from the same leagues "
        "(%d of %d new clubs): an Edit or a career of %s shows the same players" % (world, best[1], best[0][0],
                                                                                  len(told), best[1]))
    return best[2]


def id_names(plan, ids):
    """{club: {player key: name}} for the keys in ids whose change names the player: the next
    Build keeps a key's id only for the same player"""
    out = {}
    for club, keys in ids.items():
        c = (plan.get("players") or {}).get(club) or {}
        adds = c.get("add") or []
        for key in keys:
            if key.startswith("+") and key[1:].isdigit():
                ch = adds[int(key[1:])] if int(key[1:]) < len(adds) else {}
            else:
                ch = (c.get("edits") or {}).get(key) or {}
            if ch.get("name"):
                out.setdefault(club, {})[key] = ch["name"]
    return out


def id_people(plan, ids):
    """{club: {player key: {"nl": NewLife id, "born": birth date}}} for the keys in ids whose
    change says who the player is (a NewLife squad's): the next Build finds him by it, wherever
    his place in the squad is then (lbplayers._keep_ids)"""
    out = {}
    for club, keys in ids.items():
        c = (plan.get("players") or {}).get(club) or {}
        adds = c.get("add") or []
        for key in keys:
            if key.startswith("+") and key[1:].isdigit():
                ch = adds[int(key[1:])] if int(key[1:]) < len(adds) else {}
            else:
                ch = (c.get("edits") or {}).get(key) or {}
            p = {k: str(ch[f]).strip() for k, f in (("nl", "newlife_id"), ("born", "birth_date"))
                 if str(ch.get(f, "")).strip()}
            if p:
                out.setdefault(club, {})[key] = p
    return out


def club_newlife(plan):
    """{new club key: its NewLife club id} of the plan's leagues"""
    out = {}
    for p in plan.get("leagues") or []:
        nl = (p.get("newlife") or {}).get("clubs") or []
        for k in range(len(p.get("teams") or [])):
            if k < len(nl) and str(nl[k] or "").strip() not in ("", "0"):
                out["%s/%d" % (p["name"], k)] = str(nl[k]).strip()
    return out


def follow_clubs(last, now):
    """the last Build's ids file (last_build_ids) with its new clubs under their keys now: a
    NewLife club whose place in its league changed (a club before it left) is found by its
    NewLife id; one that left the world goes under a key no club has, so its players' ids are
    nobody else's. now: club_newlife of this Build's plan. A file of an older Build (no
    "club_nl") is taken as it is."""
    import collections
    was = last.get("club_nl")
    if not isinstance(was, dict) or not was:
        return last
    count = lambda d: collections.Counter(d.values())
    cw, cn = count(was), count(now)
    key_now = {v: k for k, v in now.items() if cn[v] == 1}
    out = dict(last)
    for part in ("clubs", "names", "people"):
        src = last.get(part)
        if not isinstance(src, dict):
            continue
        moved = {}
        for club, v in src.items():
            nl = was.get(club)
            if nl is None or cw[nl] != 1:
                to = club                              # a club of the game, or listed twice: as it is
            elif nl in key_now:
                to = key_now[nl]
            else:
                to = "gone:" + club                    # left the world
            moved.setdefault(to, v)
        out[part] = moved
    return out


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
    fl26-800-klubova-igra), and every new club takes at least SQUAD_FIT of the PLAYER_CAP player
    records the installed patch set allows (SQUAD while they last, squad_size)"""
    n = lambda f, rec: len(pesdb.wesys_unpack(open(os.path.join(base, f), "rb").read())) // rec
    return min(TEAM_CAP - n("Team.bin", W.T_REC), (PLAYER_CAP - n("Player.bin", 312)) // SQUAD_FIT)


def smaller_squads(counts, over, per):
    """the largest squad below per that frees `over` player records, each new club keeping
    min(its squad, the new size); None when even SQUAD_FIT does not"""
    counts = list(counts)
    for p in range(per - 1, SQUAD_FIT - 1, -1):
        if sum(max(0, c - p) for c in counts) >= over:
            return p
    return None


def squad_size(have, made):
    """the squad each of `made` new clubs gets when the tables hold `have` players: SQUAD, unless
    the player records left run out first -- then as many as they give each, down to SQUAD_FIT
    (clubs_room refuses a world below that)"""
    return max(SQUAD_FIT, min(SQUAD, (PLAYER_CAP - have) // max(made, 1)))


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


def prev_pins(prev):
    """{league name, lower case: what the last Build gave it} from that Build's plan (its
    leaguebuilder-plan.json): a league built before keeps its competition, regulation and
    region ids and its new clubs' team ids, so a league added, removed or moved in front of it
    does not hand every league after it new ids. A Master League career, a Kit Server map.txt
    and the scoreboard map all hold those ids (audit 12.10.; only NewLife clubs kept theirs)."""
    out = {}
    for q in (prev or {}).get("leagues") or []:
        if isinstance(q, dict) and q.get("name"):
            out[str(q["name"]).strip().lower()] = q
    return out


def plan(recipe, base, prev=None):
    """the plan of `recipe`; `prev` is the plan of the world's last Build, whose ids the
    leagues built then keep (prev_pins)"""
    pins = prev_pins(prev)
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
    others = others_plan([L for L in recipe["leagues"] if L.get("others")], base, cty,
                         prev_pins({"leagues": (prev or {}).get("others")}))
    fnotes = [t for p in others for t in p.pop("formation_notes", [])]
    full = recipe
    recipe = dict(recipe, leagues=[L for L in recipe["leagues"] if not L.get("others")])
    leagues = recipe["leagues"]
    names = [L.get("name", "").strip() for L in leagues]
    # a league renamed since the last Build keeps that Build's ids: built_as holds its names before
    # (project.rename_league), newest last; an old name a league of the recipe has now is its own
    taken, used, renamed = {n.lower() for n in names}, set(), {}
    for L, nm in zip(leagues, names):
        for was in reversed([str(x).strip().lower() for x in L.get("built_as") or []]):
            if nm.lower() in pins:
                break
            if was in pins and was not in taken and was not in used:
                pins[nm.lower()] = pins[was]
                used.add(was)
                renamed[nm] = was

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
        raise BuildError("%d leagues, but the game has room for %d (see docs/developers/mod-studio.md)"
                         % (len(leagues), len(free)))
    # a league built before keeps its competition id; the others take the first free ones
    cid_of, taken_cid = {}, set()
    low = low_cids(prev)
    pool = [c for c in W.cid_pool(CID_FROM, low) if c not in used_cid and c != UECL_CID]
    for i, nm in enumerate(names):
        c = (pins.get(nm.lower()) or {}).get("cid")
        if isinstance(c, int) and c in pool and c not in taken_cid:
            cid_of[i] = c
            taken_cid.add(c)
    # nor a cup's id of the last Build: build() gives the cup its own back (pinned_ids)
    prev_cups = kept_cups(renamed_cups((prev or {}).get("cup_ids") or {}, renamed), names)
    cup_cids = {w.get("cid") for w in prev_cups.values() if isinstance(w, dict)}
    rest = iter(c for c in pool if c not in taken_cid and c not in cup_cids)
    for i in range(len(leagues)):
        if i not in cid_of:
            cid_of[i] = next(rest, None)
            if cid_of[i] is None:
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
    # a league built before keeps its regulation id (and with it its slot and dates), as long as
    # the id is still free and still suits it (same exhibition kind; a split season off reg 49)
    for i in order:
        q = pins.get(names[i].lower()) or {}
        r = q.get("rid")
        if (isinstance(r, int) and r in left
                and not (r == SHARED_SLOT_REG and (leagues[i].get("split") or leagues[i].get("apertura")))
                and bool(q.get("exhibition")) == bool(leagues[i].get("exhibition"))):
            rid_of[i] = r
            left.remove(r)
    for i in order:
        if i in rid_of:
            continue
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
    # a split season stays off reg 49: its Select Team slot is the Copa Libertadores' too
    # (competition 177, fl26comptab), and a Master League made with Uruguay's Apertura/Clausura
    # there crashed while the same split on reg 76 did not (GitHub #122, Discord 09.10.)
    ok = lambda i, r: not (r == SHARED_SLOT_REG and (leagues[i].get("split") or leagues[i].get("apertura")))
    for i in order:
        L = leagues[i]
        if i in rid_of or not L.get("europe") or not [r for r in left if ok(i, r)]:
            continue
        rounds = rounds_of(int(L.get("clubs", 0) or 0)) * int(L.get("legs", 2) or 2)
        # European days first: a clash with a league-cup date only breaks a tie (#54: an 18-club
        # league with a league cup took reg 98, 3 European clashes, to dodge two cup dates)
        cup = set(LEAGUE_KO_DAYS) if L.get("league_cup") else set()
        mine = [r for r in left if ok(i, r)]
        best = fl26world.id_rank(mine[0])
        r = min((r for r in mine if fl26world.id_rank(r) == best),
                key=lambda r: (len(set(league_days(r, rounds)) & EURO_DAYS),
                               len(set(league_days(r, rounds)) & cup), left.index(r)))
        rid_of[i] = r
        left.remove(r)
    for i in order:
        if i not in rid_of:
            r = next((r for r in left if ok(i, r)), None)
            if r is None:
                raise BuildError("%s: no free regulation id for a split season" % names[i])
            rid_of[i] = r
            left.remove(r)
    # a country built before keeps its region: claimed before any league takes the first free one
    for i in order:
        L, q = leagues[i], pins.get(names[i].lower()) or {}
        fid = mkflags.by_name(cty, L.get("country", ""))
        if (L.get("above") in (None, "") and q.get("above") is None and fid is not None and q.get("country") == fid
                and fid not in country_region and isinstance(q.get("region"), int)
                and REGION_FIRST <= q["region"] <= REGION_LAST and q["region"] not in used_region):
            used_region.add(q["region"])
            country_region[fid] = q["region"]
    errs, failed = [], set()        # every problem at once (jibibi 19.10.), the leagues that had one
    for k, i in enumerate(order):
        L = leagues[i]
        name = names[i]
        try:
            n, legs = int(L.get("clubs", 0)), int(L.get("legs", 2))
            if not CLUBS_MIN <= n <= CLUBS_MAX:
                raise BuildError("%s: %d clubs -- a league has %d..%d" % (name, n, CLUBS_MIN, CLUBS_MAX))
            if not 1 <= legs <= LEGS_MAX:
                raise BuildError("%s: clubs meet 1..%d times, not %d" % (name, LEGS_MAX, legs))
            fid = mkflags.by_name(cty, L.get("country", ""))
            if fid is None:
                raise BuildError("%s: no country called %r in Country.bin" % (name, L.get("country")))
            p = {"name": name, "country": fid, "clubs": n, "legs": legs, "rid": rid_of[i], "cid": cid_of[i],
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
                 "newlife": newlife_of(L),
                 "kit_folders": list(L.get("kit_folders") or []),     # Kit Server folders and the
                 "scoreboard": L.get("scoreboard") or None,           # Scoreboard Server one (lbservers)
                 "exchange": int(3 if L.get("exchange") is None else L["exchange"]),   # null in an old package
                 "above": None, "tier": 1,
                 "real_calendar": L.get("real_calendar"),     # realcal.py: dates, or false for none
                 "europe": [[int(a), int(b)] for a, b in (L.get("europe") or [])]}
            q = pins.get(name.lower()) or {}
            if q.get("teams"):
                # the team ids the last Build gave this league's places, and the names they had:
                # build() gives a new club its old id back (pinned_tid)
                p["prev_teams"] = [t if isinstance(t, int) else None for t in q["teams"]]
                p["prev_names"] = [str(x or "").strip().lower() for x in (q.get("club_names") or [])]
            fnotes += known_formations(p, base, name)
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
                        if up.strip().lower() in failed:      # its problem is listed already
                            raise _Below(name)
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
                        if p["cup"] and L.get("cup_top_only"):
                            p["cup_top_only"] = True       # for recipe_from_plan
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
        except _Below:
            failed.add(name.lower())
            continue
        except BuildError as e:
            _problem(errs, names, str(e))
            failed.add(name.lower())
            continue
        by_name[name.lower()] = p
        out.append(p)
    game_club_checks(out, base, errs)
    if sum(1 for p in out if p.get("split")) > MAX_SPLITS:
        _problem(errs, names, "at most %d split leagues for now (the phase ids tested are 191..196)" % MAX_SPLITS)
    for p in out:
        # the points carry goes by the country's competition key, not by league (fl26swiss.c
        # split_keys): a Scottish split there would make the Clausura carry its points too
        q = next((q for q in out if p.get("apertura") and q.get("split") and not q.get("apertura")
                  and q["region"] == p["region"]), None)
        if q:
            _problem(errs, names, "%s and %s: a country has Apertura/Clausura or a split that keeps its"
                             " points, not both" % (p["name"], q["name"]))
    for p in out:
        # the game finds a split's phases by the country's competition key too (0x1414ce270
        # under 0x14134a540): Iceland with Apertura/Clausura in both divisions (GitHub #45, 0.1.3.1)
        # showed all 20 clubs under the first division and played no match in either
        q = next((q for q in out if q is not p and p.get("split") and q.get("split")
                  and q["region"] == p["region"]), None)
        if q:
            _problem(errs, names, "%s and %s: only one league of a country can be split or Apertura/Clausura"
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
                             ("the league cup", q.get("league_cup"))) if on]
        if bad:
            _problem(errs, names, "%s: a country playing February to December cannot have %s yet -- take it off"
                             % (p["name"], ", ".join(bad)))
    for p in out:
        below = [q for q in out if q["above"] == p["rid"]]
        if below and p["exhibition"]:
            _problem(errs, names, "%s: an exhibition league has no league below it (%s)" % (p["name"], below[0]["name"]))
        if len(below) > 1:
            _problem(errs, names, "%s has %d leagues below it; the game follows one link"
                             % (p["name"], len(below)))
    # the same under a league of the game (GitHub #98: three Serie C groups under Serie B put the
    # same relegated clubs into all three and lost the promoted ones)
    ours = {p["rid"] for p in out}
    gname = dict(shipped_parents(base))
    for g in sorted({p["above"] for p in out if p["above"] and p["above"] not in ours}):
        below = [p["name"] for p in out if p["above"] == g]
        if len(below) > 1:
            _problem(errs, names, "%s are all under %s; the game follows one link down from a league, so only "
                             "one of them can be under it -- groups of one division are not possible yet"
                             % (", ".join(below), gname.get(g, "regulation %d" % g)))
    for p in out:
        if p.get("own_cup"):
            national_cup(p, next((q for q in out if q["above"] == p["rid"]), None))
    for t in club_id_problems(out + others, base):
        _problem(errs, names, t)
    nlt, free_ids = newlife_tids(full.get("leagues") or [], base, full.get("newlife_ids"))   # #90 / #88
    for p in out + others:
        p["newlife_tid"] = nlt
    import lbplayers
    lbplayers.SQUAD = SQUAD                # a new club's places: the squads Build makes
    for t in lbplayers.check(full):
        _problem(errs, names, t)
    # a swap the game's tables made out of date is left out with a note (jibibi: Fortaleza and
    # Remo in the same league now); the others are checked
    stale = stale_swaps(recipe, base)
    if stale:
        gone = [pr for pr, _n in stale]
        ed = dict(recipe.get("edits") or {})
        ed["swaps"] = [pr for pr in ed.get("swaps") or [] if pr not in gone]
        if not ed["swaps"]:
            ed.pop("swaps")
        recipe = dict(recipe, edits=ed)
    for t in swap_problems(recipe, base):
        _problem(errs, names, "clubs that swap leagues: " + t)
    for t in competition_problems(recipe.get("edits") or {}, base):
        _problem(errs, names, "competition names: " + t)
    import lbtrophies
    for t in lbtrophies.problems(recipe):
        _problem(errs, names, "trophies: " + t)
    if errs:
        raise PlanProblems(errs)
    # CONMEBOL is opt-in as one complete package. If the recipe never touches
    # South American continental access, keep FL26's vanilla Libertadores and do
    # not build Sudamericana/Recopa or the modern qualifying phases.
    access_recipe = modern_libertadores_recipe(recipe, base)
    modern_conmebol = access_recipe.get("_modern_libertadores_access") == "custom"

    ge, gr, gn, gcc = game_europe(access_recipe, regrow, region_of_cid, base)
    gstaged = game_stage_places(access_recipe, regrow, region_of_cid, base)
    aaccess, accup, astaged, arows, arecipe = conmebol_association_places(
        access_recipe, base, out
    )
    conmebol_stages = own_stage_places({"leagues": out}) + gstaged + astaged
    continental_places = (
        [(p["rid"], pos, comp, 0)
         for p in out for pos, comp in p["europe"]]
        + gcc + accup
    )

    if modern_conmebol:
        reject_legacy_libq_with_modern(access_recipe, out, conmebol_stages)
        validate_modern_conmebol_access(
            out, ge, aaccess, conmebol_stages, continental_places
        )
        libq = libq_plan(conmebol_stages)
        suda_first = sudamericana_first_plan(
            conmebol_stages, continental_places
        )
    else:
        libq = None
        suda_first = None
    room = {p["rid"]: p["clubs"] for p in out}
    room.update({r: entries_of(base, regrow[r][M.R_CID]) for r, _p, _c, _a in gcc})
    room.update({row["source"]: row["capacity"] for row in arows})
    cups, notes = ccup_plan(continental_places, room)
    if suda_first and not any(c["number"] == SUDAM for c in cups):
        raise BuildError("modern Sudamericana first stage needs the Copa Sudamericana group cup")
    if suda_first:
        # Modern Sudamericana runs on CONMEBOL's February-December calendar.
        # fl26swiss reads cal=1 and borrows the native Libertadores dates, fills
        # the groups immediately after the one-match first stage, and closes it
        # at the calendar-year teardown rather than in July.
        sud = next(c for c in cups if c["number"] == SUDAM)
        sud["opts"] = {"fill": SAM_GROUP_FILL, "national": 0, "days": [], "cal": 1}
    elif recipe.get("sudamericana_calendar") and any(c["number"] == SUDAM for c in cups):
        # the classic Copa Sudamericana on the same calendar (the World Modpack, mato 23.10.): it
        # played August to May, so a Brazilian or Argentine club in the Libertadores (February to
        # November) could be drawn into it as well. Filled in February from the tables the
        # Libertadores is filled from, it takes the clubs after the Libertadores' places
        sud = next(c for c in cups if c["number"] == SUDAM)
        sud["opts"] = {"fill": SAM_GROUP_FILL, "national": 0, "days": [], "cal": 1}
    for c in cups:            # a game league's cup winner: its national cup is the game's (#95)
        c["winners"] = [[e[1], home_cup(regrow, region_of_cid, region_of_cid.get(regrow[e[1]][M.R_CID]))]
                        for e in c["entry"] if e[0] == "cup" and e[1] in regrow
                        and e[1] not in {p["rid"] for p in out}]
    home = [league_cup(p, out) for p in out if p.get("league_cup")]
    gcups, gsupers = game_cups(recipe, regrow, region_of_cid, base, out)
    home += gcups
    home += [c for p in out if p.get("apertura") for c in playoff_cups(p)]
    home += [preseason_cup(c, k, by_name) for k, c in enumerate(recipe.get("preseason_cups") or [])]
    if recipe.get("caf_super_cup", True) and {CAF_CL, CAF_CC} <= {c["number"] for c in cups}:
        cups.append(caf_super_cup(recipe))
    if modern_conmebol and recipe.get("samerica_super_cup", True) and SUDAM in {c["number"] for c in cups}:
        cups.append(samerica_super_cup(recipe))
    for c in cups:
        k = str(c["number"])
        c["name"] = ((recipe.get("ccup_names") or {}).get(k) or "").strip() or c["name"]
        c["logo"] = (recipe.get("ccup_logos") or {}).get(k) or c.get("logo")
        if "|" in c["name"]:
            raise BuildError("%s: a name cannot have a | in it" % c["name"])
    if len(cups) + len(home) > MAX_CCUP:
        raise BuildError("%d continental, league and pre-season cups -- fl26swiss.dll takes %d"
                         % (len(cups) + len(home), MAX_CCUP))
    return {"world": recipe["world"], "leagues": out, "others": others, "edits": recipe.get("edits") or {},
            "free_ids": free_ids, "players": recipe.get("players") or {}, "uecl": bool(recipe.get("uecl", True)),
            "skipped": [t for _pr, t in stale] + fnotes,        # what Build leaves out, with why
            "trophies": dict(recipe.get("trophies") or {}),     # Leagues > More > Trophies (lbtrophies)
            "uecl_logo": recipe.get("uecl_logo") or None,
            "uecl_name": (recipe.get("uecl_name") or "").strip() or None,
            "game_europe": ge, "game_replace": gr, "game_names": gn,
            "association_access": aaccess,
            "conmebol_associations": arows, "conmebol_associations_recipe": arecipe,
            "conmebol_stages": conmebol_stages,
            "libq": libq,
            "modern_libertadores_access": access_recipe.get("_modern_libertadores_access"),
            "suda_first": suda_first,
            "uefa_seed": uefa_seed(recipe, out, regrow, region_of_cid),
            "ccups": cups, "ccup_notes": notes, "home_cups": home, "game_supers": gsupers,
            "europe_first": europe_first(recipe, by_name),
            "game_seasons": august_countries(recipe),
            "editable_kits": bool(recipe.get("editable_kits")),
            "make_kits": recipe.get("make_kits", True) is not False,
            "replaced_kits": recipe.get("replaced_kits", True) is not False,
            "pack_faces": recipe.get("pack_faces", True) is not False,
            "country_order": recipe.get("country_order") or None,
            "cup_draw": cup_draw(recipe),
            # the cups' ids of the last Build, {key: {cid, reg, ...}}: build() gives each its own back
            "prev_cup_ids": kept_cups(prev_cups, names, [s["code"] for s in gsupers]),
            # B159: a world built with competition ids under 130 (eu4, r12) goes on with them
            "low_cids": low,
            # the recipe's keys kept as they were, for recipe_from_plan (RECIPE_SETTINGS)
            "settings": {k: copy.deepcopy(full[k]) for k in RECIPE_SETTINGS if k in full}}


def low_cids(prev):
    """B159 (AHMED, Tysonche35 19.10.): the last Build gave a league or a cup a competition id
    under CID_FROM (eu4 and r12 were built with FL26_LOW_CIDS=1). Such a world keeps the low ids
    in its pool: without them its own cups found no id ("no free competition ids left", or out
    of ids for a cup) on a Build with nothing changed"""
    p = prev or {}
    cids = [L.get("cid") for L in (p.get("leagues") or []) + (p.get("others") or []) if isinstance(L, dict)]
    cids += [w.get("cid") for w in (p.get("cup_ids") or {}).values() if isinstance(w, dict)]
    return any(isinstance(c, int) and c < CID_FROM for c in cids)


def kept_cups(ids, names, codes=None):
    """the cups' ids of the last Build (renamed_cups) less those of cups the recipe has no more:
    a league taken out held its national and super cup's ids for good (B159), and they are the
    ones a world near 255 competitions needs. `codes`: the game super cups still there, None
    keeps them all"""
    have = {n.lower() for n in names}
    out = {}
    for k, w in ids.items():
        kind, _, name = k.partition(":")
        if kind in ("cup", "super") and name.lower() not in have:
            continue
        if kind == "gsuper" and codes is not None and name not in codes:
            continue
        out[k] = w
    return out


def renamed_cups(ids, renamed):
    """the cups' ids of the last Build (plan's cup_ids), with a renamed league's national cup and
    super cup under its name now: they are keyed by the league's name ("cup:<name>"), and a
    career holds their ids as it holds the league's (built_as, plan above)"""
    out = dict(ids)
    for nm, was in renamed.items():
        for kind in ("cup", "super"):
            old = next((k for k in ids if k.lower() == "%s:%s" % (kind, was)), None)
            if old and "%s:%s" % (kind, nm) not in out:
                out["%s:%s" % (kind, nm)] = out.pop(old)
    return out


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


def newlife_of(L):
    """a league's "newlife" as the plan keeps it: the clubs' NewLife ids (None: a club of its own,
    Dale pack) and, as the recipe had them, the release's version and league key, which only the
    NewLife page reads (recipe_from_plan gives them back)"""
    nl = L.get("newlife") if isinstance(L.get("newlife"), dict) else {}
    out = {"clubs": [int(i) if str(i or "").strip().isdigit() else None for i in nl.get("clubs") or []]}
    out.update({k: copy.deepcopy(v) for k, v in nl.items() if k != "clubs"})
    return out


def others_plan(groups, base, cty, pins=None):
    """the plan of the recipe's clubs in no league (the "others" key): what plan() makes of a
    league, less everything that belongs to a competition. `pins`: prev_pins of the last
    Build's groups, whose new clubs keep their team ids as a league's do (prev_teams)"""
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
             "newlife": newlife_of(L),
             "game_clubs": {}}
        q = (pins or {}).get(name.lower()) or {}
        if q.get("teams"):
            # a league removed in front of the group moved its clubs' ids (0.2.4, editing a world)
            p["prev_teams"] = [t if isinstance(t, int) else None for t in q["teams"]]
            p["prev_names"] = [str(x or "").strip().lower() for x in (q.get("club_names") or [])]
        if len(p["club_names"]) > n:
            raise BuildError("%s: %d club names for %d clubs" % (name, len(p["club_names"]), n))
        p["formation_notes"] = known_formations(p, base, name)
        out.append(p)
    return out


def game_club_checks(out, base, errs=None):
    """the clubs of the game the leagues of plan `out` take (game_places): each usable, each in
    one place only, and each that plays anywhere in the game (a league, a cup, a continental
    competition) with a club to take its place there -- one in no competition at all, or a new
    one ({"name": ...}), so every competition keeps its number of clubs. Normalises "swap" to
    None, a team id or {"name": ...}. errs: a list to add the problems to (with where they
    are, see plan), not raised"""
    if not any(p.get("game_clubs") for p in out):
        return
    info = game_info(base)
    names = [p["name"] for p in out]

    def bad_(text):
        if errs is None:
            raise BuildError(text)
        _problem(errs, names, text)
    used = {}
    for p in out:
        for at, g in sorted(p["game_clubs"].items()):
            tid = g["id"]
            bad = game_club_problem(info, tid)
            if bad:
                bad_("%s, club %d: %s" % (p["name"], at + 1, bad))
                g["bad"] = True
                continue
            if tid in used:
                bad_("%s, club %d: %s is in %s and in %s: a club plays in one league"
                     % (p["name"], at + 1, club_label(info, tid), used[tid], p["name"]))
                continue
            used[tid] = p["name"]
    for p in out:
        for at, g in sorted(p["game_clubs"].items()):
            if g.pop("bad", False):
                continue
            tid, sw = g["id"], g.get("swap")
            name = club_label(info, tid)
            where = game_club_where(info, tid, g.get("keep"))
            if not where:
                g["swap"] = None                     # nothing to hand over
                continue
            if sw in (None, "", {}, 0):
                cont = not game_club_where(info, tid, True)
                bad_("%s, club %d: %s plays in %s -- pick the club that takes its place there%s"
                                 % (p["name"], at + 1, name, ", ".join(where),
                                    " (or tick 'It keeps its places in continental competitions' in Club of "
                                    "the game)" if cont else ""))
                continue
            if isinstance(sw, dict):
                nm = str(sw.get("name") or "").strip()
                if not nm:
                    bad_("%s, club %d: the new club taking %s's place needs a name"
                                     % (p["name"], at + 1, name))
                    continue
                g["swap"] = {"name": nm}
                continue
            try:
                sid = int(sw)
            except (TypeError, ValueError):
                bad_("%s, club %d: %r is not a club of the game" % (p["name"], at + 1, sw))
                continue
            bad = game_club_problem(info, sid)
            if bad:
                bad_("%s, club %d: the club taking %s's place: %s" % (p["name"], at + 1, name, bad))
                continue
            if info["entries"].get(sid):
                bad_("%s, club %d: %s already plays in %s; the club taking %s's place must be one"
                                 " that plays in nothing" % (p["name"], at + 1, info["clubs"][sid][0],
                                                            ", ".join(game_club_where(info, sid)), name))
                continue
            if sid in used:
                bad_("%s is used twice (%s)" % (info["clubs"][sid][0], used[sid]))
                continue
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
    clash = id_mask_clash(have)
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
        while nxt in taken or nxt in clash:
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


def league_ko_cup(tiers, calendar=False):
    """a single-match league cup of tiers [(league, clubs)] -- the top division and the divisions
    under it, top first: its entries, the top division's places first and then the next
    division's, cut to the largest of LEAGUE_KO_SIZES there are clubs for (only the first two
    divisions play), and its options; (None, None) under LEAGUE_KO_SIZES[0] clubs.
    The options keep the id the two-legged cup's pre-round had (`reserve`): that cup took the
    biggest of LEAGUE_CUP_SIZES its divisions filled and a pre-round of the rest, and every cup
    built after it in the same world keeps the regulation id it had."""
    field = [(r, pos) for r, n in tiers[:2] for pos in range(1, n + 1)]
    size = max((s for s in LEAGUE_KO_SIZES if s <= len(field)), default=None)
    if size is None:
        return None, None
    old = []
    for r, n in tiers:
        if len(old) >= LEAGUE_CUP_SIZES[0]:
            break
        old += [(r, pos) for pos in range(1, n + 1)]
    _main, pre = cup_field(old)
    return field[:size], {"fill": LEAGUE_CUP_FILL if calendar else LEAGUE_KO_FILL, "national": 1,
                          "days": LEAGUE_KO_CAL_DAYS if calendar else LEAGUE_KO_DAYS,
                          "like": LEAGUE_KO_LIKE, "draw": "byes", "reserve": 1 if pre else 0}


def league_cup(p, out):
    """the league cup of top division p: a single-match knockout of its division and the one
    below it (the recipe's), league_ko_cup"""
    tiers, q = [], p
    while q and len(tiers) < 4:
        tiers.append((q["rid"], q["clubs"]))
        q = next((b for b in out if b["above"] == q["rid"]), None)
    field, opts = league_ko_cup(tiers, bool(p.get("calendar") or p.get("follows_calendar")))
    if field is None:
        raise BuildError("%s has %d clubs, a league cup needs %d"
                         % (p["name"], p["clubs"], LEAGUE_KO_SIZES[0]))
    return {"name": p["league_cup"]["name"], "code": "FL_%03d_LCUP" % p["rid"], "kind": "league",
            "logo": p["league_cup"].get("logo"),
            "country": p["country"], "region": p["region"], "groups": 0, "entry": field,
            "opts": opts}


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


# Synthetic access source for a CONMEBOL association with no playable domestic league
# in this world. Real regulation ids and their replicas stay below 0x8000; the
# low nine bits carry Country.bin's id.
ASSOC_SOURCE = 0x8000
ASSOC_COUNTRY_MASK = 0x01ff
FINAL_ASSOC_RANK = 40

CONMEBOL_MODERN = "modern"                 # the recipe's "conmebol" for the modern competitions


def _comp_of(e):
    """a place's competition, or None for a malformed one"""
    try:
        return int(e[1])
    except (TypeError, ValueError, IndexError):
        return None


def modern_conmebol_places(recipe):
    """the places of the recipe only the modern CONMEBOL competitions have: a new league's or a
    game league's place in Libertadores phase 1, 2 or 3 or the Sudamericana's first stage
    (fl26world.CONMEBOL_STAGE_IDS), and every CONMEBOL association rank. [(where, position,
    competition)], where a league's name, "g<regulation>" for a league of the game or
    "a:<country>" for an association: what turning the modern competitions off takes out"""
    out = []
    for L in recipe.get("leagues") or []:
        out += [(L.get("name") or "?", e[0], _comp_of(e)) for e in L.get("europe") or []
                if _comp_of(e) in fl26world.CONMEBOL_STAGE_IDS]
    for key, places in sorted((recipe.get("game_europe") or {}).items(), key=lambda kv: str(kv[0])):
        out += [("g%s" % key, e[0], _comp_of(e)) for e in places or []
                if _comp_of(e) in fl26world.CONMEBOL_STAGE_IDS]
    assoc = recipe.get("conmebol_associations") or {}
    for key, places in sorted(assoc.items() if isinstance(assoc, dict) else [], key=lambda kv: str(kv[0])):
        out += [("a:%s" % key, e[0], _comp_of(e)) for e in places or [] if isinstance(e, (list, tuple))]
    return out


def recipe_has_modern_conmebol(recipe):
    """whether the world builds the modern CONMEBOL competitions (PR #146): only when the user
    picks them -- the recipe's "conmebol": "modern" (Mod Studio: South American places > Modern
    CONMEBOL competitions), or a place only they have (modern_conmebol_places). Places in the
    Libertadores, its qualifying round and the Copa Sudamericana alone (competitions 3, 4 and 9)
    are the classic ones every world before 0.2.5 has, and such a world builds exactly as before
    (review of #146: the Modpack r7 went from building to "modern CONMEBOL setup is incomplete")"""
    v = recipe.get("conmebol")
    if v not in (None, "", CONMEBOL_MODERN):
        raise BuildError('conmebol: %r -- "modern" or nothing' % (v,))
    return v == CONMEBOL_MODERN or bool(modern_conmebol_places(recipe))


def drop_modern_conmebol(recipe):
    """turn the modern CONMEBOL competitions off in the recipe (in place): its "conmebol", the
    places only they have and the association ranks (modern_conmebol_places) go; Libertadores,
    qualifying and Copa Sudamericana places stay, as the classic competitions'. Returns how
    many places were taken out"""
    gone = len(modern_conmebol_places(recipe))
    recipe.pop("conmebol", None)
    recipe.pop("conmebol_associations", None)
    for L in recipe.get("leagues") or []:
        if L.get("europe"):
            L["europe"] = [e for e in L["europe"] if _comp_of(e) not in fl26world.CONMEBOL_STAGE_IDS]
    ge = recipe.get("game_europe") or {}
    for key in list(ge):
        ge[key] = [e for e in ge[key] or [] if _comp_of(e) not in fl26world.CONMEBOL_STAGE_IDS]
    return gone


def modern_libertadores_recipe(recipe, base):
    """Return the effective South-American access recipe.

    Vanilla mode leaves FL26's Libertadores untouched.
    Custom mode replaces all shipped South-American domestic access first,
    then uses only the places explicitly configured by the user. This prevents
    hidden vanilla Libertadores/qualifying berths from surviving beside the
    modern allocation.
    """
    out = dict(recipe)
    custom = recipe_has_modern_conmebol(recipe)
    out["_modern_libertadores_access"] = "custom" if custom else "vanilla"

    if custom:
        raw_game = recipe.get("game_europe") or {}
        game = {str(k): [list(e) for e in (v or [])]
                for k, v in raw_game.items()}
        available = {r for r, _n, _clubs, _shipped in game_europe_tops(base)}

        # Empty game_europe means: replace the game's shipped access with none.
        # Explicit user rows remain untouched.
        for rid, _lib, _libq in fl26world.SAM_GAME:
            if rid not in available:
                continue
            key = next((k for k in game if str(k) == str(rid)), str(rid))
            game.setdefault(key, [])

        out["game_europe"] = game

    return out


def validate_modern_conmebol_access(leagues, game_access, association_access, stages, continental_places):
    """Require the complete modern package by GLOBAL totals, not country quotas."""
    counts = {
        3: 0,
        fl26world.LIB_F1: 0,
        fl26world.LIB_F2: 0,
        fl26world.LIB_F3: 0,
        9: 0,
        fl26world.SUD_FIRST: 0,
    }

    for p in leagues:
        for e in p.get("europe") or []:
            try:
                comp = int(e[1])
            except (TypeError, ValueError, IndexError):
                continue
            if comp == 3:
                counts[3] += 1

    # Shipped leagues / synthetic associations feed native Libertadores through
    # the normal access list.
    for row in list(game_access) + list(association_access):
        try:
            comp = int(row[2])
        except (TypeError, ValueError, IndexError):
            continue
        if comp == 3:
            counts[3] += 1

    # Every direct Sudamericana place (new league, shipped league or synthetic
    # association) is normalized into continental_places / ccup_plan input.
    for row in continental_places:
        try:
            comp = int(row[2])
        except (TypeError, ValueError, IndexError):
            continue
        if comp == 9:
            counts[9] += 1

    for row in stages:
        try:
            comp = int(row[2])
        except (TypeError, ValueError, IndexError):
            continue
        if comp in (fl26world.LIB_F1, fl26world.LIB_F2,
                    fl26world.LIB_F3, fl26world.SUD_FIRST):
            counts[comp] += 1

    expected = (
        (3, 26, "Libertadores groups"),
        (fl26world.LIB_F2, 13, "Libertadores Fase 2"),
        (fl26world.LIB_F1, 6, "Libertadores Fase 1"),
        (fl26world.LIB_F3, 0, "Libertadores Fase 3 direct"),
        (9, 12, "Copa Sudamericana groups"),
        (fl26world.SUD_FIRST, 32, "Copa Sudamericana Fase 1"),
    )
    bad = [(label, counts[comp], want)
           for comp, want, label in expected if counts[comp] != want]
    if bad:
        detail = "; ".join("%s %d/%d" % (label, got, want)
                           for label, got, want in bad)
        raise BuildError(
            "modern CONMEBOL setup is incomplete: %s. "
            "Once Libertadores or Sudamericana access is customized, the complete "
            "global allocation is required. Places may be distributed among South "
            "American sources however you want." % detail
        )

    return counts


def assoc_source(country):
    country = int(country)
    if not 0 < country <= ASSOC_COUNTRY_MASK:
        raise BuildError("CONMEBOL association: country id %d is outside 1..%d" %
                         (country, ASSOC_COUNTRY_MASK))
    return ASSOC_SOURCE | country


def association_club_capacity(base, country):
    """Number of playable real clubs Team.bin exposes for one Country.bin id.

    This is only a capability check. fl26swiss ranks the available association
    clubs dynamically at runtime; the recipe never contains team ids.
    """
    info = game_info(base)
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    n = 0
    for o in range(0, len(raw), W.T_REC):
        r = raw[o:o + W.T_REC]
        tid = int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")
        own = (int.from_bytes(r[T_COUNTRY:T_COUNTRY + 2], "little") >> 2) & 0x1ff
        if own != country or tid in info["national"]:
            continue
        name = (info["clubs"].get(tid) or ("", ""))[0]
        if not name or special_team(name) or info["squads"].get(tid, 0) < MIN_GAME_SQUAD:
            continue
        n += 1
    return n


def conmebol_association_places(recipe, base, leagues):
    """Normalize recipe-level CONMEBOL association access.

    Format stays the normal two-field place schema: {country: [[rank, target], ...]}.
    `target` may be Libertadores (3), Sudamericana groups (9), or one of the logical
    modern stage ids 16..19. If this world has that country's top league, its real
    regulation becomes the source; otherwise 0x8000|country is resolved dynamically
    by fl26swiss. A missing rank stays unresolved and never steals another association's berth.
    """
    raw = recipe.get("conmebol_associations") or {}
    if not raw:
        return [], [], [], [], {}
    if not isinstance(raw, dict):
        raise BuildError("conmebol_associations must be an object: country -> places")

    ids = country_ids(base)
    by_label = {str(n).strip().lower(): i for n, i in ids}
    conf = confederations(base)
    game_tops = game_top_division_countries(base)
    tops = {}
    for p in leagues:
        if p.get("above"):
            continue
        tops.setdefault(p.get("country"), []).append(p)

    access, ccup, staged, rows, normalized = [], [], [], [], {}
    allowed = {3, 9} | set(fl26world.CONMEBOL_STAGE_IDS)

    for key, places in sorted(raw.items(), key=lambda kv: str(kv[0]).lower()):
        if str(key).strip().isdigit():
            country = int(str(key).strip())
            name = next((n for n, i in ids if i == country), str(country))
        else:
            label = str(key).strip().lower()
            if label not in by_label:
                raise BuildError("CONMEBOL association %r is not a country in Country.bin" % (key,))
            country = by_label[label]
            name = next(n for n, i in ids if i == country)

        if conf.get(country) != 4:
            raise BuildError("CONMEBOL association %s (country %d) is not CONMEBOL" % (name, country))
        if not isinstance(places, (list, tuple)):
            raise BuildError("CONMEBOL association %s: places must be a list" % name)

        leagues_here = tops.get(country) or []
        if not leagues_here and country in game_tops:
            gr, gn = game_tops[country]
            raise BuildError("CONMEBOL association %s already has the game's top division %s (reg %d); "
                             "set that league's Own places instead" % (name, gn, gr))
        if len(leagues_here) > 1:
            raise BuildError("CONMEBOL association %s has more than one top division in this world (%s)" %
                             (name, ", ".join(p["name"] for p in leagues_here)))
        if leagues_here:
            source = leagues_here[0]["rid"]
            capacity = leagues_here[0]["clubs"]
            how = "league %s (reg %d)" % (leagues_here[0]["name"], source)
        else:
            source = assoc_source(country)
            capacity = association_club_capacity(base, country)
            how = "association clubs in Team.bin"

        seen, norm, unresolved = set(), [], 0
        for e in places:
            try:
                if len(e) != 2:
                    raise ValueError
                rank, comp = int(e[0]), int(e[1])
            except (TypeError, ValueError, IndexError):
                raise BuildError("CONMEBOL association %s: %r is not [rank, competition]" % (name, e))
            if not 1 <= rank <= FINAL_ASSOC_RANK:
                raise BuildError("CONMEBOL association %s: rank %d is outside 1..%d" %
                                 (name, rank, FINAL_ASSOC_RANK))
            if rank in seen:
                raise BuildError("CONMEBOL association %s: rank %d is listed twice" % (name, rank))
            if comp not in allowed:
                raise BuildError("CONMEBOL association %s: competition %d is not a modern Libertadores/Sudamericana target" %
                                 (name, comp))
            seen.add(rank)
            norm.append([rank, comp])
            unresolved += rank > capacity

            if comp == 3:
                access.append((source, rank, 3, 0))
            elif comp == 9:
                ccup.append((source, rank, 9, 0))
            else:
                staged.append((source, rank, comp, conmebol_stage(comp), 0))

        normalized[name] = norm
        rows.append({"name": name, "country": country, "source": source, "capacity": capacity,
                     "requested": len(norm), "max_rank": max(seen) if seen else 0,
                     "unresolved": unresolved, "how": how})

    return access, ccup, staged, rows, normalized


def game_europe(recipe, regrow, region_of_cid, base):
    """The recipe's game_europe.

    Logical modern-CONMEBOL targets are consumed before the normal access list:
      LIB_F1 / LIB_F2 -> custom qualifying phases
      LIB_F3          -> native Libertadores qualifying (competition target 4)
      SUD_FIRST       -> Sudamericana national first stage

    The function keeps the existing four-value return contract:
    (normal access, shipped regulations replaced, names, League-Builder cups).
    """
    ge = recipe.get("game_europe") or {}

    if not ge:
        return [], [], {}, []

    tops = {r: n for r, _c, n, _t in game_leagues(base)}
    ccups = {c: n for c, n, _code, _conf, _fill in fl26world.CCUPS}
    logical = set(fl26world.CONMEBOL_STAGE_IDS)

    places, replace, names, cc = [], [], {}, []

    for key, europe in sorted(ge.items(), key=lambda kv: str(kv[0])):
        try:
            rid = int(key)
        except (TypeError, ValueError):
            raise BuildError("European places: %r is not a league of the game" % (key,))

        if rid not in tops or M.get_tier(regrow[rid]) != 1:
            raise BuildError(
                "European places: regulation %d is not a top division of the game" % rid
            )

        clubs = entries_of(base, regrow[rid][M.R_CID])
        cup = home_cup(
            regrow,
            region_of_cid,
            region_of_cid.get(regrow[rid][M.R_CID])
        )

        bad = europe_problems(clubs, europe or [], cup is not None)

        bad += [
            "competition %d is not one a league's place can lead to" % int(e[1])
            for e in europe or []
            if str(e[1]).isdigit()
            and int(e[1]) not in fl26world.UEFA_LINE
            and int(e[1]) not in ccups
            and int(e[1]) not in logical
        ]

        if bad:
            raise BuildError(
                "European places of %s: %s"
                % (tops[rid], "; ".join(bad))
            )

        source = access_reg(rid, regrow, region_of_cid)
        normal = []
        access_touched = False

        for pos, comp in europe or []:
            pos, comp = int(pos), int(comp)

            if comp == fl26world.SUD_FIRST:
                # Kept only in game_stage_places().
                continue

            if comp in (fl26world.LIB_F1, fl26world.LIB_F2):
                # These replace the shipped continental allocation but do not
                # enter native Libertadores qualifying directly.
                access_touched = True
                continue

            if comp == fl26world.LIB_F3:
                access_touched = True
                normal.append((pos, 4))
                continue

            if comp in ccups:
                cc.append((rid, pos, comp, 0))
                continue

            access_touched = True
            normal.append((pos, comp))

        if access_touched:
            replace.append(source)
            names[str(source)] = tops[rid]

            places += [
                (cup, 0, comp, source)
                if pos == CUP_WINNER
                else (source, pos, comp, 0)
                for pos, comp in normal
            ]

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
    places = (own_places(pl) + [tuple(e) for e in pl.get("game_europe") or []]
              + [tuple(e) for e in pl.get("association_access") or []])
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


def game_top_division_countries(base):
    """{Country.bin id: (regulation, league name)} for the game's playable top divisions.

    Used by Mod Studio's CONMEBOL association editor: an association that already has a
    playable top division must be configured through that league, not through the synthetic
    0x8000|country source.
    """
    regs = M.load(base, "CompetitionRegulation.bin")
    regrow = {u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG:(i + 1) * M.REG]
              for i in range(len(regs) // M.REG)}
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    country = {}
    for o in range(0, len(raw), W.T_REC):
        r = raw[o:o + W.T_REC]
        tid = int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")
        country[tid] = (int.from_bytes(r[T_COUNTRY:T_COUNTRY + 2], "little") >> 2) & 0x1ff
    out = {}
    for rid, _cid, name, teams in game_leagues(base):
        if rid not in regrow or M.get_tier(regrow[rid]) != 1:
            continue
        seen = {}
        for tid in teams:
            c = country.get(tid, 0)
            if c:
                seen[c] = seen.get(c, 0) + 1
        if seen:
            c = max(seen, key=seen.get)
            out[c] = (rid, name)
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


def competition_ids(db, base=None):
    """[(competition id, [regulation ids], name, kind, new)] of every competition in the tables at
    <db> (a built world's, or the game's), by id: the ids modules, Sider maps and scoreboards ask
    for, on one page instead of in the files (the poll, LumpierTheGunner and Bon Kirk 11.10.).
    kind is "league" or "cup"; new = not in the tables at <base> (the world made it)."""
    regs = M.load(db, "CompetitionRegulation.bin")
    old = None
    if base and os.path.abspath(base) != os.path.abspath(db):
        try:
            b = M.load(base, "CompetitionRegulation.bin")
            old = {b[i * M.REG + M.R_CID] for i in range(len(b) // M.REG)}
        except (OSError, ValueError):
            old = None
    out = {}
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        c, rid = g[M.R_CID], u16(g, M.R_ID)
        if rid >= 1024:                           # a group or phase row of a competition
            continue
        name = text(g[M.R_NAME + ENGLISH * M.NAME_SLOT:M.R_NAME + (ENGLISH + 1) * M.NAME_SLOT])             or text(g[M.R_NAME:M.R_NAME + M.NAME_SLOT])
        e = out.setdefault(c, [name, [], "cup", old is not None and c not in old])
        e[1].append(rid)
        if g[M.R_TYPE] in (4, fl26world.SPLIT_TOTAL):
            e[2] = "league"
        if not e[0]:
            e[0] = name
    return [(c, sorted(r), n, k, new) for c, (n, r, k, new) in sorted(out.items())]


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
    """the recipe's game_cups for top divisions of the game: (league cups, the same fl26swiss
    cups league_cup() gives a new country; super cups where the region has none, built as a new
    country's by game_super_cups())"""
    res, supers, seen = [], [], set()
    tops = {r for r, _c, _n, _t in game_leagues(base)} if recipe.get("game_cups") else set()
    moved_regions = {GAME_SEASONS[n][0] for n in recipe.get("game_seasons") or [] if n in GAME_SEASONS}
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
            tiers, q = [], rid
            while q and len(tiers) < 4:
                mine = next((p for p in out if p["rid"] == q), None)
                n = mine["clubs"] if mine else entries_of(base, regrow[q][M.R_CID])
                tiers.append((q, n))
                below = u16(regrow[q], M.R_BELOW) if q in regrow else 0
                q = (below if below in regrow else 0) or next((p["rid"] for p in out if p["above"] == q), None)
            moved = {GAME_SEASONS[n][0] for n in recipe.get("game_seasons") or [] if n in GAME_SEASONS}
            field, opts = league_ko_cup(tiers, region in CALENDAR_REGIONS and region not in moved)
            if field is None:
                raise BuildError("game cups: %s has %d clubs, a league cup needs %d"
                                 % (league, sum(t[1] for t in tiers[:2]), LEAGUE_KO_SIZES[0]))
            res.append({"name": (c.get("name") or "").strip() or league + " League Cup",
                        "code": "FL_G%03d_LCUP" % rid, "kind": "league", "logo": c.get("logo") or None,
                        "country": None, "conf": conf, "region": region, "groups": 0, "entry": field,
                        "opts": opts})
        if c.get("super_cup"):
            if home_supercup(regrow, region_of_cid, region):
                raise BuildError("game cups: %s already has a super cup in the game" % league)
            # the game's own super cup shape, as a new league's (national_cups: a copy of
            # SUPER_CUP_LIKE, two clubs) -- not a fl26swiss knockout on the FA Cup's row: the game
            # fills a format-2 cup of a region from its leagues, so the Supercopa de Chile and Rei
            # came out a 16- and 26-club bracket, drawn in July from the table of a February-
            # December league still running and never played right (Vicentico 13.10.)
            # league, cup, region and conf go to the world file's gsuper line (gsuper_lines): in a
            # February-December country the season the game builds at New Year takes only the
            # shipped cups, so fl26joindll adds ours to it (with its confederation), and
            # fl26swiss fills it with the champion and the cup winner of the season just ended
            # -- what a new league's scup= gives its own super cup. Without them the Supercopa
            # de Chile and Rei were dated in January but never entered a season (Vicentico 13.10.)
            supers.append({"name": (c.get("super_name") or "").strip() or league + " Super Cup",
                           "code": "FL_G%03d_SCUP" % rid, "logo": c.get("super_logo") or None,
                           "league": rid, "league_cid": g[M.R_CID], "region": region,
                           "cup": home_cup(regrow, region_of_cid, region) or 0, "conf": conf or 0,
                           "calendar": region in CALENDAR_REGIONS and region not in moved_regions})
    return res, supers


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
    busy = ap + cl + (CCUP_DAYS if p.get("europe") else []) + (LEAGUE_KO_DAYS if p.get("league_cup") else [])
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


def samerica_super_cup(recipe):
    """The Recopa Sudamericana: previous Libertadores winner v previous Sudamericana winner.

    The Libertadores is native (regulation 10); Sudamericana is one of our cups and is resolved
    by continental() after its knockout id is known.  number=-1 is deliberately outside
    fl26world.CCUPS so it cannot collide with the Sudamericana/CAF lookups.
    """
    opts = {"fill": SAM_SUPER_FILL, "national": 1, "days": list(SAM_SUPER_DAYS), "cal": 1}
    first = recipe.get("samerica_super_cup_first")
    if first:
        if (not isinstance(first, (list, tuple)) or len(first) != 2
                or not all(str(t).isdigit() and 0 < int(t) < 65536 for t in first)):
            raise BuildError("samerica_super_cup_first: %r -- two team ids of the game" % (first,))
        if int(first[0]) == int(first[1]):
            raise BuildError("samerica_super_cup_first: the two clubs must be different")
        opts["first"] = [int(first[0]), int(first[1])]
    return {"number": -1, "name": "Recopa Sudamericana", "code": "FL_SAMRC", "conf": 4, "groups": 0,
            "kind": "super", "logo": recipe.get("samerica_super_cup_logo") or None,
            "entry": [(LIBERTADORES_KO, 0), ("ko", SUDAM)], "opts": opts}


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
    # Calendar-year cups already use the English case-6 calendar. Use its
    # knockout shape too, rather than mixing another cup shape with those dates.
    if (p.get("calendar") or p.get("follows_calendar")) and n <= NATIONAL_CUP_MAX:
        c["like"], c["bracket"] = NATIONAL_CUP_ANY
        c["clubs"], c["keep_top"] = n, False
    elif n in exact:
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


def conmebol_stage(comp):
    """The internal stage name of a logical CONMEBOL access target, or None."""
    q = fl26world.CONMEBOL_STAGE_TARGETS.get(int(comp))
    return q[2] if q else None


def conmebol_native_target(comp):
    """The old/native target a logical CONMEBOL destination ultimately feeds."""
    q = fl26world.CONMEBOL_STAGE_TARGETS.get(int(comp))
    return q[1] if q else int(comp)


def own_stage_places(pl):
    """Logical CONMEBOL stage places of new leagues.

    A normal row is (league, position, target, stage, 0). A cup-winner row keeps
    the same two-field recipe but becomes (cup regulation, 0, target, stage, league):
    the last value is the same-source fallback when there is no eligible cup winner.
    """
    out = []
    for p in pl["leagues"]:
        for pos, comp in p.get("europe") or []:
            pos, comp = int(pos), int(comp)
            if comp not in fl26world.CONMEBOL_STAGE_IDS:
                continue
            if pos == CUP_WINNER:
                # A new national cup gets its real regulation id only during Build,
                # in national_cups(). Keep the league regulation as a logical
                # placeholder here so Check/plan can count the place already.
                out.append((p["rid"], CUP_WINNER, comp, conmebol_stage(comp), p["rid"]))
            else:
                out.append((p["rid"], pos, comp, conmebol_stage(comp), 0))
    return out


def resolve_new_league_stage_cup_winners(pl):
    # Resolve plan-time cup-winner placeholders after national_cups().
    cups = {
        int(p["rid"]): int((p.get("own_cup") or {}).get("reg") or 0)
        for p in pl.get("leagues") or []
    }

    def resolve(e):
        reg, rank, fallback = int(e[0]), int(e[1]), int(e[2] or 0)
        if rank == CUP_WINNER and fallback and reg == fallback:
            cup = cups.get(fallback, 0)
            if not cup:
                raise BuildError(
                    "modern CONMEBOL: cup-winner place for league regulation %d, "
                    "but its national cup was not built" % fallback
                )
            return (cup, rank, fallback)
        return (reg, rank, fallback)

    q = pl.get("libq")
    if q:
        for key in ("phase1", "phase2"):
            q[key] = [resolve(e) for e in q.get(key) or []]

    q = pl.get("suda_first")
    if q:
        q["ties"] = [
            [resolve(e) for e in tie]
            for tie in q.get("ties") or []
        ]

    stages = []
    for e in pl.get("conmebol_stages") or []:
        reg, rank, comp, stage, fallback = e
        reg, rank, fallback = resolve((reg, rank, fallback))
        stages.append((reg, rank, comp, stage, fallback))
    if stages:
        pl["conmebol_stages"] = stages


def game_stage_places(recipe, regrow, region_of_cid, base):
    """Logical CONMEBOL stage places belonging to leagues of the game.

    Cup-winner rows carry the national cup as their source and the league as their
    same-source cascade fallback; ordinary rows use the league source directly.
    """
    ge = recipe.get("game_europe") or {}
    out = []
    tops = {r: n for r, _c, n, _t in game_leagues(base)}

    for key, europe in sorted(ge.items(), key=lambda kv: str(kv[0])):
        try:
            rid = int(key)
        except (TypeError, ValueError):
            continue

        if rid not in tops or rid not in regrow:
            continue

        source = access_reg(rid, regrow, region_of_cid)
        cup = home_cup(regrow, region_of_cid, region_of_cid.get(regrow[rid][M.R_CID]))

        for e in europe or []:
            try:
                pos, comp = int(e[0]), int(e[1])
            except (TypeError, ValueError, IndexError):
                continue

            if comp in fl26world.CONMEBOL_STAGE_IDS:
                if pos == CUP_WINNER and cup:
                    out.append((cup, 0, comp, conmebol_stage(comp), source))
                elif pos != CUP_WINNER:
                    out.append((source, pos, comp, conmebol_stage(comp), 0))

    return out


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
    """Normal continental access places of the new leagues.

    F1/F2 and Sudamericana first-stage places are consumed by the modern
    CONMEBOL stage machinery and must not also enter a native competition.
    F3 is translated to the game's normal Libertadores qualifying target (4).
    """
    out = []

    for p in pl["leagues"]:
        for pos, comp in p.get("europe") or []:
            pos, comp = int(pos), int(comp)

            if comp in (fl26world.LIB_F1, fl26world.LIB_F2, fl26world.SUD_FIRST):
                continue

            comp = conmebol_native_target(comp)

            out.append(
                ((p.get("own_cup") or {}).get("reg", 0), 0, comp, p["rid"])
                if pos == CUP_WINNER
                else (p["rid"], pos, comp, 0)
            )

    return out


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
    for t in pl.get("skipped") or []:
        lines.append("  note: " + t)
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
    if pl.get("modern_libertadores_access") != "custom":
        libq = sum(1 for e in own_places(pl) if e[2] == 4)
        if libq > LIBQ_ROOM:
            # Legacy Libertadores mode: fl26swiss gives new leagues all but two
            # of the native qualifying round's eight places.
            lines.append("  NOTE: Libertadores qualifying has %d places listed, the round takes %d of them; "
                         "the leagues listed last get none" % (libq, LIBQ_ROOM))
        lib = sum(1 for e in own_places(pl) if e[2] == 3)
        if lib > LIB_ROOM:
            # Legacy Libertadores mode: the native field leaves only the old
            # pool-club replacement room to added leagues.
            lines.append("  NOTE: Copa Libertadores has %d direct places listed, the game leaves %d for new leagues; "
                         "the leagues listed last get none (give the rest qualifying places)" % (lib, LIB_ROOM))
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
                # a February-December country's is dated as dates_lines dates it: the Japanese
                # super cup's records moved to the end of January, after the season
                lines.append("  %s: super cup, the champion v the cup winner (%s)" % (
                    c["super"], "at the end of January, after the February-December season: dated as %s, day %s"
                    % (CALENDAR_SUPER_DATE_LIKE, ",".join(map(str, CALENDAR_SUPER_DATE_DAYS)))
                    if p.get("calendar") or p.get("follows_calendar")
                    else "its date follows %s" % SUPER_CUP_LIKE))
    for cup in pl.get("ccups") or []:
        if cup.get("kind") == "super":
            if cup.get("code") == "FL_SAMRC":
                lines.append("  %s: the previous Libertadores and Sudamericana winners, one "
                             "match in late February (normally first played in a career's second season)"
                             % cup["name"])
            else:
                lines.append("  %s: the winners of the CAF Champions League and the Confederation Cup, one "
                             "match in late July (first played in a career's second season)" % cup["name"])
            continue
        lines.append("  %s: %d clubs, %s" % (cup["name"], len(cup["entry"]),
                                             "%d groups of four, then a knockout of %d"
                                             % (cup["groups"], 2 * cup["groups"]) if cup["groups"]
                                             else "a knockout"))
    if pl.get("conmebol_associations"):
        lines.append("  CONMEBOL association sources (no team ids in the recipe):")
        for a in pl["conmebol_associations"]:
            lines.append("    %s: %d place(s), ranks through %d; %d eligible club(s) from %s%s" % (
                a["name"], a["requested"], a["max_rank"], a["capacity"], a["how"],
                " -- %d requested place(s) unresolved" % a["unresolved"] if a["unresolved"] else ""))
            if a["unresolved"]:
                lines.append("      NOTE: missing ranks stay empty; they are not filled by another CONMEBOL association")
    for note in pl.get("ccup_notes") or []:
        lines.append("  NOTE: " + note)
    own = own_places(pl) + [tuple(e) for e in pl.get("association_access") or []]
    if (pl.get("modern_libertadores_access") != "custom"
            and (any(c["number"] == 9 for c in pl.get("ccups") or [])
                 or any(e[2] in (3, 4, 9) for e in own))):
        sam_names = {p["rid"]: p["name"] for p in pl["leagues"]}
        for a in pl.get("conmebol_associations") or []:
            sam_names[a["source"]] = "%s (association)" % a["name"]
        lines += samerica_lines(own, sam_names, pl.get("ccups") or [])
    for cup in pl.get("home_cups") or []:
        what = {"league": "league cup", "playoff": "playoff, filled on day %d" % cup["opts"]["fill"],
                "super": "super cup in late July"}
        pre = cup["opts"].get("pre")
        lines.append("  %s: %s, a %sknockout of %d clubs%s" % (
            cup["name"], what.get(cup["kind"], "pre-season cup in July"),
            "single-match " if cup["opts"].get("like") else "", len(cup["entry"]),
            ", %d of them from a pre-round of %d clubs in late September"
            % (len(pre["entry"]) // 2, len(pre["entry"])) if pre else ""))
    for s in pl.get("game_supers") or []:
        lines.append("  %s: super cup, the champion v the cup winner, %s" % (
            s["name"], "at the end of January (February-December season)" if s["calendar"]
            else "its date follows %s" % SUPER_CUP_LIKE))
        if s["calendar"] and not pl["leagues"]:
            # fl26joindll puts it into the New Year season only when it installs, and it does not
            # install for a world without a league of its own
            lines.append("  NOTE: %s is played only in a world with at least one new league "
                         "(the season module does not start without one)" % s["name"])
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

# ---- a new club's money and following (2026-10-08) ----
# Every new club is a copy of the last Team.bin record, so each one had that club's transfer
# budget base (raw 0x34, low 24 bits: the Master League budget is it times the money setting's
# factor) and, missing from the club ranking the game fills at career start (750 clubs at most),
# the top club's following: millions of followers for a third-division side. The NewLife data
# carries no reputation or finance fields, so both go by what a club has on the pitch (the mean
# rough overall of its best eleven) and the division it plays in, on a scale read off the
# shipped clubs: a top-flight eleven of 76 has a base about 11000, of 80 about 90000, of 84
# about 1.4M. The following goes to fl26clubs as world lines "fans <class> <percent> <ids>":
# the ranking class (0..9) a club out of the ranking counts as, and the share of the game's
# figure a lower division keeps.
MONEY_BY_OVR = [(66, 300), (70, 1300), (74, 5500), (76, 11000), (78, 22000), (80, 90000),
                (82, 480000), (84, 1400000)]
MONEY_TIER = [1.0, 0.75, 0.5, 0.35, 0.25]          # division 1, 2, ... (the last for any lower)
MONEY_MIN = 500
MONEY_B = [(86, 1200000), (84, 900000), (82, 300000), (80, 50000), (78, 30000)]   # else 10000
FAME_CLASS = [(84, 8), (82, 7), (80, 6), (79, 5), (78, 4), (77, 3), (76, 2), (75, 1)]
FANS_PCT = [100, 40, 15, 8, 5]


def recipe_ordered(filled, clubs):
    """the team ids whose squad order the recipe's players set"""
    team_of = {}
    for p in clubs["leagues"]:
        for k, t in enumerate(p.get("teams") or []):
            team_of["%s/%d" % (p["name"], k)] = t
    out = set()
    for key, c in (filled.get("players") or {}).items():
        if any("order" in ch for ch in (c.get("edits") or {}).values()):
            t = int(key) if str(key).isdigit() else team_of.get(key)
            if t is not None:
                out.add(t)
    return out


def club_strength(rows):
    """the mean rough overall of a squad's best eleven (0 for no squad)"""
    import lbplayers
    lbplayers.SQUAD = SQUAD                # a new club's places: the squads Build makes
    best = sorted((lbplayers.overall(r) for r in rows), reverse=True)[:11]
    return sum(best) / len(best) if best else 0.0


def money_base(q, tier):
    """the transfer budget base of a club of strength q in division tier"""
    import math
    pts = MONEY_BY_OVR
    if q <= pts[0][0]:
        v = pts[0][1]
    elif q >= pts[-1][0]:
        v = pts[-1][1]
    else:
        (x0, y0), (x1, y1) = next((a, b) for a, b in zip(pts, pts[1:]) if a[0] <= q <= b[0])
        v = math.exp(math.log(y0) + (math.log(y1) - math.log(y0)) * (q - x0) / (x1 - x0))
    v *= MONEY_TIER[min(tier, len(MONEY_TIER)) - 1]
    return max(MONEY_MIN, int(round(v / 100.0)) * 100)


def club_money(new_of, pl, db, log=print):
    """sets the money of the new clubs (new_of: {id: league or group}) in db's Team.bin by their
    squads and divisions; returns the world's "fans" lines for fl26clubs"""
    import lbplayers
    lbplayers.SQUAD = SQUAD                # a new club's places: the squads Build makes
    if not new_of:
        return []
    path = os.path.join(db, "Team.bin")
    raw = bytearray(pesdb.wesys_unpack(open(path, "rb").read()))
    mine = {p["rid"]: p for p in pl.get("leagues") or [] if "rid" in p}
    squads = lbplayers.Squads(db)
    groups, n = {}, 0
    for o in range(0, len(raw) - W.T_REC + 1, W.T_REC):
        tid = int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little")
        p = new_of.get(tid)
        if p is None:
            continue
        q = club_strength(squads.squad(tid))
        tier = 1 if p.get("others") else lbplayers.tier_of(p, mine)
        a = money_base(q, tier) & 0xffffff
        b = next((v for m, v in MONEY_B if q >= m), 10000) if tier == 1 else 10000
        x = struct.unpack_from("<I", raw, o + 0x34)[0]
        struct.pack_into("<I", raw, o + 0x34, (x & 0xff000000) | a)
        x = struct.unpack_from("<I", raw, o + 0x38)[0]
        struct.pack_into("<I", raw, o + 0x38, (x & ~0x7fffff & 0xffffffff) | (b & 0x7fffff))
        cls = max(0, next((c for m, c in FAME_CLASS if q >= m), 0) - (tier - 1))
        pct = FANS_PCT[min(tier, len(FANS_PCT)) - 1]
        groups.setdefault((cls, pct), []).append(tid)
        n += 1
    open(path, "wb").write(pesdb.wesys_pack(bytes(raw)))
    lines = []
    for (cls, pct), ids in sorted(groups.items()):
        for k in range(0, len(ids), 64):
            lines.append("fans %d %d %s" % (cls, pct, " ".join(str(t) for t in ids[k:k + 64])))
    log("  money and following for %d new club(s), by squad and division" % n)
    return lines


# words a club's name is filed without (FC Augsburg under A): the game's own lists do the same
CLUB_PREFIX = {"fc", "afc", "ac", "as", "sc", "cd", "ca", "cf", "sl", "sv", "vfb", "vfl", "tsg", "fk", "nk",
               "hnk", "gnk", "ks", "sk", "if", "bk", "rc", "rcd", "ud", "sd", "gd", "ogc", "aj", "us", "ss",
               "ssc", "kv", "krc", "kaa", "rsc", "pfc", "cs", "csd", "club", "the", "rb", "scr", "tsv", "fsv",
               "ssv", "sg", "spvgg", "kfc", "fsc", "nac"}


def club_sort_key(name):
    """a club's place A-Z: without the words it is filed without, and with its letters folded as
    ascii_letters folds them (Đakovo under D, Šibenik under S, Ørsted under O): the code points
    put Đ, Š and Ž after Z (HNK Đakovo Croatia came after Vukovar). Only the order of the entries
    changes, never an id"""
    import unicodedata
    words = name.replace(".", " ").split()
    while len(words) > 1 and words[0].casefold() in CLUB_PREFIX:
        words = words[1:]
    txt = unicodedata.normalize("NFKD", "".join(FOLD.get(c, c) for c in " ".join(words)))
    return "".join(c for c in txt if not unicodedata.combining(c)).casefold()


def club_order(pl, ents, regs, raw, top_id, log=print):
    """the clubs of our leagues, and of a league of the game a new club joins, entered A-Z: the
    game lists a league's clubs (Select Team, Edit) in entry order, so the clubs of the game
    that came into a league of ours came last, and so did a NewLife club in a refreshed league
    of the game (LaraCroft, AlexRufolo 10.10.). The game's own leagues keep their order."""
    name = {int.from_bytes(raw[i + W.T_ID:i + W.T_ID + 4], "little"): text(raw[i + W.T_NAME:i + W.T_NAME + W.T_NAME_LEN])
            for i in range(0, len(raw) - W.T_REC + 1, W.T_REC)}
    leagues = {regs[i + M.R_CID] for i in range(0, len(regs) - M.REG + 1, M.REG) if regs[i + M.R_TYPE] == 4}
    ours = {p["cid"] for p in pl["leagues"] if p.get("cid") and not p.get("others")}
    by_cid = {}
    for i in range(0, len(ents) - M.ENT + 1, M.ENT):
        by_cid.setdefault(ents[i + M.E_CID], []).append(i)
    done = 0
    for cid, rows in by_cid.items():
        team = {i: int.from_bytes(ents[i + M.E_TEAM:i + M.E_TEAM + 4], "little") for i in rows}
        if cid not in ours and not (cid in leagues and any(t > top_id for t in team.values())):
            continue
        rows = sorted(rows, key=lambda i: ents[i + M.E_ORDER])
        want = sorted(rows, key=lambda i: club_sort_key(name.get(team[i], "")))
        if want != rows:
            orders = [ents[i + M.E_ORDER] for i in rows]
            for i, o in zip(want, orders):
                ents[i + M.E_ORDER] = o
            done += 1
    if done:
        log("  clubs A-Z in %d league(s)" % done)


def build(pl, base, game, replace=False, log=print):
    flpaths.use_game(game, siderdir.find(game))   # the exe readers (caltab, region headings) look here
    out = os.path.join(siderdir.find(game), "livecpk", pl["world"])
    if os.path.exists(out):
        if not replace:
            raise BuildError("%s exists -- build with replace to rebuild it" % out)
        if not os.path.exists(os.path.join(out, MARK)):
            raise BuildError("%s was not made by the league builder (no %s) -- left alone" % (out, MARK))
    tmp = out + ".building"
    laps, clock = [], [time.time()]
    key = input_key(pl, base, game)
    if replace and os.path.exists(out) and pictures_only(pl, base, game, out, key, log):
        if is_live(pl["world"], game):
            switch_on(pl["world"], game, log, redraw=True)
        return out

    def lap(what):
        # 17.10.: where a Build's minutes go (a tester waited 20+ min to swap one cup's picture)
        now = time.time()
        laps.append("%s %d s" % (what, round(now - clock[0])))
        clock[0] = now

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
    clash = id_mask_clash(have)                 # B63: ids the game would take for a game club's
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
    # a new club's id from the last Build (plan: prev_teams): kept when it is still free, and no
    # other new club counts up into one (audit 12.10.: a league added in front moved them all)
    pins_all = {t for p in pl["leagues"] + others for t in (p.get("prev_teams") or [])
                if t and top_id < t <= CLUB_ID_MAX and t not in nl_ids and t not in mine}

    def pinned_tid(p, k):
        prev, names = p.get("prev_teams") or [], p.get("prev_names") or []
        nm = str((p.get("club_names") or [])[k] if k < len(p.get("club_names") or []) else "").strip().lower()
        j = names.index(nm) if nm and nm in names else (k if not nm and not (names[k:k + 1] or [""])[0] else None)
        t = prev[j] if j is not None and j < len(prev) else None
        return t if t in pins_all and t not in have else None
    if any(game_places(p) for p in pl["leagues"]):
        info = game_info(base)
        for p in pl["leagues"]:
            for at, g in sorted(game_places(p).items()):
                sw, tid = g.get("swap"), g["id"]
                if isinstance(sw, dict):
                    r = bytearray(proto)
                    sid = top_id + 1 + own
                    own += 1
                    while sid in have or sid in nl_ids or sid in clash:
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

    new_of = {}                                        # every new club's id: its league (or group)
    import lbgamestadiums as G
    picked_stadiums = {}

    def stadium_picks(p):
        """[game stadium id] of league (or group) p's clubs; [] when the recipe keeps the old way"""
        if pl.get("game_stadiums") is False:
            return []
        if id(p) not in picked_stadiums:
            n = int(p.get("clubs") or len(p.get("teams") or []) or 0)
            picked_stadiums[id(p)] = p["game_stadiums"] = G.league(
                n, p.get("tier") or 1, p.get("country"), confed, G.fixed_of(pl, p))
        return picked_stadiums[id(p)]

    def new_club(p, k):
        """a new club's Team.bin record, the k-th of league (or group) p: [record, id, abbr]"""
        nonlocal own, made
        r = bytearray(proto)
        ids = p.get("club_ids") or []
        nl = (p.get("newlife") or {}).get("clubs") or []
        if k < len(ids) and ids[k]:
            tid = ids[k]                   # checked by plan(): free, in the block
        elif k < len(nl) and nl[k] is not None and NEWLIFE_TEAMS[0] <= nl[k] <= NEWLIFE_TEAMS[1] and nl[k] not in have:
            # 0.1.8 (#90 / #88): a NewLife Database club gets a world id of its own, the one
            # plan() gave it; the NewLife id is only how the recipe names the club
            tid = (p.get("newlife_tid") or {}).get(nl[k])
            if tid is None:
                raise BuildError("%s, club %d: no world id for the NewLife club %d"
                                 % (p["name"], k + 1, nl[k]))
        elif pinned_tid(p, k):
            tid = pinned_tid(p, k)
        else:
            tid = top_id + 1 + own
            own += 1
            while tid in have or tid in nl_ids or tid in pins_all or tid in clash:    # a NewLife club's pinned id may sit lower
                tid = top_id + 1 + own
                own += 1
            if tid > CLUB_ID_MAX:
                raise BuildError("no team ids left up to %d" % CLUB_ID_MAX)
        have.add(tid)
        new_of[tid] = p
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
        # its home stadium: one of the game's (lbgamestadiums), not Selangor FC's Stadio Nazionale
        # for all of them (0.2.5)
        sids = stadium_picks(p)
        if k < len(sids):
            r[G.T_STADIUM], r[G.T_STADIUM + 1] = sids[k], 0
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
        if p["others"] == OTHERS["europe"]:
            # B167 (19.10.2026): Cup mode filled the Champions League's last places from Other
            # European teams, and with the game's own such clubs moved into leagues, three Croatian
            # village clubs of a "no league" group were all that was left there
            log("  NOTE: Cup mode can put these clubs in the Champions League (it fills the last places "
                "from Other European teams); for small clubs choose Classic Teams")
    clubs = dict(pl, leagues=pl["leagues"] + others)    # every new club, for what goes by club
    if added and pl.get("game_stadiums") is not False:
        used = {}
        for r in added:
            used[r[G.T_STADIUM]] = used.get(r[G.T_STADIUM], 0) + 1
        log("  game stadiums: %d new club(s) at %d of the game's stadiums (%s)" % (
            len(added), len(used), ", ".join("%s %d" % (G.name(s), n)
                                             for s, n in sorted(used.items(), key=lambda x: -x[1])[:5])))

    # the new clubs go in in id order, as the shipped ones are
    for r in sorted(added, key=lambda r: int.from_bytes(r[W.T_ID:W.T_ID + 4], "little")):
        raw += r
    apply_edits(pl.get("edits") or {}, raw, regs, log, game_league_edits(pl))
    swaps = (pl.get("edits") or {}).get("swaps") or []
    if swaps:                                          # two clubs of the game's leagues trade places
        info = game_info(base)
        for a, b in ((int(x), int(y)) for x, y in swaps):
            na, nb = exchange_entries(ents, a, b)
            log("  %s (%s) and %s (%s) swap leagues: %d and %d place(s)"
                % (info["clubs"].get(a, (a,))[0], info["league_of"].get(a, "?"),
                   info["clubs"].get(b, (b,))[0], info["league_of"].get(b, "?"), na, nb))
    # B65: a club with a league place is in no "Other ..." group, however it got there -- moved
    # (game_places, above), renamed or swapped by the edits, or a place the tables filed there
    gl = game_leagues(base)
    cids = {c for _r, c, _n, _t in gl} - friendly_cids(gl) | {p["cid"] for p in pl["leagues"]}
    cleared = [t for t in clear_league_pools(raw, ents, cids) if t not in nopool]
    if cleared:
        nopool += cleared
        log("  %d club(s) with a league place out of the game's other-clubs groups" % len(cleared))
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
    lineups, donors = {}, {}
    wanted = club_formations(clubs)
    if wanted:
        import mktactics
        donors = {t: formation_club(base, f) for t, f in wanted.items()}
        trows, tforms, _h = mktactics.read(base)
        shown = mktactics.add(trows, tforms, donors)[2]      # written once the squads are known
        lineups = {t: mktactics.roles(places) for t, places in shown.items()}
        log("  formations for %d clubs" % len(shown))
    club_order(pl, ents, regs, raw, top_id, log)
    with contextlib.redirect_stdout(io.StringIO()):
        M.write_tables(tmp, comp, regs, ents)
    lap("clubs and tables")

    import lbplayers
    lbplayers.SQUAD = SQUAD                # a new club's places: the squads Build makes
    log("  squads: filling them (a big world takes some minutes)")   # 0.2.4: the window says where Build is
    try:
        filled = dict(clubs, players=lbplayers.fill_newlife(clubs, base, log))   # the plan kept as it was
        filled["players"] = lbplayers.fill_tiers(filled, base, log)
    except lbplayers.Error as e:
        raise BuildError(str(e))
    lap("squads")
    last = last_build_ids(game, pl["world"]) or twin_build_ids(game, pl["world"], clubs, log)
    last = follow_clubs(last, club_newlife(clubs))
    try:
        retired = {int(x) for x in last.get("retired") or [] if lbplayers.PID_MAX >= int(x) > 0}
    except (TypeError, ValueError):
        retired = set()
    have = len(pesdb.wesys_unpack(open(os.path.join(base, "Player.bin"), "rb").read())) // 312
    # 0.2.4: the placeholder squads and the recipe's players go in with room to spare, and only the
    # finished table has to fit PLAYER_CAP: the placeholders a NewLife squad replaced are deleted
    # at the end of apply, so a world of 1212 new clubs (the Modpack, 60488 players when done)
    # passed the cap halfway and stopped (exe test 14.10.). When the finished table does not fit,
    # the squads get smaller by what is over, and the players go in again.
    per = squad_size(have, made) if made else 0
    per = SQUAD if made and filled.get("players") else per
    for attempt in range(4):
        if made:
            import mkplayers
            for n in ("Player.bin", "PlayerAssignment.bin"):
                if os.path.exists(os.path.join(db, n)):
                    os.remove(os.path.join(db, n))
            said = call(mkplayers, ["--base", base, "--out", tmp, "--per", per, "--cap", have + made * per])
            cut = squads_cut(said)
            if cut:
                # mkplayers fills the clubs in id order and stops at the cap without a word of its
                # own in the log; the clubs after it had no players at all (B28, the Modpack: 80 of
                # 1212 clubs): stop here instead of writing a world the game crashes in
                raise BuildError("%d new clubs, but the player table (%d) has room for squads of %d for %d of "
                                 "them: fewer clubs or smaller squads, else the last %d clubs have no players and "
                                 "the game crashes when one is picked"
                                 % (cut[1], PLAYER_CAP, per, cut[0], cut[1] - cut[0]))
            log("  squads of %d for %d clubs" % (per, made) + ("" if per == SQUAD else
                " (%d new clubs: %d players each would pass the %d player records)" % (made, SQUAD, PLAYER_CAP)))
        faces, ids, portraits, picked = [], {}, [], {}
        gone = set(retired)                            # apply adds the ids of the players who left
        log("  players: writing them into the tables")
        try:
            lbplayers.apply(copy.deepcopy(filled), base, db, PLAYER_CAP + made * SQUAD, log, faces,
                            lineups=lineups, ids=ids, portraits=portraits,
                            prev=last.get("clubs"), prev_names=last.get("names"),
                            formations=formations(base), picked=picked,
                            prev_people=last.get("people"), retired=gone)
        except lbplayers.Error as e:
            raise BuildError(str(e))
        pb = os.path.join(db, "Player.bin")
        n = len(pesdb.wesys_unpack(open(pb, "rb").read())) // 312 if os.path.exists(pb) else have
        if n <= PLAYER_CAP:
            break
        # 17.10. (Vicentico, the Modpack: 4 passes of ~60000 players, 20+ min): what is over is taken
        # off the squads the pass made, not spread over every new club -- a club whose squad is
        # shorter than per gives nothing up, so (over / clubs) came short and the next pass was
        # over again. Each new club keeps min(its squad, the new size): one more pass, as a rule.
        nxt = smaller_squads(lbplayers.squad_counts(db, new_of).values(), n - PLAYER_CAP, per) if made else None
        if nxt is None or attempt == 3:
            raise BuildError("the player table is full: the world has %d players, the game takes %d -- fewer "
                             "clubs or smaller squads" % (n, PLAYER_CAP))
        log("  the finished world has %d players, %d more than the game takes: squads of %d instead"
            % (n, n - PLAYER_CAP, nxt))
        per = nxt
    # 0.2.4: the tactics go in once the squads are known: a new club with no formation in the
    # recipe gets the one its squad fits (lbplayers.pick_formation), not the engine's fixed
    # 4-2-3-1 -- every club of the Modpack played 4-2-3-1. The recipe's formations stand.
    if donors or picked:
        import mktactics
        mktactics.write(base, db, {**donors, **{t: e["club"] for t, e in picked.items()}})
    if picked:
        import collections
        used = collections.Counter(e["label"] for e in picked.values())
        log("  formations picked for %d clubs from their squads (%s)"
            % (len(picked), ", ".join("%s: %d" % fc for fc in sorted(used.items(), key=lambda kv: (-kv[1], kv[0])))))
    fans = club_money(new_of, pl, db, log)
    if os.path.exists(os.path.join(db, "Player.bin")):   # a world of cups only keeps the game's players
        lbplayers.sign_keepers(db, log)
        lbplayers.line_up(db, base, recipe_ordered(filled, clubs), log)
        # a captain and set-piece takers for every club and national team with none: the game made
        # the goalkeeper, first in the squad order, captain of each (mato 18.10.: new clubs and the
        # game's clubs Build wrote squads for alike); a club with its own flags keeps them
        lbplayers.set_roles(db, None, log)
        # every new club can field a side, whatever left it short (B28): the game crashes when a
        # club with no players is picked, and Become a Legend does not start
        short = lbplayers.short_squads(db, new_of)
        if short:
            names = {tid: "%s (%s)" % (club_name(p, k), p["name"]) for p in clubs["leagues"]
                     for k, tid in enumerate(p.get("teams") or []) if tid in short}
            raise BuildError("%d club(s) with fewer than %d players -- the game crashes when one is picked:\n  "
                             % (len(short), lbplayers.MIN_SQUAD)
                             + "\n  ".join("%s, id %d: %d" % (names.get(t, "club"), t, n)
                                           for t, n in sorted(short.items())[:20])
                             + ("\n  ... and %d more" % (len(short) - 20) if len(short) > 20 else ""))
    if ids:                                            # for Mod Studio's Players page and its CSV
        with open(os.path.join(tmp, PLAYER_IDS), "w", encoding="utf-8") as f:
            # "people" and "club_nl" say who each player and club is, "retired" the ids of the
            # players no longer in the world: the next Build keeps every id with its own player
            # and gives none of a player who left to somebody else (0.2.4)
            now = club_newlife(clubs)
            json.dump({"world": pl["world"], "clubs": ids, "names": id_names(filled, ids),
                       "people": id_people(filled, ids), "club_nl": {k: v for k, v in now.items() if k in ids},
                       "retired": sorted(gone)}, f, indent=1, sort_keys=True)
    lap("players")
    if faces:
        import lbfaces
        for n, (pid, folder) in enumerate(faces):
            lbfaces.install(tmp, pid, folder, n, log)
    lbplayers.player_portraits(portraits, tmp, log)
    lbplayers.coach_portraits(clubs, tmp, log)
    newfaces = lbplayers.new_face_lines(base, db, faces, portraits)   # fl26regen: pack faces (#52)
    if pl.get("pack_faces") is False:                  # the looks of the game / Edit mode stay
        newfaces = [l for l in newfaces if not l.startswith("newfaces")]

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

    lap("faces")
    rounds = qual_rounds(pl)
    uecl, qlines = europe(tmp, db, log, bool(pl.get("uecl")), pl.get("uecl_name"), rounds)
    national_cups(pl, tmp, db, log)
    game_super_cups(pl, tmp, db, log)
    resolve_new_league_stage_cup_winners(pl)
    hc = home_cups(pl, confed)
    own_cup = {p["rid"]: (p.get("own_cup") or {}).get("reg") for p in pl["leagues"]}
    for c in pl.get("ccups") or []:
        c["winners"] = list(c.get("winners") or []) + [[r, own_cup[r]] for r in
                                                       {e[1] for e in c["entry"] if e[0] == "cup"} if own_cup.get(r)]
    prepare_sudamericana_first(pl, tmp, db, log)
    ccups = continental((pl.get("ccups") or []) + hc, tmp, db, log, alt_from(pl), pl.get("prev_cup_ids"),
                        pl.get("low_cids"))
    ccups += sudamericana_first_line(pl)
    ccups += sudamericana_playoffs(pl, tmp, db, log)
    ccups += libertadores_qualifying(pl, tmp, db, log)
    for c in (pl.get("ccups") or []) + hc:
        pl.setdefault("cup_ids", {})["ccup:" + (c.get("code") or c["name"])] = {
            f: c[f] for f in ("cid", "reg", "ko", "pre_reg") if isinstance(c.get(f), int)}
    # the confed line also tells fl26swiss which of our clubs the board sends to the AFC
    # Champions League or the Libertadores instead of the Champions League (GitHub #43), so a
    # world with a league outside UEFA gets it even with no continental cup
    if confed and (pl.get("ccups") or pl.get("association_access") or pl.get("conmebol_stages")
                   or any(confed.get(p["country"], 2) != 2 for p in pl["leagues"])):
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
        if c and c.get("super_reg"):
            L["scup"] = c["super_reg"]
        if c and c.get("reg") and not c["keep_top"] and (
            below or c["clubs"] < p["clubs"]
            or p.get("calendar") or p.get("follows_calendar")):
            # the game fills the cup from both leagues whatever its entry list says, so fl26chain
            # writes the top league's clubs and the first ones below, a field the bracket screen
            # draws (#74: a cup of 22 crashed Competition Info -> Fixtures). Also when the two
            # leagues fill the bracket exactly (20 + 12 = 32): left alone, a split top league put
            # only its own 20 into the cup of 32
            L["cup"], L["cuptop"], L["cuplow"], L["cupall"] = c["reg"], p["rid"], below["rid"] if below else 0, 1
            L["cupn"] = c["clubs"]
        # The league cup (league_ko_cup) the same way: the game fills it like a national cup, from
        # the region's league with the lowest regulation id and the one linked below it, not from
        # its entry list. Erax 2026-10-15: Liga Nacional (reg 11, 22 clubs) is the lower id, so the
        # cup of 32 (20 + 12) held the 22 of the second division alone, and Competition Info ->
        # the cup -> Fixtures crashed on a field the bracket screen has no layout for (#74, 22).
        # fl26chain writes the top division and the first clubs below it instead, lcupn in all.
        lc = next((h for h in hc if h.get("code") == "FL_%03d_LCUP" % p["rid"] and h.get("ko")), None)
        if lc:
            L["lcup"], L["lcuplow"], L["lcupn"] = lc["ko"], below["rid"] if below else 0, len(lc["entry"])
    # A league cup of a league of the game (game_cups, FL_G<rid>_LCUP) the same way (B122, Jabo9
    # 17.10.): our League One under the Championship got reg 11, England's lowest, so the game
    # filled the Carabao Cup with League One and Two. The game's league has no line of its own,
    # so the cup rides on a line of ours with no lcup= yet, one of its country first; lcuptop=
    # names the game's league.
    free = [L for L in leagues if L["id"] in mine and L.get("lcup") is None]
    for h in hc:
        code = h.get("code") or ""
        if not (code.startswith("FL_G") and code.endswith("_LCUP") and code[4:-5].isdigit()) or not h.get("ko"):
            continue
        top = int(code[4:-5])
        if not free:
            log("  warning: %s -- no league line of the world left to carry it, the game fills it "
                "itself (from the country's lowest league id)" % h["name"])
            continue
        L = next((L for L in free if L.get("region") == h.get("region")), free[0])
        free.remove(L)
        L["lcup"], L["lcuptop"], L["lcupn"] = h["ko"], top, len(h["entry"])
        L["lcuplow"] = next((r for r, _p in h["entry"] if r != top), 0)
    # fl26chain.dll keeps 16 cups to their leagues; fl26chain.lua sends the national cups first
    for c in fl26world.chain_cups(leagues)[fl26world.MAX_CHAIN_CUPS:]:
        log("  warning: cup %d -- more than %d national and league cups in the world, the game "
            "fills it itself (Competition Info -> Fixtures may not draw it)" % (c[0], fl26world.MAX_CHAIN_CUPS))
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
                          ccups + dates_lines(pl, db) + gsuper_lines(pl) + season_lines(pl, db) + july_lines(pl, base)
                          + rcal_lines(pl, base, confed) + cupdays_lines(pl, base, db, log) + first_lines(pl)
                          + order_lines(pl, base, confed)
                          + kickorder_lines(pl, base, confed)
                          + (["nopool " + " ".join(str(t) for t in nopool)] if nopool else []) + newfaces
                          + fans
                          + ["cupdraw %s" % pl.get("cup_draw", "seeded")],
                          qlines)
    pl.pop("prev_cup_ids", None)      # this Build's own are in cup_ids; the old ones must not pile up
    for p in pl["leagues"] + (pl.get("others") or []):
        p.pop("prev_teams", None), p.pop("prev_names", None)
    json.dump(pl, open(os.path.join(tmp, "leaguebuilder-plan.json"), "w", encoding="utf-8"), indent=1)

    lap("cups and the world file")
    gone = set()                          # pictures whose source is not on this PC (have_picture)
    pictures(pl, tmp, base, log, game, gone)
    lap("pictures and kits")
    region_modules(pl, tmp, game, log)
    mp_column(tmp, game, log)

    import lbtrophies
    lbtrophies.build(pl, tmp, db, log)
    write_input(tmp, key, pl, base)       # an edit of pictures alone next time draws just those
    write_manifest(tmp)                   # before keep_added: what this Build wrote, not what it kept
    if os.path.exists(out):
        keep_added(out, tmp, log, gone)
    swap_in(tmp, out)
    lap("regions and the swap")
    log("built %s: %d leagues, %d clubs" % (out, len(pl["leagues"]), made))
    log("  time: " + ", ".join(laps))
    if is_live(pl["world"], game):
        # GitHub #69: the modules read SiderAddons/modules/fl26world.txt, a copy Switch on makes.
        # A world built again while it was already on kept the old copy, and a change (February
        # to December) never reached the game until Switch on was pressed once more.
        log("%s is the live world: switching it on again, so the game reads what was just built" % pl["world"])
        switch_on(pl["world"], game, log, redraw=True)
    return out


def swap_in(tmp, out):
    """the world just built (<out>.building) in the place of the old one. The old one is moved
    aside first and deleted only once the new one is in: until 0.2.4 it was deleted first, and a
    rename that failed then (a file of the world open in another program) left no world, only its
    .building folder (B150)"""
    old = out + ".old"
    if os.path.exists(old):
        shutil.rmtree(old)
    if os.path.exists(out):
        try:
            os.rename(out, old)
        except OSError as e:
            raise BuildError("%s could not be replaced (%s) -- close what has a file of it open "
                             "(the game, a folder window) and Build again" % (out, e.strerror or e))
    try:
        os.rename(tmp, out)
    except OSError as e:
        if os.path.exists(old):
            os.rename(old, out)
        raise BuildError("%s could not be put in place (%s) -- close what has a file of it open "
                         "(the game, a folder window) and Build again" % (out, e.strerror or e))
    if os.path.exists(old):
        shutil.rmtree(old, ignore_errors=True)


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


INPUT = "leaguebuilder-input.json"        # what the last Build was made from (pictures_only)
INPUT_FORMAT = 1                          # raised when the same input builds a different world
PIC_ARG = {"league_logo": 2, "club_crest": 2, "country_flag": 1,   # picture_jobs: the picture's place
           "game_emblem": None}                                     # (none: the game's own, by competition)


def code_stamp():
    """the Build's code: the release's version in Mod Studio's exe, the sources when run from them"""
    try:
        from modstudio import VERSION
    except ImportError:
        VERSION = "?"
    if getattr(sys, "frozen", False):
        return VERSION
    import hashlib
    h = hashlib.sha1(VERSION.encode())
    here = os.path.dirname(os.path.abspath(__file__))
    for f in sorted(os.listdir(here)):
        if f.endswith(".py"):
            with open(os.path.join(here, f), "rb") as fh:
                h.update(f.encode() + fh.read())
    return h.hexdigest()


PIC_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".dds", ".tga")


def is_picture(v):
    """a value of a plan that names a picture (a logo, crest or flag): a path to an image file"""
    return isinstance(v, str) and v.lower().endswith(PIC_EXT)


def input_key(pl, base, game):
    """one hash of everything a Build reads but the pictures: the plan before Build with each
    picture as "<pic>" and without the ids of the last Build (prev_*: they come from the world
    being built again, which they give back), the game's tables, its exe, the other mods'
    UniformParameter.bin and the Build's code"""
    import hashlib
    h = hashlib.sha1()

    def strip(v):
        if isinstance(v, dict):
            return {k: strip(x) for k, x in v.items() if k not in ("prev_teams", "prev_names", "prev_cup_ids")}
        if isinstance(v, (list, tuple)):
            return [strip(x) for x in v]
        return "<pic>" if is_picture(v) else v

    def feed_file(path, whole=True):
        try:
            with open(path, "rb") as f:
                if whole:
                    h.update(f.read())
                else:                     # the exe: its size and three slices of it
                    n = os.fstat(f.fileno()).st_size
                    h.update(str(n).encode())
                    for at in (0, n // 2, max(0, n - (1 << 20))):
                        f.seek(at)
                        h.update(f.read(1 << 20))
        except OSError:
            h.update(b"-")
    h.update(json.dumps([INPUT_FORMAT, code_stamp(), strip(pl)], sort_keys=True, default=str).encode())
    import lbtrophies                     # a file put in a trophy folder is a new Build too
    h.update(json.dumps(lbtrophies.signature(pl)).encode())
    for f in sorted(os.listdir(base)):
        if os.path.isfile(os.path.join(base, f)):
            h.update(f.encode())
            feed_file(os.path.join(base, f))
    k = kits_for(base, game)
    if k:
        feed_file(k)
    feed_file(flpaths.EXE, whole=False)
    for u in other_uniforms(game):
        h.update(u.encode())
        feed_file(u)
    return h.hexdigest()


def job_signature(job):
    """a picture job (picture_jobs) with its picture's content in place of its path"""
    fn, args, rels = job
    a = list(args)
    i = PIC_ARG[fn]
    if i is not None and a[i]:
        a[i] = "sha1:" + file_hash(a[i])
    return json.loads(json.dumps([fn, a, list(rels)], default=str))


def write_input(root, key, pl, base):
    """the record pictures_only reads: the key of the plan Build was given, and the picture jobs
    of the plan it made (picture_jobs needs the clubs' ids). None written when a picture's source
    is not on this PC: the world keeps its own there (keep_added), which a job does not draw"""
    gone = set()
    jobs, _flags, _n = picture_jobs(pl, base, lambda *a: None, gone)
    if gone:
        return
    with open(os.path.join(root, INPUT), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"format": INPUT_FORMAT, "key": key, "jobs": [job_signature(j) for j in jobs]}, f)


def carry_pictures(src, dst):
    """the pictures of plan src into dst, the plan the last Build wrote, place by place"""
    if isinstance(src, dict) and isinstance(dst, dict):
        for k, v in src.items():
            if k in dst:
                if is_picture(v) or is_picture(dst[k]):
                    dst[k] = v
                else:
                    carry_pictures(v, dst[k])
    elif isinstance(src, list) and isinstance(dst, list) and len(src) == len(dst):
        for i, v in enumerate(src):
            if is_picture(v) or is_picture(dst[i]):
                dst[i] = v
            else:
                carry_pictures(v, dst[i])


def pictures_only(pl, base, game, out, key, log=print):
    """17.10. (Vicentico: 20 minutes to give one cup a new name and logo): when nothing has changed
    since the world's last Build but pictures (logos, crests, flags), draws only those again, in
    the world folder, and returns True; False when a full Build is needed. A picture someone put
    in the world by hand stays while the Build draws the same one there as the last time
    (keep_added's rule)."""
    import lbassets
    try:
        with open(os.path.join(out, INPUT), encoding="utf-8") as f:
            last = json.load(f)
        with open(os.path.join(out, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            built = json.load(f)
    except (OSError, ValueError):
        return False
    if last.get("format") != INPUT_FORMAT or last.get("key") != key:
        return False
    carry_pictures(pl, built)              # the same plan but for its pictures: the last Build's ids
    gone = set()
    jobs, _flags, _n = picture_jobs(built, base, lambda *a: None, gone)
    if gone:
        return False
    sigs = [job_signature(j) for j in jobs]
    old = last.get("jobs") or []
    if len(old) != len(sigs) or any(o[0] != n[0] or o[2] != n[2] for o, n in zip(old, sigs)):
        return False
    changed = [j for o, n, j in zip(old, sigs, jobs) if o != n]
    touched = {r for j in changed for r in j[2]}
    ours = {}
    try:
        with open(os.path.join(out, MANIFEST), encoding="utf-8") as f:
            for line in f:
                rel, _t, h = line.rstrip("\n").partition("\t")
                if rel:
                    ours[rel] = h
    except OSError:
        return False
    if not touched <= set(ours):
        return False
    work = out + ".pictures"
    if os.path.exists(work):
        shutil.rmtree(work)
    kept = 0
    try:
        for fn, args, rels in jobs:          # in order: a later job may draw over an earlier one
            if touched & set(rels):
                getattr(lbassets, fn)(work, *args)
        if any(not os.path.isfile(os.path.join(work, r)) for r in touched):
            return False
        for rel in sorted(touched):
            src, dst = os.path.join(work, rel), os.path.join(out, rel)
            h = file_hash(src)
            if os.path.exists(dst) and file_hash(dst) != ours[rel] and h == ours[rel]:
                kept += 1                    # replaced by hand, and this Build draws the same as the last
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(src, dst)
            ours[rel] = h
    finally:
        shutil.rmtree(work, ignore_errors=True)
    json.dump(built, open(os.path.join(out, "leaguebuilder-plan.json"), "w", encoding="utf-8"), indent=1)
    with open(os.path.join(out, MANIFEST), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(r + ("\t" + h if h else "") for r, h in sorted(ours.items())) + "\n")
    write_input(out, key, built, base)
    if os.path.exists(os.path.join(out, ".modstudio")):
        os.remove(os.path.join(out, ".modstudio"))
    log("only pictures changed since the last Build: %d drawn again (%d files)%s, the rest of %s left as it was"
        % (len(changed), len(touched), ", %d kept as put in by hand" % kept if kept else "", out))
    return True


EDITED = ".modstudio-edited"              # modstudio.worlds.EDITED


def keep_added(old, new, log=print, gone=()):
    """carry into the new build the pictures someone put in the old world folder by hand (a crest
    in common/render/symbol/flag, Xxspedd 04.10.): a Build replaces the whole folder.
    - a file the last Build did not write, and this one does not either: copied over
    - a picture the last Build wrote and someone replaced: theirs stays, as long as this Build
      writes the same picture as the last one (a crest set in the recipe since then wins)
    - gone: the files of a picture whose source is not on this PC (a ready world from a zip, built
      again here): the world's own stay, byte for byte, not a drawn badge (B85)
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
    # .modstudio marks a world installed from a zip (installer.ready_world): once built on this PC
    # it is not one any more, and kept it would switch Build off for the world just built (0.2.4)
    for rel in sorted(built_files(old) - {MANIFEST, ".modstudio", EDITED}):
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
    theirs = [rel for rel in sorted(gone) if rel not in kept and os.path.isfile(os.path.join(old, rel))]
    # a world from a zip made editable stays one (worlds.make_editable): every Build of it backs it up
    theirs += [EDITED] if os.path.isfile(os.path.join(old, EDITED)) else []
    for rel in theirs:
        dst = os.path.join(new, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(old, rel), dst)
    if [r for r in theirs if r != EDITED]:
        log("  kept %d picture file(s) of the world whose source is not on this PC"
            % len([r for r in theirs if r != EDITED]))
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


def live_world(game):
    """the world the modules read now (the world line of modules/fl26world.txt), or None"""
    try:
        with open(os.path.join(siderdir.find(game), "modules", MARK), encoding="utf-8", errors="replace") as f:
            for line in f:
                w = line.split()
                if w[:1] == ["world"]:
                    return w[1] if len(w) > 1 else None
    except (OSError, BuildError):
        pass
    return None


def world_modules(game, world=None):
    """{module: its file} of the modules a world brings in livecpk\\<world>\\modules (fl26regions and
    fl26regnames, lbpack.PER_WORLD: they name its own competitions and countries, so they are made
    at its Build and not shipped in the pack); world None: the live one. {} when it has none"""
    world = world or live_world(game)
    if not world:
        return {}
    try:
        d = os.path.join(siderdir.find(game), "livecpk", world, "modules")
        return {f[:-4].lower(): os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith(".lua")}
    except (OSError, BuildError):
        return {}



def sudamericana_first_plan(stages, continental_places):
    """Plan the modern Sudamericana national first stage from logical SUD_FIRST places.

    Exactly 32 clubs enter, paired inside their domestic source. A staged cup-winner
    row is (cup, 0, ..., alt=league); it is grouped with that league and seeded as the
    strongest domestic place. The 12 direct group places use ccup_entry(), so cup-winner
    destinations keep the same fallback semantics as every other continental cup.
    """
    first = [(r, pos, alt) for r, pos, comp, _stage, alt in stages
             if comp == fl26world.SUD_FIRST]
    if not first:
        return None
    if len(first) != 2 * SAM_FIRST_TIES:
        raise BuildError("modern Sudamericana first stage: %d clubs -- exactly 32 required" % len(first))
    if len(set(first)) != len(first):
        raise BuildError("modern Sudamericana first stage: the same domestic place is listed twice")

    by_source = {}
    for reg, pos, alt in first:
        source = alt if pos == CUP_WINNER and alt else reg
        by_source.setdefault(source, []).append((reg, pos, alt))

    # No country/source quota is imposed. Pair inside a source while possible,
    # then pair one leftover from odd-sized sources across sources.
    ties, leftovers = [], []
    for source in sorted(by_source):
        entries = sorted(by_source[source], key=lambda e: (e[1], e[0]))
        while len(entries) >= 2:
            ties.append([entries.pop(), entries.pop(0)])
        if entries:
            leftovers.append(entries[0])

    if len(leftovers) % 2:
        raise BuildError(
            "modern Sudamericana first stage: internal pairing error -- "
            "%d unpaired club(s)" % len(leftovers)
        )
    for i in range(0, len(leftovers), 2):
        ties.append([leftovers[i + 1], leftovers[i]])

    if len(ties) != SAM_FIRST_TIES:
        raise BuildError("modern Sudamericana first stage: %d ties -- exactly 16 required" % len(ties))

    direct_raw = [(r, pos, alt) for r, pos, comp, alt in continental_places if comp == SUDAM]
    if len(direct_raw) != 12:
        raise BuildError("modern Sudamericana groups: %d direct clubs -- exactly 12 required" % len(direct_raw))
    if len(set(direct_raw)) != len(direct_raw):
        raise BuildError("modern Sudamericana groups: the same direct domestic place is listed twice")
    first_key = {(alt if pos == CUP_WINNER and alt else r, pos) for r, pos, alt in first}
    direct_key = {(alt if pos == CUP_WINNER and alt else r, pos) for r, pos, alt in direct_raw}
    if first_key & direct_key:
        raise BuildError("modern Sudamericana: a domestic place is both direct to groups and in the first stage")
    direct = [ccup_entry(r, pos, alt) for r, pos, alt in direct_raw]
    return {"ties": ties, "direct": direct}


def prepare_sudamericana_first(pl, root, db, log=print):
    """Build the internal 16-tie one-match competition and replace Suda's group
    entry list with 12 direct + 4 Libertadores-F3 losers + 16 first-stage winners.
    Returns the master regulation id, or None when the modern first stage is off.
    """
    q = pl.get("suda_first")
    if not q:
        return None
    sud = next((c for c in pl.get("ccups") or [] if c.get("number") == SUDAM), None)
    if not sud:
        raise BuildError("modern Sudamericana first stage: Copa Sudamericana was not planned")
    import mkeuropo
    cid, (master,) = helper_ids(pl, db, "conmebol:" + SAM_FIRST_CODE)
    try:
        # Keep the technical helper in continental region 1: region 0 prevents
        # all of its regulation replicas from becoming live at runtime. Its
        # neutral file confederation keeps it out of League Info's CONMEBOL icons;
        # fl26swiss hides the helper itself from Competition Info.
        mkeuropo.prerounds_single(db, root, cid, SAM_FIRST_CODE, SAM_FIRST_NAME,
                                  [(master, SAM_FIRST_TIES)], log=log, one_match=True,
                                  region=1, confederation=0)
    except SystemExit as e:
        raise BuildError("Sudamericana first stage: %s" % e)
    sud["groups"] = 8
    sud["entry"] = (list(q["direct"]) + [(LIB_QUAL, QUAL_LOSER)] * SAM_LIB_LOSERS
                    + [(master + 1024 * (k + 1), 0) for k in range(SAM_FIRST_TIES)])
    q["cid"], q["reg"] = cid, master
    log("  Sudamericana first stage: competition %d reg %d, 32 clubs / 16 one-match ties -> groups"
        % (cid, master))
    return master


def lpre_entry_text(entries):
    """(entry text, optional alt text) for lpre world lines.

    An entry may be (source, rank) or (source, rank, fallback_source). The latter is
    used only for a cup-winner slot: alt stores 1-based entry index, fallback source,
    and first fallback rank.
    """
    words, alt = [], []
    for i, e in enumerate(entries, 1):
        reg, rank = int(e[0]), int(e[1])
        fallback = int(e[2]) if len(e) > 2 and e[2] else 0
        words.append("%d:%d" % (reg, rank))
        if rank == CUP_WINNER and fallback:
            alt.append("%d:%d:1" % (i, fallback))
    return ",".join(words), (" alt=" + ",".join(alt)) if alt else ""


def sudamericana_first_line(pl):
    q = pl.get("suda_first")
    if not q or not q.get("reg"):
        return []
    sud = next((c for c in pl.get("ccups") or [] if c.get("number") == SUDAM), None)
    if not sud or not sud.get("ko"):
        raise BuildError("Sudamericana first stage: group cup has no knockout regulation")
    entries = [e for tie in q["ties"] for e in tie]
    entry, alt = lpre_entry_text(entries)
    return ["lpre %d cup=%d fill=%d days=%d,%d entry=%s single=1%s" % (
        q["reg"], sud["ko"], SAM_FIRST_FILL, SAM_FIRST_DAY, SAM_FIRST_DAY, entry, alt)]


def sudamericana_playoffs(pl, root, db, log=print):
    """Build the modern Sudamericana post-group play-off.

    Tie k: Libertadores group (H..A) third v Sudamericana group (A..H)
    runner-up. The runtime waits until both group stages are complete, fills the
    eight two-leg ties, then builds the round of 16 from the eight Suda group
    winners plus these eight play-off winners.
    """
    sud = next((c for c in pl.get("ccups") or [] if c.get("number") == SUDAM), None)
    if not sud or not pl.get("suda_first") or not sud.get("ko") or sud.get("groups") != 8:
        return []
    import mkeuropo
    cid, (master,) = helper_ids(pl, db, "conmebol:" + SPO_CODE)
    try:
        # Same runtime/presentation split as the first stage: live in region 1,
        # neutral to League Info, and hidden as a standalone Competition Info item.
        mkeuropo.prerounds_single(db, root, cid, SPO_CODE, SPO_NAME,
                                  [(master, 8)], log=log, one_match=False,
                                  region=1, confederation=0)
    except SystemExit as e:
        raise BuildError("Sudamericana play-off: %s" % e)

    entry = []
    for k in range(8):
        entry += [(LIB_GROUPS + 1024 * (8 - k), 3),
                  (sud["reg"] + 1024 * (k + 1), 2)]

    log("  %s: competition %d reg %d, 8 two-leg ties on days %d/%d; "
        "Suda runners-up v Libertadores thirds -> round of 16 reg %d"
        % (SPO_NAME, cid, master, SPO_DAYS[0], SPO_DAYS[1], sud["ko"]))
    return ["lpre %d cup=%d fill=%d days=%d,%d entry=%s poko=1" % (
        master, sud["ko"], SPO_FILL, SPO_DAYS[0], SPO_DAYS[1],
        ",".join("%d:%d" % e for e in entry))]


def reject_legacy_libq_with_modern(recipe, leagues, stages):
    """Do not mix native/legacy Libertadores qualifying with modern F1/F2.

    Competition 4 is the game's generic/native Libertadores qualifying target.
    In a modern world F1 and F2 feed that native round as F3, so a domestic
    place sent directly to competition 4 would bypass F1/F2 and corrupt the
    intended 6 -> 3, 13 + 3 -> 8, 8 -> 4 chain.

    In custom CONMEBOL mode, competition 4 is not a domestic destination:
    Fase 3 is filled only by the eight Fase-2 winners. Vanilla worlds never call
    this guard and keep the game's original Libertadores untouched.
    """
    where = []

    for p in leagues:
        for e in p.get("europe") or []:
            try:
                comp = int(e[1])
            except (TypeError, ValueError, IndexError):
                continue
            if comp == 4:
                where.append(p.get("name") or "a new league")
                break

    for rid, places in (recipe.get("game_europe") or {}).items():
        for e in places or []:
            try:
                comp = int(e[1])
            except (TypeError, ValueError, IndexError):
                continue
            if comp == 4:
                where.append("game regulation %s" % rid)
                break

    if not where:
        return

    raise BuildError(
        "modern Libertadores qualifying is enabled, but the legacy "
        "'Libertadores qualifying' destination is also assigned (%s). "
        "Remove the legacy destination and use Phase 1 / Phase 2 instead; "
        "Phase 3 is filled automatically by the eight Phase-2 winners."
        % ", ".join(where)
    )


def libq_plan(stages):
    """Return the modern Libertadores F1/F2 access plan.

    Entries keep an optional fifth-field fallback from the staged access tuple. For a
    cup-winner destination this means (cup regulation, 0, league source), so runtime can
    cascade to the next eligible club of the same domestic source. F3 itself has no direct
    domestic entrants in the modern format.
    """
    f1 = [(r, pos, alt) for r, pos, comp, _stage, alt in stages
          if comp == fl26world.LIB_F1]
    f2 = [(r, pos, alt) for r, pos, comp, _stage, alt in stages
          if comp == fl26world.LIB_F2]
    f3 = [(r, pos, alt) for r, pos, comp, _stage, alt in stages
          if comp == fl26world.LIB_F3]

    modern = bool(f1 or f2)
    if not modern:
        return None

    if len(f1) != 6:
        raise BuildError("modern Libertadores qualifying: phase 1 has %d clubs -- exactly 6 required" % len(f1))
    if len(f2) != 13:
        raise BuildError("modern Libertadores qualifying: phase 2 has %d domestic clubs plus 3 phase-1 winners -- exactly 13 domestic clubs required" % len(f2))
    if f3:
        raise BuildError("modern Libertadores qualifying: phase 3 has %d direct domestic club(s), but its 8 places must all be the winners of phase 2" % len(f3))

    keys = [(alt if pos == CUP_WINNER and alt else r, pos) for r, pos, alt in f1 + f2]
    if len(set(keys)) != len(keys):
        raise BuildError("modern Libertadores qualifying: the same domestic place is listed in more than one qualifying phase")

    return {"phase1": f1, "phase2": f2}


def libertadores_qualifying(pl, root, db, log=print):
    """Build Libertadores F1 and F2 and return their world-file lpre lines.

    Both phases live in one auxiliary competition copied from native
    Libertadores qualifying. F2 receives F1's three winners and its eight
    winners feed native Libertadores regulation 8 (F3).
    """
    q = pl.get("libq")
    if not q:
        return []

    import mkeuropo

    cid, (m1, m2) = helper_ids(pl, db, "conmebol:" + LIBQ_CODE, 2)

    # F1 = 3 ties; F2 = 8 ties.
    try:
        mkeuropo.prerounds_single(
            db,
            root,
            cid,
            LIBQ_CODE,
            LIBQ_NAME,
            [(m1, 3), (m2, 8)],
            log=log,
            one_match=False,
        )
    except SystemExit as e:
        raise BuildError("Libertadores qualifying: %s" % e)

    # F2 gets its 13 domestic entrants plus the three F1 winners.
    # First v last gives those three F1 winners to the first three listed
    # F2 entrants, following the previously validated implementation.
    full = list(q["phase2"]) + [
        (m1 + 1024 * (k + 1), 0, 0) for k in range(3)
    ]

    if len(full) != 16:
        raise BuildError(
            "Libertadores qualifying: phase 2 resolved to %d clubs, not 16"
            % len(full)
        )

    pairs = []
    for k in range(8):
        pairs += [full[15 - k], full[k]]

    e1, a1 = lpre_entry_text(q["phase1"])
    e2, a2 = lpre_entry_text(pairs)

    lines = [
        "lpre %d cup=0 fill=%d days=%d,%d entry=%s po=1%s"
        % (m1, LIBQ_P1["fill"], LIBQ_P1["days"][0], LIBQ_P1["days"][1], e1, a1),
        "lpre %d cup=0 fill=%d days=%d,%d entry=%s po=1 feed=8%s"
        % (m2, LIBQ_P2["fill"], LIBQ_P2["days"][0], LIBQ_P2["days"][1], e2, a2),
    ]

    log(
        "  Libertadores qualifying: F1 competition %d reg %d "
        "(3 ties, days %d/%d), F2 reg %d "
        "(13 domestic + 3 F1 winners, days %d/%d) -> native F3 reg 8"
        % (
            cid,
            m1,
            LIBQ_P1["days"][0],
            LIBQ_P1["days"][1],
            m2,
            LIBQ_P2["days"][0],
            LIBQ_P2["days"][1],
        )
    )

    return lines

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


def out_of_ids(what):
    """the world has every competition the game takes: say what to take out (B154, Tysonche35
    18.10.: a league added to the Europack, and the testers then deleted the world's folder by hand)"""
    return BuildError("no free competition or regulation ids left for %s -- the world has all the "
                      "competitions the game takes (255). Untick the national or super cups of countries "
                      "you don't play (My world > Cups > Cups of our countries / of the game's countries) "
                      "or take out a league, then Build again" % what)


def pinned_ids(pl, db, key):
    """free_comp_ids for the cup `key`: its ids of the last Build first when they are still free
    (pl["prev_cup_ids"]), and no other cup's old ids (audit 12.10.: a league added in front gave
    every cup after it new ids, and a career holds them)"""
    want = pl.get("prev_cup_ids") or {}
    cids, regs = free_comp_ids(db, low=pl.get("low_cids"))
    mine = want.get(key) or {}
    others_c = {w.get("cid") for k, w in want.items() if k != key}
    others_r = {v for k, w in want.items() if k != key for f, v in w.items() if f != "cid"}
    c0 = [mine["cid"]] if mine.get("cid") in cids else []
    r0 = [mine["reg"]] if mine.get("reg") in regs else []
    return (c0 + [c for c in cids if c not in others_c and c not in c0],
            r0 + [r for r in regs if r not in others_r and r not in r0])


def helper_ids(pl, db, key, nregs=1):
    """a competition id and `nregs` regulation ids for one of the modern CONMEBOL helper
    competitions (the Sudamericana's first stage and play-off, the Libertadores' phases 1 and 2;
    key "conmebol:<code>"): its own of the last Build first, as pinned_ids gives a cup's, and
    noted in the plan's cup_ids for the next. Review of #146: they took the first free ids every
    Build, so a league or cup added later moved them, and a career holds them. Returns
    (cid, [reg, ...]); the regulations' ties are reg + 1024 * k (mkeuropo.prerounds_single)"""
    cids, regs = pinned_ids(pl, db, key)
    mine = (pl.get("prev_cup_ids") or {}).get(key) or {}
    fields = ["reg"] + ["reg%d" % k for k in range(2, nregs + 1)]
    pinned = {mine.get(f) for f in fields if mine.get(f) in regs}
    rest = iter(r for r in regs if r not in pinned)
    got, seen = [], set()
    for f in fields:
        v = mine.get(f)
        if v not in pinned or v in seen:
            v = next(rest, None)
        if v is None or not cids:
            raise out_of_ids(key.partition(":")[2] or key)
        got.append(v)
        seen.add(v)
    pl.setdefault("cup_ids", {})[key] = dict({"cid": cids[0]}, **dict(zip(fields, got)))
    return cids[0], got


def free_comp_ids(db, reserved=(), low=False):
    """competition ids and regulation ids (from CCUP_REG_FROM) nothing in the world's tables in
    <db> uses, nor anything kept for later; `low`: with the ids under 130 (low_cids)"""
    comp, regs = M.load(db, "Competition.bin"), M.load(db, "CompetitionRegulation.bin")
    used_cid = {comp[i + M.CID_OFF] for i in range(0, len(comp), M.COMP)}
    used_reg = {u16(regs[i:], M.R_ID) & 0x3ff for i in range(0, len(regs), M.REG)}
    taken = (used_reg | CCUP_KEEP | W.BAD_REG | set(W.MOVED_REG.values()) | set(fl26world.DEFAULT_SLOT)
             | set(fl26world.NO_SLOT_IDS) | set(reserved))
    return ([c for c in W.cid_pool(CID_FROM, low) if c not in used_cid and c != UECL_CID],
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
# list and appended our regions 29..127 after it, so a new country came after Thailand whatever
# its name. The `order` line puts each of our countries in its continent, by name.
SHIPPED_REGIONS = [                       # (region, name, confederation); None = a group
    (1, None, 0), (26, None, 0),
    (8, "Belgium", 2), (12, "Denmark", 2), (2, "England", 2), (3, "France", 2), (5, "Italy", 2),
    (7, "Netherlands", 2), (6, "Portugal", 2), (9, "Russia", 2), (15, "Scotland", 2),
    (4, "Spain", 2), (10, "Greece", 2), (27, "Turkey", 2), (22, None, 2),
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
# Region 10 / slot 94 is Greece in FL26 (Switzerland in PES 2021): named Switzerland, a Swiss league
# of ours sorted with it and Select Team showed the two glued together (Discord, LaraCroft 15.10.)
SLOT_COUNTRY = {7: "England", 50: "England", 8: "France", 52: "France", 9: "Italy", 53: "Italy",
                10: "Netherlands", 11: "Spain", 51: "Spain", 12: "Portugal", 13: "Brazil", 122: "Brazil",
                14: "Argentina", 15: "Chile", 16: "Germany", 17: "Usa", 18: "Japan", 88: "Belgium",
                91: "Russia", 94: "Greece", 96: "Turkey", 99: "Colombia", 102: "China",
                105: "Denmark", 114: "Scotland", 119: "Saudi Arabia"}
OTHER_CONFED = {"Germany": 2, "Usa": 6, "Japan": 3}


def moved_countries(base):
    """{regulation id: country} of the game's leagues that the tables in use give another
    country than the game ships in that regulation (game_league_countries v SHIPPED_COUNTRY):
    a database mod's moved leagues, UML 2026 v3's Ligue 1 in the Russian Premier Liga's place.
    Empty with the game's own tables."""
    return {r: nm for r, nm in game_league_countries(base).items()
            if r in SHIPPED_COUNTRY and nm != SHIPPED_COUNTRY[r]}


def slot_countries(base):
    """{Kick Off slot: country} of the game's league slots (SHIPPED_SLOT): SLOT_COUNTRY's, but
    the country of the league the tables in use have there when a database mod moved another
    country's league into it (moved_countries) -- the slot's regulation, or the league whose
    phase it is (Belgium's regular season, MLS's First Round ...), by competition id"""
    moved = moved_countries(base)
    out = dict(SLOT_COUNTRY)
    if not moved:
        return out
    regs = M.load(base, "CompetitionRegulation.bin")
    cid_of = {u16(regs[i * M.REG:], M.R_ID): regs[i * M.REG + M.R_CID] for i in range(len(regs) // M.REG)}
    league_of = {c: r for r, c, _n, _t in game_leagues(base)}
    for reg, slot in sorted(SHIPPED_SLOT.items()):
        nm = moved.get(league_of.get(cid_of.get(reg)))
        if nm:
            out[slot] = nm
    return out


def order_countries(pl, base, confed):
    """[(country name, continent block)] of every country with a league in the game or the
    world, in the default order (by continent, A-Z within it) -- the League order dialog's list"""
    ids = country_ids(base)
    names, fids = dict((fid, nm) for nm, fid in ids), dict(ids)
    got = {nm: c for _r, nm, c in SHIPPED_REGIONS if nm}
    for nm, c in OTHER_CONFED.items():
        got.setdefault(nm, c)
    for nm in sorted(set(moved_countries(base).values())):     # a database mod's league in a game slot
        got.setdefault(nm, CONTINENT.get(confed.get(fids.get(nm)), 5))
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
    slot_country = slot_countries(base)
    for reg, slot in sorted(SHIPPED_SLOT.items()):
        nm = slot_country.get(slot)
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
        # the "Other ..." groups have no name, so reorder_named left them behind every country
        # (LaraCroft, 09.10.: Other European after Asia): each goes after the last country of its
        # continent again
        block_of = {r: c for r, nm, c in SHIPPED_REGIONS if nm}
        block_of.update((r, c) for r, (nm, c) in ours.items())
        for r, nm, c in SHIPPED_REGIONS:
            if nm or c not in (2, 3, 4) or r not in out:
                continue
            out.remove(r)
            last = [i for i, x in enumerate(out) if block_of.get(x) == c]
            out.insert(last[-1] + 1 if last else len(out) - 1, r)
    return ["order " + ",".join(map(str, out))]


def dates_lines(pl, db):
    """World-file `dates` lines for national cups and super cups.

    Normally a new cup takes the dates of the shipped cup it was copied from.
    A calendar-year country instead takes a complete shipped calendar and shifts
    its days into February-December; fl26swiss.dll applies the optional shift.
    """
    out = []
    for p in pl["leagues"]:
        c = p.get("own_cup")
        if not c or not c.get("reg"):
            continue

        calendar = bool(p.get("calendar") or p.get("follows_calendar"))

        cups = (
            (c["reg"], c["like"],
             CALENDAR_CUP_DATE_LIKE, CALENDAR_CUP_DATE_DAYS),
            (c.get("super_reg"), SUPER_CUP_LIKE if c.get("super") else None,
             CALENDAR_SUPER_DATE_LIKE, CALENDAR_SUPER_DATE_DAYS),
        )

        for reg, normal_code, calendar_code, days in cups:
            if not reg or not normal_code:
                continue

            code = calendar_code if calendar else normal_code
            like = like_reg(db, code)
            if not like:
                continue

            line = "dates %d like=%d" % (reg, like)
            if calendar:
                line += " days=%s" % ",".join(map(str, days))
            out.append(line)

    for s in pl.get("game_supers") or []:              # a game league's super cup (game_super_cups)
        like = like_reg(db, CALENDAR_SUPER_DATE_LIKE if s["calendar"] else SUPER_CUP_LIKE) if s.get("reg") else None
        if like:
            out.append("dates %d like=%d" % (s["reg"], like) + (
                " days=%s" % ",".join(map(str, super_days(s))) if s["calendar"] else ""))

    return out


def gsuper_lines(pl):
    """world file lines `gsuper <reg> league=<reg> cup=<reg> region=<r> conf=<c>`: the super
    cups Build gave the game's leagues (game_super_cups), with the league whose champion and the
    cup whose winner play it. A new league's super cup is named on its league line (scup=); a
    game league has no line, so this is how fl26joindll puts a February-December country's one
    into the season the game builds at New Year, and fl26swiss fills it (cup=0: the region has
    no cup, the game fills it)"""
    return ["gsuper %d league=%d cup=%d region=%d conf=%d" % (s["reg"], s["league"], s.get("cup") or 0,
                                                              s["region"], s.get("conf") or 0)
            for s in pl.get("game_supers") or [] if s.get("reg")]


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
SCOTLAND_SPLIT = 133                      # the Scottish Premiership's first phase (SHIPPED_SLOT)
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
    for rid, country in sorted(uefakey.game_countries(base).items()):
        day = JULY_START.get(country)
        # Scotland is a split (133-136): its first phase is the regulation, not the whole season
        if day and rid not in seen and country != "Scotland" and rid != SCOTLAND_SPLIT:
            seen.add(rid)
            out.append("july %d %d" % (rid, day))
    return out


def rcal_lines(pl, base, confed):
    """world file lines `rcal <reg> <first> <last> <break> <break> <days> <also>` (0.2.0,
    tools/realcal.py): every new league's real calendar -- the recipe league's "real_calendar",
    else its country's (and tier's) real one, else its confederation's -- which fl26swiss.dll
    dates its rounds from. A split, an Apertura/Clausura and an exhibition league get none."""
    import mkflags
    import realcal
    cty = mkflags.countries(mkflags.table("Country", [base]))
    out, seen = [], set()
    for p in pl["leagues"]:
        if p.get("split") or p.get("apertura") or p.get("exhibition") or not p.get("rid") or p["rid"] in seen:
            continue
        en = mkflags.title((cty.get(p.get("country")) or ("", None))[0] or "")
        c = realcal.calendar_of(en, int(p.get("tier") or 1), (confed or {}).get(p.get("country")),
                                bool(p.get("calendar") or p.get("follows_calendar")), p.get("real_calendar"))
        if c:
            seen.add(p["rid"])
            out.append(realcal.line(p["rid"], c))
    return out


CUPDAYS_MAX = 48                          # days a `cupdays` line carries (fl26swiss CUPD_DAYS)


def cupdays_lines(pl, base, db, log=print):
    """world file lines `cupdays <league reg> <day> ...`: the days the cups of the league's country
    play on, for fl26swiss.dll to keep its rounds a day clear of. It knew only our own cups, the
    European days and the August-May national cups (calendar case 6); a cup of any other calendar
    -- Copa Chile's February and March rounds (case 9) -- had a new Chile D2 play the league the
    day after its quarter-final (antonimus, 2026-10-12). Every league of a country with a cup
    gets one, the game's leagues as well as ours: the game's cups by the dates the exe ships
    (tools/caltab.py, the switch over regulation ids 2..175), a cup of ours by the cup it is
    dated like (`dates <cup> like=<cup>`). Nothing when the exe cannot be read."""
    try:
        import caltab
        img = caltab.Image()
        cs, idc = caltab.cases(img), caltab.id_case(img)
    except (Exception, SystemExit) as e:            # no exe at hand: the old spacing stays
        log("  NOTE: the game's cup dates could not be read (%s); leagues keep clear of our cups only" % e)
        return []

    natcup = {251, 254, 286, 289, 6, 9, 41, 44, 83, 86, 132, 135}   # fl26swiss NATCUP_DAYS

    def days_of(rid):
        c = idc.get(rid) if rid and rid <= caltab.LAST_ID else None
        d = set(cs[c][2]) if c is not None and c != caltab.CASE_EMPTY and c in cs else set()
        return set() if d <= natcup else d          # case 6: the DLL moves and keeps clear of those

    comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
    region_of_cid = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
                     for i in range(len(comp) // M.COMP)}
    cup_days, game = {}, {}
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        rid, region = u16(g, M.R_ID), region_of_cid.get(g[M.R_CID])
        if region is None or rid >= 1024:
            continue
        if g[M.R_TYPE] == 3:                        # a knockout cup of the country
            cup_days.setdefault(region, set()).update(days_of(rid))
        elif g[M.R_TYPE] in (4, fl26world.SPLIT_TOTAL):
            game[rid] = region
    for p in pl["leagues"]:                         # a new country's own cups
        c = p.get("own_cup")
        if not c or not c.get("reg") or p.get("region") is None:
            continue
        for reg, code in ((c["reg"], c["like"]), (c.get("super_reg"), SUPER_CUP_LIKE if c.get("super") else None)):
            like = like_reg(db, code) if reg and code else None
            if like:
                cup_days.setdefault(p["region"], set()).update(days_of(like))
    for s in pl.get("game_supers") or []:              # a game league's new super cup
        like = like_reg(db, SUPER_CUP_LIKE)
        cup_days.setdefault(s["region"], set()).update(
            set(super_days(s)) if s["calendar"] else days_of(like) if like else set())
    leagues = dict(game)
    for p in pl["leagues"]:
        if p.get("rid") and p.get("region") is not None and not p.get("exhibition"):
            leagues[p["rid"]] = p["region"]
    out = []
    for rid, region in sorted(leagues.items()):
        days = sorted(cup_days.get(region) or ())[:CUPDAYS_MAX]
        if days:
            out.append("cupdays %d %s" % (rid, " ".join(str(d) for d in days)))
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
        cids, regs = pinned_ids(pl, db, "cup:" + p["name"])
        if not cids or not regs:
            raise out_of_ids(c["name"])
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
        pl.setdefault("cup_ids", {})["cup:" + p["name"]] = {"cid": c["cid"], "reg": c["reg"]}
        if c.get("super"):
            cids, regs = pinned_ids(pl, db, "super:" + p["name"])
            if not cids or not regs:
                raise out_of_ids(c["super"])
            pl["cup_ids"]["super:" + p["name"]] = {"cid": cids[0], "reg": regs[0]}
            c["super_cid"], c["super_reg"] = cids[0], regs[0]
            call(mkcup, ["--base", db, "--out", root, "--teams", ",".join(map(str, p["teams"][:2])),
                         "--cid", cids[0], "--reg", regs[0], "--region", p["region"], "--name", c["super"],
                         "--code", "FL_%03d_SUPER" % p["rid"], "--like", SUPER_CUP_LIKE, "--bracket", 2])
            log("  %s: competition %d, regulation %d (copied from %s)"
                % (c["super"], cids[0], regs[0], SUPER_CUP_LIKE))


CALENDAR_SUPER_TRY = (30, 27, 24, 21, 18)  # the end of January, then a few days earlier at a time
CALENDAR_SUPER_GAP = 3                      # days clear of the country's own cup either side


def calendar_super_day(region, db, log=print):
    """B198 (antonimus, 22.10.): a February-December game league's new super cup was always on
    day 30 (31 January), and Copa Chile plays its second round on days 30-31: the champion played
    the super cup and a cup leg on two days running. The first day of CALENDAR_SUPER_TRY with no
    cup of the region's (the dates the exe ships, as cupdays_lines reads them) closer than
    CALENDAR_SUPER_GAP days; day 30 when the exe cannot be read"""
    try:
        import caltab
        img = caltab.Image()
        cs, idc = caltab.cases(img), caltab.id_case(img)
    except (Exception, SystemExit) as e:
        log("  NOTE: the game's cup dates could not be read (%s); super cup on day %d"
            % (e, CALENDAR_SUPER_DATE_DAYS[0]))
        return CALENDAR_SUPER_DATE_DAYS[0]
    comp, regs = M.load(db, "Competition.bin"), M.load(db, "CompetitionRegulation.bin")
    region_of_cid = {comp[i * M.COMP + M.CID_OFF]: M.dec_region(comp[i * M.COMP + M.REGION_OFF])
                     for i in range(len(comp) // M.COMP)}
    taken = set()
    for i in range(len(regs) // M.REG):
        g = regs[i * M.REG:(i + 1) * M.REG]
        rid = u16(g, M.R_ID)
        if g[M.R_TYPE] != 3 or region_of_cid.get(g[M.R_CID]) != region or not rid or rid > caltab.LAST_ID:
            continue
        c = idc.get(rid)
        if c is not None and c != caltab.CASE_EMPTY and c in cs:
            taken.update(cs[c][2])
    for d in CALENDAR_SUPER_TRY:
        if all(abs(d - t) >= CALENDAR_SUPER_GAP for t in taken):
            return d
    return CALENDAR_SUPER_DATE_DAYS[0]


def super_days(s):
    """the day(s) a game league's calendar-year super cup is dated on"""
    return (s["day"],) if s.get("day") else CALENDAR_SUPER_DATE_DAYS


def game_super_cups(pl, root, db, log=print):
    """the super cups of the game's leagues (game_supers) into the world's tables, one mkcup.py
    each, the way national_cups() makes a new league's: a copy of SUPER_CUP_LIKE in the league's
    region with its first two clubs, which the game then fills with the champion and the cup
    winner itself (dates_lines dates it)"""
    import mkcup
    ents = M.load(db, "CompetitionEntry.bin")
    for s in pl.get("game_supers") or []:
        listed = sorted((ents[i + M.E_ORDER], int.from_bytes(ents[i + M.E_TEAM:i + M.E_TEAM + 4], "little"))
                        for i in range(0, len(ents), M.ENT) if ents[i + M.E_CID] == s["league_cid"])
        teams = [t for _o, t in listed][:2]
        if len(teams) < 2:
            raise BuildError("%s: league %d has %d clubs in the tables" % (s["name"], s["league"], len(teams)))
        cids, regs = pinned_ids(pl, db, "gsuper:" + s["code"])
        if not cids or not regs:
            raise out_of_ids(s["name"])
        s["cid"], s["reg"] = cids[0], regs[0]
        call(mkcup, ["--base", db, "--out", root, "--teams", ",".join(map(str, teams)),
                     "--cid", s["cid"], "--reg", s["reg"], "--region", s["region"], "--name", s["name"],
                     "--code", s["code"], "--like", SUPER_CUP_LIKE, "--bracket", 2])
        pl.setdefault("cup_ids", {})["gsuper:" + s["code"]] = {"cid": s["cid"], "reg": s["reg"]}
        if s["calendar"]:
            s["day"] = calendar_super_day(s["region"], db, log)
        log("  %s: competition %d, regulation %d (copied from %s%s)"
            % (s["name"], s["cid"], s["reg"], SUPER_CUP_LIKE,
               ", dated as %s, day %s" % (CALENDAR_SUPER_DATE_LIKE, ",".join(map(str, super_days(s))))
               if s["calendar"] else ""))


def continental(cups, root, db, log=print, start=None, want=None, low=False):
    """build the planned continental cups (ccup_plan) with mkccup.py into the world's tables in
    <db>, with ids nothing in them uses -- a cup's own of the last Build first (want, the plan's
    prev_cup_ids); returns the world file's ccup lines"""
    if not cups:
        return []
    import mkccup
    want = want or {}
    all_c, all_r = free_comp_ids(db, low=low)
    pin_c = {w.get("cid") for w in want.values()}
    pin_r = {v for w in want.values() for f, v in w.items() if f != "cid"}
    cids = [c for c in all_c if c not in pin_c]
    free = [r for r in all_r if r not in pin_r]
    used_c, used_r = set(), set()

    def own(key, field, pool, pinned_ok):
        v = (want.get(key) or {}).get(field)
        if v in pinned_ok and v not in used_c | used_r:
            (used_c if field == "cid" else used_r).add(v)
            return v
        if not pool:
            raise out_of_ids("the continental cups")
        return pool.pop(0)
    pres = [c for c in cups if (c.get("opts") or {}).get("pre")]
    keep = sum(1 for c in cups if (c.get("opts") or {}).get("reserve"))
    if len(all_c) < len(cups) or len(all_r) < sum(2 if c["groups"] else 1 for c in cups) + len(pres) + keep:
        raise out_of_ids("the continental cups")
    args = ["--base", db, "--out", root]
    rounds = []
    for cup in cups:
        cup_winners(cup, start)
    for k, cup in enumerate(cups):
        key = "ccup:" + (cup.get("code") or cup["name"])
        cid = own(key, "cid", cids, all_c)
        reg = own(key, "reg", free, all_r)
        ko = own(key, "ko", free, all_r) if cup["groups"] else reg        # a straight knockout is one regulation
        cup.update(cid=cid, reg=reg, ko=ko)
        ko_of = {c.get("number"): c.get("ko") for c in cups[:k]}
        cup["entry"] = [(ko_of[e[1]], 0) if e[0] == "ko" else e for e in cup["entry"]]
        if (cup.get("opts") or {}).get("pre"):         # its ties are <pre> + 1024 * (k + 1)
            cup["pre_reg"] = pre = own(key, "pre_reg", free, all_r)
            rounds.append((pre, cid, cup["name"], len(cup["opts"]["pre"]["entry"]) // 2))
            cup["entry"] = [(pre + 1024 * (e[1] + 1), 0) if e[0] == "pre" else e for e in cup["entry"]]
        elif (cup.get("opts") or {}).get("reserve"):
            free.pop(0)                                # the old cup's pre-round id: later ids stay put
        like = (cup.get("opts") or {}).get("like")
        args += ["--cup", "|".join(str(x) for x in (
            cup["name"], cup["code"], cid, reg, ko, cup["groups"],
            ",".join("%d:%d" % tuple(e) for e in cup["entry"]),
            "" if cup.get("conf") is None else cup["conf"], cup.get("region", ""))
            + ((like,) if like else ()))]
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
    cup["entry"], cup["alt"] = entry, list(cup.get("alt_fixed") or []) + alt


def ccup_alt(line, alt):
    """a world file ccup line with its cup winners' leagues (cup_winners):
    alt=<entry>:<league>:<first position>,..."""
    head, sep, name = line.partition(" name=")
    return "%s alt=%s%s%s" % (head, ",".join("%d:%d:%d" % tuple(a) for a in alt), sep, name)


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
    if o.get("like"):                                  # 0.2.0: a single-match league cup
        words += ["like=%d" % o["like"], "draw=%s" % (o.get("draw") or "byes")]
    if o.get("cal"):
        words.append("cal=1")                              # South American February-December calendar
    if o.get("first"):
        words.append("first=" + ",".join(map(str, o["first"])))
    head, sep, name = line.partition(" name=")
    return "%s %s%s%s" % (head, " ".join(words), sep, name)


def have_picture(path, name, log, what="crest", instead="drawn badge", gone=None, rels=()):
    """the picture file at `path` when there is one, else None and one line of the log.

    A recipe made on another PC keeps that PC's picture paths, so the file may not be here any
    more.  A picture that is gone is treated as the recipe's empty field: the club gets the
    drawn badge with its initials (or the shield of its shirt), the league, cup or competition
    the drawn emblem, the country no flag of ours.  Build stopped with a FileNotFoundError in
    lbassets.square() before (0.2.1).
    gone: the world-folder files (rels) this picture makes go in it, so that Build keeps the ones
    the world has already (keep_added): a ready world from a zip holds the author's crests and
    logos, and built again on this PC they came out as drawn badges (B85)."""
    if not path or os.path.isfile(path):
        return path
    if gone is not None and rels:
        gone.update(rels)
        log("  %s picture not on this PC, the world's own kept if it has one: %s (%s)" % (what, name, path))
    else:
        log("  %s picture not found, %s instead: %s (%s)" % (what, instead, name, path))
    return None


def logo_files(cid):
    """the world-folder files (rel, with /) of competition cid's emblem (lbassets.league_logo)"""
    import mkemblems
    return ["common/render/symbol/emblemLc/emb_%04d%s.png" % (cid, suf) for suf, _px in mkemblems.VARIANTS]


def crest_files(tid):
    """... of team tid's crest (lbassets.club_crest)"""
    import mkcrests
    return ["common/render/symbol/flag/e_%06d%s.png" % (tid, suf) for suf, _px in mkcrests.flag_sizes(tid)]


def flag_files(fid):
    """... of country flag fid (lbassets.country_flag)"""
    import lbassets
    if not isinstance(fid, int):             # a plan names its country by Country.bin id; else no file
        return []
    return ["common/render/symbol/flag/flag_%03d%s.png" % (fid, suf) for suf, _px in lbassets.FLAG_SIZES]


def picture_jobs(pl, base, log=print, gone=None):
    """the pictures of the plan, in the order Build draws them: [(lbassets function, its
    arguments after the world folder, the world-folder files it writes)], and the country flags
    {country: picture}. A later job may write a file an earlier one wrote: the order stands."""
    jobs, flags, done = [], {}, set()

    def job(fn, rels, *args):
        jobs.append((fn, args, list(rels)))
    for p in pl["leagues"] + (pl.get("others") or []):
        if not p.get("others"):              # clubs in no league: no competition, no logo
            job("league_logo", logo_files(p["cid"]), p["cid"], p["name"],
                have_picture(p.get("logo"), p["name"], log, "logo", "drawn emblem", gone, logo_files(p["cid"])))
        if p.get("flag") and p["country"] not in done:
            done.add(p["country"])
            flag = have_picture(p["flag"], p["name"], log, "flag", "the game's flag kept",
                                gone, flag_files(p["country"]))
            if flag:                         # no flag picture: the game's own flag stays
                flags[p["country"]] = flag
                job("country_flag", flag_files(p["country"]), p["country"], flag)
        crests, kits = p.get("club_crests") or [], p.get("club_kits") or []
        gp = game_places(p)
        for k, tid in enumerate(p["teams"]):
            if k in gp:                      # a club of the game keeps its crest
                continue
            pic = crests[k] if k < len(crests) else None
            pic = have_picture(pic, club_name(p, k), log, gone=gone, rels=crest_files(tid))
            job("club_crest", crest_files(tid), tid, p["abbrs"][k], pic, kits[k] if k < len(kits) else None)
        for g in gp.values():                # a new club taking a game club's place: a badge
            if isinstance(g.get("swap"), dict) and g.get("swap_id"):
                job("club_crest", crest_files(g["swap_id"]), g["swap_id"], g.get("swap_abbr") or "", None)
    e = pl.get("edits") or {}
    cid_of = {}
    for rid, v in game_league_edits(pl).items():
        if v.get("logo"):
            if not cid_of:
                cid_of = {r: c for r, c, _, _ in game_leagues(base)}
            if int(rid) in cid_of:
                job("league_logo", logo_files(cid_of[int(rid)]), cid_of[int(rid)], v.get("name") or "",
                    have_picture(v["logo"], v.get("name") or "league %s" % rid, log,
                                 "logo", "drawn emblem", gone, logo_files(cid_of[int(rid)])))
    for cid, v in (e.get("competitions") or {}).items():
        if v.get("logo"):
            job("league_logo", logo_files(int(cid)), int(cid), v.get("name") or "",
                have_picture(v["logo"], v.get("name") or "competition %s" % cid, log,
                             "logo", "drawn emblem", gone, logo_files(int(cid))))
    for tid, v in (e.get("clubs") or {}).items():
        # "kit": a place of the game's NewLife gave another club (refresh_game_leagues, B57); with
        # no crest picture it gets that club's shield (or badge), as a new club does, never the
        # crest of the club that left. The club keeps its id
        if v.get("crest") or "kit" in v:
            pic = have_picture(v["crest"], v.get("name") or tid, log, gone=gone,
                               rels=crest_files(int(tid))) if v.get("crest") else None
            job("club_crest", crest_files(int(tid)), int(tid), v.get("abbr") or v.get("name") or "", pic,
                v.get("kit") or None)
    cups = cup_emblems(pl)
    libq = ((pl.get("cup_ids") or {}).get("conmebol:" + LIBQ_CODE) or {}).get("cid")
    for cid, name, logo in cups:
        if cid == libq and not logo:
            # the Pre-Libertadores: the game's own Copa Libertadores emblem from the person's install
            # (antonimus 24.10.: a drawn placeholder beside the real Libertadores; mato: "do it")
            job("game_emblem", logo_files(cid), cid, name, GAME_LIBERTADORES)
            continue
        job("league_logo", logo_files(cid), cid, name, have_picture(logo, name, log, "logo", "drawn emblem",
                                                                    gone, logo_files(cid)))
    return jobs, flags, len(cups)


def pictures(pl, root, base, log=print, game=None, gone=None):
    """league logos, club crests and kits for the new leagues (tools/lbassets.py); gone (a set):
    the files of every picture whose source is not on this PC go in it (have_picture). The
    pictures are drawn from picture_jobs, which the Build also records (an edit of pictures alone
    redraws just those, pictures_only)."""
    import lbassets
    jobs, flags, ncups = picture_jobs(pl, base, log, gone)
    for fn, args, _rels in jobs:
        getattr(lbassets, fn)(root, *args)
    cups = range(ncups)
    log("  %d league logos, %d cup logos, %d club crests%s" % (
        len(pl["leagues"]), len(cups), sum(len(p["teams"]) - len(game_places(p))
                                           for p in pl["leagues"] + (pl.get("others") or [])),
        ", %d country flags" % len(flags) if flags else ""))
    if not any(p["teams"] for p in pl["leagues"] + (pl.get("others") or [])):
        return
    plain = bool(pl.get("editable_kits"))
    unipar = kits_for(base, game)
    if not unipar:
        log("  WARNING: no kits file (UniformParameter.bin) beside the tables, none unpacked from the game and "
            "no mod that has one: the new clubs get no kit (Unpack from game, then Build again)")
        return
    if unipar != kits_file(base):
        log("  kits drawn on %s (the tables folder has no UniformParameter.bin beside it)" % unipar)
    import mkkits
    ours = []                       # the clubs this Build made: their ids depend on the database (#54)
    for p in pl["leagues"] + (pl.get("others") or []):
        gp = game_places(p)
        ours += [tid for k, tid in enumerate(p["teams"]) if k not in gp]
        ours += [g["swap_id"] for g in gp.values() if isinstance(g.get("swap"), dict) and g.get("swap_id")]
    if not ours:
        return
    args = ["mkkits.py", "--team-bin", os.path.join(root, "common", "etc", "pesdb", "Team.bin"),
            "--unipar", unipar, "--root", root, "--archive", "--clubs", ",".join(map(str, ours)),
            "--fill"]               # clubs another editor added get a kit too (Discord 12.10.)
    over = other_uniforms(game)
    if over:
        # their entries go into ours: ours is read first and would hide them (Kit Studio clubs)
        args += ["--over", ";".join(over)]
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
        dressed = plain_but_dressed(pl, ours, game)
        if dressed:
            log("  WARNING: %d new clubs have Kit Server kits (%s), but Plain kits to change in Edit mode is "
                "on: Kit Server does not dress a club with a plain kit, so those kits are not worn. To wear "
                "them, untick Plain kits on the Build page and Build again (B120)"
                % (len(dressed), ", ".join(map(str, dressed[:8])) + (" ..." if len(dressed) > 8 else "")))
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
    t = unipar[:len(unipar) - len(UNIPAR)].rstrip(os.sep)   # the unpack folder the kits file is in
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


def kit_server_clubs(game):
    """the team ids Kit Server's map.txt gives a kit folder (lines switched on), in the folder the
    game's sider reads: content\\kit-server, or SPFL26's content\\kits"""
    try:
        sider = siderdir.find(game) if game else None
    except (OSError, ValueError):
        sider = None
    out = set()
    for d in ("kit-server", "kits"):
        try:
            text = open(os.path.join(sider, "content", d, "map.txt"), encoding="utf-8-sig", errors="replace").read()
        except (OSError, TypeError):
            continue
        for l in text.splitlines():
            m = re.match(r"\s*(\d+)\s*,", l)
            if m:
                out.add(int(m.group(1)))
    return out


def plain_but_dressed(pl, ours, game):
    """B120: the new clubs (ids ours) that have Kit Server kits -- a kit folder in the recipe or a
    line in Kit Server's map.txt (Import kits) -- in a world built with editable_kits. Kit Server
    leaves a club with a plain (unlicensed) kit undressed ("the team is unlicensed. Disabling
    kits"), so a player who imported kits saw none of them and was told nothing (ZeDosCaes 17.10.)"""
    have = kit_server_clubs(game)
    for p in pl["leagues"] + (pl.get("others") or []):
        for k, f in enumerate(p.get("kit_folders") or []):
            if f and k < len(p["teams"]):
                have.add(p["teams"][k])
    return sorted(t for t in set(ours) if t in have)


def other_uniforms(game):
    """the UniformParameter.bin files of the other mods sider.ini serves, lowest priority first
    (sider gives the root listed first the priority).  The worlds of ours are left out: the one
    being built is replaced, and an old one is not served."""
    try:
        import siderdir
        sider = siderdir.find(game) if game else None
        if not sider:
            return []
        lines = open(os.path.join(sider, "sider.ini"), encoding="utf-8-sig", errors="replace").read().splitlines()
    except (OSError, ImportError, ValueError):
        return []
    out = []
    for l in lines:
        m = re.match(r'\s*cpk\.root\s*=\s*"([^"]+)"', l)
        if not m:
            continue
        d = m.group(1)
        d = os.path.normpath(d if os.path.isabs(d) else os.path.join(sider, d))
        f = os.path.join(d, UNIPAR.replace("/", os.sep))
        if os.path.exists(f) and not os.path.exists(os.path.join(d, "leaguebuilder-plan.json")):
            out.append(f)
    return out[::-1]


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
    for c in (pl.get("ccups") or []) + (pl.get("home_cups") or []) + (pl.get("game_supers") or []):
        if c.get("cid"):
            out.append((c["cid"], c["name"], c.get("logo")))
    # the modern CONMEBOL helper cups (helper_ids) wear the emblem of the cup they are a round of:
    # with none of their own, the Sudamericana's first stage showed no emblem in the fixtures (B220,
    # antonimus 23.10.)
    sud = next((c for c in pl.get("ccups") or [] if c.get("number") == SUDAM), {})
    for code, name, logo in ((SAM_FIRST_CODE, sud.get("name") or SAM_FIRST_NAME, sud.get("logo")),
                             (SPO_CODE, sud.get("name") or SPO_NAME, sud.get("logo")),
                             (LIBQ_CODE, "Copa Libertadores", None)):
        h = (pl.get("cup_ids") or {}).get("conmebol:" + code) or {}
        if h.get("cid"):
            out.append((h["cid"], name, logo))
    if pl.get("uecl"):
        out.append((UECL_CID, "UECL", pl.get("uecl_logo")))
    return out


def mp_column(root, game, log=print):
    """the standings tables with an MP column (matches played) between Points and W, the A column
    kept: the world's copy of rankingTeam.bin (tools/mkmpcol.py), which fl26swiss.dll fills. A
    layout it does not know (another mod's) is left as it is, and the tables stay the game's."""
    import mkmpcol
    try:
        out = call(mkmpcol, ["--root", root, "--game", game])
    except BuildError as e:
        log("  no MP column: %s" % str(e).strip().splitlines()[0])
        return
    if out.startswith("left as it is"):
        log("  no MP column: %s" % out.strip().splitlines()[0])
    else:
        log("  standings with an MP column")


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


def keep_before(path, reason, sider=None, keep_n=30):
    """a copy of `path` before Build, Install the modules or Switch on changes it: a restore point
    in SiderAddons\\ModStudio\\backups (Restore points shows it, Put Sider back as before Mod Studio
    takes the first one). Until 0.2.4 it was <file>.before-builder / <file>.prev next to the file
    and modules\\before-builder-<n>\\ (mato 15.10.: no more copies next to the files)"""
    from modstudio import backups
    return backups.before_change(path, reason, sider, keep_n)


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
# disabled completely?"). Unticking one on the Lua modules page lists it in modules\fl26-off.txt,
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


OURS_HEAD = "; ---- FL26 Mod Studio: its modules, in the order they load. Mod Studio keeps this block ----"
OURS_END = "; ---- end of the FL26 Mod Studio modules ----"


def group_ours(lines):
    """put the lua.module lines of Mod Studio's modules (fl26..., on or off) together, between
    OURS_HEAD and OURS_END, where the first of them is (0.2.4: "group our modules in sider so it
    is easier to read"). Their order among themselves and every other line's stay as they were;
    only another module that sat between two of ours ends up after the block. Changes `lines` in
    place; True when it moved anything."""
    def ours(l):
        m = module_of(l)[0]
        if m:
            return "\\" not in m.replace("/", "\\") and m.startswith("fl26")
        # a note someone left in front of one of ours: "; off 25.09. lua.module = "fl26probe.lua""
        t = l.strip()
        return t.startswith((";", "#")) and re.search(r'lua\.module\s*=\s*"fl26', t) is not None
    marks = {OURS_HEAD, OURS_END}
    idx = [i for i, l in enumerate(lines) if ours(l)]
    if not idx:
        return False
    block = [lines[i] for i in idx]
    first = idx[0]
    # blank lines among ours go: they would pile up under the block
    gaps = {i for i in range(idx[0], idx[-1]) if not lines[i].strip()}
    rest = [(i, l) for i, l in enumerate(lines)
            if i not in set(idx) and i not in gaps and l.strip() not in marks]
    at = sum(1 for i, _l in rest if i < first)
    new = [l for _i, l in rest]
    new[at:at] = [OURS_HEAD] + block + [OURS_END]
    if new == lines:
        return False
    lines[:] = new
    return True


def stale_line(base, order, have):
    """the module of `order` (loaded) that `base` is an old form of, or None:
    fl26caps.<set> (patchset.py keeps every set under its own name) beside fl26caps, or another
    count of a numbered one (fl26slots128 beside fl26slots250, fl26regs300 beside fl26regs600).
    Both on, the second refuses the bytes the first patched (B80)."""
    if base in order or not base.startswith("fl26"):
        return None
    head = base.split(".", 1)[0]
    if head != base:
        return head if head in order and head in have else None
    m = re.match(r"^(fl26[a-z]+)(\d+)$", base)
    return next((x for x in order if m and re.match(r"^%s\d+$" % m.group(1), x) and x in have), None)


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
    retired, gone, instead = retired_modules(), [], {}
    have = set(want) | {module_of(l)[0].replace("/", "\\").rpartition("\\")[2]
                        for l in lines if module_of(l)[0] and module_of(l)[1]}
    for i, l in enumerate(lines):
        m, live = module_of(l)
        base = m.replace("/", "\\").rpartition("\\")[2] if m else None
        if live and base in retired and retired[base] in have:
            lines[i] = ";" + l.strip()
            gone.append(m)
            instead[m] = retired[base]
        elif live and m == base and stale_line(base, order, have):
            # B80 (Yanis, 16.10.): an old caps set's own name (fl26caps.<set>.lua, patchset.py) and
            # an older slots count (fl26slots128 beside fl26slots250) stayed on from a hand install;
            # each refused the bytes the shipped one had patched, and the diagnostics blamed the exe
            lines[i] = ";" + l.strip()
            gone.append(m)
            instead[m] = stale_line(base, order, have)
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
    # ours in `order`'s order: fl26caps first, the others check the bytes it moves (Yanis, 09.10.:
    # after fl26swiss, MISMATCH at 0x14154358f, caps aborted), and each one after the modules whose
    # bytes it expects (B80, 16.10.: slot7 before slots250, deeprank before rank, joindll after
    # swiss -- an alphabetical hand install). Our lines trade places; every other line stays.
    seen, ours_at = set(), []
    for i, l in enumerate(lines):
        m, lv = module_of(l)
        if lv and m in order:
            if m in seen:      # the same module twice: the second refuses what the first patched
                lines[i] = ";" + l.strip()
                gone.append(m)
                instead[m] = "its first line"
                continue
            seen.add(m)
            ours_at.append(i)
    now = [lines[i] for i in ours_at]
    want_order = sorted(now, key=lambda l: order.index(module_of(l)[0]))
    if want_order != now:
        for i, l in zip(ours_at, want_order):
            lines[i] = l
        done.append("ordered")
        log("sider.ini: the modules of Mod Studio are in their load order again (%s first)" % order[0])
    if group_ours(lines):
        done.append("grouped")
        log("sider.ini: the modules of Mod Studio are together now, in one block of their own")
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
            sorted(set(instead.values())))))
    if fixed:
        log("sider.ini: %d module(s) were loaded from a before-builder folder, now from modules: %s"
            % (len(fixed), ", ".join(fixed)))
        done += [m for m in fixed if m not in done]
    if done or gone:
        keep_before(ini, "Mod Studio's modules switched on", os.path.dirname(ini))
        open(ini, "w", encoding="utf-8", newline="\r\n").write("\n".join(lines) + "\n")
        on = [m for m in done if m not in ("ordered", "grouped")]
        if on:
            log("sider.ini: switched on %s" % ", ".join(on))
    return done + gone


def stale_world_modules(game, names, world, log=print):
    """switch off (;) the live lua.module lines of `names`: modules another world brought
    (fl26regions, fl26regnames) that the world `world` being switched on has none of -- they patch
    the exe with the other world's competition and country names. Its own Switch on puts them back
    on. Returns the modules switched off."""
    if not names:
        return []
    ini, lines = ini_lines(game)
    gone = []
    for i, l in enumerate(lines):
        m, live = module_of(l)
        base = m.replace("/", "\\").rpartition("\\")[2] if m else None
        if live and base in names:
            lines[i] = ";" + l.strip()
            gone.append(base)
    if gone:
        keep_before(ini, "Switch on %s: another world's modules switched off" % world, os.path.dirname(ini))
        open(ini, "w", encoding="utf-8", newline="\r\n").write("\n".join(lines) + "\n")
        log("sider.ini: switched off %s -- %s brings none, they were another world's"
            % (", ".join(sorted(set(gone))), world))
    return gone


DLL_REF = re.compile(r'"([A-Za-z0-9_]+\.dll)"')    # how our Lua names its DLL: "fl26swiss.dll"
AV_WINERRORS = (225, 226)                 # ERROR_VIRUS_INFECTED, ERROR_VIRUS_DELETED


def dll_names(lua_path):
    """the DLLs a module's Lua loads from the modules folder (the quoted names in its text)"""
    try:
        with open(lua_path, encoding="utf-8", errors="replace") as f:
            return sorted(set(DLL_REF.findall(f.read())))
    except OSError:
        return []


def check_dlls(dst, names, src=None):
    """the DLLs of the modules folder `dst` that are not there as they should be, as
    [(dll, why)]: why is "missing", "blocked" (Windows refuses to open it -- an antivirus holds
    or quarantines it) or "changed" (empty, or not the bytes of src's copy when `src`, the pack's
    modules folder, has one).

    B15 (bikolunar42, 13.10.): an antivirus took fl26swiss.dll, fl26join.dll ... out of
    SiderAddons\\modules right after Install modules; the .lua files stayed, sider.log said
    LoadLibraryA failed (error 126), and Mod Studio said nothing."""
    import hashlib
    out = []
    for f in names:
        p = os.path.join(dst, f)
        if not os.path.isfile(p):
            out.append((f, "missing"))
            continue
        try:
            with open(p, "rb") as h:
                data = h.read()
        except OSError:
            out.append((f, "blocked"))
            continue
        ref = os.path.join(src, f) if src else None
        if not data:
            out.append((f, "changed"))
        elif ref and os.path.isfile(ref):
            try:
                with open(ref, "rb") as h:
                    want = h.read()
            except OSError:
                continue
            if len(want) != len(data) or hashlib.sha256(want).digest() != hashlib.sha256(data).digest():
                out.append((f, "changed"))
    return out


def dll_message(problems, dst):
    """what check_dlls found, in plain words: which files, that an antivirus probably took them,
    and what to do"""
    gone = [f for f, why in problems if why != "changed"]
    changed = [f for f, why in problems if why == "changed"]
    text = []
    if gone:
        one = len(gone) == 1
        text.append("%s %s missing from %s (or Windows will not open %s) right after the install. An antivirus "
                    "(Windows Security, Avast ...) has probably removed or quarantined %s. Without %s the game "
                    "starts, but the parts of the new leagues %s run are silently missing (European draws, "
                    "new players, cups)." % (", ".join(gone), "is" if one else "are", dst,
                                             "it" if one else "them", "it" if one else "them",
                                             "it" if one else "them", "it" if one else "they"))
    if changed:
        text.append("%s in %s %s not the file Mod Studio installed (empty or different): an antivirus may have "
                    "changed %s." % (", ".join(changed), dst, "is" if len(changed) == 1 else "are",
                                     "it" if len(changed) == 1 else "them"))
    text.append("Add the SiderAddons folder (%s) as an exclusion in your antivirus (Windows Security: Virus & "
                "threat protection > Manage settings > Exclusions > Add or remove exclusions > Add an exclusion "
                "> Folder), then press Install the modules again (Home > Install now, or Build and edit your "
                "world > Build > Step by step > 0. Install the modules)." % os.path.dirname(os.path.normpath(dst)))
    return " ".join(text)


def shipped_files(src):
    """the files of the pack's modules folder to install. A module a bundle replaced is left out:
    an update unpacked over an older Mod Studio (the updater, or a zip into the same folder) keeps
    the old pack's single files, and each install copied them in only to move them out again --
    Home said "2 modules missing" for ever (B37, a tester's 0.2.4 beta, 15.10.)"""
    gone = retired_modules()
    return [f for f in sorted(os.listdir(src))
            if os.path.isfile(os.path.join(src, f)) and not (f.endswith(".lua") and f[:-4] in gone)]


def install_modules(game, log=print, settle=2.0):
    """put the pack's modules in the Sider folder's modules and load them from sider.ini.

    Every file it would replace, and sider.ini, is kept first as a restore point (keep_before;
    until 0.2.4 in modules\\before-builder-<n>\\ and sider.ini.before-builder), so the install
    can be undone on Restore points.

    At the end every DLL of the pack must be in modules as it was shipped (check_dlls): an
    antivirus that takes one away a moment after the copy (B15) stops the install with a
    BuildError that names the file and says what to do. `settle`: seconds to give the
    antivirus first."""
    pack = pack_dir()
    order = open(os.path.join(pack, "modules.txt"), encoding="utf-8").read().split()
    ini, _ = ini_lines(game)
    dst = os.path.join(siderdir.find(game), "modules")
    if not os.path.isdir(dst):
        raise BuildError("no %s -- is Sider installed in this game folder?" % dst)
    src = os.path.join(pack, "modules")
    changed, same, kept = [], 0, 0
    sider = os.path.dirname(dst)
    for f in shipped_files(src):
        a, b = os.path.join(src, f), os.path.join(dst, f)
        if os.path.exists(b) and open(a, "rb").read() == open(b, "rb").read():
            same += 1
            continue
        changed.append(f)
    if changed:
        for f in changed:
            b = os.path.join(dst, f)
            if os.path.exists(b):
                # a restore point, not modules\before-builder-<n>\ (mato 15.10.); a module's newest
                # 3 copies and its first: the face pack is big
                keep_before(b, "Install the modules: replaced by Mod Studio's", sider, keep_n=3)
                kept += 1
            try:
                shutil.copy2(os.path.join(src, f), b)
            except OSError as e:
                if getattr(e, "winerror", None) in AV_WINERRORS:     # Windows: "the file contains a virus"
                    raise BuildError(dll_message([(f, "blocked")], dst))
                raise
        log("modules: %d copied, %d already there%s" % (len(changed), same,
            ("; the %d old one(s) are in Restore points" % kept) if kept else ""))
    else:
        log("modules: all %d already there" % same)
    old = [m for m in retired_modules() if os.path.exists(os.path.join(dst, m + ".lua"))]
    if old:
        # the single files a bundle replaced go out of modules; Restore points keeps them
        for m in old:
            p = os.path.join(dst, m + ".lua")
            keep_before(p, "Install the modules: %s now ships bundled" % m, sider, keep_n=3)
            os.remove(p)
        log("modules: %s now ship bundled; the single files are in Restore points" % ", ".join(old))
    # B177 (Vran 20.10.): the modules a world brings (fl26regions, fl26regnames) are not in the pack;
    # Home said they were switched off and Install now passed them by. The live world's come from
    # its folder, as its Switch on puts them; one no world in the game brings is not switched on
    per = world_modules(game)
    for m, a in sorted(per.items()):
        b = os.path.join(dst, m + ".lua")
        if os.path.exists(b) and open(a, "rb").read() == open(b, "rb").read():
            continue
        if os.path.exists(b):
            keep_before(b, "Install the modules: the world's own", sider, keep_n=5)
        shutil.copy2(a, b)
        log("modules: %s.lua of the world in the game (%s) put in" % (m, live_world(game)))
    shipped = {f[:-4] for f in shipped_files(src) if f.endswith(".lua")}
    have = {f[:-4] for f in os.listdir(dst) if f.endswith(".lua")}
    ensure_modules(game, order, [m for m in order if m in have and (m in shipped or m in per)], log)
    roots = os.path.join(pack, "livecpk")
    for r in sorted(os.listdir(roots)) if os.path.isdir(roots) else []:
        install_root(game, os.path.join(roots, r), log)
    dlls = sorted(f for f in os.listdir(src) if f.lower().endswith(".dll"))
    if dlls:
        if settle:
            import time
            time.sleep(settle)                 # an antivirus scans a new file a moment after it is written
        bad = check_dlls(dst, dlls, src)
        if bad:
            msg = dll_message(bad, dst)
            log("modules: " + msg)
            raise BuildError(msg)
        log("modules: all %d DLLs in place" % len(dlls))
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
    keep_before(ini, "Install the modules: livecpk\\%s loaded" % name, os.path.dirname(ini))
    open(ini, "w", encoding="utf-8", newline="\r\n").write("\n".join(lines) + "\n")
    log("livecpk: %s (%d files), sider.ini loads it" % (name, n))


# ---- on: the live world ----

def switch_on(world, game, log=print, redraw=False):
    root = os.path.join(siderdir.find(game), "livecpk", world)
    wf = os.path.join(root, MARK)
    if world.lower().endswith((".building", ".old")):
        # B150: a Build's unfinished work folder is no world to switch on
        raise BuildError("%s is what a Build left unfinished, not a world -- Build %s again"
                         % (root, world.rsplit(".", 1)[0]))
    if not os.path.exists(wf):
        raise BuildError("%s has no %s -- not a league builder world" % (root, MARK))
    import siderroot
    siderroot.INI = os.path.join(siderdir.find(game), "sider.ini")
    if not os.path.exists(siderroot.INI):
        raise BuildError("no %s -- is Sider installed in this game folder?" % siderroot.INI)
    log(call(siderroot, [world]).strip())
    dst = os.path.join(siderdir.find(game), "modules", MARK)
    keep_before(dst, "Switch on %s: the world file" % world, siderdir.find(game))    # was fl26world.txt.prev
    shutil.copy2(wf, dst)
    log("world file -> %s" % dst)
    try:                                               # Edit club > Home stadium (Stadium Server)
        with open(os.path.join(root, "leaguebuilder-plan.json"), encoding="utf-8") as f:
            built = json.load(f)
    except (OSError, ValueError):
        built = None
    if built is not None:
        import lbstadiums, lbservers
        lbstadiums.write(built, siderdir.find(game), log, lbstadiums.load_edits(root))
        lbservers.write(built, siderdir.find(game), log, root, redraw=redraw)
    mods = os.path.join(root, "modules")
    for f in sorted(os.listdir(mods)) if os.path.isdir(mods) else []:
        dst = os.path.join(siderdir.find(game), "modules", f)
        if os.path.exists(dst) and open(dst, "rb").read() != open(os.path.join(mods, f), "rb").read():
            keep_before(dst, "Switch on %s: its own module" % world, siderdir.find(game), keep_n=5)
        shutil.copy2(os.path.join(mods, f), dst)
        log("%s -> %s" % (f, dst))
    import lbpack
    if os.path.isdir(mods):
        ensure_modules(game, lbpack.ORDER, [f[:-4] for f in os.listdir(mods) if f.endswith(".lua")], log)
    # B177: another world's fl26regions / fl26regnames name that world's competitions and countries
    stale_world_modules(game, set(lbpack.PER_WORLD) - set(world_modules(game, world)), world, log)
    commonlib_leagues(game, world, wf, log)
    import lbtrophies                    # Leagues > More > Trophies: FL26's Entrance.lua shows them
    lbtrophies.switch_on(siderdir.find(game), world, root, log, keep_before)
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
        keep_before(path, "Switch on %s: its leagues in the Kick Off list" % world, siderdir.find(game))
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

# what our modules wrote (fl26caps: [i/n] 0x.. old -> new) and where one found other bytes (MISMATCH)
_WROTE = re.compile(r"^\[[\w.-]+\.lua\] [\w ]+: \[\d+/\d+\] 0x([0-9a-fA-F]+) [0-9a-fA-F]+ -> ([0-9a-fA-F]+)")
_MISMATCH = re.compile(r"^\[([\w.-]+\.lua)\] [\w ]+: MISMATCH at 0x([0-9a-fA-F]+): found \S+, expected ([0-9a-fA-F]+)")


def refused_in_exe(lines, mods):
    """of the modules that refused (ABORTED), the ones whose every MISMATCH is at bytes no module of
    ours wrote in that game: FL_2026.exe itself is changed there -- another mod's fix at that spot,
    which Install now cannot mend (B145, Schmiddi 18.10.: fl26nullguard9 next to a crash fix's jump)"""
    wrote, missed = [], {}
    for l in lines:
        m = _WROTE.match(l)
        if m:
            wrote.append((int(m.group(1), 16), len(m.group(2)) // 2))
        m = _MISMATCH.match(l)
        if m:
            missed.setdefault(m.group(1), []).append((int(m.group(2), 16), len(m.group(3)) // 2))
    return [mod for mod in mods if missed.get(mod) and not any(
        a < b + bn and b < a + an for a, an in missed[mod] for b, bn in wrote)]

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
    # -- unless fl26caps took the exe: then the others refused bytes another line of ours had
    # patched first, an old module or one twice or out of order (B80), and Install now mends it
    caps = [l for l in text if l.startswith("[fl26caps.lua]")]
    caps_took = bool(caps) and not any(re.search(r"\bABORTED\b", l) for l in caps)
    aborted = [m.group(1) + ".lua" for m in (re.match(r"^\[([\w.-]+)\.lua\] .*\bABORTED\b", l) for l in text) if m]
    in_exe = refused_in_exe(text, aborted) if caps_took else []
    for l in text:
        m = re.match(r"^\[([\w.-]+)\.lua\] .*\bABORTED\b", l)
        if m and m.group(1) + ".lua" in in_exe:
            # the rest is in; only that fix is off where the exe has another mod's change (B145)
            log("  %-14s found FL_2026.exe already changed at its spot by another mod, that fix is off: %s"
                % (m.group(1), l.split("] ", 1)[-1].strip()))
        elif m:
            log("  %-14s %s: %s" % (m.group(1), "refused bytes another module had changed" if caps_took
                                    else "refused the game's exe", l.split("] ", 1)[-1].strip()))
            ok = False
    if caps_took and not ok:
        log("  fl26caps took the exe: sider.ini loads an old module of ours, one twice, or ours out of "
            "order -- Install now puts the lines right")
    # a DLL an antivirus took away (B15): the Lua loads, LoadLibraryA fails with error 126
    mdir = os.path.join(siderdir.find(game), "modules")
    names = sorted({d for m in READERS + ["fl26regen", "fl26edit", "fl26walk", "fl26compcache"]
                    for d in dll_names(os.path.join(mdir, m + ".lua"))})
    bad_dlls = check_dlls(mdir, names)
    if bad_dlls:
        log("  " + dll_message(bad_dlls, mdir))
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
        recipe = load_recipe(a[1])
        prev = None
        try:   # the world's last Build: its leagues keep their ids (prev_pins)
            with open(os.path.join(siderdir.find(game), "livecpk", recipe.get("world", ""), "leaguebuilder-plan.json"),
                      encoding="utf-8") as f:
                prev = json.load(f)
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        pl = plan(recipe, base, prev)
        print(describe(pl))
        if a[0] == "build":
            build(pl, base, game, "--replace" in a)
        return 0
    except BuildError as e:
        print("error: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
