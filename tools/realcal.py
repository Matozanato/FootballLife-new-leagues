"""realcal.py -- real-world league calendars for the world file (0.2.0).

A league's round dates come from the world file's `rcal` line, read by fl26swiss.dll:

    rcal <reg> <first> <last> <break from> <break to> <days> <also> [eu]

- first / last: the days of the year the first and the last round fall on (1 January = 0). An
  August-May league counts across New Year: first 205 (25 July), last 142 (23 May).
- break from / to: the winter (or a calendar-year league's summer) break, both days inside it,
  no round on them; 0 0 for none.
- days: the weekdays the rounds go on, a bit each, Monday 1 ... Saturday 32, Sunday 64; also:
  the weekdays a round may take when its own are taken (a Friday or Sunday), at a small cost.
  Any other weekday only when the season is too short for its rounds (a 46-round league).
- eu: optional, 1 to treat the league as one whose clubs play in Europe; without it fl26swiss
  finds that itself (a uefa line of the league, or of a cup its clubs play: cupdraw).

The days are those of 2026 (Saturday 1 August = 212), the frame of the European dates in
fl26swiss.c; the game counts days of the year, so the weekday moves a day a year.

Where the dates come from, first found wins: the recipe league's "real_calendar" (a dict of
first, last, break, days and also as dates "MM-DD" and weekday names; false: no line), the
country's real calendar (COUNTRY, docs/real-calendars), the confederation's default (CONFED).
A league none of them names, a split league and an exhibition league get no line and keep the
calendar they had.

python tools/realcal.py <fl26world.txt> [--write] prints (or writes into an existing world file)
the rcal lines of its leagues, so an installed world takes real calendars without a rebuild.
"""
import datetime
import os
import re
import sys

DAYS = {"mon": 1, "tue": 2, "wed": 4, "thu": 8, "fri": 16, "sat": 32, "sun": 64}
YEAR0 = datetime.date(2026, 1, 1)


def day(md):
    """'07-25' -> the day of the year in 2026 (205)"""
    m, d = (int(x) for x in md.split("-"))
    return (datetime.date(2026, m, d) - YEAR0).days


def mask(names):
    return sum(DAYS[n] for n in names.replace(",", " ").split()) if names else 0


def cal(first, last, brk=None, days="sat sun", also="fri"):
    """a calendar from dates: first and last round, the break (first and last day of it)"""
    return (day(first), day(last), day(brk[0]) if brk else 0, day(brk[1]) if brk else 0,
            mask(days), mask(also))


