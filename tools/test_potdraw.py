"""B243 (0.2.5): the modern Sudamericana's group draw keeps clubs of one association apart --
fl26swiss.c's pot_draw built natively with the FL26_RCAL_TEST harness (tools/native/test_potdraw.c)
and run without the game over thousands of draws: one club of every pot in each group, every club
once, no two clubs of one association in a group whenever a draw can manage it, and a single pair
when nine clubs of one association share 32 places.

    python tools/test_potdraw.py

Built by nativetest.py: zig on Windows, the system C compiler with tools/native/hosttest elsewhere;
without a compiler the test says so and is skipped.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
sys.path.insert(0, HERE)
import nativetest


r = nativetest.run("test_potdraw.c")
assert r.returncode == 0, "the pot draw checks failed"
assert "all checks passed" in r.stdout
print("ok")
