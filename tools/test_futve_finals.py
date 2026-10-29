r"""python tools/test_futve_finals.py [--game <folder>]

The focused test of tools/futve_finals.py: builds the finals world twice into temp folders and checks
the three competitions (the Apertura/Clausura play-offs 134/135 and the final competitions
142/129/175), the regulations (group masters 259/260, group rows 1283/1284/2307/2308, knockout
regulations 261/262/263), the names in the twenty slots, the entries and the three world lines.

The final competition ids 142/129/175 are the world's next free ones (leaguebuilder.free_comp_ids:
130-135 the Liga FUTVE, 136 the UEFA Conference League's reserved id, 137-141 Scotland's and Saudi
Arabia's); the knockout regulations stay the 16-bit 261/262/263. The in-game menus confirm the
finals in the next test.

  python tools/test_futve_finals.py --game "G:\Games\SP Football Life 2026"
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
import futve_finals as F

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def table_rows(data, size):
    return [data[i:i + size] for i in range(0, len(data), size)]


def one_reg(R, reg):
    hits = [r for r in R if int.from_bytes(r[M.R_ID:M.R_ID + 2], "little") == reg]
    assert len(hits) == 1, "regulation %d" % reg
    return hits[0]


def names(r):
    out = []
    for k in range(20):
        off = M.name_at(k)
        out.append(bytes(r[off:off + M.NAME_SLOT]).split(b"\0")[0].decode("utf-8", "replace"))
    return out


def run(game, out):
    r = subprocess.run([sys.executable, os.path.join(HERE, "futve_finals.py"),
                        "--game", game, "--out", out],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise SystemExit("futve_finals failed:\n%s\n%s" % (r.stdout, r.stderr))
    return os.path.join(out, "world-finals")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=os.environ.get("FL26_DIR"))
    a = ap.parse_args()
    game = a.game
    if not game:
        raise SystemExit("pass --game (or set FL26_DIR)")
    base = os.path.join(game, "SiderAddons", "livecpk", "_FL26MyWorld", "common", "etc", "pesdb")
    world = os.path.join(game, "SiderAddons", "modules", "fl26world.txt")
    if not os.path.isdir(base) or not os.path.isfile(world):
        raise SystemExit("no world at %s / %s" % (base, world))
    tmp_root = os.path.join(REPO, "out", "futve", "tmp")
    os.makedirs(tmp_root, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="futve-finals-", dir=tmp_root)
    try:
        da = run(game, os.path.join(tmp, "a"))
        db = run(game, os.path.join(tmp, "b"))
        p = F.plan(base, world, True, os.path.join(tmp, "plan"))
        pesdb_a = os.path.join(da, "common", "etc", "pesdb")
        pesdb_b = os.path.join(db, "common", "etc", "pesdb")
        comp_b, regs_b, ents_b = (M.load(pesdb_a, n) for n in
                                  ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
        C, R, E = table_rows(comp_b, M.COMP), table_rows(regs_b, M.REG), table_rows(ents_b, M.ENT)

        # the competitions: the two play-offs and the three finals
        for cid, code in ((F.AP_CID, F.AP_CODE), (F.CL_CID, F.CL_CODE),
                          (F.FI_CID, F.FI_CODE), (F.FC_CID, F.FC_CODE), (F.FF_CID, F.FF_CODE)):
            hits = [c for c in C if c[M.CID_OFF] == cid]
            ok("competition %d exists with the code %s" % (cid, code),
               len(hits) == 1 and M.code_of(hits[0]) == code)
        base134 = next(c for c in C if c[M.CID_OFF] == F.AP_CID)
        for cid in (F.FI_CID, F.FC_CID, F.FF_CID):
            c = next(c for c in C if c[M.CID_OFF] == cid)
            ok("competition %d keeps 134's region and confederation" % cid,
               c[M.REGION_OFF] == base134[M.REGION_OFF]
               and (c[M.FLAG_OFF] & 7) == (base134[M.FLAG_OFF] & 7))
        ok("final cids 142/129/175 are the world's next free competition ids "
           "(136 is the UEFA Conference League's; 143/144 have no case)", F.FI_CID == 142 and F.FC_CID == 129
           and F.FF_CID == 175)

        # the regulations: the group masters, the group rows and the knockout finals
        for reg, cid, typ, teams in ((F.AP_REG, F.AP_CID, 2, 8), (F.CL_REG, F.CL_CID, 2, 8),
                                     (F.AP_KO, F.FI_CID, 3, 2), (F.CL_KO, F.FC_CID, 3, 2),
                                     (F.FF_REG, F.FF_CID, 3, 2)):
            r = one_reg(R, reg)
            ok("regulation %d is cid %d, type %d, %d clubs" % (reg, cid, typ, teams),
               r[M.R_CID] == cid and r[M.R_TYPE] == typ and r[M.R_TEAMS] & 0x3f == teams)
        for reg, cid in ((F.AP_REG + F.REPLICA_STEP, F.AP_CID), (F.AP_REG + 2 * F.REPLICA_STEP, F.AP_CID),
                         (F.CL_REG + F.REPLICA_STEP, F.CL_CID), (F.CL_REG + 2 * F.REPLICA_STEP, F.CL_CID)):
            r = one_reg(R, reg)
            ok("group row %d is competition %d's group stage" % (reg, cid),
               r[M.R_CID] == cid and r[M.R_TYPE] == 2)

        # the names: the play-offs and the finals, all twenty slots
        for reg, name in ((F.AP_REG, F.AP_NAME), (F.CL_REG, F.CL_NAME),
                          (F.AP_KO, F.FI_NAME), (F.CL_KO, F.FC_NAME), (F.FF_REG, F.FF_NAME)):
            ok("regulation %d is named %r in all 20 slots" % (reg, name), names(one_reg(R, reg)) == [name] * 20)
        for reg, name in ((F.AP_REG + F.REPLICA_STEP, F.AP_NAME), (F.AP_REG + 2 * F.REPLICA_STEP, F.AP_NAME),
                          (F.CL_REG + F.REPLICA_STEP, F.CL_NAME), (F.CL_REG + 2 * F.REPLICA_STEP, F.CL_NAME)):
            ok("group row %d keeps the play-off's name" % reg, names(one_reg(R, reg)) == [name] * 20)

        # the entries: eight per play-off, two per final, and no shared entry id
        for cid, n in ((F.AP_CID, 8), (F.CL_CID, 8), (F.FI_CID, 2), (F.FC_CID, 2), (F.FF_CID, 0)):
            ok("competition %d has %d entry row(s)" % (cid, n),
               len([e for e in E if e[M.E_CID] == cid]) == n)
        eids = [int.from_bytes(e[M.E_EID:M.E_EID + 4], "little") for e in E]
        ok("entry ids are unique", len(eids) == len(set(eids)))

        # the world file: the two play-off lines replaced, the Final del FUTVE's after the Clausura one
        exp = list(p["lines"])
        exp[p["li_ap"]] = p["ap_line"]
        exp[p["li_cl"]] = p["cl_line"]
        exp.insert(p["li_cl"] + 1, p["ff_line"])
        got = open(os.path.join(da, "fl26world.txt"), "rb").read()
        want = (p["nl"].join(exp) + p["nl"]).encode("utf-8")
        ok("world file: the three ccup lines and the source's other lines, same endings", got == want)

        # two builds are byte-identical
        for n in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"):
            ok("two builds: %s identical" % n,
               open(os.path.join(pesdb_a, n), "rb").read() == open(os.path.join(pesdb_b, n), "rb").read())
        ok("two builds: fl26world.txt identical",
           open(os.path.join(da, "fl26world.txt"), "rb").read()
           == open(os.path.join(db, "fl26world.txt"), "rb").read())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("ok %d - the finals world: 134/135 play-offs + 142/129/175 finals, "
          "261/262/263, three lines, two identical builds" % N)
    return 0


if __name__ == "__main__":
    sys.exit(main())
