"""What this process's threads and memory did, read from Windows, not from Python (B480 round 3,
17.11.2026). In the exe test of beta4r the window stood still 3.9 s at the end of Build and 6.6 s
on Edit league > OK while its own thread took 0.00-0.95 s of the processor and the recorder's
watcher waited the whole stop for its turn: the lines of Python said nothing of who kept Python's
lock nor whether the process waited for its memory to come back from the disk (it was 3.2 GB
with 50-300 MB of it in RAM). The recorder (app.record_stalls) writes these numbers with each stop.

beat(): a heartbeat outside Python for tools/hangstacks.py. The window's thread counts it up from
a timer; another process sees it stop when that thread or Python's lock stands still (the window
itself still answers Windows then: hangstacks waited for a window that did not hang and wrote
nothing in beta4r)."""
import ctypes as C
import ctypes.wintypes as W
import os
import sys

_ON = sys.platform == "win32"
if _ON:
    _k = C.WinDLL("kernel32", use_last_error=True)
    _k.OpenThread.restype = C.c_void_p
    _k.OpenThread.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    _k.GetThreadTimes.argtypes = [C.c_void_p] + [C.c_void_p] * 4
    _k.CloseHandle.argtypes = [C.c_void_p]
    _k.CreateToolhelp32Snapshot.restype = C.c_void_p
    _k.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    _k.GetCurrentProcess.restype = C.c_void_p
    try:
        _k.GetThreadDescription.argtypes = [C.c_void_p, C.POINTER(C.c_wchar_p)]
    except AttributeError:          # before Windows 10 1607
        pass


class _TE(C.Structure):
    _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD), ("th32ThreadID", W.DWORD),
                ("th32OwnerProcessID", W.DWORD), ("tpBasePri", W.LONG), ("tpDeltaPri", W.LONG),
                ("dwFlags", W.DWORD)]


class _PMC(C.Structure):
    _fields_ = [("cb", W.DWORD), ("PageFaultCount", W.DWORD), ("PeakWorkingSetSize", C.c_size_t),
                ("WorkingSetSize", C.c_size_t), ("QuotaPeakPagedPoolUsage", C.c_size_t),
                ("QuotaPagedPoolUsage", C.c_size_t), ("QuotaPeakNonPagedPoolUsage", C.c_size_t),
                ("QuotaNonPagedPoolUsage", C.c_size_t), ("PagefileUsage", C.c_size_t),
                ("PeakPagefileUsage", C.c_size_t), ("PrivateUsage", C.c_size_t)]


class _MSE(C.Structure):
    _fields_ = [("dwLength", W.DWORD), ("dwMemoryLoad", W.DWORD), ("ullTotalPhys", C.c_ulonglong),
                ("ullAvailPhys", C.c_ulonglong), ("ullTotalPageFile", C.c_ulonglong),
                ("ullAvailPageFile", C.c_ulonglong), ("ullTotalVirtual", C.c_ulonglong),
                ("ullAvailVirtual", C.c_ulonglong), ("ullAvailExtendedVirtual", C.c_ulonglong)]


_HANDLES = {}       # thread id: (handle, name)


def _thread_ids(pid):
    out = []
    snap = _k.CreateToolhelp32Snapshot(0x4, 0)          # TH32CS_SNAPTHREAD
    if not snap or snap == C.c_void_p(-1).value:
        return out
    try:
        te = _TE()
        te.dwSize = C.sizeof(te)
        ok = _k.Thread32First(C.c_void_p(snap), C.byref(te))
        while ok:
            if te.th32OwnerProcessID == pid:
                out.append(te.th32ThreadID)
            ok = _k.Thread32Next(C.c_void_p(snap), C.byref(te))
    finally:
        _k.CloseHandle(snap)
    return out


def _name(h):
    try:
        p = C.c_wchar_p()
        if _k.GetThreadDescription(h, C.byref(p)) >= 0 and p.value:
            got = p.value
            _k.LocalFree(p)
            return got
    except Exception:
        pass
    return ""


def threads(refresh=True, tids=None):
    """{thread id: (user s, kernel s, name)} of this process's threads, and of those seen before
    that have ended since; refresh=False: only the threads seen before. tids: the threads to know
    (the recorder gives those of faulthandler's dump, the threads with Python in them) instead of
    the system's list of all threads -- thousands of calls, each giving Python's lock away and
    waiting for it again: with the window's thread busy the listing took the whole of a stop and
    the recorder missed it"""
    if not _ON:
        return {}
    now = None
    if tids is not None:
        now = set(tids)
    elif refresh:
        now = set(_thread_ids(os.getpid()))
    if now is not None:
        for tid in now:
            if tid not in _HANDLES:
                h = _k.OpenThread(0x0040 | 0x0800, False, tid)   # QUERY_(LIMITED_)INFORMATION
                if h:
                    _HANDLES[tid] = (h, _name(h))
    py = {}
    try:
        import threading
        py = {t.native_id: t.name for t in threading.enumerate()}
    except Exception:
        pass
    out = {}
    for tid, (h, name) in list(_HANDLES.items()):
        t = (C.c_ulonglong * 4)()
        if _k.GetThreadTimes(h, C.byref(t, 0), C.byref(t, 8), C.byref(t, 16), C.byref(t, 24)):
            out[tid] = (t[3] / 1e7, t[2] / 1e7, py.get(tid) or name)
    if now is not None:
        # threads that ended are read once more above (their handles keep their times), then let go
        for tid in [t for t in _HANDLES if t not in now]:
            _k.CloseHandle(_HANDLES.pop(tid)[0])
    return out


