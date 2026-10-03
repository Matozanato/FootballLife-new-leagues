r"""the squads of a recipe: read them, and write the recipe's player changes into a world.

A recipe keeps its player changes under "players", one entry per club:

    "players": {
      "72318":          {"edits": {"180590": {"name": "Ivan Example", "Speed": "88"}},
                         "add": [{"like": "180590", "name": "New Boy", "Registered Position": "CF"}],
                         "remove": ["180611"]},
      "Liga Example/3": {"edits": {"0": {"name": "Marko Primjer", "Registered Position": "GK"}}}
    }

A club of the game is keyed by its team id and its players by player id.  A new club of the
recipe has no id until the world is built, so it is keyed "<league name>/<k>" (k from 0, the
club's place in the league) and its players by their place in the squad (0 to SQUAD-1): every
new club starts with the same squad, a copy of the first shipped club with SQUAD players
(mkplayers.py), so the place says which player it is.

Every value is the text a cell of playeredit.py's CSV takes ("CF", "Right", "85"), checked with
playeredit.parse when the world is built; "name", "shirt" and "order" are the name (all four
name slots), the shirt number and the squad order (the first eleven by order start); "face" is
a face folder, moved to the player's id when the world is built (lbfaces.py); "portrait" is a
picture, the player's portrait ("mini face") without a face of his own (player_portraits).

A club's "join" lists players who come to it and keep their record:

    "players": {
      "3":     {"join": ["180590", "Liga Example/3/7"]},     # Bosnia: two players called up
      "72318": {"join": ["41234"]}                            # a club signs player 41234
    }

A player is named by his id, or a new club's player by "<league name>/<k>/<place>". A national
team (Team.bin marks the 144 of them, T_NATIONAL) calls him up: he gets a second assignment and
stays at his club. A club signs him: his club assignment moves over (a transfer), or he gets one
if he had no club. Either way he goes to the end of the squad order with a shirt number nobody
there wears, and the squad he left closes its order up behind him.

"id" is the id a new player takes instead of the next free one -- a new club's player (by its
place) or one of "add" -- so a face, portrait or option file made for that id finds him. It has
to be above the game's own ids (Player.bin keeps them in id order) and free.

"coach_portrait" is a picture for the club's manager.  The game shows a manager's portrait from
common/render/symbol/coach/coach_<coach id>.png, 256 pixels square (1001 of them in dt15_x64.cpk,
940 of the 961 shipped coaches have one; the Master League's own managers are in coachML/<id>.png).
A club names its manager in Team.bin +0x00, so the picture goes under the id of the club's
manager in the world: the shipped one for a game club, the one mkcoaches added for a new club.
"""
import collections, csv, os

import pesdb
import playeredit as E

P_REC, P_ID = E.P_REC, E.P_ID
A_REC = E.A_REC
SQUAD = 30
MIN_SQUAD = 18        # a new club may lose players down to this: eleven and seven on the bench
FIELDS = list(E.FIELDS)
CLUB_MAX = 40         # the most players a shipped club has
NATIONAL_MAX = 26     # the most a shipped national team has
PID_MAX = 399999      # a player id Mod Studio hands out stays below this
T_NATIONAL = 0x53     # Team.bin: top bit set on the 144 national teams (leaguebuilder.T_NATIONAL)
T_COUNTRY = 0x46      # Team.bin: the country, 9 bits from bit 2 (144 of 144 national teams)
T_COACH = 0x00        # Team.bin: the id of the club's manager in Coach.bin (mkcoaches.T_COACH)
PORTRAIT = 256        # a manager's portrait is a PNG this many pixels square
PLAYER_PORTRAIT = 180  # a player's portrait (mini face) is a DDS this many pixels square
PICTURES = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".dds")
BASIC = ["Registered Position", "Age", "Height (cm)", "Weight (kg)", "Stronger Foot", "Nationality"]
KEYS = ["name", "shirt", "order"] + FIELDS


class Error(Exception):
    pass


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def load(d, n):
    p = os.path.join(d, n)
    if not os.path.exists(p):
        raise Error("no %s in %s" % (n, d))
    return bytearray(pesdb.wesys_unpack(open(p, "rb").read()))


def new_key(league, k):
    return "%s/%d" % (league, k)


def new_ref(league, k, n):
    """a new club's player, for a "join" list: club k of the league, squad place n"""
    return "%s/%d/%d" % (league, k, n)


def split_ref(ref):
    """(club key, place) of a new club's player ref, or (None, pid) of a game player's"""
    ref = str(ref)
    if ref.isdigit():
        return None, int(ref)
    club, _s, n = ref.rpartition("/")
    return club, (int(n) if n.isdigit() else None)


def teams(base):
    """{team id: (national, country id)} from Team.bin"""
    import mkworld as W
    raw = load(base, "Team.bin")
    out = {}
    for o in range(0, len(raw) - W.T_REC + 1, W.T_REC):
        c = (u32(raw, o + T_COUNTRY) >> 2) & 0x1ff
        out[u32(raw, o + W.T_ID)] = (bool(raw[o + T_NATIONAL] & 0x80), c)
    return out


