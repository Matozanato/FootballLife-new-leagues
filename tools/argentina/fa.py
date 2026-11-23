"""The Torneo Federal A 2026 for mundo040.py (lab, 21/11/2026), GUIA-ARGENTINA-FL27.md 3.4:

  1st phase   the four zones of the recipe (10, 9, 9, 9), home and away, to 09/08
  2nd phase   two zones of 9, one round, from zero (mphase, from 16/08): A = the 1st-5th of Zona 1 and the 1st-4th of
              Zona 2; B = the 1st-4th of Zonas 3 and 4 and the best 5th (of the zones of 9)
  Reválida 1  the other 19 in two zones, one round (mphase): A = the rest of Zonas 1 and 2 and the 2nd best 5th,
              B = the rest of Zonas 3 and 4 and the 3rd best 5th [adaptação: the source splits them by geography]
  Zona Campeonato  1A v 4B, 2A v 3B, 1B v 4A, 2B v 3A, two legs, a level tie to the better placed; semi-finals two legs
              (reseeded by the 2nd phase's general table); the final one match, neutral, penalties: its winner goes up,
              its loser to the Reválida's 4th stage
  Reválida 2-6  2nd stage 24 (the Reválida zones' 1st-5th, the 2nd phase's 5th-9th, the four quarter-final losers),
              1 v 24 ... by the general table [adaptação: the order the source gives is the AFA's]; 3rd stage 12 + the two
              semi-final losers; 4th stage 7 + the final's loser; then 4 and 2; two legs, a level tie to the better
              placed, the last tie on penalties (its own regulation): its winner goes up
  down        the Reválida zones' last: 2 + 2 in 2026, 3 + 3 from 2027 (by points [adaptação: Zona A goes by promedio])
Days [a confirmar]: the 1st phase as the recipe; Sundays from 16/08, a midweek leg where the stages crowd."""
Z1, Z2, Z3, Z4 = "Torneo Federal A", "Torneo Federal A Zona 2", "Torneo Federal A Zona 3", "Torneo Federal A Zona 4"
F2A, F2B = "Torneo Federal A 2ª fase", "Torneo Federal A 2ª fase Zona B"
RVA, RVB = "Torneo Federal A Reválida", "Torneo Federal A Reválida Zona B"
PHASES = (F2A, F2B, RVA, RVB)


def T(lg, p): return ("t", lg, p)
def REST(lg, p): return ("rest", lg, p)


# mphase: (league, fill, after, sources, groups); group 0: the 5ths of the zones of 9
FIFTHS = [[T(Z2, 5), T(Z3, 5), T(Z4, 5)]]
MPHASES = [
    (F2A, "08-10", Z1, [T(Z1, p) for p in range(1, 6)] + [T(Z2, p) for p in range(1, 5)], []),
    (F2B, "08-10", Z1, [T(Z3, p) for p in range(1, 5)] + [T(Z4, p) for p in range(1, 5)] + [("r", 0, 1)], FIFTHS),
    (RVA, "08-10", Z1, [REST(Z1, 6), REST(Z2, 6), ("r", 0, 2)], FIFTHS),
    (RVB, "08-10", Z1, [REST(Z3, 6), REST(Z4, 6), ("r", 0, 3)], FIFTHS),
]

CUPS = [
    dict(code="FA-ZC", name="Zona Campeonato", host=Z1, et=False, pens=False, tier=3, fill="10-12",
         rounds=[(2, 0, "10-18", "10-25"), (2, 1, "11-01", "11-08")], names=["Quartas de final", "Semifinais"],
         ties=[(0, T(F2A, 1), T(F2B, 4)), (0, T(F2A, 2), T(F2B, 3)), (0, T(F2B, 1), T(F2A, 4)), (0, T(F2B, 2), T(F2A, 3)),
               (1, ("w", 0, None), ("w", 1, None)), (1, ("w", 2, None), ("w", 3, None))], rtie=[]),
    dict(code="FA-ZCF", page_of="FA-ZC", name="Final do acesso", host=Z1, et=False, pens=True, tier=3, fill="11-09",
         rounds=[(1, 1, "11-15", None)], names=["Final"],
         ties=[(0, ("w", 4, "FA-ZC"), ("w", 5, "FA-ZC"))], rtie=[(0, 2, 0)]),
    dict(code="FA-REV", name="Reválida", host=Z1, et=False, pens=False, tier=3, fill="10-26",
         rounds=[(2, 1, "11-01", "11-08"), (2, 1, "11-15", "11-22"), (2, 1, "11-25", "11-29"), (2, 1, "12-02", "12-06")],
         names=["2ª etapa", "3ª etapa", "4ª etapa", "5ª etapa"],
         ties=[], rtie=[]),
    dict(code="FA-REVF", page_of="FA-REV", name="Final da Reválida", host=Z1, et=False, pens=True, tier=3, fill="12-07",
         rounds=[(2, 1, "12-09", "12-13")], names=["Final"], ties=[], rtie=[(0, 2, 0)]),
]


def _reválida():
    rev = next(c for c in CUPS if c["code"] == "FA-REV")
    field = [T(RVA, p) for p in range(1, 6)] + [T(RVB, p) for p in range(1, 6)] \
        + [T(F2A, p) for p in range(5, 10)] + [T(F2B, p) for p in range(5, 10)] + [("l", k, "FA-ZC") for k in range(4)]
    ties = [(0, field[i], field[i + 1]) for i in range(0, 24, 2)]                       # 0-11
    f3 = [("w", k, None) for k in range(12)] + [("l", 4, "FA-ZC"), ("l", 5, "FA-ZC")]
    ties += [(1, f3[i], f3[i + 1]) for i in range(0, 14, 2)]                            # 12-18
    f4 = [("w", k, None) for k in range(12, 19)] + [("l", 0, "FA-ZCF")]
    ties += [(2, f4[i], f4[i + 1]) for i in range(0, 8, 2)]                             # 19-22
    ties += [(3, ("w", 19, None), ("w", 20, None)), (3, ("w", 21, None), ("w", 22, None))]   # 23-24
    rev["ties"] = ties
    fin = next(c for c in CUPS if c["code"] == "FA-REVF")
    fin["ties"] = [(0, ("w", 23, "FA-REV"), ("w", 24, "FA-REV"))]


_reválida()
# the Reválida zones' last places: (league, n, tier, from season, to season)
RLAST = [(RVA, 2, 4, 2026, 2026), (RVB, 2, 4, 2026, 2026), (RVA, 3, 4, 2027, 0), (RVB, 3, 4, 2027, 0)]
