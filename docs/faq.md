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

For the rest, edit the world's data files with `tools/players.py`, the same way
`rename.py` does clubs. The players live in the world's `common\etc\pesdb\Player.bin`, and
which club each one plays for, with his shirt number, in `PlayerAssignment.bin`.

**1. Find the players.**

```
python tools\players.py --root <your livecpk world> --list --club 72318
```

prints every player of that club: player id, team id, shirt number, name. `--club` also takes
the club's name as `rename.py --list` prints it. Without `--club` you get every player in the
file, including the game's own, which is how you find a player to copy from (step 2).

**2. Write what should change.** A CSV file with a header line:

```
player,name,like,shirt
180573,Ivan Example,,9
180574,,1624,
180575,Marko Example,1624,10
```

- `player`: the player id from the list (or the player's current name if no one else has it).
- `name`: the new name. It is used for all four name fields the game has (full name, shirt,
  on-screen, printed). Up to 60 bytes.
- `like`: the id of another player to copy the playing side from: position, abilities,
  skills, playing style. The player keeps his own id and his name. Leave it empty to keep
  the player as he is.
- `shirt`: the shirt number, 1 to 99.

Leave any column empty to keep that part as it is.

**3. Apply it.**

```
python tools\players.py --root <your livecpk world> --edit edits.csv
```

If any line is wrong (a player or source that does not exist, a name too long, a shirt number
out of range), nothing is written. The original files are kept as `Player.bin.bak` and
`PlayerAssignment.bin.bak`.

**Why copy instead of typing numbers?** Every new squad is already a copy: `mkplayers.py`
clones one of the game's own squads and renames it, so all new clubs start with the same
players. Changing a player by copying another whole player gives the game a record of the
kind it already reads. Setting single ratings is not offered, because the ability data is
only partly understood. The ratings are not labelled yet, some of them do not decode cleanly,
and the player's position is stored right next to them, so a wrong write can turn a whole
squad into goalkeepers. That happened to us once. Copying a whole player cannot cause it.

**Then start a new game.** A Master League career takes its own copy of the squads when it
starts, so a career you are already in keeps the old players. Start a new career, or a Kick
Off match, to see the changes. If an old `EDIT00000000` is in your save folder, move it aside
first, for the reason given in the first question.

Changes to the files are not tested in every screen of the game. If something looks wrong,
put the `.bak` files back and open an issue.
