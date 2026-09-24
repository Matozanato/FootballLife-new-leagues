r"""python playeredit.py --root <world> --export players.csv [--club <team id or name>]
   python playeredit.py --root <world> --import players.csv [--cap 51729]

A player editor that works on the files, for the clubs the game's Edit mode cannot reach.

--export writes one line per player with every field of the player record that is known,
under its own name: position and position ratings, height, weight, age, nationality, foot,
the 25 abilities, form, injury resistance, playing style and the 45 skills, together with
the club, shirt number and squad order.  Open it in a spreadsheet, change what you want,
save it as CSV, and --import writes it back.

--import reads the same columns.  Only the `player` column is required; any other column may
be left out, and an empty cell leaves that field as it is.  So a file with just

    player,Speed,Finishing
    179733,88,85

changes two abilities of one player and nothing else.

Creating a player: put `new` in the player column and give the club.  The new player is a copy
of the player named in the `like` column (or, without one, of the first player of the club),
with every other cell of the line applied on top, so a line that fills in all the columns
describes the whole player:

    player,club,like,name,shirt,Registered Position,Speed
    new,72318,180590,Ivan Example,27,CF,80

The new player gets the next free player id and joins the end of the squad.  The player table
has a ceiling that depends on the patch set installed -- see mkplayers.py; --cap says which
(default 51729, the players set used in docs/beginners-guide.md).

The squad order matters: the first eleven of a club's squad order are its starting eleven,
and the formation hands them their places in a fixed order.  For the default 4-2-3-1 of the
new clubs that order is GK, CB, CB, RB, LB, DMF, DMF, RMF, LMF, AMF, CF (order 0 to 10).  To
change the lineup, change `order`; within a club every order must be different.

Every line is checked before anything is written -- a value out of range, an unknown player
or club, a clash of squad orders -- and one bad line stops the run with the whole list of
problems.  The original files are kept as .bak the first time.

Fields and their ranges (see docs/player-record.md for where each one sits in the record):

  Registered Position   GK CB LB RB DMF CMF LMF RMF AMF LWF RWF SS CF
  GK .. CF              position rating for each position: 0 none, 1 can play, 2 natural
  Height (cm)           100-227     Weight (kg)     30-157     Age          15-78
  Nationality           0-511, a country code: copy it from a player of that country
  Stronger Foot         Right / Left
  Weak Foot Usage, Weak Foot Accuracy        0-3
  Form                  0-7          Injury Resistance   0-2
  Playing Style         0-31, copy it from a player who plays the way you want
  abilities             40-99
  skills                0 or 1
"""
import csv, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb

P_REC, P_ID = 312, 0x08
P_NAME, P_NAME_LEN, P_NAME_SLOTS = 0x44, 0x3d, 4
A_REC = 16
A_EID, A_PID, A_TID, A_PACK = 0x00, 0x04, 0x08, 0x0c
SHIRT_MASK = 0x3ff
ORDER_SHIFT, ORDER_MASK = 10, 0xfc00    # bits 16 and up are role flags, kept as they are
T_REC, T_ID, T_NAME, T_NAME_LEN = 1532, 0x08, 0x170, 0x46
DEFAULT_CAP = 51729

POSITIONS = ["GK", "CB", "LB", "RB", "DMF", "CMF", "LMF", "RMF", "AMF", "LWF", "RWF", "SS", "CF"]

