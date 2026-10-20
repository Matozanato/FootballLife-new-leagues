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

## Fixed

- **The hub's Next showed a cup tie your club was not in** (Carabao Cup: Chelsea - Tottenham while Liverpool had been drawn against Brentford, as the news and Competition Info said). The hub reads its own list of your club's days, which the game fills when it makes the matches; when Mod Studio's cup draw (seeded, random or byes) or the European bracket order then gave the matches other clubs, that list kept the old pairing. The modules now ask the game to make the list again the next day, as the game does after a change of club. A season you already play is put right the next day after loading it. (Thanks pokuuuu.)
- **Clubs in no league in Other European teams turned up in the Champions League of Cup mode** (NK Hajduk Brezje, NK Jadran Stefanec ... among its clubs). Cup mode fills the last places of the Champions League from the game's Other European teams, and in a world whose leagues take the game's own such clubs (Dynamo Kyiv, Shakhtar ...), the clubs you put there are all that is left. The League window (Clubs in no league: Other European teams) and Build's log now say so; for small clubs choose **Classic Teams** instead. A world made before keeps its clubs where they are until you change the group and Build again. (Thanks ¥$)

## Read this first

- Everything in [0.2.4](changelog-0.2.4.md) still applies.
