# What's new in Mod Studio 0.2.5

0.2.5 is being prepared (not released). If 0.2.4 needs a second round of fixes, these may
come with it instead.

## Added

- **MP (matches played) in the standings tables.** A league's table and the League Phase of the
  UEFA cups now have an MP column between Points and W; W, D, L, F, A and GD stay as they were
  and move a little closer together. The number is the game's own count of the club's matches
  (MP = W + D + L), filled by `fl26swiss`. Build writes the world's copy of the standings layout
  (`common/menu/general/rankingTeam.bin`, tools/mkmpcol.py) from the game's own; a world built
  before needs one Build, and a mod's own standings layout is left as it is (the table then stays
  the game's). Checked in the game: the Conference League's League Phase and the Belgian
  Challenger Pro League, with the club highlight and the promotion arrows in place.
- **New clubs play at the game's own stadiums, many of them, not all at Stadio Nazionale.** A
  new club was a copy of the game's last club, so every one of them -- the Modpack's 1212 --
  had its home at Stadio Nazionale unless your stadium pack gave it another. Build now gives
  each new club one of the game's 17 fictional stadiums: its size by the league's tier (the big
  ones at the top, Sports Park and Village Road down the pyramid), its look by the country (an
  English-looking ground in England, a Spanish-looking one in Spain and South America, a German
  one in central Europe), and a league spread over many of them. The pick is the same at every
  Build. **Edit club > Game stadium** gives a club the one you want, the game's real ones (Old
  Trafford, La Bombonera ...) too. A stadium of your stadium pack still comes first.
  To keep the old way, put `"game_stadiums": false` in the world file.
- **Stadiums > Your world's clubs: the home stadiums of a world you imported.** A ready world
  (the Modpack) is not built on your PC, so its clubs keep the stadiums it came with. The new tab
  lists its new clubs with their game stadium and their stadium-pack stadium: **Game stadiums
  automatically** gives them all one of the game's the way Build does, **Choose a game
  stadium...** sets one for the clubs you selected, and for your own stadium pack **From your
  stadium pack...**, **Find in your pack** (by the stadium's or the club's name) and **No pack
  stadium**. Save writes the world (a copy of the old `Team.bin` stays next to it). What you
  picked is kept in `fl26stadiums.json` in the world's folder and comes back when you install a
  newer version of the same world. Start a new Master League after saving.
