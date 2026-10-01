r"""squadimport -- a squad from any table: a CSV someone typed, exported from a website, from
Football Manager or from an EA FC database, turned into our players' fields.

    python squadimport.py <table.csv> [--base <tables dir>] [--nation <Country.bin id>]
                          [--map "column=target" ...] [--level 65] [--out squad.csv]

The table has one player per line. Its columns are recognised by their names (English, and a
few in Croatian): a name (or first + last name), position(s), age or birth date, nationality,
height, weight, foot, shirt number, an overall rating, and any ratings it has -- EA FC's six
card values or its detailed ones, Football Manager's 1-20 attributes, or our own 25 abilities
by name. A column it does not recognise is skipped; --map (or FL26 Mod Studio's import dialog)
names one by hand, and "column=" drops one.

What the table does not give is filled in from the game's own players (the tables in --base):
for every position, each ability is fitted to the player's overall rating, so a CF of 72 gets
the finishing, speed and heading a CF of 72 has in the game; the positions he can also play,
his playing style, weak foot and so on are the most common ones for his position; height and
weight the middle of his position's. Nothing of the game's players is kept or written out,
only those averages.

Ratings: a column whose values all lie in 1..20 is taken as Football Manager's scale and
stretched to 40..99 (20 -> 99, 10 -> 68); others are read as 1..99 and held to 40..99, the
range an ability has in the game. Several columns feeding one ability are averaged.

A table with no rating at all (a squad list off a website) makes every player --level (65).

--out writes the squad in the columns of playeredit.py / Mod Studio's Import CSV (player =
place in the squad, 0 up). Without it the result is printed.
"""
import collections, csv, datetime, io, os, re, sys, unicodedata

import playeredit as E

ABILITIES = [n for n, _b in E.ABILITIES]
GK_ABILITIES = ["GK Awareness", "GK Catching", "GK Clearing", "GK Reflexes", "GK Reach"]
LO, HI = 40, 99
NAME_MAX = E.P_NAME_LEN - 1          # bytes, the name slot less its terminating zero


def norm(s):
    """lower case, no accents, letters and digits only: "Heading Accuracy" -> "headingaccuracy" """
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---- what a column can be ----

# the player's own facts
BASIC = {
    "name": ["name", "player", "playername", "fullname", "longname", "knownas", "shortname",
             "commonname", "igrac", "imeiprezime", "prezimeiime"],
    "first": ["firstname", "forename", "givenname", "ime"],
    "last": ["lastname", "surname", "familyname", "prezime"],
    "position": ["position", "positions", "pos", "playerpositions", "bestposition", "preferredpositions",
                 "mainposition", "role", "pozicija", "pozicije"],
    "age": ["age", "godine", "starost"],
    "born": ["dateofbirth", "birthdate", "born", "dob", "birthday", "dateofbirthage", "datumrodjenja", "rodjen"],
    "nationality": ["nationality", "nation", "country", "nat", "citizenship", "nationalityname",
                    "nationalteam", "drzavljanstvo", "drzava", "nacionalnost"],
    "height": ["height", "heightcm", "visina"],
    "weight": ["weight", "weightkg", "tezina"],
    "foot": ["foot", "preferredfoot", "strongerfoot", "strongfoot", "noga", "jacanoga"],
    "shirt": ["shirt", "number", "no", "nr", "kitnumber", "jersey", "shirtnumber", "squadnumber",
              "clubjerseynumber", "broj", "brojdresa"],
    "overall": ["overall", "ovr", "rating", "overallrating", "ocjena", "ukupno"],
}

