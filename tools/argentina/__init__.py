"""Argentina's own rules (Mod Studio, FL 2027): what a recipe with "country_rules": ["argentina"] gets after the
build has written the world's tables and its world file -- leaguebuilder.build() calls apply(pl, root, base, log).
Formats, sources and decisions: docs/developers/fork/argentina.md.

1. The zones: `lphase <host> <zone> 3`, `lpname <zone> Zona X` (Competition Info: one item, L1/R1 between zones);
   each zone set split again in even parts every New Year (`jline fl26_join_rzones`).
2. The knockouts (fl26swiss tcup): one competition and one regulation each (a copy of the Libertadores qualifying
   round, extra time / penalties as the rule says), behind an item of their league's popup (`lphase <host> <reg> 1`,
   `lpname`), filled from the tables: `sline fl26_swiss_tcup ...`. The Primera Nacional, the B Metro, the C, the
   Promocional, the Federal A (its phases: `sline fl26_swiss_mphase`), the Interior, the Regional's eight regions, the
   interzonal matches, the promotions, the LPF (Apertura / Clausura halves, play-offs, Trofeo de Campeones, clasicos).
3. The cups (copas.py): the Copa Argentina and the Supercopa Argentina played as tcups on the game's own competitions,
   the Supercopa Internacional and the Recopa de Campeones as new ones; the 2026 editions with their real clubs.
4. The New Year (fl26join's regional pyramid mover): tiers, homes by filiation and region, the knockouts' results,
   promedios, the Interior asleep in 2026, the Federal A's mid-season leagues.
5. Competition Info: the Regional's eight regions behind one entry (`sline fl26_swiss_lvmenu`); Select Team: folders
   inside Argentina (`confsub`, `confsubnames`, fl26confgroups); the competitions' emblems (data/logos)."""
import collections, contextlib, datetime, io, json, os, re, unicodedata
import leaguebuilder as B
import mkleague as M
import mkeuropo as E

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

PN, PNB = "Primera Nacional", "Primera Nacional Zona B"
BM = "Primera B Metropolitana"
PC, PCB = "Primera C", "Primera C Zona B"
PR, PRB = "Torneo Promocional Amateur", "Torneo Promocional Amateur Zona B"
FA = "Torneo Federal A"
TI = "Torneo Argentino del Interior"
LPF = 30
SEED = 0x08000000
BIT_AWAY, BIT_ET, BIT_PENS = 24, 25, 27


def wd(mmdd):
    """a "MM-DD" of 2026 as the world file's day (the year's day + 1)"""
    m, d = (int(x) for x in mmdd.split("-"))
    return datetime.date(2026, m, d).timetuple().tm_yday + 1


def norm(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower())


# ---- the knockouts (sources: ("t", league, pos), ("b", league, k from the bottom), ("w"|"l", tie[, cup code]),
#      ("seed", source) a forced top seed of a reseeded round). Rounds: (legs, reseed, day1, day2).
def T(lg, pos): return ("t", lg, pos)
def Bt(lg, k): return ("b", lg, k)
def Wn(k, cup=None): return ("w", k, cup)
def Ls(k, cup=None): return ("l", k, cup)
def S(src): return ("seed", src)


