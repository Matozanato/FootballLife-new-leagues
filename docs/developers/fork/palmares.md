# The Palmarés of our competitions

The game keeps the user's titles in a *trophy cabinet* in the career block, and the Palmarés
(Manager > Records) shows it: one row per competition, with its count. The game writes the
cabinet for its own competitions and for most of ours. `fl26swiss.dll` writes what the game
leaves out, keeps one row per competition, and can repair a career's past titles from a file.
Nothing here needs a recipe key: it works for every world.

## The cabinet

| offset in the career block | what it is |
|---|---|
| `0x1798ab0` (`CAB_HDR`) | the header; the user's club first (a cabinet of another club is left alone) |
| `0x1798ca8` (`CAB_REC0`) | the records, `0x648` bytes each (`CAB_RECSZ`), in the order first won, up to the first one whose regulation is `0xffff`; they may run up to `0x17b0000` |

A record:

| offset | what it is |
|---|---|
| `+0` | `u16` regulation, `u16` 0 |
| `+4` | the winners: 200 `u32` clubs, `ffffffff` after the last |
| `+0x324` (`CAB_DAT`) | the dates of those wins, in the same order: `u16` year, `u8` month, `u8` day; empty is `ffff0000` |

The Palmarés counts the **dates** of a record, and shows **one row per record**. A Final del
Apertura won in 2025 and 2026 reads `05010000 0680ed45 0680ed45 ffffffff ...` and, at `+0x324`,
`e9070611 ea070611` (17 June 2025, 17 June 2026): "Final del Apertura 2". Two records of the same
regulation show as two rows of 1; a record with two clubs and one date shows 1.

## What the DLL does

All of it in `tools/native/fl26swiss.c`, section *the trophy cabinet*, once a day (`daychk`):

- **A title is in the cabinet** when the competition's record has a date of that year
  (`cab_has_year`). Nothing else decides it: the title marks of `fl26swiss-state.bin` outlived a
  career (a new Master League with the same club found "this year's title already written" and
  wrote none), and a save loaded from before the title has not got it.
- **A title the game did not write** (`cab_title_add`) goes on the lists of the competition's record
  (the club and the date), or into a record of its own after the last. A new record takes the last
  record's bytes as its model with **both lists emptied**: a copy that kept its model's dates showed
  "Supercopa 2" after one win (the model's date was of another year, so the next day's check
  did not find this year's and wrote it again). With no record at all in the cabinet yet, or no room
  left, nothing is written.
  - **A super cup of ours** (August-May: in July to November; January-December: in January to April):
    the game never writes it (it is registered outside the game's own stage run). Once its match is
    played and the game's rights code names the user's club, the title of this year is written,
    dated today. Before this, a second win was never added (a record of that super cup among the
    last three records counted as "this season's").
  - **The final of a league play-off with groups** (`ccup ... adv=1`, the Apertura's or the Clausura's
    final): with another knockout of ours running (the modern Copa Sudamericana's round of 16), the
    game wrote no title for the Final del Apertura. From three days after the final (up to 300,
    `FINAL_FIX_DAYS`), while its knockout still names the winner, the title of the final's year is
    written with the final's date. A new record is a copy of the cabinet's last one; when that final
    is the career's first title, the cabinet's first slot is written as it is, its lists emptied (a
    record is the regulation, the 200 winners and the 200 dates, and four bytes after them that stay
    the slot's own). Before, nothing was written until a second title had made a record, and sixty
    days were too few for that.
    The winner is the game's own (`ccup_ko_winner`), never one kept in the state file: that file is
    shared by every career of the club, and the DLL must never give a title this career did not win.
  - **The league title of a final of two cups** (`src=`, the Final del FUTVE) when one club won both
    and the final is not played: the same `cab_title_add`, from `honours_fix`.
- **Two records of one competition** of ours (a super cup, the knockout of a cup of ours) are merged
  (`cab_merge`): the second's winners and dates go on the end of the first's lists and the records
  after it move up one. Winners without a date (an old merge) are dated (`rec_dates_fill`).
- **The palmarés file** (`cab_file_apply`): `fl26swiss-palmares.txt` beside `fl26swiss-state.bin`
  (`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\`) repairs a career's past titles,
  one line a competition:

  ```
  256 2026 2027 2028
  ```

  Each listed year is made sure of on that competition's record (the user's club, dated 31 January);
  a date of a year that is not listed and before the last listed one is dropped (a copy's wrong date);
  later titles are not touched. A competition the cabinet has not got is left. The file is read once,
  by the first career loaded after it is put there, and then renamed to `fl26swiss-palmares.txt.applied`,
  so it never reaches another career.

The log says each of these (`fl26swiss: trophy cabinet -- ...`, `fl26swiss: palmares file -- ...`),
and `fl26swiss: cabinet -- day N: ...` lists the records whenever they change.

## Tests

`tools/test_palmares.py` builds `tools/native/test_palmares.c` (see [testing.md](testing.md#the-c-tests))
and runs it on a career block of its own: dates, a title on an existing record and on a new one,
the same year twice, a full region, a merge, winners without a date, and the palmarés file.

## Known limits

- The first title of a career whose cabinet is still empty cannot be written by the DLL (a record
  needs a model). The game's own titles fill it first in practice.
- The Palmarés row's name and logo are the competition's (`Competition.bin`, its emblem); the DLL
  only writes the cabinet.
