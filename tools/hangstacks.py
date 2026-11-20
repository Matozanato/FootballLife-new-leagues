r"""python hangstacks.py <pid | exe name> <out.txt> [--after 2.0] [--every 2.0] [--now]

The native stacks of every thread of another process, written whenever its window has not answered
for --after seconds (and again every --every seconds while the stop lasts). For the stops of Mod
Studio's window that faulthandler cannot explain (16.11.2026: a worker "at" a line of Python for
10-15 s, Python's lock held, nothing under it in the Python stacks): the Python stacks say where
each thread's Python code is, not which thread keeps the lock nor what C call it sits in.

Each frame is module+offset and the nearest exported name (no .pdb is needed: python3xx.dll
exports enough to tell a thread that waits for the lock, PyEval_RestoreThread / take_gil under
PyEval_*, from the one that works). --now: write the stacks once at start, hung or not.

B480 round 3 (17.11.2026): a stop is also the heartbeat of Mod Studio's window standing still
(FL26_STALLS on: modstudio/procstat.beat), as the window itself goes on answering Windows while a
worker keeps Python's lock. Each dump starts with the process's memory (working set, private,
page faults since the dump before) and says of each thread how much processor it took since the
dump before and whether it sits in a system call (a wait) or runs with Python under it (the likely
holder of the lock; one that runs and takes no processor waits for its memory, paged out).
Windows, 64-bit, read-only for the target (its threads are suspended for the walk and resumed).
"""
import ctypes as C
import ctypes.wintypes as W
import sys
import time

k32 = C.WinDLL("kernel32", use_last_error=True)
u32 = C.WinDLL("user32", use_last_error=True)
dbg = C.WinDLL("dbghelp", use_last_error=True)

TH32CS_SNAPTHREAD, TH32CS_SNAPPROCESS = 0x4, 0x2
PROCESS_ALL = 0x1F0FFF
THREAD_ALL = 0x1F03FF
CONTEXT_FULL = 0x10000B
AMD64 = 0x8664


class THREADENTRY32(C.Structure):
    _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD), ("th32ThreadID", W.DWORD),
                ("th32OwnerProcessID", W.DWORD), ("tpBasePri", W.LONG), ("tpDeltaPri", W.LONG),
                ("dwFlags", W.DWORD)]


class PROCESSENTRY32W(C.Structure):
    _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD), ("th32ProcessID", W.DWORD),
                ("th32DefaultHeapID", C.c_void_p), ("th32ModuleID", W.DWORD), ("cntThreads", W.DWORD),
                ("th32ParentProcessID", W.DWORD), ("pcPriClassBase", W.LONG), ("dwFlags", W.DWORD),
                ("szExeFile", W.WCHAR * 260)]


class ADDRESS64(C.Structure):
    _fields_ = [("Offset", C.c_ulonglong), ("Segment", W.WORD), ("Mode", W.DWORD)]


class KDHELP64(C.Structure):
    _fields_ = [("pad", C.c_ulonglong * 13)]


class STACKFRAME64(C.Structure):
    _fields_ = [("AddrPC", ADDRESS64), ("AddrReturn", ADDRESS64), ("AddrFrame", ADDRESS64),
                ("AddrStack", ADDRESS64), ("AddrBStore", ADDRESS64), ("FuncTableEntry", C.c_void_p),
                ("Params", C.c_ulonglong * 4), ("Far", W.BOOL), ("Virtual", W.BOOL),
                ("Reserved", C.c_ulonglong * 3), ("KdHelp", KDHELP64)]


class SYMBOL_INFO(C.Structure):
    _fields_ = [("SizeOfStruct", W.ULONG), ("TypeIndex", W.ULONG), ("Reserved", C.c_ulonglong * 2),
                ("Index", W.ULONG), ("Size", W.ULONG), ("ModBase", C.c_ulonglong), ("Flags", W.ULONG),
                ("Value", C.c_ulonglong), ("Address", C.c_ulonglong), ("Register", W.ULONG),
                ("Scope", W.ULONG), ("Tag", W.ULONG), ("NameLen", W.ULONG), ("MaxNameLen", W.ULONG),
                ("Name", C.c_char * 512)]


