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
- **A ready world installs in one click, and a newer version replaces the older one.** Install
  mods shows **Install the world** for a world zip and hides the options a ready world does not
  need. If the same world is installed already (an earlier Modpack), it asks once and takes the
  older one out first, so no file of it stays behind. The modules come along with the world every
  time, without a question. Guide: Install a ready pack, Way A.
- **Build is switched off while a ready world is on.** A world installed from a zip is built
  already; Build would have replaced it with the open recipe. The Build steps are greyed out with
  a note, Home says **Ready to play**, and Build, Plan, Switch on and Only the European cups
  explain what to do instead: press Play, or switch your own world on first. A world installed
  from a zip and built again on this PC counts as your own from then on.

- **The left bar is by what you want to do.** Home; then YOUR WORLD with **Build your world**
  (for modders, it says so at the top), **Import your world** (a world zip or a mod, and a league
  package), **Edit your world** (leagues, clubs, players, kits, stadiums as tabs) and **NewLife
  Database**; GAME CONTENT and TOOLS fold away; Settings at the bottom.
- **Modules in one line, fixed in one click.** Home and Lua modules say whether Mod Studio's
  modules are installed, up to date and switched on; when not, **Install now** puts them right.
  In `sider.ini` Mod Studio's module lines now stand together in one block of their own, with a
  heading, so the rest of the file is easy to read.
- **A final check after a world is installed.** Installing a ready world ends with **Ready to
  play** and a list of ticks (the world, switched on, the modules, the face pack, the content
  servers the world uses, the home stadiums), or **Almost ready** with what to fix.
- **Put Sider back as before Mod Studio, in one click.** Tools > Restore points (and Game >
  Put Sider back as before Mod Studio...) puts back every file Mod Studio changed as it was first
  (sider.ini, CommonLib, the map files) and takes out what it brought in: its modules, the face
  pack, the worlds and the mods installed with it. Nothing is deleted: all of it is kept in
  `SiderAddons\ModStudio\reset-<time>`, and **Undo the last reset** puts it back. Clean up in
  Restore points now always keeps the oldest copy of a file, the one from before Mod Studio.
- **Home stadiums of a world from another PC.** A modpack names its clubs' stadiums by the
  folders of its maker's stadium pack. When your stadium pack keeps a stadium under another
  region folder, Mod Studio now finds it by its name; a stadium you do not have is left out (the
  club plays where the game puts it), and the final check says how many clubs have theirs.

- **Your world saves itself.** There is no Save recipe any more: a change is saved a moment
  after you make it, and the bottom bar says **Your world is saved**. File has New world, Open a
  world... and Save your world as... (a copy under another name). The word "recipe" is gone from
  the program: it is **your world** everywhere, and "live" or "switched on" is **in the game**.
- **Import your world, simpler.** Drop a pack (or Choose a file...) and the page says in one line
  what it is: a newer version of a world you have, a ready world, a league package or a mod, with
  the leagues inside. One **Install** button does the rest. The choices are still there, under
  **More options**: which parts (leave the kits out, say), the name, the order of the content
  folders and the map lines. A league package (.fl26pack) dropped here goes into your world and
  Build and install starts. **In the game now** lists what is installed, with **Remove**.
- **One main button per page.** Build your world shows **Build and install**; the world's
  options and the single steps with Export the world fold away under **World options** and
  **Step by step**, and stay open or closed as you left them. League packages is a tab of Build
  your world. Players, Clubs, the clubs of a league and NewLife Database keep their main button
  and put the others under **More**; the team id and the crest's file name moved into the
  club's tooltip.
- **The game's tables unpack themselves.** The first time Mod Studio finds the game, it unpacks
  the game's clubs, leagues and players by itself (a minute or two) and says so
  in the bottom bar. **Settings > Unpack the game's tables** is still there for after a game update.

## Fixed

- **A big world stopped with "the player table is full" although it fits.** The game takes
  61905 players, and Build counted while it worked: the placeholder players a club's own squad
  replaces are taken out only at the end, so a world of 1212 new clubs (the Modpack, 60488
  players when built) stopped halfway. Build now checks the finished world. New clubs get squads
  of 30 when your world names its players; when the finished world is still too big, Build
  says by how much and builds again with smaller squads (never below 22).
- **Some clubs of the game lost a player to a new copy of him when NewLife refreshed them.** The
  name check that keeps a player's game id read "Yıldız" (the Turkish dotless i) and "Yildiz" as
  two names, and "Yann Aurel Bisseck" and "Yann Bisseck" too. Such a player got a new id, so the
  club had him twice or his old self played on elsewhere. The check now folds ı, ß, þ, ð, ħ and ŀ
  like the game does, and a middle name one database leaves out no longer counts.
