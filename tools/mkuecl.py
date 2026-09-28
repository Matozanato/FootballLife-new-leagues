r"""python mkuecl.py --src <livecpk world> --out <new livecpk world> [--dry]

Build a world with a Conference League in it: a copy of --src plus one new competition, cloned
from the (already reshaped) Europa League by mkphases.py -- a 36-club league phase as one group,
then the knockout. Nothing shipped changes; the clone takes the first free ids (competition 174,
regulations 186 and 187, group row 1210 in _FL26G39UCL36), which is what fl26swiss.dll expects.

Its 36 entrants are clubs of the European first divisions that are in neither the Champions
League, the Europa League nor the Super Cup entries of --src, taken one league at a time in turn
so that every country is represented. The same list is printed as a Lua table for
sider/fl26swiss.lua, because the exe gives a competition it does not know no entrants of its own
and the DLL fills it from that list after the Champions League play-off.

The competition id is 174 (--cid to change it). mkphases.py alone would take the first free one
from 130, which is 174 only in a world with 39 added leagues; nothing in fl26swiss keys on the
competition id (it finds the Conference League by regulation 186), but one id everywhere keeps
worlds comparable. The regulation ids are not negotiable: fl26swiss.dll and the fixture-date
stub of the runtime patch set both know 186, 187 and 1210, and build() refuses other ones.

    python mkuecl.py --src E:\...\livecpk\_FL26G39UCL36 --out E:\...\livecpk\_FL26G39UECL

build(pesdb, out) does the same inside a world that is being built (the league builder's
"Conference League" option): it reads the tables in <pesdb>, adds the competition and writes the
three competition tables to <out>, with no copy and no second process.
"""
import contextlib, io, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M

PESDB = os.path.join("common", "etc", "pesdb")
EUROPE = ("UEFA_CHAMPIONS_LEAGUE", "UEFA_EUROPE_LEAGUE", "UEFA_SUPER_CUP")
LEAGUES = ("ENGLAND_D1_LEAGUE", "SPAIN_D1_LEAGUE", "ITALY_D1_LEAGUE", "GERMANY_D1_LEAGUE",
           "FRANCE_D1_LEAGUE", "NETHERLANDS_D1_LEAGUE", "PORTUGAL_D1_LEAGUE", "BELGIUM_D1_LEAGUE",
           "RUSSIA_D1_LEAGUE", "GREECE_D1_LEAGUE", "TURKEY_D1_LEAGUE", "DENMARK_D1_LEAGUE",
           "SCOTLAND_D1_LEAGUE")
FIELD = 36
NAME, CODE = "FL Conference League", "FL_UECL"
CID = 174                    # the competition id (see above)
REG, KO, ROW = 186, 187, 1210  # league phase, knockout, the league phase's one group


def cid_of(comp, code):
    for i in range(len(comp) // M.COMP):
        r = comp[i * M.COMP:(i + 1) * M.COMP]
        if r[M.CODE_OFF:].split(b"\0")[0].decode("latin1") == code:
            return r[M.CID_OFF]
    return None


def pick(base):
    comp, ents = M.load(base, "Competition.bin"), M.load(base, "CompetitionEntry.bin")
    by = {}
    for i in range(len(ents) // M.ENT):
        e = ents[i * M.ENT:(i + 1) * M.ENT]
        by.setdefault(e[M.E_CID], []).append(
            (e[M.E_ORDER], int.from_bytes(e[M.E_TEAM:M.E_TEAM + 4], "little")))
    taken = {t for code in EUROPE for _o, t in by.get(cid_of(comp, code), [])}
    lists = [[t for _o, t in sorted(by.get(cid_of(comp, code), [])) if t not in taken]
             for code in LEAGUES]
    out, k = [], 0
    while len(out) < FIELD and any(k < len(l) for l in lists):
        for l in lists:
            if k < len(l) and len(out) < FIELD and l[k] not in out:
                out.append(l[k])
        k += 1
    return out


def phases_args(base, out, clubs, cid=CID):
    return ["--base", base, "--out", out, "--like", "UEFA_EUROPE_LEAGUE", "--name", NAME,
            "--code", CODE, "--cid", str(cid), "--teams", ",".join(map(str, clubs))]


def build(base, out, cid=CID, log=print):
    """add the Conference League to the tables in <base> and write them to the world <out>
    (in place when <base> is <out>'s own pesdb). The Europa League must already have its one
    league-phase group of 36 (mkreshape.py). Returns the entrants; SystemExit on anything off."""
    import mkphases
    clubs = pick(base)
    if len(clubs) < FIELD:
        raise SystemExit("only %d Conference League entrants found, %d wanted" % (len(clubs), FIELD))
    old, buf = sys.argv, io.StringIO()
    sys.argv = ["mkphases.py"] + phases_args(base, out, clubs, cid)
    try:
        with contextlib.redirect_stdout(buf):
            rc = mkphases.main()
    except SystemExit as e:
        raise SystemExit("mkphases: %s\n%s" % (e, buf.getvalue()))
    finally:
        sys.argv = old
    if rc:
        raise SystemExit("mkphases returned %s\n%s" % (rc, buf.getvalue()))
    regs = M.load(os.path.join(out, PESDB), "CompetitionRegulation.bin")
    have = {int.from_bytes(regs[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little")
            for i in range(len(regs) // M.REG) if regs[i * M.REG + M.R_CID] == cid}
    if not {REG, KO, ROW} <= have:
        raise SystemExit("the Conference League got regulations %s, not %d/%d/%d -- fl26swiss and "
                         "the fixture dates know only those; is the Europa League reshaped "
                         "(one group of 36)?" % (sorted(have), REG, KO, ROW))
    log("  Conference League: competition %d, regulations %d/%d (group %d), %d entrants"
        % (cid, REG, KO, ROW, len(clubs)))
    return clubs


def main():
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    src, out = get("--src"), get("--out")
    if not src or not out:
        print(__doc__)
        return 1
    cid = int(get("--cid") or CID)
    clubs = pick(os.path.join(src, PESDB))
    print("%d entrants" % len(clubs))
    print("local UECL = { %s }" % ", ".join(map(str, clubs)))
    cmd = [sys.executable, os.path.join(HERE, "mkphases.py")] + phases_args(
        os.path.join(src, PESDB), out, clubs, cid)
    if "--dry" in a:
        return subprocess.call(cmd + ["--dry"])
    if os.path.exists(out):
        raise SystemExit("%s exists -- pick a new name, worlds are not overwritten" % out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("*.pre*", "*.retiered", "*.bak*"))
    rc = subprocess.call(cmd)
    if rc == 0:
        print("(the calendar line above is for a clone run on its own: with fl26swiss.dll installed"
              " the Conference League's dates are written by the DLL -- six rounds from October to"
              " December, the play-off in February, the knockout on UEFA's dates -- so nothing"
              " needs to be done about it)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
