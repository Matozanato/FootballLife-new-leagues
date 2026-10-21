"""python test_id_mask.py <folder with a Team.bin> -- no new club gets an id the game takes for a
game club's (id & 0x23fff, B63: the builder's 71580 was Nam Dinh's 6044, 71587 Brunei's 6051 and a
list of the game kept only one of each pair); an id a club had at an earlier Build stays"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B
import mkworld as W
import pesdb

NL = B.NEWLIFE_TEAMS[0]


def main(base):
    raw = pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
    have = {int.from_bytes(raw[o + W.T_ID:o + W.T_ID + 4], "little") for o in range(0, len(raw), W.T_REC)}
    masks = {t & B.ID_MASK for t in have}
    assert len(masks) == len(have), "the game's own ids never share a mask"
    clash = B.id_mask_clash(have)
    assert clash and all(t > max(have) and t & B.ID_MASK in masks for t in clash), "clash ids"
    print("ok %d ids of the new-club block are skipped (first %s)" % (len(clash), sorted(clash)[:5]))

    # 2 own clubs and 40 NewLife clubs: the NewLife ones count up after the own ones, round the clash
    lg = [{"name": "A", "clubs": 2}, {"name": "B", "clubs": 40, "newlife": {"clubs": list(range(NL, NL + 40))}}]
    m, _free = B.newlife_tids(lg, base)
    got = sorted(m.values())
    assert not set(got) & clash, "a NewLife club got a clash id: %s" % sorted(set(got) & clash)
    assert len(set(got)) == 40 and not set(got) & have
    own = [t for t in range(max(have) + 1, got[0]) if t not in clash]
    assert len(own) == 2, "the 2 own clubs' ids stay below the NewLife ones (%d)" % len(own)
    print("ok NewLife ids %d..%d, none of them a game club's in the game's eyes" % (got[0], got[-1]))

    # a pin from an earlier Build that is a clash id stays (a world built before 0.2.5 keeps its ids)
    pin = min(clash)
    m2, _f = B.newlife_tids(lg, base, pins={str(NL): pin})
    assert m2[NL] == pin, "pinned %d -> %s" % (pin, m2[NL])
    print("ok an id from an earlier Build stays, even %d" % pin)
    print("test_id_mask: all passed")


if __name__ == "__main__":
    main(sys.argv[1])
