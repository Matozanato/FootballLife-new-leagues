"""CONCACAF Champions Cup qualification contract; no table or runtime generation.

Source ids are regulation ids (strings in JSON), or symbolic future sources. A source
catalogue describes leagues/cups, never a permanent continental field. resolve() is a
reference implementation for tests and previews, not a substitute for native qualification.
"""
import copy

TARGET, CODE, NAME = 13, "FL_CONCACAF", "CONCACAF Champions Cup"
FORMAT = "concacaf27"
MODULES = ("leagues_cup", "central_american_cup", "caribbean_cup")
CUP_NAMES = {TARGET: NAME, -14: "Leagues Cup", -15: "CONCACAF Central American Cup",
             -13: "CONCACAF Caribbean Cup"}
CUP_NUMBERS = dict(zip(("champions_cup", *MODULES), CUP_NAMES))
ROUND_OF_16 = 27
ACCESS_TARGETS = {TARGET: "round_one", ROUND_OF_16: "round_of_16",
                  -15: "central_american_cup", -13: "caribbean_cup"}
REGIONAL_TOTALS = {"central_american_cup": 20, "caribbean_cup": 10}
ACCESS_STAGES = ("round_of_16", "round_one")
QUOTAS = {"liga_mx": 6, "mls": 5, "leagues_cup": 3, "central_american_cup": 6,
          "caribbean_cup": 3, "canadian_premier": 2, "canadian_championship": 1,
          "us_open_cup": 1}
DIRECT = ("liga_mx", "mls", "leagues_cup", "central_american_cup", "caribbean_cup")
REGIONS = ("north", "central", "caribbean")
PATH_REGION = {p: "north" for p in QUOTAS}
PATH_REGION.update(central_american_cup="central", caribbean_cup="caribbean")
CHAMPIONS = {"liga_mx": "liga_mx_champion", "mls": "mls_cup"}
ROLES = set(QUOTAS) | set(CHAMPIONS.values())
CENTRAL = {"belize", "costa rica", "el salvador", "guatemala", "honduras", "nicaragua", "panama"}
NORTH = {"mexico", "usa", "united states", "united states of america", "canada"}
BUILD_BLOCKED = ("CONCACAF Champions Cup requires the dedicated 27-team generator and runtime contract v1; "
                 "the generic cup generator cannot build it. Re-plan the recipe and start a new career.")


class QualificationError(ValueError):
    pass


class QualificationPending(QualificationError):
    """Wait for the source's season to finish; do not redistribute its places."""


def region(country):
    country = country.strip().lower()
    return "central" if country in CENTRAL else "north" if country in NORTH else "caribbean"


def configuration(raw=None):
    if raw is None:
        raw = {}
    if isinstance(raw, dict) and raw.get("version") in (2, 3):
        return integration_configuration(raw)
    if not isinstance(raw, dict) or set(raw) - {"modules", "sources", "caribbean_titles", "caribbean_associations"}:
        raise QualificationError("concacaf must be an object with modules and/or sources (no format selector)")
    modules = raw.get("modules", {})
    sources = raw.get("sources", {})
    if not isinstance(modules, dict) or set(modules) - set(MODULES):
        raise QualificationError("concacaf.modules supports " + ", ".join(MODULES))
    if any(type(v) is not bool for v in modules.values()):
        raise QualificationError("CONCACAF module switches must be true or false")
    if not isinstance(sources, dict) or set(sources) - ROLES:
        raise QualificationError("concacaf.sources has an unknown qualification pathway")
    for role, refs in sources.items():
        if not isinstance(refs, list) or any(type(r) not in (int, str) or not str(r).strip() for r in refs):
            raise QualificationError("CONCACAF source %s must be a list of regulation ids or new league names" % role)
        if role in MODULES:
            raise QualificationError("regional source %s is managed by its module, not a domestic override" % role)
    result = {"modules": {k: modules.get(k, False) for k in MODULES}, "sources": copy.deepcopy(sources)}
    if "caribbean_titles" in raw:
        titles = raw["caribbean_titles"]
        if (not isinstance(titles, dict) or set(titles) - {"haiti", "dominican republic"} or
                any(type(v) is not int or not 1 <= v <= 1023 for v in titles.values()) or
                len(set(titles.values())) != len(titles)):
            raise QualificationError("caribbean_titles requires distinct native knockout regulation IDs for Haiti or Dominican Republic")
        result["caribbean_titles"] = dict(titles)
    if "caribbean_associations" in raw:
        extra = raw["caribbean_associations"]
        if not isinstance(extra, list) or len(extra)>11 or any(type(c) is not str or not c.strip() for c in extra):
            raise QualificationError("caribbean_associations must list up to eleven additional Caribbean associations")
        result["caribbean_associations"] = list(extra)
    return result


