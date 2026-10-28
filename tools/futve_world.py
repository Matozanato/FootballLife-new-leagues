r"""python futve_world.py [--game <folder>] [--base <pesdb>] [--world <fl26world.txt>]
                        [--out <folder>] [--phase 1|2|all] [--dry]

Rebuild the Liga FUTVE Apertura play-off in a world's tables as a league play-off: two groups of
four and a final, for the two in-game tests of this branch (see docs/developers/fork/futve-playoff.md).

  phase 1   groups of four, then a knockout of four (the old progression): the group stage on the
            days it is given, the knockout on free days after it. It only shows that a group stage
            filled the day after a split phase ends gets its matches.
  phase 2   the final: only the winner of each group goes through, a two-club one-match knockout
            copied from the Belgium Super Cup, on the day given in the world file. The better
            placed club of the regular phase is put first by the DLL (at home in the record).

The cup keeps its ids -- the competition and regulations the Build gave it -- and only its own
rows are replaced: the competition row, the regulation rows and the entry rows of that one cid.
Everything else in the three tables comes back untouched, and the Clausura cup is never named.

The world file: the Apertura line is replaced by one with the new options; the rest of the file
is copied line for line. Output goes to <out>/world-phase1 and <out>/world-phase2, each with
common\etc\pesdb and fl26world.txt, ready for tools/futve_test.py.

  --game    the game folder (default: FL26_DIR), whose world is copied to the staging folders
  --base    a pesdb folder (default: <game>\SiderAddons\livecpk\_FL26MyWorld\common\etc\pesdb)
  --world   the world file the loader reads (default: <game>\SiderAddons\modules\fl26world.txt)
  --out     where the staging folders go (default: out/futve)
  --dry     print the ids, the line and the plan, write nothing

Nothing of the game is modified. Exit code 1 with a message when the cup, its ids or the shipped
super cup cannot be found.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M
import mkworld as W

BAD_REG = W.BAD_REG

NAME = "Liga FUTVE Apertura Playoffs"
CODE = "FL_011_APO"
ENTRIES = "191:1,191:4,191:5,191:8,191:2,191:3,191:6,191:7"
CONF = 4                       # CONMEBOL
REGION = 29                    # the world's Venezuela
GROUP_DAYS = "3,5,7,9,11,13"
FINAL_DAY = 15
KO_DAYS_4 = "18,21,25,28,32,35,39"
SUPER_CUP = "BELGIUM_SUPER_CUP"
REPLICAS = (1024, 2048)        # the game's rule for a group cup's rows


def u16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def rows(b, size):
    return [b[i:i + size] for i in range(0, len(b), size)]


def rid(r):
    return u16(r, M.R_ID)


def like_reg(comp, regs, code):
    """the regulation id of the shipped competition coded `code` (its first row), or None"""
    row = M.find_code(comp, code)
    if row is None:
        return None
    cid = comp[row * M.COMP + M.CID_OFF]
    for i in range(len(regs) // M.REG):
        if regs[i * M.REG + M.R_CID] == cid:
            return u16(regs, i * M.REG + M.R_ID)
    return None


def find_cup_line(lines):
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("ccup ") and s.endswith("name=" + NAME):
            return i, s
    return None, None


def cup_ids(line):
    """(reg, ko, groups, fill, national) of a ccup line"""
    reg = int(line.split()[1])
    m = re.search(r"\bko=(\d+)", line)
    g = re.search(r"\bgroups=(\d+)", line)
    f = re.search(r"\bfill=(\d+)", line)
    n = re.search(r"\bnational=(\d+)", line)
    ko = int(m.group(1)) if m else 0
    groups = int(g.group(1)) if g else 0
    return reg, ko, groups, int(f.group(1)) if f else 3, int(n.group(1)) if n else 1


def free_ko(used, reg, bad):
    """the knockout's id: the next one after the cup's own rows, else the first free one the game
    does not reassign (mkworld's BAD_REG)"""
    for cand in (reg + 2, reg + 3, reg + 4):
        if cand < 1024 and cand not in used and cand not in bad:
            return cand
    for cand in range(176, 1024):
        if cand == reg or cand in used or cand in bad:
            continue
        if cand not in (reg + REPLICAS[0], reg + REPLICAS[1]):
            return cand
    return None


def plan(base, world, dry, tmp_root):
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    C, R, E = rows(comp, M.COMP), rows(regs, M.REG), rows(ents, M.ENT)
    with open(world, "r", encoding="utf-8", errors="replace", newline="") as f:
        raw = f.read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()
    li, line = find_cup_line(lines)
    if li is None:
        raise SystemExit("no ccup line named %r in %s" % (NAME, world))
    reg, ko, groups, fill, national = cup_ids(line)
    if groups and ko and ko != reg:
        pass                                     # an already rebuilt world: keep its knockout id
    elif ko != reg:
        raise SystemExit("cup %d: its line names ko %d but it is no group cup" % (reg, ko))
    row = [r for r in R if rid(r) == reg]
    if len(row) != 1:
        raise SystemExit("no regulation %d in %s" % (reg, base))
    cid = row[0][M.R_CID]
    if not groups:
        ko = 0                                  # picked below, once the removed rows are known
    # the cup's rows go, the rest stays
    C2 = [c for c in C if c[M.CID_OFF] != cid]
    R2 = [r for r in R if r[M.R_CID] != cid]
    E2 = [e for e in E if e[M.E_CID] != cid]
    used = {rid(r) for r in R2}
    if reg in used:
        raise SystemExit("regulation %d is still used after removing cid %d" % (reg, cid))
    for rep in REPLICAS:
        if reg + rep in used:
            raise SystemExit("the group row %d of regulation %d is taken by another competition"
                             % (reg + rep, reg))
    if not ko:
        ko = free_ko(used, reg, BAD_REG)
        if ko is None:
            raise SystemExit("no free knockout id for the play-off")
    elif ko in used:
        raise SystemExit("knockout %d is taken by another competition" % ko)
    bel = like_reg(comp, regs, SUPER_CUP)
    if bel is None:
        raise SystemExit("this world has no %s to shape a one-match final" % SUPER_CUP)
    # the base mkccup builds from: the same world without this cup's rows
    os.makedirs(tmp_root, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="base-", dir=tmp_root)
    if not dry:
        M.write_tables(tmp, b"".join(C2), b"".join(R2), b"".join(E2))
    base2 = os.path.join(tmp, "common", "etc", "pesdb")
    specs, worlds = {}, {}
    for n in (1, 2):
        spec = "%s|%s|%d|%d|%d|2|%s|%d|%d" % (NAME, CODE, cid, reg, ko, ENTRIES, CONF, REGION)
        if n == 2:
            spec += "||2|%d" % bel
        line2 = ("ccup %d ko=%d groups=2 entry=%s fill=%d national=%d days=%s gdays=%s%s name=%s"
                 % (reg, ko, ENTRIES, fill, national, FINAL_DAY if n == 2 else KO_DAYS_4,
                    GROUP_DAYS, " adv=1 kolike=%d" % bel if n == 2 else "", NAME))
        specs[n], worlds[n] = spec, line2
    return {"cid": cid, "reg": reg, "ko": ko, "bel": bel, "comp": comp, "regs": regs,
            "ents": ents, "C2": C2, "R2": R2, "E2": E2, "base2": base2, "tmp": tmp,
            "lines": lines, "nl": nl, "li": li, "specs": specs, "worlds": worlds}


def build(p, out, n):
    dest = os.path.join(out, "world-phase%d" % n)
    os.makedirs(dest, exist_ok=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, "mkccup.py"),
                        "--base", p["base2"], "--out", dest, "--cup", p["specs"][n]],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("mkccup failed for phase %d:\n%s\n%s" % (n, r.stdout, r.stderr))
    for l in r.stdout.splitlines():
        if l.strip():
            print("  " + l.strip())
    lines = list(p["lines"])
    lines[p["li"]] = p["worlds"][n]
    with open(os.path.join(dest, "fl26world.txt"), "w", encoding="utf-8", newline="") as f:
        f.write(p["nl"].join(lines) + p["nl"])
    # the rows the DLL and the tests expect. The group rows are copies of the Libertadores
    # replicas and keep their own team byte (the runtime counts the clubs); the master and the
    # knockout are the rows whose field matters.
    db = os.path.join(dest, "common", "etc", "pesdb")
    comp, regs = M.load(db, "Competition.bin"), M.load(db, "CompetitionRegulation.bin")
    R = rows(regs, M.REG)
    want = {p["reg"]: (2, 8, 2), p["ko"]: (3, 2 if n == 2 else 4, None)}
    for rid_, (typ, clubs, groups) in want.items():
        got = [x for x in R if rid(x) == rid_]
        if len(got) != 1:
            raise SystemExit("phase %d: regulation %d missing from the built world" % (n, rid_))
        r0 = got[0]
        if r0[M.R_CID] != p["cid"] or r0[M.R_TYPE] != typ or r0[M.R_TEAMS] & 0x3f != clubs:
            raise SystemExit("phase %d: regulation %d is cid %d, type %d, %d clubs; wanted %d/%d/%d"
                             % (n, rid_, r0[M.R_CID], r0[M.R_TYPE], r0[M.R_TEAMS] & 0x3f,
                                p["cid"], typ, clubs))
        if groups is not None and r0[0x10] & 0x1f != groups:
            raise SystemExit("phase %d: regulation %d names %d group(s), not %d"
                             % (n, rid_, r0[0x10] & 0x1f, groups))
    for rep in (p["reg"] + 1024, p["reg"] + 2048):
        got = [x for x in R if rid(x) == rep]
        if len(got) != 1 or got[0][M.R_CID] != p["cid"] or got[0][M.R_TYPE] != 2:
            raise SystemExit("phase %d: its group row %d is missing or not this cup's" % (n, rep))
    if not any(c[M.CID_OFF] == p["cid"] for c in rows(comp, M.COMP)):
        raise SystemExit("phase %d: competition %d missing from the built world" % (n, p["cid"]))
    print("  world-phase%d: cid %d, groups %d (+%d, +%d), knockout %d (%d clubs), line written"
          % (n, p["cid"], p["reg"], p["reg"] + 1024, p["reg"] + 2048, p["ko"], 2 if n == 2 else 4))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    ap.add_argument("--base")
    ap.add_argument("--world")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out", "futve"))
    ap.add_argument("--phase", choices=("1", "2", "all"), default="all")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    base = a.base or os.path.join(a.game or "", "SiderAddons", "livecpk", "_FL26MyWorld",
                                  "common", "etc", "pesdb")
    world = a.world or os.path.join(a.game or "", "SiderAddons", "modules", "fl26world.txt")
    if not os.path.isdir(base) or not os.path.isfile(world):
        raise SystemExit("no world found (base %s, world %s); pass --game or FL26_DIR" % (base, world))
    p = plan(base, world, a.dry, os.path.join(a.out, "tmp"))
    print("Liga FUTVE Apertura Playoffs: cid %d, regulation %d, knockout %d, one-match final as %s"
          % (p["cid"], p["reg"], p["ko"], p["bel"]))
    print("  groups %d, +%d, +%d; entries %s" % (p["reg"], p["reg"] + 1024, p["reg"] + 2048, ENTRIES))
    for n in (1, 2):
        print("  phase %d: %s" % (n, p["worlds"][n]))
    if a.dry:
        print("dry run: nothing written")
        return 0
    M.write_tables(p["base2"], b"".join(p["C2"]), b"".join(p["R2"]), b"".join(p["E2"]))
    print("  base for mkccup: %s" % p["base2"])
    phases = (1, 2) if a.phase == "all" else (int(a.phase),)
    for n in phases:
        build(p, a.out, n)
    shutil.rmtree(p["tmp"], ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
