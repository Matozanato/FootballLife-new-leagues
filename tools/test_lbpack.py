"""python tools/test_lbpack.py

The module bundles lbpack.py writes (fl26guards, fl26lateguards): every part is in, in order, and
the wrapper calls nothing Sider's Lua lacks -- pcall is not there (run023, 2026-10-07: both
bundles failed at init with "attempt to call global 'pcall'", so no guard of theirs was on).
"""
import os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbpack as P

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    for name, parts in P.BUNDLES.items():
        text = P.bundle(name, parts)
        wrapper = text[text.index("local PARTS = "):]
        ok("%s: no pcall / xpcall in the wrapper" % name, not re.search(r"\bx?pcall\s*\(", wrapper))
        at = [text.index("-- ==== %s.lua ====" % p) for p in parts]
        ok("%s: all %d parts, in order" % (name, len(parts)), at == sorted(at))
        ok("%s: init calls each part's init" % name, "p[2].init(ctx)" in wrapper)
    runtime_sources()
    livecpk_switch()
    portraits()
    print("%d cases passed" % N)


def runtime_sources():
    from pathlib import Path
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as sibling:
        dest = Path(sibling) / "sider"
        dest.mkdir()
        modules = ("fl26swiss", "fl26joindll", "fl26catlist")
        for name in modules:
            (dest / (name + ".lua")).write_text("-- old sibling copy")
        with patch.object(P, "PUBLIC", sibling), patch.object(P, "is_public", return_value=False):
            ok("CONCACAF loaders and catlist come from the current checkout", all(
                Path(P.source(name)).is_relative_to(Path(P.REPO)) for name in modules))


def livecpk_switch():
    from contextlib import redirect_stdout
    from io import StringIO
    from pathlib import Path
    from unittest.mock import patch
    import siderroot
    with tempfile.TemporaryDirectory() as scratch:
        ini = Path(scratch) / "sider.ini"
        for required in (False, True):
            ini.write_text('[sider]\nlivecpk.enabled = 0\ncpk.root = "./livecpk/_FL26Previous"\n')
            args = ["siderroot", "_FL26Next"] + (["--require-livecpk"] if required else [])
            with patch.object(siderroot, "INI", str(ini)), patch.object(sys, "argv", args), redirect_stdout(StringIO()):
                assert siderroot.main() == 0
            content = ini.read_text()
            ok("explicit LiveCPK setting is preserved unless the world requires it",
               f"livecpk.enabled = {int(required)}" in content and '#cpk.root' in content)
    catlist = Path(P.source("fl26catlist")).read_text(encoding="utf-8")
    guard = catlist.split("local function install_links(world)", 1)[1].split("local stub", 1)[0]
    ok("catlist empty-links guard uses Sider-supported iteration",
       "pairs(down)" in guard and not re.search(r"\bnext\s*\(", guard))


def portraits():
    """the pack's portraits go out at the game's own size (FL27 died on 180 ones, 02.11.)"""
    from PIL import Image
    with tempfile.TemporaryDirectory() as root:
        d = os.path.join(root, "common", "render", "symbol", "player", "regen")
        os.makedirs(d)
        Image.new("RGBA", (180, 180), (200, 150, 120, 255)).save(os.path.join(d, "0.dds"), pixel_format="DXT5")
        Image.new("RGBA", (128, 128), (200, 150, 120, 255)).save(os.path.join(d, "1.dds"), pixel_format="DXT5")
        ok("portraits: the 180 one is made smaller, the 128 one left", P.game_portraits(root) == 1)
        with Image.open(os.path.join(d, "0.dds")) as im:
            ok("portraits: %dx%d DXT5" % (P.PORTRAIT, P.PORTRAIT),
               im.size == (P.PORTRAIT, P.PORTRAIT) and im.format == "DDS")
        ok("portraits: a second pass changes nothing", P.game_portraits(root) == 0)


if __name__ == "__main__":
    main()
