"""python tools/test_retired_modules.py

ensure_modules switches a module a bundle took over (fl26nullguard ... -> fl26guards) off only when
the bundle is loaded too. Switch on hands in the world's modules alone: it turned every guard off
with no fl26guards line in sider.ini (07.10., the modpack world), and the game had no guards.
"""
import os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import leaguebuilder as B
import lbpack

N = 0
NL = chr(10)

INI = """[sider]
lua.enabled = 1
luajit.ext.enabled = 1
lua.module = "fl26nullguard.lua"
lua.module = "fl26nullguard2.lua"
lua.module = "fl26superguard.lua"
lua.module = "fl26regions.lua"
lua.module = "fl26nullguard3.lua"
lua.module = "fl26hdr127.lua"
"""


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def live(game, m):
    t = open(os.path.join(game, "SiderAddons", "sider.ini"), encoding="utf-8-sig").read()
    return ('\nlua.module = "%s.lua"' % m) in t


def main():
    retired = B.retired_modules()
    if "fl26nullguard" not in retired:
        print("skip - no retired.txt in the pack (run lbpack first)")
        return
    game = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "modules"))
        open(os.path.join(game, "FL_2026.exe"), "wb").close()
        open(os.path.join(game, "SiderAddons", "sider.ini"), "w", encoding="utf-8").write(INI)
        B.ensure_modules(game, lbpack.ORDER, ["fl26regions", "fl26regnames"], log=lambda s: None)
        ok("world modules only: the guards stay on", live(game, "fl26nullguard") and live(game, "fl26superguard"))
        ok("world modules only: no fl26guards line made up", not live(game, "fl26guards"))
        B.ensure_modules(game, lbpack.ORDER, ["fl26guards"], log=lambda s: None)
        ok("with fl26guards: its line is on", live(game, "fl26guards"))
        ok("with fl26guards: the guards it bundles go off", not live(game, "fl26nullguard") and not live(game, "fl26nullguard2"))
        if "fl26hdr127" in retired:
            ok("with fl26guards: the old nullguard3 it replaced goes off", not live(game, "fl26nullguard3"))
            ok("without fl26hdr255: hdr127 stays on", live(game, "fl26hdr127"))
            B.ensure_modules(game, lbpack.ORDER, ["fl26hdr255"], log=lambda s: None)
            ok("with fl26hdr255: hdr127 goes off (audit 12.10.)", live(game, "fl26hdr255") and not live(game, "fl26hdr127"))
    finally:
        shutil.rmtree(game, ignore_errors=True)
    b80()
    print("1..%d" % N)


def b80():
    """B80 (Yanis, 16.10.): a hand install, alphabetical, with an old caps set's own name and an
    older slots count beside the shipped ones. fl26caps applied, the two old lines and every module
    loaded before the one whose bytes it expects refused, and the diagnostics blamed the exe."""
    game = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(game, "SiderAddons", "modules"))
        open(os.path.join(game, "FL_2026.exe"), "wb").close()
        mods = sorted(lbpack.ORDER + ["fl26caps.teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar",
                                     "fl26slots128"])
        mods.remove("fl26caps")
        ini = ("[sider]" + NL + "lua.enabled = 1" + NL + "luajit.ext.enabled = 1" + NL
               + "".join('lua.module = "%s.lua"' % m + NL for m in ["fl26caps"] + mods + ["fl26swiss", "kitserver"]))
        open(os.path.join(game, "SiderAddons", "sider.ini"), "w", encoding="utf-8").write(ini)
        B.ensure_modules(game, lbpack.ORDER, [m for m in lbpack.ORDER if m not in lbpack.PER_WORLD],
                         log=lambda s: None)
        ok("B80: the old caps set's line goes off",
           not live(game, "fl26caps.teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar"))
        ok("B80: fl26slots128 goes off beside fl26slots250", not live(game, "fl26slots128") and live(game, "fl26slots250"))
        t = open(os.path.join(game, "SiderAddons", "sider.ini"), encoding="utf-8-sig").read().splitlines()
        on = [B.module_of(l)[0] for l in t if B.module_of(l)[1]]
        ours = [m for m in on if m in lbpack.ORDER]
        ok("B80: fl26swiss on once", ours.count("fl26swiss") == 1)
        ok("B80: ours load in ORDER", ours == [m for m in lbpack.ORDER if m in ours])
        ok("B80: every shipped module still on", set(ours) == set(lbpack.ORDER))
        ok("B80: someone else's module stays on", "kitserver" in on)
        before = open(os.path.join(game, "SiderAddons", "sider.ini"), "rb").read()
        B.ensure_modules(game, lbpack.ORDER, [m for m in lbpack.ORDER if m not in lbpack.PER_WORLD],
                         log=lambda s: None)
        ok("B80: a second run changes nothing", open(os.path.join(game, "SiderAddons", "sider.ini"), "rb").read() == before)
        # a numbered module of someone else's, or with no shipped one loaded, stays
        ok("B80: fl26slots128 alone is not stale", B.stale_line("fl26slots128", lbpack.ORDER, {"fl26caps"}) is None)
        ok("B80: fl26probe is not stale", B.stale_line("fl26probe", lbpack.ORDER, set(lbpack.ORDER)) is None)
        ok("B80: fl26regs300 beside fl26regs600", B.stale_line("fl26regs300", lbpack.ORDER, {"fl26regs600"}) == "fl26regs600")
    finally:
        shutil.rmtree(game, ignore_errors=True)


if __name__ == "__main__":
    main()
