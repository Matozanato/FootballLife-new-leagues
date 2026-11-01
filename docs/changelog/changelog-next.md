# What's new in the next Mod Studio update (not released yet)

The fixes of what you reported since 0.3.0. The version number and the date come when it is
released; until then this page only collects what is done and tested.

## Fixed

- **A super cup of ours won again showed the first title only.** The Palmarés counts a competition's
  dates, and the DLL took a super cup's record among the last three for "this season's" title, so a
  second or third win was never added; a record it made itself copied the dates of the record
  before it ("2 Supercopas" after one). Each win is now added once, dated, on one record. See
  [palmares.md](../developers/fork/palmares.md).
- **The final of a league play-off with groups gave no title** when another knockout of ours was
  running (the Final del Apertura in June, with the modern Copa Sudamericana's round of 16). The DLL
  now writes it three days after the final, if the game's own result names your club -- also when
  it is your career's first title (it waited for a second title before, sixty days at most).
- **A competition of ours in the Palmarés twice ("1" and "1" instead of "2")** is merged into one row.

## Also new

- **Apertura and Clausura playoffs of two groups of four, in Mod Studio.** Edit league > Format has,
  next to the playoff size, "a knockout" (as before) or "two groups of four": the 8 clubs play two
  groups (1st, 4th, 5th, 8th and 2nd, 3rd, 6th, 7th), home and away, and the two group winners meet
  in a one-match final. Each final is a competition of its own, so its winner gets its own title in
  the Palmarés, with the final's name and logo. The playoffs and their finals can be named (Playoff
  names, Final names) and the finals have their own logos. Recipe keys: `apertura.playoff_format`,
  `apertura.names`, `apertura.logos`
  ([recipe-keys.md](../developers/fork/recipe-keys.md), [futve-playoff.md](../developers/fork/futve-playoff.md)).
  A world built without them does not change.
- **A league play-off with its own group stage (0.2.5, the Liga FUTVE).** A world file's `ccup` line
  takes `gdays=<day>,...`: the groups are dealt in the order of `entry=` (the world file writes
  group A's clubs first) and dated on those days, instead of a draw and the Libertadores' calendar.
  `adv=1` sends only the winner of each group to the knockout, which is then the final; the better
  placed club of the regular phase goes first (at home in the match record). The final's row is a
  normal cup's (the FA Cup's, cut to two clubs), so the calendar and the match screens call it
  "Final", and `kolike=<shipped cup>` is the shipped cup whose calendar dates it (the Belgium Super
  Cup's, one match). The group stage is filled the day after a split phase ends and
  started and registered the way a qualifying round is (`fl26_swiss_ccup_gdays`, `_adv`, `_kolike`).
  `tools/futve_world.py` builds the cup in a world's tables, `tools/futve_fixture.py` makes the
  Táchira-99 test fixture and `tools/futve_test.py` is the in-game sandbox of the tests; the
  design is in [futve-playoff.md](../developers/fork/futve-playoff.md).
