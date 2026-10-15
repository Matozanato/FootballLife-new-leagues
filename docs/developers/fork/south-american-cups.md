# South American cups (recipe keys, not in Mod Studio yet)

A world can play the CONMEBOL season as it is today: Libertadores qualifying phases 1 and 2, a
pre-Sudamericana of 16 one-match ties, the Sudamericana groups with the qualifying losers, the
Sudamericana play-off (runners-up v Libertadores thirds) and the Recopa in late February. It
works on the game's own leagues and clubs; no new league is needed.

Mod Studio has no screen for it yet, so it is built from a recipe file with `leaguebuilder.py`.

## Install (about 10 minutes)

What you need: the game with Sider, [Python 3](https://www.python.org/downloads/) ("Add
python.exe to PATH" ticked when installing), and this repository downloaded (green **Code**
button -> **Download ZIP**, then unzip it).

1. **Close the game.**
2. Open a command prompt (Windows key, type `cmd`, Enter) and go to the repository's `tools`
   folder, for example:

   ```
   cd /d C:\Users\you\Downloads\FootballLife-new-leagues-main\tools
   ```

3. Unpack the game's tables (once, takes a few minutes; change the path to your game folder):

   ```
   python -c "import leaguebuilder as B; B.unpack_tables(r'C:\Games\FL26', 'tables')"
   ```

4. Build the world from the example recipe:

   ```
   python leaguebuilder.py build ..\docs\developers\fork\south-american-cups.recipe.json --base tables\common\etc\pesdb --game "C:\Games\FL26"
   ```

   The last line says `built ...\livecpk\_FL26SouthAmerica`.
5. Switch it on:

   ```
   python leaguebuilder.py on _FL26SouthAmerica --game "C:\Games\FL26"
   ```

   The modules must be a release that has this (its `fl26swiss.dll`): Mod Studio's **Install
   modules** puts them in place. Before such a release, build the pack yourself with
   `tools/lbpack.py` (docs/developers/fork/building.md).
6. Start the game to the main menu, close it, and check:

   ```
   python leaguebuilder.py check --game "C:\Games\FL26"
   ```

   It ends with `the world works as built`.
7. **Start a new Master League.** A career begun before the switch does not get the cups.

To go back, switch on your previous world (`on <its name>`) or use Mod Studio.

## The recipe keys

The example recipe is the one tested in game. The keys:

| key | what it sets |
|---|---|
| `libertadores_qualifying` | `{"phase1": [...], "phase2": [...]}`. Each entry is `[league, position]`, `["team", id]` (a club of the game by team id, also the Outros America clubs) or `["game8"]` (the next club the game's own rights send). Phase 1 is an even number of clubs; phase 2 gets phase 1's winners and must come to 16. Days 6/11 and 18/27. |
| `sudamericana_first_stage` | 32 clubs in 16 one-match ties: `[league, first position, clubs]` (a regulation id of the game, e.g. 67, 168, 30) or `["team", home, away]`. Played on day 44. |
| `sudamericana_playoffs` | default `true`: Sudamericana runners-up v Libertadores thirds, days 146/153, before the round of 16. |
| `samerica_super_cup_first` | `[Libertadores winner, Sudamericana winner]` team ids for the first season's Recopa; later seasons use the real champions. |
| `ccup_logos` | optional pictures: `{"9": "C:/path/sudamericana.png", "-1": "C:/path/recopa.png"}`. |

Leagues that send clubs to these cups keep their rounds off the cup days. Every New Year
`sider.log` has a `season clash audit` line: clubs with two matches on one day (0 expected).
