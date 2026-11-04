# FL Mod Studio 0.3.0 — quick start (FL26 and FL27)

> **English** · [hrvatski](../hr/quick-start-0.3.0.md) · [español](../es/quick-start-0.3.0.md) · [português](../pt/quick-start-0.3.0.md) · [français](../fr/quick-start-0.3.0.md)

Everything you need to start with 0.3.0, in order. Every page and option in depth is in the
[user guide](mod-studio-guide.md); a ready world or Modpack zip is in [Install a ready pack](install-a-pack.md).

> [!WARNING]
> **0.3.0 is more of a test version.** If 0.2.5.1 works for you and you don't need FL27, there is
> no need to rush: stay on it until 0.3.0 has been played for a while. If you are in a long career,
> keep a copy of your save folder and your old Mod Studio folder before you update.

## 1. Get 0.3.0

**You have 0.2.5.1:** **Help → Check for updates...** → **Download and install**. Or close Mod
Studio and unzip `FL26ModStudio-0.3.0.zip` over the old folder (replace all). Your settings,
worlds and recipes stay.

**First time:** download `FL26ModStudio-0.3.0.zip` from the
[latest release](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest), unzip it
into a folder of its own (keep `_internal` and `pack` next to the exe) and run `FL26ModStudio.exe`.
If Windows says "Windows protected your PC": **More info** → **Run anyway**.

The window now says **FL Mod Studio**: the same program, renamed because it works with FL27 too.
The exe, the zip's folder and `%APPDATA%\FL26ModStudio` keep their names.

## 2. Pick the game: FL26 or FL27

1. **5. Settings → Game folder → Browse...** → the folder with `FL_2026.exe` (FL26) or
   `FL_2027.exe` (FL27) → **Use this folder**.
2. The first time a game is picked, Mod Studio unpacks that game's tables (a minute or two; the
   bottom bar says so). FL26 and FL27 keep their own tables and their own saves, so you can switch
   back and forth: pick the other game's folder the same way.
3. **1. Home**: when the Ready check says the modules are missing or older, press **Install now**.

## 3. Your world from 0.2.5.1 (FL26)

Your worlds keep working. After the update:

1. **1. Home → Install now** (0.3.0's modules).
2. **2. My world → Build and install** once.
3. Load your career and play on. Some fixes show only in a new Master League: transfer money of
   small clubs, NewLife squads, and the leagues on Select Team places 76, 77 and 80.

## 4. Real clubs: NewLife Database 1.6b4

Download NewLife 1.6b4 from the **#newlife** channel of our [Discord](https://discord.gg/StQqtk3G3M).
**In FL27 use 1.6b4** (or 1.6b3): older versions were made for FL26's clubs.

1. Put the parts (`NewLife-1.6b4-Europe.zip` ...) in one new folder, not mixed with older ones.
   Do not unzip the parts.
2. **2. My world → NewLife Database → Open NewLife Database...** → that folder.
3. **New leagues:** select one or more → **Add to your world**. A league of a country the game
   already has a league of (Greek Super League 2, Scottish Championship ...) goes in as the
   division under the game's league, with promotion and relegation; the page says which.
4. **Leagues you added from an older NewLife:** **More → Update my leagues to this version**.
5. **The game's own leagues** stay as the game has them. **More → Bring the game's leagues to this
   season...** moves their clubs and squads to the NewLife season, if you want that. Tick **Only
   the game's own players** to get only the transfers and ratings, no new players.
6. **Build and install**, then start a **new** Master League: an old save does not pick up new
   squads.

## 5. Make your own world

The full route, click by click: [Make your own leagues and packs](make-your-own-leagues.md). In short:

1. **2. My world → Leagues**: add a league (or NewLife leagues, step 4), set its country, clubs,
   **Division**, European places and cups with **Edit league...**.
2. **Division** can now be one of the game's split leagues too (Scottish Premiership, 3F Superliga,
   Jupiler Pro League): your league goes under it with promotion and relegation.
3. **Build and install**, then a new Master League.

## 6. Play

- **Start the game** (top right) starts the game with everything in place.
- **FL27: always start it through its launcher** (**FL 2027 start.exe**, its shortcut, or **Start
  the game** in Mod Studio). FL_2027.exe started on its own can close while a new Master League
  is created or on its first days.
- In FL27 the Champions League and Europa League are FL27's own; Mod Studio decides who gets in
  from your leagues and plays the summer qualifiers; the Conference League is Mod Studio's.

## 7. New in 0.3.0, and where to find it

| What | Where |
|---|---|
| FL27 support | **5. Settings → Game folder** |
| A league's clubs (with crests) in Select Team | in the game: Team Info, League mode ... with the cursor on a league |
| Coloured places in the league tables (Champions League, Europa League, Conference League, up, play-off, down) | in the game, after **Build and install** |
| A league in place of one of the game's "Other ..." groups in Select Team | **2. My world → Leagues → Places in Select Team** (each league: *Automatic* or *in place of* a group), then Build |
| A league under the game's split leagues | **Leagues → Edit league... → Division** |
| NewLife league under the game's league of its country | automatic on **Add to your world**; change it in **Division** |
| January-December leagues of a new country: promotion and relegation at New Year, and their cup | automatic after Build |

## 8. Something wrong?

1. **4. Tools → Diagnostics → Run the checks → Copy a report.**
2. Post it in **#support** on the [Discord](https://discord.gg/StQqtk3G3M) (one thread per problem)
   with a screenshot and `SiderAddons\sider.log` (the **Game** menu opens it).

Known in 0.3.0: [changelog](../../docs/changelog/changelog-0.3.0.md#known) ·
common questions: [FAQ](../../docs/faq.md)
