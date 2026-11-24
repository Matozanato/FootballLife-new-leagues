# CONCACAF competitions

## Current integration and maintenance

This overview describes the integrated recipe v3 path. The later prototype and v1/v2 sections are development history. Use the [validation ledger](leagues-cup-ui-validation.md) for the evidence status and the [user guide](../../../guides/en/mod-studio-guide.md) for configuration.

### Architecture and formats

| Boundary | Responsibility |
| --- | --- |
| Mod Studio | `competition_catalog.py` exposes settings and appearance. `qualification_data.py` and the Qualification editor translate individual rows into recipe fields. `concacaf_allocation.py` prepares drafts. Allocation overview, the competition plan and automatic assignment use the validated access from `leaguebuilder.plan`. |
| Python Build | `concacaf.py` validates geographic eligibility, unique source/position identities and slot totals. `leaguebuilder.build_concacaf` stages tables, checks actual feeders and records stable competition and regulation IDs in `cup_ids`. `mkconcacaf.py`, `central_probe.py`, `caribbean.py` and `leagues_probe.py` write native tables and contracts. Reserved replica families are checked as a unit. Technical competitions remain internal to presentation. |
| Lua | `sider/experimental/fl26swiss.lua` is the packaged runtime loader despite its source directory. It validates contract versions and native exports and registers results providers before Champions Cup. `sider/fl26joindll.lua` supplies the rollback/close integration. `tools/lbpack.py` defines the release packaging boundary. |
| Native | `fl26swiss.c` owns the runtime hooks and persistent journals. `fl26concacaf.h` handles Champions Cup access and handover. `fl26regional_places.h` resolves exact regional positions and domestic cup overlap. Central American Cup uses `fl26central_probe.h` and `fl26central_annual.h`. Caribbean Cup uses `fl26caribbean.h`. `fl26join.c` covers owned registration and rollback families. |

Champions Cup has 27 entrants, five direct to the Round of 16 and 22 in 11 two-leg Round One ties. The Round of 16, quarter-finals and semi-finals are two-legged, with a single final. Leagues Cup has two native 18-club tables, 54 cross-league fixtures and eight single-match knockout fixtures including third place. Central American Cup has four groups of five, quarter-finals, semi-finals, play-ins and final. Caribbean Cup has two groups of five, two-leg semi-finals, a single third-place match and a single final.

| Buildable feeders | Domestic Round of 16 | Domestic Round One | Domestic total |
| --- | ---: | ---: | ---: |
| None | 5 | 22 | 27 |
| Leagues | 4 | 20 | 24 |
| Central American | 4 | 17 | 21 |
| Caribbean | 4 | 20 | 24 |
| Leagues + Central American | 3 | 15 | 18 |
| Leagues + Caribbean | 3 | 18 | 21 |
| Central American + Caribbean | 3 | 15 | 18 |
| All three | 2 | 13 | 15 |

Each ready regional cup contributes one direct entrant and respectively two, five or two Round One entrants. Build rechecks which feeders were emitted. If the configured domestic total no longer matches, Champions Cup is omitted. A registered feeder without an inaugural result keeps Champions Cup waiting for the appropriate January draw. A missing source or exhausted replacement never creates an extra source or duplicate entrant.

### Contracts, qualification and persistence

Recipe v3 uses `regional_access` and `champions_access` arrays of `{source, rank}` rows. A domestic cup winner is `cup:<league source>` with rank 1. Canonical league aliases resolve phases and annual totals. The migration expands v2 regional counts into positions 1 through N and preserves collisions for review. The optional switches stay under `modules`. There is no Champions Cup switch or Leagues Cup access list.

The current wire versions are Champions Cup 3, Central American Cup 4, Caribbean Cup 3 and allocated Leagues Cup 2. The three individual-places contracts require the matching Lua loader and `fl26_swiss_regional_places_abi`; allocated Leagues Cup also requires the join rollback exports. Legacy versions remain readable. Runtime bounds include 40 league ranks, at most seven Central American sources with up to four phases each, up to 64 Champions Cup wire sources and native regulation masters within 1?1023. Keep spare IDs for the underlying replica families.

Ranked places reserve exact clubs before cup winners. A duplicate winner or an eligible inaugural route with no cup result scans its associated league for an available club. A later edition requires completed, dated domestic results. Rankings, cup winners, podiums and handover state are stored through the existing save-root journal. The versioned recipe and world file describe the rules; the save contains results. Reuse the same contract when reloading a career. Migrating a recipe is independent of migrating a running career.

### Scheduling and native presentation

Leagues Cup prefers common dates. Its joint planner reserves group fixtures and a feasible knockout contingency, enforces three days of rest, checks calendars and native capacity and can split rounds or individual group fixtures. The bounded recovery runs through September 30 for groups and October 31 for knockouts. Registration is checked before it is accepted. Verified rollback and daily retry prevent duplicates; an unverified rollback blocks further registration. Registered matches retain their dates. Later calendar producers can still exhaust the reserved alternatives.

Competition Info uses independent scrollable MLS and Liga MX standings, the native round-by-round knockout list, and native scorer and assist rankings. The presentation reads the active edition using full-width match IDs. It resolves regular goals, penalties and round labels separately. The rankings aggregate native per-player contributions before truncating to 40, exclude shootout goals and use Rules as the final menu entry. The historical bracket projection header remains part of the production knockout list. There is no custom Leagues Cup overlay.

For maintenance, check the recipe with the shared planner, regenerate isolated tables, inspect the world-file contract and validate DLL exports with `mkconcacaf.check_runtime`. Inspect source eligibility, exact slot totals and the runtime journal before investigating presentation. Sider logs expose participant proofs, dates and failed registration prerequisites, rollback results, knockout list hook installation and ranking fingerprints. See [testing](testing.md). Changes to IDs, contracts or journals require both offline regressions and the pending combined live run.