# the abilities the overall rating of each kind of position is the mean of
RATED = {"GK": ["GK Awareness", "GK Catching", "GK Clearing", "GK Reflexes", "GK Reach"],
         "CB": ["Defensive Awareness", "Ball Winning", "Speed", "Physical Contact", "Heading", "Jump"],
         "DMF": ["Low Pass", "Lofted Pass", "Ball Control", "Stamina", "Ball Winning", "Offensive Awareness"],
         "CF": ["Offensive Awareness", "Ball Control", "Dribbling", "Finishing", "Speed", "Acceleration"]}


def overall(row):
    """a rough overall rating, the mean of the abilities the position leans on"""
    pos = row.get("Registered Position", "CF")
    if pos == "GK":
        names = RATED["GK"]
    elif pos in ("CB", "LB", "RB"):
        names = RATED["CB"]
    elif pos in ("DMF", "CMF"):
        names = RATED["DMF"]
    else:
        names = RATED["CF"]
    vals = [int(row[n]) for n in names if str(row.get(n, "")).isdigit()]
    return round(sum(vals) / len(vals)) if vals else 0


# the letters NFKD leaves whole, that one database folds to plain Latin anyway
FOLD = str.maketrans({"\u0142": "l", "\u0141": "l", "\u00f8": "o", "\u00d8": "o",
                      "\u0111": "d", "\u0110": "d", "\u00e6": "ae", "\u00c6": "ae",
                      "\u0153": "oe", "\u0152": "oe"})


def _letters(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s.casefold()).translate(FOLD)
    return "".join(ch for ch in s if ch.isalnum())


def _words(s):
    """the words of a name; a full stop or a hyphen splits as a space does, so an initial
    without its space ("K.Swiderski") is still its own word"""
    import re
    return [w for w in re.split(r"[\s\-.\u2013\u2014]+", s.strip()) if w]


def same_name(a, b):
    """the same player's name as two databases write it: whole, or with the first name cut to
    its initial ("Florian Niederlechner" / "F. Niederlechner"), or with the surname first
    ("Niederlechner Florian"); accents, case, hyphens aside"""
    if _letters(a) == _letters(b):
        return True
    wa, wb = _words(a), _words(b)
    if len(wa) < 2 or len(wb) < 2:
        return False
    if _letters("".join(sorted(wa))) == _letters("".join(sorted(wb))):   # the surname first
        return True
    return (_letters(wa[0])[:1] == _letters(wb[0])[:1]
            and _letters("".join(wa[1:])) == _letters("".join(wb[1:])))