def integration_configuration(raw):
    fields = {"version", "champions_cup", "modules", "regional_access", "champions_access", "legacy"}
    if (not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] not in (2, 3)
            or set(raw) - fields or ("champions_cup" in raw and type(raw["champions_cup"]) is not bool)):
        raise QualificationError("Invalid CONCACAF qualification configuration")
    modules = raw.get("modules", {})
    regional = raw.get("regional_access", {})
    champions = raw.get("champions_access", {})
    if not isinstance(modules, dict) or set(modules) - set(MODULES) or any(type(v) is not bool for v in modules.values()):
        raise QualificationError("Invalid CONCACAF regional cup switches")
    if not isinstance(regional, dict) or set(regional) - REGIONAL_TOTALS.keys():
        raise QualificationError("Only Central American Cup and Caribbean Cup accept regional access settings")
    if not isinstance(champions, dict) or set(champions) - set(ACCESS_STAGES):
        raise QualificationError("Invalid Champions Cup entry stages")
    individual = {}
    for cup, allocations in regional.items():
        if not isinstance(allocations, list):
            raise QualificationError("Regional access must be a list of qualification places")
        if raw["version"] == 2:
            individual[cup] = []
            for row in allocations:
                _access_row(row, "places")
                if row["places"] > 40:
                    raise QualificationError("Legacy regional source exceeds the native 40-position capacity")
                individual[cup].extend({"source": row["source"], "rank": rank}
                                       for rank in range(1, row["places"] + 1))
        else:
            for row in allocations:
                _access_row(row, "rank")
            individual[cup] = copy.deepcopy(allocations)
    for places in champions.values():
        if not isinstance(places, list):
            raise QualificationError("Champions Cup access must be a list of source places")
        for row in places:
            _access_row(row, "rank")
    result = {"version": 3,
              "modules": {key: modules.get(key, False) for key in MODULES},
              "regional_access": individual, "champions_access": copy.deepcopy(champions)}
    if "legacy" in raw:
        if not isinstance(raw["legacy"], dict) or "version" in raw["legacy"]:
            raise QualificationError("Invalid retained CONCACAF configuration")
        result["legacy"] = configuration(raw["legacy"])
    return result


def _access_row(row, quantity):
    if (not isinstance(row, dict) or set(row) != {"source", quantity}
            or type(row["source"]) not in (int, str) or not str(row["source"]).strip()
            or type(row[quantity]) is not int or row[quantity] < 1):
        raise QualificationError("An access row needs a source and a positive %s" % quantity)


def integration_draft(recipe):
    """Open an editable draft without importing the old implicit allocations."""
    raw = recipe.get("concacaf") or {}
    if raw.get("version") in (2, 3):
        return integration_configuration(raw)
    legacy = configuration(raw)
    draft = integration_configuration({"version": 3, "modules": legacy["modules"]})
    leagues = [(L["name"], L.get("europe") or []) for L in recipe.get("leagues") or []]
    leagues.extend((recipe.get("game_europe") or {}).items())
    for source, rows in leagues:
        for row in rows or []:
            if isinstance(row, (tuple, list)) and len(row) == 2 and str(row[1]) == str(TARGET):
                try:
                    rank = int(row[0])
                except (TypeError, ValueError):
                    continue
                if rank >= 0:
                    ref = source if rank else "cup:" + str(source)
                    draft["champions_access"].setdefault("round_one", []).append(
                        {"source": ref, "rank": rank or 1})
    if raw:
        draft["legacy"] = legacy
    return draft