The dedicated Python generator, native handover and Lua contract loader were exercised
in an isolated FL27 development world through Round One, the final and subsequent seasons.
Target `13`, code `FL_CONCACAF`, the existing name, logo overrides and saved primary
competition/regulation pins remain its identity. There is no format selector or second cup.
New plans never pad/truncate it into the former 16-team knockout. Build rejects legacy plans,
unsupported feeder modules and incompatible packaged runtimes before writing staging files.
The standalone `mkccup.py` CLI also refuses `FL_CONCACAF`. Other continental generators
retain their existing behavior. Already installed worlds and careers are not edited.

## Recipe and plan

An existing `europe`/`game_europe` assignment to target 13 requests the modern plan.
Alternatively this top-level block requests it without explicit domestic assignments:

```json
{
  "concacaf": {
    "modules": {
      "leagues_cup": false,
      "central_american_cup": false,
      "caribbean_cup": false
    },
    "sources": {
      "liga_mx": ["My Mexican League"],
      "mls": [166]
    }
  }
}
```

Source overrides are optional, ordered lists of regulation ids or new league names.
Use the ids in the actual database; 166 above is only an example. Available domestic cup
ids are mapped to symbolic `cup:<league regulation>` sources. The pure planner also
accepts these symbolic ids. League roles are `liga_mx`, `mls`, `canadian_premier`;
cup roles are `canadian_championship`, `us_open_cup`, `liga_mx_champion`, `mls_cup`.
Regional sources belong to their module and cannot be overridden as domestic sources.
Unknown, foreign-association or unavailable explicit sources are errors.

The adapter discovers top divisions by table countries and confederations. Use source
overrides where a database has more than one top division. When a source has a whole-season
total, the builder registers its phases with 0.4.0's `seasonsum` provider and reserves the
cup dates for both phases. The first phase supplies live membership for a first-season
fallback and for filtering promoted or departed clubs. The retained whole-season table
supplies the ranking when available. Upstream can omit a half whose completed table is
unavailable, so a retained aggregate can represent fewer than all phases.

The FL26 and FL27 tables checked here expose MLS as total 51 with phases 166 and 167.
The aggregate can rank MLS clubs, subject to the completeness of those phase tables.
It cannot identify the MLS Cup playoff winner. The same copies expose no playable Liga MX
division or championship stages. A custom database can supply domestic league sources
and a genuine winner when its championship has an identifiable completed knockout
regulation and is exposed as a domestic cup source. The adapter does not auto-discover
MLS Cup playoffs or Liga MX season winners. Without a usable title result, the first
ranked eligible club in the supplied league remains the direct-berth proxy. Entry order
is available only when the source's first completion is still ahead.

`tools/concacaf.py` owns validation, source ordering, quotas and the qualification contract.
`plan()` stores a versioned `concacaf` object with 27 source places, not a fixed club list;
the ordinary `ccups` list holds a pending descriptor with an empty generic `entry` list.
Recipe settings round-trip independently of this derived object. `resolve()` is a pure
reference resolver for previews/tests; it is **not called by the game**. The native adapter
executes the equivalent domestic-source contract. Build marks the generated descriptor
runtime-ready only after table generation; that marker is not an in-game validation claim.

## Places and module combinations

| Pathway | Places | Direct Round of 16 |
|---|---:|---:|
| Liga MX | 6 | 1 |
| MLS | 5 | 1 |
| Leagues Cup | 3 | 1 |
| Central American Cup | 6 | 1 |
| Caribbean Cup | 3 | 1 |
| Canadian Premier League | 2 | 0 |
| Canadian Championship | 1 | 0 |
| US Open Cup | 1 | 0 |

All five direct places are reserved before the 22 Round One places. Round One has eleven
two-leg ties; eleven winners join the five direct clubs. Round of 16, quarterfinals and
semifinals have two legs; the final has one. No defending Champions Cup winner is added.

| Leagues | Central | Caribbean | Regional-result sources | Redistributed places |
|---|---|---|---|---:|
| off | off | off | none | 12 |
| on | off | off | Leagues | 9 |
| off | on | off | Central | 6 |
| off | off | on | Caribbean | 9 |
| on | on | off | Leagues, Central | 3 |
| on | off | on | Leagues, Caribbean | 6 |
| off | on | on | Central, Caribbean | 3 |
| on | on | on | all three | 0 |

Every row still plans exactly 27 places, 22 Round One and five direct.
Champions Cup alone and Champions Cup with the [Caribbean Cup](caribbean.md)
can build. Leagues Cup and Central American Cup remain unavailable at Build.

## Mod Studio individual access (recipe v3)

The legacy sections above describe the v1 contract. Mod Studio uses recipe v3 for individual qualification. The three `modules` switches control the optional cups. Champions Cup is always listed and Build derives its inclusion from the validity and completeness of the access list. The old `champions_cup` switch is ignored on migration. Recipe v2 regional counts expand to positions 1 through N. Champions Cup assignments are retained. Conflicting positions are kept for review and prevent generation of the conflicting Champions Cup access. Explicit legacy Champions Cup league positions migrate to Round One for review. Previously implicit sources do not supply new places.

Cups ? Qualification uses the standard source and destination table. Every row selects one league position or the winner of an eligible domestic cup. A source position can appear only once across active destinations. Geographic exclusions from Champions Cup apply to automatic assignment only. Domestic Champions Cup requirements subtract only available regional feeders. The total remains five direct entrants and 22 Round One entrants. Incomplete cups are omitted from Build and their assignments stay editable. Leagues Cup has no editable qualification destination. Its annual field is fixed at 18 MLS clubs and 18 Liga MX clubs. All four competitions use the standard appearance fields.

**Auto-assign qualification places** runs against the current uncommitted Qualification draft. It keeps buildable regional allocations, tries to complete enabled regional cups from eligible league capacity, and replaces Champions Cup domestic access after confirmation when assignments already exist. An available Central American Cup or Caribbean Cup excludes that whole region from the domestic automatic assignment. Leagues Cup never adds editable qualification rows or excludes MLS or Liga MX. The proposal shows shortages and uses the ordinary Apply, Discard, Undo and Redo workflow. Build does not invoke automatic assignment.

