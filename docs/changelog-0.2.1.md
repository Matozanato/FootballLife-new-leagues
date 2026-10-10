# What's new in Mod Studio 0.2.1

0.2.1 is a **quick interim update**. Its main job is to fix the Master League / Be a Legend
crash that came with the 0.2.0 package. A bigger fix update (the calendar, January-December
leagues joining their season, the Conference League knockout and more) comes later.

## Read this first

- **The crash when you create a Master League or a Be a Legend career is fixed.** The 0.2.0
  package carried an old `fl26caps.lua` (sider.log says `3520 patches`). Install the modules
  (Install page, or Build does it) and sider.log says `3502 patches`. If you already put the
  fixed file from Discord in, you have the same file.
- Your worlds and careers made with 0.2.0 stay as they are. No new Build is needed for the fix.

## Fixes

- Master League / Be a Legend creation crash (the old `fl26caps.lua`, GitHub #122, #125).
- A world with only cups (no leagues of its own, no changes to the game's leagues) builds
  again instead of stopping with `no Player.bin`.
- A split or Apertura/Clausura league no longer takes the regulation whose Select Team slot is
  the Copa Libertadores'.
- A recipe made on another PC: a crest, logo or flag picture that is not on this PC no longer
  stops Build. The club gets the drawn badge and Build log says which picture was missing.
- Mod Studio no longer crashes at start when a `.bin` in the tables folder is not one of the
  game's tables (a patch's files copied over them). It says so and you can pick the tables
  again in Settings.
- An older league package with an empty "exchange" field no longer stops Check the plan.

## New in packages and kits

- **Add a package: take only what you want.** A package of several leagues lists them ticked,
  untick the ones you don't want. Under "What to take" untick parts too (squads, faces, crests,
  managers, kit colours, kits, scoreboards, stadiums), e.g. to take only the scoreboards from
  one package and the squads from another. This works for the FL26 Modpack too.
- **League packages carry Kit Server kits and Scoreboard Server scoreboards.** Both are
  ticked in Make a package and can be unticked. Kits and scoreboards make a package bigger
  (about 10 MB of kits and 7 MB of scoreboards a league), so it can go over Discord's limit.
- **Kits for new clubs.** New clubs without kits of their own get home, away, third and
  goalkeeper kits made from their colours and crest (Build page: "Make kits for the new
  clubs", on by default).
- **A partial database** (a mod's pesdb with only Team.bin/Player.bin) can be picked in
  Settings: its files go over the game's unpacked tables.
- Settings explains better what the game's tables are for and when to use another folder.
