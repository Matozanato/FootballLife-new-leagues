# Continental Qualification

Current entry point: MY WORLD > CUPS > CONTINENTAL > QUALIFICATION. Select the
confederation above the subtabs. UEFA Ranking and First-season clubs are tools
inside UEFA > Qualification; South American places and association allocations
are inside CONMEBOL > Qualification. These entries are no longer in LEAGUES > MORE.

The approved Competitions layout and CUPS header are unchanged. Qualification is
created on first use. Its source metadata and the first-season club pool are read
in workers and cached against database-file stamps. Workers check recipe identity,
base path and request generation before updating a widget.

## Data and drafts

`qualification_data.py` adapts existing backend metadata into immutable `Source`
records. The identifier is a recipe key, not an assumed country/regulation mapping.
There is no new persistent qualification schema:

* original leagues: `game_europe[regulation]`;
* added top divisions: the existing league's `europe`;
* eligible associations: `conmebol_associations[country-or-existing-alias]`;
* UEFA ordering: `uefa_rank`, `uefa_off`, `uefa_seed`;
* first season: `europe_first.ucl/uel/uecl`.

Each small field has a presence/value pair and an original-value fingerprint in
ContinentalEditor's existing draft. Previews shallow-copy only touched branches;
players and rosters are never deep-copied. Apply validates conflicts, then patches
these fields in one Project.touch operation. Discard reads the current project.
World-specific draft archival, autosave and Undo/Redo use the existing Cups page.
Legacy navigation opens the same integrated editor instead of mutating a project
through a second modal editing session. Old dialog classes remain available for
compatibility.

EuropeTable is shared with Edit League. Its opt-in `preserve_legacy` mode displays
old invalid positions and inactive destination IDs without clamping or substituting
them. Newly added rows use only supported destinations. Global completeness is
diagnostic while editing; local invalid positions prevent Apply.

## Presets

The preview dialog contains a checkable, reorderable source ranking and current
versus proposed rows. Confirmation changes only the CUPS draft. Cancel is pure.
The context is rechecked after the modal preview; concurrent edits invalidate the
proposal rather than overwriting them.

UEFA delegates ranking and assignment to `uefakey.ranked/apply`. The optional
preloaded candidates parameter avoids another database scan; the access algorithm
is unchanged. Conference places are not newly assigned while disabled, and saved
inactive places remain stored.

CONMEBOL now uses the fixed association action documented below. Its toolbar
never opens the ranking dialog or calls the ranking generator. The older pure
ranking helper remains internal compatibility code, not an exposed CONMEBOL tool.

Other confederations use the same workflow for backend-generated cups with an
explicit supported allocation size. AFC native destination 5 is retained, not
recreated by an invented Elite access list. Existing native/default filler may
enlarge a generated field; Check Current Competition Plan remains authoritative.

## Existing engine limitations

The native `game_europe()` replacement marker is created only when an override
touches a native destination. Empty or generated-cup-only overrides retain native
access. The editor explains and counts this; it cannot promise that excluding an
original source removes native places. No engine behavior was changed to hide this
limitation. Original Libertadores details include executable-managed access which
cannot always be represented as fixed league positions.

Modern mode disables native South American Libertadores access and requires the
complete package. With modern mode off, saved Sudamericana allocations are inactive
and no Sudamericana or Recopa is generated. Retiring classic Sudamericana
generation is an intentional backend behavior change in this branch, not only
a UI migration; stored historical allocations and the obsolete calendar setting
remain compatible and are not silently deleted.
Legacy destinations are retained, diagnosed and removed only by explicit action.
Saved association allocations in a now-playable country are reviewable through the
same detail editor, not listed as a new league-less source.

## First-season editor

The integrated view has a searchable multiselect club pool and three competition
tabs. It preserves exact saved references and ordering, identifies aliases by actual
team identity, enforces the backend FIRST_MAX and reserves inactive UECL selections.
Unknown saved references remain visibly marked until explicitly removed. This
feature controls initial career participants, never subsequent-season access.

