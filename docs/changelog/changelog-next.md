# What's new in the next Mod Studio update (not released yet)

The fixes of what you reported since 0.3.0. The version number and the date come when it is
released; until then this page only collects what is done and tested.

## Fixed

## Also new

- **Pick which of the game's "Other ..." groups a league replaces in Select Team** (vmican). Leagues > **Places in Select Team**: the Select Team column of each of your leagues is now a list, *Automatic* (as before: the order decides, the game's groups give their place last) or *in place of* Other European Leagues, Other Latin American Teams, Other Clubs (Africa) or Other. The next Build puts the league there whatever the order; that group's own clubs are then not in Select Team. With a South American world, for example, the Other Latin American Teams can make room for a league of yours. In a Master League started after that Build the league's clubs have the group's place too (Team Info lists them under the league; `fl26clubs` answers that slot from the league for the Master League club slot, `pick=1` in the world file).
