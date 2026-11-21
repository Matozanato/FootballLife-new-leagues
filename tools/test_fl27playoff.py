"""Run the installed asset and Mod Studio installer regressions: python tools/test_fl27playoff.py GAME [CONTROL]."""

from pathlib import Path
import hashlib
import struct
import sys
import tempfile
from unittest.mock import patch

import leaguebuilder as builder
import lbpack
import mkplayoffbitmap as bitmap


def main(game, control):
    exe = game / "FL_2027.exe"
    assert bitmap.supported(exe)
    assert not bitmap.supported(game / "FL_2026.exe")
    stock = bitmap.stock_part(game)
    expected = bitmap.make(stock)
    assert hashlib.sha256(expected).hexdigest() == (
        "21619d49029069395f878c6fa34f51bcd31a5d75416dd89324a142f9f131688e"
    )
    if control:
        assert bitmap.make(stock, control.read_bytes()) == expected

    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        source = folder / "pack" / lbpack.FL27_PLAYOFF_DIR
        source.mkdir(parents=True)
        (source / "fl27playoff.lua").write_bytes(b"lua")
        (source / "fl27playoff.dll").write_bytes(b"dll")
        ini = folder / "sider.ini"
        original = '[sider]\ncpk.root = ".\\livecpk\\_FL26World"\nlua.module = "fl26rank.lua"\n'
        ini.write_text(original)
        asset = folder / "livecpk" / bitmap.ROOT / bitmap.PART

        def ini_lines(_):
            return str(ini), ini.read_text().splitlines()

        with patch.object(builder, "ini_lines", ini_lines), patch.object(builder, "keep_before"):
            with patch.object(builder.flpaths, "game_exe", return_value=folder / "FL_2026.exe"):
                builder.install_playoff_display(game, print, folder / "pack")
                assert ini.read_text() == original and not asset.exists()
            with patch.object(builder.flpaths, "game_exe", return_value=exe):
                builder.install_playoff_display(game, print, folder / "pack")
                assert asset.read_bytes() == expected
                assert (folder / "modules" / "fl27playoff.dll").read_bytes() == b"dll"
                activated = ini.read_text()
                roots = [line for line in activated.splitlines() if line.startswith("cpk.root")]
                assert len(roots) == 2 and bitmap.ROOT in roots[0]
                assert activated.index("fl26rank.lua") < activated.index("fl27playoff.lua")
                builder.install_playoff_display(game, print, folder / "pack")
                assert ini.read_text() == activated
                with patch.object(bitmap, "stock_part", side_effect=OSError("missing asset")):
                    builder.install_playoff_display(game, print, folder / "pack")
                    assert ini.read_text() == original
                builder.install_playoff_display(game, print, folder / "pack")
                override = folder / "livecpk" / "_FL26World" / bitmap.PART
                override.parent.mkdir(parents=True)
                override.write_bytes(b"other mod artwork")
                builder.install_playoff_display(game, print, folder / "pack")
                assert ini.read_text() == original and override.read_bytes() == b"other mod artwork"
                override.write_bytes(stock)
                builder.install_playoff_display(game, print, folder / "pack")
                assert ini.read_text() == activated
                archive = folder / "Data" / "dt11_x64.cpk"
                archive.parent.mkdir()
                for malformed in (b"CPK ", struct.pack("<8xQ", 1 << 48),
                                  struct.pack("<8xQ", 50) + b"truncated"):
                    archive.write_bytes(malformed)
                    builder.install_playoff_display(folder, print, folder / "pack")
                    assert ini.read_text() == original
                    builder.install_playoff_display(game, print, folder / "pack")
                    assert ini.read_text() == activated
            with patch.object(builder.flpaths, "game_exe", return_value=folder / "FL_2027.exe"):
                (folder / "FL_2027.exe").write_bytes(b"unsupported image")
                builder.install_playoff_display(game, print, folder / "pack")
                assert ini.read_text() == original
    print("FL27 installed asset, control equivalence, installer priority, repeat install and fallback passed")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
