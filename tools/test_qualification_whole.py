"""B414 (Vicentico, 10.11.2026): Cups > Continental > Qualification listed Colombia's league and the
MLS by their first tournament only ("Liga BetPlay DIMAYOR I", "MLS First Round"), so places went
by the first tournament's table. The season as a whole (leaguebuilder.game_season_totals: 119, 51)
has no clubs entered of its own, got no country, and was left out of the list.

    python tools/test_qualification_whole.py <folder with the game's tables>

With the game's tables: both whole seasons are listed, under their first tournament's country and
confederation, with the clubs and the cup of it, and the page says they go by both tables; the
first tournaments stay in the list; the automatic CONMEBOL allocation still sees one league of
Colombia (the whole season is not one of its playable leagues). Without tables: skipped.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
base = sys.argv[1] if len(sys.argv) > 1 else ""
if not os.path.isfile(os.path.join(base, "CompetitionRegulation.bin")):
    print("SKIPPED: give the folder with the game's tables (common/etc/pesdb)")
    sys.exit(0)
from modstudio import qualification_data as Q
from modstudio import conmebol_allocation as A

N = 0


def ok(what, cond):
    global N
    if not cond:
        print("FAIL", what)
        sys.exit(1)
    N += 1
    print("ok  ", what)


native = {s.key: s for s in Q.metadata(base)[0]}
for whole, first, conf in (("119", "168", 4), ("51", "166", 6)):
    ok("%s (the whole season) is listed" % whole, whole in native)
    w, f = native[whole], native[first]
    ok("%s: the country and confederation of its first tournament (%s, %d)" % (w.name, w.country, w.confederation),
       w.country == f.country and w.country and w.confederation == f.confederation == conf)
    ok("%s: its clubs and cup as the first tournament's (%d)" % (w.name, w.clubs), w.clubs == f.clubs > 0 and w.cup == f.cup)
    ok("%s: marked as two tournaments (%s), the first tournament is not" % (w.name, " + ".join(w.whole)),
       len(w.whole) == 2 and w.whole[0] == f.name and not f.whole)
    said = Q.inherited_text(w, {})
    ok("the page says it goes by both tables", w.whole[0] in said and w.whole[1] in said)
    ok("... with places of its own too", w.whole[1] in Q.inherited_text(w, {"game_europe": {whole: [[1, 3]]}}))
ok("the first tournaments keep their own text", "added together" not in Q.inherited_text(native["168"], {}))
ok("the automatic allocation's playable leagues: the first tournament, not the whole season",
   "168" in A.playable_native_rids(base) and "119" not in A.playable_native_rids(base))
print("all %d checks passed" % N)
