"""The trophy cabinet of the Palmarés: fl26swiss.c's record lists, the titles the DLL writes where
the game does not, merges and the palmarés file, built natively with the FL26_RCAL_TEST harness
(tools/native/test_palmares.c) and run without the game.

    python tools/test_palmares.py

Built by nativetest.py: zig on Windows, the system C compiler with tools/native/hosttest elsewhere;
without a compiler the test says so and is skipped.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nativetest

r = nativetest.run("test_palmares.c")
assert r.returncode == 0, "the trophy cabinet checks failed"
assert "all checks passed" in r.stdout
print("ok")
