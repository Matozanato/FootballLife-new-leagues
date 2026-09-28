"""python clubnation.py <pesdb dir> [--min-id N] [--out Team.bin]

Give the clubs of a world the country of the league they play in.

Every club mkteams/mkworld makes is a clone of the last shipped club, Selangor FC, and the clone
never set the club's country -- so all 780 clubs of the G39 world are Malaysian (country 21) to
the Master League, measured live on 2026-09-26. The country is 9 bits at bit 562 of the Team.bin
record (byte 0x46, bit 2); the running game holds it at +0x418 of the team record, and
0x141558b00 (33 Master League callers, the scout screen among them) falls back on it for every
club outside the 24 shipped league slots. See docs/findings.md, "Every club of ours is Malaysian".

The squads cannot say where a club is from: they are placeholder clones too, the same 23
nationalities at every club, mostly English. The league can. A club's league is its entry in
CompetitionEntry.bin whose competition has a region with a country; the region comes from
Competition.bin +3 (mkleague.dec_region), and the country from the same two sources the game
uses -- its own 25 region pairs (0x1414cdbe0) and the pairs sider/fl26catlist.lua adds for our
regions, read from that file so the two cannot drift apart. A club whose league has no country
(a region in neither list, or one of the 0xfffc..0xfffe markers) is left as it is.

Only clubs with an id of at least --min-id (default 71578, one past the last shipped club) are
touched. Without --out this only prints what it would change. With --out it writes a new
Team.bin there; it never writes over its input.
"""
import collections, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
from mkleague import COMP, ENT, REGION_OFF, CID_OFF, E_TEAM, E_CID, dec_region

T_REC, T_ID = 1532, 0x08
T_NAT_BIT, NAT_BITS = 562, 9

# 0x1414cdbe0, the pairs it builds on its stack (docs/findings.md, "slot -> country and
# region -> country"). 22..24 answer 0xfffe..0xfffc, which are not countries, so they are out.
GAME_REGIONS = {2: 204, 3: 208, 4: 236, 5: 215, 6: 228, 7: 224, 8: 197, 9: 230, 10: 238,
                11: 227, 12: 203, 13: 237, 14: 226, 15: 232, 16: 146, 17: 144, 18: 147,
                19: 148, 20: 124, 21: 7, 27: 190, 28: 36}
CATLIST = os.path.join(HERE, "..", "sider", "fl26catlist.lua")


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def get_bits(rec, bit, n):
    lo, hi = bit // 8, (bit + n + 7) // 8
    return (int.from_bytes(rec[lo:hi], "little") >> (bit % 8)) & ((1 << n) - 1)


def set_bits(rec, bit, n, v):
    lo, hi = bit // 8, (bit + n + 7) // 8
    x = int.from_bytes(rec[lo:hi], "little")
    m = ((1 << n) - 1) << (bit % 8)
    x = (x & ~m) | ((v << (bit % 8)) & m)
    rec[lo:hi] = x.to_bytes(hi - lo, "little")


def load(d, n):
    raw = open(os.path.join(d, n), "rb").read()
    return raw[:3], bytearray(pesdb.wesys_unpack(raw))


def region_countries():
    """the game's pairs, overridden by fl26catlist's COUNTRY table, as the module does in game"""
    out = dict(GAME_REGIONS)
    src = open(CATLIST, encoding="utf-8").read()
    body = src[src.index("local COUNTRY = {"):]
    body = body[:body.index("\n}")]
    for rid, cc in re.findall(r"\[(\d+)\]\s*=\s*(\d+)", body):
        out[int(rid)] = int(cc)
    return out


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        print(__doc__)
        return 1
    db = a[0]
    min_id = int(a[a.index("--min-id") + 1]) if "--min-id" in a else 71578
    out = a[a.index("--out") + 1] if "--out" in a else None

    hdr, teams = load(db, "Team.bin")
    _, comps = load(db, "Competition.bin")
    _, ents = load(db, "CompetitionEntry.bin")
    rc = region_countries()

    comp_country = {}
    for i in range(len(comps) // COMP):
        c = comps[i * COMP:(i + 1) * COMP]
        cc = rc.get(dec_region(c[REGION_OFF]))
        if cc is not None:
            comp_country[c[CID_OFF]] = cc
    club_country = {}
    for i in range(len(ents) // ENT):
        e = ents[i * ENT:(i + 1) * ENT]
        tid, cid = u32(e, E_TEAM), e[E_CID]
        if tid >= min_id and cid in comp_country:
            club_country.setdefault(tid, set()).add(comp_country[cid])

    before, changed, lost, torn = collections.Counter(), collections.Counter(), [], []
    for i in range(len(teams) // T_REC):
        o = i * T_REC
        tid = u32(teams, o + T_ID)
        if tid < min_id:
            continue
        rec = teams[o:o + T_REC]
        old = get_bits(rec, T_NAT_BIT, NAT_BITS)
        before[old] += 1
        cs = club_country.get(tid)
        if not cs:
            lost.append(tid)
            continue
        if len(cs) > 1:                     # in leagues of two countries: no honest answer
            torn.append((tid, sorted(cs)))
            continue
        new = next(iter(cs))
        if new != old:
            set_bits(rec, T_NAT_BIT, NAT_BITS, new)
            teams[o:o + T_REC] = rec
            changed[new] += 1
    print("clubs from id %d: %d; country before: %s" % (min_id, sum(before.values()),
          ", ".join("%d x%d" % kv for kv in before.most_common())))
    print("would set" if not out else "set", sum(changed.values()), "clubs:",
          ", ".join("%d x%d" % kv for kv in sorted(changed.items())))
    if lost:
        print("left alone, in no league with a country (spare clubs no league uses, or a region "
              "missing from fl26catlist):", len(lost), lost[:10])
    if torn:
        print("left alone, leagues of two countries:", len(torn), torn[:10])
    if out:
        if os.path.abspath(out) == os.path.abspath(os.path.join(db, "Team.bin")):
            raise SystemExit("--out is the input file; write somewhere else and move it in yourself")
        open(out, "wb").write(pesdb.wesys_pack(bytes(teams), hdr))
        print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
