"""The league play-off's pure parts (0.2.5): fl26swiss.c's ccup_league_groups, ccup_entry_rank and
ccup_league_final built natively with the FL26_RCAL_TEST harness (tools/native/test_ccup_league.c)
and run without the game -- the entries dealt into the groups in their order, the final ordered by
the regular phase, a club that is not an entry last, the same club in two groups once.

    python tools/test_futve_playoff.py

Built by nativetest.py: zig on Windows, the system C compiler with tools/native/hosttest elsewhere;
without a compiler the test says so and is skipped.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
sys.path.insert(0, HERE)
import nativetest


r = nativetest.run("test_ccup_league.c")
assert r.returncode == 0, "the league play-off checks failed"
assert "all checks passed" in r.stdout
print("ok")
