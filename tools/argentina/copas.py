"""(23/11/2026, the user: "participants and matches at the start of the season, as the game's other cups"): every
cup is filled on 03/01 -- its clubs are known by then (the 2026 real ones; then last year's titles and table, and this
season's leagues after the New Year) -- so Competition Info shows its clubs and ties from the season's start.

Argentina's cups on Mod Studio 0.4.0 (lab, 23/11/2026; GUIA-ARGENTINA-FL27.md 3.8-3.9, D2): fl26swiss tcups.

- Copa Argentina: the game's own competition (comp 49, reg 59) played as a tcup in place -- its name, its emblem and
  the Libertadores' ARG 3 (`uefa 59 0 3 30`) stay. 64 clubs: the 30 of the LPF, 15 of the Primera Nacional, 10 of the
  Federal A, 5 of the B Metro and 4 of the C (the 2026 quotas). Who of each division [adaptacao: the AFA's criterion
  is not published]: the strongest squads of this season's leagues, the cup being filled in January before any table.
  Six rounds of one match; a level match goes straight to penalties (no extra time) [a confirmar]. Neutral ground in
  the real cup: here the first club named is at home [adaptacao]. The round of 64 pairs the LPF's strongest with the
  ascenso's weakest; the four strongest of the ascenso meet each other [adaptacao: the real draw goes by zones].
  2026: the real draw (CA_2026). Days: the round of 64 from 28/01 and the final on 02/12 (2026); the rounds between [a confirmar], on Wednesdays off
  the Libertadores' days.
- Supercopa Argentina: the game's own (comp 79, reg 92) in place. Last season's Copa winner v the Trofeo de Campeones'
  winner (the Trofeo's runner-up when one club won both; reg. LPF 2026 art. 29). One match, extra time and penalties,
  12/11. 2026: the real clubs (Independiente Rivadavia v Estudiantes).
- Supercopa Internacional (new competition): the Trofeo's winner (at home: the organiser's) v last season's champion
  of the Liga (the annual table's 1st; the 2nd when the Trofeo's winner is the champion; no relegated club: art. 30).
  One match, extra time and penalties, 26/09 (the 2026 date). 2026: the real clubs.
- Recopa de Campeones (new competition, art. 31): the winners of the Copa Argentina, the Supercopa Argentina and the
  Supercopa Internacional, a triangular of three matches (J1 SA v SI, J2 Copa v J1's loser, J3 Copa v J1's winner),
  a level match straight to penalties, 3/2/1/0 points (fl26swiss TC_F_TRI). Replacements as art. 31. Days [a
  confirmar]: 25/02, 11/03, 01/04. From 2027 (the 2026 super cups and Copa played in the game).
"""

PN, PNB = "Primera Nacional", "Primera Nacional Zona B"
BM = "Primera B Metropolitana"
PC, PCB = "Primera C", "Primera C Zona B"
FA1, FA2, FA3, FA4 = "Torneo Federal A", "Torneo Federal A Zona 2", "Torneo Federal A Zona 3", "Torneo Federal A Zona 4"


def Str(lg, k): return ("str", lg, k)
def W(k, cup=None): return ("w", k, cup)
def Ls(k, cup=None): return ("l", k, cup)
def Kept(cup, runner): return ("kept", cup, runner)
def Alt(src): return ("alt", src)


