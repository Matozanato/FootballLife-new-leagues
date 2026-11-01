"""Build and run one of the C test harnesses in tools/native (test_*.c), for the test_*.py that
wrap them.

    import nativetest
    out = nativetest.run("test_rcal_days.c")      # its stdout; exits 0 with SKIPPED if it cannot build

The harnesses include fl26swiss.c (or fl26chain.c) with a test define and call its pure parts
with made-up data; nothing of the game runs. On Windows they are built with zig, as before (ZIG,
PATH, D:/dev/tools/zig-*/zig.exe, or out/tools/py/ziglang/zig.exe). On Linux and macOS the
system C compiler (CC, cc, gcc or clang; zig cc as a fallback) builds them for the machine
itself, with tools/native/hosttest/windows.h standing in for the Windows header: the few Win32
calls the pure parts make work on plain files there, the rest do nothing. Without a compiler the
test prints SKIPPED and passes, as before.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
HOSTTEST = os.path.join(NATIVE, "hosttest")
TMP = os.path.join(os.path.dirname(HERE), "out", "tmp")


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    for pat in ("D:/dev/tools/zig-*/zig.exe",
                os.path.join(os.path.dirname(HERE), "out", "tools", "py", "ziglang", "zig.exe")):
        found = sorted(glob.glob(pat))
        if found:
            return found[-1]
    return None


def compiler():
    """the command that compiles a harness here, or None"""
    if os.name == "nt":
        z = find_zig()
        return [z, "cc", "-O2", "-fno-sanitize=undefined", "-w"] if z else None
    for c in (os.environ.get("CC"), "cc", "gcc", "clang"):
        if c and shutil.which(c):
            return [c, "-O2", "-w", "-I", HOSTTEST]
    z = find_zig()
    return [z, "cc", "-O2", "-fno-sanitize=undefined", "-w", "-I", HOSTTEST] if z else None


def run(source, timeout=120):
    """build tools/native/<source> and run it in tools/native; returns the CompletedProcess"""
    cc = compiler()
    if not cc:
        print("SKIPPED: no C compiler (set ZIG to zig.exe on Windows, CC elsewhere)")
        sys.exit(0)
    os.makedirs(TMP, exist_ok=True)
    exe = os.path.join(tempfile.mkdtemp(dir=TMP), os.path.splitext(source)[0] + (".exe" if os.name == "nt" else ""))
    env = dict(os.environ)
    if cc[1] == "cc":                                   # zig
        env.setdefault("ZIG_GLOBAL_CACHE_DIR", os.path.join(os.path.dirname(HERE), "out", "tools", "zig-cache"))
        env.setdefault("ZIG_LOCAL_CACHE_DIR", env["ZIG_GLOBAL_CACHE_DIR"])
    subprocess.run(cc + [os.path.join(NATIVE, source), "-o", exe], check=True, cwd=NATIVE, env=env)
    r = subprocess.run([exe], capture_output=True, text=True, timeout=timeout, cwd=NATIVE)
    sys.stdout.write(r.stdout)
    return r
