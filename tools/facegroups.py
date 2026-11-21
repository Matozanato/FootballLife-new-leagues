r"""facegroups.py <fl26regen_faces.bin> [--write] -- B183 (pepponeee98, 21.10.): regens and new
players of Sweden, Norway, Finland ... mostly came out dark-skinned.

The face pack (fl26regen_faces.bin, made by regenfaces/mkpack.py 30.09.) gives a regen or a new
player one of ten faces of his part of the world. The Nordic nations are in "nweu" with England,
France's neighbours, Germany and the Netherlands, whose ten donors are skin 6, 1, 2, 2, 4, 3, 5,
6, 4, 1 (PlayerAppearance byte 37 & 7, 1 = lightest; SKIN-COLOR-FINDING.md): six of ten dark.

This adds group 9, "nord": the pack's own faces of skin 1-2 from nweu and eeu once more, the same
portraits, and puts the Nordic nations on it. Every other nationality keeps its group and its
faces; the DLL (fl26regen.c face_of) takes any group number. Without --write it only shows.

  pack: "FL26RF01", 512 bytes nationality -> group (0xff none), u32 n, n x (u8 group, u8 0,
        u16 portrait number, 56 appearance bytes)

17.11.2026 (mato: "obvious region errors + a new region"): group 10, "sea", South-East Asia, and
the nations the 30.09. map put in the wrong part of the world (REGIONS_1711, regroup()). "sas"
was South + South-East Asia + Oceania: only 22% of the GigaPack's new players with a sas face
were South Asian. The face pool (facepool.py) uses the new map; the faces of every group that
kept its nations stay the same bytes (facepool.REDRAWN)."""
import struct, sys

GROUPS = ["nweu", "seu", "eeu", "afr", "mena", "lat", "bra", "eas", "sas", "nord", "sea"]
NORD = GROUPS.index("nord")
SEA = GROUPS.index("sea")
NORDIC = {203: "Denmark", 206: "Faroe Islands", 207: "Finland", 213: "Iceland", 226: "Norway",
          237: "Sweden"}                       # Country.bin ids
# The 17.11. region map, on top of the 30.09./B183 one: nationality (Country.bin id; the same ids
# in FL26 and FL27, whose Country.bin is the same file) -> its group. sas keeps India 9, Pakistan
# (below), Bangladesh 3, Bhutan 4, Nepal 25, Sri Lanka 33, Maldives 22. Afghanistan 1 stays mena,
# with Iran and the three Central Asian nations moved there.
REGIONS_1711 = {
    # South-East Asia (sas until now): its own group
    5: ("sea", "Brunei"), 6: ("sea", "Cambodia"), 10: ("sea", "Indonesia"), 18: ("sea", "Laos"),
    21: ("sea", "Malaysia"), 24: ("sea", "Myanmar"), 29: ("sea", "Philippines"),
    32: ("sea", "Singapore"), 36: ("sea", "Thailand"), 38: ("sea", "Vietnam"),
    43: ("sea", "Timor-Leste"),
    # Polynesia and Micronesia (sas until now): Austronesian peoples like the islands of
    # South-East Asia, brown skin (the 3-4 band the sea faces have most) and black hair; nearer
    # those faces than Africa's or South Asia's. The Oceania ids without a Country.bin entry
    # (no player has one) go with them.
    161: ("sea", "American Samoa"), 163: ("sea", "Cook Islands"), 168: ("sea", "Samoa"),
    170: ("sea", "Tahiti"), 171: ("sea", "Tonga"), 176: ("sea", "Guam"), 184: ("sea", "Palau"),
    173: ("sea", "-"), 174: ("sea", "-"), 175: ("sea", "-"), 177: ("sea", "-"), 178: ("sea", "-"),
    179: ("sea", "-"), 180: ("sea", "-"), 181: ("sea", "-"), 182: ("sea", "-"), 183: ("sea", "-"),
    # Melanesia (sas until now): dark skin, the afr faces
    164: ("afr", "Fiji"), 165: ("afr", "New Caledonia"), 167: ("afr", "Papua New Guinea"),
    169: ("afr", "Solomon Islands"), 172: ("afr", "Vanuatu"),
    # mena until now
    27: ("sas", "Pakistan"),
    # eeu until now
    216: ("eas", "Kazakhstan"), 40: ("eas", "Kyrgyzstan"),
    240: ("mena", "Uzbekistan"), 41: ("mena", "Tajikistan"), 42: ("mena", "Turkmenistan"),
    # afr until now: Central America
    108: ("lat", "Belize"),
    # placed nowhere until now (any face of the pack): no Country.bin entry; the id between
    # Grenada 117 and Guatemala 119 of the alphabetical North American ids, most likely
    # Guadeloupe. With Haiti and the other Caribbean islands (the GigaPack has one player of it)
    118: ("afr", "Guadeloupe?"),
}


def regroup(nat):
    """the nationality map with REGIONS_1711 (done twice: the same)"""
    nat = bytearray(nat)
    for n, (g, _name) in REGIONS_1711.items():
        nat[n] = GROUPS.index(g)
    return nat
LIGHT = 2                                      # skin 1-2
SKIN = 4 + 33                                  # in a 60-byte face: group, 0, portrait, then the
                                               # appearance record after its id (byte 37 there)


def read(path):
    b = open(path, "rb").read()
    if b[:8] != b"FL26RF01":
        raise SystemExit("%s: not a face pack" % path)
    nat = bytearray(b[8:520])
    n = struct.unpack_from("<I", b, 520)[0]
    faces = [bytes(b[524 + i * 60:524 + (i + 1) * 60]) for i in range(n)]
    return nat, faces


def pack(nat, faces):
    return b"FL26RF01" + bytes(nat) + struct.pack("<I", len(faces)) + b"".join(faces)


def skin(face):
    return face[SKIN] & 7


def nordic(nat, faces):
    """the pack with group nord (done once: a pack that has it already comes back as it is)"""
    nat = bytearray(nat)
    if any(f[0] == NORD for f in faces):
        return nat, list(faces)
    light = [f for f in faces if f[0] in (GROUPS.index("nweu"), GROUPS.index("eeu")) and skin(f) <= LIGHT]
    if not light:
        raise SystemExit("no light faces in nweu or eeu")
    for n in NORDIC:
        nat[n] = NORD
    return nat, list(faces) + [bytes([NORD]) + f[1:] for f in light]


def show(nat, faces):
    for g, name in enumerate(GROUPS):
        s = [skin(f) for f in faces if f[0] == g]
        if s:
            print("%-5s %2d faces, skin %s, nations %d" % (name, len(s), s, sum(1 for x in nat if x == g)))


def main(a):
    path = a[0]
    nat, faces = read(path)
    show(nat, faces)
    nat2, faces2 = nordic(nat, faces)
    if faces2 == faces:
        print("already has nord")
        return
    print("->")
    show(nat2, faces2)
    if "--write" in a:
        import shutil
        shutil.copy2(path, path + ".pre-b183")
        open(path, "wb").write(pack(nat2, faces2))
        print("written (the old one: %s.pre-b183)" % path)


if __name__ == "__main__":
    main(sys.argv[1:])
