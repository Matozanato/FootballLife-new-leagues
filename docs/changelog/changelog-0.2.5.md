# What's new in Mod Studio 0.2.5

0.2.5 is being prepared (not released). If 0.2.4 needs a second round of fixes, these may
come with it instead.

## Added

- **A third division can play the country's cup (the Coupe de France of the lower leagues).**
  For a new league right under one of the game's second divisions, like National under Ligue 2,
  **Edit league > Its best clubs play the country's cup too** puts its first clubs into the
  game's cup next to the two divisions it already has: Ligue 1 18 + Ligue 2 21 + the first 9 of
  National = 48, as the real Coupe de France takes the lower leagues (jibibi). 48 is the most the
  game's cup list holds; with fewer clubs below, the cup takes 44, 40 or 36, the fields the cup
  screens draw. Build raises the cup's bracket to that field and `fl26chain` fills it. Off by
  default: a world without the tick plays the cup as before. Start a new career after the Build.
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
- **A new club's shirt numbers follow the positions (Thanks ismael).** A new club's players wore
  the numbers of the squad Build cloned for it, so a centre back could wear 9 and a winger 2. Build
  now numbers the whole squad by position: the first eleven the way a club does (keeper 1, right
  back 2, left back 3, centre backs 4 and 5, the holding midfielder 6, the striker 9, the wingers
  7 and 11, the playmaker 10), the rest with their line's numbers (a defender 15, 22, 23 ..., a
  forward 17, 19, 21 ...), keepers always a keeper's number (1, 13, 12, 25 ...). Numbers a recipe or
  a NewLife pack gives stay as they are; the clubs of the game keep theirs. Checked on the Europe
  pack: 1139 new clubs, no number twice, no outfielder in 1, 12 or 13.
- **Bring the game's leagues to this season: Only the game's own players.** A new tick box at
  the bottom of the window. With it, a club of the game that keeps its place gets only the
  transfers between the game's players and the season's ratings: no new players and nobody let
  go. A player NewLife names differently from the game (Zambo Anguissa / Anguissa, Pote / Pedro
  Gonçalves) is then no longer made a second time while the game's own one becomes a free agent.
  A club that came up into a place still gets its whole squad. With NewLife 1.5b7 and every
  league ticked: 873 new players instead of 4082. (Thanks Aleperfe87)
- **Players > More > Import transfers...: a whole transfer window from one CSV.** One line a
  player: `player` (his name or id), `to` (the club he joins: its name in your world, with or
  without FC and such, or its team ID) and, when two players share a name, `from` (his club
  now). Commas, semicolons or tabs; accents and capitals do not matter. Each player moves as
  with Transfer to..., your new clubs included, and the message lists every line it could not
  place (no such player, two clubs of that name) instead of guessing. Make the table any way you
  like -- by hand, or with a tool off Transfermarkt; Mod Studio itself reads no website.
  (Thanks jibibi)

- **The classic Copa Sudamericana can play February to December.** A recipe setting,
  `"sudamericana_calendar": true`, puts it on the Libertadores' days and fills it in February from
  the same final tables, so a Brazilian or Argentine club in the Libertadores is no longer drawn
  into a Sudamericana played August to May at the same time. The World Modpack has it on; a world
  without it keeps the cup as it was.

## Fixed

- **Every Build of the World Modpack took the full ten minutes, even for one new logo (B239).**
  A Build after an edit of pictures alone (a logo or crest swapped) draws only those again, in
  seconds. A world made on another PC, like the Modpack, has logos whose picture files are not on
  your PC; the world keeps its own there, but that switched the quick Build off for good. Now the
  quick Build works beside them: it leaves those logos as the world has them and draws only what
  you changed. Giving a crest to a club that had none, and the first Build after an update, are
  still full Builds. (Thanks jibibi)

