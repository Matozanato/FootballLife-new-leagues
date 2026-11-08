"""UI catalog and recipe adapters for continental club competitions.

The identifiers here are explicitly namespaced: game competition IDs, generated cup
numbers and logical access targets are different things. Formats remain backend rules.
"""
from dataclasses import dataclass, replace

import leaguebuilder as B
import fl26world as W
import mkleague as M
import continental_emblems as E

from .i18n import _
from . import qualification_data as Q

CONFEDERATIONS = ((2, "UEFA"), (4, "CONMEBOL"), (6, "CONCACAF"),
                 (3, "AFC"), (5, "CAF"), (7, "OFC"))
MODERN_WARNING = (
    "Switching the modern CONMEBOL competitions off takes out the %d places only they have "
    "(Libertadores phase 1 and 2, Sudamericana first stage, countries without a league). "
    "Libertadores, qualifying and Copa Sudamericana places stay. Stored Sudamericana places become inactive; no Sudamericana or Recopa will be generated. Go on?"
)


@dataclass(frozen=True)
class Competition:
    key: str
    confederation: int
    name: str
    storage: str
    number: int | None
    information: str
    targets: tuple = ()
    available: bool = True
    title: str = ""
    native_stages: tuple = ()
    visibility_setting: str | None = None

    def path(self, field):
        if field in E.MODES:
            return (E.ROOT, E.key(self.storage, self.number), field)
        if self.storage == "game":
            return ("edits", "competitions", str(self.number), field)
        if self.storage == "uecl":
            return ("uecl_" + field,)
        return ("ccup_names" if field == "name" else "ccup_logos", str(self.number))

    def aliases(self, field):
        if self.storage == "generated" and field == "logo":
            alias = {0: "caf_super_cup_logo", -1: "samerica_super_cup_logo"}.get(self.number)
            return ((alias,),) if alias else ()
        return ()


@dataclass(frozen=True)
class Setting:
    key: str
    confederation: int
    label: str
    default: bool = True


SETTINGS = (Setting("uecl", 2, "Include the Conference League"),
            Setting("conmebol", 4, "Enable Libertadores new format, Sudamericana and Recopa Sudamericana", False),
            Setting("caf_super_cup", 5, "CAF Super Cup"))

# Only existing club competitions belong here; domestic and national-team cups stay
# available through Competition Names. New generated cups inherit CCUPS' metadata.
ORIGINALS = (
    Competition("game:ucl", 2, "Champions League", "game", M.SHIPPED_CID["UEFA_CHAMPIONS_LEAGUE"], "uefa", (0, 10)),
    Competition("game:uel", 2, "Europa League", "game", M.SHIPPED_CID["UEFA_EUROPE_LEAGUE"], "uefa", (1, 11)),
    Competition("game:uefa-super", 2, "UEFA Super Cup", "game", M.SHIPPED_CID["UEFA_SUPER_CUP"], "native-super"),
    Competition("game:libertadores", 4, "Copa Libertadores", "game", M.SHIPPED_CID["COPA_LIBERTADORES"],
                "libertadores", (3, 4, W.LIB_F1, W.LIB_F2, W.LIB_F3)),
    Competition("game:afc", 3, "AFC Champions League", "game", M.SHIPPED_CID["AFC_CHAMPIONS_LEAGUE"],
                "afc-elite", (5,), title="AFC Champions League Elite"),
)


def native_metadata(base):
    """Audit engine-recognized native club slots against actual tables, not UI mockups.

    CONTINENTAL_CIDS also includes FIFA's intercontinental cup. Confederation 1 is
    deliberately excluded from a page whose navigation is the six confederations.
    Absent/reserved slots (notably 6/7 in the standard tables) are not invented cups.
    """
    if not base:
        return {}, {}
    try:
        comp = M.load(base, "Competition.bin")
        regs = M.load(base, "CompetitionRegulation.bin")
    except (OSError, ValueError, B.BuildError, SystemExit):
        return {}, {}
    confeds, stages = {}, {}
    for i in range(0, len(comp), M.COMP):
        row = comp[i:i + M.COMP]
        cid, conf = row[M.CID_OFF], row[M.FLAG_OFF] & 7
        if cid in B.CONTINENTAL_CIDS and conf in dict(CONFEDERATIONS):
            confeds[cid] = conf
    for i in range(0, len(regs), M.REG):
        row = regs[i:i + M.REG]
        cid = row[M.R_CID]
        rid = int.from_bytes(row[M.R_ID:M.R_ID + 2], "little")
        if cid in confeds and rid < 1024:
            stages.setdefault(cid, []).append((rid, row[M.R_TYPE], row[M.R_TEAMS] & 0x3f))
    return confeds, stages


