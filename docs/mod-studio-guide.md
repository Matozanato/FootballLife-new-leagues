# FL26 Mod Studio — user guide

> Common questions (updating, crashes at start, cups, promotion, what to send when something is
> wrong): [faq.md](faq.md) · questions and help on [Discord](https://discord.gg/StQqtk3G3M)

FL26 Mod Studio is one program for everything you add to Football Life 2026:

- **mods** you download: stadiums, kits, balls, scoreboards, commentary, music, faces, Lua modules;
- the **content servers** that serve them (Stadium Server, Ball Server, Kit Server and the rest),
  with their map files edited as tables instead of by hand;
- the **Sider setup** itself: which content folders and modules are on, and in what order;
- **new leagues and clubs** (the League Builder), your changes to the game's own leagues, clubs
  and **players**, and **league packages** a modder makes once and anybody adds to their game.

Nothing of the game is overwritten. Before the program changes a file it keeps a copy, and every
mod it installs can be removed again.

---

## 1. Before you start

- **Football Life 2026** installed, with its `SiderAddons` folder (FL26 comes with Sider).
- Unzip the program anywhere, e.g. `Documents\FL26 Mod Studio`. Keep the folder together: the
  `_internal` and `pack` folders and the `README` files stay next to `FL26ModStudio.exe`.
- **Close the game** while you change things. Sider reads its setup when the game starts.

The window is in English. **Settings → Language** switches it to Croatian (Hrvatski), Spanish
(Español) or French (Français).

## 2. First run

1. **Settings → Game folder**: press `...` and pick the folder that holds `FL_2026.exe`.
   The line under it says whether `SiderAddons\sider.ini` was found.
2. If you want new leagues or player changes: **Settings → Unpack the game's tables**. It
   reads the game's clubs, leagues and players into a working folder (a few seconds). Do it
   again only after a game update.
3. Open **Overview**. It shows your setup at a glance and lists problems. Double-click a
   problem to open the page that fixes it.

**Updates.** A few seconds after it starts, the program asks GitHub whether a newer FL26 Mod
Studio is out, and says so only when there is one. **Download and install** fetches the new zip,
checks it against the release's checksum, closes the program, puts the new files over the old
ones and starts it again. Your settings, projects, restore points and the game are not touched.
**Help → Check for updates** asks at any time; untick **Help → Check for updates at start** and
the program asks only then. If the program sits in a folder Windows will not
let it write to (such as Program Files), it opens the release page instead: unpack the zip
yourself, or move the program to a folder of your own.

**Credits.** The **Credits** button next to **Help** lists everyone who helped make Mod Studio:
the testers, the people who sent reports and logs, and the ones whose ideas are in it.

**More than one Sider folder?** Sider does not have to be called `SiderAddons`. The program
looks for the folder next to `FL_2026.exe` that holds a `sider.ini`, and one level further
down too (`sider\patch 1`, `sider\patch 2` ... when one folder holds a few Sider copies). If
there are several, **Settings → Sider folder** chooses which one it works on; the others are
not touched.

## 3. The pages

The list on the left has four groups.

| Group | Pages |
|---|---|
| **Manage** | Overview, Install mods, Content folders, Lua modules, Profiles, Restore points |
| **Game content** | Stadiums, Kits, Balls, Commentary, Music, Other content |
| **League Builder** | NewLife Database, New leagues, New clubs, Game's leagues and clubs, Players, League packages, Build |
| **Tools** | Diagnostics, Settings |

## 4. Install mods

Drop a downloaded mod on **Install mods** (`.zip`, `.7z`, a folder, `.lua`, `.cpk` or
`.fl26pack`), or use **Choose a file...**.

The program looks inside and lists each part: what it is and where it will go.

| Part | What happens |
|---|---|
| Content folder (livecpk) | Copied to `SiderAddons\livecpk\<name>` and added to `sider.ini`. |
| Content server files | Copied into the server's `content` folder. Its **map file is merged into yours**: your lines stay and the mod's new lines are added. For a club you have already mapped, the choice next to **Install** decides: *use the mod's*, or *keep mine, add the mod's after*. |
| Lua module | Copied to `SiderAddons\modules` and switched on in the right place of the order. |
| Packed .cpk | Unpacked into a content folder on install. |
| League package | Added to your League Builder recipe (section 9). |
| DLL | **Not installed.** A DLL runs with the game's rights; install one only from a source you trust, by hand. |

Give the mod a name, choose whether new content folders go on top (they win) or at the
bottom, tick what you want and press **Install**. The list below shows every mod installed with
the program. **Remove the mod** deletes the files it added and puts back the files it replaced.

## 5. Content folders and Lua modules

**Content folders** lists every `cpk.root` line of `sider.ini`. Sider looks a file up from the
top down, so the folder higher in the list wins when two have the same file.

- Tick or untick a folder to switch it on or off (the line is commented out, never deleted).
- **To top**, **Up**, **Down** change the order; **Add folder...** adds a folder you already have.
- The size and what is inside (faces, kits, stadiums...) are shown for each folder.
- Nothing is written until you press **Apply**. **Discard** forgets the changes.

**Lua modules** is the same for the `lua.module` lines. The program knows the right order for
the common modules (content servers after the modules they use) and says so when a module sits
in the wrong place. Some modules need a Sider setting (for example Goal Song Server needs
`match-stats.enabled = 1`); the program says which.

Modules of the League Builder keep the order they were installed in.

## 6. Game content: the content servers

**Stadiums, Kits, Balls, Music, Commentary** and **Other content** (scoreboards, menus, referee
kits, sleeve badges and weather) each belong to one content server. Every page has:

- a **status line**: is the module on, is its content folder there;
- a tab per **map file**, shown as a table: which competition, club or stadium gets what.
  Add, change, switch off (the line becomes a comment) or delete rows; pick items from the
  library instead of typing ids. **Save** writes the file; the copy before it goes to Restore
  points;
- the **Library**: what is in the server's content folder, with pictures where there are any.
  Items that no map line uses and map lines that point at missing items are marked;
- **Settings** of the server where it has any (favourite stadium, ball, scoreboard ...).

The program checks the tables before saving: a number where a number goes, no commas inside a
name, an item that exists.

**Import kits...** (0.1.8, on the *Kits* page): kits for many clubs at once. Pick a folder of ready kit-server kits -- one folder per club, holding `p1`, `p2`, `g1` ... and `order.ini`, named after the club (`Dinamo Zagreb`) or its team ID (`2215`). The list shows every match with a tick; untick a wrong one before **OK**. The kits are copied into the kit-server library (`League\Club`, as the folder had them) and each club gets a line in `map.txt`; **Save** writes it. A club that already has a line keeps it unless **Replace kits already set** is ticked. A new League Builder club's kits go by the team ID Build gave it, so Build the world and keep it switched on first. Mod Studio does not make kits: the textures (`.ftex`) come ready from a kit maker.

## 7. Profiles

A profile remembers which content folders and modules are on, and in what order. Keep one for
Master League, one for online play, one for testing:

- **Save current setup...** stores what is on now under a name.
- **Switch to it** puts that setup in `sider.ini` (the old `sider.ini` goes to Restore points).
- **Update with current setup** overwrites the profile.

## 8. League Builder: new leagues, clubs and players

The League Builder adds new leagues to the game and changes the game's own. What it makes is a
**world**: a content folder named `_FL26...` that the game reads while it is switched on.

**New leagues → Add league**

| Field | What it means |
|---|---|
| **Name** | The league's name in the game. No two the same. |
| **Country** | Gives the flag and where the league is listed. A country the game has no league for gets a heading of its own. |
| **Clubs** | 10 to 24. |
| **Format** | *Everyone plays everyone*, 1 to 4 times, *splits in two (Scottish style)*, or *Apertura and Clausura*: two tournaments a season (September to early January, January to May), each from zero points, then playoffs of 8 or 4 clubs (or none). The whole season's table decides promotion and relegation. 18 clubs at most. A split is 46 rounds at most, before and after the split together (16 clubs twice is 30, so its biggest group twice can be 8 clubs, 14 rounds). One league per country can be split or Apertura/Clausura for now. |
| **Division** | *(top division)*, or the league above it: another new league, or one of the game's. To put a new league under another new league in one step: select it and press **Add lower tier** (it takes the country, club count, format and up/down of the league above; only the name is left). |
| **Up / down** | How many clubs change places with the league above at the end of the season. |
| **Season** | Top division of a new country only: *August to May* (the default) or *February to December*, like Brazil, Japan or Saudi Arabia: clubs go up and down at New Year, and the divisions below it follow it. Not with a split, Apertura/Clausura, a national cup or a league cup yet. |
| **Europe** | Top division only: which league position goes to which European competition. **Top flight: 1st UCL qualifying, 2nd UEL, 3rd UECL** fills the usual three (*... qualifying* are the August play-offs, see 8.2); **Add place**, **Remove place** and **Clear** for anything else. Each position once, and only positions the league has. Below 1 the position reads **Cup winner** (0.1.7): the winner of the country's cup (a new country needs **National cup**) -- and when the winner already has a European place through the league, the place goes down the league to its next club, as UEFA does it. A league of the game can have one too (*European places of the game's leagues*). Leave it empty for a lower tier. The preset follows the country: Asia gets the AFC Champions League and AFC Champions League Two, South America the Libertadores and the Copa Sudamericana, Africa the CAF Champions League and CAF Confederation Cup. Those four cups the game does not have are built with the world (section 8.2). A *Libertadores qualifying* place takes the place of a club of the game in the qualifying round (the last one of the country with the most clubs in it), at most six of its eight places; **Check the plan** says which leagues are left out past that. |
| **Logo** | Any picture (PNG with a transparent background looks best). Empty: one is drawn for you. |
| **Country flag** | Your own picture of the country's flag, stretched into the game's flag frame. It replaces the game's flag of that country everywhere (Select Team, players' nationality, the country's heading in Database > Competition Info) while the world is on. Empty: the game's own flag. |
| **Cup** | Top division only. **National cup**: the country gets its own cup, with the name you give (empty: `<league> Cup`). The game fills a country's cup from its top division and the division below it, and the cup's size follows the National cup row of the Limits (8.3): the largest size the cup screen draws that fits, so a field of 22 gives a cup of 20, the top division first. Past 44 clubs the cup keeps the top division alone. A new second division under a country the game already has (Germany, Russia ...) goes into that country's cup too, after the top division's clubs, when the cup's rounds fit the field. A new third division or lower (League One under the Championship) leaves the country's cup to the game's top two divisions, as in the game. **Super cup**: also a one-match super cup before the season, the champion against the cup winner. |
| **League cup** | Top division only. A knockout of 16, 8 or 4 clubs of this league and the one below it, by league position, the strongest against the weakest: two legs a round, the final one match, September to December. The clubs past 16, 8 or 4 play a pre-round first (0.1.7): the last places, the strongest against the weakest, two legs on 4 and 7 September; the winners take the cup's last places, against its strongest clubs. A league of 20: 1st to 12th straight into the last 16, 13th to 20th in four pre-round ties. Give it a name or leave it empty (`<league> League Cup`). |
| **Cup logos** | A picture for the national cup, the super cup, the league cup and the Apertura/Clausura playoffs, each on its own. Empty: an emblem with the cup's initials is drawn for it. |
| **Exhibition only -- not in Master League** | For Kick Off and exhibition matches: a historical league, legends and the like. Its clubs never play a Master League season, so the league stands alone: no division above or below, no European places, no cups. It still shows in Master League's team list; pick your own club from another league. |
| **Formation** | How the league's clubs line up. Pick one of the formations the game's clubs use (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ...; the list says how many clubs of the game play it): each new club gets a copy of the tactics of a club of the game with that formation, and its best eleven is lined up for it at Build. Empty: the game's default, a fixed 4-2-3-1. A single club can have its own (**Edit club**). |