The Championships use the existing formats and native screens. Central and Caribbean accept exactly 20 and 10 configured places. They advance through the ranking of the selected league when a duplicate must be skipped. Central supports up to seven selected leagues and uses its existing pot draw where the configured field supports it. If the league concentration exceeds the original grouping cap, four groups of five are still drawn from the same five pots. The new Central contract handles complete round-robin sources, annual sums and tiered phase layouts that can be represented by its existing four-phase limit.

Champions Cup preserves the 5/22 stage split. Enabled regional cups reserve their existing 3/6/3 places. Vacant configured places block generation, while duplicates can advance within the configured source at run time. The Champions Cup v3, Central American Cup v4 and Caribbean Cup v3 contracts name exact positions, or a cup linked to its domestic league. They reserve exact places and cascade overlaps within that league. Before a first verified cup result, the existing bootstrap window allows the domestic league order as a substitute. Later editions require a verified winner. Legacy contracts remain readable. A January draw before an enabled regional cup's inaugural result is skipped. The next January draw uses verified results if the edition completed. Domestic league entry order is available only through the existing first-season bootstrap check. Outside the first-career bootstrap window, an unfinished domestic cup route waits for its real winner.

V2 uses `cup_ids` for public and technical IDs. Leagues Cup's six group families and three knockout families are allocated rather than fixed at 700–708. `fl26join` receives the same IDs for rollback and rollover. The original contracts retain their old IDs and loaders. The GigaPack table check used an offline copy of 726 competitions and 1,268 regulations, with collisions across all nine old Leagues Cup base IDs. The combined generator allocated fresh families, including Leagues Cup masters 709–714 and knockout masters 715, 716 and 734. The 16-configuration regression exercises staged table generation, contract emission and pin reuse after disabling and re-enabling cups.

The integrated world still requires the matching FL27 Lua and native modules. The staged build and native harnesses do not replace live validation of the independent loaders, the combined inaugural draw and annual rollover with allocated IDs. The existing Leagues Cup split-calendar and September-recovery scenarios remain offline validations.

## Qualification policy (legacy v1)

* **Disabled module:** its quota and direct berth use domestic standings from that region.
* **Unavailable domestic pathway:** use the same regional replacement policy; an explicitly
  configured but unavailable source is a validation error rather than a silent substitution.
* **Enabled, incomplete result in later seasons:** raise `QualificationPending`; wait, retain
  the source and do not treat it as disabled.
* **Enabled, missing or invalid later result:** clear validation error requiring repair.
* **Bootstrap:** league entry order is available only before that source's first expected
  completion. The native calendar distinguishes January and July starts and calendar-year
  and August–May sources. Once a result is expected, a missing result blocks qualification.
  A missing Caribbean podium can be replaced only when the career had no opportunity to
  play the previous Caribbean edition.
* **Duplicate qualification:** advance through the relevant source's ranked eligible clubs,
  then use regional fallback if its ranking is exhausted. The same club never takes two places.

Fallback exhausts same-region leagues before other CONCACAF leagues. Within a region,
it considers rank one across leagues, then rank two, etc., with country and source id providing
a deterministic order. A club outside eligible domestic memberships is rejected. Completed
league results must include the whole current membership; enabled regional results must
contain at least their quota of eligible, unique clubs. Replacement rankings should include
additional finishers where available. The reference resolver conservatively requires completed
rankings for all leagues considered together in a regional fallback tier.

Each resolution starts with an empty used-club set. Current memberships and fresh completed
results can be supplied each season without modifying the plan. Known memberships are
deduplicated when checking capacity; unbuilt leagues contribute symbolic capacity until
club ids exist. Such capacity is provisional: actual qualification must still validate exactly
27 unique eligible clubs and fail if it cannot fill them. No partial or expanded field is valid.

## Migration and career safety

Explicit legacy target-13 positions are retained as preferred source/rank references within
their modern geographic quotas. A domestic cup rank zero becomes its cup-winner source.
Conflicting enabled-module assignments, repeated references, unavailable sources and quota
overflow fail for review instead of dropping places. Old recipes that explicitly assign more
than six Liga MX or five MLS places consequently need redistribution. A plan with saved
recipe settings retains those settings. In older plans without settings, former automatic MLS
padding cannot reliably be distinguished from explicit assignments: ambiguous padding is
not promoted into twelve new explicit berths. Review those recipes before eventual Build.

Primary pins under `cup_ids["ccup:FL_CONCACAF"]` are carried forward. The technical helper
uses `cup_ids["concacaf:FL_CCC_R1"]` through the shared allocator. Offline Build/rebuild tests
retain both identities, including after adding a league and its national cup.
Every modern plan carries `requires_new_career: true`; there is no safe in-place migration of
a career containing the old bracket. Build rejects old target-13 plans as well. Existing installed
legacy worlds can continue unchanged; this work neither inspects nor rewrites their saves.

## Generator and runtime

`mkconcacaf.generate()` copies the established mode-1 UEFA knockout (two legs except
the final), fixes its field to sixteen and clears the bronze-match bit. Other scoring rules
remain those of the established templates; this milestone verifies structure and progression,
not a complete sporting-rule audit. It rejects
an unexpected template instead of guessing. The helper uses CONMEBOL's
`mkeuropo.prerounds_single(..., one_match=False)` with eleven ties: master plus eleven
replicas, within the twenty-table limit. It does not change ordinary eight-tie preliminaries.
Static primary membership contains a preview of all 27 unique clubs; runtime selects anew.

`fl26concacaf.h` contains the bounded contract parser, pure qualifier resolver, match-pair
counter and strict handover validator. The adapter in `fl26swiss.c` retains five byes and
22 preliminary clubs in the existing profile-level checksummed state journal
(synthetic final-table key `0xfffd`). It registers the helper using the existing master-first,
replica-fallback path. Match ownership may be the master or replicas: every live record
is counted once by its actual two clubs. All eleven ties must each have exactly two
scheduled matches, no unplayed matches, and an actual game winner belonging to that
tie. Seeded/provisional winners are never used. The sixteen-team field is validated before
installation; five ties pair a bye with a winner, followed by three winner-versus-winner ties.