## Verification

Run `python tools/test_qualification.py`; optionally append
`--tables <pesdb directory>` for actual source mappings and read-only B.plan
validation of modern/classic CONMEBOL. No full world build is needed. Qt fixtures
use deterministic source metadata but real europe_problems, europe_first and UEFA
ranking functions. Full-window geometry tests cover 1400x900, 1366x768 and 1080x640.
Repeat under QT_SCALE_FACTOR=1, 1.25 and 1.5. Existing CUPS, BUILD, navigation and
ranking suites protect the previously approved UI and refresh optimization.

Local verification: 127 qualification assertions with real tables, including
modern CONMEBOL and UEFA preset B.plan validation. The 121 fixture/Qt assertions
also pass at 125% and 150% scaling in Spanish. Rendered geometry retains a 9px
external gap and the original header button dimensions. All three window sizes
have no outer scrollbar in the normal Qualification and first-season views.

The read-only 86-league navigation benchmark measured median CUPS reopen times
of 10.087ms in Competitions and 12.287ms with Qualification active. Qualification's
initial metadata load completed in 146.313ms in its worker; the pre-existing
domestic table construction remains part of the first CUPS initialization.

## Qualification UX and removed-source recovery

`pages/qualification_presentation.py` is read-only presentation. Its structured
preset comparison uses the unchanged proposal, compares assignments by source
position, labels cup winners and association ranks, and sorts changed sources
first. Unchanged sources can be revealed. Numeric destinations and raw rows remain
in a collapsed technical section. Overview tables share the existing aggregation
through `qualification_data.allocation_counts` and use the same `W.europe_count`
direct-room calculation. Automatic UEFA fillers are informational, not missing
user allocations. Modern CONMEBOL displays its five manual capacities; F3 remains
technical information only. Long explanations use the existing Fold widget.

Qualification alone has an 8px external top inset; it does not alter the main
9px gap, Competition layout, fonts or header actions.

The local errors.log identified a `StopIteration` when a pending qualification
draft referenced a deleted league. It interrupted both confederation switching
and page refresh, leaving old lists/details and a blank exception banner.
Read-only previews now omit missing draft targets without deleting their pending
values or recreating a league. Apply explicitly blocks unresolved removed-source
drafts; Undo recovers them, or a dedicated action discards only those drafts.
All valid edits remain pending. Deleted sources are removed immediately while
background metadata refresh completes. Genuine exceptions are not suppressed.

`test_qualification_ux.py` covers removal, Undo/Redo, confederation synchronization,
banner recovery, human-readable previews and counters. Proposal fingerprints were
captured before this UX work for all six fixture confederations. They protect
existing preset output without changing or examining country-specific mappings.

UX verification: 57 focused assertions and 124 existing qualification assertions
pass at 100%, 125% and 150% Qt scaling. The full production window retains the
8px subtab-to-tools gap and 9px main-tab gap at all three tested sizes. The
86-league read-only benchmark reopened active Qualification in a median 16.579ms
(Settings: 22.065ms in the same run); unchanged-navigation work-count tests still
report no editor reconstruction or repeated catalog parsing.

## Fixed CONMEBOL automatic allocation

UEFA's toolbar contains only Ranking, First-season clubs and Check plan. UEFA's
algorithm is unchanged. CONMEBOL contains Auto set continental places and Check
plan. AFC/CAF/CONCACAF/OFC retain their existing preset workflow.

`conmebol_allocation.py` is a UI proposal generator, not a competition engine.
It requires modern mode and exactly one valid playable top division per required
country. Original country/cup metadata comes from the existing database readers;
friendly competitions are filtered using `friendly_cids`. New sources use their
actual country mapping and the backend club-count/season bounds. Lower divisions,
exhibitions and unassigned groups do not satisfy the gate. Duplicate native/own
or own/own top divisions are reported rather than silently prioritized.