class IMAGEHLP_MODULE64(C.Structure):
    _fields_ = [("SizeOfStruct", W.DWORD), ("BaseOfImage", C.c_ulonglong), ("ImageSize", W.DWORD),
                ("TimeDateStamp", W.DWORD), ("CheckSum", W.DWORD), ("NumSyms", W.DWORD),
                ("SymType", W.DWORD), ("ModuleName", C.c_char * 32), ("ImageName", C.c_char * 256),
                ("LoadedImageName", C.c_char * 256), ("pad", C.c_char * 2048)]


for f, res, args in (
        (k32.OpenProcess, W.HANDLE, [W.DWORD, W.BOOL, W.DWORD]),
        (k32.OpenThread, W.HANDLE, [W.DWORD, W.BOOL, W.DWORD]),
        (k32.CreateToolhelp32Snapshot, W.HANDLE, [W.DWORD, W.DWORD]),
        (k32.Thread32First, W.BOOL, [W.HANDLE, C.c_void_p]), (k32.Thread32Next, W.BOOL, [W.HANDLE, C.c_void_p]),
        (k32.Process32FirstW, W.BOOL, [W.HANDLE, C.c_void_p]), (k32.Process32NextW, W.BOOL, [W.HANDLE, C.c_void_p]),
        (u32.EnumWindows, W.BOOL, [C.c_void_p, W.LPARAM]),
        (k32.SuspendThread, W.DWORD, [W.HANDLE]), (k32.ResumeThread, W.DWORD, [W.HANDLE]),
        (k32.GetThreadContext, W.BOOL, [W.HANDLE, C.c_void_p]),
        (k32.GetThreadTimes, W.BOOL, [W.HANDLE] + [C.c_void_p] * 4),
        (k32.CloseHandle, W.BOOL, [W.HANDLE]),
        (dbg.SymInitialize, W.BOOL, [W.HANDLE, C.c_char_p, W.BOOL]),
        (dbg.SymRefreshModuleList, W.BOOL, [W.HANDLE]),
        (dbg.SymCleanup, W.BOOL, [W.HANDLE]),
        (dbg.SymFromAddr, W.BOOL, [W.HANDLE, C.c_ulonglong, C.POINTER(C.c_ulonglong), C.c_void_p]),
        (dbg.SymGetModuleInfo64, W.BOOL, [W.HANDLE, C.c_ulonglong, C.c_void_p]),
        (dbg.SymFunctionTableAccess64, C.c_void_p, [W.HANDLE, C.c_ulonglong]),
        (dbg.SymGetModuleBase64, C.c_ulonglong, [W.HANDLE, C.c_ulonglong]),
        (dbg.StackWalk64, W.BOOL, [W.DWORD, W.HANDLE, W.HANDLE, C.c_void_p, C.c_void_p, C.c_void_p,
                                   C.c_void_p, C.c_void_p, C.c_void_p]),
        (u32.SendMessageTimeoutW, C.c_size_t, [W.HWND, W.UINT, C.c_size_t, C.c_size_t, W.UINT, W.UINT,
                                               C.c_void_p]),
        (u32.GetWindowThreadProcessId, W.DWORD, [W.HWND, C.POINTER(W.DWORD)]),
        (u32.IsWindowVisible, W.BOOL, [W.HWND]),
        (k32.K32GetProcessMemoryInfo, W.BOOL, [W.HANDLE, C.c_void_p, W.DWORD])):
    f.restype, f.argtypes = res, args


class PMC(C.Structure):
    _fields_ = [("cb", W.DWORD), ("PageFaultCount", W.DWORD), ("PeakWorkingSetSize", C.c_size_t),
                ("WorkingSetSize", C.c_size_t), ("QuotaPeakPagedPoolUsage", C.c_size_t),
                ("QuotaPagedPoolUsage", C.c_size_t), ("QuotaPeakNonPagedPoolUsage", C.c_size_t),
                ("QuotaNonPagedPoolUsage", C.c_size_t), ("PagefileUsage", C.c_size_t),
                ("PeakPagefileUsage", C.c_size_t), ("PrivateUsage", C.c_size_t)]


_LAST = {}          # what the dump before this one saw: thread id: cpu seconds, "faults": count


