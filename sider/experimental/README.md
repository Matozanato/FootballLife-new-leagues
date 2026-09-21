# Experimental modules

Everything in this folder does something the modules one level up do not, and **none of it
has been through a full season yet**. They are here because the fastest way to find out
whether they work is for more than one person to run them.

Install them exactly like the others (copy into `SiderAddons\modules\`, add a
`lua.module = "..."` line), one at a time, and read `sider.log` afterwards. Every one of
them reads the bytes it is about to change first and writes nothing at all if a single site
disagrees, so the worst case is a log line saying `ABORTED` and a game that runs exactly as
it did before.

| file | what it changes | the risk |
|---|---|---|
| `fl26hdr192.lua` | the season's competition header from 100 to **192** entries, instead of the 127 that `fl26hdr127.lua` gives | 192 needs a redirect at each of thirteen bounds rather than a single byte; the stubs go into the spare tail of the code section, where the null guards also live |
| `fl26comptab.lua` | the **Select Team** list, so leagues that had no slot in it become selectable | it hands out free slots in a table the menu reads; if your install's table differs it aborts and says which slot disagreed |
| `fl26deep4.lua` | one byte, so that a **third** division relegates into a fourth (and a fourth into a fifth); without it a fourth division promotes upwards but is never relegated into | it widens one comparison in the end-of-season mover from "exactly division 2" to "2 or 3"; if you have no pyramid deeper than three it changes nothing |

A third module, which gives the added leagues a **heading of their own** in the competition
list instead of putting them under an existing country, is not here yet. It works by copying
the game's own 80-row competition-to-heading table into spare space and adding rows after it,
and the version that exists carries that table inside itself as a blob of shipped bytes. This
repository does not redistribute game data, so it will be published once it copies those rows
out of memory at startup instead of shipping them.

**Use `fl26hdr192.lua` *instead of* `fl26hdr127.lua`, never both.** They patch the same
thirteen places, so whichever runs second will find bytes it does not recognise and abort.

A season already on disk was built against whatever header width was installed when it was
created. Switching between 127 and 192 means starting a new season.

What to report, for any of them: the `sider.log` lines the module wrote, what you expected
to see in the game, and what you saw instead. A module that aborts is not a disaster and is
still worth reporting — the mismatch lines name the addresses, which is exactly what is
needed to find out how your build differs.