# a rating of the source -> the abilities of ours it speaks for (EA FC, FM, plain English)
RATINGS = {
    # EA FC's card values
    "pace": (["pace", "pac"], ["Speed", "Acceleration"]),
    "shooting": (["shooting", "sho"], ["Finishing", "Kicking Power"]),
    "passing": (["passing", "pas"], ["Low Pass", "Lofted Pass"]),
    "dribbling": (["dribbling", "dri", "skilldribbling", "dribblingskill"], ["Dribbling", "Tight Possession"]),
    "defending": (["defending", "def"], ["Defensive Awareness", "Ball Winning"]),
    "physical": (["physical", "physic", "phy", "physicality"], ["Physical Contact", "Stamina", "Jump"]),
    # detailed ones, EA FC and Football Manager
    "finishing": (["finishing", "attackingfinishing", "fin"], ["Finishing"]),
    "crossing": (["crossing", "attackingcrossing", "cro"], ["Lofted Pass", "Curl"]),
    "heading": (["headingaccuracy", "attackingheadingaccuracy", "heading", "hea"], ["Heading"]),
    "shortpass": (["shortpassing", "attackingshortpassing"], ["Low Pass"]),
    "longpass": (["longpassing", "skilllongpassing"], ["Lofted Pass"]),
    "vision": (["vision", "mentalityvision", "vis"], ["Low Pass", "Lofted Pass"]),
    "control": (["ballcontrol", "skillballcontrol", "firsttouch", "technique", "fir", "tec"], ["Ball Control"]),
    "agility": (["agility", "movementagility", "agi"], ["Tight Possession"]),
    "balance": (["balance", "movementbalance", "bal"], ["Balance"]),
    "speed": (["sprintspeed", "movementsprintspeed"], ["Speed"]),
    "acceleration": (["acceleration", "movementacceleration", "acc"], ["Acceleration"]),
    "attpos": (["attackingpositioning", "mentalitypositioning", "offtheball", "otb"], ["Offensive Awareness"]),
    "shotpower": (["shotpower", "powershotpower", "longshots", "powerlongshots", "lon"], ["Kicking Power"]),
    "freekick": (["freekickaccuracy", "fkaccuracy", "skillfkaccuracy", "freekicktaking", "freekicks",
                  "fre", "corners", "cor", "penalties", "mentalitypenalties", "penaltytaking", "pen"], ["Place Kicking"]),
    "curve": (["curve", "skillcurve"], ["Curl"]),
    "jumping": (["jumping", "powerjumping", "jumpingreach", "jum"], ["Jump"]),
    "strength": (["strength", "powerstrength", "str"], ["Physical Contact"]),
    "stamina": (["stamina", "powerstamina", "sta", "naturalfitness"], ["Stamina"]),
    "aggression": (["aggression", "mentalityaggression", "agg"], ["Aggression"]),
    "defaware": (["defensiveawareness", "defendingmarkingawareness", "markingawareness", "marking",
                  "mar", "interceptions", "mentalityinterceptions"], ["Defensive Awareness"]),
    "tackle": (["standingtackle", "defendingstandingtackle", "slidingtackle", "defendingslidingtackle",
                "tackling", "tck"], ["Ball Winning"]),
    # goalkeepers
    "gkdiving": (["gkdiving", "goalkeepingdiving", "diving", "div"], ["GK Reach"]),
    "gkhandling": (["gkhandling", "goalkeepinghandling", "handling", "han"], ["GK Catching"]),
    "gkkicking": (["gkkicking", "goalkeepingkicking", "kicking", "kic"], ["GK Clearing"]),
    "gkreflexes": (["gkreflexes", "goalkeepingreflexes", "reflexes", "ref"], ["GK Reflexes"]),
    "gkpos": (["gkpositioning", "goalkeepingpositioning", "commandofarea", "cmd"], ["GK Awareness"]),
    "gkreach": (["aerialreach", "aerialability", "aer"], ["GK Reach"]),
    "oneonone": (["oneonones", "1v1"], ["GK Reflexes"]),
}
# "positioning" is attacking in EA FC and defensive in Football Manager: decided by the scale
POSITIONING = ["positioning"]

TARGETS = (["name", "first", "last", "position", "posgrid", "age", "born", "nationality", "height", "weight",
            "foot", "shirt", "overall"] + sorted(RATINGS) + ["positioning"] + ABILITIES)
LABELS = {"name": "Name", "first": "First name", "last": "Last name", "position": "Position(s)",
          "posgrid": "Position grade (0/1/2)",
          "age": "Age", "born": "Birth date", "nationality": "Nationality", "height": "Height",
          "weight": "Weight", "foot": "Foot", "shirt": "Shirt number", "overall": "Overall rating",
          "positioning": "Positioning (EA: attacking, FM: defensive)"}


