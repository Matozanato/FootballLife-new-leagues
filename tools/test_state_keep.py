"""B49 (0.2.4): the final tables and cup winners fl26swiss keeps at the season's end outlive the
game session -- fl26swiss.c built natively with the FL26_STATE_TEST harness
(tools/native/test_state_keep.c) and run without the game: the July teardown writes them to the
save folder's fl26swiss-state.bin, the game is quit, a save of 26 July is loaded and the Europe
places come from the kept tables, not squad strength; a later save, an older save loaded in the
same session, another club's career and a new career each get what is theirs.

    python tools/test_state_keep.py

Built by nativetest.py: zig on Windows, the system C compiler with tools/native/hosttest elsewhere;
without a compiler the test says so and is skipped.
The file is written in the temp folder, never in the game's save folder.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
sys.path.insert(0, HERE)
import nativetest


r = nativetest.run("test_state_keep.c")
assert r.returncode == 0, "the kept-state checks failed"
assert "all checks passed" in r.stdout
print("ok")
