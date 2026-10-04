r"""python mkccup.py --base <pesdb dir> --out <livecpk root> --cup "NAME|CODE|cid|reg|ko|groups|entry[|conf[|region]]" ... [--dry]

Add continental club cups where the game has none (Africa: the CAF Champions League and the
Confederation Cup): groups of four played home and away, then a knockout of the group winners and
runners-up. Each --cup is one competition:

  NAME    what the regulation rows are called ("CAF Champions League")
  CODE    the competition code (FL_CAFCL)
  cid     a free competition id
  reg     a free regulation id for the group stage; its groups take reg + 1024, reg + 2048 ...
  ko      a free regulation id for the knockout
  groups  how many groups of four (1-8), or 0 for a straight knockout (reg is then the knockout
          itself: give reg = ko)
  entry   who plays: <league regulation>:<position>,... -- 4 x groups of them, pot 1 first; for a
          knockout 2, 4, 8, 16 or 32 of them, paired in order (first v second, third v fourth ...).
          Position 0 is the winner of a cup (<cup regulation>:0), which may be one of the cups
          made earlier in the same call: a super cup is a knockout of two such entries
  conf    optional: the confederation the competition row says (Competition.bin +6, low three
          bits: 3 AFC, 4 CONMEBOL, 5 CAF ...); without it the Libertadores' (4) is kept
  region  optional: the region the competition row names (a region id, mkleague.enc_region) --
          a country's league cup or pre-season cup sits under its country, not the continent's

Both phases are shapes the engine already plays:

  group stage   the Copa Libertadores group stage (competition 5, regulation 9: master plus one
                replica per group, home and away), with the club count and the group count cut to
                this cup's, and only as many replicas as it has groups. Replica ids follow the
                game's rule (master + (group + 1) * 1024, +0x06 pointing back at the master).
  knockout      the Europa League knockout (regulation 6), with 2 x groups clubs -- or, for a
                straight knockout (groups 0), as many clubs as there are entries.

The competition row is a copy of the Libertadores' with the new id and code. Entries are written
too -- the clubs at those positions in the leagues' own entry lists -- but the field that plays is
chosen from league tables at run time: fl26swiss.dll fills the cup, draws the groups, starts the
knockout and dates both, reading the `ccup` lines this prints for modules\fl26world.txt.

    python mkccup.py --base E:\...\livecpk\_FL26Africa\common\etc\pesdb --out E:\...\livecpk\_FL26CAF ^
        --cup "CAF Champions League|FL_CAFCL|179|195|196|4|191:1,192:1,193:1,194:1,191:2,..." ^
        --cup "CAF Confederation Cup|FL_CAFCC|180|197|198|4|191:5,192:5,193:5,194:5,191:6,..."

--dry prints the plan and writes nothing.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkleague as M

R_BACK, R_GROUP, R_GROUPS = 0x06, 0x0a, 0x10
REPLICA_STEP, NO_GROUP = 1024, 255
LIB_CID, LIB_GROUPS, UEL_KO = 5, 9, 6
CONF_MASK = 7


def rid(r):
    return int.from_bytes(r[M.R_ID:M.R_ID + 2], "little")


def rows(b, size):
    return [bytearray(b[i:i + size]) for i in range(0, len(b), size)]


def parse(spec):
    bits = spec.split("|")
    if len(bits) not in (7, 8, 9):
        raise SystemExit("--cup wants NAME|CODE|cid|reg|ko|groups|entry[|conf[|region]], got %r" % spec)
    name, code, cid, reg, ko, groups, entry = bits[:7]
    conf = int(bits[7]) if len(bits) >= 8 and bits[7] else None
    region = int(bits[8]) if len(bits) == 9 and bits[8] else None
    ent = []
    for e in entry.split(","):
        r, _, p = e.partition(":")
        ent.append((int(r), int(p)))
    c = {"name": name, "code": code, "cid": int(cid), "reg": int(reg), "ko": int(ko),
         "groups": int(groups), "entry": ent, "conf": conf, "region": region}
    if conf is not None and not 2 <= conf <= 7:
        raise SystemExit("%s: confederation %d -- use 2..7" % (name, conf))
    if not 0 <= c["groups"] <= 8:
        raise SystemExit("%s: 0 to 8 groups" % name)
    if c["groups"] == 0:
        if c["reg"] != c["ko"]:
            raise SystemExit("%s: a straight knockout (groups 0) wants reg = ko" % name)
        if len(ent) not in (2, 4, 8, 16, 32):
            raise SystemExit("%s: a knockout of %d clubs -- use 2, 4, 8, 16 or 32" % (name, len(ent)))
    elif len(ent) != 4 * c["groups"]:
        raise SystemExit("%s: %d groups of four want %d entries, not %d"
                         % (name, c["groups"], 4 * c["groups"], len(ent)))
    for k in ("reg", "ko"):
        if not 175 < c[k] < REPLICA_STEP:
            raise SystemExit("%s: %s %d -- use a free id between 176 and 1023" % (name, k, c[k]))
    return c


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    base, out = get("--base"), get("--out")
    cups = [parse(v) for k, v in zip(a, a[1:]) if k == "--cup"]
    if not base or not cups or (not out and "--dry" not in a):
        print(__doc__)
        return 1
    comp, regs, ents = (M.load(base, n) for n in
                        ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    C, R, E = rows(comp, M.COMP), rows(regs, M.REG), rows(ents, M.ENT)
    used_cid = {c[M.CID_OFF] for c in C}
    used_reg = {rid(r) for r in R}

    lib = [r for r in R if r[M.R_CID] == LIB_CID and rid(r) & 0x3ff == LIB_GROUPS]
    master = [r for r in lib if r[R_GROUP] == NO_GROUP]
    reps = sorted((r for r in lib if r[R_GROUP] != NO_GROUP), key=lambda r: r[R_GROUP])
    ko_src = [r for r in R if rid(r) == UEL_KO]
    lib_comp = [c for c in C if c[M.CID_OFF] == LIB_CID]
    if len(master) != 1 or len(reps) < 8 or len(ko_src) != 1 or len(lib_comp) != 1:
        raise SystemExit("this world has no shipped Libertadores group stage (reg 9, 8 groups) "
                         "or Europa League knockout (reg 6) to copy")

    # a league's clubs in its own entry order, for the entries written here
    cid_of_reg = {rid(r): r[M.R_CID] for r in R}
    listed = {}
    for e in E:
        listed.setdefault(e[M.E_CID], []).append(
            (e[M.E_ORDER], int.from_bytes(e[M.E_TEAM:M.E_TEAM + 4], "little")))
    eid = max(int.from_bytes(e[M.E_EID:M.E_EID + 4], "little") for e in E)

    lines = []
    for cup in cups:
        ids = sorted({cup["reg"], cup["ko"]}) + [cup["reg"] + (g + 1) * REPLICA_STEP for g in range(cup["groups"])]
        taken = [i for i in ids if i in used_reg]
        if cup["cid"] in used_cid or taken:
            raise SystemExit("%s: competition %d or regulation(s) %s are taken in this world"
                             % (cup["name"], cup["cid"], taken or ""))
        for r, _p in cup["entry"]:
            if r not in cid_of_reg:
                raise SystemExit("%s: no league regulation %d in this world" % (cup["name"], r))
        used_cid.add(cup["cid"])
        used_reg.update(ids)
        cid_of_reg.update((i, cup["cid"]) for i in ids)     # a later super cup names these
        n = 4 * cup["groups"]

        c = bytearray(lib_comp[0])
        c[M.CID_OFF] = cup["cid"]
        M.put(c, M.CODE_OFF, cup["code"], M.COMP - M.CODE_OFF)
        if cup["conf"] is not None:
            c[M.FLAG_OFF] = (c[M.FLAG_OFF] & ~CONF_MASK) | cup["conf"]
        if cup["region"] is not None:
            c[M.REGION_OFF] = M.enc_region(cup["region"])
        C.append(c)

        new = []
        for r in (master + reps[:cup["groups"]] if cup["groups"] else []):
            g = bytearray(r)
            g[M.R_BELOW:M.R_BELOW + 2] = bytes(2)
            g[M.R_CID] = cup["cid"]
            grp = g[R_GROUP]
            g[M.R_ID:M.R_ID + 2] = (cup["reg"] if grp == NO_GROUP
                                    else cup["reg"] + (grp + 1) * REPLICA_STEP).to_bytes(2, "little")
            if grp == NO_GROUP:
                g[M.R_TEAMS] = (g[M.R_TEAMS] & ~0x3f) | n
                g[R_GROUPS] = (g[R_GROUPS] & ~0x1f) | cup["groups"]
            else:
                g[R_BACK:R_BACK + 2] = cup["reg"].to_bytes(2, "little")
            new.append(g)
        k = bytearray(ko_src[0])
        k[M.R_BELOW:M.R_BELOW + 2] = bytes(2)
        k[M.R_ID:M.R_ID + 2] = cup["ko"].to_bytes(2, "little")
        k[M.R_CID] = cup["cid"]
        nko = 2 * cup["groups"] if cup["groups"] else len(cup["entry"])
        k[M.R_TEAMS] = (k[M.R_TEAMS] & ~0x3f) | nko
        new.append(k)
        for g in new:
            M.put_names(g, 0, cup["name"])
        R.extend(new)

        clubs = []
        for r, p in cup["entry"]:
            if p < 1:                   # a cup's winner: nobody to write before it is played
                continue
            lst = [t for _o, t in sorted(listed.get(cid_of_reg[r], []))]
            pick = [t for t in lst[p - 1:] + lst if t not in clubs]
            if pick:
                clubs.append(pick[0])
        for i, t in enumerate(clubs):
            e = bytearray(M.ENT)
            e[M.E_TEAM:M.E_TEAM + 4] = t.to_bytes(4, "little")
            eid += 1
            e[M.E_EID:M.E_EID + 4] = eid.to_bytes(4, "little")
            e[M.E_CID], e[M.E_ORDER] = cup["cid"], i + 1
            E.append(e)

        if cup["groups"]:
            print("%s: competition %d, groups %d (%d groups of four: %s), knockout %d (%d clubs), %d entries"
                  % (cup["name"], cup["cid"], cup["reg"], cup["groups"],
                     " ".join(str(i) for i in ids[2:]), cup["ko"], nko, len(clubs)))
        else:
            print("%s: competition %d, knockout %d (%d clubs), %d entries"
                  % (cup["name"], cup["cid"], cup["ko"], nko, len(clubs)))
        lines.append("ccup %d ko=%d groups=%d entry=%s name=%s" % (
            cup["reg"], cup["ko"], cup["groups"],
            ",".join("%d:%d" % e for e in cup["entry"]), cup["name"]))

    print("")
    print("for modules\\fl26world.txt:")
    for l in lines:
        print(l)
    if "--dry" in a:
        print("dry run: nothing written")
        return 0
    M.write_tables(out, b"".join(C), b"".join(R), b"".join(E))
    return 0


if __name__ == "__main__":
    sys.exit(main())
