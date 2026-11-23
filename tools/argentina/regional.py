"""The Regional Federal Amateur's knockouts for mundo040.py (lab, 21/11/2026): one tcup per region and the 2026 final
stage, from the regulation as the source gives it (fontes/Torneo_Regional_Federal_Amateur_2026.wiki, "Primera ronda"
of each region) and the zones' sizes of argentina2026.json.

  every round two legs, penalties when level (no extra time); a round's ties paired 1 v N by the general table of the
  region's zones (the source names the pairs only in its bracket: [adaptação]); the final stage (2026 only): the
  eight regional winners in four one-match ties, neutral, penalties, on 20/12 -- the pairs are the Consejo Federal's
  [adaptação: by neighbouring regions]. Rounds' days [a confirmar]: Sundays from the zones' end (12/10), the five-round
  regions with one midweek leg.
Sources here as in mundo040.CUPS, plus ("r", group, n): the n-th best of the cup's group of candidates."""
import json, os

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SHORT = {"Bonaerense Pampeana Norte": "Pampeana Norte", "Bonaerense Pampeana Sur": "Pampeana Sur"}
DAYS4 = [("10-25", "11-01"), ("11-08", "11-15"), ("11-22", "11-29"), ("12-06", "12-13")]
DAYS5 = [("10-18", "10-21"), ("10-25", "11-01"), ("11-08", "11-15"), ("11-22", "11-29"), ("12-06", "12-13")]
FINAL_PAIRS = [("Norte", "Cuyo"), ("Litoral Norte", "Litoral Sur"), ("Centro", "Bonaerense Pampeana Norte"),
               ("Bonaerense Pampeana Sur", "Patagónica")]
ROUND_NAME = {2: "2ª rodada", 3: "3ª rodada", 4: "4ª rodada", 5: "5ª rodada", 6: "6ª rodada"}


def zone_name(reg, zn):
    short = SHORT.get(reg, reg)
    return "Regional %s" % short if zn == "Zona 1" else "Regional %s %s" % (short, zn)