# The modpack's 34 leagues and the countries around them, from docs/real-calendars.md
# (research 2026-10-08, the 2025/26 and 2026/27 seasons): the first round on the real
# weekend (a Friday for a league that kicks off on one), the last one on the real last
# weekend of the regular season, the winter break from the first free day to the last.
# Keyed by country and tier (None: any tier the country has no own line for).
COUNTRY = {
    ("Albania", None): cal("08-22", "05-10", ("12-22", "01-15")),
    ("Bosnia and Herzegovina", None): cal("08-01", "05-30", ("12-14", "02-05")),
    ("Bulgaria", None): cal("07-17", "05-24", ("12-09", "02-05"), also="fri mon"),
    ("Croatia", 1): cal("07-31", "05-23", ("12-21", "01-22")),
    ("Croatia", 2): cal("08-22", "05-30", ("12-01", "02-12")),
    ("Croatia", None): cal("08-22", "05-30", ("11-30", "02-19")),
    ("Montenegro", None): cal("08-01", "05-24", ("12-14", "02-19")),
    ("North Macedonia", None): cal("08-01", "05-24", ("12-10", "02-12")),
    ("Serbia", None): cal("07-18", "05-24", ("12-21", "01-29")),
    ("Slovenia", None): cal("07-17", "05-23", ("12-07", "01-29")),
    ("Romania", None): cal("07-11", "05-24", ("12-22", "01-15"), also="fri mon"),
    ("Hungary", None): cal("07-25", "05-17", ("12-21", "01-22")),
    ("Cyprus", None): cal("08-29", "05-23", ("12-22", "01-01")),
    ("Greece", 1): cal("08-22", "05-17", ("12-22", "01-02"), days="sun sat"),
    ("Greece", None): cal("09-05", "04-12", ("12-22", "01-02"), days="sun sat"),
    ("Ukraine", None): cal("07-31", "05-24", ("12-14", "02-19"), also="fri mon"),
    ("Austria", 1): cal("07-31", "05-17", ("12-15", "02-04")),
    ("Austria", None): cal("07-31", "05-24", ("12-01", "02-18")),
    ("Switzerland", None): cal("07-25", "05-17", ("12-21", "01-15")),
    ("Czechia", None): cal("07-25", "05-24", ("12-15", "01-29")),
    ("Czech Republic", None): cal("07-25", "05-24", ("12-15", "01-29")),
    ("Slovakia", None): cal("07-25", "05-17", ("12-15", "02-05")),
    ("Poland", 1): cal("07-24", "05-23", ("12-09", "01-28"), also="fri mon"),
    ("Poland", None): cal("07-24", "05-24", ("12-07", "02-05"), also="fri mon"),
    ("Norway", None): cal("03-28", "11-29", ("06-01", "06-24")),
    ("Sweden", None): cal("04-04", "11-08", ("06-01", "06-25")),
    ("Germany", 1): cal("08-22", "05-16", ("12-21", "01-08")),
    ("Germany", None): cal("07-31", "05-17", ("12-22", "01-14"), also="fri sun"),
    ("Belgium", 1): cal("07-25", "05-24", ("12-28", "01-15")),
    ("Belgium", None): cal("08-08", "04-19", ("12-28", "01-15"), also="fri sun"),
    ("Netherlands", 1): cal("08-08", "05-17", ("12-22", "01-08")),
    ("Netherlands", None): cal("08-07", "04-24", ("12-21", "01-07"), days="fri", also="sat sun mon"),
    ("Portugal", 1): cal("08-08", "05-17", ("12-23", "01-01"), days="sun sat"),
    ("Portugal", None): cal("08-08", "05-17", ("12-23", "01-01"), days="sun sat"),
    ("Spain", 1): cal("08-15", "05-24", ("12-22", "01-02"), days="sun sat"),
    ("Spain", 2): cal("08-15", "05-31", ("12-22", "01-02"), days="sun sat"),
    ("Spain", None): cal("08-29", "05-24", ("12-21", "01-03"), days="sun sat"),
    ("Italy", 1): cal("08-22", "05-24", ("12-30", "01-02"), days="sun sat"),
    ("Italy", 2): cal("08-22", "05-09", ("12-30", "01-02"), days="sat sun"),
    ("Italy", None): cal("08-22", "04-26", ("12-21", "01-03"), days="sun sat"),
    ("England", 1): cal("08-15", "05-24", None, days="sat sun"),
    ("England", 2): cal("08-08", "05-02", None, days="sat", also="sun fri"),
    ("England", 3): cal("08-01", "05-02", None, days="sat", also="sun fri"),
    ("England", 4): cal("08-01", "05-02", None, days="sat", also="sun fri"),
    ("England", None): cal("08-08", "04-25", None, days="sat", also="sun fri"),
    ("Scotland", None): cal("08-01", "05-17", None, days="sat", also="sun"),
    ("Turkey", None): cal("08-08", "05-17", ("12-22", "01-15"), days="sat sun", also="fri mon"),
    ("Denmark", None): cal("07-18", "05-17", ("12-07", "02-05"), days="sun sat", also="fri mon"),
    ("France", None): cal("08-15", "05-17", ("12-14", "01-02"), days="sat sun", also="fri"),
}

# The rest of the world, by confederation (2 UEFA, 3 AFC, 4 CONMEBOL, 5 CAF, 6 CONCACAF, 7 OFC)
# and season: (code, False) an August-May league, (code, True) a January-December one. A
# January-December league joins its season in mid February (fl26join), so none starts before.
CONFED = {
    (2, False): cal("08-08", "05-24", ("12-21", "01-08")),
    (2, True): cal("04-04", "11-08", ("06-01", "06-25")),
    (3, False): cal("08-22", "05-23"),
    (3, True): cal("02-28", "12-06"),
    (4, False): cal("08-08", "05-24", ("12-14", "01-15")),
    (4, True): cal("02-21", "12-06"),
    (5, False): cal("08-29", "05-31"),
    (5, True): cal("02-21", "12-06"),
    (6, False): cal("07-11", "05-24", ("12-14", "01-07")),
    (6, True): cal("02-21", "10-18"),
    (7, False): cal("08-08", "05-24", ("12-21", "01-08")),
    (7, True): cal("02-21", "12-06"),
    (0, False): cal("08-08", "05-24", ("12-21", "01-08")),
    (0, True): cal("02-21", "12-06"),
}

