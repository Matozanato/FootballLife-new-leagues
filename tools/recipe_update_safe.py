"""recipe_update_safe.py -- a copy of a world recipe that an Update of a published world can carry
to the careers of that world (18.11.2026, B4 crash of the beta 3 career b470-3006).

Two independent fixes, each a flag; the recipe given is never written, only --out:

  --ages PREV.zip   every player edit keyed by a game id whose "Age" is HIGHER than that id's age
                    in the previous release's Player.bin goes back to the previous age. fl26regen
                    takes a player whose saved age (previous + years played) is below the database
                    age + years played for a regen and gives him a generated name: beta 4 renamed 60
                    real players of every beta 3 career this way ("60 regens named again").
  --drop-new-leagues PREV.zip
                    leagues whose clubs are all new against the previous release (no club of them
                    in its Team.bin) are taken out, with their squads (players["<league>/<n>"]).
                    An old career has none of their players (the save brings its own players and
                    the new ones are dropped at the load), and the league's rows inserted in the
                    middle of Competition / CompetitionRegulation / CompetitionEntry shift the
                    rows and entry ids of every competition after them.

  python recipe_update_safe.py RECIPE --out OUT [--ages PREV.zip] [--drop-new-leagues PREV.zip]
"""
import json, os, struct, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb                                    # noqa: E402
import playeredit as pe                         # noqa: E402

PESDB = "common/etc/pesdb/"


def zip_table(path, name):
    with zipfile.ZipFile(path) as z:
        n = next(n for n in z.namelist() if n.replace("\\", "/").endswith(PESDB + name))
        d = z.read(n)
    return pesdb.wesys_unpack(d) if d[3:8] == b"WESYS" else d


def prev_ages(path):
    raw = zip_table(path, "Player.bin")
    return {struct.unpack_from("<I", raw, i + 8)[0]: pe.getf(raw[i:i + 312], "Age")
            for i in range(0, len(raw), 312)}


def prev_club_names(path):
    raw = zip_table(path, "Team.bin")
    out = set()
    for i in range(0, len(raw), pe.T_REC):
        out.add(pe.cstr(raw[i + pe.T_NAME:i + pe.T_NAME + pe.T_NAME_LEN]).strip().lower())
    return out


def fix_ages(recipe, ages, log):
    n = 0
    for key, squad in (recipe.get("players") or {}).items():
        for pid, ed in ((squad or {}).get("edits") or {}).items():
            if not (isinstance(ed, dict) and str(pid).isdigit() and "Age" in ed):
                continue
            was = ages.get(int(pid))
            try:
                now = int(ed["Age"])
            except (TypeError, ValueError):
                continue
            if was is not None and now > was:
                log("age\t%s\t%s\t%s\t%d -> %d (previous release)" % (key, pid, ed.get("name", ""), now, was))
                ed["Age"] = str(was)
                n += 1
    return n


def drop_new_leagues(recipe, clubs, log):
    keep, gone = [], []
    for lg in recipe.get("leagues") or []:
        names = [str(c).strip().lower() for c in (lg.get("club_names") or [])]
        if names and not any(c in clubs for c in names):
            gone.append(lg["name"])
            log("league\t%s\t%d clubs, all new\t%s" % (lg["name"], len(names), ", ".join(lg.get("club_names"))))
        else:
            keep.append(lg)
    recipe["leagues"] = keep
    # everything keyed by a club of it, "<league>/<n>": players (the squads), club_money, ...
    for sect, d in recipe.items():
        if not isinstance(d, dict):
            continue
        for k in [k for k in d if isinstance(k, str) and k.rsplit("/", 1)[0] in gone]:
            log("%s\t%s" % (sect, k))
            del d[k]
    # names of a dropped league anywhere else in the recipe (above=..., cups...): reported, not guessed
    left = [g for g in gone if g in json.dumps(recipe, ensure_ascii=False)]
    for g in left:
        log("STILL REFERENCED\t%s" % g)
    return gone, left


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    src = argv[0]
    get = lambda k: argv[argv.index(k) + 1] if k in argv else None
    out = get("--out")
    if not out or os.path.abspath(out) == os.path.abspath(src):
        print("--out must be another file: the recipe given is never written")
        return 2
    recipe = json.load(open(src, encoding="utf-8"))
    lines = []
    log = lambda s: (lines.append(s), print(s))
    gone, left = [], []
    if get("--drop-new-leagues"):
        gone, left = drop_new_leagues(recipe, prev_club_names(get("--drop-new-leagues")), log)
    n = fix_ages(recipe, prev_ages(get("--ages")), log) if get("--ages") else 0
    text = json.dumps(recipe, indent=1, ensure_ascii=False)
    with open(out + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(out + ".tmp", out)
    with open(out + ".txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote %s: %d leagues out (%s), %d ages back%s" % (out, len(gone), ", ".join(gone), n,
                                                           "; STILL REFERENCED: " + ", ".join(left) if left else ""))
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
