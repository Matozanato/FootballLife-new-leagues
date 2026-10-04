"""python livedump.py [--records N] [--array teams]  -> read the live game's arrays

Attaches to a running FL_2026.exe and reads the edit block out of it. Nothing is written.

The exe has no ASLR, so every address in patches/layout.json is a real address in the live
process, and the block itself is two dereferences away:

    0x143705e10          a global, the owner object          (from the one-instruction
    [owner + 0x48]       the edit block                       accessor at 0x1414b6a60)

This is the tool that answers what a disassembler cannot: how many slots are in use, what a
filled record looks like beside an empty one, and whether a patch set put an array where it
said it would.
"""
import ctypes, ctypes.wintypes as w, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAYOUT = json.load(open(os.path.join(ROOT, "patches", "layout.json")))
H = lambda s: int(s, 16) if isinstance(s, str) else s

OWNER_PTR = H(LAYOUT["getters"].get("owner_global", "0x143705e10"))
OWNER_FIELD = H(LAYOUT["getters"]["owner_field"])

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPPROCESS = 0x00000002

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", w.DWORD), ("cntThreads", w.DWORD),
                ("th32ParentProcessID", w.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", w.DWORD), ("szExeFile", ctypes.c_char * 260)]


def find_pid(name=b"FL_2026.exe"):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        raise OSError("CreateToolhelp32Snapshot failed")
    e = PROCESSENTRY32()
    e.dwSize = ctypes.sizeof(e)
    found = []
    ok = k32.Process32First(snap, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == name.lower():
            found.append(e.th32ProcessID)
        ok = k32.Process32Next(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    return found


class Mem:
    def __init__(self, pid):
        self.h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not self.h:
            raise OSError("OpenProcess failed for pid %d (error %d). Run as the same user."
                          % (pid, ctypes.get_last_error()))

    def read(self, addr, n):
        buf = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t(0)
        ok = k32.ReadProcessMemory(self.h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got))
        if not ok or got.value != n:
            return None
        return buf.raw

    def u32(self, a):
        b = self.read(a, 4)
        return None if b is None else int.from_bytes(b, "little")

    def u64(self, a):
        b = self.read(a, 8)
        return None if b is None else int.from_bytes(b, "little")

    def close(self):
        k32.CloseHandle(self.h)


def hexdump(b, base=0, width=16):
    out = []
    for i in range(0, len(b), width):
        chunk = b[i:i + width]
        h = " ".join("%02x" % c for c in chunk)
        t = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        out.append("    %06x  %-*s |%s|" % (base + i, width * 3, h, t))
    return "\n".join(out)



def dump_block(m, blk, path):
    """Copy the whole live edit block to a file, so the mapping work can go on offline."""
    size = H(LAYOUT["block"]["size_old"])
    step = 0x100000
    got = 0
    with open(path, "wb") as f:
        while got < size:
            n = min(step, size - got)
            b = m.read(blk + got, n)
            if b is None:                      # narrow down: find the readable prefix
                lo, hi = 0, n
                while lo < hi:
                    mid = (lo + hi + 0x1000) // 2 // 0x1000 * 0x1000
                    if mid <= lo:
                        break
                    if m.read(blk + got, mid) is not None:
                        lo = mid
                    else:
                        hi = mid - 0x1000
                b = m.read(blk + got, lo) or b""
                f.write(b)
                got += len(b)
                break
            f.write(b)
            got += n
    return got


def main():
    pids = find_pid()
    if not pids:
        print("FL_2026.exe is not running.")
        return 1
    if len(pids) > 1:
        print("several FL_2026.exe processes: %s -- using the first" % pids)
    m = Mem(pids[0])
    print("attached to pid %d" % pids[0])

    owner = m.u64(OWNER_PTR)
    print("owner global 0x%x -> 0x%x" % (OWNER_PTR, owner or 0))
    if not owner:
        print("The owner object is null: the edit data has not been loaded yet.")
        return 2
    blk = m.u64(owner + OWNER_FIELD)
    print("edit block   [owner+0x%x] -> 0x%x" % (OWNER_FIELD, blk or 0))
    if not blk:
        print("The block pointer is null.")
        return 2

    print("\ncounts:")
    for name, off in LAYOUT["counts"].items():
        if name.startswith("_"):
            continue
        print("  %-12s %6s   (at block+%s)" % (name, m.u32(blk + H(off)), off))

    if "--dump-block" in sys.argv:
        out = sys.argv[sys.argv.index("--dump-block") + 1]
        n = dump_block(m, blk, out)
        print("\nwrote %d of %s bytes to %s" % (n, LAYOUT["block"]["size_old"], out))
        m.close()
        return 0

    want = sys.argv[sys.argv.index("--array") + 1] if "--array" in sys.argv else "teams"
    nrec = int(sys.argv[sys.argv.index("--records") + 1]) if "--records" in sys.argv else 2
    a = LAYOUT["arrays"][want]
    stride = H(a["stride"])
    count = m.u32(blk + H(LAYOUT["counts"][want])) if want in LAYOUT["counts"] else None
    print("\n%s: stride 0x%x, cap %d, in use %s" % (want, stride, a["cap_old"], count))

    bases = {"original": H(a["base_old"])}
    mv = os.path.join(ROOT, "patches", "teams-move.json")
    if want == "teams" and os.path.exists(mv):
        bases["relocated"] = H(json.load(open(mv))["bases_new"]["teams"])
    for label, base in bases.items():
        print("\n--- %s base +0x%x ---" % (label, base))
        idxs = list(range(min(nrec, count or nrec)))
        if count:
            idxs += [count - 1, count]
        for i in sorted(set(idxs)):
            b = m.read(blk + base + i * stride, 0x60)
            if b is None:
                print("  record %d: unreadable" % i)
                continue
            print("  record %d @0x%x:" % (i, blk + base + i * stride))
            print(hexdump(b))
    if a.get("dummy"):
        print("\n--- %s dummy +%s ---" % (want, a["dummy"]))
        b = m.read(blk + H(a["dummy"]), 0x60)
        if b is not None:
            print(hexdump(b))
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
