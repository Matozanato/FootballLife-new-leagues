# Experimental modules

Everything in this folder does something the modules one level up do not, and **none of it
has been through a full season yet**. They are here because the fastest way to find out
whether they work is for more than one person to run them. They were built and verified
against the exe between 2026-09-21 and 2026-09-22, and several of them were watched working
in a running game — a menu showing the right thing is not the same as a season played with
it, and that difference is the whole reason this folder exists.

Install them exactly like the others (copy into `SiderAddons\modules\`, add a
`lua.module = "..."` line), **one at a time**, and read `sider.log` afterwards. Every one of
them reads the bytes it is about to change first and writes nothing at all if a single site
disagrees, so the worst case is a log line saying it found something else and a game that
runs exactly as it did before.

## What is here

| file | what it changes | the risk |
|---|---|---|
| `fl26hdr192.lua` | the season's competition header from 100 to **192** entries, instead of the 127 that `fl26hdr127.lua` gives | 192 needs a redirect at each of thirteen bounds rather than a single byte; the stubs go into the spare tail of the code section, where the null guards also live |
| `fl26comptab.lua` | the **Select Team** list, so leagues that had no slot in it become selectable, and rows that inherited a shipped competition's name stop displaying it | it hands out free slots in a table the menu reads; if your install's table differs it aborts and says which slot disagreed |
| `fl26slotnames.lua` | the **section heading** seven of those slots draw, which is hard-coded in the exe ("Classic Teams" over a league of yours) | it points seven slots at the switch's empty case, so the menu falls back to the competition's own name; the slot list must match YOUR world (see below) |
| `fl26clubs.lua` + `fl26clubs.dll` | the **club list** the Select Team screen shows for nine slots where the game builds the wrong one (national teams, classic teams, foreign clubs, or nothing at all) | it replaces two functions that read those lists and answers from the league's own rulebook instead; nothing is written, and a slot it cannot answer for falls back to the game's own answer |
| `fl26rank.lua` | the **league rank** (first division, second, third) from a 2-bit field to a 3-bit one, so a pyramid can be more than three deep and the game can tell D3, D4 and D5 apart | 147 sites, every one an in-place rewrite of the same length; it moves the field into a bit the shipped loader never sets, and the group count keeps five bits (31 groups) |
| `fl26deeprank.lua` | the **relegation gate**, so a club goes down from any division, not only the second | replaces `fl26deep4.lua`; load it AFTER `fl26rank.lua` and turn `fl26deep4.lua` off, or the bytes will not match |
| `fl26deep4.lua` | one byte, so that a **third** division relegates into a fourth | superseded by `fl26rank` + `fl26deeprank`, which do it properly; kept for anyone who wants the one-byte version without the rank change |
| `fl26reg64.lua` | the number of **regions** (countries the menus group by) from 29 to **64** | one instruction: the shipped code masks the region to five bits and throws away anything from 29 up, while the runtime field it feeds is six bits wide. Every shipped row keeps the region it had |

## Order, and which of these need each other

They are not independent. This is the order they were run in here:

```ini
lua.module = "fl26comptab.lua"     ; first: it prints "id N -> row R slot S" for every league
lua.module = "fl26slotnames.lua"   ; needs the slot numbers comptab printed
lua.module = "fl26clubs.lua"       ; same
lua.module = "fl26rank.lua"
lua.module = "fl26deeprank.lua"    ; after rank, and with fl26deep4 off
lua.module = "fl26reg64.lua"
```

`fl26hdr192.lua` goes where `fl26hdr127.lua` was, after `fl26joindll.lua`.

**Use `fl26hdr192.lua` *instead of* `fl26hdr127.lua`, never both.** They patch the same
thirteen places, so whichever runs second will find bytes it does not recognise and abort.
A season already on disk was built against whatever header width was installed when it was
created. Switching between 127 and 192 means starting a new season.

## Two lists you must edit for your own world

`fl26slotnames.lua` and `fl26clubs.lua` both carry a `SLOTS` table near the top, and the
numbers in them are the slots **our** test world happened to land on. A competition slot is
not a property of your league; it is handed out by `fl26comptab.lua` at boot, and it says so
in `sider.log`:

```
[fl26comptab.lua] fl26comptab:   id 180 -> row 179 slot  75
```

Read the slot of each of your leagues from those lines and put those numbers in. **Never
guess a slot.** `fl26slotnames.lua` also names, for each slot, the case byte it expects to
find and the heading that case draws today — if your install disagrees it changes nothing
and logs what it saw, which is the report we want.

## What `fl26rank.lua` and `fl26reg64.lua` are for, in one paragraph each

**Rank.** Every rulebook carries its place in the national pyramid, and the game keeps it in
two bits, which count to three. Build a fourth and a fifth division and all of D3, D4 and D5
carry the value 3; the League Info panel then shows France D4 as its own lower league, and
the end-of-season mover cannot tell which way anybody goes. `fl26rank.lua` moves the field
down one bit so it counts to seven. If you have already built a deep pyramid, renumber it
with `python tools\deepen.py --root <your root> --retier <top league ids>` — without that
the leagues still all read 3, because that is what is stored in the file.

**Regions.** A region is the country a competition is grouped under in the menus. The
shipped parser throws away any region of 29 or more, although the runtime field is six bits
and holds 64. `fl26reg64.lua` rewrites that one instruction. **The caveat that matters:**
the menu's *heading* for a region comes from a separate table of 24 rows, and a region with
no row there does not draw a blank — it draws the heading of whatever country was looked up
before it. So regions 29 and up work as groupings and borrow a name. The module that gives
them headings of their own copies the game's own rows, and the version that exists carries
those rows inside itself as a blob of shipped bytes; this repository does not redistribute
game data, so it will be published once it copies them out of memory at startup instead.

## What to report, for any of them

The `sider.log` lines the module wrote, what you expected to see in the game, and what you
saw instead. A module that refuses its patches is not a disaster and is still worth
reporting — the lines it writes name the addresses, which is exactly what is needed to find
out how your build differs. For the four that change menus (`comptab`, `slotnames`,
`clubs`, `reg64`), a screenshot of the screen that is wrong is worth more than a
description of it.

The compiled `fl26clubs.dll` is built from `tools/native/fl26clubs.c`; its checksum and the
build line are in [tools/native/README.md](../../tools/native/README.md).
