"""The Torneo Argentino del Interior for mundo040.py (lab, 21/11/2026), GUIA-ARGENTINA-FL27.md 3.6 (decisions D7, D11):
asleep in 2026; from 2027 four zones of 16 (two regions of 8 each), home and away, April to September, then:
  play-offs   the first four of each zone (16): round of 16 and quarter-finals, two legs, a level tie to the better
              placed [adaptação aprovada 19/11]; the four quarter-final winners go up to the Federal A
  repescagem  the four quarter-final losers in two ties, two legs, penalties: the two winners go up
  down        the two worst of each region of eight, in its zone's table (16) to the Regional
Pairs inside the rounds: by the general table of the four zones [adaptação: the regulation is not out]. Days: 2026's
Sundays for 2027 [a confirmar]. The zones' pairs of regions are mundo040.INTERIOR_PAIRS [adaptação]."""
TI = "Torneo Argentino del Interior"
ZONES = [TI] + ["%s Zona %d" % (TI, k) for k in (2, 3, 4)]
FROM = 2027


def T(lg, p): return ("t", lg, p)


field = [T(z, p) for z in ZONES for p in range(1, 5)]
CUPS = [
    dict(code="TI-PO", name="Playoffs", host=TI, et=False, pens=False, tier=4, fill="09-28", start=FROM,
         rounds=[(2, 1, "10-04", "10-11"), (2, 1, "10-18", "10-25")], names=["Oitavas de final", "Quartas de final"],
         ties=[(0, field[i], field[i + 1]) for i in range(0, 16, 2)]
              + [(1, ("w", k, None), ("w", k + 1, None)) for k in range(0, 8, 2)],
         rtie=[(k, 3, 0) for k in range(8, 12)]),
    dict(code="TI-REP", name="Repescagem", host=TI, et=False, pens=True, tier=4, fill="10-26", start=FROM,
         rounds=[(2, 1, "11-01", "11-08")], names=["Repescagem"],
         ties=[(0, ("l", 8, "TI-PO"), ("l", 9, "TI-PO")), (0, ("l", 10, "TI-PO"), ("l", 11, "TI-PO"))],
         rtie=[(0, 3, 0), (1, 3, 0)]),
]
