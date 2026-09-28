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
a face folder, moved to the player's id when the world is built (lbfaces.py).
"""
import collections, csv, os

import pesdb
import playeredit as E

P_REC, P_ID = E.P_REC, E.P_ID
A_REC = E.A_REC
SQUAD = 30
MIN_SQUAD = 18        # a new club may lose players down to this: eleven and seven on the bench
FIELDS = list(E.FIELDS)
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


def overall(row):
    """a rough overall rating, the mean of the abilities the position leans on"""
    pos = row.get("Registered Position", "CF")
    if pos == "GK":
        names = ["GK Awareness", "GK Catching", "GK Clearing", "GK Reflexes", "GK Reach"]
    elif pos in ("CB", "LB", "RB"):
        names = ["Defensive Awareness", "Ball Winning", "Speed", "Physical Contact", "Heading", "Jump"]
    elif pos in ("DMF", "CMF"):
        names = ["Low Pass", "Lofted Pass", "Ball Control", "Stamina", "Ball Winning", "Offensive Awareness"]
    else:
        names = ["Offensive Awareness", "Ball Control", "Dribbling", "Finishing", "Speed", "Acceleration"]
    vals = [int(row[n]) for n in names if str(row.get(n, "")).isdigit()]
    return round(sum(vals) / len(vals)) if vals else 0


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
                ((pack & E.ORDER_MASK) >> E.ORDER_SHIFT, u32(self.assigns, o + E.A_PID), pack & E.SHIRT_MASK, o))
            self.file_order[u32(self.assigns, o + E.A_TID)].append(u32(self.assigns, o + E.A_PID))
        for v in self.by_club.values():
            v.sort()

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


def best_eleven(rows):
    """{player: new order} that puts the strongest player for each place of the new clubs'
    4-2-3-1 at orders 0-10 (the formation hands out places in that order), and everyone
    else after them in the order they had"""
    left = list(rows)
    pick = []
    for pos in LINEUP:
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
            hi = 99 if k == "shirt" else 63
            if not (v.isdigit() and int(v) <= hi):
                err.append("%s %r is not 0-%d" % (k, v, hi))
        elif k == "face":
            import lbfaces
            err += lbfaces.check(v)
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
            if len(set(c.get("remove") or [])) > SQUAD - MIN_SQUAD:
                err.append("players of %s: a new club keeps at least %d players" % (club, MIN_SQUAD))
        for key, ch in (c.get("edits") or {}).items():
            err += ["players of %s, player %s: %s" % (club, key, e) for e in check_edit(ch)]
        for ch in c.get("add") or []:
            err += ["players of %s, new player: %s" % (club, e) for e in check_edit(ch)]
    return err


def has_players(recipe):
    return any(c.get("edits") or c.get("add") or c.get("remove") for c in (recipe.get("players") or {}).values())


def apply(pl, base, db, cap, log=print, faces=None):
    r"""write the recipe's player changes into the world's tables in db (the world's
    common\etc\pesdb; Player.bin and PlayerAssignment.bin come from base when the world has
    none of its own yet).  pl is the plan: its leagues carry the team ids they were given.
    faces, a list, gets (player id, face folder) for every change with a "face"."""
    changes = pl.get("players") or {}
    tids = {}
    for p in pl["leagues"]:
        for k, tid in enumerate(p.get("teams") or []):
            tids[new_key(p["name"], k)] = tid
    if not has_players(pl) and not tids:
        return 0
    src = db if os.path.exists(os.path.join(db, "Player.bin")) else base
    players, assigns = load(src, "Player.bin"), load(src, "PlayerAssignment.bin")
    index = {u32(players, i * P_REC + P_ID): i * P_REC for i in range(len(players) // P_REC)}

    def squad_of(tid):
        return sorted(((u32(assigns, i * A_REC + E.A_PACK) & E.ORDER_MASK) >> E.ORDER_SHIFT,
                       u32(assigns, i * A_REC + E.A_PID), i * A_REC)
                      for i in range(len(assigns) // A_REC) if u32(assigns, i * A_REC + E.A_TID) == tid)

    changed = added = removed = 0
    next_pid = max(index) + 1
    eid = max(u32(assigns, i * A_REC + E.A_EID) for i in range(len(assigns) // A_REC)) + 1
    drop = set()
    for club, c in changes.items():
        tid = int(club) if club.isdigit() else tids.get(club)
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
                removed += 1
        for ch in c.get("add") or []:
            like = str(ch.get("like", ""))
            srcpid = int(like) if like.isdigit() and int(like) in index else (sq[0][1] if sq else None)
            if srcpid is None:
                raise Error("players of %s: nothing to copy a new player from" % club)
            if len(index) + 1 > cap:
                raise Error("the player table is full (%d)" % cap)
            rec = bytearray(players[index[srcpid]:index[srcpid] + P_REC])
            pid = next_pid
            next_pid += 1
            rec[P_ID:P_ID + 4] = pid.to_bytes(4, "little")
            index[pid] = len(players)
            players += rec
            taken = {u32(assigns, ao + E.A_PACK) & E.SHIRT_MASK for _o, _p, ao in sq}
            shirt = next(n for n in range(1, 100) if n not in taken)
            order = max((o for o, _p, _a in sq), default=-1) + 1
            e = bytearray(A_REC)
            for off, v in ((E.A_EID, eid), (E.A_PID, pid), (E.A_TID, tid),
                           (E.A_PACK, order << E.ORDER_SHIFT | shirt)):
                e[off:off + 4] = v.to_bytes(4, "little")
            eid += 1
            ao = len(assigns)
            assigns += e
            sq.append((order, pid, ao))
            _write(players, assigns, index[pid], ao, ch)
            if faces is not None and str(ch.get("face", "")).strip():
                faces.append((pid, ch["face"]))
            added += 1
        for key, ch in (c.get("edits") or {}).items():
            if key not in where:
                log("  players of %s: no player %s, skipped" % (club, key))
                continue
            pid, ao = where[key]
            _write(players, assigns, index[pid], ao, ch)
            if faces is not None and str(ch.get("face", "")).strip():
                faces.append((pid, ch["face"]))
            changed += 1
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
        for ao, o in best_eleven(rows).items():
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
    _check_orders(assigns)
    for n, b in (("Player.bin", players), ("PlayerAssignment.bin", assigns)):
        open(os.path.join(db, n), "wb").write(pesdb.wesys_pack(bytes(b)))
    if has_players(pl):
        log("  players: %d changed, %d new, %d left their club" % (changed, added, removed))
    if lined:
        log("  best eleven picked for %d new clubs" % lined)
    return changed + added + removed


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
        pack = pack & ~E.SHIRT_MASK | int(ch["shirt"])
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
    cols = ["player", "name", "shirt", "order"] + FIELDS
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
    unknown = [c for c in head if c and c not in KEYS and c not in ("player", "club", "like")]
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