def domestic_slots(modules):
    enabled = [key for key in MODULES if modules.get(key)]
    return {"round_of_16": 5 - len(enabled),
            "round_one": 22 - sum(QUOTAS[key] - 1 for key in enabled)}


def integration_access(raw, rows, aliases=None, leagues_issues=()):
    """One result per enabled cup. Missing spots stay distinct from bad sources."""
    config = integration_configuration(raw)
    sources = catalogue(rows)
    aliases = aliases or {}
    result = {}

    def source(ref):
        key = str(ref)
        return aliases.get(key, key)

    def access(allocations, region=None):
        errors, selected, seen = [], [], set()
        for row in allocations:
            key, rank = source(row["source"]), row["rank"]
            entry = sources.get(key)
            parent = sources.get(key.removeprefix("cup:")) if entry and entry["kind"] == "cup" else entry
            identity = (key, rank)
            if not entry or not parent or (region and entry["region"] != region):
                errors.append("Unavailable or ineligible CONCACAF source: %s" % key)
            elif region == "central" and not parent.get("central_annual_supported", True):
                errors.append("Unsupported annual phases for Central American Cup source: %s" % key)
            elif identity in seen:
                errors.append("Repeated CONCACAF access source or rank: %s/%d" % (key, rank))
            elif rank > (1 if entry["kind"] == "cup" else min(40, entry["capacity"])):
                errors.append("CONCACAF source %s cannot supply rank %d" % (key, rank))
            else:
                selected.append({"source": key, "rank": rank})
            seen.add(identity)
        return selected, errors

    consumed = {}
    for cup, required in REGIONAL_TOTALS.items():
        if not config["modules"][cup]:
            continue
        allocations = config["regional_access"].get(cup, [])
        selected, errors = access(allocations, PATH_REGION[cup])
        grouping = group_regional_places(selected)
        if cup == "central_american_cup" and len(grouping) > 7:
            errors.append("Central American Cup currently supports up to seven league sources")
        if sum(len(ranks) for ranks in grouping.values()) == required and all(
                "teams" in sources[key] for key in grouping):
            try:
                initial_regional_field(grouping, {key: sources[key]["teams"] for key in grouping})
            except QualificationError as exc:
                errors.append(str(exc))
        configured = len(allocations)
        ready = configured == required and not errors
        result[cup] = {"configured": configured, "required": required, "sources": selected, "errors": errors,
                       "ready": ready}
        if not errors:
            consumed.update({(row["source"], row["rank"]): cup for row in selected})

    if config["modules"]["leagues_cup"]:
        leagues = [key for key, s in sources.items() if s["kind"] == "league" and "mls" in s["roles"] and s["capacity"] == 30]
        mexico = [key for key, s in sources.items() if s["kind"] == "league" and "liga_mx" in s["roles"] and s["capacity"] == 18]
        errors = list(leagues_issues) if len(leagues) == len(mexico) == 1 else ["Leagues Cup requires one compatible MLS and one compatible Liga MX"]
        result["leagues_cup"] = {"required": 36, "sources": leagues + mexico, "errors": errors, "ready": not errors}

    feeders = {key: cup["ready"] for key, cup in result.items()}
    required = domestic_slots(feeders)
    selected, errors = {}, []
    configured = {stage: len(config["champions_access"].get(stage, [])) for stage in ACCESS_STAGES}
    for stage in ACCESS_STAGES:
        selected[stage], issues = access(config["champions_access"].get(stage, []))
        errors.extend(issues)
    identities = [(row["source"], row["rank"]) for stage in ACCESS_STAGES for row in selected[stage]]
    if len(identities) != len(set(identities)):
        errors.append("A Champions Cup source rank is assigned to more than one stage")
    if any(identity in consumed for identity in identities):
        errors.append("A CONCACAF source position or cup winner is assigned to more than one competition")
    result["champions_cup"] = {"required": required, "configured": configured, "sources": selected,
                               "errors": errors, "ready": configured == required and not errors,
                               "feeders": feeders, "inaugural_regional_results": "wait"}
    return result


