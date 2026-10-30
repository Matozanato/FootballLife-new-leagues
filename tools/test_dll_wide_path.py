"""python tools/test_dll_wide_path.py

B294 (Pelda 30.10.): the game in "C:\\fůtbal lajf\\..." -- every module of ours said
"LoadLibraryA failed (err 126)" and the leagues had no fixtures. ctx.sider_dir is UTF-8 and
LoadLibraryA reads a name in the system's code page, so a folder named with a letter outside
plain English ones was a folder that does not exist.

Every module that loads a DLL of ours now goes through load_dll (LoadLibraryW on the UTF-8 path
turned into UTF-16, declared under the module's own name), and a path a DLL opens itself goes
through ansi_path. This reads the modules the pack ships: no LoadLibraryA on a path of ours, and
each helper as it should be.
No game.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbpack

SIDER = os.path.join(os.path.dirname(HERE), "sider")
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1


def lua(name):
    for d in (SIDER, os.path.join(SIDER, "experimental")):
        p = os.path.join(d, name + ".lua")
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
    return None


loaders = 0
for m in lbpack.ORDER:
    src = lua(m)
    if src is None or "LoadLibrary" not in src:
        continue
    loaders += 1
    calls = re.findall(r"LoadLibraryA\(([^)]*)\)", src)
    ok("%s: LoadLibraryA only inside load_dll, on its fallback" % m,
       [c for c in calls if c.strip() not in ("const char*", "path")] == [])
    ok("%s: the DLL is loaded through load_dll" % m, "load_dll(dllpath)" in src)
    helper = src[src.index("local function load_dll(path)"):]
    helper = helper[:helper.index("\nend\n")]
    ok("%s: load_dll turns UTF-8 (65001) into UTF-16 for LoadLibraryW" % m,
       "_MultiByteToWideChar(65001" in helper and "_LoadLibraryW(w)" in helper)
    # Sider's sandbox has no pcall, so a declaration that clashed with another module's would stop
    # the module: the wide calls go under the module's own names, as fl26slotnames does
    for api in ("LoadLibraryW", "MultiByteToWideChar"):
        ok("%s: %s declared under its own name" % (m, api),
           re.search(r"%s_%s\([^;]*\)\s*__asm__\(\"%s\"\);" % (m, api, api), src) is not None)
    ok("%s: no pcall (Sider's modules do not have it)" % m, re.search(r"(?<![\w-])pcall\(", src) is None)
    for name in ("fl26_join_install_t", "fl26_regen_faces_load_t"):
        if name in src:
            ok("%s: the path the DLL opens itself goes through ansi_path" % m, "ansi_path(" in src
               and "local function ansi_path(path)" in src)

ok("every module of the pack that loads a DLL was read (8)", loaders == 8)
print("test_dll_wide_path: %d checks OK" % N)
