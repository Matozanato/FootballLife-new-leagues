"""fl26confgroups.dll (FL 2027): Select Team and Competition Info by confederation, then country.

1. tools/native/test_confgroups.c -- fl26confgroups.c built natively with the game's functions as
   stand-ins, run without the game: the headers, confederation / country / league and Back, the game's own
   "cursor on this team / slot", a row added after init, a list left alone, Competition Info's
   pseudo regions, labels and a confederation's cups (the cases are listed in the .c).
2. When FL 2027's exe is on this PC (FL27_EXE, else E:/FL/FL27/game/FL_2027.exe): every byte check
   the DLL makes at install (the SIGS table, the vtable entries) against the file itself, so a
   typo in an expected byte is caught here and not as "confgroups: off" in sider.log.
   The numbers of a club's three lines (fl26_confgroups_numbers, one byte, FL 2027 only): its 25
   bytes are in that exe exactly once, at file offset 0x15080f6 = 0x141508af6, and the byte makes
   the instruction read the 40.0 instead of the 50.0.
3. The DLL as it is in tools/native, loaded into this Python (not FL_2027.exe): asked for the
   numbers over the very bytes FL 2027 has, it answers 1 and writes nothing.
4. The loader, sider/experimental/fl26confgroups.lua, run in Lua (lupa) with stand-ins for ffi
   and the DLL: FL_2026.exe is never asked for the numbers (and without a confgroups line the DLL
   is not even loaded there, as before); FL_2027.exe always, with any world, before the lists; a
   refusal or an older DLL leaves the lists as they were.

    python tools/test_confgroups_dll.py

Needs zig (ZIG, PATH, or D:/dev/tools/zig-*/zig.exe); without it part 1 says so and is skipped.
Part 4 needs lupa (pip install lupa); without it, it says so and is skipped.
No game is started.
"""
import glob, os, re, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "native")
SRC = os.path.join(NATIVE, "fl26confgroups.c")


def find_zig():
    z = os.environ.get("ZIG")
    if z and os.path.exists(z):
        return z
    z = shutil.which("zig")
    if z:
        return z
    found = sorted(glob.glob("D:/dev/tools/zig-*/zig.exe"))
    return found[-1] if found else None


def sections(path):
    raw = open(path, "rb").read()
    pe = struct.unpack_from("<I", raw, 0x3c)[0]
    nsec, optsz = struct.unpack_from("<H", raw, pe + 6)[0], struct.unpack_from("<H", raw, pe + 20)[0]
    base = struct.unpack_from("<Q", raw, pe + 24 + 24)[0]
    out = []
    for i in range(nsec):
        o = pe + 24 + optsz + 40 * i
        vsz, va, rsz, rp = struct.unpack_from("<IIII", raw, o + 8)
        out.append((base + va, vsz, rp, rsz))
    return raw, out


def read(raw, secs, va, n):
    for v, vsz, rp, rsz in secs:
        if v <= va < v + vsz and va - v + n <= rsz:
            return raw[rp + va - v:rp + va - v + n]
    raise AssertionError("0x%x is not in the file" % va)


checks = 0
zig = find_zig()
if zig:
    out = os.path.join(tempfile.mkdtemp(), "test_confgroups.exe")
    subprocess.run([zig, "cc", "-O2", "-fno-sanitize=undefined", "-w",
                    os.path.join(NATIVE, "test_confgroups.c"), "-o", out], check=True, cwd=NATIVE)
    r = subprocess.run([out], capture_output=True, text=True, timeout=120)
    sys.stdout.write(r.stdout)
    assert r.returncode == 0 and ", 0 failed" in r.stdout, "the drill-down checks failed"
    checks += 1
else:
    print("SKIPPED part 1: no zig (set ZIG to zig.exe)")