def group_regional_places(rows):
    """Group rows by ranking provider. Zero denotes that league's domestic cup winner."""
    grouped = {}
    for row in rows:
        key = row["source"]
        grouped.setdefault(key.removeprefix("cup:"), []).append(0 if key.startswith("cup:") else row["rank"])
    return {key: sorted(ranks) for key, ranks in sorted(grouped.items(), key=lambda item: (not item[0].isdigit(), int(item[0]) if item[0].isdigit() else item[0]))}


def regional_cup_reg(key, ranks, sources, cup_regs, regulations):
    if 0 not in ranks:
        return 0
    cup = "cup:" + key
    reg = cup_regs.get(cup) or sources.get(cup, {}).get("runtime_reg", 0)
    if not 0 < reg <= 1023 or reg not in regulations or regulations[reg][9] != 3:
        raise QualificationError("No eligible domestic knockout for source %s" % key)
    return reg


def initial_regional_field(grouped, tables):
    """Use the same order and same-source cascade as the native first-career draw."""
    slots = [(key, rank) for key, ranks in grouped.items() for rank in ranks]
    clubs, used = [None] * len(slots), set()
    for index, (key, rank) in enumerate(slots):
        if rank and rank <= len(tables[key]):
            club = tables[key][rank - 1]
            if club not in used:
                clubs[index] = club
                used.add(club)
    for index, (key, rank) in enumerate(slots):
        if clubs[index] is not None:
            continue
        club = next((c for c in tables[key][max(0, rank - 1):] if c not in used), None)
        if club is None:
            raise QualificationError("Regional places cannot supply distinct inaugural clubs from the configured sources")
        clubs[index] = club
        used.add(club)
    return clubs


def explicit_champions_plan(integration):
    available = {str(row["id"]): row for row in integration["sources"]}
    access = integration["access"]["champions_cup"]
    sources, places = {}, []
    for stage in ACCESS_STAGES:
        for ref in access["sources"][stage]:
            key = ref["source"]
            sources[key] = available[key]
            if available[key]["kind"] == "cup" and key.startswith("cup:") and key[4:] in available:
                sources[key[4:]] = available[key[4:]]
            places.append({"stage": stage, "path": "domestic", "preferred": [ref], "fallback": []})
    modules = {key: bool(access["feeders"].get(key)) for key in MODULES}
    for key in MODULES:
        if not modules[key]:
            continue
        source_id = "module:" + key
        sources[source_id] = {"kind": "regional", "region": PATH_REGION[key], "capacity": QUOTAS[key]}
        for rank in range(1, QUOTAS[key] + 1):
            places.append({"stage": "round_of_16" if rank == 1 else "round_one", "path": key,
                           "preferred": [{"source": source_id, "rank": rank}], "fallback": []})
    return {"format": FORMAT, "version": 3, "modules": modules, "sources": sources, "places": places}


def catalogue(rows):
    out = {}
    for value in rows:
        if not isinstance(value, dict) or type(value.get("id")) not in (str, int) or not str(value["id"]).strip():
            raise QualificationError("CONCACAF source needs a nonempty id")
        s = copy.deepcopy(value)
        key = str(s["id"])
        if key in out or s.get("conf") != 6 or s.get("region") not in REGIONS:
            raise QualificationError("CONCACAF source %s must be unique and belong to CONCACAF with a known region" % key)
        if s.get("code") == CODE:
            raise QualificationError("the defending Champions Cup winner is not a qualification source")
        if s.get("kind") not in ("league", "cup"):
            raise QualificationError("CONCACAF source %s must be a league or a cup" % key)
        capacity = s.get("capacity", 0)
        if type(capacity) is not int or capacity < 0 or (s["kind"] == "league" and not capacity):
            raise QualificationError("CONCACAF source %s has no valid capacity" % key)
        teams = s.get("teams")
        if teams is not None and (not isinstance(teams, list) or len(teams) != capacity
                                  or any(type(t) is not int or t <= 0 for t in teams)
                                  or len(set(teams)) != len(teams)):
            raise QualificationError("CONCACAF source %s has an invalid seed membership list" % key)
        s["id"] = key
        s.setdefault("roles", [])
        if not isinstance(s["roles"], list) or any(r not in ROLES for r in s["roles"]):
            raise QualificationError("CONCACAF source %s has invalid roles" % key)
        out[key] = s
    return out


