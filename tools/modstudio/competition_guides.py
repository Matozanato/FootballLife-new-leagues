"""Read-only system guides for the existing competition formats.

Sources: leaguebuilder.validate_modern_conmebol_access, libq_plan,
sudamericana_first_plan, prepare_sudamericana_first, sudamericana_playoffs,
samerica_super_cup and modern_conmebol_no_away_goals; fl26swiss.c's
lib9_titleholders, cont_build, lib9_holders and ccup_fill. These descriptions
do not assign places, change formats or supply fictional first-season winners.
"""
from .i18n import _


def conmebol(recipe, modern):
    if not modern:
        return (
            (_("Classic CONMEBOL"), (
                _("Libertadores keeps the game's qualifying, group and knockout stages. Original game qualification places remain unless explicitly overridden."),
                _("Modern mode off: no Copa Sudamericana or Recopa is generated. Libertadores keeps its original game system; custom qualifying phases 1 and 2 are not generated."),
            )),
            (_("Existing classic Sudamericana projects"), (
                _("Classic Sudamericana is no longer generated. Existing Sudamericana qualification rows remain stored but inactive while modern mode is off; normal selectors do not offer new assignments."),
                _("Existing classic Sudamericana rows remain visible in league editors and are preserved on save. They are not converted into modern places or deleted by hiding the competition."),
                _("The legacy sudamericana_calendar setting is retained for compatibility but has no effect. To use Sudamericana, enable modern CONMEBOL and complete all required qualification totals; no automatic conversion is performed."),
            )),
            (_("Switching to modern mode"), (
                _("Modern mode is a complete package: three Libertadores qualifying phases, modern Sudamericana and Recopa. Build requires the full global allocation shown when the option is on; there are no fixed country quotas."),
                _("Names and logos are retained when a competition is hidden. Disabling modern mode removes modern-only places and association allocations only after Apply and the existing confirmation; classic Libertadores, qualifying and Sudamericana places remain."),
            )),
        )
    return (
        (_("Modern versus classic"), (
            _("Modern CONMEBOL replaces the game's default South American access with the explicitly configured package. Libertadores and Sudamericana use the February-December cycle; the classic Sudamericana calendar option does not override the modern calendar."),
            _("Places can be distributed among custom leagues, original game leagues and eligible associations without a playable league. Build checks global totals, not country quotas. Enabling the option does not create the missing qualification assignments automatically."),
        )),
        (_("Libertadores — qualifying phases 1, 2 and 3"), (
            _("Phase 1: 6 assigned clubs play 3 two-leg ties. The 3 winners enter phase 2; the losers are eliminated."),
            _("Phase 2: 13 assigned clubs plus the 3 phase-1 winners make 16 clubs. Eight two-leg ties send 8 winners to phase 3; the losers are eliminated."),
            _("Phase 3: only the 8 phase-2 winners participate, in 4 two-leg ties. The 4 winners enter Libertadores groups; the 4 losers transfer to Sudamericana groups. No league receives a direct phase-3 place."),
        )),
        (_("Libertadores — groups and knockout"), (
            _("The 32-club group field is 26 configured direct places, 4 phase-3 winners and 2 protected previous-season titleholder places. There are 8 groups of 4."),
            _("The first two in each group reach the round of 16, followed by quarter-finals, semi-finals and the final. The 8 group thirds enter the Sudamericana post-group play-off; group fourths are eliminated."),
        )),
        (_("Sudamericana — first stage and groups"), (
            _("First stage: 32 assigned clubs play 16 one-match ties; the 16 winners reach the groups. Pairings stay inside a domestic source where possible; odd leftovers are paired across sources."),
            _("The group field has 32 clubs: 12 configured direct places, 16 first-stage winners and the 4 Libertadores phase-3 losers. They play in 8 groups of 4."),
        )),
        (_("Sudamericana — transfers, play-off and knockout"), (
            _("The 8 Sudamericana group winners go straight to the round of 16. The 8 group runners-up face the 8 Libertadores group thirds in 8 two-leg play-off ties."),
            _("Those 8 play-off winners join the 8 Sudamericana group winners in the round of 16, then quarter-finals, semi-finals and the final. Sudamericana group thirds and fourths are eliminated."),
            _("Libertadores transfers happen only after phase 3 (4 losers to Sudamericana groups) and after its group stage (8 thirds to the Sudamericana play-off). Phase-1 and phase-2 losers do not transfer."),
        )),
        (_("Required qualification places"), (
            _("Libertadores: 26 direct group places, 13 direct phase-2 places and 6 phase-1 places. Phase 3 has zero direct assignments; its entrants come from phase 2."),
            _("Sudamericana: 12 direct group places and 32 first-stage places. The remaining group and knockout entrants come from the progression described above."),
            _("Titleholder places and Recopa participants are supplied by competition results, not extra league assignments. The classic Libertadores qualifying destination cannot be mixed with the modern phase-1/phase-2 allocation."),
        )),
        (_("Titleholders and the first season"), (
            _("The previous Libertadores and Sudamericana champions occupy the 2 protected Libertadores group places. The runtime retains those winners across the calendar-year rollover and protects them before assigning domestic access."),
            _("If a retained champion also qualifies domestically, that domestic allocation cascades to the next eligible club of the same source rather than duplicating the champion."),
            _("A new career has no retained previous-season champions to inject. Until eligible winners exist, those places keep the game's native/default filling. Do not add 2 extra domestic places: Build still requires 26."),
        )),
        (_("Recopa Sudamericana"), (
            _("Recopa is one match in late February between the previous Libertadores and Sudamericana champions. It requires modern Sudamericana and respects the existing Recopa enable/disable setting."),
            _("The first Recopa normally stays unplayed because a new career has no previous winners. Existing first-season participant overrides can supply the two clubs as fallbacks; retained winners take priority once available."),
        )),
        (_("Match rules and changing modes"), (
            _("Modern Libertadores and Sudamericana knockout ties have no away-goals rule or extra time; a level tie is decided on penalties. Recopa retains its existing one-match rules."),
            _("Names and logos are retained when a competition is hidden. Disabling modern mode removes modern-only places and association allocations only after Apply and the existing confirmation; classic Libertadores, qualifying and Sudamericana places remain."),
        )),
    )


def european(recipe, modern):
    return ((_('European competition format'), (
        _("Every world built here has the new Champions League and Europa League: a league phase of 36 clubs, then the play-off and the knockout rounds."),
        _("Conference League also has a 36-club league phase and a February play-off when included. Switching it off keeps its custom name and logo and leaves the Champions League and Europa League formats unchanged."),
        _("European places, UEFA Ranking and first-season European participants remain available through the existing league tools. This page edits competition identities and the Conference League option."),
    )),)


PROVIDERS = {2: european, 4: conmebol}


def sections(confederation, recipe, modern):
    provider = PROVIDERS.get(confederation)
    return provider(recipe, modern) if provider else ()
