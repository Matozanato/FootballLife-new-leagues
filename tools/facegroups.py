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
        u16 portrait number, 56 appearance bytes)"""
import struct, sys

GROUPS = ["nweu", "seu", "eeu", "afr", "mena", "lat", "bra", "eas", "sas", "nord"]
NORD = GROUPS.index("nord")
NORDIC = {203: "Denmark", 206: "Faroe Islands", 207: "Finland", 213: "Iceland", 226: "Norway",
          237: "Sweden"}                       # Country.bin ids
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