src = open(SRC, encoding="utf-8").read()
defs = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"^#define (\w+)\s+0x([0-9a-fA-F]+)\b", src, re.M)}
sigs = re.findall(r'\{ (\w+),\s+"([0-9a-f]+)", "([^"]+)" \}', src)
vts = re.findall(r"\{ (\w+) \+ (0x[0-9a-f]+),\s+(\w+),\s+\"([^\"]+)\" \}", src)
assert len(sigs) >= 20 and len(vts) == 8, (len(sigs), len(vts))
exe = os.environ.get("FL27_EXE", "E:/FL/FL27/game/FL_2027.exe")
if os.path.exists(exe):
    raw, secs = sections(exe)
    for name, hexs, what in sigs:
        got = read(raw, secs, defs[name], len(hexs) // 2).hex()
        assert got == hexs, "%s (%s, 0x%x): the exe has %s, the DLL expects %s" % (name, what, defs[name], got, hexs)
        checks += 1
    for vt, off, fn, what in vts:
        got = struct.unpack("<Q", read(raw, secs, defs[vt] + int(off, 16), 8))[0]
        assert got == defs[fn], "%s: 0x%x, the DLL expects %s 0x%x" % (what, got, fn, defs[fn])
        checks += 1
    # the three direct hooks cover whole instructions and nothing rip-relative
    for name, n, want in (("TSC_INSERT", 6, "405556574154"), ("TSC_PICK", 5, "4889742418"),
                          ("TSC_JUMP", 11, "4883ec38488b8100010000")):
        assert read(raw, secs, defs[name], n).hex() == want, name
        checks += 1
    print("the DLL's byte checks match %s (%d sites)" % (os.path.basename(exe), len(sigs) + len(vts)))
else:
    print("SKIPPED part 2: no FL 2027 exe at %s (set FL27_EXE)" % exe)
# ---- the numbers of a club's three lines (fl26_confgroups_numbers): one byte, FL 2027 only ----
NUM = "f30f1005326303010f2fc8770cf30f100529330901f30f5fc1"     # the 25 bytes at 0x141508af6
NUM_OFF = 0x15080f6                                             # where they are in the exe file
num_sig = re.search('^#define NUM_SIG_HEX +"([0-9a-f]+)"', src, re.M).group(1)
num_done = re.search('^#define NUM_DONE_HEX +"([0-9a-f]+)"', src, re.M).group(1)
assert num_sig == NUM and defs["NUM_SIG"] == 0x141508af6 and defs["NUM_BYTE"] == 0x141508b07 and defs["NUM_NEW"] == 0x21
checks += 1
changed = [i for i in range(25) if num_sig[2 * i:2 * i + 2] != num_done[2 * i:2 * i + 2]]
assert len(num_done) == 50 and changed == [defs["NUM_BYTE"] - defs["NUM_SIG"]] == [17], changed
assert (num_sig[34:36], num_done[34:36]) == ("29", "%02x" % defs["NUM_NEW"])
checks += 1
# on its own: not one of the lists' byte checks (a mismatch there turns the lists off, and the
# other way round), and reached through the exe's name only
assert not any(name.startswith("NUM_") for name, _hex, _what in sigs)
assert src.count("num_floor(") == 2 and "return num_floor(exe_is_fl27());" in src
assert "num_floor" not in src[src.index("int fl26_confgroups_install(uint64_t exe_base)"):]
checks += 1
if os.path.exists(exe):
    hits, i = [], raw.find(bytes.fromhex(NUM))
    while i >= 0:
        hits.append(i)
        i = raw.find(bytes.fromhex(NUM), i + 1)
    assert hits == [NUM_OFF], "the 25 bytes are in the exe at %s, not once at 0x%x" % ([hex(h) for h in hits], NUM_OFF)
    checks += 1
    vas = [v + NUM_OFF - rp for v, vsz, rp, rsz in secs if rp <= NUM_OFF < rp + rsz]
    assert vas == [defs["NUM_SIG"]] and vas[0] - NUM_OFF == 0x140000a00, [hex(v) for v in vas]
    assert read(raw, secs, defs["NUM_SIG"], 25).hex() == num_sig
    assert read(raw, secs, defs["NUM_BYTE"], 1) == bytes([0x29])
    checks += 1

    # what the movss reads, before and after: rip-relative from the instruction's end (the 21st byte)
    def floor_of(hexs):
        disp = struct.unpack("<i", bytes.fromhex(hexs)[17:21])[0]
        return struct.unpack("<f", read(raw, secs, defs["NUM_SIG"] + 21 + disp, 4))[0]

    assert (floor_of(num_sig), floor_of(num_done)) == (50.0, 40.0), (floor_of(num_sig), floor_of(num_done))
    checks += 1
    print("the numbers' 25 bytes: once in %s, file 0x%x = 0x%x; the byte reads 50.0 now, 40.0 once written"
          % (os.path.basename(exe), NUM_OFF, defs["NUM_SIG"]))
    exe26 = os.environ.get("FL26_EXE", "E:/FL/FL26/game/FL_2026.exe")
    if os.path.exists(exe26):
        raw26, secs26 = sections(exe26)
        same = read(raw26, secs26, defs["NUM_SIG"], 25).hex() == num_sig
        del raw26
        print("note: %s has %s 25 bytes there -- only the exe's name keeps FL26 out (parts 3 and 4)"
              % (os.path.basename(exe26), "the same" if same else "other"))
else:
    print("SKIPPED the numbers' bytes in the exe: no FL 2027 exe at %s (set FL27_EXE)" % exe)

# 3. the DLL as it ships (tools/native/fl26confgroups.dll), loaded into this process, which is
#    not FL_2027.exe: the numbers' export writes nothing, though the 25 bytes are there
dll = os.path.join(NATIVE, "fl26confgroups.dll")
if (os.name == "nt" and struct.calcsize("P") == 8 and os.path.exists(dll)
        and os.path.basename(sys.executable).lower() != "fl_2027.exe"):
    import ctypes
    lib = ctypes.WinDLL(dll)
    assert hasattr(lib, "fl26_confgroups_numbers"), (
        "tools/native/fl26confgroups.dll has no fl26_confgroups_numbers: build it (build-confgroups.sh)")
    lib.fl26_confgroups_numbers.argtypes, lib.fl26_confgroups_numbers.restype = [ctypes.c_uint64], ctypes.c_int
    lib.fl26_confgroups_log.argtypes = [ctypes.c_char_p, ctypes.c_int]
    img = (ctypes.c_ubyte * (0x1508af6 + 0x1000))()
    ctypes.memmove(ctypes.addressof(img) + 0x1508af6, bytes.fromhex(NUM), 25)
    before, text = bytes(img), ctypes.create_string_buffer(2048)
    lib.fl26_confgroups_log(text, 2048)
    rc = lib.fl26_confgroups_numbers(ctypes.addressof(img))
    lib.fl26_confgroups_log(text, 2048)
    assert rc == 1 and bytes(img) == before, "the shipped DLL wrote outside FL_2027.exe (%d)" % rc
    assert text.value == b"confgroups: team numbers: off not FL 2027" + bytes([10]), text.value
    checks += 1
    print("the shipped DLL in %s: the numbers' export answers 1 and writes nothing"
          % os.path.basename(sys.executable))
else:
    print("SKIPPED part 3: no 64-bit Windows Python or no tools/native/fl26confgroups.dll")

# 4. the loader (sider/experimental/fl26confgroups.lua) with stand-ins for ffi and the DLL: who is
#    asked for what, by the exe's name and the world file
LOADER = os.path.join(os.path.dirname(HERE), "sider", "experimental", "fl26confgroups.lua")
MOCK = """
local exe, dll_ok, has_numbers, numbers_rc = ...
local calls, logs, pending = {}, {}, ""
local function said(s) pending = pending .. s .. string.char(10) end
local exports = {
  fl26_confgroups_install = function(base) calls[#calls + 1] = "install"; said("confgroups: ok -- lists"); return 0 end,
  fl26_confgroups_log = function(buf, cap) buf.text = pending; pending = ""; return 0 end,
}
for _, k in ipairs({ "slot", "region", "head", "trace", "country", "cup", "cname", "emblem" }) do
  exports["fl26_confgroups_" .. k] = function() end
end
if has_numbers then
  exports.fl26_confgroups_numbers = function(base)
    calls[#calls + 1] = "numbers"
    said(numbers_rc == 0 and "confgroups: team numbers: ok -- one byte" or "confgroups: team numbers: off bytes")
    return numbers_rc
  end
end
ffi = {
  cdef = function() end,
  new = function() return {} end,
  string = function(buf) return buf.text or "" end,
  cast = function(ty, v) return v end,
  C = {
    fl26confgroups_MultiByteToWideChar = function() return 0 end,
    fl26confgroups_LoadLibraryW = function() return nil end,
    fl26confgroups_LoadLibraryA = function() calls[#calls + 1] = "load"; if dll_ok then return exports end end,
    fl26confgroups_GetProcAddress = function(h, name) return h[name] end,
    fl26confgroups_GetModuleHandleA = function() return 0x140000000 end,
    fl26confgroups_GetLastError = function() return 126 end,
    fl26confgroups_GetModuleFileNameA = function(_, buf) buf.text = exe; return #exe end,
  },
}
log = function(s) logs[#logs + 1] = s end
return calls, logs
"""


def lua_runtime():
    try:
        from lupa import luajit21 as lj
    except ImportError:
        try:
            from lupa import lua54 as lj
        except ImportError:
            return None
    return lj.LuaRuntime()


def loader_run(exe_path, world, dll_ok=True, has_numbers=True, numbers_rc=0):
    """what the loader does in a game whose exe is exe_path, with this world file (None: no file):
    (the DLL's calls in order, the sider.log lines)"""
    lua = lua_runtime()
    side = tempfile.mkdtemp()
    os.mkdir(os.path.join(side, "modules"))
    if world is not None:
        with open(os.path.join(side, "modules", "fl26world.txt"), "w", encoding="utf-8") as f:
            f.write(world)
    calls, logs = lua.execute(MOCK, exe_path, dll_ok, has_numbers, numbers_rc)
    module = lua.execute(open(LOADER, encoding="utf-8").read())
    module.init(lua.table_from({"sider_dir": side + os.sep}))
    shutil.rmtree(side, ignore_errors=True)
    return list(calls.values()), list(logs.values())


if lua_runtime() is None:
    print("SKIPPED part 4: no Lua runtime here (pip install lupa to run it)")
else:
    FL26 = os.sep.join(["E:", "FL", "FL26", "game", "FL_2026.exe"])
    FL27 = os.sep.join(["E:", "FL", "FL27", "game", "FL_2027.exe"])
    PLAIN = "league 300 7 2" + chr(10)                           # a world of no confgroups line
    LINED = PLAIN + "confgroups slots=7:0,13:1 regions=2:0,16:1 countries=7:10 cups=0:2" + chr(10)
    NOLINE = "confgroups: off no confgroups line in the world file"
    NOFILE = "confgroups: off no world file"
    OK = "confgroups: team numbers: ok -- one byte"
    # FL26: without a line the DLL is not loaded at all (as before), and it is never asked for the numbers
    for world, why in ((PLAIN, NOLINE), (None, NOFILE)):
        calls, logs = loader_run(FL26, world)
        assert calls == [] and logs == [why], (calls, logs)
        checks += 1
    calls, logs = loader_run(FL26, LINED)            # a line in FL26: the lists' install says no itself
    assert calls == ["load", "install"] and not any("team numbers" in l for l in logs), (calls, logs)
    checks += 1
    calls, logs = loader_run("C:/Games/PES2021.exe", LINED)
    assert "numbers" not in calls, calls
    checks += 1
    # FL 2027: the numbers with any world, before the lists and without them
    for world, why in ((PLAIN, NOLINE), (None, NOFILE)):
        calls, logs = loader_run(FL27, world)
        assert calls == ["load", "numbers"] and logs == [OK, why], (calls, logs)
        checks += 1
    for path in (FL27, FL27.upper(), "D:/My Games/FL 27/fl_2027.exe"):
        calls, logs = loader_run(path, LINED)
        assert calls == ["load", "numbers", "install"], (path, calls)
        assert logs == [OK, "confgroups: ok -- lists"], logs
        checks += 1
    # the numbers refused (other bytes in the exe): its line, and the lists go in all the same
    calls, logs = loader_run(FL27, LINED, numbers_rc=2)
    assert calls == ["load", "numbers", "install"], calls
    assert logs == ["confgroups: team numbers: off bytes", "confgroups: ok -- lists"], logs
    checks += 1
    # an older DLL (no such export): said once, the lists as before
    calls, logs = loader_run(FL27, LINED, has_numbers=False)
    assert calls == ["load", "install"] and logs[0].startswith("confgroups: team numbers: off"), (calls, logs)
    assert "newer fl26confgroups.dll" in logs[0] and logs[1:] == ["confgroups: ok -- lists"], logs
    checks += 1
    # the DLL did not load (an antivirus took it): both parts say so, nothing is called
    calls, logs = loader_run(FL27, LINED, dll_ok=False)
    assert calls == ["load", "load"] and len(logs) == 2, (calls, logs)
    assert all("LoadLibraryA failed (err 126)" in l for l in logs), logs
    assert logs[0].startswith("confgroups: team numbers: off") and logs[1].startswith("confgroups: off"), logs
    checks += 1
    print("the loader: FL_2026.exe is never asked for the numbers, FL_2027.exe always, before the lists")
print("test_confgroups_dll: %d checks OK" % checks)
print("ok")