| Country | Lib groups | F2 | F1 | Suda groups | First stage | Cup destination |
|---|---:|---:|---:|---:|---:|---|
| Brazil | 5 | 2 | 0 | 6 | 0 | Lib groups |
| Argentina | 5 | 1 | 0 | 6 | 0 | Lib groups |
| Chile | 2 | 2 | 0 | 0 | 4 | F2 |
| Colombia | 2 | 2 | 0 | 0 | 4 | F2 |
| Uruguay | 2 | 1 | 1 | 0 | 4 | Suda first stage |
| Paraguay | 2 | 1 | 1 | 0 | 4 | F1 |
| Peru | 2 | 1 | 1 | 0 | 4 | Suda first stage |
| Ecuador | 2 | 1 | 1 | 0 | 4 | F1 |
| Bolivia | 2 | 1 | 1 | 0 | 4 | F2 |
| Venezuela | 2 | 1 | 1 | 0 | 4 | F1 |
| Total | 26 | 13 | 6 | 12 | 32 | One per supported domestic cup |

The country-specific cup column is a deterministic template policy within the
requested quotas, not a claim of official rights stored in the database. The
engine stores cup existence and supports zero-position access, not official
rights for every real or newly generated national cup. Brazil/Argentina use one
group berth, Chile/Colombia/Bolivia one F2 berth, Ecuador/Paraguay/Venezuela one F1
berth, and Peru/Uruguay one Sudamericana first-stage berth. No extra target or
competition is introduced.

With a supported national cup, one quota berth is represented as position 0.
The other berths use consecutive positive positions in destination order
3/17/16/9/19; zero is stored last, matching EuropeTable ordering. Without a cup,
the same berth uses the next league position. Original cups use `home_cup` metadata;
new cups use the existing `cup` flag and pure `national_cup` shape validator.
There must be at least as many distinct clubs as total quota berths, even when
one berth is a cup winner. The existing backend/DLL same-source cascade resolves
an already-qualified cup winner; the UI does not implement another cascade.

Missing countries, ambiguity, insufficient capacity, incompatible historical
rows or conflicting unrelated places abort with no mutation. Existing
`conmebol_associations` require explicit manual review; the action never replaces
them, uses them as substitutes, or removes them to force totals. This restriction
is local to the automatic action: manual association editing and general Build
remain unchanged. Nonoverlapping unrelated access rows are preserved.

All ten patches are validated with `europe_problems`, existing draft validation
and the global modern capacities before one batch enters the shared draft.
No Project.touch/save/Build happens until normal Apply. Repeating the action is
idempotent. Calculation uses a worker and a small source/access snapshot; stale
results after source edits, table changes or world switching are refused.

Run `python tools/test_conmebol_auto_allocation.py [--tables <pesdb>]`. The optional
integration checks the actual four original plus six added divisions via B.plan,
including cup-winner stage fallback sources. It never performs a full world Build.
Local validation: 71 checks including the actual-table plan, plus 69 fixture/UI
checks at 125% and 150%. Existing Qualification (124), Qualification UX (57),
CUPS, BUILD, UEFA and navigation suites pass without changing their algorithms.

## Dedicated UEFA Ranking presentation

The UEFA toolbar opens `UefaRankingDialog`, not the generic `PresetDialog`.
Both share `RankingPreviewDialog` calculations and draft confirmation, so UEFA
still delegates unchanged to the existing ranking/access/seeding functions.
The UEFA tool has its own title, instructions, association filter, summary and
Apply UEFA ranking to draft action. Optional technical details show the current
and proposed association order, exclusions and seeding as well as qualification.

All qualification comparison previews explain the unchanged orange difference
color with a compact legend. The CONMEBOL checkbox label is now exactly
"Enable Libertadores new format, Sudamericana and Recopa Sudamericana"; only
the display label changed, not its conmebol key or behavior. No selector-layout
changes are required at the supported widths, including Spanish localization.
`test_uefa_ranking_ui.py` passes 27 checks at 100%, 125% and 150% scaling,
including exact equivalence to uefakey and preservation of CONMEBOL Auto Set.
