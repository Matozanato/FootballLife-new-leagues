"""Names go into the game's tables in letters its fonts have (B173, 20.10.2026: the Azeri Premier
League's Şəfa and Məmmədov showed a box for ə). pesdb.game_text at write time, Mod Studio's own
data keeps the name as it was.

    python tools/test_game_text.py [<unpacked *_fnt.bin> ...]

With font files (common/menu/font/pes_fnt.bin, plname_fnt.bin ... of the game's dt11_x64.cpk) it
also checks pesdb.FONT_RANGES against the letters they have.
"""
import os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pesdb
import mkleague as M
import playeredit as E

CASES = [("Şəfa Futbol Klubu", "Şafa Futbol Klubu"), ("Rəşad Məmmədov", "Raşad Mammadov"),
         ("Alin Șerban", "Alin Şerban"), ("Nichita Moțpan", "Nichita Moţpan"), ("Țitruș", "Ţitruş"),
         ("Mustafa Yiǧitoǧlu", "Mustafa Yiğitoğlu"), ("Július Szӧke", "Július Szöke"),
         ("Nguyễn Văn Quyết", "Nguyên Văn Quyêt"), ("Phạm Đức Huy", "Pham Đúc Huy"),
         ("Emi\u0307rhan Can", "Emirhan Can"), ("Luka Gorše\u200f", "Luka Gorše"),
         ("Yusuf Karadaǧ\u200e", "Yusuf Karadağ"), ("Guillermo Tegu\u0308e\u0301", "Guillermo Tegüé"),
         ("Al-Sulaikh\xa0Sport Club", "Al-Sulaikh Sport Club")]
# what the fonts have stays: Ə (only the small one is missing), Turkish, Polish, Czech, Nordic,
# Greek, Cyrillic, pinyin, and everything past U+20FF
SAME = ["Real Madrid", "Qarabağ Ağdam FK", "ƏLİYEV", "Kenan Yıldız", "Łukasz Skorupski", "Tomáš Souček",
        "Martin Ødegaard", "Hannes Þór Halldórsson", "Ολυμπιακός", "Зенит", "Црвена звезда", "Lǚ Wénjūn",
        "東京ヴェルディ", "전북 현대", "Dinamo Tbilisi", ""]


def font_codes(path):
    raw = pesdb.wesys_unpack(open(path, "rb").read())
    o = raw.find(b"WFNT")
    n, first = struct.unpack_from("<I", raw, o + 12)[0], struct.unpack_from("<I", raw, o + 20)[0]
    have = set()
    for i in range(n):
        c = struct.unpack_from("<I", raw, o + first + 16 * i)[0]     # a glyph's UTF-8 bytes
        try:
            have.add(ord(c.to_bytes((c.bit_length() + 7) // 8 or 1, "big").decode("utf-8")))
        except (UnicodeDecodeError, TypeError):
            pass
    return have


def main(fonts):
    n = 0
    for a, want in CASES:
        got = pesdb.game_text(a)
        assert got == want, (a, got, want)
        assert all(pesdb.font_has(c) for c in got), (a, got)
        n += 1
    for a in SAME:
        assert pesdb.game_text(a) == a, (a, pesdb.game_text(a))
        n += 1
    # the player's four name slots: the name and the shirt in letters the game has
    slots = E.name_slots("Rəşad Məmmədov")
    got = [E.cstr(slots[k * E.P_NAME_LEN:(k + 1) * E.P_NAME_LEN]) for k in range(4)]
    assert got == ["Raşad Mammadov", "MAMMADOV", "MAMMADOV", "Raşad Mammadov"], got
    n += 1
    # a club's name (mkleague.put: Team.bin names, regulation names), cut on a whole letter
    b = bytearray(70)
    M.put(b, 0, "Şəfa Futbol Klubu", 70)
    assert b.split(b"\0")[0].decode("utf-8") == "Şafa Futbol Klubu", b
    b = bytearray(5)
    M.put(b, 0, "Şəfa", 5)                    # Ş is two bytes, a one: "Şaf" and the end
    assert bytes(b) == "Şaf".encode("utf-8") + b"\0", b
    b = bytearray(2)
    M.put(b, 0, "Şəfa", 2)                    # no half of Ş
    assert bytes(b) == b"\0\0", b
    r = bytearray(2352)
    pesdb.reg_set_name(r, "Misli Premyer Liqası Ə ə")
    assert pesdb.cstr(r[0x14:0x14 + 115]) == "Misli Premyer Liqası Ə a"
    n += 3
    for path in fonts:                          # the ranges are the fonts' own
        have = font_codes(path)
        mine = {c for c in range(0xA0, 0x2100) if pesdb.font_has(chr(c))}
        theirs = {c for c in have if 0xA0 <= c < 0x2100}
        assert mine <= theirs, (path, sorted(hex(c) for c in mine - theirs)[:20])
        n += 1
    print("game text: %d checks passed" % n)


if __name__ == "__main__":
    main(sys.argv[1:])
