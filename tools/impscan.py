r"""python impscan.py SET.json  ->  the patches the .trace attribution could not see

The exe carries a seventeen-megabyte `.impdata` section.  It is not data and it is
not encrypted: the protector moved whole functions out of `.trace` and left them
there verbatim, which is why a crash inside it disassembles cleanly once the bytes
are in front of you.  What it is not is *traced*, so every tool in this repository
that walks the `.trace` attribution is blind to it, and any edit-block offset a
function there carries stays at its shipped value while the same offset in `.trace`
is moved.

That is what killed the season at day 237.  `0x14151c240` is a one-line jump into
`0x144adc450`, a linear search of the regulation array by id:

    mov  r9d, [rdi + 0xd0bcf4]          the regulation count -- unrelocated
    ...
    imul rdx, rcx, 0x314
    cmp  word [rdx + rdi + 0xc12e9c], r10w    the id field -- unrelocated

With the array moved, `+0xd0bcf4` is no longer the count but whatever our layout
put there, and the loop read 48472 records off the shipped base and ran off the
end of the block.  The tail pad did not save it and could not: the walk is
unbounded.

The fix needs no new judgement.  Every instruction here is byte-for-byte one that
the `.trace` attribution has already seen, decided about and rewritten somewhere
else in the exe, so this reads the generated set, builds `old bytes -> new bytes`
from it, and applies the same rewrite at the `.impdata` copies.  A site whose
encoding the set does not already carry is printed and left alone rather than
guessed at.

    python impscan.py patches/<set>.json            list what it finds
    python impscan.py patches/<set>.json --json OUT write the patch records
"""
import bisect, json, os, re, struct, sys
from capstone import *
from capstone.x86 import X86_OP_MEM

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flpaths

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# What makes an offset worth chasing into `.impdata` is not that a patch mentions it.
# It is that the set moved it out of the shipped block and into the grown tail: the old
# value lands inside the original block and the new one past its end.  Without that
# test a set that also rewrites record shapes -- `--slots32` says `0x208 -> 0x408` --
# sends the scan hunting two-byte-ish constants that occur by the hundred in 398 MB,
# and it obligingly finds them.  249 patches instead of 23, every extra one wrong.
SIZE_OLD = 0x1877068
MD = Cs(CS_ARCH_X86, CS_MODE_64)
MD.detail = True


def section(d, want):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    base = struct.unpack_from("<Q", d, pe + 24 + 24)[0]
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        if d[o:o + 8].rstrip(b"\0").decode(errors="replace") == want:
            _, va, rsz, ptr = struct.unpack_from("<IIII", d, o + 8)
            return base + va, ptr, rsz
    raise SystemExit("no %s section" % want)


def rewrites(patches):
    """old bytes -> new bytes, from the generated set, keeping only what is unambiguous

    The same encoding can appear in the set with two different answers when the
    site belongs to the save copy rather than the edit block.  Those are dropped:
    an `.impdata` site cannot be told apart that way, so it is not rewritten at all
    rather than rewritten on a coin toss.
    """
    seen = {}
    for p in patches:
        o, n = p["old"].lower(), p["new"].lower()
        seen.setdefault(o, set()).add(n)
    return {o: next(iter(n)) for o, n in seen.items() if len(n) == 1}, \
           {o for o, n in seen.items() if len(n) > 1}


PAIR = re.compile(r"(0x[0-9a-f]+) -> (0x[0-9a-f]+)")


def moved(patches):
    """shipped block offset -> where the set moved it, read out of the set's own notes

    Nothing is hand-listed here.  Every patch the generator emits says in its `why`
    which offset it rewrote and to what, so the same sentence that documents the
    `.trace` edit is what tells this scanner to hunt that offset in `.impdata`.  An
    offset the set answers two ways -- the edit block and the save copy disagree --
    is dropped, because an `.impdata` site carries nothing that would tell them
    apart.
    """
    seen, label = {}, {}
    for p in patches:
        m = PAIR.search(p.get("why", ""))
        if not m:
            continue
        old, new = int(m.group(1), 16), int(m.group(2), 16)
        if not (0 < old < SIZE_OLD <= new):
            continue
        seen.setdefault(old, set()).add(new)
        label.setdefault(old, p["why"].split(":")[0])
    good = {o: next(iter(n)) for o, n in seen.items() if len(n) == 1}
    bad = {o for o, n in seen.items() if len(n) > 1}
    return good, bad, label


