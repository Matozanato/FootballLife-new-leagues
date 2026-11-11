"""A league's first season with nobody abroad ("first_season_abroad": false, the world file's
`firstabroad <reg> 0`): fl26swiss.c's abroad_last, first_sub and fl26_swiss_firstabroad, built
natively (tools/native/test_first_season.c) and run without the game.

    python tools/test_first_season.py

Built by nativetest.py: zig on Windows, the system C compiler with tools/native/hosttest elsewhere;
without a compiler the test says so and is skipped.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nativetest


r = nativetest.run("test_first_season.c")
assert r.returncode == 0, "the first-season checks failed"
assert "all checks passed" in r.stdout
print("ok")
