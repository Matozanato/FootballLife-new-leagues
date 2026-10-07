"""python tools/test_lbpack.py

The module bundles lbpack.py writes (fl26guards, fl26lateguards): every part is in, in order, and
the wrapper calls nothing Sider's Lua lacks -- pcall is not there (run023, 2026-10-07: both
bundles failed at init with "attempt to call global 'pcall'", so no guard of theirs was on).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbpack as P

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    for name, parts in P.BUNDLES.items():
        text = P.bundle(name, parts)
        wrapper = text[text.index("local PARTS = "):]
        ok("%s: no pcall / xpcall in the wrapper" % name, not re.search(r"\bx?pcall\s*\(", wrapper))
        at = [text.index("-- ==== %s.lua ====" % p) for p in parts]
        ok("%s: all %d parts, in order" % (name, len(parts)), at == sorted(at))
        ok("%s: init calls each part's init" % name, "p[2].init(ctx)" in wrapper)
    print("%d cases passed" % N)


if __name__ == "__main__":
    main()