def entries(d, imp_va, imp_sz):
    """every address in `.impdata` that `.trace` jumps or calls into

    These are the front doors of the functions the protector moved out.  A four
    byte value that merely looks like an offset turns up by chance in a section
    this size, so a candidate only counts if a straight decode from the door in
    front of it actually walks onto it -- which is the difference between code and
    a coincidence in a table.
    """
    tr_va, tr_raw, tr_sz = section(d, ".trace")
    tr = d[tr_raw:tr_raw + tr_sz]
    out = []
    for i in range(len(tr) - 5):
        if tr[i] in (0xE8, 0xE9):
            t = tr_va + i + 5 + struct.unpack_from("<i", tr, i + 1)[0]
            if imp_va <= t < imp_va + imp_sz:
                out.append(t)
    out.sort()
    return out


def reached(seg, imp_va, door, want, const, limit=0x400):
    """walk from `door` and return the instruction that carries the value at `want`

    Decoding backwards from a displacement has no unique answer -- `cmp word ptr
    [rdx + rdi + 0xc12e9c], r10w` reads perfectly well as a three-byte-shorter `cmp
    dword` if you start late -- so the boundary is settled by decoding forwards
    from the door instead, which is the only reading the processor will ever take.
    """
    off = door - imp_va
    for ins in MD.disasm(seg[off:off + limit], door):
        if ins.address > want:
            return None
        if ins.address + ins.size > want:
            for op in ins.operands:
                if op.type == X86_OP_MEM and op.mem.disp == const:
                    return ins
            return None
        if ins.mnemonic == "int3":
            return None
    return None


def scan(patches, verbose=False):
    """the `.impdata` patches implied by a set of `.trace` patches"""
    d = open(flpaths.need_exe(), "rb").read()
    imp_va, imp_raw, imp_sz = section(d, ".impdata")
    seg = d[imp_raw:imp_raw + imp_sz]
    table, ambiguous = rewrites(patches)
    good, split, label = moved(patches)
    doors = entries(d, imp_va, imp_sz)
    taken = {p["va"].lower() for p in patches}

    out, unknown, skipped = [], [], []
    for const in sorted(good):
        pat = struct.pack("<I", const)
        i = seg.find(pat)
        while i >= 0:
            va = "0x%x" % (imp_va + i)
            k = bisect.bisect_right(doors, imp_va + i) - 1
            ins = reached(seg, imp_va, doors[k], imp_va + i, const) if k >= 0 else None
            if ins and va not in taken:
                asm = "%s %s" % (ins.mnemonic, ins.op_str)
                old_ins = bytes(ins.bytes).hex()
                if old_ins in ambiguous:
                    skipped.append((va, label.get(const, ""), asm))
                else:
                    out.append({"va": va,
                                "old": struct.pack("<I", const).hex(),
                                "new": struct.pack("<I", good[const]).hex(),
                                "why": "impdata %s: 0x%x -> 0x%x (%s)"
                                       % (label.get(const, "offset"), const, good[const], asm),
                                "asm": asm})
            i = seg.find(pat, i + 1)
    if verbose:
        for va, why, asm in skipped:
            print("  TWO ANSWERS %-14s %-26s %s" % (va, why, asm))
        print("%d offsets hunted, %d dropped as ambiguous in the set" % (len(good), len(split)))
        print("%d impdata patches, %d ambiguous" % (len(out), len(skipped)))
        for q in out:
            print("  %-14s %-26s %s" % (q["va"], q["why"].split(":")[0][8:], q["asm"]))
    return out


def main():
    gen = json.load(open(sys.argv[1]))
    out = scan(gen["patches"], verbose=True)
    if "--json" in sys.argv:
        dst = sys.argv[sys.argv.index("--json") + 1]
        json.dump(out, open(dst, "w"), indent=1)
        print("wrote " + dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
