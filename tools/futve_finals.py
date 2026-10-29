r"""python tools/futve_finals.py [--game <folder>] [--base <pesdb>] [--world <fl26world.txt>]
                                 [--out <folder>] [--dry]

Build the Liga FUTVE finals block in a staged world: the Apertura and Clausura play-offs become two
groups of four, each sending its two group winners to a final that is a competition of its own
(142 Final del Apertura, 143 Final del Clausura), and the Final del FUTVE (144) between the two
final winners (regulation 263, day 166).

The competition ids are the world's next free ones (leaguebuilder.free_comp_ids): the Liga FUTVE
takes 130-135, 136 is the UEFA Conference League's reserved id, 137-141 are Scotland's and Saudi
Arabia's, so the finals take 142, 143 and 144 -- with the 134 row's region (29) and confederation
(4). The knockout regulations stay the 16-bit 261/262/263.

The Apertura and Clausura cups keep their competition ids (134/135) and their group masters
(259/260); the knockout regulations (261/262) move to the new final competitions, so the group
competitions keep only the group rows. The final competitions' rows are the FA Cup's knockout row
(one match a round) cut to two clubs; their names are written in all twenty regulation slots and
their two entry rows exist (placeholder clubs; fl26swiss.dll rewrites them when it fills the
final). The Final del FUTVE is a 2-club straight knockout of its own (regulation 263), also from the
FA Cup row.

The world file gets the three ccup lines, the Apertura/Clausura ones replacing the old ones and the
Final del FUTVE's inserted after the Clausura one; every other line is copied untouched, in the
source's line endings. Output goes to <out>/world-finals, with common\etc\pesdb and fl26world.txt.

The base is the live world (or --base/--world); nothing of the game is modified.

  --game    the game folder (default FL26_DIR), whose world is copied
  --base    the pesdb folder (default <game>\SiderAddons\livecpk\_FL26MyWorld\common\etc\pesdb)
  --world   the loader's world file (default <game>\SiderAddons\modules\fl26world.txt)
  --out     the staging root (default out/futve); the world goes to <out>/world-finals
  --dry     print the plan and write nothing

  python tools/futve_finals.py --game "G:\Games\SP Football Life 2026"
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import mkleague as M
import futve_world as F

AP_NAME = "Liga FUTVE Apertura Playoffs"
AP_CODE = "FL_011_APO"
AP_CID, AP_REG, AP_KO = 134, 259, 261
AP_ENTRIES = "191:1,191:4,191:5,191:8,191:2,191:3,191:6,191:7"
AP_DAYS = "3,5,7,9,11,13"
AP_FINAL = 15

CL_NAME = "Liga FUTVE Clausura Playoffs"
CL_CODE = "FL_011_CPO"
CL_CID, CL_REG, CL_KO = 135, 260, 262
CL_ENTRIES = "192:1,192:4,192:5,192:8,192:2,192:3,192:6,192:7"
CL_DAYS = "145,148,151,154,157,160"
CL_FINAL = 163

FF_NAME = "Final del FUTVE"
FF_CODE = "FL_011_FFU"
FF_CID, FF_REG = 144, 263
FF_ENTRIES = "191:1,192:1"
FF_FINAL = 166
FF_FILL = 0          # 0 = the DLL tries it every tick: its src= champions appear on days 15 and 163

FI_NAME = "Final del Apertura"
FI_CODE = "FL_011_AFI"
FI_CID = 142
FC_NAME = "Final del Clausura"
FC_CODE = "FL_011_CFI"
FC_CID = 143

CONF = 4
REGION = 29
REPLICA_STEP = 1024


def table_rows(data, size):
    return [bytearray(data[i:i + size]) for i in range(0, len(data), size)]


def rid(r):
    return int.from_bytes(r[M.R_ID:M.R_ID + 2], "little")


def find_line(lines, name):
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("ccup ") and s.endswith("name=" + name):
            return i, s
    return None, None


def reg_cid(R, reg):
    hits = [r for r in R if rid(r) == reg]
    if len(hits) != 1:
        raise SystemExit("no unique regulation %d in the base" % reg)
    return hits[0][M.R_CID]


def one_reg(R, reg):
    hits = [r for r in R if rid(r) == reg]
    if len(hits) != 1:
        raise SystemExit("no unique regulation %d in the built world" % reg)
    return hits[0]


def teams_of(E, cid):
    es = sorted((e for e in E if e[M.E_CID] == cid), key=lambda e: e[M.E_ORDER])
    return [int.from_bytes(e[M.E_TEAM:M.E_TEAM + 4], "little") for e in es]


def plan(base, world, dry, tmp_root):
    comp_b, regs_b, ents_b = (M.load(base, n) for n in
                              ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    C, R, E = table_rows(comp_b, M.COMP), table_rows(regs_b, M.REG), table_rows(ents_b, M.ENT)
    with open(world, "r", encoding="utf-8", errors="replace", newline="") as f:
        raw = f.read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()
    li_ap, line_ap = find_line(lines, AP_NAME)
    li_cl, line_cl = find_line(lines, CL_NAME)
    if li_ap is None:
        raise SystemExit("no ccup line named %r in %s" % (AP_NAME, world))
    if li_cl is None:
        raise SystemExit("no ccup line named %r in %s" % (CL_NAME, world))
    ap_reg, _ko, _g, ap_fill, ap_nat = F.cup_ids(line_ap)
    cl_reg, _ko, _g, cl_fill, cl_nat = F.cup_ids(line_cl)
    if ap_reg != AP_REG or cl_reg != CL_REG:
        raise SystemExit("the world's play-offs are regulations %d/%d, not %d/%d"
                         % (ap_reg, cl_reg, AP_REG, CL_REG))
    ap_cid, cl_cid = reg_cid(R, AP_REG), reg_cid(R, CL_REG)
    if ap_cid != AP_CID or cl_cid != CL_CID:
        raise SystemExit("the world's play-offs are competitions %d/%d, not %d/%d"
                         % (ap_cid, cl_cid, AP_CID, CL_CID))
    # the two cups' rows go; the rest of the world stays
    C2 = [c for c in C if c[M.CID_OFF] not in (AP_CID, CL_CID)]
    R2 = [r for r in R if r[M.R_CID] not in (AP_CID, CL_CID)]
    E2 = [e for e in E if e[M.E_CID] not in (AP_CID, CL_CID)]
    used_cid = {c[M.CID_OFF] for c in C2}
    used_reg = {rid(r) for r in R2}
    for cid in (FI_CID, FC_CID, FF_CID):
        if cid in used_cid:
            raise SystemExit("competition %d is taken in the base" % cid)
    for reg in (AP_REG, CL_REG, AP_KO, CL_KO, FF_REG,
                AP_REG + REPLICA_STEP, AP_REG + 2 * REPLICA_STEP,
                CL_REG + REPLICA_STEP, CL_REG + 2 * REPLICA_STEP):
        if reg in used_reg:
            raise SystemExit("regulation %d is taken in the base" % reg)
    shape = F.like_reg(comp_b, regs_b, F.FINAL_SHAPE)
    date_src = F.like_reg(comp_b, regs_b, F.SUPER_CUP)
    if shape is None or date_src is None:
        raise SystemExit("this world has no %s/%s to copy a final's row and calendar"
                         % (F.FINAL_SHAPE, F.SUPER_CUP))
    tpl_ap = next(bytearray(c) for c in C if c[M.CID_OFF] == AP_CID)
    tpl_cl = next(bytearray(c) for c in C if c[M.CID_OFF] == CL_CID)
    os.makedirs(tmp_root, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="finals-base-", dir=tmp_root)
    if not dry:
        M.write_tables(tmp, b"".join(C2), b"".join(R2), b"".join(E2))
    base2 = os.path.join(tmp, "common", "etc", "pesdb")
    # mkccup: the two group cups (their knockout is the final's regulation) and the FUTVE's cup
    ap_spec = "%s|%s|%d|%d|%d|2|%s|%d|%d||2|%d" % (
        AP_NAME, AP_CODE, AP_CID, AP_REG, AP_KO, AP_ENTRIES, CONF, REGION, shape)
    cl_spec = "%s|%s|%d|%d|%d|2|%s|%d|%d||2|%d" % (
        CL_NAME, CL_CODE, CL_CID, CL_REG, CL_KO, CL_ENTRIES, CONF, REGION, shape)
    ff_spec = "%s|%s|%d|%d|%d|0|%s|%d|%d|%d" % (
        FF_NAME, FF_CODE, FF_CID, FF_REG, FF_REG, FF_ENTRIES, CONF, REGION, shape)
    ap_line = ("ccup %d ko=%d groups=2 entry=%s fill=%d national=%d days=%d gdays=%s adv=1 kolike=%d name=%s"
               % (AP_REG, AP_KO, AP_ENTRIES, ap_fill, ap_nat, AP_FINAL, AP_DAYS, date_src, AP_NAME))
    cl_line = ("ccup %d ko=%d groups=2 entry=%s fill=%d national=%d days=%d gdays=%s adv=1 kolike=%d name=%s"
               % (CL_REG, CL_KO, CL_ENTRIES, cl_fill, cl_nat, CL_FINAL, CL_DAYS, date_src, CL_NAME))
    ff_line = ("ccup %d ko=%d groups=0 entry=%s fill=%d national=1 days=%d kolike=%d src=%d,%d name=%s"
               % (FF_REG, FF_REG, FF_ENTRIES, FF_FILL, FF_FINAL, date_src, AP_KO, CL_KO, FF_NAME))
    return {"ap_cid": AP_CID, "cl_cid": CL_CID, "ap_fill": ap_fill, "cl_fill": cl_fill,
            "shape": shape, "date_src": date_src, "C2": C2, "R2": R2, "E2": E2,
            "tpl_ap": tpl_ap, "tpl_cl": tpl_cl, "base2": base2, "tmp": tmp,
            "lines": lines, "nl": nl, "li_ap": li_ap, "li_cl": li_cl,
            "ap_line": ap_line, "cl_line": cl_line, "ff_line": ff_line,
            "ap_spec": ap_spec, "cl_spec": cl_spec, "ff_spec": ff_spec}


def build(p, out):
    dest = os.path.join(out, "world-finals")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest, exist_ok=True)
    cmd = [sys.executable, os.path.join(HERE, "mkccup.py"), "--base", p["base2"], "--out", dest]
    for k in ("ap_spec", "cl_spec", "ff_spec"):
        cmd += ["--cup", p[k]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("mkccup failed:\n%s\n%s" % (r.stdout, r.stderr))
    for l in r.stdout.splitlines():
        if l.strip():
            print("  " + l.strip())
    db = os.path.join(dest, "common", "etc", "pesdb")
    comp_b, regs_b, ents_b = (M.load(db, n) for n in
                              ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    C, R, E = table_rows(comp_b, M.COMP), table_rows(regs_b, M.REG), table_rows(ents_b, M.ENT)
    # the knockout of each group cup belongs to its final competition now
    ap_ko = one_reg(R, AP_KO)
    ap_ko[M.R_CID] = FI_CID
    M.put_names(ap_ko, 0, FI_NAME)
    cl_ko = one_reg(R, CL_KO)
    cl_ko[M.R_CID] = FC_CID
    M.put_names(cl_ko, 0, FC_NAME)
    ff = one_reg(R, FF_REG)
    M.put_names(ff, 0, FF_NAME)
    # the final competitions: the play-offs' competition row with the new id and code
    for tpl, cid, code in ((p["tpl_ap"], FI_CID, FI_CODE), (p["tpl_cl"], FC_CID, FC_CODE)):
        c = bytearray(tpl)
        c[M.CID_OFF] = cid
        M.put(c, M.CODE_OFF, code, M.COMP - M.CODE_OFF)
        C.append(c)
    # their two entry rows (placeholder clubs; the DLL rewrites them): the group winners' slots
    eid = max((int.from_bytes(e[M.E_EID:M.E_EID + 4], "little") for e in E), default=0) + 1
    for cid, tlist in ((FI_CID, teams_of(E, p["ap_cid"])[:2]), (FC_CID, teams_of(E, p["cl_cid"])[:2])):
        for i, t in enumerate(tlist):
            e = bytearray(M.ENT)
            e[M.E_TEAM:M.E_TEAM + 4] = t.to_bytes(4, "little")
            e[M.E_EID:M.E_EID + 4] = eid.to_bytes(4, "little")
            eid += 1
            e[M.E_CID] = cid
            e[M.E_ORDER] = i + 1
            E.append(e)
    M.write_tables(dest, b"".join(C), b"".join(R), b"".join(E))
    # the world file: the two lines replaced, the Final del FUTVE's after the Clausura one
    lines = list(p["lines"])
    lines[p["li_ap"]] = p["ap_line"]
    lines[p["li_cl"]] = p["cl_line"]
    lines.insert(p["li_cl"] + 1, p["ff_line"])
    with open(os.path.join(dest, "fl26world.txt"), "w", encoding="utf-8", newline="") as f:
        f.write(p["nl"].join(lines) + p["nl"])
    verify(dest, p, C, R, E, lines)


def verify(dest, p, C, R, E, lines):
    for cid, code in ((AP_CID, AP_CODE), (CL_CID, CL_CODE), (FI_CID, FI_CODE),
                      (FC_CID, FC_CODE), (FF_CID, FF_CODE)):
        hits = [c for c in C if c[M.CID_OFF] == cid]
        if len(hits) != 1:
            raise SystemExit("competition %d missing (or repeated)" % cid)
        if M.code_of(hits[0]) != code:
            raise SystemExit("competition %d is %r, not %r" % (cid, M.code_of(hits[0]), code))
    for reg, cid, typ, teams in ((AP_REG, AP_CID, 2, 8), (CL_REG, CL_CID, 2, 8),
                                 (AP_KO, FI_CID, 3, 2), (CL_KO, FC_CID, 3, 2),
                                 (FF_REG, FF_CID, 3, 2)):
        r = one_reg(R, reg)
        if r[M.R_CID] != cid or r[M.R_TYPE] != typ or r[M.R_TEAMS] & 0x3f != teams:
            raise SystemExit("regulation %d is cid %d type %d %d clubs; wanted %d/%d/%d"
                             % (reg, r[M.R_CID], r[M.R_TYPE], r[M.R_TEAMS] & 0x3f, cid, typ, teams))
    for reg, cid in ((AP_REG + REPLICA_STEP, AP_CID), (AP_REG + 2 * REPLICA_STEP, AP_CID),
                     (CL_REG + REPLICA_STEP, CL_CID), (CL_REG + 2 * REPLICA_STEP, CL_CID)):
        r = one_reg(R, reg)
        if r[M.R_CID] != cid or r[M.R_TYPE] != 2:
            raise SystemExit("group row %d is not competition %d's" % (reg, cid))
    for reg, name in ((AP_REG, AP_NAME), (CL_REG, CL_NAME), (AP_KO, FI_NAME),
                      (CL_KO, FC_NAME), (FF_REG, FF_NAME)):
        r = one_reg(R, reg)
        for k in range(20):
            off = M.name_at(k)
            got = bytes(r[off:off + M.NAME_SLOT]).split(b"\0")[0].decode("utf-8", "replace")
            if got != name:
                raise SystemExit("regulation %d slot %d is %r, not %r" % (reg, k, got, name))
    for cid, n in ((AP_CID, 8), (CL_CID, 8), (FI_CID, 2), (FC_CID, 2), (FF_CID, 2)):
        if len([e for e in E if e[M.E_CID] == cid]) != n:
            raise SystemExit("competition %d has %d entries, not %d"
                             % (cid, len([e for e in E if e[M.E_CID] == cid]), n))
    eids = [int.from_bytes(e[M.E_EID:M.E_EID + 4], "little") for e in E]
    if len(set(eids)) != len(eids):
        raise SystemExit("two entry rows share an entry id")
    if p["ff_line"] not in lines or p["ap_line"] not in lines or p["cl_line"] not in lines:
        raise SystemExit("a ccup line is missing from the world file")
    print("  world-finals: 134/135 groups 259/260, finals %d/%d/%d at 261/262/263, "
          "FF line %d, %d entries" % (FI_CID, FC_CID, FF_CID, lines.index(p["ff_line"]), len(E)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    ap.add_argument("--base")
    ap.add_argument("--world")
    ap.add_argument("--out", default=os.path.join(REPO, "out", "futve"))
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    base = a.base or os.path.join(a.game or "", "SiderAddons", "livecpk", "_FL26MyWorld",
                                  "common", "etc", "pesdb")
    world = a.world or os.path.join(a.game or "", "SiderAddons", "modules", "fl26world.txt")
    if not os.path.isdir(base) or not os.path.isfile(world):
        raise SystemExit("no world found (base %s, world %s); pass --game or FL26_DIR" % (base, world))
    p = plan(base, world, a.dry, os.path.join(a.out, "tmp"))
    print("Liga FUTVE finals block: Apertura 134 (groups %d), Clausura 135 (groups %d), "
          "finals %d/%d/%d (regs %d/%d/%d)" % (AP_REG, CL_REG, FI_CID, FC_CID, FF_CID,
                                                AP_KO, CL_KO, FF_REG))
    print("  final rows as reg %d, cut to two clubs; calendar as reg %d" % (p["shape"], p["date_src"]))
    for k in ("ap_line", "cl_line", "ff_line"):
        print("  " + p[k])
    if a.dry:
        print("dry run: nothing written")
        return 0
    build(p, a.out)
    shutil.rmtree(p["tmp"], ignore_errors=True)
    print("  written to %s" % os.path.join(a.out, "world-finals"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
