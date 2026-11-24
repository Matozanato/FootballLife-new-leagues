# CONCACAF Caribbean Cup

The optional FL27 module is off by default. Enable it from Cups under CONCACAF.
It uses the Champions Cup recipe and adds one competition ID and four
regulation rows. The other regional modules remain unavailable.

The combined loader validates the Caribbean contract while registering the
continental cup list. Only the exact group and knockout pair in that
contract may register two groups of five. Other group cups still require
four clubs per group. The Champions Cup contract loads after the registry
and its Round One rows have both been registered.

Two five-club groups play one leg on five matchdays. The bye is implicit in
the fixture grid. There are ten real fixtures per group. Group winners host
the return legs of the cross-group semifinals. The native four-club bracket
uses stage 46 for both semifinals, stage 53 for the final and stage 54 for
third place. All are two-legged, making 28 fixtures without a helper cup.

| Stage | Dates |
|---|---|
| Domestic selection | July 28 to August 4 |
| Groups | August 5 and 19, September 2, 9 and 16 |
| Semifinals | October 14 and 21 |
| Final and third place | December 1 and 5 |

The scheduler reserves all nine dates for eligible domestic leagues and
their registered split phases. Live conflicts depend on the domestic
calendar, especially externally supplied domestic cups.

The base distribution is Jamaica 2, Dominican Republic 2, Trinidad and Tobago
2, Haiti 1 and Suriname 1. The two CFU places and unavailable domestic places
are redirected one per association per pass, starting with the lowest number
of allocated places. Equal counts use the listed association order. A club
already selected is skipped. An optional ordered concacaf.caribbean_associations
list adds explicitly configured Caribbean top divisions with zero base quota.

Jamaica, Trinidad and Tobago and Suriname use completed league rankings.
The optional concacaf.caribbean_titles object maps haiti to the verified
opening-versus-closing champion knockout regulation and dominican republic
to the verified LDF Cup regulation. An eligible title winner takes one
place. The Dominican league ranking supplies the other and replaces a
duplicate titleholder. When verified title routes are unavailable, Haiti
and the Dominican Republic use standings proxies. Build rejects fewer
than ten unique eligible Caribbean clubs and ambiguous top divisions.

Entry order is available only when a source could not yet have completed
its first season. Once that source should have a result, the draw waits for
a fresh completed ranking or a configured title result. The checksummed journal keeps
draws, domestic rankings, title winners and the podium. Live fixture
state prevents duplicate or retroactive registration.

The July driver checks the previous edition's 20 completed group matches,
eight completed knockout matches and matching podium. It calls native
teardown through `fl26_join_close_caribbean` with exactly the group master,
two replicas and knockout regulation. It verifies all four season markers
are reset and all four fixture counts are zero before registration.
Deploy the matching `fl26join.dll`, `fl26swiss.dll` and Lua together. The
Build and Switch on runtime checks cover the Swiss contract and loader.
A missing Join export blocks replacement at runtime.

See [career identity and journal limits](concacaf.md#career-identity-and-journal-limits).
The isolated August 2029 FL27 replay verified the January 2026 creation date
after a July reload, ten completed-ranking qualifiers including Dominican
clubs 73167 and 73172, removal of the previous 28 fixtures, 20 new group
fixtures, four completed first-matchday fixtures and retention of both the
previous podium and the 2029 Champions Cup results. Evidence stays in the
local development output. This replay did not cover every optional title
route or calendar in an arbitrary world.

The group resolver uses points, goal difference, goals scored and the
tied-club mini-table. Placement hosts are ranked by points, goal difference,
goals scored, away goals, wins and away wins from regulation scores.
Fair-play points and external Concacaf club rankings are unavailable
to the implementation. Stable club ID breaks ties remaining after the
available sporting criteria as a substitute for the official final criteria.

Native settings enable away goals and extra time. The score resolver
checks regulation aggregate, regulation away goals, equally weighted
extra-time goals and then penalties. The podium is published after both
placement series finish and the finalists and third-place participants
agree with the verified semifinal outcomes.

Only the preceding December podium feeds the next January. Its champion
has a Round-of-16 bye, and its runner-up and third-place winner enter Round
One. Those berths are reserved before domestic allocation. First-edition
redistribution is available when the career had no opportunity to play the
preceding Caribbean edition.

[Official 2026 Caribbean Cup regulations, §§5 and 12](https://images.concacaf.com/image/private/fl_attachment/prd/voeb37ionr3hxr8wgpvm.pdf)
