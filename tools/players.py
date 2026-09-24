r"""python players.py --root <world> --list [--club <team id or name>]
   python players.py --root <world> --edit edits.csv

Edit the players of a world built by mkworld.py and mkplayers.py, without the game's Edit mode
(which cannot reach clubs in a league of our own -- see docs/faq.md).

mkplayers.py makes every squad by cloning one shipped squad and renaming it, so every new
club starts with the same players under placeholder names.  This changes three things per
player, all of which the file format is known for:

  name         the four name slots of Player.bin (+0x44, 0x3d bytes each: full name, name on
               the shirt, name on screen, printed name), all set to the new name
  like         a player id to copy the playing side from: position, abilities, skills,
               playing style -- everything in the record except the player's own id and
               names.  This is what mkplayers.py already does when it clones a squad, so a
               copied record is one the game has already accepted.  The source can be any
               player in the same Player.bin, including the shipped ones
  shirt        the shirt number, 1..99, in PlayerAssignment.bin (bits 0-9 of +0x0c)

To set single fields -- any ability, position, height, foot, skill -- or to create new
players, use playeredit.py, which knows every field of the record (docs/player-record.md).

--list prints player id, club id, shirt number and name, one player per line.  --club
limits it to one club (its team id, or its name exactly as rename.py --list prints it).

--edit takes a CSV file with a header line and these columns, any of which but the first
may be left empty:

    player,name,like,shirt
    100000,Ivan Example,,9
    FL P00002,,40123,
    100002,Marko Example,40123,10

The first column is the player id or the player's current name; a name that several players
share must be given as an id.  A line that names a player that is not there, a source that is not
there, a name longer than 60 bytes or a shirt number outside 1..99 stops the run before
anything is written.  The original files are kept as .bak the first time.
"""
import csv, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb

P_REC = 312
P_ID = 0x08
P_NAME, P_NAME_LEN, P_NAME_SLOTS = 0x44, 0x3d, 4

A_REC = 16
A_PID, A_TID, A_PACK = 0x04, 0x08, 0x0c
SHIRT_MASK = 0x3ff

T_REC, T_ID = 1532, 0x08
T_NAME, T_NAME_LEN = 0x170, 0x46


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def cstr(b):
    return b.split(b"\x00", 1)[0].decode("utf-8", "replace")


