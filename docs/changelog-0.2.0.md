# What's new in Mod Studio 0.2.0

0.2.0 is the **last release with new features**. From here on Mod Studio only gets bug fixes,
about once a week. If you want to take it further, fork it: **0.2.0 comes with complete
documentation for forks**, from [forking.md](forking.md) through the chapters in
[docs/fork/](fork/) (code map, every recipe key, the world file, every module and DLL, building,
testing, the NewLife release format). The code is MIT licensed.

## Read this first

- **A calendar day now holds 792 matches instead of 280.** Big worlds no longer lose matches
  on busy days.
- **Careers saved with an older version do not load in 0.2.0** (they stay on the loading
  screen). The bigger day changes how a career is saved, so start a new Master League career
  after updating. Keep your old Mod Studio folder if you want to finish an old career.
- **Your worlds stay as they are.** No new Build is needed for the 792 limit. Install the
  modules (Install page, or Build does it) so the new patch set and modules are in.
- An old `EDIT00000000` save from before your last Build still hides clubs that Build added since
  (Other European among them). Build warns about it. Delete or rename the old save so the game
  makes a new one.

## The big one: 792 matches a day

Until now a day in the game's calendar had room for 280 matches. A world with many leagues
put more than that on some weekends and the extra matches were never played (in a 34-league
world, about 1,000 matches a season).

- The patch set is now `...-fixtures-calendar` (3,519 patches). Each day has room for 792
  matches. Tested with a new career through a whole season, including days with more than 280
  matches, with no crash.
- On top of that, the league rounds are spread out:
  - only leagues that send clubs to Europe keep clear of the European days;
  - every league's rounds lean 0-2 days later, so the whole world does not play on the same
    Saturday;
  - the game's own leagues (Bundesliga, Super Lig, Pro League ...) are spaced as well. Before,
    they were never moved and some played on the January Champions League day;
  - national cup days block two days instead of three;
  - a league round next to a European day moves a day clear when it has to (18 and 20 club
    leagues no longer play the day after the January Champions League matchday);
  - the August European play-offs move three days clear of the national cups' first round.
- In our 34-league test world the spreading alone brought the matches that never got a day
  from 1,078 to 2 out of 14,400. With room for 792 a day, even the busiest days fit.

## New

### Continental cups

- **CONCACAF Champions Cup**: a knockout of 16 clubs; MLS fills the places.
- **OFC Champions League**.
- **AFC Challenge League**, next to the AFC Champions League and ACL Two. The J1 League's
  11th-14th go there, and the CSL and Saudi places come after ACL Two.
