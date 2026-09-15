"""python callindex.py [--rebuild]  -> build/refresh an exact call graph index for .trace

One linear capstone pass over the code section, recording every direct `call rel32`
as (target, caller). Written to $FL26_OUT/callindex.tsv so later queries are instant.

This is the exact counterpart to the approximate scan in xref.py: byte scanning for
call opcodes over 39 MB of x86 mostly lands mid-instruction, so callers found that way
have to be re-verified one at a time. Here the decode itself provides the alignment.

  python callindex.py                 # build if missing, then print stats
  python callindex.py 1414bb280       # list callers of a target
"""
import os, struct, sys
from capstone import *
import flpaths

OUT = flpaths.out_dir()
IDX = os.path.join(OUT, "callindex.tsv")


def code_section():
    d = open(flpaths.need_exe(), "rb").read()
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    imgbase = struct.unpack_from("<Q", d, pe + 24 + 24)[0]
    best = None
    for i in range(nsec):
        p = pe + 24 + opt + i * 40
        nm = d[p:p + 8].rstrip(b"\0").decode("latin1")
        vsz, va, rsz, ro = struct.unpack_from("<IIII", d, p + 8)
        if nm in (".trace", ".text"):
            if best is None or rsz > best[3]:
                best = (nm, imgbase + va, ro, rsz)
    nm, va, ro, rsz = best
    return d, nm, va, ro, rsz


def build():
    d, nm, va, ro, rsz = code_section()
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.skipdata = True
    n = 0
    os.makedirs(OUT, exist_ok=True)
    with open(IDX, "w", newline="\n") as fh:
        fh.write("# section %s va=%x size=%x\n" % (nm, va, rsz))
        for i in md.disasm(d[ro:ro + rsz], va):
            if i.mnemonic != "call":
                continue
            t = i.op_str
            if not t.startswith("0x"):
                continue            # indirect / register call
            fh.write("%s\t%x\n" % (t[2:], i.address))
            n += 1
    return n


def load():
    m = {}
    with open(IDX) as fh:
        for ln in fh:
            if ln.startswith("#"):
                continue
            t, c = ln.split()
            m.setdefault(int(t, 16), []).append(int(c, 16))
    return m


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--rebuild" in sys.argv or not os.path.exists(IDX):
        print("building call index (one linear pass, takes a few minutes)...")
        print("  %d direct calls -> %s" % (build(), IDX))
    m = load()
    if not args:
        print("%d distinct call targets indexed" % len(m))
        top = sorted(m.items(), key=lambda kv: -len(kv[1]))[:10]
        print("most-called targets:")
        for t, cs in top:
            print("  %x  %d callers" % (t, len(cs)))
    for a in args:
        t = int(a, 16)
        cs = sorted(set(m.get(t, [])))
        print("%x: %d callers" % (t, len(cs)))
        for c in cs:
            print("  %x" % c)


def starts():
    """sorted list of every address that is the target of a direct call

    A far more reliable function-start oracle than walking back to int3 padding: the
    compiler pads with a single 0xcc as often as two, so the walk-back silently runs
    past a boundary. Anything called directly is a function start by definition.
    """
    if not os.path.exists(IDX):
        build()
    s = set()
    with open(IDX) as fh:
        for ln in fh:
            if ln[0] == "#":
                continue
            s.add(int(ln.split("\t")[0], 16))
    return sorted(s)


def enclosing(va, tbl=None):
    """the largest known function start <= va"""
    import bisect
    tbl = tbl if tbl is not None else starts()
    k = bisect.bisect_right(tbl, va) - 1
    return tbl[k] if k >= 0 else None
