"""Draft-only automatic access for the CONCACAF Qualification page."""
from collections import Counter
from copy import deepcopy

import leaguebuilder as B
from . import qualification_data as Q
from .i18n import _

C = B.concacaf


def league_order(source):
    roles = set(source["roles"])
    priority = 0 if roles & {"mls", "liga_mx"} else 1 if source["region"] == "north" else 2
    return priority, -source["capacity"], source["country"].casefold(), source["id"]


def regional_places(cup, sources, previous, cups):
    """Keep valid individual places and distribute new places across eligible countries."""
    required = C.REGIONAL_TOTALS[cup]
    eligible = {s["id"]: s for s in sources if s["region"] == C.PATH_REGION[cup]
                and (cup != "central_american_cup" or s.get("central_annual_supported", True))}
    limit = 7 if cup == "central_american_cup" else required
    rows = deepcopy(previous[:required])
    groups = C.group_regional_places(rows)
    order = list(groups) + [key for key in sorted(eligible, key=lambda key: league_order(eligible[key]))
                            if key not in groups][:max(0, limit - len(groups))]

    def next_place(key):
        ranks = groups.get(key, [])
        capacity = min(40, eligible[key]["capacity"])
        if len(ranks) >= capacity:
            return
        positions = ([0] if key in cups else []) + list(range(1, capacity + 1))
        for rank in positions:
            if rank in ranks:
                continue
            row = {"source": key if rank else "cup:" + key, "rank": rank or 1}
            hypothetical = C.group_regional_places(rows + [row])
            if all("teams" in eligible[k] for k in hypothetical):
                try:
                    C.initial_regional_field(hypothetical, {k: eligible[k]["teams"] for k in hypothetical})
                except C.QualificationError:
                    continue
            return row

    while len(rows) < required:
        countries = Counter()
        for key, ranks in groups.items():
            countries[eligible[key]["country"].casefold()] += len(ranks)
        for key in sorted(order, key=lambda key: (countries[eligible[key]["country"].casefold()],
                                                  len(groups.get(key, ())), league_order(eligible[key]))):
            candidate = next_place(key)
            if candidate:
                rows.append(candidate)
                groups = C.group_regional_places(rows)
                break
        else:
            break
    if previous and len(rows) < required:
        retry = regional_places(cup, sources, (), cups)
        if len(retry) > len(rows):
            return retry
    return rows


def champions_places(sources, access, cups, occupied):
    excluded = {C.PATH_REGION[key] for key in C.REGIONAL_TOTALS if access["feeders"].get(key)}
    eligible = sorted((s for s in sources if s["region"] not in excluded), key=league_order)
    ranks, used, source_count = [], set(), Counter()
    for position in range(41):
        for source in eligible:
            key = source["id"]
            ref = key if position else "cup:" + key
            rank = position or 1
            if (ref, rank) in occupied or source_count[key] >= min(40, source["capacity"]):
                continue
            if position == 0 and key not in cups or position > source["capacity"]:
                continue
            club = source["teams"][position - 1] if position and "teams" in source else None
            if club in used:
                continue
            if club is not None:
                used.add(club)
            source_count[key] += 1
            ranks.append((ref, rank))
    allocation = {}
    start = 0
    for stage in C.ACCESS_STAGES:
        count = access["required"][stage]
        allocation[stage] = [{"source": key, "rank": rank} for key, rank in ranks[start:start + count]]
        start += count
    return allocation


def generate(recipe, base):
    """Return patches for the existing draft and the resulting builder access report."""
    if not base:
        raise B.BuildError(_("The game's tables must be available to verify qualification sources."))
    before = C.integration_draft(recipe)
    proposed = dict(recipe, concacaf=deepcopy(before))

    def integrate():
        plan = B.plan(proposed, base)
        data = plan["concacaf_integration"]
        refs = {str(league["rid"]): league["name"] for league in plan["leagues"]}
        return data, refs

    data, refs = integrate()
    sources = [s for s in data["sources"] if s["kind"] == "league"]
    cups = {s["id"].removeprefix("cup:") for s in data["sources"] if s["kind"] == "cup"}
    config = proposed["concacaf"]

    def recipe_refs(rows):
        return [dict(row, source=("cup:" + refs.get(row["source"][4:], row["source"][4:])
                                 if row["source"].startswith("cup:") else refs.get(row["source"], row["source"])))
                for row in rows]

    for cup in C.REGIONAL_TOTALS:
        if config["modules"][cup] and not data["access"][cup]["ready"]:
            previous = data["access"][cup]["sources"]
            rows = regional_places(cup, sources, previous, cups)
            config["regional_access"][cup] = recipe_refs(rows)

    after_regions, _ = integrate()
    occupied = {(row["source"], row["rank"]) for cup in C.REGIONAL_TOTALS
                for row in after_regions["access"].get(cup, {}).get("sources", ())}
    champions = champions_places(sources, after_regions["access"]["champions_cup"], cups, occupied)
    config["champions_access"] = {stage: recipe_refs(rows) for stage, rows in champions.items()}
    final, _ = integrate()

    changes = {}
    for key, branch in Q.CONCACAF_ACCESS.items():
        rows = config[branch].get(key) or []
        if rows != (before[branch].get(key) or []):
            changes["qualification", "concacaf", key] = (bool(rows), rows)
    return changes, final["access"]


def summary(access):
    lines = [_("Review the automatic assignment, then Apply to save or Discard to restore.")]
    for key in C.REGIONAL_TOTALS:
        cup = access.get(key)
        if cup and not cup["ready"]:
            lines.append(_("%s: %d of %d places configured. This cup supplies no Champions Cup qualifiers.")
                         % (_(C.CUP_NAMES[C.CUP_NUMBERS[key]]), cup["configured"], cup["required"]))
            lines.extend(cup["errors"])
    leagues = access.get("leagues_cup")
    if leagues and not leagues["ready"]:
        lines.append(_("Leagues Cup supplies no Champions Cup qualifiers in this plan."))
        lines.extend(leagues["errors"])
    champions = access["champions_cup"]
    for stage, label in zip(C.ACCESS_STAGES, (_("Round of 16"), _("Round One"))):
        missing = champions["required"][stage] - champions["configured"][stage]
        if missing > 0:
            lines.append(_("Champions Cup (%s): %d places still to assign.") % (label, missing))
    lines.extend(champions["errors"])
    return "\n".join(lines)