def catalog(base):
    try:
        names = {cid: name for cid, name, _regs in B.game_competitions(base)} if base else {}
    except (OSError, ValueError, B.BuildError, SystemExit):
        names = {}
    confeds, stages = native_metadata(base)
    entries = [replace(c, name=names.get(c.number, c.name), available=c.number in names,
                       native_stages=tuple(stages.get(c.number, ()))) for c in ORIGINALS]
    known = {c.number for c in ORIGINALS}
    for cid, conf in sorted(confeds.items()):
        if cid not in known and cid in names:
            entries.append(Competition("game:%d" % cid, conf, names[cid], "game", cid, "native",
                                       native_stages=tuple(stages.get(cid, ()))))
    entries.insert(2, Competition("uecl", 2, B.mkuecl.NAME, "uecl", None, "uecl", (2, 12),
                                  visibility_setting="uecl"))
    for number, name, _code, conf, _fill in W.CCUPS:
        info = "sudamericana" if number == B.SUDAM else "generated"
        targets = (number, W.SUD_FIRST) if number == B.SUDAM else (number,)
        entries.append(Competition("generated:%d" % number, conf, name, "generated", number, info, targets,
                                   visibility_setting="conmebol" if number == B.SUDAM else None))
    for factory, info in ((B.samerica_super_cup, "recopa"), (B.caf_super_cup, "caf-super")):
        definition = factory({})
        entries.append(Competition("generated:%d" % definition["number"], definition["conf"],
                                   definition["name"], "generated", definition["number"], info,
                                   visibility_setting="conmebol" if info == "recopa" else "caf_super_cup"))
    return tuple(entries)


def slot(recipe, path):
    """Presence matters: absent defaults and explicit empty/false fields are preserved."""
    node = recipe
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return (False, None)
        node = node[key]
    return (True, node)


def put(recipe, path, value):
    """Patch one field, pruning only empty ancestors of that field."""
    node, ancestors = recipe, []
    for key in path[:-1]:
        if not isinstance(node.get(key), dict):
            if value is None:
                return
            node[key] = {}
        ancestors.append((node, key))
        node = node[key]
    if value is None:
        node.pop(path[-1], None)
        for parent, key in reversed(ancestors):
            if parent[key]:
                break
            parent.pop(key)
    else:
        node[path[-1]] = value


def identity(recipe, competition, field):
    primary = slot(recipe, competition.path(field))[1]
    if field == "logo" and not primary:
        primary = next((slot(recipe, p)[1] for p in competition.aliases(field) if slot(recipe, p)[1]), None)
    return primary or ("" if field == "name" else None)


def fingerprint(recipe, competition, field):
    return tuple(slot(recipe, p) for p in (competition.path(field),) + competition.aliases(field))


def write_identity(recipe, competition, field, value):
    put(recipe, competition.path(field), value or None)
    for alias in competition.aliases(field):
        # CAF's old editor mirrors its alias. Existing Recopa aliases stay consistent;
        # clearing either logo also clears its fallback, so an old picture cannot reappear.
        if competition.number == 0 or slot(recipe, alias)[0] or not value:
            put(recipe, alias, value or None)


def modern(recipe):
    try:
        return B.recipe_has_modern_conmebol(recipe)
    except B.BuildError:
        return False


def setting_value(recipe, setting):
    return modern(recipe) if setting.key == "conmebol" else bool(recipe.get(setting.key, setting.default))


def visible(competition, recipe):
    """UI visibility only: hiding never removes identity or classic recipe data."""
    key = competition.visibility_setting
    if key is None:
        return True
    setting = next(s for s in SETTINGS if s.key == key)
    return setting_value(recipe, setting)