Completed domestic results are captured through the retained tables and cup-winner journal,
including before teardown. January qualification for later editions requires completed results
dated in the preceding calendar year. Live mid-season standings and strength seeds are not used.
Bootstrap can use entry order for a source that could not yet have finished. A January-start
career can enter its first February, while a July-start career enters the following February.
An incomplete used source waits;
missing later results produce an explicit qualification error. The season snapshot is
resolved against current domestic memberships: departed clubs are excluded, returning
clubs retain their completed relative ranking and promoted/new clubs follow in entry order.
This ordering supplies eligible replacements without treating a running season as final.
The snapshot drives registration and handover only during the edition's active window.
Completed results and participant views survive July until replacement by the following
January edition. Before the January draw, native teardown clears the previous edition.
The champion is retained separately and gains no defending-winner place.

### Career identity and journal limits

Both CONCACAF cups read the original ML start date from the native save block.
`fl26layout.h` finds the field from the initializer's relocated instruction.
The August-start value denotes a calendar initialized on July 1. This field
travels with the save, including Save As, and has no sporting-record expiry.
CONCACAF ignores legacy build markers, including conflicting markers for the same
club. An unreadable or unsupported native date blocks new qualification.

The sporting journal remains shared by the profile and keyed by club, regulation,
record kind and game date. It validates checksums, rejects rows dated after the loaded
game date, and excludes rows preceding the native career start. Those checks cannot
distinguish two branches or careers managing the same club when their dates overlap.
Same-day checkpoints and a later branch's records dated before the loaded checkpoint
can still collide. Use a separate profile with a matching journal for independent
careers or replay branches. Copying just the ML file preserves the start date and
can leave qualification pending when required sporting records are absent.

Build emits `ccup` (main calendar/lifecycle), `lpre` (helper/calendar) and
`concacaf 1 data=<comma-separated uint16 words>`. Generic filling of these two regulations
is intercepted by the dedicated engine; their legacy `entry=` lists are registry placeholders,
not alternative qualification instructions. The packed layout is documented alongside
`cq_parse()` in `fl26concacaf.h`: version/ids/dates, domestic source records and 27 place
records containing preferred source/rank references and regional fallback lists. It contains
no permanently qualified club ids. Source indexes are zero-based. Unknown versions,
truncation, invalid counts and unavailable source ids are rejected.

Lua checks `fl26_swiss_concacaf_version()` before installing hooks, then loads the contract
after cup/preliminary registration. Native acceptance requires the club-list, progression,
teardown and daily hooks. Build checks the packaged PE exports and ABI data without loading
the DLL; Switch on checks the installed DLL and Lua before changing the world or INI.
Required exports: `fl26_swiss_concacaf`, `fl26_swiss_concacaf_version`,
`fl26_swiss_concacaf_abi` (value 1). Old world files without this directive retain old behavior.

## Calendar and FL27 validation

The engine uses a fixed 365-day calendar. Qualification opens on January 2 (day 1)
and closes before Round One. Round One uses days 33/40 (3/10 February),
R16 61/68 (3/10 March), QF 89/96 (31 March/7 April), SF 117/124 (28 April/5 May), and
final day 145 (26 May). There are nine distinct dates with at least seven days between
rounds: **51 matches**, including one final and no bronze match. The main calendar assigns
all seven dates by knockout stage and leg.
All source/fallback domestic leagues reserve both preliminary days and seven main days
through the existing shared rest/calendar scheduler. This is static spacing and runtime
conflict avoidance, not proof that an arbitrary congested world has no fixture collisions.
Check actual domestic cups, league matches and any other continental commitments in game.
If handover misses the first R16 date, the runtime logs an error instead of dating it in the past.

Use `tools/native/build-swiss.sh <output DLL>` to regenerate the draw table and compile
with Zig. Where Zig is unavailable, the native README also permits a Windows x86-64
compiler with GCC-style assembly. Generate the same table with `tools/mkswiss.py` and
produce the DLL and its matching import library in an isolated build directory.

Keep rebuilt DLLs and import libraries in the local test output directory. The
tracked copies in `tools/native` and `sider/experimental` follow upstream/main.
`tools/lbpack.py` builds the DLL from source and pairs it with the Lua from this
checkout in the normal `modules.txt` load order. Import libraries stay in the
build output. Build and Switch on require the version-1 CONCACAF exports and
the 0.4.0 loader interfaces.

Mato confirmed that the public C source contains all 0.4.0 safeguards and that
building the public runtime from it is officially supported. The shipped native
DLL also exposes `fl26_swiss_wm_report`, `fl26_swiss_wm_state`, and
`fl26_swiss_wm_fail` as intentionally private entry points. The public runtime
requires none of them, and the Lua report probe is optional. The combined build
adds the Caribbean registry entry point and needs the matching Join teardown bridge.

For the next game test, install matching modules into a **separate FL27 test installation**,
build a new isolated world with all three modules false, activate through Switch on, and
start a new ML career. Never activate this structure over a legacy career. Preserve the Sider
log and the state journal belonging to the test save. Verify the contract-accepted line,
27 unique qualifier lines (five direct), 22 preliminary fixtures and their dates, no R16 after
first legs, the all-22-complete handover line, 16/8/4/1 main matches and a single final.
There must be 51 completed fixtures total. Reload before/after qualification and before/after
the last second leg; confirm no duplicate registration. Cross July, verify helper/main teardown,
champion retention and a fresh field derived from the next season's completed sources.
Check missing/incomplete-source errors and domestic collision logs. Competition Info exposes
Round One under CONCACAF Champions Cup through the qualifying-round page route. The technical
helper stays hidden. The Sider overlay reads the existing edition journal and pages through the
five direct entrants and the 22 Round One clubs. The presentation update can use an existing
career with the confirmed field and all 22 preliminary fixture records.
The observed August 2029 replay began from Pantoja's January 14 checkpoint, reloaded
on July 16 and retained the January 1, 2026 career start. The live table after
the Caribbean draw still contained all 29 completed Champions Cup knockout
fixtures and the journal's champion matched the live final. This replay
did not exercise the next January rollover or simultaneous careers sharing one
profile. No external results archive ships with these cups.