SHOWN = {"shortpass": "Short passing", "longpass": "Long passing", "control": "Ball control / first touch",
         "speed": "Sprint speed", "attpos": "Attacking positioning / off the ball", "shotpower": "Shot power / long shots",
         "freekick": "Free kicks / corners / penalties", "defaware": "Marking / interceptions",
         "tackle": "Tackling", "gkdiving": "GK diving", "gkhandling": "GK handling", "gkkicking": "GK kicking",
         "gkreflexes": "GK reflexes", "gkpos": "GK positioning / command of area", "gkreach": "Aerial reach",
         "oneonone": "One on ones"}


def label(t):
    """what a target is called in a list a person picks from"""
    if t in LABELS:
        return LABELS[t]
    if t in RATINGS:
        return "%s -> %s" % (SHOWN.get(t, t.title()), ", ".join(RATINGS[t][1]))
    return t


_ALIAS = {}
for _t, _names in BASIC.items():
    for _n in _names:
        _ALIAS.setdefault(_n, _t)
for _t, (_names, _abs) in RATINGS.items():
    for _n in _names:
        _ALIAS.setdefault(_n, _t)
for _n in POSITIONING:
    _ALIAS.setdefault(_n, "positioning")
for _a in ABILITIES:
    _ALIAS[norm(_a)] = _a              # our own names win: a table of ours reads back as it is
_ALIAS["position"] = "position"
_ALIAS["registeredposition"] = "position"
_ALIAS["heightcm"] = "height"
_ALIAS["weightkg"] = "weight"
_ALIAS["strongerfoot"] = "foot"


GRID = {p.lower(): p for p in E.POSITIONS}


def guess(head, rows=()):
    """{column index: target} for the columns recognised by name; a name column made only of
    numbers (our own CSV's "player" id) is left out"""
    out, taken = {}, set()
    vals = lambda i: [(r[i] if i < len(r) else "").strip() for r in rows]
    # a PES editor's table: 13 columns GK..CF graded 0/1/2 and "POS" as the game's code 0..12
    grid = bool(rows) and sum(1 for i, h in enumerate(head)
                              if norm(h) in GRID and set(vals(i)) <= {"", "0", "1", "2"}) >= 10
    for i, h in enumerate(head):
        t = "shirt" if h.strip() == "#" else _ALIAS.get(norm(h))
        numeric = bool(rows) and all(re.fullmatch(r"\s*\d*\s*", r[i] if i < len(r) else "") for r in rows)
        if grid and norm(h) in GRID:
            t = "posgrid"
        elif t == "position" and numeric and norm(h) == "pos":
            codes = [int(v) for v in vals(i) if v]
            if not (codes and max(codes) <= 12 and (grid or min(codes) == 0)):
                t = "positioning"               # Football Manager's "Pos" attribute, 1-20
        if t is None or (t in taken and t not in RATINGS and t not in ABILITIES
                         and t not in ("positioning", "posgrid")):
            continue
        if t == "name" and numeric:
            continue
        out[i] = t
        taken.add(t)
    return out


# ---- reading the table ----

def read_table(path):
    """(header, rows) of a CSV in whatever separator and encoding it has"""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1250", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    first = text.splitlines()[0] if text.strip() else ""
    sep = max([",", ";", "\t", "|"], key=first.count)
    lines = [l for l in csv.reader(io.StringIO(text), delimiter=sep)]
    lines = [[c.strip() for c in l] for l in lines if any(c.strip() for c in l)]
    if not lines:
        return [], []
    return lines[0], lines[1:]


# ---- cell values ----

