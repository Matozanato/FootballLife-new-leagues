"""Title leagues -- the split leagues whose title is a final of two cups' (an Apertura/Clausura grand
final), any number in one world: fl26swiss.c's fl26_swiss_title_league, grand_final_of and
league_champion_kept, built natively (tools/native/test_grand_final.c) and run without the game.

    python tools/test_grand_final.py

Built by nativetest.py: zig on Windows, the system C compiler with tools/native/hosttest elsewhere;
without a compiler the test says so and is skipped.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nativetest


r = nativetest.run("test_grand_final.c")
assert r.returncode == 0, "the title league checks failed"
assert "all checks passed" in r.stdout
print("ok")
