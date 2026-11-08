# Continental CUPS audit — 2026-11-07

This is an audit of the current local engine and source tables, not a list of real-life
competitions. Phase 3 adds presentation and existing identity/settings editing only.

Final navigation: MY WORLD > CUPS > CONTINENTAL contains both Competitions and
the completed Qualification editor. Country cup tables are CUPS > Game Countries
and Our Countries; UEFA Ranking and First-season clubs are inside UEFA >
Qualification. Trophies is an embedded GAME CONTENT > TROPHIES page, immediately
above Other content. LEAGUES > MORE retains only Pre-season cups, Competition
names, Competition IDs, League order, Seasons of the game's leagues, and World
name and file. References to Phase 3 below describe that audit's original scope.

The subsequent retirement of classic Sudamericana generation is an intentional
backend change, preserving inactive historical allocations. The optional
`continental_emblems` extension preserves existing single-logo worlds. Native
modern CONMEBOL strips were visually confirmed by the maintainer in FL27 using
Bolivia (three blue and four orange places); FL26 has not been independently
checked in-game. Dark/Light emblems have automated coverage, but their in-game
rendering remains incompletely verified.

## Sources and identifier namespaces

- `tools/mkleague.py`: `SHIPPED_CID`, native competition codes and IDs.
- `tools/leaguebuilder.py`: `CONTINENTAL_CIDS`, `caf_super_cup`,
  `samerica_super_cup`, `continental`, `europe`, `qual_rounds`,
  `libertadores_qualifying`, `prepare_sudamericana_first`, `sudamericana_playoffs`.
- `tools/fl26world.py`: `COMPETITIONS`, `CCUPS`, `CONMEBOL_STAGE_TARGETS`.
- `tools/mkuecl.py`: Conference League creation and fixed competition ID 174.
- `tools/mkeuropo.py`: European qualification/play-offs and CONMEBOL auxiliary stages.
- Locally unpacked `Competition.bin` and `CompetitionRegulation.bin`: confirm native
  slots, actual source names, confederations and stage limits.

**CID** means a game's competition ID; **cup number** means a generated continental
cup's recipe key; **target** means a logical qualification destination. They are not
interchangeable. For example, target 0 is UCL, but cup number 0 is the CAF Super Cup;
target 8 is AFC Champions League Two, while native CID 8 is AFC Champions League.

## Main competitions

| Confederation | Competition | Origin / internal mapping | CUPS display |
|---|---|---|---|
| UEFA | Champions League | Native CID 2; targets 0/10; existing league-phase rework | Yes, independent list entry |
| UEFA | Europa League | Native CID 3; targets 1/11; existing league-phase rework | Yes |
| UEFA | Conference League | Generated CID 174; targets 2/12; dedicated `uecl_*` storage | Yes |
| UEFA | UEFA Super Cup | Native CID 4 | Yes |
| CONMEBOL | Copa Libertadores | Native CID 5; classic and modern modes; targets 3/4/16/17/18 | Yes |
| CONMEBOL | Copa Sudamericana | Generated cup number 9; targets 9/19; modern package only | Yes, when modern CONMEBOL is enabled |
| CONMEBOL | Recopa Sudamericana | Generated cup number -1; modern mode, existing world setting | Yes, when modern CONMEBOL is enabled |
| CONCACAF | CONCACAF Champions Cup | Generated cup number/target 13 (`FL_CONCACAF`) | Yes |
| AFC | AFC Champions League / Elite reference | Native `AFC_CHAMPIONS_LEAGUE`, CID 8, target 5 | Yes, titled AFC Champions League Elite, with explicit legacy-format explanation |
| AFC | AFC Champions League Two | Generated cup number/target 8 (`FL_AFCCL2`) | Yes |
| AFC | AFC Challenge League | Generated cup number/target 15 (`FL_AFCCHL`) | Yes |
| CAF | CAF Champions League | Generated cup number/target 6 (`FL_CAFCL`) | Yes |
| CAF | CAF Confederation Cup | Generated cup number/target 7 (`FL_CAFCC`) | Yes |
| CAF | CAF Super Cup | Generated cup number 0 (`FL_CAFSC`); both CAF cups required | Yes |
| OFC | OFC Champions League | Generated cup number/target 14 (`FL_OFCCL`) | Yes |

