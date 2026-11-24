"""The interzonal matches for mundo040.py (lab, 21/11/2026), counted in each club's zone table (fl26swiss izone):
  Primera Nacional  one rival, home and away (argentina2026.json "interzonal", from the source)
  Primera C         three rivals, home and away ("tres fechas interzonales sin repetición de encuentros, local y
                    visitante ... conforme el sorteo": AFA Boletín 6825, art. 2). The 84 matches (fecha, home, away)
                    read from the Wikipedia page's wikitext (21/11/2026): c_interzonal_2026.json
Days: the source's interzonal fechas (PN 7 and 25; C 4, 8, 12, 20, 24, 28), each on its weekend's Sunday (one day a
round in the game; the zones' rounds are on Saturdays)."""
import json, os, re, unicodedata

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PN, PNB, PC, PCB = "Primera Nacional", "Primera Nacional Zona B", "Primera C", "Primera C Zona B"
C_RIVALS = {
    "Argentino de Rosario": ["Yupanqui", "Atlas", "Central Córdoba"],
    "Berazategui": ["Central Córdoba", "Fénix", "Atlas"],
    "Centro Español": ["Leones de Rosario", "Central Córdoba", "Fénix"],
    "Defensores de Cambaceres": ["General Lamadrid", "Leones de Rosario", "Sportivo Barracas"],
    "Deportivo Paraguayo": ["Central Ballester", "Sportivo Barracas", "Luján"],
    "Estrella del Sur": ["Luján", "Cañuelas", "Yupanqui"],
    "J. J. de Urquiza": ["Muñiz", "El Porvenir", "General Lamadrid"],
    "Juventud Unida": ["Claypole", "Muñiz", "El Porvenir"],
    "Leandro N. Alem": ["Cañuelas", "Central Ballester", "Muñiz"],
    "Lugano": ["Sportivo Barracas", "Luján", "Leones de Rosario"],
    "Mercedes": ["El Porvenir", "Claypole", "Deportivo Español"],
    "Puerto Nuevo": ["Fénix", "Yupanqui", "Central Ballester"],
    "Sacachispas": ["Atlas", "Deportivo Español", "Claypole"],
    "Victoriano Arenas": ["Deportivo Español", "General Lamadrid", "Cañuelas"],
}
PN_DAYS = ["03-29", "08-16"]          # fechas 7 and 25 (the source: 27-29/03, 14-16/08), on the Sunday
PC_DAYS = {4: "03-22", 8: "04-19", 12: "05-17", 20: "07-19", 24: "08-16", 28: "09-13"}   # fechas 4..28, the Sunday
# the C's 84 interzonal matches as the source lists them (fecha, home, away): c_interzonal_2026.json, read from the
# Wikipedia page's wikitext 21/11/2026 -- the same 42 pairs as C_RIVALS, each twice, one home each


def norm(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower())


def team_finder(by, leagues):
    """name -> team id among the clubs of those leagues (exact, then one containing the other)"""
    pool = []
    for lg in leagues:
        L = by[lg]
        for nm, tid in zip(L.get("club_names") or [], L.get("teams") or []):
            pool.append((norm(nm), tid, nm))

    alias = {"J. J. de Urquiza": "J.J. Urquiza", "Leandro N. Alem": "L.N. Alem", "Leones de Rosario": "Leones"}

    def find(name):
        k = norm(alias.get(name, name))
        hit = [t for n, t, _ in pool if n == k] or [t for n, t, _ in pool if k and (k in n or n in k)]
        if len(set(hit)) != 1:
            raise SystemExit("interzonal: %r -> %d club(s) of %s" % (name, len(set(hit)), leagues))
        return hit[0]
    return find


def matchings(rivals):
    """the 3-regular pairs as three perfect matchings (augmenting paths; König says they exist)"""
    edges = {(a, b) for a, bs in rivals.items() for b in bs}
    left = sorted(rivals)
    out = []
    while edges:
        match = {}

        def aug(a, seen):
            for b in sorted(x for y, x in edges if y == a):
                if b in seen:
                    continue
                seen.add(b)
                if b not in match or aug(match[b], seen):
                    match[b] = a
                    return True
            return False
        for a in left:
            if not aug(a, set()):
                raise SystemExit("interzonal: no perfect matching left at %s" % a)
        rnd = sorted((a, b) for b, a in match.items())
        out.append(rnd)
        edges -= set(rnd)
    return out


def cups(by):
    data = json.load(open(os.path.join(HERE, "argentina2026.json"), encoding="utf-8"))
    fpn = team_finder(by, [PN, PNB])
    fpc = team_finder(by, [PC, PCB])
    team = lambda tid: ("team", tid)
    # one match a round, in date order: the first half's (the first named at home), then the same pairs the other
    # way round in the second half [adaptação: who is at home first]
    pairs = [(fpn(a), fpn(b)) for a, b in data["primera_nacional"]["interzonal"]]
    pn_ties = [(0, team(a), team(b)) for a, b in pairs] + [(1, team(b), team(a)) for a, b in pairs]
    fx = json.load(open(os.path.join(HERE, "c_interzonal_2026.json"), encoding="utf-8"))
    fechas = sorted(PC_DAYS)
    alias_c = {"Argentino (R)": "Argentino de Rosario", "Central Córdoba (R)": "Central Córdoba", "Fenix": "Fénix"}
    pc_ties = [(fechas.index(x["fecha"]), team(fpc(alias_c.get(x["home"], x["home"]))), team(fpc(alias_c.get(x["away"], x["away"]))))
               for x in fx]
    return [
        dict(code="PN-IZ", name="Interzonal", host=PN, et=False, pens=False, tier=2, fill="03-20",
             rounds=[(1, 0, d, None) for d in PN_DAYS], names=["Data 7", "Data 25"],
             ties=pn_ties, rtie=[],
             izone=[PN, PNB]),
        dict(code="PC-IZ", name="Interzonal", host=PC, et=False, pens=False, tier=4, fill="03-15",
             rounds=[(1, 0, PC_DAYS[f], None) for f in sorted(PC_DAYS)], names=["Data %d" % f for f in sorted(PC_DAYS)],
             ties=sorted(pc_ties, key=lambda t: t[0]), rtie=[],
             izone=[PC, PCB]),
    ]
