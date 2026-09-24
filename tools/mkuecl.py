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

    python mkuecl.py --src E:\...\livecpk\_FL26G39UCL36 --out E:\...\livecpk\_FL26G39UECL
"""
import os, shutil, subprocess, sys

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


def main():
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    src, out = get("--src"), get("--out")
    if not src or not out:
        print(__doc__)
        return 1
    clubs = pick(os.path.join(src, PESDB))
    print("%d entrants" % len(clubs))
    print("local UECL = { %s }" % ", ".join(map(str, clubs)))
    cmd = [sys.executable, os.path.join(HERE, "mkphases.py"), "--base", os.path.join(src, PESDB),
           "--out", out, "--like", "UEFA_EUROPE_LEAGUE", "--name", "FL Conference League",
           "--code", "FL_UECL", "--teams", ",".join(map(str, clubs))]
    if "--dry" in a:
        return subprocess.call(cmd + ["--dry"])
    if os.path.exists(out):
        raise SystemExit("%s exists -- pick a new name, worlds are not overwritten" % out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("*.pre*", "*.retiered", "*.bak*"))
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
