"""Match crest pictures to clubs by name -- a pure function, no UI and no file writing.

    match(files, clubs) -> [(file, club_id or None, score 0..1)]

files: picture file names ("CD Universidad Cesar Vallejo.png", "alianza_lima_r_l.png").
clubs: [(club_name, club_id), ...].

The idea comes from Xxspedd's escudos.py (FL Mod Studio Discord).

How it scores: both sides are reduced to words (accents folded, lower case, letters and digits
only, filler words dropped; a file also loses the crest pack's size suffix _r, _r_l, _r_ll).
The score is the Jaccard overlap of the two word sets, or 0.7 when one joined-up name contains
the other with at least 4 letters in the shorter one, from the start of a word to the end of one
-- a file called "Real Madrid" is worth 0.7 against "Real Madrid Castilla" and 1.0 against "Real
Madrid", but "Mali" is nothing against "Bruk-Bet Termalica".

The assignment is greedy over the best scores first: a file and a club are each used at most
once, nothing under 0.4 is accepted, everything else comes back as (file, None, 0.0).
"""
import re
import unicodedata

MIN_SCORE = 0.4
CONTAINS_SCORE = 0.7
SHORTEST_CONTAINS = 4                     # letters needed before "one name contains the other" counts

FILLER = frozenset((
    "fc", "cf", "cd", "csd", "ca", "ac", "sc", "sd", "ud", "ad", "afc", "club", "the",
    "de", "del", "la", "las", "el", "los", "atletico", "atletica", "deportivo", "deportiva",
    "futbol", "futebol", "balompie", "sport", "sports",
))
SIZES = ("_r_ll", "_r_l", "_r")           # the crest packs' size suffixes, longest first


def _fold(text):
    """no accents, lower case, words of letters and digits only"""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    return re.findall(r"[a-z0-9]+", t)


def words(text, is_file=False):
    """the words a name is matched by; a file name also loses the extension and its size tag"""
    t = text
    if is_file:
        stem, dot, ext = t.rpartition(".")
        if dot and 0 < len(ext) <= 5 and ext.isalnum():
            t = stem
        low = t.lower()
        for s in SIZES:
            if low.endswith(s):
                t = t[: -len(s)]
                break
    return [w for w in _fold(t) if w not in FILLER]


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


def score(file_words, club_words):
    """Jaccard word overlap, or CONTAINS_SCORE when one joined name contains the other"""
    if not file_words or not club_words:
        return 0.0
    a, b = set(file_words), set(club_words)
    j = len(a & b) / float(len(a | b))
    ja, jb = "".join(file_words), "".join(club_words)
    short, long_words = (ja, club_words) if len(ja) <= len(jb) else (jb, file_words)
    if len(short) >= SHORTEST_CONTAINS and _contains(long_words, short):
        return max(j, CONTAINS_SCORE)
    return j


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


def match(files, clubs):
    """-> [(file, club_id or None, score)] in the order the files came in"""
    fw = [words(f, is_file=True) for f in files]
    cw = [words(n) for n, _id in clubs]
    cand = []
    for i, a in enumerate(fw):
        for j, b in enumerate(cw):
            s = score(a, b)
            if s >= MIN_SCORE:
                cand.append((s, i, j))
    cand.sort(key=lambda t: (-t[0], t[1], t[2]))          # best first; ties by file, then club
    out = [(f, None, 0.0) for f in files]
    used_f, used_c = set(), set()
    for s, i, j in cand:
        if i in used_f or j in used_c:
            continue
        used_f.add(i)
        used_c.add(j)
        out[i] = (files[i], clubs[j][1], round(s, 3))
    return out