def set_modern_mode(recipe, on, confirm):
    """The legacy South American editor's operation, shared without UI or snapshots.

    None means the destructive change was cancelled; False is an unchanged recipe.
    """
    if on and recipe.get("conmebol") != B.CONMEBOL_MODERN:
        recipe["conmebol"] = B.CONMEBOL_MODERN
        return True
    if not on and modern(recipe):
        gone = B.modern_conmebol_places(recipe)
        if gone and not confirm(len(gone)):
            return None
        B.drop_modern_conmebol(recipe)
        return True
    return False


def preview_recipe(recipe, changes, competitions):
    """Copy only edited branches. Players and all other large data remain shared/read-only."""
    result = Q.preview(recipe, changes)
    if any(k[0] == "identity" and competitions[k[1]].storage == "game" for k in changes):
        result["edits"] = dict(recipe.get("edits") or {})
        result["edits"]["competitions"] = {k: dict(v) for k, v in
                                             (result["edits"].get("competitions") or {}).items()}
    for root in ("ccup_names", "ccup_logos"):
        if root in recipe:
            result[root] = dict(recipe[root] or {})
    if any(k[0] == "identity" and k[2] in E.MODES for k in changes):
        result[E.ROOT] = {k: dict(v) for k, v in (recipe.get(E.ROOT) or {}).items()}
    for key, value in changes.items():
        if key[0] == "qualification":
            continue
        if key[0] == "identity":
            write_identity(result, competitions[key[1]], key[2], value)
        elif key[1] == "conmebol":
            if not value:
                result["leagues"] = [dict(L) for L in result.get("leagues") or []]
                result["game_europe"] = dict(result.get("game_europe") or {})
            set_modern_mode(result, value, lambda _n: True)
        else:
            result[key[1]] = value
    return result


def configured_places(recipe, targets):
    rows = [p for L in recipe.get("leagues") or [] for p in L.get("europe") or []]
    for root in ("game_europe", "conmebol_associations"):
        rows += [p for places in (recipe.get(root) or {}).values() for p in places or []]
    count = 0
    for p in rows:
        try:
            count += int(p[1]) in targets
        except (TypeError, ValueError, IndexError):
            pass
    return count


def generated_information(c, recipe):
    sizes = [s for s in B.CCUP_SIZES if c.number not in W.CCUP_KNOCKOUT or s <= B.CCUP_KNOCKOUT_MAX]
    text = _("Supported fields: %s clubs. The current plan determines the field.") % "/".join(map(str, sizes))
    if c.number in W.CCUP_KNOCKOUT:
        return text + " " + _("Knockout competition; no group stage.")
    return text + " " + _("Fields of eight or more use groups of four followed by a knockout; four clubs use a knockout.")


def uefa_information(c, recipe):
    return _("League phase of 36 clubs, knockout play-off and knockout rounds. The Champions League and Europa League retain this format with Conference League off.") + " " + _("Summer qualification rounds are selected by the existing access list; they are stages of this competition.")


def libertadores_information(c, recipe):
    if not modern(recipe):
        return _("Classic mode: the game's Libertadores qualifying, group stage and knockout. Original game access stays unless explicitly replaced.")
    return _("Modern mode: three qualifying phases, eight groups of four, then knockout rounds. See the system guide below for progression, titleholders and required places.")


def sudamericana_information(c, recipe):
    if modern(recipe):
        return _("Modern mode: 32-club first stage, 32-club group stage, post-group play-off and knockout rounds. See the system guide below for transfers and required places.")
    return _("Sudamericana is not generated while modern CONMEBOL is off. Existing qualification places remain stored but inactive; the legacy calendar option has no effect.")


INFORMATION = {
    "generated": generated_information,
    "uefa": uefa_information,
    "uecl": lambda c, r: _("League phase of 36 clubs, knockout play-off and knockout rounds. Included only when Include the Conference League is on.") + " " + _("Summer qualification rounds are selected by the existing access list; they are stages of this competition."),
    "libertadores": libertadores_information,
    "sudamericana": sudamericana_information,
    "native": lambda c, r: _("Uses the game's existing competition format. This page does not change its stages or participant limits."),
    "afc-elite": lambda c, r: _("Elite is shown through the existing native AFC Champions League slot (AFC_CHAMPIONS_LEAGUE, competition ID 8; access target 5). Its original game name, logos and format are preserved. A separate modern Elite format is not implemented by this engine."),
    "native-super": lambda c, r: _("Uses the game's existing super cup format and participants."),
    "recopa": lambda c, r: _("One match in late February between the previous Libertadores and Sudamericana winners. Requires modern CONMEBOL and the Sudamericana. The first season normally has no previous winners; existing first-season participant settings are respected."),
    "caf-super": lambda c, r: _("Two clubs, one match in late July: CAF Champions League winner versus Confederation Cup winner. Requires both African cups and CAF Super Cup on. First played in the second season, after both cups have a winner."),
}