BASE_CUPS = [
    # Primera Nacional (3.2): the final of the 1st promotion, the Reducido (no extra time, a level tie to the better
    # placed), the Reducido's final (penalties). Dates: GUIA 3.2 (31/10 .. 12/12); the order of the final and the
    # 2nd phase [adaptação]: the final's loser enters the 2nd phase, so the final comes first.
    dict(code="PN-FIN", name="Final do 1º acesso", host=PN, et=True, pens=True, tier=2, fill="10-25",
         rounds=[(1, 0, "11-08", None)], names=["Final"],
         ties=[(0, T(PN, 1), T(PNB, 1))], rtie=[(0, 1, 0)]),
    dict(code="PN-RED", name="Reducido", host=PN, et=False, pens=False, tier=2, fill="10-25",
         rounds=[(1, 0, "10-31", None), (2, 1, "11-14", "11-21"), (2, 1, "11-28", "12-05")],
         names=["1ª fase", "2ª fase", "Semifinais"],
         ties=[(0, T(PN, 2), T(PNB, 8)), (0, T(PNB, 2), T(PN, 8)), (0, T(PN, 3), T(PNB, 7)), (0, T(PNB, 3), T(PN, 7)),
               (0, T(PN, 4), T(PNB, 6)), (0, T(PNB, 4), T(PN, 6)), (0, T(PN, 5), T(PNB, 5)),
               (1, Wn(0), Wn(1)), (1, Wn(2), Wn(3)), (1, Wn(4), Wn(5)), (1, Wn(6), S(Ls(0, "PN-FIN"))),
               (2, Wn(7), Wn(8)), (2, Wn(9), Wn(10))], rtie=[]),
    dict(code="PN-RFIN", page_of="PN-RED", name="Final do Reducido", host=PN, et=False, pens=True, tier=2, fill="12-06",
         rounds=[(2, 1, "12-09", "12-13")], names=["Final"],
         ties=[(0, Wn(11, "PN-RED"), Wn(12, "PN-RED"))], rtie=[(0, 1, 0)]),
    # Primera B Metropolitana (3.3): the 2nd to the 9th, reseeded 1..8 by the table each round; penalties
    dict(code="BM-RED", name="Reducido", host=BM, et=False, pens=True, tier=3, fill="11-01",
         rounds=[(2, 1, "11-07", "11-14"), (2, 1, "11-21", "11-28"), (2, 1, "12-05", "12-12")],
         names=["Quartas de final", "Semifinais", "Final"],
         ties=[(0, T(BM, 2), T(BM, 3)), (0, T(BM, 4), T(BM, 5)), (0, T(BM, 6), T(BM, 7)), (0, T(BM, 8), T(BM, 9)),
               (1, Wn(0), Wn(1)), (1, Wn(2), Wn(3)), (2, Wn(4), Wn(5))], rtie=[(6, 2, 0)]),
    # Primera C (3.5): final (the second leg at the better's: a reseeded round of two), Reducido of 12 + the final's
    # loser in the semi-finals, the desafiliación (the two last, one match, neutral), the promotion v the Promocional
    dict(code="PC-FIN", name="Final do 1º acesso", host=PC, et=False, pens=True, tier=4, fill="10-11",
         rounds=[(2, 1, "10-17", "10-24")], names=["Final"],
         ties=[(0, T(PC, 1), T(PCB, 1))], rtie=[(0, 3, 0)]),
    dict(code="PC-RED", name="Reducido", host=PC, et=False, pens=True, tier=4, fill="10-11",
         rounds=[(2, 0, "10-17", "10-24"), (2, 1, "10-31", "11-07"), (2, 1, "11-14", "11-21"), (2, 1, "11-28", "12-05")],
         names=["1ª fase", "2ª fase", "Semifinais", "Final"],
         ties=[(0, T(PC, 2), T(PCB, 7)), (0, T(PCB, 2), T(PC, 7)), (0, T(PC, 3), T(PCB, 6)), (0, T(PCB, 3), T(PC, 6)),
               (0, T(PC, 4), T(PCB, 5)), (0, T(PCB, 4), T(PC, 5)),
               (1, Wn(0), Wn(1)), (1, Wn(2), Wn(3)), (1, Wn(4), Wn(5)),
               (2, Wn(6), Wn(7)), (2, Wn(8), S(Ls(0, "PC-FIN"))),
               (3, Wn(9), Wn(10))], rtie=[(11, 3, 0)]),
    dict(code="PC-DES", name="Desfiliação", host=PC, et=True, pens=True, tier=4, fill="10-11",
         rounds=[(1, 0, "10-24", None)], names=["Desfiliação"],           # the day [a confirmar]
         ties=[(0, Bt(PC, 1), Bt(PCB, 1))], rtie=[(0, 0, 5)]),
    # Promocional (3.7): final (two legs) and Reducido (the 2nd to the 4th + the final's loser in the semi-finals);
    # the key and the days [a confirmar] (only the AFA rules of 2025)
    dict(code="PR-FIN", name="Final do acesso", host=PR, et=False, pens=True, tier=5, fill="10-04",
         rounds=[(2, 1, "10-10", "10-17")], names=["Final"],
         ties=[(0, T(PR, 1), T(PRB, 1))], rtie=[(0, 4, 0)]),
    dict(code="PR-RED", name="Reducido", host=PR, et=False, pens=True, tier=5, fill="10-04",
         rounds=[(2, 0, "10-10", "10-17"), (2, 1, "10-24", "10-31"), (2, 1, "11-07", "11-14")],
         names=["1ª fase", "Semifinais", "Final"],
         ties=[(0, T(PR, 2), T(PRB, 4)), (0, T(PRB, 2), T(PR, 4)), (0, T(PR, 3), T(PRB, 3)),
               (1, Wn(0), Wn(1)), (1, Wn(2), S(Ls(0, "PR-FIN"))), (2, Wn(3), Wn(4))], rtie=[]),
    # the promotion: the desafiliación's winner (the C's, at home in the second leg; level: it stays) v the
    # Promocional's Reducido winner. Days [a confirmar]
    dict(code="PC-PRO", name="Promoção", host=PC, et=False, pens=False, tier=4, fill="11-15",
         rounds=[(2, 0, "11-21", "11-28")], names=["Promoção"],
         ties=[(0, Wn(0, "PC-DES"), Wn(5, "PR-RED"))], rtie=[(0, 4, 5)]),
]

# the Interior's zones: two regions each [adaptação, 19/11 the sources give no pairs]
INTERIOR_PAIRS = [("Norte", "Litoral Norte"), ("Centro", "Cuyo"), ("Litoral Sur", "Bonaerense Pampeana Norte"),
                  ("Bonaerense Pampeana Sur", "Patagónica")]
SHORT = {"Bonaerense Pampeana Norte": "Pampeana Norte", "Bonaerense Pampeana Sur": "Pampeana Sur"}




# the 2027 promotions (La Gaceta 22/10/2026, Jujuy al Momento 26/10/2026; the representatives: 21/11/2026 the user,
# "vamos do seu critério": the losers of the access finals): two legs, the lower club at home first, a level aggregate
# keeps the upper club (TC_F_BETTER, no extra time, no penalties). ("fil", dir, n): the n-th from the bottom among the
# clubs of direct (1) / indirect (0) filiation of the leagues of the cup's group 0.
PROMOS = [
    dict(code="PM-PNBM", name="Promoção com a B Metro", host=PN, et=False, pens=False, tier=2, fill="12-14", start=2027,
         rounds=[(2, 0, "12-16", "12-20")], names=["Promoção"], groups=[[T(PN, 1), T(PNB, 1)]],
         ties=[(0, ("fil", 1, 3), Ls(6, "BM-RED"))], rtie=[(0, 2, 3)]),
    dict(code="PM-PNFA", name="Promoção com o Federal A", host=PN, et=False, pens=False, tier=2, fill="12-14", start=2027,
         rounds=[(2, 0, "12-16", "12-20")], names=["Promoção"], groups=[[T(PN, 1), T(PNB, 1)]],
         ties=[(0, ("fil", 0, 3), Ls(0, "FA-REVF"))], rtie=[(0, 2, 3)]),
    dict(code="PM-BMC", name="Promoção com a Primera C", host=BM, et=False, pens=False, tier=3, fill="12-14", start=2027,
         rounds=[(2, 0, "12-16", "12-20")], names=["Promoção"],
         ties=[(0, Bt(BM, 3), Ls(11, "PC-RED"))], rtie=[(0, 3, 4)]),
]


