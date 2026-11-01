"""The trophy ceremony's tournament map -- fl26swiss.c's fl26_swiss_tmap and tmap_handler, built
natively (tools/native/test_ceremony.c) and run without the game: the world file's tmap records taken
and refused, each regulation's tournament answered, 217 for any other.

    python tools/test_ceremony.py

Built by nativetest.py: zig on Windows, the system C compiler with tools/native/hosttest elsewhere;
without a compiler the test says so and is skipped.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nativetest


r = nativetest.run("test_ceremony.c")
assert r.returncode == 0, "the tournament map checks failed"
assert "all checks passed" in r.stdout
print("ok")
