"""python ctxdump.py sites.json [--before N] -> disassembly context for each site

Reads the site list tailscan.py writes ({"sites":[{va, value, func, text}, ...]}) and
prints the instruction at each site preceded by `before` instructions of the same
function, so a register that is believed to hold the block can be traced back to where
it was loaded. Meant for reviewing a candidate relocation by eye.
"""

import json, sys
from capstone import *
import callindex

d, nm, sva, ro, rsz = callindex.code_section()
off_of = lambda va: ro + (va - sva)
md = Cs(CS_ARCH_X86, CS_MODE_64)


def window(f, va, before):
    start = max(f, va - before * 15)
    ins = list(md.disasm(d[off_of(start) : off_of(va) + 16], start))
    return ins[-before - 1 :]


def main(argv):
    sites = json.load(open(argv[1]))["sites"]
    before = 6
    if "--before" in argv:
        before = int(argv[argv.index("--before") + 1])
    only = argv[2] if len(argv) > 2 and not argv[2].startswith("--") else None
    for s in sites:
        if only and only not in s["value"]:
            continue
        f = int(s["func"], 16)
        va = int(s["va"], 16)
        print("\n%s  value %s  fn %s" % (s["va"], s["value"], s["func"]))
        for ins in window(f, va, before):
            print("   %-12x %s %s" % (ins.address, ins.mnemonic, ins.op_str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