class Squads:
    """the players of a set of tables (the game's, or a built world's)"""

    def __init__(self, db):
        self.db = db
        self.players = load(db, "Player.bin")
        self.assigns = load(db, "PlayerAssignment.bin")
        self.index = {u32(self.players, i * P_REC + P_ID): i * P_REC for i in range(len(self.players) // P_REC)}
        self.by_club = collections.defaultdict(list)
        self.file_order = collections.defaultdict(list)
        for i in range(len(self.assigns) // A_REC):
            o = i * A_REC
            pack = u32(self.assigns, o + E.A_PACK)
            self.by_club[u32(self.assigns, o + E.A_TID)].append(
                ((pack & E.ORDER_MASK) >> E.ORDER_SHIFT, u32(self.assigns, o + E.A_PID), E.shirt_of(pack), o))
            self.file_order[u32(self.assigns, o + E.A_TID)].append(u32(self.assigns, o + E.A_PID))
        for v in self.by_club.values():
            v.sort()
        self.clubs_of = collections.defaultdict(list)     # player id -> [team id] (club and national)
        for tid, v in self.by_club.items():
            for _order, pid, _shirt, _o in v:
                self.clubs_of[pid].append(tid)

    def name(self, pid):
        o = self.index[pid]
        return E.cstr(self.players[o + E.P_NAME:o + E.P_NAME + E.P_NAME_LEN])

    def summary(self):
        """[{player, name, Nationality, Registered Position, Age, rating, clubs}] of every player,
        for finding one (the Players page's Sign / Call up list); read once, a few seconds"""
        if getattr(self, "_summary", None) is None:
            need = {"Nationality", "Registered Position", "Age"}
            for pos in ("GK", "CB", "DMF", "CF"):
                need |= set(RATED[pos])
            out = []
            for pid, o in self.index.items():
                rec = self.players[o:o + P_REC]
                r = {n: E.show(n, E.getf(rec, n)) for n in need}
                r["player"] = str(pid)
                r["name"] = E.cstr(rec[E.P_NAME:E.P_NAME + E.P_NAME_LEN])
                r["rating"] = overall(r)
                r["clubs"] = list(self.clubs_of.get(pid, []))
                out.append(r)
            self._summary = out
        return self._summary

    def row(self, pid, shirt=None, order=None):
        o = self.index[pid]
        rec = self.players[o:o + P_REC]
        r = {"player": str(pid), "name": E.cstr(rec[E.P_NAME:E.P_NAME + E.P_NAME_LEN])}
        if shirt is not None:
            r["shirt"], r["order"] = str(shirt), str(order)
        for n in FIELDS:
            r[n] = E.show(n, E.getf(rec, n))
        return r

    def squad(self, tid):
        """[row] of a club, in squad order"""
        return [self.row(pid, shirt, order) for order, pid, shirt, _o in self.by_club.get(tid, [])
                if pid in self.index]

    def proto(self, per=SQUAD):
        """the squad every new club starts with (mkplayers.py picks it the same way)"""
        tid = next((c for c in sorted(self.by_club) if len(self.by_club[c]) >= per), None)
        if tid is None:
            return []
        keep = set(self.file_order[tid][:per])            # mkplayers copies the first `per` in the file
        rows = [r for r in self.squad(tid) if int(r["player"]) in keep]
        for k, r in enumerate(rows):
            r["player"] = str(k)
            r["name"] = ""                       # mkplayers names them FL Pnnnnn
        return rows


LINEUP = ["GK", "CB", "CB", "RB", "LB", "DMF", "DMF", "RMF", "LMF", "AMF", "CF"]   # 4-2-3-1


def best_eleven(rows, lineup=None):
    """{player: new order} that puts the strongest player for each place of the formation at
    orders 0-10 (the formation hands out places in that order) -- lineup, the role of each
    place, or the new clubs' default 4-2-3-1 -- and everyone else after them in the order
    they had"""
    left = list(rows)
    pick = []
    for pos in lineup or LINEUP:
        def score(r):
            rating = int(r.get(pos, "0") or 0) if str(r.get(pos, "")).isdigit() else 0
            own = r.get("Registered Position") == pos
            return (own or rating == 2, rating, overall(dict(r, **{"Registered Position": pos})))
        if not left:
            break
        best = max(left, key=score)
        pick.append(best)
        left.remove(best)
    left.sort(key=lambda r: int(r.get("order", "0") or 0))
    return {r["player"]: str(n) for n, r in enumerate(pick + left)}


def merged(rows, edits):
    """the rows with a club's changes on top (a copy); edits keyed like rows' "player" """
    out = []
    for r in rows:
        r = dict(r)
        r.update(edits.get(r["player"], {}))
        out.append(r)
    return out


def check_edit(ch):
    """problems with one player's changes, as sentences"""
    err = []
    for k, v in ch.items():
        v = str(v).strip()
        if v == "":
            continue
        if k in E.FIELDS:
            try:
                E.parse(k, v)
            except ValueError as e:
                err.append(str(e))
        elif k == "name":
            if len(v.encode("utf-8")) > E.P_NAME_LEN - 1:
                err.append("name %r is longer than %d bytes" % (v, E.P_NAME_LEN - 1))
        elif k in ("shirt", "order"):
            lo, hi = (1, 99) if k == "shirt" else (0, 63)
            if not (v.isdigit() and lo <= int(v) <= hi):
                err.append("%s %r is not %d-%d" % (k, v, lo, hi))
        elif k == "face":
            import lbfaces
            err += lbfaces.check(v)
        elif k == "portrait":
            bad = portrait_problem(v)
            if bad:
                err.append(bad)
        elif k == "id":
            if not (v.isdigit() and 1 <= int(v) <= PID_MAX):
                err.append("player id %r is not 1-%d" % (v, PID_MAX))
        elif k != "like":
            err.append("unknown field %r" % k)
    return err


def check(recipe):
    """every problem in the recipe's player changes, as sentences (empty = fine)"""
    err = []
    names = {L["name"]: L for L in recipe.get("leagues", [])}
    for club, c in (recipe.get("players") or {}).items():
        if not club.isdigit():
            lg, _s, k = club.rpartition("/")
            if lg not in names or not k.isdigit() or int(k) >= names[lg].get("clubs", 0):
                err.append("players of %s: no such new club in the recipe" % club)
                continue
            if c.get("add"):
                err.append("players of %s: a new club cannot take extra players (change them instead)" % club)
            # a player who joins counts towards the eleven and seven on the bench
            if len(set(c.get("remove") or [])) - len(set(c.get("join") or [])) > SQUAD - MIN_SQUAD:
                err.append("players of %s: a new club keeps at least %d players" % (club, MIN_SQUAD))
        if str(c.get("coach_portrait") or "").strip():
            bad = portrait_problem(c["coach_portrait"])
            if bad:
                err.append("manager of %s: %s" % (club, bad))
        if c.get("stadium"):
            import lbstadiums
            bad = lbstadiums.problem(c["stadium"])
            if bad:
                err.append("home stadium of %s: %s" % (club, bad))
        for key, ch in (c.get("edits") or {}).items():
            err += ["players of %s, player %s: %s" % (club, key, e) for e in check_edit(ch)]
            if "id" in ch and (club.isdigit() or not key.isdigit()):
                err.append("players of %s, player %s: only a new player takes an id of your own" % (club, key))
        for ch in c.get("add") or []:
            err += ["players of %s, new player: %s" % (club, e) for e in check_edit(ch)]
        refs = [str(r) for r in c.get("join") or []]
        if len(set(refs)) != len(refs):
            err.append("players of %s: a player joins twice" % club)
        for ref in refs:
            src, n = split_ref(ref)
            if src is None:
                continue
            lg, _s, k = src.rpartition("/")
            if lg not in names or not k.isdigit() or int(k) >= names[lg].get("clubs", 0) or n is None or n >= SQUAD:
                err.append("players of %s: no player %s in the recipe" % (club, ref))
            elif src == club:
                err.append("players of %s: %s is already in this squad" % (club, ref))
    want = collections.Counter()
    for club, c in (recipe.get("players") or {}).items():
        for key, ch in (c.get("edits") or {}).items():
            if str(ch.get("id", "")).strip():
                want[str(ch["id"]).strip()] += 1
        for ch in c.get("add") or []:
            if str(ch.get("id", "")).strip():
                want[str(ch["id"]).strip()] += 1
    err += ["player id %s is given to %d new players" % (i, n) for i, n in sorted(want.items()) if n > 1]
    return err


def has_players(recipe):
    return any(c.get("edits") or c.get("add") or c.get("remove") or c.get("join") or c.get("coach_portrait")
               for c in (recipe.get("players") or {}).values())


def portrait_problem(path):
    """why a picture cannot be a manager's portrait, or None"""
    if not os.path.isfile(path):
        return "no file %s" % path
    if not path.lower().endswith(PICTURES):
        return "%s is not a picture (%s)" % (os.path.basename(path), " ".join(PICTURES))
    return None


def coach_portraits(pl, root, log=print):
    r"""the recipe's manager portraits, into the world folder root: each club's "coach_portrait"
    becomes common\render\symbol\coach\coach_<the id of its manager>.png, 256 pixels square
    (a picture that is not square is centred on a clear background).  Needs the world's Team.bin."""
    from PIL import Image
    import mkworld as W
    tids = {}
    for p in pl["leagues"]:
        for k, tid in enumerate(p.get("teams") or []):
            tids[new_key(p["name"], k)] = tid
    want = {(int(club) if club.isdigit() else tids.get(club)): c["coach_portrait"]
            for club, c in (pl.get("players") or {}).items() if str(c.get("coach_portrait") or "").strip()}
    want.pop(None, None)
    if not want:
        return 0
    raw = load(os.path.join(root, "common", "etc", "pesdb"), "Team.bin")
    coach = {u32(raw, o + W.T_ID): u32(raw, o + T_COACH) for o in range(0, len(raw) - W.T_REC + 1, W.T_REC)}
    out = os.path.join(root, "common", "render", "symbol", "coach")
    os.makedirs(out, exist_ok=True)
    done = 0
    for tid, path in sorted(want.items()):
        bad = portrait_problem(path)
        if bad or tid not in coach:
            log("  manager portrait of club %d: %s, skipped" % (tid, bad or "no such club"))
            continue
        try:
            im = Image.open(path).convert("RGBA")
        except (OSError, ValueError) as e:
            log("  manager portrait of club %d: %s, skipped" % (tid, e))
            continue
        im.thumbnail((PORTRAIT, PORTRAIT), Image.LANCZOS)
        sq = Image.new("RGBA", (PORTRAIT, PORTRAIT), (0, 0, 0, 0))
        sq.paste(im, ((PORTRAIT - im.width) // 2, (PORTRAIT - im.height) // 2))
        sq.save(os.path.join(out, "coach_%d.png" % coach[tid]))
        done += 1
    log("  %d manager portraits" % done)
    return done


def _media(faces, portraits, pid, ch):
    """a changed player's face folder and portrait picture, into the lists build() installs"""
    if faces is not None and str(ch.get("face", "")).strip():
        faces.append((pid, ch["face"]))
    if portraits is not None and str(ch.get("portrait", "")).strip():
        portraits.append((pid, ch["portrait"]))


def player_portraits(portraits, root, log=print):
    r"""each (player id, picture) as the player's portrait, common\render\symbol\player\<id>.dds:
    PLAYER_PORTRAIT pixels square, DXT5, the picture centred on a clear background -- the form of
    the regen faces' portraits, which the game showed in the Team Sheet (30.09.). It goes after
    the faces, so it wins over a face folder's own portrait.dds."""
    from PIL import Image
    if not portraits:
        return 0
    out = os.path.join(root, "common", "render", "symbol", "player")
    os.makedirs(out, exist_ok=True)
    done = 0
    for pid, path in portraits:
        bad = portrait_problem(path)
        try:
            if bad:
                raise ValueError(bad)
            im = Image.open(path).convert("RGBA")
        except (OSError, ValueError) as e:
            log("  portrait of player %d: %s, skipped" % (pid, e))
            continue
        im.thumbnail((PLAYER_PORTRAIT, PLAYER_PORTRAIT), Image.LANCZOS)
        sq = Image.new("RGBA", (PLAYER_PORTRAIT, PLAYER_PORTRAIT), (0, 0, 0, 0))
        sq.paste(im, ((PLAYER_PORTRAIT - im.width) // 2, (PLAYER_PORTRAIT - im.height) // 2))
        sq.save(os.path.join(out, "%d.dds" % pid), pixel_format="DXT5")
        done += 1
    log("  %d player portraits" % done)
    return done


def _runs(ids):
    """sorted ids as "a-b" / "a" words"""
    out, ids = [], sorted(ids)
    i = 0
    while i < len(ids):
        j = i
        while j + 1 < len(ids) and ids[j + 1] == ids[j] + 1:
            j += 1
        out.append("%d-%d" % (ids[i], ids[j]) if j > i else "%d" % ids[i])
        i = j + 1
    return out


def new_face_lines(base, db, faces=(), portraits=(), per=64):
    """the world file's "newfaces" lines: the world's own players (ids above the game's, in db's
    Player.bin) get a face of the regen face pack by nationality (fl26regen, GitHub #52). A player
    with his own face folder is left out; one with only his own portrait goes in "newfaces3d"
    lines (the 3D face, his picture kept)."""
    if not os.path.exists(os.path.join(db, "Player.bin")):
        return []
    shipped, players = load(base, "Player.bin"), load(db, "Player.bin")
    top = max(u32(shipped, i * P_REC + P_ID) for i in range(len(shipped) // P_REC))
    own = {u32(players, i * P_REC + P_ID) for i in range(len(players) // P_REC)}
    own = {pid for pid in own if pid > top}
    own -= {pid for pid, _f in faces}
    keep = own & {pid for pid, _p in portraits}
    lines = []
    for word, ids in (("newfaces", own - keep), ("newfaces3d", keep)):
        runs = _runs(ids)
        lines += ["%s %s" % (word, " ".join(runs[k:k + per])) for k in range(0, len(runs), per)]
    return lines


def apply(pl, base, db, cap, log=print, faces=None, lineups=None, ids=None, portraits=None):
    r"""write the recipe's player changes into the world's tables in db (the world's
    common\etc\pesdb; Player.bin and PlayerAssignment.bin come from base when the world has
    none of its own yet).  pl is the plan: its leagues carry the team ids they were given.
    faces, a list, gets (player id, face folder) for every change with a "face", portraits
    (player id, picture) for every one with a "portrait". lineups:
    {new club id: the role of each place 0-10} for the clubs with a formation of their own.
    ids, a dict, gets {club: {player key: player id}} the way Mod Studio's Players page keys them:
    a new club's players by their place in its squad ("0", "1" ...), and a player added to any
    club as "+0", "+1" ... in the order of its "add" list."""
    changes = pl.get("players") or {}
    tids = {}
    for p in pl["leagues"]:
        game = {int(k) for k in (p.get("game_clubs") or {})}
        for k, tid in enumerate(p.get("teams") or []):
            if k not in game:                          # a club of the game goes by its team id
                tids[new_key(p["name"], k)] = tid
    if not has_players(pl) and not tids:
        return 0
    src = db if os.path.exists(os.path.join(db, "Player.bin")) else base
    players, assigns = load(src, "Player.bin"), load(src, "PlayerAssignment.bin")
    index = {u32(players, i * P_REC + P_ID): i * P_REC for i in range(len(players) // P_REC)}
    shipped = load(base, "Player.bin")
    game_top = max(u32(shipped, i * P_REC + P_ID) for i in range(len(shipped) // P_REC))
    shipped_n = len(shipped)                           # records past these are the world's own

    def squad_of(tid):
        return sorted(((u32(assigns, i * A_REC + E.A_PACK) & E.ORDER_MASK) >> E.ORDER_SHIFT,
                       u32(assigns, i * A_REC + E.A_PID), i * A_REC)
                      for i in range(len(assigns) // A_REC) if u32(assigns, i * A_REC + E.A_TID) == tid)

    # a new club's squad as mkplayers left it: place n in it is the recipe's key "n"
    first = {key: [pid for _o, pid, _a in squad_of(tid)] for key, tid in tids.items()}
    added_ids = {}                                     # club -> [id of each "add" entry]

    def club_tid(club):
        return int(club) if club.isdigit() else tids.get(club)

    # the players named in "join" lists, found before anything moves: a new club's player by
    # his place in its squad as mkplayers left it
    refs = {}
    for club, c in changes.items():
        for ref in c.get("join") or []:
            srcclub, n = split_ref(ref)
            if srcclub is None:
                if n not in index:
                    raise Error("players of %s: no player %d in the game" % (club, n))
                refs[str(ref)] = n
            else:
                t = tids.get(srcclub)
                sq = squad_of(t) if t is not None else []
                if n is None or n >= len(sq):
                    raise Error("players of %s: no player %s (was the club built?)" % (club, ref))
                refs[str(ref)] = sq[n][1]

    renamed = {}                                       # old player id -> the id of the recipe

    def new_id(want, old=None):
        pid = int(want)
        if pid <= game_top:
            raise Error("player id %d: a new player's id has to be above the game's own (%d)" % (pid, game_top))
        if pid > PID_MAX:
            raise Error("player id %d: above %d" % (pid, PID_MAX))
        if pid in index and pid != old:
            raise Error("player id %d is taken" % pid)
        return pid

    def renumber(old, pid):
        o = index.pop(old)
        players[o + P_ID:o + P_ID + 4] = pid.to_bytes(4, "little")
        index[pid] = o
        for i in range(len(assigns) // A_REC):
            if u32(assigns, i * A_REC + E.A_PID) == old:
                assigns[i * A_REC + E.A_PID:i * A_REC + E.A_PID + 4] = pid.to_bytes(4, "little")
        renamed[old] = pid

    changed = added = removed = joined = 0
    next_pid = max(index) + 1
    eid = max(u32(assigns, i * A_REC + E.A_EID) for i in range(len(assigns) // A_REC)) + 1
    drop = set()
    touched = set()                                    # clubs whose squad order may have gaps
    later = {}                                         # club -> {ref: changes} of players who join it
    for club, c in changes.items():
        tid = club_tid(club)
        if tid is None:
            log("  players of %s: the club was not built, skipped" % club)
            continue
        sq = squad_of(tid)
        where = {}                                     # recipe key -> (pid, assignment offset)
        for n, (order, pid, ao) in enumerate(sq):
            where[str(pid) if club.isdigit() else str(n)] = (pid, ao)
        for key in c.get("remove") or []:
            if key in where:
                drop.add(where[key][1])
                touched.add(tid)
                removed += 1
        for ch in c.get("add") or []:
            like = str(ch.get("like", ""))
            srcpid = int(like) if like.isdigit() and int(like) in index else (sq[0][1] if sq else None)
            if srcpid is None:
                raise Error("players of %s: nothing to copy a new player from" % club)
            if len(index) + 1 > cap:
                raise Error("the player table is full (%d)" % cap)
            rec = bytearray(players[index[srcpid]:index[srcpid] + P_REC])
            if str(ch.get("id", "")).strip():
                pid = new_id(ch["id"])
            else:
                pid = next_pid
                while pid in index:
                    pid += 1
            next_pid = max(next_pid, pid + 1)
            added_ids.setdefault(club, []).append(pid)
            rec[P_ID:P_ID + 4] = pid.to_bytes(4, "little")
            index[pid] = len(players)
            players += rec
            shirt = E.free_shirt(u32(assigns, ao + E.A_PACK) for _o, _p, ao in sq)
            order = max((o for o, _p, _a in sq), default=-1) + 1
            e = bytearray(A_REC)
            for off, v in ((E.A_EID, eid), (E.A_PID, pid), (E.A_TID, tid),
                           (E.A_PACK, E.with_shirt(order << E.ORDER_SHIFT, shirt))):
                e[off:off + 4] = v.to_bytes(4, "little")
            eid += 1
            ao = len(assigns)
            assigns += e
            sq.append((order, pid, ao))
            _write(players, assigns, index[pid], ao, ch)
            _media(faces, portraits, pid, ch)
            added += 1
        for key, ch in (c.get("edits") or {}).items():
            if key not in where:
                if key in (c.get("join") or []):
                    later.setdefault(club, {})[key] = ch   # a player who joins: once he is there
                    continue
                log("  players of %s: no player %s, skipped" % (club, key))
                continue
            pid, ao = where[key]
            if str(ch.get("id", "")).strip() and not club.isdigit() and int(ch["id"]) != pid:
                renumber(pid, new_id(ch["id"], pid))
                pid = int(ch["id"])
            _write(players, assigns, index[pid], ao, ch)
            _media(faces, portraits, pid, ch)
            changed += 1

    # the players who join a club or a national team
    kinds = teams(base)
    for p in pl["leagues"]:
        for tid in p.get("teams") or []:
            kinds.setdefault(tid, (False, p.get("country")))
    signed = {}                                        # player id -> the club that signed him
    for club, c in changes.items():
        tid = club_tid(club)
        if tid is None or not c.get("join"):
            continue
        national = kinds.get(tid, (False, 0))[0]
        for ref in c["join"]:
            pid = refs[str(ref)]
            pid = renamed.get(pid, pid)
            rows = [(i * A_REC, u32(assigns, i * A_REC + E.A_TID)) for i in range(len(assigns) // A_REC)
                    if u32(assigns, i * A_REC + E.A_PID) == pid and i * A_REC not in drop]
            if any(t == tid for _ao, t in rows):
                log("  players of %s: player %d is already there" % (club, pid))
                continue
            sq = squad_of(tid)
            shirt = E.free_shirt(u32(assigns, ao + E.A_PACK) for _o, _p, ao in sq if ao not in drop)
            order = max((o for o, _p, ao in sq if ao not in drop), default=-1) + 1
            pack = E.with_shirt(order << E.ORDER_SHIFT, shirt)     # no role flags: a newcomer
            mine = [ao for ao, t in rows if kinds.get(t, (False, 0))[0] == national]
            if national and mine:                      # one national team at a time
                for ao in mine:
                    drop.add(ao)
                    touched.add(u32(assigns, ao + E.A_TID))
                mine = []
            if not national:
                if pid in signed:
                    raise Error("player %d joins two clubs (%s and %s)" % (pid, signed[pid], club))
                signed[pid] = club
            if mine:                                   # a transfer: his club assignment moves
                ao = mine[0]
                touched.add(u32(assigns, ao + E.A_TID))
                assigns[ao + E.A_TID:ao + E.A_TID + 4] = tid.to_bytes(4, "little")
                assigns[ao + E.A_PACK:ao + E.A_PACK + 4] = pack.to_bytes(4, "little")
            else:
                e = bytearray(A_REC)
                for off, v in ((E.A_EID, eid), (E.A_PID, pid), (E.A_TID, tid), (E.A_PACK, pack)):
                    e[off:off + 4] = v.to_bytes(4, "little")
                eid += 1
                ao = len(assigns)
                assigns += e
            ch = (later.get(club) or {}).get(str(ref))
            if ch:
                _write(players, assigns, index[pid], ao, ch)
                _media(faces, portraits, pid, ch)
                changed += 1
            joined += 1

    # a new club starts with the prototype's squad order, which is sorted by position and
    # plays centre backs out wide; unless the recipe orders it, give it its best eleven
    lined = 0
    for key, tid in tids.items():
        eds = (changes.get(key) or {}).get("edits") or {}
        if any("order" in ch for ch in eds.values()):
            continue
        rows = []
        for order, pid, ao in squad_of(tid):
            if ao in drop:                             # leaving the club: no place in the order
                continue
            rec = players[index[pid]:index[pid] + P_REC]
            r = {"player": str(ao), "order": str(order)}
            for n in FIELDS:
                r[n] = E.show(n, E.getf(rec, n))
            rows.append(r)
        for ao, o in best_eleven(rows, (lineups or {}).get(tid)).items():
            ao = int(ao)
            pack = u32(assigns, ao + E.A_PACK) & ~E.ORDER_MASK | int(o) << E.ORDER_SHIFT
            assigns[ao + E.A_PACK:ao + E.A_PACK + 4] = pack.to_bytes(4, "little")
        lined += 1 if rows else 0
    if drop:
        keep = bytearray()
        for i in range(len(assigns) // A_REC):
            if i * A_REC not in drop:
                keep += assigns[i * A_REC:(i + 1) * A_REC]
        assigns = keep
    # a player left with no club and made in this build is the placeholder a NewLife squad
    # replaced: the game lists him as a free agent (#96). A game player with no club stays --
    # a recipe may drop one on purpose.
    assigned = {u32(assigns, i * A_REC + E.A_PID) for i in range(len(assigns) // A_REC)}
    base_ids = {u32(shipped, i * P_REC + P_ID) for i in range(len(shipped) // P_REC)}
    drop_ids = set(index) - assigned - base_ids
    if drop_ids:
        players = b"".join(players[o:o + P_REC] for _pid, o in sorted(index.items(), key=lambda kv: kv[1])
                           if _pid not in drop_ids)
        for pid in drop_ids:
            index.pop(pid, None)
        if faces is not None:
            faces[:] = [f for f in faces if f[0] not in drop_ids]
        if portraits is not None:
            portraits[:] = [f for f in portraits if f[0] not in drop_ids]
    # a squad someone left closes up -- orders 0, 1, 2 ... in the order they had -- so its
    # first eleven are still eleven
    for tid in touched:
        for n, (order, pid, ao) in enumerate(squad_of(tid)):
            if order != n:
                pack = u32(assigns, ao + E.A_PACK) & ~E.ORDER_MASK | n << E.ORDER_SHIFT
                assigns[ao + E.A_PACK:ao + E.A_PACK + 4] = pack.to_bytes(4, "little")
    for club, c in changes.items():
        tid = club_tid(club)
        if tid is None or not (c.get("join") or c.get("add")):
            continue
        national = kinds.get(tid, (False, 0))[0]
        n, most = len(squad_of(tid)), NATIONAL_MAX if national else CLUB_MAX
        if n > most:
            raise Error("players of %s: %d players -- a %s has at most %d" % (
                club, n, "national team" if national else "club", most))
    if len(players) > shipped_n:
        # Player.bin is in id order, as the game ships it; an id of the recipe's own can land
        # anywhere above the game's, so the world's part is put back in order
        recs = sorted((players[o:o + P_REC] for o in range(shipped_n, len(players), P_REC)),
                      key=lambda r: u32(r, P_ID))
        players = players[:shipped_n] + b"".join(recs)
    _check_orders(assigns)
    if ids is not None:
        for key, pids in first.items():
            gone = set((changes.get(key) or {}).get("remove") or [])
            ids[key] = {str(n): renamed.get(pid, pid) for n, pid in enumerate(pids)
                        if str(n) not in gone and renamed.get(pid, pid) not in drop_ids}
        for club, pids in added_ids.items():
            ids.setdefault(club, {}).update({"+%d" % n: pid for n, pid in enumerate(pids)
                                             if pid not in drop_ids})
    for n, b in (("Player.bin", players), ("PlayerAssignment.bin", assigns)):
        open(os.path.join(db, n), "wb").write(pesdb.wesys_pack(bytes(b)))
    if has_players(pl):
        log("  players: %d changed, %d new, %d left their club%s%s%s" % (
            changed, added, removed, ", %d joined a club or a national team" % joined if joined else "",
            ", %d took an id of their own" % len(renamed) if renamed else "",
            ", %d placeholders deleted" % len(drop_ids) if drop_ids else ""))
    if lined:
        log("  best eleven picked for %d new clubs" % lined)
    return changed + added + removed + joined


def _write(players, assigns, po, ao, ch):
    rec = bytearray(players[po:po + P_REC])
    old = bytes(rec)
    for n, v in ch.items():
        v = str(v).strip()
        if n in E.FIELDS and v != "":
            E.setf(rec, n, E.parse(n, v))
    E.natural(rec, old)
    name = str(ch.get("name", "")).strip()
    if name:
        nm = name.encode("utf-8")
        for k in range(E.P_NAME_SLOTS):
            at = E.P_NAME + k * E.P_NAME_LEN
            rec[at:at + E.P_NAME_LEN] = nm + bytes(E.P_NAME_LEN - len(nm))
    players[po:po + P_REC] = rec
    pack = u32(assigns, ao + E.A_PACK)
    if str(ch.get("shirt", "")).strip().isdigit():
        pack = E.with_shirt(pack, int(ch["shirt"]))
    if str(ch.get("order", "")).strip().isdigit():
        pack = pack & ~E.ORDER_MASK | int(ch["order"]) << E.ORDER_SHIFT
    assigns[ao + E.A_PACK:ao + E.A_PACK + 4] = pack.to_bytes(4, "little")


def _check_orders(assigns):
    seen, clash = {}, []
    for i in range(len(assigns) // A_REC):
        o = i * A_REC
        k = (u32(assigns, o + E.A_TID), (u32(assigns, o + E.A_PACK) & E.ORDER_MASK) >> E.ORDER_SHIFT)
        if k in seen:
            clash.append("club %d: two players have squad order %d" % k)
        seen[k] = 1
    if clash:
        raise Error("squad orders clash:\n  " + "\n  ".join(clash[:10]))


# ---- CSV: the same columns as playeredit.py, one club at a time ----

def export_csv(path, rows):
    cols = ["player", "player_id", "name", "shirt", "order"] + FIELDS
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])


def import_csv(path, rows):
    """changes {key: {field: text}} from a CSV of one club: a line matches a player by its
    `player` cell, or when that is empty or unknown, by its place in the file; only cells
    that differ from the player as he is become changes"""
    with open(path, newline="", encoding="utf-8-sig") as f:
        lines = list(csv.reader(f))
    if not lines:
        return {}, []
    head = [c.strip() for c in lines[0]]
    unknown = [c for c in head if c and c not in KEYS and c not in ("player", "player_id", "club", "like")]
    if unknown:
        raise Error("unknown columns: %s" % ", ".join(unknown))
    by_key = {r["player"]: r for r in rows}
    out, err = {}, []
    for n, line in enumerate(lines[1:]):
        cell = {h: (line[i].strip() if i < len(line) else "") for i, h in enumerate(head) if h}
        if not any(cell.values()):
            continue
        key = cell.get("player", "")
        r = by_key.get(key) or (rows[n] if n < len(rows) else None)
        if r is None:
            err.append("line %d: no player %s and no player in that place" % (n + 2, key or "?"))
            continue
        ch = {k: v for k, v in cell.items() if k in KEYS and v != "" and v != str(r.get(k, ""))}
        e = check_edit(ch)
        if e:
            err += ["line %d: %s" % (n + 2, x) for x in e]
        elif ch:
            out[r["player"]] = ch
    return out, err
