# What's new in Mod Studio 0.2.4

0.2.4 is a bug-fix update (in progress). Nothing new to learn: Install the modules, Build
once, and your 0.2.2 career keeps working.

## Changed

- **Export the world takes the scoreboards and menu themes of other packs along.** When the
  switched-on map lines of the Scoreboard Server or Menu Server on your PC give the world's
  competitions (its leagues, cups, super cups, confederation cups) a board or a theme from another
  pack, a modpack's, the zip carries those folders under `<world>\_packs` with their map lines, as
  it already did for kits. The receiver needs nothing else; the themes show with the Menu Server
  module on in `sider.ini`. Guide 9.1.

## Fixed

- **A world could be built with clubs that have no players; picking one crashed the game.** The
  placeholder squads are handed out in club-id order and stop at the player table's cap (61905
  with the modules installed) without a word in the Build log; a world past the cap -- 1212 new
  clubs with squads of 30 -- got its last 80 clubs with no players at all, and the Build log said
  only `no player 0, skipped` for each of their squad edits. In the game such a club crashes
  when picked, and Become a Legend does not start. Build now stops when the placeholder squads
  do not reach every club, saying how many fit, and stops at the end if any new club has fewer
  than 18 players; Mod Studio's checks say so about a world that is already built (build it again).
  The Build page's own count of the room (Checks) was already right for a Build inside Mod Studio.
- **A league with a place in the game's Copa Libertadores played the day before or after it.**
  Nacional (Uruguay) had a league round on 22 September and the Libertadores quarter-final on
  the 23rd. The fixture module now asks the game for the Libertadores days (qualifying round,
  group stage, knockout) when the first league is dated and keeps such a league two days clear
  of them, as it does of a continental cup of ours. Thanks antonimus.
- **A calendar-year league played the day after its own cup.** The cup's days (the `dates ...
  days=` line of a January-December country) were kept clear only when the league was spaced
  the old way, not by the real-calendar scheduler: the Copa AUF Uruguay's second round on 18
  April, the league on the 19th. Both schedulers keep a day clear of them now, two on the
  first try, like the cup days of every other country. Thanks antonimus.
- **FL26 update 2.2 (`data_s25262b.cpk`): Mod Studio read its tables before the older ones.**
  The game's files were taken in alphabetical order, which puts `data_s25262b` before
  `data_s2526b`, so the newest tables were covered by older ones and the version label said
  `data_s2526d`. They are now layered the way the game does it; unpack the tables again
  (Tools, or the next Build does it). Thanks to everyone on the 2.2 update.
- **New clubs: the crest picked in the club dialog did not show in the table** until another
  league was chosen (the pick was saved; only the row was stale). GitHub #140, thanks B2Y26Arabia.
- **Cup mode: a saved cup (World Cup, Euro...) could not be loaded.** With the modules the
  load ran for a minute or two and the game closed; without them the same save loaded in
  seconds. The raised club limits had moved the game's tables but not three places where a
  cup save puts its teams, coaches and regulations back on load, so the live season came back
  without teams. Checked in the game: a World Cup save loads in seconds and continues at the
  cup menu. Thanks Vicentico.
- **League Two (and any league with nothing below it): the promotion arrows stuck to the first
  rows of the standings when scrolling.** Thanks Vicentico.
- **Super cups of the game's own leagues** (New leagues > cups of the game's countries) came
  out as a 16-club knockout; they are now a two-club super cup (champion v cup winner), and in
  a February-December country it is played at the end of January. Needs Build again. Thanks
  Vicentico.
- **NewLife Database: "Bring the game's leagues to this season" skipped the Brasileirão Série B**
  (the game's Série B keeps only 6 of its 20 clubs in the 2026 line-up, and a league with fewer
  than half of its clubs left did not count as the game's own). Thanks Vicentico.
- **Build stopped with "players of <club>: no player <n>"** on a recipe written with 0.2.1
  (30-man new clubs). The transfer of a player the club no longer has is skipped with a note in
  the log. Thanks diwwanmago.

## Read this first

- Everything in [0.2.2](changelog-0.2.2.md) still applies. Your 0.2.2 / 0.2.3 career keeps
  working after this update; a cup saved before 0.2.4 loads too.