def source_order(sources, geographical_region):
    """Same-region leagues first; stable ids, independent of recipe row order."""
    return sorted((k for k, s in sources.items() if s["kind"] == "league"),
                  key=lambda k: (sources[k]["region"] != geographical_region, sources[k]["region"],
                                 sources[k].get("country", ""), k))


def plan(raw, rows, legacy=(), previous_ids=None):
    config = configuration(raw)
    if config.get("version") in (2, 3):
        raise QualificationError("CONCACAF v2 access requires the integrated world generator")
    sources = catalogue(rows)
    roles = {role: sorted(k for k, s in sources.items() if role in s["roles"]) for role in ROLES}
    for role, refs in config["sources"].items():
        refs = [str(r) for r in refs]
        if len(refs) != len(set(refs)) or any(r not in sources for r in refs):
            raise QualificationError("CONCACAF source %s names an unavailable or repeated source" % role)
        expected = "cup" if role in {"canadian_championship", "us_open_cup"} | set(CHAMPIONS.values()) else "league"
        if any(sources[r]["kind"] != expected or sources[r]["region"] != "north" for r in refs):
            raise QualificationError("CONCACAF source %s must use North American %s sources" % (role, expected))
        country_role = "liga_mx" if role == "liga_mx_champion" else "mls" if role in ("mls_cup", "us_open_cup") else "canadian_premier" if role == "canadian_championship" else role
        countries = {"liga_mx": {"mexico"}, "mls": NORTH - {"mexico", "canada"}, "canadian_premier": {"canada"}}
        if any(sources[r].get("country", "").lower() not in countries[country_role] for r in refs):
            raise QualificationError("CONCACAF source %s belongs to the wrong domestic association" % role)
        roles[role] = refs
    if config["modules"]["leagues_cup"] and (not roles["liga_mx"] or not roles["mls"]):
        raise QualificationError("Leagues Cup requires both MLS and Liga MX league sources")

    # Capacity is exact for known memberships; new clubs use symbolic places until Build
    # assigns their ids. Runtime must still check actual membership and exactly 27 clubs.
    eligible = set()
    for key, s in sources.items():
        if s["kind"] == "league":
            eligible.update(s.get("teams", [(key, i) for i in range(s["capacity"])]))
    if len(eligible) < 27:
        raise QualificationError("CONCACAF Champions Cup needs 27 unique eligible clubs; available source capacity is %d" % len(eligible))

    places = []
    for path, quota in QUOTAS.items():
        enabled = path in MODULES and config["modules"][path]
        preferred = ["module:" + path] if enabled else roles.get(path, []) if path not in MODULES else []
        if enabled:
            sources[preferred[0]] = {"id": preferred[0], "kind": "regional", "conf": 6,
                                     "region": PATH_REGION[path], "capacity": quota, "roles": [path]}
        for i in range(quota):
            direct = path in DIRECT and i == 0
            primary = preferred
            rank = i + 1
            if direct and path in CHAMPIONS and roles[CHAMPIONS[path]]:
                primary = roles[CHAMPIONS[path]]
            elif i and path in CHAMPIONS and roles[CHAMPIONS[path]]:
                rank = i
            places.append({"path": path, "place": i + 1, "stage": "round_of_16" if direct else "round_one",
                           "preferred": [{"source": k, "rank": rank} for k in primary],
                           "fallback": source_order(sources, PATH_REGION[path]),
                           "reason": "enabled_module" if enabled else "disabled_module" if path in MODULES
                           else "domestic" if primary else "unavailable_domestic"})

    migrated, seen = [], set()
    for ref in legacy:
        key, rank = str(ref["source"]), ref["rank"]
        if key not in sources or type(rank) is not int or rank < 0:
            raise QualificationError("legacy CONCACAF assignment has no eligible source: %s" % ref)
        s = sources[key]
        if rank == 0:
            key = "cup:" + key
            if key not in sources:
                raise QualificationError("legacy CONCACAF cup winner has no cup source")
            rank, s = 1, sources[key]
        if (key, rank) in seen:
            raise QualificationError("repeated legacy CONCACAF assignment")
        seen.add((key, rank))
        if s["kind"] == "cup":
            path = "canadian_championship" if s.get("country", "").lower() == "canada" else "us_open_cup"
        elif s["region"] == "central":
            path = "central_american_cup"
        elif s["region"] == "caribbean":
            path = "caribbean_cup"
        else:
            path = next((r for r in ("liga_mx", "mls", "canadian_premier") if key in roles[r]), None)
        if not path or (path in MODULES and config["modules"][path]):
            raise QualificationError("legacy CONCACAF place %s conflicts with its modern pathway; review the assignment" % ref)
        if s["kind"] == "league" and rank > s["capacity"]:
            raise QualificationError("legacy CONCACAF rank exceeds source capacity")
        candidates = [p for p in places if p["path"] == path and "legacy" not in p
                      and (p["stage"] != "round_of_16" or rank == 1 or path in MODULES)]
        if not candidates:
            raise QualificationError("legacy CONCACAF places exceed the %s quota; review assignments instead of truncating" % path)
        slot = candidates[0]
        slot["preferred"] = [{"source": key, "rank": rank}]
        slot["legacy"] = copy.deepcopy(ref)
        migrated.append(copy.deepcopy(ref))

    return {"version": 1, "format": FORMAT, "target": TARGET, "code": CODE, "participants": 27,
            "round_one": 22, "direct": 5, "round_one_ties": 11, "round_of_16": 16,
            "final_legs": 1, "other_knockout_legs": 2, "defending_champion_berth": False,
            "modules": config["modules"], "sources": sources, "places": places,
            "configuration": copy.deepcopy(config),
            "legacy_places": migrated, "previous_ids": copy.deepcopy(previous_ids or {}),
            "runtime_ready": False, "requires_new_career": True,
            "first_season": "entry_order_seed", "later_incomplete": "wait", "later_missing": "error"}


