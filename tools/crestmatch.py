"""Match crest pictures to clubs by name -- a pure function, no UI and no file writing.

    match(files, clubs, where=None, countries=None) -> [(file, club_id or None, score 0..1)]

files: picture file names ("CD Universidad Cesar Vallejo.png", "alianza_lima_r_l.png").
clubs: [(club_name, club_id), ...] or [(club_name, club_id, country), ...].

The idea comes from Xxspedd's escudos.py (FL Mod Studio Discord).

How it scores: both sides are reduced to words (accents folded, lower case, letters and digits
only, filler words dropped; a file also loses the crest pack's size suffix _r, _r_l, _r_ll and
football-logos.cc's "_1500x1500.football-logos.cc"). The same name, run together or not, is 1.0;
otherwise the score is the Jaccard overlap of the two word sets, or 0.5 when one name contains
the other (its words, or its joined-up letters with at least 4 of them, from the start of a word
to the end of one). 0.5 is under TICK: "Real Madrid" against "Real Madrid Castilla" is shown as a
suggestion, never ticked, and "Mali" is nothing against "Bruk-Bet Termalica".

Countries (B139): a file is of the country its folder names (where) or its name starts with
("poland_cracovia_1500x1500.football-logos.cc.png"). A club of that country is taken before any
other, whatever their scores, and a club of another country is never worth a tick. One name inside
the other is worth a tick (0.65) only when the club is of the file's country and the only club of
it the file's name is inside or holds; two such clubs, or a country unknown, stay at 0.5.

The assignment is greedy over the best scores first: a file and a club are each used at most
once, nothing under 0.4 is accepted, everything else comes back as (file, None, 0.0).
"""
import re
import unicodedata

MIN_SCORE = 0.4
TICK = 0.6                                # this good or better: ticked in Import crests / Import kits
CONTAINS_SCORE = 0.5                      # one name inside the other: a suggestion, under TICK (B139)
HOME_CONTAINS = 0.65                      # ... the only such club of the file's own country: ticked
SHORTEST_CONTAINS = 4                     # letters needed before "one name contains the other" counts
FOLDER_DEPTH = 3                          # how many of a folder's last names may name its country

FILLER = frozenset((
    "fc", "cf", "cd", "csd", "ca", "ac", "sc", "sd", "ud", "ad", "afc", "club", "the",
    "de", "del", "la", "las", "el", "los", "atletico", "atletica", "deportivo", "deportiva",
    "futbol", "futebol", "balompie", "sport", "sports",
))
PHRASES = (("football", "club"), ("sporting", "club"), ("athletic", "club"))  # filler as two words only
SIZES = ("_r_ll", "_r_l", "_r")           # the crest packs' size suffixes, longest first
SITES = (".football-logos.cc",)           # a download site's tag at the end of the name


def _fold(text):
    """no accents, lower case, words of letters and digits only"""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    return re.findall(r"[a-z0-9]+", t)


def key(text):
    """a name as one run of letters and digits, to compare countries and folders by:
    "Côte D'ivoire" and "cote-divoire" are both cotedivoire"""
    return "".join(_fold(text))


def words(text, is_file=False):
    """the words a name is matched by; a file name also loses the extension, its size tag and
    a site's tag ("_1500x1500.football-logos.cc")"""
    t = text
    if is_file:
        stem, dot, ext = t.rpartition(".")
        if dot and 0 < len(ext) <= 5 and ext.isalnum():
            t = stem
        low = t.lower()
        for s in SITES:
            if low.endswith(s):
                t = t[: -len(s)]
                low = t.lower()
                break
        for s in SIZES:
            if low.endswith(s):
                t = t[: -len(s)]
                break
    t = re.sub(r"\s*\([A-Za-z]{2,3}\)\s*$", "", t)        # NewLife's country tag: "Dreams FC (GHA)"
    out, run = [], []
    for w in _fold(t) + [""]:
        if len(w) == 1 and w.isalpha():                     # "F.C." and "S.C." are fc and sc
            run.append(w)
            continue
        out += ["".join(run)] if len(run) > 1 else run
        run = []
        if w:
            out.append(w)
    out = [w for w in out if not (is_file and re.fullmatch(r"\d+x\d+", w))]
    for a, b in PHRASES:                                    # "Pyramids Football Club" is pyramids (B139)
        while any(out[i:i + 2] == [a, b] for i in range(len(out) - 1)):
            i = next(i for i in range(len(out) - 1) if out[i:i + 2] == [a, b])
            del out[i:i + 2]
    return [w for w in out if w not in FILLER]