# lab 23/11/2026: the Copa Sudamericana of Mod Studio (ccup 9, the recipe's game_europe 30: 1-6) fills its 32 from the
# game's leagues after ours -- the LPF's 7th to the 13th too: 13 Argentine clubs. As the real cup: six of Argentina and
# six of Brazil; the rest from Chile and Colombia, the world's only other South American leagues [adaptacao: the real
# group stage has four of each other country, through the first stage]. The pots (8 entries each) stay as built.
SUD_KEEP = {30: 6, 29: 12}          # league reg -> its last place kept
SUD_MORE = (67, 168)                # Chile, Colombia: the next places, alternately


def sud_field(line):
    if not line.startswith("ccup ") or "name=Copa Sudamericana" not in line:
        return line
    m = re.search(r"entry=([0-9:,]+)", line)
    ent = [tuple(int(x) for x in e.split(":")) for e in m.group(1).split(",")]
    nxt = {r: max([k for rr, k in ent if rr == r and k <= SUD_KEEP.get(rr, 99)] or [0]) for r in SUD_MORE}
    out, turn = [], 0
    for r, k in ent:
        if r in SUD_KEEP and k > SUD_KEEP[r]:
            r2 = SUD_MORE[turn % len(SUD_MORE)]; turn += 1
            nxt[r2] += 1
            r, k = r2, nxt[r2]
        out.append("%d:%d" % (r, k))
    return line[:m.start(1)] + ",".join(out) + line[m.end(1):]