# name: (first bit counted from the start of the record, width in bits, value added)
BODY = [
    ("Registered Position", 434, 4, 0),
    ("GK", 350, 2, 0), ("CB", 468, 2, 0), ("LB", 318, 2, 0), ("RB", 474, 2, 0),
    ("DMF", 414, 2, 0), ("CMF", 456, 2, 0), ("LMF", 466, 2, 0), ("RMF", 460, 2, 0),
    ("AMF", 464, 2, 0), ("LWF", 472, 2, 0), ("RWF", 476, 2, 0), ("SS", 478, 2, 0),
    ("CF", 470, 2, 0),
    ("Height (cm)", 216, 7, 100), ("Weight (kg)", 256, 7, 30), ("Age", 408, 6, 15),
    ("Nationality", 233, 9, 0), ("Stronger Foot", 514, 1, 0),
    ("Weak Foot Usage", 454, 2, 0), ("Weak Foot Accuracy", 462, 2, 0),
    ("Form", 438, 3, 0), ("Injury Resistance", 458, 2, 0), ("Playing Style", 155, 5, 0),
]
ABILITIES = [
    ("Offensive Awareness", 370), ("Ball Control", 281), ("Dribbling", 352),
    ("Tight Possession", 416), ("Low Pass", 263), ("Lofted Pass", 402), ("Finishing", 396),
    ("Heading", 288), ("Place Kicking", 250), ("Curl", 332), ("Speed", 306),
    ("Acceleration", 344), ("Kicking Power", 358), ("Jump", 294), ("Physical Contact", 390),
    ("Balance", 376), ("Stamina", 338), ("Defensive Awareness", 275), ("Ball Winning", 312),
    ("Aggression", 384), ("GK Awareness", 326), ("GK Catching", 364), ("GK Clearing", 269),
    ("GK Reflexes", 320), ("GK Reach", 300),
]
SKILLS = [
    ("Scissors Feint", 519), ("Double Touch", 523), ("Flip Flap", 485), ("Marseille Turn", 497),
    ("Sombrero", 482), ("Cross Over Turn", 287), ("Cut Behind & Turn", 528),
    ("Scotch Move", 525), ("Step On Skill control", 500), ("Heading (skill)", 495),
    ("Long Range Drive", 527), ("Chip shot control", 506), ("Long Range Shooting", 518),
    ("Knuckle Shot", 513), ("Dipping Shot", 494), ("Rising Shots", 499),
    ("Acrobatic Finishing", 524), ("Heel Trick", 505), ("First-time Shot", 511),
    ("One-touch Pass", 507), ("Through Passing", 487), ("Weighted Pass", 484),
    ("Pinpoint Crossing", 483), ("Outside Curler", 493), ("Rabona", 515),
    ("No Look Pass", 512), ("Low Lofted Pass", 488), ("GK Low Punt", 490),
    ("GK High Punt", 496), ("Long Throw", 521), ("GK Long Throw", 522),
    ("Penalty Specialist", 501), ("GK Penalty Saver", 502), ("Gamesmanship", 491),
    ("Man Marking", 504), ("Track Back", 517), ("Interception", 503),
    ("Acrobatic Clear", 530), ("Captaincy", 492), ("Super-Sub", 516),
    ("Fighting Spirit", 486), ("Trickster", 489), ("Mazing Run", 531),
    ("Speeding Bullet", 526), ("Incisive Run", 510), ("Long Ball Expert", 529),
    ("Early Cross", 447), ("Long Ranger", 520),
]
FIELDS = {n: (b, w, add) for n, b, w, add in BODY}
FIELDS.update({n: (b, 6, 40) for n, b in ABILITIES})
FIELDS.update({n: (b, 1, 0) for n, b in SKILLS})
LIMITS = {n: (add, add + (1 << w) - 1) for n, (b, w, add) in FIELDS.items()}
LIMITS.update({n: (40, 99) for n, _ in ABILITIES})
LIMITS.update({"Registered Position": (0, 12), "Playing Style": (0, 31)})
for p in POSITIONS:
    LIMITS[p] = (0, 2)
LIMITS["Injury Resistance"] = (0, 2)

META = ["player", "club", "shirt", "order", "name", "like"]
COLUMNS = META[:5] + list(FIELDS)


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def cstr(b):
    return b.split(b"\x00", 1)[0].decode("utf-8", "replace")


def getf(rec, name):
    b, w, add = FIELDS[name]
    return (int.from_bytes(rec, "little") >> b & ((1 << w) - 1)) + add


def setf(rec, name, val):
    b, w, add = FIELDS[name]
    v = int.from_bytes(rec, "little")
    v = v & ~(((1 << w) - 1) << b) | ((val - add) << b)
    rec[:] = v.to_bytes(len(rec), "little")


def show(name, v):
    if name == "Registered Position":
        return POSITIONS[v] if v < len(POSITIONS) else str(v)
    if name == "Stronger Foot":
        return "Left" if v else "Right"
    return str(v)


def parse(name, s):
    """cell text -> stored value, or raise ValueError with the reason"""
    if name == "Registered Position":
        if s.upper() in POSITIONS:
            return POSITIONS.index(s.upper())
        if not s.isdigit():
            raise ValueError("%s must be one of %s, not %r" % (name, " ".join(POSITIONS), s))
    if name == "Stronger Foot":
        if s.lower() in ("right", "r", "0"):
            return 0
        if s.lower() in ("left", "l", "1"):
            return 1
        raise ValueError("%s must be Right or Left, not %r" % (name, s))
    try:
        v = int(s)
    except ValueError:
        raise ValueError("%s: %r is not a number" % (name, s))
    lo, hi = LIMITS[name]
    if not lo <= v <= hi:
        raise ValueError("%s must be %d-%d, not %d" % (name, lo, hi, v))
    return v


