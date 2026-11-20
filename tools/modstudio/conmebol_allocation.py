"""Fixed UI-only association template; no ranking, Build or engine changes.

Cup destinations are a documented template policy, not a claim that the database
encodes official cup rights. All destinations and cup cascading use existing rules.
"""
from collections import Counter
from copy import deepcopy
import os
import leaguebuilder as B
from . import qualification_data as Q, filecache
from .i18n import _

DESTINATIONS = (3, 17, 16, 9, 19)
QUOTAS = {
    "Brazil": (5, 2, 0, 6, 0), "Argentina": (5, 1, 0, 6, 0),
    "Chile": (2, 2, 0, 0, 4), "Colombia": (2, 2, 0, 0, 4),
    "Uruguay": (2, 1, 1, 0, 4), "Paraguay": (2, 1, 1, 0, 4),
    "Peru": (2, 1, 1, 0, 4), "Ecuador": (2, 1, 1, 0, 4),
    "Bolivia": (2, 1, 1, 0, 4), "Venezuela": (2, 1, 1, 0, 4),
}
CUP_TARGETS = {
    "Brazil": 3, "Argentina": 3, "Chile": 17, "Colombia": 17,
    "Bolivia": 17, "Ecuador": 16, "Paraguay": 16, "Venezuela": 16,
    "Peru": 19, "Uruguay": 19,
}


class AllocationError(ValueError):
    pass


def fail(message):
    raise AllocationError(message + "\n\n" + _("No qualification places were changed."))


