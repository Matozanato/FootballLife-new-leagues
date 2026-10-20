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
- **Undo and Redo of the last change to your world.** Two buttons in the bottom bar next to "Your
  world is saved", and Ctrl+Z / Ctrl+Y when no text box is in use: up to 30 steps back. New world
  or Open starts again with none.

## Fixed

- **Home > Last changes: rows painted over each other (B83).** While a message box was open (the one
  after Install the modules), the list of last changes was drawn on top of the old one until you
  went to another page. The same in the world cards, the pack ticks and the league crests. (Thanks
  David)
- **A deleted world came back at the next start (B107).** After Delete world and New world (left as
  it was), Mod Studio opened the deleted world again when it started, because New world and Open did
  not change which world the next start opens. It now opens the one you had open. (Thanks jibibi)
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


## Read this first

- Everything in [0.2.4](changelog-0.2.4.md) still applies.
