# FL Mod Studio 0.4.0 — quick start (FL26 and FL27)

> **English** · [hrvatski](../hr/quick-start-0.4.0.md) · [español](../es/quick-start-0.4.0.md) · [português](../pt/quick-start-0.4.0.md) · [français](../fr/quick-start-0.4.0.md)

Everything you need to start with 0.4.0, in order. Every page and option in depth is in the
[user guide](mod-studio-guide.md); a ready world zip is in [Install a ready pack](install-a-pack.md).
Coming from 0.2.5.1 or older? Read the [quick start for 0.3.0](quick-start-0.3.0.md) too.

## 1. Before you update

- **Keep a copy of your save folder and your old Mod Studio folder**, as always.
- **Install the modules again after the update: 1. Home → Install now.** Many fixes are in our
  modules in the game.
- **A running career keeps what its save holds.** New leagues, cups and clubs of an updated world
  come only in a new Master League. Your career goes on with the leagues it has.
- **New licence.** From 0.4.0 Mod Studio is under the FL Mod Studio License (`LICENSE.txt` in the
  zip). It stays free to use, change and share. Selling it and removing the "Powered by FL
  ModStudio" mark are not allowed. 0.3.0 and older stay under the MIT License.

## 2. Get 0.4.0

**You have 0.3.0:** **Help → Check for updates...** → **Download and install**. Mod Studio closes,
puts the new files in its folder and starts again.

**First time, or by hand:** download `FL26ModStudio-0.4.0.zip` from the
[latest release](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest).
Right-click it → **Extract All...** → a folder of its own (for example `Documents\FL26 Mod Studio`).
Don't run it from inside the zip, and keep `_internal` and `pack` next to `FL26ModStudio.exe`.
Double-click `FL26ModStudio.exe`. If Windows says "Windows protected your PC": **More info** →
**Run anyway**. Your settings, worlds and recipes are in `%APPDATA%\FL26ModStudio`, so they stay.

**Pick the game:** **5. Settings → Browse...** → the folder with `FL_2026.exe` (FL26) or
`FL_2027.exe` (FL27), not `SiderAddons` → **Use this folder**. The first time, Mod Studio unpacks
the game's tables: a minute or two, wait.

## 3. Your world from 0.3.0

1. **1. Home → Install now** (0.4.0's modules).
2. A world you build yourself: **2. My world → Build and install** once. Many fixes of 0.4.0 need
   a new Build.
3. Load your career and play on. New leagues, cups and clubs come only in a new Master League.

A ready world from a zip (GigaPack, a Modpack) needs no Build. When its maker gives you a new
version, install the new zip the same way as the first time (section 4).

## 4. GigaPack (Football Life 2027)

GigaPack by MatoZanato 1.0 is a ready world for **Football Life 2027**: 317 leagues and 5,239
clubs, in one zip, installed by Mod Studio, no Build needed. Downloads, md5, what it can't do yet
and the known issues: [GigaPack](../../docs/gigapack.md).

In short (you need FL27 with **update 1.1**; close the game and its launcher first):

1. Mod Studio 0.4.0, and the game folder with `FL_2027.exe` (section 2).
2. Don't unzip GigaPack. **1. Home → Import a world zip** → pick `GigaPack-1.0.zip` →
   **Install the world**. Wait for **Ready to play**. If it says **Almost ready**, it lists what
   to fix.
3. Green **Start the game** in Mod Studio (or FL27's launcher, not `FL_2027.exe` directly) →
   **Master League** → **New game**. Only a new Master League gets the new leagues.

## 5. New in 0.4.0, and where to find it

| What | Where |
|---|---|
| GigaPack 1.0, a ready world of 317 leagues for FL27 | [GigaPack](../../docs/gigapack.md) (section 4) |
| A world zip goes in at once | **2. My world → + Add... → Choose a file...** → the zip → **Install the world** |
| Import your world says whether a zip is a newer, an older or the same version of your world | **1. Home → Import a world zip** |
| An update of a world you share keeps its players' careers: Export asks for a version | **Export...** on the world's card in **2. My world**; FAQ: [Updating a shared world without breaking careers](../../docs/faq.md#updating-a-shared-world-without-breaking-careers) |
| A tab for cups: domestic cups and continental competitions | **2. My world → Cups**: **Game Countries**, **Our Countries**, **Continental**. **Apply**, then **Build and install** |
| Trophies, in FL27 too (FL27 not yet checked in the game) | **3. Game content → Trophies** |
| A third cup for the lower divisions (FL27) | **Leagues → Edit league... → Third cup (like the EFL Trophy)**, your own dates in **Cup days** |
| Leagues of up to 32 clubs (29 to 32 meet once); FL27 also takes 8 and 9. Not yet played through a whole season in the game | **Leagues → Edit league... → Clubs** |
| Your own order of a league's clubs in Select Team (FL27) | **2. My world → Clubs → More → Order in Select Team...** |
| A **Save** button for a player | **2. My world → Players**, beside **Undo changes to this player** |
| FL27: competition ids up to 1023 (FL26 stays at 255) | **COMPETITIONS** at the top of **2. My world**, after **1. Home → Install now** |
| Animations, and how to switch them off | **5. Settings → Program → Animations (pages, buttons and dialogs come in softly)** |

Everything else, with the fixes: [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md).

## 6. Something wrong?

1. **4. Tools → Diagnostics → Run the checks → Copy a report.**
2. On our [Discord](https://discord.gg/StQqtk3G3M): **#support** → **Open a support ticket** in the
   pinned post, with the report, a screenshot, `sider.log` and `sider.ini` (the **Game** menu opens
   both).

Known in 0.4.0: [known issues](../../docs/known-issues.md#open-in-mod-studio-040-2026-11-21) ·
what changed: [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md) ·
common questions: [FAQ](../../docs/faq.md)
