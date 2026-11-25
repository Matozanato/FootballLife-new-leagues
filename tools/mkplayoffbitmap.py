"""Build the FL27 per-widget bitmap from the verified game asset."""

import argparse
import hashlib
from pathlib import Path
import struct

import afp
import cpkread


PART = "common/menu/parts/cmnIconRankPromotion.bin"
STOCK_SHA256 = "92bef6fe9937e618d5ee65be7eebcf61783d50fc27636d26148b1e4d9495ea99"
PICTURE = "cmnIconRankPromotion-updown-playoff"
CELL = 42
CONTROL_SHA256 = "69e5d8a83b219466105a9330e35482e0b8b5359f80d3e783dfa1fe3db3253b37"
EXE_SHA256 = "64382330cc98f0231dac69d4e977b1113a3b0aa244614a65b99415a36542a2c0"
ROOT = "FL27 Playoff Indicators"
MODULE = "fl27playoff"


def supported(exe):
    exe = Path(exe)
    if exe.name.lower() != "fl_2027.exe":
        return False
    try:
        with exe.open("rb") as src:
            digest = hashlib.sha256()
            for block in iter(lambda: src.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest() == EXE_SHA256
    except OSError:
        return False


def stock_part(game):
    archive = game / "Data" / "dt11_x64.cpk"
    try:
        with archive.open("rb") as src:
            base, rows = cpkread.toc(src, max_metadata=64 * 1024 * 1024)
            for row in rows:
                if cpkread.path_of(row) == PART:
                    src.seek(base + row["FileOffset"])
                    size = row["FileSize"]
                    if not 0 < size <= 1024 * 1024:
                        raise ValueError("unexpected promotion icon size")
                    data = src.read(size)
                    if len(data) != size:
                        raise ValueError("truncated promotion icon")
                    if not data.startswith(b"CRILAYLA"):
                        return data
                    unpacked, compressed = struct.unpack_from("<II", data, 8)
                    if unpacked > 1024 * 1024 or 16 + compressed + 256 > size:
                        raise ValueError("invalid compressed promotion icon size")
                    return cpkread.crilayla(data)
    except (struct.error, IndexError, KeyError, TypeError, OverflowError, ValueError) as exc:
        raise ValueError(f"invalid archive {archive.name}: {exc}") from exc
    raise ValueError(f"{PART} is missing from dt11_x64.cpk")


def orange_tile(package):
    texture = package.txdt(0)
    width, height = struct.unpack_from(">HH", texture, 0x10)
    if (width, height, texture[0x17]) != (126, CELL, 0x15):
        raise ValueError("unexpected promotion icon atlas")
    pictures = {name: rect for name, _, rect in package.pictures()}
    if pictures.get("cmnIconRankPromotion-updown-0") != (0, 85, 1, 167, 83):
        raise ValueError("unexpected green promotion tile bounds")
    tile = bytearray()
    for y in range(CELL):
        start = 0x40 + 4 * (y * width + CELL)
        tile.extend(texture[start:start + 4 * CELL])
    # The stock green uses RGB (0, 188, 32) blended toward white. Its
    # red channel records the blend. Keep the alpha and neutral pixels.
    for p in range(0, len(tile), 4):
        alpha, red, green, blue = tile[p:p + 4]
        if alpha and green > max(red, blue):
            coverage = 255 - red
            tile[p + 1:p + 4] = bytes((255, 255 - (128 * coverage + 127) // 255, red))
    return bytes(tile)


def ap2(package):
    entry = package.u32(package.fields(11)[0] + 4)
    _, size, offset = struct.unpack_from(">III", package.txp, entry)
    return bytes(package.txp[offset:offset + size])


def make(stock, control=None):
    if hashlib.sha256(stock).hexdigest() != STOCK_SHA256:
        raise ValueError("unrecognized FL27 27.1.1 stock icon part")
    original = afp.Package(stock)
    orange = orange_tile(original)
    width = 126
    if control is not None:
        if hashlib.sha256(control).hexdigest() != CONTROL_SHA256:
            raise ValueError("unrecognized working atlas-only control")
        atlas = afp.Package(control).txdt(0)
        for row in range(CELL):
            start = 64 + 4 * (row * width + CELL)
            source = 4 * row * CELL
            if atlas[start:start + 4 * CELL] != orange[source:source + 4 * CELL]:
                raise ValueError("generated orange bitmap differs from the working control")
    package = afp.Package(stock)
    package.add_argb_pictures([(PICTURE, bytes(orange))], cell=CELL)
    struct.pack_into(">I", package.txp, 12, len(package.txp))
    data = package.pack()

    result = afp.Package(data)
    if ap2(result) != ap2(original):
        raise ValueError("the stock movie was changed")
    stock_atlas = original.txdt(0)[64:]
    if result.txdt(0)[64:64 + len(stock_atlas)] != stock_atlas:
        raise ValueError("original atlas pixels were changed")
    if sorted(p for p in result.pictures() if p[0] != PICTURE) != sorted(original.pictures()):
        raise ValueError("original atlas picture bounds were changed")
    if (PICTURE, 3, (0, 1, 85, 83, 167)) not in result.pictures():
        raise ValueError("unexpected orange bitmap bounds")
    rebuilt_atlas = result.txdt(0)
    for row in range(CELL):
        source = 4 * row * CELL
        target = 64 + 4 * (row + CELL) * width
        if rebuilt_atlas[target:target + 4 * CELL] != orange[source:source + 4 * CELL]:
            raise ValueError("orange bitmap differs from the working control")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", type=Path)
    parser.add_argument("control", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    data = make(stock_part(args.game), args.control.read_bytes())
    asset = args.root / PART
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(data)
    print(asset)


if __name__ == "__main__":
    main()