# Asia's West and the Gulf play August to May, like Europe (CONFED[(3, False)])
WEST_ASIA = {"Saudi Arabia", "United Arab Emirates", "Qatar", "Kuwait", "Bahrain", "Oman", "Iran",
             "Iraq", "Jordan", "Lebanon", "Syria", "Yemen", "Palestine"}

# The flag ids of the countries above, as Country.bin numbers them, for a world file's
# `country=` (the command-line use, where the game's tables are not at hand)
FLAG = {191: "Albania", 194: "Austria", 197: "Belgium", 198: "Bosnia and Herzegovina", 199: "Bulgaria",
        200: "Croatia", 201: "Cyprus", 202: "Czechia", 204: "England", 210: "Germany", 211: "Greece",
        212: "Hungary", 215: "Italy", 221: "North Macedonia", 224: "Netherlands", 226: "Norway",
        227: "Poland", 228: "Portugal", 229: "Romania", 234: "Slovakia", 235: "Slovenia",
        236: "Spain", 237: "Sweden", 238: "Switzerland", 239: "Ukraine", 303: "Serbia",
        304: "Montenegro"}


def parse_override(o):
    """the recipe's "real_calendar": {"first": "07-25", "last": "05-23", "break": ["12-21",
    "01-22"] or null, "days": "sat sun", "also": "fri"}"""
    brk = o.get("break")
    return cal(o["first"], o["last"], tuple(brk) if brk else None, o.get("days") or "sat sun",
               o.get("also") if o.get("also") is not None else "fri")


def calendar_of(country, tier, confed=None, calendar=False, override=None):
    """the (first, last, break from, break to, days, also) of a league, or None"""
    if override is False:
        return None
    if isinstance(override, dict):
        return parse_override(override)
    for key in ((country, tier), (country, None)):
        if key in COUNTRY:
            c = COUNTRY[key]
            # a country table line is August-May or January-December as its dates say; a league
            # of the other kind falls through to the confederation's
            if (c[0] < c[1]) == bool(calendar):
                return c
    if calendar:
        return CONFED.get((confed or 0, True), CONFED[(0, True)])
    if confed == 3 and country in WEST_ASIA:
        return CONFED[(3, False)]
    return CONFED.get((confed or 0, False), CONFED[(0, False)])


def line(rid, c):
    return "rcal %d %d %d %d %d %d %d" % ((rid,) + tuple(c))


def world_lines(path):
    """the rcal lines for an existing world file's leagues (the command-line use): its league
    lines' country and tier; a calendar-year league is one of a `season <region> 1` line"""
    cal_regions, leagues = set(), []
    for ln in open(path, encoding="utf-8", errors="replace"):
        w = ln.split()
        if len(w) >= 3 and w[0] == "season" and w[2] == "1":
            cal_regions.add(int(w[1]))
        elif w and w[0] == "league":
            kv = dict(x.split("=", 1) for x in w[2:] if "=" in x and not x.startswith("name="))
            leagues.append((int(w[1]), kv))
    out = []
    for rid, kv in leagues:
        country = FLAG.get(int(kv.get("country", 0)))
        conf = int(kv.get("conf", 0) or 0)
        cy = int(kv.get("region", -1)) in cal_regions
        if not country and not conf:
            continue
        c = calendar_of(country, int(kv.get("tier", 1)), conf, cy)
        if c:
            out.append(line(rid, c))
    return out


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    path = argv[0]
    lines = world_lines(path)
    if "--write" not in argv:
        print("\n".join(lines))
        return 0
    keep = [ln.rstrip("\r\n") for ln in open(path, encoding="utf-8") if not re.match(r"\s*rcal\s", ln)]
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(keep + lines) + "\n")
    print("%s: %d rcal line(s)" % (path, len(lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