## Tests

Run `python -m unittest discover -s tools -p 'test_concacaf*.py'`. Set `CONCACAF_TEST_BASE`
to a folder containing the game's tables to include actual recipe planning and round trips
for all eight combinations, plus isolated table generation and fake-game Build/rebuild tests.
Set `CONCACAF_TEST_DLL` to the compiled DLL to include compatibility/build tests.
`tools/native/test_concacaf.c` exercises strict completion, winners, match counting, duplicate
rejection, contract bounds and season resets without any game pointers.
Also run the existing `test_pinned_ids.py` and `test_conmebol_modern.py` with that database
path. The latter builds unrelated CONMEBOL worlds in a temporary fake game directory.

## Cups and Qualification integration

For the January draw, the runtime prefers a completed domestic ranking
from the preceding calendar year. Capture includes the full August–May
fixture set when it finishes in spring. Bootstrap is evaluated per league
against its first expected completion, so a calendar-year source can supply
results while an August–May source from the same career still uses entry
order. Once the league's first finish is expected, missing results leave
qualification pending.

Champions Cup winner retention requires the edition's valid 27-club field
and a played single-leg final on its configured date. The winner is kept
with the final's date. The generic continental winner scan skips this cup.

The Cups catalog reports the fixed 27-club format. Qualification retains stored
target-13 assignments and the `concacaf` recipe object, and leaves generic cup-size
presets unavailable for this competition. The standings strip skips the dedicated
runtime entries because their placeholder ranks describe fixture shape.

The Caribbean Cup setting is available under CONCACAF in Cups, and Qualification
shows its January advancement routes. Future Leagues Cup and Central American Cup
entries should have independent settings. Qualification should
surface their regional eligibility and advancement rules through the same draft
and validation flow as domestic sources. First Season should show which places use
completed results and which use domestic entry order. After the first edition,
season-scoped result providers should deliver each feeder's ordered finishers to
the planner. Leagues Cup draws from MLS and Liga MX; Central American Cup and
Caribbean Cup draw from their respective associations. Keep regional redistribution
and overlap handling in the shared CONCACAF resolver.

## Central American Cup validation

| Phase | Live result |
| --- | --- |
| 1 | The fixed 20-club field played all 58 native fixtures. The quarterfinals, semifinals, two independent play-ins and final produced native sporting results. July rollover closed all nine prior-edition regulation rows and opened the next edition. |
| 2A | The July 2027 draw selected 20 clubs from completed annual rankings in seven associations, in quotas of 4/4/3/3/3/2/1. Save and reload reproduced the entrants and groups. |
| 2B | The 2026 edition produced one verified sporting journal publication with six actual finishers. After reload, the 2027 Champions Cup put the champion among five Round of 16 byes and the other five among 22 Round One entrants, with 27 unique clubs overall. The 51-fixture completion and July retention audits passed. |

The live runs used ordinary domestic league sources. Split and Apertura/Clausura
sources, optional national cup berths, combined Central American and Caribbean
feeders, and reallocation with Central America disabled have offline coverage
only. Each phase used an isolated profile. The Phase 2B profile was restored
and the live evidence was archived.

## Central American Cup Phase 2A

The isolated prototype's `central_probe 2` contract uses seven association records in quota order: Costa Rica (4), Guatemala (4), Honduras (3), El Salvador (3), Panama (3), Nicaragua (2), and Belize (1). Each record names the current membership regulation, calendar type, optional national cup regulation, and up to four fixture phases with their expected team and leg counts. A zero record means the association has no configured source.

Qualification uses the latest completed annual league result available at the in-game July draw. Each phase must have its full round robin, with every expected pair and leg played. Apertura and Clausura contribute to the combined annual ranking. Split groups retain their tier order and use the native table when available. The final domestic rankings use the existing retained-results store and are intersected with current top-division membership. Promoted clubs become eligible for league berths after earning an annual top-division rank. Entry order can supply an association only if the existing CONCACAF career-start rules show that a completed annual result cannot yet be expected.

A national cup berth requires an explicit source regulation and counts toward the association quota. A verified winner takes that place and the league fills the remaining places in annual order, skipping duplicates. Unavailable quota places go one at a time to the least represented eligible association, with ties broken in contract order. An association can supply at most eight clubs.

National cup capture checks the live regulation's bronze rule and the
terminal bracket slot. Depending on the layout the final can use stage 53
or 54. With a bronze tie, only stage 53 can supply the title. The final must
be fully played and its score must agree with the native winner for that
regulation. Ambiguous or incomplete results supply no cup berth.