- **A club wore another club's crest in some competitions (B199).** A world zip carries the
  scoreboards other packs give its competitions, and a scoreboard can bring crests of its own, by
  team id. The World Modpack's Community Shield board had Leicester City's crest for the id whose
  place the world gives Bolton Wanderers, so in those matches Bolton showed Leicester's crest.
  Make a world zip now leaves out a pack's crest for any club whose crest the world draws itself.
  (Thanks JamesNotLike)

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
  Build > New clubs > **Kits made for clubs in a game club's place** (on by default) switches this
  off: the game's kit, or your kit pack's line for the id, stays. (Thanks quicksite, NedimMM;
  the switch: Vicentico12)

- **A kit you changed by hand went back to Mod Studio's (B166).** A kit put into a club's kit
  folder of the world by hand (through Sider, or by copying the files in) was replaced at the next
  Build or Switch it on: by the league package's kit when a file's size differed, or by the drawn
  kit when the club's colours, the crest or the kit that lends the numbers changed. Mod Studio now
  notes what it put in each folder and leaves a folder whose files you changed alone, and says so in
  the log. To get Mod Studio's kit back, delete the folder and Build. (Thanks LaraCroft)

- **The shorts crest still lay on its side after the update (B213).** 0.2.4 turned the crest on
  the shorts of the kits Mod Studio draws, but a kit was drawn again only when the club's colours
  or crest changed, so every kit drawn before kept the old shorts. The next Build now draws such
  kits once more (a Switch on leaves them, so switching worlds stays quick; a world that came
  ready from a zip keeps the kits it brought). (Thanks Dolokhov)

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

- **A new league phase's Goal Ranking listed scorers of another competition (B193).** From the
  second season the table a league phase gets was used before, and its goal and assist lists
  were not emptied: the Conference League's league phase listed the Champions League's last
  round of 16 scorers. The lists of a league phase are now emptied at its draw, before any
  match is played.

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

- **Bring the game's leagues to this season a second time gave places back to the game's old clubs
  (B196).** A crest you set on a club that Bring had put in a game club's place (Bolton, Lanerossi
  Vicenza, JEF United Chiba ...) made Mod Studio treat that place as yours the next time you
  brought the leagues to a newer NewLife: the place was skipped and the game's old club came back
  under the new club's crest. Your change is now kept aside, the place goes to the same club again
  and gets your crest back; a change made for a club that no longer comes into that place goes
  with it.