POS_WORDS = {
    "gk": "GK", "g": "GK", "goalkeeper": "GK", "keeper": "GK", "vratar": "GK", "golman": "GK",
    "cb": "CB", "d": "CB", "dc": "CB", "centreback": "CB", "centerback": "CB", "defender": "CB",
    "branic": "CB", "stoper": "CB", "centralnibranic": "CB", "obrana": "CB",
    "lb": "LB", "lwb": "LB", "dl": "LB", "wbl": "LB", "leftback": "LB", "leftwingback": "LB", "lijevibek": "LB",
    "rb": "RB", "rwb": "RB", "dr": "RB", "wbr": "RB", "rightback": "RB", "rightwingback": "RB", "desnibek": "RB",
    "dm": "DMF", "dmf": "DMF", "cdm": "DMF", "defensivemidfield": "DMF", "defensivemidfielder": "DMF",
    "zadnjivezni": "DMF",
    "cm": "CMF", "cmf": "CMF", "mc": "CMF", "m": "CMF", "centralmidfield": "CMF", "centralmidfielder": "CMF",
    "midfielder": "CMF", "midfield": "CMF", "vezni": "CMF", "srednjivezni": "CMF",
    "lm": "LMF", "lmf": "LMF", "ml": "LMF", "leftmidfield": "LMF", "leftmidfielder": "LMF",
    "rm": "RMF", "rmf": "RMF", "mr": "RMF", "rightmidfield": "RMF", "rightmidfielder": "RMF",
    "am": "AMF", "amf": "AMF", "cam": "AMF", "amc": "AMF", "attackingmidfield": "AMF",
    "attackingmidfielder": "AMF", "ofenzivnivezni": "AMF", "playmaker": "AMF",
    "lw": "LWF", "lwf": "LWF", "lf": "LWF", "aml": "LWF", "leftwinger": "LWF", "leftwing": "LWF",
    "lijevokrilo": "LWF",
    "rw": "RWF", "rwf": "RWF", "rf": "RWF", "amr": "RWF", "rightwinger": "RWF", "rightwing": "RWF",
    "desnokrilo": "RWF",
    "ss": "SS", "secondstriker": "SS", "shadowstriker": "SS",
    "cf": "CF", "st": "CF", "stc": "CF", "fc": "CF", "striker": "CF", "centreforward": "CF",
    "centerforward": "CF", "forward": "CF", "attacker": "CF", "napadac": "CF", "spica": "CF",
}
# Football Manager: "D (RLC)", "AM (L)", "ST (C)" -- a role and the sides it is played on
FM_ROLE = {"GK": {"": "GK", "C": "GK"}, "D": {"C": "CB", "L": "LB", "R": "RB"},
           "WB": {"L": "LB", "R": "RB"}, "DM": {"": "DMF", "C": "DMF"},
           "M": {"C": "CMF", "L": "LMF", "R": "RMF"}, "AM": {"C": "AMF", "L": "LWF", "R": "RWF"},
           "ST": {"": "CF", "C": "CF"}, "F": {"C": "CF"}}


def positions(cell):
    """[our positions] of a position cell, the first the main one: "ST, LW", "D (RC), DM",
    "Centre-Forward", "AM (RL)" all read"""
    if re.fullmatch(r"\s*\d{1,2}\s*", cell) and int(cell) < len(E.POSITIONS):
        return [E.POSITIONS[int(cell)]]         # a PES editor's code: 0 GK, 1 CB ... 12 CF
    out = []
    for m in re.finditer(r"\b(GK|D|WB|DM|M|AM|ST|F)\s*\(([RLC]+)\)", cell.upper()):
        for side in m.group(2):
            p = FM_ROLE[m.group(1)].get(side)
            if p and p not in out:
                out.append(p)
    rest = re.sub(r"\b(GK|D|WB|DM|M|AM|ST|F)\s*\([RLC]+\)", " ", cell, flags=re.I)
    for part in re.split(r"[,/;|+]|\s{2,}|\s-\s", rest):
        k = norm(part)
        p = POS_WORDS.get(k) or (k.upper() if k.upper() in E.POSITIONS else None)
        if p is None and k:
            # "Defender - Centre-Back": the most specific word that is a position
            words = [POS_WORDS.get(norm(w)) for w in re.split(r"[\s\-]+", part)]
            joined = POS_WORDS.get(norm(part.split("-")[-1])) if "-" in part else None
            p = joined or next((w for w in reversed(words) if w), None)
        if p and p not in out:
            out.append(p)
    return out


def number(cell):
    m = re.search(r"-?\d+(?:[.,]\d+)?", cell or "")
    return float(m.group().replace(",", ".")) if m else None


def height_cm(cell):
    c = (cell or "").lower()
    m = re.search(r"(\d)\s*'\s*(\d{1,2})", c)                  # 6'1"
    if m:
        return round(int(m.group(1)) * 30.48 + int(m.group(2)) * 2.54)
    v = number(c)
    if v is None:
        return None
    if v < 3:                                                   # 1,85 m
        v *= 100
    return round(v)


