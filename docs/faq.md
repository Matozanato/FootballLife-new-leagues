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