def load(db, n):
    p = os.path.join(db, n)
    if not os.path.exists(p):
        raise SystemExit("no %s at %s" % (n, p))
    raw = bytearray(pesdb.wesys_unpack(open(p, "rb").read()))
    return p, raw


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    root = get("--root")
    if not root:
        raise SystemExit(__doc__)
    db = os.path.join(root, "common", "etc", "pesdb")
    ppath, players = load(db, "Player.bin")
    apath, assigns = load(db, "PlayerAssignment.bin")
    if len(players) % P_REC or len(assigns) % A_REC:
        raise SystemExit("Player.bin or PlayerAssignment.bin is not a whole number of records")

    index = {u32(players, i * P_REC + P_ID): i * P_REC for i in range(len(players) // P_REC)}
    slot = {}                                   # player id -> offset of its assignment
    for i in range(len(assigns) // A_REC):
        slot.setdefault(u32(assigns, i * A_REC + A_PID), i * A_REC)
    name_of = lambda o: cstr(players[o + P_NAME:o + P_NAME + P_NAME_LEN])

    if "--list" in a:
        club = get("--club")
        want = None
        if club is not None:
            if club.isdigit():
                want = int(club)
            else:
                _, teams = load(db, "Team.bin")
                hits = [u32(teams, i * T_REC + T_ID) for i in range(len(teams) // T_REC)
                        if cstr(teams[i * T_REC + T_NAME:i * T_REC + T_NAME + T_NAME_LEN]) == club]
                if len(hits) != 1:
                    raise SystemExit("%d clubs are named %r -- use the team id" % (len(hits), club))
                want = hits[0]
        n = 0
        for pid, o in index.items():
            s = slot.get(pid)
            tid = u32(assigns, s + A_TID) if s is not None else None
            if want is not None and tid != want:
                continue
            shirt = u32(assigns, s + A_PACK) & SHIRT_MASK if s is not None else None
            print("%7d  %7s  %3s  %s" % (pid, "-" if tid is None else tid,
                                         "-" if shirt is None else shirt, name_of(o)))
            n += 1
        print("%d players" % n)
        return 0

    edits = get("--edit")
    if not edits:
        raise SystemExit("give --list or --edit FILE")
    by_name = {}
    for pid, o in index.items():
        by_name.setdefault(name_of(o), []).append(pid)

    todo, errors = [], []
    with open(edits, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows or [c.strip().lower() for c in rows[0][:1]] != ["player"]:
        raise SystemExit("the first line must be the header: player,name,like,shirt")
    for ln, row in enumerate(rows[1:], 2):
        row = [c.strip() for c in row] + [""] * 4
        key, new, like, shirt = row[:4]
        if not key or key.startswith("#"):
            continue
        if key.isdigit() and int(key) in index:
            pid = int(key)
        elif len(by_name.get(key, [])) == 1:
            pid = by_name[key][0]
        elif key in by_name:
            errors.append("line %d: %d players are named %r -- use the player id"
                          % (ln, len(by_name[key]), key)); continue
        else:
            errors.append("line %d: no player %r" % (ln, key)); continue
        if new and len(new.encode("utf-8")) > P_NAME_LEN - 1:
            errors.append("line %d: %r is longer than %d bytes" % (ln, new, P_NAME_LEN - 1)); continue
        src = None
        if like:
            if not (like.isdigit() and int(like) in index):
                errors.append("line %d: no player with id %r to copy from" % (ln, like)); continue
            src = int(like)
        num = None
        if shirt:
            if not (shirt.isdigit() and 1 <= int(shirt) <= 99):
                errors.append("line %d: shirt number %r is not 1..99" % (ln, shirt)); continue
            if pid not in slot:
                errors.append("line %d: player %d is in no squad, so has no shirt number" % (ln, pid)); continue
            num = int(shirt)
        if not (new or src is not None or num is not None):
            errors.append("line %d: nothing to change" % ln); continue
        todo.append((pid, new, src, num))
    if errors:
        raise SystemExit("nothing written:\n  " + "\n  ".join(errors))

    # copies read the file as it was, so a line copying from a player another line edits
    # gets the original, whatever order the lines are in
    before = bytes(players)
    for pid, new, src, num in todo:
        o = index[pid]
        if src is not None:
            s = index[src]
            rec = bytearray(before[s:s + P_REC])
            rec[P_ID:P_ID + 4] = players[o + P_ID:o + P_ID + 4]
            rec[P_NAME:P_NAME + P_NAME_LEN * P_NAME_SLOTS] = \
                players[o + P_NAME:o + P_NAME + P_NAME_LEN * P_NAME_SLOTS]
            players[o:o + P_REC] = rec
        if new:
            nm = new.encode("utf-8")
            for k in range(P_NAME_SLOTS):
                at = o + P_NAME + k * P_NAME_LEN
                players[at:at + P_NAME_LEN] = nm + bytes(P_NAME_LEN - len(nm))
        if num is not None:
            at = slot[pid] + A_PACK
            v = (u32(assigns, at) & ~SHIRT_MASK) | num
            assigns[at:at + 4] = v.to_bytes(4, "little")

    for path, raw in ((ppath, players), (apath, assigns)):
        if not os.path.exists(path + ".bak"):
            shutil.copyfile(path, path + ".bak")
        open(path, "wb").write(pesdb.wesys_pack(bytes(raw)))
    print("edited %d players in %s" % (len(todo), db))
    return 0


if __name__ == "__main__":
    sys.exit(main())