def _copa():
    lpf = [Str("LPF", k) for k in range(1, 31)]
    quota = [(PN, 8), (PNB, 7), (FA1, 3), (FA2, 3), (FA3, 2), (FA4, 2), (BM, 5), (PC, 2), (PCB, 2)]
    asc, k = [], 1                                        # round by round: every division's strongest first
    while len(asc) < sum(n for _l, n in quota):
        for lg, n in quota:
            if k <= n:
                asc.append(Str(lg, k))
        k += 1
    ties = [(0, lpf[i], asc[33 - i]) for i in range(30)] + [(0, asc[0], asc[3]), (0, asc[1], asc[2])]
    first, n = 0, 32
    for r in range(1, 6):                                 # the bracket: the winners of ties 2i and 2i+1
        ties += [(r, W(first + 2 * i), W(first + 2 * i + 1)) for i in range(n // 2)]
        first += n
        n //= 2
    assert len(ties) == 63
    return dict(code="CA", name="Copa Argentina", host="LPF", own=(49, 59), y1=(2026, CA_2026), et=False, pens=True, tier=1, fill="01-03",
                rounds=[(1, 0, "01-28", None), (1, 0, "04-08", None), (1, 0, "07-15", None), (1, 0, "09-09", None),
                        (1, 0, "10-14", None), (1, 0, "12-02", None)],
                names=["32avos de final", "16avos de final", "Oitavas de final", "Quartas de final", "Semifinais",
                       "Final"], ties=ties, rtie=[])


CA_FINAL = 62

# lab 23/11/2026 (the user: "the 2026 cups with the clubs already defined; from 2027 by the criteria"): the real 2026
# editions. Copa Argentina 2026: the draw of 10/12/2025 (Infobae, "Sortearon los cruces de la Copa Argentina 2026"),
# matches 1-32 in its order, the first named at home; the round of 32 pairs the winners of 1-2, 3-4 ... [a confirmar:
# the source gives no numbered bracket]. Names: the world's clubs (the build's, the game's for the LPF).
CA_2026 = [("CA San Lorenzo", "Deportivo Rincón"), ("CA Huracán", "Olimpo"), ("CA River Plate", "Ciudad de Bolívar"),
           ("CA Boca Juniors", "Gimnasia y Esgrima (C)"), ("Racing Club", "San Martín (F)"),
           ("CA Independiente", "Atenas (RC)"), ("CA Platense", "Argentino (MM)"),
           ("Argentinos Juniors", "Ferrocarril Midland"), ("CA Banfield", "Real Pilar Fútbol Club"),
           ("Club Atlético Lanús", "Sarmiento (LB)"), ("Club Atlético Talleres", "Club Atlético Argentino de Mer"),
           ("Club Atlético Belgrano", "Atlético de Rafaela"), ("CA Vélez Sarsfield", "Club Deportivo Armenio"),
           ("Club Atlético Tigre", "Claypole"), ("Estudiantes de la Plata", "Club Atlético Ituzaingó"),
           ("Gimnasia La Plata", "Camioneros"), ("Newell's Old Boys", "Acassuso"),
           ("CA Rosario Central", "Sportivo Belgrano"), ("Independiente Rivadavia", "Estudiantes (BA)"),
           ("Gimnasia de Mendoza", "Gimnasia y Tiro (S)"), ("Central Córdoba SDE", "Gimnasia y Esgrima (J)"),
           ("Atlético Tucumán", "Sportivo Barracas"), ("Instituto AC Córdoba", "Atlanta"),
           ("Estudiantes de Río Cuarto", "San Martín (T)"), ("Godoy Cruz", "Deportivo Morón"),
           ("San Martín (SJ)", "Deportivo Madryn"), ("Club Atlético Unión", "Agropecuario"),
           ("Defensa y Justicia", "Chaco For Ever"), ("CA Sarmiento", "Tristán Suárez"), ("CA Aldosivi", "San Miguel"),
           ("CA Barracas Central", "Temperley"), ("Deportivo Riestra", "Deportivo Maipú")]
# Supercopa Argentina 2026 (12/11, Córdoba): Independiente Rivadavia (Copa Argentina 2025) v Estudiantes (Trofeo de
# Campeones 2025); Supercopa Internacional 2026 (26/09, Santiago del Estero): Estudiantes (Trofeo 2025, at home) v
# Rosario Central (the 2025 annual table's 1st) -- AFA / Liga Profesional, Cadena 3

CUPS = [
    _copa(),
    dict(code="SA", name="Supercopa Argentina", host="LPF", own=(79, 92), et=True, pens=True, tier=1, fill="01-03", item="Final",
         y1=(2026, [("Independiente Rivadavia", "Estudiantes de la Plata")]), rounds=[(1, 0, "11-12", None)], names=["Final"],
         ties=[(0, Kept("CA", 0), Alt(W(0, "LPF-TC")))], rtie=[]),
    dict(code="SI", name="Supercopa Internacional", host="LPF", own=True, logo="supercopa_internacional.png", et=True, pens=True, tier=1, fill="01-03", item="Final",
         y1=(2026, [("Estudiantes de la Plata", "CA Rosario Central")]), rounds=[(1, 0, "09-26", None)], names=["Final"],
         ties=[(0, W(0, "LPF-TC"), ("prev", "LPF", 1))], rtie=[]),
    dict(code="RC", name="Recopa de Campeones", host="LPF", own=True, logo="recopa_de_campeones.png", et=False, pens=True, tier=1, fill="01-03", item="Jogos",
         start=2027, flags=4, rounds=[(1, 0, "02-25", None), (1, 0, "03-11", None), (1, 0, "04-01", None)],
         names=["1º jogo", "2º jogo", "3º jogo"],
         ties=[(0, ("cond", 4, 0), ("cond", 5, 0)), (1, ("cond", 6, 0), Ls(0)), (2, ("cond", 6, 0), W(0))],
         groups=[[Kept("CA", 0), Kept("SA", 0), Kept("SA", 1), Kept("SI", 0), Kept("SI", 1), Kept("CA", 1)]], rtie=[]),
]