- **A kit line added for a club on the Kits page left the club's old line on (B203).** A club of
  a pack (the Modpack's Arezzo, Pisa ...) then had two lines in `map.txt`, and Mod Studio said the
  first one counts, though Kit Server uses the last one. Adding or changing a club's line now
  switches its other lines off (#), **Import kits** with **Replace kits already set** replaces the
  line in effect, and the warning names the line that is not used. Stadiums, balls and goal songs,
  whose servers pick one of several lines, are left as they were. (Thanks JoJofiaz)

- **A new player made a keeper kept a midfielder's positions, and one copied from a keeper kept
  keeper abilities (B201, B202).** A new player is a copy of the player you had selected. Given a
  position over the goalkeeper line from that player, he now becomes a copy of a player of that
  kind from the same club, at the rating he had, and plays none of the other side's positions
  (no more 99 in a CF's skills to reach his rating). Build and the Player Editor do the same for a
  player moved over that line. (Thanks JoJofiaz)

- **A national cup of a big world stopped after its first round (B178).** Mod Studio keeps a
  country's cup to the clubs the game gives it when a league of yours sits below the top one, but
  it took only 16 such cups. In a world with more (the Europack has 18, the Modpack more), the
  rest were left to the game, which filled the Greek Cup with both Greek leagues, 30 clubs, played
  the first round and never the second: the next match showed in the calendar and was skipped.
  Up to 128 cups are now kept. Takes effect from the next season's cup draw in a career already
  started. (Thanks monkusgigus)

- **Competition Info > Copa Libertadores or AFC Champions League > Group stage crashed the game
  from the new year (B205).** The page reads each group's table from the cup's latest season, and
  from January that season is already open and holds no tables while the groups are being played.
  As for the cups of a world file (0.2.4.1), the Group stage item is left out while a group has no
  table, instead of crashing. (Thanks Micarodvzla22)

- **The same club played the Copa Libertadores and a continental cup of the world file in the
  same months (B204).** The game files the Libertadores on 1 January, the MLS's places included,
  and Inter Miami was already in the CONCACAF Champions Cup filled in August from the same
  league. A club from outside CONMEBOL that a cup of the world file already holds now keeps
  that cup, and its Libertadores place goes to a CONMEBOL club no continental cup holds.
  (Thanks Micarodvzla22)

- **The log filled with "creationflags is only supported on Windows platforms" (B210).** Mod Studio
  run from its source on a Mac (the game under CrossOver) asked Windows every few seconds whether
  the game was running, with a command a Mac has not got. It now takes the answer "not running"
  there and writes nothing to errors.log. (Thanks evannoteven)

- **No tables for the calendar-year leagues and no Libertadores or AFC Champions League groups from
  the third season of a big world (B211).** The game keeps every table of every season in one pool
  of 595, and a world of 86 leagues (the World Modpack) filled it with two seasons. On 1 January of
  the third season the leagues and cups played in a calendar year (the MLS, Brazil, Argentina,
  Japan, the Libertadores, the AFC Champions League and more, 41 in all) got no table, and the two
  cups drew their groups with nowhere to play them, so their knockouts had no club. When fewer than
  120 tables are free, the tables of a season two years old (2027/28 in 2029) are now given back
  from 17 December, the way the game frees them itself in July. The season under way is kept, and a
  world with tables to spare is left as it is. A career already in its third season gets the tables
  back from the next January.

- **The Champions League's league phase had no table from the third season of a big world, and its
  League Phase page crashed the game (B212).** After the July rollover the new European seasons
  took the last free tables of the pool, and the B211 fix gave back only seasons two years old
  until 17 December, so the Champions League was drawn in August with no table and Competition Info
  > League Phase crashed (ucrtbase 0xc0000409). From the July rollover on, a season that finished
  last year is now given back too, and not only when fewer than 120 tables are free, but also when
  fewer are free than the finished seasons hold (the new seasons need about as many). The season
  under way is kept, and a world with tables to spare is left as it is. A competition whose new
  season was already built short at the rollover (the Champions League got 3 of its 20 tables) is
  built again as soon as the tables are back. If a league phase is still drawn with no table, the
  Group stage item is greyed out instead of crashing the game.

- **A new Master League crashed mid-season (FL_2026.exe+0x1321d00) when the world's save folder held
  an Edit save of an older version of the world (B197).** That Edit save names players in its
  squads that the new version no longer has, and the game read the missing player without
  checking. fl26nullguard12 (in fl26guards) now skips such a player. Install a world zip also
  offers, after Ready to play, to move an Edit save from before the install aside, the way Build
  already did.

- **The Supercopa de Chile was played on the day of Copa Chile's second round (B198).** A super cup
  Build adds to a February-December league of the game was always on 31 January. It now takes a
  day at the end of January at least three days from the country's own cups (28 January for
  Chile). (Thanks antonimus)

- **Competition Info > Europa League or Conference League > League Phase showed "Group A" with no
  clubs (B206).** The page shows the table of the competition's latest season, and the game opens
  next season's empty table for those two cups months before the draw, while the knockouts are
  still being played. While next season's table is empty, the page now shows the league phase that
  was played; after the draw it shows the new one. (Thanks Micarodvzla22)

- **The Libertadores champion missing from the Club World Cup (B200).** When the game offered no
  entrant of a champion's confederation (the CONCACAF or OFC champion), our champion took the place
  of the last entrant on the list, and that could be another champion we had just put in: the
  Libertadores winner, the CAF champion. A champion now takes only the place of an entrant that is
  not a confederation champion, and the clubs of UEFA and CONMEBOL keep theirs. (Thanks
  Micarodvzla22)

- **First-season European clubs were left out of every new August-May career (B209).** A new
  career of a league that plays August to May is built on 1 July, and the list only counted for a
  career built from late July on, so it was always left out and the clubs came by squad strength instead
  (sider.log: "not a career built in this session"). A career built from 1 July counts now, and the
  summer's qualifying rounds already leave the listed clubs out. The day a career is built is also
  written to the save folder's `fl26swiss-state.bin` with the season's other keeps, so a career
  saved and continued after a restart still takes the list in its first summer. (Thanks Jabo9)

- **Mod Studio crashed at every start after Open a world... was given a world's
  leaguebuilder-plan.json (B224).** That file, in the folder of every built world, is the plan
  Build made, not a world file, and the next start opened it again and crashed counting its clubs.
  Opening it now opens the world it was built from, the way My world does for a world in the game;
  Save asks for a name, so the plan in the world's folder is never written over. (Thanks ferraz j.)

- **A Master League crashed in December (FL_2026.exe+0x135a384) when the game picked the clubs of
  next year's pre-season friendly cup (B223).** The pick takes clubs from a list of candidates
  until the cup is full and never checked that the list had run out; with too few candidates it
  read below the list. Seen three times out of three from one World Modpack career, day 346-348.
  fl26nullguard13 (in fl26guards) now stops the pick when the candidates are used up, and the
  game then fills or skips the cup the way it already does when a list is short.

- **A crash past Skip Match in the quarter-finals of a cup whose round was played before its
  slots were mended (B187).** A 0.2.4 career could play such a round with another season's clubs
  in its slots; the game then found only some of the winners, the semi-finals had no club and
  FL26 2.2 crashed. The round's winners are now worked out from the legs (goals, extra time,
  penalties, away goals) and put through. (Thanks Ibiss K.B.)

- **The national team you manage stopped stopping the hub (B20).** Every day the team of
  controller 0 was handed back to the computer except your club, so the national team's
  friendlies and qualifiers went by without you. Your national team now stays yours, and a save
  that lost it gets it back once when it is loaded. (Thanks Vicentico12)

- **Modern CONMEBOL: the Pre-Libertadores (B227).** Its phase 2 was on two days the game gives
  Copa Chile and Copa do Brasil, so a Chilean club had two matches on one day: it is on 18 and 25
  January now, and the Sudamericana's national first stage moves from 44 to 40 for the same
  reason. Before phase 2 was played the game's own entry list could put one of its clubs into the
  Libertadores' third qualifying round as well (Católica against Millonarios in the calendar);
  such a club is now kept out until phase 2's winners go in. The Pre-Libertadores matches wear the
  Libertadores' scoreboards, and its emblem is the game's own Copa Libertadores emblem, taken from
  your install at Build. Needs a fresh Build of the world. (Thanks antonimus)

- **NewLife: the same player twice, the game's one a free agent (B102).** NewLife 1.5b8 gives no
  game id for some 1100 players the game has (Elliot Anderson at Manchester City, the game's at
  Nottingham Forest), and each became a new player while the game's lost his club. A player with
  no id is now the game's when the full name, the age (a year either way), the height (3 cm) and
  the keeper/outfield side match, one of each; he moves to his NewLife club instead. Bring the
  game's leagues makes about 190 fewer copies with 1.5b8. (Thanks David.BDJ, JamesNotLike, Cala79)

- **Leagues > More > Competition IDs pointed scoreboards at the wrong column (B225).** Its note said
  scoreboards, kits and Sider's competition maps go by the Competition ID; they go by the regulation
  ids (sider.log's tournament_id: Liga FPD is competition 179, regulation 113, and the game asks for
  113). The pickers in Other content already listed regulation ids; the note now says so too.
  (Thanks Shawn)

## Read this first

- Everything in [0.2.4](changelog-0.2.4.md) still applies.