**World name** (on the same page) must start with `_FL26`. After **Build** the **League ID** column
shows each league's competition id in the game, the one its logo file carries.

**Pre-season cups** (button on the same page): friendly knockouts of 4 or 8 invited clubs in July, before the season, paired in the order you give them (first against second ...). A club is one of a new league or a club of the game (its id); at least one has to be from a new league, and its country hosts the cup. A career starts in August, so the first one is played in the second season. Each cup can have a **Logo**; empty: one is drawn for it.

**Cups of the game's countries** (same page): a league cup -- the Carabao Cup, say -- for leagues of the game. Tick **League cup** next to a league: 16 clubs of it and the league below it, by position (the clubs past 16 through a pre-round in early September, 0.1.7), one match a round from late September to December, on days the game's league and cup calendar leaves free. **Super cup**, the champion against the cup winner in late July, only where the game has none (Brazil, Chile, Scotland, Greece, the USA); a new career has no cup winner yet, so the first one is played in the second summer. Empty name: the league's name and *League Cup* / *Super Cup*.

**European places of the game's leagues** (same page): which positions of the Premier League, LaLiga, Serie A ... go to which European competition. The list shows the game's own places; tick **Own places for this league** to change them. A league not ticked keeps the game's places, a ticked league with no rows sends nobody.

