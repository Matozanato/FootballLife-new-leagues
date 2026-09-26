r"""python rename.py --root <world> --list
   python rename.py --root <world> --names names.csv
   python rename.py --root <world> --managers managers.csv

Rename clubs in a world built by mkworld.py (or any Sider livecpk root that carries
common\etc\pesdb\Team.bin).

Team.bin is packed, so a hex editor cannot change it directly; this unpacks it, rewrites the
two strings a club record carries -- the name at +0x170 (up to 69 bytes of UTF-8) and the
three-letter abbreviation at +0x372 -- and packs it again. Nothing else in the record is
touched, so squads, kits, competitions and ids stay as they were.

--list prints every club in the file: team id, abbreviation, name, and the club's manager when
the world has a Coach.bin. Use it to find the ids.

--names takes a CSV file, one club per line, no header:

    72318,Dinamo Example,DIN
    FL 0002,Hajduk Example,HAJ
    FL 0003,Only The Name Changes

The first column is either the team id or the club's current name, exactly as --list prints
it. The third column is optional; without it the abbreviation is left alone. Lines starting
with # are skipped. A club named in the file that is not found stops the run before anything
is written, so a typo never produces a half-renamed world.

--managers renames the clubs' managers instead, in the world's Coach.bin (mkworld.py writes
one; for an older world run mkcoaches.py first). Same layout, two columns:

    72318,Ivan Example
    FL 0002,Marko Example

The first column names the club, as above; the manager is whoever that club employs (the id
at +0x00 of its Team.bin record), and both copies of the name in the Coach record (+0x08 and
+0x36, up to 45 bytes) are rewritten. A manager who also works at another club -- a shipped
club's, say -- is refused, because renaming him would rename him there too.

The original file is kept as Team.bin.bak (Coach.bin.bak) the first time. Afterwards, if the game has an
Edit save (Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\EDIT00000000), move
it aside and let the game write a fresh one -- an Edit save made before the change is read
instead of the data files and will show the old names.
"""
import csv, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb

T_REC = 1532
T_ID = 0x08
T_NAME, T_NAME_LEN = 0x170, 0x46
T_ABBR, T_ABBR_LEN = 0x372, 3
T_COACH = 0x00
C_REC, C_ID = 100, 0x00
C_NAMES, C_NAME_LEN = (0x08, 0x36), 46


def cstr(b):
    return b.split(b"\x00", 1)[0].decode("utf-8", "replace")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    root = get("--root")
    if not root:
        raise SystemExit(__doc__)
    path = os.path.join(root, "common", "etc", "pesdb", "Team.bin")
    if not os.path.exists(path):
        raise SystemExit("no Team.bin at " + path)
    raw = bytearray(pesdb.wesys_unpack(open(path, "rb").read()))
    if len(raw) % T_REC:
        raise SystemExit("Team.bin is %d bytes, not a whole number of %d-byte records" % (len(raw), T_REC))
    n = len(raw) // T_REC
    recs = []
    for i in range(n):
        o = i * T_REC
        recs.append((o, int.from_bytes(raw[o + T_ID:o + T_ID + 4], "little"),
                     cstr(raw[o + T_NAME:o + T_NAME + T_NAME_LEN]),
                     cstr(raw[o + T_ABBR:o + T_ABBR + T_ABBR_LEN])))
    coach_of = {tid: int.from_bytes(raw[o + T_COACH:o + T_COACH + 4], "little")
                for o, tid, _, _ in recs}

    cpath = os.path.join(root, "common", "etc", "pesdb", "Coach.bin")
    craw = cdata = None
    coach_at = {}
    if os.path.exists(cpath):
        craw = open(cpath, "rb").read()
        cdata = bytearray(pesdb.wesys_unpack(craw))
        coach_at = {int.from_bytes(cdata[i + C_ID:i + C_ID + 4], "little"): i
                    for i in range(0, len(cdata) - C_REC + 1, C_REC)}

    if "--list" in a:
        for _, tid, name, abbr in recs:
            ci = coach_at.get(coach_of[tid])
            mgr = ("  (manager: %s)" % cstr(cdata[ci + C_NAMES[0]:ci + C_NAMES[0] + C_NAME_LEN])
                   if ci is not None else "")
            print("%6d  %-3s  %s%s" % (tid, abbr, name, mgr))
        print("%d clubs" % n)
        return 0

    managers = get("--managers")
    names = get("--names")
    if not names and not managers:
        raise SystemExit("give --list, --names FILE or --managers FILE")
    by_id = {tid: o for o, tid, _, _ in recs}
    by_name = {}
    for o, _, name, _ in recs:
        by_name.setdefault(name, []).append(o)

    if managers:
        return rename_managers(managers, recs, by_id, by_name, coach_of, coach_at, cdata, craw,
                               cpath)

    todo, errors = [], []
    with open(names, newline="", encoding="utf-8-sig") as f:
        for ln, row in enumerate(csv.reader(f), 1):
            if not row or not row[0].strip() or row[0].lstrip().startswith("#"):
                continue
            key = row[0].strip()
            new = row[1].strip() if len(row) > 1 else ""
            abbr = row[2].strip() if len(row) > 2 else ""
            if not new:
                errors.append("line %d: no new name" % ln); continue
            if len(new.encode("utf-8")) > T_NAME_LEN - 1:
                errors.append("line %d: %r is longer than %d bytes" % (ln, new, T_NAME_LEN - 1)); continue
            if abbr and not (len(abbr) == T_ABBR_LEN and abbr.isascii() and abbr.isalnum()):
                errors.append("line %d: abbreviation %r is not three plain letters or digits" % (ln, abbr)); continue
            if key.isdigit() and int(key) in by_id:
                offs = [by_id[int(key)]]
            elif key in by_name:
                offs = by_name[key]
                if len(offs) > 1:
                    errors.append("line %d: %d clubs are named %r -- use the team id" % (ln, len(offs), key)); continue
            else:
                errors.append("line %d: no club %r" % (ln, key)); continue
            todo.append((offs[0], new, abbr))
    if errors:
        raise SystemExit("nothing written:\n  " + "\n  ".join(errors))

    for o, new, abbr in todo:
        nm = new.encode("utf-8")
        raw[o + T_NAME:o + T_NAME + T_NAME_LEN] = nm + bytes(T_NAME_LEN - len(nm))
        if abbr:
            raw[o + T_ABBR:o + T_ABBR + T_ABBR_LEN] = abbr.upper().encode("ascii")
    if not os.path.exists(path + ".bak"):
        shutil.copyfile(path, path + ".bak")
    open(path, "wb").write(pesdb.wesys_pack(bytes(raw)))
    print("renamed %d clubs in %s" % (len(todo), path))
    return 0


