# Questions people ask

## How do I rename the new clubs?

The new clubs are called `FL 0001`, `FL 0002` and so on because that is the pattern
`mkworld.py` gives them. There are two ways to change that.

**When you build the world.** `mkworld.py --club-name "My Club %04d"` changes the pattern for
every club it makes (`%04d` is the club's number). `--league-name` does the same for the leagues.
Use this for a different naming style, not for individual names.

**Afterwards, one club at a time: `tools/rename.py`.** The names live in the world's
`common\etc\pesdb\Team.bin`. That file is packed, so a hex editor will not work on it. The
tool unpacks it, changes only the name and the three-letter abbreviation, and packs it again.
Squads, kits, competitions and ids are not touched.

```
python tools\rename.py --root <your livecpk world> --list
```

prints every club in the file: team id, abbreviation, name. Write a CSV file with one club per
line: the team id (or the current name), the new name, and optionally a new abbreviation:

```
72318,Dinamo Example,DIN
FL 0002,Hajduk Example,HAJ
FL 0003,Only The Name Changes
```

and apply it:

```
python tools\rename.py --root <your livecpk world> --names names.csv
```

A name may be up to 69 bytes. The abbreviation must be three plain letters or digits. If any
line is wrong (a club that does not exist, a name that is too long), nothing is written, so a
typo never leaves a half-renamed world. The original file is kept as `Team.bin.bak`.

These are the same two fields `mkworld.py` fills in when it names the clubs. The tool changes
nothing the builder does not already write.

**After renaming, check your Edit save.** If you have
`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\EDIT00000000` from before the
change, the game reads it instead of the data files and keeps showing the old names. Move it
somewhere safe (do not just delete it if it holds edits you care about), start the game, and
let Edit mode write a new one. From then on the new save carries the new names.

## Do the new clubs show up in the game's Edit mode?

It depends on which league a club is in.

- **Clubs added to a league the game already has: yes.** Measured on 2026-09-11 with ten clubs
  added to the Premier League. In Edit > Teams > Premier League the list scrolls past
  Wolverhampton to the new clubs, and each one can be opened and edited like any shipped club.
- **Clubs in a new league of our own: not through the league lists.** Edit mode's list of
  leagues is fixed inside the game, not read from the data files. A new league never appears in
  it, whatever id it has, and neither do Edit > Competition Structure or Edit > Competitions. So
  the clubs of a new league cannot be reached from their league there. We have not checked
  whether some other Edit screen, such as a search or an "other clubs" list, reaches them in the
  current version. If you find one, please open an issue.

The new leagues and their clubs do show up where it matters for playing: Kick Off > League,
Master League's Select Team list (with `sider/experimental/fl26comptab.lua` and
`fl26slotnames.lua`) and, with `fl26catlist.lua`, Database > Competition Info.

The same rule about the Edit save applies here too. After you rebuild a world, move the old
`EDIT00000000` aside before deciding that a change did not work. An Edit save written before a
data change hides that change.

## How do I edit the players of the new clubs, if not in Edit mode?

Edit mode reaches a club through its league, so players of a club in a new league cannot be
reached there (see the question above). Players of clubs you added to a league the game
already has can be edited in Edit mode as usual.

The easiest way is the editor with a window:

```
python tools\playereditor.py --root <your livecpk world>
```

Pick a club, pick a player, change any field, **Apply**, **Save**. **New player** creates one,
**Up** / **Down** change the squad order (the green rows are the starting eleven). It uses the
same checks as the spreadsheet route below.

For many players at once, edit the world's data files with `tools/playeredit.py`, the same way
`rename.py` does clubs. The players live in the world's `common\etc\pesdb\Player.bin`, and
which club each one plays for, with his shirt number and his place in the squad, in
`PlayerAssignment.bin`. Every field of a player is known (see
[player-record.md](player-record.md)), so you can set any of them, and create new players.

**1. Export the club to a spreadsheet.**

```
python tools\playeredit.py --root <your livecpk world> --export club.csv --club 72318
```

writes one line per player of that club with every field under its own name: position,
position ratings, height, weight, age, nationality, foot, the 25 abilities, form, injury
resistance, playing style and the skills, plus club, shirt number and squad order. `--club`
also takes the club's name as `rename.py --list` prints it. Without `--club` you get every
player in the file, including the game's own, which is handy to look up a nationality or a
playing style to copy.

**2. Change what you want** in Excel, LibreOffice or any text editor, and save it as CSV
(UTF-8). You can delete the columns you do not change; an empty cell leaves that field alone.

**3. Import it.**

```
python tools\playeredit.py --root <your livecpk world> --import club.csv
```

Every line is checked first: a rating outside 40-99, an unknown position, a height the game
cannot store, two players with the same squad order. If anything is wrong, nothing is written
and you get the whole list. The original files are kept as `Player.bin.bak` and
`PlayerAssignment.bin.bak`.

**Creating a player.** Write `new` in the `player` column and name the club:

```
player,club,like,name,shirt,Registered Position,Speed,Finishing
new,72318,180590,Ivan Example,27,CF,84,86
```

The new player starts as a copy of the player in `like` (or of the club's first player) and
then takes every value on the line, so fill in as many columns as you like. He gets a new
player id, the shirt number you gave (or the first free one), and the last place in the squad.

**The starting eleven is the first eleven of the squad order.** The formation gives them
their places in a fixed order. For the new clubs' default 4-2-3-1 that is order 0 to 10 =
GK, CB, CB, RB, LB, DMF, DMF, RMF, LMF, AMF, CF. To change who starts, change the `order`
column (every player of a club needs a different number). If a goalkeeper sits at order 1
he will start at centre back, which is what a squad written in any other order looks like.

`tools/players.py` still does the three quick jobs it always did (rename, shirt number, copy
a whole player from another) with a four-column CSV; `playeredit.py` does all of that too.

**Then start a new career.** A Master League career takes its own copy of the squads when it
starts, so a career you are already in keeps the old players. If an old `EDIT00000000` is in
your save folder, move it aside first, for the reason given in the first question.

Tested in the game on 2026-09-24: a club's whole squad rewritten this way showed the right
names, positions and ratings in Select Team and Game Plan, and played a Master League match.
If something looks wrong, put the `.bak` files back and open an issue.
