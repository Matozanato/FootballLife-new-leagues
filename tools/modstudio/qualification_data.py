"""Qualification UI adapters. Existing recipe fields and builder rules are authoritative.

No game generation lives here. Only small qualification branches are copied for
previews; database reads are cached and called by the UI's background loaders.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import os

import leaguebuilder as B
import fl26world as W
import mkleague as M
import uefakey
from . import filecache
from .i18n import _, tr

ROOTS = ("uefa_rank", "uefa_off", "uefa_seed")
TARGETS = {2: (0, 10, 1, 11, 2, 12), 4: (3, 17, 16, 9, 19),
           3: (5, 8, 15), 5: (6, 7), 6: (13,), 7: (14,)}
MODERN_TOTALS = {3: 26, 17: 13, 16: 6, 18: 0, 9: 12, 19: 32}


@dataclass(frozen=True)
class Source:
    kind: str
    key: object
    name: str
    country: str
    confederation: int
    clubs: int
    cup: bool = False
    native: tuple = ()
    country_id: int = 0
    linked_to: tuple = ()
    invalid_link: bool = False

    @property
    def draft_key(self):
        return ("qualification", self.kind, self.key)


def eligible(league):
    return not league.get("above") and not league.get("exhibition") and not league.get("others")


def modern(recipe):
    try:
        return B.recipe_has_modern_conmebol(recipe)
    except B.BuildError:
        return False


def table_signature(base):
    return tuple(filecache.stamp(os.path.join(base, n)) for n in
                 ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin", "Team.bin", "Country.bin", "PlayerAssignment.bin")) if base else ()


def keys(recipe):
    result = {("qualification", "root", k) for k in ROOTS}
    result.update(("qualification", "first", k) for k, _title in B.EUROPE_FIRST)
    result.update(("qualification", "league", L["name"]) for L in recipe.get("leagues") or [] if L.get("name"))
    for kind, root in (("game", "game_europe"), ("association", "conmebol_associations")):
        result.update(("qualification", kind, k) for k in recipe.get(root) or {})
    return result


def state(recipe, key):
    _namespace, kind, name = key
    if kind == "league":
        league = next((L for L in recipe.get("leagues") or [] if L.get("name") == name), None)
        if league is None:
            return (False, None), (False, None)
        context = {k: deepcopy(league[k]) for k in ("name", "country", "above", "clubs", "cup", "season", "exhibition", "others") if k in league}
        value = ("europe" in league, deepcopy(league.get("europe")))
        return value, (value, context)
    roots = {"game": "game_europe", "association": "conmebol_associations", "first": "europe_first"}
    node = recipe if kind == "root" else recipe.get(roots[kind]) or {}
    value = (name in node, deepcopy(node.get(name)))
    return value, value


def write(recipe, key, value):
    """Patch one qualification slot; callers own the touched containers."""
    _namespace, kind, name = key
    present, data = value
    if kind == "league":
        node = next(L for L in recipe.get("leagues") or [] if L.get("name") == name)
        field = "europe"
    elif kind == "root":
        node, field = recipe, name
    else:
        root = {"game": "game_europe", "association": "conmebol_associations", "first": "europe_first"}[kind]
        if not present and not recipe.get(root):
            return
        if recipe.get(root) is None:
            recipe[root] = {}
        node, field = recipe[root], name
    if present:
        node[field] = deepcopy(data)
    else:
        node.pop(field, None)
        if kind in ("game", "association", "first") and not node:
            recipe.pop({"game": "game_europe", "association": "conmebol_associations", "first": "europe_first"}[kind], None)


def preview(recipe, changes):
    result = dict(recipe)
    kinds = {k[1] for k in changes if k[0] == "qualification"}
    if "league" in kinds:
        result["leagues"] = [dict(L) for L in recipe.get("leagues") or []]
    for kind, root in (("game", "game_europe"), ("association", "conmebol_associations"), ("first", "europe_first")):
        if kind in kinds:
            result[root] = dict(recipe.get(root) or {})
    for key, value in changes.items():
        if key[0] == "qualification":
            # A removed source may still own an unsaved draft. Keep that draft
            # in the editor, but never resurrect its league in a read-only preview.
            if key[1] == "league" and not any(L.get("name") == key[2] for L in result.get("leagues") or []):
                continue
            write(result, key, value)
    return result


def metadata(base):
    if not base:
        return (), (), {}
    paths = [os.path.join(base, n) for n in ("Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin", "Team.bin", "Country.bin", "PlayerAssignment.bin")]

    def load():
        countries = B.game_league_countries(base)
        confeds = B.country_confederations(base)
        ids = dict(B.country_ids(base))
        comp, regs = M.load(base, "Competition.bin"), M.load(base, "CompetitionRegulation.bin")
        regrow = {int.from_bytes(regs[i + M.R_ID:i + M.R_ID + 2], "little"): regs[i:i + M.REG] for i in range(0, len(regs), M.REG)}
        regions = {comp[i + M.CID_OFF]: M.dec_region(comp[i + M.REGION_OFF]) for i in range(0, len(comp), M.COMP)}
        native = []
        for rid, name, clubs, shipped in B.game_europe_tops(base):
            country = countries.get(rid, "")
            conf = confeds.get(country)
            if conf not in TARGETS:
                continue
            cup = B.home_cup(regrow, regions, regions.get(regrow[rid][M.R_CID])) is not None
            native.append(Source("game", str(rid), name, country, conf, clubs, cup,
                                 tuple(tuple(p) for p in shipped), ids.get(country, 0)))
        playable = B.game_top_division_countries(base)
        associations = []
        for name, country in ids.items():
            if confeds.get(name) == 4 and country not in playable:
                associations.append(Source("association", name, name, name, 4,
                                           min(B.FINAL_ASSOC_RANK, B.association_club_capacity(base, country)), country_id=country))
        return tuple(native), tuple(associations), confeds

    return filecache.by_files("cups-qualification-sources", paths, load)


def sources(recipe, base, fallback_confeds=None):
    native, associations, confeds = metadata(base)
    confeds = dict(fallback_confeds or {}, **confeds)
    result = []
    for source in native:
        key = next((k for k in recipe.get("game_europe") or {} if str(k) == str(source.key)), source.key)
        result.append(Source(**dict(source.__dict__, key=key)))
    own_countries = set()
    country_ids = {s.country: s.country_id for s in native + associations}
    for L in recipe.get("leagues") or []:
        if not eligible(L):
            continue
        country = L.get("country", "")
        own_countries.add(country)
        conf = confeds.get(country)
        if conf in TARGETS:
            result.append(Source("league", L["name"], L["name"], country, conf,
                                 int(L.get("clubs") or 0), bool(L.get("cup")), country_id=country_ids.get(country, 0)))
    if modern(recipe):
        templates = list(associations) + [Source("association", s.country, s.country, s.country, 4, s.clubs,
                                                country_id=s.country_id) for s in native if s.confederation == 4]
        for source in templates:
            key = next((k for k in recipe.get("conmebol_associations") or {}
                        if str(k).strip().casefold() == source.name.casefold()
                        or str(k).strip() == str(source.country_id)), source.key)
            parents = [s for s in result if s.kind != "association" and s.country == source.country]
            if parents:
                if key not in (recipe.get("conmebol_associations") or {}):
                    continue
                own = [s for s in parents if s.kind == "league"]
                parent = own[0] if len(own) == 1 else parents[0]
                result.append(Source(**dict(source.__dict__, key=key, clubs=min(B.FINAL_ASSOC_RANK, parent.clubs),
                                            linked_to=parent.draft_key, invalid_link=len(own) != 1)))
            else:
                result.append(Source(**dict(source.__dict__, key=key)))
    return tuple(result)


def destinations(conf, recipe):
    ids = TARGETS[conf]
    if conf == 4 and not modern(recipe):
        ids = (3, 4)
    if conf == 2 and not recipe.get("uecl", True):
        ids = tuple(c for c in ids if c not in (2, 12))
    names = dict(W.COMPETITIONS)
    return [(c, names[c]) for c in ids]


def touches_native(rows):
    generated = {c for c, _n, _code, _conf, _fill in W.CCUPS} | {W.SUD_FIRST}
    for row in rows or []:
        try:
            if len(row) == 2 and int(row[1]) not in generated:
                return True
        except (TypeError, ValueError):
            pass
    return False


def effective(source, recipe):
    present, rows = state(recipe, source.draft_key)[0]
    if source.kind != "game":
        return list(rows or [])
    native = [] if modern(recipe) and int(source.key) in {r for r, _l, _q in W.SAM_GAME} else [list(p) for p in source.native]
    if not present:
        return native
    # Exact current game_europe() semantics: empty/generated-only overrides do
    # not add a native replacement to game_replace. Do not promise otherwise.
    return list(rows or []) if touches_native(rows) else native + list(rows or [])


def editable_rows(source, recipe):
    present, rows = state(recipe, source.draft_key)[0]
    return list(rows or []) if present or source.kind != "game" else effective(source, recipe)


def inherited_text(source, recipe):
    if source.linked_to:
        return _("Stored association ranks are retained under their original key. This country now has a playable league; review these legacy rows explicitly. They are not a new league-less source.")
    if source.kind == "association":
        return _("Association ranks resolve to eligible clubs at runtime, not league positions or team IDs. Available clubs: %d.") % source.clubs
    if source.kind == "league":
        return _("These are the same qualification fields used by Edit League. Cup-winner places cascade through this domestic source.")
    if state(recipe, source.draft_key)[0][0]:
        if not touches_native(editable_rows(source, recipe)) and (source.native or
                (str(source.key) in {str(r) for r, _l, _q in W.SAM_GAME} and not modern(recipe))):
            return _("This backend retains native access for empty or generated-cup-only overrides. The table edits your stored rows only; inherited entries still count in the overview. Explicit native destinations replace native access.")
        return _("Your places: they replace the game's for this league.")
    sam = {str(r): (l, q) for r, l, q in W.SAM_GAME}
    if str(source.key) in sam and not source.native:
        if modern(recipe):
            return _("Modern CONMEBOL disables this league's native Libertadores access. Enable Own places and configure its allocations.")
        return _("Native Libertadores groups: %s; qualifying: %s. These executable-managed places are retained, not an empty custom allocation.") % sam[str(source.key)]
    return _("Native access is retained. The rows below are read-only reference; enable Own places to replace them.")


def row_errors(source, rows, recipe):
    errors = B.europe_problems(source.clubs, rows, source.cup)
    allowed = dict(destinations(source.confederation, recipe))
    for row in rows:
        try:
            target = int(row[1])
        except (ValueError, TypeError, IndexError):
            continue
        if target not in allowed:
            errors.append(_("Destination %d is inactive, legacy or incompatible with the selected confederation/mode; its stored value is preserved.") % target)
    if source.kind == "association" and any(int(p[0]) == 0 for p in rows if len(p) == 2):
        errors.append(_("An association rank must start at 1; no domestic cup-winner slot exists."))
    return errors


def allocation_counts(all_sources, recipe, conf):
    counts = Counter()
    notes = []
    allowed = dict(destinations(conf, recipe))
    seen_sources = {}
    for source in all_sources:
        seen = seen_sources.setdefault(source.linked_to or source.draft_key, set())
        if source.invalid_link:
            notes.append(_("%s: stored association data conflicts with playable top divisions; the backend requires explicit review/removal.") % source.country)
            continue
        # Count effective rows from all sources, even historically cross-confed
        # allocations; warn about their location rather than hiding them.
        for row in effective(source, recipe):
            try:
                p, c = map(int, row)
                if c in allowed or (conf == 4 and c == 18):
                    if p in seen or p < 0 or p > source.clubs or (p == 0 and not source.cup):
                        notes.append(_("%s: an allocation cannot resolve to an eligible club.") % source.name)
                    else:
                        counts[c] += 1
                    seen.add(p)
            except (TypeError, ValueError):
                notes.append(_("%s: malformed qualification row retained.") % source.name)
    return counts, notes


def overview(all_sources, recipe, conf):
    counts, notes = allocation_counts(all_sources, recipe, conf)
    allowed = dict(destinations(conf, recipe))
    names = dict(W.COMPETITIONS)
    if conf == 4 and modern(recipe):
        lines = ["%s: %d / %d — %s" % (_(names[c]), counts[c], want,
                 _("Complete") if counts[c] == want else _("Incomplete") if counts[c] < want else _("Excess"))
                 for c, want in MODERN_TOTALS.items()]
        lines.append(_("Phase 3 receives only phase-2 winners; no direct assignments are supported."))
    elif conf == 2:
        comps = [c for c, n in counts.items() for _i in range(n)] + [e[2] for e in W.HOLDERS]
        lines = [tr(W.europe_count_text(W.europe_count(comps, bool(recipe.get("uecl", True))))),
                 _("Qualifying rounds and overflow use the existing access list and seeding. Check the current plan for the resolved rounds.")]
        lines += [_('%s: %d configured entries; seeding resolves their qualifying rounds.') % (_(names[c]), counts[c])
                  for c in (10, 11, 12) if c in allowed]
    else:
        lines = ["%s: %d" % (_(names[c]), counts[c]) for c in allowed]
        for c, _n, _code, cup_conf, fill in W.CCUPS:
            if cup_conf == conf and c in allowed:
                sizes = [n for n in B.CCUP_SIZES if c not in W.CCUP_KNOCKOUT or n <= B.CCUP_KNOCKOUT_MAX]
                lines.append(_("%s: supported fields %s; inherited fill and the current plan determine the generated field.") % (_(names[c]), "/".join(map(str, sizes))))
        if conf == 4:
            lines.append(_("Original Libertadores access remains native. Classic Sudamericana is not generated; its old places remain stored but inactive."))
        if conf == 3:
            lines.append(_("Native AFC Champions League access and format are retained; this UI does not invent an Elite access list."))
    known = {s.draft_key for s in all_sources}
    try:
        B.recipe_has_modern_conmebol(recipe)
    except B.BuildError as exc:
        notes.append(str(exc))
    for key in keys(recipe):
        if key[1] in ("game", "association") and key not in known:
            notes.append(_("Stored source %s is unavailable here; its data is preserved and is not counted. Check the current plan.") % str(key[2]))
    return lines + list(dict.fromkeys(notes))


def ranked_sources(all_sources, recipe, conf):
    rows = [s for s in all_sources if s.confederation == conf and not s.linked_to]
    if conf != 2:
        return sorted(rows, key=lambda s: (s.kind == "association", s.kind != "game", s.name.casefold())), []
    identifier = lambda s: "g%d" % int(s.key) if s.kind == "game" else s.key
    by_id = {identifier(s): s for s in rows}
    candidates = [dict(id=identifier(s), name=s.name, country=s.country, clubs=s.clubs,
                       cup=s.cup, game=s.kind == "game") for s in rows]
    on, off = uefakey.ranked(recipe, None, candidate_rows=candidates)
    return [by_id[c["id"]] for c in on], [by_id[c["id"]] for c in off]


def generate(recipe, all_sources, conf, ranked, excluded, sizes=None):
    """Deterministic UI proposal; never writes to recipe. Not official non-UEFA quotas."""
    proposed = preview(recipe, {})
    proposed["leagues"] = [dict(L) for L in recipe.get("leagues") or []]
    proposed["game_europe"] = dict(recipe.get("game_europe") or {})
    proposed["conmebol_associations"] = dict(recipe.get("conmebol_associations") or {})
    notes = []
    shortage = False
    if conf == 2:
        def candidate(s):
            return dict(id="g%d" % int(s.key) if s.kind == "game" else s.key, name=s.name,
                        country=s.country, clubs=s.clubs, cup=s.cup, game=s.kind == "game")
        notes.extend(tr(n) for n in uefakey.apply(proposed, list(map(candidate, ranked)), list(map(candidate, excluded))))
        for source in ranked + excluded:
            if source.kind == "game" and source.key != str(int(source.key)):
                data = proposed["game_europe"].pop(str(int(source.key)))
                write(proposed, source.draft_key, (True, data))
        for s in excluded:
            if s.kind == "game" and s.native:
                notes.append(_("%s: the existing backend retains native access for an empty game-league override. Exclusion is saved using the existing UEFA key, but cannot suppress that inherited access here.") % s.name)
        for s in ranked + excluded:
            if s.kind == "game":
                other = [p for p in effective(s, recipe) if int(p[1]) not in TARGETS[2]]
                if other:
                    write(proposed, s.draft_key, (True, effective(s, proposed) + other))
        if not recipe.get("uecl", True):
            # Keep saved Conference places inert instead of silently deleting them.
            for s in ranked + excluded:
                rows = [p for p in effective(s, proposed) if int(p[1]) not in (2, 12)]
                rows += [p for p in effective(s, recipe) if int(p[1]) in (2, 12)]
                write(proposed, s.draft_key, (True, rows))
            proposed["uefa_seed"] = [p for p in proposed["uefa_seed"] if p[2] not in (2, 12)]
            notes.append(_("Conference League is off. Existing Conference allocations are retained as inactive data, not generated anew."))
    else:
        if conf == 4 and not modern(recipe):
            return {}, [_('Enable modern CONMEBOL explicitly before generating this preset.')], False
        targets = {k: n for k, n in MODERN_TOTALS.items() if n} if conf == 4 else dict(sizes or {})
        if not targets or any(c not in dict(destinations(conf, recipe)) for c in targets):
            return {}, [_('No supported generated field was selected.')], False
        if conf != 4:
            generated = {c for c, _n, _code, continent, _fill in W.CCUPS if continent == conf}
            if any(c not in generated or n not in B.CCUP_SIZES or
                   (c in W.CCUP_KNOCKOUT and n > B.CCUP_KNOCKOUT_MAX) for c, n in targets.items()):
                return {}, [_('The selected allocation size is not supported by the existing competition.')], False
        retained = {s.draft_key: [p for p in effective(s, recipe) if int(p[1]) not in targets] for s in ranked + excluded}
        affected = set(retained)
        outside = Counter(int(p[1]) for s in all_sources if s.draft_key not in affected for p in effective(s, recipe))
        free = {s.draft_key: [p for p in range(1, s.clubs + 1)
                             if p not in {int(row[0]) for row in retained[s.draft_key]}] for s in ranked}
        for s in ranked + excluded:
            write(proposed, s.draft_key, (True, retained[s.draft_key]))
        for target, required in targets.items():
            needed = max(0, required - outside[target])
            if outside[target] > required:
                shortage = True
                notes.append(_("Existing allocations outside this ranking already exceed destination %d.") % target)
            while needed:
                progress = False
                for s in ranked:
                    if not free[s.draft_key]:
                        continue
                    pos = free[s.draft_key].pop(0)
                    rows = effective(s, proposed) + [[pos, target]]
                    write(proposed, s.draft_key, (True, rows))
                    needed -= 1
                    progress = True
                    if not needed:
                        break
                if not progress:
                    break
            if needed:
                shortage = True
                notes.append(_("%s: shortage of %d eligible source positions.") % (_(dict(W.COMPETITIONS)[target]), needed))
        if conf == 3:
            notes.append(_("Native AFC Champions League places are retained; only the generated AFC cups are proposed."))
    fatal = []
    changed_sources = ranked + excluded
    for s in changed_sources:
        # Previously stored unsupported destinations are preserved. They are
        # warnings, but never repaired silently by a ranking operation.
        old = effective(s, recipe)
        new = effective(s, proposed)
        if old != new:
            fatal.extend("%s: %s" % (s.name, e) for e in B.europe_problems(s.clubs, new, s.cup))
    notes.extend(fatal)
    if conf == 4 and any(int(p[1]) in (4, 18) for s in all_sources for p in effective(s, proposed)):
        shortage = True
        notes.append(_("Preserved Libertadores qualifying/phase-3 legacy rows conflict with modern access. Review them explicitly before using this preset."))
    if conf == 4 and any(s.linked_to and state(recipe, s.draft_key)[0][0] for s in all_sources):
        shortage = True
        notes.append(_("Review the stored association records that now belong to playable countries before generating a preset; no legacy record was migrated or removed."))
    changes = {}
    for key in keys(recipe) | keys(proposed):
        before = state(recipe, key)[0]
        after = state(proposed, key)[0]
        if before != after:
            changes[key] = after
    complete = not fatal and not shortage
    return changes, notes, complete


def club_choices(recipe, base):
    """Same references as EuropeFirstDialog, filtered to playable domestic clubs."""
    def read_clubs():
        leagues = B.game_leagues(base)
        friendly = B.friendly_cids(leagues)
        leagues = [L for L in leagues if L[1] not in friendly]
        raw = B.pesdb.wesys_unpack(open(os.path.join(base, "Team.bin"), "rb").read())
        national = {int.from_bytes(raw[o + B.W.T_ID:o + B.W.T_ID + 4], "little")
                    for o in range(0, len(raw), B.W.T_REC) if raw[o + B.T_NATIONAL] & 0x80}
        return {"clubs": B.game_clubs(base), "national": national,
                "league_of": {t: name for _r, _c, name, teams in leagues for t in teams},
                "club_country": B.club_countries(base)}
    paths = [os.path.join(base, n) for n in ("Team.bin", "Competition.bin", "CompetitionRegulation.bin", "CompetitionEntry.bin", "Country.bin")]
    info = filecache.by_files("cups-first-club-labels", paths, read_clubs)
    labels, canonical = {}, {}
    countries = dict((c, n) for n, c in B.country_ids(base))
    for tid, (name, _short) in info["clubs"].items():
        if tid in info["national"] or tid not in info["league_of"]:
            continue
        league = info.get("league_of", {}).get(tid, "")
        country = countries.get(info.get("club_country", {}).get(tid), "")
        labels[tid] = "%s — %s / %s [%d]" % (name, league, country, tid)
        canonical[tid] = ("game", tid)
    for L in recipe.get("leagues") or []:
        if L.get("others") or L.get("exhibition"):
            continue
        inherited = {int(g["at"]): g for g in L.get("game_clubs") or []}
        for k in range(int(L.get("clubs") or 0)):
            ref = "%s/%d" % (L["name"], k)
            g = inherited.get(k)
            if g and int(g["id"]) not in info["clubs"]:
                continue
            name = info["clubs"][int(g["id"])][0] if g else B.club_name(
                {"name": L["name"], "club_names": list(L.get("club_names") or [])}, k)
            labels[ref] = "%s — %s / %s [%s]" % (name, L["name"], L.get("country", ""), ref)
            canonical[ref] = ("game", int(g["id"])) if g else ("new", L["name"], k)
    return labels, canonical


def reference_key(ref):
    s = str(ref).strip()
    if s.isdigit():
        return int(s)
    name, slash, index = s.rpartition("/")
    return "%s/%d" % (name.strip(), int(index.strip())) if slash and index.strip().isdigit() else s


def canonical_ref(ref, aliases):
    key = reference_key(ref)
    return aliases.get(key, ("unresolved", str(ref)))


def validate_changes(original, recipe, changes, available, aliases=None):
    """Local Apply checks; incomplete global packages remain editable drafts.

    Stored legacy destinations are not silently migrated. New unsupported rows
    are refused; unchanged legacy rows can remain and are diagnosed by the UI.
    """
    errors = []
    by_key = {s.draft_key: s for s in available}
    for key in changes:
        if key[0] != "qualification" or key[1] not in ("game", "league", "association"):
            continue
        present, rows = state(recipe, key)[0]
        if not present:
            continue
        source = by_key.get(key)
        if source is None:
            errors.append(_("A qualification source was removed or is no longer eligible. Discard to reload it."))
            continue
        if source.invalid_link:
            errors.append(_("Remove the incompatible saved association override explicitly; configure the playable league's own places instead."))
            continue
        errors.extend("%s: %s" % (source.name, e) for e in B.europe_problems(source.clubs, rows or [], source.cup))
        old = state(original, key)[0][1] or []
        allowed = dict(destinations(source.confederation, recipe))
        for p in rows or []:
            if len(p) == 2 and int(p[1]) not in allowed and p not in old:
                errors.append(_("%s: a new allocation uses an unavailable destination.") % source.name)
    for source in available:
        if source.linked_to and not source.invalid_link and (source.draft_key in changes or source.linked_to in changes):
            parent = by_key.get(source.linked_to)
            if parent:
                combined = editable_rows(parent, recipe) + editable_rows(source, recipe)
                errors.extend("%s: %s" % (parent.name, message)
                              for message in B.europe_problems(parent.clubs, combined, parent.cup))
    for key, title in B.EUROPE_FIRST:
        draft_key = ("qualification", "first", key)
        if draft_key in changes:
            rows = (recipe.get("europe_first") or {}).get(key) or []
            if len(rows) > B.FIRST_MAX:
                errors.append(_("%s: at most %d manual participants are supported.") % (_(title), B.FIRST_MAX))
    if any(k[0] == "qualification" and k[1] == "first" for k in changes):
        seen = set()
        old_first = original.get("europe_first") or {}
        current_first = recipe.get("europe_first") or {}
        old_counts = Counter(canonical_ref(ref, aliases or {}) for key, _title in B.EUROPE_FIRST for ref in old_first.get(key) or [])
        counts = Counter()
        for key, _title in B.EUROPE_FIRST:
            for ref in current_first.get(key) or []:
                canonical = canonical_ref(ref, aliases or {})
                counts[canonical] += 1
                if canonical in seen and counts[canonical] > old_counts[canonical]:
                    errors.append(_("A club cannot be assigned to more than one European competition."))
                seen.add(canonical)
        # Use the same builder validator, excluding only already-unresolvable
        # references that the user has not chosen to remove from an old recipe.
        by_name = {L["name"].strip().lower(): dict(rid=i + 1, clubs=int(L.get("clubs") or 0))
                   for i, L in enumerate(recipe.get("leagues") or []) if L.get("name")}
        first = dict(recipe.get("europe_first") or {})
        for key, _title in B.EUROPE_FIRST:
            old = (original.get("europe_first") or {}).get(key) or []
            valid = []
            for ref in first.get(key) or []:
                name, _slash, pos = str(ref).rpartition("/")
                resolved = str(ref).strip().isdigit() or (name.strip().lower() in by_name and pos.strip().isdigit()
                            and int(pos) < by_name[name.strip().lower()]["clubs"])
                if aliases is not None and reference_key(ref) not in aliases:
                    resolved = False
                if resolved:
                    valid.append(ref)
                elif ref not in old:
                    errors.append(_("A new first-season club reference cannot be resolved: %s") % str(ref))
            first[key] = valid
        try:
            B.europe_first(dict(recipe, europe_first=first), by_name)
        except B.BuildError as exc:
            errors.append(str(exc))
    return errors
