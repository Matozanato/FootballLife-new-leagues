"""python test_liga_futve.py <folder with the game's tables> -- the Liga FUTVE recipe
(tools/testdata/regress018/liga_futve.json, docs/developers/fork/futve-playoff.md) builds the world
of phase 5 with Mod Studio's keys alone: January-December Apertura/Clausura with groups and a grand
final, the days of phase 5 by hand, the trophy ceremony, the Libertadores' cinematics for the
Apertura's final, the continental places in the order of the finals, nobody abroad in the first
season, the modern CONMEBOL competitions with the play-off on 144 and 161.

Built with the ids of phase 5 pinned (tools/testdata/futve/phase5-ids.json: what a Build of Felix's
world reads from its last plan), its world file has every Liga FUTVE and South American line of
phase 5's (tools/testdata/futve/phase5-world.txt, taken from the world Felix played three seasons
with) -- the same regulations, competitions, entries and days -- but for:
  - `contorder 11 finals` and `firstabroad 11 0`: phase 5's code always on, now an option;
  - the league line: no scupcup=255 (its super cup's cup is the league's cup=255 anyway) and the
    cup's entry options (cupall=1 cuptop=11 cuplow=0 cupn=14) every Build writes since 0.2.4;
  - the Final del Clausura on competition 147: phase 5 took 129 by hand, the base's Danish cup."""
import json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import mkleague as M

KEEP = re.compile(r"^(league|split|season|splitdays|ccup|lpre|dates|tmap|cine|contorder|firstabroad) "
                  r"|^uefa (11|29|30|67|168|329\d\d) ")
NEW = ["contorder 11 finals", "firstabroad 11 0"]


def league_line(s):
    """the league line without the keys phase 5 and a Build write differently, keys in order"""
    words = [w for w in s.split(" name=")[0].split()
             if not re.match(r"(scupcup|cupall|cuptop|cuplow|cupn)=", w)]
    return " ".join(words[:2] + sorted(words[2:])) + " name=" + s.split(" name=", 1)[1]


def main(base):
    data = os.path.join(HERE, "testdata")
    r = json.load(open(os.path.join(data, "regress018", "liga_futve.json"), encoding="utf-8"))
    ids = json.load(open(os.path.join(data, "futve", "phase5-ids.json"), encoding="utf-8"))
    want = [l.rstrip("\n") for l in open(os.path.join(data, "futve", "phase5-world.txt"), encoding="utf-8") if l.strip()]
    pl = B.plan(r, base, {"cup_ids": ids["cup_ids"], "leagues": []})
    assert not [t for t in pl["skipped"] if "modern CONMEBOL" in t], pl["skipped"]
    game = tempfile.mkdtemp(prefix="fl26-liga-futve-")
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "livecpk"))
        B.build(pl, base, game, False, log=lambda *a: None)
        world = os.path.join(B.siderdir.find(game), "livecpk", r["world"])
        got = [l for l in open(os.path.join(world, "fl26world.txt"), encoding="utf-8").read().replace("\r", "").split("\n")
               if KEEP.match(l)]
        built = json.load(open(os.path.join(world, "leaguebuilder-plan.json"), encoding="utf-8"))
        db = os.path.join(world, "common", "etc", "pesdb")
        comp = M.load(db, "Competition.bin")
        codes = {comp[i * M.COMP + M.CID_OFF]: bytes(comp[i * M.COMP + M.CODE_OFF:(i + 1) * M.COMP]).split(b"\0")[0]
                 for i in range(len(comp) // M.COMP)}
    finally:
        shutil.rmtree(game, ignore_errors=True)
    for l in NEW:
        assert l in got, l
    lg = [l for l in got if l.startswith("league ")]
    lw = [l for l in want if l.startswith("league ")]
    assert len(lg) == 1 and [league_line(lg[0])] == [league_line(lw[0])], (lg, lw)
    rest_got = sorted(l for l in got if l not in NEW and not l.startswith("league "))
    rest_want = sorted(l for l in want if not l.startswith("league "))
    assert rest_got == rest_want, "\n".join(["phase 5 only:"] + sorted(set(rest_want) - set(rest_got))
                                           + ["built only:"] + sorted(set(rest_got) - set(rest_want)))
    print("world file: the %d Liga FUTVE and South American lines of phase 5, the league line as a Build "
          "writes it, and %s" % (len(rest_want), ", ".join(NEW)))
    cups = built["cup_ids"]
    for k, v in ids["cup_ids"].items():
        if k != "final:FL_011_CFI":
            assert cups.get(k) == v, (k, cups.get(k), v)
    assert cups["final:FL_011_CFI"]["cid"] != 129 and codes.get(129) == b"DENMARK_CUP", (cups["final:FL_011_CFI"], codes.get(129))
    print("ids: every competition and regulation of phase 5 kept but the Final del Clausura's (%d, not the "
          "Danish cup's 129)" % cups["final:FL_011_CFI"]["cid"])
    print("all passed")


if __name__ == "__main__":
    main(sys.argv[1])