def load(db, n):
    p = os.path.join(db, n)
    if not os.path.exists(p):
        raise SystemExit("no %s at %s" % (n, p))
    return p, bytearray(pesdb.wesys_unpack(open(p, "rb").read()))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    root = get("--root")
    if not root or not (get("--export") or get("--import")):
        raise SystemExit(__doc__)
    db = os.path.join(root, "common", "etc", "pesdb")
    ppath, players = load(db, "Player.bin")
    apath, assigns = load(db, "PlayerAssignment.bin")
    _, teams = load(db, "Team.bin")
    if len(players) % P_REC or len(assigns) % A_REC:
        raise SystemExit("Player.bin or PlayerAssignment.bin is not a whole number of records")
    index = {u32(players, i * P_REC + P_ID): i * P_REC for i in range(len(players) // P_REC)}
    slot = {}
    for i in range(len(assigns) // A_REC):
        slot.setdefault(u32(assigns, i * A_REC + A_PID), i * A_REC)
    clubs = {u32(teams, i * T_REC + T_ID): cstr(teams[i * T_REC + T_NAME:i * T_REC + T_NAME + T_NAME_LEN])
             for i in range(len(teams) // T_REC)}

    def club_of(s):
        if s.isdigit() and int(s) in clubs:
            return int(s)
        hits = [c for c, n in clubs.items() if n == s]
        return hits[0] if len(hits) == 1 else None

    out = get("--export")
    if out:
        want = None
        if get("--club"):
            want = club_of(get("--club"))
            if want is None:
                raise SystemExit("no single club %r -- use the team id" % get("--club"))
        rows = []
        for pid, o in index.items():
            s = slot.get(pid)
            tid = u32(assigns, s + A_TID) if s is not None else None
            if want is not None and tid != want:
                continue
            pack = u32(assigns, s + A_PACK) if s is not None else None
            rec = players[o:o + P_REC]
            rows.append([pid, "" if tid is None else tid,
                         "" if pack is None else pack & SHIRT_MASK,
                         "" if pack is None else (pack & ORDER_MASK) >> ORDER_SHIFT,
                         cstr(rec[P_NAME:P_NAME + P_NAME_LEN])] +
                        [show(n, getf(rec, n)) for n in FIELDS])
        rows.sort(key=lambda r: (str(r[1]), r[3] if r[3] != "" else 0, r[0]))
        with open(out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            w.writerows(rows)
        print("wrote %d players to %s" % (len(rows), out))
        return 0

    cap = int(get("--cap", str(DEFAULT_CAP)))
    with open(get("--import"), newline="", encoding="utf-8-sig") as f:
        lines = list(csv.reader(f))
    if not lines or "player" not in [c.strip() for c in lines[0]]:
        raise SystemExit("the first line must be a header with a `player` column")
    head = [c.strip() for c in lines[0]]
    unknown = [c for c in head if c and c not in FIELDS and c not in META]
    if unknown:
        raise SystemExit("unknown columns: %s" % ", ".join(unknown))

    errors, todo = [], []
    next_pid = max(index) + 1
    for ln, row in enumerate(lines[1:], 2):
        cell = {h: (row[i].strip() if i < len(row) else "") for i, h in enumerate(head) if h}
        key = cell.get("player", "")
        if not key or key.startswith("#"):
            continue
        err = []
        if key.lower() == "new":
            club = club_of(cell.get("club", ""))
            if club is None:
                err.append("a new player needs a club (team id or exact name)")
            like = cell.get("like", "")
            if like:
                if not (like.isdigit() and int(like) in index):
                    err.append("no player %r to copy from" % like)
                src = int(like) if like.isdigit() else None
            else:
                mates = sorted(((u32(assigns, s + A_PACK) & ORDER_MASK) >> ORDER_SHIFT, p) for p, s in slot.items()
                               if club is not None and u32(assigns, s + A_TID) == club)
                src = mates[0][1] if mates else None
                if club is not None and src is None:
                    err.append("club %d has no players to copy from -- give `like`" % club)
            pid = next_pid
            next_pid += 1
        else:
            if not (key.isdigit() and int(key) in index):
                errors.append("line %d: no player %r" % (ln, key))
                continue
            pid, src, club = int(key), None, None
            if cell.get("club") and club_of(cell["club"]) != (u32(assigns, slot[pid] + A_TID) if pid in slot else None):
                err.append("moving a player to another club is not supported; "
                           "create him there with `new` instead")
        vals = {}
        for n in FIELDS:
            if cell.get(n):
                try:
                    vals[n] = parse(n, cell[n])
                except ValueError as e:
                    err.append(str(e))
        name = cell.get("name", "")
        if name and len(name.encode("utf-8")) > P_NAME_LEN - 1:
            err.append("name %r is longer than %d bytes" % (name, P_NAME_LEN - 1))
        nums = {}
        for k, hi in (("shirt", 99), ("order", 63)):
            if cell.get(k):
                if not (cell[k].isdigit() and int(cell[k]) <= hi):
                    err.append("%s %r is not 0-%d" % (k, cell[k], hi))
                else:
                    nums[k] = int(cell[k])
                if src is None and pid not in slot:
                    err.append("player %d is in no squad, so has no %s" % (pid, k))
        errors += ["line %d: %s" % (ln, e) for e in err]
        todo.append((pid, src, club, name, vals, nums))

    new = [t for t in todo if t[1] is not None]
    if len(index) + len(new) > cap:
        errors.append("%d new players would make %d, over the cap of %d (see --cap)"
                      % (len(new), len(index) + len(new), cap))
    if errors:
        raise SystemExit("nothing written:\n  " + "\n  ".join(errors))

    before = bytes(players)
    eid = max(u32(assigns, i * A_REC + A_EID) for i in range(len(assigns) // A_REC)) + 1
    for pid, src, club, name, vals, nums in todo:
        if src is not None:
            s = index[src]
            rec = bytearray(before[s:s + P_REC])
            rec[P_ID:P_ID + 4] = pid.to_bytes(4, "little")
            index[pid] = len(players)
            players += rec
            squad = [u32(assigns, i * A_REC + A_PACK) for i in range(len(assigns) // A_REC)
                     if u32(assigns, i * A_REC + A_TID) == club]
            taken = {p & SHIRT_MASK for p in squad}
            shirt = nums.get("shirt") or next(n for n in range(1, 100) if n not in taken)
            order = max(((p & ORDER_MASK) >> ORDER_SHIFT for p in squad), default=-1) + 1
            e = bytearray(A_REC)
            e[A_EID:A_EID + 4] = eid.to_bytes(4, "little")
            e[A_PID:A_PID + 4] = pid.to_bytes(4, "little")
            e[A_TID:A_TID + 4] = club.to_bytes(4, "little")
            e[A_PACK:A_PACK + 4] = (order << ORDER_SHIFT | shirt).to_bytes(4, "little")
            slot[pid] = len(assigns)
            assigns += e
            eid += 1
            print("new player %d at club %d, shirt %d, squad order %d" % (pid, club, shirt, order))
        o = index[pid]
        rec = bytearray(players[o:o + P_REC])
        for n, v in vals.items():
            setf(rec, n, v)
        if name and name != cstr(rec[P_NAME:P_NAME + P_NAME_LEN]).strip():
            nm = name.encode("utf-8")
            for k in range(P_NAME_SLOTS):
                at = P_NAME + k * P_NAME_LEN
                rec[at:at + P_NAME_LEN] = nm + bytes(P_NAME_LEN - len(nm))
        players[o:o + P_REC] = rec
        if nums and pid in slot:
            at = slot[pid] + A_PACK
            pack = u32(assigns, at)
            if "shirt" in nums:
                pack = pack & ~SHIRT_MASK | nums["shirt"]
            if "order" in nums:
                pack = pack & ~ORDER_MASK | nums["order"] << ORDER_SHIFT
            assigns[at:at + 4] = pack.to_bytes(4, "little")

    # squad orders must stay distinct inside a club, or two players claim one place
    touched = {u32(assigns, slot[t[0]] + A_TID) for t in todo if t[0] in slot}
    seen, clash = {}, []
    for i in range(len(assigns) // A_REC):
        k = (u32(assigns, i * A_REC + A_TID), (u32(assigns, i * A_REC + A_PACK) & ORDER_MASK) >> ORDER_SHIFT)
        if k[0] not in touched:
            continue
        if k in seen:
            clash.append("club %d: players %d and %d both have squad order %d"
                         % (k[0], seen[k], u32(assigns, i * A_REC + A_PID), k[1]))
        seen[k] = u32(assigns, i * A_REC + A_PID)
    if clash:
        raise SystemExit("nothing written:\n  " + "\n  ".join(clash[:20]))

    for path, raw in ((ppath, players), (apath, assigns)):
        if not os.path.exists(path + ".bak"):
            shutil.copyfile(path, path + ".bak")
        open(path, "wb").write(pesdb.wesys_pack(bytes(raw)))
    print("%d players changed, %d of them new; %d players in all (cap %d)"
          % (len(todo), len(new), len(index), cap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
