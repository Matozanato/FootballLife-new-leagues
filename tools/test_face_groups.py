"""python test_face_groups.py -- B183 (pepponeee98, 21.10.): Nordic regens and new players mostly
dark-skinned. facegroups.nordic on a made-up pack: the Nordic nations get group nord with only the
pack's light faces of nweu and eeu (the same portraits), every other nation and face stays as it
was, and done twice it is the same."""
import os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facegroups as F

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def face(group, k, skin):
    data = bytearray(56)
    data[F.SKIN - 4] = 0x28 | skin              # bits 3-5 hold another field: kept
    return bytes([group, 0]) + struct.pack("<H", k) + bytes(data)


def main():
    nweu, eeu, afr = F.GROUPS.index("nweu"), F.GROUPS.index("eeu"), F.GROUPS.index("afr")
    nat = bytearray(b"\xff" * 512)
    for n in list(F.NORDIC) + [204, 210]:       # England, Germany
        nat[n] = nweu
    nat[1] = afr
    faces = [face(nweu, 0, 6), face(nweu, 1, 1), face(nweu, 2, 4), face(nweu, 3, 2),
             face(eeu, 4, 1), face(eeu, 5, 3), face(afr, 6, 5)]
    path = os.path.join(os.environ.get("TEMP", "."), "fl26_b183_faces.bin")
    open(path, "wb").write(F.pack(nat, faces))
    nat0, faces0 = F.read(path)
    ok("a pack reads back as written", nat0 == nat and faces0 == faces)

    nat2, faces2 = F.nordic(nat0, faces0)
    nord = [f for f in faces2 if f[0] == F.NORD]
    ok("Sweden, Norway, Finland, Denmark, Iceland, Faroe on nord", all(nat2[n] == F.NORD for n in F.NORDIC))
    ok("nord holds only light faces (%s)" % [F.skin(f) for f in nord], nord and all(F.skin(f) <= 2 for f in nord))
    ok("nord's faces are the pack's own portraits of nweu and eeu",
       sorted(struct.unpack_from("<H", f, 2)[0] for f in nord) == [1, 3, 4])
    ok("a face's other bytes come along", all(f[1:] in [g[1:] for g in faces] for f in nord))
    ok("England, Germany, the African nation keep their group", nat2[204] == nweu and nat2[210] == nweu and nat2[1] == afr)
    ok("every face of before is still there, in its place", faces2[:len(faces)] == faces)
    ok("done twice: the same", F.nordic(nat2, faces2) == (nat2, faces2))
    os.remove(path)
    print("test_face_groups: ok (%d)" % N)


if __name__ == "__main__":
    main()