- **The modern CONMEBOL competitions, if you want them** (vmardonesdev and nissindiaz,
  [#146](https://github.com/Matozanato/FootballLife-new-leagues/pull/146)). **South American
  places > Modern CONMEBOL competitions** switches on the Copa Libertadores' qualifying in three
  phases (phase 1: 6 clubs, phase 2: 13 clubs and the phase-1 winners, phase 3: the eight
  phase-2 winners), a Copa Sudamericana with a first stage of 32 clubs and a play-off after the
  groups (its runners-up against the Libertadores' third-placed clubs), and the Recopa
  Sudamericana in February between the two winners (from a career's second season). Your
  leagues and the game's South American leagues then get places in **Libertadores phase 1**,
  **phase 2** and **Copa Sudamericana first stage**, and **CONMEBOL countries without a league**
  gives places to the clubs of Bolivia, Peru ... when the country has no league in your world.
  The window counts the places against the field Build needs: 26 Libertadores group places, 13
  in phase 2, 6 in phase 1, 12 Sudamericana group places and 32 in its first stage.
  Left off, nothing changes: a world with Libertadores, qualifying or Copa Sudamericana places
  builds exactly as before, ids and all. Switching it off again takes out only the places the
  modern competitions have, after asking. Start a new Master League after a Build that switches
  it on or off.

- **Back and Forward through the pages, as in a browser.** Two arrows at the left of the section
  bar, Alt+Left / Alt+Right and the mouse's side buttons take you back to the pages you had open
  (up to 50). (Thanks Vicentico)

- **Build lists every problem at once, each with Go there.** Check the plan, Build the world and
  Build and install stopped at the first problem, and the next showed only after it was put right.
  They now list them all above the log, each with where it is (the league and club, a club of the
  game by its name and team ID), and **Go there** (or a double-click) opens its page: Clubs at the
  league and club, Leagues at the league or at the game's league of a club of the game, Players
  at a club's players. A swap of two clubs of the game that the game's tables have in the same
  league now is left out with a note instead of stopping Build. Messages about a club of the game
  now give its name and its team ID together. (Thanks jibibi, vmican)

- **Undo and Redo of the last change to your world.** Two buttons in the bottom bar next to "Your
  world is saved", and Ctrl+Z / Ctrl+Y when no text box is in use: up to 30 steps back. New world
  or Open starts again with none.
- **Trophies of your own for a competition.** Leagues > More > Trophies (and Cups > Trophies on My
  world) lists every competition with its competition and regulation IDs; pick a trophy folder for
  one and Build copies it into the world. When the world is switched on, FL26's own Entrance.lua
  shows that trophy in the competition's matches and in its final, for the world's new leagues and
  cups and for the game's competitions alike. The folder is laid out like FL26's
  `SiderAddons\content\Entrance` folders (the files at the top or in a phase folder, the final's in
  `Final`; they replace the AFC Champions League trophy's files). A competition with no folder
  paired keeps what it had: no competition borrows another's trophy. Switch on writes one marked
  block at the top of Entrance.lua and replaces it every time; nothing else in the file is touched.
  Without FL26's Entrance.lua in `modules` the Build log says the trophies are not shown.

## Fixed

- **Home > Last changes: rows painted over each other (B83).** While a message box was open (the one
  after Install the modules), the list of last changes was drawn on top of the old one until you
  went to another page. The same in the world cards, the pack ticks and the league crests. (Thanks
  David)

- **A deleted world came back at the next start (B107).** After Delete world and New world (left as
  it was), Mod Studio opened the deleted world again when it started, because New world and Open did
  not change which world the next start opens. It now opens the one you had open. (Thanks jibibi)

- **A dash instead of the crest of a club of the game in your league (B108).** On the Leagues page
  the game's own clubs in a league of yours (Zamora and Deportivo Táchira in the Liga FUTVE) had no
  crest: the world holds only the crests Build drew. Mod Studio now shows the crest the game shows:
  from a crest pack switched on in sider.ini, else from the game's own files. (Thanks David)

- **Clubs that took a game club's place wore the kit of the club that left (B176).** NewLife's
  "Bring the game's leagues to this season" gives the place of a club that went down to the club
  that came up, and the club keeps the game's team id. The kit for that id stayed the old club's:
  in the Europack, Schalke 04, SC Paderborn and SV Elversberg played the Bundesliga in Heidenheim's,
  St. Pauli's and Wolfsburg's kits (your kit pack's line for the id, or the game's own kit). Such a
  club now gets a kit drawn from its colours and crest, as a new club does, in
  `content\kit-server\<world>\Clubs of the game`, and the kit pack's line for the id is switched off
  while the world is in the game (back on with any other world). A line of your own whose folder
  names the club (`Modpack\Game leagues\FC Schalke 04`) is kept. A world you already have gets
  them at its next Build or Switch it on (the Europack draws 49 kits once, about half a minute).
  (Thanks quicksite, NedimMM)

- **A kit you changed by hand went back to Mod Studio's (B166).** A kit put into a club's kit
  folder of the world by hand (through Sider, or by copying the files in) was replaced at the next
  Build or Switch it on: by the league package's kit when a file's size differed, or by the drawn
  kit when the club's colours, the crest or the kit that lends the numbers changed. Mod Studio now
  notes what it put in each folder and leaves a folder whose files you changed alone, and says so in
  the log. To get Mod Studio's kit back, delete the folder and Build. (Thanks LaraCroft)

- **Home said "switched off: fl26regions, fl26regnames" and Install now did not help (B177).**
  Those two modules come with a world (they name its competitions and countries), not with Mod
  Studio's module pack, so Install now passed them by. Home now counts them only when the world in
  the game has them, and Install now puts that world's copies in and switches them on. Switching on
  a world that has none switches another world's off. (Thanks Vran)

- **The hub's Next showed a cup tie your club was not in (B162)** (Carabao Cup: Chelsea - Tottenham
  while Liverpool had been drawn against Brentford, as the news and Competition Info said). The hub
  reads its own list of your club's days, which the game fills when it makes the matches; when Mod
  Studio's cup draw (seeded, random or byes) or the European bracket order then gave the matches
  other clubs, that list kept the old pairing. The modules now ask the game to make the list again
  the next day, as the game does after a change of club. A season you already play is put right the
  next day after loading it. (Thanks pokuuuu.)

- **Clubs in no league in Other European teams turned up in the Champions League of Cup mode
  (B167)** (NK Hajduk Brezje, NK Jadran Stefanec ... among its clubs). Cup mode fills the last
  places of the Champions League from the game's Other European teams, and in a world whose leagues
  take the game's own such clubs (Dynamo Kyiv, Shakhtar ...), the clubs you put there are all that
  is left. The League window (Clubs in no league: Other European teams) and Build's log now say so;
  for small clubs choose **Classic Teams** instead. A world made before keeps its clubs where they
  are until you change the group and Build again. (Thanks ¥$)

- **"Plays in Ligue 2" after Bring the game's leagues and a new Ligue 3 (B137).** The game's Ligue 2
  has more places than this season's, so the clubs the season has elsewhere keep their places
  there (Bring has no club to put in), and a NewLife league of yours that has them too stops
  Build. The Bring window now names those clubs and says what to do: in that league use **Club
  of the game** and give it a new club in its place, or leave it out. (Thanks jibibi)

- **A club of the game in one of your leagues could not be put in another (B95)** (Envigado and
  Unión Magdalena, in NewLife's Colombian Second Division: "as if they did not exist"). **Club of the
  game...** now finds it (search its name or team ID) and moves it: out of its old place, which is a
  new club then, into this one, with who takes its places in the game. **NewLife club...** lists the
  release's clubs the game has too, greyed, and says that Club of the game puts them in; it also no
  longer lists the clubs a league of yours has already. (Thanks vmican)

- **Import crests no longer ticks wrong crests over the game's own clubs (B170).** With a big
  crest folder (David's Logos) about 75 pictures were ticked onto clubs of the game because the
  club's name was inside the picture's: "fc-united-of-manchester" went to Manchester United,
  "cove-rangers" to Rangers FC, "portuguesa-de-sao-paulo" to Sao Paulo FC, and most B sides
  ("alaves-b", "fc-augsburg-ii", "valencia-mestalla") to their first team. Such a match is now
  only a suggestion (50 %, not ticked) for a club of the game, a reserve or youth side's picture
  (B, II, U23, Reserves, Promesas, Sevilla Atletico ...) is never ticked for a first team, and
  Atletico, Deportivo, Sport tell clubs apart when both names have them ("atletico-de-cali" is
  not Deportivo Cali). "galatasaray.png" for Galatasaray SK still ticks. (Thanks David)

- **Names with letters the game cannot draw (B173).** The game's fonts have no small ə, so the
  Azeri Premier League (Şəfa, Məmmədov) showed boxes, and the same went for Romanian ș and ț
  and Vietnamese letters such as ơ, ư, ạ. Build now writes such a letter into the game's tables
  as one the fonts have: ə as a (Mammadov, as UEFA spells it), ș ț as ş ţ, a Vietnamese letter
  with the accents the fonts have (Nguyễn -> Nguyên); invisible marks some names carry go. Club,
  league, player and coach names; Mod Studio keeps the names as they were. Build the world again
  to get it. (Thanks LaraCroft)

- **The header's PACK box follows the world in the game (B168).** After Activate of another
  world you installed (the Modpack r12 after eu4), PACK still named the zip installed last while
  ACTIVE WORLD was right. It now names the pack the active world came from; for a world built
  on your PC it names the last pack that brought no world (scoreboards, kits), or nothing.
- **A save loaded in the summer, or the game quit between 1 July and the August draws, sent the
  wrong clubs to Europe.** The final tables (and cup winners) the modules keep at the end of a
  season for the next season's continental places lived only while the game ran. After a restart,
  or a save of those weeks loaded, the places of your leagues went by squad strength instead of
  last season's table (Cyprus and Bosnia: 8 places from the tables, 124 by squad strength), and a
  continental super cup of ours could take its winners from the game again. The modules now
  write what they keep to `fl26swiss-state.bin` in the game's save folder (it moves with the
  world like your careers) and read it back when a save is loaded or the game starts again:
  the tables of your career, of the season just finished, never those of a later save or of a
  career with another club. Needs Install the modules; a career already past 1 July without them
  gets its tables from the next season's end. Thanks bythezl19.
- **Portugal's Supertaça was played after the first league round.** The modules bring a
  league of a country that really kicks off early forward to its July or early August start, the
  game's own leagues too, but the game's super cups stay on their dates: Liga Portugal started
  on 8 August and the Supertaça (13 and 16 August) came after it. The same hit the Netherlands,
  Turkey, Russia, Belgium and France. A league now starts no earlier than a week after a cup its
  country plays before its first round, so those leagues start where the game starts them, after
  their super cup. Needs Install the modules and Build again; a new career. Thanks Hugo Freixo.
- **Our continental cups played on the same day as the game's own, or the day before.** The
  Copa Sudamericana's group stage was on the days of the Libertadores qualifying round (4 and
  11 February) and its knockout on the Libertadores group days, and the Tuesday cups (AFC
  Champions League Two) were the day before the AFC Champions League's Wednesdays -- and the
  same club can be in both, because the game fills its January-December cups on 1 January,
  months after ours were filled. A cup of ours whose leagues can send a club to one of the
  game's cups now plays in the weeks that cup leaves free, at least a day apart from every one
  of its days, on the same weekdays and with the same number of rounds. Copa Sudamericana:
  groups 25 November, 2 December, 21 and 28 January, 18 and 25 February; knockout 11 March,
  1, 8 and 22 April, 6 and 13 May, final 27 May. AFC Champions League Two and AFC Challenge
  League: groups 25 November, 2 December, 14, 21 and 28 January, 4 February; knockout 18
  February (round of 16 only), 11 and 25 March, 1, 15 and 29 April, final 13 May (the
  Tuesday cup a day earlier each time). The CAF, CONCACAF and OFC cups keep their days.
  `sider.log` names the days each cup takes (`cup ... its leagues reach ...`). A career that
  is already past the group stage's days of before (the AFC Champions League Two's groups end
  on 17 February there) plays this season's knockout on the days of before too, never on a day
  already gone; from the next season the new days. Thanks DavidBDJ.

- **The African and Asian cups had no knockout from the second season (B172).** The CAF and AFC
  cups of a world (the Modpack's five) kept last season's clubs after the summer, and a cup that
  still held clubs counted as drawn: its groups were never drawn again, stayed out of the new
  season and had no table ("group A has a table of 0 rows"), so the knockout was never filled.
  A cup is now drawn anew once a season when neither it nor its groups are in the season, its
  old groups emptied first, and its groups get the season's tables the way the game makes them.
  From the fourth season the game had no table left to give them: it keeps every table of every
  season in one pool of 600, and the Champions League, Europa League and Conference League took 30
  tables each season that no season holds and that were never given back (r12, fourth season: 0
  free, 55 of them such tables of earlier seasons). A table of an earlier season that no season
  holds is now freed, before a cup's groups are drawn and at every summer rollover.
- **The game crashed at a quarter-final of the CONCACAF Champions Cup in a later season (B181).**
  A cup that is a knockout only (the CONCACAF Champions Cup, the OFC Champions League) and the
  Conference League's knockout kept last season's rounds: the new season's matches got the new
  clubs, but each tie still named last season's two clubs, so the game found few of the round of
  16's winners and played a quarter-final with no club in it (r12, fourth season, 7 April). Every
  tie still to be played now names the clubs of its match; a career already in that state is put
  right when it is loaded, as long as the round has not been played yet.
- **The Conference League not played in a later season (B118).** Its league phase kept last
  season's 36 clubs after the summer and counted as filled; it is now filled anew once a season
  when it is in no season.
- **The Champions League's round of 16 not drawn after two seasons with full tables (B169).**
  When two seasons of the league phase both had 36 rows, the older table could be read; the
  latest season's is now taken.
- **The UEFA cups' Goal and Assist Ranking started again at the play-off (B114).** After the
  league phase, the play-off and the knockout of the Champions League, Europa League and
  Conference League showed only the goals of their own matches, and the game wrote its own list
  again every few days. The ranking of a running play-off or knockout now keeps the league
  phase's and the play-off's goals and assists too, also after the game's own rewrite. (Thanks
  Micarodvzla22)

- **A UEFA play-off drawn again in spring (B192).** In a later season a play-off already played
  in February could be drawn a second time between March and June. A play-off is no longer
  drawn after its second leg.

- **A national team or club of the game went missing next to a new club (B63).** The game takes
  two clubs whose ids differ only in bits 14-16 as the same club, and a few of its lists keep only
  the first: the third new club of every world (id 71580) was Nam Dinh's twin, the tenth (71587)
  Brunei's, then Timor-Leste, Botswana and Wrexham. Build now steps round those 24 ids for a club
  that gets a new id; a club keeps the id it had at an earlier Build, so careers and kit or face
  packs of a world you built before still find it. (Thanks Nissin)

- **Make it editable (and restoring or deleting a world backup) stopped on a long file path (B189).** A pack with a
  deep folder (Spain's "Supercopa de España" kits, a long club name) has files whose full path is
  longer than 260 characters, and Windows refuses those unless long paths are switched on: the
  backup that Make it editable makes first stopped half-way. Mod Studio now copies and removes
  world folders with long paths itself, whatever that Windows setting says. (Thanks SladeBR)

- **"Windows does not let Mod Studio write" said what you could not do.** It told everyone to run
  Mod Studio as administrator and move the game out of Program Files, even when Mod Studio was
  already administrator and the game was in D:\Games. It now says only what applies: out of
  Program Files, run as administrator; already administrator, close the game and Sider, allow
  FL26ModStudio.exe in Controlled folder access, or untick Read-only. (Thanks AHMED)

- **Build stopped on "no formation '161' (the Formation list has them)" (B105).** A league from a
  pack made over other tables can name a formation your tables do not have. Build now goes on: the
  league's clubs play the formation their squad fits (as "Picked from each club's squad") and the
  log names the league and the formation. (Thanks Dee Jay and Micarodvzla22)

- **Install of a big world zip stopped half-way on a full C: (B41).** Import your world unpacked
  every zip into the Windows temp folder on C:, and the Modpack takes 7 GB unpacked, even with the
  game on D:. When C: has no room for it, Mod Studio now unpacks beside the game (the disk Install
  copies to anyway), and when neither disk has room it says how much is needed before it starts.
  (Thanks vmican)

- **Generated players of Sweden, Norway, Finland and the other Nordic nations were mostly
  dark-skinned (B183).** A regen or a new player gets one of the face pack's faces of his part of
  the world, and the Nordic nations shared theirs with England, Germany and the Netherlands, six of
  ten of them dark. They now have a group of their own with the pack's light faces. (Thanks
  pepponeee98)

## Read this first

- Everything in [0.2.4](changelog-0.2.4.md) still applies.
