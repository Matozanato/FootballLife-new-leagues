r"""python tools/test_layout_sites.py -- the modules find the FL 2027 caps set's layout in its code.

Our DLLs and the late lua guards do not carry block offsets of their own for the FL 2027 set: they
read them at run time out of instructions fl26caps rewrites (tools/native/fl26layout.h, reg_off()
in fl26join/fl26chain, fl26match's table and cap, fl26ctlguard's today/user reads, the standings
counts fl26swiss/fl26join take from the code). So a set that moves the calendar or grows an array
(limits-headroom, 07.11.2026: 4140 match ids a day, 2000 regulations, 3600 standings tables) needs
no new constants -- as long as every one of those instructions is still the one the readers expect
and carries the new value. This lays sider/fl26caps.fl27.lua over the exe's bytes (no game, no
write) and decodes each site the way the module does, and checks sider/fl26regs2000.fl27.lua's
requirements against the same image.

Needs the FL 2027 exe: FL26_EXE=E:/FL/FL27/game/FL_2027.exe (skipped without it).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)
sys.path.insert(0, HERE)

N = 0

# the set's numbers (patchset.py --calendar-ids 4140 --caps regulations=2000 --standings-tables 3600 ...)
WANT = {"ids": 4140, "regs": 2000, "fixtures": 30000, "matches": 131000, "tables": 3600,
        "header": 1024, "players": 180017}
DAYS, EVENTS = 365, 0x94          # a day's ids, then its count (4 bytes) and 18 event slots


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %2d - %s" % (N, name))


def lua_patches(path):
    """[(va, old bytes, new bytes)] of a generated caps / regs module"""
    txt = open(path, encoding="utf-8").read()
    return [(int(v, 16), bytes.fromhex(o), bytes.fromhex(n))
            for v, o, n in re.findall(r'\{va=0x([0-9a-f]+), old="([0-9a-f]*)", new="([0-9a-f]*)"', txt)]


class Image:
    """the exe's bytes with a module's patches laid over them, read by virtual address"""

    def __init__(self, exe_path, patches):
        os.environ["FL26_EXE"] = exe_path
        import calwiden, flpaths
        # flpaths fixes its EXE once, at import: with FL26_DIR=<the FL26 game> set, the env line
        # above came too late and this read FL_2026.exe (16.11.2026). Point it at this exe.
        flpaths.EXE = exe_path
        self.exe = calwiden.Exe()
        self.over = {}
        self.mismatch = []
        for va, old, new in patches:
            have = self.exe.read(va, len(old)) if self.exe.off(va) is not None else None
            if have is not None and have != old:
                self.mismatch.append(va)
            for i, b in enumerate(new):
                self.over[va + i] = b

    def read(self, va, n):
        base = self.exe.read(va, n) if self.exe.off(va) is not None else bytes(n)
        return bytes(self.over.get(va + i, base[i]) for i in range(n))

    def site(self, va, op):
        """the dword after opcode bytes `op` at va, None when the bytes there are not `op`"""
        b = self.read(va, len(op) + 4)
        return int.from_bytes(b[len(op):], "little") if b[:len(op)] == op else None


def main():
    exe = os.environ.get("FL26_EXE", r"E:\FL\FL27\game\FL_2027.exe")
    if not os.path.exists(exe) or os.path.basename(exe).lower() != "fl_2027.exe":
        print("1..0 # skipped: FL26_EXE is not an FL_2027.exe")
        return
    caps = os.path.join(TOP, "sider", "fl26caps.fl27.lua")
    head = open(caps, encoding="utf-8").read(4096)
    ok("the install copy says regulations=%d players=%d" % (WANT["regs"], WANT["players"]),
       "regulations=%d" % WANT["regs"] in head and "players=%d" % WANT["players"] in head)
    img = Image(exe, lua_patches(caps))
    ok("every patch of the install copy finds the bytes it expects in the exe", not img.mismatch)

    # fl26layout.h, site by site (the same opcode bytes it checks before it trusts the value)
    today = img.site(0x140aed7b0, b"\x44\x0f\xb7\x89")
    cal = img.site(0x140aed7b8, b"\x48\x81\xc1")
    ok("lay_today / lay_calendar: both sites read (today 0x%x, calendar 0x%x)" % (today or 0, cal or 0),
       today is not None and cal is not None)
    size = (today - cal) // DAYS
    ok("365 days of 0x%x bytes between them, none left over" % size, (today - cal) % DAYS == 0)
    elem = 4 if img.read(0x141350347, 4) == b"\x44\x89\x24\x83" else 2
    ok("lay_day_elem: the scheduler appends u32 ids", elem == 4)
    ok("lay_day_ids: a day holds %d ids" % WANT["ids"], (size - EVENTS) // elem == WANT["ids"])
    import calwiden
    calwiden.ELEM = 4
    k, stride, idb, cnt, ev = calwiden.shape(WANT["ids"])
    ok("... the stride calwiden lays out for it (0x%x, %d blocks of 0x80)" % (stride, k), size == stride)
    ok("lay_regcap: the block constructor makes %d regulation records" % WANT["regs"],
       img.site(0x1414b87dd, b"\x41\xbe") == WANT["regs"])
    ok("lay_fixcap: %d fixture rounds" % WANT["fixtures"], img.site(0x1414bba84, b"\xbe") == WANT["fixtures"])
    for va, op, name in ((0x140caf678, b"\x48\x81\xc2", "lay_rounds"), (0x140ac8fe3, b"\x48\x8d\x8e", "lay_user"),
                         (0x140a9ac07, b"\x8b\x89", "lay_selcomp"), (0x140b07859, b"\x4d\x8d\xb7", "lay_ranking"),
                         (0x140f3c0b8, b"\x8b\x9e", "lay_fbase"), (0x140cd1691, b"\x8b\x9a", "lay_fans")):
        ok("%s: its instruction is still there" % name, img.site(va, op) is not None)
    block = img.site(0x1414b6f72, b"\xba")
    ok("today lies inside the edit block (0x%x of 0x%x)" % (today, block), today + 0x14 < block)

    # fl26join / fl26chain reg_off(): cmp word [rdx+r13+disp32], bx at 0x1415435a9
    reg = img.site(0x1415435a9, b"\x66\x42\x39\x9c\x2a")
    ok("reg_off: the regulation array at +0x%x, %d records of 0x314 inside the block" % (reg or 0, WANT["regs"]),
       reg is not None and reg + WANT["regs"] * 0x314 <= block)

    # fl26match: the lookup's lea rax,[rcx+table] at +0x21, the allocator's cmp eax,cap at +0x26
    look, alloc = img.read(0x1414bc560, 0x28), img.read(0x1414bc710, 0x2b)
    ok("fl26match: the lookup and allocator signatures", look[:7] == bytes.fromhex("48895c241056be")
       and look[11:14] == b"\x44\x0f\xb7" and look[0x21:0x24] == b"\x48\x8d\x81" and alloc[0x26] == 0x3d)
    ok("fl26match: the match table holds %d" % WANT["matches"],
       int.from_bytes(alloc[0x27:0x2b], "little") == WANT["matches"])
    sched = img.site(0x14158bde2, b"\x49\x8d\xb7")
    ok("fl26match: the clubs' schedules are the table 0xc past today (fl26ctlguard's controller table)",
       sched == today + 0xc)

    # fl26ctlguard: the team lookup's lea / count and the user club read it checks first
    ok("fl26ctlguard: lea rdi,[r8+teams] and mov eax,[r8+count] in the team lookup",
       img.site(0x1414bcade, b"\x49\x8d\xb8") is not None and img.site(0x1414bcb24, b"\x41\x8b\x80") is not None)

    # the standings counts fl26swiss / fl26join read from the patched code
    ok("standings: %d tables (cmp ebx at 0x14158f381)" % WANT["tables"],
       img.site(0x14158f381, b"\x81\xfb") == WANT["tables"])
    hdr = img.read(0x1414fd4e3, 6)
    ok("standings: a header of %d (the dword at 0x1414fd4e5 the modules read)" % WANT["header"],
       int.from_bytes(hdr[2:6], "little") == WANT["header"])

    # fl26regs2000.fl27.lua: what it requires before it writes, on the same image
    regs = os.path.join(TOP, "sider", "fl26regs2000.fl27.lua")
    txt = open(regs, encoding="utf-8").read()
    req = [(int(v, 16), bytes.fromhex(w)) for v, w in re.findall(r'\{va=0x([0-9a-f]+), want="([0-9a-f]+)"', txt)]
    ok("fl26regs2000: its %d requirements hold over the install copy" % len(req),
       req and all(img.read(va, len(w)) == w for va, w in req))
    rp = lua_patches(regs)
    caps_vas = {va + i for va, _, new in lua_patches(caps) for i in range(len(new))}
    ok("fl26regs2000: its %d patches find their bytes and touch none of fl26caps'" % len(rp),
       all(img.read(va, len(old)) == old for va, old, _ in rp if va < 0x150000000)
       and not any(va + i in caps_vas for va, _, new in rp for i in range(len(new))))
    print("1..%d" % N)


if __name__ == "__main__":
    main()
