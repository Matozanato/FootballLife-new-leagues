r"""python tools/test_refused_in_exe.py

B145 (Schmiddi 18.10.): fl26nullguard9 ABORTED because FL_2026.exe itself already had a jump at its
spot (another mod's crash fix) -- no module of ours wrote there that game. Mod Studio said "refused
bytes another module had already changed ... Home > Install now", which Install now cannot fix.
Now that case is a warning that names the exe; a spot one of OUR modules wrote first is still the
B80 error (old module / one twice / out of order), and a refused fl26caps is still the exe error.
"""
import os, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from modstudio import checks as C

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


CAPS = "[fl26caps.lua] fl26caps: set 'beta024b9', 900 patches, verifying\n"
NG9 = ("[fl26nullguard9.lua] fl26caps: set 'nullguard9', 2 patches, verifying\n"
       "[fl26nullguard9.lua] fl26caps: MISMATCH at 0x140cd6a18: found 8b542440e9ca7c850190909090, "
       "expected 8b542440488b4c24480fb71491  [redirect]\n"
       "[fl26nullguard9.lua] fl26caps: ABORTED, 1 of 2 sites did not match. Nothing was written.\n")
# an old copy of ours that wrote the same spot earlier in that game
OURS_FIRST = ("[fl26nullguard3.lua] fl26caps: [1/1] 0x140cd6a18 8b542440488b4c24480fb71491 -> "
              "e9c37e85019090909090909090  redirect\n")


def run(text):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "sider.log")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    C._refused.clear()
    return C.exe_problems(types.SimpleNamespace(log_path=p))


got = run(CAPS + "[fl26caps.lua] fl26caps: [1/900] 0x140001000 00 -> 01  x\n" + NG9)
ok("B145: the exe's own change at the spot is a warning, not Install now",
   len(got) == 1 and got[0][0] == "warn" and "fl26nullguard9.lua" in got[0][2]
   and "another mod" in got[0][2] and "Install now" not in got[0][2])

got = run(CAPS + OURS_FIRST + NG9)
ok("a spot one of our modules wrote first is still the B80 error (Install now)",
   len(got) == 1 and got[0][0] == "err" and "Install now" in got[0][2])

two = NG9.replace("nullguard9", "nullguard8").replace("0x140cd6a18", "0x140001000")
got = run(CAPS + "[fl26caps.lua] fl26caps: [1/900] 0x140000fff 0000 -> 0101  x\n" + NG9 + two)
ok("both at once: the error for ours, the warning for the exe's",
   [g[0] for g in got] == ["err", "warn"] and "fl26nullguard8.lua" in got[0][2]
   and "fl26nullguard9.lua" in got[1][2] and "fl26nullguard9.lua" not in got[0][2])

got = run("[fl26caps.lua] fl26caps: MISMATCH at 0x140001000: found 00, expected 01  [x]\n"
          "[fl26caps.lua] fl26caps: ABORTED, 1 of 900 sites did not match.\n" + NG9)
ok("fl26caps refused: still the 'not the Steam exe' error",
   len(got) == 1 and got[0][0] == "err" and "Steam" in got[0][2])

ok("no ABORTED: nothing", run(CAPS) == [])



# the same in the CLI check (leaguebuilder.check, what "Check" prints)
import leaguebuilder as B
g = tempfile.mkdtemp()
open(os.path.join(g, "FL_2026.exe"), "wb").write(b"MZ")
os.makedirs(os.path.join(g, "SiderAddons", "modules"))
with open(os.path.join(g, "SiderAddons", "sider.log"), "w", encoding="utf-8") as f:
    f.write(CAPS + NG9)
said = []
try:
    B.check(g, log=said.append)
except Exception:
    pass
said = "\n".join(said)
ok("check: the exe's own change is said as such, not 'Install now'",
   "already changed at its spot by another mod" in said and "Install now" not in said)
print("test_refused_in_exe: ok (%d)" % N)