def memory():
    """{"faults", "ws_mb", "private_mb", "free_mb"} of this process and the PC ({} off Windows)"""
    if not _ON:
        return {}
    p = _PMC()
    p.cb = C.sizeof(p)
    out = {}
    if _k.K32GetProcessMemoryInfo(C.c_void_p(_k.GetCurrentProcess()), C.byref(p), p.cb):
        out.update(faults=p.PageFaultCount, ws_mb=p.WorkingSetSize / 2**20, private_mb=p.PrivateUsage / 2**20)
    m = _MSE()
    m.dwLength = C.sizeof(m)
    if _k.GlobalMemoryStatusEx(C.byref(m)):
        out["free_mb"] = m.ullAvailPhys / 2**20
    return out


def busiest(before, after, n=3):
    """the n threads that took the most processor time between two threads() readings:
    [(seconds, user, kernel, tid, name)]"""
    out = []
    for tid, (u, k, name) in after.items():
        u0, k0, _n = before.get(tid, (u, k, name)) if tid in before else (0.0, 0.0, name)
        out.append((u - u0 + k - k0, u - u0, k - k0, tid, name))
    out.sort(reverse=True)
    return out[:n]


def told(before_threads, after_threads, before_mem, after_mem):
    """one line for the recorder: who took the processor in a stop, and the memory"""
    parts = ["%.2f s (%.2f user) thread 0x%x %s" % (s, u, tid, name or "?")
             for s, u, _k2, tid, name in busiest(before_threads, after_threads) if s >= 0.005]
    line = "threads' processor time in it: " + ("; ".join(parts) or "none of them used the processor")
    if before_mem and after_mem and "faults" in before_mem and "faults" in after_mem:
        line += "; %d page faults; working set %.0f of %.0f MB private; %.0f MB of RAM free" % (
            (after_mem["faults"] - before_mem["faults"]) & 0xFFFFFFFF, after_mem["ws_mb"],
            after_mem["private_mb"], after_mem.get("free_mb", 0.0))
    return line


BEAT_NAME = "Local\\FL26ModStudioBeat-%d"


class beat:
    """an 8-byte counter in memory another process can map (hangstacks --beat): tick() it from the
    window's thread"""

    def __init__(self):
        import mmap
        self._m = mmap.mmap(-1, 8, tagname=BEAT_NAME % os.getpid()) if _ON else None
        self.n = 0

    def tick(self):
        if self._m is not None:
            self.n += 1
            self._m[:8] = self.n.to_bytes(8, "little")


# ---- memory back from the disk, without Python's lock (B480 round 3) ----
# In the exe test of beta4r the process was 3.2 GB with 50-300 MB of it in RAM after Make it
# editable (7.4 GB copied) and after Build (its process took the PC's memory for 19 minutes): every
# step after them -- the first opening of Leagues, Edit league > OK -- went over the recipe's
# players with each page coming back from the disk while Python's lock was held (6.6 s of a
# stopped window for 0.95 s of the processor). bring_back() reads the process's own memory with
# ReadProcessMemory: the pages come back in big reads, in a worker, with the lock let go (a
# trimmed 2 GB in 0.4 s here, the window's turns kept; a walk of it after: 2 page faults instead
# of 400,000). It reads only; a region freed meanwhile makes that read fail, never crash.

class _MBI(C.Structure):
    _fields_ = [("BaseAddress", C.c_void_p), ("AllocationBase", C.c_void_p), ("AllocationProtect", W.DWORD),
                ("PartitionId", W.WORD), ("RegionSize", C.c_size_t), ("State", W.DWORD), ("Protect", W.DWORD),
                ("Type", W.DWORD)]


class _RANGE(C.Structure):
    _fields_ = [("VirtualAddress", C.c_void_p), ("NumberOfBytes", C.c_size_t)]


if _ON:
    _k.VirtualQuery.argtypes = [C.c_void_p, C.POINTER(_MBI), C.c_size_t]
    _k.VirtualQuery.restype = C.c_size_t
    _k.ReadProcessMemory.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
    _k.GetCurrentThread.restype = C.c_void_p
    try:
        _k.PrefetchVirtualMemory.argtypes = [C.c_void_p, C.c_size_t, C.c_void_p, W.ULONG]
    except AttributeError:
        pass


