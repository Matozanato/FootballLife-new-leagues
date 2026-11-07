"""Regression tests for custom player face appearance mappings.

Uses synthetic face.fpk files, not game assets.
Run: python3 tools/test_face_app_lines.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lbplayers


def make_face(root, source_id):
    win = root / "#Win"
    win.mkdir(parents=True)
    (root / "sourceimages").mkdir()
    texture = (
        f"/Assets/pes16/model/character/face/real/"
        f"{source_id}/sourceimages/"
    )
    (win / "face.fpk").write_bytes(
        b"synthetic-test\x00" + texture.encode("ascii") + b"\x00"
    )
    return str(root)


def check(name, actual, expected):
    assert actual == expected, (
        f"{name}: expected {expected!r}, got {actual!r}"
    )
    print(f"PASS: {name}")


def player_table(directory, ids):
    """Write synthetic WESYS Player.bin records."""
    import pesdb

    directory.mkdir(parents=True, exist_ok=True)
    raw = bytearray()
    for pid in ids:
        record = bytearray(lbplayers.P_REC)
        start = lbplayers.P_ID
        record[start:start + 4] = pid.to_bytes(4, "little")
        raw.extend(record)

    (directory / "Player.bin").write_bytes(
        pesdb.wesys_pack(bytes(raw))
    )


def test_world_lines(root, face):
    base = root / "base"
    world = root / "world"

    player_table(base, [100, 101])
    player_table(world, [
        100, 101, 200001, 200002, 200003, 200004
    ])

    check(
        "Consecutive generated face IDs are compressed",
        lbplayers.new_face_lines(str(base), str(world)),
        ["newfaces 200001-200004"],
    )

    check(
        "Custom face and portrait-only player are separated",
        lbplayers.new_face_lines(
            str(base),
            str(world),
            faces=[(200002, face)],
            portraits=[(200003, "synthetic-portrait")],
        ),
        [
            "newfaces 200001 200004",
            "newfaces3d 200003",
            "faceapp 200002:12345",
        ],
    )

    check(
        "Custom face takes precedence over a portrait-only face",
        lbplayers.new_face_lines(
            str(base),
            str(world),
            faces=[(200002, face)],
            portraits=[(200002, "synthetic-portrait")],
        ),
        [
            "newfaces 200001 200003-200004",
            "faceapp 200002:12345",
        ],
    )

    check(
        "Missing world player table falls back to face mappings",
        lbplayers.new_face_lines(
            str(base),
            str(root / "missing-world"),
            faces=[(200002, face)],
        ),
        ["faceapp 200002:12345"],
    )


def main():
    with tempfile.TemporaryDirectory(prefix="fl26-faceapp-") as tmp:
        root = Path(tmp)

        first = make_face(root / "first", "12345")
        second = make_face(root / "second", "36912")
        text_id = make_face(root / "text-id", "custom")

        check(
            "Face copied from another player",
            lbplayers.face_app_lines([(200001, first)]),
            ["faceapp 200001:12345"],
        )

        check(
            "Same source and target needs no mapping",
            lbplayers.face_app_lines([(12345, first)]),
            [],
        )

        check(
            "Multiple mappings keep their order",
            lbplayers.face_app_lines([
                (200001, first), (200002, second)
            ]),
            ["faceapp 200001:12345 200002:36912"],
        )

        check(
            "Mapping lines split at configured size",
            lbplayers.face_app_lines([
                (200001, first), (200002, second)
            ], per=1),
            ["faceapp 200001:12345", "faceapp 200002:36912"],
        )

        check(
            "Non-numeric source ID is not mapped",
            lbplayers.face_app_lines([(200003, text_id)]),
            [],
        )

        check(
            "Missing face folder is ignored",
            lbplayers.face_app_lines([
                (200004, str(root / "missing"))
            ]),
            [],
        )

        broken = root / "broken" / "#Win"
        broken.mkdir(parents=True)
        (broken / "face.fpk").write_bytes(b"invalid face")

        check(
            "Missing texture path is ignored",
            lbplayers.face_app_lines([
                (200005, str(broken.parent))
            ]),
            [],
        )

        test_world_lines(root, first)

    print("All 11 face appearance mapping tests passed.")


if __name__ == "__main__":
    main()