def rename_managers(csvfile, recs, by_id, by_name, coach_of, coach_at, cdata, craw, cpath):
    if cdata is None:
        raise SystemExit("no Coach.bin at %s -- run mkcoaches.py first (see docs/faq.md)" % cpath)
    tid_at = {o: tid for o, tid, _, _ in recs}
    clubs_of = {}
    for tid, k in coach_of.items():
        clubs_of.setdefault(k, []).append(tid)
    todo, errors = [], []
    with open(csvfile, newline="", encoding="utf-8-sig") as f:
        for ln, row in enumerate(csv.reader(f), 1):
            if not row or not row[0].strip() or row[0].lstrip().startswith("#"):
                continue
            key = row[0].strip()
            new = row[1].strip() if len(row) > 1 else ""
            if not new:
                errors.append("line %d: no new name" % ln); continue
            if len(new.encode("utf-8")) > C_NAME_LEN - 1:
                errors.append("line %d: %r is longer than %d bytes" % (ln, new, C_NAME_LEN - 1)); continue
            if key.isdigit() and int(key) in by_id:
                tid = int(key)
            elif key in by_name and len(by_name[key]) == 1:
                tid = tid_at[by_name[key][0]]
            elif key in by_name:
                errors.append("line %d: %d clubs are named %r -- use the team id" % (ln, len(by_name[key]), key)); continue
            else:
                errors.append("line %d: no club %r" % (ln, key)); continue
            k = coach_of[tid]
            if k not in coach_at:
                errors.append("line %d: club %d names manager %d, who is not in Coach.bin -- run mkcoaches.py" % (ln, tid, k)); continue
            others = [t for t in clubs_of[k] if t != tid]
            if others:
                errors.append("line %d: club %d's manager also manages club %s" % (ln, tid, others[0])); continue
            todo.append((coach_at[k], new))
    if errors:
        raise SystemExit("nothing written:\n  " + "\n  ".join(errors))

    for i, new in todo:
        nm = new.encode("utf-8")
        for off in C_NAMES:
            cdata[i + off:i + off + C_NAME_LEN] = nm + bytes(C_NAME_LEN - len(nm))
    if not os.path.exists(cpath + ".bak"):
        shutil.copyfile(cpath, cpath + ".bak")
    open(cpath, "wb").write(pesdb.wesys_pack(bytes(cdata), craw[:3]))
    print("renamed %d managers in %s" % (len(todo), cpath))
    return 0


if __name__ == "__main__":
    sys.exit(main())