### AFC naming and actual support

The engine calls its existing Asian top competition **AFC Champions League**. The
documentation also refers to its role as Champions League Elite
(`docs/developers/mod-studio.md`, continental cup winner fallback discussion).
The local source tables give CID 8 group-phase regulation 15 a 32-club limit and
knockout regulation 16 a 16-club limit. This is not a separately implemented modern
Elite format. The UI labels the role explicitly while preserving the source name as
the editable field's default, existing overrides, the CID, qualification target and
format. It never creates a second Elite tournament or rewrites an old recipe on open.

## Supported auxiliary competitions and stages

These are represented in their parent competition's details, not as misleading
independently editable tournaments. Their IDs can be assigned/pinned during Build.

| Confederation | Auxiliary competition or stage | Origin / mapping | CUPS display |
|---|---|---|---|
| CONMEBOL | Pre-Libertadores phases 1 and 2 | One generated auxiliary competition `FL_LIBQ`; targets 16/17 | Yes, Libertadores modern-mode stages; no independent identity setting exists |
| CONMEBOL | Libertadores phase 3 | Native qualifying regulation 8, parent CID 5; target 18 is internal, not a direct league place | Yes, Libertadores modern-mode stages |
| CONMEBOL | Sudamericana first stage | Generated auxiliary `FL_SUDA1`; target 19 | Yes, Sudamericana modern-mode stages |
| CONMEBOL | Sudamericana post-group play-off | Generated auxiliary `FL_SUDAPO`; 8 two-leg ties | Yes, Sudamericana modern-mode stages |
| UEFA | Champions League qualifying/play-offs | Native/added regulations under CID 2; target 10 | Yes, parent stages; existing access list determines summer rounds |
| UEFA | Europa League qualifying/play-offs | Native/added regulations under CID 3; target 11 | Yes, parent stages |
| UEFA | Conference League qualifying/play-offs | Added regulations under CID 174; target 12 | Yes, parent stages |
| CONMEBOL | Classic Libertadores qualifying | Native regulation 8 under CID 5; target 4 | Yes, classic-mode parent stages |

## Exclusions and extensibility

- Native **FIFA Club World Cup**, CID 1, is intercontinental (confederation 1), not
  a seventh confederation or a UEFA tournament. It remains reachable through the old
  Competition Names tool. Its separate existing engine reworks are outside Phase 3.
- Native IDs 6/7 occur in the engine's broad continental-slot range but are absent
  from the audited source tables. No tournaments are fabricated for those holes.
- Domestic cups, national-team competitions and World Selection Challenge are not
  confederation club competitions and remain outside this catalog.
- Real-life tournaments or modern formats absent from the source are not advertised
  as supported. In particular, the modern Elite format is not added by its UI label.
- Generated cup entries come from `fl26world.CCUPS`; super cups use the backend's
  existing factory definitions. Native entries are checked against engine-recognized
  slots and actual tables; additional valid native entries are discovered rather than
  filtered out by a mockup list. Display providers and storage adapters are separate
  from widget layouts.
- Independent names/logos exist only where the current engine/recipe already supports
  them. Existing native names, `ccup_*`, `uecl_*` and legacy logo aliases remain intact.

## Legacy Sudamericana migration

Modern CONMEBOL off now generates neither Sudamericana nor Recopa. Original
Libertadores access and rules remain available. Existing logical-9 qualification
rows in custom leagues and `game_europe` are retained unchanged but inactive, with
a notice in Check the plan/Build. `sudamericana_calendar` is retained on round-trip
for compatibility but no longer controls generation. There is no automatic migration.

To reactivate Sudamericana, enable modern CONMEBOL and configure its complete
allocation: Libertadores groups 26, phase 2 13, phase 1 6; Sudamericana groups 12,
first stage 32. Existing logical-9 rows count toward the 12 direct group places.
Old Libertadores qualifying (logical 4) cannot be mixed with modern phases.
Disabling modern mode retains the existing explicitly confirmed cleanup of
modern-only places and associations; logical-9 rows and competition identities stay.
Rebuild the world to change generated content; existing installations are not
rewritten merely by opening an old recipe.