def weight_kg(cell):
    v = number(cell)
    if v is None:
        return None
    return round(v * 0.4536) if "lb" in (cell or "").lower() else round(v)


def foot(cell):
    k = norm(cell)
    if k in ("0", "1"):                     # a PES editor's table: 0 right, 1 left
        return "Left" if k == "1" else "Right"
    if k in ("left", "l", "lijeva", "lijevi", "links", "gauche", "izquierdo"):
        return "Left"
    if k in ("right", "r", "desna", "desni", "rechts", "droite", "derecho", "both", "obje"):
        return "Right"
    return None


def age_from(cell, today=None):
    """the age on a birth date cell: 2001-03-14, 14.03.2001, 14/03/2001, Mar 14, 2001, or a year"""
    today = today or datetime.date.today()
    c = (cell or "").strip()
    m = re.search(r"\((\d{1,2})\)\s*$", c)                    # Transfermarkt: "Mar 14, 2001 (25)"
    if m:
        return int(m.group(1))
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%Y.", "%d/%m/%Y", "%m/%d/%Y", "%b %d, %Y", "%d %b %Y",
                "%B %d, %Y", "%d %B %Y", "%Y/%m/%d"):
        try:
            d = datetime.datetime.strptime(c, fmt).date()
            return today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        except ValueError:
            pass
    m = re.fullmatch(r"(19|20)\d\d", c)
    return today.year - int(c) if m else None


class Countries:
    """a nationality cell -> Country.bin id, by the names of the game's own Country table"""
    EXTRA = {"england": "England", "usa": "USA", "unitedstatesofamerica": "USA",
             "korearepublic": "Republic of Korea", "southkorea": "Republic of Korea", "ivorycoast": "Cote d'Ivoire",
             "czechia": "Czech Republic", "turkiye": "Turkey", "iriran": "Iran", "chinapr": "China",
             "northmacedonia": "North Macedonia", "fyrmacedonia": "North Macedonia", "republicofireland": "Ireland",
             "drcongo": "Congo DR", "bosniaherzegovina": "Bosnia and Herzegovina", "bih": "Bosnia and Herzegovina",
             "bosna": "Bosnia and Herzegovina", "bosnaihercegovina": "Bosnia and Herzegovina",
             "hrvatska": "Croatia", "srbija": "Serbia", "slovenija": "Slovenia", "crnagora": "Montenegro",
             "njemacka": "Germany", "austrija": "Austria", "madjarska": "Hungary", "italija": "Italy",
             "francuska": "France", "spanjolska": "Spain", "engleska": "England", "albanija": "Albania",
             "makedonija": "North Macedonia", "kosovo": "Kosovo", "brazil": "Brazil", "argentina": "Argentina",
             "nizozemska": "Netherlands", "holland": "Netherlands", "belgija": "Belgium", "svicarska": "Switzerland",
             "polska": "Poland", "poljska": "Poland", "ceska": "Czech Republic", "slovacka": "Slovakia",
             "rumunjska": "Romania", "bugarska": "Bulgaria", "grcka": "Greece", "portugal": "Portugal"}
    # three-letter FIFA codes, as Football Manager and many sites write them
    CODES = {"alb": "Albania", "alg": "Algeria", "and": "Andorra", "arg": "Argentina", "arm": "Armenia",
             "aus": "Australia", "aut": "Austria", "aze": "Azerbaijan", "bel": "Belgium", "bih": "Bosnia and Herzegovina",
             "blr": "Belarus", "bol": "Bolivia", "bra": "Brazil", "bul": "Bulgaria", "can": "Canada",
             "chi": "Chile", "chn": "China", "civ": "Cote d'Ivoire", "cmr": "Cameroon", "cod": "Congo DR",
             "col": "Colombia", "crc": "Costa Rica", "cro": "Croatia", "cyp": "Cyprus", "cze": "Czech Republic",
             "den": "Denmark", "ecu": "Ecuador", "egy": "Egypt", "eng": "England", "esp": "Spain", "est": "Estonia",
             "fin": "Finland", "fra": "France", "gab": "Gabon", "geo": "Georgia", "ger": "Germany", "gha": "Ghana",
             "gre": "Greece", "gui": "Guinea", "hon": "Honduras", "hun": "Hungary", "irl": "Ireland", "irn": "Iran",
             "isl": "Iceland", "isr": "Israel", "ita": "Italy", "jam": "Jamaica", "jpn": "Japan",
             "kor": "Republic of Korea", "kos": "Kosovo", "ksa": "Saudi Arabia", "ltu": "Lithuania",
             "lux": "Luxembourg", "lva": "Latvia", "mar": "Morocco", "mex": "Mexico", "mkd": "North Macedonia",
             "mli": "Mali", "mne": "Montenegro", "mlt": "Malta", "ned": "Netherlands", "nga": "Nigeria",
             "nir": "Northern Ireland", "nor": "Norway", "nzl": "New Zealand", "pan": "Panama", "par": "Paraguay",
             "per": "Peru", "pol": "Poland", "por": "Portugal", "qat": "Qatar", "rou": "Romania", "rus": "Russia",
             "sco": "Scotland", "sen": "Senegal", "srb": "Serbia", "sui": "Switzerland", "svk": "Slovakia",
             "svn": "Slovenia", "swe": "Sweden", "tun": "Tunisia", "tur": "Turkey", "ukr": "Ukraine",
             "uru": "Uruguay", "usa": "USA", "uzb": "Uzbekistan", "ven": "Venezuela", "wal": "Wales",
             "zam": "Zambia", "rsa": "South Africa"}

    def __init__(self, pairs):
        """pairs: [(name, id)] as leaguebuilder.country_ids gives them"""
        self.by = {}
        for nm, fid in pairs:
            base = re.sub(r"\s*\(\d+\)$", "", nm)
            k = norm(base.replace("&", "and"))
            self.by.setdefault(k, fid)
            self.by.setdefault(k.replace("and", ""), fid)

    def find(self, cell):
        c = (cell or "").strip()
        if c.isdigit():
            return int(c)
        for part in [c] + re.split(r"[,/;|]|\s{2,}", c):
            k = norm(part.replace("&", "and"))
            if not k:
                continue
            alias = self.EXTRA.get(k) or (self.CODES.get(k) if len(k) == 3 else "") or ""
            for key in (k, k.replace("and", ""), norm(alias), norm(alias).replace("and", "")):
                if key and key in self.by:
                    return self.by[key]
        return None


