"""Match crest pictures to clubs by name -- a pure function, no UI and no file writing.

    match(files, clubs) -> [(file, club_id or None, score 0..1)]

files: picture file names ("CD Universidad Cesar Vallejo.png", "alianza_lima_r_l.png").
clubs: [(club_name, club_id), ...].

The idea comes from Xxspedd's escudos.py (FL Mod Studio Discord).

How it scores: both sides are reduced to words (accents folded, lower case, letters and digits
only, filler words dropped; a file also loses the crest pack's size suffix _r, _r_l, _r_ll).
The score is the Jaccard overlap of the two word sets, or 0.7 when one joined-up name contains
the other with at least 4 letters in the shorter one -- a file called "Real Madrid" is worth
0.7 against "Real Madrid Castilla" and 1.0 against "Real Madrid".

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


def score(file_words, club_words):
    """Jaccard word overlap, or CONTAINS_SCORE when one joined name contains the other"""
    if not file_words or not club_words:
        return 0.0
    a, b = set(file_words), set(club_words)
    j = len(a & b) / float(len(a | b))
    ja, jb = "".join(file_words), "".join(club_words)
    short = ja if len(ja) <= len(jb) else jb
    long_ = jb if short is ja else ja
    if len(short) >= SHORTEST_CONTAINS and short in long_:
        return max(j, CONTAINS_SCORE)
    return j


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
