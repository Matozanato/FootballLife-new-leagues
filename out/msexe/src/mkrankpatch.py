r"""Build the patch set that gives the league rank one more bit.

The rank of a league in its national pyramid (first division, second, third) lives in the top
TWO bits of the regulation flags word at +0x304, so it can only count to three -- which is why
our third, fourth and fifth divisions all carry the value 3 and the promotion/relegation UI
confuses them. Moving the field down to bits 29-31 gives it eight values.

Bit 29 is today the top bit of the group count (bits 24-29). The loader masks that count to
five bits before storing it (0x1414f828d: movzx edx, byte [rax+0x10]; and dl,0x1f), so bit 29
is never set by anything shipped, which is what makes it available.

Every instruction involved re-encodes to the same length, so this is an in-place byte patch
with no trampolines and no new memory:

  rank read    shr/sar r, 0x1e            -> 0x1d
               and/test r, 0xc0000000     -> 0xe0000000
               cmp r, 0x40000000/0x80000000/0xc0000000 -> 0x20000000/0x40000000/0x60000000
               and r, 0x3fffffff          -> 0x1fffffff   (record copier: "all but the rank")
  rank write   0x1414c9cc0 mask 0x3fffffff -> 0x1fffffff, 0x1414c9ccd shl 0x1e -> 0x1d
  group read   and r, 0x3f after shr r,0x18 -> 0x1f;  and r, 0x3f000000 -> 0x1f000000
  group write  0x1414c9e70 mask 0xc0ffffff -> 0xe0ffffff, 0x1414c9e7d and 0x3f -> 0x1f

Sites are found by walking every reference to +0x304 in .trace, decoding the instruction whose
DISPLACEMENT lands exactly there (capstone's disp_offset, so no guessing), and then following
the register the value went into. An idiom is only patched when it acts on that register -- a
cmp against 0x40000000 that happens to sit near the read proves nothing.

Excluded by hand: the three sites around 0x1422b9xxx. They look like the idiom but the shift is
applied to a value that never came from +0x304, and their structure has a +0xb98 field, so it
is not a regulation record at all.

Run it as `python tools/mkrankpatch.py <out dir>`: it writes rankpatches.txt to read and
rankpatches.lua, the table that goes into sider/fl26rank.lua between its header and footer.
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flpaths
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

EXCLUDE = [(0x1422b9000, 0x1422ba000)]
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'      # where the two listings go

d = open(flpaths.need_exe(), 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
opt = pe + 24
so = opt + struct.unpack_from('<H', d, pe + 20)[0]
for i in range(struct.unpack_from('<H', d, pe + 6)[0]):
    o = so + i * 40
    if d[o:o+8].rstrip(b'\0') == b'.trace':
        vsz, rva, rsz, po = struct.unpack_from('<IIII', d, o + 8)
        VA, PO, SIZE = 0x140000000 + rva, po, min(rsz, vsz)
body = d[PO:PO + SIZE]
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True

FAMILY = {}
for i, b in enumerate(['ax', 'cx', 'dx', 'bx', 'sp', 'bp', 'si', 'di']):
    for f in ('r' + b, 'e' + b, b, b[0] + 'l', b[0] + 'h'):
        FAMILY[f] = i
for i in range(8, 16):
    for s in ('', 'd', 'w', 'b'):
        FAMILY['r%d%s' % (i, s)] = i

def fam(t):
    return FAMILY.get(t.strip().strip(','))

def dst_of(op):
    return fam(op.split(',')[0])

def src_of(op):
    return fam(op.rsplit(',', 1)[1]) if ',' in op else None

CMP = {0x40000000: 0x20000000, 0x80000000: 0x40000000, 0xc0000000: 0x60000000}
patches = {}

def add(ins, new, role, note=''):
    if ins.address in patches: return
    if any(lo <= ins.address < hi for lo, hi in EXCLUDE): return
    text = ins.mnemonic + ' ' + ins.op_str + (' -- ' + note if note else '')
    patches[ins.address] = (bytes(ins.bytes), new, role, text)

def imm32(b, v):
    b = bytearray(b)
    struct.pack_into('<I', b, len(b) - 4, v)
    return bytes(b)

def imm8(b, v):
    b = bytearray(b)
    b[-1] = v
    return bytes(b)

def reads_304(ins):
    off = ins.encoding.disp_offset
    b = bytes(ins.bytes)
    if not off or off + 4 > len(b): return False
    return struct.unpack_from('<i', b, off)[0] == 0x304

i = body.find(b'\x04\x03\x00\x00')
while i >= 0:
    # Walk the candidate starts from the longest back: the extra bytes can only be legal
    # prefixes (REX and friends), which never stand alone, so the longest consistent decode is
    # the real instruction. Taking the shortest instead silently drops the REX and reads the
    # wrong register -- which is how `mov r9d, [rbx+0x304]` first looked like `mov ecx, ...`.
    for back in range(11, 0, -1):
        s = i - back
        if s < 0: continue
        g = md.disasm(body[s:s + 8 + 18 * 8], VA + s)
        try:
            first = next(g)
        except StopIteration:
            continue
        if first.encoding.disp_offset != back or not reads_304(first): continue
        if first.mnemonic not in ('mov', 'movzx', 'movsxd', 'and', 'or', 'xor', 'cmp', 'test'):
            continue

        if first.mnemonic == 'and' and first.op_str.startswith('dword'):
            v = int(first.op_str.rsplit(', ', 1)[1], 16)
            if v == 0x3fffffff:
                add(first, imm32(first.bytes, 0x1fffffff), 'rank-write', 'rank setter, keep 29 bits')
            elif v == 0xc0ffffff:
                add(first, imm32(first.bytes, 0xe0ffffff), 'group-write', 'group setter, keep bit 29')
            break

        dstf = dst_of(first.op_str)
        if dstf is None: break
        live, shifted24 = {dstf}, set()
        for k, ins in enumerate(g):
            if k >= 18: break
            op, dst, src = ins.op_str, dst_of(ins.op_str), src_of(ins.op_str)
            if ins.mnemonic in ('mov', 'movzx', 'movsxd'):
                if src is not None and src in live and dst is not None:
                    live.add(dst); shifted24.discard(dst)
                elif dst is not None:
                    live.discard(dst); shifted24.discard(dst)
                continue
            if dst is None or dst not in live: continue
            if ins.mnemonic in ('shr', 'sar'):
                if op.endswith(', 0x1e'): add(ins, imm8(ins.bytes, 0x1d), 'rank-read')
                elif op.endswith(', 0x3e'): add(ins, imm8(ins.bytes, 0x3d), 'rank-read')
                elif op.endswith(', 0x18'): shifted24.add(dst)
                else: live.discard(dst)
                continue
            if ins.mnemonic in ('and', 'test', 'cmp') and ', 0x' in op:
                try:
                    v = int(op.rsplit(', ', 1)[1], 16)
                except ValueError:
                    continue
                if ins.mnemonic in ('and', 'test') and v == 0xc0000000:
                    add(ins, imm32(ins.bytes, 0xe0000000), 'rank-read')
                elif ins.mnemonic == 'cmp' and v in CMP:
                    add(ins, imm32(ins.bytes, CMP[v]), 'rank-read')
                elif ins.mnemonic == 'and' and v == 0x3fffffff:
                    add(ins, imm32(ins.bytes, 0x1fffffff), 'rank-read', 'copier: all but the rank')
                elif ins.mnemonic == 'and' and v == 0x3f000000:
                    add(ins, imm32(ins.bytes, 0x1f000000), 'group-read')
                elif ins.mnemonic == 'and' and v == 0x3f and dst in shifted24:
                    add(ins, imm8(ins.bytes, 0x1f), 'group-read')
                # an `and` that isolates the rank leaves it in the same register, so the
                # compare that follows is still about the rank; any other `and` ends the trail
                if ins.mnemonic == 'and' and v not in (0xc0000000, 0x3fffffff):
                    live.discard(dst)
        break
    i = body.find(b'\x04\x03\x00\x00', i + 1)

# ---- second seed: the same two fields reached through the TOP BYTE, at +0x307 -----------
#
# The first pass above only ever looked at +0x304, so every access that reads the flags word
# one byte at a time was invisible to it -- and there are ten of them. Byte +0x307 is bits
# 24-31 of the word: bits 0-5 of the byte are the group count, bits 6-7 are the rank. So
#
#     movzx r, byte [reg+0x307] ; and r, 0x3f        is the group count, SIX bits
#     test byte [reg+0x307], 0x3f                    is "does it have any groups"
#
# and six bits is exactly one too many once the rank owns bit 29: a league of rank 5 (binary
# 101) sets bit 29, and an unnarrowed read of the group count then answers 32 + the real
# number. That is not a wrong label on a screen, it is a loop bound, which is how the first
# in-game test of the widened rank ended in a crash.
#
# The rank through the same byte is bits 6-7 -> bits 5-7, so: shr r,6 -> 5, and/test r,0xc0
# -> 0xe0, cmp r,0x40/0x80/0xc0 -> 0x20/0x40/0x60.
CMP_BYTE = {0x40: 0x20, 0x80: 0x40, 0xc0: 0x60}

def reads_307(ins):
    off = ins.encoding.disp_offset
    b = bytes(ins.bytes)
    if not off or off + 4 > len(b): return False
    return struct.unpack_from('<i', b, off)[0] == 0x307

i = body.find(b'\x07\x03\x00\x00')
while i >= 0:
    for back in range(11, 0, -1):
        s = i - back
        if s < 0: continue
        g = md.disasm(body[s:s + 8 + 18 * 8], VA + s)
        try:
            first = next(g)
        except StopIteration:
            continue
        if first.encoding.disp_offset != back or not reads_307(first): continue

        # the direct form: the mask is in the instruction that reads the byte
        if first.mnemonic in ('test', 'and', 'cmp') and first.op_str.startswith('byte'):
            try:
                v = int(first.op_str.rsplit(', ', 1)[1], 16)
            except ValueError:
                break
            if v == 0x3f:
                add(first, imm8(first.bytes, 0x1f), 'group-read', 'byte +0x307, six bits')
            elif v == 0xc0:
                add(first, imm8(first.bytes, 0xe0), 'rank-read', 'byte +0x307')
            break

        if first.mnemonic not in ('mov', 'movzx', 'movsxd'): break
        dstf = dst_of(first.op_str)
        if dstf is None: break
        live = {dstf}
        for k, ins in enumerate(g):
            if k >= 18: break
            op, dst, src = ins.op_str, dst_of(ins.op_str), src_of(ins.op_str)
            if ins.mnemonic in ('mov', 'movzx', 'movsxd'):
                if src is not None and src in live and dst is not None: live.add(dst)
                elif dst is not None: live.discard(dst)
                continue
            if dst is None or dst not in live: continue
            if ins.mnemonic in ('shr', 'sar'):
                if op.endswith(', 6'): add(ins, imm8(ins.bytes, 5), 'rank-read', 'byte +0x307')
                else: live.discard(dst)
                continue
            if ins.mnemonic in ('and', 'test', 'cmp') and ', 0x' in op:
                try:
                    v = int(op.rsplit(', ', 1)[1], 16)
                except ValueError:
                    continue
                if ins.mnemonic in ('and', 'test') and v == 0x3f:
                    add(ins, imm8(ins.bytes, 0x1f), 'group-read', 'byte +0x307, six bits')
                elif ins.mnemonic in ('and', 'test') and v == 0xc0:
                    add(ins, imm8(ins.bytes, 0xe0), 'rank-read', 'byte +0x307')
                elif ins.mnemonic == 'cmp' and v in CMP_BYTE:
                    add(ins, imm8(ins.bytes, CMP_BYTE[v]), 'rank-read', 'byte +0x307')
                if ins.mnemonic == 'and' and v not in (0xc0, 0x3f):
                    live.discard(dst)
        break
    i = body.find(b'\x07\x03\x00\x00', i + 1)


# the setters build their value in eax out of dl, so no read of the word reaches them
def fixed(va, old, new, role, note):
    got = d[va - VA + PO: va - VA + PO + len(old)]
    assert got == old, "0x%x is %s, expected %s" % (va, got.hex(), old.hex())
    patches[va] = (old, new, role, note)

fixed(0x1414c9ccd, bytes.fromhex('c1e01e'), bytes.fromhex('c1e01d'),
      'rank-write', 'shl eax, 0x1e -- rank setter, three bits now')
fixed(0x1414c9e7d, bytes.fromhex('83e03f'), bytes.fromhex('83e01f'),
      'group-write', 'and eax, 0x3f -- group setter, five bits now')

roles = {}
for a in patches:
    roles[patches[a][2]] = roles.get(patches[a][2], 0) + 1
out = sorted(patches.items())
with open(os.path.join(OUT, 'rankpatches.txt'), 'w') as f:
    for va, (old, new, role, text) in out:
        f.write("0x%-12x %-12s %-22s %-22s %s\n" % (va, role, old.hex(), new.hex(), text))
with open(os.path.join(OUT, 'rankpatches.lua'), 'w') as f:
    for va, (old, new, role, text) in out:
        f.write('  {va=0x%x, old="%s", new="%s", why="%s: %s"},\n'
                % (va, old.hex(), new.hex(), role, text.replace('"', "'")))
print("%d patches -- %s" % (len(patches), ", ".join("%s %d" % kv for kv in sorted(roles.items()))))
