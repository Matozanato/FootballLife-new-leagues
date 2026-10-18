# What's new in the next Mod Studio update (not released yet)

The fixes of what you reported since 0.2.4 (2026-10-18). The version number and the date come when
it is released; until then this page only collects what is done and tested.

## Fixed

- **Kits on FL26 1.0 without the game's updates (B153).** Build said "only pictures changed since
  the last Build" or "no kits: the game's UniformParameter.bin was not unpacked", and the new clubs
  played in blank kits. FL26 1.0 keeps its kit list only in the game's Data archives, and Unpack the
  game's tables read just download\. It now takes it from Data too (the updates' own list still goes
  over it). Tables an older Mod Studio unpacked without it: Build asks once to unpack them again.
  (Thanks ZeDosCaes21)
