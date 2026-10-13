# What's new in Mod Studio 0.2.3

0.2.3 is a quick fix for 0.2.2, out the same evening.

## Fixed

- **Mod Studio closed during Build, with no message.** Some of the builder's checks stop the
  Build with a message of their own; in 0.2.2 that message took the whole program down instead
  of showing up. Build now stops with the message in a window, so you see what to change (or
  can send it to us).
- **Build stopped with "FL_2026.exe not found at C:\Football Life 2026".** With the game in any
  other folder, Build read the game's cup dates from the default folder instead of the one in
  Settings, and stopped there (in 0.2.2 this closed the program). The builder now uses the game
  folder from Settings for everything it reads from the game, and if the cup dates still cannot
  be read, Build goes on without them instead of stopping.
- **A crash now leaves a note.** If Mod Studio still closes on its own, it writes where it was
  to `%APPDATA%\FL26ModStudio\crash.log`. Send that file with your sider.log.

## Read this first

- Everything in [0.2.2](changelog-0.2.2.md) still applies: Install the modules, Build once,
  start a new career. 0.2.3 changes nothing in the game's modules, only the program.
- 0.2.2 was a big update and more bugs can still turn up. If Build stops with a message, post
  it in #support on Discord or open a GitHub issue, with sider.log.
