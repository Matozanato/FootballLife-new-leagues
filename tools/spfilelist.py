r"""python spfilelist.py [path to spFileList.bin]  -> the download folder's load order

Reads the manifest that lists the archives in the game's `download` folder. Read-only: it
prints and never writes, because the file lives inside the installation.

Why it matters. Everything this project ships so far goes in through sider, as loose files in
a livecpk root. An installer that imports somebody else's league mod will meet the other
mechanism instead -- a `.cpk` dropped into `download` -- and then the question is not "does it
work" but "which of the two copies of Competition.bin wins". This file is where that is
written down.

Format, decoded 2026-09-21 from the shipped file (3,753 bytes, 78 slots, 21 used):

    +0x00  u32   0x64, the same number the data patches carry in their group field
    then 78 records of 0x30 bytes from +0x04, the unused ones all zero:
    +0x00  u32   index: counts DOWN the list, 21 for the first entry, 1 for the last -- so
                  the first entry's index is also how many entries there are
    +0x04  u32   group: 100 for the data patches, 200..700 for the add-ons
    +0x08  u32   tag:   10100, 10200, 10300 -- the three patch generations
    +0x0c  char[0x24]  the archive's file name

Which end wins, measured rather than assumed: the four data patches ship
`CompetitionEntry.bin` with 1,261 rows in `data_s2526`, 1,264 in `b` and 1,317 in `c`, and the
world this project builds on contains the 1,317 version. `data_s2526c` carries the LOWEST index
of the four, 18. So a smaller index is a higher priority, and the add-ons at 1..17 sit above
all four data patches. (Consistent and checkable, but not proof of what the engine does: the
name `spFileList` appears in no binary in the installation, so either the loader builds the
name at runtime or this manifest belongs to the installer rather than the game. Anyone adding
an archive should verify it is read before relying on it.)
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flpaths

HDR, REC = 4, 0x30


def read(path):
    """[(index, group, tag, name)] for the used entries, in file order."""
    d = open(path, "rb").read()
    slots = (len(d) - HDR) // REC
    if slots < 1:
        raise SystemExit("%s is too short to be a file list" % path)
    out = []
    for i in range(slots):
        o = HDR + i * REC
        rec = d[o:o + REC]
        if not any(rec):
            break                      # the list ends at the first empty slot
        idx, group, tag = struct.unpack_from("<III", d, o)
        out.append((idx, group, tag, rec[12:].split(b"\0")[0].decode("latin1")))
    return out, slots


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        flpaths.GAME_DIR, "download", "spFileList.bin")
    if not os.path.isfile(path):
        raise SystemExit("no file list at %s\nSet FL26_DIR, or pass the path." % path)
    rows, slots = read(path)
    print("%s: %d archives listed, %d slots in the file" % (path, len(rows), slots))
    print("  index  group    tag   archive                        on disk")
    folder = os.path.dirname(path)
    for idx, group, tag, name in rows:
        p = os.path.join(folder, name)
        size = "%.1f MB" % (os.path.getsize(p) / 1048576.0) if os.path.isfile(p) else "MISSING"
        print("  %5d  %5d  %5d   %-30s %s" % (idx, group, tag, name, size))

    listed = {r[3] for r in rows}
    extra = sorted(f for f in os.listdir(folder)
                   if f.lower().endswith(".cpk") and f not in listed)
    if extra:
        print("\narchives present but not listed (%d):" % len(extra))
        for f in extra:
            print("   " + f)
        print("whether the game loads these anyway is the open question in this tool's notes.")
    else:
        print("\nevery .cpk in the folder is listed.")
    print("\nsmaller index = higher priority (measured, see the notes at the top).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
