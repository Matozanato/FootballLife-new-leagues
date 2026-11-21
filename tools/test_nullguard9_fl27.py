"""python tools/test_nullguard9_fl27.py -- nullguard9 on FL 2027 (09.11., test of everything): the FL27
limits set has already widened the match id read at 0x140cd6a21 (fl26caps.fl27, M4), the guard used to
refuse those bytes and Home said NOT READY in every FL27 game. Its u32 trampoline must be the FL26 one
with only the read swapped (same length, so both jumps land where they did) and the site it accepts must
be what fl26caps.fl27 leaves there."""
import os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIDER = os.path.join(HERE, "..", "sider")
src = open(os.path.join(SIDER, "fl26nullguard9.lua"), encoding="utf-8").read()
caps = open(os.path.join(SIDER, "fl26caps.fl27.lua"), encoding="utf-8").read()
fails = 0


def ok(cond, what):
    global fails
    print(("ok   " if cond else "FAIL ") + what)
    fails += not cond


tramp = re.search(r'va=0x14252e8e0,\s*old="0+",\s*new="([0-9a-f]+)"', src).group(1)
site_old = re.search(r'va=0x140cd6a18, old="([0-9a-f]+)"', src).group(1)
wide_site = re.search(r'WIDE_SITE = "([0-9a-f]+)"', src).group(1)
wide_tramp = re.search(r'WIDE_TRAMP = "([0-9a-f]+)"', src).group(1)
m4 = re.search(r'va=0x140cd6a21, old="([0-9a-f]+)", new="([0-9a-f]+)"', caps)

ok(m4 is not None, "fl26caps.fl27 still widens the read at 0x140cd6a21")
ok(len(wide_tramp) == len(tramp), "the u32 trampoline is as long as the u16 one")
ok(tramp.replace(m4.group(1), m4.group(2), 1) == wide_tramp, "only the read differs: %s -> %s" % m4.groups())
off = 0x140cd6a21 - 0x140cd6a18
ok(site_old[off * 2:off * 2 + 8] == m4.group(1), "FL26's site has the u16 read where M4 expects it")
ok(site_old[:off * 2] + m4.group(2) + site_old[off * 2 + 8:] == wide_site,
   "the u32 site is FL26's with M4 written over it")


def jumps(t):
    b = bytes.fromhex(t)
    return [0x14252e8e0 + i + 5 + struct.unpack("<i", b[i + 1:i + 5])[0] for i in (18, 23) if b[i] == 0xe9]


ok(jumps(wide_tramp) == [0x140cd6a25, 0x140cd6ead], "the u32 trampoline jumps back to 0x140cd6a25 / 0x140cd6ead")
ok(bytes.fromhex(wide_tramp)[12] == 0x74 and bytes.fromhex(wide_tramp)[13] == 9, "je out still skips read + jmp (9 bytes)")
print("FAILED %d" % fails if fails else "all ok")
sys.exit(1 if fails else 0)