def pid_of(name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    e = PROCESSENTRY32W()
    e.dwSize = C.sizeof(e)
    got = []
    ok = k32.Process32FirstW(snap, C.byref(e))
    while ok:
        if e.szExeFile.lower() == name.lower():
            got.append((e.th32ProcessID, e.th32ParentProcessID))
        ok = k32.Process32NextW(snap, C.byref(e))
    k32.CloseHandle(snap)
    return got


def threads_of(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    e = THREADENTRY32()
    e.dwSize = C.sizeof(e)
    out = []
    ok = k32.Thread32First(snap, C.byref(e))
    while ok:
        if e.th32OwnerProcessID == pid:
            out.append(e.th32ThreadID)
        ok = k32.Thread32Next(snap, C.byref(e))
    k32.CloseHandle(snap)
    return out


def windows_of(pid):
    out = []

    @C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def each(h, _l):
        p = W.DWORD()
        u32.GetWindowThreadProcessId(h, C.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            out.append(h)
        return True
    u32.EnumWindows(each, 0)
    return out


def answers(h, ms=300):
    """does the window's thread take a message within ms (WM_NULL, as Windows itself asks)"""
    r = C.c_size_t()
    return bool(u32.SendMessageTimeoutW(h, 0, 0, 0, 0x0002, ms, C.byref(r)))   # SMTO_ABORTIFHUNG


def name_at(hp, addr):
    mod = IMAGEHLP_MODULE64()
    mod.SizeOfStruct = 0x248                       # the size of the first (A) version of the struct
    where = "?"
    if dbg.SymGetModuleInfo64(hp, addr, C.byref(mod)):
        where = "%s+0x%x" % (mod.ModuleName.decode("ascii", "replace"), addr - mod.BaseOfImage)
    sym = SYMBOL_INFO()
    sym.SizeOfStruct, sym.MaxNameLen = 88, 500
    disp = C.c_ulonglong()
    if dbg.SymFromAddr(hp, addr, C.byref(disp), C.byref(sym)):
        where += "  %s+0x%x" % (sym.Name.decode("ascii", "replace"), disp.value)
    return where


def cpu(ht):
    t = (C.c_ulonglong * 4)()
    if not k32.GetThreadTimes(ht, C.byref(t, 0), C.byref(t, 8), C.byref(t, 16), C.byref(t, 24)):
        return 0.0, 0.0
    return t[3] / 1e7, t[2] / 1e7


def dump(pid, out, why, depth=48):
    hp = k32.OpenProcess(PROCESS_ALL, False, pid)
    if not hp:
        out.write("cannot open process %d (error %d)\n" % (pid, C.get_last_error()))
        return
    dbg.SymInitialize(hp, None, True)
    out.write("==== %s  %s  pid %d\n" % (time.strftime("%H:%M:%S"), why, pid))
    pm = PMC()
    pm.cb = C.sizeof(pm)
    if k32.K32GetProcessMemoryInfo(hp, C.byref(pm), pm.cb):
        before = _LAST.get("faults")
        out.write("memory: working set %d MB of %d MB private; %s page faults%s\n" % (
            pm.WorkingSetSize >> 20, pm.PrivateUsage >> 20, pm.PageFaultCount,
            "" if before is None else " (%d since the last dump)" % ((pm.PageFaultCount - before) & 0xFFFFFFFF)))
        _LAST["faults"] = pm.PageFaultCount
    ctx = C.create_string_buffer(1232 + 16)
    base = C.addressof(ctx)
    base += (16 - base % 16) % 16                  # CONTEXT must sit on 16 bytes
    for tid in threads_of(pid):
        ht = k32.OpenThread(THREAD_ALL, False, tid)
        if not ht:
            continue
        u, kk = cpu(ht)
        if k32.SuspendThread(ht) == 0xFFFFFFFF:
            k32.CloseHandle(ht)
            continue
        try:
            C.memset(base, 0, 1232)
            C.c_ulong.from_address(base + 0x30).value = CONTEXT_FULL
            if not k32.GetThreadContext(ht, base):
                continue
            rip = C.c_ulonglong.from_address(base + 0xF8).value
            rsp = C.c_ulonglong.from_address(base + 0x98).value
            rbp = C.c_ulonglong.from_address(base + 0xA0).value
            sf = STACKFRAME64()
            sf.AddrPC.Offset, sf.AddrPC.Mode = rip, 3
            sf.AddrStack.Offset, sf.AddrStack.Mode = rsp, 3
            sf.AddrFrame.Offset, sf.AddrFrame.Mode = rbp, 3
            frames = []
            for _ in range(depth):
                if not dbg.StackWalk64(AMD64, hp, ht, C.byref(sf), base, None,
                                       dbg.SymFunctionTableAccess64, dbg.SymGetModuleBase64, None):
                    break
                if not sf.AddrPC.Offset:
                    break
                frames.append(sf.AddrPC.Offset)
        finally:
            k32.ResumeThread(ht)
            k32.CloseHandle(ht)
        names = [name_at(hp, a) for a in frames]
        # B480 round 3: which thread works. A thread in a system call (ntdll!Nt*, win32u!NtUser*:
        # a wait, a sleep, a message loop) does not run Python then; one at user code with Python
        # under it is the likely holder of Python's lock, and one that took no processor since the
        # last dump while there waits for its memory to come in from the disk (a page fault)
        top = names[0] if names else ""
        in_call = ("ntdll+" in top or "win32u+" in top) and ("  Nt" in top or "  Zw" in top)
        has_py = any("python3" in n.lower() for n in names)
        cpu_was = _LAST.get(tid)
        _LAST[tid] = u + kk
        took = "" if cpu_was is None else ", %.2f s since the last dump" % (u + kk - cpu_was)
        if in_call:
            state = "in a system call (a wait)" + (", Python under it" if has_py else "")
        else:
            state = "RUNS, Python under it (the likely holder of Python's lock)" if has_py else "runs, no Python under it"
        out.write("-- thread %d (0x%x)  cpu so far %.2f s user + %.2f s kernel%s; %s\n"
                  % (tid, tid, u, kk, took, state))
        for a, n in zip(frames, names):
            out.write("   %016x  %s\n" % (a, n))
    out.write("\n")
    out.flush()
    dbg.SymCleanup(hp)
    k32.CloseHandle(hp)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    target, path = argv[0], argv[1]
    after = float(argv[argv.index("--after") + 1]) if "--after" in argv else 2.0
    every = float(argv[argv.index("--every") + 1]) if "--every" in argv else 2.0
    out = open(path, "a", encoding="utf-8")

    def find():
        if target.isdigit():
            return int(target)
        got = pid_of(target)
        # a one-file exe is two processes of the same name: the child has the window
        with_win = [p for p, _pp in got if windows_of(p)]
        return with_win[0] if with_win else None
    pid = None
    while pid is None:
        pid = find()
        if pid is None:
            time.sleep(1.0)
    out.write("watching pid %d, a stop of %.1f s or longer is written\n" % (pid, after))
    out.flush()
    if "--now" in argv:
        dump(pid, out, "asked for at start")
    hung_since, told = None, 0.0
    # B480 round 3 (17.11.2026): Mod Studio's window answers Windows (WM_NULL is taken by Qt's loop
    # alone) while a worker keeps Python's lock, so in beta4r this tool saw no stop at all. With
    # FL26_STALLS on, the window's thread counts a heartbeat up 10 times a second
    # (modstudio/procstat.beat): once it has moved, standing still for --after seconds is a stop
    import mmap
    try:
        beat = mmap.mmap(-1, 8, tagname="Local\\FL26ModStudioBeat-%d" % pid)
    except OSError:
        beat = None
    beat_val, beat_at, beat_moved = None, time.perf_counter(), False
    while True:
        time.sleep(0.25)
        if not threads_of(pid):
            out.write("%s the process is gone\n" % time.strftime("%H:%M:%S"))
            return 0
        now = time.perf_counter()
        hung = any(not answers(h) for h in windows_of(pid)[:4])
        if beat is not None:
            v = bytes(beat[:8])
            if v != beat_val:
                beat_moved = beat_moved or beat_val is not None
                beat_val, beat_at = v, now
            elif beat_moved and now - beat_at >= 0.6:
                hung = True
        if not hung:
            if hung_since is not None and told:
                out.write("%s answering again after %.1f s\n\n" % (time.strftime("%H:%M:%S"), now - hung_since))
                out.flush()
            hung_since, told = None, 0.0
            continue
        if hung_since is None:
            hung_since = min(now, beat_at) if beat_moved else now
        if now - hung_since >= after and now - told >= every:
            dump(pid, out, "the window or its heartbeat has not answered for %.1f s" % (now - hung_since))
            told = now


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