The five pots use domestic rank, association order, and club ID. The deterministic draw places one club from every pot in each group and caps every association at two clubs per group. These are Mod Studio approximations for participant qualification and seeding. The real 2026 draw used the Concacaf Club Ranking. [Official 2026 draw procedures](https://www.concacaf.com/news/concacaf-reveals-date-and-procedures-for-2026-central-american-cup-draw)

For a well-formed 20-club field, eight clubs per association is the exact feasibility bound for any five pots of four. Split each association's clubs into two sets of at most four. Connect each club's pot to its association set with one edge. The resulting bipartite multigraph has maximum degree four, so a four-color edge coloring assigns one club per pot and at most two per association to each group.

The Phase 2A world builder's `--dynamic` option creates an offline overlay. It uses ordinary leagues to exercise both calendars. Split, Apertura/Clausura and optional national cup configurations have offline contract and ranking coverage. If native records for an early phase are already gone and no verified annual ranking was retained, qualification blocks. The standalone validation package uses profile `20271130` and the Phase 1 package uses `20271129`. If both routes resolve to the same Documents folder, the launcher verifies the Phase 1 transaction, parks its isolated test root, and restores it with a SHA-256 inventory check. The production backup stays in the Phase 1 vault.

Use Alajuelense for the July 2026 bootstrap and replay. Use a separate January 2026 career with CA Independiente for an all-sporting July 2027 draw. A July 2026 career can still be within the legitimate bootstrap window for Panama in July 2027 because its first full calendar season is 2027. Restore and prepare a clean isolated root when changing careers so each career has its own retained results. Audit the pre-draw state and compare the qualification trace and exact groups before the first group fixture.

## Central American Cup Phase 2B

After the second leg of the December final, the dynamic cup validates all 58 played
fixtures and traces the bracket through the quarterfinals, semifinals, final and
both play-ins. It publishes six ordered finishers to `fl26swiss-state.bin`
using the same final-table journal record as the Caribbean podium.

The existing `FL26SST1` header and 176-byte records keep their layout. The Central
record uses kind 0 and key `0xa000 | knockout_reg`. The completion date identifies
the edition year and must be its final's second-leg date. A complete record has
six unique club handles, with the team ID in the upper bits, ordered as champion,
runner-up, losing semifinalists in bracket order, and play-in winners in tie
order. The record includes the managed club and the existing FNV-1a checksum.
The journal appends completed editions and suppresses identical records. Its
existing date window governs runtime lookup.

The January Champions Cup draw uses the preceding year's Central American Cup.
It corroborates the six finishers against the loaded career's native bracket
before using the result or accepting its slots in a retained Champions Cup
field. A valid native bracket can recreate a missing or damaged journal row.
When the expected bracket is missing or incomplete, the draw waits. When the
career began after the preceding feeder draw, the first Champions Cup uses
the existing deterministic reallocation. Disabled feeders use that same
reallocation path. The champion occupies one of five byes and the remaining
five occupy Round One places. Domestic routes skip clubs already reserved for
the regional cups. A club appearing in guaranteed places from both regional
cups blocks the draw so both sporting commitments remain intact.

The journal is shared by the profile and does not identify a career branch.
Careers with the same managed club and overlapping dates can still collide
in domestic rankings or Caribbean records. The Central American handover
verifies its six finishers against the loaded career's native bracket before
using them. This check does not change the lineage rules for other records.
Keep one career and its journal per isolated profile.

For live validation, build a separate world with `tools/central_probe.py --dynamic
--champions-plan <plan.json>`. Supply the CONCACAF plan object with Central
America enabled, Leagues Cup disabled, and domestic regulation IDs present in
the input database. If enabling the Caribbean Cup, include its domestic
sources in that database and their scheduling metadata in the validation
world. Package to a new directory with `--phase2b-world`, which selects profile
`20271131`. Use the existing account and the shared isolation launcher with
`-Profile 20271131`. Verify the native save route before starting FL27.
The launcher checks both known Documents roots for profile collisions and
preserves the original root or a verified Phase 1 transaction if they share
the same Documents route.

1. Keep a checkpoint before the second leg of the Central American final.
   Verify that the sporting journal has no completed record for that edition.
2. Complete the final and compare the six published club IDs with native
   tie results. Reload the completed checkpoint and compare the journal
   and qualification trace for duplicate publication or changed placements.
3. Advance to the following January. Check the five direct and 22 Round One
   entries against the published result. Verify all 27 are unique, the champion
   is direct, and the five other Central finishers are in Round One.
4. Reload before and after January qualification, then complete the Champions
   Cup and confirm the 51-match structure. Advance through July and verify
   journal retention and that the following January uses only its own preceding
   Central edition.
5. Repeat the scoped handover with the Caribbean Cup enabled on an independent
   test profile. Compare its three sporting slots and verify deterministic
   fallback in a Central-disabled control.

## Leagues Cup Phase 1 mechanics prototype

For the current runtime and both completed editions, see the
[20271146 live validation](leagues-cup-ui-validation.md#validación-de-dos-ediciones-en-el-perfil-20271146).
The prototype notes below describe earlier packages.

Live `20271141` confirmed the MLS headline, all 18 scrollable rows and the
cutoff after fourth place. The Sider log recorded zero matches, two 18-row
tables, and no successful shoulder switch. The input dispatcher checks
virtual slot `+0x230` for actions 6 and 7 before it invokes the two shoulder
callbacks. The scrolling revision now installs captions through the native
footer setter and reads those two presses through FL27's mode-2 input query
even if the scrolling list resets its action modes. The other controls keep
their original handler. The movement-arrow gate is disabled at the scrolling
initializer call for Leagues Cup rows only. The participant preview's source
is separate from the standings snapshot and still needs to be identified.

Live `20271140` confirmed two groups and L1/R1 selection. Both providers
returned 18 rows, but only eight could be reached through the grouped layout.
The next source revision uses the Champions League scrolling controller
(`0x140aed610`, initializer `0x140aeda10`) and `rankingTeam.bin` for this cup.
Its private vtable binds both shoulder actions to changing the regulation and
rebinding the already allocated native list. This keeps two cohorts and a
single Competition Info entry. The scrolling provider also supplies the
previous-row area at `+0x3c4` and display flags at `+0x78c` read by this
controller. No historical ranks are inferred. The existing `flZone` widget,
when available in the native layout, marks positions 1–4.

Leagues Cup preserves the stock Rules item when present. Native scorer and
assist pools have 40 rows per regulation/season, and the UEFA carry helper
truncates on every merge. Activation requires confirming how masters and
replicas share or duplicate these records, and gathering a single edition
without losing players below a per-stage cutoff. Individual awards and the
team of the season have a separate validity gate and need equivalent evidence
for their pools. The revision keeps these four public paths hidden pending
that work. It does not use a partial per-master ranking to populate them.

Package `groups-crash-fix-validation-20271140` corrects the startup failure
observed in `20271139`. The dump for PID 25472 recorded `0xc0000409`, fast-fail
parameter 7, and FL27's return address `0x140af6237`. Its caller locals held
competition 768 and a zeroed regulations vector. At `0x140af6228` the grouped
controller requires at least one regulation. At `0x140af6231` it calls the CRT
failure handler if the vector is empty. This happens before row decoding.

Both grouped-controller calls now get the two phase keys even if a snapshot
is unavailable. The vector uses the game's own allocation and the row provider
uses DLL-owned storage. The inaugural roster can be validated against the
canonical team records from January, independently of the July scheduling
tick. If the snapshot fails validation, the regular controller receives two
valid group keys and zero rows. Release validation should open Group Stage
before the draw, check both 18-club cohorts and zero points, and repeat after
the draw. To inspect a new crash offline, run `python -B tools/leagues_crash_audit.py
<minidump>` and capture its JSON alongside the matching Sider log and WER
report. The JSON lists candidate return addresses and identifies the known
group-vector fail-fast with its recorded locals when present.

The experimental `groups-calendar-validation-20271139` package supersedes the
public page layout described below. It exposes Group Stage and a disabled
Knockout Stage entry while the connected bracket remains under investigation.
Group Stage supplies both 18-row tables through the native grouped controller.
The two real replica IDs of the primary master are lookup keys for presentation
only. A field confirmation for the current career timeline and year unlocks
the tables even with zero fixtures. A partial or invalid fixture set still
fails the existing integrity checks. Public Phase One fixture pages were removed.

The `20271138` log reports a failed July 31 allocation. Each of the three
masters for one cohort had only two admissible dates in August 4–28. The
allocator already enumerates every ordered triple and checks shared-date
capacity, so that calendar could not satisfy the three-match requirement.
The next package allows August 1–31 and clips the lower bound to dates after
registration day. The minimum rest, native day capacity, atomic registration
and rollback remain enforced. Failure logs now include each master's legal
date mask. Offline tests reproduce the logged domain counts with synthetic
dates, exercise a recoverable boundary case and retain a case with no solution.
The exact date domains of the failed career were unavailable. A live draw is
required to establish whether the wider window admits that calendar.

The inaugural 2026 edition was verified in FL27 with all 62 fixtures,
knockout progression, a persisted podium and a cold restart. That evidence
belongs to the standalone profile 20271135.

The combined validation builder accepts `--annual --champions` with
`--domestic-world` and `--knockouts`. It keeps the inaugural field and
uses both completed MLS phases for the following year's ranking. It
requires 18 current Liga MX members, a complete prior edition before
teardown, and a unique field proof for a later edition on reload.
Champions Cup validates the prior cup's complete native bracket before
accepting the podium. Journal reuse still has the existing same-club,
same-start-date career identity limitation. Use dedicated profiles.

The native Competition Info adapter keeps the primary Leagues Cup entry
in the category. Phase One has two native scrolling standings items, MLS
and Liga MX, and one native fixtures-and-results item. It uses Matozanato's
standings factory redirect and qualifying-page flow. The three knockout
fixture items appear as their fixtures become available.

In the FL27 executable, the call returning at `0x141542354` passes one
regulation to `0x141541480`. This is the fixture page path. The scrolling
standings controller (`0x140aed610`) reads a standings table for one
regulation through `0x141579b90` at `0x140aedd37`, then reads rows again
from two other calls during row rendering. The native Group Stage path
at `0x140af5837` and `0x140af6213` accepts a vector of regulations and
dereferences real records for group navigation. The adapter instead
selects one cohort per native scrolling controller and intercepts its
three table calls. The two DLL-owned buffers hold 18 ranked rows each,
using the canonical club handle, explicit rank at `+4`, packed stats
at `+8`, and goals and matches played at `+12`. A fresh scan of all
54 Phase One fixtures populates both buffers when the menu opens.
The UI counts a penalty decision as a regulation-time draw and shows
the sporting points from the validated scorer. The career timeline and
edition guard access to the buffers. When the fixture page is selected,
the call at `0x14154236a` appends all six batches to the game's own vector.
Both paths use registered regulation IDs and leave game records intact.

The bracket factory (`0x140af9810`) chooses its layout from a single
record and later derives placements from the entry list. Appending
regulations to the factory's type-3 vector alone would still give the
factory its first entry at `0x140af9933`. A virtual bracket needs a
presentation-specific record and downstream match resolution for its
round slots. The factory's `0x140af9a50` check scans the global regulation
array directly, before the subsequent record getter. A getter override
alone would leave a virtual ID invisible to that check. The small-bracket
constructor `0x140b32a20` rereads the Competition Info selection, asks for
the phase vector again at `0x140b32bb8`, then uses both regulation getters
at `0x140b32c39` and `0x140b32c4f`. A factory-only proxy would therefore
also be lost at construction time. The adapter exposes three native fixture
pages for those rounds. A live comparison needs snapshots with the
Leagues Cup knockout pages open and a working multi-round native bracket
open, including its selection, bracket regulation and replica records.
The read-only `tools/leagues_live_audit.ps1` collector can capture these
with `-CompetitionInfo` alongside the fixtures, derived standings and
runtime log. A collector run must target a game process already started
manually from the specified isolated package. The builder accepts
`--logo` for supplied official artwork. The existing package uses a
competition-specific fallback. Scrolling, competition identity and
emblem rendering, and all 54 fixture displays require live verification.

Validate the combined package in a separate career. Check the 2027
Champions Cup's three Leagues Cup places in January, then check the MLS
ranking, Liga MX membership, schedule and stale-fixture removal in July.
The all-eight feeder matrix is offline resolver coverage; the combined
package enables Leagues Cup and leaves the other two optional feeders off.

The opt-in `leagues_probe 1` contract owns a fixed 2026 field and six blocks of
nine interleague fixtures. It uses the native single-match qualifying template
for every fixture. The sparse UEFA league generator demonstrated that the
engine can emit selected pairings, but its league path has no verified
shootout behavior. The single-match template gives this prototype a native
tie-deciding path. All owned rows enable penalties and clear extra time.
The runtime checks the loaded rules before start.

Each block has one master and nine tie replicas, under its own technical
competition ID. This uses 60 regulation rows, six competition IDs and a
target of 54 match records. Registration runs July 31 through August 3.
August 6, 13 and 20 are preferred dates. Each master receives its own
date in the configured August window (August 4–28 by default).
The original August 9 batch overlapped MLS Second Round (regulation 167).
The July build also exposed Austin FC's August 15 US Open Cup fixture
(regulation 54), which blocked the fixed August 13 batch.

The allocator reads native match demand and calendar load after the daily
fixture producers. It excludes dates within two days of a participant's
match, reserves observed US Open Cup dates and accounts for unresolved
records from relevant competitions. It searches all legal three-round
sequences for the two disjoint cohorts and scores their combinations by
date preference and load. Each combination respects cumulative daily
capacity, including masters sharing a date. It publishes no rows until
it has a complete assignment. The native paths then verify all 54
matches and their day-list entries or invoke exact-ID teardown and verify
cleanup. Save reload reconstructs the master dates from the native records.

The expanded isolated package builds an 18-club Liga MX using the normal
Mod Studio Apertura/Clausura generator, with eight-club playoffs in each
half. MLS retains its shipped two-phase structure. The validation overlay
preserves all 18 Mexican entrants, including Atlante. No separate Mexican
domestic cup is enabled in that package.

The zero-added-league path installs the native teardown trampoline without
installing league registration or promotion hooks. Worlds with added
leagues still initialize the full join path. Both require the rollback
bridge to be ready before cup registration can start.

Phase One standings rank by points, regulation goal difference,
regulation goals scored, regulation wins, then ascending club ID. The
club ID is the deterministic final tiebreak. Same-association teams
cannot meet in Phase One. The three technical knockout masters register
four cross-league quarterfinals (MLS 1 vs Liga MX 4, and so on), two
semifinals, and two placement games. Both semifinal losers play bronze.
All eight eliminations validate the same regulation and penalty score
bytes as Phase One. The sporting journal records the champion, runner-up
and bronze winner. The Champions Cup provider reserves their three rights
and requires the complete bracket of the loaded career as proof.

A later fixture producer can still create a conflict without exposing
its dates beforehand. The runtime and auditor report a materialized late
conflict and block validation. They do not move an existing match. This
expanded world includes Liga MX, but the native calendar and knockout
registration still require live acceptance. The fixed inaugural field
stays pinned to 2026 in the original mechanics package. The opt-in
annual contract is exercised only in the separate combined package.
The Mod Studio checkbox and the fully native unified competition page
remain gated.
Two nine-club waves per league each play three different opponents. This is
a compact mechanics schedule inside the official window, with three full
rest days between a club's tournament fixtures. It does not reproduce the
official pairings, geographic tiers, kickoffs or venues. A same-day clash
with an existing native fixture for either club blocks registration. A later
clash with a fixture generated after registration invalidates the audit.
The prototype never moves domestic fixtures.

Only the 2026 edition is armed. Existing fixtures prevent duplicate
registration. A partial or inconsistent native schedule withholds the
tables and should be diagnosed from a fresh isolated checkpoint. Both
18-club tables are rebuilt from the native match records after reload. The
regulation score counts toward goals for, goals against and goal difference.
The separate native penalty score determines which club receives two points
instead of one. Tied regulation scores without a valid shootout are rejected.
Knockout progression, final tournament tiebreaks and podium publication are
outside this phase.

### Isolated world and manual acceptance

Build an overlay with `tools/leagues_probe.py build`. Supply `--base` with
the archived Phase 2B PESDB for the verified clubs and squads, `--stock`
with the extracted stock FL27 PESDB for the competition tables, `--metadata`
with the archived FL27 world contract for the database dimensions, and
`--output` with a new directory. The output includes an `edition.json`
inventory. Place the overlay and a newly compiled runtime in a separately
verified FL27 clone. Use a fresh, verified unused profile and the same
save-route and checksum checks as the Central prototype. Place the generated
world file in both its livecpk overlay and Sider's modules directory. This
overlay is a build input for a validation package.

Start a fresh 2026 career with a fixed-field MLS club before July 31. At
registration, audit the exact 54 records with `tools/leagues_probe.py audit
--pid <package-pid> --exe <isolated-FL_2027.exe> --edition <edition.json>`.
Play one match to a level regulation score and simulate another tied match.
Check that each moves directly to penalties. Audit both fixture score
tuples and the separate points tables before and after a full restart and
reload. Finish the phase and compare the 54 played results and both tables.
A missing shootout, extra time, bad fixture count, overlap or changed saved
score blocks progression to Phase 2. These are manual acceptance gates.

### Competition Info presentation in the original Phase 1 package

Phase 1 disables the native Group Stage menu entry for Leagues Cup
containers. Their replica regulations are single-match ties and do not
provide standings tables. The six scheduling masters remain visible in
this validation package.

For a unified presentation, keep the six masters and give Competition
Info one public competition ID and one name and logo. The existing
category and phase adapters provide display-only interception points.
The category adapter currently hides tie replicas. It cannot consolidate
masters across separate competition IDs on its own. The menu and page
redirectors select one native regulation at a time. Two 18-club standings
pages and an aggregate match list need a dedicated display adapter backed
by the validated Phase One results, plus an audit of name and logo
lookups from the calendar, results and Competition Info. Test those
paths separately from the scheduler and keep all match ownership on
the technical regulations. Add the knockout bracket with Phase 2.

### Approved Phase 3 qualification

Career qualification will select the top 18 MLS clubs from the most recent
eligible completed **annual** league standings and all 18 clubs from the
configured Liga MX top division. This intentionally approximates the real
MLS conference selection. It requires no conference data. Split and
Apertura/Clausura sources must prove their complete annual rankings.
Incomplete tables, individual half-season winners and playoff finalists
cannot replace annual rankings. First-career entry order may be used only
when an eligible completed season could not yet exist since career creation.
Phase 1 uses the fixed field exclusively.