- **Install mods: a world zip's scoreboards and kits of other packs were gone right after the
  install, and a league package's kits with them.** Install mods ends with Switch on, which
  writes the world's own kit and scoreboard map lines and takes every line of Mod Studio's out
  first. The lines a world zip brings for the scoreboards and menu themes of a modpack
  (`<world>\_packs`) and for kits borrowed from other packs (`<world>\_kits`) end in the same
  tag, so they went out with the rest: a modpack installed from its zip played with the game's
  own scoreboards, and the clubs of the game that had dropped into its leagues wore the wrong
  kit. The world's own package kits and scoreboards went the same way when their source folder
  is on the PC the world was built on (`no folder ..., skipped`). Now Switch on keeps the lines
  a world carries and the lines whose copy is already under the world, and Export the world
  carries them along again from such a PC. The Modpack's scoreboards show after Install mods.
  Thanks Vran, Mob, ELBastos.
- **A world could be built with clubs that have no players; picking one crashed the game.** The
  placeholder squads are handed out in club-id order and stop at the player table's cap (61905
  with the modules installed) without a word in the Build log; a world past the cap -- 1212 new
  clubs with squads of 30 -- got its last 80 clubs with no players at all, and the Build log said
  only `no player 0, skipped` for each of their squad edits. In the game such a club crashes
  when picked, and Become a Legend does not start. Build now stops when the placeholder squads
  do not reach every club, saying how many fit, and stops at the end if any new club has fewer
  than 18 players; Mod Studio's checks say so about a world that is already built (build it again).
  The Build page's own count of the room (Checks) was already right for a Build inside Mod Studio.
- **A database mod that moves the game's leagues (UML 2026 v3) got the wrong countries and the
  wrong NewLife leagues.** With Settings on the mod's tables (**Use another tables folder**),
  Mod Studio still took a game league's country from its slot: UML's Ligue 1, in the Russian
  league's slot, was "Russia" in the UEFA ranking (and left out like Russia), in the July
  starts and in the League order. The country now comes from the clubs the tables put in the
  league. The NewLife Database took "in the game" from the plain game's clubs, so a league
  whose clubs the mod left out or renumbered (the Russian league, Ligue 2) could not be added;
  now a club is in the game only when the tables have it, and the rest are new clubs. With the
  game's own tables nothing changes. Build again. Thanks Yanis.
