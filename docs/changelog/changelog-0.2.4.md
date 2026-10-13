# What's new in Mod Studio 0.2.4

0.2.4 is the second quick fix for 0.2.2, out the same evening as 0.2.3.

## Fixed

- **Build stopped with "FL_2026.exe not found at C:\Football Life 2026".** With the game in any
  other folder, Build read the game's cup dates from the default folder instead of the one in
  Settings, and stopped there (in 0.2.2 this closed the program). The builder now uses the game
  folder from Settings for everything it reads from the game, and if the cup dates still cannot
  be read, Build goes on without them instead of stopping.

## Read this first

- Everything in [0.2.2](changelog-0.2.2.md) and [0.2.3](changelog-0.2.3.md) still applies.
  0.2.4 changes nothing in the game's modules, only the program.
- More bugs can still turn up. If Build stops with a message, post it in #support on Discord
  or open a GitHub issue, with sider.log (and crash.log if there is one).
