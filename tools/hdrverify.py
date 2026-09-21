r"""python hdrverify.py sider/fl26hdr192.lua [N] [--inbound] -> read the module back and check it

hdr127.py writes the trampolines; this reads them. The generator and the checker share
nothing but the exe and the site list, so a mistake in the encoding shows up here as a stub
that does not decode into what it claims to be.

For every one of the thirteen bounds:

  * the bytes the module expects to find really are in the exe at that address;
  * the patch that replaces them is a `jmp rel32` (plus a `nop` where the pair was six bytes
    long) landing on a stub the same module writes;
  * the stub is exactly three instructions -- `cmp <the same register>, N`, `jb <the target
    the original jb had>`, `jmp <the instruction after the pair>`.

`--inbound` adds the slow half: a linear decode of all of `.trace` looking for any branch
aimed inside a replaced pair, and a sweep of `.rdata`, `.trace` and `.data` for an aligned
u32 holding an RVA that points inside one -- a jump table entry. Both must come back empty,
or the redirect would send something into the middle of a `jmp`. It takes a couple of
minutes and the answer does not change unless the site list does.

Reads the exe and the module; writes nothing.
"""
import os
import re
import struct
import sys

try:
    import capstone
except ImportError:
    raise SystemExit("hdrverify needs capstone: python -m pip install capstone")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hdr127 as H


def load(path):
    """The module's patch list, as (va, old bytes, new bytes)."""
    txt = open(path, encoding="utf-8").read()
    out = []
    for va, old, new in re.findall(r'\{va=0x([0-9a-f]+), old="([0-9a-f]*)", new="([0-9a-f]*)"',
                                   txt):
        out.append((int(va, 16), bytes.fromhex(old), bytes.fromhex(new)))
    if not out:
        raise SystemExit("%s has no patches" % path)
    return out


def check(path, n, md, d, secs):
    stubs, jumps = {}, {}
    for va, old, new in load(path):
        if H.section_of(secs, va) is None:
            # No section covers it, so it is the mapped page tail: a stub.
            stubs[va] = new
        elif va in H.BOUNDS:
            jumps[va] = (old, new)

    if not stubs:
        print("%s has no trampolines (N = %d fits in the immediate)" % (path, n))
        return 0
    missing = [va for va in H.BOUNDS if va not in jumps]
    if missing:
        print("BAD: %d bound(s) got no redirect: %s"
              % (len(missing), ", ".join("0x%x" % v for v in missing)))
        return len(missing)

    bad = 0
    for va in H.BOUNDS:
        old, new = jumps[va]
        off = H.offset_of(secs, va)
        if d[off:off + len(old)] != old:
            print("BAD 0x%x: the module expects %s, the exe holds %s"
                  % (va, old.hex(), d[off:off + len(old)].hex()))
            bad += 1
            continue
        orig = list(md.disasm(old, va))
        target, fall = int(orig[1].op_str, 16), va + len(old)

        j = list(md.disasm(new, va))
        to = int(j[0].op_str, 16) if j and j[0].operands else -1
        ok = (j and j[0].mnemonic == "jmp" and to in stubs
              and all(i.mnemonic == "nop" for i in j[1:]))
        s = list(md.disasm(stubs.get(to, b""), to)) if ok else []
        ok = ok and len(s) == 3 and (
            s[0].mnemonic == "cmp"
            and s[0].op_str.split(",")[0] == orig[0].op_str.split(",")[0]
            and s[0].op_str.endswith(hex(n))
            and s[1].mnemonic == "jb" and int(s[1].op_str, 16) == target
            and s[2].mnemonic == "jmp" and int(s[2].op_str, 16) == fall)
        print("%s 0x%x -> 0x%x : %s" % ("ok  " if ok else "BAD ", va, to,
              " ; ".join("%s %s" % (i.mnemonic, i.op_str) for i in s)))
        bad += not ok
    print("%d stub(s), %d redirect(s), %d bad" % (len(stubs), len(jumps), bad))
    return bad


def inbound(md, d, secs):
    """Anything aimed inside the bytes a redirect replaces would land mid-jump."""
    ranges = {}
    for va in H.BOUNDS:
        off = H.offset_of(secs, va)
        ins = list(md.disasm(d[off:off + 16], va))
        ranges[va] = va + ins[0].size + ins[1].size

    base, vsz, raw, rsz, _ = [s for s in secs if s[4] == ".trace"][0]
    hits = 0
    for i in md.disasm(d[raw:raw + rsz], base):
        if i.group(capstone.x86.X86_GRP_JUMP) or i.group(capstone.x86.X86_GRP_CALL):
            op = i.operands[0]
            if op.type == capstone.x86.X86_OP_IMM:
                for va, end in ranges.items():
                    if va < op.imm < end:
                        print("  0x%x: %s %s -> inside the pair at 0x%x"
                              % (i.address, i.mnemonic, i.op_str, va))
                        hits += 1
    print("  %d branch(es) into a replaced pair" % hits)

    want = set()
    for va, end in ranges.items():
        want |= {x - H.IMAGE_BASE for x in range(va + 1, end)}
    found = 0
    for name in (".rdata", ".trace", ".data"):
        b, vs, rp, rs, _ = [s for s in secs if s[4] == name][0]
        buf = d[rp:rp + rs]
        for o in range(0, len(buf) - 4, 4):
            if struct.unpack_from("<I", buf, o)[0] in want:
                print("  %s+0x%x holds an RVA inside a replaced pair" % (name, o))
                found += 1
    print("  %d jump-table entr(ies) into a replaced pair" % found)
    return hits + found


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not args:
        raise SystemExit(__doc__.strip().splitlines()[0])
    path = args[0]
    n = int(args[1]) if len(args) > 1 else int(re.search(r"hdr(\d+)", path).group(1))

    d = open(H.EXE, "rb").read()
    secs = H.sections(d)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True

    bad = check(path, n, md, d, secs)
    if "--inbound" in sys.argv:
        print("anything aimed inside the replaced bytes:")
        bad += inbound(md, d, secs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
