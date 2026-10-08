# The NewLife release format

This page describes a NewLife release as Mod Studio reads it: which files it opens, which
columns and keys it uses, and how the ids work. The code is `tools/modstudio/newlife.py` (the
release as leagues), `pages/newlife.py` (the page) and `leaguebuilder.newlife_tids` /
`pin_newlife` (world ids). A fork that wants to read releases, or to make its own data in the
same shape, needs only this page.

Releases are downloaded on their own. They are not in this repository. Mod Studio copies
nothing from a release except into the recipe a person builds, plus the crests and league
logos it unpacks to its cache.

## Whole or in parts

A release comes in one of two shapes:

- **Whole:** a folder (usually `newlife-<version>/`) with `players.csv`, `clubs.csv` and
  `newlife.json`.
- **Parts:** `NewLife-*.zip` files, one per continent or piece of one. Each zip has the
  same three files for its own clubs, and its `newlife.json` has `"part": {"name": ...}`. A
  person downloads the parts they want into one folder and opens that folder. The parts are
  read where they are, without unpacking.

`find()` also looks one folder deeper, because a download is often unpacked into a subfolder.
**Every part must have the same `version`.** A folder that mixes versions is refused.

A release can also carry pictures, in the folder or inside the zips:

- `crests/<club newlife_id>.png`: club crests;
- `logos/*.png`: league logos, each one named in `newlife.json` under `league_logos`.

The ones a recipe uses are unpacked to `%APPDATA%\FL26ModStudio\newlife\<version>\crests|logos\`,
and the recipe points at those files.

## `newlife.json`

| key | read by Mod Studio | meaning |
|---|---|---|
| `name` | yes | shown with the version (`NewLife Database 1.3`) |
| `version` | yes | the release version; parts must agree; written into the recipe (`newlife.version`) |
| `part` | yes | `{"name": ...}` in a part |
| `league_logos` | yes | `[{"file": "logos/x.png", "country": "<Country.bin id>", "league": "<league name>"}]` |
| `format` | no | `1` |
| `player_ids`, `team_ids` | no | the id ranges used, as `[[lo, hi], ...]` |
| `blocks` | no | the id blocks the release keeps to: `{"players": [400000, 999999], "teams": [98304, 114687]}` |
| `counts` | no | players, clubs, and how many of each the game already has |
| `files` | no | sha256 of `players.csv` and `clubs.csv` |
| `made_from` | no | where the data came from (free text) |

Mod Studio ignores keys it does not know, so a release may carry more.

## `clubs.csv`

UTF-8, with a header row:

| column | meaning |
|---|---|
| `newlife_id` | the club's id in the release. For a club the game has, this **is** the game's team id |
| `in_game` | `1` when the game already has the club, else `0` |
| `name` | the club's name |
| `country` | `Country.bin` id of the club's country |
| `league` | the league's name. `country` + `league` together make one league on the NewLife page. A club with no league is in no league list |
| `home_kit`, `away_kit` | shirt words, `"<pattern> #rrggbb #rrggbb #rrggbb"` (for example `plain #cd1018 #cd1018 #080808`), the same form as a recipe's `club_kits` |

## `players.csv`

UTF-8, with a header row, one player per row:

| column | meaning |
|---|---|
| `newlife_id` | the player's id in the release. For a player the game has, this is usually the game's player id. Other players are numbered from 400000 up (`blocks.players`) |
| `game_id` | the game's player id when the game has him, else empty |
| `name` | the player's name |
| `birth_date` | the birth date (not used by Build; `Age` is) |
| `club_id` | the `newlife_id` of his club. A player without one belongs to no squad |
| everything after | the 97 fields of `tools/playeredit.py` (`FIELDS`), by their names and in its CSV texts: `Registered Position`, the position ratings (`GK` ... `CF`), `Height (cm)`, `Weight (kg)`, `Age`, `Nationality`, `Stronger Foot`, the abilities, `Playing Style`, the skills and the AI styles |

A field left empty keeps the value of the placeholder player whose place the player takes.
Values are checked at Build, like any `players` edit in a recipe ([recipe-keys.md](recipe-keys.md)).

## What Mod Studio does with it

- **Leagues.** Clubs are grouped by `(country, league)`. A league's new clubs are those with
  `in_game` = 0. Its `in_game` clubs stay where the game has them. They can be brought into the
  league as clubs of the game (`game_clubs`). Within a country, leagues are sorted by
  strength, the mean `overall` of their best players.
- **Squads.** A club gets its best `SQUAD` = 30 players, with at most three goalkeepers
  (`Release.squad`).
  - Ranking uses `lbplayers.overall`, a mean of the abilities each position leans on.
  - A club the release has fewer than 18 players for (`MIN_SQUAD`) keeps placeholder
    players up to 18. They are brought to the club's level and given names made from the
    league's own players.
- **Players the game has.** A player whose `game_id` is in the person's tables, under the same
  name, moves to the club with a `join`. He keeps his face and id and takes the release's
  fields. If his old club would drop below 18 players, or an earlier league already took him,
  he stays where he is and is left out of the new club. Any other row becomes a new player.
- **Club ids.**
  - NewLife ids of new clubs (98304..114687, `NEWLIFE_TEAMS`) only identify the club, in
    the recipe's `newlife.clubs`.
  - The club's id in the world is given out at Build by `newlife_tids`, after the builder's
    own clubs and at most `CLUB_ID_MAX` = 81919.
  - `pin_newlife` writes it into the recipe's `newlife_ids` so the club keeps it when other
    leagues change. Kit and crest packs keyed on the world id keep working.
- **Updates.**
  - *Update my leagues to this version* reads a newer release and replaces the clubs and
    squads of every league that came from an older one. The league's own settings, and what
    the person set for a club that stays, are kept.
  - *Bring the game's leagues to this season* moves the game's own clubs between the
    game's leagues as the release has them, and gives them the release's squads. What it
    changed is kept in the recipe's `newlife_game`, so it can be undone exactly.

## Making a release in this format

- Keep the three file names and the column names exactly as above.
- Keep `version` the same in every part.
- Use the game's own ids for clubs and players the game has. For everything new, use ids
  inside the `blocks` ranges, so they never collide with the game's or with a world's own clubs.
- Keep `country` as `Country.bin` ids and the shirt words in the form above.
- A crest goes in `crests/` under the club's `newlife_id`. A league logo goes in `logos/` and
  must be listed in `league_logos`, or it is not found.