def apply(pl, root, base, log=print):
    """the rules on a world just built: its tables (root/common/etc/pesdb) and its world file (root/fl26world.txt)"""
    from . import regional, ti, fa, copas, iz, lpf
    CUPS = [dict(c) for c in BASE_CUPS] + regional.cups() + [dict(c) for c in ti.CUPS] + [dict(c) for c in fa.CUPS] \
        + [dict(c) for c in copas.CUPS]
    by = {L["name"]: L for L in pl["leagues"]}
    data = json.load(open(os.path.join(HERE, "argentina2026.json"), encoding="utf-8"))
    db = os.path.join(root, "common", "etc", "pesdb")
    comp, regs, ents = (M.load(db, n) for n in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin"))
    rows = [regs[i * M.REG:(i + 1) * M.REG] for i in range(len(regs) // M.REG)]
    crow = [comp[i * M.COMP:(i + 1) * M.COMP] for i in range(len(comp) // M.COMP)]
    # run again: the knockouts of a run before (codes FL_ARG_...) go first, so they are not added twice
    ours = {M.comp_cid(x) for x in crow if M.code_of(x).startswith("FL_ARG_")}
    if ours:
        crow = [x for x in crow if M.comp_cid(x) not in ours]
        rows = [x for x in rows if M.reg_cid(x) not in ours]
        comp, regs = bytearray(b"".join(crow)), bytearray(b"".join(rows))
        log("a run before: %d knockout competition(s) taken out first" % len(ours))
    used_r = {int.from_bytes(x[M.R_ID:M.R_ID + 2], "little") for x in rows}
    used_c = {M.comp_cid(x) for x in crow}
    free_r = (x for x in range(300, 2000) if x not in used_r)
    free_c = (x for x in range(1, M.CID_LIMIT) if x not in used_c and x > max(L["cid"] for L in pl["leagues"]))
    src = next(x for x in rows if int.from_bytes(x[M.R_ID:M.R_ID + 2], "little") == E.LIB_QUAL)
    libc = next(x for x in crow if M.comp_cid(x) == E.LIB_CID)
    lines = []

    # ---- 1. the zones
    zone_of = {}
    for n, L in by.items():
        m = re.match(r"^(.*) Zona (\S+)$", n)
        if not m or m.group(1) not in by:
            continue
        host = by[m.group(1)]
        zone_of[L["rid"]] = (host["rid"], m.group(2))
    hosts = {h for h, _z in zone_of.values()}
    for r, (h, z) in sorted(zone_of.items()):
        lines.append("lphase %d %d 3" % (h, r))
        lines.append("lpname %d Zona %s" % (r, z))
    for h in sorted(hosts):
        second = [z for r, (hh, z) in zone_of.items() if hh == h]
        lines.append("lpname %d Zona %s" % (h, "A" if any(z.isalpha() for z in second) else "1"))
    # lab 22/11/2026: zones split again in even parts each New Year (fl26join rz_balance): the Interior and each region
    # of the Regional -- the Regional's 190 ended 2027 with one club and stopped the pyramid
    name_of = {L["rid"]: n for n, L in by.items()}
    sets = [h for h in sorted(hosts) if name_of.get(h, "").startswith(("Regional ", "Torneo Argentino del Interior"))]
    rz = [len(sets)]
    for h in sets:
        zs = [h] + sorted(r for r, (hh, _z) in zone_of.items() if hh == h)
        rz += [len(zs)] + zs
    lines.append("jline fl26_join_rzones " + " ".join(str(x) for x in rz))

    # ---- 2. the knockouts (and the interzonal matches, whose pairs are team ids of this build)
    lpf_ids = [int.from_bytes(ents[i * M.ENT:i * M.ENT + 4], "little") for i in range(len(ents) // M.ENT)
               if M.ent_cid(ents[i * M.ENT:(i + 1) * M.ENT]) == 22]
    gnames = {}
    for d in (db, base):
        for tid, (nm, _ab) in B.game_clubs(d).items():
            gnames.setdefault(tid, nm)
    lpf_tid = {gnames.get(t): t for t in lpf_ids}
    cl = [(0, ("team", lpf_tid[lpf.GAME_NAME[b]]), ("team", lpf_tid[lpf.GAME_NAME[a]])) for a, b in lpf.PAIRS]
    clasicos = dict(code="LPF-CL", name="Clássicos (2º jogo)", host="LPF", et=False, pens=False, tier=1, fill="10-25",
                    rounds=[(1, 0, lpf.CLASICOS_DAY, None)], names=["Clássicos"], ties=cl, rtie=[], izone=["LPF"])
    CUPS[:] = [c for c in CUPS if not c.get("izone") and not c["code"].startswith("PM-") and not c["code"].startswith("LPF-")]         + iz.cups(by) + PROMOS + lpf.CUPS + [clasicos]
    rid_of = {}
    new_c, new_r = bytearray(), bytearray()
    by["LPF"] = {"name": "Liga Profesional", "rid": LPF, "cid": 22, "region": -1, "slot": 255}   # the game's league (reg 30, comp 22)
    regs = bytearray(regs)
    own_cids = set()
    for c in CUPS:
        host = by[c["host"]]
        if isinstance(c.get("own"), tuple):     # lab 23/11/2026: the game's cup, its regulation made a tcup in place
            cid, r = c["own"]
            at = next(i for i in range(len(regs) // M.REG) if int.from_bytes(regs[i * M.REG + M.R_ID:i * M.REG + M.R_ID + 2], "little") == r)
            old = bytes(regs[at * M.REG:(at + 1) * M.REG])
            g = bytearray(src)
            g[M.R_ID:M.R_ID + 2] = r.to_bytes(2, "little")
            M.set_reg_cid(g, cid)
            for k in range(M.NAME_SLOTS):        # its names as the game has them
                o = M.name_at(k)
                n = M.R_CID_HI - o if M.CID_WIDE and k == M.NAME_SLOTS - 1 else M.NAME_SLOT
                g[o:o + n] = old[o:o + n]
            g[M.R_TEAMS] &= ~0x3f
            v = int.from_bytes(g[0x10:0x14], "little") & ~((1 << BIT_AWAY) | (1 << BIT_ET) | (1 << BIT_PENS))
            v |= (1 << BIT_ET if c["et"] else 0) | (1 << BIT_PENS if c["pens"] else 0)
            g[0x10:0x14] = v.to_bytes(4, "little")
            regs[at * M.REG:(at + 1) * M.REG] = g
            ci = next(i for i in range(len(comp) // M.COMP) if M.comp_cid(comp[i * M.COMP:(i + 1) * M.COMP]) == cid)
            comp = bytearray(comp)
            comp[ci * M.COMP + 6] = (libc[6] & ~7) | (comp[ci * M.COMP + 6] & 7)   # a knockout's kind, as our tcups' (the super cup's was 0x04)
            own_cids.add(cid)
            rid_of[c["code"]] = r
            c["cid"], c["rid"] = cid, r
            continue
        cid, r = next(free_c), next(free_r)
        hc = next(x for x in crow if M.comp_cid(x) == host["cid"])
        row = bytearray(libc)
        M.set_comp_cid(row, cid)
        M.put(row, M.CODE_OFF, "FL_ARG_" + c["code"].replace("-", ""), M.COMP - M.CODE_OFF)
        row[M.REGION_OFF] = hc[M.REGION_OFF]
        row[6] = (row[6] & ~7) | (hc[6] & 7)
        g = bytearray(src)
        g[M.R_ID:M.R_ID + 2] = r.to_bytes(2, "little")
        M.set_reg_cid(g, cid)
        M.put_names(g, 0, c["name"] if c.get("own") else "%s - %s" % (host["name"], c["name"]))   # a competition of its own: its name alone
        g[M.R_TEAMS] &= ~0x3f
        v = int.from_bytes(g[0x10:0x14], "little") & ~((1 << BIT_AWAY) | (1 << BIT_ET) | (1 << BIT_PENS))
        v |= (1 << BIT_ET if c["et"] else 0) | (1 << BIT_PENS if c["pens"] else 0)
        g[0x10:0x14] = v.to_bytes(4, "little")
        new_c += row; new_r += g
        rid_of[c["code"]] = r
        c["cid"], c["rid"] = cid, r

    def enc(s, cup):
        if s[0] == "seed":
            return SEED | enc(s[1], cup)
        if s[0] == "alt":                                # a winner, or the tie's loser when the winner is in already
            return 0x04000000 | enc(s[1], cup)
        if s[0] == "str":                                # this season's clubs, strongest squad first
            return 0x90000000 | by[s[1]]["rid"] << 8 | s[2]
        if s[0] == "prev":                               # last season's final table, clubs still in the league
            return 0xA0000000 | by[s[1]]["rid"] << 8 | s[2]
        if s[0] == "kept":                               # a cup's last winner (0) / runner-up (1), kept
            return 0xB0000000 | rid_of[s[1]] << 8 | s[2]
        if s[0] == "t":
            return 0x10000000 | by[s[1]]["rid"] << 8 | s[2]
        if s[0] == "b":
            return 0x10000000 | by[s[1]]["rid"] << 8 | 0x80 | s[2]
        if s[0] == "cond":                               # the Trofeo's sides (fl26swiss mode 1, 2, 3 of group g)
            return 0x80000000 | s[1] << 16 | s[2] << 8
        if s[0] == "half":                               # the LPF's Apertura / Clausura table
            return 0x70000000 | s[1] << 8 | s[2]
        if s[0] == "fil":
            return 0x60000000 | s[1] << 7 | s[2]
        if s[0] == "team":                               # a fixed club (the interzonal pairs)
            return 0x50000000 | s[1]
        if s[0] == "r":
            return 0x40000000 | s[1] << 8 | s[2]
        if s[0] == "rest":                               # mphase: the rest of a zone from place p
            return 0x10000000 | by[s[1]]["rid"] << 8 | 0x40 | s[2]
        base = 0x20000000 if s[0] == "w" else 0x30000000
        other = rid_of[s[2]] if s[2] and s[2] != cup["code"] else 0
        return base | other << 8 | s[1]

    for c in CUPS:
        v = [c["rid"], wd(c["fill"]), c["tier"] | (1 | c.get("flags", 0)) << 8 | c.get("until", 0) << 16, len(c["rounds"])]   # TC_F_BETTER (+HOMEBEST)
        for k, (legs, reseed, d1, d2) in enumerate(c["rounds"]):
            v += [legs | (0x10 if reseed else 0) | ((c.get("start", 0) << 16) if k == 0 else 0), wd(d1), wd(d2) if d2 else 0]
        v.append(len(c["ties"]))
        for rd, a, b in c["ties"]:
            v += [rd, enc(a, c), enc(b, c)]
        if c.get("groups"):
            v.append(len(c["groups"]))
            for g in c["groups"]:
                v += [len(g)] + [enc(x, c) for x in g]
        lines.append("sline fl26_swiss_tcup " + " ".join(str(x) for x in v))
        if c.get("y1"):   # lab 23/11/2026: one year's real first round (the 2026 cups), by the world's club names
            yr, pairs = c["y1"]
            tid_of = dict(lpf_tid)
            for L in by.values():
                for t, nm in zip(L.get("teams") or [], L.get("club_names") or []):
                    tid_of.setdefault(nm, int(t))
            miss = [nm for pr in pairs for nm in pr if nm not in tid_of]
            if miss:
                raise SystemExit("%s %d: club(s) not in this world: %s" % (c["code"], yr, miss))
            y = [c["rid"], yr, len(pairs)] + [0x50000000 | tid_of[nm] for pr in pairs for nm in pr]
            lines.append("sline fl26_swiss_tcupy " + " ".join(str(x) for x in y))
        if c.get("izone"):
            lines.append("sline fl26_swiss_izone %d %d %s" % (c["rid"], len(c["izone"]), " ".join(str(by[z]["rid"]) for z in c["izone"])))
        if c["code"] == "LPF-CL":   # the LPF: its dates (Apertura / Clausura Saturdays) and its halves
            doy = lambda md: datetime.date(2026, *map(int, md.split("-"))).timetuple().tm_yday - 1
            lines.append("sline fl26_swiss_ldates %d %d %s" % (LPF, 29, " ".join(str(wd(x)) for x in lpf.APERTURA + lpf.CLAUSURA)))
            lines.append("sline fl26_swiss_lhalf 1 %d 0 14 0 0 0" % LPF)        # half 1: the Apertura, half 2: the Clausura
            lines.append("sline fl26_swiss_lhalf 2 %d 15 28 %d %d %d" % (LPF, c["rid"], doy("07-01"), doy("12-31")))
            for h, nm in ((1, "Apertura"), (2, "Clausura")):          # their tables, items of the LPF's menu (lhview)
                lines.append("lphase %d %d 4" % (LPF, h))
                lines.append("lpname %d %s" % (0xBF00 + h, nm))
        if c.get("own"):   # lab 23/11/2026: a cup of its own -- its knockout is the first item of its own menu (fl26swiss)
            lines.append("lphase %d %d 1" % (c["rid"], c["rid"]))
            lines.append("lpname %d %s" % (c["rid"], c.get("item", "Chave")))
        for h in ([] if c.get("own") else c.get("hosts") or [c["host"]]):   # a competition of its own: no popup item
            lines.append("lphase %d %d 1" % (by[h]["rid"], c["rid"]))
        if not c.get("own"):
            lines.append("lpname %d %s" % (c["rid"], c["name"]))
        if c.get("page_of"):   # lab 21/11/2026: the final is the last page of its knockout's item, not an item of its own
            lines.append("lphase %d %d 5" % (next(x for x in CUPS if x["code"] == c["page_of"])["rid"], c["rid"]))
        for k, nm in enumerate(c["names"]):
            lines.append("lpname %d %s" % (0xC000 + c["rid"] * 8 + k, nm))
        log("%-8s comp %3d reg %3d  %d round(s), %d tie(s)  (%s)" % (c["code"], c["cid"], c["rid"], len(c["rounds"]),
                                                                       len(c["ties"]), c["name"]))
    # lab 23/11/2026 (the user's "solution 1"): the Regional's eight regions behind one entry of Argentina's competition
    # list, "Torneo Regional Federal Amateur" -- a competition and a regulation of their own (no clubs, no matches);
    # choosing it shows the regions in place, each with its popup (fl26swiss lvmenu, the estaduais' list level)
    hosts_rg = [regional.zone_name(reg, "Zona 1") for reg in data["regional"]["regioes"]]
    hosts_rg = [h for h in hosts_rg if h in by]
    rg_entry_cid = 0
    if hosts_rg:
        cid, r = next(free_c), next(free_r)
        hc = next(x for x in crow if M.comp_cid(x) == by[hosts_rg[0]]["cid"])
        row = bytearray(libc)
        M.set_comp_cid(row, cid)
        M.put(row, M.CODE_OFF, "FL_ARG_REGIONAL", M.COMP - M.CODE_OFF)
        row[M.REGION_OFF] = hc[M.REGION_OFF]
        row[6] = (row[6] & ~7) | (hc[6] & 7)
        g = bytearray(src)
        g[M.R_ID:M.R_ID + 2] = r.to_bytes(2, "little")
        M.set_reg_cid(g, cid)
        M.put_names(g, 0, "Torneo Regional Federal Amateur")
        g[M.R_TEAMS] &= ~0x3f
        new_c += row; new_r += g
        lines.append("sline fl26_swiss_lvmenu %d %d %s" % (r, len(hosts_rg), " ".join(str(by[h]["rid"]) for h in hosts_rg)))
        rg_entry_cid = cid
        log("REGIONAL entry comp %3d reg %3d over %d region(s): %s" % (cid, r, len(hosts_rg), ", ".join(hosts_rg)))
    if own_cids:   # the game's cups played as tcups: no entries of their own (the tcup puts the clubs in)
        ents = b"".join(ents[i * M.ENT:(i + 1) * M.ENT] for i in range(len(ents) // M.ENT)
                        if M.ent_cid(ents[i * M.ENT:(i + 1) * M.ENT]) not in own_cids)
    with contextlib.redirect_stdout(io.StringIO()):
        M.write_tables(root, bytes(comp) + bytes(new_c), bytes(regs) + bytes(new_r), ents)
    # the Federal A's mid-season phases: filled by fl26swiss (mphase), asleep until then (fl26join rlate), items of
    # the Federal A's popup (lphase 2: the phase's table, its zones with L1/R1)
    ent_of = collections.defaultdict(list)
    for i in range(len(ents) // M.ENT):
        e = ents[i * M.ENT:(i + 1) * M.ENT]
        ent_of[M.ent_cid(e)].append(int.from_bytes(e[0:4], "little"))
    late = []
    for lg, fill, after, srcs, groups in fa.MPHASES:
        cup = {"code": "MP"}
        v = [by[lg]["rid"], wd(fill), by[after]["rid"], len(srcs)] + [enc(x, cup) for x in srcs]
        if groups:
            v.append(len(groups))
            for g in groups:
                v += [len(g)] + [enc(x, cup) for x in g]
        lines.append("sline fl26_swiss_mphase " + " ".join(str(x) for x in v))
        ids = ent_of.get(by[lg]["cid"], [])
        late += [by[lg]["rid"], len(ids)] + ids
    lines.append("jline fl26_join_rlate " + " ".join(str(x) for x in late))
    for lg, nm in ((fa.F2A, "2ª fase"), (fa.RVA, "Reválida - 1ª etapa")):
        lines.append("lphase %d %d 2" % (by[fa.Z1]["rid"], by[lg]["rid"]))
        lines.append("lpname %d %s" % (0x8000 + by[lg]["rid"], nm))   # the item; the zone title keeps "Zona A"
    rl = []
    for lg, k, tier, a, b in fa.RLAST:
        rl += [by[lg]["rid"], k, tier, a, b]

    # ---- 3. the New Year: tiers, homes, maps, the knockouts' results
    entries = collections.defaultdict(list)
    for i in range(len(ents) // M.ENT):
        e = ents[i * M.ENT:(i + 1) * M.ENT]
        entries[M.ent_cid(e)].append(int.from_bytes(e[0:4], "little"))
    prov_region = collections.defaultdict(collections.Counter)
    for reg, zs in data["regional"]["regioes"].items():
        for cl in zs.values():
            for x in cl:
                prov_region[norm(x.get("provincia"))][reg] += 1
    prov_region = {p: cn.most_common(1)[0][0] for p, cn in prov_region.items()}
    regional_host = {}
    for reg in data["regional"]["regioes"]:
        regional_host[reg] = by["Regional %s" % SHORT.get(reg, reg)]["rid"]
    # each club: its filiation and its province (the sources' "Distribución geográfica" for the PN and the Federal A)
    info = {}
    for key in ("primera_nacional", "primera_c", "federal_a", "promocional"):
        for zn, cl in data[key]["zonas"].items():
            for x in cl:
                info[norm(x["nome"])] = x
    for x in data["primera_b"]["clubes"]:
        info[norm(x["nome"])] = x
    # 21/11/2026: by the NewLife id first -- a name in the build may be cut at 30 letters ("Club Atlético Argentino de
    # Mer") or lose its "Club Social y Deportivo": the B Metro's Argentino (Q), Talleres (RdE), Argentino (M), San Martín (B)
    info_nl = {str(x["nl"]): x for x in info.values() if x.get("nl")}
    for k, pv in json.load(open(os.path.join(HERE, "provincias.json"), encoding="utf-8")).items():
        if k in info:   # the sources' "Distribucion geografica" (Wikipedia 2026), read once into the data file
            info[k].setdefault("provincia", pv)
    # Buenos Aires (the city and its suburbs) is direct filiation; the province's interior goes by its region
    promo_a = by[PR]["rid"]

    def home_of(name, lg, nl=None):
        x = info_nl.get(str(nl)) if nl else None
        x = x or info.get(norm(name))
        if lg.startswith("Regional") or lg.startswith(PR):
            return by[lg]["rid"]
        if not x:
            return 0
        if x.get("filiacao") == "direta":
            return promo_a
        reg = prov_region.get(norm(x.get("provincia")), None)
        return regional_host.get(reg, 0) if reg else 0

    groups, homes, flags, direct = [], [], [], []
    tiers = [(LPF, 1, 0, 0)]      # the LPF: by promedio, then the annual table's last still up (rprom)
    for n, L in by.items():
        if n == "Liga Controle" or L["region"] != by[PN]["region"] or n in fa.PHASES:   # the pyramid: region 17
            continue
        t = 2 if n.startswith(PN) else 3 if n in (BM,) or n.startswith(FA) else 4 if n.startswith(PC) or n.startswith(TI) \
            else 5
        up = 1 if n == BM else 0
        down = 2 if n.startswith(PN) or n == BM else 0
        tiers.append((L["rid"], t, up, down))
        names = L.get("club_names") or []
        nl_of = {int(t): nl for nl, t in (L.get("newlife_tid") or {}).items()}
        for k, tid in enumerate(L.get("teams") or []):
            h = home_of(names[k] if k < len(names) else "", n, nl_of.get(int(tid)))
            x = info_nl.get(str(nl_of.get(int(tid)))) or info.get(norm(names[k] if k < len(names) else ""))
            if (x and x.get("filiacao") == "direta") or n in (BM,) or n.startswith(PC) or n.startswith(PR):
                direct.append(tid)
            if h:
                homes.append((tid, h))
    for rid, t, up, down in tiers:
        slot = 255 if rid == LPF else next(L["slot"] for L in by.values() if L["rid"] == rid)
        groups += [rid, t, 0, up, down, slot]
    flags = [LPF, 4] + [x for rid, _t, _u, _d in tiers if rid != LPF for x in (rid, 16)]   # RGF_EXT; RGF_SIZE (D12)
    # the maps: a Regional zone -> its region's Interior zone and Federal A zone; a Promocional zone -> C and B Metro
    fa_zone = {}
    for zn, cl in data["federal_a"]["zonas"].items():
        cnt = collections.Counter(prov_region.get(norm(info.get(norm(x["nome"]), {}).get("provincia")), None) for x in cl)
        lg = FA if zn == "Zona 1" else "%s %s" % (FA, zn)
        for reg, k in cnt.items():
            if reg and (reg not in fa_zone or k > fa_zone[reg][1]):
                fa_zone[reg] = (by[lg]["rid"], k)
    ti_zone = {}
    for z, pair in enumerate(INTERIOR_PAIRS):
        lg = TI if z == 0 else "%s Zona %d" % (TI, z + 1)
        for reg in pair:
            if lg in by:
                ti_zone[reg] = by[lg]["rid"]
            else:
                log("no league %s in this build: region %s has no Interior zone" % (lg, reg))
    maps = []
    for reg, zs in data["regional"]["regioes"].items():
        short = SHORT.get(reg, reg)
        for zn in zs:
            lg = "Regional %s" % short if zn == "Zona 1" else "Regional %s %s" % (short, zn)
            if lg in by and reg in ti_zone and reg in fa_zone:
                maps += [by[lg]["rid"], ti_zone[reg], fa_zone[reg][0]]
    maps += [by[PR]["rid"], by[PC]["rid"], by[BM]["rid"], by[PRB]["rid"], by[PCB]["rid"], by[BM]["rid"]]
    ties = []
    for c in CUPS:
        for tie, win, lose in c["rtie"]:
            ties += [c["rid"], tie, win, lose]
    v = [len(groups) // 6] + groups + [len(homes)] + [x for h in homes for x in h] + [len(maps) // 3] + maps \
        + [len(ties) // 4] + ties + [0]
    lines.append("jline fl26_join_regional " + " ".join(str(x) for x in v))
    # 21/11/2026 (the first 0.4.0 test: every Argentine league stopped at the end of June, closed at the July teardown
    # as an August-May one): the region plays January to December -- its leagues close at New Year (fl26join)
    lines.append("season %d 1" % by[PN]["region"])
    lines.append("jline fl26_join_rflags " + " ".join(str(x) for x in flags))
    # the Libertadores' Argentine places (GUIA 3.1, AFA): ARG 1 the Apertura's champion, ARG 2 the Clausura's, ARG 3 the
    # Copa Argentina's (the game's reg 59), each falling to the annual table's next club without a place; ARG 4 and 5
    # the annual table's best without one; ARG 6 the next, in the 2nd qualifying phase (LIBQ). `uefa <reg> <pos> <comp>
    # <alt>`, comp 3 = the group stage, 4 = the qualifying; pos 0 = the winner of reg. The Copa Sudamericana's
    # (ARG 1-6 the next six) stay the game's own: the access list has no Sudamericana place [pendente: copas]
    ap, cp = rid_of["LPF-AP"], rid_of["LPF-CP"]
    for reg_, pos, comp_, alt in ((ap, 0, 3, LPF), (cp, 0, 3, LPF), (59, 0, 3, LPF), (LPF, 1, 3, 0), (LPF, 2, 3, 0), (LPF, 3, 4, 0)):
        lines.append("uefa %d %d %d %d" % (reg_, pos, comp_, alt))
    seed = []
    for nm, (p24, p25) in lpf.PROM_SEED.items():
        tid = lpf_tid[lpf.GAME_NAME[nm]]
        for y, p in ((2024, p24), (2025, p25)):
            if p is not None:
                seed += [tid, y, p, lpf.PROM_PJ[y]]
    lines.append("jline fl26_join_rprom %d 2 %d %s" % (LPF, len(seed) // 4, " ".join(str(x) for x in seed)))
    lines.append("sline fl26_swiss_filiation " + " ".join(str(x) for x in sorted(set(direct))))
    inv = [x for c in CUPS if c.get("invite") for x in (c["rid"],) + tuple(c["invite"])]
    lines.append("jline fl26_join_rinvite " + " ".join(str(x) for x in inv))
    lines.append("jline fl26_join_rlast " + " ".join(str(x) for x in rl))
    rh = []
    for z, pair in enumerate(INTERIOR_PAIRS):
        lg = TI if z == 0 else "%s Zona %d" % (TI, z + 1)
        if lg not in by:
            continue
        for reg in pair:
            zs = data["regional"]["regioes"].get(reg) or data["regional"]["regioes"].get(reg.replace("ó", "o")) or {}
            homes_ = [by[regional.zone_name(reg, zn)]["rid"] for zn in zs if regional.zone_name(reg, zn) in by]
            rh += [by[lg]["rid"], 2, 5, ti.FROM, 0, len(homes_)] + homes_
    lines.append("jline fl26_join_rlasth " + " ".join(str(x) for x in rh))
    sleep = []
    for n, L in by.items():
        if n.startswith(TI):
            ids = entries.get(L["cid"], [])
            sleep += [L["rid"], len(ids)] + ids
    lines.append("jline fl26_join_rsleep " + " ".join(str(x) for x in sleep))
    log("mover: %d league(s), %d home(s), %d map(s), %d tie rule(s); Interior asleep on %d placeholder(s); "
          "regions -> Federal A zone: %s" % (len(groups) // 6, len(homes), len(maps) // 3, len(ties) // 4,
                                             len(sleep) - 2 * 4, {k: v[0] for k, v in fa_zone.items()}))
    have_nl = {str(nl) for L in by.values() for nl in (L.get("newlife_tid") or {})}
    missing = [n for n, x in info.items() if str(x.get("nl")) not in have_nl
               and not any(n == norm(nm) for L in by.values() for nm in (L.get("club_names") or []))]
    if missing:
        log("clubs of the sources with no club of the build (no home):", missing[:20])

    # lab 23/11/2026 (the user, Select Team of a new Master League: "every zone grouped, not so many rows"): folders
    # inside Argentina's level (fl26confgroups confsub): each division's zones and phases under one row, the Regional
    # under "Regionais" and each region under its own row
    folds, fsub = [], []
    def folder(name, parent, cid, leagues):
        f = len(folds) + 1
        folds.append("%d:%d:%d:%s" % (f, parent, cid, name))
        fsub.extend("%d:%d" % (by[n]["slot"], f) for n in leagues if n in by and by[n].get("slot", 255) < 1024)
        return f
    zones_of = lambda h: [h] + sorted((n for n in by if n.startswith(h + " Zona ")), key=lambda n: int(re.sub(r"\D", "", n.rsplit(" ", 1)[1]) or 0) if n.rsplit(" ", 1)[1].isdigit() else n)
    folder(PN, 0, 0, [PN, PNB])
    folder(PC, 0, 0, [PC, PCB])
    folder(FA, 0, 0, [FA] + [n for n in by if n.startswith(FA + " ")])
    folder(PR, 0, 0, [PR, PRB])
    folder(TI, 0, 0, zones_of(TI))
    rg = folder("Regionais", 0, rg_entry_cid, [])
    for h in hosts_rg:
        folder(h, rg, 0, zones_of(h))
    lines.append("confsub slots=" + ",".join(fsub))
    lines.append("confsubnames " + "|".join(folds))
    log("Select Team folders: %d, %d league(s) in them" % (len(folds), len(fsub)))

    # ---- write: our lines replace the earlier ones of the same kinds (a world built again keeps none twice)
    keys = ("lphase", "lpname", "sline", "jline", "confsub", "confsubnames")   # (our uefa lines: their comp 3 / 4)
    path = os.path.join(root, B.MARK)
    old = [l for l in open(path, encoding="utf-8").read().splitlines() if l.split(" ", 1)[0] not in keys
           and not re.match(r"^uefa \d+ \d+ [34] \d+$", l) and l not in lines]   # (our season line: once)
    old = [sud_field(l) for l in old]
    open(path, "w", encoding="utf-8").write("\n".join(old + lines) + "\n")
    log("argentina: %d line(s) of the world file" % len(lines))
    from . import emblems
    emb = {c["cid"]: c["logo"] for c in CUPS if c.get("logo")}
    emb.update({by[n]["cid"]: f for n, f in emblems.LEAGUES.items() if n in by})
    if rg_entry_cid:
        emb[rg_entry_cid] = emblems.REGIONAL
    emblems.write(root, emb, log)