def playable_native_rids(base):
    def read():
        leagues = B.game_leagues(base)
        friendly = B.friendly_cids(leagues)
        return frozenset(str(r) for r, cid, _name, _teams in leagues if cid not in friendly)
    return filecache.by_files("cups-conmebol-playable-native", [os.path.join(base, n) for n in
                              ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin")], read)


def snapshot(recipe):
    """Only source/cup context and access rows; never copy players or club rosters."""
    fields = ("name", "country", "clubs", "above", "exhibition", "others", "cup", "season",
              "europe", "split", "apertura", "legs", "cup_join")
    return {"leagues": [{k: deepcopy(L[k]) for k in fields if k in L} for L in recipe.get("leagues") or []],
            **{k: deepcopy(recipe[k]) for k in ("conmebol", "game_europe", "conmebol_associations") if k in recipe}}


def _valid_own(league):
    try:
        clubs = int(league.get("clubs") or 0)
        return (Q.eligible(league) and isinstance(league.get("name"), str) and league["name"].strip()
                and B.CLUBS_MIN <= clubs <= B.CLUBS_MAX
                and str(league.get("season") or B.SEASONS[0]).strip().lower() in B.SEASONS)
    except (TypeError, ValueError):
        return False


def _check_cup(source, recipe):
    if not source.cup or source.kind == "game":
        return
    # Same pure cup-shape selector used during planning. No cup is built here.
    children = [L for L in recipe.get("leagues") or [] if L.get("above") == source.key]
    if len(children) > 1:
        fail(_("The domestic cup source for %s is ambiguous. Review its divisions first.") % source.name)
    p = {"name": source.name, "clubs": source.clubs, "own_cup": {},
         "calendar": next(L for L in recipe["leagues"] if L.get("name") == source.key).get("season") == "calendar"}
    try:
        # national_cup records a lower-division id in its temporary result; no
        # regulation ids are allocated or persisted by this shape-only check.
        below = {"clubs": int(children[0]["clubs"]), "rid": 0} if children else None
        B.national_cup(p, below)
        if p["own_cup"]["clubs"] < 2:
            raise ValueError()
    except (ValueError, TypeError, KeyError, B.BuildError):
        fail(_("The domestic cup for %s cannot be safely used by this template. Review its configuration first.") % source.name)


def generate(recipe, base):
    """Return existing-slot patches atomically. Nothing in recipe is mutated."""
    if not Q.modern(recipe):
        fail(_("Enable Modern CONMEBOL competitions before using automatic allocation."))
    if not base:
        fail(_("The game's tables must be available to verify the ten top divisions."))
    _native, _associations, confeds = Q.metadata(base)
    labels = {name.strip().casefold(): name for name in confeds}
    filtered = dict(recipe, leagues=[dict(L, country=labels.get(str(L.get("country", "")).strip().casefold(), L.get("country")))
                                    for L in recipe.get("leagues") or [] if _valid_own(L)])
    all_sources = Q.sources(filtered, base)
    playable = playable_native_rids(base)
    candidates = {country: [] for country in QUOTAS}
    for source in all_sources:
        if source.kind not in ("game", "league") or source.confederation != 4 or source.clubs <= 0:
            continue
        if source.kind == "game" and str(source.key) not in playable:
            continue
        if source.country in candidates:
            candidates[source.country].append(source)
    missing = sorted(country for country, rows in candidates.items() if not rows)
    ambiguous = sorted(country for country, rows in candidates.items() if len(rows) > 1)
    if missing or ambiguous:
        lines = [_("All 10 CONMEBOL countries must have a playable top division to use automatic qualification allocation."),
                 _("Available: %d/10") % sum(len(rows) == 1 for rows in candidates.values())]
        if missing:
            lines.append(_("Missing: %s") % ", ".join(_(c) for c in missing))
        if ambiguous:
            lines.append(_("Ambiguous top divisions: %s") % ", ".join(_(c) for c in ambiguous))
        fail("\n".join(lines))
    selected = {c: rows[0] for c, rows in candidates.items()}
    selected_keys = {s.draft_key for s in selected.values()}
    names = [str(L.get("name") or "").strip().casefold() for L in recipe.get("leagues") or []]
    if any(s.kind == "league" and names.count(str(s.key).strip().casefold()) != 1 for s in selected.values()):
        fail(_("League names are ambiguous. Give each league a unique name before automatic allocation."))
    if recipe.get("conmebol_associations"):
        fail(_("Stored association allocations need manual review before this action. They were not replaced or used as substitutes for playable leagues."))
    # Preserve historical/unrelated records; never erase them to force totals.
    for key in Q.keys(recipe):
        if key[1] not in ("league", "game"):
            continue
        _present, rows = Q.state(recipe, key)[0]
        for row in rows or []:
            try:
                if len(row) != 2:
                    raise ValueError()
                target = int(row[1])
            except (TypeError, ValueError):
                fail(_("Stored qualification rows need manual review before automatic allocation."))
            if target in (4, 18):
                fail(_("Stored Libertadores qualifying entries are incompatible with this template. Review them manually; they were preserved."))
            if key not in selected_keys and target in DESTINATIONS:
                fail(_("CONMEBOL places exist outside the ten selected top divisions. Review them manually; they were preserved."))
    changes = {}
    for country, source in selected.items():
        quota = QUOTAS[country]
        if sum(quota) > source.clubs:
            fail(_("%s needs %d eligible clubs for its fixed quota, but only %d are available.") % (source.name, sum(quota), source.clubs))
        _check_cup(source, recipe)
        old = Q.editable_rows(source, recipe)
        retained = [deepcopy(row) for row in old if int(row[1]) not in DESTINATIONS]
        cup_target = CUP_TARGETS[country] if source.cup else None
        rows, position = [], 1
        for target, number in zip(DESTINATIONS, quota):
            for _i in range(number - (target == cup_target)):
                rows.append([position, target])
                position += 1
        if cup_target is not None:
            rows.append([0, cup_target])
        rows += retained
        if B.europe_problems(source.clubs, rows, source.cup):
            fail(_("Existing places in %s cannot be safely combined with this template. Review them manually.") % source.name)
        value = (True, rows)
        if Q.state(recipe, source.draft_key)[0] != value:
            changes[source.draft_key] = value
    proposed = Q.preview(recipe, changes)
    counts, notes = Q.allocation_counts(all_sources, proposed, 4)
    expected = {target: Q.MODERN_TOTALS[target] for target in DESTINATIONS}
    template_totals = {target: sum(q[i] for q in QUOTAS.values()) for i, target in enumerate(DESTINATIONS)}
    actual = {target: counts[target] for target in DESTINATIONS}
    if template_totals != expected or actual != expected or counts[18] or sum(actual.values()) != 89 or notes:
        fail(_("The complete fixed allocation could not be validated. Review existing qualification places first."))
    if Q.validate_changes(recipe, proposed, changes, all_sources):
        fail(_("The selected qualification sources changed or contain incompatible places. Review them before automatic allocation."))
    return changes