def resolve(pl, results=None, first_season=False, memberships=None):
    """Reference qualification for one season: no mutation, no implicit titleholder.

    results[source] = {status: complete|incomplete|missing|invalid, clubs: ranked ids}.
    First-season absent/incomplete results use declared league entry order; later ones
    must complete. A later enabled cup with missing/invalid results is an error, not off.
    """
    results = results or {}
    sources = copy.deepcopy(pl["sources"])
    for key, teams in (memberships or {}).items():
        key = str(key)
        if key not in sources or sources[key]["kind"] != "league" or not isinstance(teams, list) or not teams or any(type(t) is not int or t <= 0 for t in teams) or len(set(teams)) != len(teams):
            raise QualificationError("invalid current-season membership for source %s" % key)
        sources[key]["teams"] = list(teams)
        sources[key]["capacity"] = len(teams)
    known = {t for s in sources.values() if s["kind"] == "league" for t in s.get("teams", [])}
    if any(s["kind"] == "league" and "teams" not in s for s in sources.values()):
        raise QualificationError("qualification preview needs actual league memberships for every source")
    if len(known) < 27:
        raise QualificationError("current-season sources cannot supply 27 unique eligible clubs")
    pools = {}

    def pool(key):
        if key in pools:
            return pools[key]
        s = sources[key]
        r = results.get(key, {"status": "missing"})
        if not isinstance(r, dict) or r.get("status") not in ("complete", "incomplete", "missing", "invalid"):
            raise QualificationError("source %s has an invalid result status" % key)
        status = r["status"]
        if status == "complete":
            clubs = r.get("clubs")
            if not isinstance(clubs, list) or not clubs or any(type(t) is not int or t not in known for t in clubs) or len(set(clubs)) != len(clubs):
                raise QualificationError("source %s has invalid, duplicate or ineligible qualifying results" % key)
            if s["kind"] == "league" and set(clubs) != set(s["teams"]):
                raise QualificationError("league %s needs its complete ranked membership" % key)
            if s["kind"] == "cup":
                domestic = {t for v in sources.values() if v["kind"] == "league"
                            and v.get("country", "").lower() == s.get("country", "").lower()
                            for t in v.get("teams", [])}
                if any(t not in domestic for t in clubs):
                    raise QualificationError("cup source %s includes a club outside its domestic sources" % key)
            if s["kind"] == "regional":
                if len(clubs) < s["capacity"]:
                    raise QualificationError("regional source %s has no complete qualifying ranking" % key)
                domestic = [v for v in sources.values() if v["kind"] == "league" and v["region"] == s["region"]]
                if key == "module:leagues_cup":
                    domestic = [v for v in domestic if set(v["roles"]) & {"liga_mx", "mls"}]
                allowed = {t for v in domestic for t in v.get("teams", [])}
                if any(t not in allowed for t in clubs):
                    raise QualificationError("regional source %s includes an ineligible club" % key)
        elif first_season and status in ("missing", "incomplete"):
            clubs = s.get("teams", []) if s["kind"] == "league" else []
        elif status == "incomplete":
            raise QualificationPending("source %s has not completed its season; keep its berths pending" % key)
        else:
            raise QualificationError("source %s has %s results; its berths cannot be redistributed as disabled" % (key, status))
        pools[key] = clubs
        return clubs

    used, entries = set(), []
    caribbean = "module:caribbean_cup"
    central = "module:central_american_cup"
    podium = pool(caribbean)[:3] if caribbean in sources else []
    central_finishers = pool(central)[:6] if central in sources else []
    leagues = "module:leagues_cup"
    leagues_finishers = pool(leagues)[:3] if leagues in sources else []
    regional_pools = {caribbean: podium, central: central_finishers, leagues: leagues_finishers}
    regional_clubs = podium + central_finishers + leagues_finishers
    reserved = set(regional_clubs)
    if len(reserved) != len(regional_clubs):
        raise QualificationError("a club occupies guaranteed places in multiple regional cups")
    # Reserve all five byes before assigning any Round One place.
    order = sorted(enumerate(pl["places"]), key=lambda x: (x[1]["stage"] != "round_of_16", x[0]))
    for index, slot in order:
        chosen, how, origin = None, "first_season_seed" if first_season else "completed_result", None
        for ref in slot["preferred"]:
            rank = ref["rank"] - 1
            regional = ref["source"] in regional_pools
            candidates = regional_pools[ref["source"]][rank:rank + 1] if regional else pool(ref["source"])[rank:]
            chosen = next((t for t in candidates if t not in used and (regional or t not in reserved)), None)
            if candidates and candidates[0] in used:
                how = "duplicate_qualification"
            if chosen is not None:
                origin = ref["source"]
                break
        if chosen is None:
            if how != "duplicate_qualification":
                how = "first_season_fallback" if first_season and slot["reason"] == "enabled_module" else slot["reason"]
            # Exhaust same-region ranks before crossing into other CONCACAF regions.
            for same_region in (True, False):
                keys = [k for k in slot["fallback"] if (sources[k]["region"] == PATH_REGION[slot["path"]]) == same_region]
                lists = [pool(k) for k in keys]
                for rank in range(max(map(len, lists), default=0)):
                    chosen = next((clubs[rank] for clubs in lists if rank < len(clubs)
                                   and clubs[rank] not in used and clubs[rank] not in reserved), None)
                    if chosen is not None:
                        origin = next(k for k in keys if rank < len(pool(k)) and pool(k)[rank] == chosen)
                        break
                if chosen is not None:
                    break
        if chosen is None:
            raise QualificationError("CONCACAF Champions Cup cannot fill 27 unique clubs: no eligible replacement for %s/%s" % (slot["path"], slot["place"]))
        used.add(chosen)
        entries.append({"slot": index, "club": chosen, "stage": slot["stage"], "path": slot["path"], "how": how, "source": origin})
    if len(used) != 27 or sum(e["stage"] == "round_one" for e in entries) != 22 or sum(e["stage"] == "round_of_16" for e in entries) != 5:
        raise QualificationError("invalid CONCACAF plan: expected 27 unique clubs, 22 Round One and 5 direct")
    return sorted(entries, key=lambda e: e["slot"])
