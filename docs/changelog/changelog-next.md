# What's new in the next Mod Studio update (not released yet)

The fixes of what you reported since 0.3.0. The version number and the date come when it is
released; until then this page only collects what is done and tested.

## Fixed

- **The super cup of a February-December league of ours was not played** when the country's cup had
  already been drawn for its new season on New Year's day (the Supercopa de Venezuela of a second
  Master League season): the game names last season's cup winner no more by then, and the super cup
  was left out without a word. The cup module now keeps the cup's winner and runner-up from its
  final on, and the league's final table, and fills the super cup with them; when it still cannot,
  the log says why.
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

- **Apertura and Clausura from February to December.** A new country's top division playing
  February to December can now be Apertura/Clausura, as the real Liga FUTVE: the Apertura from
  February to May, the Clausura from late July to October, each with its playoffs of two groups and
  its final, the grand final in December, the cup through the year and the super cup at the end of
  January. Build lays every day clear of the national teams' windows, the Libertadores and the Club
  World Cup; Edit league > Days by hand sets any of them. For now with a grand final, one such league
  in a world, 16 clubs at most. Recipe keys: `season: "calendar"` with `apertura`, `calendar_days`.
- **Continental places in the order of the finals.** For a February-December Apertura/Clausura
  league with the modern CONMEBOL, Edit league > continental places in the order of the finals: the
  champion, the best of the table, the runner-up and the next to the Libertadores, the two finals'
  losers and the next two to the Sudamericana, as the real Liga FUTVE. Off, the table's order (a
  fase 5 world gets its order back with this option). Recipe key: `places_order`.
- **The trophy ceremony for a new league's finals.** Edit league > Trophy ceremony: the league's
  national cup and super cup, its playoffs' finals and its grand final end with the trophy and the
  celebration, like a big final of the game (a two-legged final after its second leg). Recipe key:
  `ceremony` ([futve-playoff.md](../developers/fork/futve-playoff.md)).
- **Cinematics for a new league's finals.** Edit league > Cinematics: for the cup, the super cup,
  the playoffs' finals and the grand final, a folder of your cinematics packs (LIB, UEFA Champions
  League F ...): that final takes its entrance, scenes and ceremony. Install the modules puts the new
  module `fl26cine` before the packs' `common\cinematics.lua`. Recipe key: `cinematics`.
- **A grand final for Apertura and Clausura leagues, in Mod Studio.** With playoffs of two groups of
  four, Edit league > Grand final: the Apertura's and the Clausura's final winners meet after the
  Clausura's final, over two legs or one match, and the winner is the league's champion -- the title
  with the league's name in the Palmarés, the super cup. A club that wins both finals is champion
  without it, and the table's leader gets no title. Any number of such leagues in one world. Recipe
  key: `apertura.grand_final` ([futve-playoff.md](../developers/fork/futve-playoff.md)). A world
  built without it does not change.
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
