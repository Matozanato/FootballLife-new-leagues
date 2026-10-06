r"""python regress018.py [--base <pesdb dir>] [--only <name>]

One command that builds every test recipe and checks it (0.1.8, round 3).

For every *.json under tools/testdata/buildcheck/ and tools/testdata/regress018/:
  1. build it:  python tools/leaguebuilder.py build <recipe> --base <base> --game out/scratch/regress/<name>
     (a subprocess; its output is kept, and a failed build is one FAIL line with the last 5
     lines of that output);
  2. run tools/buildcheck.py on the built pesdb (a subprocess) and keep its PASS/FAIL lines;
  3. the European-day check (GitHub #54): read <world dir>/fl26world.txt for the regulation id
     of every league of the world (fl26world.from_tables; a `league <id> ... name=<name>` line).
     For every league of the world that has European places in its recipe ("europe" key) count
        len(set(leaguebuilder.league_days(rid, rounds)) & leaguebuilder.EURO_DAYS)
     where rounds = rounds_of(clubs) * legs. One line per league:
        "<league name>: reg <rid>, <n> European day(s)"
     and it is a FAIL when n > 1, otherwise PASS.

Prints a summary table (recipe, build ok, buildcheck fails, worst European-day count) and exits
1 on any FAIL.

--base defaults to $FL26_PESDB; --only keeps recipes whose
name contains the given text.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B

TOOLS = HERE
TESTDIRS = [os.path.join(TOOLS, "testdata", "buildcheck"),
            os.path.join(TOOLS, "testdata", "regress018")]
SCRATCH = os.path.join(os.path.dirname(TOOLS), "out", "scratch", "regress")
DEFAULT_BASE = os.environ.get("FL26_PESDB", "")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def recipes(only=None):
    """[(name, path)] of every recipe, sorted by name; --only keeps names containing it"""
    out = []
    for d in TESTDIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                out.append((f[:-5], os.path.join(d, f)))
    if only:
        out = [(n, p) for n, p in out if only.lower() in n.lower()]
    return sorted(out)


def run(cmd):
    """run cmd, return (rc, combined output)"""
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def find_world_dir(gamedir):
    """the world folder the build wrote (the folder holding fl26world.txt under gamedir)"""
    for root, _dirs, files in os.walk(gamedir):
        if "fl26world.txt" in files:
            return root
    return None


def world_league_ids(worlddir):
    """{league name: regulation id} from the world file's `league <id> ... name=<name>` lines"""
    out = {}
    path = os.path.join(worlddir, "fl26world.txt")
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line.startswith("league "):
            continue
        head, _sep, nm = line.partition(" name=")
        bits = head.split()
        try:
            rid = int(bits[1])
        except (IndexError, ValueError):
            continue
        if nm:
            out[nm.strip()] = rid
    return out


def europe_lines(recipe_path, worlddir):
    """[(line, ok)]: one per league of the recipe with European places; ok False when n > 1"""
    recipe = json.load(open(recipe_path, encoding="utf-8"))
    ids = world_league_ids(worlddir)
    out = []
    for L in recipe.get("leagues") or []:
        if not L.get("europe"):
            continue
        name = str(L.get("name", "")).strip()
        rid = ids.get(name)
        clubs = int(L.get("clubs", 0) or 0)
        legs = int(L.get("legs", 2) or 2)
        rounds = B.rounds_of(clubs) * legs
        n = len(set(B.league_days(rid, rounds)) & B.EURO_DAYS) if rid is not None else 0
        out.append(("%s: reg %s, %d European day(s)" % (name, rid, n), n, n <= 1))
    return out


def main():
    a = sys.argv[1:]
    get = lambda k: a[a.index(k) + 1] if k in a else None
    base = get("--base") or DEFAULT_BASE
    only = get("--only")
    if not os.path.exists(os.path.join(base, "CompetitionRegulation.bin")):
        print("no shipped tables in %s -- pass --base <folder with CompetitionRegulation.bin>" % base)
        return 2

    rows = []
    anyfail = False
    for name, path in recipes(only):
        gamedir = os.path.join(SCRATCH, name)
        if os.path.exists(gamedir):
            shutil.rmtree(gamedir)
        print("=" * 72)
        print("recipe %s  (%s)" % (name, path))
        build_ok = False
        bc_passes = bc_fails = 0
        worst = None
        rc, out = run([sys.executable, os.path.join(TOOLS, "leaguebuilder.py"),
                       "build", path, "--base", base, "--game", gamedir])
        if rc != 0:
            print("FAIL %s: build failed (exit %d); last 5 lines:" % (name, rc))
            for l in out.splitlines()[-5:]:
                print("     " + l)
        else:
            build_ok = True
            tail = [l for l in out.splitlines() if l.strip()]
            print("build OK" + ("  (last line: %s)" % tail[-1] if tail else ""))
            worlddir = find_world_dir(gamedir)
            if worlddir is None:
                build_ok = False
                print("FAIL %s: build wrote no fl26world.txt under %s" % (name, gamedir))
            else:
                pesdb = os.path.join(worlddir, "common", "etc", "pesdb")
                rc, bout = run([sys.executable, os.path.join(TOOLS, "buildcheck.py"),
                                pesdb, "--base", base])
                for l in bout.splitlines():
                    if l.startswith("PASS"):
                        bc_passes += 1
                        print("  buildcheck: " + l)
                    elif l.startswith("FAIL"):
                        bc_fails += 1
                        print("  buildcheck: " + l)
                for l, n, ok in europe_lines(path, worlddir):
                    print("  " + l + ("" if ok else "   <- FAIL"))
                    if worst is None or n > worst:
                        worst = n
                    if not ok:
                        anyfail = True
        if not build_ok or bc_fails:
            anyfail = True
        rows.append((name, build_ok, bc_fails, worst))

    print("=" * 72)
    print("summary: recipe                 build-ok  buildcheck-fails  worst-European-days")
    for name, build_ok, bc_fails, worst in rows:
        print("         %-22s %-8s  %-16s  %s" % (
            name, "yes" if build_ok else "NO", str(bc_fails) if build_ok else "-",
            "-" if worst is None else worst))
    print("regress018: %s" % ("all recipes passed" if not anyfail else "SOME FAILED"))
    return 1 if anyfail else 0


if __name__ == "__main__":
    sys.exit(main())
