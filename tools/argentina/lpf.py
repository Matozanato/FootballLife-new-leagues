"""The Liga Profesional for mundo040.py (lab, 21/11/2026): the 2027 format (approved 29/10/2026; La Página Millonaria
30/10/2026, El Litoral) on the game's own league (reg 30: 30 clubs, one round, 29 rounds in FL27, its shipped calendar
every 11 days January to December).
  30 rounds   the 29 of the game's round robin + one more meeting of each "clásico o emparejamiento" pair (home and
              away over the year: "la revancha de cada clásico/interzonal"); the extra meeting is a tcup round of 15
              fixed pairs on its own day, counted in the table (izone) [adaptação: it is the Clausura's 15th round]
  dates       Apertura: the game's rounds 1-15 on 15 Saturdays, 24/01 to 02/05; Clausura: rounds 16-29 on 14 Saturdays,
              25/07 to 24/10, the clásicos on 31/10 [a confirmar: the AFA's fixture is not out]
  tables      the annual one is the game's; Apertura / Clausura are counted by fl26swiss (lhalf: the Clausura from zero)
  play-offs   the first 16 of each half: 1 v 16, 2 v 15 ... (bracket 1-16 / 8-9 / 4-13 / 5-12 / 2-15 / 7-10 / 3-14 /
              6-11), one match, the better placed at home to the quarter-finals [adaptação: the pages say only "1° vs.
              16°"], semi-finals and final neutral; a level match goes to penalties [adaptação: not stated]
  Trofeo      the Apertura's champion v the Clausura's, one match, neutral, extra time and penalties, 19/12 (reg. LPF 2026
              art. 20-23); the same champion twice: [pendente]
  pairs       the 2026 draw's pairs (Wikipedia, "Emparejamientos", read as consecutive pairs) [a confirmar for 2027]"""
APERTURA = ["01-24", "01-31", "02-07", "02-14", "02-21", "02-28", "03-07", "03-14", "03-21", "03-28", "04-04", "04-11",
            "04-18", "04-25", "05-02"]
CLAUSURA = ["07-25", "08-01", "08-08", "08-15", "08-22", "08-29", "09-05", "09-12", "09-19", "09-26", "10-03", "10-10",
            "10-17", "10-24"]
CLASICOS_DAY = "10-31"
PAIRS = [("Boca Juniors", "River Plate"), ("Independiente", "Racing Club"), ("Huracán", "San Lorenzo"),
         ("Newell's Old Boys", "Rosario Central"), ("Estudiantes (LP)", "Gimnasia y Esgrima (LP)"),
         ("Gimnasia y Esgrima (M)", "Independiente Rivadavia"), ("Banfield", "Lanús"), ("Belgrano", "Talleres (C)"),
         ("Argentinos Juniors", "Platense"), ("Tigre", "Vélez Sarsfield"), ("Estudiantes (RC)", "Instituto"),
         ("Atlético Tucumán", "Central Córdoba (SdE)"), ("Sarmiento (J)", "Unión"), ("Barracas Central", "Deportivo Riestra"),
         ("Aldosivi", "Defensa y Justicia")]
BRACKET = [(1, 16), (8, 9), (4, 13), (5, 12), (2, 15), (7, 10), (3, 14), (6, 11)]


def H(half, pos): return ("half", half, pos)


def playoffs(code, name, half, days, fill):
    ties = [(0, H(half, a), H(half, b)) for a, b in BRACKET]
    ties += [(1, ("w", k, None), ("w", k + 1, None)) for k in range(0, 8, 2)]          # 8-11
    ties += [(2, ("w", 8, None), ("w", 9, None)), (2, ("w", 10, None), ("w", 11, None))]   # 12-13
    ties += [(3, ("w", 12, None), ("w", 13, None))]                                    # 14
    return dict(code=code, name=name, host="LPF", et=False, pens=True, tier=1, fill=fill, flags=2,
                rounds=[(1, 0, d, None) for d in days], names=["Oitavas de final", "Quartas de final", "Semifinais", "Final"],
                ties=ties, rtie=[])


def TROFEO_GROUP(tcd):
    """the Apertura's and the Clausura's champions and runners-up, and the tie-break's winner"""
    return [("w", 14, "LPF-AP"), ("w", 14, "LPF-CP"), ("l", 14, "LPF-AP"), ("l", 14, "LPF-CP"), ("w", 0, tcd)]