**UEFA ranking** (same page, 0.1.7): every European league of the world -- the game's and your
new top divisions -- in one list, strongest country first. Drag a league (or **Up** / **Down**)
to change the order, untick one to give it no European place, **UEFA's order** puts the list back
to UEFA's association ranking for 2026-27. The right side shows what each league gets, and
**OK** writes it: the places of UEFA's key for 2024-27 -- rank 1 has five Champions League
places, rank 6 two and a play-off place, rank 30 one place in the Champions League's second
qualifying round, and so on, the cup winner's Europa League place included. A world never has all 55 of UEFA's countries, so
the places of the ranks it does not have go to the next clubs of the strongest leagues in turn,
one round at a time, and every competition stays full: with twelve leagues England's 6th, 7th
and 8th go to the Champions League qualifying, say. Past the 30th league there is no place left, and
the list says so. The qualifying places go to the rounds in the key's order, the strongest
country to the round nearest the league phase. Afterwards you can still change any league's
places by hand (*Europe* on the league, *European places of the game's leagues*): Build takes
the places, not the ranking.

**South American places** (same page, 0.1.7, read only): for every South American league, the
game's four and yours, which positions go to the Copa Libertadores, its qualifying round and the
Copa Sudamericana. The game's Libertadores places are its own (Brazil 1st-4th and the Copa do
Brasil winner, qualifying 5th-6th, and so on -- the same the game's Competition Info shows); the
Copa Sudamericana is Mod Studio's, so the list shows how many clubs each of the game's leagues
sends to it with your places in: your leagues first, then Brazil, Argentina, Chile and Colombia
one club each in turn until 32. A club already in the Libertadores or its qualifying gives way to
the next one of its league. **Check the plan** prints the same list whenever the world has a
Libertadores or Sudamericana place.

**Competition names** (same page): a new name and logo for the game's cups, super cups and continental competitions -- the FA Cup, the Champions League, the Libertadores ... -- and for the continental cups the world builds (CAF Champions League, Confederation Cup, AFC Champions League Two, Copa Sudamericana, CAF Super Cup). Every stage of a competition takes the name. Empty: the game's own. The game's leagues are renamed on *Game's leagues and clubs*.

**New clubs**: pick the league, then **Edit club** (name, short name, crest), **Paste names...**
or **Load names from file...**. An empty name becomes `<league> 01`, `<league> 02` ...; a club
with no crest gets a numbered badge. Kits are lent from the game's own clubs. Such a kit is a
licensed one, and Edit mode will not change it ("You cannot edit this strip"): tick **Kits you
can edit in the game** on the Build page and the new clubs borrow none, each wears a plain kit
that Edit > Teams > Strip changes like any other club's, Paste Image included.
Names keep their letters (FK Željezničar); the three-letter short name has none, as in the game,
so Č, Ž, Đ become C, Z, D there. After **Build** the **Team ID** column shows each club's id in
the game.

**Manager**: in **Edit club** of a new club you can name its manager. Empty: a numbered one (`FL M0001` ...). **Manager picture** under it gives the manager a portrait (the same as **Manager portrait...** on the Players page); *Game's leagues and clubs* > **Edit club** has it for the game's clubs too.

**Formation**: in **Edit club** of a new club you can give it a formation of its own; *As the league* keeps the league's. The pitch under the list shows where everyone stands.

**Home stadium** (0.1.7): in **Edit club**, a stadium of Stadium Server's library for the club; the slot and the name are filled in from the folder, change the name if you like. It is written to Stadium Server's `map_teams.txt` when the world is switched on (and when the live world is built again), so a new club's id never has to be looked up. A line of your own for the same club is switched off meanwhile, and on again when the club no longer has one here. *Game's leagues and clubs* > **Edit club** has it for the game's clubs too. Stadium Server has to be installed (the *Stadiums* page).

**Clubs the game already has.** A place of a new league can hold one of the game's clubs instead
of a new one: select the place, then **Club of the game...**, and search by name or team ID
(**Only clubs in no league** narrows the list). The club keeps its name, crest, kits, manager and
players, and plays in your league only. When it plays somewhere in the game (a league, a cup, the
Europa League ...), you pick who takes its place there: a club of the game that plays in nothing,
or a new club you name. A pre-season tournament (the *Pre-season friendly Cups* of SPFL26) does not count: the club keeps playing it, as the Premier League's clubs do (0.1.7). **Edit club** on a club of the game changes its name, crest, manager's portrait and stadium, as on *Game's leagues and clubs* (0.1.7). That way no competition of the game changes its number of clubs; the
game's leagues keep their dates only with the number they were made for. National teams, the
classic and default teams and clubs with fewer than 18 players cannot be picked. **New club
here** gives the place back to a new club. The club no longer shows under the Master League's
*Other ... clubs* groups.

**Insert club** and **Remove club** add a place before the selected club or take one out (10 to
24 clubs); names, crests, managers and player changes move with their clubs. Check the league's
European places, then **Build** again. Any change to a league's clubs needs a **new career**.

**Move to another league...** (0.1.7) takes the selected new club to the end of another new league, with its name, short name, crest, manager, formation, kits, NewLife id and player changes; the league it leaves keeps one club less. A club of the game moves with **Club of the game** instead: take it out of one league, put it in the other.

**Game's leagues and clubs**: new names, logos and crests for what the game already has.

**Import crests...** (0.1.8, on this page and on *New clubs*): crests for many clubs at once. Pick a folder of pictures; each is matched to a club by its file name -- the club's name (`Alianza Lima.png`, `alianza_lima_r_l.png`) or its team ID (`2287.png`, the crest packs' `e_2287_r.png`). The list shows every match with a tick; untick a wrong one before **OK**. A club that already has a crest keeps it unless **Replace crests already set** is ticked. The pictures stay in that folder and Build reads them from there, so keep it. (Matching by name is an idea from Xxspedd's crest script.)

**Swap leagues with a club...** (0.1.7): two clubs of the game's leagues trade places -- a promoted club for a relegated one, a club of one country's league for one of another's. Each takes the other's places in the league, the cups and the European competitions, so every league of the game keeps its number of clubs. A club in a new league of the recipe cannot swap too. **Undo club changes** takes the swap back. Then **Build** again and start a new career.

> **Edit file.** If the game's save folder has an Edit file (`EDIT00000000`), it overrides club
> names. Move it somewhere else to see your names.

### Players

**Players** changes the squad of any club: the new clubs of the recipe and the game's own.
Pick a club (or press **Players** on New clubs), then a player:

- **Name**, **shirt number**, **position** and the positions they can play (A = natural,
  B = can play there), stronger foot, height, weight, age, nationality, playing style;
- all **abilities** and **skills** (the names are the game's own);
- **Rating**: the rating of the list, made of the abilities the position leans on. Changing
  it moves every ability of the player by the same amount. A player of a new club has no
  name until the Build numbers him (FL P00001 ...); type one in **Name** to give him yours;
- **Face**: **Choose...** a face folder (section 8.1). **Clear** gives the game's face back. A
  new player without one gets a face of the regen face pack that fits his nationality, with its
  portrait (0.1.5.5, with the modules installed);
- **Portrait**: **Choose...** a picture (PNG or JPG) for the player's small portrait in the squad
  lists, without a face of his own. Build makes it 180 x 180; it wins over a face folder's portrait;
- **Order up / Order down**: the squad order. The first eleven start the match;
- **Add player** (a copy of the player you pick, with a new id; clubs of the game only),
  **Remove from club** (a new club keeps at least 18 players);
- **Best eleven** puts the strongest player at every place; **Squad level...** raises or
  lowers every ability of the whole squad;
- **Pitch** (new clubs): the first eleven in the club's formation. Select a player in the list,
  then click a place to put him there; whoever stood there takes his place in the squad order;
- **Export CSV... / Import CSV...**: edit a squad in a spreadsheet. Export first, change the
  cells, import the same columns back.
- **Import a squad from a table...**: any table of players becomes the club's squad -- one
  typed by hand, a squad list copied off a website, a Football Manager or EA FC export. The
  columns are recognised by their names (name, position, age or birth date, nationality,
  height, foot, shirt number, overall, and any ratings) and shown so you can fix one that is
  wrong. What the table does not have comes from the game's own players of the same position
  and rating; Football Manager's 1-20 ratings are stretched to the game's 40-99. The table's
  players take the club's places in squad order: a new club keeps its 30 places (fewer
  players = the rest leave, down to 18), a club of the game gains or loses players to match.

Every change is written into the world when you **Build**; the game's files stay as they are.
**Undo changes to this player** and **Undo all changes of this club** go back to the game's.

The club list also has **National teams** and **Other clubs (no league)**: the teams the game keeps outside any league (national sides, clubs that only play a cup or a continental competition). Their players are edited the same way.

#### Transfers, national teams, ids, the manager's portrait

- **Sign players...** (a club): a list of every player of the game and of your new clubs, with
  a nationality filter and a name search; pick several with Ctrl or Shift. They move to this
  club: their old club loses them (a transfer). **Transfer to...** does the same from the other
  side: the selected player moves to the club you pick. The list shows *from ...* on the club
  that gets him and *to ...* on the club he leaves; **Remove from club** on either row calls the
  transfer off. A club has at most 40 players.
- **Call up players...** (a national team: pick *National teams* in the league list): the list
  opens on the team's country. The players join the national squad **and stay at their clubs**,
  as in the game. **Remove from club** drops a player from the national squad (not from his
  club). A national team has at most 26 players; a player is in one national team at a time.
  Your squad is written into the game's data, but in a Master League career the game picks its
  own national squads, so there your call-ups do not stay.
- A player who joins goes to the end of the squad order with a free shirt number; the squad he
  left closes its order up.
- **Player ID** column: every player's id -- the game's own, the one you typed, or the one the
  last **Build** gave a new player (build once before you make minifaces or faces for new
  players). **Export CSV...** writes it as `player_id`; Import CSV ignores that column.
- **Club ID** (next to the club) and **Player ID** (Basics tab): for your **new** clubs and
  players only. Empty = the next free id at Build. Type one when a kit, crest or face pack was
  made for a certain id. Club ids: from the first id after the game's clubs (71578) up to 81919;
  player ids: above the game's highest up to 399999; never one the game or another new club or
  player already has. The id is used everywhere the world refers to the club or player (squads,
  competitions, kits, crests, manager, faces). The game's own clubs and players keep their ids:
  its kits, faces and your saves are tied to them.
- **Manager portrait...**: a PNG or JPG for the club's manager. Build makes it 256 x 256 and puts
  it at `common/render/symbol/coach/coach_<manager id>.png`, the game's own place for manager
  portraits. Press it again to take the picture away.

### 8.1 Faces

A face mod is a folder like this (the way face makers share them):

```
<any name>\
    #Win\face.fpk
    #Win\face.fpkd
    sourceimages\#windx11\*.ftex
    portrait.dds            (or <id>.dds, optional)
```

Choose that folder for a player. At **Build** the face is copied into the world and pointed at
the player, so it works for a new player whose id did not exist when the face was made, and it
never replaces a face of the game. Without a portrait the small player picture in the menus stays
the empty outline; the face itself still shows. A folder with more than one face inside is refused: pick the
one face you mean.

### 8.2 Build, switch on, play

**Keep the world's own Team.bin.** It is in the world folder and holds the world's clubs and its play-offs. Replacing it with the game's own Team.bin drops both, and the line-ups only look fixed because the world's clubs are gone (GitHub #75). Build the world again instead.

**Build**:

0. **Install the modules** — once, and again after a new version of the program. Files it
   replaces are kept in `SiderAddons\modules\before-builder-1\`.
1. **Check the plan** — what will be made; nothing is written.
2. **Build the world**.
3. **Switch it on** — makes it the active world in `sider.ini`.
4. Start the game, come back and press **After a start: check**. It reads `sider.log` and says,
   module by module, whether the world was taken.

**Include the Conference League** (on the Build page, on by default) also builds the
Conference League: a league phase of 36 clubs and a February play-off, like the other two. The
Champions League and the Europa League get their league phase of 36 and their February play-off
either way. Off: no Conference League. (Mod Studio 0.1.3 and earlier left the Champions League and Europa
League in the game's groups of four when this was off, which the mod cannot run -- they broke;
Checks flags such a world: build it again.) **Conference League logo** next to it: your own picture
for it; empty: a UECL emblem is drawn (the game has none for it). **Conference League name**
under it: what the game calls it, *FL Conference League* when empty (type *UEFA Conference
League* if you like); a new name needs the world built again. Both are used by **Only the new
European cups...** too.

> **European places.** The places you give your leagues come after the ones the game's own
> leagues have. Each competition takes 36 clubs; places past the 36th get nothing, and
> **Check the plan** says so. New leagues with no places send nobody to Europe, and Overview
> warns about it. The title holders come first: the Champions League and Europa League winners
> take two of the Champions League's direct places, the Conference League winner one of the Europa
> League's. The league-phase draw follows UEFA's rules: no club meets a club from its own
> country, and at most two of its opponents come from any one other country.
>
> **The August qualifying.** A *qualifying* place puts the club in the August qualifying of
> that competition: up to three rounds (0.1.7) -- the second qualifying round (days 220 and 225),
> the third (229 and 236) and the play-off (243 and 250; the Champions League's 244 and 251) --
> each of 16 clubs over two legs, the eight strongest squads seeded (second leg at home), two
> clubs of one country kept apart. Winners go on to the next round, from the play-off into the
> league phase. Losers drop as UEFA's do: *Champions League qualifying*'s play-off losers to the
> Europa League, its third round's to the Europa League play-off, its second round's to the
> Europa League third round; *Europa League qualifying* the same way into the Conference League;
> *Conference League qualifying*'s losers are out. The first places listed go to the play-off,
> later ones to the earlier rounds. How many rounds a world gets follows from its places, and
> every Conference League round needs 8 clubs more: 116 places in Europe for the three
> play-offs alone, 132 for all nine rounds. With the game's own places it is the play-offs
> alone; Build's summary says which rounds a world gets (*August qualifying*). Every play-off
> takes 8 places off the direct entrants of the competitions its winners and losers go to: with
> all three, the Champions League takes 28 clubs directly, the Europa League and the Conference
> League 20 each. A place past those is played in that competition's qualifying. Your leagues'
> qualifying places come before the game's (Portugal, Scotland, Greece, Denmark ...).

Then **start a new Master League** (or Become a Legend) career. The new leagues are under their
country in Select Team and Kick Off. In the Kick Off and Edit lists a new Asian country comes
before *Other Clubs (Asia)*, a South American one with the game's (after Colombia, before MLS,
0.1.7), a CONCACAF one after MLS, and African and Oceanian ones (the game
has no section for them) after Asia.

> **Other continents' cups.** When your leagues send clubs to the CAF Champions League, the
> CAF Confederation Cup, the AFC Champions League Two or the Copa Sudamericana, **Build**
> makes those cups too. Each gets 32, 16, 8 or 4 clubs: your leagues' places first, then the
> game's own leagues of that continent (Asia and South America) fill it. With 8 or more it
> plays groups of four and then a knockout; below 8, a knockout only. They are filled at the
> end of August, from the league tables. A club already in the Copa Libertadores, its
> qualifying round or the AFC Champions League is not drawn into them. A CAF cup with fewer
> than 4 places takes the next CAF cup's places first (with two and two, the CAF Champions
> League gets all four), then the next positions of your leagues. **CAF Super Cup** (Build
> page, on by default) has the winners of the two CAF cups meet once in late July, from a
> career's second season on.

> **Saves belong to a world.** A career saved with one world on needs that same world to load.

**File → Save recipe** stores everything in a `.json` file; **Open recipe** brings it back.
**Build** also keeps a copy of the recipe in `%APPDATA%\FL26ModStudio\recipes\<world>.json`,
and Mod Studio opens the last recipe again when it starts, so closing it without saving loses
nothing that was built.

**Only the new European cups...** (Build page) builds a world with nothing but the new
Champions League and Europa League -- league phase of 36 and the February play-off -- and the
Conference League when **Include the Conference League** is ticked. No new leagues; the game's
clubs and leagues stay as they are, and your recipe is not changed. It asks for a world name
(`_FL26Euro` by default), builds it and offers to switch it on. Only one world can be on, so it
is instead of a world with new leagues: a world with new leagues already has the new format.

> **Exhibition leagues and Master League.** A league ticked *Exhibition only* never plays a
> Master League season, but the game has one team list for Kick Off and Master League, so its
> clubs still show when you pick your club for a new career. Do not start a career with one of
> them. **Check the plan** and **Build** say so.

### 8.3 Limits

| | |
|---|---|
| New leagues per world | 39 |
| Clubs per league | 10 – 24 |
| New clubs in all | 793 |
| Times clubs meet | 1 – 4 |
| Split leagues | 2 per world |
| Divisions in one country | down to the 7th |
| Players per new club | 30 at the start; remove down to 18; signed players bring it up to 40 |
| Players per national team | 26 |
| National cup | the top division and the one below, up to 44 clubs. Up to 32 the sizes are 2-16, 18, 20, 24, 28, 30 and 32 -- the largest that fits (22 clubs give a cup of 20); 33 to 43 become 32; 44, or a size a shipped cup has, stays; more than 44: the top division alone |

### 8.4 NewLife Database: real clubs and players

The NewLife Database is a separate download with real clubs and players for new leagues: names,
birth dates, positions and ratings on the game's scale, and the clubs' colours. Every club and
player in it has an id of its own that stays the same in every version of the database. It is
not on GitHub: get it from the NewLife channel of our [Discord](https://discord.gg/StQqtk3G3M).
It comes in parts, one per continent (a big one in more than one), plus *Free agents*, each
under 10 MB. Download only the parts you want.

1. Put the parts you downloaded in one folder. Do not unpack them: Mod Studio reads the zips as
   they are. (They are LZMA zips: 7-Zip opens them, Windows' own zip viewer does not.)
2. **League Builder > NewLife Database > Open NewLife Database...** and pick that folder. The list
   shows every league of those parts: country, clubs, clubs the game already has (*In game*),
   players and level. Click a league to see its clubs.
3. Select one or more leagues (Ctrl or Shift for more) and press **Add to the recipe**. Each
   becomes a new league with its clubs and their squads, the top division of its country. Change
   its division, format, European places and the rest on *New leagues*, like any other league.
4. **Build**, switch the world on and start a new career (section 8.2).

- **Your own line-up** (0.1.7): untick a club in the list on the right to leave it out, and
  **Add a club from another league...** to bring in clubs of any league of the release -- this
  season's first division is last season's with two promoted clubs, say. The league's row gets a
  `*`. A club can be in one league of the recipe only.
- A league takes 10 to 24 clubs, its new clubs and the game's own together; the others are grey. The line at the bottom counts the new clubs
  of the recipe against the 793 a world takes.
- Clubs the game already has join the new league as clubs of the game (section 8, *Clubs the
  game already has*), in its last places, with their own names, crests, kits and players. One
  that also plays a competition of the game (Basel and Young Boys play the Europa League) needs
  the club that takes its place there: *New clubs*, pick it, **Club of the game**. Build says
  which ones until then.
- A player the game already has (the same player under the same name, Urbański at Górnik in
  the game and at Legia in NewLife, say) moves to the NewLife club instead of being made a
  second time (0.1.7): he keeps his face, name and id and takes NewLife's position and ratings.
  He stays where he is when his old club would drop below 18 players, or when an earlier league
  already took him; then he is left out of the NewLife club, not copied (0.1.7.2).
- A NewLife club takes a world id of its own (0.1.7.2), in the block the game reads for clubs,
  counting up after the ids the builder gives its own clubs. The **Club id** column on New clubs
  shows it, and a Kit Server's `map.txt` is keyed on it. A world built before 0.1.7.2 must be
  built again and the career started new for the kits to follow. From 0.1.8 a club keeps the id
  of its first Build (the recipe remembers it): removing, adding or updating another league no
  longer moves it.
- **A newer NewLife version** (0.1.8): put its parts in a folder (not mixed with the old ones),
  **Open NewLife Database...** that folder and press **Update my leagues to this version**. Every
  league you added from an older version is listed with what changes (*16 clubs now, 18 in
  NewLife 1.3 (5 new, 3 not in it)*) and a **Keep my clubs** box: ticked, the league keeps its
  clubs; unticked, it gets the clubs it has in the new version. Either way the squads come from
  the new version, and the league keeps its name, division, format, European places and cups; a
  club that stays keeps its manager and a crest you picked, and clubs of your own you put in the
  league stay. Player changes you made on *Players* for those clubs are replaced. Then Build and
  start a new career.
- A NewLife club gets a shield crest in its colours and the kit of the game closest to its
  colours, until you give it your own (**Edit club**).

## 9. League packages: share a whole league

A modder makes a league once — clubs, names, crests, logos, squads, faces — and shares **one
`.fl26pack` file**. Anybody adds it to their own recipe and builds.

**Make a package** (League packages → **Make a package...**, or File → Make a league package):

1. Name, author, version and a short description.
2. Tick the leagues that go in (**Select all** / **Select none** over the list). A league below
   another new league must go with it.
3. Optionally **also my changes to the game's own leagues, clubs and players**.
4. Save. The file holds the pictures and faces, not paths on your computer.

**Add a package** (League packages → **Add a package...**, File → Add a league package, or
drop it on Install mods):

1. The program shows what is inside and asks.
2. A league with a name you already have is added as `Name (Package)`.
   A package the recipe already has (the same name) is replaced by the new version (0.1.7): the old
   one's leagues, clubs and player changes go out, the new ones come in.
3. **Save the recipe**, then **Build**.

Ids are given out when each person builds, from what their own game has, so a package works next
to other packages and next to your own leagues. **Remove from the recipe** takes a package out
again, including the changes it made to the game's clubs.

A league placed below one of the game's leagues works for everybody with the same game version.

## 10. Tools

**Diagnostics — Run the checks** looks at the whole setup: content folders that are on but
missing, modules in the wrong order or switched on twice, map lines that point at nothing,
League Builder worlds (only one should be on), and the last `sider.log`. **Copy a report**
puts it all in the clipboard to paste in a forum post or a bug report.

**Restore points**: every file the program changed, with the copy from before. **Put this copy
back** restores it. Copies live in `SiderAddons\ModStudio\backups`. **Clean up...** removes old
ones.

## 11. When something is wrong

| What you see | What to do |
|---|---|
| *sider.ini not found* | Settings → Game folder: pick the folder with `FL_2026.exe`. |
| *no game tables* | Settings → Unpack the game's tables. |
| A mod does not show in the game | Diagnostics → Run the checks. A content folder higher in the list may have the same file. |
| The game does not start after a change | Restore points → put `sider.ini` back, or switch to a profile that worked. |
| The new league is not in Select Team | Start a *new* career; old careers keep their old leagues. |
| Club names are the game's | An Edit file overrides them (section 8). |
| *your leagues send nobody to Europe* | New leagues → Edit the top division → Europe (the **Top flight** button fills the usual three), then Build again. |
| *the Conference League is on, but its tables are missing* | Build the world again: it was built before the option, or with it off. |
| A face does not show | The folder must hold `#Win\face.fpk`; Build again after choosing it. |
| Anything else | Diagnostics → **Copy a report**, and post it with `SiderAddons\sider.log`. |