def cups():
    data = json.load(open(os.path.join(HERE, "argentina2026.json"), encoding="utf-8"))
    out, finals = [], {}
    for reg, zs in data["regional"]["regioes"].items():
        zones = sorted(zs, key=lambda z: int(z.split()[-1]))
        size = {z: len(zs[z]) for z in zones}
        Z = [zone_name(reg, z) for z in zones]
        z4 = [zone_name(reg, z) for z in zones if size[z] == 4]
        z3 = [zone_name(reg, z) for z in zones if size[z] == 3]
        z2 = [zone_name(reg, z) for z in zones if size[z] == 2]
        T = lambda lg, p: ("t", lg, p)
        groups, direct, second = [], [], []           # direct: into the first knockout round of 16 (or the 3rd round)
        if reg in ("Norte",):
            direct = [T(z, p) for z in Z for p in (1, 2)]
        elif reg == "Litoral Norte":                  # 1st and 2nd of the zones of 3+, the best 3rd of the zones of 4, Zona 1's winner
            groups = [[T(z, 3) for z in z4]]
            direct = [T(z, p) for z in z4 + z3 for p in (1, 2)] + [("r", 0, 1)] + [T(z, 1) for z in z2]
        elif reg == "Litoral Sur":                    # 1st and 2nd of all, the two best 3rds of the zones of 4
            groups = [[T(z, 3) for z in z4]]
            direct = [T(z, p) for z in Z for p in (1, 2)] + [("r", 0, 1), ("r", 0, 2)]
        elif reg in ("Centro", "Bonaerense Pampeana Norte"):
            # the leaders and the best 2nd of the zones of 4 to the 3rd round; the other 2nds of the zones of 4 and the
            # best 2nds of the zones of 3 (Centro five, Pampeana Norte two) to the 2nd round
            k3 = 5 if reg == "Centro" else 2
            groups = [[T(z, 2) for z in z4], [T(z, 2) for z in z3]]
            direct = [T(z, 1) for z in Z] + [("r", 0, 1)]
            second = [("r", 0, n) for n in range(2, len(z4) + 1)] + [("r", 1, n) for n in range(1, k3 + 1)]
        elif reg == "Cuyo":                           # the leaders of the zones of 4 to the 3rd round (guide 3.6b)
            direct = [T(z, 1) for z in z4]
            second = [T(z, 2) for z in z4] + [T(z, p) for z in z3 for p in (1, 2)]
        elif reg == "Bonaerense Pampeana Sur":
            # the leaders of the zones of 4 and the two best leaders of the zones of 3 to the 3rd round; the 2nds of the
            # zones of 4, the other leaders of the zones of 3 and the three best 2nds of the zones of 3 to the 2nd
            groups = [[T(z, 1) for z in z3], [T(z, 2) for z in z3]]
            direct = [T(z, 1) for z in z4] + [("r", 0, 1), ("r", 0, 2)]
            second = [T(z, 2) for z in z4] + [("r", 0, n) for n in range(3, len(z3) + 1)] + [("r", 1, n) for n in (1, 2, 3)]
        else:                                          # Patagónica: 1st and 2nd of the zones of 4 to the 3rd round;
            groups = [[T(z, 2) for z in z3]]          # the leaders of the zones of 3 and the five best 2nds to the 2nd
            direct = [T(z, p) for z in z4 for p in (1, 2)]
            second = [T(z, 1) for z in z3] + [("r", 0, n) for n in range(1, 6)]
        ties, rounds, names = [], [], []
        r = 0
        if second:                                     # the 2nd round, then its winners join the direct ones
            assert len(second) % 2 == 0, reg
            for i in range(0, len(second), 2):
                ties.append((r, second[i], second[i + 1]))
            field = direct + [("w", k, None) for k in range(len(ties))]
            first_round_no = 2
            names.append(ROUND_NAME[2])
            r += 1
        else:
            field = direct
            first_round_no = 2
        assert len(field) & (len(field) - 1) == 0, (reg, len(field))
        prev = []
        start = len(ties)
        for i in range(0, len(field), 2):
            ties.append((r, field[i], field[i + 1]))
        names.append(ROUND_NAME[first_round_no + r])
        prev = list(range(start, len(ties)))
        r += 1
        while len(prev) > 1:
            start = len(ties)
            for i in range(0, len(prev), 2):
                ties.append((r, ("w", prev[i], None), ("w", prev[i + 1], None)))
            prev = list(range(start, len(ties)))
            names.append("Final regional" if len(prev) == 1 else ROUND_NAME[first_round_no + r])
            r += 1
        days = DAYS5 if r == 5 else DAYS4
        assert r <= len(days), (reg, r)
        days = days[len(days) - r:]
        code = "RG-" + {"Norte": "N", "Litoral Norte": "LN", "Litoral Sur": "LS", "Centro": "CE", "Cuyo": "CU",
                        "Bonaerense Pampeana Norte": "PN", "Bonaerense Pampeana Sur": "PS"}.get(reg, "PA")
        out.append(dict(code=code, name="Mata-mata regional", host=zone_name(reg, "Zona 1"), hosts=[zone_name(reg, "Zona 1")],
                        et=False, pens=True, tier=5, fill="10-13",
                        rounds=[(2, 1, a, b) for a, b in days], names=names, ties=ties, groups=groups,
                        rtie=[(len(ties) - 1, 4, 4)],                 # the two finalists to the Interior (D10)
                        invite=(6, 4, 2026)))                         # 2026: the best six not promoted (D11)
        finals[reg] = (code, len(ties) - 1)
    hosts = [zone_name(reg, "Zona 1") for reg in data["regional"]["regioes"]]
    out.append(dict(code="RG-ETF", name="Etapa final", host=hosts[0], hosts=hosts, et=False, pens=True, tier=5,
                    fill="12-14", until=2026, rounds=[(1, 0, "12-20", None)], names=["Etapa final"],
                    ties=[(0, ("w", finals[a][1], finals[a][0]), ("w", finals[b][1], finals[b][0])) for a, b in FINAL_PAIRS],
                    groups=[], rtie=[(k, 3, 4) for k in range(4)]))   # the four winners to the Federal A 2027
    return out


if __name__ == "__main__":
    for c in cups():
        print(c["code"], len(c["rounds"]), "rounds", len(c["ties"]), "ties", c["names"], c["rounds"][0])
