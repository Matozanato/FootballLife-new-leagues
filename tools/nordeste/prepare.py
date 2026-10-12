"""Prepare clubs and the exact 2026 competition specification; no game activation.

The stock 0.2.1 runtime cannot play this specification yet. The recipe builds
placeholder squads only, not a playable Copa do Nordeste.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
import leaguebuilder as L
import pesdb

# Official 2026 draw order. States describe the represented club, not a DB guess.
GROUPS = {
    "A": [("Vitória", "BA", "VIT", 1937), ("ASA", "AL", "ASA", None),
          ("Sousa", "PB", "SOU", None), ("Itabaiana", "SE", "ITA", None),
          ("Fluminense-PI", "PI", "FPI", None)],
    "B": [("Juazeirense", "BA", "JUA", None), ("CRB", "AL", "CRB", 2506),
          ("Botafogo-PB", "PB", "BOT", None), ("Confiança", "SE", "CON", None),
          ("Piauí", "PI", "PIA", None)],
    "C": [("Ceará", "CE", "CEA", 2454), ("Sport", "PE", "SPT", 1936),
          ("América-RN", "RN", "ARN", None), ("Imperatriz", "MA", "IMP", None),
          ("Ferroviário", "CE", "FER", 5573)],
    "D": [("Fortaleza", "CE", "FOR", 5143), ("Retrô", "PE", "RET", None),
          ("ABC", "RN", "ABC", None), ("Maranhão", "MA", "MAR", None),
          ("Jacuipense", "BA", "JAC", None)],
}
ALIASES = {
    "Vitória": ["EC Vitória"], "CRB": ["Clube de Regatas Brasil"],
    "Ceará": ["Ceará SC"], "Sport": ["Sport Recife"],
    "Fortaleza": ["Fortaleza EC"], "Ferroviário": ["Ferroviário AC"],
    "ASA": ["ASA de Arapiraca"], "Sousa": ["Sousa EC"],
    "Fluminense-PI": ["Fluminense PI"], "Botafogo-PB": ["Botafogo PB"],
    "América-RN": ["América RN"], "Maranhão": ["Maranhão AC"],
}
SOURCE = "https://ge.globo.com/pe/futebol/copa-do-nordeste/noticia/2026/03/03/copa-do-nordeste-2026-veja-grupos-formula-de-disputa-e-datas.ghtml"


def normalized(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s.casefold())
                   if c.isalnum() and not unicodedata.combining(c))


def resolve(base):
    teams = pesdb.team_rows(pesdb.load("Team", str(base)))
    participants = []
    for group, clubs in GROUPS.items():
        for slot, (name, state, abbr, known_id) in enumerate(clubs):
            accepted = {normalized(s) for s in [name] + ALIASES.get(name, [])}
            matches = [t for t in teams.values() if normalized(t["name"]) in accepted]
            if len(matches) > 1:
                raise ValueError(f"Ambiguous club: {name}: {[t['id'] for t in matches]}")
            if known_id in teams and normalized(teams[known_id]["name"]) not in accepted:
                raise ValueError(f"ID {known_id} no longer identifies {name}")
            team = matches[0] if matches else None
            participants.append(dict(group=group, slot=slot, name=name, state=state,
                                     abbr=abbr, team_id=team["id"] if team else None,
                                     database_name=team["name"] if team else None,
                                     squad="existing" if team else "mod_placeholder"))
    ids = [p["team_id"] for p in participants if p["team_id"] is not None]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate participant ID")
    return participants


def fixtures(participants):
    """Valid circle schedule for the real format, not the official fixture order.

    All A/C clubs have three home matches; all B/D clubs have two.
    """
    groups = {g: [p for p in participants if p["group"] == g] for g in GROUPS}
    result = []
    for rnd in range(5):
        for left, right in [("A", "B"), ("C", "D")]:
            for i in range(5):
                home, away = groups[left][i], groups[right][(i + rnd) % 5]
                if rnd % 2:
                    home, away = away, home
                result.append(dict(round=rnd + 1, home=home["name"], away=away["name"],
                                   home_id=home["team_id"], away_id=away["team_id"]))
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--build-clubs", action="store_true")
    args = parser.parse_args()
    base = args.base.resolve()
    participants = resolve(base)
    missing = [p for p in participants if p["squad"] == "mod_placeholder"]
    recipe = {"world": "_FL26Nordeste2026Clubs", "uecl": False, "leagues": []}
    if missing:
        recipe["leagues"].append({"name": "Nordeste 2026 - elencos ficticios", "country": "Brazil",
                                 "others": "latam", "clubs": len(missing),
                                 "club_names": [p["name"] for p in missing],
                                 "club_abbrs": [p["abbr"] for p in missing]})
    write_json(HERE / "clubs.recipe.json", recipe)
    if args.build_clubs:
        plan = L.plan(recipe, str(base))
        print(L.describe(plan))
        root = Path(L.build(plan, str(base), str(HERE / "staging")))
    else:
        root = HERE / "staging/SiderAddons/livecpk" / recipe["world"]
    if (root / "common/etc/pesdb/Team.bin").exists():
        built = pesdb.team_rows(pesdb.load("Team", str(root / "common/etc/pesdb")))
        for p in missing:
            hits = [t for t in built.values() if t["name"] == p["name"]]
            if len(hits) != 1:
                raise ValueError(f"Generated club missing or ambiguous: {p['name']}")
            p["team_id"] = hits[0]["id"]
            p["database_name"] = hits[0]["name"]
    spec = {
        "name": "Copa do Nordeste 2026", "upstream": "FL26 Mod Studio 0.2.1",
        "status": "rules_and_scheduler_components_live_integration_pending",
        "source": SOURCE, "base": str(base),
        "team_bin_sha256": hashlib.sha256((base / "Team.bin").read_bytes()).hexdigest(),
        "upstream_sha256": {name: hashlib.sha256((TOOLS / name).read_bytes()).hexdigest()
                            for name in ["leaguebuilder.py", "mkccup.py", "native/fl26swiss.c"]},
        "participants": participants, "fixed_entrants": True,
        "fixtures": fixtures(participants), "fixture_order": "generated_not_official",
        "quarterfinals": [["A1", "C2"], ["B1", "D2"], ["C1", "A2"], ["D1", "B2"]],
        "semifinals": [["E", "H"], ["F", "G"]],
        "rec_source": "https://www.srgoool.com.br/downloads.php?id_anexo=1583",
        "tiebreakers": ["points", "wins", "goal_difference", "goals_for",
                        "fewer_red_cards", "fewer_yellow_cards", "draw"],
        "knockout": {"extra_time": False, "away_goals": False,
                     "tied_score": "penalties", "return_host": "cumulative_campaign"},
        "legs": {"groups": 1, "quarterfinals": 1, "semifinals": 2, "final": 2},
        "qualification": {"per_group": 2},
        "pending": ["runtime cross-group fixtures and four separate standings",
                    "quarterfinal/semifinal/final progression and home advantage",
                    "official tiebreakers and calendar integration",
                    "resolve placeholder clubs outside season leagues",
                    "save/load and season rollover validation"],
    }
    write_json(HERE / "nordeste2026.json", spec)
    print(Counter(p["squad"] for p in participants))
    print("Prepared club assets and specification; NOT a playable cup; nothing activated.")


if __name__ == "__main__":
    main()
