"""python tools/test_kits_import.py

Tests for the five kit-import helpers of modstudio/pages/kits.py (is_kit_folder,
kit_folders, library_path, same_files, place). The helpers are loaded from their own source:
the ordinary import first, and when PySide6 (or the package) is missing they are pulled out of
kits.py with ast and exec'd with only os and shutil -- nothing is retyped and kits.py is not
touched. Builds fake folder trees under tempfile.mkdtemp(); plain asserts, one "ok" line each.
"""
import ast, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KITS = os.path.join(HERE, "modstudio", "pages", "kits.py")
WANT = ("is_kit_folder", "kit_folders", "library_path", "same_files", "place")


def load_helpers():
    sys.path.insert(0, HERE)
    try:
        from modstudio.pages import kits as K
        print("helpers: imported modstudio.pages.kits directly")
        return tuple(getattr(K, n) for n in WANT)
    except Exception as e:
        print("helpers: %s: %s -- loading the five functions from source with ast"
              % (type(e).__name__, e))
        src = open(KITS, encoding="utf-8").read()
        body = [n for n in ast.parse(src).body
                if isinstance(n, ast.FunctionDef) and n.name in WANT]
        if len(body) != len(WANT):
            raise RuntimeError("only found %d of the five helpers in %s" % (len(body), KITS))
        ns = {"os": os, "shutil": shutil, "__name__": "kits_helpers"}
        exec(compile(ast.Module(body=body, type_ignores=[]), KITS, "exec"), ns)
        return tuple(ns[n] for n in WANT)


is_kit_folder, kit_folders, library_path, same_files, place = load_helpers()
N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %2d - %s" % (N, name))


def write(path, data=b"x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def club(dirpath, order=True, p1=False):
    """a club kit folder: order.ini, or a p1 kit folder with its config.txt"""
    os.makedirs(dirpath, exist_ok=True)
    if order:
        write(os.path.join(dirpath, "order.ini"))
    if p1:
        write(os.path.join(dirpath, "p1", "config.txt"))


tmp = tempfile.mkdtemp(prefix="kitsimport-")
try:
    # ---- is_kit_folder ----
    a = os.path.join(tmp, "club_order"); club(a)
    ok("is_kit_folder: a folder with order.ini", is_kit_folder(a) is True)
    b = os.path.join(tmp, "club_p1"); club(b, order=False, p1=True)
    ok("is_kit_folder: a folder with only p1/config.txt", is_kit_folder(b) is True)
    p1only = os.path.join(tmp, "just_p1", "p1"); write(os.path.join(p1only, "config.txt"))
    ok("is_kit_folder: a bare p1 folder (config.txt, no p1 inside) is not a club",
       is_kit_folder(p1only) is False)
    empty = os.path.join(tmp, "empty"); os.makedirs(empty)
    ok("is_kit_folder: an empty folder", is_kit_folder(empty) is False)

    # ---- kit_folders ----
    ok("kit_folders: the club folder itself", kit_folders(a) == [a])
    lc = os.path.join(tmp, "finder", "League", "Club"); club(lc)
    ok("kit_folders: League/Club under root", kit_folders(os.path.join(tmp, "finder")) == [lc])
    plc = os.path.join(tmp, "pack", "Pack", "League", "Club"); club(plc)
    ok("kit_folders: Pack/League/Club under root", kit_folders(os.path.join(tmp, "pack")) == [plc])
    deep = os.path.join(tmp, "deep", "A", "B", "C", "Club"); club(deep)
    ok("kit_folders: depth 3 misses a club four levels down",
       kit_folders(os.path.join(tmp, "deep")) == [])
    ok("kit_folders: depth 4 finds it", kit_folders(os.path.join(tmp, "deep"), depth=4) == [deep])

    # ---- library_path ----
    root = os.path.join(tmp, "libroot")
    club2 = os.path.join(root, "Club"); club(club2)
    want = os.path.join(os.path.basename(os.path.dirname(club2)) or "Imported", os.path.basename(club2))
    ok("library_path: root is the club", library_path(club2, club2) == want)
    ok("library_path: Club directly under root",
       library_path(root, club2) == os.path.join(os.path.basename(root), "Club"))
    lc2 = os.path.join(root, "League", "Club"); club(lc2)
    ok("library_path: League/Club under root",
       library_path(root, lc2) == os.path.join("League", "Club"))

    # ---- place ----
    src = os.path.join(tmp, "src", "Club"); club(src); write(os.path.join(src, "kit.bin"), b"12345")
    lib = os.path.join(tmp, "library"); os.makedirs(lib)
    r = place(src, lib, "Club")
    ok("place: a fresh copy returns rel and copies the tree",
       r == "Club" and os.path.isfile(os.path.join(lib, "Club", "kit.bin"))
       and os.path.isfile(os.path.join(lib, "Club", "order.ini")))
    r2 = place(src, lib, "Club")
    ok("place: the same files are already there -> same path, no copy",
       r2 == "Club" and not os.path.exists(os.path.join(lib, "Club (2)")))
    write(os.path.join(lib, "Club", "extra.bin"), b"different-size")
    r3 = place(src, lib, "Club")
    ok("place: other files there -> the club goes next to it as \"Club (2)\"",
       r3 == "Club (2)" and os.path.isdir(os.path.join(lib, "Club (2)")))
    r4 = place(src, os.path.dirname(src), os.path.basename(src))
    ok("place: src == dst returns rel unchanged",
       r4 == "Club" and not os.path.exists(os.path.join(os.path.dirname(src), "Club (2)")))
    ok("same_files: an identical copy compares equal",
       same_files(src, os.path.join(lib, "Club (2)")) is True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("%d cases passed" % N)