- **National cup winners can go to our continental cups.** If the cup winner already has a
  place through its league, the place falls back to the league: the next free position, after
  the places other competitions take (#95).
- Up to 16 continental cups in a world (8 before).
- **The game's own Club World Cup**: our continental champion replaces a club from its own
  confederation.

### Leagues and seasons

- **League order** (League Builder page): the order of the countries in Master League's Select Team and
  in the Kick Off / Edit team list. Choose *By continent* (the game's order), *Every country
  A-Z*, or your own order.
- **Seasons of the game's leagues** (League Builder page, experimental): Japan, China, Brazil, Chile
  and Saudi Arabia can play August to May like Europe. Their cups are dated to match, and a
  division below follows its top flight.
- **Apertura/Clausura: the league below gets promotion and relegation** (#106). The table is
  counted from the matches of both tournaments.
- **Seeded country cup draws** for every world. The top division's clubs get the byes and the
  later rounds and are split evenly between the two halves of the bracket. The Fixtures screen
  shows the draw that is really played. Choose *Seeded* (default), *Random* or *Off* on the
  League Builder page.
- **Board objective by continent** (#43): the board of a club in our Asian league asks for the
  AFC Champions League, and in our South American league for the Libertadores. Before, they
  always asked for the Champions League.
- Placeholder squads start at their division's level (about 72 in a top flight, down to 57).

### Kits, logos, faces

- **Import kits from plain pictures** (Kits page, thanks to Xxspedd): a club folder of
  `p1.png`, `p2.png` ... `g1.png` becomes a Kit Server kit. Numbers and names come from a kit
  you pick in *Numbers and names from*.
- **Logos for the cups of the game's countries** (Build > Cups of the game's countries): the
  league cup and the super cup each take their own logo. With no picture, Build draws an emblem
  with the cup's initials.
- **Editable kits (#112)**: new clubs now get real plain kits that you can paint in Edit (Paste
  Image). Before, they got the kits of team 0.
- Faces of players past the game's appearance table are drawn with their own face.
- Crests and logos you add are cropped and scaled to fill the square.

### Regens

- `fl26regen` can stay switched off: show the League Builder's own modules, untick `fl26regen`
  and press **Apply**. Build, Install the modules and switching worlds now leave it off. The game
  then makes its own regens, with no names or faces from the regen face pack.

### NewLife Database

- **Update my leagues** keeps the faces and portraits you linked on the Players page for players
  who stay in the league (#111).
- **A game league brought to the NewLife season takes the game's rating scale**, measured on
  the players both have and matched by rank, so a star lands where the game rates its stars
  and the best clubs keep the strength the game gives them.
- The NewLife table sorts by any column (click a header; click again to reverse).
- **NewLife club...** under New clubs works before you open the NewLife page (#105).
- **Remove club / Insert club** move a league's NewLife ids with the places. A removed club no
  longer "plays in two leagues", and Build no longer reads the ids of the clubs after it one
  place off.

### Mod Studio itself

- The twelve small crash guards are installed as two files, `fl26guards.lua` and
  `fl26lateguards.lua`, so the `sider.ini` list is shorter. sider.log still names each guard.
- **Documentation for forks**: [forking.md](forking.md) and the chapters in `docs/fork/`. They
  cover the code map, every recipe key, the world file, every module and DLL, building, testing
  and the NewLife release format.

## Fixes

- The league phase of the Champions League, Europa League and Conference League was called
  "Group A" and "Group stage" on some screens. It now says "League Phase".
- Match Results showed "Group stage - Matchday 54" for the Champions League, Europa League
  and Conference League play-offs and qualifying rounds. They now show as play-offs (fix by
  n1ne).
- **Other European lost its last clubs after a Build** that moved some of its clubs into new
  leagues. The game loads the Edit save's club lists without raising their length; the module
  now follows how far each list was really written.
- **Kit Server: kick-off crash with editable kits**. The goalkeeper kit pick found no kit of the
  game for a new club.
- AFC cups took J1 and Saudi clubs by squad strength in the second season. The final tables of
  the leagues our cups draw from are now kept at the summer teardown.
- A dragged league stays in its continent on the Leagues page (#107). Before, North American and
  Oceanian leagues always ended up last in the Build order.
- Saudi Arabia moves in Select Team too (region 28 was named Thailand).
- The League order dialog wrote a key Build did not read.
- A split or Apertura/Clausura under a February-December league (Liga BetPlay, J1 League ...) is
  refused with a clear message. Before, the division played the wrong season.
- The old Edit save warning now says that it also hides new clubs from Other European.
- Team ID shows "at Build" for a club that gets its id when you Build.

## Known issues

See [known-issues.md](known-issues.md). Most important:

- Careers from older versions do not load (see the top of this page).
- Clubs of new African, North American and Oceanian leagues keep the objective the game picks:
  the game has no board objective for those cups.
- The Club World Cup is the game's own (every season, mid-December), with the champions of the
  continental cups your world builds in it. The 2025 format with 32 clubs is not in Mod Studio.

## Thanks

Everyone who reported, tested and helped, on GitHub and on the Discord. In particular Gu (game
seasons, the guard bundles), Xxspedd (kits from pictures), LumpierTheGunner, LaraCroft, lub7628, aaron, rwee,
vmardonesdev, victormican, jibibi and Risto. The full list is in the README credits.