CUPS = [
    playoffs("LPF-AP", "Apertura - Playoffs", 1, ["05-09", "05-13", "05-17", "05-24"], "05-03"),
    playoffs("LPF-CP", "Clausura - Playoffs", 2, ["11-07", "11-14", "11-21", "11-28"], "11-01"),
    # the same champion twice: the two runners-up meet three days before (one match, neutral, extra time, penalties)
    # and the winner plays the Trofeo; the same runner-up twice: it plays the Trofeo straight away (reg. LPF 2026 art. 20-23)
    dict(code="LPF-TCD", name="Trofeo - desempate", host="LPF", et=True, pens=True, tier=1, fill="11-29",
         rounds=[(1, 0, "12-16", None)], names=["Desempate dos vices"],
         ties=[(0, ("cond", 1, 0), ("cond", 2, 0))], groups=[TROFEO_GROUP("LPF-TCD")], rtie=[]),
    dict(code="LPF-TC", name="Trofeo de Campeones", host="LPF", et=True, pens=True, tier=1, fill="11-29",
         rounds=[(1, 0, "12-19", None)], names=["Trofeo de Campeones"],
         ties=[(0, ("w", 14, "LPF-AP"), ("cond", 3, 0))], groups=[TROFEO_GROUP("LPF-TCD")], rtie=[]),
]

# the source's names -> the game's (FL27 2026 database)
GAME_NAME = {"Boca Juniors": "CA Boca Juniors", "River Plate": "CA River Plate", "Independiente": "CA Independiente",
             "Racing Club": "Racing Club", "Huracán": "CA Huracán", "San Lorenzo": "CA San Lorenzo",
             "Newell's Old Boys": "Newell's Old Boys", "Rosario Central": "CA Rosario Central",
             "Estudiantes (LP)": "Estudiantes de la Plata", "Gimnasia y Esgrima (LP)": "Gimnasia La Plata",
             "Gimnasia y Esgrima (M)": "Gimnasia de Mendoza", "Independiente Rivadavia": "Independiente Rivadavia",
             "Banfield": "CA Banfield", "Lanús": "Club Atlético Lanús", "Belgrano": "Club Atlético Belgrano",
             "Talleres (C)": "Club Atlético Talleres", "Argentinos Juniors": "Argentinos Juniors", "Platense": "CA Platense",
             "Tigre": "Club Atlético Tigre", "Vélez Sarsfield": "CA Vélez Sarsfield", "Estudiantes (RC)": "Estudiantes de Río Cuarto",
             "Instituto": "Instituto AC Córdoba", "Atlético Tucumán": "Atlético Tucumán",
             "Central Córdoba (SdE)": "Central Córdoba SDE", "Sarmiento (J)": "CA Sarmiento", "Unión": "Club Atlético Unión",
             "Barracas Central": "CA Barracas Central", "Deportivo Riestra": "Deportivo Riestra", "Aldosivi": "CA Aldosivi",
             "Defensa y Justicia": "Defensa y Justicia"}

# the promedio's seasons before the career (Wikipedia, "Tabla de descenso por promedio", 21/11/2026, from a model summary
# of the page: [a confirmar]): points 2024, 2025; matches 41 (2024) and 32 (2025) a season, as the table's 105 = 41 + 32 + 32
PROM_SEED = {"Boca Juniors": (67, 62), "River Plate": (70, 53), "Rosario Central": (47, 66), "Argentinos Juniors": (56, 57),
             "Vélez Sarsfield": (76, 40), "Lanús": (59, 50), "Racing Club": (70, 53), "Independiente": (63, 47),
             "Huracán": (62, 47), "Estudiantes (LP)": (63, 42), "Independiente Rivadavia": (46, 43), "Barracas Central": (49, 49),
             "Talleres (C)": (72, 34), "Gimnasia y Esgrima (LP)": (48, 38), "Defensa y Justicia": (58, 38), "Instituto": (53, 34),
             "Unión": (60, 39), "San Lorenzo": (45, 51), "Belgrano": (49, 37), "Gimnasia y Esgrima (M)": (None, None),
             "Platense": (57, 35), "Tigre": (39, 49), "Deportivo Riestra": (48, 52), "Newell's Old Boys": (49, 33),
             "Atlético Tucumán": (50, 34), "Central Córdoba (SdE)": (42, 42), "Sarmiento (J)": (35, 35), "Banfield": (41, 35),
             "Aldosivi": (None, 33), "Estudiantes (RC)": (None, None)}
PROM_PJ = {2024: 41, 2025: 32}
