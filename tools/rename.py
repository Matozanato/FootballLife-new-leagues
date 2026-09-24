r"""python rename.py --root <world> --list
   python rename.py --root <world> --names names.csv

Rename clubs in a world built by mkworld.py (or any Sider livecpk root that carries
common\etc\pesdb\Team.bin).

Team.bin is packed, so a hex editor cannot change it directly; this unpacks it, rewrites the
two strings a club record carries -- the name at +0x170 (up to 69 bytes of UTF-8) and the
three-letter abbreviation at +0x372 -- and packs it again. Nothing else in the record is
touched, so squads, kits, competitions and ids stay as they were.

--list prints every club in the file: team id, abbreviation, name. Use it to find the ids.

--names takes a CSV file, one club per line, no header:

    72318,Dinamo Example,DIN
    FL 0002,Hajduk Example,HAJ
    FL 0003,Only The Name Changes

The first column is either the team id or the club's current name, exactly as --list prints
it. The third column is optional; without it the abbreviation is left alone. Lines starting
with # are skipped. A club named in the file that is not found stops the run before anything
is written, so a typo never produces a half-renamed world.

The original file is kept as Team.bin.bak the first time. Afterwards, if the game has an
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

    if "--list" in a:
        for _, tid, name, abbr in recs:
            print("%6d  %-3s  %s" % (tid, abbr, name))
        print("%d clubs" % n)
        return 0

    names = get("--names")
    if not names:
        raise SystemExit("give --list or --names FILE")
    by_id = {tid: o for o, tid, _, _ in recs}
    by_name = {}
    for o, _, name, _ in recs:
        by_name.setdefault(name, []).append(o)

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


if __name__ == "__main__":
    sys.exit(main())
