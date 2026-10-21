# What's new in Mod Studio 0.2.5

0.2.5 is being prepared (not released). If 0.2.4 needs a second round of fixes, these may
come with it instead.

## Added

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

- **The African and Asian cups had no knockout from the second season (B172).** The CAF and AFC
  cups of a world (the Modpack's five) kept last season's clubs after the summer, and a cup that
  still held clubs counted as drawn: its groups were never drawn again, stayed out of the new
  season and had no table ("group A has a table of 0 rows"), so the knockout was never filled.
  A cup is now drawn anew once a season when neither it nor its groups are in the season, its
  old groups emptied first, and its groups get the season's tables the way the game makes them.
- **The Champions League's round of 16 not drawn after two seasons with full tables (B169).**
  When two seasons of the league phase both had 36 rows, the older table could be read; the
  latest season's is now taken.

## Read this first

- Everything in [0.2.4](changelog-0.2.4.md) still applies.
