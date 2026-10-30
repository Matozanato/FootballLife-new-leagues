# What's new in Mod Studio 0.2.5.1

0.2.5.1 (2026-10-30) fixes what you reported since 0.2.5 (2026-10-28). Worlds of 0.2.5 keep
working: Build them once with 0.2.5.1, and careers carry on.

**You don't have to update.** If 0.2.5 works for you and none of the fixes below is something you
are waiting for, stay on it. If you hit a problem with 0.2.5.1, tell us on Discord.

## Fixed

- **A game folder with letters outside plain English ones (B294).** With the game in a folder such
  as `C:\fůtbal lajf\...`, none of our modules could load its DLL (`LoadLibraryA failed (err 126)`
  in sider.log) and the added leagues had no fixtures. The modules now load their DLLs from any
  folder name. (Thanks Pelda)
- **A world named with a space (B295).** With a world such as `_FL26MyWorld 1.4B` in the game,
  Mod Studio read its name only up to the space: after every Switch it on the top bar said
  "older or damaged: fl26regions.lua, fl26regnames.lua", Install the modules could put in another
  world's, and a Build of that world did not switch it on again. The whole name counts now, and
  the World name field of the Leagues page no longer takes a space (Rename world never did).
  (Thanks pepponeee98)
- **Build stopped on "no free player id left below 262144" (B282).** Every rebuild of a big world
  took a fresh block of player ids and never gave the old ones back, so a world rebuilt a few
  times (Modpack size) ran out. A rebuild now gives back the ids it leaves. (Thanks juanjose6124)
- **Build stopped on "player ... joins two clubs" (B274).** Leagues of two packs in one world that
  moved the same player of the game: the first club of the recipe keeps him, the second move is
  skipped with a note naming both clubs, and Build goes on. (Thanks juanjose6124)
- **A league taken out and added again (B287).** Its clubs and players came back with other ids,
  so the Edit made with that league no longer fitted. They get their old ids back now.
  (Thanks pepponeee98)
- **"No free competition ids left" while cups were unticked (B273).** The ids of national, super
  and league cups you unticked stayed held until one more Build worked. An unticked cup gives its
  id back at once.
- **The Competitions counter (B279).** It showed "212 / 255" on a world whose Build had no
  competition id left: ids under 130 are the game's. It now shows what the world has / what it
  can have.
- **The Copa Argentina crashed after its first round (B278).** When the league below swapped clubs
  with the top league, the cup was given a field the bracket screen cannot draw (26 clubs: 13 ties,
  the last leading nowhere), and the game closed. A cup of up to 32 clubs is now cut to a size
  the bracket draws. (Thanks D1eg0Ar, Agus)
- **A cup drawn again after its first match (B280).** A save loaded on the day of a cup's first
  round and played at once could have the cup drawn again with its clubs moved, and the game
  closed. A cup whose first round has started is left alone. (Thanks Agus)
- **Super cups before their league's first round (B283).** The super cup of an added league that
  starts in July (Romania, Poland, Ukraine, Bulgaria) was played after the league's first rounds,
  and could be played twice. It is now a week before the league starts, and played once.
  (Thanks Daemon)
- **A career loaded in its first autumn was taken for a new one (B289).** Played on into the next
  summer, it put the first-season list of European clubs into that summer's competitions as well.
- **First-season European list (B284).** With a list of 36 for the Champions League and the summer
  qualifying on, the last clubs of the list got no place. Clubs past the direct places now go to
  the competition's own qualifying. (Thanks Daemon)
- **More clubs of one country in Europe than its places (B281).** A title holder already in through
  its league handed its place to another club of its country (an eighth Italian club). Its place
  now goes to the top-up, and the top-up takes a country only while it has fewer clubs in than its
  places. (Thanks pepponeee)
- **UEFA qualifying in a world with no UEFA ranking of its own (B250).** The world's own leagues'
  qualifying places went ahead of the game's: the Greek champion, Portugal's second and third,
  Belgium, Turkey, Scotland and Denmark got nothing. Places now go by association rank.
  (Thanks monkusgigus)
- **"Croatian clubs (no league)" in the UEFA ranking (B290).** A group of clubs in no league took a
  rank of its own, and the real Croatian league came a rank lower. It is left out of the ranking.
- **Libertadores qualifying in Competition Info (B275).** From 1 July only phase 3 showed under the
  qualifying item. Phases 1 and 2 stay there, with their results, until January.
- **Sudamericana play-off by squad strength (B276).** A group that finished exactly in its draw
  order was read as unplayed and its places went by squad strength. A played group always goes by
  its table now. (Thanks antonimus)
- **Match Results after a summer qualifying match (B266).** The page showed a "%s" title over empty
  rows. It shows the round you played. (Thanks Konsel)
- **Mod Studio froze and took gigabytes on a big world (B267, B270).** Every change kept a full copy
  of the world for Undo: typing a Rating on Players froze the window, and 30 changes took over
  5 GB. Undo now keeps only what each change touched. (Thanks JoJofiaz)
- **Mod Studio on a Mac (B288).** Run from source with the game in CrossOver, every content folder
  was "missing on disk". sider.ini paths now take the system's separator; nothing changes on
  Windows. (Thanks evannoteven)
- **A world's own folder as the tables (B277).** Picking a folder inside a world in Settings > Use
  another tables folder gave "Country.bin not found". Mod Studio now says why (a world holds only
  the tables it changes) and keeps the tables it had. (Thanks jibibi)
- **Delete / Rename world from a world card (B269).** The box said to press Apply or Discard, which
  that page doesn't have. It opens Content folders now, where they are.
- **Translations (B292).** The Delete world title was in English in Spanish, French and Portuguese,
  and the kit import note named the Save button in English. (Thanks gianito9)
- **sider.log lost lines in a long season.** With ML Fast Forward, our log dropped every line after
  mid-season. It keeps them now.

## Also new

- **European places counter.** The European places dialog of the game's leagues counts the places
  you gave the Champions, Europa and Conference League against the clubs each one takes straight
  in, as you change them; Check the plan prints the same. (Thanks pepponeee)
- **Cup winner hint.** The line under Europe in the league window says how to give a place to the
  cup winner: take the position below 1. (Thanks Vicentico)