# ---- what the game's players say about a position ----

class Model:
    """per registered position: every ability as a + b * overall (least squares over the game's
    players of that position), and the usual values of the other fields"""
    OTHER = ["Weak Foot Usage", "Weak Foot Accuracy", "Form", "Injury Resistance", "Playing Style"]

    def __init__(self, players):
        """players: a Player.bin as bytes"""
        import lbplayers
        need = ["Registered Position", "Height (cm)", "Weight (kg)"] + ABILITIES + E.POSITIONS + self.OTHER
        by = collections.defaultdict(list)
        for o in range(0, len(players) - E.P_REC + 1, E.P_REC):
            rec = players[o:o + E.P_REC]
            d = {k: E.getf(rec, k) for k in need}
            if d["Registered Position"] >= len(E.POSITIONS):
                continue
            pos = E.POSITIONS[d["Registered Position"]]
            row = {k: str(v) for k, v in d.items()}
            row["Registered Position"] = pos
            d["ovr"] = lbplayers.overall(row)
            by[pos].append(d)
        self.fit, self.usual, self.also, self.body = {}, {}, {}, {}
        for pos, ds in by.items():
            xs = [d["ovr"] for d in ds]
            mx = sum(xs) / len(xs)
            sxx = sum((x - mx) ** 2 for x in xs) or 1
            f = {}
            for a in ABILITIES:
                ys = [d[a] for d in ds]
                my = sum(ys) / len(ys)
                b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
                f[a] = (my - b * mx, b)
            self.fit[pos] = f
            self.usual[pos] = {k: collections.Counter(d[k] for d in ds).most_common(1)[0][0] for k in self.OTHER}
            self.also[pos] = [p for p in E.POSITIONS if p != pos
                              and sum(1 for d in ds if d[p] >= 1) * 2 >= len(ds)]
            hs = sorted(d["Height (cm)"] for d in ds)
            bmi = sorted(d["Weight (kg)"] / (d["Height (cm)"] / 100.0) ** 2 for d in ds)
            self.body[pos] = (hs[len(hs) // 2], bmi[len(bmi) // 2])

    @classmethod
    def from_base(cls, base):
        import pesdb
        return cls(pesdb.wesys_unpack(open(os.path.join(base, "Player.bin"), "rb").read()))

    def predict(self, pos, ovr):
        return {a: clamp(a0 + b * ovr) for a, (a0, b) in self.fit[pos].items()}

    def overall_of(self, pos, have):
        """the overall a player with these abilities most likely has (median over the abilities
        that follow the overall at all)"""
        est = sorted((v - a0) / b for a, v in have.items() for a0, b in [self.fit[pos][a]] if b > 0.3)
        return est[len(est) // 2] if est else None


def clamp(v):
    return int(max(LO, min(HI, round(v))))


# ---- the whole conversion ----

def scale_of(values):
    """"fm" when every number is in 1..20 (Football Manager), else "99" """
    nums = [v for v in values if v is not None]
    return "fm" if nums and max(nums) <= 20 and min(nums) >= 1 else "99"


def to_ours(v, scale):
    if v is None:
        return None
    return clamp(LO + (v - 1) * (HI - LO) / 19.0) if scale == "fm" else clamp(v)


def convert(head, rows, mapping, model, countries, nation=None, today=None, level=65):
    """[{field: text}] of the players of the table, and [warnings]. mapping: {column: target}."""
    warn = []
    cols = collections.defaultdict(list)
    for i, t in sorted(mapping.items()):
        if t:
            cols[t].append(i)
    cell = lambda r, i: r[i] if i < len(r) else ""
    scales = {i: scale_of([number(cell(r, i)) for r in rows])
              for t, idx in cols.items() if t in RATINGS or t in ABILITIES or t in ("overall", "positioning")
              for i in idx}
    out, unrated = [], []
    for n, r in enumerate(rows, 2):
        p = {}
        if "name" in cols:
            nm = " ".join(cell(r, i) for i in cols["name"]).strip()
        else:
            nm = " ".join(x for x in [" ".join(cell(r, i) for i in cols.get("first", [])),
                                       " ".join(cell(r, i) for i in cols.get("last", []))] if x).strip()
        nm = re.sub(r"\s+", " ", nm)
        if not nm:
            warn.append("line %d: no name, skipped" % n)
            continue
        b = nm.encode("utf-8")
        if len(b) > NAME_MAX:
            nm = b[:NAME_MAX].decode("utf-8", "ignore")
            warn.append("line %d: name cut to %d bytes: %s" % (n, NAME_MAX, nm))
        p["name"] = nm
        pos = []
        for i in cols.get("position", []):
            pos += [x for x in positions(cell(r, i)) if x not in pos]
        graded = {GRID[norm(head[i])]: cell(r, i).strip() for i in cols.get("posgrid", [])
                  if i < len(head) and norm(head[i]) in GRID}
        if not pos:
            pos = [q for q in E.POSITIONS if graded.get(q) == "2"]
        if not pos:
            pos = ["CMF"]
            warn.append("line %d (%s): no position read, made a CMF" % (n, nm))
        main = pos[0]
        p["Registered Position"] = main
        if graded:                              # the table grades every position: take it as it is
            for q in E.POSITIONS:
                g = graded.get(q, "0")
                p[q] = "2" if q == main or g == "2" else "1" if g == "1" or q in pos[1:] else "0"
        else:
            also = set(pos[1:]) | set(model.also.get(main, []))
            for q in E.POSITIONS:
                p[q] = "2" if q == main else "1" if q in also else "0"

        # abilities: what the table says, then the rest from the position's fit to the overall
        feed = collections.defaultdict(list)
        for t, idx in cols.items():
            if t in RATINGS or t == "positioning" or t in ABILITIES:
                for i in idx:
                    v = to_ours(number(cell(r, i)), scales[i])
                    if v is None:
                        continue
                    if t in ABILITIES:
                        targets = [t]
                    elif t == "positioning":
                        targets = ["Defensive Awareness" if scales[i] == "fm" else "Offensive Awareness"]
                    else:
                        targets = RATINGS[t][1]
                    for a in targets:
                        feed[a].append((v, t in ABILITIES))
        have = {}
        for a, vs in feed.items():
            own = [v for v, mine in vs if mine]
            have[a] = own[0] if own else round(sum(v for v, _m in vs) / len(vs))
        ovr = None
        for i in cols.get("overall", []):
            ovr = to_ours(number(cell(r, i)), scales[i])
        if ovr is None:
            ovr = model.overall_of(main, {a: v for a, v in have.items()
                                          if (main == "GK") == (a in GK_ABILITIES)})
        if ovr is None:
            ovr = level
            unrated.append(nm)
        ab = model.predict(main, ovr)
        ab.update(have)
        for a in ABILITIES:
            p[a] = str(ab[a])

        for i in cols.get("age", []):
            v = number(cell(r, i))
            if v is not None:
                p["Age"] = str(int(max(15, min(45, v))))
        if "Age" not in p:
            for i in cols.get("born", []):
                v = age_from(cell(r, i), today)
                if v is not None:
                    p["Age"] = str(max(15, min(45, v)))
        if "Age" not in p:
            p["Age"] = "25"
        h = next((height_cm(cell(r, i)) for i in cols.get("height", []) if height_cm(cell(r, i))), None)
        w = next((weight_kg(cell(r, i)) for i in cols.get("weight", []) if weight_kg(cell(r, i))), None)
        mh, bmi = model.body.get(main, (180, 23.0))
        h = int(max(150, min(210, h or mh)))
        p["Height (cm)"] = str(h)
        p["Weight (kg)"] = str(int(max(50, min(110, w or round(bmi * (h / 100.0) ** 2)))))
        f = next((foot(cell(r, i)) for i in cols.get("foot", []) if foot(cell(r, i))), None)
        p["Stronger Foot"] = f or "Right"
        nat = None
        for i in cols.get("nationality", []):
            nat = countries.find(cell(r, i)) if countries else None
            if nat is None and cell(r, i):
                warn.append("line %d (%s): nationality %r not found, used the club's country" % (n, nm, cell(r, i)))
        if nat is None:
            nat = nation
        if nat is not None:
            p["Nationality"] = str(nat)
        for k, v in model.usual.get(main, {}).items():
            p[k] = str(v)
        for i in cols.get("shirt", []):
            v = number(cell(r, i))
            if v is not None and 0 <= v <= 99:
                p["shirt"] = str(int(v))
        for s, _b in E.SKILLS:
            p[s] = "0"
        out.append(p)
    if unrated:
        warn.append("%d player(s) with no rating in the table made %d: %s"
                    % (len(unrated), level, ", ".join(unrated[:6]) + (" ..." if len(unrated) > 6 else "")))
    return out, warn


# ---- command line ----

def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 1
    get = lambda k: a[a.index(k) + 1] if k in a else None
    path = a[0]
    import leaguebuilder as B
    base = B.base_dir(get("--base"))
    head, rows = read_table(path)
    mapping = guess(head, rows)
    for i, x in enumerate(a):
        if x == "--map" and i + 1 < len(a):
            col, _e, t = a[i + 1].partition("=")
            if col not in head:
                raise SystemExit("--map: no column %r (the columns: %s)" % (col, ", ".join(head)))
            if t and t not in TARGETS:
                raise SystemExit("--map: %r is not a target; they are: %s" % (t, ", ".join(TARGETS)))
            mapping[head.index(col)] = t or None
    for i, h in enumerate(head):
        print("  %-28s -> %s" % (h, label(mapping[i]) if mapping.get(i) else "(skipped)"))
    nation = int(get("--nation")) if get("--nation") else None
    level = int(get("--level") or 65)
    players, warn = convert(head, rows, mapping, Model.from_base(base), Countries(B.country_ids(base)), nation,
                            level=level)
    for w in warn:
        print("  " + w)
    cols = ["player", "name", "shirt"] + list(E.FIELDS)
    if get("--out"):
        with open(get("--out"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for k, p in enumerate(players):
                w.writerow([str(k) if c == "player" else p.get(c, "") for c in cols])
        print("%d players -> %s" % (len(players), get("--out")))
    else:
        for p in players:
            print("  %-26s %-4s age %-3s %s  %s" % (p["name"], p["Registered Position"], p["Age"],
                                                   p.get("Nationality", "-"),
                                                   " ".join(p[x] for x in ("Speed", "Finishing", "Low Pass",
                                                                           "Defensive Awareness", "GK Reflexes"))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
