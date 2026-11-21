"""python setcheck.py [patches/<set>.json]  -> does this set still fit the exe?

The Lua applier is all or nothing: it reads every target, compares it against the bytes
the generator recorded, and writes only if all of them match.  That is the right rule at
runtime, but it means a set that is off by one byte fails silently from the player's point
of view -- the game simply runs unmodified -- and the only way to find out is to start it.
This does the same verify pass offline, on the exe file, and says which site disagrees.

Pages past the image are verified too: the applier reserves them first, so reading there
returns zeros, and every patch that lands on one records an `old` of zeros.

    python setcheck.py                       the set the install copy was built from
    python setcheck.py patches/<set>.json    a named set
"""

import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import flpaths

H = lambda s: int(s, 16) if isinstance(s, str) else s


def image():
    return open(flpaths.need_exe(), "rb").read()


def sections(d):
    """[(name, va, size, raw offset)] for every section the file backs"""
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    base = struct.unpack_from("<Q", d, pe + 24 + 24)[0]
    out = []
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        name = d[o : o + 8].rstrip(b"\0").decode(errors="replace")
        vsz, va, rsz, ptr = struct.unpack_from("<IIII", d, o + 8)
        out.append((name, base + va, max(vsz, rsz), ptr))
    return out


def check(gen):
    d = image()
    secs = sections(d)
    bad, outside = [], 0
    for p in gen["patches"]:
        va = H(p["va"])
        old = bytes.fromhex(p["old"])
        have = None
        for _, sva, sz, ptr in secs:
            if sva <= va < sva + sz and ptr:
                off = ptr + (va - sva)
                have = d[off : off + len(old)]
                break
        if have is None:
            # past the image: the applier reserves the page, so it reads as zeros there
            outside += 1
            have = bytes(len(old))
        if have != old:
            bad.append((va, p["why"], have.hex(), p["old"]))
    return bad, outside


def main(argv):
    src = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else None
    if src is None:
        lua = open(os.path.join(ROOT, "sider", "fl26caps.lua")).read()
        name = lua.split("Set:")[1].split("\n")[0].strip()
        src = os.path.join(ROOT, "patches", name + ".json")
    gen = json.load(open(src))
    bad, outside = check(gen)
    print(
        "%s: %d patches (%d on reserved pages), %d disagree with the exe"
        % (os.path.basename(src), len(gen["patches"]), outside, len(bad))
    )
    for va, why, have, want in bad[:20]:
        print("  0x%x  %s\n     exe %s  set %s" % (va, why[:90], have, want))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