- **Build switched off your own kits for the clubs of a league package that carries kits.** A
  `map.txt` line you set on the Kits page (`71578, "Serie C\Catania FC"`) was greyed out with
  "(switched off by FL26 Mod Studio)" at every Build, and the package's kit went into
  `<world>\<league>\<club>` with a line of Mod Studio's. Only kits made in the clubs' colours
  gave way to a line of yours; a package's kits did not, which is why it hit one league. Now a
  club with a line of your own (to a kit that is in the library) keeps it, gets no package kit
  and no made kit, and a line of yours an older Build switched off is switched on again at the
  next Build. Package kits also stay with their club when you Remove, Insert or Move a club, or
  update the league to a newer NewLife (they stayed by place, so the clubs below wore the next
  club's kit). Thanks pepponeee98.
- **Build stopped with `KeyError` (in `lbplayers.py`) on a world built before.** A player
  listed at two places (a NewLife club listed twice) was given his id from the last Build twice.
  He now takes it once, and a stale ids file no longer stops Build. With 0.2.3, delete
  `fl26playerids.json` in the world's folder (`SiderAddons\livecpk\<world>`) before each Build.
  Thanks maur0.
- **A league with a place in a continental competition of the game played the day before or
  after it, on every continent.** Nacional (Uruguay) had a league round on 22 September and the
  Libertadores quarter-final on the 23rd. The fixture module now knows the days of the game's
  own continental competitions in advance: the Copa Libertadores (qualifying round, group stage,
  knockout), the AFC Champions League (group stage and knockout) and the Club World Cup. A league
  that can send a club to one of them (its places in the world's access list, its country's cup
  winner's place, or the game's own South American and Asian leagues) keeps two days clear of the
  Libertadores and AFC Champions League days and a day clear of the Club World Cup's. A day the
  game gives one of them that is not among the known ones is noted in `sider.log` (`the game's
  reg ... plays N date(s)`) and kept clear by every league dated after it. Thanks antonimus.
- **A January-December league with a European place (Norway, Sweden, Finland, Ireland...) played
  the day before or after a European match.** Only August-May leagues were kept clear of the
  European days by the older scheduler, and the real-calendar scheduler used the wrong season's
  weekdays for the autumn of a league dated in January. Now both keep such a league two days
  clear of the August qualifying rounds of its own year, and clear of the autumn league phase
  and the spring knockouts, each on its own season's weekdays. A league with only a
  Libertadores or AFC place no longer loses the European days for nothing.
- **Both fixture schedulers now read one list of busy days per league** (continental cups of
  ours and of the game, pre-season cups, league cup, European days, national and calendar
  cups), so a day one of them keeps clear is a day the other keeps clear too. A continental cup
  of ours that takes a club through its cup winner (`alt=` places) is now kept clear by that
  league as well.
- **A calendar-year league played the day after its own cup.** The cup's days (the `dates ...
  days=` line of a January-December country) were kept clear only when the league was spaced
  the old way, not by the real-calendar scheduler: the Copa AUF Uruguay's second round on 18
  April, the league on the 19th. Both schedulers keep a day clear of them now, two on the
  first try, like the cup days of every other country. Each January-December country now
  keeps clear of its own cup's days, not of the one world-wide list. Thanks antonimus.
- **FL26 update 2.2 (`data_s25262b.cpk`): Mod Studio read its tables before the older ones.**
  The game's files were taken in alphabetical order, which puts `data_s25262b` before
  `data_s2526b`, so the newest tables were covered by older ones and the version label said
  `data_s2526d`. They are now layered the way the game does it; unpack the tables again
  (Tools, or the next Build does it). Thanks to everyone on the 2.2 update.
- **Second season: the Europa League had no round of 16, and its league phase table was empty
  from February on.** After the July teardown the February play-off is outside the season, and
  the game's start of it opened a new season on the Europa League -- dated by February's year,
  so one season early -- and every look at the league phase table from then on found that empty
  season: the play-off was played, but the round of 16 was never drawn and Competition Info
  showed an empty League Phase. The draw (since 0.2.3, 13 October) already took the fuller table
  of the two seasons; now the play-off and its ties are given the league phase's season year
  before they start, as in a first season, so no second season is opened at all. Needs Install
  the modules; a career that has already passed February of its second season keeps the table
  it has, the next season is right.
- **A February play-off with 7 ties instead of 8 (14 clubs), a qualifying round with 6.** A
  world with more than 300 competition regulations -- the 0.2.1 Modpack has 334 -- lost its
  highest regulation ids with the 0.2.1 modules: the game counts its regulations again after
  every load and looked at the first 300 only, so the last ties of the European rounds (and of
  the Libertadores and AFC groups) never got matches. `fl26regs600.lua`, installed since 0.2.2,
  makes the game count all of them. New: **Checks** now says so when a world has more
  regulations than the modules switched on let the game count, and points at Install the
  modules (a new career is needed). Thanks Micarodvzla22.
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
  a February-December country (the Supercopa de Chile, the Supercopa Rei) it is played at the
  end of January, between the champion and the cup winner of the season just ended. Needs
  Install mods and Build again, then a new career. Thanks Vicentico.
- **A new division under a February-December league of the game** (a J2 under the J.League)
  could send its own champion to that country's super cup. Needs Install mods.
- **NewLife Database: "Bring the game's leagues to this season" skipped the Brasileirão Série B**
  (the game's Série B keeps only 6 of its 20 clubs in the 2026 line-up, and a league with fewer
  than half of its clubs left did not count as the game's own). Thanks Vicentico.
- **Build stopped with "players of <club>: no player <n>"** on a recipe written with 0.2.1
  (30-man new clubs). The transfer of a player the club no longer has is skipped with a note in
  the log. Thanks diwwanmago.

- **A game under `Program Files`: Install mods, Install the modules, Build and Switch on stopped
  with a raw `PermissionError [WinError 5]`.** Windows lets only a program run as administrator
  change files there. Mod Studio now tries the game folder when you choose it and before it
  writes there, and says plainly what to do: run it as administrator (the message has a
  **Restart as administrator** button) or move the game out of Program Files. Home shows the
  same as long as the folder is not writable. FAQ. Thanks Konkubent.
- **An antivirus quarantined our DLLs (`fl26swiss.dll`, `fl26join.dll` ...) right after Install
  the modules, and Mod Studio said nothing**: the game started without the European draws and
  the new cups. Install the modules now checks every DLL it copied (there, and the bytes it
  shipped) and stops with a message that names the file and says to add `SiderAddons` as an
  exclusion in the antivirus and install again; Home, Diagnostics and *4. Check* say the same
  while a DLL a switched-on module needs is missing. FAQ. Thanks bikolunar42.

## Read this first

- Everything in [0.2.2](changelog-0.2.2.md) still applies. Your 0.2.2 / 0.2.3 career keeps
  working after this update; a cup saved before 0.2.4 loads too.
