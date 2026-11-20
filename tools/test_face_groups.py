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
    regions()


def regions():
    """17.11. (mato: "obvious region errors + a new region"): sea for South-East Asia, the nations
    the 30.09. map put in the wrong part of the world moved; everything else as it was"""
    g = {name: i for i, name in enumerate(F.GROUPS)}
    ok("sea is group 10, after the ten of before", F.SEA == 10 and F.GROUPS[:10] == [
        "nweu", "seu", "eeu", "afr", "mena", "lat", "bra", "eas", "sas", "nord"])
    old = bytearray(b"\xff" * 512)
    for n in (3, 4, 5, 6, 9, 10, 18, 21, 22, 24, 25, 29, 32, 33, 36, 38, 43) + tuple(range(161, 185)):
        old[n] = g["sas"]
    for n in (162, 166, 204, 135):              # Australia, New Zealand, England, USA
        old[n] = g["nweu"]
    for n in (1, 27, 11, 76):                   # Afghanistan, Pakistan, Iran, Morocco
        old[n] = g["mena"]
    for n in (216, 40, 240, 41, 42, 230, 200):  # Central Asia, Russia, Croatia
        old[n] = g["eeu"]
    for n in (108, 80, 120):                    # Belize, Nigeria, Haiti
        old[n] = g["afr"]
    old[13] = g["eas"]
    new = F.regroup(old)
    want = {9: "sas", 3: "sas", 25: "sas", 33: "sas", 22: "sas", 4: "sas", 27: "sas",
            10: "sea", 36: "sea", 38: "sea", 21: "sea", 29: "sea", 5: "sea", 6: "sea", 18: "sea",
            24: "sea", 32: "sea", 43: "sea", 161: "sea", 163: "sea", 168: "sea", 170: "sea",
            171: "sea", 176: "sea", 184: "sea",
            164: "afr", 165: "afr", 167: "afr", 169: "afr", 172: "afr", 118: "afr",
            216: "eas", 40: "eas", 240: "mena", 41: "mena", 42: "mena", 108: "lat",
            1: "mena", 162: "nweu", 166: "nweu", 13: "eas"}
    ok("the map: South Asia (Pakistan with it) on sas, South-East Asia and Polynesia on sea, Melanesia "
       "on afr, Kazakhstan/Kyrgyzstan on eas, Uzbekistan/Tajikistan/Turkmenistan on mena, Belize on lat",
       all(new[n] == g[w] for n, w in want.items()))
    ok("no nation of the old map is left on sas but South Asia's",
       sorted(n for n in range(512) if new[n] == g["sas"]) == [3, 4, 9, 22, 25, 27, 33])
    ok("every other nation keeps its group",
       all(new[n] == old[n] for n in range(512) if n not in F.REGIONS_1711))
    ok("done twice: the same", F.regroup(new) == new)
    print("test_face_groups: ok (%d)" % N)


if __name__ == "__main__":
    main()