def information(c, recipe, plan=None):
    supercup = c.information in ("native-super", "recopa", "caf-super")
    status = _("Depends on configured places. Check the current plan to see whether it is generated.")
    if c.storage == "game":
        status = _("Available in the selected game's tables.") if c.available else _("Not found in the selected game's tables; identity editing is unavailable.")
    elif c.storage == "uecl":
        status = _("Included in this world.") if recipe.get("uecl", True) else _("Disabled; its name and logo are retained.")
    elif c.information == "caf-super" and not recipe.get("caf_super_cup", True):
        status = _("Disabled; its name and logo are retained.")
    elif c.information == "recopa" and (not modern(recipe) or not recipe.get("samerica_super_cup", True)):
        status = _("Unavailable in the selected mode or disabled by existing world settings.")
    format_text = INFORMATION[c.information](c, recipe)
    if c.information in ("native", "native-super", "afc-elite") and c.native_stages:
        kinds = {1: _("Qualifying"), 2: _("Group stage"), 3: _("Knockout")}
        source = "; ".join(_("%s: table limit %d clubs (regulation %d)") %
                           (kinds.get(kind, _("Stage")), count, rid)
                           for rid, kind, count in c.native_stages)
        format_text += " " + _("Native stage limits from the selected tables: %s.") % source
    if c.confederation == 4:
        try:
            B.recipe_has_modern_conmebol(recipe)
        except B.BuildError as exc:
            format_text = _("The existing CONMEBOL mode is invalid: %s. Check the current plan before building.") % str(exc)
    details = [("Type", _("Continental club super cup") if supercup else _("Continental club competition")),
               ("Source", _("Original game competition") if c.storage == "game" else _("Generated with the world")),
               ("Format and stages", format_text),
               ("Availability", status)]
    if c.targets:
        details.append(("Qualification overview", _("Explicit configured rows pointing to this competition: %d. Inherited places, automatic fill and capacity limits are resolved by the current plan. Edit places through the existing league tools.") % configured_places(recipe, c.targets)))
    elif supercup:
        details.append(("Qualification overview", _("Participants are the winners of the corresponding competitions.")))
    else:
        details.append(("Qualification overview", _("No logical qualification target is registered for this native competition. The existing game allocation is retained.")))
    if plan is not None:
        if plan.get("error"):
            details.append(("Current plan", _("The plan could not be completed: %s") % plan["error"]))
        elif c.storage == "generated":
            cup = plan["cups"].get(c.number)
            if cup is None:
                details.append(("Current plan", _("Not generated by the current plan.")))
            else:
                if cup["groups"]:
                    field = _("%d participants; %d groups.") % (cup["participants"], cup["groups"])
                else:
                    field = (_("%d participants; super cup.") if supercup else
                             _("%d participants; knockout.")) % cup["participants"]
                details.append(("Current plan", field))
        else:
            text = _("Current recipe plan completed successfully.")
            if c.information in ("uefa", "uecl"):
                rounds = [stage for target, stage in plan.get("uefa_rounds", ()) if target == c.targets[0]]
                if rounds:
                    text += " " + _("Summer rounds in the current plan: %s (%d clubs per round).") % (
                        ", ".join(_(W.QSTAGES[stage]) for stage in sorted(rounds)), W.PLAYOFF)
            details.append(("Current plan", text))
    return details


def plan_summary(recipe, base):
    """Use the actual builder on demand, retaining only a tiny display summary."""
    try:
        plan = B.plan(recipe, base)
        return {"cups": {c["number"]: {"participants": len(c.get("entry") or []), "groups": c.get("groups", 0)}
                         for c in plan.get("ccups") or []},
                "uefa_rounds": sorted(B.qual_rounds(plan))}
    except (B.BuildError, OSError, ValueError, SystemExit) as exc:
        return {"error": str(exc)}
