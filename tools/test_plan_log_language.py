r"""python tools/test_plan_log_language.py

Z3 D17 (FL Testovi, 20.11.2026, rc2): in Croatian (and every other language) most of Check the
plan stayed English. The plan's summary is one text of many lines, and tr() ran the "log" rules over
it whole, so a rule's ^ and $ held for its first and last line only; and some kinds of line had no
rule at all (team ids, player changes, the European places of a league of the game, the play-offs
for promotion, the super cups, the Select Team notes, the cups).

Now tr() goes line by line and each such line has a rule in hr, es, fr and pt. Offline: the lines
are made with leaguebuilder's own formats, no game, no window.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


# one line of each kind, as leaguebuilder.describe writes them (D17's log, 20.11.2026)
PLAN = """world _FL26Megapack: 317 new leagues, changes to 0 of the game's leagues and 0 of its clubs
  team ids: 5880 free in the new-club block (76040..81919)
  Conference League: yes (competition 123, regulations 400/401)
  player changes in 5047 clubs
  European places of Jupiler Pro League (a league of the game): cup winner Europa League, 1. Champions League, 2. Champions League qualifying, 3. Europa League qualifying, 4. Conference League
  European places of Liga de Primera (a league of the game): none
  Allsvenskan                reg 300  comp 400  region 10  slot 120  division 1  16 clubs x2
      plays February to December with the league above it (the game's season for that country), promotion and relegation at New Year
      European places: cup winner Conference League qualifying, 1. Champions League qualifying, 2. Conference League qualifying
  groups of one division: Serie C Girone A, Serie C Girone B under the game's league 82 -- 3 down, 1 + 1 + 1 up, every league keeps its size (fl26chain moves the set at the season's end)
      border clubs of Serie C Girone A (they make room for a relegated club of its region): Carpi -> Serie C Girone B
  EXPERIMENTAL: the game's leagues of Japan, Saudi Arabia play August to May
  NOTE: Uzbekistan Pro League takes the place of the game's "Other Latin American Teams" group in Select Team
  July and August qualifying: Champions League: first qualifying round, second qualifying round, third qualifying round, play-off
  European places (listed / clubs straight into the league phase): Champions League 28/28, Europa League 18/12 (6 into its qualifying rounds), Conference League 10/12 (2 more from the big five), Europa League 30/28 (2 over)
  qualifying places (listed / new clubs of the rounds): Champions League qualifying 56/56, Europa League qualifying 40/40
  China League One: the country's cup (regulation 127) takes both divisions, 32 clubs
  J2 League: the country's cup (regulation 55) keeps the top division's clubs only
  Primera Federacion Grupo 1: the country's cup (regulation 25) keeps the game's divisions 19 and 80
  Liga 2: the country's cup (regulation 26) keeps the game's divisions 19 and 80, and the first 4 of this league: 40 clubs
  Australia Cup: national cup of 12 clubs (a cup of its own; its rounds and dates follow SCOTLAND_CUP), the top division only
  Korea Cup: national cup of 28 clubs (a cup of its own; its rounds and dates follow ENGLAND_D1_CUP), the two divisions and the first 4 of K3 League
  Iranian Super Cup: super cup, the champion v the cup winner (its date follows BELGIUM_SUPER_CUP)
  Kyrgyzstan Super Cup: super cup, the champion v the cup winner (at the end of January, after the February-December season: dated as JAPAN_SUPER_CUP, day 30)
  CAF Champions League: 32 clubs, 8 groups of four, then a knockout of 16; 16 of them the winners of a preliminary round of 32 clubs, one match a tie
  CONCACAF Champions Cup: 16 clubs, a knockout; 16 of them the winners of a preliminary round of 32 clubs, one match a tie
  CAF Super Cup: the winners of the CAF Champions League and the Confederation Cup, one match in late July (first played in a career's second season)
  Recopa Sudamericana: the previous Libertadores and Sudamericana winners, one match in late February (normally first played in a career's second season)
  TFF 3. Lig 2. Grup Promotion Play-off: play-off for a place in the league above, filled on day 149, its winner moved at the season's end (fl26chain), a knockout of 4 clubs
  Liga Cup: league cup, a single-match knockout of 16 clubs, 8 of them from a pre-round of 16 clubs in late September
  Playoffs MX: playoff, filled on day 200, a knockout of 8 clubs
  Copa de la Liga: pre-season cup in July, a knockout of 4 clubs
  Supercopa do Brasil: super cup, the champion v the cup winner, at the end of January (February-December season)
  Supercopa de Chile: super cup, the champion v the cup winner, its date follows BELGIUM_SUPER_CUP"""

# English left over: the line's English words (league and cup names, NOTE's group name and
# PAZI-like words of the target language aside)
ENGLISH = re.compile(r"\b(?:free in|player changes|European places|a league of the game|plays February|"
                     r"the game's|groups of one|border clubs|EXPERIMENTAL: the|takes the place|qualifying|"
                     r"listed|clubs straight|into its|more from|over\)|country's cup|takes both|keeps the|"
                     r"national cup of|a cup of its own|the top division only|the two divisions|super cup|"
                     r"the champion v|cup winner|groups of four|knockout|preliminary round|one match|"
                     r"the winners of|the previous|play-off for|filled on day|league cup|pre-season|"
                     r"in late|none$)")        # "division 1  16 clubs x2" is French as well
NAMES = re.compile(r"Other Latin American Teams|TFF 3\. Lig 2\. Grup Promotion Play-off|Playoffs MX|"
                   r"Liga Cup|Copa de la Liga|CONCACAF Champions Cup|Recopa Sudamericana|CAF Super Cup|"
                   r"Iranian Super Cup|Kyrgyzstan Super Cup|Supercopa do Brasil|Supercopa de Chile")


def main():
    from modstudio import i18n
    i18n.CODE = "en"
    ok("English: tr leaves the plan as it is", i18n.tr(PLAN) == PLAN)
    for code in ("hr", "es", "fr", "pt"):
        i18n.TEXT.clear()
        del i18n.RULES[:]
        for d in reversed(i18n._dirs()):        # as set_language, without Qt's buttons
            p = os.path.join(d, code + ".json")
            if os.path.exists(p):
                import json
                with open(p, encoding="utf-8") as f:
                    i18n.RULES[:0] = json.load(f).get("log", [])
        whole = i18n.tr(PLAN)
        lines = whole.split("\n")
        ok("%s: as many lines as the plan" % code, len(lines) == len(PLAN.split("\n")))
        ok("%s: the whole text gives what each line gives" % code,
           lines == [i18n.tr(l) for l in PLAN.split("\n")])
        left = [l for l in lines if ENGLISH.search(NAMES.sub("", l))]
        ok("%s: no line left in English%s" % (code, "".join("\n    " + l for l in left)), not left)
        ok("%s: the numbers stay" % code, "76040..81919" in whole and "5047" in whole and "day 149" not in whole
           and "149" in whole and "JAPAN_SUPER_CUP" in whole)
    print("all %d passed" % N)


if __name__ == "__main__":
    main()
