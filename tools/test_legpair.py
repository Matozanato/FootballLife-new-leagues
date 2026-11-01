"""B246 (antonimus 26.10.): the Libertadores phase 3 hand-over gives each match record of a tie
its new pair whole, in its leg's order, even when the new pair shares a club with the old one
(Deportes La Serena v Deportes La Serena, Lanus gone). fl26swiss.c's libq_leg_pair built natively
with the FL26_RCAL_TEST harness (tools/native/test_legpair.c) and run without the game.

    python tools/test_legpair.py

Built by nativetest.py: zig on Windows, the system C compiler with tools/native/hosttest elsewhere;
without a compiler the test says so and is skipped.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
sys.path.insert(0, HERE)
import nativetest


r = nativetest.run("test_legpair.c")
assert r.returncode == 0, "the phase 3 hand-over checks failed"
assert "all checks passed" in r.stdout
