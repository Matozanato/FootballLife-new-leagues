"""python boundscan.py  -> every fixed array the code indexes, with its ceiling and record size

The engine indexes a fixed array by checking the index against a constant and then multiplying
it by the record size.  This finds every place that does and groups them by (bound, stride), so
a ceiling can be read off rather than guessed -- and so that raising one is costed honestly: the
site count is how many places have to agree.

It also answers a question by not answering it.  There is no array bounded at 1536, which is
where a club index kills a season (docs/bounded-arrays.md).

Needs capstone, and FL26_DIR (or FL26_EXE) pointing at the game.
"""
import os, re, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flpaths


def image():
    d = open(flpaths.need_exe(), "rb").read()
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    base = struct.unpack_from("<Q", d, pe + 24 + 24)[0]
    secs = []
    for i in range(nsec):
        off = pe + 24 + optsz + 40 * i
        name = d[off:off + 8].rstrip(b"\0").decode()
        vsz, va, rsz, rp = struct.unpack_from("<IIII", d, off + 8)
        secs.append((name, va, vsz, rp, rsz))
    return d, secs, base


def scan(section=".trace"):
    d, secs, base = image()
    name, sva, vsz, rp, rsz = [s for s in secs if s[0] == section][0]
    blob = d[rp:rp + rsz]
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.skipdata = True
    out = []
    # imul r64, r64, imm -- 48 69 /r imm32, or 48 6b /r imm8
    for m in re.finditer(rb"\x48[\x69\x6b]", blob):
        i = m.start()
        start = max(0, i - 24)
        ins = list(md.disasm(blob[start:i + 32], base + sva + start))
        for k, x in enumerate(ins):
            if x.address != base + sva + i or x.mnemonic != "imul":
                continue
            parts = [p.strip() for p in x.op_str.split(",")]
            if len(parts) != 3:
                break
            try:
                stride = int(parts[2], 16) if parts[2].startswith("0x") else int(parts[2])
            except ValueError:
                break
            if stride < 0x40:            # below a plausible record size it is arithmetic
                break
            bound = None
            for y in ins[max(0, k - 6):k]:
                tail = y.op_str.split(",")[-1].strip()
                if y.mnemonic == "cmp" and tail.startswith("0x"):
                    try:
                        bound = int(tail, 16)
                    except ValueError:
                        pass
            field = None
            for y in ins[k + 1:k + 4]:
                if y.mnemonic == "lea" and "+" in y.op_str and "0x" in y.op_str:
                    field = y.op_str
            if bound:
                out.append((x.address, bound, stride, field))
            break
    return out


def main():
    hits = scan()
    print("bound + imul stride sites: %d" % len(hits))
    grouped = {}
    for va, b, s, field in hits:
        grouped.setdefault((b, s), []).append((va, field))
    for (b, s), sites in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        if b < 8 or b > 0x20000:         # flags and masks, not array bounds
            continue
        print("bound %-8d stride %-8s sites %3d   e.g. %x  %s"
              % (b, hex(s), len(sites), sites[0][0], sites[0][1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