def _private_regions():
    """[(address, size)] of this process's committed private memory that can be read"""
    out, a, m = [], 0, _MBI()
    while _k.VirtualQuery(C.c_void_p(a), C.byref(m), C.sizeof(m)):
        base = m.BaseAddress or 0
        # MEM_COMMIT, MEM_PRIVATE, readable, not a guard page nor no-access
        if m.State == 0x1000 and m.Type == 0x20000 and m.Protect & 0xEE and not m.Protect & 0x101:
            out.append((base, m.RegionSize))
        a = base + m.RegionSize
        if a >= 1 << 47 or m.RegionSize == 0:
            break
    return out


def bring_back(stop=None):
    """this process's memory back in RAM, if Windows had put it out (for a worker thread: the reads
    let Python's lock go). Returns (MB read, seconds). stop(): True ends it early"""
    import time
    if not _ON:
        return 0, 0.0
    t = time.perf_counter()
    h = C.c_void_p(_k.GetCurrentProcess())
    regs = _private_regions()
    try:                        # from the page file in big reads first (Windows 8 and later)
        for i in range(0, len(regs), 512):
            part = regs[i:i + 512]
            arr = (_RANGE * len(part))(*[_RANGE(a, n) for a, n in part])
            _k.PrefetchVirtualMemory(h, len(part), arr, 0)
    except Exception:
        pass
    step = 1 << 20
    buf = C.create_string_buffer(step)
    got, n = C.c_size_t(), 0
    for a, size in regs:
        for off in range(0, size, step):
            if stop is not None and stop():
                return n >> 20, time.perf_counter() - t
            if _k.ReadProcessMemory(h, C.c_void_p(a + off), buf, min(step, size - off), C.byref(got)):
                n += got.value
    return n >> 20, time.perf_counter() - t


def low_memory_priority(thread=False):
    """the pages this process (thread=True: this thread) brings in -- the files it reads and
    copies, its own memory -- are the first Windows takes back when the PC is short of memory, not
    the window's (MEMORY_PRIORITY_LOW). For Build's process and the copy of Make it editable: their
    gigabytes of files pushed Mod Studio's own memory out to the disk (B480 round 3). True when set"""
    if not _ON:
        return False
    pri = W.ULONG(2)                                    # MEMORY_PRIORITY_LOW
    try:
        if thread:
            return bool(_k.SetThreadInformation(C.c_void_p(_k.GetCurrentThread()), 0, C.byref(pri), 4))
        return bool(_k.SetProcessInformation(C.c_void_p(_k.GetCurrentProcess()), 0, C.byref(pri), 4))
    except Exception:
        return False


def normal_memory_priority():
    """this thread back to MEMORY_PRIORITY_NORMAL (after low_memory_priority(thread=True))"""
    if not _ON:
        return False
    pri = W.ULONG(5)
    try:
        return bool(_k.SetThreadInformation(C.c_void_p(_k.GetCurrentThread()), 0, C.byref(pri), 4))
    except Exception:
        return False


_KEEPER = []


def keep_in(every=1.0, rest=15.0, room=1024):
    """a thread that brings this process's memory back in RAM (bring_back, Python's lock let go)
    once Windows has put much of it out and the PC has the room for it again. B480 round 3 (beta4r
    exe test, GigaPack): Build's process and Make it editable's copy pushed all but 50-300 MB of
    Mod Studio's 3.2 GB out; every click after it then took its pages back one by one on the
    window's thread, with Python's lock held: Edit league > OK 6.2 s, the end of Build 3.9 s, Make
    it editable 2.3-3.5 s, Leagues 1.2 s of a stopped window. It looks once a second (two calls
    to Windows); it reads nothing while the PC is short of memory (that would push out the game or
    the others), nor more often than every `rest` seconds. Started once; True when it runs"""
    if not _ON or _KEEPER:
        return bool(_KEEPER)
    import threading
    import time

    def run():
        last, wait = 0.0, rest
        while True:
            time.sleep(every)
            try:
                m = memory()
                priv, ws, free = m.get("private_mb", 0), m.get("ws_mb", 0), m.get("free_mb", 0)
                out = priv - ws
                if out < 400 or ws > 0.7 * priv or free < out + room or time.monotonic() - last < wait:
                    continue
                bring_back()
                last = time.monotonic()
                after = memory().get("ws_mb", 0)
                # Windows took it right back (short of memory after all): ask much less often
                wait = rest if after - ws > 0.5 * out else min(wait * 4, 600.0)
            except Exception:
                return
    t = threading.Thread(target=run, daemon=True, name="memory-back")
    _KEEPER.append(t)
    t.start()
    return True