def file_id(name):
    """the team id a file is named by, or None: "12345.png", "e_12345_r.png" (the crest packs'
    flag/e_<id>_r.png names)"""
    stem = name.rpartition(".")[0] or name
    low = stem.lower()
    for s in SIZES:
        if low.endswith(s):
            low = low[: -len(s)]
            break
    if low.startswith("e_"):
        low = low[2:]
    return int(low) if low.isdigit() else None


def file_country(name, countries):
    """(country, the rest of the name) when a file name starts with a country and "_", as
    football-logos.cc names them ("poland_cracovia_1500x1500..."); (None, name) otherwise.
    countries: {key(name): country}"""
    head, sep, rest = name.partition("_")
    c = countries.get(key(head)) if sep and countries else None
    return (c, rest) if c and words(rest, True) else (None, name)


def folder_country(path, *names):
    """the country a folder of crests is of: the first of its last FOLDER_DEPTH names, from the
    innermost out, found in names ({key(name): country}, the countries before the leagues) --
    "Africa/Algeria/ligue-1-mobilis" is Algeria; None when none is"""
    parts = [p for p in re.split(r"[\\/]+", path or "") if p][-FOLDER_DEPTH:]
    parts = [key(p[:-4] if p.lower().endswith(".zip") else p) for p in reversed(parts)]
    for by in names:
        for p in parts:
            if by.get(p):
                return by[p]
    return None


def score(file_words, club_words):
    """1.0 for the same name, CONTAINS_SCORE when one contains the other, else the Jaccard word
    overlap"""
    return _score(file_words, club_words)[0]


def _score(file_words, club_words):
    """(score, True when it is one name inside the other)"""
    if not file_words or not club_words:
        return 0.0, False
    ja, jb = "".join(file_words), "".join(club_words)
    if ja == jb:
        return 1.0, False                 # the same name, run together or not ("manchesterunited")
    a, b = set(file_words), set(club_words)
    j = len(a & b) / float(len(a | b))
    short, long_words = (ja, club_words) if len(ja) <= len(jb) else (jb, file_words)
    if len(short) >= SHORTEST_CONTAINS and (a < b or b < a or _contains(long_words, short)):
        # no tick on its own: "United Sport FC" took nine "X United" crests, Rangers
        # "rangers-kinshasa", LA Galaxy "ts-galaxy" (B139)
        return CONTAINS_SCORE, True
    return j, False


def _contains(long_words, short):
    """short is in the joined long name from the start of one of its words to the end of one: "mali"
    is not in "bruk bet termalica" and "port" not in "sport" (Import crests 18.10.)"""
    starts, ends, at = set(), set(), 0
    for w in long_words:
        starts.add(at)
        at += len(w)
        ends.add(at)
    long_ = "".join(long_words)
    i = long_.find(short)
    while i >= 0:
        if i in starts and i + len(short) in ends:
            return True
        i = long_.find(short, i + 1)
    return False


def match(files, clubs, where=None, countries=None):
    """-> [(file, club_id or None, score)] in the order the files came in. where: the country of
    all the files (folder_country), countries: {key(name): country} for file_country"""
    fc, fw = [], []
    for f in files:
        c, rest = file_country(f, countries)
        fc.append(key(c or where or ""))
        fw.append(words(rest, is_file=True))
    cw = [words(c[0]) for c in clubs]
    cc = [key(c[2] or "") if len(c) > 2 else "" for c in clubs]
    cand = []
    for i, a in enumerate(fw):
        inside = []                       # the clubs of the file's own country one name is inside
        for j, b in enumerate(cw):
            s, part = _score(a, b)
            if s >= MIN_SCORE:
                # 2 the file's own country, 1 a country unknown on either side, 0 another (B139)
                home = 1 if not fc[i] or not cc[j] else 2 if fc[i] == cc[j] else 0
                cand.append((home, s, i, j))
                if home == 2 and part:
                    inside.append(len(cand) - 1)
        if len(inside) == 1:              # the only one of its country: "mostaganem" is ES Mostaganem
            home, s, i, j = cand[inside[0]]
            cand[inside[0]] = (home, HOME_CONTAINS, i, j)
    cand.sort(key=lambda t: (-t[0], -t[1], t[2], t[3]))   # own country, best first; ties by file, club
    out = [(f, None, 0.0) for f in files]
    used_f, used_c = set(), set()
    for home, s, i, j in cand:
        if i in used_f or j in used_c:
            continue
        used_f.add(i)
        used_c.add(j)
        out[i] = (files[i], clubs[j][1], round(s if home else min(s, CONTAINS_SCORE), 3))
    return out
