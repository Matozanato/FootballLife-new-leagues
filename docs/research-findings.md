# Findings

> **About this file.** This is the research log behind FL26 Mod Studio, published with 0.2.0 for
> anyone who wants to build on it. It is written in the order things were found, so early
> sections (the TL;DR included) describe the state at the time and are often superseded further
> down -- search for an address or a table name and read its latest entry. Scripts it mentions
> under `scratchpad/` or in the private research tree are not part of the repository. The
> current, checked state of the code is in [forking.md](forking.md) and [fork/](fork/).

What is known about Football Life 2026 / PES 2021 competition data and the parts of
`FL_2026.exe` that constrain it. Every address, offset and bit position here was read
out of the binary or verified against the shipped data tables; anything untested is
marked as such in place.

FL26 runs on the PES 2021 engine, so most of this should apply to any PES 2021 based build. All addresses below are virtual addresses in `FL_2026.exe` with image base `0x140000000`.

---

## TL;DR

- **Competitions, leagues, cups and all their rules are plain data**, not hardcoded in the exe. They live in three binary tables that Sider can already override at runtime with livecpk. No exe patch needed to define a new league.
- **I got a new custom league to show up in League mode and be selectable.** That part works.
- **Existing competitions can be reshaped the same way.** The Champions League, World Cup and EURO are just several regulation rows sharing a competition id — group count, teams per phase, how many advance, one leg or two, extra time, third-place playoff are all bits you can edit.
- **The season scheduler then generated zero fixtures for it.** That's the real blocker. Everything else is solved or solvable.
- **There is a lot of room left.** 164 of 256 competition IDs are free, 133 of 256 regulation IDs are free, and 86 of the 300 runtime regulation slots are free. That's **86 new competitions with no exe patch at all**.
- Teams are the tight one: the exe array caps at **750 and 743 are used**, so 7 free slots today. The team *handle* format allows 16,381, but that is not the ceiling — the arrays sit at fixed offsets in one block and each one's capacity exactly fills the space to the next, so raising a cap means relocating everything after it. See "The arrays are one fixed-layout block".
- The bottleneck for new *countries* is regions: 29 max, 24 used, **5 free** — and a **one-byte patch** takes that to 8, because the field already holds 32 values and one `cmp` throws the rest away.
- European qualification (who goes to UCL/UEL) is a **static table inside the exe**, not data. A new league sends nobody to Europe unless you patch it.

---

## 1. Where competitions actually live

Three files inside `common/etc/pesdb/` (packed in `download\data_s2526*.cpk`):

| File | Record size | What it holds |
|---|---|---|
| `Competition.bin` | 36 bytes | The list of competitions |
| `CompetitionRegulation.bin` | 2352 bytes | Rules, format, number of teams, names |
| `CompetitionEntry.bin` | 12 bytes | Which clubs play in which competition |

Sider's livecpk intercepts these fine, so you can test changes without repacking a CPK. That alone means "you can't add leagues, they're baked into the exe" is simply not true — the definition of a league is data.

**Free space:** 91 of 256 competition IDs are used, and 123 of 256 regulation IDs are used. So there are 50+ free competition slots and 50+ free regulation slots sitting there unused.

---

## 2. The regulation record is fully decoded

The parser that reads a regulation row lives at `0x1414f7e80`–`0x1414f841f`. I pulled every field width out of it and then verified the meanings by correlating against all 214 existing rows in the file. Everything below is confirmed against real data, not guessed:

**Structure fields**

- `0x00` — regulation ID you get **relegated into**
- `0x04` — regulation ID you get **promoted into**
- `0x09` — competition type: 1 playoff, 2 groups, 3 knockout, 4 league, 5 MLS style, 9 split league
- `0x0b` — number of teams, 6 bits (so max 63)
- `0x0c` bits 12–17 — format template, 53 possible values
- `0x10` bits 0–4 — number of groups, 5 bits (max 31)
- `0x10` bits 12–14 — number of rounds, 3 bits (1 = single, 2 = double, 3 = triple round robin)

**Match rule bits, all at `0x10`**

- bit 25 — extra time
- bit 24 — away goals rule
- bit 26 — parsed and stored, but nothing reads it (see section 5)
- bit 27 — penalties
- bit 28 — third place playoff
- bit 29 — single leg vs. two legs
- bit 30 — group labels: numbers instead of letters

**Format template values seen in use:** 1 = normal league, 2 = domestic knockout cup, 11/12/13 = split league (Scottish style), 20 = UCL groups, 22 = UCL knockout, 28/30 = UEL, 50/52 = custom groups/knockout.

The practical consequence: **promotion and relegation between two divisions is two integers.** You point D1's relegation field at D2's regulation ID and D2's promotion field at D1's. Number of teams, rounds, extra time, penalties, two-legged ties, group stages — all editable per competition, in data.

Bits 21–23 are the matchday template and bit 24 is the away goals rule; both are decoded in
section 5.

---

## 3. What I actually tested in game

I built a test package with Sider livecpk: a new competition (competition ID 6, region 11, regulation 11) called "SuperSport HNL", 10 clubs, format template 1.

**Result: the league appears in the League mode menu and can be selected.** That was the moment I stopped assuming the community consensus was right.

Starting the season crashed with an access violation at `0x1413236e4`. Cause traced: the "team difficulty by rank" routine reads a standings rank of −1 (the standings table at `0x141579b90(comp)` initialises ranks to −1 before the first matchday) and uses it to index a table at `0x1428e52e0`. Classic negative index.

I put a live patch in via a debugger breakpoint at `0x1413236e1` clamping rank < 0 to 0. **The crash goes away and the season starts.**

And then: **the fixture generator produces zero matches.** The only option available is "advance to next season". The crash was a symptom; this is the actual wall.

---

## 4. Exactly how to add a league, step by step

This is the part I most want people to have, because once you see it, it stops looking hard. The entire thing is three appended records and one line in a config file.

### The container format

The `.bin` tables aren't raw — they're WESYS containers: 3 header bytes, the string `WESYS`, u32 compressed size, u32 uncompressed size, then zlib.

```python
def wesys_unpack(d):
    assert d[3:8] == b"WESYS"
    csz, usz = struct.unpack("<II", d[8:16])
    return zlib.decompress(d[16:16+csz])

def wesys_pack(raw, hdr=b"\x00\x01\x01"):
    c = zlib.compress(raw, 9)
    return hdr + b"WESYS" + struct.pack("<II", len(c), len(raw)) + c
```

Inside, every table is a flat array of fixed-size records with no index and no count field — the row count is just file length divided by record size. **Which means you add a competition by appending 36 bytes to the end of a file.** That's the whole trick.

Record sizes: Competition 36, CompetitionEntry 12, CompetitionKind 88, CompetitionRegulation 2352, Country 1420, Team 1532, Player 312.

### Step 1 — clone a competition that already works

Do not build a row from scratch. Find a league that already behaves the way you want and copy it. I used Turkey's Süper Lig: a plain single-table league, no split, no playoff, nothing exotic.

```python
craw = load("Competition")                             # 36-byte records
tmpl = [r for r in rows(craw, 36) if r[5] == 119][0]   # 119 = TURKEY_D1_LEAGUE
r = bytearray(tmpl)
r[3] = NEW_AREA * 8      # byte 3 holds the region in bits 3..7  (area == r[3] >> 3)
r[5] = NEW_COMP          # competition id — 6 and 7 are free, among 164 others
r[6] = 0x22              # flags; 0x22 = domestic league
r[8:36] = b"CROATIA_D1_LEAGUE".ljust(28, b"\x00")   # internal code string
write(craw + bytes(r))
```

### Step 2 — the regulation row

```python
rraw = load("CompetitionRegulation")                     # 2352-byte records
tmpl = [x for x in rows(rraw, 2352) if x[2] == 118][0]   # reg 118 = Turkish league
r = bytearray(tmpl)
r[2]   = NEW_REG          # regulation id — 11, 12, 13, 14 are free
r[8]   = NEW_COMP         # points back at the competition row
r[0xb] = len(TEAMS)       # team count, 6 bits, max 63
r[0xf] = 0                # asset index (logo/colours) — 0 until you make one
set_name(r, "SuperSport HNL")
write(rraw + bytes(r))
```

Names sit at `0x14 + k*115` for k in 0..19 — twenty language slots, NUL-terminated, 115 bytes each, slot 0 is English. Write the same string into all twenty unless you actually want per-language names.

Everything from section 2 — rounds, extra time, penalties, two-legged ties — is a bit in this row. Because you cloned a working league you inherit sane values for all of it and only touch what you care about.

### Step 3 — put teams in it

```python
def entry_pack(team, rowid, comp, slot):
    return struct.pack("<III", team, rowid, comp | (slot << 8))

eraw = load("CompetitionEntry")
for i, t in enumerate(TEAMS):
    eraw += entry_pack(t, 9100 + i, NEW_COMP, i + 1)
write(eraw)
```

`team` is a team id that already exists in `Team.bin`. `rowid` only has to be unique — I used 9100+ to stay clear of everything shipped. Slots are 1-based.

**This is the step people assume is blocked, and it isn't.** I used ten clubs that already exist in the game but aren't in any league. You only hit the 743-of-750 team wall if you want clubs the game has never heard of. A new league built from existing clubs costs zero team slots and zero patched bytes.

### Step 4 — promotion and relegation (optional)

Two u16 fields, and that's genuinely all:

```python
struct.pack_into("<H", d1, 0, D2_REG)   # offset 0x00 — where D1 relegates to
struct.pack_into("<H", d2, 4, D1_REG)   # offset 0x04 — where D2 promotes to
```

For the second division I cloned Spain's Segunda (reg 80) instead of Turkey, because it already has a working promotion link. I also copied D1's calendar dword at `0x10` so both divisions run on the same season shape, and set the promotion bit at `0x12`.

### Step 5 — ship it through Sider

Write the packed tables to:

```
SiderAddons\livecpk\YourPackage\common\etc\pesdb\Competition.bin
                                                 CompetitionRegulation.bin
                                                 CompetitionEntry.bin
```

and add one line to `sider.ini`:

```
cpk.root = ".\livecpk\YourPackage"
```

Set `debug = 1` while testing and watch `sider.log` for `livecpk file found`. If that line doesn't appear, Sider isn't intercepting and you're still reading the original CPK — which will look exactly like "my edit did nothing".

That's the whole process. No hex editing, no repacking a CPK, and it's undone by commenting out one line. You can keep several variants side by side as separate packages and switch between them.

---

## 5. Reshaping competitions that already exist

Adding a league is one half. Changing the Champions League, the World Cup or the EURO is
the other half, and it runs on the same mechanism.

### A multi-phase competition is several regulation rows

A competition with a group stage and a knockout bracket is not one record. It is several
regulation rows sharing one competition id. The Champions League is three:

```
cid  reg  type      teams  draw
2    2    playoff   16     0     qualifying playoff
2    3    group     32     1     group stage
2    4    knockout  16     0     knockout bracket
```

The World Cup is two (reg 34 groups / reg 35 knockout), EURO is two (24 / 16), the Europa
League is two (48 / 32). The fields that wire phases together:

- `0x08` — competition id, identical in every row of the competition
- `0x06` — parent regulation (0 = the main row)
- `0x0a` — group index (0xff = the main row)
- `0x03` — group sub-index, ×4
- `0x10` bits 18-20 — phase ordinal: 0 playoff, 1 groups, 2 knockout
- `0x0c` bits 12-17 — format template, set per phase

One gotcha when reading shipped values: byte `0x0b` packs the team count into bits 0-5 and
the seeded-draw flag into bit 6. A raw `0x0b` of 96 on the UCL group row is **32 teams with
a draw**, not 96 teams. `docs/competition-slotmap.txt` lists the masked values.

### What you can change, purely in data

| Want to change | Field |
|---|---|
| Teams in a phase | `0x0b` bits 0-5, max 63 |
| Number of groups | `0x10` bits 0-4, max 31 |
| How many advance from each group | `0x0c` bits 18-23 |
| Single or double round robin in groups | `0x10` bits 12-14 |
| Seeded draw vs fixed | `0x0b` bit 6 |
| Extra time | `0x10` bit 25 |
| Penalties | `0x10` bit 27 |
| Third-place playoff | `0x10` bit 28 |
| One leg or two | `0x10` bit 29, with the subtype at `0x10` bits 9-11 |
| Matchday template | `0x10` bits 21-23 — see below |
| Calendar template (country) | `0x10` bits 5-8, values 0..8, parser rejects >= 9 |
| League tier | `0x10` bits 15-17 |

Shipped values to work from: 8 groups in the UCL, 12 in the UEL, 8 in the World Cup, 6 in
the EURO, 4 in the AFC Champions League, 3 in Copa América. The third-place playoff is on
for the World Cup, Copa América, the Asian Cup and AFCON, and off for the EURO. Single-leg
is on for the FA Cup, World Cup and EURO, off for UCL and UEL knockouts. The Community
Shield and Johan Cruyff Shield have extra time switched off, so they go straight to
penalties — copy those two if that is the behaviour you want.

So a 48-team, 12-group World Cup with two advancing per group is a handful of bit edits.
Same for restructuring the Champions League, as long as you stay on a format template the
scheduler already understands.

### Matchday templates (bits 21-23 at 0x10)

This picks which days of the week the competition plays on, and it is per country:

| value | used by |
|---|---|
| 0 | one-off matches: super cups, friendlies, practice |
| 1 | England |
| 2 | Spain, Germany, Russia, Greece, Argentina, Chile, China |
| 3 | Italy, Saudi Arabia |
| 4 | France, Brazil, Libertadores, custom league, South American WC qualifiers |
| 5 | Netherlands, Belgium, Denmark, Scotland, Japan, United States, Colombia |
| 6 | cups and group stages generally |
| 7 | Portugal only |

### Bit 24 at 0x10 = the away goals rule

This one took a while, so here is the whole chain in case it is useful as a method.

Correlation got nowhere — the split does not track bracket size, powers of two, entrant
count, format template, extra time or legs — so I went to the disassembly instead. In the
regulation parser at `0x1414f8255` the engine reads byte `0x13` of the record (the top byte
of the dword at `0x10`, so bit 0 of it is bit 24 of the dword) and hands it to a setter:

```
1414f8255  movzx edx, byte ptr [rax + 0x13]
1414f8259  and   dl, 1
1414f825c  call  0x1414c9b50
```

```
1414c9b50  and   dword ptr [rcx + 0x304], 0xffffffdf
1414c9b57  movzx eax, dl
1414c9b5a  and   eax, 1
1414c9b5d  shl   eax, 5
1414c9b60  or    dword ptr [rcx + 0x304], eax
```

So bit 24 lives in the runtime regulation object at **`+0x304` bit 5**. The extra-time
setter at `0x1414c9cf0` writes the same dword at bit 4, which is a useful confirmation that
this is where per-competition match rules are kept.

Scanning for reads of `+0x304` that isolate bit 5 gives a query function at `0x14151bf40`.
It has a byte-identical prologue to `0x14151c130` (which returns `+0x304` bit 4, extra time)
and `0x14151d580` (penalties) — the same `HasX(competition)` family.

The caller that settles it is `0x141331810`, the tie decider. For a single match it compares
the two scores and, if level, asks extra time then penalties. For a two-legged tie it pulls
each team's aggregate, compares it against this leg, and when the aggregate is level:

```
14133191b  movzx ecx, word ptr [rdi]
14133191e  call  0x14151bf40          ; away goals enabled?
141331923  test  al, al
141331925  je    0x141331932          ; not enabled -> skip
141331927  cmp   bl, byte ptr [rdi + 0x1f]
...
141331932  movzx edx, byte ptr [rdi + 0x1c]
141331936  movzx ecx, byte ptr [rdi + 0x1f]
141331942  add   edx, eax             ; home this leg + away aggregate
14133194d  add   ecx, eax             ; away this leg + home aggregate
14133194f  cmp   edx, ecx
```

That crosswise sum is the away goals comparison, and it only runs when the bit is set.
**Bit 24 = 1 means away goals decide a level two-legged tie.**

The shipped data then makes sense. It is set on the Copa del Rey, Coppa Italia, DFB-Pokal,
Copa do Brasil, Copa Argentina, Emperor's Cup, US Open Cup, Russian Cup, Greek Cup, Turkish
Cup, Chinese Cup, Chilean Cup, Colombian Cup, the custom cup, the Spanish Super Cup, the
Libertadores playoff and knockout, the AFC Champions League knockout and the Danish European
playoff. It is clear on every UEFA competition — UEFA abolished away goals in 2021 — and on
the cups the game models as single-leg only, where the rule can never apply: FA Cup, Coupe
de France, KNVB Cup, Taça de Portugal, Belgian Cup, Danish Cup, Scottish Cup, Saudi Cup.

Practically: **turning away goals on or off for any competition is one bit.** If you want
them back in the Champions League, set bit 24 on the UCL knockout regulation.

### Bit 30 at 0x10 = group labels are numbers, not letters

Same method, and this one is a nice example of the parser not storing a flag as a flag. It
uses bit 30 to index a two-entry table in `.rdata`, and stores the *result*:

```
1414f8190  mov  ecx, dword ptr [rax + 0x10]
1414f8193  shr  ecx, 0x1e
1414f8196  and  ecx, 1
1414f8199  mov  edx, dword ptr [rbx + rcx*4 + 0x297d268]   ; table = { 1, 0 }
1414f81a3  call 0x1414c9e30
```

The setter writes a 3-bit enum into runtime `+0x300` bits 16-18. The table is `{1, 0}`, so
bit 30 clear gives enum 1 and bit 30 set gives enum 0.

The consumer is the group-label builder at `0x140ca570a`. It initialises two static string
arrays once, then picks between them:

```
140ca57bf  ... "1" "2" "3" ... "12"   -> array at 0x1434ba730
140ca59ed  lea r13, [rip + ...]        ; -> array at 0x1434ba8b0
140ca5a21  ... "A" "B" "C" ... "L"    -> array at 0x1434ba8b0

140ca5d5d  movzx eax, byte ptr [rax + 0x302]   ; the enum, as a byte
140ca5d64  and   eax, 7
140ca5d67  mov   r8, rdi
140ca5d6a  shl   r8, 5                          ; index * sizeof(std::string)
140ca5d6e  cmp   eax, 1
140ca5d71  jne   0x140ca5d78
140ca5d73  add   r8, r13                        ; enum 1 -> "A".."L"
140ca5d76  jmp   0x140ca5d82
140ca5d78  lea   rax, [rip + ...]               ; enum 0 -> "1".."12"
140ca5d7f  add   r8, rax
```

So **bit 30 set = groups are numbered, bit 30 clear = groups are lettered**, and either way
the maximum is 12 labels.

The shipped data is exactly what you would expect once you know that. Set (numbered) on the
Copa Libertadores group stage — which really does use Grupo 1-8 — the custom cup groups, and
all five World Cup qualifying group stages. Clear (lettered) on the Champions League, Europa
League, AFC Champions League, EURO, Copa América, AFC Asian Cup and the World Cup finals
groups, all of which use Group A onwards.

One more consumer, at `0x14126f0f8`, reads the enum and forces any value >= 2 back to 1, so
the third bit of the enum is unused headroom rather than a third labelling scheme.

### Bit 26 at 0x10 is inert in this build

Bit 26 is parsed (`0x1414f8267`) and stored via `0x1414c9d10` into runtime `+0x304` bit 6,
exactly like the flags around it. It is then never read.

That is a stronger claim than "I could not find it", so here is the basis. Scanning all
39 MB of code for every `mov` / `movzx` / `test` / `bt` against `+0x304`, and re-decoding
each candidate with a disassembler anchored on a proven instruction boundary (raw byte
scanning alone produces mostly mid-instruction garbage), gives 83 genuine reads. Not one of
them shifts by 6 or masks `0x40`, except a single site at `0x1414ef22c` — and that site is
one step of an unrolled `xor`/`and`/`xor` loop that copies masks `4, 8, 0x10, 0x20, 0x40,
0x80, ...` from one object to another. It is a generic field copier, not a consumer. For
comparison the same scan finds nine real readers for bit 28 (third place playoff) and three
for bit 24.

**Scan scope, since "nowhere in the binary" needs one.** All scanning in this document
covers `.trace`, the 39 MB of unpacked game code. The executable has other sections marked
executable: `.impdata` is the protector's packed blob (380 MB, not decodable x86 as it sits
on disk), and `.xcode`, `.xtls`, `.idata`, `.sxdata` and `.sbss` together come to 13,824
bytes of protector stubs, TLS callbacks and import thunks. Those small sections were
disassembled and reference none of the regulation runtime fields, so the game logic really
is all in `.trace`.

The data hints at what it *was*. Bit 26 is set on exactly three competitions — the Champions
League playoff, the Champions League knockout and the Europa League knockout, 11 regulation
rows in total. Those are precisely UEFA's away-goals competitions before the rule was
abolished in 2021, and they are also the competitions where bit 24 (away goals) is clear.
The obvious reading is that bit 26 is a superseded away-goals flag that the data still
carries and the code no longer consults — but that is inference from the split, not
something the disassembly proves. What the disassembly does prove is that **setting or
clearing bit 26 changes nothing**, so do not spend time on it.

### The one hard limit

Format templates are an enumeration the exe interprets in code, and the parser rejects
anything >= 53. The values actually in use:

1 league · 2 domestic cup KO · 3 super cup · 4 promotion playoff · 6 two-season league ·
7/8 MLS rounds · 9/10 Colombian KO · 11 split league · 12 split-league regular season ·
13/14/15 playoff groups · 18 UCL playoff · 20 UCL groups · 22 UCL KO · 23 European playoff ·
28/30 UEL groups/KO · 31 UEFA super cup · 32 pre-season cup · 33/34/36 friendlies ·
35 Club World Cup · 37 EURO groups · 39 national-team KO · 40 qualifiers · 46 World Cup
groups · 48 World Cup KO · 49 custom league (League mode) · 50/52 custom cup groups/KO

You can reshape any competition by reusing one of these. You cannot invent a 53rd — that
means new scheduler code, which is the same wall as section 6.

### Match rules that are *not* per-competition

Substitutions and match length are global match options, not regulation fields, so "5 subs
in every competition" is not a data edit here. The strings `is_ex_substitution` and
`NUM_SUBSTITUTION` in `.rdata` are the starting point for forcing a default.

Away goals *are* per-competition after all — bit 24 at `0x10`, decoded above.

VAR does not exist in the engine at all.

---

## 6. The other data tables

`Competition`, `CompetitionRegulation` and `CompetitionEntry` are the three that matter for
building a league, but they are not the only decoded ones.

### CompetitionKind.bin — 9 rows, 88 bytes each

A tiny lookup that names the competition types used in regulation byte `0x09`. Each row
carries localised names plus an ASCII identifier:

| id | identifier |
|---|---|
| 1 | `PLAYOFF` |
| 2 | `GROUPSTAGE` |
| 3 | `KNOCKOUT` |
| 4 | `LEAGUE` |
| 5 | `LEAGUE_2SEASONS` |
| 6 | `QUALIFICATION_1` |
| 7 | `QUALIFICATION_2` |
| 8 | `PRACTICE` |
| 9 | `SPLIT_TOTAL` |

Types 6 and 7 are qualification rounds — worth knowing if you are building a continental
competition with a qualifying path.

### Country.bin — 214 rows, 1420 bytes each

Every nation the game knows, which is a different thing from a *region*. Regions (max 29)
are the slots competitions live in; Country.bin is the nationality and national-team list.

Names sit in about 20 slots of 70 bytes starting at `0x4e`. Slot 2 (`0xda`) is Italian,
slot 3 (`0x120`) is English, slot 9 (`0x2c4`) is the three-letter code. Slot 0 is Japanese.

The interesting part is two bytes in the header:

- `0x04` — **geographic region**: 1 Asia, 2 Europe, 3 Africa, 4 North/Central America,
  5 South America, 6 Oceania, 0 other
- `0x05` — **football confederation**, i.e. which qualifying path the nation actually plays in

They are usually the same, and the cases where they differ are exactly the real-world
oddities: Israel and Turkey are `(1, 2)` — Asian geography, European football; Kazakhstan
and the Central Asian states are `(2, 3)`; Australia is `(6, 3)`, Oceania playing in Asia;
Guyana and Suriname are `(5, 6)`, South America playing in CONCACAF.

Which means **moving a nation into a different World Cup qualifying confederation is a
one-byte edit**.

### Team.bin — 743 rows, 1532 bytes each

Clubs and national teams in one table. This is the array the 750-team exe limit applies to,
so 743 of 750 used is read straight off this file. Team id is a `u32` at `0x08`; names run
in about 20 language slots of 70 bytes from `0x9e`, with English at `0x170` and the
three-letter abbreviation at `0x372`.

### A detail worth knowing before you build a cup

The `teams` field in a regulation is the **size of that phase's bracket**, not the number of
clubs entered. `CompetitionEntry` can hold many more:

| competition | regulation `teams` | entries |
|---|---|---|
| Copa del Rey | 20 | 42 |
| Coppa Italia | 20 | 40 |
| Copa do Brasil | 20 | 41 |
| UCL knockout | 16 | 32 |
| FA Cup | 44 | 44 |

So a cup where the big clubs join late is expressed by entering everyone in
`CompetitionEntry` and setting the bracket smaller — the engine already works this way for
most domestic cups.

---

## 7. The scheduler is the blocker

This is the one thing I couldn't crack, and it's where anyone picking this up would have to start.

- There is no RTTI on the scheduler classes and no static calendar tables to read. The format template (53 values) and the country calendar template (9 values) are both read from the regulation and then **interpreted in code**.
- Master League data creation runs through `ModeDataCreationThread::run` at `0x141267040`. The steps that touch runtime regulation objects most heavily — 9 references to the `0x314` stride — are `0x14126e970` and `0x14126f000`. Those are my prime suspects for the fixture generator.
- My working theory is that the generator doesn't recognise the combination of (format template 1 + calendar template of a region that has no existing competitions). Reusing an existing country's calendar template, e.g. Turkey or Greece, might just work. **I have not tested this yet.** If it does, the scheduler never needs touching and new leagues become a pure data mod.

### What the calendar template actually is, and who reads it

This narrows the search a lot, so it is worth writing down properly.

The parser reads bits 5-8 of the dword at `0x10`, rejects anything `>= 9` (falling back to the
default), and stores the value as a **whole dword at runtime `+0x2f8`** — not bit-packed, which
makes it easy to trace. The values in the shipped data:

| template | used by |
|---|---|
| 0 | cups, playoffs, practice — anything without a league season |
| 1 | Argentina, Belgium, Chile, Colombia, China, Japan, Netherlands, Scotland, USA, Turkey, ... |
| 2 | Spain D1/D2, Germany, Greece, Russia, Saudi Arabia, China D1 |
| 3 | Italy D1/D2 only |
| 4 | Brazil D1/D2, France D1/D2 |
| 5 | Portugal D1 only |
| 7 | Colombia, Denmark |
| 8 | Belgium |

Value 6 is unused, so there are two free slots inside the accepted range.

Anchoring on the getter that returns a runtime regulation object (`0x1414bb000`, 885 call
sites) rather than scanning for the offset directly — the offset `+0x2f8` is far too common
across unrelated classes to scan for blind — gives **exactly four** consumers of the field:

| site | what it is |
|---|---|
| `0x140a9bd43` | competition-rules UI (its caller references `title_yellowCard`, `switch_description`) |
| `0x140a9c4df` | same UI path |
| `0x140fc86e6` | reached from `EventRankingListener` |
| `0x14134c29e` | a date/period predicate, called 11 times from `0x14134c4d0` |

The last one is the interesting one. It dispatches on the template value:

```
14134c2a3  mov  esi, dword ptr [rax + 0x2f8]   ; calendar template
14134c2a9  lea  eax, [rsi - 2]
14134c2ac  cmp  eax, 1
14134c2af  jbe  0x14134c349                    ; templates 2 and 3
14134c2b5  test esi, esi
14134c2b7  jne  0x14134c3ea                    ; anything else -> false
```

so only templates 0, 2 and 3 get real handling there, and both branches then compare dates
and return a bool. That places the field in season-boundary logic rather than in fixture
generation itself.

**The practical takeaway for anyone adding a league:** the template is a small enumeration
interpreted in code, so an unused value is not a blank slate you can define — it is a value
with no handler. Copy the template of a country whose season shape matches the one you want,
and prefer 1 or 2, which are the two that many countries share.

### The record-to-runtime field map

Chasing any regulation field means first knowing where it lands in the runtime object, so
that map is now generated rather than guessed: `docs/regulation-field-map.txt`, produced by
`tools/regmap.py`. It walks the parser, pairs each field read with the setter it is handed
to, and disassembles the setter to recover the target offset and bit range — 25 fields.

It reproduces all five fields that were reverse-engineered by hand (away goals `+0x304`
bit 5, the inert bit 26 at `+0x304` bit 6, group labels at `+0x300` bits 16-18, extra time
at `+0x304` bit 4, calendar template at `+0x2f8`), which is the check that it is reading the
parser correctly.

`tools/regfields.py` does the other direction: for all 885 call sites of the object getter,
it records which field is touched next, giving a usage count per field. The busiest are
`+0x308` (108 sites), `+0x304` (89), `+0x80` (73), `+0x30a` (68) and `+0x300` (56); the
calendar template at `+0x2f8` has only 4. Low counts are the tractable ones.

### 1422 function names, which changes how tractable all of this is

The single most useful thing found so far, and it turned up by accident while chasing the
fixture array.

`.data` holds a task registration table of 4-qword entries: `{ factory function,
"Class::CreateTaskUnit", "Common/TaskName", 0 }`. There are **1422 of them**, dumped to
`docs/task-registrations.txt` by `tools/tasktable.py`. This build carries almost no RTTI and
most of its own functions reference no strings at all, so until now naming anything meant
walking a call chain and hoping. Now a large part of the engine has real names attached.

It was found by taking a function that appeared to have **zero** callers in the call index
— meaning it is reached indirectly — and searching the image for an 8-byte pointer to it
(`tools/ptrfind.py`). The slot turned out to sit in this table. A function with no direct
callers is a lead, not a dead end.

One correction to the earlier version of this section: that zero-caller function was
originally reported as one of the fixture-array functions, named `CmnUpdateDayBegin`. It was
not. The attribution came from a bug in `func_start` described under "Finding where a
function begins" below, and with the bug fixed **none of the 21 functions that touch the
fixture array appears in the task table at all**. The table is real and the 1422 names are
real; that one link between the table and the fixture code was not.

### Finding where a function begins, and why the first method was wrong

Both `funcinfo.py` and `nameup.py` originally located a function start by walking backwards
until they saw two consecutive `0xcc` int3 padding bytes. That is wrong twice over. It
started the walk at `k = 3`, so passing an address that was *already* a function start
returned a point two bytes before it and every subsequent call-index lookup missed. And more
seriously, this compiler pads with a **single** `0xcc` about as often as with two, so the
walk runs straight past a real boundary and attributes a call site to whatever function
happens to lie further back.

Both now use a much better oracle, `callindex.starts()`: **every target of a direct call is
a function start by definition**, and the call index already holds 75,961 of them. The
enclosing function is then the largest known start at or below the address. This immediately
exposed the mistakes above — `0x1413007c0` turned out to be a two-instruction thunk that
jumps to `0x141300730`, with the call site that had been attributed to it living in a
different function entirely.

The general lesson is the one this document keeps arriving at: a heuristic that is right
most of the time produces findings that are wrong some of the time, and there is no way to
tell which from the output alone. Prefer an oracle that is right by construction.

### Task objects, and why walking the call graph downwards fails

Every entry in the task table points at a thunk that jumps to a factory body of exactly one
shape:

```
141300730  mov  edx, 0xa0                ; size of the task object
14130075c  call 0x1403fb410              ; allocate
141300774  call 0x1413118b0              ; base task constructor
141300779  lea  rax, [rip + 0x15d1588]   ; -> 0x1428d1d08
141300780  mov  qword ptr [rbx], rax     ; primary vtable
141300783  lea  rax, [rip + 0x15d1656]   ; -> 0x1428d1de0
14130078a  mov  qword ptr [rbx + 0x70], rax   ; secondary vtable
```

So a name in the table yields the task's two vtables and therefore its real methods;
`tools/taskvt.py <name>` prints them. `CmnUpdateDayBegin` has 24 primary slots and 1
secondary.

This also explains a negative result worth recording. `tools/reach.py` walks the call graph
*downwards* from a function, following direct calls and tail jumps. Run from a
`CreateTaskUnit` address it reaches 16 functions and stops, because the factory does nothing
but allocate and store vtables. Run from the vtable slots of `CmnUpdateDayBegin` it walks up
to 1158 functions and still reaches none of the fixture-array functions. The engine
dispatches through vtables at nearly every level, so a direct-call graph cannot connect a
named task to the data it eventually touches. Naming this code will have to come from the
data side, not from reachability.

Names worth knowing if you are working on competitions:

| function | name |
|---|---|
| `0x140c023f0` | `EditLeagueOrganizeAreaSelect` — **the in-game region picker** |
| `0x140c067c0` | `MenuEditLeagueOrganizeMain` |
| `0x140c0c130` | `MenuEditLeagueOrganizeTeamNum` |
| `0x140abb130` | `MenuModeCompeRegulationSetting` — the regulation editor UI |
| `0x140ab5850` | `ModeCompeSuperTeamSetting` (League/LeagueGroupings) |
| `0x140b2f500` | `ModeGroupLeagueBase::CreateGroupLeague` |
| `0x1412f3220` | `CmnCheckFlowScheduleProcess` |
| `0x1413007c0` | `CmnUpdateDayBegin` (a thunk; the body is `0x141300730`) |

`EditLeagueOrganizeAreaSelect` is the obvious next place to look for how a region id becomes
a name and a flag, since that menu has to render exactly that list — see section 11.

## Master League: what can actually be changed, and what cannot

The question is how far Master League can be modded. The honest structural answer is that
ML is almost entirely **code**, sitting on top of a **data** layer it shares with the rest
of the game. So the useful thing is to draw that line precisely.

### The data layer, in full

Every table the engine can load is now enumerated in `docs/pesdb-schema.txt`: **28 tables**,
with their ids and record sizes read out of the binary rather than guessed. The loader at
`0x14125f310` bounds a table id with `cmp edx, 0x1c` and indexes a name array at
`0x1434d6630` and a record-size array at `0x1428bb100`.

That list is the whole data surface. If a thing is not expressible in one of those 28
tables, it is not moddable without patching code. Three of the shipped record counts —
Team 743, Competition 91, CompetitionRegulation 214 — reproduce numbers derived a completely
different way earlier in this document, which is what makes me trust the schema.

The tables read once at load, into the edit block; nothing later reads a `.bin` again. Each
table has between zero and four reader functions, all in the loader cluster.

### What that means for Master League, feature by feature

The task table names 85 ML tasks, which is the feature list from the engine's own mouth.
Sorting them by whether a pesdb table backs them:

| ML feature | Backed by data? | Consequence |
|---|---|---|
| Managers | **Yes** — `Coach.bin` | add, rename, replace freely |
| Squads, players, ratings, growth curves | **Yes** — `Player.bin`, `PlayerAssignment.bin` | full control |
| Clubs, kits, finances-at-start | **Yes** — `Team.bin` | full control |
| Tactics and formations | **Yes** — `Tactics.bin`, `TacticsFormation.bin` | full control |
| Stadiums, derbies | **Yes** — `Stadium*.bin`, `Derby.bin` | full control |
| Competitions in the ML calendar | **Yes** — the `Competition*` tables | see the rest of this document |
| Transfer and negotiation behaviour | **No table** | code |
| Club finances over a season — sponsors, gate, prize money, wages | **No table** | code |
| Training, skill training, youth development | **No table** | code |
| Scouting | **No table** | code |
| Coach missions, philosophy, hall of fame | **No table** | code |

The "no table" rows are not a failure to look. The shipped data surface is 1517 distinct
`cpk_dat/` paths in the binary, and the only shipped parameter file among them is
`cpk_dat/common/parameter/MatchVisualSetting.json`. The 234 `constant/*.json` files are all
under `DevelopData/`, a developer tree that is not shipped, and all of them are match
gameplay rather than ML. There is no ML configuration file to edit.

### The manager slots, which is the one clear win

`0x1414f2460` is the function that reads `Coach.bin`, and it writes into an array at
**`edit+0xc4ca0c`, stride `0x258` (600 bytes)**, with its count at **`edit+0xd0bcf0`** and a
bound of **1300** enforced at 20 sites:

```
1414bc279  mov  ebx, dword ptr [rcx + 0xd0bcf0]
1414bc285  cmp  ebx, 0x514                        ; 1300
1414bc2b4  imul r9, rbx, 0x258
1414bc2bb  lea  rdx, [rbp + 0xc4ca0c]
1414bc2c5  add  rdx, r9
```

The same shape appears independently at `0x140e5c3da` and `0x1414f2b8f`, which is what
makes the stride and the bound trustworthy rather than a single reading.

FL26 ships **961 managers**. So there are **339 free manager slots**, available in pure data,
with no patched byte. That is the most immediately usable Master League finding here: real
managers with real names can be added to the game, and the ceiling is a long way off.

For comparison, the equivalent numbers elsewhere: teams 743 of 750 (7 free), competitions
91 of 256, runtime regulations 214 of 300.

### The player slots

The player array resisted the method that worked for coaches, because `0x1414f00c0` is not
the array builder at all — it walks `Player.bin` with the *on-disk* stride `0x138` and
collects ids into a vector. The real array shows up instead in the access idiom, which is
used at **110 sites**:

```
140af25f4  cmp  edi, 0x7531               ; index < 30001 ?
140af25fa  jb   0x140af2603
140af25fc  mov  eax, 0x184c3bc            ; out of range -> a dummy record
140af2601  jmp  0x140af260c
140af2603  mov  eax, edi
140af2605  imul rax, rax, 0x17c           ; index * 380
140af260c  cmp  dword ptr [r15 + rax + 0x158], r12d
```

There is no base displacement in the final access: the index scales by `0x17c` and is added
straight to the edit block pointer. So the **player array starts at `edit+0`, its runtime
record is 380 bytes, and the index bound is 30001**. An out-of-range index is redirected to
a fixed dummy record at `edit+0x184c3bc`, which is why that address turns up near player
code and is not a second array.

The arithmetic closes the case: `30001 × 380 = 0xadf4bc`, which is **exactly** where the
team array begins. The player array occupies `edit+0x0` up to `edit+0xadf4bc` with nothing
left over, so 30001 is the real capacity and not just a check someone forgot to update.

FL26 ships **27,927 players**, so there are **2,074 free player slots** in pure data.

### Free slots, all together

Everything above, in the form that actually matters when planning a mod. None of it needs a
patched byte.

| | runtime capacity | shipped | free |
|---|---|---|---|
| Players | 30,001 | 27,927 | **2,074** |
| Managers | 1,300 | 961 | **339** |
| Teams | 750 | 743 | **7** |
| Runtime regulations | 300 | 214 | **86** |
| Competition ids | 256 | 91 | **165** |

Teams are the one tight number, and that was already known. Everything else has real room.

Nothing in this section has been tested in game.

Nothing in this section has been tested in game.

### Are the array sizes stored in the save, hardcoded, or neither?

Neither, and this is the question that was blocking every limit-raising idea.

`0x1414f6ae0` is the block rebuilder. It runs about seventeen array builders back to back,
each in the same three-instruction idiom, all fed the same source object from `[rsi + 0x18]`:

```
1414f6caa  mov  rcx, qword ptr [rsi + 0x18]
1414f6cae  call 0x1414f1480          ; the regulation array
1414f6cb3  call 0x1414efc80          ; a tick between builders
1414f6cc6  mov  rcx, qword ptr [rsi + 0x18]
1414f6cca  call 0x1414f5120
```

Inside the regulation builder `0x1414f1480` the count has an unambiguous origin:

```
1414f1800  mov  rcx, qword ptr [rcx + 0x10]
1414f1804  call 0x14125f2c0          ; number of records in pesdb table 8
1414f1809  mov  ebx, eax
1414f180b  mov  dword ptr [rbp + 0x78], ebx     ; loop bound
...
1414f1b56  inc  esi                             ; one per object actually emitted
1414f1b58  mov  dword ptr [rsp + 0x50], esi
1414f1b68  cmp  edx, dword ptr [rbp + 0x78]
1414f1b6b  jae  0x1414f1bb2
...
1414f1d34  mov  ecx, dword ptr [rsp + 0x50]
1414f1d38  mov  dword ptr [rax + 0xd0bcf4], ecx ; the stored count
```

and `0x14125f2c0` is a small helper that bounds-checks a table id against `0x1c`, indexes an
array of 28 table pointers and tail-calls for that table's record count:

```
14125f2c0  cmp  edx, 0x1c
14125f2c3  jae  0x14125f2d4
14125f2c7  mov  rcx, qword ptr [rcx + rax*8]
14125f2ce  jne  0x1408aef50
```

So **the count at `edit+0xd0bcf4` is not a constant and is not read from the save. It is
recomputed at load time as the number of objects the builder emitted while walking the
pesdb table.** The same shape applies to the other builders and the other three counts in
the `4 × u32` block at `edit+0xd0bce8`.

For anyone modding, this is good news and bad news in one:

- **Good:** add rows to a pesdb table and the count follows by itself. Nothing has to be
  told the new size, and no save carries a stale one.
- **Bad:** because the size is derived rather than declared, the 300 and 750 ceilings are
  not a number you can edit. They are bound checks in the consumers — `cmp .., 0x12c` in 87
  places, `cmp .., 0x2ee` in 167 — plus the fixed room the array has inside the edit block.
  Raising a limit is a code patch, not a data edit. That is the answer, and it settles the
  question that was open in `docs/deepseek-notes.md` section 1.7.

This came out of the three builders' callers: `0x1414f1480` and `0x1414f5120` have exactly
one caller each, and it is the same function, which is what made it findable at all.

### The fixture cluster

Working back from the array rather than forward from the regulation turned out to be the
better direction. The fixture table is at `edit+0xd65f64`; `tools/dispscan.py` finds every
instruction referencing it by linear decode, and the stride shows up as `imul reg, reg,
0x208`.

The bound is confirmed in code at `0x14134e910`:

```
14134e90b  call 0x1414c9890           ; fixture index
14134e910  cmp  eax, 0x7d0            ; 2000, the hard cap
14134e91d  imul rcx, rax, 0x208
14134e924  lea  rsi, [rbx + 0xd65f64]
```

and the `(tag << 14 | slot)` handle split is visible a few instructions later as a pair of
`test` against `0x3fff` and `0xffffc000`.

23 sites reference the array, and they cluster:

- **Accessors, not logic** — `0x141546c70` (106 callers), `0x141579bd0` (20), `0x141510f00`
  (11). Ignore these; they are `GetFixture`-style helpers and they will pollute any search.
- **The season/day machinery** — `0x140fc8e20`, `0x14134d9c0`, `0x14134e6c0`, `0x141350650`,
  `0x141350b40`, `0x1413f4f90`, `0x1413f5b70`. Two of these were listed in an earlier version
  as `0x14134e570` and `0x1413f59d0`; those were bad function starts from the int3 walk-back,
  corrected above. `0x14134d9c0` and `0x14134e570` call each other, so that pair is
  recursive, which is what you would expect of round-by-round generation, and `0x14134d9c0`
  has exactly one caller, inside `0x14134e570`. The one external way into the recursion is
  `0x140fc8e20`.

Reading upwards from there with `tools/nameup.py`, the only named thing above the recursion
within six levels is `0x140fc8010`, which references the string `EventRankingListener`. That
is suggestive of standings rather than generation, but a call chain four levels long is weak
evidence and it is recorded here as a lead, not a conclusion.

`0x14134e570` is the one to start on: it is both the function the calendar-template chain
leads to and a function that walks the fixture array.

Still not proven to be the generator rather than a consumer. But this is the difference
between "somewhere in 39 MB" and "these seven functions", which is where the previous
version of this document left off.

Both of those rely on `tools/callindex.py`, which does one linear disassembly pass over the
39 MB code section and writes out every direct call as an exact (target, caller) pair —
709,555 of them. Byte-scanning for call opcodes mostly lands mid-instruction, so an exact
index is worth the one-time cost; every query after it is instant.

**There is also a plan B that I think is underrated.** The fixture table is at `edit+0xd65f64`, stride `0x208`, 2000 entries, and the schedule ID for a competition is read out of the runtime regulation object at `+0x88`. The season calendar is at `edit+0x16038a8`, stride `0x2c4`. The format is known. So in principle a fixture list can be written directly instead of asking the engine to generate one — you'd ship a precomputed schedule rather than fix the generator. Uglier, but it requires no understanding of the generator at all.

---

## 8. European qualification is in the exe, and it's a small patch

This one surprised me. Who qualifies for the Champions League and Europa League is **not** in the data files. It's a static table in `.data` at `0x1434f1fa0`, 112 rows of 12 bytes:

```
u32  source regulation ID   (the league or cup)
u32  right type             0 = competition winner, 13+n = nth league position (13 = 1st, 18 = 6th)
u32  target type            0 UCL groups, 1 UCL qualifiers, 2 UEL, 3 Libertadores,
                            4 Sudamericana, 7 AFC CL, 9 Belgian europlayoff, 10 Danish europlayoff
```

Real examples from the table: Premier League (regulation 17) positions 1–3 → UCL, 4th → UCL qualifiers, 5th–6th → UEL, FA Cup winner → UEL. Eredivisie 1st → UCL, 2nd → qualifiers, 3rd–4th → UEL. The loop filters rows by target type and by the region of the source league, which it reads from the runtime regulation object at bits 7–12 of `+0x30c`.

So a new league gets nobody into Europe by default, and your UCL just keeps drawing from the existing leagues.

**But the fix is genuinely small.** The table has exactly one consumer — nothing else in the binary references that range. To add rows you relocate the table to free space, then change the `lea rdi,[rip+…]` at `0x1413b7784` and the row count `mov ebp,0x70` at `0x1413b778e`. That's two edits and it can be scripted. Tiny patch, big payoff.

---

## 9. How much room is actually left

This is the part I think matters most, because "there's no space" is the other half of the folklore and it isn't true either.

### Competitions and leagues

| Thing | Limit | Used | **Free** |
|---|---|---|---|
| Competition IDs | 256 | 91 (ids 1..141) | **164** |
| Regulation IDs | 256 | 123 distinct (214 rows incl. group sub-rows) | **133** |
| Runtime regulation objects | 300 | 214 | **86** |
| Regions (countries) | 29 (0..28) | 24 | **5** — ids 0, 11, 13, 14, 20 |

Which region is which was not documented anywhere I could find, so here it is, read out of
`Competition.bin` byte 3 (`area = byte3 >> 3`):

| area | | area | | area | |
|---|---|---|---|---|---|
| 1 | club international (UCL, UEL, Libertadores, AFC CL) | 10 | Greece | 22 | Germany |
| 2 | England | 12 | Denmark | 23 | United States |
| 3 | France | 15 | Scotland | 24 | Japan |
| 4 | Spain | 16 | Brazil | 25 | national teams (World Cup + qualifiers) |
| 5 | Italy | 17 | Argentina | 26 | special (custom cup, custom league, friendlies) |
| 6 | Portugal | 18 | Chile | 27 | Turkey |
| 7 | Netherlands | 19 | Colombia | 28 | Saudi Arabia |
| 8 | Belgium | 21 | China | | |
| 9 | Russia | | | | |

The five free ids are gaps in the middle of the range, which suggests they held countries
in an earlier version.

**What the menu calls them is a different question, and the answer is uncomfortable.** The
exe holds a 24-record table at `0x1426770c0` mapping an area id to a display key
`compeCategory-<name>`. That table is PES 2021's original assignment, and FL26's data does
not always agree with it:

| area | exe display key | what FL26's data actually puts there |
|---|---|---|
| 10 | `swissConfederation` | Greece |
| 22 | `PEU` (generic "other Europe") | Germany |
| 23 | `PLA` (generic "other Latin America") | United States |
| 24 | `PAS` (generic "other Asia") | Japan |
| 28 | `thailand` | Saudi Arabia |

The other sixteen agree exactly, as do the three structural ids (1 `interClub`,
25 `interNational`, 26 `event`). The reading that fits is the obvious one: PES 2021 had no
licensed Bundesliga, J-League or MLS category, so Konami shipped generic continental buckets,
and FL26 filled those buckets with real leagues without touching the exe. **Untested in
game** — it predicts that Greek competitions appear under a Swiss label — but the data on
both sides is unambiguous.

Two consequences that matter if you are adding a country:

- The table contains **none of the five free ids** (0, 11, 13, 14, 20), and there is no
  fallback entry: the lookup falls through all 24 records and leaves the destination pointer
  untouched. A new region on a free id therefore has **no name key at all**. The one-byte
  `cmp al, 0x1d` → `0x20` patch in section 9 buys encoder headroom; the menu label is a
  separate problem and needs a new table entry, which is an exe patch.
- Adding to an id that already exists costs nothing and inherits that id's label, whatever
  it says.

A plain league costs 1 competition ID + 1 regulation ID + 1 runtime slot. A cup with a group stage plus knockout costs 1 competition ID + 2 regulation rows. The binding constraint is the 300 runtime objects, so:

**Without patching the exe at all, there is room for about 86 new competitions.** For scale, the game currently ships 42 leagues, 56 knockout competitions and 14 group stages, across 24 countries. You could add another two thirds of that on top, in data.

The catch is *where* they go. Those 86 competitions can be distributed as:

- **extra divisions and cups inside the 24 countries that already exist** — unlimited, no region needed. A D2, D3, D4, a league cup, a super cup for any existing country is pure data.
- **completely new countries — only 5 of them**, using the free region IDs 0, 11, 13, 14 and 20.

So five new nations, each with as many divisions and cups as you like, plus as much depth as you want in the existing 24. That is a *lot* of content and none of it needs a single patched byte.

Past that:

- **Regions 29 → 32 is a one-byte patch.** This one is worth spelling out, because 5 free countries sounds much more limiting than it has to be. Here is the actual parser code:

```
1414f8390  mov    ecx, dword ptr [rax]   ; dword0 of the regulation row
1414f8392  shr    ecx, 0x1b              ; >> 27
1414f8395  movzx  eax, cl
1414f8398  and    al, 0x1f               ; mask to 5 bits, so 0..31
1414f839a  cmp    al, 0x1d               ; is it >= 29?
1414f839c  jae    0x1414f83a2            ; yes -> reject, keep the default
1414f839e  movzx  r14d, cl               ; no  -> region = this value
```

  The field physically holds **0 to 31**. Values 29, 30 and 31 are perfectly encodable and the runtime region field is 6 bits wide (up to 63), so nothing downstream objects. They are thrown away by that single `cmp al, 0x1d`. Change the immediate byte at `0x1414f839b` from `0x1d` to `0x20` and you get **8 free regions instead of 5**.

  Past 32 you'd have to widen a 5-bit field in the record format, which is a different order of problem. And the honest caveat: I never found the menu name and flag tables, so a brand new region may well render blank or wrong in the UI even though the parser accepts it. Fixing the label is probably an `all.str` job, but I didn't get there.
- **Runtime regulations 300 → more**: `cmp ..,0x12c` in 87 places. Patching those is mechanical, but on its own it is *not enough* — see "The arrays are one fixed-layout block".

### Teams

| | |
|---|---|
| Exe array cap | **750** |
| Currently used | **743** — 7 free slots |
| Format ceiling | **16,381** (handle is `tag << 14 \| slot`, so 14 bits for the slot) |
| Array location | `edit+0xadf4bc`, stride 1680 bytes, counter at `edit+0xd0bcec` |

**750 is not a format limit, it's an array size** — the team handle reserves 14 bits for the
slot index, so the *handle* format supports 16,381 teams. That is worth knowing, but it is
not the ceiling, and an earlier version of this document treated it as though it were.
The array is embedded at a fixed offset in a block whose next array begins exactly where
this one ends, so the handle format is the *second* wall, not the first. See below.

For scale on what's in there now: the 42 shipped leagues account for 625 team entries, and `CompetitionEntry.bin` has 1317 rows total.

What raising it actually costs:

- `cmp ..,0x2ee` in **167 places**
- `imul 0x690` (the 1680-byte stride) in **124 places**
- roughly **120 displacement references** to `0xadf4bc`
- allocating a larger array past the end of the ~25.8 MB edit structure and redirecting every offset behind it
- **the EDIT serialiser**, so saves and option files still work — I never located this, and it's the part I'd expect to be genuinely fiddly

I want to be honest about the status of the 16,381 figure: that is what the handle format
permits, and nothing more. Nobody has taken this game past 750 teams as far as I know. The
167 `cmp` sites are fully enumerated, so that part of the work is not a mystery — but
patching them is necessary and not sufficient, for the reason in the next section.

### Raising the caps: the complete picture

This is the main goal of the project. The previous version of this section ended with "the
patch set is enumerated, but where to put it is not yet answered". It is answered now, and
three more things turned up on the way that change the cost: the block's allocation, a
*second copy* of the same arrays with the same caps, and the on-disk format. Everything
below is static, from the exe, with the tool that produced it named so it can be re-run.

**1. The block is allocated with a plain immediate, and growing it is six patches.**

The size that was "not anywhere in the code section" was there; the earlier scan looked at
the wrong range. Scanning every decoded instruction for an immediate operand in
`0x1860000..0x1a00000` (`tools/blockrefs.py`, range `blocksize`) finds exactly one value
with exactly four sites:

| site | instruction | what it is |
|---|---|---|
| `0x1414b6f72` | `mov edx, 0x1877068` then `call 0x1403fb410` | **the allocation** (tag `0x14`, zero-fill off), result stored to `[owner+0x48]`, then in-place ctor `0x1414b8750` |
| `0x1414b5d0d` | `mov edx, 0x1877068` then `call 0x140227930` | the matching free, size passed explicitly |
| `0x1414b707e` | `mov edx, 0x1877068` then `call 0x1403fb410` | a **backup copy** of the block, stored to `[owner+0x80]` |
| `0x1414b714a` | `mov r8d, 0x1877068` then `memset` | zero-fill fallback when there is no block to copy |

`0x1877068` = 25,653,352 bytes = the last referenced field (`+0x1877060`) plus 8. So the
block is `sizeof(EditBlock)` on the heap, nothing more. The backup copy at `0x1414b7060`
and its restore in `0x1414b6bf0` copy it with an unrolled loop of 128-byte chunks:
`mov edx, 0x30ee0` (`0x30ee0 * 0x80 + 0x68 = 0x1877068`) at `0x1414b70b1` and
`0x1414b6d29`. Those two constants are the only other places the size is baked in.

Six sites, all `mov reg, imm32`. **Growing the block itself is trivial.** That removes the
blocker the previous section ended on: a relocated array can go past `+0x1877068`.

The owner object is built by `0x1414b6f50` (one caller, `0x140403a90`, the data-set
loader that also pulls `TeamColor.bin`, `UniColor.bin`, `PlayerAppearance.bin`,
`StadiumEditParam.bin`). It allocates three blocks side by side:

| owner field | size | ctor | role |
|---|---|---|---|
| `+0x48` | `0x1877068` | `0x1414b8750` | the edit block |
| `+0x50` | `0x40258` (262,744) | `0x1414c5040` | not identified |
| `+0x60` | `0x260554` (2,491,732) | `0x1414bce10` | not identified |
| `+0x68` | `0x40` | `0x1414eec30` | then `0x1414f23d0(this, editBlock)` |

`0x1414b6a60()` returns the owner; `[rax+0x48]` is the block. That is the getter the
rest of the engine uses, and it is how the copy in point 4 below was recognised.

**2. The layout, completed.** The three record dummies sit packed right after the coach
array, and there is one more large array that had not been named:

| range | what | evidence |
|---|---|---|
| `+0xd0b0ec` | dummy **team** (1,680 B) | `cmp r14d, 0x2ee; jb; lea rsi,[r13+0xd0b0ec]` at `0x141eec94c`: the out-of-range fallback, same idiom as the player dummy |
| `+0xd0b77c` | dummy **regulation** (788 B) | same idiom, `cmp esi, 0x12c` at `0x141eece00` |
| `+0xd0ba90` | dummy **coach** (600 B) | same idiom, `cmp edi, 0x514` at `0x141eec6ec`; ends at `+0xd0bce8`, the count block |
| `+0xe9ff08..+0x16038a8` | **13,000 x 596-byte records** | copied out by `0x1414016b0` with `cmp ebx, 0x32c8; add rdi, 0x254`; ends byte-exact at the season calendar |

The 13,000-record array is the one open question in the layout: 596 bytes per record and a
cap of 13,000, well under the 30,001 player slots but well over anything else, is most
likely per-player state for the season mode. It has not been confirmed.

**3. The patch inventory, redone properly.** The earlier table counted only instructions
carrying the *bare* base address. `tools/blockrefs.py` now decodes every function from its
known start and collects every displacement or immediate that lands inside an array's
range, after dropping two kinds of noise it found the hard way: call targets below the
image base that the call index had recorded (they decoded the protector blob), and MSVC
switch tables (`mov ecx,[rdx+rax*4+off]` where `off` is the table's own RVA, which lands in
the team range for all of the menu code at `0x140a...`-`0x140c...`).

| array | range | sites | functions | of which |
|---|---|---|---|---|
| Teams | `0xadf4bc..0xc12e9c` | **179** | 117 | 47 `add/mov reg, 0xadf4bc`, 84 `lea [blk+0xadf4bc]`, 35 field displacements, ~13 that belong to another object (see point 4) |
| Regulations | `0xc12e9c..0xc4ca0c` | **550** | 391 | 288 `[blk + idx + 0xc12e9c + field]`, 215 displacements, 47 immediates |
| Coaches | `0xc4ca0c..0xd0bce8` | **478** | 266 | 281 displacements, 196 immediates |
| Count block | `0xd0bce8..0xd0bcf8` | 947 | 550 | all four counters |
| Fixtures | `0xd65f64..0xe63de4` | 137 real | 126 | 13 bare base; the rest of the 1,102 hits are unrelated constants like `0xe20014` |

And the bound checks (`tools/capmap.py`, per enclosing function):

| constant | sites | functions | spread |
|---|---|---|---|
| `0x2ee` (750) | 164 | 133 | 33 in `0x1413...`, 18 in `0x1414...`, 16 in `0x1415...`, 11 in `0x140c...` menus, 10 in the save code `0x141e.../0x141f...` |
| `0x690` (team stride) | 186 | 143 | same spread |
| `0x514` (1,300) | 39 | | |
| `0x12c` (300) | 305 | | includes unrelated uses of 300 |
| `0x7531` / `0x7530` | 130 / 77 | | |

So teams are **179 base sites + 164 bound sites + 186 stride sites**, not 84 + 167. Still
mechanical, still enumerable, but the next point is what makes it a project.

**4. There is a second copy of every array, with the same caps, in a different layout.**

`0x141401060` is a constructor. It builds, in place at `rcx`:

| offset | count x stride | ctor | what |
|---|---|---|---|
| `+0x50` | 750 x 0x690 | `0x1414c59f0` | teams |
| `+0x133a30` | 1,300 x 0x258 | `0x1414c5ff0` | coaches |
| `+0x1f2110` | 300 x 0x314 | `0x1414c98f0` | regulations |
| `+0x22bc80` | 2,000 x 0x208 | `0x140af1db0` | fixtures |
| `+0x329b00` | 13,000 x 0x254 | `0x140af1ed0` | the 596-byte records |
| `+0x1049b3c` | 80 x 0x15fc | `0x1414de7b0` | 80 of something 5,628 bytes wide; competition seasons is the guess |
| `+0x10b9588` | 250 x 0x88 | `0x1414dba10` | not identified |
| `+0x11403b8` | vector, capacity 30,001 x 380 | heap, `0xadf4c4` bytes | **players**, allocated separately at `0x14140146d`, filled with the `cmp ebx,0x7531 / mov eax,0x184c3bc` idiom |

Every adjacency is byte-exact again, and the *order* is different from the edit block
(teams first, no inline player array), so this is a genuinely separate type. It is filled
by `0x1414016b0`, which takes the edit block from `0x1414b6a60()->[+0x48]` and copies each
array across with the edit-block caps as loop bounds (`cmp ebx, 0x2ee` at `0x141401703`,
`0x514`, `0x12c`, `0x7d0`, `0x32c8`), then copies a further dozen fixed regions
(`edit+0x16038a8 -> +0xa8d4a0`, `edit+0x1787a48 -> +0xafa1a0`, `edit+0xd0bd04 -> +0xb08668`,
and so on). Both are called back to back from `0x140afbc50` and `0x140b0eb10`, two
"proceed / return" confirmation menus, i.e. **this copy is made when a mode is entered**,
and it is the mode's working database from then on. Its size is not an immediate: it comes
from a virtual on the mode object (`[0x143700898]->vt[7]`, mode byte at `0x143700891` in
{3, 4}), because there are two variants: `0x140afd660` builds the other one with **750
teams, 750 coaches, 180 regulations, 1,750 fixtures, 12,360 of the 596-byte records** and a
30,000-player vector (`0xadf348`).

Consequences:

- The team cap is enforced in **three layouts**: the edit block, the mode copy, and the
  mode copy's variant. Raising it in one and not the others gives a mode that silently
  truncates at entry.
- In the mode copy the team array starts at `+0x50`. Its field accesses are therefore
  ordinary small displacements (`[base + idx*0x690 + 0x50 + field]`), indistinguishable by
  value from any other struct access. They cannot be found by displacement range at all;
  the only handle is the 186 `imul ..., 0x690` sites, each of which needs its base traced.
- The ~13 "team slot 65 / 100 / 250 / 257 / 261" hits in the edit-block inventory are this
  object's fields (`+0xafa1a0`, `+0xb08668`, `+0xb45ec8`, ...) used from the copy code with
  the *mode copy* as base. A range-based patch of the edit block would corrupt them.
  Attribution per function is mandatory, not optional.

**5. The EDIT file is a count-driven container, so it does not need re-laying-out.**

The save buffer is allocated at four sites with `mov edx, 0xa7c860` (`0x141ef3453`,
`0x141ef35a2`, `0x141ef36d2`, `0x141ef4836`); `0xa7c860 + 0x880 = 10,997,984`, which is the
byte size of `dataSP/EDIT00000000` on disk. The writer is `0x141eec0d0`: for each table it
walks the edit-block array up to the cap, skips empty slots, and emits used records through
a per-record writer (`0x141ef4d70`), with a `cmp eax, 0x4000000` sanity check on the running
size. The reader is `0x141eede00`, which uses the pesdb row-count helper `0x14125f2c0` on
Coach, CompetitionRegulation, Competition, Player, Team, PlayerAssignment and
CompetitionEntry: the EDIT file is pesdb-shaped tables. Nothing in it is at a cap-dependent
offset. A larger team array changes nothing on disk except how many records there can be;
only the `0xa7c860` container would need growing if the content outgrew it (it will not for
teams: a Team row is 1,532 bytes on disk).

**6. The counts really are derived, and here is the scan.** `0x1414bc0a0` walks all 750
team slots (`lea rdi,[r13+0xadf4bc]; mov ebp,0x2ee`), compares each id against the empty
sentinel at `0x14351ae44`, and stores the tally to `+0xd0bcec`; the same for 1,300 coaches
into `+0xd0bcf0`. This settles the earlier "derived at load" answer with the actual code.

**7. So what does raising the team cap actually take?**

1. Grow the block: 6 immediates (point 1).
2. Move the team array past `+0x1877068`: rewrite 179 sites, after attributing each one to
   the edit block rather than the mode copy (point 4); move the dummy team with it or leave
   it (it is reached by displacement, not by index).
3. Raise every `0x2ee` bound and every `0x2ee` loop count that refers to teams: 164 sites in
   133 functions, each checked by hand for whether 750 means teams there.
4. Do the same inside the mode copy and its variant: relocate their team arrays (their
   constructors and the copy function are known), and find their accessors through the 186
   `imul 0x690` sites.
5. Leave the EDIT file alone (point 5); grow the container only if needed.

That is a **multi-week binary-patching project with a real chance of subtle corruption**,
not the afternoon the previous version of this section suggested. It is *possible*: every
constant is an immediate and every site is enumerable. But it is not cheap, and it is not
something to attempt without the game running to test each step, which this session cannot.

**Players, for completeness.** Nothing here changes the verdict for players. Their array is
at `+0`, so there is no base displacement to rewrite; growing them in place shifts every
field above `+0xadf4bc` in the edit block (thousands of sites), and the mode copy keeps its
own 30,001-capacity vector with its own `0x7531` checks. And the mode copy's 13,000-record
array (point 2) may be a separate per-player cap for the season mode that would need
confirming first.

**The linked accounting, which is what actually matters.** A club is not one slot. From
`PlayerAssignment.bin`, 21,303 assignments over 743 teams is **28.7 players per club**, and
each club has a manager. So "N more clubs" means N team slots, ~29 N player slots and N
coach slots at once:

| need per new club | free now | clubs that fit |
|---|---|---|
| 1 team slot | **7** | **7** |
| ~29 player slots | 2,074 | ~72 |
| 1 coach slot | 339 | 339 |

Teams are the wall, and only teams. Players and coaches have room for seventy-odd clubs
without touching anything. That means the *cheap* route is not raising a cap at all: it is
freeing team slots. Every unused national side, dummy or placeholder team among the 743 is
a club that can be added today with zero patching, and its players and manager fit.
Counting how many of the 743 are reclaimable is the next concrete task, and it is a data
question, not a binary one.

### Pre-biased displacements, and why range scanning cannot patch this game

Phase 0 of the plan set out to attribute every array reference to an object. The first thing
it turned up invalidates the site counts in the section above, so it belongs here rather
than in a changelog.

The function that fills the mode copy from the edit block, `0x1414016b0`, does this:

```
1414016ce  mov  rsi, [rax+0x48]     ; rsi = edit block
1414016f7  lea  rdi, [r14+0x50]     ; rdi = mode copy + team[0]
141401700  sub  r15, r14            ; r15 = edit block - mode copy
141401703  cmp  ebx, 0x2ee
14140170b  lea  rcx, [rsi+0xd0b0ec] ; out of range: the dummy team
141401714  lea  rcx, [r15+0xadf46c] ; 0xadf4bc - 0x50
14140171b  add  rcx, rdi            ; = edit + 0xadf4bc + i*0x690
```

`0xadf46c` is a reference to the edit block's team array, but it is stored **pre-biased by
the destination's offset inside the mode copy**, so it does not equal the array base and
does not fall inside the array's address range. Two consequences, both bad for the earlier
method:

- a range scan **misses** it, so a relocation built from range hits would leave this site
  pointing at the old address;
- and it **misfiles others**: `0xb18fdc` is `coaches - 0x133a30`, which lands inside the
  *team* range, and `0xa20d8c` is `regulations - 0x1f2110`, which lands inside the *player*
  range. The "team slot 140" and similar entries in the earlier inventory are these.

So references have to be attributed by what the base register actually holds, not by the
value of the displacement. `tools/attrib.py` does that with a small forward abstract
interpretation over each function, tracking every register as a linear expression over
`EDIT` (the block, recognised from `0x1414b6a60()->[+0x48]` or the handle dereference
`0x140edf9c0`) and the incoming arguments `A0..A3`. A base of `EDIT + c` is a direct site;
`EDIT - Ax + c` is a pre-biased one, and the array it means is recovered by matching the
displacement against `base - copy_offset` for each known pair. A second pass binds a
function's parameters when **every** caller passes the edit block, which resolved 323
arguments over two rounds.

The result, for teams: 136 direct, 2 pre-biased, 37 immediate, and **90 that the tool
refuses to classify**. That refusal is the useful part. Among the 90 are
`0x140afd770  lea rdx,[rsi+0xb45ec8]` and its neighbours inside `0x140afd660` — which is the
*mode copy's* constructor, where `rsi` is the copy and not the block. A range-based patch
would have rewritten them and corrupted the mode copy. They are excluded, and
`tools/patchset.py` refuses to emit a relocation set while any site for that array is still
unattributed.

**One more constant the tools now enforce.** The block may only grow by a multiple of
`0x80`. The backup copy is an unrolled loop of `0x80`-byte chunks with a fixed `0x68`-byte
tail (`0x30ee0 x 0x80 + 0x68 = 0x1877068`), so the size must stay congruent to `0x68` modulo
`0x80` or the copy runs off the end. The generator asserts it.

**Still unresolved from Phase 0.** The mode copy's allocation size comes from a virtual on
the object at `0x143700898` (`vt[7]`, via `0x141400b10`, only when the mode byte at
`0x143700891` is 3 or 4). Following the two factories `0x141b39b40` and `0x141b39a20` leads
to `0x141b3a8d0` / `0x141b3a9c0`, which store `0x142ac1460` at `[obj+0]` — but that address
is not a vtable: it holds an inline `std::string` ("Compression") among function pointers,
so it is a descriptor array and the trail stops there. This blocks Phase 2.2 only. The
cheap way around it, if the trail stays cold: both variants grow their team array by the
same amount, so a single `add eax, delta` after the virtual call in `0x141400b10` fixes both
— which needs a code cave rather than an in-place rewrite, and there is plenty of inter-
function padding for one.

### Two things identify the edit block when the interpreter loses it

The symbolic pass follows the block from the getter that returns it, so it attributes any
site it can reach along a chain of register moves. It loses the block whenever the pointer
goes through a spill slot, a struct field, or a branch it does not model — and it then
refuses to guess, which left 90 references to the team array unattributed. Two properties
of the block settle almost all of them without guessing.

**The count fields and the dummy records exist only in the edit block.** Every record type
has one shared out-of-range dummy, and the four live counts sit together near the end of the
block. The mode copy has none of this: it holds the same arrays at a completely different
set of offsets, its teams starting at `+0x50`. So a register that forms `+0xd0bcec` (the
team count) or `+0xd0b0ec` (the dummy team) is the edit block, whatever the interpreter
believed about it. `0x1414f5120` is the clean example — the base is loaded from `[r12+8]`,
which the tool cannot follow, and the two instructions before the site write the team and
coach counts through that very register:

    mov  rax, [r12 + 8]
    mov  [rax + 0xd0bcec], ecx      ; team count
    mov  [rax + 0xd0bcf0], r8d      ; coach count
    mov  rax, [r12 + 8]
    lea  r15, [rax + 0xadf4bc]      ; the team array

**The out-of-range fallback pairs the array with its dummy.** Every bounded accessor in the
engine compares an index against the cap and picks either the record or the shared dummy,
so both `blk + base` and `blk + dummy` are formed off the same register within a few bytes
of each other. That pairing identifies the block by itself, and it catches the accessors
where no count field is nearby.

The pairing has to be done on what the register *holds*, not on its name. Accessors
routinely copy the block pointer to a scratch register and then reach the array through one
name and the dummy through the other, as `0x140c7a0c0` does in five instructions:

    mov  r8, rcx
    cmp  edx, 0x2ee            ; the index against the team cap, 750
    jb   ok
    lea  rax, [rcx + 0xd0b0ec] ; the dummy team
    ret
    ok:
    lea  rax, [r8 + 0xadf4bc]  ; the team array

Keyed on register names those two lines look unrelated. Keyed on the symbolic value they are
the same pointer, and the `cmp` against the cap confirms which array it is.

Together the two rules resolved 39 of the 90 team sites in the first pass and the large
majority of the rest in the second. Both are recorded on the site as `edit-pattern` with the
evidence that produced them, so a patch set carries its own justification.

### The scaled index says which array, when the register cannot

Requiring a register to hold the block before a constant is attributed is right, but it
rejects the commonest accessor in the game, because the block arrives *after* the constant:

    cmp   dword ptr [rdx + 0xd0bcec], 0   ; the team count -- rdx is the block
    cmp   r12d, 0x2ee                     ; the index against the team cap
    jb    ok
    lea   rcx, [rdx + 0xd0b0ec]           ; the team dummy
    jmp   done
    ok:
    imul  rcx, rax, 0x690                 ; index times the team stride
    add   rcx, 0xadf4bc                   ; plus the team base
    add   rcx, rdx                        ; plus the block
    done:

At the `add` the register holds a scaled index, not a pointer, so a rule about what the
register contains cannot help. The multiply on the line above settles it instead: the six
arrays have six distinct strides, so a multiply by `0x690` names the team array, and a byte
size is never added to a scaled index. That pairing is checked over a three-instruction
window, which is all the idiom ever spans, and it resolved the 26 sites the stricter
immediate rule had opened up.

It is worth noticing why this is safe where attribution by value was not. `0xadf4bc` on its
own is ambiguous between the team base and the player array's size. `imul` by `0x690`
followed by `add` of `0xadf4bc` is not ambiguous at all — nothing in the block would multiply
by the team stride and then add the player array's size. The evidence is the *combination*,
which is the pattern every rule here follows.

### The layout, checked rather than assumed

`tools/layoutcheck.py` reads `patches/layout.json` and verifies the things the patch
generator takes for granted: that no two arrays overlap, that every dummy and count field
lies inside the block and outside every array, and that the block size still satisfies the
memcpy invariant. It runs in a second and should be run before generating any patch set.

    array        start       end         size       stride     cap  to next
    players      0x0         0xadf4bc    0xadf4bc      380   30001  packed
    teams        0xadf4bc    0xc12e9c    0x1339e0     1680     750  packed
    regulations  0xc12e9c    0xc4ca0c    0x39b70       788     300  packed
    coaches      0xc4ca0c    0xd0b0ec    0xbe6e0       600    1300  gap 0x5ae78
    fixtures     0xd65f64    0xe63de4    0xfde80       520    2000  gap 0x3c124
    rec596       0xe9ff08    0x16038a8   0x7639a0      596   13000  (last)

Two things fall out of it that were not obvious from the addresses alone.

**The four record arrays are packed with no padding at all**, and the run of them ends at
`0xd0b0ec` — which is the team dummy. So the shared dummy records sit immediately after the
coach array, in the order team, regulations, coach, followed at `0xd0bce8` by the four
counts. That whole cluster is one region, which is why raising a cap cannot simply extend an
array in place: everything after it, dummies included, would have to move.

**There are exactly three size/base collisions**, one at each packed boundary, and they are
the ones listed by the checker. The player dummy is the exception to the tidy picture: it
sits at `0x184c3bc`, far away in the 0x2737c0-byte tail past the end of the last array. That
tail is still unmapped and is the natural place to look for whatever Phase 3 needs.

### The mode copy is packed too, which reshapes Phase 2

The copy the game builds when it enters a mode holds the same records in a different order,
and `layoutcheck.py` now confirms it is packed exactly as tightly as the block:

    teams              +0x50         750 records of 0x690
    coaches            +0x133a30    1300 records of 0x258
    regulations        +0x1f2110     300 records of 0x314
    fixtures           +0x22bc80    2000 records of 0x208
    rec596             +0x329b00    then 5.9 MB of something else
    competitions80     +0x1049b3c
    x250               +0x10b9588
    players_vector     +0x11403b8

Every span is an exact whole number of records, and every cap matches the block's. That
settles a question the plan had left open, and not in the convenient direction: **making the
copy bigger is not enough.** Its team array is followed immediately by its coach array, so
growing teams in place would run straight into the coaches. The copy needs the same
treatment the block got — the array relocated to the end, every reference rewritten — before
any cap can move.

The references to rewrite are already identified. They are the pre-biased displacements and
the copy-family functions that the team-array work deliberately excluded, so the exclusion
list built for Phase 1 is the input list for Phase 2.

One piece of good news in the same table. The copy has no inline player array: it holds a
`players_vector` at `+0x11403b8`, filled by a separate heap allocation of `0xadf4c4` bytes in
the constructor. Raising the *player* cap in the copy is therefore a size change and not a
relayout, which is the opposite of the team situation.

What still blocks this is the copy's allocation size, which comes from a virtual and whose
trail went cold. That is now the single thing standing between the finished team-array work
and a raised cap.

### A size and the next base are the same number

The arrays are packed end to end, so each array's base equals the total size of everything
before it. That makes a constant genuinely ambiguous, and the ambiguity is not academic:

    0x7531 * 0x17c = 11,400,380 = 0xadf4bc

which is the player cap times the player stride, and also the base of the team array. A
scanner that attributes constants by value therefore reads every "size of the player array"
as "pointer to the team array". Three such sites were classified as team references before
this was noticed, and one of them is an allocation argument:

    mov  r12d, [r13 + 0xd0bce8]   ; the player count
    mov  edx, 0xadf4c4            ; 0xadf4bc + 8: the size to allocate
    call 0x1403fb410
    ...
    mov  eax, 0x184c3bc           ; the player dummy
    add  rbp, 0x17c               ; the player stride
    cmp  ebx, 0x7531              ; the player cap
    jb   loop
    mov  [rsi + 0x11403a8], 0xadf4bc   ; the exported block's size, into the vector header

Everything around those two constants is the player array. Rewriting them to move the team
array would have allocated a buffer of the wrong size and recorded a wrong length — the kind
of fault that corrupts quietly rather than crashing at the patch site.

So an immediate is only attributed when the register it is added to is already known to hold
the block. `add rcx, 0xadf4bc` where `rcx` is the block is the team array and nothing else;
`mov edx, 0xadf4c4` proves nothing on its own and goes to review. The three sites above are
recorded in `patches/attrib-manual.json` with verdict `size` and the array they size, because
they are not junk: they are exactly the sites that must be patched when the *player* cap is
raised, and the note is there so that phase does not have to rediscover them.

The general lesson for the later phases: in a packed block, six of these collisions exist by
construction, one at every array boundary. Attribution has to come from what a register
holds, never from what a number looks like.

### What is left is deliberately not patched

Six functions and four sites survive both rules, and all of them must stay unpatched. They
are recorded in `patches/attrib-manual.json` with the reasoning, and the generator will not
emit a set while any site is still unattributed.

Five of the six are the mode copy's own constructors and fill routines. Their displacements
land inside the team array's *value* range while pointing at fields of a different object —
`0x141401060` builds sub-objects at `+0xafa1a0`, `+0xb628c8`, `+0xc07430` and so on, off the
copy it is constructing. The proof that these are the copy and not the block is that the
same offsets appear in the fill function `0x1414016b0` off `r14`, in a function where the
interpreter separately and correctly attributes the `rsi` side to the edit block. The sixth,
`0x140af30f0`, takes its base from `[owner + 0x270]`; the destructor directly above it frees
that same field through `0x141400890`, the copy constructor's neighbour, which is what makes
`[owner + 0x270]` the mode copy.

The four remaining sites are not code. Two decode as `test byte ptr [rax + rax + disp], bh`
— base and index the same register, which no compiler emits for an array — and two read an
MSVC switch jump table whose address happens to fall in the team range. In all four the
displacement points within a kilobyte of the instruction's own address, which is the tell: a
block offset has no reason to sit next to the code that uses it.

This is the part worth keeping in mind for the later phases. Of the references that look
like the team array by value, a good third of the hard cases are not the team array at all,
and patching them would corrupt an unrelated object rather than fail loudly.

### The arrays are one fixed-layout block

This is the constraint that governs every "can we raise the limit" question, and it was
missed until the player array was located.

The big arrays are not separately allocated. They are fields at fixed offsets inside one
edit block, laid end to end, and **each array's capacity exactly fills the gap to the next
array**:

| array | base | runtime record | capacity | bytes needed | bytes available |
|---|---|---|---|---|---|
| Players | `edit+0x0` | 380 | 30,001 | 11,400,380 | 11,400,380 |
| Teams | `edit+0xadf4bc` | 1,680 | 750 | 1,260,000 | 1,260,000 |
| Regulations | `edit+0xc12e9c` | 788 | 300 | 236,400 | 236,400 |
| Coaches | `edit+0xc4ca0c` | 600 | 1,300 | 780,000 | 782,468 |

Three of the four are exact to the byte. The coach row has 2,468 bytes left over, which is
where the dummy coach record at `edit+0xd0ba90` lives, immediately before the count block at
`edit+0xd0bce8`.

That symmetry is not a coincidence and it is not slack anyone left for modders. It means
the caps are **layout**, not just checks:

- Patch the 167 team `cmp` sites to allow 16,381 teams and the array needs 27.5 MB where
  1.26 MB exists. Team 751 onward is written straight over the regulation array, then the
  coaches, then the counts.
- Patch the player bound to 40,000 and the array needs 15.2 MB where 11.4 MB exists, and it
  runs over the teams.

To genuinely raise any of these you would have to move every array after it, which means
rewriting the base displacement in every one of the hundreds of `lea [reg + 0x…]` sites that
address them — and the block is serialised, so old saves would no longer load.

So the practical position is the one in the free-slot table: **2,074 players, 339 managers,
7 teams, 86 regulations and 165 competition ids are genuinely available, and the numbers
above them are a different and much larger piece of work than patching a comparison.**

### Short version

| Want to add | Exe patch needed? |
|---|---|
| A new division or cup in an existing country | **No** |
| A new country with a full league pyramid (5 available) | **No** |
| Promotion/relegation between your new divisions | **No** |
| Up to ~86 new competitions total | **No** |
| Your new league feeding into UCL/UEL | Yes, but tiny — 2 instructions |
| A 6th, 7th, 8th new country | Yes — literally one byte, plus unknown UI name/flag tables |
| More than ~86 new competitions | Yes, 87 sites |
| More than 7 new clubs | Yes, and this is the big one — ~400 sites + serialiser |

---

## 10. A suggested order, for whoever wants to try

If I were the one doing this, here's the order I'd attack it in. Steps 1 and 2 need no exe patching at all, which is why I'd start there.

1. **New league, data only.** Three table rows. Test whether it shows in the menu (it does) and whether the season generates. That last part is the open question — try an existing country's calendar template first.
2. **Second division with promotion and relegation.** Also data only, two integer fields.
3. **European rights for the new league** via the `0x1434f1fa0` table patch. Small patch, large payoff.
4. **Domestic cup and super cup** for the new country. Format templates 2 and 3, data only, plus one rights row for cup winner → UEL.
5. Raise the regulation limit past 300 if you need more competitions (87 sites, same pattern as teams but fewer).
6. Raise the team limit past 750 (167 sites, plus allocation, plus the EDIT serialiser).
7. New regions beyond the free 5 — the one-byte parser patch is trivial, but the menu name and flag tables are the unknown part.
8. A brand new continental competition with its own qualification rights — needs the target type → competition mapping, which I never located.

---

## 11. What's still unsolved

These are the loose ends, in rough order of how much they block. If you already know any
of these, saying so is the single most useful thing you could do with this document.

1. **The fixture generator.** Does a new league schedule correctly if it reuses an existing
   country's calendar template? If not, where in `ModeDataCreationThread` does generation
   actually happen? Everything else on this list is a nice-to-have; this one decides
   whether new leagues are playable at all. Progress: the calendar template field is now
   fully traced and its four consumers identified (section 7), and none of them is the
   generator — which at least rules out a large branch of the search. The remaining chain
   `0x14134c230` -> `0x14134c4d0` -> `0x14134e570` carries no RTTI and no strings, so
   naming it probably needs a debugger.
2. **The EDIT serialiser** — how the edit block is written to saves. Needed before any
   limit raise is safe, because a bigger array that does not round-trip through a save is
   worse than no change at all.
3. **Region name and flag tables in the menus.** Needed to use the 5 free region ids
   properly. New lead: `EditLeagueOrganizeAreaSelect` at `0x140c023f0` (section 7) is the
   menu that renders the region list, so whatever it reads is the answer. I looked for a 29-entry table statically — scanning for an array with exactly
   the free ids 0, 11, 13, 14 and 20 blank — and found nothing outside packed data, so it
   is not a plain array indexed by region. Likely a string-id lookup; finding it probably
   needs a debugger rather than a file scan.
4. **What decides which leagues the League/ML menu offers.** No hard id list in the exe.
   `CommonLib.lua` has one, but that is a community module, not the game. Most likely
   derived by filtering regulation rows on type and rank, which is consistent with a new
   league appearing in the menu unprompted.
5. **Target type → competition mapping** for European qualification, needed for genuinely
   new continental competitions rather than reusing an existing slot.
6. **What bit 26 was for.** It is proven inert (section 5); the historical meaning is a
   guess. Cosmetic curiosity rather than a blocker.

Every flag bit in the dword at `0x10` is now accounted for.

Closed since the first version of this document: bits 21-23 at `0x10` (matchday template),
bit 24 (away goals), bit 26 (inert) and bit 30 (group labels), all in section 5; the
region-to-country map (section 9); and `CompetitionKind.bin`, `Country.bin` and `Team.bin`
(section 6).

---

## Bonus, unrelated: graphics presets are a Lua file

While digging I found that every graphics quality preset — shadow resolutions, LOD rejection length bias, local lights, SSAO/SAO, crowd quality type, subsurface scattering — is plain readable Lua at `Fox/Scripts/Gr/gr_init_dx11.lua` inside `Data\dt00_x64.cpk`. No exe patching required to build a higher-quality preset than the game offers, and Sider livecpk may be able to override it directly.

Also: `settings.dat` in `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE` is 612 bytes with a `WECF` header and is fully decodable. And no, there's no FPS unlock worth chasing — the match simulation itself is tied to 60 fps.

---

## Status

Confirmed working: a new league defined purely in data appears in League mode and is
selectable. Not working: the season scheduler generates no fixtures for it. That single
problem is the difference between "listed" and "playable" — see
[What's still unsolved](#11-whats-still-unsolved).

## The size that blocks 750 is a constant, not a virtual call

Phase 2 has been stuck on one question: the mode copy is allocated from a size that the
disassembly traced to a virtual call, `[0x143700898]->vt[7]` reached through
`0x141400b10`, and the trail went cold at a descriptor array rather than a vtable.  With
the game running the object could have been read directly -- but it is null outside a
mode, so that was not the way in either.

Reading `0x141400b10` to the end settles it without any of that:

```
141400b10  movzx  eax, byte [0x143700891]     ; the mode byte
141400b1b  sub    al, 3
141400b1d  cmp    al, 1
141400b1f  jbe    0x141400b28                 ; only modes 3 and 4 go on
141400b21  xor    eax, eax
141400b27  ret
...
141400b63  mov    rax, [rcx]                  ; mode 4: ask the codec
141400b66  call   qword ptr [rax + 0x30]      ;   how long the serialised data is
141400b69  add    eax, 0x11403b8              ;   past the arrays
141400b6e  cmp    eax, 0x15b6d94              ;   does it still fit?
141400b73  jbe    0x141400b81
141400b75  mov    byte [0x143700891], 3       ;   no -- fall back
141400b7c  mov    eax, 0x15b6d94              ; mode 3: the whole thing
141400b81  mov    rcx, [0x1437008a0]
141400b8d  add    eax, ecx                    ; plus a global slack value
141400b93  ret
```

The virtual call is not where the size comes from.  It asks the codec how much
*serialised* data there is, so a partly-filled copy can be allocated small; the answer is
then clamped against the same constant, and if it does not fit, the mode byte is knocked
back to 3 and the constant is used anyway.  `0x141400ba0` is the same constant with no
question asked.

    0x15b6d94   22,769,044   the copy object
    0x11403b8   18,088,888   where its serialisation buffer starts
    0x4769dc     4,680,156   how long that buffer is

and 18,088,888 + 4,680,156 = 22,769,044 exactly.  The copy object is the arrays followed
by one buffer, with nothing else in it.

The constant appears three times and nowhere else:

    141400b6e  cmp  eax, 0x15b6d94       the fits-in-the-object check
    141400b7c  mov  eax, 0x15b6d94       the mode-3 answer
    141400ba0  mov  eax, 0x15b6d94       the other allocator's answer

Both allocation paths lead there.  At `0x140afbe06` the result of `0x141400b10` goes
straight into the aligned allocator at `0x1403fb410`, and at `0x140af1baa` the result of
`0x141400ba0` does the same after adding what `0x140ef0000` returns.  Three constants
grow the copy object; there is no vtable to chase.

`0x1437008a0` deserves a note of its own.  It is added to the size unconditionally, so it
looks like a ready-made growth knob -- but the same global is read as a length and stored
into the object's own `[+0x11403ac]` field at `0x1414007f4`, so it means something to the
serialiser as well.  It is not free space to take; the constants are.

### What the copy's constructor says the caps are

`0x141401060` builds the copy by running a placement-new loop over each array, and each
loop's trip count is that array's capacity.  Read straight off:

    +0x50        stride 0x690    0x2ee  =   750    teams
    +0x133a30    stride 0x258    0x514  =  1300    coaches
    +0x1f2110    stride 0x314    0x12c  =   300    regulations
    +0x22bc80    stride 0x208    0x7d0  =  2000    fixtures
    +0x329b00    stride 0x254    0x32c8 = 13000    rec596
    +0x1049b3c   stride 0x15fc   0x50   =    80    competitions
    +0x10b7a58   stride 0x8d8    0x3                (three of something)
    +0x10b9588   stride 0x88     0xfa   =   250    x250

Every one matches the block's own capacity.  The copy is not a different shape, it is the
same shape laid out in a different order -- which is why raising a cap means editing two
layouts, not one.

The teams gap is worth measuring, because it is the first thing anyone would hope to use.
There is none: `0x50 + 750 * 0x690` ends at `0x133a30`, and the coaches begin at
`0x133a30`.  The copy is packed to the byte, exactly as the block is.

That leaves one way to fit 1600 teams, and it is the opposite of what the block needed.
The block's team array had to move to the end because its base is a 32-bit displacement
that every reference spells out.  The copy's team array is at `+0x50`, a disp8 that no
amount of patching can widen in place -- but every field *after* it is already a 32-bit
constant.  So in the copy the teams stay where they are and everything after them moves
out by `0x15ca20`, and not one instruction has to change length.

## The copy's layout, measured instead of read

Shifting the eight offsets the copy's constructor names, and nothing else, killed the game
the moment Master League finished loading -- at `0x141fea5ba`, on a null `this`.  A control
run with the identical menu walk and no patches went straight past the same cutscene into
the board meeting, so the patches caused it and not the flow.

Following the copy pointer through the copy functions instead of matching constants found
77 distinct offsets rather than 8, and two clearly different shapes among them.  That is
more list than evidence, so the question went to the running game.

The copy holds a duplicate of the block's arrays.  Take records 0..5 of one block array,
search the copy for each, and if the hits step by exactly that array's stride then that
array really is there and its base is measured rather than guessed.  Six records at the
right stride is not something that happens by accident.

Inside Master League there are two objects carrying team data.  The one that answers to
every probe lies out like this:

    +0x50        750 x 0x690    teams          ends +0x133a30
    +0x133a30    300 x 0x314    regulations    ends +0x16d5a0
    +0x16d5a0   1300 x 0x258    coaches        ends +0x1df9c0
    +0x286af8   2000 x 0x208    fixtures       ends +0x384978
    +0x3c0a9c  13000 x 0x254    rec596

Teams, regulations and coaches are packed end to end.  Fixtures and rec596 are not: there
is `0xa7138` between the coaches and the fixtures and `0x3c124` between the fixtures and
rec596, so something unmeasured sits in each gap.

This contradicts what `0x141401060` says.  That constructor puts 1300 records of `0x258`
at `+0x133a30`; the running game has 300 records of `0x314` there.  Both readings are
careful and they cannot both describe the same object, so they describe different objects:
`0x141401060` builds one shape, and the object Master League actually fills is another.
The earlier note calling the copy "the same shape in a different order" was drawn from the
constructor alone and is wrong for the object that matters.

The practical consequence is the important part.  A relayout of the copy cannot be
generated from the constructor's constants, because those constants belong to a different
object; and it should not be generated from a 77-offset dataflow list either, because that
list mixes the shapes together.  Until each shape is separated and measured, the copy is
not safe to move -- which makes raising the *block's* cap while leaving the copy at 750 the
cheaper thing to try, since the copy would then simply never see a team past the 750th.

## The 751st club exists, and where it stops

`teams-1600-block` was only ever shown not to break startup. The test it was built for is
to put clubs in, so `tools/addteams.py` clones a working club record into the free slots
and raises the count.

The array's own arithmetic answers the first question before the game does. Slots 743 to
749 read `ff ff ff ff` and slot 750 onwards reads zero: the old build initialised exactly
750 records and nothing beyond, so the zeros are ground the game has never touched. Writing
ten clubs across that boundary and setting the count to 753 left the game running, with the
counts intact, and the records read back correctly from slot 750, 751 and 752 -- past the
limit, in the live process, with the game still playing.

The club id is not the record's index. The dword at `+0x00` is the id shifted left by
fourteen; the low fourteen bits are zero in all 743 records, and the array is sorted by it.
The highest id in use is 71577, so new clubs take 71578 upwards and stay at the end of the
sort.

### A reload wipes them, and says exactly which sites are still wrong

Walking on to the main menu put the count back to 743 and refilled records 743..749 with
`ff ff ff ff` -- but left 750, 751 and 752 alone. That is a loop bounded by 750 writing
into the *relocated* array: the base it used was patched, the count it used was not.

Which sites those are follows from the patch set itself. `teams-1600-block` held thirteen
cap sites at 750 because they sit inside the copy code, on the argument that the copy's
team array is not moving. But four of the team-base relocations land inside that same copy
code, at `0x1413fea74`, `0x1413fedf7`, `0x141401714` and `0x141401c8a`. A function that
reads the block's team array at the block's own offset is working on the block, whatever
region it was grouped into, so its bounds checks guard the block and have to be raised with
it. That splits the thirteen: seven belong to the four block functions `0x1413fea10`,
`0x1413feda0`, `0x1414016b0` and `0x141401c10`, and six belong to the copy proper
(`0x140af30f0`, `0x140afd660`, and the copy constructor `0x141401060`).

`teams-1600-blockfull` raises 105 sites instead of 98 on that rule and the game still
starts, loads and plays.

## Where a league is defined

The array the layout calls `regulations` is the competition table: 215 records of 0x314
bytes with 300 allowed, each one a u16 competition id at `+0x00`, a name at `+0x02`, and a
list of team ids at `+0x170` that runs to the first `ff ff ff ff`. Forty-eight slots fit.

Everything the game treats as a competition is one of these records -- Premier League with
its twenty clubs, both AFC Champions League seasons with thirty-two, the Croatian
SuperSport HNL with ten. Ids above 1024 are season variants, `season << 10 | base id`, not
free slots; the free ones between the HNL and the AFC Champions League are 12, 13 and 14.

So a new league is a new record and nothing more exotic. `tools/addleague.py` clones the
HNL, because it is the only ten-club league in the table and a league of ten placeholder
clubs wants its shape, and inserts the clone at its sorted position with the ten
placeholder ids in the list. The table went to 216 and the game kept running.

## The Edit UI does not read either table

The new league did not appear, and neither did the clubs.

Edit mode's league list is curated, not enumerated: the Croatian SuperSport HNL is in the
competition table with ten clubs and is not in the list at all, and the list's Asian
section, "Other Clubs (Asia)", holds about ten hand-picked clubs and not Selangor, whose
record the placeholders were cloned from. Replacing Arsenal's id in the Premier League's
competition record did not change the Premier League's team list on screen either.

The team record does carry a grouping byte at `+0x418`, but it is the country, not the
league: 204 for England, 215 for Italy, 210 for Germany, 13 for Japan, 21 for Malaysia, one
value per nation across all 743 clubs.

So the UI's lists come from somewhere else -- the competition data files rather than the
edit block. Raising the block's caps buys the storage; it does not by itself buy a league
the menus will show.

## Edit > Save does not carry a new club

The save path works and is easy to drive: Settings > Edit > Save, two confirmations, and
the file lands in `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save`, not in the
game folder's `dataSP`. Saving with 753 clubs and 216 competitions in memory grew
EDIT00000000 by 999 bytes.

It did not bring them back. Restarting -- with the seven extra cap sites raised, so the
loader is not the clamp -- gave 743 clubs and 215 competitions again, with slots 743
onwards empty. The save is a delta over base data the game loads from its own data files,
and a club that does not exist in that base has nothing to be a delta of.

Persistence for new clubs therefore runs through the data files, the same place the UI gets
its league lists, and not through the edit save.

## 753 clubs, from the game's own data

The base a new club needs is `common/etc/pesdb/Team.bin`: 743 records of 1532 bytes in
Konami's WESYS zlib container, shipped in `download/data_s2526*.cpk` and served instead
from disk by any of Sider's livecpk roots. The FL mod's own `01_smkdb_fa*.cpk` do not
contain pesdb at all, so the season files are the only source and nothing overrides them.

Two fields identify a club. The dword at `+0x08` is the id -- unique, ascending, and equal
to the ids in the live block, with 71577 as the last of them, which is Selangor FC at
record 742. The dword at `+0x00` is a second id of another kind, also unique. The name is
at `+0x170` and the three-letter abbreviation at `+0x372`, the same two strings the block
carries at `+0x04` and `+0x4a`.

`tools/mkteams.py` clones the last club ten times, gives each fresh ids, a placeholder name
and a placeholder abbreviation, and packs the result back into WESYS. Dropped into a
livecpk root, with `teams-1600-blockfull` applied:

    players       27927
    teams           753
    coaches         774
    regulations     215

    743 id= 71578  FL Test 01  T01
    750 id= 71585  FL Test 08  T08
    752 id= 71587  FL Test 10  T10

Ten clubs past the old limit, in the block, after a full restart, with names -- and the
game made ten managers to go with them without being asked, which is the clearest sign that
it accepts them as real clubs and not as data sitting in an array.

The three pieces each did their part: the block grew and the array moved so there is room,
the cap sites were raised so the loader fills all 753 rather than stopping at 750, and the
data file supplies the clubs the edit save cannot.

## A new league, in the data and in the block

Three tables under `common/etc/pesdb` define a competition, and `tools/mkleague.py` writes a
row into each:

  `Competition.bin`, 36 bytes: `b0`/`b1` are 100/200 everywhere, `b3` is a region slot,
  `b5` the competition id, `b6` a flag, and a code string from `+0x08`. The region slots run
  in eights -- 16 England, 24 France, 32 Spain, 40 Italy, 128 Brazil, 192 Japan -- and the
  shipped rows use twenty-odd of them.

  `CompetitionRegulation.bin`, 2352 bytes: regulation id at `+0x02`, competition id at
  `+0x08`, type at `+0x09` (4 is a league), team count at `+0x0b`, and the name **twenty
  times over** from `+0x14`, one 0x73-byte slot per language. Writing only the first slot
  produced a league that still called itself Premier League on screen, which is what
  identified the other nineteen.

  `CompetitionEntry.bin`, 12 bytes per club: club id at `+0x00`, a unique entry id at
  `+0x04`, competition id at `+0x08`, and the club's position in the league at `+0x09`.

With those three rows the block comes up with 753 clubs, 216 competitions, and record 11
reading id 12, "FL Test League", holding FL Test 01 through FL Test 10 -- a new league of
ten placeholder clubs, from the game's own data, after a restart.

### It is still not in the menus

Neither Kick Off's league list nor Edit's shows it, with the league sitting in England's
region slot between the Premier League and the EFL Championship where a shipped league
would appear. An earlier attempt had put the Croatian league in region slot 88, which no
shipped row uses, and that was worth ruling out -- but slot 16 is England's own and the
result is the same.

So the menus do not enumerate `Competition.bin`. They work from a list of competition ids
the executable itself holds, and a competition whose id is not in that list exists in every
table and appears nowhere. That list is the next thing to find, and it is what stands
between one placeholder league and thirty.

## The edit save masks every data-file change

Two runs of `joinleague.py` put the ten placeholder clubs into the Premier League's
`CompetitionEntry` rows and raised regulation 17 from 20 teams to 30, and the game kept
loading twenty clubs.  Nothing was wrong with the rows.  `EDIT00000000` was.

The edit save is not a list of edits on top of the shipped data in the sense of "the fields
the player changed".  It carries whole competition rosters, and when it is present the
rosters in `CompetitionEntry.bin` are never consulted.  A save written before the data
files changed therefore silently pins the old squad list, with no error and no visible
difference between "my rows are wrong" and "my rows are not being read".

With the save moved aside:

    teams: 753 regulations: 215
    Premier League: 30 clubs; last 12: West Ham United, Wolverhampton Wanderers,
      FL Test 01 .. FL Test 10

and in Edit > Teams > Premier League the list scrolls past Wolverhampton to FL Test 01
through FL Test 10, each selectable, each with its own ratings
(`docs/img/edit-premier-league-fl-test.png`).

That is the 750-club limit broken end to end: clubs numbered past the cap exist in the
block, are held by a competition, and are reachable in the UI.

The practical rule for every later test: after changing a pesdb file, delete or move
`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\EDIT00000000` before deciding
that the change did not work.

## The new clubs survive in the game's own save

The save that masked the data files was the *old* one.  Once it was gone and Edit mode
wrote a fresh `EDIT00000000` (10998983 bytes -- the container is a fixed size, so a bigger
roster costs nothing on disk), the game was stopped and started again with that save in
place:

    block 0x7ff4e31e0010  teams 753 (cap 1600)  regulations 215  coaches 774
    highest club id 71587 (FL Test 10)
      record 13, id 17, Premier League -- 30 clubs
        Arsenal FC .. Wolverhampton Wanderers, FL Test 01 .. FL Test 10

So the order that works is: change the data files, delete the save, let Edit mode write a
new one.  From then on the save carries the new clubs itself.  `tools/blockstat.py` is the
one command that asks the running game all of this.

## A new competition is invisible, and the region byte is not the reason

`Competition.bin` byte 3 groups competitions into what the Edit menu calls a Competition
Category, in steps of eight:

    8   int'l clubs      16  England    24  France    32  Spain    40  Italy
    48  Portugal         56  Netherlands 64  Belgium  72  Russia   80  Greece
    96  Denmark         120  Scotland  128  Brazil   136  Argentina 144 Chile
    152 Colombia        168  China     176  Germany  184  US       192  Japan
    200 national teams  208  custom    216  Turkey   224  Saudi Arabia

so the index is byte 3 / 8, and 0, 11, 13, 14, 20, 29 and up are unused.

FL Test League was given byte 3 = 16, England's slot, and Edit > Competition Structure >
Europe still listed eighteen competitions -- the same eighteen as before, Belgium through
Turkey, with Premier League 3/18 and EFL Championship 4/18 and nothing new.  It was then
rebuilt with byte 3 = 104, the free slot 13, on the theory that a competition sharing
England's slot was being deduplicated away.  Same result: eighteen.  And Edit >
Competitions, which lists the categories themselves with their flags, shows no category
for slot 13 either -- the list runs Int'l Competitions, Belgium, Denmark, England, France,
Italy, Netherlands, Portugal, Russia, ... with nothing between Denmark and England and
nothing new at the end.

Meanwhile the block holds the league perfectly:

    block ...  teams 753  regulations 215
      record 10, id 12, FL Test League -- 10 clubs
        FL Test 01 .. FL Test 10

So byte 3 is not a filter the menus apply; it is a label they read *after* deciding what to
show.  The decision is made somewhere else, and three searches say it is not made from a
list that exists as data:

- no window anywhere in the 438 MB exe holds all eighteen European league ids as u8, u16
  or u32 within 144 bytes;
- no window anywhere in the running process holds them either;
- no array anywhere in the running process holds pointers to the eighteen regulation
  records, whose addresses were read out of the block first.

The eighteen are Belgium 111, Denmark 128, England 9 and 66, France 12 and 68, Germany 39,
Greece 117, Italy 10 and 69, Netherlands 13, Portugal 14, Russia 114, Scotland 137, Spain
11 and 67, Turkey 119 and the custom league 86 -- exactly the league-type competitions in
Europe that ship with the game, and no more.

Worth remembering while this is open: Belgium, Denmark, Scotland, Greece, Turkey, Russia,
China, Colombia and Saudi Arabia are not in vanilla PES 2021.  Whoever built Football Life
added them, and if the list is not data then they added them to the executable, which is
where this has to go next.

## A new league is playable -- the Competition Structure list is not the whole game

Competition Structure is a curated list and a new competition never joins it.  That looked
like the blocker for thirty leagues.  It is not, because it is not the list the game plays
from.

Kick Off > League > New lists the leagues by name, and there, third from the top between
3F Superliga and Premier League, sits **FL Test League** with FL Test 01 through FL Test 10
in the League Info panel (`docs/img/kickoff-league-fl-test.png`).  Selecting it, taking the
default settings and picking FL Test 01 starts a season: the mode opens on a fixture,
FL Test 01 v FL Test 06 on 12/9/2025, with Forward Time, Game Plan, My Team Info, Database
and System (`docs/img/kickoff-league-fl-test-started.png`).

So the recipe works end to end.  Ten placeholder clubs past the old 750-club limit, in a
competition id the game has never seen, in a league that can be played.

Two caveats worth writing down before they are forgotten:

- The competition this test ran under was **cid 130**, one of the free ids inside the range
  Football Life itself used for its added leagues (111-141).  cid 6 and cid 7 were tried
  earlier; all three are equally absent from Competition Structure, and cid 130 is the one
  that has been carried all the way into a playable season.  Whether the low ids play as
  well is untested.
- The fixture header reads **FA Cup - Round 1**, not FL Test League.  The competition
  category byte was 16, England, so the mode appears to have pulled England's cup into the
  season's calendar and to be branding the fixture with it.  Cosmetic so far, but it is the
  first sign that the category byte does have consequences downstream, and a new league in
  its own category (or the right cup wiring) is the next thing to look at.

## Six leagues and 120 clubs, from one command

`mkworld.py` does the arithmetic that doing this by hand gets wrong: it reads the shipped
tables once, hands out club ids above the highest in use, takes competition ids from the
free list inside the range Football Life used for its own additions and regulation ids from
the free list below 600, and writes `Team.bin` beside the three competition tables so one
livecpk root carries the whole set.

    python tools/mkworld.py --base <pesdb> --out <root> --leagues 6 --clubs 20

    base: 743 clubs, 91 competitions, 214 regulations, 1317 entries
      FL League 01     competition 130  regulation 11   clubs 71578-71597
      ...
      FL League 06     competition 135  regulation 33   clubs 71678-71697
    6 leagues, 120 clubs added; 863 clubs in all

and the game, restarted on it:

    block ...  teams 863 (cap 1600)  regulations 220  coaches 884
    highest club id 71697 (FL 0120)
      record 10, id 11, FL League 01 -- 20 clubs ... FL 0001 .. FL 0020
      ... six of them ...

All six are in Kick Off > League > New, each with its twenty clubs in the info panel
(`docs/img/kickoff-six-new-leagues.png`).  The game created 121 managers for them without
being asked, which is where the coach count of 884 comes from.

The list order is the tell: FL League 01, 02, 03, 04, **Premier League**, FL League 05, 06.
Not alphabetical, not by competition id -- by regulation id, which is 11, 12, 13, 14, 17,
32, 33.  So the league menu is walking the regulation table in id order and taking every
league it finds, which is exactly why a new competition appears here and never in the
curated Competition Structure list.

Two limits of the shape as it stands, both worth knowing before scaling to fifty:

- the competition id is one byte in all three tables, so 255 is the ceiling and the shipped
  data leaves 50 free below 141 -- enough for thirty to fifty leagues, but not with room to
  spare, and ids above 141 are untested;
- a regulation's team count is six bits, so 63 clubs is the most a single phase can hold.

## Forty leagues work; the next wall is the coach cap, not the team cap

Forty leagues of twenty clubs -- 800 new clubs, 1543 in all -- kills the game about
eighteen seconds in, before the menu appears.  That looked like the raised team cap failing
at scale.  It is not:

    40 x 20 clubs = 1543 clubs, coaches would be 1574   -> exited after about 17 seconds
    40 x 14 clubs = 1303 clubs, coaches would be 1334   -> exited after about 17 seconds
    40 x 13 clubs = 1263 clubs, coaches would be 1294   -> teams 1263, coaches 1284, fine

The team cap is 1600 and 1303 is nowhere near it.  The coach cap is **1300**, and the game
creates a manager for every club that has none, so the real ceiling on clubs is

    1300 - 774 already in use = 526 new clubs, whatever the team cap says.

Forty leagues themselves are no trouble at all.  With thirteen clubs each the block loads

    teams 1263 (cap 1600)  regulations 254  coaches 1284
    highest club id 72097 (FL 0520)
    record 138, id 139, FL League 40 -- 10 clubs

and Kick Off > League > New scrolls through FL League 01 to FL League 39 and on into the
shipped leagues.  Competition ids ran to 174, well past the 141 Football Life stops at, so
ids above the shipped range are fine.

So the road to eight hundred clubs runs through the coach array, and it is the same job
that was done for teams: `patches/attrib.json` already carries 17 attributed cap sites for
coaches, but the array has only 620 records of room above it before the fixtures begin, so
it has to be relocated into the grown block rather than merely uncapped -- and 22 of its
sites are still unattributed, which `patchset.py` will refuse to emit until they are
resolved.

## Eight hundred new clubs: the coach array, relocated and uncapped

The team array was relocated into the grown edit block once already, and the coach array
needed exactly the same treatment -- not merely a raised cap, because it has only 620
records of room above it before the fixtures begin.

What stood in the way was attribution.  `patchset.py` refuses to emit a set while any site
touching a relocated array is unattributed, and 22 coach sites were still `review-arg` or
`review-unknown`.  Disassembling all 22 settled them:

- Nine sites in the edit-data functions read the coach count at `[r8 + 0xd0bcf0]`, scale it
  by `imul r10, rax, 0x258`, and take `lea rcx, [r8 + 0xc4ca0c]` -- the array base, plain as
  it gets.  Those are edits.
- The two mode-copy constructors, 0x141401060 and 0x1414016b0, displace the coach array the
  same way they displace the team array: 0xc7dd00, 0xc81c48, 0xcaac90, 0xcac26c, 0xcad848,
  0xcaee24, 0xcaf24c.
- Three are junk.  0x140c7628a is the index bytes of the jump table belonging to
  0x140c74280.  0x140c987ff is `movzx edx, byte ptr [rcx + r13 + 0xc98eb0]` where r13 is the
  image base loaded by `lea r13, [rip - 0xc987f6]`, so the constant is an image offset that
  merely resembles a coach displacement.  0x141a112c9 is data the disassembler read as code.

With those verdicts in, `patchset.py` was generalized to relocate and uncap any array
rather than teams alone, and the new `teams-coaches` set is what it emits:

    block 0x1877068 -> 0x1c84268   (+4248064)
    teams    -> block + 0x1877070
    coaches  -> block + 0x1b07470
    105 team cap sites 750 -> 1600  (6 held inside the mode copy)
     16 coach cap sites 1300 -> 2600 (1 held)
    289 patches

And the goal, at last, holds in the running game:

    python tools/mkworld.py --base <pesdb> --out ...\_FL26World40 --leagues 40 --clubs 20
    python tools/gamerun.py start --set teams-coaches
    python tools/blockstat.py
    -> block 0x...  players 27927  teams 1543  coaches 1564  regulations 254
       highest club id 72377 (FL 0800)
       record 138, id 139, FL League 40 -- 20 clubs

**Forty new leagues, eight hundred new placeholder clubs, 1543 clubs and 1564 coaches, in
the menus.**  Kick Off > League > New lists FL League 01, 02, 03 and on.

## The menus hold 1543 clubs; starting a season does not

Loading is not playing.  At 1543 clubs the menus are healthy but walking into a league
season kills the process outright -- the window goes, `gamerun.py status` reports
`FL_2026.exe running: False`.  At 1263 clubs the same walk goes all the way to General
Settings and a Select Team screen with a full squad list.

The suspect is the mode copy.  `teams-coaches` grows and relocates the *edit* block's
arrays; the second copy of the same data that the game builds on mode entry -- ctor at
0x141401060, fill at 0x1414016b0, size 0x15b6d94 -- it leaves alone, which is why six team
cap sites and one coach cap site inside that code are deliberately held.  That copy's team
array is still sized for 750 and its coach array for 1300, so mode entry at 1543 clubs is
writing past both.

That makes the mode copy the next piece of work, and it is the piece `teams-1600` was
already trying to do when it proved unsafe.  Until then the honest statement of where this
stands is: **the menus and the edit data hold 800 new clubs; a season does not yet.**

## Where a season stops: 1303 clubs, and the exact number is 1303

Bisection on the club count, each run a fresh `mkworld.py` build, a deleted edit save and a
walk from the title screen to Kick Off > League > New > FL League 01 > Select Team:

    clubs  coaches   loads   season starts
    1263    1284      yes       yes
    1303    1324      yes       yes
    1304    1325      yes       NO   (process gone)
    1308    1329      yes       NO
    1313    1334      yes       NO
    1323    1344      yes       NO
    1343    1364      yes       NO
    1383    1404      yes       NO
    1423    1444      yes       NO
    1543    1564      yes       NO

Every one of those loads into the menus and reports its clubs through `blockstat.py`.  The
line is not fuzzy and it is not a timing artefact: **1303 clubs starts a season, 1304 does
not.**  The number is independent of how the clubs are distributed -- 40 leagues of 14, 29
of 20, 19 of 30, 113 of 5 and 11 of 51 all agree -- so it is a count of clubs, not of
leagues, regulations or entries.

What it is *not*: the mode copy's own region sizes.  Its team region is
0x133a30 - 0x50 = 0x1339e0 bytes, which at stride 0x690 is 750 records, and its coach region
is 0x1f2110 - 0x133a30 = 0xbe6e0, which at stride 0x258 is 1300.  A copy laid out that way
would have died at 751 clubs, not at 1304, so the crash is something else that is sized by
club count and has room for exactly 1303.  A raw scan of the executable for the dwords 1303,
1304, 1324 and 1325 returns only noise; finding the site needs the disassembly-driven cap
scan, not a byte search.

So the practical result today is **560 new placeholder clubs in 40 new leagues, playable**,
against 526 before the coach cap was raised, and 800 loadable but not yet playable.

## The new clubs have no players, so every match is a forfeit

Starting a season in FL League 01 and forwarding time gives:

    You have lost the match through default as you do not have the minimum number of
    players needed in order to field a side.

`blockstat.py` says why: `players 27927` with or without the new clubs.  `mkworld.py` copies
a team record, and the game invents a *manager* for every club that lacks one, but nothing
invents players, and nothing assigns them to the new squads.  The competition machinery is
therefore proven end to end -- fixtures, calendar, standings, a season that advances -- with
empty teams walking through it.

That makes placeholder players and squad registration the next piece of work, and it is a
data job rather than a patch job: the player array is already capped at 65000 against 27927
in use, so there is room for eighteen players per new club many times over.  What is missing
is the table that ties a player to a club, and the tool that writes it.

## Two tables away from a playable match: Player.bin and PlayerAssignment.bin

The season that forfeited every match needed two things the tools were not writing, and the
executable's own schema names them (`docs/pesdb-schema.txt`, ids 15 and 16).

`Player.bin`, 312 bytes a record, 27927 shipped:

    +0x08  player id, four bytes
    +0x44  four name slots of 0x3d bytes: the full name, the name on the shirt, the name
           on screen and the printed name

`PlayerAssignment.bin`, 16 bytes a record, 21303 shipped -- this is the table that ties a
player to a club:

    +0x00  a unique entry id
    +0x04  player id, matching Player.bin +0x08
    +0x08  club id, matching Team.bin +0x08
    +0x0c  packed: squad order in bits 10 and up, shirt number in bits 0-9

All 21303 assignments carry a club id that exists in `Team.bin`, and every player id in them
exists in `Player.bin`, which is what proves the two key fields rather than assuming them.
Shipped squads run 19 to 30 players, 26 being much the commonest.

`tools/mkplayers.py` writes both.  It does not invent ability values: it clones a shipped
squad whole and renames it, because a squad of twenty-three copies of one outfield player
has no goalkeeper and cannot take the field, while a cloned squad keeps a legal spread of
positions, a keeper, a captain and its shirt numbers.

**The result is a match.**  Kick Off > League > New > FL League 01, Forward Time, To Next
Match: FL 0001 v FL 0006 names two full elevens of FL P000xx, a goalkeeper and a captain in
each, walks them out of the tunnel and kicks off.  Screenshots in
`docs/img/kickoff-placeholder-squads.png` and `docs/img/match-fl-0001-v-fl-0006.png`.

## The player array is the one that cannot be moved

Only ninety of the 560 new clubs can have squads today, and the reason is in
`patches/layout.json`:

    players: base 0x0, stride 0x17c, cap 30001, relocatable false

It begins at offset 0 of the edit block.  Every access to it therefore carries no
displacement to rewrite -- there is nothing to find and nothing to patch -- so unlike the
team and coach arrays it cannot be relocated into fresh space.  It can only grow in place,
which shifts every other array above it and means rewriting all of their displacements at
once rather than one array at a time.

The arithmetic that follows is simple and unforgiving:

    cap 30001 - 27927 shipped = 2074 spare players = 90 squads of 23

So `mkplayers.py` fills clubs in order until the budget runs out and says so, rather than
writing a file the game will refuse.  Ninety squads is enough for six leagues of fifteen,
and at eleven players a club it would be 188 clubs -- still short of eight hundred.

Growing the player array in place is therefore the piece of work that stands between this
and a fully playable world, and it is a bigger job than the two that came before it: not
"find the cap sites for one array" but "move every array above players at once".

## Raising the player cap works, and a season still will not use it

The player array cannot be relocated, but it does not have to be.  Once the team array has
been moved out of the way its old region is free, and the player array can simply grow into
it -- in place, with no displacement to rewrite anywhere, because it starts at offset 0.
The only limit is what sits above the teams, and that is the regulation array at 0xc12e9c:

    0xc12e9c / 0x17c = 33314 records, with 36 bytes to spare

So `layout.json` now carries 33314 as the player cap rather than the aspirational 65000,
and the new `teams-coaches-players` set (389 patches) raises 100 of the 101 attributed
player cap sites along with the team and coach work.  It loads:

    players 33309  teams 1303  coaches 1324  regulations 254

That is 3308 players past the cap the game shipped with, and the menus are happy: Kick Off >
League > New > FL League 01 > Select Team shows FL 0001 with a full twenty-three man squad,
positions and all, GK through LWF, at four and a half stars.

And then confirming that team kills the process.  Measured:

    29997 players, 1303 clubs   season starts, match kicks off
    31377 players, 1303 clubs   loads, lists, dies at team confirm
    33309 players, 1303 clubs   loads, lists, dies at team confirm

The ceiling sits just about exactly at the cap the game shipped with, 30001, which is the
strongest hint available about where it lives.  Holding the one player cap site that falls
inside the copy code (0x140af3702, `cmp ebx, 0x7531`) does not change it, so it is not that
check: something in the mode copy keeps players in a region sized for 30001 and a season
overruns it.

Two ceilings now sit at the same place in the game -- clubs past 1303 and players past
about 30001, both fine in the menus and both fatal on mode entry -- and that is enough to
name the mode copy as the single remaining structural job.  Until it is relaid out, the
raised player cap buys room the menus can use and a season cannot, so the playable recipe
stays at the shipped cap: 2074 spare players, ninety squads of twenty-three.

A footnote worth keeping: once the player array is allowed past 30001 it runs straight over
the *original* team base, so `addteams.team_base`, which probed the original base first and
took whatever looked like a record, started reading player records and calling them clubs --
`highest club id 262143` with a name of pure garbage.  It now probes the relocated base
first, which only holds anything when a set that moves the teams is installed.

## What 1303 is counting has never actually been asked

The season ceiling has been reproduced five times over -- 40x14, 29x20, 19x30, 113x5 and
11x51 all start a season at 1303 clubs and all lose the process at 1304 -- and the
agreement across those shapes is what made it look like a settled fact about the number of
clubs. It is not. Every one of those runs was built the same way: `mkworld.py` hands out
club ids from just above the highest shipped one, so in all five the id of the last club
was 71577 + (clubs - 743), and the game invents a manager for every club that has none, so
the coach count was clubs + 21 in all five as well. Four quantities crossed their boundary
together, every time:

    clubs                1303 -> 1304
    highest club id     72137 -> 72138
    coaches              1324 -> 1325
    competition entries   1877 -> 1878

What the five distributions did vary is the number of leagues -- 11 against 113 -- and the
number of clubs in each, from 5 to 51. So the ceiling is not the regulation count and not
the size of any one league, which is worth knowing and is all those runs established.

This matters because a scan of the executable finds no literal 1303 or 1304 anywhere, and
`capmap.py 0x517 0x518 0x52c 0x52d 0x530` turns up only scattered `mov`, `add` and `sub`
sites, none with the shape of a bounds check. A ceiling with no constant behind it is a
derived one -- a buffer divided by a record size, or a table indexed by something -- and
which quantity it derives from decides where to look. A limit on the club *id* would mean a
table indexed by id, and would be the cheapest of the four to work around: the ids could
simply be packed into the gaps the shipped data leaves. A limit on the coach count would
mean the array that was raised last is still short somewhere else.

`mkworld.py --id-from` exists to break the first of those ties: the same 1303 clubs
carrying ids from somewhere else entirely. The extra-club build in `_FL26Ceiling` breaks the
last: 1304 clubs where the extra one belongs to no competition, so the entry count stays at
1877 while the club count crosses. Both are built and neither is answered, because both are
read off the screen and the display is off.

## The regulation array is now fully attributed

`attrib.py` left 306 references to the regulation array undecided, and an undecided site is
never patched, so the array could not be moved -- which is what the player array needs,
since the only room it can grow into is the space below whatever sits above it.

All 306 are settled, and on one argument rather than 306. The argument is about the
displacement, not the function. Two of them carry a displacement that is *exactly*
0xc12e9c, the array's base; three more carry the base plus a whole number of 0x314-byte
records plus a field offset. An exact landing is a far stronger claim than a range hit, and
the one thing that could still undo it is the pre-biased form the copy code emits, where a
displacement of `array base - copy field offset` reaches an array it does not look like it
reaches. That cannot be what these are: no array base minus any of the 77 measured mode-copy
field offsets equals any of the three displacements.

Then 301 of the 306 corroborate themselves. The function holding them also reads the
regulation count at 0xd0bcf4, which is the other half of the idiom -- walk 0 to count, scale
by 0x314, compare the u16 id at +0x00 -- and that is why 290 of the 306 are `cmp` and why
they are scattered across 206 functions: it is one inlined helper, not 206 decisions. The
five that do not read the count were read by hand, and the clearest of them says the whole
thing out loud at 0x14126f080:

    cmp  eax, 0x12c            ; 300, the shipped regulation cap
    jb   0x14126f08c
    mov  rax, rcx              ; out of range -> record 0
    jmp  0x14126f096
    imul rax, rax, 0x314       ; in range -> scale by the stride
    add  rax, rcx              ; rcx = [owner + 0x48], the edit block
    lea  r15, [rax + 0xc12e9c]

The verdicts are in `patches/attrib-manual.json`, which is the only channel a reviewed site
has into a patch set.

This does not by itself buy more players. The player array's *season* ceiling is about
30001 whatever the block-side cap is, so relocating regulations and raising the cap past
33314 adds room the menus will use and a season still will not. It removes the obstacle;
the ceiling above it is a different problem.

## The player ceiling has never been bisected either

The player ceiling is quoted as "about 30001, the cap the game shipped with", and the
roundness of that is doing more work than the evidence does. What was actually measured is
29997 starting a season and 31377 failing. The boundary is somewhere in the 1380 values
between, and the shipped cap is only the most obvious candidate in that range. Club counts
were bisected to a single value and players never were.

## The mode copy is not what a League season trips over

Everything about the two ceilings pointed at the mode copy for as long as nothing had
looked at it while a season was being created. `modeprobe.py` has now looked, on the League
season screen, with 1304 clubs loaded:

    mode byte 0   copy 0x0

The copy is not built there. Whatever a League season does with the club list, it does not
do it through the second copy of the edit data, so the copy cannot be what the season trips
over -- and the several places that named it as the last obstacle were wrong to.

The measured field map agrees from the other direction. The copy's regulation region is
exactly 300 records and its fixture region exactly 2000, both the shipped caps, so those
would overflow long before 1303 clubs mattered; and there is no player region in the copy at
all, so it cannot be what limits players either. The team region runs from +0x50 to the
coach region at +0x133a30, which is 0x1339e0 bytes, or 750 records of 0x690 -- the shipped
team cap exactly. If the copy were built for a League season, 1303 clubs would have
destroyed it at 751, not at 1304.

## The 1303-club ceiling was not a club ceiling

It is worth saying plainly first: **1443 clubs start a season.** The number that has stood in
this repository as a hard limit for weeks was an artefact of how the test worlds were built.

The crash that ends a season creation is at **0x1413236e4**, and it is the same instruction
every time:

    sub ecx, dword ptr [r8 + rax*4]        ; rax = 0xffffffff, r8 = 0x1428e52e0

`r8` is a 28-entry table in `.rdata` holding 3, 2, 2, 2, 1, 1, 1, 0, 0, 0, 0, -1, -1, -1,
-2, -2, -2, -3 ... -- a seeding or form modifier indexed by a club's finishing position.
`rax` is that position, and it arrives as -1. Nothing checks it, so the read lands at
0x1428e52e0 + 0xffffffff*4 = 0x5428e52dc, which is not mapped, and the process dies.

The -1 comes from a lookup a few instructions earlier:

    mov  r13d, dword ptr [r15 + 0x3c0]     ; how many clubs this competition has
    ...
    cmp  edi, 0x30                         ; the table holds 48 entries
    jb   0x14132368c
    mov  r14, r15                          ; past 48: fall back on entry 0
    ...
    lea  r14, [r15 + rcx*4]                ; entry = r15 + i*20
    mov  ecx, dword ptr [rax]              ; the entry's packed club id
    and  eax, 0x3fff                       ; low 14 bits
    cmp  eax, dword ptr [rbp - 0x21]
    xor  ecx, ebx                          ; high 18 bits
    test ecx, 0xffffc000
    je   0x1413236c3
    ...
    mov  eax, dword ptr [r14 + 4]          ; found: take its position

So a competition carries up to 48 (club, position) pairs, the club is found, and its
position is the uninitialised -1. In every capture the club being looked up is the same one
-- `rbx` is 0x45e68000, and 0x45e68000 >> 14 is 71578, which is FL 0001, the club the walk
selects -- and `r13` is always the size of the league that club is in: 17, 16, 15, 14 across
the four shapes that crashed.

### What actually sets the ceiling

Runs, all driven through the identical menu walk with `crashcatch.py` attached:

    leagues x size   clubs   in competitions   result
    40 x 13           1263        520          starts
    40 x 14           1303        560          starts
    40 x 14 +1 last   1304        561          starts
    40 x 14 +120 orphans 1423     560          starts
    57 x 10           1313        570          starts
    42 x 14           1331        588          starts
    42 x 14 +1 last   1332        589          starts
    42 x 14 +2 last   1333        590          CRASH
    59 x 10           1333        590          CRASH
    54 x 11           1337        594          CRASH
    60 x 10           1343        600          CRASH
    43 x 14           1345        602          CRASH
    44 x 14           1359        616          CRASH
    48 x 14           1415        672          CRASH
    49 x 14           1429        686          CRASH
    50 x 14           1443        700          CRASH
    57 x 14           1541        798          CRASH

Three things fall out of that table.

**The club count is not the limit.** 1423 clubs start a season and 1333 do not. The
difference is that in the 1423-club world 120 of them are *orphans* -- built by
`mkworld.py --orphans`, belonging to no competition at all. They exist, they are in the
block, the menus list them, and a season does not care.

**The league count is not the limit either.** 57 leagues start a season quite happily at
10 clubs each; 42 leagues do not at 14 and a bit.

**What is left is the clubs that are in a competition**, and the boundary is exact. Holding
the league count at 42 and moving only the last league's size, 589 starts a season and 590
does not. Adding the 1317 entries the game ships with, that is **1906 CompetitionEntry
records working and 1907 failing**.

### How the old number arose

Every world that established "1303 clubs" was uniform -- N leagues of M clubs, no orphans --
so the club count and the in-competition count were the same number plus a constant, and
they crossed their boundaries together. 40 x 14 gives 1303 clubs and 560 in competitions;
the 1304 that failed was 11 x 51, which is 561 in competitions *and* a 51-club league. Two
quantities moved, only one of them mattered, and the one that got written down was the
wrong one.

### What is still open

One run does not fit the entry rule: **33 x 17** has only 561 clubs in competitions, well
under 589, and it crashes at the same instruction with `r13` = 17. Its distinguishing
feature is that the league the season starts in has 17 clubs rather than 14, which suggests
a second and independent rule about the size of the league you actually play in. The run
built to confirm that -- 30 x 17, only 510 in competitions -- drifted off the menu path and
died at an unrelated address in a different module, so it settles nothing. That rule is
plausible and unproven.

## Reading the menus with the display off

None of the above could be measured by looking at the screen, because there was none. With
the monitor off the game renders a blank window; a restart does not fix it and the window is
full size, so it is the renderer, not the geometry.

Key presses still arrive, though, and the game's own memory shows it: pressing `enter` moves
about a thousand dwords of the writable `.data` section where sitting idle moves ninety.
`blindwalk.py` turns that into an instrument -- send one key, measure the churn it caused
against an idle baseline this run measures for itself, and print whether the press did
nothing, moved a cursor, or changed a screen. A walk that drifts off its path shows a
different churn signature immediately, which is how the 20 x 17 and 30 x 17 runs were
recognised as worthless rather than being written down as results.

## The boundary was the match table, and a new league had never had a fixture date

Two facts, found by watching the season being built rather than by watching it die, take
the 589/590 "ceiling" apart completely. Neither is about clubs.

### A new league gets no dates

The first match the placeholder clubs ever played was not a league match. In the running
42 x 14 world, FL 0001's match on day 254 is record 12961 of the match table, and its key
is 23, not 11: it is a tie in the English cup, which drew the new clubs in because their
competition carries England's category byte. That is what the "FA Cup - Round 1" branding
was saying all along. League 01's own 91 matches sit at records 0-90 with the date word at
+0x08 left at 0xffff. They had never been put on a day.

The reason is in the exe. Season creation walks every regulation (loop at 0x141315800,
bounded by the regulation count at block+0xd0bcf4) and, for each, `0x141350b40(key)` runs
over the regulation's rounds and matches and puts each match on a day -- but only after
`0x14157f810(key, &vec)` has filled a vector of 12-byte entries (day, round, leg) that
say which day each round belongs on. That function is a switch on the regulation id:

    0x14157f829   cmp  edi, 0x403          ; ids above the first table
    0x14157f844   cmp  r8d, 0xae           ; ids 1..175 -> first jump table
    0x14157f85b   movzx eax, byte [0x1415802e8 + id - 1]    ; case index
    0x14157f863   mov  ecx, dword [0x1415801ec + eax*4]     ; case code
    0x14157f86d   jmp  rcx

Sixty-three cases. Case 5, which ids 17-22, 50, 99, 116 and 118 share (the ten big
leagues), jumps to 0x141582550 and copies a 38-round league calendar out of `.rdata` at
0x14298ed80, then adjusts it per regulation. Case 62 is `ret` with the vector empty, and
that is where **every one of the 39 free ids in 1..175** goes -- 11, 12, 13, 14, 32, 33, 49,
60-66, 69-73, 75, and so on, exactly the ids `mkworld.py` hands out. A second table covers
ids 0x405-0x468 (84 of 100 empty), and everything else is empty too. `datecases.py`
decodes both tables from the exe and marks the free ids.

So a new league is created, gets its fixture rounds and its 91 match records, and is then
never scheduled, because the scheduler's date templates are per-id and compiled in.

### The match table is full, and the game drops what does not fit

The match table is 13000 records of 0x254 bytes at block+0xe9ff08 (the 58 `cmp 0x32c8`
sites). A record's own index sits at +0x00 and reads 0xffff while free. New matches are
made by an allocator (0x1413f5400.., it writes the key at 0x1413f56c3) that asks
`0x1414bc710` for a free record:

    0x1414bc729   cmp  word [r8 + r9 + 0xe9ff08], cx     ; cx = 0xffff
    0x1414bc736   cmp  eax, 0x32c8
    0x1414bc73b   jb   ...
    0x1414bc73d   xor  eax, eax                          ; none: return 0
    ...
    0x1413f56b1   je   0x1413f588c                       ; allocator: give up

Nothing is reported. In the 42 x 14 world the table holds 13000 records with none free,
the last 42 of them cup ties that pulled the new clubs in, and a breakpoint on the
give-up path counts **287** matches dropped during season creation; in 42 x 14 + 2 it counts
**329**, and the first three dropped are ties involving FL 0010, FL 0007 and FL 0012. The
cup draw allocates in order and the table simply ran out two clubs earlier.

### Why that was a crash and not a quiet defect

A club that is drawn into no dated match has nothing to do all season. Season creation
sets today to day 181 (1 July; 0x14126976c) and then `0x1413069c0` advances the day in
steps computed by `0x1415120d0`, whose stop is "the user's club has a match in today's
list". The 42 x 14 world stopped at day 254, the Saturday of FL 0001's cup tie. The 590
world had no such tie, so the day ran on to **362, 29 December**, where the shipped
calendar holds a kind-0x20 event in both worlds; that event opens the season-objectives
screen (0x141300cb0 in the day-event dispatcher at 0x1413007d0), which calls
`0x1413235a0` for each user club, which reads the club's previous-season standing from
the 48-pair table and finds the unset -1 -- the `sub ecx, [r8 + rax*4]` at 0x1413236e4
that every crash in this repository has ended at.

None of 1303, 1906, 589 or 590 was ever a limit the code checks. 33 x 17 falls out too:
a 17-club league draws differently, the table filled at a different club.

### The fix, and what it showed

`teams-coaches-dates` is `teams-coaches` plus one byte: 0x1415802f2, the case byte for
id 11, 62 -> 5. With it:

- League 01 is scheduled: 26 rounds of 7 matches, 182 new entries in the daily lists,
  match 0 dated 2025-08-22, round 13 on 2026-03-01.
- Both worlds start a season and stop on **day 233, 22 August 2025**, FL 0001's first
  league match. 42 x 14 + 2, the world that defined the "ceiling", starts.
- The matches dropped by the full table are still dropped: 287 and 329.

The day itself is the next wall. A calendar day is 0x2c4 bytes at block+0x16038a8 (365
of them): a 0xffff-terminated list of u16 match ids from +0x00, a count at +0x230, and
18 event qwords at +0x234 (low u16 = kind, 0x3f = empty; kind 0x20 carries a date). The
scheduler `0x141350290` refuses a match when the list holds 0x118 = **280** ids, again
silently. The busiest Saturday already carries 167 shipped matches, and 42 leagues of 14
on the same template add 294 to it, so patching every free id to case 5 will overflow the
day, and 800 clubs certainly will. Both the match table (relocatable, 187 attributed sites,
28 of them caps) and the calendar have to grow before the world does.

Two smaller things fell out of the same runs. The season rebuilds the edit block from the
League-mode object with the shipped caps (750 teams, 184 regulations, ~21000 players): the
recount at 0x1414bc0a0 writes the four counts at 0x1414bc23a-0x1414bc24f, and the mode
object's constructor 0x140afd660 sizes 750 teams, 1300 coaches, 180 regulations, 1750
fixtures and 12360 matches. And regulation ids 14, 32 and 33, free in the shipped file, are
not free in the game: leagues built on them show Libertadores and Asian clubs in their
tables, so a world builder must skip them.

## The match table grows: 26000 records, nothing dropped

`teams-coaches-dates-matches` relocates the match table (block+0xe9ff08, 0x254 bytes a
record, 13000 of them) to the end of the grown block at +0x1c84230 and gives it 26000
records, and moves the one-byte-per-match flag array (block+0x18378a0) after it with the
same cap. In the 42 x 14 world with fourteen leagues dated:

- the give-up path 0x1413f588c is never hit (287 drops before),
- 13612 records are in use, past the old 13000,
- each of the fourteen new leagues has 182 dated matches, the season starts on day 233,
- the busiest calendar day holds 271 of the 280 ids a day can take.

Everything the world could not fit before now fits. What follows is how the sites were
found, because the match table is referenced very differently from the team table.

### Reading a match-table site

`attrib.py` names 187 sites for the table by value, but the table is walked by
`base + field + index` in a register far more often than by a displacement inside a
record, so a displacement like 0xe9ff10 is not "record 0 field 8" but "field 8 of whatever
record `rax` points at", and the site has to move with the base. The rule that sorted
the 146 sites `attrib.py` could not name is in `attrib-manual.json`:

- **edit** (40): a displacement that is the table base plus a field offset (+0x00 own
  index, +0x04 key, +0x08 date, +0x14 / +0x18 clubs, ...) with the record index in a
  register. Moved by the delta.
- **copy** (46): the same shape inside a function that copies the block to or from the
  League-mode object (0x140afd660 and the copy constructors 0x141401060, 0x1414016b0,
  0x1413fea10, 0x1413feda0, 0x141401c10 and their callees). Left alone, as with the teams:
  the mode copy keeps its own layout.
- **junk** (60): the value 0xe9ff08.. inside an unrelated immediate or a rip-relative
  target that only happens to fall in the range.

The 0x32c8 caps: 58 in the exe, 28 attributed as caps by the tool, one deliberately not
patched (0x14140115f in copy constructor A, which sizes the mode copy), and the other 29
folded in as `extra_cap_sites` in `layout.json` after reading each one. The free-record
finder 0x1414bc710, the id lookup 0x1414bc560 (its `mov esi, 0x32c8` bound and the three
displacements of its direct-index / binary-search / linear-scan paths) and the memset in
0x1414bb970 are among them.

### The table runs into the calendar

13000 x 0x254 = 0x763a20, and 0xe9ff08 + 0x763a20 = 0x1603928, but the calendar starts
at 0x16038a8: the shipped table's last record overlaps the first 0x80 bytes of calendar
day 0 (1 January) and nobody noticed, because day 0 has no matches. The id lookup's
binary search uses the calendar base as its end pointer (`lea rdi, [rcx + 0x16038a8]` at
0x1414bc5a8), so that one site, filed by value under the calendar, moves with the table
(`extra_sites` in `layout.json`). Every other 0x16038a8 site in a function that also
touches the table -- eleven of them, in the copy functions and the initialisers -- is the
calendar, the member right after the table, and stays.

### The match flags

The byte array at block+0x18378a0 is one flag per match, cleared by 0x1414bb970 through
0x1415a1720, read by 0x1414bb3c0 and written by 0x1414bb3f0, with a count at 0x183ab68
and a 0x41-word list at 0x183ab6c after it. Five sites (`attrib-manual.json`,
`matchflags`); it moves and grows with the table because the two are indexed by the same
match id.

### One more thing the run said

With the fourteen date bytes left out by mistake (the first build of the set had them
missing), the same world ran to day 254 with 13852 records in use and 0 drops: no crash,
the placeholder clubs simply had no league matches again. Which is to say the date bytes
and the table are independent fixes, and either alone is not enough.

## Spreading the leagues over the week

With fourteen new leagues on the big-league calendar (case 5), every one of them plays on
the same weekday as the ten shipped big leagues, and the calendar day holds 280 match ids
(0x141350290). Measured over the 365 days of the E42 season, by day-of-week (`day % 7`):

    weekday 2: max 271   (the shipped league day: ~173 shipped ids + 98 new)
    weekday 6: max 158   (the midweek day)
    weekdays 0, 1, 4, 5: max 51, 12, 43, 43

So the wall was not the calendar day, it was fourteen leagues on one weekday. Instead of a
stride change over 195 functions, the date-template switch got a stub (`datecave.py`): case
62 -- "no calendar", where every free regulation id lands -- and the `ja` for ids above 175
both go to 0x14252e690, in the zero padding at the end of the code section. The stub looks
the id up in a 256-byte table (0xff = no calendar, as before; 0..6 = case 5's calendar
shifted by that many days), calls case 5 for the vector, adds the shift to every entry's day
and wraps at 365. Rounds, gaps and legs are untouched; only the weekday moves.

`--date-offsets 2,6,5,1` deals the fourteen keys over four weekdays: busiest day 188 (was
271), every league 182 dated matches, round 0 on 23/24/27/28 August, season start day 235.
The case-5 template's largest day is 363, so shifts of up to 6 wrap into early January,
which is why the stub wraps rather than clamps.

## Rows past 750 were never constructed

The first match against a club past row 750 aborted: `0xc0000409`, fail-fast code 7, from
the game's own checked `vector[]` ("invalid vector<T> subscript", 0x1425a1fd8) in the
kit-clash resolver 0x1415296d0 -- the away side's kit vector was empty. The vector is built
by 0x14152b910 from the team record's kit list at +0x5d8 (ten 8-byte entries: low nibble
type, high nibble index, bit 0 of the next byte a flag), and for FL 0008 (row 750) that
list was all zero. Not only the list: everything from +0x2d0 to +0x600 of rows 750 and up
was zero at the main menu, before any season existed.

The team record has a constructor (0x140b15630), and it runs on exactly 750 rows, in four
places the cap pass never saw because they are `mov reg, 750` loop counters rather than
`cmp` bounds: the block's C++ constructor (`__ehvec_ctor(base, 0x690, 750, ...)` at
0x1414b87b7, destructor 0x1414ba607), the initialiser 0x1414bb970 (0x1414bba21) and the
reset 0x1414bbe60 (0x1414bbea3) that runs before every mode copy is written back. The loader
then fills ids, names and the rest from Team.bin for all 1331 rows, so the rows *looked*
loaded -- but their defaults (the seven `0x91 ff..` empty kit slots, the 0xff fields) and
the kit entries were missing. Two more of the same shape: the user-club finder scanning 750
rows (0x1414bc12e) and a `cmova` clamp to 750 (0x1414f370a); the coach array has the same
eight (`extra_cap_sites` in `layout.json`). With them raised, rows 750..1330 carry the same
kit list as rows 743..749 at the main menu.

### The copy's loop bounds must not move

The same set had raised five sites it should not have. The League-mode copy (0x140afd660,
0x135bd10 bytes from 0x1413fea00) holds 750 teams at +0x50, **750** coaches at +0x133a30
(0x1a1800 - 0x133a30 = 750 x 0x258), 180 regulations, 1750 fixtures and 12360 matches, and
keeps that layout. Its write-back to the block (0x1413fea10) loops `cmp edi, 0x2ee` over
its own team array; raised to 1600, it copied coach memory into block rows 750..1599 as
teams. The coach loop's bound is the same 0x2ee (0x1413feacc; the tool filed it under
teams), and copy A's write-back has the pair 0x14140172f / 0x141401856, its fill
0x141401e07 (26000 records into a 13000-record array, over the copy's calendar and the
sub-objects after it -- the likely Master League crash). These are `hold_sites` in
`layout.json`, which `cap_patches` refuses to raise. The dummy-select sites next to them
(`cmp` then a forward `jb` to the dummy record) may move: they only decide whether a block
row past the old cap is real.

The fill direction (block -> copy, 0x1413feda0) loops over the block's *counts*, so with
1331 teams it writes 581 rows past the copy's team array. That is shipped behaviour (214
regulations into 180 slots), and harmless only because the coach, regulation, fixture and
match loops that follow rewrite everything it ran over.

## The first live match: the kit wall is gone, two walls remain

With the monitor on, the game was driven into an actual match (the user at the controls,
the tracer and memory reads on my side). Three things came out of it, and they are three
different problems that had been blurred together as "it crashes".

**The kit wall is gone.** The kit-clash resolver 0x1415296d0 -- the fail-fast that aborted
the moment an opponent sat past team row 750 -- was reached twice for a match involving FL
0009 (row 751) and did **not** abort (rcx/rdx were two live club handles, r8=0, no CRASH
line). The row-750 kit fix works in a real match, not only at the main menu.

**A data crash in the stadium scene (0x141afae35).** Playing FL 0009 away, the match
reached the stadium intro and died: `mov eax, [r8 + 0x200]` with r8 = 0. The function walks
a list of player-view objects (`[rsi+0x130]`, count at +0x10, array at +0x18) and reads
each one's sub-object at +0x50; for one player that sub-object is null. The sub-object is
the one checked against 0x17 (23, the squad size) at 0x141afae55, so it is the player's
model/appearance built by the fill calls 0x14187b730 / b790 / b8c0 just above the loop.
Everything the placeholder club needs was verified present and correct: the team record's
squad slots at +0x14c (24 filled entries, identical shape to a row < 750), and all 23 of
the club's players in the player array (id at record+0x30, the FL players occupy 2104
records around index 27900+). So the null is not missing data; it is a player-view object
that the scene assembly did not build. The assembly is upstream of 0x141afae35 -- that
function receives the list ready-made -- and its call tree (0x141afac00 and the fill
functions' five-deep callees) references no team array, no 0x16705a8 side table and no 0x2ee
bound, so the row-750 dependence, if that is what it is, is indirect and could not be
pinned from the disassembly alone. This is the real remaining modding wall and it is not
yet solved.

**A render crash on the loading screen (0x14cf444ae).** A second, unrelated crash:
`sider.dll +0x1b0fd` and `d3d11.dll` sit directly in the faulting thread's stack, and the
fault is in the JITted render region (0x14cf..., 0x15ac...). It fires during the heavy
asset load of a match, with a register signature (rax=rcx pattern, r15=0x15ace83cb,
r14=0x2e000000) identical across every occurrence. This is the crash that kept turning up
as an unrelated "control" failure on drifted blind walks; seeing it now with Sider and D3D11
in the stack identifies it as a graphics-hook / driver-stability crash, not a data one. It
cannot be fixed by patching the tables, and it will interfere with verifying any match
render regardless of the data. A low-row match (FL 0001 v FL 0006, both players visible in
the team select -- so low rows assemble fine) got past team selection and died here on the
loading screen.

So of the three, one is fixed (kits), one is a data bug we can chase (the stadium
player-view null, row-750-adjacent), and one is an environmental Sider/D3D crash outside the
data. The practical consequence: the data layer for row-750 clubs is sound as far as every
table goes; what is unproven is 3D match rendering, and that is entangled with a graphics
crash that has nothing to do with the caps.

## The stadium crash, traced statically to the player-model builder

Static disassembly (no game running) followed the null player-view sub-object from the crash
site down to the exact function and condition that leaves it null.

The crash loop is in function 0x141af8080 at 0x141afae20..0x141afae7b: it walks the scene's
player-view list (`[rsi+0x130]`, count +0x10, pointer array +0x18) and for **every** element
reads `[element+0x50]` then `[[element+0x50]+0x200]`. The +0x50 sub-object is the player's
model; when it is null (r8=0) the read at 0x141afae35 faults. So every element's +0x50 must
be built before this loop runs.

Just above the loop, three fill calls build them: 0x14187b730, **0x14187b790**, 0x14187b8c0.
b790 is the real builder. It iterates the same player-view list (array [rbx+0x18], count
[rbx+0x10]) and for each element calls **0x141876560** to build that element's +0x50. If that
call returns 0 (al=0) b790 **bails immediately to 0x14187b8b8** without finishing -- so every
element after the failing one keeps +0x50 = null, and the crash loop then dies on the first
un-built one. One player's model failing to build takes down the whole scene.

0x141876560 returns 0 in exactly one way: when `[element+0x50]==0` and `[element+0x90]==0`
and its worker **0x1418765d0** returns 0. 0x1418765d0 counts (in ebp) how many entries in the
element's *parts* list (`[element+0x70]`, count `[element+0x68]`) pass the validator
**0x141883cc0**; `test ebp,ebp; je` at 0x141876632 means **if zero parts are valid it returns
0**. The validator is trivial: a part is valid iff `[part+0x20]!=0` (else a vtable fallback).
So the model fails to build precisely when the player-view element has **no part carrying
data** at +0x20.

What this rules in and out:
- **Not missing player data.** mkplayers.py builds each placeholder by cloning a real player's
  entire 312-byte record and overwriting only the id (+0x08) and the name slots (+0x44). Every
  appearance/attribute field is a real player's, so the placeholders are appearance-complete;
  the earlier +0x80/+0xbc "difference" was an optional field most real players also lack.
- **The open question is the parts list.** The parts (element+0x70) are assembled upstream
  during scene setup, from the match/team data -- that is where a row-750 (or per-team)
  linkage would break, leaving the parts present but data-less (+0x20 == 0) or the list empty
  (+0x68 == 0). Which of the two, and what feeds it, is the next thing to find.
- **Row-750 dependence is not yet proven.** FL 0009 (row 751) hit this stadium crash, but the
  one low-row placeholder match tried (FL 0001, row 743) died earlier on the unrelated
  Sider/D3D loading-screen crash, so it never reached the model build. It is still possible
  this affects placeholder clubs at any row; the live check must settle it.

The live check is now a single freeze, not a blind watch: hold at 0x14187b8b8 (the bail), read
the failing element `[rdi]`, and dump its +0x50 / +0x90 / +0x70 parts (each part's +0x20).
Empty parts vs data-less parts points straight at the upstream source. Harness written
(scratchpad/modelfreeze.py + modelinspect.py), ready for the next monitored session.

## The match-load crash: a custom-stadium graphics-resource failure (2026-09-11)

The intermittent crash on loading a match is **not** the player-model builder crash chased
above, and **not** caused by our capacity patches or placeholder data. It is a graphics
resource *create* that fails with E_INVALIDARG while the Sider `StadiumServer` stack loads a
custom stadium's AddOn textures.

- Chain: factory 0x141fea370 -> virtual create `[r10+0x28]` -> negative HRESULT (0x80070057)
  -> factory returns null -> an unchecked consumer dereferences it. Faulting sites seen:
  0x141fea5ba (in .trace) and 0x14cf444ae / 0x15454f19a (in the executable, VM-protected
  `.impdata` section -- packed code, not "outside the image").
- Reproduces with **zero** of our patches (the `none` set), PES21_Hook.dll + sider.dll in the
  stack -- a stock game bug (missing null check) reached through the user's stadium mods.
- Trigger, from sider.log: `StadiumServer.lua` loading **La Bonbonera** (st028) -- ~950 AddOn
  `.ftex` textures plus entrance/result demo scenes -- immediately precedes the crash. The
  type=8 resource is a texture; intermittency points at timing/resource pressure over that
  large custom-texture set, not one corrupt file.
- Defensive fix `nullguard` (trampoline at 0x14252e68c guarding fn 0x141fea5b0) removes the
  0x141fea5ba face but the failure resurfaces in the VM-protected code, so it is hardening,
  not a cure. The cure is on the resource side (trim/repair the custom stadium, or a
  stadium-server setting); our placeholder clubs use a generic stadium and should sidestep it.

### Confirmed: placeholder clubs bypass the custom-stadium crash (2026-09-11)

Verified on disk, without launching the game. The built world `_FL26Goal` carries 798 placeholder
clubs with IDs 71578..72375 (the highest real shipped ID is 71577). StadiumServer maps custom
stadiums by `team_id` from per-country `Mapping.txt`; across all 13 files (291 assignments) the
highest mapped `team_id` is 9943 and no assignment is ≥71578. So no placeholder club is in the
stadium map → they all get a generic stadium → none triggers the La Bombonera (~950 `.ftex`) path
that intermittently crashes graphics resource-create. The goal (placeholder leagues) is not blocked
by this crash; Boca/River crashed because they are real clubs with a custom stadium.

### SOLVED: live match with placeholder clubs (nullguard alongside caps) (2026-09-12)

The exhibition kickoff crash with placeholder clubs is **0x141fea5ba** — a stock null-deref: fn
0x141fea5b0 does `mov rdi,[rcx+0x18]` with no null-check when the graphics factory (0x141fea410)
returns null for an asset a placeholder club (id≥71578) does not have in the match scene. This is
the same bug the **nullguard** set fixes (the trampoline returns 0). The
`teams-coaches-dates-matches` set does NOT include nullguard, so the exhibition crashed regardless
of the chosen stadium.

Solution: load nullguard as a separate second module (`fl26nullguard.lua`) alongside `fl26caps.lua`.
The caps set occupies the same .trace code-cave (trampoline 0x14252e690–0x14252e7e6), so the
nullguard trampoline was relocated to **0x14252e800** (both rel32 recomputed; the module verifies
the bytes). Result: FL 0001 v FL 0006 through Local Match — pre-match → entrance → team photo →
formations → kickoff (scoreboard 001 0:0 006), no crash. `docs/img/match-fl-0001-v-fl-0006-live-exhibition.png`.

### The player cap raised to 33314 shows 234 squads in the menus, but only ~90 clubs are playable: the 30001 mode-copy ceiling hits exhibition too (2026-09-12)

New set `teams-coaches-players-dates-matches` (516 patches) = the dates-matches world plus the
block player cap 30001 -> 33314, and a new data root `_FL26E42x234` built with
`mkplayers.py --cap 33314` (33309 players, 234 squads of 23). In the menus this is a clear win:
clubs above the old 90 boundary now carry real squads -- FL 0099 shows FW 75 / MF 75 / DF 76,
4 stars and a full 11-man pre-match, where at cap 30001 it was the degenerate "39/39/39, 1 star".

But a match is still bounded by the **30001 mode-copy ceiling**, and it is not season-specific --
it hits exhibition (Local Match) at kickoff too:

- **FL 0099 v FL 0100** (both above 90, both with real squads): Kick Off -> ~10 s load -> crash,
  WER fault offset **0x84ed4c0** (VA 0x1484ed4c0, c0000005). A new offset, deep in a data region;
  not the graphics null-deref (0x1fea5ba, nullguard's), the d3d11 turf crash (0xcf444ae) or the
  squad-less crash (0x15148796d).
- **FL 0001 v FL 0006** (both low), *same 33309-player data*: kicks off cleanly -- tunnel,
  entrance, formation, scoreboard 001 0:0 006, 22 players on the pitch, no crash.

So the crash is not the total player count (identical for both matches) but the **DB index of the
participating clubs' players**. Placeholder players sit after the 27927 shipped players; FL 0001's
are at index ~27927 (< 30001) and FL 0099's at ~30181 (>= 30001). The mode copy the match builds
is 30001-capped regardless of the block cap, so any club whose squad players cross index 30001
overflows it. 30001 - 27927 = 2074 = 90 squads of 23 -> clubs FL 0001..0090 play, FL 0091+ crash.

This is exactly the ceiling flagged earlier ("relocating regulations and raising the cap past
33314 adds room the menus will use and a season still will not"), now shown to bound exhibition
match-load as well, and pinpointed at fault site **0x1484ed4c0**. Raising the block cap is
therefore menu-only until this mode-copy allocation is itself relocated/enlarged; that is the real
work for a playable 800-club world. The block-cap set and `_FL26E42x234` are kept on disk for the
next attempt; the playable config is `_FL26E42` + `teams-coaches-dates-matches` + nullguard.

### Correction: clubs above 90 DO play in exhibition at cap 33314; the 0x1484ed4c0 crash is intermittent (2026-09-12)

The same FL 0099 v FL 0100 match that crashed on its first attempt kicked off cleanly on the
second (scoreboard 099 0:0 100, placeholder players at DB index > 30001 on the pitch). The
"players at index >= 30001 overflow a 30001-sized mode copy" explanation in the previous
section is therefore withdrawn; the mode copy has no player region (see above), and the fault
site 0x1484ed4c0 is in the protector's `.impdata` blob alongside the other residual
graphics-null consumers (0x14cf444ae, 0x15454f19a). Treat it as an intermittent crash of that
family, not as a capacity ceiling.

Net: the block cap 30001 -> 33314 (`teams-coaches-players-dates-matches`) is a real, playable
gain for exhibition: 234 squads, and clubs 91..234 kick off. The ceiling still standing for the
800-club goal is season creation above ~30001 players (0x1413236e4, rax = -1 standings read),
recorded earlier and not yet re-tested with the combined set.

### Season creation works at 33309 players with the combined set; the season block is a filtered subset (2026-09-12)

With `teams-coaches-players-dates-matches` (block cap 33314, dates, matchflags) and the x234
root, FL 0099 (club 99, players at DB index > 30001) starts a League season and plays its first
match (CL play-off v SE Palmeiras, kickoff reached, scoreboard 099 0:0 PAL). The
"team confirm kills the process at 31377 / 33309 players" result recorded earlier with the
older `teams-coaches-players` set did not reproduce; whether the dates/matchflags patches fixed
it or the earlier crash was of the intermittent kind is not settled -- the older set was not
re-run today.

Measured on the season calendar screen: the mode block holds `players 23337  teams 1149
coaches 1149  regulations 184` against 33309 / 1331 / 1352 / 256 in the menus. So the season
copy filters: 743 shipped clubs + 29 of the 42 FL leagues (406 clubs), 13 leagues (182 clubs)
dropped, and only the players of the kept clubs. That is why 30001-sized structures in the mode
copy (the separately allocated player vector, 0xadf4c4 at 0x14140146d) are not hit here:
23337 < 30001. For the 800-club world the question becomes what the filter keeps -- if it keeps
every league in the season's competition scope, ~46 000 players would overflow that vector and
it (plus its 0x7531 checks) must be grown; if it keeps a bounded scope, the block cap alone
carries the season. Next step: identify the selection rule (which 13 FL leagues fall out and
why) and force a season copy above 30001 players to see where it breaks.

Status after today: cap 33314 = 234 playable squads in exhibition and in a season. The physical
block ceiling (regulations at 0xc12e9c) stays the limit for more; going past it means relocating
regulations + fixtures (attrib.json: fixtures 37 unresolved, players 100 review-imm, count 178).

## The regulations relocated, the player cap at 35985, and the season's packed player table (2026-09-12)

### Relocating the regulation array: cap ceiling 35991

With teams and coaches relocated the player array still ends at the regulation array
(0xc12e9c / 0x17c = 33314 players). The set `teams-coaches-regs-players-dates-matches`
moves the regulations too (to +0x1c84230), and then the first thing above the players is
the dummy-record triple at 0xd0b0ec, which is not relocated by design (the dummies and the
count fields are what identifies the block to the attribution walk). So the player cap can
go to 0xd0b0ec / 0x17c = **35991**; `patchset.py --player-cap N` picks the cap and refuses
one that reaches the dummies (or the regulation base, for a set that leaves it in place).

Two things the regulation relocation needed that the earlier arrays did not:

- **Derived pointers stay.** The regulation attribution has 169 sites whose displacement is
  not the array base plus a field: `cmp word ptr [rcx], ax` after `lea rcx, [rsi + base]`,
  or `[r8 - 0x314]` after `lea r8, [r13 + base + 0x314]`. The `lea` is its own attributed
  site and moves; the displacement relative to it must not. `array_patches` now skips a site
  whose operand is neither the attributed offset nor offset + field. Every site of the proven
  sets (teams, coaches, rec596) has operand == offset (+ field), so they are unaffected.
- **Reused regulation ids in the fixture-date switch.** The date stub (datecave.py) is reached
  through the case-byte table at 0x1415802e8 (one byte per regulation id 1..175); ids the
  shipped game already uses keep their shipped case -- 74 is case 25, 76..78 case 3 (Copa
  Libertadores and friends), 138..140 cases 44..46 -- so a new league on one of those ids got a
  cup calendar with no league fixtures, standings at -1 and the 0x1413236e4 crash on team
  confirm. datecave now rewrites the case byte of every reused id to the empty case, which is
  the stub (4 byte patches in the set).

At cap 35991 (data root `_FL26E42x350`, 35977 players, 350 squads) the menus load, and
League 08 / FL 0099 and League 22 / FL 0300 reach the season calendar
(`docs/img/season-fl-0300-v-fl-0301-calendar-cap35991.png`).

### A season does not carry 0x17c records: the packed table BH1

plan.md 3.3 assumed the mode copy carries a 30001-record vector of full player records
(0xadf4c4 = 30001 x 0x17c + 8). It does not, except as a fallback. The season's players live
in a global packed table, called BH1 here:

- `0x143700880` the table, `0x143700888` its count, `0x14370088c` an owned flag; allocated by
  0x1413fcc70(count) as 8 + count x **0x9c** bytes, freed by 0x1413fcd30, adopted from an
  external buffer by 0x1413fcde0(ptr, count).
- The packer 0x1412e4b50 fills it from the block: record i for i < min(count, 30001), the
  player dummy 0x184c3bc past that. The unpacker 0x1412e5eb0 goes the other way through a
  30001-record temporary vector (loop bound `cmp esi, 0x7531`) and writes into the block.
- The League-mode copy object A (constructor 0x141401060) keeps its own copy of the table at
  +0x11403b8, 30001 x 0x9c = 0x4769dc bytes, with the length at +0x11403a8 and a pointer at
  +0x11403b0; the object is 0x11403b8 + 0x4769dc = 0x15b6d94 bytes (constants at
  0x141400b6e/b7c/ba0). The compressor FL1 = 0x141b39b40(BH1, 0x4769dc) works on the byte
  length (mode byte 0x143700891: 2 compressing, 3 raw, 4 compressed), and the loader
  0x141400940 tests `cmp [rcx+0x11403a8], 0x4769dc` before decompressing (0x141b39a20) in
  0x8ed3 chunks of 0x80 bytes. Copy object B (0x140afd660) does the same with 30000 records
  at +0xee53d0 (object size 0x135bd10, 0x8ed2 chunks + 0x40, adopt count 0x7530 at
  0x140af23cf). Both constructors keep the 0x17c-record vector as a fallback for an empty BH1.

None of this is reachable from the attribution walk: the sites measure the table, not the
block. So a block with more than 30001 players got a season in which every later player was
the dummy, and whoever read past the table read whatever followed it -- the intermittent
kickoff crashes above club ~90 at cap 33314 fit that. `patchset.py` now grows all of it with
the block cap (`COPY_PLAYER_SITES`, 51 sites: BH1 allocations, packer, unpacker, adopt counts,
copy A's table length / object size / compressor length / memcpy chunk counts and its
fallback vector, the same for copy B, plus the block's own 30001 loops the walk never reached:
constructors, destructors, id lookups, two per-index side tables of 8 and 4 bytes per index,
and a 2400-player copy).

The memcpy tails are fixed code: the chunk loops copy 0x80 bytes per iteration and the
remainders (0x5c, 0x3c, 0x40 bytes) are hard-wired, so the byte length must keep them, which
means **cap = 17 (mod 32)**. The generator refuses anything else; 35985 is the largest such
cap under 35991, and 35977 players fit.

Still not grown, as residual risk: a menu-mode object at 0x1436f9dc0 (size 0x20248, constructor
0x140e98bc0) has a 30001-dword table at +0xd8 filled by `rep stosd` at 0x140c728c7 with
fields after it at +0x1d5d8; a separate 2 x 30000 qword id-list object (0x1414d5038) is
bounds-checked (`cmp bx, [rcx+0x1e910]`) and left alone.

### The walk dropped rbp-based sites: a divide by zero at team confirm

With the regulations relocated and the packed table grown, team confirm in League 08 exited
without an access violation. crashcatch (which now logs every exception and the exit code)
showed `0xc0000094` at 0x141545f62: `div r8`, r8 = the number of sub-regulations returned by
0x141541480, which walks the regulation array with the *unrelocated* base
(`imul rcx, rax, 0x314; lea rax, [rbp + 0xc12e9c]; add rax, rcx`) -- with the regulations
moved it reads player data, finds nothing, and divides by zero.

The site was never in patches/attrib.json. `attrib.py` treated `rbp` as a frame pointer and
dropped every rbp-based displacement unless it already knew rbp held the block. Many block
walkers do keep the block in rbp (`mov rbp, [rax + 0x48]` after the owner getter) and lose it
to the linear interpreter at an early `pop rbp`: the epilogue of one return path sits in the
middle of the function, and everything after it was attributed with rbp unknown. A scan of
the exe for the six base immediates found the uncovered sites: regulations at 0x14134609a,
0x1415105b1, 0x141516bad, 0x14151b44d, 0x14154153c, 0x141f076b3; coaches at 0x1414badc2; and
the three exception-unwind funclets of the block constructor (0x14249508d, 0x1424950c1,
0x1424950f5 -- only run when construction fails, left alone).

The fix in attrib.py: an unknown rbp is no longer dropped. A displacement of array size stays
a review site, and the bounded-accessor pass promotes it when rbp also forms a count or dummy
displacement in the same function -- something a frame pointer never does. That promoted all
six regulation sites (each function reads `[rbp + 0xd0bcf4]`, the regulation count). The coach
site is a lookup 0x1414bada0 the call index does not list (so no caller ever told the walk
what rcx is); it walks 0x258-byte records from 0xc4ca0c up to the coach cap 0x514, a layout
only the block has, and got a manual `edit` verdict. The change also surfaced 28 mode-copy
sites in 0x141401c10 and 0x140ebaab0 (verdict `copy`, the same sub-object offsets as the
constructor 0x141401060) and six junk decodes; all recorded in patches/attrib-manual.json.
The set went from 1222 to 1229 patches, and League 08 / FL 0104 now starts its season and
plays its first match (docs/test-log.md, 2026-09-12, cap 35985).

Why the earlier 35991 runs reached the calendar without these seven sites: the divide
happens only when 0x141541480 finds no sub-regulation at all, and with the old base pointing
into player records the count it computes depends on what those bytes happen to hold. Those
runs passed by luck, not by a different code path.

## 2026-09-13 -- the upper belt, and what stands between us and 800 clubs

### The belt

Above the player array the block holds a run that has to move as one piece if the players
are to grow past 35991: the dummy triple at 0xd0b0ec, the four counts at 0xd0bce8..f4, an
unnamed region at 0xd0bcf8, the fixture table at 0xd65f64 and a second unnamed region at
0xe63de4, ending at the 596-byte match table 0xe9ff08. `patches/layout.json` records it as
`block.upper_belt`, and `patchset.py` shifts every attributed reference to each member by one
delta. The layout offsets stay as the attribution fingerprint: the walk runs on the shipped
offsets and only the emitted displacements change. Above the belt the dead 596-byte table
leaves the players room up to the season calendar at 0x16038a8, i.e. 60745 records.

Attributing the belt needed four generalisations in `attrib.py`, all in the linear
interpreter:

- an epilogue snapshot restored at `ret`, because an early-return epilogue (`pop rsi`,
  `mov rbx,[rsp+0x30]`) killed the register the fixture idiom had just formed;
- `imul reg, reg, stride` followed by `add reg, block` (and the mirror) keeps the block;
- `cmov` between two registers carrying the same terms keeps the terms with the smaller
  constant;
- fingerprint promotion: count and dummy displacement sites are their own fingerprint, a
  region site inside a function that already touches the region is promoted, and an array
  without a dummy is promoted at its base. `pop` stopped counting as an effect.

With 22 manual verdicts on top (`patches/attrib-manual.json`, now 29 functions / 485 sites)
the belt attributes with zero review sites, and the old proven set still regenerates byte for
byte at 1229 patches.

### The player cap is no longer the wall

At cap 46353 the block loads 46327 players and 800 new clubs, a season starts on clubs whose
players sit around absolute index 36200, and the pre-match screen draws both line-ups. What
now fails is Kick Off, reproducibly, in the packed .impdata region (docs/test-log.md,
2026-09-13). That is the next thing to chase, and it is a different problem from the counts.

### The league list resolves to the wrong league at scale

Adding enough leagues makes the League-mode list disagree with itself: the highlighted row
and its League Info name one league, Confirm loads another, and the rows at the end of the FL
run load a competition with no teams. It is not the patch set -- the same set with the
42-league root resolves every row correctly -- and it is not a 256-regulation wall, since a
254-regulation root diverges too. The list also shows high-numbered FL leagues among the low
ones, which nothing mkworld writes accounts for: every league gets region 16 and both id
series rise with the league number. So the ordering the widget displays comes from somewhere
else, and the index Confirm uses indexes something else again. Until that is understood, the
league a run actually gets must be read off the calendar, not the list.

### 20-club leagues work

`mkworld --clubs 20` produces leagues the game is happy with: League Info lists all twenty,
the season builds a twenty-club calendar, and 40 such leagues reach 800 new clubs with 254
regulations instead of the 272 that 58 leagues of 14 need. That is the cheaper route to the
target, and it makes the 14-club question moot for this goal.

## 2026-09-13 -- 800 placeholder clubs play, and where the league list really stops

### The player cap is not the wall any more, and neither is 35991

A cap of 46609 (17 mod 32) with the upper belt relocated loads 46603 players over 1555
teams, and both sides of a league match draw from well above the old 35991 ceiling.  FL
League 26 of the 58x14 root fields clubs 351 and 362, whose players sit at absolute
35982-36254 -- squarely across the old wall -- and the match reaches live play at 0:00.
A second run on the 50x16 root kicked off FL 0593 v FL 0600 with players at 41548-41731.
So a placeholder club at any index the data holds can now play; the ceiling that stopped
last week was the cap and the belt, not an index the match code refuses.

### Twenty clubs to a league breaks the row-to-league mapping -- WITHDRAWN 2026-09-13

The section below is wrong and is kept only so the mistake is not repeated.  The 20-club
world resolves rows correctly; what fooled the measurement is that the league list
re-sorts itself between visits, so the row read off a screenshot was not the row the
Confirm acted on.  Screenshot immediately before the Confirm, and every size resolves.
See "League size is free" in the later entry.

With 20 clubs to a league the Kick Off league list loads a different league than the row
the cursor sits on: row "FL League 02" came back as FL League 01, row "FL League 08" as
FL League 05.  The League Info panel agrees with the row label every time, so the list and
the panel read the same index and only the Confirm resolves elsewhere.  Rebuild the same
world at 14 clubs to a league and the divergence is gone: row "FL League 06" loads FL
League 06, clubs FL 0071-0084, players P01611 upward.  16 clubs is also clean.  So the
trigger is the league size, not the league count (43 leagues resolve correctly) and not
the total club count (602 and 800 both resolve when the leagues are small enough).

### The list drops leagues past a point, and the point is not the regulation id

Two dead theories, both killed by measurement.  The 256-regulation count is not a
threshold (a 254-regulation root diverged the same way as 272).  Nor is the shipped
regulation-id band: moving all 40 leagues to ids 176-215 with `mkworld.py --reg-from 176`
did not fix the mapping, it only changed the symptom to a Select Team screen with no rows
at all -- and on the 58-league root, which spans ids 11 through 184, FL League 51 (id well
above the shipped maximum of 175) resolves and loads its clubs perfectly.

What does happen is that the Kick Off league list holds a bounded number of entries and
silently drops the rest.  The 50-league root shows FL League 01 through 38 and then the
shipped leagues; 39 through 50 are absent.  The 58-league root shows up to 58 but with 06,
16 and 52-57 missing, and it re-sorts itself between visits to the screen -- the same
screen entered twice gives two different orders.  An unstable order with dropped entries
is the shape of a fixed-size table being overfilled, not of an id the exe reserves.  The
scrambled order itself is harmless: every row's label, its League Info and the league the
Confirm loads agree, so a walk can still find any league that is in the list.

### Where this leaves 800 clubs

800 new placeholder clubs load, schedule and play.  What is not yet reachable from the
Kick Off menu is all of them at once: at 50 leagues only the first 38 appear in the list,
which is 608 of the 800.  The clubs above that are in the data and the exhibition screens
reach them -- FL 0701 of the 58x14 root draws its ratings fine -- so the remaining work is
the list's own capacity, not the world.

### `--reg-from` and the datecave stub

`mkworld.py` now takes `--reg-from N` to move a run's regulation ids above the shipped
band.  Note the ceiling: the datecave stub indexes regulation ids 1..255, so a run built
on 300 cannot get date stubs and `patchset.py` refuses it with "regulation id 300 is
outside the stub's table (1..255)".  The option stays useful for placing a run in the
176-255 window, which the experiment above shows the exe is content with.

## 2026-09-13 (later) -- league size is free, and the club wall is 1536

### League size is free: 14 to 33 clubs all work

A twelve-league world built with `mkworld.py --sizes 24,22,20,18,16,14` resolves every row
correctly and plays.  The 24-club league starts a season and kicks off; its Competition
Info reads "Contested by 24 teams, 46 Home & Away Fixtures", so the round count is computed
from the team count and is not inherited from the regulation record we copy.  That matters
because every new league copies the Premier League's 2352-byte regulation, a 20-club
record, and the copy is clearly not what fixes the schedule.  A 33-club league built with
`--extra 13` also starts a season, so the size is not capped at the largest shipped league
either.  Shipped sizes worth knowing, all type 4: Premier League 20, Ligue 1 and Eredivisie
18, LaLiga 2 and Serie BKT 22, EFL Championship 24.

The earlier claim that 20 clubs broke the row-to-league mapping was a measurement error and
is withdrawn above.  The list re-sorts between visits; a screenshot taken before navigating
away does not describe the list the Confirm sees.

### The club wall is exactly 1536

A league whose clubs sit at team index 1536 or above kills the process the moment a season
is created.  No exception is raised, no dump is written, the window simply goes.  The
bracket is tight and each step was measured:

* 39 leagues of 20, clubs FL 0761-0780, team indices 1503-1522: season starts.
* 39 leagues of 20 with a 33-club last league, clubs to FL 0793, indices to 1535: season
  starts.  This is the highest that works.
* 40 leagues of 20, clubs FL 0781-0800, indices 1523-1542: dies.  Still dies with a 41st
  league above it, so it is not about being last.  Still dies with 18 players per club
  instead of 23, so it is not the player index.  Still dies with the cap raised from 46353
  to 47121, so it is not cap headroom.
* 39 leagues of 20 plus 40 orphan clubs, so the file holds 1563 clubs and 46787 players but
  no league reaches past index 1522: season starts.

So the limit is not the club count in the file and not the player count.  It is the index
of the clubs inside the league being played, and the ceiling is 0x600.  On this base of 743
shipped clubs that is 793 new clubs, seven short of 800.

### The league list still truncates

Separate from the club wall, the Kick Off league list holds a bounded number of entries:
50 leagues gives 38 reachable, 49 gives about 43, 40 gives all 40.  The list also re-sorts
between visits and drops entries, which is the shape of a fixed-size table being overfilled.
Every row that is present is self-consistent -- label, League Info and the league the
Confirm loads all agree -- so the truncation costs reach, not correctness.

## 2026-09-13 (evening) -- the 1536 wall is two walls, and the first one is the board meeting

The wall was traced from the address Windows records for the fault.  Three crashes at the
40-league world all report the same offset, `0x13236e4`, which on this exe is
`0x1413236e4`:

```
1413236ca  mov    rcx, qword ptr [rbp + 0x67]
1413236ce  lea    r8, [rip + 0x15c1c0b]   ; 1428e52e0
1413236d5  mov    rax, qword ptr [rbp + 0x6f]
1413236d9  movzx  eax, byte ptr [rax]
1413236dc  mov    edx, dword ptr [rcx + rax*4]
1413236df  mov    ecx, edx
1413236e1  mov    eax, dword ptr [rbp + 0x77]
1413236e4  sub    ecx, dword ptr [r8 + rax*4]      <-- faults
```

The table at `0x1428e52e0` is 32 dwords long and holds nothing but small signed numbers --
`0, 3, 2, 2, 2, 1, 1, 1, 0, 0, 0, 0, -1, -1, -1, -2, -2, -2` and then `-3` to the end --
after which an unrelated table of triples begins.  Only one instruction in the whole exe
references it.  The value that indexes it comes from a search a few instructions earlier:
the function asks `0x141510280` which competition the team plays in (that one walks the
regulation array at `0xc12e9c`, reads each regulation's entry count from `+0x30a` masked to
seven bits, and returns the regulation id), looks the competition's runtime record up
through the thunk chain at `0x141579b90`, and then scans a 48-slot list of 20-byte entries
inside that record for the team's packed handle.  On a hit it takes `[entry+4]` as the
index.  There is no bounds check between that read and the table.

What the site computes is the target the board sets: the result is clamped to
`[1, number of teams]` and handed to the season-objective screen.  Overwriting the three
bytes at `0x1413236e1` with `xor eax, eax; nop` -- index 0, whose table entry is 0, a
neutral modifier -- takes the season past the point where it always died.  The board
meeting appears, the objective is offered and accepted, the press conference runs.

So the first wall is real and it is that one unchecked index.

### The second wall is in the schedule

With the objective site neutralised, the 40-league world dies a little later instead, twice
at the same place, `0x140cd6a21`:

```
140cd69cc  lea    rdx, [rip + 0x1a5914d]   ; 14272fb20 'd_schedule_'
...
140cd6a18  mov    edx, dword ptr [rsp + 0x40]
140cd6a1c  mov    rcx, qword ptr [rsp + 0x48]
140cd6a21  movzx  edx, word ptr [rcx + rdx*4]      <-- faults
```

`[rsp+0x48]` is a vector built a few instructions earlier and `[rsp+0x40]` is an index that
the `'d_schedule_'` lookup writes.  The strings around it -- `d_schedule_`, `schedule_date`
-- put this in fixture-calendar writing, not in the objective.  It is the same shape of bug
as the first: an index from data used on a vector without a check.

Two conclusions.  The 1536 ceiling is not one bound in one array; it is a series of
unchecked indexes that only stay in range while club indexes stay small.  And each one has
to be found the same way, because none of them is a size field that can simply be raised.

### The exe notices a debugger

`bptrace.py` was the obvious tool for this and it cannot be used here.  With it attached the
season did not fault at `0x1413236e4` at all: it died at a `__fastfail`
(`0xc0000409`) instead, and the breakpoint never hit.  Writing bytes into the running
process without attaching (`scratchpad/poke.py`) is fine, and patching the exe on disk --
which is what `patchset.py` already does -- is fine.  So for this exe the working
loop is: read the fault address out of the Windows Application log, patch bytes, run again.

### The second wall is the club index too, not the league count

The obvious alternative reading of `0x140cd6a21` was that 40 leagues is simply more schedule
entries than the vector beside it holds -- that the second wall is about how many
competitions the world has, not how high the club indexes run.  It is not.  The same
40-league world, unpatched, playing FL League 38 whose clubs sit at indices 1483-1502,
creates the season all the way through: board meeting, press conference, and the Master
League hub with standings (FL 0741, FL 0758, FL 0757 ...) and a fixture list starting
28/8/2025.  Forty leagues are fine.  What is not fine is a club at 1536.

Which points at what the two sites have in common.  Neither is a size field; both are
indexes taken out of data and used without a check.  The likeliest shape is a runtime table
of teams with 1536 slots that the shipped data never fills: a club above that has no
runtime record, so everything that reaches for one gets rubbish, and fixing any single site
just moves the crash to the next reader.  If that is right, the thing to raise is that
table, not the individual sites -- and nothing in the exe compares anything against 1536
(only two `cmp reg, 0x600` exist and both are message-code switches), so like the old 1303
ceiling it is computed from a buffer size and a stride rather than written down.

### 1536 is not a buffer over a stride either

`immindex.py` was run over the code section and `immquery.py` asked which immediate over
which record size gives 1536.  The answer is nothing worth chasing.  1821 immediates divide
into 1536 by some stride, and the only ones whose stride is a size the data actually uses
are `0x4800 / 0xc`, `0x6000 / 0x10` and `0x750d0 / 0x138`; every site holding them sits in
a run of unrelated configuration constants (`0x7530`, `0x2710`, `0x3e8` and so on) or in a
bitmask, not next to anything that indexes clubs.  A scan of the whole 458 MB image for
every encoding of a comparison against 1536, not just the code section, finds two, and both
are message-code switches.

So 1536 is neither stored nor computed from a buffer the way the old 1303 ceiling was.

The line worth following next is the heap object the game reaches through
`0x1414b6a60` and then `[rax + 0x78]`.  The competition records live inside it: the resolver
at `0x14158df30` bounds an index at `0x258`, multiplies by `0x187c` and adds `0x4650`.  A
team table is very likely a sibling field of that same object, and its bound will be written
the same way -- an immediate next to an `imul`, not a lone constant -- so the way to find it
is to walk that object's fields, not to search for the number 1536.

Two candidates from that search were followed to the end and both are coincidences, which
is worth writing down so nobody spends the evening on them again.  `0x6000` is the size of
two adjacent regions at `+0x4698c` and `+0x4c990` of a runtime object, zeroed together at
`0x1416f51d6`, each with its element count in the dword immediately above it; every reader
(`0x1416f5e70`, `0x1416f6e70`, `0x1416f70e0`) walks them with `rax*8` and `add rbx, 8`, so
they hold 3072 pointers, not 1536 records.  `0x1b0000` is more tempting still -- it is
exactly 1536 * 0x480 and it sits inside `0x140cd6900`, the very function that crashes -- but
at `0x140cd6dbc` it is passed in `edx` to a call on the `schedule_next` node, a flag mask,
not a size.

So the constant hunt is closed with nothing, and the heap-object walk described above is
the open line.

## 2026-09-14 -- the calendar day is the next wall, measured at 251 of 280

The 39-league world was finally measured instead of estimated.  `_FL26E39x793` (39 leagues,
793 new clubs, 1536 clubs in total), set `teams-coaches-regs-players-dates-matches-upper`,
a Master League season created on FL League 38:

* the match table holds **21,010 of 26,000** records -- well past the shipped 13,000, so
  raising it was not optional,
* the daily lists hold **19,264** match ids, so 1,746 records in the table sit on no day,
* **no day is full, and the busiest day carries 251 of the 280 a day can hold.**

Twenty-nine slots.  The next league to be dated on the same weekday overflows it, and the
scheduler drops the overflow without a word, so the failure would look like clubs with
nothing to do rather than like an error.

The busiest day is an outlier: day 37 carries 251 where the next-busiest carry 196, 190,
188.  The four date offsets `patchset.py` cycles (2, 6, 5, 1) are what keeps the rest
apart; they are the reason 39 leagues fit at all, and they are also why the load is uneven.

For comparison, the same tool on a shipped-world season (no new leagues) reports a busiest
day of 166, which agrees with the 167 counted by hand earlier and is the check that the
measurement is reading the right bytes.

### What raising it involves

The day record is 0x2c4 bytes: a u16 id list from +0x00 (0x230 bytes, so exactly 280 ids,
no slack), a **u16** count at +0x230, and 18 event qwords at +0x234.  The scheduler is
`0x141350290` and it is small and explicit:

    1413502b0  lea    rbx, [r14 + 0x16038a8]      ; the calendar
    1413502b7  cmp    r13d, 0x16d                 ; 365 days
    1413502c0  imul   rcx, r13, 0x2c4             ; the stride
    14135033b  cmp    eax, 0x118                  ; 280, four times in this function
    14135034c  inc    word ptr [rbx + 0x230]      ; the count is 16-bit

So the cap itself is four compares in one function, the count field has room, and the work
is the same shape as the match table: **135 sites reference the calendar base `0x16038a8`**
(against 187 for the match table), and the calendar has to be relocated because the id list
cannot grow in place.  This is a Phase-sized job, not a patch.

### An old Master League save hangs under the patch

Before the measurement, `Continue` was tried on `ML00000000` dated 2026-09-10, made before
the block grew.  The edit block loaded -- `calread.py` read a populated calendar and day 236
out of the running process -- but the UI never left the loading spinner, and was still
spinning seven minutes later.  The save was backed up, not overwritten, and the season below
was created with `New` instead.

That is the first direct evidence for the save-compatibility risk: a save written under one
block layout is not merely stale under another, it can hang the load.  A released patch has
to refuse a save it did not write.

## 2026-09-14 -- the target type to competition binding, found

Section 8 said who qualifies for Europe is a table in `.data` at `0x1434f1fa0`, and the
round-2 notes added that the target type in each row is only a filter key: nothing in the
query turns it into a competition id.  That left the binding unlocated, and it is the one
thing standing between the rights table and a **new** continental competition.  It is code,
and it is small and regular.

### The chain, bottom to top

`0x1413b7760` walks all 112 rows and keeps a row when `row.target_type == arg3` and
`region_of(row.source_regulation) == arg2`; `0x1413b7880` is the thin wrapper that returns
how many it kept, reached through the thunk `0x1413b7900`.  Above it three functions pass
the target type straight through -- `0x141357470`, `0x1413561f0`, `0x141355c90` -- so the
constant comes from the top of the chain, not from any of them.

### The top of the chain is one builder per competition

    141364209  xor    r8d, r8d          ; target type 0  -- UCL groups
    14136420c  xor    edx, edx          ; confederation 0 -- UEFA
    141364211  call   0x141355c90
    14136421b  lea    r8d, [rdx + 1]    ; target type 1  -- UCL qualifiers
    14136421f  call   0x141355c90
    141364229  lea    r8d, [rdx + 2]    ; target type 2  -- UEL
    141364232  jmp    0x141355c90       ; tail call

and the South American one, `0x141365fb0`:

    141366040  mov    edx, 1            ; confederation 1 -- CONMEBOL
    141366048  lea    r8d, [rdx + 2]    ; target type 3   -- Libertadores
    14136604c  call   0x141355c90
    141366059  lea    r8d, [rdx + 3]    ; target type 4   -- Sudamericana
    141366062  jmp    0x141355c90       ; tail call

Each builder first proves its own competitions exist by scanning the regulation array for
its ids (`cmp word ptr [rcx], 6` then `5` for the UEFA pair, `8` for the South American
one) and returns doing nothing if they are missing.  Target type 7 is reached the same way
from `0x1413633ff` and `0x14136383f`, which call `0x141357470` directly with `r8d = 7`.

### The dispatcher

`0x14135e940` runs the builders in sequence, one block per confederation, each guarded by a
lookup of its area id:

    14135e95e  mov    eax, 4            ; area 4
    14135e97c  call   0x141364240       ; or 0x141364110
    14135e98f  mov    eax, 0xa          ; area 10
    14135e9ad  call   0x141365fb0
    14135e9c0  mov    eax, 0x10         ; area 16
    ...

### Why this matters, and what it costs

A new continental competition needs a target type nobody consumes, and a consumer for it.
The consumer is one more call in the builder for its confederation -- the builders end in a
tail call, so appending a target type means turning that `jmp` into a `call` plus a new tail
call, about twenty bytes in a cave.  Nothing existing is taken away: every call already
there stays, which is the only acceptable shape of this change.

So a Conference League is: a new competition and regulation id (there are 164 and 133 free),
a format template reused from the ones in use (20/22 for UCL-shaped, 50/52 for a custom
cup), rows in the rights table with a new target type, the two-instruction relocation of
that table, and one appended call in the UEFA builder.  No part of that replaces anything.

Still open: which target type values are genuinely unconsumed.  0, 1, 2 (UEFA), 3, 4
(CONMEBOL) and 7 are accounted for here; 9 and 10 are the Belgian and Danish europlayoffs
and are reached through `0x1413571c0` / `0x14135dc40`, which have not been read yet.

2026-09-14 -- spreading the season over all seven weekdays
---------------------------------------------------------

The datecave stub gives every new regulation id a day shift of 0..6, but until now only
four of the seven were used, and they were handed out round-robin over the key list.  That
is the worst thing to do with them: the shipped competitions are not spread evenly over the
week, so a round-robin plan piles our leagues onto the days the shipped world already fills.
Measured in `_FL26E39x793`, round-robin over 0..6 gives a busiest day of **261** -- worse
than the four-shift plan's 251.

`tools/dayplan.py` measures the live season instead of guessing.  It reads the match table
and the 365 daily id lists, splits each day's load into "shipped" (a match whose regulation
key is not one of ours) and a per-key row for each of our leagues, and then searches for the
assignment of shifts that flattens the total: greedy placement of the heaviest league first,
then local search that moves one league at a time while the peak keeps dropping.  It prints
the plan as the `--date-offsets key:shift,...` argument, which `patchset.py` now accepts in
that form as well as as a bare list.

The first searched plan measured, in a real Master League season:

    busiest day 251 -> 233      headroom 29 -> 47

The peak day is the one place the shipped world is heavy: 153 shipped matches plus 98 of
ours.  Every other heavy day (206, 193, 190) is 100% ours, so there is more to win here --
but the simulation over-promises.  It predicted 193 for the plan that measured 233, because
shifting a league's *measured* days by a delta is not exactly what the generator does: the
fixture template is regenerated, not translated.  The tool is therefore an iterator, not an
oracle -- measure a season, plan, install, measure again.

### The second plan crashes at season creation

dayplan measured the 233 season and proposed a plan it predicted at 187.  Installed, the
game died during season creation, at the step where the manager's General Settings dialog is
confirmed, twice out of two runs:

    02:11:08Z  offset 0x1148796d
    02:20:50Z  offset 0x084ed4c0   -> VA 0x1484ed4c0

Two different addresses at the same step; 0x1484ed4c0 is the address an earlier session
already recorded as an intermittent crash with garbage registers, so neither run is proof on
its own.  Re-installing the first plan and re-running the same script created a season
normally and measured 233 again -- so the first plan is 2 for 2 and the second 0 for 2.
That is evidence that the plan matters, not a mechanism.  The obvious suspect is the stub's
wrap at 365: a shift can carry a fixture over the end of the season into day 0, and the
second plan uses more of the large shifts.  Not yet tested.

The installed set holds the first plan, the one that works.

2026-09-14 -- what it costs to widen a calendar day
---------------------------------------------------

A day record holds 280 match ids and nothing spare: the id list runs 0x00..0x22f, the count
sits at 0x230, eighteen event slots of eight bytes run 0x234..0x2c3, and the 365th record
ends at 0x1642a1c, which is the current-day field.  So the list cannot grow in place.  It
grows by relocating the calendar and widening the stride, and `tools/calstride.py` now says
exactly what that costs, from the code rather than from a constant scan:

    base    135    the calendar base as a disp32 or an imm32
    stride   81    `imul r, i, 0x2c4`
    cap      65    `cmp r, 0x118`, the id the scheduler will not write
    count   101    the count at +0x230
    event    99    an event slot, +0x234 .. +0x2c3
    after    38    the three fields past the calendar, reached off its base
    ---
            519

Every one of the 135 base references is the base exactly -- no site carries a folded day
offset -- so relocation is the same displacement rewrite the patch set already does for the
other arrays.  The day index and the field offsets are computed at run time everywhere.

Why this needed a flow-graph walk, not a scan.  0x230 and 0x118 are ordinary numbers.
`call 0x1414bb000` followed by `cmp dword ptr [rax + 0x230], 1` appears in eight of these
functions and has nothing to do with the calendar; so do `[rbp + 0x234]` locals in two more.
A constant scan counts 116 sites at +0x230 where 101 are real.  And the naive fix -- follow
the registers in a straight line -- is wrong in the other direction: in 0x141315fd0 the
early-return path holds `mov r13, [rsp + 0x28]`, restoring the caller's r13, and read in
order that clears the tag on every day-record field after it.  The tool therefore carries
the tags to a fixpoint over the flow graph and merges at joins, and analyses blocks the
graph cannot reach -- jump-table targets -- from no assumptions rather than skipping them.

Twenty-nine sites are established by the shape of the access instead of by the taint,
inside functions the taint already proved walk the calendar; they are marked `"by": "shape"`
in `patches/calendar-sites.json` for a reviewer.  0x1412e8480 is the clearest of them:
`lea r9, [rsi + 0x238]`, a loop of `cmp r10d, 0x12` over eight-byte steps reading `[r9 - 4]`
-- the eighteen event slots, walked through a pointer the taint never reached.

### What is not affected

The 365 (`cmp eax, 0x16d`, 104 sites) stays: the season is still a year.  The eighteen
events per day stay.  The id list still begins at +0 and is still indexed `[day + i*2]`, so
no id access changes; only the fields behind it move.  No shipped competition is touched --
this is the same calendar, with more room in it.

### What is still unknown

Whether anything outside the executable assumes 0x2c4.  The mode copy carries its own
calendar (0x1413fea00 copies a 0x135bd10-byte object) and the copy's day stride has not been
measured; if the copy is widened too, the two loop bounds in `layout.json`'s `hold_sites`
note apply here as well.  Until that is settled the widening is not safe to install.

### The mode copy carries its own calendar, and its own copy loop

`0x1414016b0` (block -> A) ends with `lea rcx, [rsi + 0x16038a8]`, `lea rdx, [r14 + 0xa8d4a0]`,
`call 0x1413fbf60`, and `0x141401c10` does the same the other way: the mode copy holds a
calendar of its own at copy +0xa8d4a0, and one function moves it.  That function is a
stride-aware loop -- `mov r10d, 0x16d`, a body unrolled as five 0x80-byte blocks plus a
0x44 tail, then `add r9, 0x2c4` -- so the stride is not only an immediate there, it is the
shape of the code.  Widening the day therefore means rewriting that loop, and widening the
copy's calendar too, which shifts everything above +0xa8d4a0 in the copy.

This also marks the limit of what `calstride.py` can see: 0x1413fbf60 takes the calendar as
an argument and never mentions the base, so it is not among the 106 functions.  Any other
function that is handed a day record rather than computing one is invisible to the walk in
the same way, and the 519 sites are a lower bound.

So the widening is two jobs, not one, and the second has no patch class yet.  The measured
headroom -- 47 ids on the busiest day after the date spread -- is what decides whether it is
needed at all before the league count reaches the target, and that is the cheaper question
to answer first.

2026-09-14 -- the day cap is not the wall at fifty leagues
-----------------------------------------------------------

Measured, not estimated.  `_FL26E50x800` -- fifty leagues of sixteen clubs -- builds a
Master League season of 18,144 matches, and with a spread `dayplan.py` searched for those
fifty regulation ids the busiest day holds **196 of 280**.  The earlier thirty-nine leagues
of twenty clubs reach 233, because twenty clubs play 380 matches a season where sixteen play
240: more leagues of a normal size are cheaper than fewer large ones.

So the calendar day, which looked like the next wall when it was first measured at 251, is
not what stops the target of forty to fifty leagues.  The 1536-club wall is: fifty leagues
of twenty clubs would need a thousand new clubs, and there is room for about eight hundred.
Widening the day -- 519 sites, plus the mode copy's own calendar and its unrolled copy loop
-- can wait until the club count is free to grow, which is what would fill the days.

2026-09-14 -- the heap object at +0x78 does not hold the 1536 bound
--------------------------------------------------------------------

`tools/obj78.py` walks every function that calls `0x1414b6a60`, follows the object loaded
from `[rax + 0x78]`, and reports each `(bound, stride, offset)` it is indexed with.  Thirty-
six indexed accesses, and the bounds are 0x258, 0xcd, 0x64, 0xa, 0x9, 0x3, 0x2 -- nothing
of the order of 1536.  The competition array is the only large one: 600 records of 0x187c
at +0x4650, ending at +0x39a330, with a set of smaller fields from +0x39a8f0 up.  The whole
object is about 4.6 MB.

Read live, a competition record is a short header and then entries of 0x10 bytes --
`<id> ff ff ff ff 00 00 00 00 2b 00 00 00` repeating -- whose first dwords climb by 0x4001
(0x45e68000, 0x45e6c001, 0x45e70002), so the index is packed into a bitfield rather than
stored plainly.  0x187c happens to equal 0x7c + 1536 * 4, which is a coincidence of
arithmetic: the entries are sixteen bytes, not four.

So the sibling-table guess is closed: whatever refuses a club index of 1536 is not reached
by indexing this object.  What is still true is the shape of the answer -- a bound written
beside an `imul`, not a lone constant -- and `obj78.py` is the tool for asking that question
of any other object once one is identified.

## What 0x1484ed4c0 actually is (2026-09-14)

This address has been on the record since 2026-09-11, five times, always described the same
unhelpful way: a crash with garbage registers somewhere in the protector's blob.  Two
minidumps taken tonight say what it is, and the answer is not what any of the earlier
entries guessed.

Windows Error Reporting will leave a dump without being a debugger, so it does not trip the
anti-debug path that turns these faults into `__fastfail`.  `tools/crashdump.py` reads the
exception record, the faulting thread's registers, and -- the part that matters -- sweeps
that thread's stack for return addresses inside `.trace`.

The fault itself:

    at 0x1484ed4c0  (.impdata)        mov [rcx], r8d
    write of 0x1ecee0dc1              r8 = 0, so it is storing zero
    rax c8072890  rdx 9c67b725  rbx dbfedbdf  r9 7cc5b908  r10 14ab18846
    r11 5dd5cd28  r12 ba238df7  r13 dba6d565  r14 b3eb6750  r15 f49f7b2c

The second dump, from a different run, a different process and a different thread, has
**every one of those registers identical**.  Only `rcx` differs -- 0x1ecee0dc1 against
0x1b535e701 -- along with the stack pointer.  That single fact rewrites the case.  Identical
registers across two independent crashes is not memory corruption arriving at random; it is
one deterministic code path, run twice, whose only varying input is a pointer that depends
on where the heap happens to lie.  "Garbage registers" was always the wrong reading: those
are a virtual machine's working registers, and they are constant because the handler is.

The stack names the code that got there.  Below the handler sit `.trace` frames in two
clusters: FoxCore transform work (`transform`, `Rotation`, `TransformRT`) at the very top,
then sky and lighting (`TppAtmosphere`, `StartSkyCapture`, `SH_LIGHTING`, `atshFilePath`),
and underneath all of it a long run of jemalloc -- the game's allocator, strings and all
(`jemalloc-3.4.0\src\jemalloc.c`, `arena.h`, `tcache.h`, `bitmap.h`).  The faulting thread
is a worker, not the main thread.

So the shape is: a worker thread, in scene and lighting work, storing a zero through a
pointer that is wild and misaligned, with the allocator immediately beneath it.  That is
the signature of **heap corruption** -- something wrote past the end of an allocation
earlier, the allocator's own bookkeeping now yields a bad pointer, and the crash surfaces
in whatever unrelated code allocates next.  It explains everything the older entries found
puzzling: why it is intermittent, why the fault address never led anywhere, why it moves
between match load, exhibition kickoff and now the Master League hub, and why bptrace only
ever turned it into `__fastfail`.

Two things were checked first and are not the cause.  All 2543 patches of
`teams-coaches-regs-players-dates-matches-upper` apply cleanly and both nullguard patches
after them (`sider.log`), and the two code caves do not collide: the date-spread stub
occupies 0x14252e690..0x14252e7e6 and the nullguard trampoline begins at 0x14252e800, 26
bytes clear.

Two observations bound where to look next.  A Kick Off exhibition -- RSC Anderlecht 0:0
FL 0098 -- **loads and plays** in this same world with the whole patch set live, so neither
793 new clubs nor the size of the patch set breaks a match by itself.  And the second crash
came while the game merely sat in the Master League hub after the season was created, with
no day advanced and no match entered, which rules out match entry as the trigger and points
at something that runs on its own schedule.

If this is heap corruption, the suspect is one of our own cap patches: a bound raised on an
array that was never enlarged to match, so the game writes past its end.  That is a
bisection, not a disassembly, and it is the next thing to run.

## Not everything that dies is the same crash (2026-09-14)

Five minidumps now, and they are not one failure.  Sorting them apart is what the fault
addresses alone could never do.

**Three are the heap-corruption signature.**  0x1484ed4c0, `mov [rcx], r8d`, with `rax
c8072890  rdx 9c67b725  rbx dbfedbdf  r9 7cc5b908  r10 14ab18846  r11 5dd5cd28  r12
ba238df7  r13 dba6d565  r14 b3eb6750  r15 f49f7b2c` identical in every one, and only `rcx`
-- the wild pointer -- different: 0x1ecee0dc1, 0x1b535e701, 0x1edad21c1.  A fourth, at
0x1531cc313, is a different handler reading through a different wild pointer (0x8b12900d,
held in r12), and its stack is the same neighbourhood: the allocator and the file-path
helpers ('z:/', 'vector<T> too long').

**One is not a crash at all.**  0x14195849c is in `.trace`, not the protector, and the
instruction there is

    141958493  call   0x14029e5d0
    141958498  test   eax, eax
    14195849a  je     0x1419584a7
    14195849c  mov    dword ptr [0], 0xdeadbeef

-- the game killing itself on purpose because the call above it failed.  The call's argument
is `Fox/Scripts/Gr/init.lua`, and the enclosing function also names 'MainRender' and
'MainViewport': this is graphics init, and the deliberate null write is its assertion that
the script loaded.  The registers say the same thing in another voice -- r12 = 0x780 and
r15 = 0x438, which is 1920 by 1080.

That one is ours to fix, and the fix is patience.  The season walk stopped the old instance
and started the next one fourteen seconds later; the game needs about twenty-five to leave
memory, and the new instance was reading assets while the old one still held them.  The wait
is now forty seconds, and the walk has moved out of the scratchpad into `tools/seasonnew.py`
where the reasoning can live next to the number.

**`upper` is not the cause.**  The same world was run on
`teams-coaches-regs-players-dates-matches` -- 1229 patches against 2543, the same array
bases, without the `upper1`/`upper2` region shifts or the `belt` move -- and it died the same
way at the same step.  Whatever corrupts the heap is in the part both sets share, so the
bisection has to go lower: teams, coaches, regulations, players, matches.

An arithmetic audit of the installed set came back clean and is worth recording as a
negative: the relocated arrays pack end to end inside the block with no overlap at all
(players 0..0xc12a78, calendar 0x16038a8, teams 0x1877070, coaches 0x1b07470, regulations
0x1c84230, rec596 0x1cf7910, matchflags 0x2bbec50, belt 0x2bc51e0, block ending 0x2d5a068 --
1.6 MB of slack above the highest array).  No patch overlaps another's bytes, and not one of
the `hold_sites` that layout.json marks as must-not-raise was raised.  The corruption is not
a mistake in the placement; it is a bound raised somewhere over an array that does not live
in the block at all.

## Two shapes of fault, told apart by arithmetic (2026-09-14)

Inside `.impdata` there is no instruction to read: the code at the faulting address is the
protector's virtualised form and the bytes there mean nothing.  The registers still mean
something, and the arithmetic that built the faulting address is usually visible in them.
`tools/crashdump.py` now looks for it -- if two registers add up to exactly the address
that faulted, it says so, and if a register holds it outright, it says that instead.

Across five dumps this separates two classes cleanly:

    1644   read  0001d3696c3e   = rdx 0000042c7440 + r8 0001cf3cf7fe   base + index
    12016  read  000036605eaa   = rdx 000008206050 + r8 00002e3ffe5a   base + index
    7220   read  00008b12900d   held outright in r12                   a pointer
    14308  write 0001edad21c1   held outright in rcx                   a pointer

The pointer class is the one already written up above: registers full of high-entropy
values, a heap pointer that is rubbish, jemalloc and FoxCore frames beneath it.

The base+index class is new and is more informative.  In both dumps the base in `rdx` is a
perfectly ordinary small heap pointer, and every register except a handful is zero -- this
is not a register file full of garbage, it is one bad number.  The index in `r8` is
absurd: 0x2e3ffe5a and 0x1cf3cf7fe, the second larger than 32 bits.  So the object being
indexed is intact and reachable; what is wrong is a count or an index stored in it.  That
is a different bug from a corrupted pointer, and it is the one worth chasing, because an
index comes from a field we can name.

(`r9` holds the faulting address shifted right by 24 in both, and `r11` a byte of it
shifted back left -- that is the protector's own address lookup, not the original
instruction, and it carries no information about the bug.)

## Master League -> Continue dies on a missing schedule (2026-09-14)

Resuming the existing Master League save crashes at `0x140cd6a21`, in `.trace` -- real
game code, not the protector, which makes it the most readable crash we have.  The dump
has our edit block in `r12` (0x7ff4e1f90010), so the code is walking our data at the time.

    140cd69cc  lea    rdx, [rip + 0x1a5914d]   ; 'd_schedule_'
    140cd69d8  call   0x140402370              ; make the key string
    140cd69f0  call   0x14150d620              ; look it up -> count at [rsp+0x40],
                                               ;               pointer at [rsp+0x48]
    140cd6a07  call   0x140e4cd10
    140cd6a12  je     0x140cd6ead              ; that result is checked
    140cd6a1c  mov    rcx, qword ptr [rsp + 0x48]
    140cd6a21  movzx  edx, word ptr [rcx + rdx*4]   <-- rcx = 0
    140cd6a28  call   0x1414bb280              ; ...then our block is indexed by it
    140cd6a51  lea    rdx, [rip + 0x1a590d8]   ; 'schedule_date'

The lookup of `d_schedule_` returned null and the result is never checked -- the call right
after it is checked, which is what makes the omission look like an oversight rather than a
guarantee.  The read is of address 0, not of a wild address, so this is a missing array and
not a corrupted one.

This is the same site as the second wall recorded for the 1536-club limit, where it faulted
on a wild address instead.  One unchecked pointer, reachable two ways.

Practical consequence for testing: a season cannot be resumed, so every run must create
one.  `tools/seasonnew.py` does that in about seven minutes, which is cheaper than making
this safe would be -- but it is a small, well-understood null check, and it is the obvious
first candidate if resuming ever matters.

## The same call path, once as a fault and once as a deliberate abort (2026-09-14)

Opening Settings -> Options from the main menu killed the process with `0xc0000409` --
`__fastfail`, raised from inside a system DLL, which is the CRT deciding the heap is
corrupt rather than an access violation happening to land somewhere.  No debugger was
attached, so this is not the anti-debug path.

What makes it useful is the stack.  Six of its `.trace` return addresses are the same six,
in the same order, as the stack of dump 12016 -- the `rdx + r8` base+index fault:

    14038e401  14162ff76  14022c667  1415e5f80  141631576  1403ae4f6

So the heap damage and the absurd index are reached through one call path, and that path is
walked by ordinary menu work -- opening a settings submenu, in this case, with no match and
no season generation involved.  Whatever writes out of bounds is doing it earlier and
elsewhere; these frames are only where the damage is noticed.  They are still the best
handle we have, because unlike everything in `.impdata` they are real code that can be
disassembled and named.

### What those frames are

Naming them changes the story.  `tools/funcinfo.py` on the six:

    14038e3e0   jemalloc.  Its strings are the allocator's own assertions --
                'bitmap_get(bitmap, binfo, bit)', '(g & (1LU << (bit & ...))) == 0',
                'jemalloc/internal/bitmap.h', 'internal/tcache.h', 'Invalid conf value'.
    1415e5f30   the FoxEngine effect system: 'FxInfinityLifeNode', 'FxRandomLifeNode',
                'FxReceiveLifeNode'.
    14022c630   a leaf called from 1092 sites -- a thunk, no information in it.
    14162fb20, 1416311f0, 1403ae320   unnamed, few callers each, between the two.

So the `__fastfail` is **jemalloc asserting on its own bitmap**: the allocator checked an
invariant of its run metadata and found it broken.  That is not a symptom that can be
argued with -- it is the heap itself reporting damage, from inside the allocator, before
any of our data is read.

And the path into it is the effect system.  That fits what the other dumps already showed:
the `0x1484ed4c0` class dies among FoxCore transform and sky-capture frames with a long run
of jemalloc beneath it.  Three different deaths -- a wild pointer, an absurd index, and an
allocator assertion -- all in the same neighbourhood, which is the neighbourhood that
allocates constantly and therefore the one that notices first.

This does not name the writer.  It does narrow what to look for: something is writing past
the end of an allocation, and the next allocator operation on that run is where it lands.

(Later: it is not our writer.  The same death, register for register, happens on the
unpatched exe with our data root switched off -- see "The startup death is not ours" at
the end of this file.  The description of the dumps here is still accurate; the inference
that the patch set is what damaged the heap is not.)

## The game listens to one named controller, and it was a dead one

The virtual pad produced nothing.  Not a wrong button, not an occasional dropped press:
nothing at all, on the title screen and in the menus, from a pad created before the game
started and from one created after.  It was not the pad.  XInput reported slot 0 connected
and reported `XUSB_GAMEPAD_A` to anyone who polled it while the harness held the button
down, and Windows enumerated the device as `USB\VID_045E&PID_028E` -- the identity of a real
Xbox 360 controller.  The game was not asking about that device.

Which device it asks about is written down.  `Settings.exe` keeps the game's non-save
settings in `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\settings.dat`, a 612-byte
file beginning `WECF`, and at offset 0x64 it holds sixteen bytes that parse as a DirectInput
*instance* GUID.  An instance GUID names one controller as it was plugged in on one machine,
not a model and not a class.  The one stored here was `2b5a9260-e320-11f0-8002-444553540000`,
and enumerating DirectInput live turned up five game controllers on this machine -- none of
them that.  The game was faithfully polling a controller that no longer exists.

`Settings_b.dll` is where the shape of the file is legible: it carries `ChangeJoystickDevice`,
`GetJoystickDeviceList`, `controller_device_index`, `joystick_player_index`, `guid`, and the
`ysl::peripheral::input_joystick_dx8` class whose `polling` and `get_object_push` are the
functions behind every button read.  The device is chosen by GUID once, in Settings.exe, and
the game obeys that choice without ever falling back to "whatever is plugged in".

Writing the live instance GUID of the virtual pad into those sixteen bytes and restarting
the game fixed it completely: Cross left the title screen, and the D-pad moved the main menu
tile cursor.  `tools/padbind.py` does the enumeration, the comparison and the rewrite, and
keeps the original file beside it -- the binding is the user's own controller setting.

Two details worth keeping.  The exe imports both `DINPUT8.dll` and `XINPUT1_3.dll` and its
RTTI names both `cobra::me::hid::impl::xb2::XInputPad` and a `di8` pad, with a `pad_assign`
table naming `DI8_Xbox360`, `DI8_PS3` and `XInput`; the binding is what selects among them,
not the API.  A virtual *DualShock 4* in place of the Xbox pad was twice followed by the game
dying eleven seconds into startup, which read as evidence that the DirectInput enumeration
path reaches deep into the game -- but the same death, register for register, later turned
up with the Xbox pad bound and working.  It is the patch set's own flaky startup crash; the
pad type has nothing to do with it.

## The block constructor has unwind funclets, and the attribution walk cannot see them

The edit block is one C++ object with about thirty array members, and MSVC gives a
constructor like that a small funclet per member, to be run if a later member's
constructor throws. They sit together at `0x142495050 .. 0x1424953ad`, one after the
other, and they all have the same shape:

    14249507d  push   rbp
    14249507f  sub    rsp, 0x20
    142495083  mov    rbp, rdx
    142495086  mov    rcx, qword ptr [rbp + 0x80]     ; the block under construction
    14249508d  add    rcx, 0xadf4bc                   ; the member's offset
    142495094  lea    r9, [rip - 0x1bb439b]           ; 1408e0d00, the team destructor
    14249509b  mov    r8d, 0x2ee                      ; 750 records
    1424950a1  mov    edx, 0x690                      ; of 0x690 bytes
    1424950a6  call   0x14159fa0c                     ; __ehvec_dtor

The immediate add is not what hides them -- a scan of `.trace` for
`add r64, <a block member's offset>` finds 109 sites and the walk had already attributed
100 of them. What hides them is that a funclet is not reachable. It has no array access
of its own to walk out from, and nothing calls it: it is named only by the unwind data,
so no caller graph leads there. `patches/attrib.json` has no site anywhere in the
range. The player
funclet's count at `0x142495060` had been found by hand and was being patched through
`COPY_PLAYER_SITES`; its eight siblings were not, and had been running at the shipped
offsets and counts through every set that relocates an array.

What that means with the block relocated: the team funclet destroys 750 team objects at
`0xadf4bc`, which after the move is the middle of the player array. The regulation and
coach funclets do the same elsewhere. Destructors run over live records of another type,
and the pointers they free are not pointers.

The funclets that matter are the eight the relocation moves -- teams, regulations,
coaches, the match table, the two dummies inside the belt, the fixture table and the tail
of `upper2`. Everything from the season calendar at `0x16038a8` upward stays where it is
and needs no patch. `tools/patchset.py` now emits all of them from an explicit
`DTOR_FUNCLETS` table, twelve sites on the full set.

This is a latent fault, not a proven cause of any particular crash: the funclets run only
if a member's constructor throws. It is written down here because it was found while
looking for something else, and because a destructor walking the wrong memory is exactly
the shape of fault that is impossible to attribute afterwards.

## One table in the block is reached without ever naming the block

`0x140c4f0f0` opens the way every edit-block function opens:

    140c4f136  call   0x1414b6a60                  ; the owner
    140c4f13b  mov    rbx, qword ptr [rax + 0x48]  ; the block

and then, four hundred bytes later, searches a table inside it:

    140c4f240  mov    eax, ecx
    140c4f242  lea    rax, [rax*8 + 0xe63de4]      ; the table, in upper2
    140c4f24a  add    rax, rbx                     ; ... plus the block
    140c4f24d  cmp    edx, dword ptr [rax]
    140c4f24f  je     0x140c4f25d
    140c4f251  inc    ecx
    140c4f253  cmp    ecx, 0x7530                  ; 30000 entries
    140c4f259  jb     0x140c4f240
    140c4f25d  test   rax, rax
    140c4f262  mov    rax, qword ptr [rax]         ; and dereferences the hit

The offset is in the `lea` and the block base arrives in the `add` after it, so the
instruction that carries the offset carries no block reference of its own. That is why
`patches/attrib.json` has no site anywhere in this function: the walk attributes an
instruction by what its base register is, and this one has no base register at all.

A sweep of `.trace` for index-only memory operands whose displacement lands in a
relocated region finds 63 candidates and exactly one real instruction; the other 62 are
misaligned decodes, recognisable by what they decode to (`rol ..., 0`, `test byte ptr
[...], ah`) and by displacements like `0xc3870f` that are a `jbe` opcode read as data.
So this is the only one, and it is now in `patches/layout.json` as `upper2`'s
`extra_sites`. Left behind by the belt move it would have searched the middle of the
player array and dereferenced a player's field as a pointer.

The `0x7530` bound stays. The table is 30000 x 8 bytes inside a region of 0x3c124, with
0x17a4 to spare, so it cannot hold a player index past 30000 without somewhere to grow
into. Players above that are simply not in it.

## A check for the two shapes the attribution walk cannot file

Both misses above have the same cause: the attribution walk decides what an instruction
refers to by looking at its base register, and neither shape has one to look at. So
`tools/blindspots.py` looks for them the way they were found by hand.

    python blindspots.py <set>      # exit 1, and a list, if the set leaves one behind

It sweeps `.trace` for `add r64, <a member's offset>` and for index-only memory operands
whose displacement lands in a region the set relocates, and prints what the generated
`sider/fl26caps.<set>.lua` does not touch. Three filters keep the output to real
instructions: the enclosing function, taken from the `.pdata` runtime function table,
must call the owner getter `0x1414b6a60`, which is how a block function begins; the
candidate must be a real instruction boundary, found by disassembling that function from
its start; and the member must be one this particular set actually moves, since a member
left in place needs no patch. Without the boundary check the index-only sweep returns
111 candidates, of which one is an instruction; with it, one.

Run against the ladder as it stood, it names exactly the funclets each set was missing --
two for `teams-coaches`, three for `teams-coaches-dates-matches`, four for the regulation
set -- and reports the rebuilt sets clean. Every stored set has been regenerated, which
also brings the older ones up to date with the `extra_cap_sites` and `hold_sites` work
they predate.

## The startup death is not ours

The nine-to-eleven second startup death had been read as evidence that the patch set
corrupts the heap before a season is even started: the faulting thread's first real frame
is jemalloc, and jemalloc was asserting on its own bitmap, which is the allocator
reporting damage from inside itself.

That reading was wrong, and the mistake was never testing an unpatched boot. Booting eight
times with the full set gave four deaths. Booting the same way with **no patches at all
and our data root switched off in `sider.ini`** gives deaths too, and the dumps are the
same two deaths:

    patched   c0000005  rip 0x158ecc042  rbp 0x50  r9 0x36  r11 0x2a000000
                        r8 0x2e3ffe5a    first .trace caller 0x14038e6ca
    vanilla   c0000005  rip 0x158ecc042  rbp 0x50  r9 0x36  r11 0x2a000000
                        r8 0x2e32fe5a    first .trace caller 0x14038e6ca

    patched   c0000409  rcx 5  rbx 0x16  r14 0x638f5600  frames 0x1415a0558,
                        0x14159f0be, 0x14159f1b8
    vanilla   c0000409  rcx 5  rbx 0x16  r14 0x638f5600  same three frames

Register for register, on an exe with nothing of ours in it. `r8` differs in the middle
digits only: it is of the form (K << 20) - 422 in both.

What it actually is, as far as the dumps say: the second death is a `__fastfail` with
subcode 5, and the first is a read of a small unmapped address from `.impdata`, the
protector's own virtualised code. The stack under both is the archive reader -- the
`.trace` frames carry `TocInfo::rtv is null` and `Specified num is more than the number of
files(TocInfo::files)` -- with jemalloc beneath. Sider hooks `ReadFile` and redirects it
into livecpk, and the last thing a healthy log shows before the title screen is the intro
movie being read in sixty 0x70000-byte chunks. A race there fits everything observed and
is not something this project can fix.

So `gamerun.py start` retries: `--tries N`, three by default. Two consecutive failures
have not been seen.

The jemalloc reasoning above stands as a description of the dumps and is left as it is.
What does not stand is the conclusion drawn from it, that the patch set corrupts the heap
at startup. The one thing that has ever been shown about these two deaths is that they
happen without us.

## The block constructed 30001 players and destroyed 46193 (2026-09-14)

The startup death turned out not to be ours, which left the heap corruption without a
suspect and the day-243 season death without an explanation. The suspect was in the block
constructor all along, one instruction away from the funclets.

`0x1414b8700` builds the edit block by calling `__ehvec_ctor(base, stride, count, ctor)`
once per array, and `0x1414ba310` tears it down with `__ehvec_dtor` in the reverse order.
The player array is the one that starts at offset 0, so its call takes the block pointer
straight from `rcx` and no `lea` names it:

    0x1414b8787  mov edx, 0x17c        ; stride
    0x1414b878c  mov r8d, 0x7531       ; 30001 records
    0x1414b8792  call 0x14159eff8      ; __ehvec_ctor

Nothing there is an array access, so the attribution walk has nothing to walk out from and
files the count under nothing. The destructor's matching count is at `0x1414ba61f`, and
that one the copy scan did find -- it sits in a function the scan reads -- so it has been
raised to the player cap in every set that carries the mode-copy player patches, all the
way back. The result, in the installed set:

    constructor   0x1414b878c   30001    left alone
    destructor    0x1414ba61f   46193    raised

The block therefore ran the player constructor over records 0..30000 and the player
destructor over records 0..46192. Records 30001..46192 were destroyed without ever having
been constructed: whatever the allocator happened to leave in their pointer fields was
handed to `free`. That is a heap corruption with no bad instruction to find afterwards,
and it happens on every teardown, which is every mode switch and every season roll.

The same asymmetry, smaller, in the regulations: constructor count at `0x1414b87dd` and
destructor count at `0x1414ba5e8`, both still 300 with the cap at 600. Both are now in
`patches/layout.json` as `extra_cap_sites`, along with `0x1414ba61f` itself so that a set
which raises the player cap without the mode-copy patches moves both ends; the fixture
counts at `0x1414b88bf` and `0x1414ba563` are recorded there too, unraised, because the
fixture cap is still 2000 and they are correct as they stand.

`blindspots.py` now checks this third shape as well. It walks each function that calls
`__ehvec_ctor` or `__ehvec_dtor` forward from its `.pdata` start, keeping a register file
of immediates and of block-relative pointers, and resolves `rcx`, `rdx` and `r8` at the
call: `rcx` says which array, and `r8` remembers the address of the instruction that put
the number there. A count that still equals an array's old cap in a set that raises that
cap is reported. It found one more on the first run -- `teams-coaches-players` raises the
player cap but carries no mode-copy patches, so with the constructor fixed it was the
destructor that lagged -- and the whole ladder is clean now.

Whether this is the day-243 death is not yet shown. It is the right shape for it and it is
certainly a bug, which is enough to fix it first and measure afterwards.

## The coach cap that must not be raised (2026-09-14)

A fourth shape the attribution walk cannot file is a bounds check whose limit reaches the
comparison through a register -- `mov r12d, 0x514` and then `cmp edi, r12d`, rather than
`cmp edi, 0x514`. The walk files cap sites by the immediate in the comparison, and there
is no immediate in the comparison. A sweep for it, restricted to functions that call the
owner getter, returns four sites, all of them coaches and all in the same pair of
functions: 0x1414e2532, 0x1414e294f, 0x1414e29ac and 0x1414e2ca0.

They looked like four more missed cap sites. They are not, and the arithmetic is the whole
argument:

    0x1414e2cbf  mov dword ptr [r13 + rcx*4 + 0x1d4c0], edx   ; write a coach id
    0x1414e2cc7  inc word ptr [r13 + 0x1e912]                 ; and count it
    0x1414e2cdb  cmp r10w, r8w                                ; r10 = 1300
    0x1414e2cdf  jbe ...                                      ; full: stop

The object here is not the edit block -- the owner getter is called separately, a few
instructions later, for the block. It keeps a list of coach ids at +0x1d4c0, four bytes
each, with its u16 count at +0x1e912. And `0x1d4c0 + 1300 * 4` is `0x1e910`: the table
ends two bytes before its own counter. The 1300 is not a bounds check that happens to
agree with the array size, it is the size of the table, and raising it writes coach ids
over the count and over whatever follows.

So all four are recorded in `patches/layout.json` as coach `hold_sites` with that
reasoning, and `blindspots.py` now reads `hold_sites` and treats them as covered. A cap
that is structural rather than defensive is not a miss, and leaving it reported forever
would bury the next real one.

Nothing was regenerated for this: the four sites are not in `attrib.json`, so no set was
ever emitting them, and the generated output is unchanged.

## The 750 at block+0x16705a8 is a table's size, not a team bound (2026-09-14)

A 750-entry table at block+0x16705a8 with a 0x10 stride had been noted as a per-team side
table that sits above the season calendar and cannot grow -- a suspected wall. Both halves
of that reading are wrong, and the function that settles it is 0x140b10944:

    0x140b10a86  cmp dword ptr [r15 + 0x1673488], edi   ; the live count
    0x140b10a8d  lea rbp, [r15 + 0x16705a8]             ; the table
    0x140b10a94  jbe out                                ; i >= count: done
    0x140b10a96  cmp edi, 0x2ee                         ; i vs 750
    0x140b10a9c  jb  real                               ; over it, fall back to entry 0
    0x140b10aa5  shl rdx, 4                             ; stride 0x10
    0x140b10aba  cmp edi, dword ptr [rbp + 0x2ee0]      ; the same count, reached through rbp

`0x16705a8 + 750 * 0x10` is `0x1673488`: the table ends exactly where its own counter
begins. So the 750 is the size of the structure, not a bounds check that happens to agree
with the team cap, and raising it writes entries over the count -- the same shape as the
coach id list at +0x1d4c0 above. And the loop is driven by that count, not by a team row,
so it is not a per-team table either.

There are 93 references to the offset in `.trace` and none of them appear in
`attrib.json`, because the walk files an access against an array and this one lands above
every array it knows. It is recorded as a teams `hold_site` so the next sweep that notices
a 750 does not read it as a missed cap.

Nothing here moves: the -upper sets relocate the belt and the match table, and everything
from the season calendar at 0x16038a8 upward stays where it is.

## What a season actually costs, and which of its limits can move (2026-09-14)

Planning 40-50 new leagues needs the season's budget written down, because the three
numbers behave differently and only one of them is a cap we can raise.

**The calendar is exactly 365 days and cannot be extended in place.** It begins at
block+0x16038a8 with a 0x2c4 stride, and `0x16038a8 + 365 * 0x2c4` is `0x1642a1c` -- which
is the current-day field. The array ends where the field that indexes it begins, the same
shape as the coach id list and the table at +0x16705a8.

**The per-day match list is 280 and that 280 is structural.** A day record is a
0xffff-terminated list of u16 match ids at +0x00 taking 0x230 bytes (280 of them), the
count at +0x230, and 18 event slots of 8 bytes at +0x234: `0x230 + 4 + 18 * 8` is `0x2c4`,
the stride exactly. Raising the per-day cap therefore means a wider day record, which
means relocating the calendar and rewriting every access to it -- not a cap patch. The
practical route is the one the generator already takes: spread leagues across the week
with `--date-keys` / `--date-offsets`. The season just created has 233 matches on its
busiest day, 47 short of the cap, with 0 days full.

**The match table is the one that moves.** It is `rec596`, shipped at 13000 records and
raised to 26000 in the upper set, and it is relocated to the grown block end, so it can go
further. The season just created uses **21010 of 26000** with the current world.

That last number is the Phase 6 arithmetic. A league of 20 clubs playing everyone twice is
380 matches a season; 45 such leagues is 17100 more, which would want roughly 38000
records. So the match table has to roughly double again before the new leagues are added,
and the daily lists have enough total room (365 * 280 = 102200 slots) that the constraint
there is clustering, not capacity.

## A screen reader that always returns an answer is not a screen reader

`screen.bartab` reads which of the hub's six menu tabs is drawn white by taking the
brightest of six boxes along one row. It cannot fail: it always returns a tab number.
`screen.parkbar` was built on it, and `seasonrun.park` was built on `parkbar`, so the
whole season walk rested on a function that answers "which tab" even when no tab is on
screen.

The Diary is where that bill came due. It opens with a green header block sitting exactly
where the menu bar sits, so the six boxes read `[66.7, 23.0, 23.0, 23.0, 23.0, 23.2]`,
the brightest is the leftmost, and `bartab` returned 0 -- Forward Time. `parkbar` saw the
tab it wanted, pressed nothing, and returned success. `park` reported that the hub was
ready. Every step of the forty-step stall ladder then walked a Forward Time menu that was
not there, and the season sat on day 212 for forty steps and zero moves while each step
believed it had worked.

The fix is a check that can say no. Two rows of the hub's header band -- at 3% and 9% of
the window height, sampled across the middle 90% of its width -- are pure black on the
hub and on nothing else: under 3 on every hub capture in the archive, 23 or more on the
Diary, the results table, the dialogue screens and the press conference alike. That is
`screen.onhub`, and `bartab` now refuses rather than guesses.

**The second check is the one that protects the save.** `esc` is the only key measured
that leaves the Diary; z, enter and the pad's circle were each timed against it and none
of them move it. But `esc` on the hub opens *"Return to Top Menu? Unsaved data will be
lost."* -- and that dialog does not cover the header band, so `onhub` still says yes. A
`parkbar` running under it would read a tab, press `right`, and move the answer from No to
Yes, and the confirm after that would throw the season away. So `screen.modal` reads the
centre panel -- over 120 mean grey when a dialog is up, around 50 on the bare hub -- and
`bartab` refuses while one is open. `park` now reads the screen before choosing what to
press: a dialog gets `enter` (the highlighted answer, which on that dialog is No), the
bare hub gets `z`, and anything else gets `esc`.

## The region cap is three caps, and only the first one is the one-byte patch

Section 9 above says regions go 29 -> 32 for one byte and stops there, with "past 32 you'd
have to widen a 5-bit field in the record format, which is a different order of problem."
That sentence was true and unhelpful. Here is the measurement behind it, because 32 is not
where this actually ends.

**Cap 1 -- 29, and it is a comparison.** `cmp al, 0x1d` at `0x1414f839a`. One byte to `0x20`
and the parser accepts everything the field can encode. Already documented.

**Cap 2 -- 32, and it is the record format.** Not a design limit, just a full dword. dword0
of the `CompetitionRegulation.bin` record is packed to the bit:

```
1414f83e4  movzx edx, word [rax]        and 0x1ff    ; bits 0..8    -> setter 1414c9eb0
1414f83f4  mov   edx, [rax]  shr 9      and 0x1ff    ; bits 9..17   -> setter 1414c9c80
1414f83c9  mov   ecx, [rax]  shr 0x12   and 0x1ff    ; bits 18..26  -> setter 1414c9f30
1414f8390  mov   ecx, [rax]  shr 0x1b   and 0x1f     ; bits 27..31  -> region, 1414c9c10
```

9 + 9 + 9 + 5 = 32. There is no bit 26 to borrow: it is the top of the third field.

But the region does not have to live in dword0. Across all 253 regulation rows in the
installed set, **byte `+0x01` is zero in every row** (so are `+0x05` and `+0x07`), and the
parser never reads it -- bits 8..15 are the unused high end of the two 9-bit fields below.
Repointing the four instructions at `0x1414f8390` to `movzx ecx, byte [rax + 1]` gives the
region an 8-bit source with room to spare, and `cmp al, 0x1d` becomes a bound against the
runtime instead of against the encoding. `Competition.bin` has the same headroom from the
other side: byte 3 carries the region in bits 3..7, and bits 0..2 are zero in all 130 rows.

**Cap 3 -- 64, and it is the runtime object.** This is the one that actually binds. The
region lives at `+0x30c` bits 7..12 of the runtime regulation, six bits:

```
1414c9c10  and dword [rcx + 0x30c], 0xffffe07f   ; clear bits 7..12
1414c9c1a  and edx, 0x3f                          ; six bits in
1414c9c1d  shl edx, 7
1414c9c20  or  dword [rcx + 0x30c], edx
```

One setter, and **30 getter sites** reading it with the same `shr 7 / and 0x3f` idiom:

```
140acce1f 140acd68f 140b6a856 140b81ba3 140b82750 140c6bdac 140c6cd88 140c6ce00
140eada89 140f1f641 140fa1bb1 141264a5f 141264b7d 1414cce96 1414cdb5d 1414ce2d4
1414ced48 1414cee9d 141541288 141541639 141542dd9 141542e6a 1415430a8 1415432a8
141543499 141543898 141543e65 141544ff8 141545088 141545528
```

Its neighbours in that dword are bits 0..6 (from record `+0x0b`) and bits 13..16 (from
record `+0x0a`), so widening the field past six bits means moving a neighbour as well as
rewriting all 31 sites. That is the same shape of job as the 87-site `cmp .., 0x12c` work,
and it is the next order of problem -- not this one.

So the ladder is 29 -> 32 (one byte) -> 64 (repoint the parser read, no table moves, nothing
downstream touched) -> beyond (31 sites plus a field relocation).

**And none of that is the real work.** Region *names* come from a 24-record table at
`0x1426770c0` (`{u64 key_ptr; u32 id; u32 pad}`) walked with `cmp ecx, 0x18`. It contains
none of the free ids and has no fallback, so a new region on any id above the shipped 24
renders with no label at all. Whatever the numeric cap, that table has to be relocated and
extended before a new region is usable in the UI. The cap is arithmetic; the name table is
the deliverable.

All of the above is static analysis of the installed exe and data. None of it is tested in
game yet.

### The region name table, and why it is smaller work than it looked

Section 9 said the name table was never found and that a new region "may well render blank".
It is found, and the shape of the fix is smaller than that warning implied.

The table is 24 records of 16 bytes at `0x1426770c0`, each `{u64 key_ptr; u32 id; u32 pad}`,
and the strings sit immediately after it in the same part of `.rdata`:

```
 0  compeCategory-interClub   id  1     12  compeCategory-swissConfederation  id 10
 1  compeCategory-event       id 26     13  compeCategory-turkey              id 27
 2  compeCategory-belgium     id  8     14  compeCategory-PEU                 id 22
 ...                                    23  compeCategory-thailand            id 28
```

The whole lookup is one loop, and it has exactly one caller:

```
140acd478  lea r10, [rip + 0x1ba9c49]   ; 1426770c8 -- the id field of record 0
140acd47f  lea r11, [rip + 0x1ba9c3a]   ; 1426770c0 -- the table base
140acd486  xor ecx, ecx
140acd490  cmp dword ptr [rax], edx     ; is this record's id the one we want?
140acd496  add rax, 0x10
140acd49a  cmp ecx, 0x18                ; 24 records
140acd49d  jb  0x140acd490
140acd49f  jmp 0x140acd4aa              ; fall through with rbx untouched -> no key at all
140acd4a6  mov rbx, [r11 + rax*8]       ; hit: the key pointer
```

So extending it is three edits, not a research project: relocate the table, fix the two `lea`
displacements, and change one `cmp ecx, 0x18`. The count is an imm8, so anything up to 127
fits without changing the instruction's length. There is room to put it: the same `.rdata`
section holds a run of **28858 zero bytes at `0x1426d1f1d`**, which is 28 times what a
64-record table needs.

The part that genuinely is a separate problem is the label text: a key like
`compeCategory-turkey` is looked up in the game's `.str` system, so a brand new key needs a
new text entry. But that problem can be sidestepped entirely, and this is the useful bit --
**a new region's record can point at a key that already exists.** Football Life already ships
three generic buckets (`PEU` other Europe, `PLA` other Latin America, `PAS` other Asia), and a
new region pointed at one of those renders with a real label immediately, with no text work
at all. Unique names are then an improvement to make later rather than a precondition.

Taken with the three caps above, raising regions to 64 is: one byte for the parser bound, a
repointed field read so the encoding stops at the record rather than at five bits, a
relocated 16-byte-per-record table, and two displacements. None of it is the "different order
of problem" the earlier note implied. It is still untested -- none of this has been run.

### 0x1484ed4c0 named: the sky bake, on the main thread, leaving a press conference

The store at `0x1484ed4c0` has been in this file for a while as an `.impdata` address with a
wild `rcx`. Two things were missing: what the game was doing, and which thread was doing it.
Both are now known, from two dumps sixteen hours apart plus the last frame the season walk
captured before the process went away.

**What was on screen.** The pre-match press conference before the *first match of the season*
-- day 236 of a season that started on day 212. The stack agrees: `1403ff4aa` is the flow
scheduler, and its string pool holds `MovieMain`, `flow`, `system_task`, `match_end` and
`SE_WIPE_IN_01`, the screen-wipe transition. So the crash is in the load that follows a cut
scene, not in the cut scene and not in idle calendar advance.

**Which thread.** The main game thread, not the renderer. This corrects an assumption that
had been carried for a while. `140318b06` on the faulting thread carries
`SetGameFrameWaitType`, `FoxGameFrame`, `__game_main`; the renderer is a separate and
perfectly healthy thread whose own frames read `MainRender`, `MainViewport`,
`Fox/Scripts/Gr/init.lua`. The thread that died is the one that owns the load, so the
"renderer trips over the simulation's corrupted pointer" reading does not apply.

**The chain, outermost to innermost**, every name from its function's string pool:

```
140318b06  SetGameFrameWaitType, FoxGameFrame, __game_main
14036c7f6  the Lua VM
1402ba073  FoxCore, DataBody, dataBodySet
14193d974  StartSkyCapture, ClearSkyCoefficients, FixSkyCoefficients
14193eb6c  TppAtmosphere, rayleighScatteringCoefficient, capturePosition, useBakedData
1416c3163  SH_LIGHTING
14038e4e0  jemalloc
1484ed4c0  mov dword ptr [rcx], r8d      <- faults, storing zero through a wild pointer
```

That is the atmosphere and spherical-harmonics lighting bake that runs when a scene is
brought up -- stadium setup -- driven from Lua through FoxCore.

**One bug, not several.** Across the two dumps every register is byte-identical except `rcx`
and `rsp`, and the call chain matches frame for frame from `14038f23e` outward. `rcx` is
`0x1f66ded41` in one and `0x1edad21c1` in the other: both around 7.9 GB, both *unaligned*.
That is the shape of a corrupted heap value rather than a null, a small bad offset or an
index off a good base, and the jemalloc frames sitting between the sky bake and the fault
mean the block may already have been damaged before this path touched it.

**fl26nullguard.lua does not cover this.** The guarded site `0x141fea5ba` appears nowhere in
either dump -- not on a stack, not anywhere in memory. It is a neighbour rather than a
relative: its function starts at `0x141fea5b0` and its four callers all sit in the same
`0x14179xxxx` cluster that the faulting thread also touches at `1417acf80`, but that is a
different function on a different path. The existing guard would not intercept this.

**What is still unknown**, stated plainly so nobody re-derives it: who produced the bad
`rcx` (it is made inside the protector VM and is not on the stack), and which data item was
being processed. The entire 5352-byte faulting stack region of both dumps contains no
printable string at all -- no club, no stadium, no competition, no file path. The
identification stops at the subsystem.

One method note worth keeping: the season walk's own stall screenshots answered the "what
was on screen" question that the dumps could not, and they were already on disk. The walk
was also making things worse -- its third stall step walks Forward Time to `Skip Match` and
confirms, which was being done while the press conference was still up, and that is a way to
start a live match by accident. The step that actually answers that screen now runs first.

## The twelve bits above the abilities, and the squad of goalkeepers

The ability block runs from +0x1c to +0x37.  That is 27 bytes, 216 bits, and the 34
six-bit fields this project decodes account for 204 of them.  The remaining twelve were
treated as slack, and `maxsquad.setfields` packed only the fields and wrote the result
back -- which zeroed those twelve bits on every single write.

They are not slack.  Bits 6..9 of that tail, counted from the top of the fields, hold the
position a player is registered at:

    position = (int.from_bytes(rec[0x1c:0x37], "little") >> (34 * 6 + 6)) & 0xf

     0 GK   1 CB   2 LB   3 RB   4 DMF   5 CMF   6 LMF
     7 RMF  8 AMF  9 LWF  10 RWF  11 SS  12 CF

Across the 3212 shipped players that yields 426 goalkeepers, 581 centre-backs, 206 left
and 220 right-backs, and 428 forwards -- three or four keepers a club, which is exactly
right.  It was read off the Game Plan screen: 27 of AC Sparta Prague's players carry a
position badge there, and every one of them agrees with this decode.

Zeroing it set every player to 0, and 0 is goalkeeper.  That is the whole explanation for
a season the managed club could never win.  Three photographs of one screen settle it:

    maxed data                  the bench is twelve GKs, cohesion 33
    Player.bin.premax restored  RB DMF CMF CMF CMF AMF GK AMF AMF RWF LWF RWF, cohesion 42
    one raised field per player GKs again, and the ratings collapse to 40

The third is the one that named the culprit.  If a particular ability had been carrying
the position, raising one field per player would have broken one player.  It broke all of
them and dropped their ratings to the floor, which only a write that damages the block
itself can do -- and a round-trip check then showed `fields()` followed by `setfields()`
changing 386 of 400 shipped records.  With the tail preserved it changes none.

Two things follow.  A club could never be strengthened: every attempt turned it into
eleven keepers playing out of position, which is also why boostclub's Real Madrid
transplant looked like it had not helped -- it had, and the maxing undid it.  And the
"six goalkeeping fields" rule in maxsquad, derived to stop exactly this, was treating a
symptom; it stays because those fields really are position-bearing ratings, but it was
never the reason squads turned into goalkeepers.

## The second crash that ends a season, and why this one is fixable

Driving a season now fails in two different places, and until 15 September 2026 only one of
them had a name.  The known one is 0x1484ed4c0: it fires while a season is being generated
or a match is being loaded, it lives in `.impdata` -- the protector's virtualised code --
and its stack holds nothing but sky and lighting.  Three attempts to create a season on the
morning of the 15th died there in a row, at 06:34, 06:44 and 06:52, all with the same fault
offset, which is what that crash has always looked like: a probability, not a condition.

The second one is new and is the opposite kind of bug.  It killed a season in progress at
day 257 -- mid-September of the second season, after forty-two days had gone by without
trouble -- with fault offset 0x00000000fc9238, that is **0x140fc9238**, and that address is
in `.trace`, the game's own readable code.  The dump says the access violation is a read of
`0x3c0`, which is not a corrupted pointer at all; it is a null one, plus a field offset:

    140fc9210  push rbx/rbp/rdi/r14/r15; sub rsp, 0x30
    140fc921c  movzx ebx, dx              ; the id this call is about -- 0x405 in the dump
    140fc921f  mov   rdi, rcx
    140fc9222  call  0x1414b6a60
    140fc922a  mov   r15, [rax + 0x48]
    140fc922e  call  0x141579b90          ; look the id up
    140fc9235  mov   r14, rax
    140fc9238  cmp   dword ptr [rax + 0x3c0], ebp     <-- rax is 0

The lookup at 0x141579b90 returned null for id 0x405 and the caller never checks.  Every
register in the dump agrees: rax 0, rbp 0, and rcx/rbx/rsi/r8 all holding 0x405.  What is
read at +0x3c0 is a count -- the code immediately compares it against 0x30 and indexes
twenty-byte entries with it -- so the object is a list of at most 48 somethings hanging off
whatever the id names.

That makes this crash the same shape as 0x141fea5ba, which `fl26nullguard.lua` already
handles with a code-cave trampoline: test the pointer, and when it is null take the path the
function itself takes when there is nothing to do.  Here that path is already written and
five bytes away -- `jbe 0x140fc93c6`, the branch taken when the count is zero.  A guard has
not been built yet; what is established is that it can be, which is more than can be said
for 0x1484ed4c0.

One lead was checked and closed.  The date-spread stub in `datecave.py` takes every
regulation id above 175, and 0x405 is 1029, far outside the 256-entry table it reads -- but
the stub bounds-checks that table (`cmp eax, 256; jae empty`) and hands such an id the same
"no calendar" answer as an unlisted one.  The id in the crash is not a regulation id being
read out of our own table.

## Game Plan walk works; loading a save loses the club (2026-09-15, afternoon)

**tools/gameplan.py** walks hub -> Team Management -> Game Plan -> Team Sheet/Edit Position,
presses R3 (`Auto Lineup Select`) once through the virtual pad, photographs the sheet before
and after, and returns to the hub with the bar parked on Forward Time.  Verified on a fresh
season (FL 0741, day 212): no dialog, the eleven changed at once (LMF 89->96, AMF 89->96,
RMF 85->95, LB 86->96, RB 85->97), the cohesion badge went 41 -> 50, and the prompt strip
turned into `R3 Reset` -- a second press in the same visit undoes it, so the tool presses
once.  A second walk after two Returns found the badge still at 50: the pick persists
without any confirm step.

Screen readers (measured): the Team Management menu's first row reads green 11.8 ahead of
red when highlighted; the Game Plan family shares a teal header (g-r 86) *and so do its Help
pages*, which cost twenty minutes of pressing buttons at a help topic -- the pitch (green
fraction of 0.30-0.53 x 0.25-0.70) is what the help pages lack.  Game Plan vs Team Sheet:
the teal arrows icon at 0.39-0.45 x 0.78-0.84 reads g-r 26.2 on Game Plan and 0.0 on the
sheet.  The white title strip does not separate them (help pages are white too).  The
keyboard's `z` does not leave the Team Sheet (four presses, no movement); the pad's circle
does, every time.

**Pad button table.**  The game reads a virtual X360 pad by DirectInput button *index*
through its PlayStation table, so the names are shifted: X360 A=square, B=cross, X=circle,
Y=triangle, LB=L1, RB=R1, Back=L2, Start=R2, LThumb=SHARE (opens Help), RThumb=OPTIONS;
L3/R3 are unreachable from an X360 pad.  A virtual DualShock 4 (`FL26_PAD=ds4`, bound with
`padbind.py --to "wireless controller"`, game restarted) maps 1:1 and R3 works.  The
earlier note that a DS4 crashes the game was already retracted (the same 11 s startup death
recurs with the X360 pad).

**Loading a save loses the club -- not a sacking.**  Decisive test: the fresh FL 0741 season
above (real eleven, cohesion 41) was saved to slot 2 at 14:40 and loaded with seasonload.py
at 14:50.  After the load: Standings empty, no date strip, no club badge, Game Plan shows
eleven nameless 0-rated players, the hub news reads "newly signed manager of FL 0001" and
"New manager, , talked" (empty name).  Both saves that were read as "we had been sacked"
(handover, lines 108-110) were this state.  nullguard3 guards exactly the read of the
schedule (`d_schedule_`) that comes back null on load, so the crash it suppresses and the
empty club are one fault: the load path does not find our club's schedule/league.  Cause
still open; the next test is whether a stock club survives save -> load.

**nullguard3 vs season generation, corrected.**  Three New-season runs in a row died at
generation with nullguard3 on and the next succeeded with it off, but the fault was
0x1484ed4c0 -- the intermittent sky-bake heap corruption already documented above as
present on the unpatched exe -- and it hit again today with nullguard3 off (dump
FL_2026.exe.12020.dmp, 15:01), then passed on retry.  So nullguard3 is not shown to break
generation; `tools/guard3.py` still keeps it off for seasonnew.py and on for seasonload.py
(the load cannot run without it, and generation gains nothing from it).

### Save -> load: broken under our set, clean on the stock game (2026-09-15, evening)

Three chains, each: New season -> photograph the Team Sheet -> Save slot 2 -> Load slot 2 ->
photograph again.  The league picked is the first on the list (`FL26_LEAGUE_DOWNS=0`, the
Belgian league, RSC Anderlecht) so the club is a stock one.

| exe / data                                   | fresh sheet             | after load                          |
|----------------------------------------------|-------------------------|-------------------------------------|
| our set + our cpk.root, club FL 0741 (14:50) | real eleven, cohesion 41| nameless 0s, no club, "Jorge Jesus" |
| our set + our cpk.root, Anderlecht (16:22)   | real eleven, cohesion 35| nameless 0s, no club, "Jorge Jesus" |
| set `none` + cpk.root off, Anderlecht (16:55)| real eleven, cohesion 35| identical: Anderlecht, Figo, cohesion 35 |

So the load path is not broken by our club ids -- a stock club loses everything the same
way -- and it is not broken in the game as shipped.  It is broken by our patch set, our data
root, or the two together; the bisection (patches on / root off first) is running.  What the
loaded state looks like: the followers count survives (33,640 for Anderlecht, 9,229,632 for
FL 0741), the manager becomes "Jorge Jesus", the club news names "FL 0001" and "FL P00001",
the eleven is eleven empty records.  That reads like the block coming back with its team
and player tables empty or misaligned rather than a single lookup failing.

Side findings: a club-coloured hub header (Anderlecht's purple) defeats `screen.onhub`,
which wants the band black; the reliable signature is the six tab labels -- each box of the
bar row holds more than 3% of pixels brighter than 110 on every hub (black, purple, loaded)
and at least one box is empty on every other screen measured.  `gpscreen` likewise wants
the teal Game Plan header, which a stock club paints in its own colour.  A stock club's
press conference has multiple-choice questions that keyboard Enter does not answer; the
pad's cross does.

### Save -> load bisection: the save's match table stops at 13,000 (2026-09-15, night)

Same chain as above (New season -> Team Sheet -> Save slot 2 -> Load slot 2 -> Team Sheet),
full patch set on, the data root varied.  A "root" here is a livecpk directory put on
sider.ini line 22; `_FL26Bis1` holds only E39x793's Team/Player/PlayerAssignment tables,
`_FL26Bis142` E42's tables filtered to the shipped competitions plus one FL league
(cid 142, 14 clubs), `_FL26Cid130` one FL league at cid 130.

| patch set | cpk.root                                 | leagues added | after load |
|-----------|------------------------------------------|---------------|------------|
| full      | off                                      | 0             | intact     |
| full      | `_FL26Bis1` (teams/players only, 1536)   | 0             | intact     |
| full      | `_FL26Cid130` (one league)               | 1             | intact     |
| full      | `_FL26Bis142` (one league)               | 1             | intact     |
| full      | `_FL26E42` (588 clubs)                   | 42            | no club    |
| full      | `_FL26E39x793` (793 clubs)               | 39            | no club    |

The patches are innocent, so are the team and player tables and the competition ids; what
breaks it is the number of leagues, i.e. the number of matches a season generates.  Forty
leagues of 14-20 clubs are ten to fifteen thousand matches on top of the shipped calendar.

Why that number matters: a Master League save is not the live block.  Saving fills a
"mode copy" (layout.json `copy`, variant A: constructor 0x141401060, block -> copy fill
0x141401c10, copy -> block fill 0x1414016b0 on load, allocated in 0x141400b10 with object
size 0x181f894).  The copy's match table (rec596, stride 0x254) lives at copy+0x329b00
with room for 13,000 records, and three sites keep it there while the live block's table
was raised to 26,000: `mov ebx,0x32c8` at 0x14140115f (constructor count), `cmp
edi,0x32c8` at 0x141401e07 (save loop bound, a layout.json hold_site) and `cmp ebx,0x32c8`
at 0x141401856 (load loop bound, hold_site).  The calendar copy starts at copy+0xa8d4a0 =
0x329b00 + 13000*0x254, so there is no slack: every match past 13,000 is dropped from the
save, and a loaded season whose fixtures point at them comes back as the empty state
photographed above (no managed club, nameless eleven, the schedule strip that nullguard3
guards read as null).  A season with one added league stays under 13,000 and round-trips.

The fix is the treatment the player table already got inside the copy
(`patchset.copy_player_patches`): grow the copy by 13000*0x254 = 0x7639a0 bytes, shift
every copy offset at or past 0xa8d4a0, raise the object size constants and the three
13,000 sites to 26,000.  Variant B of the copy (constructor 0x140afd660, 12,360 records,
loops 0x1413feb8c/0x1413fef4c) is a different format and is left alone unless it turns out
to be the live one.

Also from tonight: after a generation crash (0x1484ed4c0) the next seasonnew attempts
reported "the game window is not there" within seconds of gamerun saying "running", with
no dump and the process alive -- the window simply was not up yet.  seasonnew.boot now
waits for it.

### The copy grows one table at a time: matches fixed, teams/coaches/regulations next (2026-09-15, night)

The mlcopy set (rec596 13000 -> 26000 inside copy A) was generated, verified by the module
("applied all 2665 patches") and driven through the whole chain on `_FL26E42`: new season,
Team Sheet, Save slot 2, Load slot 2, Team Sheet again.

What changed: the save file grew from 20.1 MB to 27.7 MB, and the loaded hub draws its
schedule strip again -- four fixtures with dates and kick-off times where every earlier
load had a blank band.  That is the first part of the season surviving a round trip, and
it confirms both the mechanism (the save is written from the mode copy, not the block) and
the method (grow the copy's array, shift every field above it, raise the three counts).

What did not change: the club.  The loaded season still reads "FL 0001", manager "Jorge
Jesus", standings empty.  `layout.json` `copy.caps_from_ctor` says why -- rec596 was not
the only array the copy keeps at the pre-growth cap:

| array       | copy cap | block cap | stride | copy offset |
|-------------|----------|-----------|--------|-------------|
| teams       | 750      | 1600      | 0x690  | 0x50        |
| coaches     | 1300     | 2600      | 0x258  | 0x133a30    |
| regulations | 300      | 600       | 0x314  | 0x1f2110    |
| fixtures    | 2000     | 2000      | 0x208  | 0x22bc80    |
| rec596      | 26000    | 26000     | 0x254  | 0x329b00    |

Every team record past the 750th is dropped from the save, so the managed club -- ours are
far above that -- comes back as the first club in the file, its coach as a stock name and
its league's regulation as nothing.  The remedy is the same treatment applied to the three
remaining arrays, with the growths composing in offset order: teams 850*0x690 = 0x15ca50,
coaches 1300*0x258 = 0xbe720, regulations 300*0x314 = 0x39b30, on top of the 0x7639a0 the
matches already take.  fixtures is held at 2000 in the block and stays held in the copy.

Also settled tonight: three season generations in a row crashed at 0x1484ed4c0 under the
new set and the control run with the old set passed first time, which looked like the set
causing it.  It was not.  A static audit of all 106 mlcopy sites found none of them on a
path that runs before the first save (copy A is constructed only by the two save flows;
none of the patched functions is referenced indirectly anywhere in the file), and the very
next run with the same set generated a season first time.  The crash remains the known
intermittent one.

**A third wall, flagged not yet grown: 80 competitions.**  The copy carries an 80-entry
competition array at copy+0x1049b3c, stride 0x15fc, and unlike the others this one is a
block wall first: the matching block array is at block+0x1719b84 with the same stride and a
cap of 80 enforced in 0x1414bc960, where an index of 80 or more returns record 0 instead.
Our roots run to roughly 130 competitions, so anything this array holds -- standings and
per-competition records are the likely content -- is unavailable above the eightieth.
Growing it needs a block-side relocation of the kind rec596 got, not just a copy shift, so
it is left for a later pass.

**The copy does not carry the per-match flag run.**  `arrays.matchflags` (13,000 bytes,
one per match, grown with rec596 in the block) has no counterpart in copy A: there is no
0x32c8 immediate in the copy code outside the three rec596 counts, no gap in the copy's
45-field map of 0x32c8 or 0x6590, and the fills walk rec596 record by record without
touching a flag run.

**An overrun that was there all along.**  The block -> copy loops for teams, coaches and
regulations are bounded by the block's own count fields (0xd0bcec/f0/f4), not by
constants.  With those counts raised and the copy still at 750 records, saving wrote up to
1,600 team records into a 750-record area -- into the copy's coach array and past it.  So
the copy was not merely truncating the save, it was corrupting its own tail on every save.

### Save -> load works: a 793-club season survives the round trip (2026-09-15, 21:17)

The full `mlcopy` set (2,688 patches), our own root `_FL26E39x793` (39 added leagues, 793
added clubs), our own club FL 0741, `FL26_LEAGUE_DOWNS=45`.  New season -> Team Sheet ->
Save slot 2 -> Load slot 2 -> Team Sheet.  The season generated first time.

Before saving: FL 0741, manager Luis Figo, cohesion 41, eleven named players rated 81-99.
After loading: the same eleven, the same ratings, the same cohesion, the same club, the
club's own follower count, and four fixtures with dates and kick-off times at the club's
stadium.  The two Team Sheet captures are pixel-identical apart from one line.

This is the first Master League season on our data to survive a save and a load.

Two things are still missing, both small against that and both pointing at tables the copy
does not carry rather than at the copy's caps:

  * the manager's name.  The loaded club's header shows "FL 0741" with no name under it
    where the fresh season showed "Luis Figo", and the hub's news reads "New FL 0741
    manager, ,".  The coach record comes back (the club has a manager, the game does not
    fall back to a stock name any more) but the name string does not.
  * the standings column is empty.  That is the 80-competition wall documented above: our
    roots run to about 130 competitions and the block returns record 0 for any index of 80
    or more, so the league the club plays in has no standings object to show.

**nullguard2 is now in sider.ini.**  The mid-season guard (null-check at 0x140fc9238, the
competition lookup that returned null for id 0x405 and killed a season at day 257) was
written on 12 September but never loaded.  It is installed as
`modules/fl26nullguard2.lua` and listed in sider.ini next to the other two.  A boot with
the full configuration applies all four modules: the mlcopy set's 2,688 patches, nullguard,
nullguard3 and nullguard2.  The original sider.ini was kept as `sider.ini.before-nullguard2`.

### Correction: the 80-entry array is not competitions, and the standings wall is elsewhere (2026-09-15, 22:00)

The entry above called `copy.competitions80` an 80-slot competition array and blamed the
empty standings on it.  That was wrong, and it was wrong in the way guesses usually are:
this file recorded it honestly at first -- "80 of something 5,628 bytes wide; competition
seasons is the guess" -- the guess became the label `competitions80` in `copylayout.py`,
and the label was then read back as a fact.

What block+0x1719b84 (80 x 0x15fc) actually holds, from its constructor 0x1414de7b0 and
its allocator 0x140ef3c10: a pool of per-player records.  Each has an 8-byte key at +0,
a bitfield at +0x10 whose bits 18-27 count entries and stop at 100, a date at +0x14, and
100 sub-entries of 0x38 from +0x18 (0x18 + 100*0x38 = 0x15f8).  The allocator finds the
slot whose key matches the global empty key, then fills the header from a player record
through the player lookup at 0x1414bc9a0.  Its consumers are the Master League menus
around the strings `offer`, `history`, `hall` and `title`.

It is not indexed by competition id anywhere.  The accessor 0x1414bc960 has twenty
callers and `edx` is a slot counter bounded by `cmp ..., 0x50` at every one; the other
path, 0x1414bc8e0, is a linear search by key over the same eighty slots.  And the shipped
game settles it on its own: `docs/competition-slotmap.txt` lists 92 distinct competition
ids reaching 141, with standings that work, which no 80-competition cap would allow.

Where the standings do live -- and this file already named the accessor months ago at the
top: 0x141579b90 -> 0x14158b6f0 -> 0x14158dfc0 work on the object returned by
0x1414b6a60() at +0x78, not on the edit block at +0x48.  Inside it, 0x14159ebf0 linearly
searches a table of 100 entries of 0xb4 keyed by competition id (`cmp edx, 0x64` at
0x14159ec1d); each entry holds up to twenty phase slots (`cmp ecx, 0x14`), which index a
table of 600 entries of 0x187c at +0x4650 (`cmp eax, 0x258` at 0x14158df83) -- the
per-phase standings tables themselves.  With roughly 92 shipped competitions and our 39
leagues we sit near 131, above that 100-entry table, and the 600 phase tables are a second
bound behind it.

That object is neither the edit block nor the mode copy, so nothing in `layout.json`
models it yet: it needs its own allocation, base and cap walk before a single byte is
patched.  Note also that 0x141579b90 is the same lookup `nullguard2` guards, which returned
null for id 0x405 and killed a season mid-run -- a null standings object for a competition
past the hundredth is exactly what that guard was papering over.

### The standings object, measured: 100 competition entries and 600 phase tables (2026-09-15, late)

The correction above named the accessor chain and stopped.  This is the object it lands in,
read out of the unpatched exe at `<game folder>\FL_2026.exe`.  Everything with an address
below was disassembled; anything called an inference says so.

**The chain, corrected in two places.**  `0x141579b90` is not a function, it is a five-byte
`jmp 0x14158b6f0`.  `0x14158b6f0` calls `0x14158dfc0` and, on a non-null result, tail-jumps
into `0x1414ff0c0`.  `0x14158dfc0` does two things before it ever touches the 100-entry
table, and the first one matters:

    14158dfcc  lea rcx, [rsp+0x38]
    14158dfd1  call 0x1415451a0              ; competition id -> the object's key
    14158dfda  cmp ecx, [rip -> 14351ae28]   ; the "no competition" sentinel
    14158dfe0  jne 14158dfea                 ; equal -> return null
    14158dfea  call 0x14159ebf0              ; the 100-entry search
    14158dff5  call 0x14158df30              ; the phase-table search

`0x1415451a0` walks the **edit block's** regulation array (`block + 0xc12e9c`, stride
`0x314`, count at `block + 0xd0bcf4`) for the competition id, then calls `0x1414bb000` and
returns the `u32` at `+0x80` of the regulation record it finds.  So **the 100-entry table is
not keyed by competition id**: it is keyed by that `+0x80` field, and a competition with no
regulation record returns the sentinel and a null standings object before the 100 is even
reached.  `0x1414bb000` carries a regulation cap of its own -- `cmp eax, 0x12c` at
`0x1414bb045` -- and that site is already in `patches/attrib.json` as a `regulations` cap
site, so our set raises it to 600 along with the other 106.

**The object.**  `0x1414b6a60` returns the global at `0x143705e10`; `+0x48` is the edit
block, `+0x78` is this one.  It is allocated in one piece by `0x1414b62c0`:

    1414b62cb  mov edx, 0x3a2ef0         ; the whole object, 3,813,616 bytes
    1414b62d5  call 0x1403fb410          ; allocate
    1414b62da  mov [rbx+0x78], rax
    1414b62e5  mov r8d, 0x3a2ef0         ; memset 0
    1414b62fc  jmp 0x1414fd680           ; construct

and its constructor `0x1414fd680` lays it out, each member with its own initialiser:

| offset | what | built by |
| --- | --- | --- |
| `+0x000000` | 100 entries of `0xb4` -- the competition table | `0x1414fd4e0` |
| `+0x004650` | 600 tables of `0x187c` -- the per-phase standings | `0x1414fd460` |
| `+0x39a5f0` | `0x300` bytes, not identified | -- |
| `+0x39a8f0` | `0x100` bytes | `0x141400e50` |
| `+0x39a9f0` | 250 records of `0x88` | `0x1414dba10` |
| `+0x3a2ec0` | `u32` = `0xcd`, then a tail to `0x3a2ef0` | `0x1414db7a0` |

`100 * 0xb4 == 0x4650` exactly, so the phase tables begin where the entry table ends: the
two are one contiguous run, and growing the first moves the second.

An entry of `0xb4` is a `u32` key at `+0` followed by **two** sub-records of `0x58`
(`4 + 2*0x58 == 0xb4`).  A sub-record is `u32 tag`, `u16 order` (`0xffff` = unused), then
**twenty `u32` phase-table indices** from `+8`, each run `-1` terminated.  So the "twenty
phase slots" of the earlier note are real but they sit one level lower than it said --
twenty per sub-record, two sub-records per competition, not twenty per entry.

A phase table of `0x187c` begins `u16 competition id`, `u16 phase tag`; both `0xffff` means
free.  `0x14158f350` is the pool allocator: it scans all 600 for a free one, stamps the
competition id into it, and **returns -1 when the pool is exhausted**.

**Is 0x64 a capacity?**  Yes, and a hard one.  `0x1414fd4e0` constructs exactly `0x64`
entries, the allocation covers exactly 100 of them, and `0x14158f420` is the find-or-create:
it searches for the key, and only if a create flag is set does it look for a slot holding
either the key or the empty sentinel, write the key and call `0x1414fd580` to initialise the
sub-records.  When all 100 slots are taken it falls out of the loop and writes nothing --
silently.  The competition then has no entry, `0x14159ebf0` fails to find it, `0x14158dfc0`
returns null, and that null is exactly what `nullguard2` was catching at `0x140fc9238`.

**The bound sites,** enumerated the way `patchset.py` enumerates block caps, over the 58
functions that read `owner+0x78` plus the constructor, the allocator and the copy:

| bound | sites | addresses |
| --- | --- | --- |
| 100 entries (`0x64`) | 14 | `0x1414fd4e3` (ctor count); `0x14158f71c` `0x14158f73c` `0x14158f760` `0x14158f78c` `0x14158f7ac`; `0x14159048e` `0x1415904be`; `0x14159ec1d` `0x14159ec4d`; `0x14159ecfd` `0x14159ed3d`; `0x14159ee70` `0x14159ee91` |
| entry stride (`0xb4`) | 13 | `0x1414fd569` `0x14158f716` `0x14158f749` `0x14158f786` `0x14158f7a6` `0x141590487` `0x1415904b7` `0x14159ec16` `0x14159ec46` `0x14159ecf6` `0x14159ed36` `0x14159ee69` `0x14159ee8a` |
| 20 phase slots (`0x14`) | 5 | `0x14158df6e` `0x14158f8a3` `0x14158fdee` `0x1415902db` `0x14159eda2` |
| sub-record stride (`0x58`) | 11 | `0x14158f7c7` `0x14158f7f8` `0x14158f827` `0x1415904d7` `0x141590508` `0x14159ec68` `0x14159ecba` `0x14159ed63` `0x14159ee12` `0x14159eea9` `0x14159eec9` |
| 600 tables (`0x258`) | 9 | `0x1414fd476` (ctor count), `0x1413fb201` (copy loop count); `0x14158df83` `0x14158f381` `0x14158f3b0` `0x14158f8d2` `0x14158fe38` `0x141590254` `0x14159edb3` |
| table stride (`0x187c`) | 8 | `0x1413fb2be` `0x1414fd4b9` `0x14158df8a` `0x14158f390` `0x14158f8d9` `0x14158fe45` `0x141590260` `0x14159edc0` |
| table base (`0x4650`) | 8 | `0x1414fd46f` `0x14158df91` `0x14158f39a` `0x14158f8e0` `0x14158fe4c` `0x14159026b`; `0x1413fb1fa` as `0x5ec6` (= `0x4650 + 0x1876`), `0x14159edca` as `0x4964` (= `0x4650 + 0x314`) |
| object size (`0x3a2ef0`) | 2 | `0x1414b62cb` (allocate), `0x1414b62e5` (memset) |
| tail offsets | 4 | `0x1414fd69f` (`0x39a8f0`), `0x1414fd6ab` (`0x39a9f0`), `0x1414fd6d4` (`0x3a2ec4`), `0x1414fd6db` (`0x3a2ec0`) |

The three `cmp ..., 2` in `0x14159ebf0` and `0x14159ecd0` bound the two sub-records inside an
entry, not competitions; they are structural and would not move.  Three other `cmp ..., 0x64`
sites the scan turned up -- `0x140f3be6e`, `0x1413fc5fc`, `0x1413fc9bc` -- are not this table:
the first is a UI threshold, the other two bound a `0x208` fixture walk.

**The mode copy does carry it, and our set has already moved it.**  `0x1413fb0b0` is a
member-wise copy of exactly this object's front: 50 unrolled iterations of two `0xb4` entries
(`mov r9d, 0x32`, `add rdx, 0x168`), then 600 iterations of `0x187c` starting at
`rcx + 0x5ec6`.  It has six callers, two of them inside copy A's fills:

    141401aff  call 0x1413fb0b0     ; rcx = live object, rdx = copy + 0xcaf24c   (load)
    1414020ae  call 0x1413fb0b0     ; rcx = copy + 0xcaf24c, rdx = live object   (save)

`0xcaf24c` is already a `copyfields.json` field; the mlcopy set rewrites both sites to
`0x166ad7c`.  The slot's length is the gap to the next copy field -- `0x1049b3c - 0xcaf24c
== 0x39a8f0` -- which is the entry table plus the phase tables plus the unidentified `0x300`,
and matches what `0x1413fb0b0` actually copies.  So the standings **are** written into the
save and read back from it; the copy is not the wall, and the object is not rebuilt from
nothing at load time.

**Which bound actually limits us.**  The 100 entries.  At roughly 131 competitions the entry
table runs out and every competition past the hundredth to ask for standings gets none.  The
600 phase tables are a pool shared across all competitions, and whether that pool is also
exhausted cannot be read out of the exe -- it depends on how many phases each competition
claims, which is a runtime number.  The twenty slots are per sub-record and are not a
competition limit at all.

**What a grown version would cost.**  It is one object, so this is the mode copy's shape of
problem rather than the block's: growing the entry table moves the phase tables, which moves
everything above them, which changes the allocation size and the copy slot.  For 200 entries
and 900 tables:

    entry table   200 * 0xb4   = 0x8ca0                          (+0x4650)
    phase tables  900 * 0x187c = 5,641,200 = 0x561630            (+0x1cb690)
    object size   0x3a2ef0 + 0x4650 + 0x1cb690 = 0x572bd0        (5.6 MB, from 3.6 MB)

The patch would be: the 14 `0x64` sites, the 9 `0x258` sites, the 8 `0x4650` base sites (two
of them in disguised form), the 2 size sites, the 4 tail offsets, and the copy loop's `0x32`
at `0x1413fb0d4` and `0x258` at `0x1413fb201` -- and then, on the copy side, the slot at
`0x166ad7c` grows by the same amount, so every copy A field above it shifts again and the
copy's own size constants move with them.  Strides stay: nothing here needs a wider record.

Two things make this cheaper than it looks and one makes it dearer.  Cheaper: the entry table
is 18 KB, so doubling it costs nothing, and the phase pool is the only expensive part; and
the object is heap-allocated from one `mov edx, imm32`, which is easier than the block's
relocation was.  Dearer: `0x1413fb0b0` copies the entry table with a hand-unrolled
two-at-a-time loop, so the new entry count has to stay even, and its second loop hard-codes
`rcx + 0x5ec6` rather than `0x4650` -- the kind of disguised constant a cap walk looking only
for `0x4650` would miss.

**What has to be measured live first, and how.**  Nothing above says how many of the 100
entries and how many of the 600 tables a loaded season on our data actually uses, and that is
the whole question: if our league has no regulation record after the load, the chain dies at
`0x1415451a0` and no amount of growing these tables helps.  `tools/standread.py` (new,
written for this and **not run** -- the game was not started) reads the object out of the
running process the way `livedump.py` reads the block, and prints:

  * which of the 100 entries are in use, their key, and which competition ids in the block's
    regulation array carry that key at `+0x80`;
  * every competition that has a regulation record but no entry -- if our league is on that
    list, the 100 is the wall and the diagnosis is confirmed;
  * how many of the 600 phase tables are stamped, and with which competition ids
    (`--tables`).

The check to run, with a Master League season loaded and the hub on screen:

    python tools/standread.py --set teams-coaches-regs-players-dates-matches-upper-mlcopy --tables

Three outcomes, and what each means.  If the entry table is full at 100 and our competition
is in the "regulation but no entry" list, the growth above is the fix.  If our competition
has an entry but no phase table, the 600 pool is the wall instead and only the `0x258` sites,
the `0x187c` walks and the object size need to move.  If our competition has neither a
regulation record nor a key, the standings are not a capacity problem at all, the fault is
upstream in what the load puts back into the block's regulation array, and this section is a
map of the wrong room.

### The standings are not capped: they are populated fresh and lost on load (2026-09-15, 22:20)

Two measurements settle what the last two sections were guessing at.

`tools/standread.py` (written from the map above) read the live standings object with a
season loaded:

    standings 0x7ff4e5f90010, size 0x3a2ef0
    86 of 100 entries in use
    115 of 600 phase tables in use

Neither pool is exhausted at our roughly 131 competitions: fourteen entry slots and 485
phase tables are free.  So the 100-entry table is not a wall we are hitting, and the fix
proposed in the previous section -- growing it to 200 -- would have bought nothing.

The second measurement is the one that matters.  The same season, photographed before
saving and after loading:

  * fresh: the standings panel lists our league -- FL 0741, FL 0757, FL 0754, FL 0742 and
    the rest, all on zero because no match has been played -- and the club header carries
    the manager's name, "Luis Figo".
  * after Save and Load: the standings panel is empty and the manager's name is gone; the
    header reads "FL 0741" with nothing under it and the news reads "New FL 0741 manager,
    ,".

Everything else survives: club, eleven, ratings, cohesion, followers, fixtures with dates
and times.  So standings work perfectly well on our data, with 39 added leagues, and are
lost specifically in the round trip -- the same shape as the three array truncations the
`mlcopy` set fixed, one layer further in.  The object is carried by the copy (0x1413fb0b0,
called from copy A at 0x141401aff on load and 0x1414020ae on save, against copy+0xcaf24c),
so the question is what that copy leaves behind: whether its loop covers all 100 entries or
only the first 50, and what happens to the 0x2600 bytes between the extent it touches
(0x39a8f0) and the object's real size (0x3a2ef0).

The manager's name is a second, independent loss and a useful cross-check: the coach record
comes back (the club has a manager rather than a stock one) while the name string does not.

Note what this corrects: two sections above, the empty standings were blamed first on an
80-entry array that turned out to be per-player records, and then on a 100-entry table that
turns out to have room to spare.  Both were reasoned from static bounds alone.  The fresh
season's hub had the answer in it the whole time and nobody had looked at that half of the
picture.

### Auto Lineup Select is now the wrong thing to do after a load (2026-09-15, 22:35)

`gameplan.py` was written because a loaded save fielded whatever eleven it had been saved
with, and a club in the wrong shape loses to clubs it outrates by twenty points.  The
mode-copy fix ended that problem, and with it the reason for the walk.

Pressing R3 in a loaded season now makes things worse.  The saved eleven photographed
straight after a load reads 81-99 with everyone in position; after one R3 the same club
fields 53-57 with every outfield player boxed red as out of position and the cohesion badge
at 50.  The goalkeeper, alone, keeps his 81.  So a loaded season is left exactly as saved;
only a freshly generated one, which has never had an eleven picked, gets the walk.

Why the auto-picker does that on a loaded season is not established and is worth chasing:
it looks like the squad's position data is not what the picker expects after a round trip,
which would put it next to the manager's name and the standings on the list of things the
copy does not carry whole.

Related, from the same run: `seasonrun.py` drives the calendar with the keyboard, and the
keyboard cannot leave the Team Sheet -- the same dead end `gameplan.py` documents, where
four presses of `z` did nothing.  A chunk that started on that screen spent its whole ten
minutes there and moved the day not once, reporting a clean exit.  The supervisor now
presses the pad's circle until the hub is on screen before every chunk.

#### Measured live, and the capacity reading is dead (2026-09-15, later)

`tools/standread.py` was run against a loaded season on `_FL26E39x793`: **86 of 100 entries
and 115 of 600 phase tables in use**.  Neither pool is exhausted, so the 100 is not the wall
at our ~131 competitions and the section above is right about the structure and wrong about
the consequence.  The panel was also seen populated on a *fresh* season with the same data
and empty on the *same season after Save + Load*, so this is a round-trip loss, not a
capacity loss.

**The copy carries all 100 entries, not 50.**  `0x1413fb0b0`'s first loop is hand-unrolled
two *entries* at a time, not two sub-records:

    1413fb0cd  lea rdx, [rcx+0xb4]     ; cursor one entry in
    1413fb0d4  mov r9d, 0x32           ; 50 iterations
    1413fb0e0  ... copies 0xb4 bytes to rdx-0xb4   (entry 2i)
    1413fb171  ... copies 0xb4 bytes to rdx        (entry 2i+1)
    1413fb1e9  add rdx, 0x168          ; 2 * 0xb4
    1413fb1f4  jne 0x1413fb0e0

`50 * 0x168 == 0x4650 == 100 * 0xb4`, exactly the entry table.  Entry 80 is copied.

**The second loop covers each phase table completely.**  `0x258` iterations of `0x187c` from
`rcx + 0x5ec6` (= record base + `0x1876`), copying two `u16` at `+0` and `+2`, five
sub-objects, and four `u16` at `+0x1874`..`+0x187a`.  The sub-objects and their helpers
tile the record with no hole:

| offset | length | helper | what the helper copies |
| --- | --- | --- | --- |
| `+0x0004` | `0x314` | `0x1413fb000` | head `0x14` + 48 x `0x10` + byte at `+0x310` |
| `+0x0318` | `0x7c0` | `0x1413fc250` | 48 x `0x30`-ish, tail fields to `+0x798` |
| `+0x0ad8` | `0x32c` | `0x1413fbeb0` | head 8 + 40 x `0x14` + `+0x320`,`+0x324` |
| `+0x0e04` | `0x32c` | `0x1413fbeb0` | same |
| `+0x1130` | `0x744` | `0x1413faf10` | head `0x10` + 92 x `0x14` + byte at `+0x740` |

So the copied extent is `0x4650 + 600 * 0x187c == 0x39a5f0`, and **nothing inside the
standings proper is left behind**.

**What is left behind is the tail.**  The object is `0x3a2ef0`; the copy writes `0x39a5f0`
of it and the copy slot is only `0x39a8f0` long, so `0x3a2ef0 - 0x39a5f0 = 0x8900` bytes
never make the round trip: the `0x300` at `+0x39a5f0`, the `0x100` at `+0x39a8f0`, the 250
records of `0x88` at `+0x39a9f0`, and the `0x30`-byte tail after `+0x3a2ec0`.  None of the
accessor chain touches any of it -- `0x14159ebf0`, `0x14158df30`, `0x14158dfc0` and
`0x14158f420` use only `+0` and `+0x4650` -- so on the code as written the standings do not
depend on the uncopied tail either.

**Which leaves the key.**  The entry is not found by competition id but by the `u32` at
`+0x80` of the competition's regulation record (`0x1415451a0`).  The entry table survives
the round trip with its keys intact; if the *regulations* come back with different `+0x80`
values, every saved entry is orphaned and the panel is empty while the data is all still
there -- which is exactly what 86 occupied entries beside an empty panel look like.  That is
now the leading hypothesis and it is one live read away from being settled.

**The check that settles it.**  `standread.py` grew a `--keys` dump: every regulation live as
`cid -> key`, each marked `entry` or `NO ENTRY`.  Run it twice on the same season, once on
the fresh season and once after Save + Load:

    python tools/standread.py --set teams-coaches-regs-players-dates-matches-upper-mlcopy --keys

If our league's cid keeps its key across the round trip and stays `entry`, the key theory is
dead and the fault is in the panel's own reader.  If its key changes, or it goes to
`NO ENTRY`, the fault is in what the load puts back into regulation `+0x80` and the fix is
there, not in any of the caps enumerated above.

**The manager's name: a coach-record field the copy does carry.**  The block's coach record
copy is `0x140d5e170`, called by copy A at `0x14140178a` (stride `0x258`, `add rdi, 0x258` at
`0x141401791`).  It copies `u16` at `+0`, `u32` at `+4`, then **`0x17` iterations of two
bytes from `+8`, i.e. 46 bytes at `+0x08`..`+0x36`** -- the shape of a name -- then the
bitfields at `+0x36`..`+0x3e`, three `0xa0` sub-objects at `+0x40`..`+0x1c0`, and `+0x220`
to `+0x258` by SSE.  Gaps: `+0x3e`..`+0x40` and `+0x1c0`..`+0x220`.  So if the manager's
name were the coach record's own name field it would survive, and it does not; the lost
string is therefore something else, and the two `.rdata` handles `manager_name`
(`0x142bdcc58`, referenced once from `0x1420d9e7d`) and `managerName` (`0x142690268`) are UI
property names, not storage.  Not located yet.  The cheap next measurement is a live diff of
the managed club's coach record at `+0x08`..`+0x36` before and after the round trip: if those
46 bytes are intact after the load, the displayed name comes from somewhere else entirely.

#### The forward-time crash at 0x141572125 is a null coach record, not the standings (2026-09-15, later still)

Pushing time forward on a loaded season died at `0x141572125`, reading `0x220`.  The
function is `0x1415720d0` (extent `0x1415720d0`-`0x141572390`), and the faulting read is

    141572100  mov rbx, rdx             ; argument 2
    14157210d  call 0x141268ae0         ; -> eax, an index
    141572117  cmp eax, 0x28            ; 40, the size of the table below
    14157211e  lea r8, [rbx + 0x220]
    141572125  movzx ecx, byte ptr [r8] ; rbx = 0, so r8 = 0x220

so the null register is **`rdx`, the second argument**, kept in `rbx`.  The object it wants
is a record of `0x258` bytes holding a 40-byte table of ids at `+0x220` (`0xff` = empty; the
loop at `0x141572200` removes an entry by writing `0xff` back) and a flag byte at `+0x257`.
That is a **coach record**: the block's coach array is `block + 0xc4ca0c`, stride `0x258`,
and `0x140d5e170` -- the copy helper that carries coaches into the mode copy -- restores
exactly `+0x220`..`+0x258` with SSE at its tail.  It is **not** the standings object, not one
of its `0xb4` entries and not one of its `0x187c` phase tables; nothing in
`0x1415720d0` reads `owner+0x78`.  The `0x14` in `rax`/`r15` is what `0x141268ae0` returned,
bounded by `cmp eax, 0x28`; its resemblance to the twenty phase slots is a coincidence.

**Where the null comes from.**  `0x1415720d0` has seven callers.  Two of them set `r9b, 1`,
and the dump has `r14 = 1`, which is `movzx r14d, r9b` at entry -- so the caller is
`0x140f143a0` or `0x1413184ec`.  `0x140f143a0` fits everything:

    140f14384  call 0x1414bc780         ; the coach lookup -- CAN return null
    140f14397  mov r9b, 1
    140f1439d  mov rdx, rax             ; passed straight through, unchecked
    140f143a0  call 0x1415720d0

`0x1414bc780` indexes `r9 + 0xc4ca0c + i*0x258`, then validates a handle: it reads a dword at
`+4` of the record and compares it with the generation half of the handle
(`0x1414bc7f3`, `cmovne rbx, rdx` with `rdx = 0`).  A stale handle returns **null**, silently.
The sibling caller `0x141522a51` calls the same lookup and does check -- `test rax, rax;
je 0x141522b3c` at `0x141522a2f` -- and skips the call entirely.  So the game itself treats
"no coach record" as a do-nothing case at one site and forgets to ask at another.

**Is this the same fault as the empty standings?**  On the evidence, no -- different object,
different array, and the standings chain is not on this stack.  It is plausibly the same
fault as the **missing manager name**, and that is a testable claim rather than an
assumption: both concern the managed club's coach, the lookup's null path is a *handle
generation mismatch* rather than a missing record, and the name is missing while the record
itself is present (the club has a manager).  What would settle it: read the managed club's
coach record live before and after the round trip and compare the `u32` at `+4` -- if the
generation changes across Save + Load, stale handles explain the null here and the blank name
there, and neither is a capacity problem.  Nothing yet shows that a loaded season with
working standings would survive this crash; there is no measurement either way.

**Guardable, but not in nullguard2's shape.**  Guarding the read at `0x141572125` does not
work: the "not found" path (`mov edx, 0xff` at `0x141572138`, target `0x141572141`) rejoins
the body, which dereferences `rbx` again at `0x1415721bf` (`movzx eax, byte ptr [rbx+0x257]`),
`0x141572213` and `0x14157223f`.  A jump there would only move the fault.

The guard that does exist is at the **entry**, and the game's own null-checked caller is the
evidence that doing nothing is the correct behaviour.  The first instruction is

    1415720d0  48 89 5c 24 20     mov qword ptr [rsp+0x20], rbx

five bytes, before the prologue, so a five-byte `jmp` to a stub is a clean splice: the stub
tests `rdx`, `ret`s at once if it is zero, otherwise re-executes the store and jumps back to
`0x1415720d5`.  The return value is safe to leave undefined -- all seven callers ignore `rax`
(`0x140f143a5` `lea rdx, [rsp+0x48]`, `0x1412638ba` `mov edx, [rbp+0x48]`, `0x14126fd6e`
`mov rdx, [rsp+0x38]`, `0x14156adf8` `inc r13d`, `0x14156e9a7` `nop`, and the two checked
sites).  Flags do not need preserving at the entry: nothing has been computed yet, and the
first flag consumer is `0x14157211a`, after the call at `0x14157210d` which clobbers them
anyway.  Free cave space begins at `0x14252e840`, after nullguard3's `0x14252e820`-`0x14252e836`.

For the record, the bytes the applier would verify: `48 89 5c 24 20` at `0x1415720d0`, and
`41 0f b6 08 41 3b cf 74 13` at `0x141572125` (the read, the compare and the branch) if a
site guard is ever preferred instead.  Neither is written; this is a map, not a patch.

#### The load writes the coach array 0x15ca20 too high (2026-09-15, night)

Measured, not inferred, with `tools/coachread.py --dump` on one season read twice: fresh,
then saved to slot 2 and loaded back.

| | coach records in use | first record at index |
|---|---|---|
| fresh season | 1485 of 2600 | 0 |
| same season after save -> load | 220 of 2600 | 2380 |

The records themselves are intact -- same ids, same generations, same names, same 40-byte
id tables -- they are simply written 2380 slots further up the array, and 2380 * 0x258 is
**0x15ca20 exactly**, which is this set's teams growth (750 -> 1600 records of 0x690).  So
on the load path the teams growth is added to the coach base a second time.  Everything
that was below index 2380 in the fresh season is gone, which is why 1485 records come back
as 220: the rest ran off the end of the array.

That one bug explains three symptoms at once:

  * **the manager's name disappears** -- "Luis Figo" sat at index 1483 in the fresh season,
    which after the shift is an empty slot, so the lookup finds nothing to print;
  * **the crash at 0x141572125** -- `0x1414bc780` returns null for a handle whose slot is
    now empty, and `0x140f143a0` passes that null straight into a function that reads
    +0x220 off it;
  * **the standings panel is blank** -- the regulation array reads as garbage after the
    load at its patched base, so the key lookup that the panel starts from cannot succeed.

**The standings object itself is not at fault and the earlier theory is dead.**  Read with
`tools/standread.py --keys` on both halves of the same round trip, it is identical: 86 of
100 entries in use and 115 of 600 phase tables in use, fresh and loaded alike.  Nothing in
it is truncated, copied short or re-keyed.  The panel is empty because what it looks up has
moved, not because what it stores was lost.

#### The round trip is stable, and the standings panel came back with it (2026-09-15, night)

With the corrected biased displacements, the same save was loaded three times in a row and
the coach array was dumped after each load.  Every dump is line-for-line identical to the
fresh season's: 1485 records in use, the first at index 0, Luis Figo at 1483, same
generations and same id tables.  `diff` of fresh against the third load is empty.

That answers the question the old bug raised.  Under the broken set the damage compounded:
a load shifted the records up by 2380 slots and threw away everything that ran off the end,
and saving from that state wrote the crippled array back to disk, so a third run would have
had no coaches left at all.  The save file itself was never corrupt -- the save path uses
direct block references and was always right -- but one save after one bad load would have
made it so.  Under the corrected set nothing moves and the cycle is stable.

The hub's standings panel is populated again after the third load, listing our own clubs,
and the news item announcing the manager's appointment is back.  Both were symptoms of the
same displacement: the panel looks competitions up through the regulation array, which was
being written 0x21b100 too high into a 600-record array, so nothing survived for it to find.

No guard was installed for this test.  `sider/fl26nullguard4.lua` remains written but not
enabled: the null it guards came from the displaced coach array, so the right order is to
prove the crash is gone before adding a trampoline that would hide it.


## The load path put regulation records on top of the team array (2026-09-16)

A season loaded from a save crashed a day after matchday 1, at day 238, in the AI lineup
pass 0x141500ef0: 0x141503cc0 answered 0xff ("no candidate left") and the 0xff was used as
an index. nullguard5 moved the fault one dereference along, to 0x1415032f0. The sentinel was
the symptom; the cause was in the data.

Measured live at day 212, before a single match or transfer: 69 of 1483 clubs already had
broken squad handles, 233 of them. A handle at team_rec + 0x14c + 8k is {u16 index, u16
generation, u32 player_id}; the index is the player's own slot in the live player array,
repeated at player+0x2c with the id at +0x30. In the damaged entries only the leading two to
four bytes were clobbered, so 147 handles resolved to the DUMMY record and 86 silently
resolved to the wrong player. 0x141503de0 counts a DUMMY entry as an available player, so
the fill loop asked for one more player than the candidate vectors could ever hold.

The damaged offsets lay on a 0x314 lattice -- the regulation stride -- in a 20-byte window
at +0x28c..+0x2a0 over 293 records, starting at block+0x1a69130. That is the regulation
record initialiser running against the old copy layout:

    0x140af3e73  lea rdi, [rdx + 0x1f2110]    <- old regulations offset, unpatched
    0x140af3e7a  cmp ebp, 0x12c               <- patched, 300 -> 600

in the accessor 0x140af3680, A branch (rdx = [r15 + 0x270]). The index bound was raised to
600 while the base displacement next to it kept the shipped copy layout, so 293 regulation
records were initialised 0x21b100 bytes low -- 0x40d210 - 0x1f2110, the regulations' copy
offset growth -- straight over team rows 1214 and up. The coach branch of the same accessor
had the identical gap: 0x140af3cb1 kept 0x133a30 while 0x140af3cb8 was raised to 2600.

Why the generator missed both: the mlcopy field walk only covers copy A's own functions
(copy.mlcopy.code_a), and the handful of sites that reach a copy field from outside are
listed by hand in copy.mlcopy.outside_sites. That list had the accessor's buffer field
(0x140af375f) but not its coach and regulation bases -- even though both of their index
bounds were already listed as count_sites in the same file.

Fixed by adding the two sites to outside_sites, and by a new generation-time check,
check_copy_fields(): it scans the whole code section for every copy A field offset mlcopy
moves and refuses to emit a set unless each occurrence is either patched or named in
copy.mlcopy.field_scan_allow with a reason. Variant B's four sites are allowed there (B
keeps its shipped layout), as are seven numeric coincidences in 0x14128xxx where the value
is a formatter argument rather than a field.

Verified: the set went from 2688 to 2690 patches, the game applied all of them, the same
save was loaded, and tools/rosterread.py found 0 broken handles in all 1473 clubs that have
a roster (69 clubs, 233 handles before). Wisla Krakow, the club in the crash dump, is clean.

sider/fl26nullguard6.lua stays in the tree but is NOT installed: with the data correct the
0xff should not arise. It remains the right stopgap if it ever does -- it leaves the fill
loop through the loop's own exit at 0x14150287b instead of faulting, which is what the game
does for any club with fewer available players than slots.

## The 1,536 club wall: where it is not, and the one lead left (2026-09-16)

**Correction, same day.** This section first argued the wall was the fixture table rather than
the club index. It is not, and the test that says so was already in the log: in
`_FL26E40x800` -- one world, 40 leagues, nothing regenerated between attempts -- **FL League 39
starts a season and FL League 40 kills the process**. Same world, same fixtures, same
competitions; the only thing that changes is the index of the clubs in the league being played.
No budget-shaped ceiling can behave that way. The bracket at team index 1536 stands, and so
does everything built on it.

What the day's measuring did establish is a negative worth keeping, because it closes off the
obvious search:

**1536 is in no team-array guard.** Every place the team array is indexed was enumerated by
taking all 124 `imul` sites that use the team stride 0x690 and disassembling each enclosing
function up to the site to read the guard protecting it:

| guard before a team-array index | sites |
|---|---|
| **0x2ee = 750** (the shipped club cap, raised to 1600 by every set) | **103** |
| small loop counters (1, 2, 0xa, 0xb, 0x15, 0x18, 0x28, 0x3c, 0x40, 0x56) | 21 |
| **0x600 = 1536** | **none** |

So the club array is guarded in exactly one way, at 750, and we raise all 103 of those. There
is no second, lower ceiling hiding in the club accesses themselves. With the two `cmp ...,0x600`
sites in .text being message-code switches, and nothing dividing into 1536 for any stride the
block uses (`immquery.py --strides 0x690,0x5fc,0x314,0x208`: nothing), the number does not
exist in the executable in any form. Whatever stops at 1536 is a structure, not a comparison.

**The engine's shape for a capped array**, confirmed today at the regulation lookup
`0x1415102f0`, is worth stating because it is what a ceiling looks like here when there is one:

    cmp ebp, 0x12c                ; the cap -- our set patches this to 600
    jb  indexed
    lea rbx, [rdx + 0xd0b77c]     ; over the cap: one shared dummy record
    jmp on
  indexed:
    lea rbx, [rdx + 0xc12e9c]     ; base
    imul rcx, rax, 0x314          ; stride

Nothing of that shape exists with 1536 in it.

**The lead that is left** is the heap object the season code works from -- `0x1414b6a60()`
then `[rax + 0x78]`, a different allocation from the edit block at `[rax + 0x48]`. Walked
today through `0x14158df30`, it holds the competition records: **base `+0x4650`, stride
`0x187c`, cap `0x258` = 600**, reached through a per-owner list of up to **20** `u32` slots
terminated by `-1`. Each competition record carries its entered teams as **48 entries of 20
bytes at `+0x00` with the count at `+0x3c0`** -- 48 x 20 = 0x3c0, so that list ends exactly
where its own counter begins, the same shape as the 750-entry table at `block+0x16705a8`.

The board-meeting crash at `0x1413236e4` is `sub ecx, [0x1428e52e0 + rax*4]` over a small
static table of signed modifiers, with `rax` taken from `[r14+4]` -- a field of one of those
20-byte entries. By then the index is already junk, so the fault is downstream of whatever
goes wrong. The 18,000 bytes below the competition array are not a mystery, only a thing this
section first failed to look up: `seasonread.py` has them documented as a header array of
**100 entries of 0xb4 bytes**, and 100 x 0xb4 is exactly 0x4650.



## G2: the fixture table is rounds, it is global, and a record holds 16 matches (2026-09-16)

The plan carried the fixture table as "never raised because its scope was never established".
Established, statically, in one pass.

**It is an ordinary capped array.** All 29 sites that index it were found by their 0x208
stride and each guard read: **26 guarded at 0x7d0 = 2000, three at 0x7cf = 1999**, and nothing
else. Plus the constructor at `0x1414b88bf` (`mov r8d, 0x7d0`, `edx = 0x208`, base
`edit+0xd65f64`). That is the same shape as teams, coaches and regulations, so raising it is
the same ordinary cap patch, and the array is already a member of the upper belt the `-upper`
sets move.

**It is global.** The array lives inside the edit block, next to the players, clubs and
regulations -- not inside a competition object and not inside the season object at
`[owner+0x78]`. One table serves the whole world.

**A record holds sixteen matches.** From the scheduler at `0x1413509d0`:

    cmp  eax, 0x7cf              ; the fixture id, refused above 1999
    imul rcx, rax, 0x208
    lea  r13, [r15 + 0xd65f64]   ; the fixture array in the edit block
    ...
    cmp  r14d, 0x10              ; sixteen slots
    mov  ecx, r14d
    shl  rcx, 5                  ; of 32 bytes
    add  rcx, r13
    add  rcx, 4                  ; starting at +4

16 x 32 = 512, the slots run +0x04..+0x203, and the packed count sits at **+0x204** -- the
table ends exactly where its own counter begins, the third structure in this game built that
way. 0x204 + 4 = 0x208.

Two consequences worth having in writing:

1. **Sixteen is per record, not per round.** See the correction below -- this was written as a
   per-competition ceiling on the first pass, and it is not one.
2. **2,000 rounds is the budget for the entire world.** A double round-robin league of N clubs
   spends 2(N-1) of them, so our 39 leagues of 20 spend 1,482 before a single cup exists. A
   group phase is worse than it looks: every group of every matchday is its own record, so a
   12-group World Cup group stage spends 36. How much the shipped competitions already spend is
   the one number still missing, and it cannot be read from a save (they are encrypted) -- it
   wants `livedump.py` against a running season. Until it is measured, treat cups and
   continental competitions as capable of exhausting this table, and raise it before stage C
   rather than after.

### Correction, same day: sixteen is the size of one record, not a limit on a round

The first version of this section said "no competition can schedule more than 16 matches in one
round". That is wrong, and the rest of the scheduler says so plainly. The full loop:

    1413509b5  test dword ptr [rax + 0x300], 0x1f80000  ; bits 19-24, six bits -> max 63
    1413509bf  jbe  <done>                              ; nothing to schedule
    1413509c5  mov  edx, r12d                           ; sub-unit index
    1413509cb  call 0x1414c9890                         ; -> a fixture id, ONE PER SUB-UNIT
    1413509d0  cmp  eax, 0x7cf
    1413509dd  imul rcx, rax, 0x208                     ; that sub-unit's own record
    1413509ee  xor  r14d, r14d
    1413509f1  test dword ptr [r13 + 0x204], 0x3ffffff  ; the record's match count
    141350a02  cmp  r14d, 0x10                          ; slot < 16 ? real slot : clamp to base
    ...
    141350acb  inc  r14d
    141350ace  mov  eax, dword ptr [r13 + 0x204]
    141350ad5  and  eax, 0x3ffffff
    141350ada  cmp  r14d, eax
    141350add  jb   <next match>                        ; inner bound is the COUNT, not 16
    141350ae3  inc  r12d
    141350af6  cmp  r12d, eax
    141350af9  jb   <next sub-unit>                     ; outer bound is the six-bit field

Two things follow that the first reading missed. The inner loop is bounded by the record's own
count field, which is **26 bits wide**, not by 16 -- `cmp r14d, 0x10` is the familiar
clamp-to-entry-0 fallback, the same shape as every other capped array in this executable, not a
loop bound. And the outer loop fetches **a separate fixture id for each of up to 63 sub-units**,
so one competition round is spread across as many records as it has groups: the ceiling on a
round is 63 x 16 = 1,008 matches, not 16.

The shipped data already proves it. The Europa League group phase (reg for cid 3) is **48 clubs
seeded into groups**, which is 24 matches on every matchday, and it runs in the stock game. 24
is more than 16; it fits because it is twelve groups of two matches, twelve records.

What survives the correction is narrower and still useful: **no single group can hold more than
16 matches**, because writing slot 16 lands on the clamp. A group of 32 plays exactly 16 and is
the largest that fits; 33 or 34 in one group needs 17. That lines up with the measured league
ceiling -- 33 clubs in a single-group league play 16 matches a round with one idle, 34 would
need 17 -- so the 16-slot record is a plausible explanation for the 33-club limit specifically,
and that is a testable prediction rather than a finding: build a 34-club league and see where it
dies.

For the wishlist this means the formats we care about are mostly unaffected:

| format | matches in a round | per record | verdict |
|---|---|---|---|
| World Cup 48, 12 groups of 4 | 24 | 2 | fits |
| Club World Cup 32, 8 groups of 4 | 16 | 2 | fits |
| UCL league phase, 36 as six groups of six | 18 | 3 | fits |
| UCL league phase, 36 as one Swiss table | 18 | **18** | over by 2 |
| domestic league, 34 clubs | 17 | **17** | over by 1 |

So the two cases that actually hit the wall are a genuine single-table Swiss phase and a
domestic league above 33. That is consistent with the modding scene: the new Champions League
format has been built by others, and SmokePatch is doing the 48-team World Cup -- both are
group-shaped as far as the engine is concerned, and neither needs a seventeenth slot.

Raising 16 is possible but it is **not a one-immediate patch**. The stride 0x208 is
4 + 16 x 32 + 4, so more slots means a new stride, a new count offset and a relocated array --
all 29 index sites plus the constructor, the same work as the belt moves, not a byte flip.
Worth doing only if a single-table Swiss phase or a 34+ league turns out to be wanted.

## A fourth season-killer, and this one hangs instead of crashing (2026-09-16)

Loading slot 1 never finishes. The screen sits on the loading spinner, the process burns four
cores, and nothing in the Windows log says a word -- because nothing crashed. Slot 2 loads the
same world in the ordinary time and comes up at day 271, so this is the save, not the world.

**How it was read, since this exe fails fast under a debugger.** `DebugActiveProcess` is what
the anti-debug check watches for; `SuspendThread` + `GetThreadContext` is not that, and it
returns RIP. Sampling every thread a few dozen times put 18 of the in-exe samples inside
`0x141576950`, a bounded 18-slot search of a calendar day record, and the rest around
`0x140fd7180`. That is now `tools/ripsample.py`.

**The loop, at `0x1412aab30`:**

    1412aab30  cmp  ax, bx              ; walked date vs the target date
    1412aab58  seta cl                  ; still after it?
    1412aab5d  jne  1412aab7e           ; yes -> look at this day
    1412aab62  jne  1412aabe2           ; before it -> done
    1412aab7e  mov  dword [rsp+0x38], 0x21
    1412aab90  call 0x141576950         ; is competition 33 on this day?
    1412aab9f  mov  dword [rsp+0x38], 0x3d
    1412aabb1  call 0x141576950         ; is competition 61 on this day?
    1412aabd4  call 0x140fd7180         ; neither -> step the date back one day
    1412aabdd  jmp  1412aab30

`0x140fd7180` is an ordinary "one day earlier": decrement the day byte at `+3`, on underflow
decrement the month byte at `+2`, and on underflow `add word [rbx], 0xffff` -- **the year is a
16-bit word and that is a wrapping decrement.**

So the exit condition is "the walked date has fallen below the target", and the year cannot
fall below zero: it wraps to 65,535, which is above the target again, and the walk never ends.
Watching the record live confirms it -- the same `rbx` (0x8efb60, a stack slot), the year
sweeping the whole 16-bit range between samples:

    rbx=0x8efb60 year=51302 month=12 day=10
    rbx=0x8efb60 year=19918 month=3  day=25
    rbx=0x8efb60 year=60868 month=6  day=11
    ...

**What it is looking for makes it worse.** Competition `0x21` is 33, the EURO. Competition
`0x3d` is 61, and 61 is in our own free-id list: **there is no competition 61 in this build.**
So one of the two targets can never be found by construction, and the other is a national-team
tournament that is not on every season's calendar. When neither is there, the walk is unbounded
by design and only the target date saves it.

Not yet known: what makes slot 1 enter the walk with a start date before the target, where slot
2 does not. That is the next thing to look at, and it needs the two saves compared rather than
more disassembly. Worth a guard of the nullguard kind either way -- a bound on the walk turns
an unattended run that hangs for ever into one that fails and can be retried.

## G2a measured live: the fixture table is FULL (2026-09-16)

The number the G2 section said was missing -- how many of the 2,000 fixture records the world
already spends -- is measured, on the running 39-league season loaded from slot 2 at day 271:

    fixture records in use: 2000 / 2000   (19,264 matches)
        6 matches  x55
        7 matches  x26
        8 matches  x210
        9 matches  x170
       10 matches  x1448
       11 matches  x42
       12 matches  x46
       16 matches  x3
    records holding more than 16: none

**Every record is in use.** There is no headroom at all: the table is not "mostly free with
room for cups", it is saturated by the leagues alone. That settles G2a's priority -- the cap
has to be raised before any competition is added, not after, because the next competition has
nowhere to put its rounds.

The distribution is the confirmation that the reading of a record is right. A double round-robin
league of 20 clubs plays 10 matches a round and 38 rounds a season; 39 such leagues spend
1,482 records of exactly 10 matches. The measurement shows **1,448 records holding exactly 10**,
which is that number less the rounds not yet played into by day 271. The 6-to-12 spread is the
cups and the shipped competitions, and the three records holding 16 are the 32-club group
matchdays.

**Nothing holds more than 16**, as the corrected G2 section says it should not.

One anomaly worth recording rather than explaining away: the live player count reads **46,628**,
which is above the 46,193 this patch set raises the cap to. Either the count field is counting
something other than the array's occupancy, or the cap is not the bound on it. Not chased here.

Measured with `tools/livedump.py`'s reader against the relocated bases the set installs
(fixtures at `block + 0x2c20058`, counts at `block + 0x2bc5ddc..0x2bc5de8`), because the
shipped offsets in `layout.json` are the pre-relocation ones and read garbage under any
`-upper` set.

## F1: where target types actually come from (2026-09-16)

The plan's open question was "which target-type values are free". The question turns out to be
slightly the wrong one, and the right answer is better: **the target type is not a value the
data can choose. It is an immediate in a handful of small, adjacent code blocks, and those
blocks are now located.**

The whole consumption of the qualification table at `0x1434f1fa0` goes through exactly one
function, `0x1413b7760`, reached through exactly four call sites in two wrappers
(`0x1413b7900`, `0x1413b7910`). Above them sits one resolver, `0x141357470`, and above that
`0x1413561f0` and `0x141355c90`. Every caller passes the target type through as an argument,
so the values themselves live at the top — and the top is a set of blocks all built the same
way: **scan the regulation array for a literal regulation id, and on a hit ask for literal
target types.**

| block | finds regulation | second argument | target types requested |
|---|---|---|---|
| `0x1413641e0` | **5** | 0 | **0, 1, 2** |
| `0x141364310` | **5** | 0 | **0, 1, 2** |
| `0x141365fe0` | **10**, then **9**, then **8** | 1 | **3, 4** |
| `0x1413633b0`, `0x1413636c0` | (caller's) | 2 | **7** |

They read like this — the UEFA one, in full:

    cmp word ptr [rdx], 5         ; the regulation id, hard-coded
    add rdx, 0x314                ; walk the regulation array
    ...
    xor r8d, r8d
    call 0x141355c90              ; target 0  -- UCL groups
    lea  r8d, [rdx + 1]
    call 0x141355c90              ; target 1  -- UCL qualifiers
    lea  r8d, [rdx + 2]
    jmp  0x141355c90              ; target 2  -- UEL

So the target types the executable ever asks for are **0, 1, 2, 3, 4 and 7** through these
blocks. The data also carries rows for 9 and 10 (the Belgian and Danish euro play-offs), which
are asked for somewhere else again. **5, 6 and 8 are unused by the data**, and nothing was
found that asks for them, so they are free numbers with no code behind them — free as labels,
not as machinery.

What this means for building a new continental competition, concretely: a new competition needs
a new row in the rights table (cheap — the table relocates with two edits), a **new call asking
for its target type** (about ten bytes, but there is no slack inline, so a code cave), and the
code that actually puts the returned clubs into the new competition, which is what
`0x1413604a0` and `0x141360b20` do for the existing ones and is the real work.

The cheaper route is worth weighing first: the UEFA block already finds regulation 5 and asks
for three targets. A Conference League that entered through an existing target — taking the
clubs a fourth European place would have taken — costs no code at all, only rows. Whether the
resulting clubs can then be routed into a *different* competition than the one the builder
hard-codes is the thing to establish before any of this is built.

## F0 measured: regulation ids above 175 are not free, and the bound is not a ceiling (2026-09-16)

The plan's F0 stage said the regulation id space is unbounded -- the lookup that turns an id
into a record (`0x1415415f0`) is a linear scan over a 16-bit key with no comparison against
any ceiling, so 80 ids above the shipped maximum of 175 should be ours for the taking. That
static reading is correct as far as it goes, and it is not what the game does.

Four worlds were built, identical in every respect except the ids they hand their leagues:
39 leagues of 20 clubs each, 780 new clubs, 23 players apiece, the same 39 regulation records
byte for byte apart from the id at `+0x02` and the name digit. In every one of them the new
regulation rows are appended at table indices 214-252 and every new competition sits in region
slot 16, so neither position in the table nor the region byte can account for a difference.

Each world was then walked down the Select Team list one keypress at a time, photographing
every entry, until the selection stopped moving at the end of the list.

| world | regulation ids | entries in the list | FL leagues that appear |
|---|---|---|---|
| `_FL26F0Ctl` / `_FL26E39x793` | the holes below 143 | 44 | **12** -- 01, 05, 06, 07, 22, 23, 24, 25, 36, 37, 38, 39 |
| `_FL26F0Cid` | the same holes, competition ids all 142-180 | 44 | **12** -- the same twelve |
| `_FL26F0R144` | 144-204 | 34 | **5** -- 01 (144), 02 (145), 03 (146), 04 (152), 12 (177) |
| `_FL26E39Reg176` | 176-214 | 30 | **1** -- 02 (177) |

Three things follow.

**Competition ids above the shipped maximum are innocent.** `_FL26F0Cid` gives all 39 leagues
competition ids 142-180 and changes nothing: the list is the same 44 entries with the same
twelve leagues as the world we run every day. That closes the other half of F0 by measurement
rather than by inference.

**The regulation id is what moves the needle, and raising it costs shipped content too.** The
low-id worlds list Copa Libertadores 2017, Copa Sudamericana 2016 and European Qualifiers; the
worlds with ids above 143 do not. Whatever the id feeds, it is not only our leagues that
suffer -- the same 29 shipped entries survive in both high-id worlds and the extras do not.

**It is not a ceiling.** Id 177 is visible in two different worlds. Ids 176, 178 and 153 are
not. 144, 145, 146 and 152 are; 154, 170, 171, 173 and 174 are not. No arithmetic on the id
separates the visible set from the invisible one, and nothing in the regulation functions
compares an id against 175 or 176 -- a sweep of the immediate index for 0xaf and 0xb0 inside
the 394 functions that touch the regulation array finds nothing but stack frames.

So the mechanism is still open, and it is the next thing to find. The likely shape, from
`mkleague.py`'s own note, is a fixed menu the engine carries -- "the menus know those slots and
no others" was written about the region byte, and something of the same kind indexed by
regulation id would explain both the shipped competitions that come and go and the scattered
set of ids that work.

**What the project should do meanwhile:** treat the 80 ids above 175 as unavailable, not as
the reserve the plan counted on. The wishlist wants 40-50 new regulation ids and the holes
below 175 hold 52, of which our 39 leagues already take most. That is the real constraint, and
it is tighter than F0 assumed.

## The player cap at 51,729, and thirty players a club (2026-09-16)

The goal was at least thirty players in every club, and the worlds we run had twenty-three.
Thirty across 793 new clubs is 23,790 players, and with the 27,840 the shipped tables already
carry that is 51,630 -- past the 46,193 the installed set allowed.

Raising it turned out to be free. `patchset.py --player-cap 51729` checks the new cap against
the ceiling the upper belt leaves above the player array (`0x16038a8`) and 51,729 x 0x17c fits
under it, so the set generates with **the same 2,690 patches at the same 2,690 addresses and
the same block size 0x1877068 -> 0x2d5a068** as the 46,193 set. Only the immediate values
differ. Every relocated base is identical, which is worth writing down because an earlier
theory blamed a load hang on the two sets disagreeing about a base; they do not.

One trap on the way: regenerating the set without `--date-keys` and `--date-offsets` silently
drops the ten fixture-date patches -- the code cave at `0x14252e690` and its table of shifts
for our 39 regulation ids -- and produces 2,681 patches instead of 2,690. The arguments are
kept in the set's own json (`date_keys`, `date_offsets`), so a regeneration should read them
back from there rather than be retyped.

Measured live, on a fresh season in `_FL26E39x793p30` (the same world, rebuilt with
`mkplayers.py --per 30 --cap 51729`):

| | |
|---|---|
| players in the file | 51,630 |
| players live | 48,039 -- under the cap, where 46,628 against a cap of 46,193 was **over** it |
| clubs with a roster | 1,473 |
| **clubs with exactly 30** | **719** (it was 803 clubs with exactly 23) |
| the rest | 19-29 for 531 clubs, 31-40 for 223 |

793 of those 1,473 clubs are ours and every one was written with thirty; the other 680 are
shipped and keep whatever the shipped tables gave them, which is where the 227 clubs still
sitting at exactly 23 come from. So the cap is not what stops a club having thirty, and the
target is met for the great majority of our clubs. What is left is the seventy-odd of ours that
came out at something other than thirty -- the season builder moves players between clubs while
it generates -- and that is a different problem from the one the cap was blamed for.

**Save and load survive it.** The season was written to slot 2 (`ML00000001`, 30.4 MB against
the old 20.1 MB) and read back: identical counts, identical squad histogram, day 212 either
way.

The old set is kept as `modules/fl26caps.lua.46193bak` on the game side.

## The hang on slot 1 was a stale save, not a fourth crash (2026-09-16)

Loading save slot 1 never finished. The sampler put the game in a tight loop at
`0x1412aab30`, which walks the Master League calendar **backwards** one day at a time and
stops when the walked date falls below a target date. Reading both dates out of the running
process while it spun answered it in one measurement:

```
walked  y=0 m=10 d=7   (0x070a0000)
target  y=0 m=0  d=0   (0x00000000)
```

The target is **all zero**, and a real date has a month of at least 1, so the walk can never
step below it. That is the whole hang.

The loop, read literally:

```
1412aab17  mov  eax, [r12 + 0x1642a24]     ; the walked date, packed: year 0..15, month 16..23, day 24..31
1412aab0f  mov  ebx, [r12 + 0x1789474]     ; the target date, same packing
1412aab30  cmp  ax, bx ... seta cl         ; cl = walked > target
1412aab5d  jne  0x1412aab7e                ; greater -> ask about competitions 0x21 and 0x3d, step back a day, loop
1412aab5f  cmp  ax, bx / jne 0x1412aabe2   ; less -> leave.  equal -> one more pass, then leave
1412aabd4  call 0x140fd7180                ; the step-back-one-day routine
```

`r12` is the Master League block (`[0x143705e10] -> +0x48`). Both dates are fields of it, and
they are written only by the **new-game** initialiser at `0x1412695b0`, which sets
`+0x178946c`, `+0x1789474` and `+0x1789478` to 2025-08-01 (`0x010807e9`) and derives
`+0x1642a24` from the day counter at `+0x1642a1c`. On a load they come out of the save file.

### Why they came out zero

Slot 1 held a save written on 15 September, under the previous world and the 46,193-player
patch set: **20,128,148 bytes**. Every save this world writes is **30,369,633 bytes**. The
old file simply does not carry the fields the current, larger block expects at those offsets,
so they stayed at zero and the calendar walk had nothing to walk down to.

Proof, in order:

| step | result |
|---|---|
| load slot 2 (saved today, 30.4 MB) | **loads**, day 212 |
| read the two fields after that load | both `0x010807e9` = 2025-08-01 |
| re-save the running season into slot 1 | 30,369,633 bytes, the same size as slot 2 |
| load slot 1 | **loads**, day 212 |

So there is no fourth season-killer. There is a rule: **a save is only loadable by the patch
set and world that wrote it.** The stale file is kept as
`ML00000000.stale-20260915-oldblock` in case it is ever worth reading with the old set.

### The date-floor guard was built for this and is not installed

Before the cause was known, `tools/datefloor.py` was written to stop the year wrapping: the
step-back routine ends in `0x140fd71ef  add word ptr [rbx], bp` with `ebp = 0xffff`, which
takes year 0 to 65535 and sends the walk off on another 65,000-year pass. The patch is
correct -- it was installed, sider logged `applied all 2 patches`, and the year stayed pinned
at 0 instead of sweeping -- but it does not make the loop terminate. It turns a sixteen-bit
wrap into a twelve-month cycle, because the month is still reset to December on every January
step. Neither version exits against a zero target.

It is therefore **removed from `sider.ini` and from `modules/`** (kept as
`fl26datefloor.lua.notinstalled`). The tool stays in the tree as a worked example of a code
cave with a hand-checked `rel32` on both ends, and because a guard here may still be wanted
the day a save is loaded that we cannot re-make. It is not a fix for anything today.

## The fixture table is full, and it truncated a competition (2026-09-16)

G2a has been carrying a missing number: how many of the 2000 global fixture records the
shipped competitions already spend. It is answerable only against a running season, because
saves are encrypted. Measured today, on the loaded 39-league season in `_FL26E39x793p30`:

**All 2000 records are in use. Not one is free.**

The table is at `block + 0x2c20058` in the current set — `0xd65f64` is its **shipped**
offset, and the `-upper` sets move it with the rest of the upper belt
(`0xd0b0ec -> 0x2bc51e0`, delta `0x1eba0f4`). Reading it at the shipped offset returns
player names, because the player array below it now runs to `0x17c * 51729 = 0x12bf13c`;
that is the belt moving out of the way working exactly as designed, not a collision.

### What a record actually is

```
+0x000  u32   the competition this round belongs to
+0x004  16 slots of 32 bytes:
          +0x00 home   +0x04 away   +0x08 match index   +0x0a 0xffff
          +0x0c competition (again)  +0x0e round/slot key
          +0x10 four fillers of 0x07f7ffff
+0x204  u8    how many of the 16 slots this round uses (the rest of the dword is other state)
```

So a record is **one round of one competition**, and the 16 is a round's match limit — which
is the same 16 that G2b exists to raise.

### The table, competition by competition

56 competitions share the 2000 records. Every ordinary league gets its full set — 38 rounds
of 10 matches for a 20-club league, 34 of 9, 30 of 8 — until the end of the array:

| competition | first record | rounds | matches per round |
|---|---|---|---|
| … | … | … | … |
| 140 | 1937 | 38 | 10 |
| 147 | 1975 | 22 | 6 |
| **143** | **1997** | **3** | **16** |

Competition 143 starts at record 1997 and gets **three rounds** before index 1999 ends the
array. Three rounds of sixteen matches is not a competition; it is what was left of one.

**And 143 is ours.** The head field of a record is the regulation id, and the 39 ids in this
world's `date_keys` are exactly 11, 12, 13, 49, 60-66, 69-78, 93, 94, 96, 98, 100-102,
109-114, 121, 138, 139, 140 and **143**. Every one of the other 38 has its full 38 rounds of
10. The thirty-ninth, the last to be drawn, got three.

**So the fixture table is not merely full, it has already overflowed, in the world we run
every day, and our last league is playing three rounds of a season.** G2a stops being a
headroom exercise and becomes a correctness fix for a defect that is live right now.

### What the cap should become

56 competitions average 35.7 rounds. The target world is 40-50 leagues plus the 16-19 new
competitions of `competition-wishlist.md` — call it 90 competitions, so roughly 3,300
records, and a cap of **6,000** leaves real headroom at a cost of 3.0 MB at the shipped
stride (6.2 MB once G2b widens the record to `0x408`). Nothing about that is expensive; the
block already grew by 22 MB.

### And copy B is smaller than the table it copies

The third fixture array, built by `0x140afd660` at `+0x1c4210`, holds **1750** records
(`mov edi, 0x6d6` at `0x140afd6ed`) against the block's 2000. With the block array full,
**records 1750-1999 have nowhere to go** — which is competitions 143 and 147 entirely and a
third of 140. That is the same failure mode as the 596-byte match table before it was
relocated: the copy stops at its own hard-coded cap and the rest is dropped without a word.

This is the answer to the "what does 1750 become" question in `g2b-fixture-record.md`: it is
not a free choice, it has to track the block's cap, and it is **already** losing records
today.

## Sixteen of our leagues never reach the live team array (2026-09-16)

The open question was why roughly seventy of our clubs come out with fewer than thirty
players. Measuring it properly turned up a much larger defect sitting above it.

**On disk everything is correct.** In the world the game is actually running,
`livecpk\_FL26E39x793p30`:

```
Team.bin                1536 rows = 743 shipped + 793 ours, 793 distinct FL names, no repeats
PlayerAssignment.bin    every one of our 793 clubs has exactly 30 players
CompetitionEntry.bin    39 competitions, 20 distinct clubs each, all 793 placed exactly once
```

So nothing we write causes a short squad. The shortfall is made inside the game.

**In the live team array a third of our clubs are simply not there.** Reading the live
array by club name -- the name is a NUL-terminated string at `+0x04` of the `0x690`-byte
record; the `u16` at `+0x00` is the row index in its low bits -- gives eight contiguous
runs of FL clubs:

```
rows    0..59    FL 0001 .. FL 0020   60 rows   league 1, three times over
rows  220..239   FL 0061 .. FL 0080   20 rows
rows  298..437   FL 0081 .. FL 0120  140 rows
rows  534..633   FL 0321 .. FL 0380  100 rows
rows  721..980   FL 0421 .. FL 0680  260 rows
rows 1081..1100  FL 0681 .. FL 0700   20 rows
rows 1113..1172  FL 0701 .. FL 0760   60 rows
rows 1185..1217  FL 0761 .. FL 0793   33 rows
```

693 rows carry an FL name but only **473 distinct clubs** are among them. Counted by league:

```
arrive exactly right (20 rows)   17 leagues   4 7 17 22 23 24 25 29..39
arrive three times  (60 rows)     4 leagues   1 6 19 26
arrive four times   (80 rows)     1 league    5
never arrive at all               16 leagues  2 3 8..16 18 20 21 27 28
```

Sixteen leagues times twenty clubs is exactly the 320 clubs missing. Competitions 130, 131
and 132 each hold twenty distinct clubs on disk -- FL 0001-0020, FL 0021-0040, FL 0041-0060
-- and all three come up in the live array holding FL 0001-0020. The loader is reading one
competition's club list and handing it to several competitions.

**This is what the squad question was really asking.** A club that occupies three rows has
its thirty players spread across them, which is why the live histogram shows clubs at 22,
23 and 25 that are thirty on disk. Fixing the roster counts before this is fixed would be
fixing a symptom.

**What this measurement does not yet separate.** It was taken on a season generated, saved,
loaded and played to day 271, so it cannot by itself say whether the leagues are lost at
season generation or at save and load. The count of clubs with a roster is 1473 both here
and in the fresh-season measurement above, which points at generation, but that is
inference and not a measurement. The check is to generate a fresh season and run the same
name census before anything is saved.

**Corrections to earlier entries.** Two things written above are wrong and are left in place
with this note rather than edited away. The shipped club count is **743**, not 750, and our
clubs do **not** occupy the team rows above it -- the live array is ordered by competition,
so our leagues are interleaved among the shipped ones and FL 0001 sits at row 0. And
`rosterread.py` reads a club id from `rec[8:12]`, which in the live record is part of the
name string; the club numbers it prints are meaningless, though its broken-handle test does
not depend on them and stands.

### The leagues are already gone at the title screen (2026-09-16, same evening)

The entry above could not say whether the sixteen leagues are lost when a season is
generated or when one is saved and loaded. The answer is neither. Running `clubcensus.py`
against a game that had only been **booted** -- sitting in the Select Team menu, no Master
League season in existence -- gives exactly the same picture:

```
live: 1483 named rows, 693 of them ours, 473 distinct clubs of ours
      never arrived: 320      arrived on more than one row: 100

130  x3     134  x4     135  x3     153  x3     160  x3
lost: 131 132 142 143 144 145 146 147 148 149 150 152 154 155 161 162
```

So the defect is in whatever fills the edit block at startup. Season generation and save and
load both faithfully carry forward a team array that was already wrong before either of them
ran. That is worth the retries it took to find, because it moves the search from a ten-minute
season walk to a ninety-second boot.

**The squads are a separate and much smaller matter.** Over our live rows at boot the sizes
are `{30: 675, 25: 6, 24: 3, 23: 9}`. Thirty is the overwhelming norm; the spread seen at day
271 is transfers during play, which is the game working, not a defect. The squad question is
closed by this measurement: nothing needs fixing there.

**What distinguishes a lost league from a working one is its regulation id, and nothing
else.** Read out of `Competition.bin` and `CompetitionRegulation.bin`, all thirty-nine of our
leagues are byte-identical -- area 2, parent 0, conf 2, flags 34, type 4, group 255, twenty
teams, the same eight-byte header -- and differ only in competition id and regulation id:

```
work        49 62 74 93 94 96 98 109 110 111 112 113 114 121 138 139 140 143
repeat      11 x3   60 x4   61 x3   76 x3   100 x3
lost        12 13 63 64 65 66 69 70 71 72 73 75 77 78 101 102
```

Row order does not decide it either: ours are the last thirty-nine rows of the table, 214 to
252, and rows 221-229 are all lost while 242-252 all work.

**Where this stops, and what to try next.** The live regulation array was read to see whether
competitions that share the `+0x80` key are the ones that collide -- several do share a key,
for instance four competitions on `0x89` and five on `0x80` -- but the live record is 0x314
bytes against the 2352 on disk and is plainly a different structure, and no offset in it
carries the disk regulation id, the team count or the type. Until that record is mapped,
anything built on those keys is guesswork and is not recorded here as a finding. The next
step is to map the live regulation record properly, which is now cheap: boot, read, compare
against a world whose regulation ids are varied deliberately.

## The lost leagues are not lost — the wrong club list is written into their block (2026-09-16, late)

The previous section established that sixteen of our thirty-nine leagues never get their
clubs into the live team array, and that this is already true at the title screen.  This
section says what is actually happening in that array.  Everything below was measured on a
game sitting idle at Select Team with no Master League season in existence, set
`teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures`, world `_FL26E39x793p30`.

### The array is one packed block per competition, in regulation order

The live team array has 1600 slots and 1483 of them are named, the last at row 1482.  Rows
are not addressed by team id: the fill walks competitions and appends each competition's
club list to the array, so a competition occupies one contiguous block whose length is its
club count.  Our leagues are interleaved among the shipped ones because the walk is in
regulation-id order, and our regulation ids (11, 12, 13, 49, 60 … 143) are spread through
the shipped ones.  That is why FL 0001 sits at row 0, before the Premier League at row 60:
our first league's regulation id is 11.

### Thirty-nine leagues, thirty-four blocks

| leagues | regulation ids | blocks | what is in them |
|---|---|---|---|
| 1 | 11 | 1 | correct |
| 2, 3 | 12, 13 | 2 | **league 1's clubs again** (FL 0001–0020) |
| 4 | 49 | 1 | correct |
| 5, 6, 7 | 60, 61, 62 | 3 | correct |
| 8, 9 | 63, 64 | 2 | **league 5's clubs again** (FL 0081–0100) |
| 10, 11 | 65, 66 | 2 | **league 6's clubs again** (FL 0101–0120) |
| 12–16 | 69–73 | 5 | **sixteen national teams**, Ireland … Norway, five times over |
| 17 | 74 | 1 | correct |
| 18 | 75 | 1 | **league 5's clubs again** |
| 19 | 76 | 1 | correct |
| 20, 21 | 77, 78 | 2 | **league 19's clubs again** (FL 0361–0380) |
| 22–26 | 93, 94, 96, 98, 100 | 5 | correct |
| 27, 28 | 101, 102 | 2 | **league 26's clubs again** (FL 0501–0520) |
| 29–39 | 109 … 143 | 11 | correct |

Twenty-three blocks are right, eleven hold another competition's list, and five hold a list
that is not ours at all.  The five blocks for leagues 12–16 are rows 454–533: sixteen rows
each holding Ireland, Northern Ireland, Scotland, Wales, England, Portugal, Spain, France,
Belgium, Netherlands, Switzerland, Italy, Czech Republic, Germany, Denmark, Norway — the
same sixteen national teams, written out five times in a row.

This changes what the defect is.  Nothing is dropped and nothing overflows: every block the
walk means to write gets written, at the right place and the right size for whatever list it
resolved.  What fails is the resolution from a regulation to its competition's club list.
The clubs that "never arrived" are simply the ones whose block was filled from the wrong
source.

It also stops being a defect about our data.  A shipped sixteen-team national-team list
landing in five of our blocks is the same fault working in the other direction.

### The round count follows the wrong list too

Leagues 12–16 were noted earlier as carrying 30 fixture rounds live where the other
twenty-club leagues carry 38.  Sixteen teams playing each other twice is exactly 30 rounds.
So the regulation's round list is generated from the club list the block actually received,
not from the twenty clubs the disk assigns.  The regulation and the fixtures agree with each
other and both disagree with the disk.

### The regulations themselves are correct live

Every one of our thirty-nine leagues has a live regulation record at row `id - 1` with the
right name and the right competition: the u32 at `+0x80` holds `0x82`…`0xad`, which are
exactly the competition ids of FL_LEAGUE_01…FL_LEAGUE_39 in `Competition.bin`, including the
jump from `0x88` (136) to `0x8e` (142) where the shipped Scotland and Saudi competitions sit.
All thirty-nine keys are distinct.  The earlier suspicion that several competitions share a
`+0x80` key is **wrong for our leagues** and is retracted: no two of ours collide.

So the chain regulation → competition is intact live, `CompetitionEntry.bin` is contiguous
and correct on disk (our 793 entries occupy file rows 1317–2109 in ascending competition
order, one run per competition), and `Competition.bin` gives all thirty-nine leagues
byte-identical records differing only in the id.  The break is between the competition id and
the entry list the fill reads for it.

### Name and squad agree, so the duplicates are real duplicates

Reading each live row's roster handles back to `PlayerAssignment.bin`: 675 of our 693 live
rows carry the squad their name says they should.  The eighteen that do not are the first six
rows of each of the three copies of league 1 — rows 0–5, 20–25 and 40–45 — where the name is
FL 0001…FL 0006 and the players belong to FL 0005…FL 0009, with 23–27 players instead of 30.
Every other row, in every league, matches.  So a repeated block is a genuine second copy of a
club, not a different club wearing the wrong name, and the earlier worry that the name and
the roster are systematically offset is closed.

### Tools

`tools/clubcensus.py` gives the per-competition arrival table.  The block map, the raw name
dump and the name-versus-roster check were one-off scripts against the same three constants:
name at `+0x04`, roster at `+0x14c`, count at `[+0x426] & 0x7f`.

### The fill writes a contiguous slice of Team.bin, and only the starting row is wrong

Re-expressing the whole live array as slices of `Team.bin` row order settles what the fill
does.  Every block, right or wrong, is a run of consecutive `Team.bin` rows.  That is why the
wrong blocks looked like other competitions' club lists: our leagues are twenty consecutive
rows each, so "league 5's clubs" and "rows 823–842" are the same twenty names.  The block
that held sixteen national teams is the giveaway, because no competition on disk has those
sixteen as its entry list — they are simply `Team.bin` rows 0–15.

So all thirty-nine leagues do get a block.  What the fill gets wrong is the row it starts
from, and for five of them the length as well:

| league | competition | start row it should use | start row it used | length |
|---|---|---|---|---|
| 1 | 130 | 743 | 743 | 20 |
| 2 | 131 | 763 | **743** | 20 |
| 3 | 132 | 783 | **743** | 20 |
| 4 | 133 | 803 | 803 | 20 |
| 5, 6, 7 | 134, 135, 136 | 823, 843, 863 | same | 20 |
| 8, 9 | 142, 143 | 883, 903 | **823**, **823** | 20 |
| 10, 11 | 144, 145 | 923, 943 | **843**, **843** | 20 |
| 12–16 | 146–150 | 963 … 1043 | **0** | **16** |
| 17 | 151 | 1063 | 1063 | 20 |
| 18 | 152 | 1083 | **823** | 20 |
| 19 | 153 | 1103 | 1103 | 20 |
| 20, 21 | 154, 155 | 1123, 1143 | **1103**, **1103** | 20 |
| 22–26 | 156–160 | 1163 … 1243 | same | 20 |
| 27, 28 | 161, 162 | 1263, 1283 | **1243**, **1243** | 20 |
| 29–39 | 163–173 | 1303 … 1503 | same | 20, 33 |

Every wrong start is the start of an earlier one of our competitions, and the five that come
out at row 0 with sixteen rows have lost both numbers.  The shortfall against the correct
start, in rows, runs −20, −40 for the first pair, then −60, −80, −80, −100, then −260 for
league 18, then −20, −40 twice more.

This is a much smaller target than "the leagues do not load".  The fill itself is fine: it
places each competition's block at the right offset in the live array and copies a run of
team rows into it.  What is wrong is one lookup — competition id to the first team row and
the team count — which for sixteen of our competitions returns an earlier competition's
answer, or nothing at all.  The next step is to find that table in the live block; if it is a
fixed-size per-competition index, growing it is the same kind of fix as every other cap in
this project.

(This supersedes the "thirty-four blocks" count in the table above: there are thirty-nine
blocks, but the five for leagues 12–16 are sixteen rows long instead of twenty.)

### The regulation id is what picks a good league from a bad one

Nothing on disk separates the sixteen leagues that come up wrong from the twenty-three that
come up right — not the competition record, not the entry rows, not the rowids, not the row
order.  The one thing they do not share is the regulation id.

That has a precedent in this project.  `tools/mkworld.py` has always refused regulation ids
14, 32 and 33, with the note that they are "free in the file but not in the game: a league
built on one of them shows Libertadores and Asian clubs in its table, so the exe knows them."
Showing somebody else's clubs in the table is exactly the symptom measured here.  So the
honest reading is that the list of ids the exe knows is longer than three, and these sixteen
belong on it:

```
12 13 63 64 65 66 69 70 71 72 73 75 77 78 101 102
```

and the twenty-three that work are

```
11 49 60 61 62 74 76 93 94 96 98 100 109 110 111 112 113 114 121 138 139 140 143
```

They are now listed in `mkworld.py` as `BAD_REG` alongside 14, 32 and 33.  They are listed
rather than derived because there is nothing to derive them from: the next world built will
simply skip them, and the boot census will say whether that was right.

**This costs us leagues.**  Counting the free regulation ids against the ceiling of 175 that
the earlier id experiment established: 52 are free in the tables, and excluding the nineteen
known-bad ones leaves 33.  Twenty-three of those are the ones already proven to work; ten
(144, 145, 146, 152, 153, 154, 170, 171, 173, 174) are untested.  Thirty-three is short of
thirty-nine even if all ten untested ones turn out good, so a thirty-nine-league set cannot
be built out of ids the tables leave free below that ceiling.

Moving upward does not help, and the earlier id experiment already says so.  Four worlds were
built there, identical apart from the ids they handed their leagues, and walked down the
Select Team list one keypress at a time: the holes below 143 put **twelve** of our leagues in
the list, ids 144–204 put **five**, and ids 176–214 put **one**.  So the ids we already use
are the best range available, and the answer to a short id budget is fewer leagues, not
higher ids.  That is a decision for the user, not a fix to apply.

Two symptoms, one cause.  The twelve leagues that reached the Select Team list in that
experiment — regulation ids 11, 60, 61, 62, 93, 94, 96, 98, 138, 139, 140, 143 — are all
inside the twenty-three whose club tables are correct here.  Appearing in the menu is the
stricter test of the two, and both tests agree about which ids are sound.  The experiment
also tried ids 144, 145, 146 and 152 and found leagues built on them in the list, so four of
the ten untested ids above have already shown themselves good once.

One caution about reading that experiment backwards.  In the world built on the holes below
143 — the world measured here — only twelve leagues reached the Select Team list, yet
twenty-three have a correct club table.  So a league missing from the menu is not proof that
its regulation id is bad; the menu is the stricter test.  The ids at or above 144 that have
actually been *seen working* are 144, 145, 146, 152 and 177, the last one twice, which also
means the ceiling of 175 is not a wall so much as the point where the good ids thin out.  The
right comparison between ranges is the count — twelve against five against one — not the
absence of any particular id.

## One region cannot hold thirty-nine leagues (2026-09-16, later still)

**The two sections above blame the regulation id.  That was wrong, and this section
replaces that conclusion.**  The id lists stay on the record because the measurements behind
them are sound — twenty-three leagues load correctly and sixteen do not, and which ones is
exactly as tabulated — but the reason is not the id.  It is the region.

Every competition row carries a region slot at `Competition.bin +3`, the thing the menus
group countries by.  Shipped rows use it in steps of eight, and no shipped region holds more
than ten competitions.  All thirty-nine of our leagues were filed under region 16, England,
which already had five of its own — **forty-four competitions in one region**, four times
what the game has ever been asked to hold.

The test was a single change and nothing else.  The world `_FL26E39x793p30` was copied to
`_FL26Reg39` and thirty-nine bytes were rewritten: our leagues were dealt round-robin over
the twenty-two region slots the shipped data already uses, other than 8 and 16, so no region
holds more than eleven competitions.  Same clubs, same players, same competition ids, same
regulation ids, same patch set, same everything.  Booted to the title screen and censused:

```
on disk: 743 shipped rows + 793 ours, 793 distinct names of ours
         our squad sizes: {30: 793}
live: 1536 named rows, 793 of them ours, 793 distinct clubs of ours
      never arrived: 0      arrived on more than one row: 0
live squad sizes over our rows: {30: 793}
```

Every one of the thirty-nine leagues, all twenty clubs of each, every club once and once
only, thirty players apiece, and 1536 live rows against 1536 rows on disk.  Nothing missing,
nothing duplicated.

So the defect was never about which ids we chose.  Forty-four competitions in one region
overruns something, and the overrun shows up as a club table whose blocks start from the
wrong row — which is why it looked like a per-id fault: with the leagues in id order, which
ones fall over is decided by where they sit in an overfull region, and that is stable from
boot to boot.

### What this changes

* `mkworld.py` keeps refusing only 14, 32 and 33 again; the sixteen ids added earlier tonight
  are removed, because they are not bad ids.
* `mkworld.py` gains `--regions A,B,C`, which deals the leagues round-robin over a list of
  region slots.  `--region` still takes a single one.
* The earlier id experiment — twelve leagues in the Select Team list for ids below 143, five
  for 144–204, one for 176–214 — was measured on worlds that *also* had every league in
  region 16.  Its ranking of id ranges may well be an artefact of the same overrun and should
  be re-run now that the regions are spread.
* The league count is not capped at twenty-three.  Thirty-nine work.

### Still open

How many competitions one region can actually hold.  Eleven is proven good and forty-four is
proven bad; the shipped maximum is ten.  Worth finding, because it decides how thinly the
leagues have to be spread — and whether a region can be given more room the way every other
cap in this project has been.

## Correction: it happens during season creation, not at boot (2026-09-16, later still)

Two claims above are wrong and this section withdraws them.

**The club table is perfect at boot.** Booting the unchanged world `_FL26E39x793p30` with the
same patch set and censusing at the title screen:

```
live: 1536 named rows, 793 of them ours, 793 distinct clubs of ours
      never arrived: 0      arrived on more than one row: 0
live squad sizes over our rows: {30: 793}
```

Walking as far as Master League → New → Select Team and censusing again from the league list:
identical, still 793 of 793.  Then finishing the walk — picking a league, a club, the manager
screens, the board meeting — and censusing at the hub:

```
live: 1483 named rows, 693 of them ours, 473 distinct clubs of ours
      never arrived: 320      arrived on more than one row: 100
```

with exactly the same leagues lost and the same ones repeated three and four times as the
table further up.  So the defect is in **season creation**, and the earlier statement that it
was "already true at the title screen, before any season exists" is withdrawn: that census
was taken on a game that had already been through a new-season attempt, not on a freshly
booted one.  The check is not ninety seconds after all; it costs the full walk.

**The region experiment proves nothing yet.**  Four worlds were built tonight moving our
leagues out of region 16 into other region slots, and all four came up clean — but every one
of them was censused at the title screen, where the unchanged world is clean too.  The
comparison was between a title screen and a hub.  The test is being re-run the only way that
can answer it: create a season on the spread-region world and census at the hub.

What still stands is everything measured on the post-generation game, because that state
reproduces exactly: the live array is one packed block per competition in regulation order,
the wrong blocks are contiguous slices of `Team.bin` starting from the wrong row, five of
them start at row 0 with sixteen rows, and name and roster agree on 675 of 693 rows.  Those
are facts about what season creation leaves behind.  Only the claim about *when* it happens,
and the conclusion drawn about regulation ids, were wrong.

## The region is not it either (2026-09-16, later still)

The region hypothesis has now been tested the only way that can answer it, and it failed.

`_FL26Reg39` — the world whose sole difference from `_FL26E39x793p30` is thirty-nine bytes at
`Competition.bin +3`, dealing our leagues round-robin over twenty-two region slots so that no
region holds more than eleven competitions — was booted and taken through a complete Master
League new-season walk: league list, club, manager screens, board meeting, hub.  The walk
finished cleanly, day 232, 14747 matches in the table.  Censused at the hub:

```
live: 1483 named rows, 693 of them ours, 473 distinct clubs of ours
      never arrived: 320      arrived on more than one row: 100
  130 x3   134 x4   135 x3   153 x3   160 x3
  131 132 142-150 152 154 155 161 162  all lost
live squad sizes over our rows: {22: 2, 23: 7, 24: 3, 25: 4, 27: 2, 28: 1, 29: 4,
                                 30: 434, 31: 32, 32: 189, 33: 7, 34: 8}
```

That is the unchanged world's result, to the club.  The same sixteen leagues lose their
clubs, the same five are repeated the same number of times, the same 473 survive.  Spreading
the leagues over regions changes nothing at all.

So the section above titled "One region cannot hold thirty-nine leagues" is withdrawn in
full.  Its measurement was the invalid title-screen one; on the test that matters the spread
world and the crowded world are indistinguishable.  Forty-four competitions in one region may
still be more than the menus were ever meant to hold, but it is not what breaks the club
table.

### What is left standing

Three candidate causes have now been eliminated by measurement rather than by argument:

* **the data on disk** — clubs, players, entries, rowids, ordering, competition records: all
  verified correct, and the same data produces a perfect table at boot;
* **the region slot** — spread over twenty-two regions, identical failure;
* **the competition id** — the earlier id experiment moved the competition ids and left the
  regulation ids alone, and the same twelve leagues came through.

The one variable that has ever changed the outcome is the **regulation id**.  Four worlds
differing only in the ids they handed their leagues gave twelve, five and one league in the
Select Team list.  That makes the id the live suspect again — but the id lists written into
the superseded section above must not be trusted as they stand, because they were derived
from a single world.  What they cannot distinguish is an id whose *value* the exe treats
specially from an id whose *position* among all the regulations decides the outcome.  The two
predict different fixes: a bad-id blacklist in one case, a rule about spacing or ordering in
the other.

Settling that needs an experiment that moves an id without moving anything else, which is why
the next test swaps the competition each of four good/bad regulation pairs points at —
`CompetitionRegulation.bin +0x08`, one byte each — and asks whether the failure follows the
id or stays with the league.

And everything remains conditioned on the timing: the table is perfect at boot and perfect at
the Select Team list.  Whatever the id decides, it decides it inside season creation.

## A world that survives season creation: twenty-three leagues, correct to the club (2026-09-16, night)

The first configuration to come out of season creation with an intact club table.

`_FL26Good23` was built from the shipped tables with `mkworld.py --leagues 23 --clubs 20
--reg-ids 11,49,60,61,62,74,76,93,94,96,98,100,109,110,111,112,113,114,121,138,139,140,143`
— the twenty-three regulation ids whose leagues came up correct in the thirty-nine-league
world — and `mkplayers.py --per 30 --cap 51729`.  1203 clubs, 41727 players.  The edit save
was moved aside first, because it carries whole competition rosters and is read instead of
`CompetitionEntry.bin`.  Same patch set as every other run, unchanged: the set's `date_offsets`
is a lookup keyed by regulation id, so the sixteen keys that no longer exist are simply never
asked for.

Walked all the way through a new Master League season — league, club, manager screens, board
meeting — and censused at the hub:

```
on disk: 743 shipped rows + 460 ours, 460 distinct names of ours
         our squad sizes: {30: 460}
live: 1186 named rows, 460 of them ours, 460 distinct clubs of ours
      never arrived: 0      arrived on more than one row: 0
```

and every one of the twenty-three competitions shows twenty clubs on disk, twenty distinct
live, twenty rows live.  Nothing lost, nothing duplicated, after the step that had destroyed
the table in every previous run.  (Live squad sizes spread from 29 to 34 — season creation
moves players between clubs, which is a different matter and not a fault.)

`mkworld.py` gained `--reg-ids` for this: the id list is now nameable rather than derived,
because it is the one variable that has ever changed the outcome, and naming it is usually a
way to try ids the default allocator would refuse.

### What this does not yet settle

Two things changed between this world and the broken one: the regulation ids, and the number
of leagues.  Twenty-three leagues on good ids work; thirty-nine leagues including sixteen
suspect ids do not.  Whether the cure was the ids or the smaller count is untested, and the
two point at completely different fixes — a blacklist in one case, a hard league limit in the
other.

The test that separates them holds the count at twenty-three and flips the ids: a world of
twenty-three leagues built on the sixteen suspect ids plus seven known-good ones.  If exactly
those sixteen come up holding another league's clubs, the id is the cause.  If all twenty-three
load, the count is.

## It is the regulation id, and the league count has nothing to do with it (2026-09-16, night)

The control world settles it.  `_FL26Bad23` holds exactly as many leagues as `_FL26Good23`
— twenty-three, twenty clubs each, thirty players each, same base tables, same patch set, same
walk — and differs in one thing: the regulation ids are the sixteen suspect ones plus seven
known-good, instead of twenty-three known-good.  Censused at the hub after a completed season
creation:

```
live: 1146 named rows, 360 of them ours, 200 distinct clubs of ours
      never arrived: 260      arrived on more than one row: 100
```

League by league, against the id each was built on:

```
comp 130 reg 11  good   ok (list repeated 3x)     comp 149 reg 75  BAD   all 20 lost
comp 131 reg 12  BAD    all 20 lost               comp 150 reg 77  BAD   list repeated 2x
comp 132 reg 13  BAD    all 20 lost               comp 151 reg 78  BAD   all 20 lost
comp 133 reg 49  good   ok                        comp 152 reg 101 BAD   list repeated 2x
comp 134 reg 60  good   ok (list repeated 4x)     comp 153 reg 102 BAD   all 20 lost
comp 135 reg 63  BAD    all 20 lost               comp 154 reg 109 good  ok
comp 136 reg 64  BAD    all 20 lost               comp 155 reg 110 good  ok
comp 142 reg 65  BAD    list repeated 2x          comp 156 reg 111 good  ok
comp 143 reg 66  BAD    all 20 lost               comp 157 reg 112 good  ok
comp 144-148 reg 69-73  BAD  all 20 lost each
```

**Every one of the seven good ids produced a correct league.  Not one of the sixteen suspect
ids did** — thirteen lost all their clubs outright, and the other three came up with their
club list copied onto a second block, which is the other face of the same defect: a block that
starts at the wrong row of `Team.bin` holds somebody else's clubs, and that somebody's list is
then counted twice.

Twenty-three leagues work on good ids and fail on bad ones.  So the league count is not the
cause, the regulation id is, and the twenty-three-league world's clean result was the ids
rather than the smaller world.  `BAD_REG` in `mkworld.py` goes back to nineteen ids —

```
14 32 33  and  12 13 63 64 65 66 69 70 71 72 73 75 77 78 101 102
```

— this time on a controlled measurement rather than on a single world's coincidence.

### What it costs, and what is left to measure

Free regulation ids below the 175 ceiling: 52.  Minus the nineteen bad ones: **33**.  Of those,
twenty-three are now proven good over a whole season creation, and ten are untested:

```
144 145 146 152 153 154 170 171 173 174
```

Four of them — 144, 145, 146, 152 — were seen carrying a league into the Select Team list in
the earlier id experiment, which is the stricter of the two tests, so the ten are not a wild
guess.  If all ten hold, thirty-three leagues fit; if none do, twenty-three is the number.
Either way the answer is a league count, and the way past it is F0 — the 175 ceiling — not a
better choice of ids.

A world of thirty-three leagues on all thirty-three candidate ids is the next measurement, and
it answers the question in a single walk: whichever of the ten come up holding their own clubs
are good ids.


## The club list is written into the block by id, and the id decides whose clubs it gets (2026-09-17)

Two worlds ago the verdict was "the regulation id decides". That was an observation, not a
mechanism, and it left the obvious question open: the data for all thirty-nine leagues is
byte-identical apart from two numbers, so what does the exe know about an id that the data
does not say?

Measured, in order:

**The data really is identical.** In `_FL26E39x793p30` every one of the thirty-nine
competition rows carries region 16, flag 34, type 4 and twenty clubs; only the regulation
id and the competition id differ. Whatever separates a good id from a bad one is in the
exe.

**The block is right until Master League setup.** A reader that walks the live regulation
array (`block+0x1c84230`, stride `0x314`, count at `block+0x2ebf968`) and compares each
record's team handle list against `CompetitionEntry.bin` reports zero mismatches at the
title screen, on the Select Team list, and every six seconds through the whole approach to
season creation. A team handle is `(team key << 14) | row`, confirmed against the shipped
Premier League: its handles `0x194000, 0x1ac000, 0x3f9c000, 0x4150000, …` shift down to
`101, 107, 4071, 4180 …`, which is competition 9's disk team list exactly.

**It goes wrong in one step, at setup.** At the moment the Master League mode builds its
own copy the array is replaced -- 253 records become 238 -- and sixteen of our leagues come
out of that replacement holding another league's clubs:

    reg 12, 13        <- reg 11's clubs      (competition 130)
    reg 63, 64, 75    <- reg 60's clubs      (competition 134)
    reg 65, 66        <- reg 61's clubs      (competition 135)
    reg 77, 78        <- reg 76's clubs      (competition 153)
    reg 101, 102      <- reg 100's clubs     (competition 160)
    reg 69 - 73       <- a generated list of sixteen

That is exactly the BAD list of 2026-09-16, arrived at from the other end. The names, the
competition ids and the team counts stay correct throughout; only the club list moves.

**The shipped game does the same thing on purpose.** Scottish Premiership is regulation 133
with 134 "First Phase", 135 "Top Six" and 136 "Bottom six" under the same competition 137,
and those three inherit their clubs the same way in the same step. Our bad ids are being
caught by the mechanism that serves them: the exe holds its own idea of which regulation is
a phase of which, keyed by regulation id, and reusing one of those ids for a standalone
league hands the league to its parent.

**Where the write happens.** A hardware write watchpoint on one regulation's team list
(`block+0x1c84230 + slot*0x314 + 0x170`) catches every write to it. There are two, and both
go through `0x141522b50`:

    0x141522b50  set_regulation_teams(u16 regid, vector<u32>* handles, u8 flag)
                   rsi = 0x1414bc860(block, regid)     ; plain lookup by id, no aliasing
                   0x1414c9740(rsi)                    ; clear the list
                   for h in *handles: 0x1414c9a10(rsi, h)
                   0x1414ca020(rsi, flag); 0x1414c97a0(rsi)

The caller decides what to hand it. `0x14135c020` walks a vector of 0x30-byte schedule
entries (regulation id at +0x00, flag at +0x0a), calls `0x141353cd0` to work out that
regulation's clubs and passes the answer to `0x141522b50`. `0x1414bc860` itself is innocent
-- it is a linear search for the id, patched by our set like every other one. The inherited
club list is already in the vector `0x141353cd0` returns.

Also settled on the way, and worth keeping:

- `0x141261ca0` is the regulation copier used at stage 3 of the data creation thread
  (`0x14126f7e0`, return address `0x14126f88d`). It copies the team list with an xor
  bitfield trick in two halves, `& 0x3fff` and the rest -- verbatim, forty-eight slots.
- `0x1412647b0` builds the mode's regulation vector. Its dispatch is a jump table at
  `0x141264cf4` on `[mode+0x7c] - 9`; every site in it that touches the regulation array or
  its count is in our patch set, including the two `cmp …, 0x12c` bounds.
- The 28-entry table at `0x14297d800` is not an alias table for phases: it is the
  season-variant table, each entry listing `id + 1024*k`.
- The 165-entry table at `0x1434fdf00` carries no group list for any of our ids -- the
  pointer at +0x08 and the count at +0x10 are zero for all of them.

### The usable id pool, measured in a world of thirty-nine (2026-09-17)

`_FL26T39` put the twenty-three proven ids together with the ten untested ones and with
176-181, thirty-nine leagues in all. After Master League setup only three of ours came up
holding another league's clubs: **152, 153, 154**. So 144, 145, 146, 170, 171, 173 and 174
are good, and -- against the earlier belief that nothing above 175 works -- **176 to 181 all
work**. That belief came from a different test, in the menus, and does not hold for this
failure. The pool is therefore comfortably larger than thirty-nine without touching the
ceiling at 175.

### The board meeting reads an empty table, and nullguard3 is needed for generation after all (2026-09-17)

Two crashes stood between a correct thirty-nine-league world and a season that finishes
generating, and both are now closed.

**`0x140cd6a21`, at the board meeting.** `seasonnew.py` had been turning nullguard3 off on
every boot, on the belief that it broke season generation. That belief was already retracted
in this file -- the runs it came from died of the intermittent sky bake, a different fault --
but the switch stayed off. The board meeting reads the same schedule nullguard3 guards, and
died there. `seasonnew.py` now honours `FL26_GUARD3=on`, and with the guard on the walk went
eight confirmations further.

**`0x14128a3aa`, eight confirmations later.** Dump FL_2026.exe.3756.dmp, `rax = 0`, access
violation reading address 4:

    14128a3a3  mov   rax, qword ptr [rbp - 0x50]   ; begin
    14128a3a7  mov   r8d, esi
    14128a3aa  mov   r9d, dword ptr [rax + 4]      <- faults when begin is null
    14128a3ae  mov   ebx, dword ptr [rsp + 0x40]
    14128a3b2  mov   r11, qword ptr [rbp - 0x48]   ; end
    14128a3b6  cmp   rax, r11
    14128a3b9  je    0x14128a411                   ; the empty case, already written

The function searches a vector of eight-byte (handle, value) pairs for the entry whose
handle matches `ebx & 0x3fff`, and answers -1 when there is none. It pre-loads the first
pair before testing that there is one. Nothing is corrupt; the table is simply empty.
`sider/fl26nullguard7.lua` redirects the eleven bytes at `0x14128a3a3` to a trampoline at
`0x14252e8a0` that does the same two moves, tests the pointer, and takes the function's own
not-found branch when it is null. With it installed the season generates: the hub comes up,
3015 matches in the table, no day anywhere near the 280 cap.

**What the census then showed.** Thirty-eight of the thirty-nine leagues hold exactly their
twenty clubs, each club on one row, no duplicates anywhere -- the first time that has
happened. The thirty-ninth, regulation 177, lost nineteen. It is a different failure from
the inheriting ids: **177 is not in the live regulation array at all** after setup, so its
clubs have nowhere to arrive. It goes in `BAD_REG` with its own note, and 185 takes its
place.

### Thirty-nine leagues, every club in its own league (2026-09-17)

`_FL26G39` on the id set

    11 49 60 61 62 74 76 93 94 96 98 100 109 110 111 112 113 114 121 138 139 140
    143 144 145 146 170 171 173 174 176 178 179 180 181 182 183 184 185

with nullguard3 and nullguard7 both on, taken through Master League season creation to the
hub. The census reads:

    on disk: 743 shipped rows + 780 ours, 780 distinct names of ours
    live:    1506 named rows, 780 of them ours, 780 distinct clubs of ours
             never arrived: 0      arrived on more than one row: 0

All thirty-nine competitions report twenty clubs on disk, twenty distinct live, twenty rows
live. The season itself generated: 15428 match ids in the daily lists, the busiest day at
196 of the 280 cap. 185 is good and goes in the map as such.

### A new mid-season fault, reading past the end of the edit block (2026-09-17)

Four days into the first season of `_FL26G39` the game died at fault offset `0x4adc49a`,
VA `0x144adc49a`, in `.impdata` -- the protector's region, the same region the intermittent
sky bake lives in. Dump FL_2026.exe.8104.dmp. What makes this one worth a note is the
address it read:

    access violation: read of 0x7ff4e5260294
    rdi = 0x7ff4e2200010   (the edit block)
    rcx = 0xbcb2 = 48306   (an index, and below the 51729 player cap)
    rax = rbx = rsi = 0x7ff4e4a9e55c  = block + 0x289e54c

`0x7ff4e5260294` is `block + 0x3060284`, and the block ends at `0x3053be8` -- so the read is
0xc69c bytes past the end. Callers in `.trace`: `0x1415151d6`, `0x14151b25d`, `0x14134370c`,
`0x1414d63e6`. `0x14151b230` is a small wrapper that fetches a value with `0x140afa4f0` and
passes it as an id to `0x141514cd0` (17 callers, the ' ' string -- a name lookup); its caller
`0x141343570` loads the NOTEAM sentinel from `0x14351ae44` two instructions earlier, so this
is on the team-name path.

No stride and base fitted to (48306, block+0x3060284) matches a table we know, so the index
is not simply too large for a table we have grown. Recorded and left: the first question is
whether it is deterministic, which one more season run answers for free.

Practical lesson from the same run: `seasonplay.py --until N` without `--new` will try to
recover from whatever is in the slot, and a save from another world is worse than no save.
Start a fresh world's season with `--new`, which checkpoints before the first chunk.

## 2026-09-17 -- the mid-season wall is seventeen megabytes of code nobody attributed

The season died in the spring three times running, always at the same instruction,
`0x144adc49a`, always reading an address a little past the end of the edit block.
Padding the block so the read would land inside it did not help: the fourth run got
five days further and died the same way.  The pad was the wrong shape of answer,
because the read is not a single stale pointer.  It is a loop.

`.impdata` is a 398 MB section, and the earlier note that it holds "the protector's
virtualised handlers" is only half right.  It is not encrypted and it is not
virtualised.  It holds whole ordinary functions the protector moved out of `.trace`,
byte for byte, reachable through one-line thunks: `0x14151c240` is nothing but
`jmp 0x144adc450`.  The bytes in the crash dump and the bytes on disk are identical,
and they disassemble on the first try:

    144adc470  mov    r9d, dword ptr [rdi + 0xd0bcf4]      the regulation count
    144adc47d  test   r9d, r9d
    144adc480  je     0x144adc4ad                          none -- give up
    144adc482  movzx  r10d, word ptr [rax + 4]             the id we are looking for
    144adc490  mov    ecx, r8d
    144adc493  imul   rdx, rcx, 0x314
    144adc49a  cmp    word ptr [rdx + rdi + 0xc12e9c], r10w   the id field of record ecx
    144adc4a3  je     0x144adc4ba                          found it
    144adc4a5  inc    r8d
    144adc4a8  cmp    r8d, r9d
    144adc4ab  jb     0x144adc490

A linear search of the regulation array by id, with `rdi` the edit block.  Both
offsets it uses are the shipped ones: `+0xc12e9c` is `arrays.regulations.base_old`
and `+0xd0bcf4` is the count that goes with it.  Every tool in this repository walks
the `.trace` attribution, `.impdata` is not in it, so when the set moved the
regulation array to `+0x1c84230` and its count to `+0x2ebf968`, this copy of the
search did not move with it.

So the count it reads is not a count.  It is whatever our layout happens to put at
the shipped offset, and in the run that died it was 48472.  The loop then walked
48472 records of 0x314 bytes off the shipped base and left the block entirely.  No
tail pad can catch that; the walk is unbounded by construction.

The fix needs no new judgement, only a place to look.  `tools/impscan.py` reads the
generated set, collects every `0x... -> 0x...` the patches already record in their
own `why` notes, and hunts those shipped offsets through `.impdata`.  A four-byte
value turns up by chance in a section this size, so a hit only counts if a straight
decode forward from a front door -- an address `.trace` actually jumps or calls into
-- walks onto it.  That test matters twice over: it throws out four coincidences in
data, and it settles the instruction boundary, which decoding backwards cannot.
`cmp word ptr [rdx + rdi + 0xc12e9c], r10w` reads perfectly well as a three-byte
shorter `cmp dword` if you start late, and a patch written against that reading
would never match.

**Which offsets are worth hunting** is the one place this needed a criterion rather
than a list, and the first one tried was wrong.  Chasing every `0x... -> 0x...` a
patch mentions works on this set and falls apart on the next: `--slots32` rewrites
the fixture record's shape and says `0x208 -> 0x408`, and a two-byte-ish constant
turns up by the hundred in 398 MB.  That run produced 249 patches instead of 23,
every extra one wrong.

The honest test is what actually makes an offset dangerous: the set moved it out of
the shipped block and into the grown tail.  So `0 < old < 0x1877068 <= new`, and
nothing else qualifies.  That is also what settled the one genuinely ambiguous case.
`0xadf4bc` is answered two ways by the set -- `0x1877070` for the 115 sites that
relocate the team array, and `0x12bf13c` once for a table length inside the mode
copy -- and the second answer is not a relocation at all, so the test drops it and
the team array's `.impdata` copy can be patched after all.

**Twenty-four sites, in six groups.**

| offset | moves to | sites | what it is |
|---|---|---|---|
| `0xadf4bc` | `0x1877070` | 1 | the team array |
| `0xc12e9c` | `0x1c84230` | 8 | the regulation array |
| `0xd0bcf4` | `0x2ebf968` | 9 | its count |
| `0xd0bce8` | `0x2ebf95c` | 1 | the count beside it |
| `0xd0bd04` | `0x2ebf978` | 3 | upper1 |
| `0xd66168` | `0x2bc53e4` | 1 | the fixture count |
| `0x16038a8` | `0x245b2b0` | 1 | a rec596 side table |

All twenty-four sit between `0x14407f` and `0x144b24` -- a single neighbourhood,
which is what a run of functions moved together looks like.  Sixty-two offsets pass
the test and are hunted; the other thirty-eight have no copy out there at all.

The set goes 2736 -> 2760 patches.  Nothing else changes: same block size, same
bases, same 2736 existing patches byte for byte, so a save written before the fix
still loads after it.

The tail pad from earlier today stays.  It is no longer load-bearing, but a read
that lands in our own zeroed memory is still better than one that does not, and the
next unattributed site -- if there is one in a section this size -- will be easier
to find alive than in a dump.

## 2026-09-17 -- the calendar day, re-measured in the world of thirty-nine

The last measurement of the busiest calendar day was 251 of 280, taken before the
world had its full complement of leagues.  The generated season in `_FL26G39` reports
it directly, and it is worse but still inside the wall:

    fullest days: day 37 = 243, then 210 on nine separate days (18, 23, 25, 36, 39,
    268, 270, 305, 326, 340, 361), day 268 = 206

**243 of 280.**  Thirty-seven ids of headroom on the worst day, and a flat ceiling of
210 on the ordinary busy ones -- which is what thirty-nine leagues of twenty clubs
playing on the same weekend looks like: ten matches a league, and most leagues share
a match day.

So the day cap is not the next wall at thirty-nine leagues, but it is close enough
that it becomes one at about forty-five.  The spread the set applies (`--date-offsets`,
one offset per competition) is what is holding it down; without it the same fixtures
pile onto the same weekday and the scheduler drops the overflow silently.

## 2026-09-17 -- the season reaches the end of the year, and the manager is sacked

With the twenty-four `.impdata` offsets patched, the calendar ran **day 232 to day 364
in a single twenty-minute chunk, sixteen moves, no crash**.  The same world on the
same save had died at day 237 and again at 246 an hour earlier, and at 268-271 on
earlier nights.  The spring wall is gone, and it was never a wall in the spring: it
was whatever day the loop first ran off the end of the block.

The league table is real.  Our twenty clubs in FL League 26, ordered on points:

    4  FL 0517  29    8  FL 0516  26   11  FL 0507  23
    5  FL 0520  29    9  FL 0501  25   12  FL 0510  22
    6  FL 0513  29   10  FL 0504  23   13  FL 0509  21
    7  FL 0518  27

Fixtures are scheduled into January (29/12/2025, 1/1/2026, 5/1/2026, 9/1/2026), which
is what a season crossing the new year is supposed to look like.

**The new obstacle is not a defect.**  FL 0501 finished the calendar year ninth, and
the board let the manager go.  The game then blocks the calendar behind a modal:

    You are yet to decide which team you want to manage next season.  Please go to
    [Manager's Office] -> [Management Career] -> [Manager Offers], then select one
    from your list of managerial offers.

Dismissing it returns to the hub, and it comes back on the next nudge.  That is also
why the checkpoint failed four times running with "could not reach the save list":
`seasonsave.py` walks System -> Save and the modal takes the first press each time.

Two things follow for the walk, and neither is a patch:

1. `seasonsave.py` must clear a modal before it counts its steps, not assume the hub.
2. `seasonrun.py` needs a manager-offer step -- Manager's Office, Management Career,
   Manager Offers, take one -- or the run ends every year at the same place.

Worth saying plainly: being sacked is the ordinary Master League outcome of finishing
ninth, and the fact that it happened *to us*, on our own clubs, in our own league, on
a table the game computed itself, is the strongest evidence yet that the thirty-nine
leagues are not a display trick.

## The way out of the sacked hub, walked and measured

The gate described above has an ordinary answer, and on 17 September it was walked by hand,
one screenshot per press.  The path is now in `seasonrun.takeoffer()` and is called both from
the stall ladder and from `seasonsave.py` when a panel is still up after parking.

    the panel        enter                    dismisses it
    the hub          circle                   unfocus the Forward Time panel.  This is the
                                              step nothing worked without: while that panel
                                              has focus the arrows move inside it and the
                                              menu bar never moves, which is why three
                                              `right`, a `left`, two `up`, keyboard `e` and
                                              pad `r1` all left the bar reading tab 0.
    the bar          right, to tab 3          Manager's Office.  Team Management and My Team
                                              Info are greyed out and the bar skips them, so
                                              one `right` from Forward Time lands on 3.
                     cross                    Messages / Management Career / ...
                     down, cross              Management Career -- Messages is first, and
                                              confirming straight away opens the inbox, which
                                              has a Return and no Confirm.
    the card grid    down, right, cross       Manager Offers, bottom right, with the bell
    Category         cross                    Club Teams -> the List of Offers
    the list         down x n, cross          Accept / Game Plan / Squad List, on Accept
                     cross, cross             "Accepted the role of X", then OK

Four offers were waiting: FL 0504, Zulte Waregem, FL 0518 and Club Atlético Belgrano.  Two of
them are ours, and the list prints their competition as **FL League 26** -- the first evidence
from inside the game that a new league is a career destination the AI recruits from, not just
a table that computes.  FL 0518 was accepted and the game confirmed the role.

### What it cost to learn, and the wrong diagnosis in between

Day 364 was then thrown away, and the reason is worth more than the day was.

Mid-walk, every call started answering "the game window is not there".  The process was
alive; `Get-Process` said `MainWindowHandle 0` and a working set falling from 806 MB to 130
MB, and an `EnumWindows` sweep found no top-level window for the pid at all.  That reads
exactly like a game tearing itself down, so it was written up as one -- an uncapped
`while screen.bartab() != 0: press right` loop left running in the background, a dropdown
eating every arrow, the stray presses walking onto System and confirming an exit.  The game
was killed on that basis and the season restarted.

**That diagnosis was wrong, and the evidence for it could never have been right.**  Every
shell here runs in **session 0**.  A session 0 process cannot see session 1's windows, so
`MainWindowHandle` and `EnumWindows` return nothing for a perfectly healthy game, every
time, and a full-desktop screenshot from session 0 comes back as a blank 1024x768 -- which
is session 0's own desktop, not the monitor.  None of those three readings was evidence of
anything.

What had actually happened is the failure project memory already names as the commonest one
in this whole setup: the **session 1 helper agent had died**.  `session1.py ping` said so in
one line -- "the agent is not answering in session 1" -- and `session1.py start` brought
everything back at once: the same game process, at the title screen, healthy.  It had never
been in trouble.  The game was then killed by hand, for nothing.

So the rules are:

1. When a call says "the game window is not there", **ping the session 1 agent before
   concluding anything about the game.**  It is one command and it is the likeliest answer.
2. Never read a game's health from session 0 -- not `MainWindowHandle`, not `EnumWindows`,
   not a desktop screenshot.  The one honest screenshot is the one the agent takes.
3. Never loop on a screen read without a step cap.  `seasonrun.barto()` caps at six.  This
   one stands on its own merits; it was not what ended the session.

The checkpoint on disk is still day 232 in slot 2, which is a twenty-minute re-run now that
the mid-season wall is patched -- the whole point of having fixed the wall.

## Stage C, the part that can be answered without the game

`mkcup.py` now builds the cup world, and two of the three unknowns in the Stage C plan turn
out to be answerable from the tables alone.

**The cup world.** `_FL26G39Cup` is `_FL26G39` plus one knockout: **FL Cup 01, competition
174, regulation 186, region 16, type 3, bracket 16**, entered by the sixteen clubs
71578-71593, which are the first sixteen of FL_LEAGUE_01.  Sixteen into a bracket of sixteen
is BELGIUM_CUP's own shape, chosen deliberately for a first test -- a bracket smaller than
the entry list is legal (Coppa Italia is 20 against 40) but it is a second unknown, and one
at a time.  131 competitions, 254 regulations, 2113 entries.  It is built and sitting in
livecpk; it is deliberately **not** in `sider.ini` yet, because Stage B has the machine and
enabling a root means restarting the game.

**The id defaults were wrong.** `mkcup.py` defaulted to cid 150, and a 39-league world owns
competition ids 130-168 with the shipped rows carrying on to 173.  A cup built with the old
default would have silently overwritten one of our own leagues.  It now allocates the first
free id the way `mkworld.py` does: cid 174, regulation 186.

**The calendar dword copies itself.**  This was the open question in the plan -- whether
cloning a shipped cup carries the calendar field, or whether it has to be set by hand.
Measured on the built world, at `+0x10` of the regulation row:

    FL Cup 01      reg 186  type 3  calendar 0x08c00220
    BELGIUM_CUP    reg 122  type 3  calendar 0x08c00220     <- identical
    FL_LEAGUE_01   reg  11  type 4  calendar 0x0020a020     <- a league's is a different shape

So the wholesale row copy does carry it, and a cup does not need the hand-editing a league
needed.  What that does not settle is whether the game honours it: the field is right, and
whether a season draws the cup from it is what the run has to show.

Left for the game, unchanged from the plan: does the cup appear, is it drawn, does it have
dated rounds, does it enter our club, and what does it do to the per-day match count -- a cup
adds midweek dates, which is exactly where the 280-per-day ceiling would first bite.

## The promotion link, read off the shipped pairs

Stage D lists "find the promotion link" as work.  It does not need finding: five shipped
pairs carry it -- England, Italy, Spain, France, Brazil -- and all five agree exactly.

    +0x00   on the first division: the regulation its bottom drops into
    +0x04   on the second division: the regulation its top climbs into
    +0x10   the calendar shape
    +0x12   the tier word

`+0x10` and `+0x12` are one dword, which is why "the calendar dword at 0x10" and "the
promotion bit at 0x12" in the older step-4 notes are the same field described twice.  Whole:

    ENGLAND_D1  0x0020a020      ENGLAND_D2  0x00212020
    ITALY_D1    0x0060a060      ITALY_D2    0x00612060
    SPAIN_D1    0x0040a040      SPAIN_D2    0x00412040
    FRANCE_D1   0x0080a080      FRANCE_D2   0x00812080
    BRAZIL_D1   0x0080a080      BRAZIL_D2   0x00812080

One selector byte NN runs through all of it.  A first division is `0x00NN_a0NN`; its second
division is `0x00(NN+1)_20NN` -- the same selector, the top nibble turned from a to 2, the
tier word one higher.  France and Brazil share NN=0x80 and are still two separate countries,
so NN is a calendar shape, not a country.

`tools/tierlink.py` writes the four fields.  It refuses a first division whose calendar is
not one of these shapes rather than inventing a second division for it, and it was checked
by predicting all five shipped pairs from their first division alone before being pointed at
ours -- five for five.

**Our leagues already carry 0x0020a020**, which is England's shape, so a second division of
ours is 0x00212020 and there is no calendar choice to make.  Dry run on regulations 11 and
49: `+0x00` on 11 goes 0 -> 49, `+0x04` on 49 goes 0 -> 11, and 49's calendar becomes
0x00212020.

What this does not say is whether the game acts on it -- whether a season actually relegates
three clubs from 11 into 49 and promotes three back.  That is Stage D's season test and it
needs B finished first.

## A second crash, and it is not the one we just fixed

At day 341, on the re-run, the game died at **0x14cf444ae**, `c0000005`, reading
**0x163e172b7**.  That address is inside `.impdata`, which is where the mid-season wall
lived, so the first guess was another unrelocated offset.  It is not, and the evidence says
so three ways.

**The code there is mutated, not plain.**  The `.impdata` functions behind the mid-season
wall were ordinary compiled code the protector had moved.  This is not:

    14cf44499  and    r10, rsi
    14cf4449c  add    r8, r10
    14cf4449f  and    rax, rsi
    14cf444a7  clc
    14cf444ab  adc    rax, r8
    14cf444ae  mov    al, byte ptr [rax]      <== fault

An address assembled out of `not`/`and`/`adc` is the protector's arithmetic, and there is no
displacement in it to rewrite.  `impscan.py` could not have found this and a disp-only patch
cannot fix it.

**The pointer is not an array walk.**  `rax` held `0x163e172b7` outright -- a constructed
pointer, not base plus index times stride.  Nothing in the edit block is near it: the block
was at `0x7ff4e1c70010`.

**The callers are not the season.**  Sweeping the faulting thread's stack for `.trace`
return addresses and naming them gives path handling (`'z:/'`, `'..'`, `'./'`), jemalloc
(`'jemalloc.c'`), the Lua runtime (`'nil'`, `'local'`, `'function'`) and `'CmdWatchNotice'`.
The regulation search, the team array and the fixture table are nowhere in it.  Whatever
this is, it is file and script machinery, not the competition tables we relocate.

So this is a separate fault, filed separately, and nothing about it undoes the mid-season
fix: the run crossed day 232 -> 330 in one chunk and reached 341, ground the wall used to
make impassable at 237.

**And it is not new.**  The Windows Application log has it thirteen times, and twelve of them
are from before any of tonight's work:

    09-11  05:02  07:36  09:51  12:39  12:56  13:11  15:11  19:58  22:51
    09-12  07:09  10:17
    09-13  11:03
    09-17  08:08   <- tonight

Nothing at all on the 14th, 15th or 16th, which were three nights of heavy season running,
and then one tonight.  That is the shape of a sporadic fault rather than a wall: a wall
stops the same day every time and this has never stopped the same thing twice.  Worth
knowing before spending a night on the protector's arithmetic -- the answer to a sporadic
crash with a working checkpoint is the checkpoint, and that is now fixed.

### The expensive part was ours, though

Those ninety-eight days were thrown away, because `seasonplay.py` only checkpointed on two
of its return codes and the chunk had ended on a third -- `rc 99`, the supervisor's own
watchdog for "seasonrun took longer than its slot".  A perfectly healthy game sat there with
ninety-eight days of season in memory and no save on disk, and the next crash took the lot.
It now checkpoints after any chunk where the game is alive and the day moved.  A save costs
about a minute; replaying ninety-eight days costs twenty, and replaying them into the same
crash costs the night.

## Reading the standings of a patched season

`standread.py` is the check for Stage B's exit criterion, and it has a trap worth writing
down, because its wrong answer looks like data rather than like an error.

Without `--set` it reads the regulation array at the shipped offset:

    regulations: 48472 records at block+0xc12e9c, 7728 distinct keys

48472 is the same impossible count the mid-season wall walked off the end of -- the shipped
offset under a set that has relocated the array.  The competition-id column then prints
garbage (`10709`, `3104`, `65535`) and nothing about the output announces itself as wrong.

With the set named, the same call reads the relocated base and the leagues are ours:

    python tools/standread.py --set teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures
    regulations: 26592 records at block+0x1c84230, 4272 distinct keys
      0  key 00000082  competition 11      <- FL_LEAGUE_01
      7  key 00000083  competition 49
      9  key 00000084  competition 60

`FL26_SET` in the environment does **not** do it; the flag has to be passed.  Every reader
in the repo that walks the block takes the same flag and deserves the same suspicion: a
count in the tens of thousands is the tell.

## Where the first full season stopped: two tables ran out, not one (2026-09-17)

The 39-league season was let run to the end of its calendar. It did not crash and the manager
was not sacked. It ended with **9 of our 39 leagues holding a final table and 30 holding
twenty clubs at position -1**. Read live, that is not one failure but two, and they sit in
different tables.

### 1. The fixture table is full again, at 6000

`fixtures` raised the global round table from 2000 to 6000 records. Measured on the running
season, at `block + 0x2bc51e0`, stride `0x208`:

```
records in use: 6000 of 6000   highest used index: 5999
competitions with rounds: 81
```

Not one record free, exactly as at 2000. The overflow is visible at the tail of our own
range: regulation 181 gets **7 rounds of a 38-round season** and regulations 182, 183, 184
and 185 get **none at all**. A record is one round of one competition, so 39 leagues of 38
rounds cost 1482 records on their own and the shipped competitions spend the rest.

The floor for 39 leagues is about **6200**; 8000 leaves room for the cups Stage C adds. This
is the same edit that `fixtures` already performs, with a larger number.

### 2. The season header holds exactly 100 competitions

This is the wall the older notes guessed at as "about 80". It is 100, and it is the reason
thirty leagues that *did* get a full 38-round schedule still finished with every position
unset.

The season object at `[owner + 0x78]` opens with a header array of **100 entries of 0xb4
bytes**, and the competition objects begin immediately after it at `+0x4650` — which is
`100 * 0xb4`. So the count is not a spare-capacity number: the two arrays are adjacent, and
raising the header means moving the object array, exactly like the fixture job.

```
header entries in use: 100 of 100
keys: 1 2 3 4 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 27 39 40 42 43 49 56 66 67 68
      69 73 74 75 76 77 78 79 82 90 100 101 102 111 ... 170 171 172 173
```

Full, and the keys stop at 173. A competition outside the header still gets a standings
object — all 106 of them exist, with the right twenty clubs — but nothing ever writes a
position into it. That is where the `-1` comes from.

### What this means for the two numbers

They are independent. Leagues 182-185 have no schedule at all (table 1). Leagues 100,
109-114, 121, 138-146, 170-180 have a complete schedule and no standings (table 2). Only
nine of ours clear both: 49, 60, 61, 62, 76, 93, 94, 96 and 98. Five of those nine — 76, 93,
94, 96, 98 — also carry a second, empty table, which is the 2026 season being generated on
top of a finished 2025 one, so the rollover itself works where the header lets it.

Five shipped competitions are also short (167, 169, 105, 107, 30), so neither cap is
something our leagues alone hit; we simply hit them first.

### The anatomy of the 100, and what raising it costs (2026-09-17)

`tools/hdrscan.py` finds the whole job rather than guessing at it. Three numbers move
together, and only one of them is awkward.

**The count, 0x64 — 13 sites in 5 functions.**

```
0x14158f420   the registration walk: find this competition's slot, or a free one
0x141590420
0x14159ebf0
0x14159ecd0
0x14159ee40
```

The first of them reads exactly as expected — `[rax + 0x78]` for the season object, `add rax,
0xb4` for the next entry, `cmp ecx, 0x64` for the end of the header, and a second copy of the
same walk that takes a free slot when the key is not found. Fall off the end of that loop and
the competition is simply not registered; nothing errors, and its standings object is later
built with the right twenty clubs and never written to.

**Where the objects start, 0x4650 — 6 sites in `.trace`, 3 more in `.impdata`.**
**The whole allocation, 0x39a8f0 — 7 sites.**
Both are imm32 already, so both are ordinary in-place rewrites once the new count is chosen.

**The awkward part.** Every one of the 13 count sites is encoded `83 /7 ib` — a *one-byte*
immediate:

```
0x14158f71c  83 f9 64 72 ef      cmp ecx, 0x64 ; jb ...
0x14159048e  41 83 f8 64 72 ec   cmp r8d, 0x64 ; jb ...
```

so **127 is the ceiling that costs nothing**: thirteen single-byte edits plus the two imm32
families. That is +27 slots, which would take this world from 9 of 39 leagues to 36 of 39 --
better, and still not all of them, and no room at all for Stage C's cups.

Anything above 127 needs `81 /7 id`, which is three bytes longer, and the `jb rel8` behind it
grows too. There is no slack inline, so each of the thirteen has to become a jump into a cave
— which `.impdata` has in abundance, and which `impscan.py` already knows how to work in.

Both numbers are worth having on the table: 127 is an afternoon, the full count is the same
kind of work as the fixture table with a detour on top.

### The sporadic crashes are not tied to a day (2026-09-17)

The run that finished the calendar year went **341 -> 344 without incident** and then died at
**day 364**, fault offset `0x84ed4c0` — the shipped random crash Stage B already expects, in
`.impdata`, and a different address from the `0x14cf444ae` family logged as "the day-341
crash".

Two runs, two different days, two different faults. Neither is a day: the earlier notes named
them after the day they happened to land on, which is an accident of when the season was
being driven, not a property of the crash. The Windows log entry (Application Error, id 1000)
is the thing to read, not the day counter.

The session-1 agent was alive through this one, so "the game window is not there" was honest
here — but it is still the wrong thing to reason from. The crash entry in the log is.

Practical consequence: nothing to fix, and the checkpoint is the whole answer. This one cost
the 37 days from the last checkpoint at 327.

### Correction: 0x39a8f0 is not the allocation, and that makes the job cheaper (2026-09-17)

The note above called `0x39a8f0` "the whole allocation, = 0x4650 + 600 * 0x187c". The
arithmetic is right and the reading is wrong. Every one of its seven sites is an *offset into*
the season object, not a size:

```
14158b57b  mov  rbp, qword ptr [rax + 0x78]      ; the season object
14158b581  lea  rcx, [rbp + 0x39a8f0]            ; ... and the member after the objects
141401b46  lea  rcx, [r13 + 0x39a8f0]
141401b52  lea  rbx, [r13 + 0x39a9f0]            ; and another one right behind it
```

So the object array ends exactly where the next member begins, and growing the header in
place would drag every field after it as well — a much larger job than three numbers.

**It does not have to move.** The object array is 600 slots and a finished 39-league season
uses **106**. Keep the boundary at `0x39a8f0` fixed and pay for header entries out of object
slots nobody uses:

| header entries | object base | object slots still below 0x39a8f0 |
|---|---|---|
| 100 (shipped) | 0x4650 | 600 |
| 127 | 0x594c | 599 |
| 200 | 0x8ca0 | 597 |
| 400 | 0x11940 | 591 |

Four hundred header entries cost nine object slots. Nothing at or after `0x39a8f0` changes,
and the season object keeps its size — which also means the save layout is untouched by this
half of the work.

**What actually has to be edited, then:**

- the 13 count bounds, `83 /7 ib` — one byte each, ceiling 127 without re-encoding
- the 6 `0x4650` sites in `.trace` (plus 3 in `.impdata` to confirm), imm32
- the object-count bounds, `81 fb 58 02 00 00` and `3d 58 02 00 00` — imm32, lowered slightly
- the 12 `0xb4` stride sites: **nothing**. The stride does not change.

127 is thirteen one-byte edits and nine imm32 edits. Past 127 the only obstacle left is the
imm8 encoding of those thirteen.

## Correction: the header of 100 is not what empties the tables (2026-09-17)

The two sections above read a snapshot taken at **day 181 — the summer break, between two
seasons** — and drew a conclusion from it that the next season disproves. Read again at day
57 of the following year, with the same world and the same patch set:

```
our leagues seen      : 39
with a filled table   : 35
with no table at all  : 4   -> 182, 183, 184, 185
```

Exactly the four leagues that the full fixture table left with **no schedule at all**. Every
other one of our 39 has real positions, including 181, the one that gets 7 rounds of 38.

So the thirty tables of `-1` at day 181 were not a failure. They were the **new season's
tables, created and not yet played**. The nine that showed a filled table were the ones whose
previous season's table had not yet been recycled; five of those carried both at once, which
is what a rollover in progress looks like. Nothing was broken, and the number 9 was a
measurement of the calendar, not of the game.

### What survives from the two earlier sections

- **The fixture table being full is real, and it is the only real failure.** 6000 of 6000
  records, 182-185 with no schedule, 181 truncated to 7 rounds. Raising
  `arrays.fixtures.cap_new` to about 8000 fixes all five, and it is one number.
- **The header really does hold exactly 100 and really is full** — that measurement stands,
  and `hdrscan.py` and the arithmetic about paying for entries out of unused object slots are
  still correct. What does *not* stand is the claim that it causes the `-1`. It does not.
  Thirty-five of our competitions get standings with the header full, so whatever the header
  gates, it is not this. Raising it is no longer a known requirement, and it should not be
  patched until something is actually shown to need it.

### The lesson worth keeping

A season read between seasons shows tables that have been reset for the year about to start.
The reading is only a verdict on the season that finished if it is taken **before** the
rollover, or against a competition that still carries its old table. Read the same world
twice, at two points in the year, before calling anything broken.

### Open: 30 of our leagues have no 2026 row in the persistent table (2026-09-17)

Read mid-way through the second season (day 128), the live side is healthy — 35 of our 39
leagues carry real positions, and the four that do not are 182-185, the fixture-starved ones.
The persistent side disagrees:

```
100 of 100 entries in use          the competition -> per-season map
244 of 600 phase tables in use     2025: 140   2026: 91   2027: 13
our 39 leagues in the map          39          <- all of them, none missing
our leagues with a 2026 slot        9          <- 49, 60, 61, 62, 76, 93, 94, 96, 98
```

`standread` calls this object "standings" at the same address `seasonread` calls the season
object, so the 100-entry map and the 100-entry header found by `hdrscan.py` are the same
thing seen from two tools. Every one of our leagues has its entry; what thirty of them lack
is a *second* sub-record for the season now being played. The likeliest reading is that those
thirty are overwriting last season's table instead of archiving a new one — which would cost
history rather than play, and matches the live side being fine.

Two things this is **not** yet: it is not the 100 being full (all 39 are in it), and it is not
the 600 phase tables being full (244 used). What caps 2026 at 91 rows is not yet known.

Deliberately left open rather than guessed at. The season is still running; the honest test is
to read it again once the year ends and see whether the thirty acquire a row at the rollover,
the way the nine already have. Reading one snapshot and calling it a fault is exactly the
mistake corrected earlier today.

## A new crash at the end of the SECOND season: a null pointer at 0x141333485 (2026-09-17)

Nothing had ever taken this world past one season. The second season's end does not survive:
the run reached day 128 twice from the same checkpoint and died both times within a few days
of it — once at `0x84ed4c0` (the shipped `.impdata` fault) and once at a fault that has
**never appeared before in seven days of logs**:

```
thread 4144  code c0000005  at 000141333485  (.trace)
  access violation: read of 0x0000000000000008
  rcx 0000000000000000        <- the null
  r14 000000000086fbd8        <- a stack slot the caller was meant to fill
  r15 00007ff4e2250010        <- the edit block, from [owner + 0x48]
```

```
141333482  mov    rcx, qword ptr [r14]
141333485  movzx  eax, byte ptr [rcx + 8]     <- here
14133348d  cmp    eax, 0x14                   <- twenty
141333493  lea    ebx, [rax - 0x14]
```

A plain null-struct field access: the caller left a stack slot empty and this reads field
`+8` of nothing. The `0x14` two instructions later is twenty, which is how many clubs each of
our leagues has.

**The call chain names the feature.** Callers in `.trace`, innermost first:

```
141333395  141331470  141332f10  141333cff  1412f8ee5  1413071eb  141b3779c
```

`0x1412f8ee5` is inside `0x1412f8780`, one of the six functions that address the season object
as `[season + 0x39a8f0]`. So this is season/standings processing, running at the point in the
calendar where a season is wound up.

**The obvious suspect is the open question above.** Thirty of our thirty-nine leagues have no
row for the season now being played; a wind-up that walks every competition and expects to
find one would get exactly this null. That is a hypothesis with a mechanism, not a conclusion
— but it is the first one to test, and it is testable: give those thirty their row, or guard
the load, and see whether the second season ends.

**The fix shape is familiar.** This is the same class as the nullguard modules already in the
tree: a check at `0x141333485` that skips the record when `rcx` is null. Cheap to try, and it
would say whether the missing rows merely cost history or end the save.

Not attempted today: the season is still running and the patch set may not change under it.

### What that function actually does, and why a one-site guard is the wrong fix

Read whole, `0x141333420` is a **weighted random pick over five options**. `r10` is set to 5,
the loop steps a pointer by `0xc`, it accumulates a running total into `edx` from a static
table at `0x1428e61c8`, writes the five partial sums to the stack, calls `0x1415149e0` and
compares the result against them — the standard shape of "roll, then find the bucket".

The null is not a failed lookup inside it. It is the **argument**: `r14` is `r9` as passed in,
and the function dereferences `[r14]` in three separate places —

```
141333482  mov  rcx, qword ptr [r14]     ; the branch taken when dl is set
1413334d8  mov  r8,  qword ptr [r14]     ; the branch taken when it is not
14133354a  mov  rbx, qword ptr [r14]     ; again, after the pick
```

— so a guard at the faulting instruction alone would move the crash eight instructions down.
Both entry branches and the tail would have to be covered, which is no longer a nullguard but
a rewrite of the function's contract.

**So the fix is upstream, not here.** Something in the chain
`141b3779c -> 1413071eb -> 1412f8ee5 -> 141333cff -> 141332f10 -> 141331470 -> 141333395`
handed this function a structure whose table pointer was never filled. `0x1412f8ee5` sits in
one of the season-object functions, which is where to look, and the thirty leagues with no
row for the current season remain the obvious reason a season-object lookup would come back
empty.

Correcting the note above: do **not** start with a guard at `0x141333485`. Fix the fixture
table first, confirm whether every league then gets its row, and only then — if it still dies
— follow the caller chain to whichever one accepted an empty result.

## Correction: the fixture table was never "full" in the way I counted (2026-09-17)

Raising `arrays.fixtures.cap_new` from 6000 to 8000 worked — a fresh season on the same world
now gives **all 39 of our leagues their full 38 rounds**, where the previous one left 182-185
with no schedule at all and 181 with 7. That part is real and measured.

But the reason given for it was wrong. A free fixture record is marked `0xffff` in its
competition field, and the census counted those as a competition of that number. So

```
records holding a real competition : 2194
records marked free (0xffff)       : 5806
highest record actually used       : 2193
```

reads as "8000 of 8000 in use" if `0xffff` is not excluded — which is exactly what "all 2000
records are in use, not one is free" (2026-09-16) and "6000 of 6000" (earlier today) were.
Both numbers were the size of the table, not its occupancy.

**What the table actually is: a bump allocator.** Records 0..2193 are used and 2194..7999 are
free, contiguously. A whole fresh 39-league world costs **2194 records** — 39 leagues of 38
rounds is 1482 of those, and the shipped competitions spend the rest.

**So why did 6000 run out?** Because the count grows as seasons are played, not at creation.
The world that starved 182-185 was in its *second* season. One season costs about 2200, so
6000 is between two and three seasons' worth and the second one ran the table dry.

That makes 8000 a postponement, not a cure: it buys roughly three and a half seasons. The
question worth answering next is whether the table ever gives a finished season's rounds back,
or whether it only ever grows — and that is measurable by reading this number at the start of
each season rather than by reasoning about it.

## The -1 that kills a season, caught in the act (2026-09-17)

The fresh 8000-fixture world died at day 360 of its **first** season, fault offset
`0x13236e4` — the crash `seasonread.py` was written to chase. The dump names it exactly:

```
access violation: read of 0x0005428e52dc
rax 00000000ffffffff   rcx 00000000ffffffff   r13 0000000000000014
r8  00000001428e52e0        <- a static table
```

`0x1428e52e0 + 0xffffffff * 4 = 0x5428e52dc`. The fault is `table[-1]`, four gigabytes past
the end, and nothing is corrupt — the index really is minus one.

### Where the -1 comes from

```
141323669  mov    edi, r12d                  ; r12 = 0
14132366f  mov    dword ptr [rbp + 0x77], r12d   ; the slot starts at 0
...
141323682  <loop over r13d = 0x14 = TWENTY entries, matching a club id>
1413236b2  test   ecx, 0xffffc000             ; ... ignoring the low 14 bits, the id packing
1413236c3  mov    eax, dword ptr [r14 + 4]    ; found: take the entry's value
1413236c7  mov    dword ptr [rbp + 0x77], eax
...
1413236e1  mov    eax, dword ptr [rbp + 0x77]
1413236e4  sub    ecx, dword ptr [r8 + rax*4] ; and index the static table with it
```

Twenty entries, and `+4` of an entry is the standings pair's **position** field — the same
`+4` that `seasonread.py` reads. So the club was *found*; what it holds is `-1`, the position
of a club whose table was never filled in. The game then uses a league position as an array
index without checking it.

This closes the loop on the phrase in the older notes. "The -1 that kills a season" is not a
metaphor: an unfilled standings position is read straight into `table[rax*4]`.

### Which league still has -1, and why it appeared only now

The obvious candidates are 182-185. Until today they had **no fixtures at all**, so they never
reached the point of needing a position. With the fixture table raised they play for the first
time — and the season header, which holds exactly 100 competitions and is full, is the reason
a competition can end up without a filled table.

That reverses this morning's correction back again, and the reason is worth stating plainly:
the header being full was never harmless, it was **unreachable**. Four leagues that never
played could not expose it. This is the third reading of the same wall today, and the only one
taken with every league actually playing.

To be confirmed on the running world rather than asserted — the measurement is `standread.py`
against a season that has reached the autumn.

## The negative position is a wall, not a rarity, and nullguard8 takes it down

The fault at `0x13236e4` first showed up on day 360 and looked like one of the sporadic
deaths. It is not. After the supervisor reloaded slot 1 at day 232 and played forward, the
same fault came back within four minutes, dump `FL_2026.exe.7832.dmp`, with the registers
identical to the first time:

    rax = rcx = rdx = 0xffffffff
    r8  = 0x1428e52e0
    read of 0x5428e52dc  =  r8 + 0xffffffff * 4

So the season cannot get past this point at all. Every chunk loads, advances, and dies in
the same place. That makes it the blocker for the whole D1 run, and it is why the guard was
installed while the run was live: unlike a capacity change, a code-cave trampoline does not
touch the edit block, so every checkpoint on disk stays loadable.

`sider/fl26nullguard8.lua` replaces seven bytes at `0x1413236e1` with a jump to a
trampoline that performs the same load, tests the sign, and skips the subtraction when the
index is negative. Skipping leaves `ecx` holding what `mov ecx, edx` put there three
instructions earlier -- the same result as subtracting zero. An unranked club contributes
no adjustment, which is the honest answer for a club whose table has never been filled in.
Verified in `sider.log`:

    [fl26nullguard8.lua] fl26caps: applied all 2 patches -- nullguard8: negative standings
    position guarded at 0x1413236e1

### Correction: the code caves are not what the exe file says they are

An earlier note in this session recorded that the bytes around `0x14252e8a0` are non-zero
on disk, and flagged that as a contradiction, because `fl26nullguard7.lua` declares its
`old` as all zeros there and applies cleanly.

There is no contradiction; the file reading was wrong. `.trace` holds `0x252d800` bytes of
virtual data starting at `0x140001000`, so it ends at `0x14252e800`. Everything from there
to `.rdata` at `0x14252f000` is the zero-filled tail of the last page -- it exists in the
process but has no bytes in the file. A file offset computed as `va - 0x140001000 + 0x600`
runs straight on into `.rdata`'s raw data and returns its bytes instead.

The rule that follows: for any address at or above `0x14252e800`, the running process is
the authority, not the file. The appliers already enforce this by verifying `old` before
they write, which is how nullguard8's cave at `0x14252e8c0` was confirmed zero.

## The season wants 113 competitions and is allowed 100

Measured on the running D1 world, mid-season, with `fixcensus.py`:

    records holding a competition : 2314
    records free                  : 5686
    highest record used           : 2313
    competitions with rounds      : 113
    our leagues with all 38 rounds : 39 of 39

Two things at once. The fixture fix holds -- all 39 of our leagues have their full 38
rounds, where the 6000-record world left four of them with nothing. And the count of
competitions that actually own fixtures is 113, against a season header of exactly 100.

That is the number behind the user's observation that a table showed about 130 points. The
thirteen competitions that do not fit are not reported as missing; they simply never get a
row for the new season, so their results keep landing in the previous season's table, which
is why matches played reads 76 -- two seasons of 38 -- instead of 38.

113 also settles the size of the fix. 127 is the ceiling of the cheap version, because
every one of the thirteen bounds is `cmp r32, 0x64` with an 8-bit immediate and 0x7f is the
largest value a signed byte holds. 127 clears 113 with fourteen to spare, so the expensive
version -- `81 /7 id` plus a trampoline at each of the thirteen sites -- is not needed.

`tools/hdr127.py` generates the module: 28 patches, thirteen one-byte bounds, six
`0x4650 -> 0x594c` table bases and nine `600 -> 599` table counts. The boundary at 0x39a8f0
is held fixed and the twenty-seven extra header entries are paid for with a single phase
table.

### Three sites that look like the table base and are not

hdrscan found the constant 0x4650 at three addresses in `.impdata` as well as six in
`.trace`. `.impdata` is ordinary code -- that is the whole reason `impscan.py` exists -- so
these looked like code paths that would keep using the old base if they were left alone.
They are not. Each sits in a run of u32s next to 0xffffffff sentinels, and the only way to
decode one as an instruction is to start reading in the middle of the number:

    0x14ea41684  ...09 00 00 e3 be 81 28 50 46 00 00 ff ff ff ff...
                                    `- mov esi, 0x46502881, straddling the site

The generator now refuses every candidate outside `.trace`, and prints the ones it refused
rather than dropping them quietly. Worth recording because the first, looser version of the
check passed one of these three: requiring that some instruction ends on the number is not
enough on its own when the surrounding bytes decode into anything at all.

## The run log lies about time, and a screenshot is still the only witness

While the first guarded chunk was playing, the log showed nothing for six minutes. Under
the two-minute rule that is a stall, so: screenshot first. It showed a dialog waiting for an
answer -- "You will proceed to the next day. The transfer period will come to an end." --
with Yes already highlighted. Confirming it moved the walk straight on to the calendar.

But the log was not the evidence it looked like. `seasonplay.py` flushes every line it
writes; `seasonrun.py`, the child, does not, and its stdout is a pipe, so Python
block-buffers it. Its lines only reach the parent when the buffer fills or the process
exits -- which is why the previous chunk's eight day-moves all appeared at once, at the end.
Read live, the day counter had gone from 232 through the New Year wrap to 163 while the log
stood still at "loaded".

So the silence proved nothing either way, and whether that dialog was genuinely blocking or
had just appeared cannot now be established. Both fixes are worth having and only one of
them is about the dialog:

- `PYTHONUNBUFFERED=1` and `python3 -u` in the runner, so the log is a timeline again.
- The screenshot rule earned its keep. It was the only thing in the session that could say
  what the game was actually doing, and it took twenty seconds.

The lesson is narrower than "logs lie": a log written by a parent about a child says when
the *parent* heard something, and a pipe decides when that is.

## Confirmed on the running world: the header is full, and the trade is free

`standread.py` against the D1 world in its second season, the reading that was owed before
anything was installed:

    100 of 100 entries in use
    159 of 600 phase tables in use

Both halves matter. The header is full -- not nearly full, exactly full -- while the fixture
table holds rounds for 171 competitions across the two seasons. So the shortfall is real and
active right now, and it is what denies thirteen competitions a row of their own.

And the price of hdr127 is confirmed to be nothing. The patch buys twenty-seven header
entries by giving up one phase table, 600 -> 599, and only 159 of those 600 are in use with
two seasons running at once. There was no way to know that from the exe; it had to be read
off a live world.

## nullguard8 under a real run: 313 days in one chunk

The first guarded chunk, end to end:

    13:41:14  seasonrun --until 540 --minutes 12
    ...
    | day 179 -> 180  (22 moves, -3 s left)
    | finished on day 180 after 22 move(s)
    13:53:18  chunk ended rc 0, day 232 -> 180

Day 232 through the New Year wrap to day 180 -- 313 game days, twenty-two moves, rc 0.
The same world, unguarded, died at day 360 twice in a row and again four minutes into a
reload. The guard holds under the run, not only at the site.

Two smaller things the chunk shows. All twenty-two move lines arrive at once at the end,
which is the buffering above, seen from the other side. And the moves slow to one day each
near day 176-180: that is May, where every league is playing its last rounds at once.

## hdr127 works: 115 competitions where the ceiling was 100

Installed, all 28 patches applied, and a fresh season created on the same world. Read back
with the reader taught the new layout:

    115 of 127 entries in use
    139 of 599 phase tables in use

The same world before the patch, in its second season, read `100 of 100 entries in use`
while 171 competitions held fixtures. The header is no longer the thing doing the limiting:
the game registered 115 competition instances because there was somewhere to put them.

The fixture side is unchanged, as it should be -- a fresh season is 2,314 records, 113
competitions, and all 39 of our leagues with their full 38 rounds.

**Twelve spare, and that is the number to watch.** 127 is not headroom, it is a fit. Stage C
adds a cup, and a cup is a competition instance like any other; so is every continental
group. The next thing that widens the world has to be counted against those twelve before
it is built, not after.

### The reader had to be taught the layout first

The first reading after installing said `88 of 100 entries in use` and `600 of 600 phase
tables in use` -- on a season that had barely started. Neither number meant anything.
`standread.py` had the shipped constants baked in, and hdr127 moves the phase tables from
0x4650 to 127 * 0xb4 and drops their count to 599, so the reader was looking at the last
header entries and calling them tables.

It now takes `--entries N` and derives the table base and count from it, so the three cannot
drift apart. Worth writing down because the failure was silent: a tool reading a patched
world with unpatched constants does not raise, it reports.

## All 39 of our leagues now hold a standings entry of their own

With the id column working, the fresh season on the widened header reads:

    115 of 127 entries in use
    entries carrying one of our 39 regulations : 39
    competitions with a regulation but no entry : 99

Thirty-nine of thirty-nine. That is the end of the symptom the user found: a league with no
entry of its own keeps writing into the previous season's table, which is what produced 76
matches played and about 130 points.

Two honest limits on this reading:

- The "before" dump cannot be used for a per-league comparison. It was taken without
  `--set`, so its id column was resolved against the shipped regulation base on a world that
  relocates the table. The number that *is* sound from it is the one that needed no lookup:
  the header was exactly full, 100 of 100.
- The 99 competitions that have a regulation but no entry are not yet explained. The header
  is not full, so nothing is being turned away -- these are competitions the season did not
  start. Whether any of them should have started is a separate question and not one today's
  numbers answer.

### A count field that survived relocation and lied

`standread.py` reads the live regulation count from `blk + 0xd0bcf4`. That address is the
count as the game ships it, and every set we build relocates the regulation table, so what
sits there afterwards is something else entirely: read against the fixtures set it returned
41,943,074 records, and before that 27,923, on a table whose cap is 600.

It did not fail. It produced an id column full of plausible-looking numbers, and 28 of the
115 rows came back with lists dozens of ids long. The count is now clamped to the cap and
the clamp is printed, because the failure mode here is not a crash -- it is a column that
looks like data.

## Correction: hdr127 applies cleanly and changes nothing. The header still stops at 100

The two readings reported above -- "115 of 127 entries in use" on a fresh season and
"127 of 127" in the second -- were both wrong, and wrong in the same way.

`standread.py` treats an entry as in use when its key is not the 0xffffffff sentinel. The
twenty-seven entries the patch added have never been touched by the game, so they hold
**zero**, and zero is not the sentinel. Counted strictly, by key:

    fresh season   115 rows -> 88 real keys at indices 0-87, 27 blanks at 100-126
    second season  127 rows -> 100 real keys at indices 0-99, 27 blanks at 100-126

Indices 100 to 126 are untouched in both. The game is still using exactly the first
hundred, which is exactly what it did before the patch: the pre-patch reading of the same
fresh world said `88 of 100`, and 88 + 27 = 115. The arithmetic that looked like success was
the blanks being counted.

So: 28 patches applied and verified in `sider.log`, every bound and base and count changed,
and the behaviour is identical. The patch is not wrong; it is incomplete.

### The likely reason, stated as a hypothesis and not a result

A free entry is meant to be recognisable, and the accessors compare against a sentinel held
at `0x14351ae28` rather than against zero. Entries 0-99 hold either a real key or that
sentinel; entries 100-126 hold zero. That points at an initialiser which stamps the sentinel
across the header and was not among the sites hdrscan found -- so the allocator, looking for
the first entry whose key is the sentinel, never considers the new twenty-seven at all.

If that is right, the missing patch is wherever the header is first filled with the
sentinel, and `hdrscan.py` did not find it because it looks for the stride 0xb4 paired with
a bound of 0x64 in the same function. An initialiser that writes 0x64 entries without ever
adding 0xb4 to a pointer -- a memset, or a loop over a differently shaped index -- would not
match. To be found and confirmed, not assumed.

### The lesson, which is the same one as the .impdata sites

A tool that reads a patched world with unpatched assumptions does not fail; it reports. This
is the third time today: the fixture census counting 0xffff free records as competition
65535, the regulation count read from a relocated address, and now an occupancy test that
cannot tell "never initialised" from "in use". Each time the number looked plausible and
each time it was the flattering reading. The check that would have caught all three is the
same: before believing a count, look at what the individual records actually hold.

## The site that was missing, and the scan that now says it is the only one

`0x1414fd4e0` is the header initialiser. It is four instructions of shape:

    1414fd4e3  mov  r9d, 0x64                 ; the count -- stated once, never compared
    1414fd4f0  mov  eax, [rip + ...]          ; the free-entry sentinel at 0x14351ae28
    1414fd4fb  mov  dword ptr [r8], eax       ; stamp it into the entry
    1414fd569  add  r8, 0xb4                  ; next entry
    1414fd570  sub  r9, 1
    1414fd574  jne  0x1414fd4f0

`hdrscan.py` pairs a 0xb4 stride with `cmp ?, 0x64` inside one function. A count-down loop
has no comparison at all, so this function was filed under "0xb4 elsewhere, left alone".
That single omission is the whole reason the first version of the patch applied cleanly,
verified every byte, and changed nothing: entries 100 to 126 were never stamped, so they
held zero rather than the sentinel, and the allocator looks for the sentinel.

Having been caught once by an incomplete scan, the constant was then looked for in every
encoding it could take, across `.trace`, near any 0xb4 stride:

    mov r32, 100 (imm32)         near a stride: 2   0x1414fd4e3 and 0x141f7c437
    mov r64, 100 (sign-extended) near a stride: 0
    push 100                     near a stride: 0
    cmp r32, 100 (imm32)         near a stride: 0
    cmp r/m, 100 (imm8)          near a stride: 13  -- the bounds already patched

`0x141f7c437` is `mov r8d, 0x64; sub r8d, ebx` after a value has been clamped to 0x63: a
percentage, not a header. So the header's hundred is written in exactly fourteen places, and
all fourteen are now in the set. The module is 29 patches and `sider.log` confirms each,
including `0x1414fd4e5 64000000 -> 7f000000`.

## The crash that interrupted the hdr127 test was the shipped one

`FL_2026.exe.3956.dmp`, written at 14:51 while the season-creation walk sat on the
manager-settings step:

    thread 17740  code c0000005  at 0x1484ed4c0  (.impdata)
      access violation: write of 0x1ea6ef601
      rcx 0x00000001ea6ef601

The address is held outright in `rcx` — a pointer, not an index — and every register
apart from `rsi`/`rdi`/`r8` holds garbage of the same shape. This is the shipped
season-generation bug at `0x1484ed4c0`, which kills the walk at the manager-settings
step roughly one time in two on a clean game and is already recorded as such in the
public notes. It is not hdr127: the widened header is not touched until the season
object is built, which is later.

Nothing to guard here. The walk was simply started again.

## hdr127 is live: 127 entries, none of them blank

Measured on a season created under the 29-patch build, read strictly by key:

    88 of 127 entries in use
    139 of 599 phase tables in use

The number that matters is not the 88 -- a fresh season opens with 88 competitions
either way. It is that the reader printed no "never stamped" tail at all. Under the
28-patch build, indices 100-126 held **zero**: the initialiser at `0x1414fd4e0` stamped
the free sentinel across exactly `mov r9d, 0x64` = 100 entries and left the rest as the
allocator found them, and the allocator looks for the sentinel, so it could never hand
one of them out. That is why the widened header applied cleanly and changed nothing.

With `0x1414fd4e5` patched from `0x64` to `0x7f`, all 127 entries are stamped and all 127
are therefore reachable. The header really is 127 wide now.

What this does **not** yet show is a season using more than 100. A season opens at 88 and
grows into the rest as cups and continental phases start; the shipped build reached 100
and stopped. `tools/hdrwatch.py` samples the header every five minutes beside a season run
and says so the first time the count passes 100.

Cost, unchanged: one phase table. 127 * 0xb4 = 0x594c, leaving 599 tables of 0x187c inside
the same 0x39a8f0 boundary. 139 of those 599 are in use on a fresh season, so the pool is
not where the pressure is.

## The fixture table does hand records back

Open until now, and answered by `tools/fixwatch.py` sampling a live run:

    15:19:54   day 363   2329 used   high-water 2328   117 competitions
    15:29:54   day 181   1593 used   high-water 2614    78 competitions

One process, one edit block, no save and no reload in between: the chunk ran straight
from day 238 to day 181 through New Year and came out the other side with **1021 fewer
records in use**, while the high-water mark went on rising to 2614. So the rounds of a
finished season are reclaimed at the rollover, and the allocator hands the freed records
out again rather than only ever bumping.

This corrects the earlier reading in these notes. "No handback observed" was true of what
had been watched -- a single season, inside one session -- and was never evidence of
absence; nothing had yet been watched across a boundary.

Nor is the boundary the only place it happens, which is what this section said when it was
first written. At 15:49, well inside a season, the count went 1593 -> 1461 at day 179. So
rounds are reclaimed as they are finished with, not swept up once a year.

What it means for the cap: 8000 is not being spent 2200 per season forever. Peak demand is
one season's rounds plus whatever of the next has been drawn when the old one is dropped,
which on this world is under 2700. The raise from 6000 was still needed -- 39 leagues of 38
rounds do not fit in the shipped 2000, and the starvation it fixed was measured -- but the
headroom above it is far larger than a bump-only table would have left.

## The wall is down: 115 competitions, fifteen of them past the old ceiling

Read on the running season at 15:30, day into 2026:

    115 of 127 entries in use          (0 never stamped, 12 free)
    100  00000005   8,9,10,1032,1033,2056,2057,3080,3081,4104,4105,5129,6153,7177,8201
                    00000005/2026: 157,158,159,160,161,162,163,164,165,166,167,168,169,170,171
    101  00000029   52        ...
    114  00000047   84

Entries 100 to 114 hold real competitions, all tagged 2026, each with its own phase
tables. On the shipped header those fifteen would have been turned away without an error
and would have gone on writing into the previous season's table -- the 76 played and ~130
points the user reported. Two of the fifteen are the multi-group competitions (15 phase
tables at index 100, 10 at index 110), which is exactly the shape that was being lost.

Twelve slots remain free at this point in the season.

## Open lead: what is actually inside a phase table

A phase table is 0x187c bytes and opens with what the reader already knew plus a little
more. Table 152 of the live season, competition 31, phase 2026:

    0000  1f 00 ea 07  1f 00 00 00  03 00 00 00  01 00 00 00
    0010  ea 07 03 1c  94 40 22 00  ff ff ff ff  00 00 00 00
    0020  29 00 00 00  e0 03 03 04  ff ff ff ff  00 00 00 00
    0030  08 00 00 00  df 43 06 05  ff ff ff ff  00 00 00 00

So: `+0x00` u16 competition, `+0x02` u16 phase, `+0x04` the competition again as a u32,
then two small counts (3 and 1), then a run of 16-byte records. `(0x187c - 0x10) / 16` is
390, and a 20-club double round-robin is 380 matches, so the body is most likely the
fixture-and-result list for the phase rather than the sorted table.

Two decodings of the 16-byte record fit the bytes and cannot be told apart from one
sample -- the record may begin at `+0x10` or at `+0x14`, which shifts every field by one
word and changes what the `ffffffff` column means. Guessing between them is how a number
that looks like data gets written down as a fact, so it is left open here.

A first attempt at the cross-check did not settle it, and is recorded so the next attempt
does not repeat it. The same packed 32-bit word shape appears in both tables, which is
encouraging, but scanning every four-byte offset of competition 31's fixture records and
taking the low twelve bits as a club gives 81 distinct values where a 20-club league should
give 20. A blind scan mixes fields together, so the number means nothing. Settling this
needs the function that writes a fixture record disassembled, not more sampling.

Worth having, because it would let "38 played, not 76" be read as a number at any moment
instead of waiting for a league table to appear on screen, and it is the same data Stage D
needs to check promotion and relegation. The way to settle it is to cross-check one
competition against the fixture table, whose layout is already known.

## The next thing that could run out is the phase tables, not the header

Across the first two rollovers of the hdr127 run:

    fresh season          139 of 599 phase tables in use
    after one rollover    335 of 599
    header, both times    115 of 127

The header has settled: 115 in use, 12 free, unchanged across a season boundary, so the
competition entries are being reused. The phase tables are not settling. Roughly 196 more
are in use after a season than before it, and nothing has yet been seen going back.

Extrapolated -- and it is only an extrapolation from two points -- a third season lands
near 530 and a fourth passes 599. If that is what happens, the pool is the next wall, and
it arrives after about four seasons rather than immediately.

Two things would change the picture and neither has been measured yet: the tables may be
reclaimed later in a season rather than at the boundary, the way the fixture records are,
and the growth may simply be the second season's competitions coexisting with the first's
until the first is fully retired. The run continues to day 700, which reaches a third
rollover, and `tools/hdrwatch.py` now reports the pool alongside the header and shouts if
fewer than 60 tables are left.

Worth noting what this is not: it is not a cost of hdr127. Widening the header spent one
table out of 600. The growth is the game's own.

## The handback, seen a second way

`fixcensus.py` on the same world after 655 days played says it without being asked:

    highest record used : 2162
    NOTE: 702 records below the high-water mark are free -- the table is no longer packed,
          so something is handing records back
    competitions with rounds : 79

Holes below the highest record in use are a different kind of evidence from a falling
count, and they agree. A bump allocator cannot produce them.

A wording caveat that matters for reading these numbers: `high` here is the highest index
currently in use, not a historical high-water mark. It falls when the records at the top are
freed, which is exactly what a rollover does -- so a fall in it is not evidence that the
allocator restarted, and `fixwatch.py` no longer says it is.

And the phase tables did not keep climbing: 139 on a fresh season, 335 after the first
rollover, still 335 after the second. So the extrapolation in the section above -- a third
season near 530, a fourth past 599 -- is not what the world does. Two seasons coexist and
the pool settles. A third rollover is running now to confirm the plateau rather than assume
it.

655 days, two season boundaries, no crash and no recovery.

## The header is tighter than the first costing assumed

Watched on the running world: 115 of 127 at day 163, then **119 of 127 at day 310**, with
the season still going. Eight free.

The 113 this was all costed against came from the fixture census -- competitions holding
rounds at one instant. That is not the header's high-water mark, and using it as one was a
mistake of the kind that reads as a fact. The header's own peak has not been measured yet;
all that is known is that it is at least 119.

127 is the ceiling of the cheap patch, because every bound is a one-byte immediate. If the
peak lands near it, the next step is not another widening of the same shape: above 127
each of the 13 bounds needs the four-byte form, which is longer than what it replaces and
so needs its own trampoline. That is worth knowing before Stage C's cup takes a slot.

## Three rollovers: both pools grow slowly, and the header is nearly full

    fresh season       88 of 127 entries   139 of 599 phase tables
    after rollover 1  115 of 127           335 of 599
    after rollover 2  115 of 127           335 of 599
    after rollover 3  119 of 127           355 of 599

A third season boundary moved the header by four entries and the pool by twenty, not by
another two hundred, so neither pool grows by a season's worth each year.

**But "settle" was the wrong word, and this section said it too early.** Watched on into the
fourth season the header went on climbing -- 115, 115, 119, and at day 242 of the next year
**124 of 127**. Three free. The phase tables moved with it, 335, 355, 375. Four points that
rise every time are not a plateau; what the third rollover actually showed is that the
growth per season is small, not that it has stopped.

If the header reaches 127 the original bug returns unchanged, just at a higher number:
competitions turned away without an error, writing into the previous season's table. The
cheap patch cannot be pushed past 127 -- every bound is a one-byte immediate -- so if the
peak is above it the next step is the four-byte form with a trampoline at each of the 13
sites.

Two things are still unknown and both matter: whether the climb flattens on its own, and
whether the peak within a season is what is being sampled here at all. The run continues,
and `hdrwatch.py` reports every change.

## Two more 0x1484ed4c0 dumps, and a wrong turn corrected

Two dumps today, 14:51 during the season-creation walk and 16:12 during a chunk playing
through the third rollover:

    rcx 0x00000001ea6ef601      (14:51)
    rcx 0x00000001f830e5c1      (16:12)

Every other register is identical between them: rax c8072890, rdx 9c67b725, rbx dbfedbdf,
r9 7cc5b908, r10 14ab18846, r11 5dd5cd28, r12 ba238df7, r13 dba6d565, r14 b3eb6750,
r15 f49f7b2c.

That is the signature already recorded under "0x1484ed4c0 named: the sky bake, on the main
thread, leaving a press conference": one bug, every register byte-identical but `rcx`, and
`rcx` a value around 8 GB that is **unaligned** -- a corrupted heap pointer, not a null and
not an index off a good base. Both of today's values fit it exactly (`...601`, `...5c1`).
So these are two more instances of the known crash, not a new one.

**Where I went wrong, written down so the next reader does not repeat it.** Working only
from today's dumps I disassembled `0x1402bfcdf` -- the topmost `.trace` address on the
stack -- found it landing one instruction after `call 0x14159f3e0`, confirmed that callee
is `__security_check_cookie`, and concluded the fault was the stack-cookie failure reporter
firing after a stack smash. It is a clean-looking chain and it is wrong. `crashdump.py`
finds frames by scanning the stack, not by unwinding, and almost every function with a
stack buffer ends in a cookie check, so a scanned address landing after one is close to
meaningless. The earlier attribution had the real chain, from the string pools of each
frame: `__game_main` -> the Lua VM -> FoxCore `dataBodySet` -> `StartSkyCapture` ->
`TppAtmosphere` -> `SH_LIGHTING` -> jemalloc -> the faulting store. `0x1402bfc10` sits in
the same `0x1402bxxxx` FoxCore cluster as `dataBodySet`, which is why its return address is
lying around on that stack at all.

I had this file's own answer available and reasoned from a partial view instead. The rule
that would have caught it: before writing down a new attribution for an address, read what
is already written about that address.

**What today does add**, and it is small: the crash is not confined to the season-creation
walk. It arrived once at the manager-settings step and once mid-run at a rollover. Both are
moments a scene is brought up, which is what the sky-bake attribution predicts, so this is
a confirmation of that reading rather than a correction to it. The public note's "season
generation, about one time in two" describes where a user meets it, not the trigger.

**Guarding it remains ruled out.** A wild heap pointer means the damage precedes the store;
skipping the write trades a crash for silent corruption.

## Why the header grows, and the number it is growing towards

The sub-record tags say what is happening. In the 2029 season the header still holds
sub-records tagged 2025:

    41 tagged 2025    15 tagged 2026    55 tagged 2027    75 tagged 2028    20 tagged 2029

An entry keeps up to two sub-records, so this is not unbounded per entry. What accumulates
is entries: a competition that has ever run keeps its slot, and each new season adds the
competitions that had not run before. That is why the count climbs 88, 115, 119, 124 rather
than resetting -- and it also says where the climb ends.

It ends at the number of distinct competitions the world can ever run, which is readable
directly:

    regulations: 600 records, 129 distinct keys
    124 of 127 entries in use
    competitions with a regulation but no entry: 56, 57, 58, 108   (the rest are 0xffff padding)

124 in use plus 4 real competitions still without one is 128. The header holds 127.

So the demand this world settles at is one entry more than the cheap patch can express, and
the shortfall is not a matter of waiting to see: 0x7f is the largest value a sign-extended
one-byte immediate can carry, and every one of the 13 bounds uses that form. 128 needs the
four-byte encoding, which is longer than the instruction it replaces, so each site needs a
trampoline -- the job that was described earlier as "a different job, and nothing so far
asks for it". Something now asks for it.

Stated as what it is: 128 is an inference from 124 + 4, not a peak that has been watched.
It could be that one of those four never starts, in which case 127 is exactly enough and
nothing more is needed. The run continues and `hdrwatch.py` reports every change, so this
resolves itself either way within a season or two.

What follows regardless: **the cup should not be enabled yet.** It would take one of the
three remaining slots and it is the competitions already in the world that are competing
for them.

## Correction: 128 was a guess, and so was 124

The four competitions with a regulation but no entry -- 56, 57, 58 and 108 -- read like
this once `regdump.py` is pointed at the relocated table:

    id 56  type 4  bit8 of +0x304 = 0  clubs 0  phases 0  fixture idx [0xffffffff]
    id 31  type 3  bit8 of +0x304 = 1  clubs 40  phases 6   fixture idx [828..833]
    id 52  type 1  bit8 of +0x304 = 1  clubs 20  phases 38  fixture idx [852..889]

Bit 8 of `+0x304` is half of what the season-start decider at `0x141546c70` ends on, and
the four all have it clear with no clubs, no phases and no fixtures. So they are not
starting *this* season, and the obvious conclusion is that demand is the 124 already in the
header and 127 is comfortable.

That conclusion does not survive counting. Across the live regulation table:

    distinct keys whose regulation says it starts : 106
    distinct keys whose regulation says it does not : 22
    entries in the header                          : 124

124 is larger than 106. So an entry is **not** released when its competition stops taking
part -- the header holds entries for competitions that started in some earlier season and
are not starting now. Which means bit 8 describes the current season only, and says nothing
about whether one of those four starts in a later one.

Where that leaves the number: the ceiling is the count of distinct keys that ever start,
which is at least the 124 observed and at most the 128 that exist. The header holds 127. It
could be exactly enough or one short, and neither 128 nor 124 has been earned yet.

Both of the earlier framings in this file are wrong as stated: "124 + 4 = 128, so we are one
short" assumed every key eventually starts, and the reading above would have assumed none of
the four ever does. What is actually established is narrower and worth keeping: **header
entries are never reclaimed**, so the count only rises, and the thing to watch is whether it
stops at 124.

Also fixed on the way: `regdump.py` had no `--set`, so it always read the shipped base. On a
relocated world that does not fail -- it prints player records as regulations, with names
like "FL P19298" and a count of 41,943,074, which is exactly what it printed at 16:45 before
anyone noticed.

## The three 0x64 sites hdr127 did not patch are not the header

`standbounds.py` lists 17 sites comparing against 100 inside functions that touch the
standings object; hdr127 patches 14. The other three were checked rather than assumed:

    140f3be6e   cmp eax, 0x64 / jl      no stride near it, signed -- unrelated
    1413fc5fc   cmp edi, 0x64 / jb      stride 0x208, not 0xb4
    1413fc9bc   cmp edi, 0x64 / jb      stride 0x208, not 0xb4

The last two are the mode-copy loops, and read whole they say what they are:

    1413fc5d0  cmp    edi, 0x7d0            <- patched to 0x1f40 by the set
    1413fc5e0  cmovae rcx, rbx              <- past the cap: take the dummy record
    1413fc5e7  add    rcx, 0xd65f64         <- the shipped fixtures base
    1413fc5f3  inc    edi
    1413fc5f5  add    rsi, 0x208
    1413fc5fc  cmp    edi, 0x64
    1413fc5ff  jb     0x1413fc5d0

So 0x64 is the size of the *copy's* fixture array and the 0x7d0 beside it is the
dummy-select against the block's cap -- which the set already raises, at `0x1413fc5d0` and
`0x1413fc990`. `layout.json`'s hold_note says these copy-side numbers stay at their shipped
values because the copy keeps its shipped layout, and they do.

Nothing to change. Recorded because "a bound of 100 next to the shipped fixtures base, left
unpatched" looks alarming until it is read in full, and the next person to run
`standbounds.py` will see the same three.

## A different crash: a real stack buffer overrun at a rollover

`FL_2026.exe.15604.dmp`, 17:03, while a chunk crossed New Year (day 364 -> 0):

    thread 13324  code c0000409  at 0x14159fc14  (.trace)
    rcx 0x2   r11 0x2c30

`c0000409` is STATUS_STACK_BUFFER_OVERRUN and `rcx = 2` is the fast-fail code for a stack
cookie check failure, so this one really is what I wrongly claimed the `0x1484ed4c0` dumps
were. Different crash, different class, and this time the evidence is the exception code
rather than an inference from a scanned stack.

The frame it died in is `0x141722690`:

    1417226a0  mov   eax, 0x2c40           ; chkstk: 0x2c40 bytes of locals
    1417226b7  mov   [rsp + 0x2c30], rax   ; the cookie, right above the buffer
    141722774  lea   rcx, [rsp + 0x30]
    141722779  mov   r8d, 0x2c00
    14172277f  call  0x1415a1720           ; memset(buf, 0, 0x2c00)
    141722790  ...
    1417227a2  call  0x141728990           ; fills it

`r11 = 0x2c30` in the dump is the cookie slot, which confirms the frame. The buffer runs
from `rsp+0x30` to `rsp+0x2c30` with the cookie immediately above it, so whatever
`0x141728990` writes ran past the end.

**Is it ours?** No patch in the set lands inside `0x141722000-0x141729400` -- not one of the
2750 caps patches, and none of hdr127's 29, which all sit in the `0x1413fb`-`0x14159e`
range. So no byte we changed is in that code. That is not the same as clearing us: the
buffer is filled from game state, and we have made that state larger.

`0x2c00` is exactly `128 * 0x58`, and `0x58` is the sub-record stride of the season header
-- the same structure hdr127 widens. That is suggestive and it is **not** a conclusion:
`0x2c00` has other factorisations, nothing has been shown to iterate that buffer per header
entry, and today has already produced two attributions that looked this clean and were
wrong. It is written down as the first thing to check, not as the answer.

**Checked, and the lead does not hold.** `0x141728990` was disassembled through to
`0x141729200`: it contains no `0xb4`, no `0x64`, no `0x187c`, no `0x4650` and no reference
to the standings getter. The only `0x58`s in it are xmm spill displacements in the prologue
and epilogue, not the sub-record stride. So the function that fills the buffer does not walk
the season header, and `0x2c00 = 128 * 0x58` is a coincidence of arithmetic. hdr127 is not
cleared -- the buffer is still filled from a world we made larger -- but the specific
mechanism that made it a suspect is ruled out.

**Frequency so far: once.** hdr127 has been installed since roughly 15:05 and has since run
655 game days in one unattended run plus this one, with four season rollovers, and this is
the first stack overrun. If it recurs the public note needs a warning; one occurrence does
not earn one.

The run recovered on its own and is playing again.

## Why later seasons lose their leagues: the set was generated without its date keys

Measured 2026-09-17 on the world that had just finished its fifth season, the one where the
in-game calendar for September 2029 was empty and 35 of our 39 leagues had no rounds.

What the match table (rec596) actually held, counted per competition and per the year stamp
at `+0x08` of the record:

    11     2280   OURS  {2025: 190, 2026: 380, 2027: 380, 2028: 380, 2029: 380, 2030: 380, 2031: 190}
    17      380         {2030: 190, 2031: 190}
    49      380   OURS  {65535: 380}
    60      380   OURS  {65535: 380}
    74     1511   OURS  {2025: 80, 2026: 120, 2027: 120, 2028: 120, 2029: 40, 65535: 1031}
    145    1900   OURS  {2025: 190, 2026: 110, 2027: 300, 2028: 300, 2029: 300, 2030: 300, 65535: 400}
    185     380   OURS  {65535: 380}

The records are there.  Every one of our leagues has its 380 (a 20-club double round robin),
allocated and holding the right competition id.  What they do not have is a **date**: the
year field reads 0xffff.  A match with no date is never put on a calendar day, and a match
that is not on a calendar day is never played.  That is the empty calendar, exactly.

The four leagues that still worked -- 11, 74, 138, 145 -- are the four that carry real years,
and they are also the four that are still in the calendar at all:

    competitions in the calendar : 35
    ours in the calendar         : [(11, 2280), (74, 480), (138, 300), (145, 1500)]

Two other things fall out of the same table and should not be mistaken for the fault:

  * **The match table is full**, 26000 of 26000.  It is full because competition 11 is
    keeping six seasons of history (2025..2031) while the shipped competitions keep two
    (2030, 2031).  Pruning works; it works on the shipped ones.  Whether ours are skipped by
    the pruner for the same reason they are skipped by the scheduler is not established.
  * **Nine calendar days sit at exactly 280 ids**, the ceiling, and all nine are the same
    weekday (100, 107, 114, 121, 142, 233, 261, 268, 275 are all 2 mod 7).  That is the
    stacked history of the four working leagues, 60 ids a day from competition 11 alone,
    which is six rounds of a 20-club league on one day.

### The cause

`patchset.py` takes `--date-keys`, and when it is not given it falls back to the module
default:

    DATE_KEYS = [11]

The set we have been running, `...-mlcopy-fixtures`, was generated when the fixture list was
raised from 6000 to 8000, and that invocation did not pass `--date-keys` or `--date-offsets`.
So the set carries one date key where the set it replaced carried thirty-nine:

    teams-coaches-regs-players-dates-matches-upper-mlcopy            keys=39  offs=39
    teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures   keys=1   offs=0
    teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-slots32  keys=39 offs=39

Competition 11 is the one key that survived, and competition 11 is the one league that played
all six seasons.  That is the whole shape of it.

What is **not** yet explained: why the first season still scheduled all 39.  With no date case
the first season's generator evidently finds dates another way, and only the rollover path
needs the jump-table case.  74, 138 and 145 dropping out in different seasons (2029, 2026,
2030) rather than all at once says the same thing -- there is a second path that works
sometimes.  That path is not mapped, and this note does not claim it is.

### The fix, and what it costs

Regenerated with the 39 keys and the measured offsets from the slots32 sibling:

    python tools/patchset.py teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures \
        --player-cap 51729 --date-keys <39 ids> --date-offsets <39 key:shift pairs>

    2760 patches, block 0x1877068 -> 0x3171a68

Eleven patches added, one removed, none changed.  `block_size_new`, `copy_size_new`,
`bases_new`, `relocated` and `mlcopy` are byte for byte what they were, so **this does not
move the edit block and existing saves stay loadable**.  Installed to
`SiderAddons\modules\fl26caps.lua`.

Not yet verified: this has not been played.  The claim above is about what the table holds
and which argument was missing, not yet about the season that comes out the other side.  The
test is a fresh world run past two rollovers with the year stamps checked afterwards.

## Open lead: one dated season costs 20,968 of the 26,000 match records

Measured on the first season of the fixed set, 2026-09-17:

    day 212, 20968 of 26000 match records live
    match ids placed : 20968 over 232 days
    busiest day      : 243 ids     (the ceiling is 280)
    days at the 280 ceiling : 0

That is one season, not a history: every competition in the table reads two calendar years,
2025 and 2026, which is one season spanning New Year.  39 leagues of 20 clubs are 14,820 of
it; the shipped competitions are the other ~6,150.

So the headroom is **5,032 records**, and what happens at the first rollover depends on an
ordering nobody has watched: if the generator frees the finished season before it allocates
the next one, 26,000 is enough forever; if it allocates first, it needs about 42,000 and
will run out on the first try.  The broken world gave one piece of evidence for the hopeful
answer -- the shipped competitions there held exactly two calendar years each, one season,
while the leagues that had kept their dates held six -- but that says pruning happens, not
when.

If it turns out to need more, the cost is known and it is not small: rec596 is 0x254 bytes a
record and matchflags is grown alongside it, so 26,000 -> 44,000 adds roughly eleven
megabytes to the edit block.  That moves the block, and **a save is only loadable by the
patch set that wrote it**, so it would be a break in save compatibility rather than another
free widening.  Not to be done on a guess; the rollover now running answers it either way.

## What is inside a phase table: the whole 0x187c, accounted for

The open lead from earlier today -- a blind four-byte scan of a phase table gave 81 distinct
low-12 values for a 20-club league and was abandoned -- is settled from the code instead, and
the guess it was testing was wrong.  A phase table is not a list of matches.

The release path is `0x14158fd90`.  It takes a header sub-record in `rcx`, reads the season
object the usual way (`call 0x1414b6a60`, then `[rax + 0x78]`), and walks the sub-record's
phase indices:

    14158fdcf  lea    r8, [r14 + 8]          ; the 20 phase indices at +0x08
    14158fde0  cmp    dword ptr [rax], -1    ; terminated by -1, at most 0x14 of them
    14158fe38  cmp    r14d, 0x258            ; the index must be below 600
    14158fe45  imul   rcx, r14, 0x187c
    14158fe4c  lea    rbx, [r9 + 0x4650]     ; the pool starts after the header
    14158fe5c  mov    dword ptr [rbx], 0xffffffff
    ... five member clears ...
    14158fe8f  mov    qword ptr [rbx + 0x1874], -1

So **`+0x00` reading 0xffffffff is a freed phase table**, written here and nowhere else in
this function, and the bound on a phase index is 600 -- the same 600 the pool is sized for.

The five clears are the five members, and each one names its own offset and shape:

    0x1414ff000   rcx + 0x0004   -> 0x1414fd600
    0x1414ff070   rcx + 0x0318   -> 0x140fc7d30, with 0xffff
    0x1414ff010   rcx + 0x0ad8   0x28 records of 0x14, count at +0x320, 0x28 at +0x324,
                                 a flag byte at +0x328
    0x1414fefa0   rcx + 0x0e04   the same code again, the same shape
    0x1414ff090   rcx + 0x1130   -> 0x140afc3b0

and `0x140fc7d30` gives the size of the member at `+0x318` away: it sets a flag at
`[rcx + 0x7bc]`, then clears 0x30 records of 0x14 bytes from `rcx` and another 0x30 from
`rcx + 0x3c4`.

Laid end to end that accounts for every byte:

    +0x0000  0x0004   the free flag; 0xffffffff means this table is not in use
    +0x0004  0x0314   cleared by 0x1414fd600 -- and 0x314 is the regulation record stride
    +0x0318  0x07c0   two arrays of 0x30 records of 0x14, with a flag at the end
    +0x0ad8  0x032c   0x28 records of 0x14, with count, capacity 0x28 and a flag
    +0x0e04  0x032c   the same again
    +0x1130  0x0744   cleared by 0x140afc3b0
    +0x1874  0x0008   set to -1 on release
                      ----
                      0x187c

0x0004 + 0x0314 = 0x0318, + 0x07c0 = 0x0ad8, + 0x032c = 0x0e04, + 0x032c = 0x1130,
+ 0x0744 = 0x1874, + 8 = 0x187c.  Nothing is left over, which is the check that the five
clears really are the whole structure and not five of a longer list.

What the numbers suggest, stated as a suggestion: 0x28 is 40 and 0x30 is 48, and a phase of a
competition has at most that many clubs in it.  Two 40-slot tables and two 48-slot tables in
one phase is the shape of a standings table kept more than one way (overall and home/away is
the obvious guess), not of a fixture list.  That is not established here; what is established
is the offsets, the sizes, and the free sentinel.

The earlier reading -- `(0x187c - 0x10) / 16 = 390` sixteen-byte records against 380 matches
in a 20-club double round robin -- is withdrawn.  It fitted a number and nothing else.

## 0x14159fc14 is `__report_gsfailure`, not a function worth reading

The stack buffer overrun dump (`c0000409`, `FL_2026.exe.15604.dmp`) reported its fault at
0x14159fc14.  Disassembled, that address is:

    14159fbf8  mov    qword ptr [rsp + 8], rcx
    14159fc01  mov    ecx, 0x17
    14159fc06  call   0x1422931b8
    14159fc0d  je     0x14159fc16
    14159fc0f  mov    ecx, 2
    14159fc14  int    0x29            ; __fastfail(FAST_FAIL_STACK_COOKIE_CHECK_FAILURE)

That is the CRT's `__report_gsfailure`: every stack-cookie failure in the process ends on
this one instruction, whichever function actually smashed its frame.  So the fault address
in that class of dump carries no information at all, and any attribution has to come from
the frame that failed its check -- for that dump, 0x141722690.

Written down because this is the second time today a cookie-check address invited a wrong
conclusion.  The first was reading a `__security_check_cookie` call on the stack as evidence
of a smash; this is the same trap from the other end.

## A header entry, field by field, from the code that claims a slot

`0x14158f9b0` is the function that gives a competition its place in a season's header, and
`0x14158faab` is the branch that writes a slot from scratch.  What it writes is the layout:

    14158facf  mov    dword ptr [rdx], eax                  ; the entry's key, copied in
    14158fad3  mov    word ptr [rdx + 4], bx                ; the competition id
    14158fadc  mov    qword ptr [rdx + 8], -1               ; twenty phase indices,
    ...        ...                                          ; ten qwords, 0x50 bytes
    14158fb24  mov    qword ptr [rdx + 0x50], -1

and the scan that finds the slot gives the stride and the count:

    14158f9c1  lea    r10, [rcx + 8]      ; first id at entry + 8
    14158f9e2  add    r10, 0x58           ; second at entry + 0x60
    14158f9e6  cmp    r11d, 2             ; two of them, and no more

So an entry of 0xb4 is

    +0x00  u32    the key
    +0x04  0x58   slot 0
    +0x5c  0x58   slot 1

    slot:  +0x00  u32    the key again
           +0x04  u16    the competition id; 0xffff is an empty slot
           +0x08  0x50   twenty phase indices, each -1 when unused

and 4 + 2 * 0x58 = 0xb4 exactly.  The earlier note had these offsets right but called the
u16 at +0x04 an "order"; it is the competition id, which is what the scan above compares
against its argument.

This gives a second and better occupancy number.  `hdrwatch.py` has been counting entries
whose key is neither zero nor the free sentinel, which is how much of the header has ever
been touched.  What the 100-competition wall was actually about is how many competitions a
season is carrying, and that is the number of slots whose id is not 0xffff -- two per entry.
The watcher now prints both.  They are the same number only while no entry has been retired,
and the measured fact that entries are never given back means they will drift apart.

Not established: whether anything ever writes 0xffff back into a slot's id.  Nothing in
this function does; it only claims slots and resets the phases of one it already holds.

### Looked for, not found: anything that empties a header slot

If a slot were ever given back, something would have to write 0xffff into the u16 at
slot + 0x04.  A byte scan of 0x14158d000 .. 0x1415a1000 -- the neighbourhood that holds
every header walker and every 0x187c site -- finds **no** `mov word ptr [reg + disp], 0xffff`
at all.  The four writes to a `+4` field in that range are `mov word ptr [r + 4], r16`, and
both of them that were read (0x141597940, 0x1415965c5) belong to a different structure: a
six-byte record copied as u32 + u16, with the cursor advanced by 6.

That is a negative from a scan, not a proof: a free could be written through a register
loaded with 0xffff somewhere else entirely, and this only covers one neighbourhood.  But it
agrees with what the live measurement says -- four seasons in, entries in use went 88, 115,
119, 124 and never fell -- and it is the reason the ceiling question stays open rather than
being answered with "it will be reclaimed".

## Correction: the u16 in a header slot is the season, not the competition

The note above read a header entry off the code that writes it and called the u16 at
slot + 0x04 the competition id.  Read out of a live season instead, it is the year.

    entry 0
      +000  82 00 00 00   the key: 130
      +004  82 00 00 00   slot 0 repeats it
      +008  e9 07 00 00   0x07e9 = 2025
      +00c  00 00 00 00   phase index 0
      +010  ff ff ...     the other nineteen indices, unused
      +05c  ff ff ff ff   slot 1's key: empty
      +060  ff ff 00 00   slot 1's year: 0xffff, so this entry holds one season

and the key is the regulation's own u32 key at regulation + 0x80, confirmed by matching
them across six entries:

    entry 0 key 130  phase 0 -> table comp 11 year 2025 ; regulation 10 key 130
    entry 1 key 9    phase 1 -> table comp 17 year 2025 ; regulation 13 key 9
    entry 2 key 10   phase 2 -> table comp 18 year 2025 ; regulation 14 key 10
    entry 3 key 11   phase 3 -> table comp 19 year 2025 ; regulation 15 key 11

So the corrected layout is

    entry  +0x00  u32    the regulation key, from regulation + 0x80
           +0x04  0x58   slot for one season
           +0x5c  0x58   slot for another season

    slot   +0x00  u32    the key again
           +0x04  u16    the season year; 0xffff means this slot is empty
           +0x08  0x50   twenty phase indices, -1 when unused

and the argument the claiming function compares against `word ptr [entry + 8]` is the year
it is being asked for, not a competition.  The code reading was right about every offset and
wrong about what one of them means, which is the difference between disassembling a writer
and looking at what it wrote.

Two consequences, both of which fit what has already been measured:

- **An entry is a competition, and its two slots are two seasons.**  That is why the shipped
  competitions keep exactly two calendar years of match records and why phase tables live
  across a rollover: the header is built to hold the season that is ending and the one
  starting.
- **The header ceiling is a ceiling on competitions, not on competition-seasons.**  127
  entries is 127 competitions, and the measured climb 88, 115, 119, 124 is the season
  learning about more competitions, not the same ones being counted twice.

The phase table's first dword is not a key in that numbering either: it reads `0b 00 e9 07`,
which is the competition id as a u16 and the year as a u16.  That is what makes
`hdrwatch.py`'s free test -- both halves 0xffff -- the right one.

### What the rollover should look like, written down before it happens

From the layout above, on the run now going (fresh season, 88 entries, 88 slots filled, 139
phase tables, 20,968 of 26,000 match records):

- **entries** should stay near 88.  An entry is a competition, and the rollover does not
  invent competitions; if entries jump by ~88 the "entry is a competition" reading is wrong.
- **slots filled** should roughly double, to ~176, as each competition's second slot takes
  the new season.
- **phase tables** should roughly double, to ~280 of 599.  They were 335, 355 and 375 on the
  old world, which is more than double 139 -- so if this one lands near 280 the earlier
  numbers were carrying a third season, and if it lands near 350 something else is holding
  tables open.
- **match records** are the one with no headroom for doubling: 20,968 of 26,000.  If the
  finished season is freed before the new one is allocated, this stays near 21,000; if not,
  it needs 42,000 and cannot have it.

And the thing the whole run exists to answer: **39 of 39 leagues still on the calendar, and
zero undated records.**  Anything else means the date keys were not the whole fault.

## What the four tables inside a phase actually hold

Read out of the live season (competition 11, phase 0, day 264, five rounds played).

**`+0x318` and `+0x6dc` -- the league table, twice.**  Each is up to 0x30 = 48 rows of 0x14,
and both hold exactly **20 live rows for a 20-club league**, which is the check that these
are clubs and not something that merely fits.  A row opens with the club handle and then the
position, and the positions tie the way a table does:

    0  0e 00 ea 45  01 00 00 00  07 02 10 04  06 20 00 03  02 00 00 00
    1  0d c0 e9 45  02 00 00 00  07 02 10 04  05 10 00 03  01 00 00 00
    2  0b 40 e9 45  03 00 00 00  05 01 20 00  06 20 00 03  02 00 00 00
    3  03 40 e7 45  04 00 00 00  ...
    4  06 00 e8 45  04 00 00 00  ...
    5  00 80 e6 45  06 00 00 00  ...

The remaining 0x0c of a row is packed into bytes and is **not** decoded here; the leading
byte differs between the two arrays (7 in the first, 4 in the second) on the same clubs, so
the two arrays are the same league counted two different ways rather than a copy.  48 rows
is the ceiling on clubs in one phase, which is comfortably above the 14-to-33 range these
worlds use.

**`+0xad8` and `+0xe04` -- leaderboards, not standings.**  Each is up to 0x28 = 40 rows of
0x14 with a count at +0x320.  The first held 31 rows over only 17 distinct clubs, so a club
appears more than once and these are not clubs at all:

    count=31, distinct clubs=17
    rank : 1, 2, 3, 3, 3, 3, 3, 8, 8, 8, ...
    tally: 4, 3, 2, 2, 2, 2, 2, 1, 1, 1, ...

A row is (something small, something large, the club handle, the rank, the tally).  Ranks
tie and then skip -- seven players tied third, the next is eighth -- and the tally falls 4,
3, 2, 1 five rounds into a season.  That is a top-scorers table, and the second one, 16 rows
with 3, 2, 1, is the same shape for a smaller tally.  40 rows is the ceiling, so these are
the top 40 of whatever they rank.

So the phase table is: the key, a competition-shaped block, **the league table twice**, **two
leaderboards**, and 0x744 at `+0x1130` that is still unread.  The earlier guess that a phase
table is a fixture list was wrong in every part.

### Measured: every league has a table, and it survives a crash and a reload

`leaguetable.py`, run on the day-264 season after it crashed and was recovered from the
slot-1 checkpoint:

    ours with a phase table : 39
    ours with a full table  : 39      (20 rows each, the full 20-club league)
    ours in the calendar    : 39 of 39
    undated records         : 0

The competitions that do have a phase table with no rows in it are the cups and the
knockouts -- competition 5 carries 14 phases and competition 34 carries 10, and neither is
a league -- so an empty league table there is what it should be, not a fault.

This is the other half of what the empty September 2029 screen showed: no calendar *and* no
table.  Both now read correctly on the fixed set, and they read correctly after a save and
a load, which is the path that used to lose things.

### Crash frequency on the evening of 17 September, recorded without a conclusion

Five dumps in under an hour on the fixed set:

    17:47:54  0x1484ed4c0    during season generation
    17:50:12  c0000409       at startup, inside a system DLL
    17:56:20  0x1484ed4c0    during season generation
    18:33:27  0x1531cc313    mid-chunk, callers all in 0x1403xxxx
    18:43:58  0x1484ed4c0    a minute after a save was loaded

All of them are the same family: a corrupted pointer held outright in a register
(`rcx = 0x1b6b5e701`, `r12 = 0x8d92b7cd`), most registers garbage, in `.impdata`, with no
patch of ours anywhere near.  This is the crash already written up as the game's own scene
setup, and none of it is new in kind.

What is worth writing down is the *rate*.  Earlier today a run went 655 game days unattended
with no crash at all.  Tonight the longest clear stretch was about thirty game days.  The
only thing that changed in between is the date keys -- which means 38 leagues that were
previously generating nothing are now generating fixtures, phases and tables every day.

That is a correlation and one evening of it.  It is **not** evidence that the fix causes
crashes: more of the game's own work being done is exactly what was asked for, and a crash
in the game's own scene code is not made ours by happening more often.  But if the rate
stays like this it changes what a long Master League feels like, and it would have to be
said in the public notes.  The checkpoint-and-recover supervisor is what makes the run
survive it either way.

### Checked, and cleared: the date stub cannot read past its own table

The new key list reaches regulation id 185 where the old one stopped at 143, and the
stub's table is 256 bytes, so it is worth asking what happens to an id above 255 --
especially since one of the eleven date patches repoints the `ja` at `0x14157f84b` so
that ids 176..1025 reach the stub instead of returning empty.

They cannot run off the end. The stub's first three instructions are

    movzx eax, di            ; the regulation id
    cmp   eax, 0x100
    jae   empty              ; 256 and above: restore and return, no calendar

so an id of 256..1025 leaves without touching the table, exactly as the empty case it
replaced would have done. Inside the table, an id that was never given a shift reads
0xff and takes the same exit. `build()` also refuses at generation time to place a key
outside 1..255.

So the crashes recorded tonight are not this. That does not make them the game's fault
by elimination -- it only removes the one piece of our own code that the new key list
plausibly changed the behaviour of.

### The screen at the moment of the crash: a new league's results page

Two legs in a row died between game days 271 and 275 and it looked deterministic; the
third leg went on to day 281, so it is not one particular day. What it is, a rolling
capture caught: the last frame before the window goes away is the match-results screen of
one of the new leagues -- "FL League 26, Matchday 6", five fixtures with scores, page 1 of
2, waiting on Next.

That places the crash in the results presentation, not in the simulation. It fits what the
dumps say and what disassembly of the fault address says: 0x1484ed4c0 is not code at all.
Disassembled it reads as nonsense (`mov cs, word ptr [rax]`, `out dx, al`), and every
general register in the dump holds a random-looking value. The process had already jumped
into data through a corrupted pointer and executed garbage before it faulted; the fault
address therefore names where it landed, not what went wrong. The two dumps taken from the
same repeated state fault at two different addresses (0x1484ed4c0 and 0x1531cc313), which
is the same conclusion from the other side.

Why now: on the set published before 2026-09-17, 38 of the 39 new leagues had no dated
matches, so they generated no results screens. With the dates fixed they all do. The crash
rate went from one unattended run of 655 game days without a crash to six deaths in an
hour. That is not proof of cause -- the honest statement is that the fix made the game do
a great deal of work it had previously been skipping, and the crash lives in that work.

The run still advances: each leg reloads the day-264 checkpoint or better and gains ten to
twenty days, so a rollover is reachable by restarts even at this rate. What it costs is
unattended running, which is exactly what a person playing this would notice.

### Tested and dropped: the crash is not a day with too many matches in it

The results screen is built from one calendar day's matches, and our world puts far more
matches on a day than the shipped game does -- the busiest day of this season holds 243.
A fixed-size list behind that screen would explain everything: an overrun writes over a
neighbouring object, the next call through it lands in data, and the fault address is
wherever it landed.

It does not survive contact with the numbers. `crashdays.py` joins each death's game day
to how many matches that day holds. Of the played days the median holds 86 matches and the
busiest 243; the two deaths whose day is known both happened on days holding 50, which is
busier than only 35% of played days. A run has also passed a 210-match day without
trouble. So the size of the day is not what decides it, and the results screen's list is
not the thing to look for.

Keep the tool running as more deaths accumulate -- two is a small number, and the one
thing worth noticing is that both were on days of exactly 50.

## A league-table row, decoded

A row of a phase table's league table is 0x14 bytes and now reads in full:

    +0x00  u32   club handle
    +0x04  u32   position, ties included
    +0x08  u8    points
    +0x09  48b   eight six-bit fields: won, lost, drawn, a fourth count,
                 then goals for and goals against as twelve bits each
    +0x0f  u8    matches played
    +0x10  u8    a second goal count
    +0x11  3     zero

The six-bit packing is the same idea the player ability block uses. Goals take two fields
each, which is why the odd fields read zero in every row seen -- no league here scores 64.

This is checked, not inferred from shape. On a 20-club league six rounds in: goals for
summed to 127 and goals against to 127; wins summed to 47 and losses to 47; 47 + 47 plus
13 drawn pairs is 60 matches, which is exactly what 20 clubs play in six rounds. Every row
also satisfies points = 3 * won + drawn and won + drawn + lost = played.

Two fields are not confirmed. The fourth six-bit field is never larger than that club's
wins and the byte at +0x10 never larger than its goals; across the league they sum to 26
and 72, against 47 wins and 127 goals. Wins at home and goals at home is what they look
like, and nothing yet rules out something else that is bounded the same way.

`leaguetable.py --comp N --full` now prints a real table -- played, won, drawn, lost,
goals for, goals against, points -- instead of a row of hex.

### The death days, with the day recovered from the log

`crashdays.py` now recovers the day even when the chunk ended with "day 264 -> None", by
keeping the running day from the progress lines above it. Four deaths on this run: days
246, 271, 271 and 281. Against a season whose played days hold a median of 86 matches and
at most 243, those days hold 50, 86, 86 and 50, in 5, 15, 15 and 5 competitions.

So there is no size effect, in either count. Two of the four fall on a day of exactly 50
matches in 5 competitions -- and every such day in the season is the same five leagues,
11, 143, 145, 146 and 185 -- which looked like something until the other two landed on a
15-competition day instead. A day carrying 210 matches across 21 of the new leagues has
been passed without trouble.

Day 271 twice over is the only repeat, and the leg that started from the same checkpoint a
third time went past it to 281. Nothing here identifies a trigger yet; what it does do is
close off "our world puts too much on one day" as the explanation.

### The phase table's last unread member, +0x1130, is an array of 93 mostly-empty rows

Read live from a new league six rounds into a season, the 0x744 bytes at +0x1130 are not
opaque: they are 93 rows of 0x14, laid out

    +0x00  u32   an id -- the competition id (176) in row 0, zero in every other row
    +0x04  u32   14, in every row
    +0x08  u16   0xffff
    +0x0a  u16   0
    +0x0c  u32   0
    +0x10  u32   0xffffffff

and a last row that breaks the pattern and reads as a terminator. Every row carries the
same constants, so nothing in it has been filled in yet at this point in the season. 93
matches no count in the league -- not the 20 clubs, not the 38 rounds, not the 48 rows the
league table allows -- so it is something that only fills later, or in a competition shaped
differently from a straight league.

That accounts for the whole 0x187c. Nothing in this member is written by anything the
season has done in six rounds, which also means it is not a candidate for the crash.

#### Correction to the paragraph above: nonsense at the fault address is expected there

I wrote that the process "had already jumped into data through a corrupted pointer and
executed garbage". That over-reads the evidence, and it contradicts what this repository
already knew. `.impdata` is the protector's section -- seventeen megabytes of
read-write-execute holding virtualised handlers -- so code there is not meant to
disassemble as x86, and every general register holding an unrecognisable value is the
virtual machine's own state, not proof of a wild jump. `crashdump.py` says as much in its
own docstring.

What stands from that paragraph is only the part that did not depend on the misreading:
the fault address names a protector handler rather than a feature, and two dumps of the
same repeated state fault at two different addresses. The place to look is the stack, and
`crashdump.py --threads` exists because the thread that dies here need not be the thread
to blame.

### Half of tonight's "crashes" were not crashes

The run's log calls a chunk that ends with "the game window is not there" a death, and I
counted those as crashes. They are not all the same event. Checked at 19:12 on 17
September: the game process had been alive since 18:49, no crash dump had been written
since 18:43, `today()` read 281 out of its memory -- and EnumWindows returned no top-level
window at all for its pid. The game had lost its window and kept running.

So the evening divides in two. Five genuine crashes, each with its own dump (17:47, 17:50,
17:56, 18:33, 18:43). Then a windowless process from about 19:02, which produced two more
"deaths" that were the same corpse being handed chunk after chunk, because `alive()` in
seasonplay only asked the task list. That is fixed; the crash-rate figure is corrected
down accordingly, and the correct statement is five crashes in the hour to 18:43 and none
after it.

This also means the two deaths I attributed to day 281 are one event, not two, and neither
is a crash. What remains of the crash-day table is days 246, 271 and 271 -- and the 50/5
pattern that looked like a lead was resting on the 281 entries.

#### The crash-day table, with stalls separated out

`crashdays.py` now matches each death against the crash-dump folder: a real crash leaves a
46 MB dump within a few minutes of itself, a lost window leaves nothing. On this run that
gives three crashes -- days 246, 271 and 271 -- and one windowless stall, counted twice
because two chunks were handed to the same corpse.

Those three days hold 50, 86 and 86 matches, in 5, 15 and 15 competitions, against a
median played day of 86 and a busiest of 243. Still no size effect, and the 50/5 pattern
now rests on a single crash rather than two, which is no pattern at all. Day 271 twice
over remains the only thing that repeats.

#### Correction again, and this one is the real answer: the agent died, not the game

The section above says the game "had lost its window and kept running". It had not. These
tools run in session 0 and cannot see session 1's windows at all -- that is the entire
reason `session1.py` and its scheduled `FL26Agent` exist -- so EnumWindows from here
returns nothing for a perfectly healthy game, and the check I ran to prove a windowless
game proved only that I had run it from the wrong place.

What actually happened at about 19:02 is that the session 1 agent stopped answering.
`python tools/session1.py ping` said so in one line at 19:34, after an hour spent on crash
dumps, the calendar, the size of the game day and a code change that made things worse:
`alive()` was given the same impossible window check, so it called every healthy game dead
and four legs in a row killed a good game and reloaded it. Both are reverted.

This repository already knew: `drive.py` carries the same lesson in a comment, dated 14
September, about four season attempts read as a dead game. It is now enforced rather than
remembered -- `seasonplay.py` pings the agent at the start of every run and starts it if it
is silent.

So the crash figures stand at five genuine crashes with dumps between 17:47 and 18:43, and
the "deaths" after 19:02 were the agent. `crashdays.py` still tells them apart correctly,
by whether a dump was written; only its explanation of the second category was wrong.

### The session 1 agent does not hang, it dies -- and it did it twice in fifteen minutes

After the 19:02 incident the agent was restarted at 19:35 and answered at 19:37 and 19:39.
By 19:49 it was gone again: not wedged, gone -- `Get-CimInstance` showed no
`session1_agent` process at all until the watchdog started one, and the new pid's creation
time is the second the watchdog acted.

Its own loop cannot explain that. It catches every exception around a command, throws away
a command that will not parse, and returns only on an explicit "bye". A python-level fault
would leave it running. So something takes the process out from under itself, and the
likeliest candidate is a native call inside a capture -- the agent screenshots by window
handle, and a window that goes away between the handle being fetched and the bitmap being
drawn is a fault in Win32, not a Python exception.

Nothing here confirms that. What is measured is only that the process disappears, twice in
fifteen minutes, on a night when the game is restarting often. For now the answer is the
watchdog: a ping every three minutes, restart on silence, which cost seven seconds the one
time it has fired. If the agent keeps dying at this rate the capture path is where to look.

### Correction, and the cause was mine: two clients on a channel that holds one command

The agent was not dying. `session1.py` talks to it through exactly one pair of files --
`cmd.json` in, `reply.json` out -- with no request ids and no queue. Two clients talking at
once read each other's replies and time out, and a timeout is reported as "the agent is not
answering in session 1", which is the same sentence as a dead agent.

At 18:53 I started a rolling screen capture to catch the frame before each death. It calls
`screen.grab` every six seconds, and `screen.grab` is a client of that channel -- two of
them, a focus and a shot. The season run is a client of the same channel continuously, for
every keypress and every screenshot it takes. The trouble began at 19:02, nine minutes
later, and everything that followed -- the "windowless game", the deaths with no dump, the
checkpoint that failed at 19:49 -- is consistent with commands and replies crossing.

Then I made it worse twice. The `alive()` window check could not work from session 0 at
all. The agent watchdog I added to protect the night polled the same single-file channel
every sixty seconds, from outside the run, which is the very thing that had caused the
problem; it reported the agent dead at 19:49 and 19:55 and restarted a healthy one both
times. Both are gone, and so is the rolling capture.

What this leaves standing: five real crashes with dumps between 17:47 and 18:43, and one
frame -- a new league's results page -- caught before one of them. The frame is still good
evidence. The rate is not, and nothing after 19:00 counts as a crash at all.

The rule, in the tools rather than in my head: while a season run is going, nothing else may
call the session 1 agent. Not a capture, not a watchdog, not a ping.

#### And the windowless game is real after all, measured the right way

With the run paused and nothing else on the channel, the agent -- which lives in session 1
and can see that desktop -- was asked for the window list at 20:03. It answered, and
listed the desktop: the NVIDIA overlay, Windows Input Experience, Program Manager, its own
console. No FL_2026 window, while the game's process was running in session 1 with a live
edit block.

So the state I described at 19:12 does exist; what was wrong was the instrument. Asking
EnumWindows from session 0 can never establish it, because that answer is empty for every
game, healthy or not. Asking the agent establishes it in one line, and the agent is the
only thing that can.

The game had been in that state since about 19:54, which is what the run had been
reporting all along. Recovery is the same as for a crash -- kill it and reload the
checkpoint -- and that is what the run does when it is left alone to do it.

### The header goes past the shipped wall in early January, and my prediction was already wrong

Watched live on the fixed set, one season, 39 new leagues. The header held 88 entries from
generation through to December -- day 302 still read 88, day 364 read 90 -- and then at day
4, the first week of January, it jumped to **111 of 127**, with 191 of 599 phase tables in
use. That is 11 competitions more than the shipped header could ever hold: on an unmodified
game those eleven are turned away without a word and write into the previous season's
table, which is the 76-matches-played, 130-points reading that started this whole line of
work. `fl26hdr127.lua` is doing exactly what it was written to do, and this is the first
time it has been seen doing it on a season that schedules all 39 leagues.

It also breaks the prediction I wrote down before this run: "entries should stay near 88".
They did not -- they were near 88 for two thirds of a season and then rose by 21 in a week,
when the winter rounds of the cups and continental competitions start. The prediction was
made from a season that had 38 leagues generating nothing, so it measured a quieter world
than this one.

That matters for the number that is actually at stake. Entries are never given back, so 111
of 127 leaves sixteen. If a rollover adds competitions the way January did, the ceiling is
close, and the failure at the ceiling is silent -- the same silent failure at a higher
number. The rollover this run is heading for now has two questions to answer, not one.

## The date fix is not the whole answer: five leagues were dropped at the year boundary

At day 364 the season held 21,308 match records with 39 of 39 new leagues on the calendar.
One chunk later, at day 4 of January, it held 22,417 -- and five of the new leagues were
gone: competitions 76, 93, 94, 96 and 98. Not undated, not unscheduled. Gone. Each had held
380 records, the full 38 rounds of a 20-club league, and now holds none. The other 34 still
hold 380 each, split across the two calendar years exactly as they should be (comp 11:
170 in 2025 and 210 in 2026).

Undated records remain at zero, so the date-key fix is doing its job and is not what failed
here. Something else drops whole leagues when the calendar turns over from one year to the
next, and it takes the match records with it.

The obvious suspect is capacity. The match table holds 26,000 and the run was at 21,308
before the turn; rebuilding the second half of the season while the first half is still
allocated could ask for more than that, and the freeing of five leagues' 1,900 records
looks like something being sacrificed rather than something being tidied. Against that:
22,417 plus the missing 1,900 is 24,317, still under 26,000, so if it is capacity then the
peak demand during the rebuild is higher than either figure and the arithmetic has to be
done at the moment it happens, not after.

What is worth noticing about the five is that they are a near-contiguous block -- 76, 93,
94, 96, 98 -- while 74 and 100 on either side survived. That is not the shape of a
capacity failure, which would drop whatever came last. It is closer to the shape of one
list running short.

This is the first thing to look at tomorrow. It also means the public note must not be
promoted from "cause found" to "fixed": the undated-record cause was real and is fixed, and
a second fault underneath it is now visible that was previously hidden by it.

### The five stopped at 18 rounds while everyone else reached 24

The dropped leagues are not gone as leagues. Competitions 76, 93, 94, 96 and 98 still have
their header entry, their phase table and a full 20-row standings table. What they have
lost is the rest of their season: their tables read 18 matches played, frozen, while every
surviving new league reads 24 (74, 100 and 176 all at 24, and comps 11 and 176 hold their
380 records split 170/210 and 180/200 across the two calendar years).

Eighteen rounds is where the first calendar year ends. So these five played up to the
December break and then were simply not carried into the new year's calendar, along with
all twenty of their remaining rounds -- 200 matches each, 1,000 in all, and the 1,900
records they had held were released.

That is the original symptom exactly -- a league that stops having fixtures while its table
sits there looking fine -- but occurring at a calendar-year boundary inside one season,
rather than between seasons. It was invisible before today because on the old set 38 of the
39 leagues had no dates at all and so never got as far as being dropped.

What to do with it tomorrow, in order: find what runs at the turn of the year and rebuilds
the calendar; see what it iterates and what bound it stops at; check whether the five are
last in whatever order that is, rather than last by competition id, which they are not.

### The likeliest cause: the calendar day hit its 280 ceiling when the new year was built

Ruled out first: the five are not a group in our own data. Their date shifts are 1, 2, 2,
2 and 5, spread across three of the seven, while leagues sharing each of those shifts
survived. Nothing in the patch set groups them.

What did change is the calendar. Before the turn no day in the season was at the ceiling --
the busiest held 243 of 280, and `calfull.py` reported zero days at 280 and zero within 20
of it. After the new year was built there are **two days at exactly 280** (days 37 and 268)
and one at 269 (day 23). Day 37 held 243 before and holds 280 now.

A day holds 280 match ids and the scheduler at 0x141350290 drops whatever does not fit
without a word -- which is why `calfull.py` was written. So a league whose next round falls
on a saturated day loses that round silently, and the five losing all twenty remaining
rounds rather than one suggests that a league which cannot place a round is abandoned for
the rest of the season rather than carried on to the next one.

That last step is inference, not measurement. What is measured: no day was full before, two
days are full now, and five leagues stopped exactly at the year boundary.

If it holds, the fix is the same kind as the others in this project and not a new idea: the
280 is a fixed count (`NCOUNT = 0x230` bytes inside a day stride of 0x2c4) and raising it is
the next cap to raise. That is tomorrow's work, and it wants the day stride and everything
that indexes it checked first, exactly as the team and regulation tables were.

## The day record is full: what the other 146 bytes are (2026-09-17, evening)

A calendar day is `0x2c4` bytes. 280 match-id slots account for `0x230`, and the day's
count is the `u16` at `+0x230` that the scheduler increments. That leaves 146 bytes, and
whether they are spare decides whether the 280 can be raised where it stands.

They are not spare. Read out of a live season, `+0x234` to `+0x2c4` is a second table --
eighteen entries of eight bytes:

    u16 kind
    i16 parameter
    u16 year
    u8  month
    u8  day

An unused entry reads `3f 00 ff ff ff ff 00 00`, kind 63. 132 days of 365 carry at least
one live entry, and every live entry repeats its own day's date, which is what identifies
the table as belonging to the day rather than being padding that happens to hold old bytes.
Day 0 carries kinds 6, 9, 60 and 62; almost every other day carries kind 9 alone with a
parameter of -11 or -31.

So the day record is fully used, and 280 cannot be grown in place. Raising it means a
wider day stride, which means relocating the calendar array the way the team, coach and
regulation tables were relocated -- and the calendar sits at a fixed offset inside the
edit block with the rest of the block behind it.

## How big that job is, measured rather than guessed

The code section (the protector renames it `.trace`, base `0x140001000`) names the
calendar base `0x16038a8` at 135 sites. Disassembling `0x120` bytes either side of each:

    77 of the 135 do day arithmetic
    46 of those carry all three constants -- stride 0x2c4, limit 0x118, count +0x230
    the rest carry one or two

For comparison, the regulation table's relocation touched a few dozen sites. This is the
largest cap in the game we have looked at, and it is the first one where the constant
cannot simply be rewritten in place.

## The ceiling is real but it is narrow

At day 57 of the second calendar year, with the date-key fix in: **22,571 matches across
248 of 365 days, 155 competitions with records, 155 of them on the calendar, and zero
undated records.** The fix is holding through a rollover.

Two days sit at exactly 280 -- day 37 and day 268 -- and one at 269. Everything else is
below 260, and 117 days of the year carry nothing at all. So the calendar is not full; it
is lumpy. Moving a handful of rounds off two days would clear the ceiling without touching
a single byte of code, and that is the cheaper fix to try first.

## The 280-slot ceiling is not what killed the five leagues

Written down earlier today as the leading explanation, and it is wrong. The measurement
that settles it, taken at day 85 of the second calendar year:

    155 competitions have match records
    155 of them are on the calendar
    0 records carry no date

If the calendar had refused an entry, the record would still exist -- the scheduler drops
the *date*, not the record, and the record would read as undated. There are none. The five
leagues have no match records at all. Nothing was dropped from the calendar; nothing was
ever made.

So the ceiling is a separate, real, and much smaller problem: two days of 365 sit at 280
while 117 days carry nothing. It is worth fixing by spreading dates, not by raising a cap
that would cost a relocation of the whole calendar.

## What the five dead leagues actually look like

They are FL League 07 to 11 -- competition ids 76, 93, 94, 96 and 98, regulation slots 58,
73, 74, 76 and 78. Everything except the fixtures is intact and indistinguishable from a
league that is playing:

- the regulation record is there and correctly named
- there is a season header entry
- there is exactly one phase table, and its twenty club rows hold real club handles
- a dead table and a live one differ only in the ids and handles they carry: 23 bytes of
  0x314 between FL League 06 and FL League 07, all of them identity

They are also contiguous: they are the 7th to 11th entries of our own list, and in
regulation-slot order every league of ours between slot 58 and slot 78 is dead while
everything outside that span is alive. Whatever went wrong took a run, not a scattering.

The fault is therefore in whatever generates a competition's fixtures at the turn of the
year, and it is upstream of dating. The only place it can be seen is inside one rollover,
so `tools/leaguewatch.py` now counts each of the 39 leagues' records and says which league
loses its season and on which day, and `tools/arraywatch.py` watches the arrays fill and
empty across the same moment. The run is at day 85 with the turn perhaps an hour away.

One number worth keeping in view while that happens: the club table is at 1506 of 1600.

## The calendar ceiling can be cleared without touching the game

`tools/dayplan.py`, run against the live season, searched the seven day-shifts for the
assignment that flattens the calendar best:

    round-robin 0..6 (what we ship):  peak 280  -- the ceiling exactly, on days 37 and 268
    searched assignment:              peak 240  -- the shipped competitions' own peak

At 240 our leagues contribute nothing to the busiest day and it has 40 free slots. So the
280-slot cap needs no raising for a 39-league world: it needs the leagues put on different
days, which is data we already control. The assignment is kept in
`docs/date-spread-2026-09-17.txt` and goes in the next regenerated set.

That is worth stating plainly against what was written earlier today: raising 280 would
have meant relocating the calendar and rewriting 77 code sites, and it would have bought
nothing a seven-value list of day shifts does not buy.

## The one caller of the scheduler, and where an unlisted competition is dropped

`0x141350290` has exactly one caller: `0x141350cf7`, inside `0x141350b40`. That function
takes a fixture record -- index bounded by `cmp eax, 0x7d0` (2000, the shipped fixture cap
our set raises) at `0x141350bca`, stride `0x208`, at block offset `0xd65f64` -- and walks
up to sixteen entries of `0x20` bytes in it.

For each entry it resolves a match id (`0x1414d6380`, `0xffff` means none, and the function
gives up on that entry), then resolves the match record (`0x1414bc990`), then calls
`0x14157f810`, which builds a list of triples: a day, a competition key and a two-bit
field. The competition it looks for comes out of the match record itself:

    141350cad  mov  r11d, [rbx + 4]        ; the match record's +0x04
    141350cb4  shr  edx, 0x10
    141350cb7  and  edx, 0xfff             ; the competition
    141350cc4  cmp  edx, [r9 + rcx*4 + 4]  ; against each entry of the list
    141350cd9  je   0x141350ce8            ; found: take its day
    141350ce4  jae  0x141350d01            ; ran out: skip, no day, no error

So the match is given a calendar day only if its competition appears in that list, and a
competition that does not appear is passed over without a word. That is the mechanism
behind the undated records of 2026-09-16: the set generated with one date key put one
competition in the list, and every other league's matches fell through `jae 0x141350d01`
and were never offered to the scheduler at all.

Worth keeping separate from the 280-slot ceiling. Both drop a fixture silently, but this
one drops it before the calendar is ever consulted.

## A prediction written before the rollover, so that it can be wrong

Recorded at 21:05 on 2026-09-17, with the run at day 163 of the second calendar year and
the turn still ahead.

The season header is filling faster than it did last year: 112 entries of 127 at day 74,
115 at day 163. An entry is never given back. Last year it stood at 88 through December,
90 on day 364, and 111 on day 4 -- a jump of twenty-one across the turn itself.

If it jumps by twenty-one again it wants 136 and it has 127. So:

- **The prediction.** At this rollover the header runs out, and the competitions that do
  not fit lose their season the way FL League 07 to 11 lost theirs -- regulation, clubs and
  phase table intact, no match records at all.
- **What would falsify it.** The header stops below 127 and leagues still die; or the
  header fills and every league keeps its fixtures.

This is a guess about a mechanism, not a measurement, and it is written down now precisely
so that it cannot be adjusted afterwards to fit whatever happens. It is also not obviously
right: last year the header reached 111 of 127 and never touched the ceiling, yet five
leagues died anyway. If the header is the cause, something must explain why 111 was enough
to kill them. If nothing does, the prediction is wrong and the cause is elsewhere.

`tools/hdrwatch.py` already warns at 125 and at full; `tools/leaguewatch.py` names the
league and the day. Both are running.

## The match-record allocator, and why a league can come out empty

`0x1414bc710` is the whole allocator. It is a linear scan of the match array for a header
`u16` of `0xffff`, bounded by the cap, claiming the slot by writing its own index:

    1414bc729  cmp  word ptr [r8 + r9 + 0xe9ff08], cx   ; free?
    1414bc736  cmp  eax, 0x32c8                         ; the cap
    1414bc73d  xor  eax, eax                            ; none free -> NULL
    1414bc749  mov  word ptr [rcx + r9 + 0xe9ff08], ax  ; claim

Both the bound and the base are in our patch set (26000, relocated to `0x1cf7910`), so
nothing is missed there.

What matters is what happens when it returns NULL. The league season generator is
`0x1413f4430`, reached as `0x1413ac170` -> `0x1413f36c0` -> `0x1413f38c9` for a competition
whose format dword at `+0x84` is 1:

    1413f4592  call 0x1414bc710
    1413f459d  je   0x1413f4793     ; failed -> the loop-continue stub
    1413f45b9  mov  word ptr [rax + 4], cx   ; competition id into the record

`0x1413f4793` is not an error path. It restores the base pointer and falls into the inner
loop's increment. So a failed allocation drops that one fixture and the loop rolls on;
there is no counter, no abort and no rollback. The function then returns 1 unconditionally
at `0x1413f4865`, and even that is thrown away -- at `0x1413f38d3` the caller clobbers `al`
with `movzx eax, bl` before looking at it.

**A competition can therefore report a fully generated season while having created no
matches at all.** The schedule structure is built earlier and separately
(`0x1413f40f0`, `0x1413f3010`, `0x1413f3e00`) and succeeds regardless, which is exactly
why the five dead leagues have a regulation, a header entry, a phase table and twenty club
rows and nothing to play. The cup and knockout paths (`0x1413f49f0`, `0x1413f54b0`,
`0x1413f59d0`, `0x1413f64f0`) fail the same way, some of them without even testing the
return value.

## A second prediction, same moment, different mechanism

Written at 21:08, still before the turn, alongside the header one above.

- **The prediction.** At the rollover the match array is briefly exhausted. The old season's
  records are freed per competition as each is regenerated, so occupancy hovers near its
  full-season figure and crosses 26000 for a while in the middle of the run. Every
  competition generated during that window comes out empty, and the ones after it recover
  as more old records are freed. That is precisely the shape observed: a contiguous run of
  five in the middle, with leagues before and after unharmed.
- **What would confirm it.** `arraywatch.py`, sampling every three seconds through the turn,
  sees rec596 reach 26000 of 26000.
- **What would falsify it.** rec596 never comes near the cap and leagues die anyway.

Of the two predictions this one is the better fit, because the header one cannot explain
why 111 of 127 was enough to kill five leagues last year. If it holds, the fix is the same
kind we have done five times: raise the cap. A full season is about 22,600 records, so
holding two of them at once wants roughly 46,000, and the array is already one of the
relocated ones.

## The match array is one dense season, and it cannot hold two

Measured at day 178, second calendar year:

    22,723 records in use
    highest index in use: 22,722
    runs of used records: 1
    free slots below the highest used index: 0

Not one hole. The array is packed solid from index 0 and nothing is given back while a
season is played -- records only accumulate. The years stamped at `+0x08` split
9,365 in 2025 and 13,358 in 2026, which is one football season running from August to May
across two calendar years, not two seasons sharing the array.

That changes where to look. **The dangerous moment is the generation of the next season,
around day 212, not the calendar New Year.** At that point the old season's 22,723 records
are sitting in the array and the new season needs about the same again. 22,723 + 22,600 is
45,300 against a cap of 26,000. Unless the old season is freed first -- and completely --
the allocator at `0x1414bc73d` starts returning NULL, and everything downstream of it
swallows that in silence.

This also puts a question mark over the earlier note that the five leagues lost their
records "at the 364 -> 4 wrap". An append-only array cannot lose records at the New Year.
What can be said from measurement is narrower and firmer: they have no records in the
current season, and the array holds exactly one season. Whether they lost them at the wrap
or never had them this season is not something the data in front of us can settle.

Both watchers now sample every three seconds through days 198-240 as well. The run is at
day 178, so that window is minutes away.

## What the match array would have to be, and the hard ceiling above it

If the next season's generation is what empties a league, the cap has to hold two seasons
at once, because nothing is freed until it is.

    one season, measured             22,723 records
    two at once, with some room      ~46,000
    46,000 x 0x254                   27,416,000 bytes, against 15,496,000 today
    the edit block                   about 51.8 MB today, about 63.7 MB then

`matchflags` is one byte per record and has to move with it, 26,000 -> 46,000.

**There is a hard ceiling above that, and it is 65,535.** A calendar day stores match ids
as `u16` and uses `0xffff` for an empty slot -- `mov word ptr [rbx + rax*2], r12w` in the
scheduler. So no match may ever have an id of 65,535 or more, whatever the array's cap
says. 46,000 sits comfortably under it; anything near 65,000 would not.

Not generating that set now, deliberately: `patchset.py` writes `sider/fl26caps.lua` as
well as the JSON, the season run restarts the game when it has to, and a restart that
picked up a different patch set than the save was made under is how a world gets damaged.
The numbers are recorded here and the set gets built when the run is finished.

## The regulation record's season state, and exactly what the five dead leagues lack

Comparing two dead leagues against two live neighbours (FL League 06 against 07, and 12
against 11) and keeping only the offsets where BOTH dead differ from BOTH live:

    +0x84         u32   format: 1 = league. The same for dead and live.
    +0x88..0x120  38 x u32   one fixture-record index per round.
                             live: 0x1b8, 0x1b9, 0x1ba, ... consecutive
                             dead: 0xffffffff throughout
    +0x170..      u32 club handles, the competition's participants
                             live: 0x45ff814e, 0x45ffc14f, 0x46000150, ...
                             dead: 0xffffffff throughout
    +0x2fc        u16   the season year
                             live: 0x7e9 (2025)      dead: 0xffff
    +0x302, +0x30a      two small fields that differ consistently
                             live: 0x331, 0x94       dead: 0x201, 0x80

So a dead league has no season year, no rounds and no participants in its regulation. The
38 entries at `+0x88` confirm what the fixture records are for: FL League 03's first entry
is fixture 326, whose `+0x0c` holds match id 3124, which is exactly where competition 60's
records begin in the match array. The chain regulation -> round -> fixture -> match record
is now readable end to end.

These are runtime fields, written when a season is generated. The dead leagues were passed
over before any of them was filled in, which is upstream of the allocator, upstream of
dating, and upstream of the calendar.

### One path checked and dropped

`CompetitionEntry.bin` in the built world looked like the participants list. It is not:
it holds 2,097 records over 1,427 competitions, one to five each, and seventeen of our
thirty-nine leagues have none -- including live ones like FL League 03, 06, 22 and 23. It
does not separate dead from live and says nothing about this. Recorded so the next person
does not spend the same twenty minutes on it.

## CONFIRMED, caught in the act: the match array runs out during the season generation

2026-09-17, 21:15. The prediction written an hour earlier, before the event, holds.

The season generation ran at day 181 -- the end of the old season, not the calendar New
Year and not day 212. The watcher saw all five previously empty leagues gain a season
within one sample:

    21:15:27  day 181  FL League 07 (id 76): 0 -> 380  gained its season
    21:15:27  day 181  FL League 08 (id 93): 0 -> 380  gained its season
    21:15:27  day 181  FL League 09 (id 94): 0 -> 380  gained its season
    21:15:27  day 181  FL League 10 (id 96): 0 -> 380  gained its season
    21:15:27  day 181  FL League 11 (id 98): 0 -> 380  gained its season

and the array immediately behind them:

    records in use   26,000 of 26,000     <- exactly the cap
    highest index    25,999
    runs             1                    <- no holes anywhere
    by year          2025: 5,430   2026: 14,601   2027: 5,969
    competitions with records   99, down from 168

It has stayed there, unmoving, across four samples twelve seconds apart.

So the mechanism is now measured rather than inferred. The old season is **not** freed
before the new one is built: 20,031 records of the season just finished were still in the
array while 5,969 of the new season had been created, and at that point the array was full.
From that instant `0x1414bc710` returns NULL for every request, `0x1413f4430` treats it as
a loop-continue, the function reports success anyway and the caller discards even that --
so every competition generated after the wall comes out with a regulation, clubs, a phase
table and no matches. That is exactly the state FL League 07 to 11 were found in.

It also explains why the casualties are a contiguous run in the middle rather than the end:
which leagues die depends only on where they fall in the generation order relative to the
moment the array fills. This time our five were early enough to be served, so the victims
will be whichever competitions come after them.

**The fix is a cap raise, and the numbers are already worked out above:** about 46,000
records so that a finished season and a new one fit side by side, `matchflags` moving with
it, and the hard ceiling of 65,535 well clear. Nothing about the calendar, the header or
the date keys needs to change for this.

## The victims are whoever comes after the wall, and this time there were 87

Measured on the same running game a few minutes later, at day 215, counting leagues by
whether their regulation has a round list at `+0x88`:

    leagues with a round list:   60
    leagues with none:           87
    competitions with any record of the new season: 31

The 87 are not scattered. They are the tail of the generation order: our FL League 19
through 39 in an unbroken run, together with the game's own later competitions -- Liga
Profesional de Futbol, Super League, Trendyol Super Lig, and the phase competitions
(First Phase, Top Six, Bottom six, Regular Season, Playoffs Group A and B).

Last season the array filled late and took five of ours. This season it filled early and
took twenty-one of ours and dozens of the game's own. Which leagues die is not a property
of the league at all -- it is only where they stand in the queue when the array runs out.

That also disposes of every theory that looked for something special about competitions
76, 93, 94, 96 and 98. There was never anything special about them.

The fixture watcher caught the other half of the same moment:

    21:19:58  RECORDS HANDED BACK: 2624 -> 1593 used (day 215)

so the fixture table *is* reclaimed at a season boundary. The match array is the one that
is not -- or not soon enough -- and that is the whole defect.

## Correction: the round array is 58 slots, not 38 -- and that is a ceiling on league size

Earlier tonight this file said the regulation holds "38 u32 fixture-record indices at
+0x88..+0x120, one per round". The 38 was inferred from where the differences stopped in a
live comparison, and it is wrong. The code says otherwise:

    0x1414c9db0   addRoundIndex(reg, fixtureRecord)
    0x1414c9dcc   cmp ..., 0x3a          ; 58 slots
    0x1414c9dde   cmp ..., 0x3a
    0x1414c9de6   mov dword ptr [rcx + rax*4 + 0x88], edx
    0x1414c9df0   setRoundIndexAt, same 0x3a bound

58 slots of four bytes is `+0x88` to `+0x170`, which lands exactly where the participant
handles begin -- so the two lists are back to back and the record has no room to spare
between them. A 38-round league fills 38 of the 58 and leaves the rest at -1, which is why
a live comparison sees differences stop at `+0x120`.

**This is a real ceiling and it is not in our patch set.** 58 rounds is a double
round-robin of 30 clubs. The README says league sizes from 14 to 33 have been tried: a
33-club league wants **66** rounds and would run off the end of this array. (66, not 64:
with an odd number of clubs one sits out each round, so a single round-robin takes n
rounds, not n-1. 33 clubs play 16 matches a round with one idle, for 33 rounds each half.)
`addRoundIndex`
returns 0 when it is full, and like everything else on this path nobody checks. Raising it
is not a matter of one immediate, because the array is bounded by the club list behind it.

## What the season rebuild actually does, and every place it can drop a competition

    0x141314fc0   the driver: builds the list of competitions active this season
    0x1413155c6   -> 0x141314350   teardown: writes 0x2fc = 0xffff and clears calendar days
    0x1413155da   -> 0x1413156e0   rebuild: per competition, 0x141315c00 calls 0x1413ac170

`0xffff` in the season year is therefore the **teardown value**, not an error code. A league
found with `0x2fc = 0xffff` was cleared and then never rebuilt -- which is exactly the state
the empty leagues are in, and it explains why everything else about them looks healthy.

Conditions that pass a competition over without an error, all confirmed by address:

    0x141315841  its id is not in the active list                      -> next competition
    0x141315863  bit 8 of the dword at +0x304 is clear (disabled)      -> next competition
    0x141315a1f  the participant count, word[reg+0x30a] & 0x7f, differs
                 from what it was before enumeration -> the clear/add/finalise trio is
                 skipped and the club list at +0x170 is left empty
    0x1413ac1ae  the regulation lookup returned NULL                   -> nothing built
    0x1413ac285  the format dword at +0x84 is not one of 1..6          -> nothing built

That fourth one is worth noting against the measurements: a dead league reads `+0x30a` =
0x80 and a live one 0x94, and `0x94 & 0x7f` is 20 -- twenty clubs -- while `0x80 & 0x7f` is
zero. So a torn-down league carries a participant count of zero, consistent with teardown
rather than with a distinct fault.

Two walls in this chain that our set already covers, checked rather than assumed: the
regulation lookup's linear scan at `0x1414bc88f` and the rebuild loop's dummy-record
fallback at `0x141315800` are both `cmp ..., 0x12c` (300) and both are patched to 600.

### Where this disagrees with the measurement, the measurement wins

The disassembly points at the calendar's 280-slot scan as the only capacity in the chain
that fails silently and can bite a run in the middle. Tonight's measurements say it is not
what happened: there were no undated records, and the match array was watched filling to
exactly 26,000 of 26,000 during the generation while 87 leagues -- an unbroken tail of the
order -- came out empty. The 280 ceiling is real and still worth the flatter date spread,
but it is not this defect.

## The fix, first result: a fresh season on the 46,000-record set

Built, installed and started at 21:23 on 2026-09-17. `sider.log` reports **all 2,760
patches applied**, block `0x1877068 -> 0x3cd4ae8`, and every guard module alongside it.

The season created on it, read at day 212:

    records used                20,968 of 46,000
    undated records             0
    our leagues with a round list    39 of 39
    our leagues with match records   39 of 39, 380 each

So one season costs about 21,000 records and two fit inside 46,000 with roughly 4,000 to
spare. That is the margin the whole fix rests on, and it is now a measured number rather
than the estimate of 22,600 used to size it.

Two other counts from the same read, worth keeping in view rather than acting on:
`regulations` stands at 538 of 600 and `teams` at 1,506 of 1,600.

The real test is the generation at the end of this season, and `nightK8.sh` is running it
with `leaguewatch.py` beside it to name any league that loses its fixtures.

## A save belongs to the patch set that made it (2026-09-17, 21:45)

A Master League save stores the tables as they were laid out when it was written, so the
save and the patch set are a matched pair. Raising a cap moves the tables and the old save
no longer fits.

Measured: the season saved under the 26,000-record set (slot 1, in-game 30/6/2026) was
loaded with the 46,000-record set installed. The load never completes. The spinner keeps
turning, the day counter stays at 0, the process stays responsive, GPU and CPU keep
working, nothing faults and nothing is logged. Five minutes of sampling the day counter
every fifteen seconds showed no movement at all. The only way out is to kill the game.

There is no error path here because the game does not know anything is wrong: it is
reading a table whose stride and base it believes are correct.

Practical consequence: **when a cap changes, every existing save is dead.** A test on a new
set starts from `seasonnew.py`, never from `seasonload.py`. Before spending time on a load
that will not finish, check which set wrote the save.

## The fixed set, second confirmation (2026-09-17, 22:02)

Fresh season on the 46,000-record set, built after the collision was cleaned up:

- day 232, hub reached, all menu steps reported ok
- match table at block+0x1cf7910, 46,000 records of 0x254, relocated
- **20,968 records in use**
- **all 39 of our leagues hold 380 records each; none is empty**
- 20,968 match ids on the daily lists, **0 days at the 280 cap**
- busiest day is day 37 with 223, leaving 57 spare

The date spread is doing its job: under the old offsets the busiest day sat at 280.

## The 33-club claim in the public README is over-stated (2026-09-17, 22:20)

The README says "League sizes from 14 to 33 clubs. Different sizes in the same world." What
was actually measured on 2026-09-13 is narrower: a 33-club league **starts a season**. That
is not the same as a 33-club league playing a full schedule, and the round array says it
cannot.

The arithmetic, against the 58-slot bound at `0x1414c9dcc`:

| clubs | rounds, double round-robin | fits 58? |
|---|---|---|
| 20 | 38 | yes |
| 24 | 46 | yes (and the game's own Competition Info says 46) |
| 30 | 58 | yes, exactly full |
| 31 | 62 | no |
| 33 | 66 | no, eight rounds over |

30 clubs is the largest size that fits, and it fits with nothing to spare. Above it
`addRoundIndex` returns 0 and, like every other refusal on this path, nobody checks the
return -- so the season still starts and the league simply stops having fixtures partway
through. That is the same shape of failure as the empty leagues, one level down.

The 24-club reading is the useful control: the game computed 46 rounds itself and the array
held them, which is why sizes up to the shipped maximum have never shown a problem.

**Not yet tested live**, because it needs a world built at 31+ clubs and the machine is on
the overnight rollover run. Until it is, the README claim should read 14 to 30, with 33
described as "starts a season, full schedule unverified".

## The five leagues that die at the rollover are NOT the record pool (2026-09-17, 22:30)

This corrects tonight's earlier conclusion in one specific way. Two different failures were
being read as one:

1. **87 leagues dead at the second generation.** That was the match-record pool. The array
   filled to exactly 26,000 of 26,000 with no holes, the allocator at `0x1414bc710` started
   returning NULL, and everything downstream swallowed it. Raising the pool to 46,000 fixed
   this, and the fix holds: a fresh season uses 20,968 of 46,000.

2. **Five leagues dead at the rollover: FL League 07, 08, 09, 10, 11, regulation ids 76, 93,
   94, 96, 98.** This is a different defect and the pool does not explain it. Measured on
   both sets, at the moment of the wrap:

   | set | pool at the wrap | our leagues left |
   |---|---|---|
   | 26,000 | 22,417 of 26,000 | 34 of 39 |
   | 46,000 | 22,672 of 46,000 | 34 of 39 |

   Neither run was anywhere near full, and the *same five* leagues die in the same order on
   both. Raising the pool changed nothing for them.

So the earlier line "there was never anything special about 76, 93, 94, 96, 98" was right
about the 87 and wrong about these five. Something is specific to them.

### What the five look like

    live   +0x2fc year 2025    +0x302 0x331   +0x304 0x4002dd00   +0x30a 0x4094 (20 clubs)
    dead   +0x2fc year 0xffff  +0x302 0x201   +0x304 0x4002dc00   +0x30a 0x4080 (0 clubs)

Every field is the teardown state. `0xffff` in the year is what `0x141314350` writes before
a rebuild, so this is not damage -- it is a league that was torn down and never built back.
The one bit that differs in `+0x304` is **bit 8**, which is exactly what the rebuild tests
at `0x141315863` before it will touch a competition, and the participant count at `+0x30a`
is exactly what `0x141315a1f` tests. Both are wrong on the dead five.

### What has been ruled out

* **The match-record pool.** 22,672 of 46,000 at the wrap. Not full.
* **The season header.** 115 of 127 entries in use after the five were dropped, 117 season
  slots filled, 197 of 599 phase tables. Twelve entries spare, so `fl26hdr127` is not the
  wall here either.
* **Queue position.** These five are not a contiguous tail. In the regulation table they sit
  at indices 58, 73, 74, 76 and 78, interleaved with healthy shipped competitions -- index
  57 (FL League 06) and 79 (FL League 12) are both fine.

### What is suggestive but not yet evidence

Regulation ids 76, 93, 94, 96 and 98 are the ids our world builder found free **inside the
shipped block of super cups and promotion play-offs** (ids 79 to 97: EFL Championship,
LaLiga 2, Ligue 2, Serie BKT, the three promotion play-offs, and seven super cups). Every
other FL league sits in a clean run of free ids. Whether that adjacency is the cause or a
coincidence of how ids were handed out is not established, and it must not be written down
as the answer until a measurement says so.

Note that bit 8 clear is a perfectly normal state elsewhere: every competition that only
runs in some years -- FIFA World Cup, UEFA EURO, Copa America, the qualifiers -- carries it
clear between tournaments. So the bit means "runs this season", and the question is who
decides that our five do not.

### The measurement that will settle it

`tools/deadwatch.py`, new. It samples the five and two healthy neighbours every two seconds
and prints a line only when a field moves. The order of the changes is the whole point: a
snapshot taken after the fact cannot tell a cause from its consequence. If the participant
count goes to zero first, we are hitting `0x141315a1f`; if bit 8 clears first, we are
hitting `0x141315863` and something upstream decided the league does not run.

Armed against the current overnight run, which reaches the next generation around day 212.

## Correction within the hour: the five are late, not dead (2026-09-17, 22:43)

`deadwatch.py` caught what a snapshot could never have shown. At **day 181** all five came
back at once:

    22:43:22  day 181  FL League 07 (id 76): year 2026, state 0x302 817, flags 0x4002dd00
                       (rebuild flag on), clubs 20, rounds 38
    ... the same line for ids 93, 94, 96 and 98, in the same second.

So they are not lost. They are torn down at the rollover with everything else, the other
thirty-four are rebuilt immediately, and these five are rebuilt **about a hundred game days
later**. Every field comes back correct: twenty clubs, thirty-eight rounds, the season year,
and the rebuild flag back on.

That makes the defect much smaller than it looked, and differently shaped: it is not
"five leagues die", it is "five leagues have no fixtures for the first third of the season".
Whether they then play a full thirty-eight rounds from day 181 onward, or a truncated one,
is the next thing to measure -- 38 rounds are listed, but listed is not played.

This also explains why every previous reading found exactly five leagues empty: every one of
those readings was taken between the wrap and day 181.

Eight seconds after the rebuild the game crashed -- `c0000005` at `0x1484ed4c0`, dump
`FL_2026.exe.7440.dmp`. Day 181 is also where the earlier stall screenshots came from. The
proximity is suggestive and nothing more until the dump is read.

### Who writes the flag

Found by scanning for the immediate rather than the displacement, which is why the earlier
displacement scan missed it:

    1414ca020  and dword ptr [rcx + 0x304], 0xfffffeff   ; clear bit 8
    1414ca02a  movzx eax, dl
    1414ca030  shl eax, 8
    1414ca033  or  dword ptr [rcx + 0x304], eax          ; set it from the argument
    1414ca039  ret

A two-line setter, `setRunsThisSeason(regulation, bool)`. Seven callers:

    14126f74c  14126f8be  14126f942  141270074  141315a4f  1413631f0  141522c00

`0x141315a4f` is inside the rebuild itself, immediately after the participant-count test at
`0x141315a1f` -- so the rebuild turns the flag on when it accepts a competition, which
confirms the flag is a **consequence** of being rebuilt and not the gate that decides it.
The gate is the active-competition list searched at `0x141315841`, and the flag is only read
afterwards at `0x141315863`.

The neighbouring setter at `0x1414ca000` does the same for bit 2, and `0x1414c99a9` clears
bit 8 as part of wiping a record.

## A launch crash that is the game killing itself on purpose (2026-09-17, 22:46)

Three crashes inside four minutes while the run was recovering. The third is worth writing
down because its address is readable and its meaning is unambiguous.

    141958487  lea  rdx, [rip + 0x1128aa2]   ; 'Fox/Scripts/Gr/init.lua'
    14195848e  mov  rcx, qword ptr [rsp + 0x78]
    141958493  call 0x14029e5d0              ; load that script
    141958498  test eax, eax
    14195849a  je   0x1419584a7              ; loaded -> carry on
    14195849c  mov  dword ptr [0], 0xdeadbeef

That last instruction is a deliberate fatal marker, not a pointer bug: a write of
`0xdeadbeef` to address zero is how this build says "cannot continue". It fires only when
the script load returns non-zero.

So a `c0000005` at `0x14195849c` means **a startup resource failed to load**, most plausibly
file contention while the previous instance was still releasing its handles -- the run had
stopped the game forty-five seconds earlier. It is not our tables and there is nothing to
find in the patch set. `gamerun --tries` is the right answer to it.

The other two in the same window:

* `0x1484ed4c0`, `c0000005`. Inside `.impdata`, the protector's 17 MB generated region
  (VA 0x143d14000 to 0x15b951a00). Disassembling the file there yields nonsense because the
  section is built at runtime, so the address names a protector handler and not a feature.
* `0x7fffec061858`, `c0000409` -- a stack cookie check, i.e. `__fastfail`, in a system
  module rather than the game.

## The five lose their club list, and nothing else (2026-09-17, 22:49)

The run crashed, reloaded the day-180 checkpoint, and `deadwatch` caught the load. This is
the cleanest reading of the defect so far, because the two healthy controls and the five
differ in exactly one field.

On a fresh boot, before any season is loaded, all seven records look identical: 20 clubs,
0 rounds, torn down. Then the save loads:

    22:49:43  FL League 06 (id  74): year 2025, state 0x302 817, flags 0x4002dd00, rounds 38
    22:49:43  FL League 07 (id  76): clubs 0
    22:49:43  FL League 08 (id  93): clubs 0
    22:49:43  FL League 09 (id  94): clubs 0
    22:49:43  FL League 10 (id  96): clubs 0
    22:49:43  FL League 11 (id  98): clubs 0
    22:49:43  FL League 12 (id 100): year 2025, state 0x302 817, flags 0x4002dd00, rounds 38

The controls gain a season year, a state, the rebuild flag and thirty-eight rounds. The five
gain none of that, and the single field that moves on them is the participant count at
`+0x30a`, which goes from 20 to **0**.

That is the input to the test at `0x141315a1f`, the third of the silent skips: a competition
whose participant count does not match is passed over with its club list left empty. So the
chain is now anchored at both ends -- the club list goes first, and everything else about
these leagues follows from it.

It also settles the direction of causation that `deadwatch` was written to answer: the
rebuild flag is not cleared to disable them, it simply never gets turned on, because the
rebuild never accepts them.

**What is still open:** why the club list is lost for these five and no others. Both
readings so far -- the wrap at day 73 and this load at day 180 -- show the same five, so it
is a property of the record and not of the moment. Their regulation ids (76, 93, 94, 96, 98)
remain the only structural thing known to distinguish them: they are the ids our builder
found free inside the shipped block of super cups and promotion play-offs.

The next test that would settle it is cheap in principle and costs one world rebuild: move
those five leagues to ids in a clean range and see whether the defect follows the ids or
stays with the leagues. That is a deliberate experiment for tomorrow, not something to slip
into the overnight run.

## The day-181 rebuild crashes the game, three times out of three (2026-09-17, 22:50)

The overnight run stopped being able to make progress, and the reason is exact.

| when | what happened | seconds later |
|---|---|---|
| 21:15:27 | the five gained their season at day 181 (26,000 set) | the `day181-stall` screenshots at 21:16-21:17 |
| 22:43:22 | the five gained their season at day 181 (46,000 set) | crash at 22:43:30, `c0000005` at `0x1484ed4c0` |
| 22:50:39 | the five gained their season at day 181, after a reload | crash at 22:50:45, `c0000005` at **the same** `0x1484ed4c0` |

Three for three, on both patch sets, and the two readable crashes are at the identical
address. The late rebuild of these five leagues is followed within six to eight seconds by
the process going down.

That makes the run a loop: it reloads the day-180 checkpoint, plays one day, rebuilds the
five, and dies. The supervisor was stopped rather than left to repeat that all night.

`0x1484ed4c0` is inside `.impdata`, so the address names a protector handler and the
instruction cannot be read from the file. What can be said without the dump's stack is that
it is reached only on this path, and that the path is the one where five competitions are
built a hundred game days after everything else.

### Why this is one defect and not two

The missing club list and the crash are the same event seen from two sides. The five are
skipped at the rollover because their participant count is zero; they are built later, when
something restores it; and building a competition's season in the middle of an already
running season is evidently not a case the game is prepared for. Fixing the club list would
remove the late rebuild, and removing the late rebuild would remove the crash.

### The experiment that follows

Move those five leagues off regulation ids 76, 93, 94, 96 and 98 and onto free ids in a
clean range, change nothing else, and rebuild. If the defect follows the ids, this is a
bad-id problem with a one-line fix in the world builder. If it stays with the leagues, the
ids are innocent and the cause is in how the five are placed relative to the shipped
competitions.

Note that all five of these ids were in the *good* twenty-three list from 2026-09-16 -- they
came through season **creation** perfectly. Whatever is wrong with them only shows at a
season **rollover**, which is a stage nothing was tested against until tonight.

## The day-181 crash, named: a lifted vector setter in the sky-capture path (2026-09-18)

Two dumps from tonight's day-181 failures -- `FL_2026.exe.7440.dmp` (22:43) and
`FL_2026.exe.19340.dmp` (22:50) -- are the same signature as the three from 2026-09-14:
fault at 0x1484ed4c0 in `.impdata`, and every register identical to those three except
`rcx`, which is the wild pointer: 0x1f0edeac1 and 0x1b5b5eac1 here against 0x1ecee0dc1,
0x1b535e701 and 0x1edad21c1 before.  Five of this class now.

What is new is that the stack is no longer a scan.  `crashdump.py` sweeps the stack for
values that look like return addresses, which can pick up stale ones, so the earlier entry
could only name a neighbourhood.  Tonight the two dumps agree on 32 of their 34 swept
frames, and five of those frames verify as a real chain -- each is exactly five bytes past
a `call` to the next frame's entry, and `funcinfo.py` confirms each callee has that one
call site:

    1419418a0
      -> 14193d910   'StartSkyCapture', 'ClearSkyCoefficients', 'FixSkyCoefficients'
        -> 14193ea40 'TppAtmosphere', 'atshFilePath', 'rayleighScatteringCoefficient'
          -> 1416c3110  'SH_LIGHTING'
            -> 1416c22b0
              -> 141718820   <- the crash is in here

and 0x141718820 is one instruction long:

    141718820  jmp 0x14eb93180

Its body was lifted into the protector, which is why the fault address is in `.impdata`.
The functions either side of it were not lifted, and they are all the same shape:

    141718830  movaps xmm0, xmmword ptr [rdx]
    141718833  movaps xmmword ptr [rcx + 0x90], xmm0
    14171883a  ret
    141718890  movaps xmm0, [rdx] / movaps [rcx + 0xc0], xmm0 / ret
    1417188a0  movaps xmm0, [rdx] / movaps [rcx + 0x150], xmm0 / ret

A family of tiny setters that copy a 16-byte vector into an object at a fixed offset --
object in `rcx`, source in `rdx`.  That matches the fault exactly: a write, through `rcx`,
to an address ending 0xeac1, which is not 16-byte aligned, and `movaps` to an unaligned
address faults.  `rdx` at the fault is 0x9c67b725, itself not a readable pointer.  So the
setter was called with a wild `this`.

This confirms the 2026-09-14 reading rather than replacing it: heap corruption upstream,
surfacing in whichever code allocates or dereferences next, and tonight that code is the
atmosphere's spherical-harmonic lighting setup.  Nothing in the chain reads a regulation,
a match record or a club.  The crash is in rendering, not in the season.

**The correlation with day 181 is three for three, but the three are not one crash.**  The
two above, 22:43:22 and 22:50:39 on the 46,000-record set, are this class.  The third,
21:15:27 on the 26,000-record set (`FL_2026.exe.15356.dmp`), is a different fault in a
different subsystem: a **read** at 0x158ecc042, address formed as `rdx 0x8206050 + r8
0x2e7ffe5a` -- base plus an index of 779,027,546, which is the bad-table-index shape, not a
wild pointer -- and its frames are the Fox effects system (`Fx`, `FxInfinityLifeNode`,
`FxRandomLifeNode`, `FxReceiveLifeNode`) with one message string from a layout helper,
`'W20091203010:The number of box(5) is not enough.'`.  Particles, not sky.

So what day 181 reliably produces is not one fault but a dying renderer: two subsystems,
two different failure shapes, neither of them reading a regulation, a match or a club.
Correlation is all it is.  The rebuild does not itself touch the
sky.  The honest statement is that whatever the late rebuild does allocates, and the heap
it allocates from is already damaged.  That points the bisection at our cap patches again,
as the older entry said: a bound raised on an array that was never grown to match.

The other two dumps written tonight are already-known events and not new evidence.
`FL_2026.exe.18916.dmp` at 22:46 is the deliberate 0xdeadbeef marker at 0x14195849c --
`Fox/Scripts/Gr/init.lua` failed to load -- and `FL_2026.exe.19128.dmp` at 22:46 is its
`__fastfail` companion (code 0xc0000409) in ntdll.  Both sit one minute after the 22:45
stop, which is the relaunch-contention case recorded earlier, not a season failure.

## Two things cleared out of the way for the id-move experiment (2026-09-18)

**The base tables.** The experiment was held up on not knowing which shipped pesdb to build
from.  It is settled by looking at what the game ships: `download\data_s2526.cpk` (12 Oct
2025) is the full set, and `a` (22 Oct), `b` (12 Nov) and `c` (15 Nov) are overlays that
carry only the files they change -- `a` has 6 tables, `b` 8, `c` 9, against the base's 16.
Later letter wins, which the growing tables confirm: CompetitionEntry 7466 -> 7477 -> 7484
-> 7789 bytes, CompetitionRegulation 10314 -> 10314 -> 10314 -> 10947.

`mkworld.py --base` wants one directory holding all four tables it reads, so the overlays
have to be flattened first.  Done, base then a then b then c, at

    <extracted game data>\common\etc\pesdb

which loads as 91 competitions, 214 regulations, 1317 entries.  (Note for anyone reading
`pesdb.load` instead: `FL26_PESDB` is a *path list*, newest CPK first, and searches in
order -- it does not need flattening.  `--base` does.)

**The ungrown-array theory is not supported statically.**  The 2026-09-14 entry proposed
that the heap corruption behind the 0x1484ed4c0 class is one of our own cap patches: a
bound raised on an array that was never enlarged to match.  `blindspots.py` exists to
answer exactly that -- it lists block references a patch set does not cover -- and for
`teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures` it prints

    fl26caps.<set>.lua: nothing uncovered

The one array that is *not* relocated, players, grows in place from 30001 to 33314 records
of 0x17c, ending at block+0xC12E78 -- 36 bytes below the regulation array's original base
at 0xc12e9c.  It grows over where the team array used to live, which is only safe because
teams is relocated and every reference to it is rewritten, and that is the thing
`blindspots.py` just confirmed.  So the static side is clean; if the corruption is ours it
is dynamic, and a bisection over the patch set is still the way to find it.

### The counts and dummies are already out of the way (2026-09-18)

One more version of the ungrown-array theory, checked and closed.  The player array is the
only one that grows in place, and the installed set takes it to **51729** records of 0x17c,
which reaches block+0x12bf13c -- well past where the regulation array used to start.  The
arrays tile the block almost solidly from 0 to 0x16038a8, so everything the grown players
run over is relocated: teams, regulations, coaches, upper1, fixtures, upper2, rec596.  The
one gap between them, 0xd0b0ec..0xd0bcf8, is not an array at all -- it holds the dummy
records and the counts, including the regulation count at 0xd0bcf4 that the season rebuild
loop reads.

Those are moved too.  The set carries 574 patches rewriting `0xd0bcf4 -> 0x3b20888` and a
further 128 rewriting the dummies to `0x3b1fc80`, onto a **belt** above the grown arrays
(block grows 0x1877068 -> 0x3cd4ae8, the belt sits at 0x3b1fc80).  So nothing the player
array grows over is still addressed where it used to be.

Two notes for anyone reading older entries against the live game.  The rebuild loop's
`cmp dword ptr [r14 + 0xd0bcf4], r13d` at 0x1413157e3 is the *file* address; under the set
it reads the belt.  And `patches/layout.json` currently states the player cap as 33314 with
a note deriving it from the unrelocated regulation base, while the installed set uses
51729 -- correct, because that set relocates the regulations -- so anything regenerating
this set must pass `--player-cap 51729` or it will not reproduce what is running.

### A stall rung that was added and taken straight back out (2026-09-18)

At 23:23 a run sat on the pre-season press conference -- a three-line question with
`(x) Confirm` under it -- long enough for the chunk to time out at 23:30 and for the
checkpoint after it to fail, because the save list cannot be reached from a conference.
The obvious rung to add is "press the button the screen names", and it was added.

It was wrong and is reverted.  The next screenshot, one rung later, shows the question
already answered and the conference running on with `OPTIONS Skip` -- so the keyboard's
enter does reach that screen, and the stall was the length of the sequence, not an
unanswerable prompt.  Meanwhile a rung that presses the pad's Confirm fires on every cycle
of the ladder, including the cycles where the game is sitting on the hub with the bar on
Forward Time, and two crosses there open the menu and take its first item -- which on a
match day is `To Next Match`.  That is the live match a run once played with nobody holding
the pad, and it is the one failure the ladder's comments are written around.

The rule the ladder already states, restated because it nearly got broken: a key that does
nothing costs a second and a half, a wrong confirm costs a season, so nothing that confirms
may be added without a screen read in front of it.

### Correction inside the hour: the sky-capture crash is not about day 181 (2026-09-18)

`FL_2026.exe.15924.dmp`, 23:50:54.  Sixth dump of the class, and it settles the question the
entry above left open.  Same fault, same registers to the bit -- `rax c8072890  rdx
9c67b725  rbx dbfedbdf  r9 7cc5b908  r10 14ab18846  r11 5dd5cd28  r12 ba238df7  r13
dba6d565  r14 b3eb6750  r15 f49f7b2c`, `rsp` ending 0xb18 as in every other one, so the same
depth on the same path -- with only `rcx` different again (0x1eab7e5c1).  31 of its 34
swept frames match the 22:50 dump.

What is new is when.  The run had just checkpointed **day 276** at 23:47:32 and started the
next chunk at 23:47:48; the crash came three minutes into ordinary play, nowhere near a
rollover and nowhere near day 181.  So the three-for-three at day 181 earlier tonight was
sampling, not cause: what actually happens is that the season generator runs on day 181 and
a long run spends a disproportionate share of its time there, so that is where the dice
were thrown most often.

The class is therefore **season-wide and intermittent**, which is what the 2026-09-14 entry
said before tonight's runs briefly suggested otherwise.  It also means the crossing
experiment now under way answers a smaller question than it was set up to answer -- it can
still say whether day 181 is *worse* than an ordinary day, but "the game died at 181" is no
longer evidence of anything by itself.

### The deaths so far land on heavy match days (2026-09-18, three samples)

`crashdays.py` over tonight's K10 log, against the calendar of this world:

    days that were played : 235, median 86 matches, busiest 243
    crash   day 301  180 matches in 18 competitions  -- busier than 92% of played days
    crash   day 297   80 matches in  8 competitions  -- busier than 49% of played days
    crash   day 301  180 matches in 18 competitions  -- busier than 92% of played days
    mean matches on a death day : 147   (median played day: 86)

147 against a median of 86, and two of the three on the same heavy day, is the shape the
tool was written to detect.  It is also **three samples**, two of which are the same day
reached twice, so it is a lead and nothing more -- and the day attributed is the last day
the log knew about, which is where the chunk started, not necessarily where it died.

What keeps it interesting rather than dismissible is that it fits the fault.  The crash is
in scene and lighting work with the allocator underneath it, and a results screen built
from 180 matches across 18 competitions allocates a great deal more than one built from the
few dozen the shipped game puts on a day.  None of these days is near the 280-per-day
calendar cap, so this would not be a cap overflow; it would be pressure.

Next time the night produces deaths, run this again before theorising.  If the mean walks
back down toward 86 as samples accumulate, the idea is dead.

### A five-minute reproduction of the five-league failure (2026-09-18)

The failure reproduced tonight from a checkpoint rather than from a fresh season, which
makes it cheap to test for the first time.  The sequence, from the watchers:

    00:22:55  day 297  loaded from slot 2; all 39 leagues hold 380 matches
    00:27:13  day   0  ids 76, 93, 94, 96, 98: clubs 20 -> 0, rounds 38 -> 0,
                       year torn down, rebuild flag off.  Nothing printed for the two
                       healthy controls, 74 and 100, so nothing on them moved.
    00:27:15  day   2  the same five: 380 matches -> 0.  34 of 39 leagues unaffected.

Five minutes from load to failure, against roughly thirty-five for a fresh season.  The
save that does it is kept at

    ...\2026\save\ML00000001.day297-repro      (with SYSTEM00000000.day297-repro)

Restore both over the live names and load slot 2 to run it again.  Note the standing rule
that a save belongs to the patch set that made it: this one is the 46,000-record set
`teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures`, and it will load forever
under anything else.

Two things this run adds.  The failure survives a save and a reload -- the world that loses
its five leagues is one that was written to disk at day 297 and read back -- so it is not an
artefact of a long uninterrupted session.  And the five went down as a unit, every field at
once inside one two-second sample, while the controls either side of them did not move at
all in that sample.  That is a different picture from the 22:49 capture, where the only
field that moved on the five was the participant count; both are consistent with the five
being torn down and not rebuilt, and neither yet says which write comes first.

This is exactly the save the id-move experiment wants: `_FL26G39IdMove` is built and waiting,
and the question is whether a world identical except for five numbers loses the same five
leagues.

### The id-move world differs by five bytes (2026-09-18)

Verified rather than asserted, because the whole value of the experiment is that nothing
else changed.  `_FL26G39IdMove` against `_FL26G39`, byte for byte:

    CompetitionRegulation.bin  253 rows, same length, 5 bytes differ
    all differences at offset +0x02 of a row -- the regulation id, and nothing else
      row 220: id  76 -> 186   (competition 136, 20 teams)
      row 221: id  93 -> 187   (competition 142, 20 teams)
      row 222: id  94 -> 188   (competition 143, 20 teams)
      row 223: id  96 -> 189   (competition 144, 20 teams)
      row 224: id  98 -> 190   (competition 145, 20 teams)
    every other file under common/etc/pesdb identical by checksum

Worth noticing while counting: the five sit on five **consecutive rows** of the built
table, fenced by working leagues at row 219 (id 74) and row 225 (id 100).  That is probably
nothing more than the id list being sorted -- 74, 76, 93, 94, 96, 98, 100 puts them next to
each other by construction -- but it is the first time the five have looked like a block
rather than a scatter, and the live array indices (58, 73, 74, 76, 78) had made them look
interleaved.  If the failure follows the ids after the move, that reading is wrong; if it
follows the rows, it is worth a second look.

## The five leagues are late, not lost -- and the rebuild survives (2026-09-18, 00:41)

Crossing attempt 1 of the K10 run, from the day-178 checkpoint, is the first time the
day-181 rebuild has been watched through to the other side.  What happened:

    00:35:13  day 178  loaded.  34 leagues at 380 matches; ids 76, 93, 94, 96, 98 at 0,
                       and on those five the ONLY field that moved on load was the club
                       count, 20 -> 0.  Year still torn down, state still dead, rebuild
                       flag still off, rounds still zero.  The two controls gained year,
                       state, flag and 38 rounds in the same instant.
    00:40:22  day 181  all five rebuilt in full: year 2026, state 0x331, rebuild flag on,
                       20 clubs, 38 rounds.
    00:41:13  day 181  all five at 380 matches.  0 of 39 leagues without a season.
    00:42+             the game is still running.

Two conclusions, and the second is the one that matters.

**The five are not dead.**  They are rebuilt with a complete season -- twenty clubs,
thirty-eight rounds, three hundred and eighty matches -- about a hundred game days after
everyone else.  Every earlier entry that called them dead was reading a snapshot taken
before day 181.  The world does end up with all thirty-nine leagues running.

**The rebuild is survivable.**  Three times earlier tonight the process died within eight
seconds of it, which is what made this experiment worth running; this time it passed
cleanly.  Together with the sixth dump of the sky-capture class landing at day 301, in
ordinary play, that settles it: the crash is an intermittent renderer fault that a long run
meets wherever it happens to be, and the day-181 rebuild was simply the place a stalled run
kept meeting it.  The rebuild was never the cause.

What is still open, and is now the whole of the problem: **why do those five miss the
rollover in the first place?**  The load capture above is the sharpest evidence yet -- the
club list is the only thing that goes, and it goes while the record around it stays exactly
as the teardown left it.  The five remaining crossings will say whether any of this varies.

### A third launch-time failure, and what it is (2026-09-18, 01:11)

`FL_2026.exe.19960.dmp`, code 0xc0000409 -- a deliberate `__fastfail`, not an access
violation -- at **0x14159fc14**, which unlike the usual one is in `.trace` and can be read.
It landed one and a half minutes after the run stopped the game for crossing attempt 3, and
the game came up on the retry immediately afterwards.

The enclosing function is 0x14159fbc4, reached from 0x14159eff8, and that function's strings
name it: `InitializeConditionVariable`, `SleepConditionVariableCS`,
`WakeAllConditionVariable`.  A condition-variable wrapper -- worker-thread
synchronisation -- failing its own check at startup, with `rcx 2` and `rdx -2` going in.

So the launch-time family now has three known members, all of them the game failing to come
up cleanly when relaunched seconds after the previous instance exited, and none of them
touching our data:

    0x14195849c   `mov [0], 0xdeadbeef` -- Fox/Scripts/Gr/init.lua would not load
    0x7fffec061858  its `__fastfail` companion in ntdll
    0x14159fc14   this one, in the condition-variable wrapper

The crash-dump watcher labels 0xc0000409 "not the usual crash, look at it", which was right
to do once.  It is now looked at: if it arrives within a couple of minutes of a deliberate
stop, it is the relaunch, and `gamerun --tries` is already the answer.

## The late rebuild jams the calendar against its ceiling (2026-09-18, 01:20)

Measured with `calfull.py` on the running game, one minute after the day-181 rebuild of
FL League 07-11 in crossing attempt 3:

    today            : day 181
    match ids placed : 34348 over 245 days
    days at the 280 ceiling : 22
      [0, 3, 4, 18, 21, 22, 25, 36, 37, 39, 266, 267, 270, 301, 302, 305, 326, 336, 337, 340]
    days within 20 of it    : 0

Against the same world earlier tonight, before any rollover, on a freshly generated season:

    20968 match ids, 0 days at the cap, busiest day 223 of 280, 57 to spare

So the five leagues coming back a hundred days late do not land in empty space.  Their
fixtures go onto a calendar that is still carrying the season everyone else is playing, and
**twenty-two days are now pinned at exactly 280** -- the hard per-day ceiling, past which
the scheduler at 0x141350290 drops what does not fit and says nothing.

Two things follow.  The first is that "all 39 leagues have 380 matches" and "all 39 leagues
will play 380 matches" are not the same statement, and tonight only the first is measured.
A day at exactly 280 is a day that was full when something else wanted in.

The second is a caution about an old conclusion rather than a reversal of it.  The
280-per-day ceiling was tested and rejected as the cause of the five leagues dying at the
rollover, and nothing here reopens that: at the rollover the calendar had room.  What is new
is that the ceiling **is** reached in the aftermath, once the late season is laid on top of
the live one, and no measurement of the five leagues' actual played fixtures has been taken
in that state.

The thing to measure next, and it needs a run that carries well past day 181 rather than a
crossing that stops at 200: how many of each late league's 380 matches ever appear on a
calendar day, and how many are quietly not placed.


## The calendar jam is a standing state, not a moment

Follow-up to the entry above, which left open whether the 22 days pinned at the
280-per-day ceiling were an artefact of the rebuild instant.

They are not. The same measurement, taken twenty-five game days later in the same
run (day 206) and again as the run ended (day 215):

    day 181   34348 match ids over 245 days   22 days at 280
    day 206   34348 match ids over 245 days   22 days at 280
    day 215   34348 match ids over 245 days   22 days at 280

Same total, same count, same day list
`[0, 3, 4, 18, 21, 22, 25, 36, 37, 39, 266, 267, 270, 301, 302, 305, 326, 336,
337, 340]`. Nothing is placed or dropped after the rebuild finishes: the calendar
the rebuild writes at day 181 is the calendar the season then plays.

Against a freshly generated season on the same set -- 20968 ids, zero full days,
busiest day 223, headroom 57 -- so the late rebuild adds 13380 ids and takes the
calendar from comfortable to pinned.

This does not say matches are lost. "380 listed in the regulation record" and "380
placed on calendar days" are still different statements, and the scheduler at
0x141350290 drops silently past the ceiling. The per-competition count is the
measurement that settles it, and it needs a run standing past day 181 to take:
`calfull.py --json <path>` (the flag takes a path; without one it raises
IndexError), then count placements per competition id against the five late
leagues' 380 each.


## 1204 matches are scheduled and never given a day

Measured on the crossing of day 181, with `calcomp.py` (new) against the live game:
for every competition, how many match records exist and how many of them appear in
some calendar day's list.

Before the rollover, at day 178: **nothing unplaced anywhere**. Every record of
every competition, ours and the shipped ones, sits on a day.

After the rebuild, at day 181: 35552 records in use, 34348 placed, so **1204
matches exist and are on no calendar day at all**. They belong to fifteen
competitions, and every one of them is ours:

    comp 176, 178, 180, 181 : 380 scheduled, 290 placed   -- 150 lost, 39%
    comp 184                : 380 scheduled, 300 placed
    comp 170, 171           : 380 scheduled, 330 placed
    comp 174, 179, 183      : 380 scheduled, 340 placed
    comp 185                : 380 scheduled, 350 placed
    comp 143, 145           : 210 of the 2027 half placed out of 210/200
    comp 144                : one single match
    comp 147                : one single match

The losses land on the leagues with the highest ids, and nothing is lost in the
2025 half. That is the signature of a scheduler filling days in competition order
until the 280-per-day ceiling is reached and dropping the rest without a word --
the drop at 0x141350290. The leagues that go last pay for it.

### A count that looks alarming and is not

Thirty of our 39 leagues hold 760 match records where nine hold 380. That is not a
duplicated season. The match record carries its own year at +0x08 (u16, with month
at +0x0a and day-of-month at +0x0b), and a football season spans two calendar
years, so one season is e.g. 180 records in 2026 plus 200 in 2027. A league with
760 is carrying the tail of last season as well as all of this one:

    comp 74  : 2025:180/180   2026:380/380   2027:200/200    = two seasons
    comp 96  : ------------   2026:180/180   2027:200/200    = this season only

The nine at 380 -- 49, 60, 61, 62, 76, 93, 94, 96 and 98 -- have no 2025 records at
all. Five of those nine are the five that the watcher reports as dying at the
rollover, so on this crossing **the five came out with 380 scheduled and 380
placed: fully built and fully on the calendar.** They are not the ones losing
matches. Why those nine drop their previous season while the other thirty keep it
is a separate question and is not answered here.

### What this changes

The open question from the previous entry -- "380 listed is not 380 played" -- is
now measured, and the answer is that roughly one match in 28 never gets a day, all
of it on our leagues, none of it on the five that looked broken. The ceiling is
doing real damage to the season, just not to the leagues we were watching.

`dayplan.py` already exists to spread leagues apart rather than raise the ceiling
(the ceiling is not liftable -- see the 280-per-day note). Spreading the fifteen
losing competitions is the obvious next move, and this measurement is the way to
tell whether it worked: rerun `calcomp.py` after the rebuild and the number to
reach is zero unplaced.


### dayplan.py cannot see the matches it needs to move

Noted while reaching for the spreading tool: `dayplan.py`'s `measure()` builds its
per-league day load by walking the calendar and counting ids. That was correct
while everything was placed, and it is not correct now. The 1204 matches the
scheduler dropped are on no day, so they are invisible to it -- it would optimise
a load 1204 matches lighter than the real one and could report a comfortable peak
for a season that is still losing matches.

The other half of the same problem: the assignment currently in the set was
searched against a **freshly generated** season, 20968 ids with a peak of 223 and
57 days of headroom. The jam only exists after the rollover, when every league
carries the tail of one season and the whole of the next. A spread optimised for
year one is optimised for the easy case.

Both point the same way. The match record carries its own date -- year at +0x08,
month at +0x0a, day-of-month at +0x0b -- so the load a season *wants* can be
computed from the records alone, dropped matches included, instead of from the
calendar that already turned some away. Whether the record date maps onto the
calendar day index directly is being measured before anything is built on it.


### The relaunch crash, twice more, with a code this time

01:23:09 and 01:35:42, both within ninety seconds of a deliberate `gamerun.py
stop`, both `c0000409`, both at `0x7fffd23d38ad` -- a system module, not the game.
That is the launch/relaunch-contention family and the timing rule already covers
it: `c0000409` within a couple of minutes of a deliberate stop is a relaunch, and
`gamerun --tries` is the answer. Both crossings that followed ran to completion
rc 0, so nothing was blocked.

One detail worth keeping. `c0000409` arrives through `__fastfail`, whose code is
in rcx, and rcx here is 2 -- not the stack-cookie check the classifier's label
assumes. The registers are otherwise an empty frame (rdx, rsi, rdi all zero) and
the return addresses on the stack are stale .trace addresses rather than a live
chain. The classifier's "STACK BUFFER OVERRUN (cookie check)" label is the generic
name for the exception code, not a reading of this crash.


## Spreading the leagues is not enough any more, and by how much

With the demand measurement in hand, `dayplan.py` gained a `--demand` mode that
counts from the match records instead of from the calendar, and the search was run
against the real load of a second season (day 181, 35552 matches wanting a day).

    current assignment   peak 351   1204 matches turned away
    greedy               peak 308
    searched, 3000       peak 290     55 turned away
    searched, 15000      peak 290     35 turned away

Five times the search moves the overflow but not the peak, so 290 is the floor for
this world under seven day-shifts, and the ceiling is 280. **A day-shift alone
cannot fit this season.** It gets us from 1204 lost matches to about 35 -- a 97%
cut, and worth doing on its own -- but not to zero.

Why seven shifts is the whole space, and not an arbitrary cap worth widening: the
shift is a whole number of days added to every fixture of a league, and our leagues
play one round a week. A shift of 7 lands each round exactly where the previous
round was, so the per-day load is unchanged; shifts 7..13 duplicate 0..6 and buy
nothing. The datecave stub's seven is the natural limit, not a limitation.

The other number from the same run is the one that binds: **the shipped
competitions alone want 241 on their busiest day.** Of a 280-slot day that leaves
39 places for 39 leagues, and our leagues do not spread thinly enough to live
inside it.

So the remaining 35 have to come from somewhere other than the spread. The
options, smallest first:

  - Raise the per-day ceiling. Previously judged not worth pursuing because
    spreading was believed sufficient; that reason is now gone, and the target is
    small -- 290 rather than the 351 we have, so ten slots on the worst day.
  - Take load off the worst days at the source rather than shifting whole leagues.
  - Carry fewer leagues, which is the thing the project exists not to do.

Note for whoever reads the old note in project memory saying the ceiling does not
get raised, the leagues get spread instead: that was right when it was written and
it is now measured to be insufficient by ten slots.


### The blind spot, demonstrated rather than argued

Both modes were run against the same running game on the crossing of attempt 5,
which reproduced attempt 4 to the match: 35552 wanting a day, 34348 placed, 1204
turned away, the same 22 over-full days, still there at day 197.

    from the calendar : current peak 280, searched 266, "headroom 14 of 280"
    from the records  : current peak 351, searched 290, 35 matches still homeless

The calendar-based measurement reports a season that is comfortably inside the
ceiling and a plan with fourteen slots to spare. It is looking at a calendar that
has already thrown 1204 matches away -- of course nothing is over 280 on it;
nothing is allowed to be. Anyone tuning the spread on that number would have
shipped a world that silently drops a twentieth of its season and measured it as
healthy.

Use `--demand`. The old mode is kept only because it is the right measurement
before the first rollover, when the two agree.


## The reason the calendar was never widened has just been measured false

The ceiling was scoped in full back in September and then set aside. The scope is
not in doubt -- `calstride.py` walks the code and finds 519 sites, 135 of them the
calendar base, 81 the 0x2c4 stride, 65 the `cmp r, 0x118` limit, 101 the count at
+0x230, 99 an event slot and 38 the three fields reached past the array; 77 of the
135 do day arithmetic and 46 carry all three constants. The sites are already
enumerated in `patches/calendar-sites.json`.

It was set aside for this stated reason:

> raising 280 would have meant relocating the calendar and rewriting 77 code sites,
> and it would have bought nothing a seven-value list of day shifts does not buy.

The second half of that sentence is the part tonight's measurement contradicts.
Searched against the real load of a second season, the best seven-value list of day
shifts peaks at **290 against a ceiling of 280**, and 15000 iterations do not move
the peak. The shifts buy an enormous amount -- 1204 lost matches down to about 35 --
but they do not buy what widening the day would buy, because they cannot reach the
ceiling at all.

Nothing else in that analysis is overturned. The day record genuinely has no slack:
it ends exactly where the current-day field begins at 0x1642a1c, so the list cannot
grow in place and the array has to be relocated, the way teams, coaches and
regulations already were. The cost is what it always was. Only the "buys nothing"
has changed, and it has changed because the question moved: it was written when the
target was one season of 39 leagues, and the jam is a property of the second season,
which nothing had run through at the time.

A cap of 320 would cover the searched peak of 290 with room to spare: 320 ids is
0x280, plus the count and the 18 event slots gives a stride of 0x30c, and 365 of
those is 285 KB against the present 258 KB.

This is a large build and it is a decision, not a detail. Recording it here as the
one remaining route to "all 39 leagues actually play all 380 matches", with the
previous reasoning against it marked as superseded rather than deleted.


### The site list is still current

`calstride.py` was re-run tonight against the binary as it stands and its output is
**identical** to `patches/calendar-sites.json` from 14 September -- same 106
functions, same 519 sites, same 38/135/65/101/99/81 split, same 141 flagged for
review. So the scope above is not a stale number being quoted from an old entry; it
is what the code says now, and no re-derivation is needed before deciding.


## The nine leagues that come out of the rollover without their history

Measured on two separate crossings (attempts 4 and 6), and the two lists are
identical league for league:

    keeps last season's records   11 74 100 109 110 111 112 113 114 121 138 139
                                  140 143 144 145 146 170 171 173 174 176 178
                                  179 180 181 182 183 184 185      (30 leagues)
    new season only               49 60 61 62 76 93 94 96 98        (9 leagues)

A league that keeps its history carries 760 match records after the rollover -- the
2025 tail of the season just finished plus the whole of the new one. The nine carry
380: the new season and nothing behind it. The retained records add up to 5430,
which is the entire 2025 population of the table, so this is the whole of the
game's memory of last season and nine of our leagues are not in it.

Two things this is NOT, both checked rather than assumed:

  - It is not the late/on-time split. The five that rebuild late at day 181 are
    among the nine, but so are 49, 60, 61 and 62, which rebuild at day 178 with
    everyone else.
  - It is not simply "a low id". Ids below 100 among ours are 11, 49, 60, 61, 62,
    74, 76, 93, 94, 96 and 98, and two of those eleven -- 11 and 74 -- keep their
    history.

It is stable across crossings, which makes it a property of the world rather than
of a run, and that is what makes it testable. The id-move experiment already built
and waiting (`_FL26G39IdMove`, five bytes different, ids 76/93/94/96/98 moved to
186..190) now has a sharp prediction attached to it: if where an id sits is what
puts a league in the group of nine, those five should come out of the next rollover
holding last season's records like the thirty do. If they still come out bare, id
position is not the cause and the split is something else.

Whether losing last season's records is even harmful is not established. It is
visible in the records and history screens; nothing measured tonight says it
affects the season being played.


### A theory closed, and a caveat the id-move run has to carry

The regenerated set came out one patch smaller than the one it replaced, 2760 against
2759, and the missing patch is informative:

    jump-table byte at 0x141580333, 0x03 -> 0x3e
    "fixture dates: regulation 76 reuses a shipped id (case 3); send it to the stub"

Eight of our leagues sit on a competition id a shipped competition already uses, and
each needs its jump-table case sent to the date stub. Moving 76 up to 186 puts it on
a free id, so that patch is no longer needed -- hence one fewer.

That suggested an explanation for the nine leagues that lose last season's records,
and the explanation is wrong. The two sets barely overlap:

    reuse a shipped id   74, 76, 138, 139, 140, 144, 145, 146
    lose their history   49, 60, 61, 62, 76, 93, 94, 96, 98

Only 76 is in both, and 74 reuses an id while keeping its history. Closed.

The caveat matters more. **Regulation 76 is not a single-variable move.** Moving it
to 186 changes two things at once: where the id sits, and the fact that it no longer
collides with a shipped competition and no longer needs its case redirected. The
other four -- 93, 94, 96 and 98 to 187..190 -- are clean, none of them is in the
reuse list, and for those four the only difference is the id. So the experiment
should be read on those four, and 76 treated as a fifth data point that carries an
extra change.

Everything else about the regenerated set checks out as intended: `bases_new`,
`block_size_old` and `block_size_new` are identical to the set it replaces, and the
day-shift assignment is the same multiset of offsets simply renumbered onto the new
ids.


### A seventh .impdata fault, at a new address

02:18, six minutes into the id-move world's first season, day 232, ordinary play:

    c0000005 at 0x1531cc313 (.impdata)
    read of 0x11112b7cd, held outright in r12 -- a pointer, not an index
    rax = rbx = rdi = 0x14c1498af

Same shape as the sky-capture family -- a lifted routine in .impdata dereferencing a
register that holds garbage -- but a different faulting address and a different
register set, so it is not the `0x1484ed4c0` crash whose six dumps share their
registers to the bit. The repeated 0x14c1498af across three registers is a pointer
into .impdata itself, which is what the protector's thunks look like.

Recorded, not chased. It cost one chunk: the checkpoint at day 232 was written 26
seconds before the fault, so the run loses under a minute of play. This is exactly
what the five-minute chunking is for.


## The id-move world does not play, and a control says so

The id-move world was built, installed and given a fresh season at 02:13. In the
following half hour it made **no net progress at all**:

    02:15  checkpoint at day 232
    02:18  c0000005 at 0x1531cc313 in play      -> back to day 232
    02:30  c0000005 at 0x1484ed4c0 in play      -> back to day 232
    02:44  played day 232 -> 258, rc 0
    02:46  the game vanished during the save, no dump; the checkpoint was never
           written, so the 26 days were lost -> back to day 232

Four attempts, three in-play failures, day 232 at the end exactly as at the start.

Before blaming the moved ids, the obvious alternative had to be excluded: five hours
of continuous running may simply have left the machine or the game in a bad state.
So the original world was restored from the backup the run took (`patches/<set>.json`,
both lua copies, and the `cpk.root` line, verified back to `_FL26G39` on line 61) and
given the same work in the same minutes:

    02:58  control starts
    03:04  loaded slot 2 at day 178   (three launch attempts; see below)
    03:12  played day 178 -> 227, through the rollover, rc 0, no crash

Forty-nine game days including the day-181 rebuild, clean, immediately after the
moved world could not manage five minutes. **The machine is fine.**

An earlier reading of this, given while only the launch crashes were visible, said
the opposite -- that the machine had gone sour and the ids were innocent. That was
wrong and is corrected here. What confused it: the launch-time crashes are common to
both worlds and have nothing to do with either. The control needed three launches
too (`c0000409` at 0x7fffd23d38ad, `c0000409` at 0x7fffec061858, `c0000005` at
0x158ecc042) before one took. Launch failures are noise; what separates the two
worlds is what happens after the game is up.

This is evidence, not proof, and the gap in it is real: the control loaded an
existing save and fast-forwarded, while the moved world was playing out a fresh
first season. Those are different kinds of work. A mirror of the control is running
in the moved world now -- load its own day-232 checkpoint, play eight minutes, three
attempts -- which removes that difference and leaves the five ids as the only thing
between them.


## The id-move world quits; it does not crash

The mirror of the control was run in the moved world: load its own day-232
checkpoint, play eight minutes, three attempts -- the same work the original world
had just done cleanly.

    03:15  attempt 1 load -> rc 1, "the game window is not there"
    03:20  attempt 2 load -> rc 1
    03:24  attempt 3 load -> rc 1

Seven attempts now in the moved world across two runs -- four playing, three
loading -- and not one has completed. Against the original world in the same hour:
loaded, played 49 days, crossed the rollover, rc 0.

The failure is not the one that was assumed all evening. Three things say so:

  - **No crash dump.** The crash-dump folder has nothing after 03:00, and all three
    disappearances are later.
  - **No Windows log entry.** The Application log's last FL_2026 record is 03:00:35.
    The 03:20, 03:23 and 03:27 exits are not in it at all.
  - **No error from Sider.** `sider.log` runs to its last write at 03:25 with the
    title screen's assets being served and a soundtrack playing, then simply ends.

A crash leaves an exception, a dump and a log line. This leaves none of the three.
The process is ending without faulting -- the game is quitting, not dying. That is a
different investigation from the `.impdata` families, and nothing learned about them
applies to it.

It is also worth being clear about what the experiment did and did not answer. It
was meant to ask whether an id's position puts a league in the group of nine that
lose their history. **It never got to ask.** The world does not stay up long enough
to reach a rollover, so the question is still open and the answer is not "no".

What is established is narrower and still useful: a world identical to the working
one except that five regulation ids are 186..190 instead of 76, 93, 94, 96 and 98
cannot hold a session. Since `_FL26G39IdMove` differs from `_FL26G39` in exactly
five bytes, and the patch set differs only in the date keys and the one jump-table
patch that regulation 76 no longer needs, the cause is inside a very small space.

The original world was restored by the run itself and is being verified now. Nothing
about the working world was left changed: `cpk.root` on line 61 reads `_FL26G39`.


### Correction: the entry above claims more than the evidence carries

Written twenty minutes after it: the original world was put back and given the same
load, and **it failed the same way** -- 03:29 start, 03:33 `load rc 1`, "the game
window is not there", no dump, no Windows log entry.

So the comparison that entry rests on is confounded by time, not controlled:

    02:58 - 03:12   original world   loaded, played 49 days, rc 0
    03:13 - 03:27   moved world      three loads failed
    03:29 - 03:33   original world   load failed

The last success anywhere is 03:12. Whatever went wrong after it is not specific to
the moved world, and "a world that differs by five bytes cannot hold a session" is
not supported. The seven failed attempts are real; the attribution to the five ids
is withdrawn.

A second, worse process error sits underneath this. The standing rule in this
project is that a stall gets a screenshot before it gets a theory, and these
failures were reasoned about from logs, dumps and the Windows event log only. The
screenshot the load walk had already saved shows the game **alive at 165 fps on the
Master League hub** at the moment the walk believed it was on the save-slot list --
the file is even named `06-slots.png`. That is a navigation desync, visible at a
glance, and it was sitting on disk through the whole diagnosis. Three conclusions
were drawn and two of them reversed before anyone opened it.

What this leaves genuinely established about the id-move experiment: nothing. The
world was built and verified at five bytes, it was installed, and no run in it ever
reached a rollover. That is the whole result. The night's measurements that do not
depend on it -- the 1204 unplaced matches, the demand measurement, the day-shift
floor of 290, the nine leagues -- were taken in the original world before 03:12 and
are unaffected.


## 2026-09-18 03:45 — the load failures from 03:12 onward were a dead tool, not a dead world

Root cause of the run of seven failed load attempts: the session-1 agent process had
exited. With it gone, every tool that needs the screen reports "the game window is not
there" regardless of which world is installed, and a load returns rc 1 while the game is
in fact alive — the fixture watcher saw a fresh edit block at 03:36:40 during one of the
"failed" attempts.

Restarted with `python tools/session1.py start` (pid 5352). A single deliberate load of
slot 2 in the original world then succeeded: `loaded: season running at day 178`, and the
screenshot `tools/shots/check/09-loaded.png` shows the Master League hub drawing normally
(standings, fixture dates 3/5/2026-29/6/2026, fps counter live).

This supersedes both earlier attributions of those failures — first to the machine, then
to the id-move build. Neither was the cause. The two crashes at 02:18 and 02:30 in the
id-move world are a separate matter: those produced real dumps (0x1531cc313, 0x1484ed4c0)
and are not explained by the agent outage.

Process lesson, recorded because it cost the night: the answer was in screenshots the
walks had already written to disk. `tools/shots/control/06-slots.png` showed the game
alive on the hub at the moment the walk believed it was on the save-slot list. When a run
says "the game window is not there", the first action is to open the last image in that
run's shots folder.

## 2026-09-18 04:15 — the demand-offset build: one season fits with room to spare

A build was made whose ONLY difference from _FL26G39 is the per-league date offsets:
22 of the 39 changed to the values `dayplan --demand` found by minimising true demand
(what the season's match records ask for) instead of placed matches (what the calendar
managed to hold). Verified single-variable: `date_keys` identical, `bases_new` identical,
`block_size_new` identical, patch count 2760 in both, so the ids did not move and the
layout is unchanged. Offsets used:

    11:3,49:4,60:0,61:1,62:1,74:1,76:3,93:4,94:1,96:1,98:4,100:1,109:1,110:1,111:1,
    112:5,113:6,114:2,121:2,138:2,139:2,140:2,143:5,144:2,145:5,146:6,170:2,171:6,
    173:1,174:1,176:1,178:0,179:4,180:6,181:5,182:5,183:1,184:2,185:5

A fresh season generated cleanly and reached day 212. Measured there:

- all 39 leagues carry 380 matches: 14820 records, **14820 placed, 0 unplaced**
- busiest day wants 233 against the 280 ceiling — 47 places spare, **0 days over**
- 39 of 39 leagues present on the calendar; none lost its season at generation

Scope of that result, stated plainly: this is the ONE-season state. The old world was
also clean at a comparable point — its 1204 unplaced matches appeared only at the
rollover, where the finished season and the new one briefly overlap. The demand model
predicted a peak of ~290 against 280 for that overlapped state, which is why 233 here is
better than predicted rather than a contradiction. The decisive measurement is a crossing,
and a continuation run toward day ~181 of the next calendar year is under way.

## 2026-09-18 04:35 — two more ways to get "the game window is not there"

Three distinct causes now wear the same message, which is why it kept being misread:

1. **The session-1 agent is dead.** Every screen tool times out or reports no window, in
   any world. Fixed by `python tools/session1.py start`. It died twice tonight, at roughly
   03:12 and 04:26.
2. **The game is alive but has no window.** Process FL_2026 8620 was Responding=True with
   no entry in the session's window list, no crash dump and no Application-log record. A
   half-dead state that produces the message honestly.
3. **Two season walks driving one game.** The guard in the continuation script was
   `while pgrep -f seasonplay.py`, and `pgrep` does not exist in this Git Bash — the loop
   fell through silently, so a second `seasonplay.py` started at 04:19:58 while the first
   was still at day 232. Both walks then ran `gamerun`'s stray-process sweep and killed
   each other's helpers. This almost certainly produced the day-242 stall and the lost
   window. The guard now uses `tasklist`, which is always present, and refuses to start.

Discovered along the way and fixed on its own merits: the stall ladder answers every
dialog with its default, and every dialog here opens on No, so a dialog whose No keeps the
day where it is can hold a run indefinitely — `"You will proceed to the next day. The
transfer period will come to an end."` is one. `screen.knownyes()` now matches the dialog
box against reference thumbnails in `tools/dialogs/yes-*.png` and the new `yesdialog` rung
answers Yes only on a match; anything unrecognised keeps the safe default, because a blind
Yes on "Return to Top Menu? Unsaved data will be lost." throws the season away.

Stated honestly: with two walks fighting, the dialog cannot be shown to have been the
cause of that stall on its own. The fix is right regardless; the attribution is not
claimed.

## 2026-09-18 05:09 — the date offsets and the five-league death are independent

First crossing measured in the demand-offset world. At the New Year wrap (day 365 -> 0)
the same five leagues lost their clubs — 76, 93, 94, 96 and 98, each going 380 -> 0 with
`clubs 0`, `state 513`, rebuild flag OFF — while the other 34 kept theirs. Identical to
the signature in the original world.

So the two problems are separate and can be worked on separately:

- **matches with no calendar day** — addressed by the demand-based offsets (0 unplaced of
  14820 in the one-season state, busiest day 233 of 280);
- **five leagues losing their season at the wrap** — untouched by the offsets, and still
  open. Not the ids either: the id-move experiment never reached a rollover, so nothing
  is known about that route.

The run continues toward day ~181, where the rebuild happens and where the original world
left 1204 matches without a day. That measurement is the one that decides whether the
offset build is worth shipping.

## 2026-09-18 05:25 — scope decision: ship 34 leagues, come back to the other five later

Decision by the project owner. The five leagues that lose their clubs at the year wrap
(76, 93, 94, 96, 98) are a separate fault from everything else, measured tonight: the
demand-based date offsets fix the calendar loss completely and do not touch this at all.
Holding the whole project behind them costs more than they are worth right now — 34 new
leagues is already a large addition, and existing leagues can have their regions changed,
which is a further avenue that does not depend on this.

So the set is rebuilt with 34 date keys:

    11,49,60,61,62,74,100,109,110,111,112,113,114,121,138,139,140,143,144,145,146,
    170,171,173,174,176,178,179,180,181,182,183,184,185

The offsets are the demand-based ones, unchanged for the leagues that remain. No
re-measurement was needed to know they still fit: dropping five leagues can only reduce
the load on every calendar day, and the 39-league version already measured a busiest day
of 233 against the 280 ceiling. Build verified: 34 keys, bases and block size identical
to the installed layout, 2759 patches.

The five stay on the list as unfinished work, not as a failure — with the calendar problem
solved and the id-move experiment never having reached a rollover, nothing about them has
been ruled out.

## 2026-09-18 05:40 — the c0000409 address is never the bug

The stack-buffer-overrun dumps we keep collecting report a fault address that is always the
same kind of thing. 0x14159fc14, inside FL_2026.exe, disassembles to:

    14159fc01  mov  ecx, 0x17
    14159fc06  call 0x1422931b8          ; IsProcessorFeaturePresent(0x17)
    14159fc0d  je   0x14159fc16
    14159fc0f  mov  ecx, 2
    14159fc14  int  0x29                 ; __fastfail(FAST_FAIL_CORRUPT_LIST_ENTRY)

That is `__report_gsfailure` — the runtime's own reporter, reached after the corruption has
already happened. The same holds for the c0000409 entries that name an address in ntdll
(0x7fff...): those are the identical routine in another module.

So: a c0000409 fault address tells you nothing about the cause, and mapping it to a
function is wasted work. The caller's stack in the dump is the only thing worth reading
for these, unlike the c0000005 access violations where the faulting instruction is the
evidence.

## 2026-09-18 05:46 — correction: date_keys does not choose which leagues exist

The "34-league build" recorded an hour ago did not do what its name says, and the entry
above should be read with this one. `date_keys` is the list of leagues that receive a date
offset; it has nothing to do with which leagues the game creates. Dropping 76, 93, 94, 96
and 98 from it left all 39 leagues in the world with those five carrying no date table at
all. Measured straight after: 19068 match records wanting a day **and 1900 with an
unreadable date** — exactly 5 x 380.

The calendar itself was still fine (busiest day 223 of 280, nothing over the ceiling), so
the defect is the dateless records, not congestion.

Reverted to the 39-key demand build, which measured clean: 14820 of 14820 placed, busiest
day 233 of 280. The scope decision stands unchanged in substance — **we ship the 34 leagues
that survive the wrap and stop chasing the other five** — but that is a statement about the
outcome we accept, not about how the set is built. Removing a league for real means taking
it out of the club and regulation patches, which is a larger change and is not needed to
act on the decision.

Also corrected: the reasoning "fewer leagues can only lower the daily peak" was wrong for
the same reason. The leagues were never removed, so nothing was subtracted from the load —
the five simply moved to offset 0. The peak fell for a different reason than the one given.

## 2026-09-18 06:25 — the cup's regulation id collides with the id-move experiment

Noted before it costs a run. FL Cup 01 in `_FL26G39Cup` takes **regulation 186** (competition
174, knockout, bracket 16 — docs/plan.md:186, docs/findings.md:6697). The id-move experiment,
still unresolved, moves FL League 07-11 to **regulations 186-190**.

Those two cannot both be installed: the cup and FL League 07 would claim regulation 186.
Whichever is retried second has to be renumbered first. The cup has the older claim and is
already built, so the id move is the one to shift — 191-195 rather than 186-190 — if it is
ever retried.

Also recorded from the same read of the plan, because it fixes the order of work: a season
with the cup cannot be continued from a league-only save and vice versa (docs/plan.md:220-222).
Stage C therefore cannot start until the crossing measurement now running is finished.

## 2026-09-18 06:35 — the recurring 0x1484ed4c0 crash is heap corruption, not a bug at that address

Four crashes tonight at the same place. Dump FL_2026.exe.20064.dmp reads:

    thread 20004  code c0000005  at 0001484ed4c0  (impdata)
      access violation: write of 0001f372ec01
      rcx 00000001f372ec01        -- the address is held outright in rcx: a pointer, not an index

Static disassembly at that address is nonsense, because `.impdata` in memory is not what the
file holds at that offset — the usual reason attribution cannot see it. The call stack is
readable and is the evidence:

    00014038f23e   strings: 'jemalloc-3.4.0\src\jemalloc.c'
    00014038dfb2   strings: 'fox_foundation\modules\jemalloc-3.4.0\src\jemalloc.c',
                            'jemalloc/internal/arena.h'

The crash is inside **jemalloc**, the game's allocator, writing through a pointer that is
garbage — and the surrounding registers are garbage too. A fault inside the allocator while
it walks its own structures means the heap metadata was already corrupted by an earlier
out-of-bounds write. The allocator is the victim, not the culprit, and the faulting address
is therefore no more useful than the c0000409 one.

This is exactly the failure a capacity raise can cause: an array whose element count was
raised while the allocation that holds it was not. `patchset.py` reports "cap back edges:
443 raised site(s) swept across 7 array(s), none left behind", so the sites it knows about
are covered — the candidate is an allocation size computed somewhere that sweep does not
reach.

Next check, when the game is free: for each relocated table, compare the count the patch set
writes against the size of the allocation the game makes for it.

## 2026-09-18 08:10 — the crossing measured, and the offsets that actually fit it

The demand-offset build was carried through a full crossing and measured at the rebuild on
day 181, which is the two-season overlap state (760 records per league, not 380):

    35552 matches want a calendar day
    35110 get one
      442 do not  --  409 ours, 33 shipped
    busiest day wants 340 against the 280 ceiling; 10 days over

Against the original world's 1204, that is a two-thirds cut — real, but not the near-total
fix projected earlier. **That projection was wrong and here is why:** it was computed from a
single season's demand, while the state that actually loses matches has two seasons
overlapping. The model never saw the state it was predicting.

Re-planning against the overlap state first produced "STILL OVER: 45 matches", which was
also wrong, for a duller reason: `dayplan.py` ignored `FL26_SET` and defaulted to an older
set name without the `-fixtures` suffix, so it read a different world's `date_keys` and
planned for leagues 12, 13, 63-78, 101 and 102 — none of them installed. Fixed.

With the installed league list, the search finds:

    shipped peak 241, current peak 340
    searched: peak 281   busiest: day 37 = 281, day 268 = 281, then six days at 280
    STILL OVER: 2 matches

So the right offsets take the loss from 442 to 2, and the calendar ceiling stops being the
thing that decides whether these leagues play. The remaining two matches are the only part a
day shift cannot reach; widening the day would be for those alone, which is a much weaker
case than it was at 1204.

    --date-offsets 11:1,49:2,60:1,61:2,62:5,74:5,76:2,93:6,94:2,96:2,98:4,100:1,109:1,
    110:1,111:1,112:4,113:5,114:2,121:2,138:2,139:2,140:2,143:5,144:2,145:2,146:6,170:4,
    171:6,173:1,174:0,176:1,178:6,179:4,180:0,181:1,182:5,183:1,184:6,185:1

Method note worth keeping: plan against the worst state the season reaches, not the state
that is convenient to measure. Both wrong numbers tonight came from measuring the easy one.

## The 0x1484ed4c0 crash is deterministic, not random corruption

Measured 2026-09-18 across three separate dumps of the same signature
(processes 20692, 20064, 13148, taken at 08:18, 06:34 and 06:17, on two
different builds of the set).

Every general-purpose register except `rcx` and the stack pointer is
**identical bit for bit** in all three:

    rax c8072890   rdx 9c67b725   rbx dbfedbdf   rsi 0   rdi 0   r8 0
    r9  7cc5b908   r10 14ab18846  r11 5dd5cd28
    r12 ba238df7   r13 dba6d565   r14 b3eb6750   r15 f49f7b2c
    rbp = rsp + 0x1c8, rsp low 20 bits always 0xfeb18

Only the faulting pointer moves:

    rcx = 1eb72f4c1 / 1f372ec01 / 1ec76f241      (write, unaligned)

That rules out the reading it had been given. Garbage left by a stray write
does not reproduce to the bit across processes; a fixed code path does. These
registers are the protector's virtual-machine state at a single instruction in
`.impdata`, reached the same way every time. The crash is one deterministic
computation, and the only thing that varies is the address it computes.

What varies about `rcx` is consistent with a base that moves run to run (a heap
allocation) plus a large fixed displacement: all three land in 0x1eb–0x1f4
million, all three are unaligned, all three are writes. That is the shape of an
index running past the end of its allocation, not of a freed pointer being
reused — which is the same conclusion the jemalloc reading reached, but now
resting on evidence instead of on which allocator happened to be on the stack.

Consequence for the hunt: the question to answer is no longer "what corrupted
the heap" but "which array does a scaled index at this instruction belong to".
The displacement is fixed, so recovering the allocation base from one dump is
enough to name it. The jemalloc framing in the earlier entry is superseded —
the allocator is downstream of this, not upstream.

Practical note: this fires during season generation at the General Settings ->
OK step often enough that the walk's four-attempt retry exists for it, and a
retry usually gets through. It is intermittent in *whether* it is reached, not
in what it does once reached.

## The overlap measurement on the second demand build, and two corrections

Measured 2026-09-18 at day 215 of the second season, with both seasons present --
the state the first build was measured in, so the numbers are comparable.

    matches wanting a day : 35552
    of those, on a day    : 35387
    unplaced              : 165   (164 ours, 1 shipped)
    busiest day wanted    : 321   (the ceiling is 280)
    days over the ceiling : 10, asking for 165 places that do not exist

Against the build it replaces -- 442 unplaced, busiest day 340 -- that is a cut of
about two thirds, and against the state before any date planning (1204) it is about
seven eighths. It is a real improvement and the direction is right.

**It is not the 2 the plan promised, and that is the more useful result.**

`dayplan.py` searches on the assumption that moving a league from shift a to shift b
moves every one of its match days by (b - a) mod 7, so the search is exact arithmetic
on days it has actually measured rather than a model of the scheduler. Within one
generated season that is true. Across a regeneration it is not: the offsets are an
input to the fixture generator, so a different assignment does not shift the season
that was measured -- it produces a different season, with a different demand pattern,
and the arithmetic the plan was optimal for describes a world that no longer exists.

The plan is therefore a good heuristic and a bad promise. The honest way to use it is
to plan, rebuild, measure, and plan again from the new measurement -- and to expect
each round to improve the number without hitting the predicted one. Two rounds have
now gone 1204 -> 442 -> 165.

The leagues still short are all at the top of the id range: 183 and 185 lose 60 each,
174, 178 and 180 lose 10 each, 184 loses 12, 171 and 182 lose 1 each.

## The five leagues are not dead -- they lose a season, not their existence

Measured in the same run, and it corrects the framing this scope decision was made on.

At the rollover, competitions 76, 93, 94, 96 and 98 go from 380 fixtures to 0, as they
have every time. But at day 206 of the new year the monitor recorded all five going
0 -> 380 again, and at day 215 they read:

    76   380 records   380 placed   0 short
    93   380 records   380 placed   0 short      (the other 34 read 760, being two
    94   380 records   380 placed   0 short       seasons at once)
    96   380 records   380 placed   0 short
    98   380 records   380 placed   0 short

So the five do not stop existing and do not stop playing. What they lose is the
*previous* season -- the 34 carry the old season alongside the new one across the
rollover, and these five do not. Every one of them is fully scheduled in the season
that is actually being played.

That makes "34 leagues" the wrong description of what we have. We have 39 leagues
playing, five of which drop their history at the year boundary. Whether that is
acceptable to ship is a different and much smaller question than the one the scope
decision was answering, and it is the user's to make.

## Stage C: the cup is created and drawn, and never plays

Measured 2026-09-18 in `_FL26G39Cup`, a world that is `_FL26G39` plus exactly one
competition and nothing else: competition id 174 `FL_CUP_01`, regulation id 186,
knockout, 16 of our clubs entered. Teams and players byte-identical to the league
world, so the cup is the only variable.

A season generated in it reads, at day 212:

    comp 186    37 records     0 placed    37 short

The cup exists. It gets its bracket -- 37 match records is a drawn 16-team knockout,
not an empty shell. Not one of those matches is on a calendar day, so not one of them
will ever be played. All 39 leagues in the same season are fully scheduled.

This is the free-id wall, exactly as predicted before the run and for the predicted
reason: the date-template table the exe keys off regulation id covers ids 1..175 and
0x405..0x468, and **186 is in neither**, so there is no template to look up at all.
A cup is not scheduled by some other mechanism; it goes through the same door.

### What the case table says about the way out

`datecases.py` decoded against the shipped regulations gives the map directly. Case 62
is the empty case, and it holds 45 ids -- including every league we created (11, 49, 60,
61, 62, 93, 94, 96, 98, 100, 109-114, 121, 143, 170, 171, 173, 174). Those leagues play
only because our own datecave stub supplies their dates; the exe gives them nothing.

The shipped knockout cups sit in cases of their own, and one of them is our cup's exact
shape:

    case 38   id 122 (16 teams)  Belgian Croky Cup     <- 16-team domestic knockout
    case 39   id 124 (16 teams)  Kypello Elladas       <- likewise
    case  6   id 23 (44), 24 (20), 25 (20), 26 (18)    FA Cup, Coppa Italia, Copa del
                                                        Rey, Coupe de France

Note the last line, because it settles a question worth settling: **a case is shared by
many live competitions as a matter of course.** Nine ids share case 6 and all of them
run. So borrowing a template is not inherently a collision -- what collides is taking
an id another competition already owns, which is a different mistake.

### The route to try

There are 22 regulation ids below 175 with no regulation on them at all: 12, 13, 14, 32,
33, 63-66, 69-73, 75, 77, 78, 101, 102, 152, 153, 154. Most are in the empty case; 77
and 78 are in case 3, and 152-154 in case 53.

So: build the cup on a free id at or below 175 and point that id's case byte at 38. That
is one byte in the table at `0x1415802e8 + id - 1`, and it costs no new date logic --
the cup borrows a calendar the exe already carries for a competition of exactly its
shape. The alternative, teaching our datecave stub to emit cup-shaped dates for id 186,
is real work and only worth it if the borrowed shape turns out to be wrong.

## Stage C, continued: a cup below regulation 175 will not let a season generate

Measured 2026-09-18, eight generation attempts across three worlds that differ from the
league world by one competition and nothing else.

    cup on regulation 186, no case byte    season generates; cup has 37 ties, 0 dated
    cup on regulation  12, case byte 38    3 attempts, all died
    cup on regulation  12, NO case byte    2 attempts, all died
    cup on regulation 102, case byte 38    3 attempts, all died

Every one of the eight deaths is the same fault, and it is not the usual one: a write
at **0x140adfb62**, which is in `.trace` and therefore readable, unlike the recurring
`.impdata` crash.

    140adfb10  cmp   eax, 1600                    ; the team loop, fully patched
    140adfb29  lea   rcx, [rbx + 0x1877070]       ; teams, relocated -- correct
    140adfb35  mov   byte [rcx + 0x41d], 0xff     ; mark every team
    140adfb3c  cmp   eax, [rbx + 0x3b20880]       ; against the patched count
    ...
    140adfb4b  call  0x1414bca80                  ; -> rax
    140adfb62  mov   byte [rax + 0x41d], 0        ; rax is 0.  No null check.

So the loop over the team array is ours and is correct; the fault is one instruction
later. A lookup returns null and the code writes through it. The pattern reads as
"clear the flag on every team, then set it on the one team that is X" -- and for a cup
on a low id there is no such team.

**The two experiments that matter are the ones that rule things out.** Taking the case
byte away and leaving everything else changed nothing: the cup on 12 died the same way
without it. So the borrowed cup calendar is innocent -- the id itself is the variable.
And moving the cup from 12 to 102 changed nothing either, so 12 is not a special id;
the whole low range behaves this way.

That leaves the position for a cup exactly inverted, and worth stating plainly because
it is not what the league work would lead anyone to expect:

  - **below 175** the exe has a date template and the season will not generate at all
  - **above 175** the season generates and the cup is drawn, and never gets a date

A new league wants a low id. A new cup cannot have one. The remedy that works for
leagues -- borrow a shipped calendar through the case byte -- is unavailable to a cup,
because a cup cannot survive being where the case bytes are.

### What that leaves

The datecave route, which was the expensive option, is now the only one: teach our own
stub to emit cup-shaped dates for a regulation above 175, the way it already emits
league-shaped dates for ids the exe abandons. The stub already owns the dates of 39
leagues; a knockout is fewer records, not more, but it is a different shape -- rounds
that depend on the previous round's result rather than a fixed 38-week grid.

Not started. The league world and the 2760-patch set are back in place.

## The 0x1484ed4c0 crash fires during ordinary play, not only during generation

Until today every dump of this fault came from season generation, which made it easy to
read as a generation bug. On 18 September at 15:15 it took a season that had been running
for half an hour, mid-chunk, on day 274 of the Stage D world -- the game was advancing
days, not building anything.

The dump is the same crash, not a lookalike. Set against the previous one, every general
register matches to the bit:

    rax c8072890   rdx 9c67b725   rbx dbfedbdf   rsi 0   rdi 0   r8 0
    r9  7cc5b908   r10 14ab18846  r11 5dd5cd28
    r12 ba238df7   r13 dba6d565   r14 b3eb6750   r15 f49f7b2c

Only two things differ, and both are the two things that are allowed to: the faulting
pointer in rcx (0x1ecf3e981 here, 0x1f173e5c1 before) and the stack base. That is now
four dumps across three builds and two entirely different activities agreeing on the same
register set.

So the trigger is not "generating a season". Whatever computation this is, it runs in
both places, and it runs the same way each time -- which is the opposite of what heap
corruption looks like and one more reason to trust the deterministic reading.

The dump was a mini one (the standing policy: full dumps only when deliberately hunting,
never during a run), so tools/memmap.py cannot name the region rcx points into. Naming it
still needs a full dump of this exact fault.

## The cup now has a route: the date stub can call the cup calendar

Stage C ended with a cup that is created and drawn and never played, and with the finding
that a cup cannot live below regulation 175. That left one route, and it is now built.

The date switch's cases are not separate functions; they are inline bodies inside
0x14157f810, and each one tail-jumps to a helper. Case 5 -- the big league -- jumps to
0x141582550. Case 38 -- the Belgian Croky Cup, the 16-team domestic knockout -- jumps to
0x1415810d0. The two helpers have the same signature, id in cx and &vector in rdx, and
each does the same small job: copy a static array of 12-byte date records into the
vector. 38 records for the league (r14d = 0x26 at 0x141582587), 10 for the cup (edi = 0xa
at 0x1415810f1, stepping a table by 0xc).

Two helpers of identical shape means our own stub can choose between them. tools/datecave.py
now does: its table byte was a day shift 0..6, and is now a day shift plus a flag, with
0x10 meaning "take the cup calendar". The shift loop afterwards is untouched, because it
walks 12-byte records either way and never asks which helper filled them.

This is the only place a cup can be caught. Below 175 a cup will not let a season generate
at all; above 175 the switch never consults the case table and goes straight to its `ja`,
which is the branch this stub already owns. So the stub is not a convenience here -- it is
the mechanism.

Assembled: 100 bytes of code, 256 of table, 12 spare in the cave. Not yet run in the game.

## The cup date helper cannot be poisoned by an id it does not know

Before spending a game run on the cup stub it is worth knowing what 0x1415810d0 does with
a regulation id it has never seen. It does two separable things, and only the second one
looks the id up at all.

    1415810e7  lea   rbx, [rip + 0x140d912]     the ten date records, a fixed table
    1415810ee  movzx ebp, cx                    the id, kept for later
    1415810f1  mov   edi, 0xa                   ten of them
    141581100  mov   rdx, rbx / mov rcx, rsi / call 0x141586640    push one into the vector
    14158110b  add   rbx, 0xc / sub rdi, 1 / jne                   next

That loop is unconditional. It never consults the id, never consults the world, and pushes
the same ten 12-byte records whatever it was called for. So a cup on regulation 186 gets
ten dated rounds simply by reaching this helper -- which is exactly what the date stub now
arranges.

Only afterwards does the id matter:

    141581115  call  0x1414b6a60                the world
    14158111a  movzx edx, bp                    the id
    14158111d  mov   rcx, [rax + 0x48]
    141581121  call  0x1414bc860                find the regulation
    141581126  test  rax, rax / je exit         not found -- skip, do not crash
    14158112b  mov   ecx, [rax + 0x300] / shr ecx, 0x1d
    141581134  je    -> call 0x14157f720        top three bits 0
    14158113b  jne   -> exit                    top three bits 2 or more
    14158113d        call 0x14157f790           top three bits 1

Two things follow. The first is the one that mattered: the lookup is null-checked, so an
unknown id skips the tail and returns normally. Calling this helper for a regulation the
shipped game never meant it to see cannot fault.

The second is a lever we did not have. The dword at regulation+0x300, shifted right by 29,
picks between two extra date passes or none. That is the top three bits of the u16 state
field at +0x302, and it means a cup's shape here is not fixed by the helper -- the
regulation's own state word chooses which of the two tails runs. Untested; recorded
because it is the next thing to try if ten rounds turn out to be the wrong ten.

## Stage D: New Year is the wrong boundary -- the season ends in May

The Stage D experiment was designed around a sentence that turned out to be wrong: "the
link is written at the start of a season; whether it MEANS anything only shows at the year
boundary, when the tables finish." The tables do not finish at the year boundary.

The run crossed it at 15:46 on 18 September, day 364 -> 0 -> 4, and the two linked
regulations read:

    regulation 11   season 2025   says 20 clubs, holds 20   fingerprint 59ae0a64
    regulation 49   season 2025   says 20 clubs, holds 20   fingerprint 5dc89e0c

Not one club moved in either direction. But this is not a null result, because the season
year still reads 2025 and the club lists are bit-identical to the ones taken on day 274 and
on day 309 -- three readings, one fingerprint each side. Nothing had been decided because
nothing had finished.

Day 0 is 1 January. The football season runs from about day 206 to May. At the rollover it
is half played: the calendar year turned, the season did not. Promotion and relegation are
settled when the tables finish, which is somewhere around day 130-150, and the next season
is dealt out at day 206. So there is one window in which a finished table can be read
before a new season overwrites it, and it is not at New Year.

The control readings are what make this worth writing down rather than simply correcting.
Day 274 and day 309 have the same fingerprints as day 4, so the lists do not drift on their
own during a season. Whatever changes after the tables finish will be the tables' doing.

The run continues to day 190.

## Stage D, the same reasoning error twice: the list is participants, not standings

Day 148 is mid-May, the month the tables were supposed to finish in, and both divisions
read exactly what they read on day 274 of the previous year:

    regulation 11   season 2025   fingerprint 59ae0a64
    regulation 49   season 2025   fingerprint 5dc89e0c

Four readings now -- day 274, day 309, day 4, day 148 -- and one fingerprint each side.

The experiment has been aimed at the wrong day twice, and both times for the same reason.
First at New Year, because "the tables finish at the year boundary"; they do not, the
season runs to May. Then at day 190, because "the tables finish in May and must be read
before the next season overwrites them". That second one has the same shape as the first:
it assumes the club list is a standings table that gets filled in when the season ends.

It is not. The array at regulation+0x170 is the list of PARTICIPANTS. A finished table
says who goes down; the participant list is rewritten when the NEXT season is set up. That
happens on day 206 -- independently measured, because day 206 is when the five leagues that
lose their history are dealt a fresh 380-fixture season, and it is when every other league
gets its second season too.

So the swap, if the link means anything, lands on day 206 and not one day earlier. Nothing
before that can answer the question, and four clean readings before it are not four pieces
of evidence -- they are one, repeated.

The run is extended to day 215, a week past the deal, where the season year should read
2026.

## Stage D result: the link did not move a single club

Driven through the whole of the second season to day 215, past the deal. The answer is
negative, and three things had to be understood before it could be read at all.

**The year field does not mean "has this rolled".** It means "the oldest season this record
still holds". At day 215, thirty of our leagues read 2025 and nine read 2026 -- and
calcomp.py says the 2025 ones hold 760 match records and the 2026 ones hold 380. Two
seasons against one. Every one of the 39 had been dealt a new season; the nine simply threw
the old one away. Twenty-one days of play changed none of it, so this is a steady state and
not a rollover still in flight. `tools/seasonyear.py` prints it.

**In this world nine leagues drop their history, not five.** 49, 60, 61, 62, 76, 93, 94, 96
and 98. The five previously known (76, 93, 94, 96, 98) are a subset. What the extra four
have in common with them is not established.

**The result.** Regulations 11 and 49 both hold exactly the twenty clubs they started with.
Not one crossed. Both lists were REORDERED at the turn -- the fingerprints moved, which is
what the order-sensitive fingerprint is for -- and the new order is presumably last
season's finishing order. So the game did finish the tables and did use them for something.
It did not use them to promote or relegate.

**What this does not yet establish.** There is no control. Nobody has shown that the
shipped pairs promote in Master League either, and if they do not, then our link is not at
fault and the whole approach is aimed at something the mode does not do. The five shipped
second divisions have been snapshotted at day 215 for exactly that comparison at the next
crossing: EFL Championship (79, 24 clubs, fp 3c34fb7a), Liga 2 (80, 22, e1074aeb), Ligue 2
(81, 21, 07dfba87), Serie B (82, 20, db7ae890), Brasileirao Serie B (163, 20, 432d30c2).

**And a reason to doubt the premise.** The runtime regulation record does not look like the
file record: at +0x04, where tierlink.py's file layout has the promotion field, live memory
holds the competition NAME -- "FL League 01" reads straight out of reg 11 at +0x04. So the
four fields that tierlink writes are a FILE layout, and nothing has yet shown that the
runtime keeps them at all, let alone where. A link the runtime never loads would produce
exactly the result measured here. Finding where -- or whether -- the runtime holds the
promotion target is the next thing Stage D needs, and it is a memory question, not another
season.

## Stage E control: the cup was dated all along, and the date switch was never the problem

The control run -- the known-good set, no cup key, the same `_FL26G39Cup` world -- generated
on its first attempt at 17:12 (the 17:02 crash was the ordinary startup one and not this
session's death). It then read competition 186 as `37 records, 21 placed, 16 unplaced`,
where Stage C had read `37 records, 0 placed`. The 21 are not noise. Printed record by
record, the match record turns out to carry a real date -- year at `+0x08`, month at `+0x0a`,
day of month at `+0x0b` -- and a round id at `+0x06`. (`+0x0c` is a state word; two earlier
scripts of mine read it as the day and printed 0 and 1 for everything.) Grouped by round:

    regulation 186 (FL Cup 01, cloned from BELGIUM_CUP)
      round 0x2e:  8 matches   2025-09-09 x4  2025-09-12 x4
      round 0x2f: 16 matches   undated (year 0xffff), state 3
      round 0x33:  8 matches   2025-10-14 x4  2025-10-17 x4
      round 0x34:  4 matches   2026-01-07 x2  2026-01-10 x2
      round 0x35:  1 match     2026-02-14
    regulation 122 (Belgian Croky Cup)
      round 0x2e: 16 matches   2025-09-09 x8  2025-09-12 x8
      round 0x33:  8 matches   2025-10-14 x4  2025-10-17 x4
      round 0x34:  4 matches   2026-01-07 x2  2026-01-10 x2
      round 0x35:  1 match     2026-02-14

Our cup carries the Belgian cup's dates, round for round, with no patch touching the date
switch for id 186 at all. **A cup's rounds are dated by the template it was cloned from, not
by the regulation-id switch that dates leagues.** Stage E -- the cup branch in the date stub,
`CASE38`, the cup bit -- was built on the wrong premise. The code is harmless and stays, but
it is not the route.

What is actually wrong is the shape. The regulation on disk enters 16 clubs and says
bracket 16, which is Belgium's own shape. Live, the regulation's participant list at `+0x170`
holds **20** handles, and they are exactly the 20 handles of FL League 01 (regulation 11):
same set, nothing missing, nothing extra. The game ignores CompetitionEntry for a national
cup and fills it with the whole of the league it is tied to, the way Belgium's cup takes
Belgium's league. Twenty into a knockout needs a preliminary round to get to sixteen. That
preliminary is given round id 0x2e -- and 0x2e is where the Belgian template keeps the round
of 16's dates. So the preliminary plays on the Belgian round-of-16 days, the real round of
16 is pushed to id 0x2f, and Belgium has no 0x2f, so it is never dated. Sixteen undated
records, state 3, handles half `ffffffff`: a round waiting on a draw that will never be
given a day.

Why it read 0 placed in Stage C: it was read on the day the season was dealt, before the
calendar had been built; the scheduler places the records afterwards. Same records, later
reading, 21 of them on days. Not a contradiction, a timing error, and the same class of
error as the Stage D readings.

The shipped table already contains the cup that lives this exact life. Surveyed live, every
knockout under 120 records, participants counted from `+0x170`:

    ENGLAND_D1_CUP   reg 23  bracket 44  parts 20  recs 19   0x2e:4[09-12] 0x2f:8[10-17] 0x33:4[02-14] 0x34:2[03-28] 0x35:1[05-16]
    ITALY_D1_CUP     reg 24  bracket 20  parts 40  recs 39   0x2e:8 0x2f:16 0x30:8 0x33:4 0x34:2 0x35:1
    SPAIN_D1_CUP     reg 25  bracket 20  parts 42  recs 41   0x2e:10 0x2f:16 0x30:8 0x33:4 0x34:2 0x35:1
    FRANCE_D1_CUP    reg 26  bracket 18  parts 39  recs 38   0x2e:7 0x2f:16 0x30:8 0x33:4 0x34:2 0x35:1
    NETHERLANDS/PORTUGAL/TURKEY/GERMANY  parts 18  recs 17   0x2e:2 0x2f:8 0x33:4 0x34:2 0x35:1
    BELGIUM_CUP      reg 122 bracket 16  parts 16  recs 29   two legs: 0x2e:16 0x33:8 0x34:4 0x35:1
    RUSSIA_CUP       reg 123 bracket 16  parts 16  recs 15   0x2e:8 0x33:4 0x34:2 0x35:1

Two things fall out of the table. The number of matches follows the participant count, not
the "bracket" byte (England says 44 and draws 19 matches for 20 clubs). And templates
differ in which round ids they date: the ones built for 18-42 participants date 0x2f, the
16-club ones do not. England's cup is 20 participants from one 20-club league, single leg,
five dated rounds -- our situation exactly.

So Stage F is `_FL26G39Cup2`: the same world with the cup cloned `--like ENGLAND_D1_CUP
--bracket 44`, same ids (competition 174, regulation 186), the known-good set with no cup
key, no exe change. Expected reading: 19 records on 0x2e 0x2f 0x33 0x34 0x35, all dated,
0 unplaced. Then the season is walked to day 260 to see the four preliminary matches on
12 September actually played. Running as this is written.

Tooling note for the next time a record needs reading: `scratchpad/cuprounds.py` prints a
regulation's records grouped by round with dates; `cupsurvey.py` does the table above;
`cupreg.py` prints a regulation's live participants. All read-only.

## Stage F: the cup plays the wrong shape, and the fix is 16 clubs, not an exe patch

`_FL26G39Cup2` -- the cup cloned `--like ENGLAND_D1_CUP --bracket 44`, known-good set, no
cup key, no exe change -- generated on the third attempt (two ordinary scene-setup crashes
first, 0x1531cc313 and 0x1484ed4c0, both the game's own). Regulation 186 read as nineteen
records, the England shape:

    round 0x2e:  4 matches   2025-09-12   (the preliminary)
    round 0x2f:  8 matches   UNDATED, state 3   (the round of 16)
    round 0x33:  4 matches   2025-10-17
    round 0x34:  2 matches   2026-01-10
    round 0x35:  1 match     2026-02-14

Progress and a wall in one reading. The shape is now England's -- 4+8+4+2+1 = 19 single-leg
matches instead of Belgium's two-legged 8+4+2+1 -- but round 0x2f still carries no date, and
`calcomp` reads `19 records, 11 placed, 8 short`. The eight short are exactly round 0x2f.

The reason is now exact, from the disassembly. Whatever dates a cup, it ends at the ten-record
copy loop in the cup helper 0x1415810d0, which copies from a static table at 0x14298ea00.
That table holds twelve records covering rounds **0x2e, 0x33, 0x34, 0x35, 0x36** -- and no
0x2f. It is a sixteen-club bracket's shape: 16 -> 8 -> 4 -> 2 -> 1 across 0x2e/0x33/0x34/0x35,
which is exactly what Belgium (16 participants) plays, cleanly, every season. There is simply
no row in the table for a round of 16 held under id 0x2f.

Our cup has a 0x2f round because it has **twenty** participants, not sixteen. Live, the
regulation's participant list at +0x170 holds 20 handles, and they are the twenty of FL
League 01 exactly. The game fills a national cup from the league it is tied to and ignores
CompetitionEntry's sixteen. Twenty into a knockout needs a preliminary round to reach
sixteen; that preliminary takes 0x2e, pushing the real round of 16 onto 0x2f, which the
table cannot date.

So the switch case, the template, the bracket byte -- none of them are the lever. Cloning
from England instead of Belgium changed the leg count and the later-round dates but not this,
because both routes end at the same sixteen-club date table. **The lever is the participant
count.** A cup that receives sixteen clubs plays 0x2e/0x33/0x34/0x35 and every round has a
date already sitting in the shipped table, with nothing patched.

The open question is therefore not "how do we date round 0x2f" but "how do we give the cup
sixteen participants instead of twenty". The game took twenty because the cup is tied to a
twenty-club league. The three candidates, cheapest first: tie the cup to a sixteen-club
league (build one league at sixteen and point the cup at it); find the field that says "take
the top sixteen" that the shipped sixteen-club cups in twenty-club countries must use; or,
last, add a 0x2f row to the date table in the exe, which is the thing to avoid.

The season is being walked to day 260 to see whether the undated round of 16 stalls the cup
in play or is simply skipped. That reading decides how urgent this is: a cup that plays its
prelim and its later rounds and only drops the round of 16 is still a broken cup, but a cup
that wedges the calendar on an undated round is a different severity.

Addresses touched, for the record: date switch 0x14157f810 (keyed by regulation id, bounds
ids 1..175, so id 186 is out of its range -- the cup is dated by a route that does not go
through the id switch at all); cup helper 0x1415810d0 with its table 0x14298ea00; the two
scheduler callers 0x14135099c (literal key 0x6c) and 0x141350c80 (key from the phase record).

## Stage G: the cup works -- sixteen clubs, no exe patch. SOLVED.

`_FL26G39Cup3` is `_FL26G39Cup2` with one change: FL League 01 shrunk from twenty clubs to
sixteen. Nothing else -- same England-template cup, same regulation 186, the known-good set,
no cup key, no exe change. It generated on the second attempt and read:

    regulation 186: 15 records
      round 0x2e:  8 matches   2025-09-12   (round of 16, 8 ties)
      round 0x33:  4 matches   2025-10-17   (quarter-finals)
      round 0x34:  2 matches   2026-01-10   (semi-finals)
      round 0x35:  1 match     2026-02-14   (final)
    comp 186: 15 records, 15 placed, 0 unplaced
    competitions with unplaced matches: 0
    reg 186 participants = 16   (was 20 in Cup2)
    reg 11  participants = 16   (FL League 01, now a 16-club league, 240 fixtures not 380)

Every round dated, nothing unplaced. This is the sixteen-club bracket the shipped date table
was written for: 16 -> 8 -> 4 -> 2 -> 1 across rounds 0x2e/0x33/0x34/0x35, no preliminary,
no round of 16 under 0x2f. **The participant count was the whole of it.** Confirmed against
Stage F, where the identical cup with twenty participants left round 0x2f undated.

So the recipe for a cup that plays a full, correctly dated Master League knockout, with no
change to the executable and on the set already published:

1. The cup is filled from the **first league in its region** (lowest competition id), not
   from its own CompetitionEntry list and not from the whole region. In our worlds that is
   FL League 01 (cid 130). The sixteen clubs in the cup's own entry list are ignored.
2. That first league must have **sixteen clubs**, because the shipped cup date table only
   covers a sixteen-club bracket. Any other size that does not reduce to a clean power-of-two
   knockout across 0x2e/0x33/0x34/0x35 will leave a round undated -- twenty forces a round of
   16 onto 0x2f, which has no date row.
3. Build the cup `--like ENGLAND_D1_CUP --bracket 44` (or any real knockout template; the
   template sets the leg count and the later-round calendar, not whether it plays). Give it
   the same sixteen clubs for tidiness even though the game refills it.

The cost is that the cup's feeder league is a sixteen-club league rather than twenty. For a
39-league world that wants a cup, the choice is the user's: make one of the leagues a
sixteen, or add a dedicated sixteen-club league in its own region to feed the cup. Either is
data only.

What this closes: the date-stub cup branch (CASE38, the cup bit, `datecave.cup()`) was built
to force a calendar onto a cup and is not needed -- a cup above id 175 is dated by the
default sixteen-club path without it. The code is harmless and can stay, but the cup does not
depend on it. The open item that remains is only cosmetic and for later: whether a cup can be
given twenty participants at all (it would need a 0x2f date row added to the table in the
exe, which is the thing we avoid).

`_FL26G39Cup3` is left in place as the proof. The user's primary world `_FL26G39` (39 leagues
of 20) is unchanged on disk; switch back to it with `siderroot.py _FL26G39` when the cup
world is no longer wanted.

## Stage E: the region table read, and the two levels of the job

Read the region name table live at 0x1426770c0. It is 24 records of 16 bytes,
`{u64 name_ptr; u32 id; u32 pad}`, and record 24 onward is unrelated data -- the table is
exactly 24 long. Each record's name_ptr points to a localization KEY string, not a display
name: "compeCategory-england", "compeCategory-france", "compeCategory-itray" (the game's own
typo), and so on, which the language file resolves to the shown name.

The 24 ids present, with their key:

    1 interClub   2 england   3 france   4 spain   5 italy   6 portugal   7 netherlands
    8 belgium   9 russia   10 swissConfederation   12 denmark   15 scotland   16 brazil
    17 argentina   18 chile   19 colombia   21 china   22 PEU   23 PLA   24 PAS
    25 interNational   26 event   27 turkey   28 thailand

The mapping to the file was the missing piece: the `Competition.bin` region byte is the
region id times eight. England id 2 is byte 16; Scotland id 15 is byte 120; the shipped KSA
rows sit at byte 224, which is id 28 -- thailand's slot, so KSA competitions render under
"thailand". At runtime the region is the regulation field +0x30c bits 7-12, and there it is
the id directly (england reads 2), not the byte.

The parser at 0x1414f839a bounds the id: `and al, 0x1f; cmp al, 0x1d; jae skip` -- an id of
0x1d (29) or more is rejected and the default is kept. So the usable id space is 0..28, and
the ids with no name record are 0, 11, 13, 14, 20. Those five are free to us with no patch,
but they have no name entry and the table has no fallback, so a league placed on one renders
with a blank region name. Raising the 0x1d immediate to 0x20 would additionally free 29, 30,
31 -- the field physically holds five bits, so 31 is the wall.

This splits the work in two, and the split is the decision:

- **Free and additive, now.** Place new leagues in the 24 shipped country slots by setting
  the region byte to id*8. A league under France (byte 24), one under Spain (byte 32), and so
  on. No executable change at all. The limit is that the names are the 24 the game ships;
  there is no way to show "Croatia" this way. `mkworld.py` already takes `--regions`.
- **Real work, later.** A brand-new named region needs three things: a 25th record grown into
  the name table (which means finding and raising wherever the count 24 bounds the lookup --
  the table has one rip-relative reader around 0x140acd47b to run down), a localization key
  that resolves to the wanted name (the "compeCategory-*" strings live in the language file,
  not the exe), and the menu's flag table, which is still unlocated. None of this is needed
  to put three tiers in one existing country.

For the promotion/relegation goal the relevant half is the cheap one: three leagues placed in
the same shipped region are three tiers of one country, which is all the tier link needs. New
region NAMES are a separate, cosmetic want that can wait.

## Stage D revisited: the runtime tier link is real, and it is at +0x7c / +0x7e

Stage D was filed as a negative: two leagues were linked, a season ran, no club crossed, and
the working note guessed the runtime never reads the file's promotion link. Reading the live
regulation records of the shipped pyramids shows that guess was wrong.

The runtime regulation record (stride 0x314) carries the tier link as two u16 fields:

    +0x7c   the division ABOVE  -- the promotion target, set on a second division
    +0x7e   the division BELOW  -- the relegation target, set on a first division

Every shipped two-tier pyramid carries it, both ways:

    Premier League (17) +0x7e = 79 (EFL Championship);  Championship (79) +0x7c = 17
    LaLiga (19)         +0x7e = 80 (LaLiga 2);           LaLiga 2 (80)     +0x7c = 19
    Ligue 1 (20)        +0x7e = 81 (Ligue 2);            Ligue 2 (81)      +0x7c = 20
    Serie A (18)        +0x7e = 82 (Serie BKT);          Serie BKT (82)    +0x7c = 18
    Série A (29)        +0x7e = 163 (Série B);           Série B (163)     +0x7c = 29

Single-tier leagues (Bundesliga, Scottish Premiership) and same-tier splits (Colombia's
DIMAYOR I and II) carry neither field -- so this is specifically the promotion pyramid, not a
generic "related competition" pointer.

The file source is the CompetitionRegulation.bin record, and tierlink.py already writes the
right offsets. The shipped Premier record has +0x00 = 79 (relegates into) and +0x10 = the D1
calendar 0x0020a020; the Championship record has +0x04 = 17 (promotes into) and +0x10 =
0x00212020. tierlink.py writes exactly these. Our _FL26G39Tiers world's file holds reg 11
+0x00 = 49 and reg 49 +0x04 = 11 -- the same shape as the shipped pair.

So why did Stage D read empty? Because the runtime record that was read was the WRONG world.
The check ran against whatever world was loaded at the time (later the cup worlds), and none
of those were tierlinked -- reg 11 and 49 there carry no link because their files carry none.
The linked world was never loaded and read back. Two things Stage D never verified, and both
matter: whether the file link loads into +0x7c/+0x7e at runtime, and whether the two tiers
held DISTINCT clubs in the same region (the note said the membership looked identical, which
would make any crossing invisible).

The clean test is _FL26G39Tri: reg 11 (clubs 71578-71597), reg 49 (71598-71617), reg 60
(71618-71637), zero overlap, all in England (region byte 16), linked as a three-tier chain
D1=11 <-> D2=49 <-> D3=60 (the middle division carries both +0x00=60 and +0x04=11). The
runtime read of +0x7c/+0x7e after generation says whether the link loads; a full-season
rollover says whether clubs actually cross.

### Runtime confirmation on _FL26G39Tri (2026-09-18, ~20:22)

Season generated on the first attempt; all 39 leagues took a season on day 212. The runtime
read of the three tiers:

    reg 11 FL League 01  region 2  20 clubs  above=-            below=49 (FL League 02)
    reg 49 FL League 02  region 2  20 clubs  above=11 (Lg 01)   below=60 (FL League 03)
    reg 60 FL League 03  region 2  20 clubs  above=49 (Lg 02)   below=-
    overlaps 11&49 0   49&60 0   11&60 0

So the file link loads into the runtime record, the three-tier chain is live (the middle
division carries both directions), and the three tiers hold distinct clubs. Every doubt
Stage D left open is answered except the last one, which is behavioural: whether clubs
actually cross at the rollover. That needs a full season played to the next day-212, and the
walk is running (seasonplay --days 372, checkpointing to slot 2).

The club handle at +0x170 decodes as (club_ref << 12) | slot: the low twelve bits are the
club's position in the league, the high bits are the club's stable identity. tierwatch.py
records the set of club_refs per tier so the before/after diff names which clubs moved.

## The day-364 load crash: heap corruption, not a game-logic wall (2026-09-18)

Loading the _FL26G39Tri day-364 checkpoint (slot 2) crashes identically twice with c0000409
(STATUS_STACK_BUFFER_OVERRUN, the stack-cookie fastfail). The faulting rip is a system address
(vcruntime __report_gsfailure); the smashed FL_2026.exe function is at **0x1403abb40**.

That function is NOT game logic. It is the memory allocator's extent red-black tree
insert/rebalance (jemalloc; neighbouring frames carry prof.h/bitmap.h/tcache.h assert strings),
reached from a free()/extent-coalesce path (0x1403add10 -> 0x1403ae320 -> 0x1403abb40) while
the save was being deserialized. It keeps a 0x800-byte on-stack scratch array walked with a
0x10 stride and NO end-of-buffer check -- capacity 128 tree levels. Entry 129 overwrites the
cookie and the return address.

A valid red-black tree is never 128 deep. The descent overran because the extent tree was
already **corrupt** before this free() touched it. So the real bug is an out-of-bounds WRITE
earlier in the load that clobbered allocator metadata; the crash only surfaces at the next
free() that traverses the damaged tree. This is why it is not guardable at 0x3abb40 -- a bounds
check there just turns the crash into silent, deeper corruption. The fix belongs at the write
site.

Assessment: not generic (a clean save does not corrupt its own allocator) and not tied to the
sacked-manager state (0x3abb40 is allocator code with nothing about manager offers). It is
data-driven. Two live hypotheses, not yet separated:
  1. An enlarged/relocated table from the mlcopy set (teams/coaches/regs/rec596 0x254/fixtures)
     is written with a count from the NEW capacity while its backing allocation was left at the
     ORIGINAL size -- an OOB write past the allocation into adjacent heap metadata. This would
     be exposed by a deep mid-season save (day 364) carrying more accumulated records than the
     shallow saves that save/load was first proven on.
  2. The novel three-tier chain itself (reg 49 is BOTH a promotion target and a relegation
     target -- a shape no shipped competition has; every shipped pyramid is two tiers). The
     loader may size a structure for two-tier links and overrun on a division linked both ways.

The exact table/count is not recoverable from these two dumps (the offending write is upstream,
off this stack). To separate the hypotheses cheaply: generate a FRESH _FL26G39Tri season, save
immediately (a shallow day-212 save), and load it. If the fresh three-tier save loads, the
crash is the deep-save table-allocation mismatch (hypothesis 1, and it threatens the base
world's deep saves too). If the fresh three-tier save also crashes, the three-tier chain is the
cause (hypothesis 2, a promotion/relegation design constraint). To find the write site itself:
load under allocator junk/redzone fill and catch the first overrun.

## Blueprint: adding a UEFA Conference League (native multi-phase clone) (2026-09-18)

FL26 ships the new single-table continental format natively; the Conference League is the
only major UEFA competition missing. It can be added additively by cloning the Champions
League's regulation shape. Parsed from the base pesdb (Competition/CompetitionRegulation/
CompetitionKind/CompetitionEntry .bin); no game process touched.

Champions League = competition id 2, THREE phases, each a separate regulation row sharing the
cid, ordered by ascending master rid + R_TYPE(+0x09) + per-phase calendar(+0x10):
  - master rid 2, R_TYPE 1 PLAYOFF,   16 teams, cal 0x0c802408
  - master rid 3, R_TYPE 2 GROUPSTAGE, 32 teams, cal 0x00842208
  - master rid 4, R_TYPE 3 KNOCKOUT,  16 teams, cal 0x2c880200
  Group stage has 8 per-group REPLICA rows: replica_rid = master + (grp+1)*1024, grp byte
  +0x0a = 0..7, and +0x06 points back to the master rid. Knockout has no replicas. 32 entries.
Europa League = cid 3, only TWO phases (no playoff): master rid 5 GROUPSTAGE 48 teams
  cal 0x0080220c (12 group replicas), master rid 6 KNOCKOUT 32 cal 0x2c840200.
Competition row (stride 36): region byte +3 = 8 (the UEFA/European continental MENU slot --
CL/EL/Super Cup all sit there, so a comp placed at region 8 shows alongside them), flag +6 =
0x22, code +8 = e.g. UEFA_CHAMPIONS_LEAGUE. No display-name field in the 36-byte row; the name
comes from the regulation inline name (reg+0x14) when reg+0x00 nameid = 0.
R_TYPE indexes the global CompetitionKind enum (0 PLAYOFF,1 GROUPSTAGE,2 KNOCKOUT,3 LEAGUE,...);
a clone copies rows verbatim and does NOT touch CompetitionKind.

Recipe (additive): pick a free cid (6 is free; the current world uses cids 130-168), three free
GOOD master rids for the phases (NB: 11/49/60 are taken by the _FL26G39Tri league tiers -- pick
others), clone comp 2's competition row + all 19 regulation rows (3 masters + 8 group replicas +
name/cid/+0x06 remap), and add 32 CompetitionEntry rows. mkleague.add_league copies only ONE
regulation row so it cannot do a multi-phase comp -- needs a small new tool modelled on mkcup.py
that iterates every reg row with cid==2 and applies the remap.

UNVERIFIED, needs a live probe before any build is trusted (biggest risk first):
  1. Whether the exe runs continental phase logic for a brand-NEW cid (6) it has no hardcoded
     handler for. It generically runs league (type-4) regulations, but type 1/2/3 continental
     behaviour on an unknown cid is untested -- the exe may only drive cid 2/3/5/8. This is the
     single decisive unknown; test it minimally before cloning the whole structure.
  2. Whether replica rids (>1024, above the REG_MAX=600 GOOD/BAD range) must be GOOD.
  3. Calendar collision: cloning CL's calendars lands fixtures on the same days as CL; the 280/
     day cap silently drops overflow (calcomp.py). The new comp may need distinct calendars.

### Discriminating test result (2026-09-18 22:09): the crash is the deep save, NOT the 3-tier chain

Generated a FRESH season on _FL26G39Tri (all three tiers wired live, clubs distinct, 0 overlap),
saved it immediately as a shallow day-212 save (slot 1, ML00000000, 45.4 MB), stopped the game,
and loaded it back. The load SUCCEEDED: FL_2026.exe came up, no new crash dump (count stayed 5),
and triread read the live tier link from the running game -- reg 11<->49<->60 intact, three tiers,
0 club overlap. So the novel three-tier chain is save/load-safe; hypothesis 2 is ruled out.

The day-364 crash is therefore the deep-save path (hypothesis 1): a data-size OOB write exposed
only once a save carries enough accumulated records (a full season of matches/transfers/career
events) to push some enlarged mlcopy table past its original allocation. Consequences: (a) the
three-tier promotion/relegation design is sound and shippable; (b) but deep saves of ANY world
built on this set -- including the base 39-league mod -- are at risk on load, and crash-recovery
on a long unattended walk (which reloads a deep checkpoint after a crash) can hit it. The fix
is still the upstream enlarged-table allocation-vs-count audit noted above; it is now a
release blocker for long-save reliability, not just a lost run.

### CORRECTION (2026-09-18, later): the [owner+0x60] table is NOT the proven culprit

Deeper static tracing walked back the [owner+0x60]/+0x88 hypothesis:
- Every WRITER of region2 is hard-capped at 0x7548 (30024): the append 0x1414bd5c0 refuses to
  insert once count >= 30023; the load-reset 0x1414bd4a0 inits exactly 30024 slots then zeroes
  the count. 0x7548 is a fixed cache capacity, NOT the player count (0x7531=30001, raised
  elsewhere). So region2 cannot overflow from its own count on any normal path, and a same-layout
  save cannot deliver a bad count. Enlarging this table would fix nothing.
- The ONLY way it could bite: the compaction/save walker 0x1414bce50 iterates by the stored count
  field [+0x260552] and trusts it; a count >30024 arriving by some other route would over-iterate
  past +0x260550. Not reachable from a same-set save.
- KEY: the crash stack frame is NOT the ML deserializer. 0x1415a4b60 / 0x1415a50c0 / 0x1415a5300
  are the CRI/CRIWARE CPK binder (strings "This isn't Cpk Binder.", "BinderIdList overflow.",
  "box(5) is not enough" = a CRI FS container box). The free() that trips the corrupt extent tree
  is ASSET/CPK loading -- an innocent victim traversing a heap already corrupted upstream.

Net: the true OOB write site is still unpinned and is NOT rec596, NOT fixtures, NOT [owner+0x60].
Static analysis cannot pin it (the write is upstream, off every captured stack). The reliable way
is dynamic: load the day-364 save under Windows PageHeap (gflags /p /enable FL_2026.exe /full) or
jemalloc redzone/junk fill and catch the FIRST overrun write, which names the undersized
allocation directly. A cheap in-process count-clamp guard on [owner+0x60] would almost certainly
come back negative (the count can't be bad from a same-set save), so it is not worth running.

### BREAKTHROUGH (2026-09-18 23:07): redzone makes the day-364 save load; run recovered

Booted FL_2026 with MALLOC_CONF=redzone:true,abort:true (verified present in the live process
env) via a local launch wrapper -- no persistent system change. Loaded slot 2 (the day-364
save that reproducibly crashed with c0000409). It LOADED: seasonload rc=0, "season running at
day 364", same pid never died, triread reads the live three-tier chain at day 364. The
per-allocation redzone padding ABSORBED the out-of-bounds write that previously overran into
adjacent extent-tree metadata, so the fatal corruption never happened.

Implications:
- The bug is a BOUNDED OOB write (small enough to fit a redzone gap) -- confirms the OOB-write
  class, not a wild pointer.
- redzone MASKS it; it does not FIX it (perf overhead + env-var dependency, not shippable). It
  also did NOT name the culprit: no redzone-violation abort fired (the write stayed within the
  padding and that block was not freed), so the exact table is still unpinned. The culprit can
  now be hunted from the LOADED overflow state in memory (compare each table's in-use count to
  its original capacity).
- The day-364 run is RECOVERED and is the FASTEST route to a live promotion/relegation crossing:
  from day 364 the next rollover at day 212 is ~213 days away (vs ~365 from a fresh day-212
  season). A redzone-stable crash-safe walk can now reach it.
- A separate non-fatal CRI/CPK "box(5)" fastfail (dump 19152, thread, rcx=5) occurred during
  load but the game continued -- unrelated asset-loader complaint.

### The play-time crash: redzone masks the load, not the simulation (2026-09-19 00:02)

The redzone-recovered day-364 walk crossed New Year and the winter break cleanly and
checkpointed at day 127 (slot 2, 45.9 MB). The next chunk crashed ~11 minutes in, at some
day above 127, with a DIFFERENT signature from the load crash:

- code c0000005 (access violation), a **write** to the address held outright in `rcx =
  0x00000001ecf6ed41` -- a pointer, not an index. rip = 0x1484ed4c0 (in the `.impdata`
  code region the attribution tables don't cover; use impscan.py).
- The whole register file is high-entropy garbage: rax=0xc8072890, rbx=0xdbfedbdf,
  rdx=0x9c67b725, r12=0xba238df7, r13=0xdba6d565, r14=0xb3eb6750, r15=0xf49f7b2c. Not
  jemalloc junk fill (0xa5.. / 0x5a..); this is a live pointer field overwritten with
  data, then dereferenced.
- The caller chain is entirely in the 0x1403xxxx allocator region -- the **same jemalloc
  family** as the day-364 load crash (0x1403abb40 / 0x1403add10 / 0x1403ae320). The
  allocator wrote through a free-list / extent pointer that had been clobbered.

Reading: this is the SAME upstream bounded OOB write, wearing a second face. redzone pads
each allocation, so the load-time overflow into extent-tree metadata is absorbed and the
save LOADS. But during simulation the allocation pattern differs; the same OOB write now
lands on a live pointer inside a neighbouring block, and a later allocator operation
dereferences the clobbered pointer -> c0000005. `abort:true` did not fire because the
write did not cross a redzone boundary that jemalloc later checked -- it corrupted a
pointer that was used before any redzone verification.

Consequences:
- redzone is NOT a crash-safe play environment, only a crash-safe LOAD environment.
- The checkpoint ratchet still gets us to the crossing: shorten the chunk below the crash
  interval (12 min vs a ~11 min crash) so a checkpoint lands before each crash; on crash,
  recovery reloads the last checkpoint (redzone via FL26_DBGWRAP) and continues. The walk
  advances in ratchets across nondeterministic crashes.
- If instead the walk sticks re-crashing at a FIXED day, the crash is deterministic (a
  specific day's computation) and needs its own guard, not a shorter chunk.
- Next hunt lead for the shippable fix: enable jemalloc junk fill (junk:true) so a
  use-after-free pointer becomes 0x5a5a5a5a5a5a5a5a and the faulting deref names the class
  directly; run from the loaded overflow state and diff each relocated table's in-use
  count against its original capacity.

### Promotion/relegation: the mechanism works for shipped pyramids, NOT for ours -- and why (2026-09-19)

Decisive measurement. Walked the day-364 season across the day-212 rollover to day 281,
then compared club membership (club_ref = handle>>12) of a shipped pyramid and our
synthetic chain, before (day-364 recovered save) vs after (day-281):

- **Premier (reg 17) <-> Championship (reg 79): promotion/relegation WORKS.** 3 clubs left
  Premier (416, 420, 1508) and joined Championship; 3 left Championship (1532, 7040, 16732)
  and joined Premier. Exact mirror 3-up/3-down, and it SURVIVED the new-season
  regeneration (still applied at day 281). LaLiga/LaLiga2 (19/80) same shape.
- **Our FL League 01/02/03 (reg 11/49/60): zero movement.** No club changed tier.

So the engine does simulate promotion/relegation, and regeneration preserves it -- the
negative is specific to our chain.

Root-cause narrowing: the runtime regulation window +0x70..+0x90 is STRUCTURALLY IDENTICAL
between ours and the shipped pyramids -- tier links +0x7c (above) / +0x7e (below) set
correctly (11<->49<->60), +0x84=01 like the promoting leagues (single-tier Bundesliga
reg 16 has +0x84=03 and both tier links ffff). So the tier link is NECESSARY BUT NOT
SUFFICIENT; the count is not the missing piece either.

External confirmation (evoweb thread the user found, login-gated; plus web search): this is
a solved PES2021 modding problem. The machinery is a "cup module" that LINKS divisions,
packaged as Gerlamp's "Competition Server" (adds lower divisions with working, ADDITIVE
promotion/relegation without touching existing leagues) and SMcCutcheon & Zlac's "MLPR --
Master League Promotion/Relegation Tool" (forces ML promotion/relegation for added lower
leagues). A known config detail: a "1st Division" flag in the competition regulation (modders
clear it on added 2nd/3rd/4th divisions so their top teams don't qualify for continental
cups by league position). Next: obtain the thread's exact recipe / study Competition Server
+ MLPR to replicate the linking module our chain lacks. This is directly aligned with the
additive-installer goal (importing existing PES modder leagues).

### Reverse-engineered the CDF division-linking cup module (2026-09-19)

Fully reverse-engineered the community CDF_Sofrench module (static only; the untrusted
DLL was never loaded). It hooks one FL_2026.exe function to rebuild a cup's participant
list from four divisions, additively and with no exe modification. Two reusable game
primitives fell out: **0x141522b50** = the participant-list builder (feed it a team-handle
vector -> it populates any competition's participants, deduping on the 14-bit slot), and
**0x143705e10** = the competition registry (walked to map a competition id -> handle +
club count). Full write-up, including the install/signature/trampoline flow and how to
reuse it for our own additive module and for the promotion/relegation hook, in
`cdf-hook-reverse.md`.

### What a save file is, statically (2026-09-21)

Relevant because the deep-save load crash cannot be traced from the exe alone, and a reader
for the file would let a promotion be verified from a save instead of from a running game.

The save is Blowfish-encrypted and zlib-compressed. The Blowfish P-array constant
(`0x243f6a88`) sits at `.rdata:142c37220` with a runtime copy at `.data:14352bf20`, and the
only code reference is `0x14227d1c2`, inside the key schedule at `0x14227d1b0`. Its one caller
`0x142262010` is a thin wrapper: it asks the object for a key length (`0x14038c420`) and a key
pointer (`0x141007cd0`) and passes both in, so the key is a field of whatever object is doing
the encrypting, not a constant this function can be read for. zlib is present and named
(`.rdata:1429d80e1` and the version strings). No AES table is present; the inverse-S-box hit at
`142c28a70` is a coincidence of four bytes, with no code reference.

Practical reading: writing a save decoder means finding the object that owns the key, not
breaking anything -- but it is a day of work for a convenience, and the running game already
answers the same questions through `livedump`. Recorded so nobody re-derives the entry points.

### The multi-phase clone exists now (2026-09-21)

`tools/mkphases.py` does what the Conference League blueprint above said was missing: it copies
every regulation row of a multi-phase competition, not one, and renumbers the three things that
have to agree -- the master ids, the replica ids (`master + (group + 1) * 1024`), and each
replica's back-pointer at `+0x06`. It works out every new id before writing anything, because a
half-renumbered clone is worse than none.

Two corrections to the blueprint, from reading the rows rather than the summary:

* The play-off phase has replicas too, not only the group stage. The Champions League carries
  eight for the play-off (1026, 2050 ... 8194) and eight for the group stage (1027 ... 8195).
* The entry counts are 33 for the Champions League and 34 for the Europa League, not 32 and 48.
  48 is the group-stage club count in the regulation row, which is a different number.

Verified by cloning the Europa League into a scratch world and reading it back: competition 174,
masters 186 (group stage, 48) and 187 (knockout, 32), twelve replicas 1210 ... 12474, each
pointing at its master, 34 entries.

The one thing it deliberately does not do is invent a calendar; the clone keeps the source's
dates and will collide with it. That is the same problem `fl26swiss` solves for the league
phase by writing its own sixteen matchdays.

### The download folder has a manifest, and it says which archive wins (2026-09-21)

Everything this project ships goes in through sider, as loose files in a livecpk root. An
installer that imports somebody else's league mod will meet the other mechanism -- a `.cpk`
dropped in the game's `download` folder -- and then the question is which of two copies of
`Competition.bin` the game reads. `download/spFileList.bin` is where that is written down, and
`tools/spfilelist.py` reads it.

3,753 bytes: one `u32` of 0x64, then 78 records of 0x30 bytes, of which 21 are used and the
rest are zero. A record is `{u32 index, u32 group, u32 tag, char[0x24] name}`. The index counts
down -- 21 for the first archive, 1 for the last -- so the first entry's index is also how many
there are. The group is 100 for the four data patches and 200..700 for the add-ons; the tag is
10100, 10200 or 10300, three patch generations.

Which end wins, measured rather than assumed: the data patches ship `CompetitionEntry.bin` with
1,261 rows in `data_s2526`, 1,264 in `data_s2526b` and 1,317 in `data_s2526c`, and the world
this project builds on carries the 1,317 version -- while `data_s2526c` holds the *lowest*
index of the four. A smaller index is a higher priority, which also puts the seventeen add-ons
above all four data patches.

One honest gap: the name `spFileList` appears in no binary in the installation -- not
`FL_2026.exe` (including `.impdata`), not the launcher, not the switcher, not `PES21_Hook.dll`,
which knows only PES's own `DpFileList.bin`. The executable knows the two folders as strings
(`.\download\` and `./Data/`) and both sit in what looks like an embedded Lua constant pool,
with no `lea` anywhere pointing at them. So either the name is assembled at runtime or this
manifest belongs to the repack's installer rather than to the game. Anyone who adds an archive
should check it is read before relying on the order above.

## What a mod takes over, before installing it: modscan.py (2026-09-21)

The importer's first question is not how to merge somebody else's league but what that league
would cost. Mods in circulation are written to replace: they ship a whole `Competition.bin`
with their league sitting on an id the game already uses, and installing one means the shipped
competition is gone without a word. `tools/modscan.py` answers the question without installing
anything -- point it at a livecpk root or a `.cpk` and it reads the six tables that carry ids.

The base it compares against is composed the way the `download` folder composes it: for each
table, the copy from the listed archive with the highest priority that carries it. Measured
while writing the tool, the composition is simpler than the manifest suggests -- only the four
`data_s2526` patches carry pesdb tables at all. The seven multi-gigabyte add-ons, which sit at
higher priority, hold faces and menu files and not one table between them:

    data_s2526    Competition 91, Regulation 214, Team 743, Player 27927, Entry 1261
    data_s2526a                                   Team 743, Player 27985, Entry 1263
    data_s2526b                   Regulation 214, Team 743, Player 28040, Entry 1264
    data_s2526c                   Regulation 214, Team 743, Player 28071, Entry 1317

So the shipped world is 91 competitions, 214 regulations, 743 clubs, 27,927 players.

Comparing ids alone is not enough, and getting that wrong would have made the tool useless:
every world this project builds ships the complete table with its own rows appended, so an
id-only check would report our own additive worlds as taking over all 91 shipped competitions.
Each shared id is therefore compared byte for byte, and a row counts as taken over only when
the bytes differ. There is a second way to take a league over that no id check sees at all --
leave every row alone and enter different clubs into it -- so the entry table is compared as
line-ups per competition as well.

Run against `_FL26G39Tri`, the world all the season work runs on:

    Competition.bin       130 ids: 39 new, 0 changed, 91 identical, 0 dropped
    CompetitionRegulation 253 ids: 39 new, 0 changed, 214 identical, 0 dropped
    Team.bin             1523 ids: 780 new, 0 changed, 743 identical, 0 dropped
    Player.bin          51327 ids: 23400 new, 0 changed, 27927 identical, 0 dropped
    PlayerAssignment    44703 ids: 23400 new, 0 changed, 21303 identical, 0 dropped
    CompetitionEntry     2097 rows, and no shipped competition's line-up changes

That is the first independent confirmation that "everything additive" is true of what we
actually ship, rather than a rule we have been following carefully. It is also the acceptance
test the importer will have to pass: remap a foreign mod's ids, run modscan on the result, and
the verdict has to come back additive.

The hostile path was checked too, on a copy of the shipped tables in a scratch folder with one
competition's code overwritten and two clubs deleted. The tool names what is lost rather than
counting it -- "competition 20 was PORTUGAL_D1_CUP and becomes MODDER_LEAGUE" -- because the
number alone does not tell somebody which of their leagues is about to disappear.

Player.bin is 312 bytes with the player id at +0x08, not the 188 bytes assumed at first; the
giveaway is that the unpacked table does not divide by 188.

## Turning a replace into an add: modremap.py (2026-09-21)

The other half of the importer. Given a mod modscan.py has just called hostile, this gives every
colliding row a free id, follows every reference to it, and writes out base + mod instead of mod
over base.

The references are the work. A competition id is written in four places, a regulation id in
four more, and one of them cannot be chosen freely at all: a replica -- one group of a phase --
must keep the id master + (group + 1) * 1024, so moving a master drags sixteen other rows with
it. The promotion and relegation links at regulation +0x04 and +0x00 point at other divisions
of the same pack and have to be followed too, or an imported pyramid promotes its champion into
whatever shipped division happens to own the old number.

Ids are handed out from 130 for competitions and 186 for regulations, which is where this
project's own tools start looking, because the numbers below include ones the exe treats
specially (mkworld.BAD_REG).

Three test packs were built in the scratchpad from the shipped tables and put through it:

  * a league pack sitting on competition 20 with eighteen clubs written over shipped club rows.
    After the remap: competition 130, eighteen new club ids, shipped competition 20 back to its
    own line-up, and modscan's verdict additive.
  * the same with two clubs deleted, to check that a table rebuilt wholesale is reported as
    dropping shipped rows rather than silently shrinking the world.
  * a pack replacing the Champions League with a nineteen-row multi-phase competition. The
    three masters landed on 186, 187, 188 and all sixteen replicas followed exactly --
    1210, 2234 ... 8378 for the play-off, 1211 ... 8379 for the groups -- with the back-pointers
    rewritten and the shipped Champions League untouched.

Two fields were nearly missed, and both were caught by reading the shipped data rather than the
code: `Competition +0x04` is a parent competition -- the five World Cup qualifying competitions
all carry 27, the World Cup -- so a pack with its own qualifiers needs that link followed too.
And the 48-slot club list a regulation has at runtime is *not* in the file record: the twenty
offsets in a league's regulation that happen to hold a valid club id are all inside the name
slots. Entries are the only place a competition names its clubs.

Two things the loop taught that were not obvious before writing it:

  * a pack that keeps a competition's line-up ships entry rows identical to the shipped ones,
    so nothing counts as the mod's and the import arrives with no clubs in it. Those clubs
    belong to the competition that stays, so they are copied and not moved: both competitions
    then name the same clubs, which is what a parallel cup wants anyway.
  * a club can be renumbered perfectly and still be unplayable, because the squad lives in
    PlayerAssignment.bin. The tool counts squad rows per imported club and names the ones that
    cannot field eleven.

Pictures move too, once the asset keys were read out of the shipped archives (next section).
`--assets` copies the mod's files into the output with the crest, kit, portrait and face
numbers rewritten onto the new ids; a file that carries a moved id in a shape the tool has no
rule for is named out loud rather than copied silently under the old number. Checked on a pack
carrying 54 such files: crests `e_000001_r.png` became `e_071578_r.png`, the kit folder and the
kit file inside it both followed, and a portrait belonging to a player the pack did not move
was left exactly as it was. The full old->new mapping is written to remap.json beside the
tables.

## Where the pictures are keyed from, and a competition emblem for our leagues (2026-09-21)

Read out of the shipped archives while building the importer, because a mod that is renumbered
correctly still looks wrong if its pictures stay behind. Every one of these is keyed by an id
we control, which means every one is additive from a livecpk root:

    club crest         common/render/symbol/flag/e_<team id, 6 digits>_r[_l|_ll].png
                       740 files in dt15_x64.cpk for 743 clubs (mkcrests.py already uses this)
    competition emblem common/render/symbol/emblemLc/emb_<competition id, 4 digits><variant>.png
                       312 files, 91 distinct numbers, and they are the competition ids:
                       emb_0002 is the Champions League, which is competition 2
    player portrait    common/render/symbol/player/<player id>.dds -- 27,697 in dt14_all.cpk,
                       against 27,927 shipped players
    face model         Asset/model/character/face/real/<player id>/...
    kit                common/character0/model/character/uniform/team/<team id>/<team id>_*.bin
    manager portrait   common/render/symbol/coach/coach_<coach id>.png, and coachML/<id>.png

One thing that looked like a finding and was not: `common/render/symbol/flag/flag_<n>.png` has
exactly 214 files and the shipped regulation table has exactly 214 rows. It is a coincidence.
flag_001 is Afghanistan and flag_020 is Macau -- these are national flags, keyed by nation id,
and nothing to do with competitions.

The emblem variants: 43 competitions ship only the black and white silhouettes (`_b_l`,
`_b_ll`, `_w_l`, `_w_ll`), 40 ship only the full-colour `_l` and `_ll`, a few ship both plus
`_s1` / `_s2` alternates. `_l` is 256 pixels square and `_ll` is 512. Either set on its own is
enough for a shipped competition, so which one a given menu reaches for is still unmeasured;
`mkemblems.py` writes both.

That tool now gives each of our 39 leagues a placeholder shield -- the league's initials, its
tier number, a colour derived from the competition id -- and 234 files are deployed in
`_FL26G39Tri`. Self-drawn, no game art copied. Which competitions are ours is decided by
comparing with the shipped table and not by a number: shipped competition ids run up to 145
with gaps, and 130 to 145 are Scotland and Saudi Arabia, so "everything from 130" would have
redrawn six shipped badges.

Also checked while there: `Data/dt10_x64.cpk` carries a `common/etc/pesdb` folder, but only
auxiliary tables (stadiums, balls, boots, weekly data). None of the six tables the importer
cares about is in it, so the four download patches really are the whole base for those.

## The rest of the shipped tables, and the two the importer had missed (2026-09-21)

Listing every `common/etc/pesdb` file across all forty-odd archives turns up more than the six
the importer started with. The ones that matter, decoded far enough to say what they are keyed
by (record size found by factoring the unpacked length, the key column by testing which offset
holds values that are all valid ids):

    Coach.bin          100 bytes, manager id at +0x00, 961 managers -- and the club that
                       employs him names him at Team.bin +0x54 (741 of 743 clubs do)
    Tactics.bin        24 bytes, the club at +0x04, 772 rows. Not keyed by an id of its own
    TacticsFormation   792 bytes x 773 rows, keyed at +0x00 by the same number Tactics.bin
                       carries at +0x00 -- one formation per tactics row. Row 0 is a header
                       (key 782); row 1's key is Tactics row 0's key
    SpecialPlayerAssignment  16 bytes x 254, the player at +0x00, a row number at +0x08
    Derby.bin          12 bytes x 254, {club A +0x00, club B +0x04, number and flags +0x08}.
                       The first rows read Manchester United v Manchester City, Everton v
                       Liverpool, Chelsea v Fulham. The derby's number is the low nine bits
                       of +0x08 and is unique across all 254 rows; the bits above it are
                       flags (0, 2, 4, 6 seen)

Two readings that looked right and were not, recorded so nobody spends the hour again. The
"club id every 264 bytes at +0x0f" in TacticsFormation is the constant 256 in all 2,319 blocks,
not a club. And SpecialPlayerAssignment's +0x0c is not a club: the values there are 1 to 6,
which are valid club ids only by accident -- the club never appears in that table at all, the
player does.

All five are now carried by the importer, and `UNHANDLED` is down to the two weekly tables:

    Coach.bin          a pack's own managers get free ids; the clubs that employ them are
                       repointed at Team +0x54
    Tactics.bin        rows follow their club's new number, and where the row's own key at
                       +0x00 collides with a shipped one it is given a free key
    TacticsFormation   moves with that key. If the pack shipped no formation of its own, the
                       row the old key pointed at is cloned under the new one -- otherwise a
                       moved tactics row would line up nobody
    Derby.bin          both clubs repointed, and the derby gets the next free number. Nine
                       bits is the whole field, so a pack that would push past 511 derbies is
                       stopped there rather than quietly overwriting one
    SpecialPlayerAssignment  the player repointed, a fresh row number

Two of those tables ship unpacked -- `Derby.bin` and `SpecialPlayerAssignment.bin` have no
WESYS header, they are plain arrays of records -- so the reader falls back to raw bytes and the
writer writes them back the same way.

A rule that came out of testing this: a row the pack adds for a club or a player it did NOT
move is left out. A second tactics row for a shipped club, or a second special-player row for a
shipped player, is a takeover wearing an extra row as a disguise -- two rows answering the same
question, and nothing in the id comparison would have caught it. `modscan.py` now also counts
how many more times a mod repeats a key than the shipped table does, because some of these
tables repeat by design: the shipped Tactics.bin has 772 rows for 730 clubs.

The round trip was checked on a pack built for it: a Champions League replacement carrying
colliding tactics keys, a derby between two shipped clubs, and three special players. Scan says
NOT additive, remap moves 1 competition and 19 regulations and leaves out the two shadowing
rows, and the second scan says additive with no repeated keys left.

A club with no tactics row is not broken. The 780 clubs this project adds have no row in that
table at all and they play, so an unlisted side gets whatever the engine gives it. A club with
no squad is a different matter, and that is the one the tool counts.

The four archives also carry `Country.bin`, `CompetitionKind.bin`, `PlayerWeekno.bin` and
`TeamWeekno.bin`, and `dt10_x64.cpk` holds the stadium, ball, boot and glove tables. None of
them is touched by a league pack in the usual case.

## The two kind tables, and what the regulation's type byte is actually naming (2026-09-21)

Two small tables turn out to be the names behind numbers this project has been writing blind.

`CompetitionKind.bin`, 88 bytes x 9 rows, id at +0x00, the Japanese name from +0x04 and an
ASCII code at +0x41:

    1  PLAYOFF           2  GROUPSTAGE        3  KNOCKOUT
    4  LEAGUE            5  LEAGUE_2SEASONS   6  QUALIFICATION_1
    7  QUALIFICATION_2   8  PRACTICE          9  SPLIT_TOTAL

That is exactly the range of the regulation's type byte at +0x09, and counting the shipped
regulations by it gives 93 group stages, 56 knockouts, 42 leagues, 14 play-offs, 4 practice, 3
split totals and 2 two-season leagues. So the byte this project has been setting by copying a
prototype has a published vocabulary of nine values, and two of them -- QUALIFICATION_1 and
QUALIFICATION_2 -- are not used by a single shipped competition. The engine knows a qualifying
round even though nothing ships one, which is worth remembering for the Champions League work.

Byte +0x01 of each kind row carries a number that differs per kind (10, 11, 16, 24, 43, 10, 10,
32, 48). It looks like a per-kind size, and it is worth saying clearly that it is not a club
limit, because someone will read 24 next to LEAGUE and believe it. Measured against the shipped
regulations, every kind has a competition bigger than its number: group stages go to 48 against
11, knockouts to 44 against 16, leagues to 30 against 24. So nothing here caps the 36-club
Champions League this project is building, and the byte stays unidentified.

`SpecialPlayerAssignmentKind.bin`, 136 bytes x 9, id at +0x00, ASCII at +0x04, Japanese at
+0x24:

    1  ML_NEWFACE_EURO       2  ML_NEWFACE_SAMERICA   3  ML_NEWFACE_ASIA
    4  ML_NEWFACE_J_LEAGUE   5  EXTRA                 6  MONTAGE_PRESET
    7  JAPAN_RESERVE         8  ML_COACH              9  ML_COACH_LEGEND

This settles what `SpecialPlayerAssignment.bin` +0x0c is: the kind, and the values 1 to 6 seen
there are Master League newgen pools, not club ids. The table is the pool of generated faces
Master League draws new players from -- nothing a league pack needs, but a pack that ships one
is now carried rather than dropped.

`PlayerWeekno.bin` and `TeamWeekno.bin` are eight bytes each, two 32-bit numbers (91 and 1; 1
and 5). Whatever they are, they carry no ids, so they are off the importer's list of worries.

## One entry list per competition, and it does not have to match (2026-09-21)

Two things about `CompetitionEntry.bin` that the project had been careful about without needing
to be.

**The entry list belongs to the competition, not to the phase.** The Champions League has three
phases -- a play-off of 16, a group stage of 32, a knockout of 16 -- and one list of 33 entry
rows, slots numbered from 1. There is no per-phase list and no phase column in the row. So a
multi-phase competition is entered once, which is what the new Champions League format needs to
know: thirty-six clubs, one list.

**The declared club count and the number of clubs actually entered disagree in 26 of the 91
shipped competitions, in both directions.** Some carry fewer clubs than they declare -- the
Bundesliga declares 20 and enters 18, Copa Libertadores declares a 32-club group stage and
enters 17 -- and some carry many more: the Copa del Rey's regulation says 20 and 42 clubs are
entered, the Coppa Italia 20 against 40. Two competitions even repeat a slot number (the
Champions League once, the Copa do Brasil three times).

That is worth knowing twice over. It says the engine does not require the two numbers to agree,
so a league built with an entry list that does not match its declared size is not automatically
broken -- and it says an importer has no business "correcting" either number when it moves a
pack across, because the shipped data itself would fail that test 26 times.

## What the shipped game actually links together, top to bottom (2026-09-21)

Counted rather than assumed: of 214 shipped regulations, exactly 11 carry a promotion or a
relegation link, and every one of them is a master league regulation (group 255, kind LEAGUE).

    down          up
    17 -> 79      79 -> 17     England: Premier League / EFL Championship
    19 -> 80      80 -> 19     Spain:   LaLiga / LaLiga 2
    20 -> 81      81 -> 20     France:  Ligue 1 / Ligue 2
    18 -> 82      82 -> 18     Italy:   Serie A / Serie B
    29 -> 163    163 -> 29     Brazil:  Serie A / Serie B
    52 -> 145     --           Japan:   J1 League relegates into nothing

Two things fall out of that list and both matter to the promotion work.

There is no three-tier chain anywhere in the shipped data. Every second division carries an up
link and no down link, so the deepest structure the game ships is a pair. A third tier is not a
case the shipped data exercises, which is why it had to be built rather than copied, and why
the League Info panel showing only a pair is not evidence of a bug.

And the J1 League relegates into regulation 145, which does not exist -- there is no such row
in any of the four archives, packed or otherwise. The shipped game carries a dangling
relegation link and plays the J-League perfectly well. So a link pointing at nothing is
survivable, which also says what a link on its own is worth: not much. The chain this project
needs is done by the hook, and the link fields are the declaration, not the machinery.

## A phase declares how many groups it has, and the field was measurable (2026-09-21)

Until now the number of groups in a phase was only implicit: count the replica rows pointing
back at the master. There is a declared field as well, and having it wrong is the kind of
mismatch that shows up as a competition the season builder walks off the end of.

Found by asking the data rather than the code. For every one of the 108 master regulations the
replica count is known -- it is just how many rows point back at it -- so every bit field in
the packed block from +0x0b was tested against that number. Exactly one matches, in all 108
rows with no exception:

    CompetitionRegulation +0x10, the low five bits = the number of groups in this phase

Champions League group stage: 8. Europa League: 12. EURO: 6. Every knockout, league and
practice regulation: 0. Five bits, so up to 31 groups can be declared, which is more than the
replica rule can address anyway.

The high nibble of the same byte is something else and varies between leagues that have the
same shape, so it is not part of this. `mkphases.py` printed +0x10..+0x14 as "calendar", which
was a guess; it now names the group count it can actually read.

What this changes in practice: a phase cloned from a prototype with a different number of
groups carries the prototype's number. Checked across all 77 livecpk worlds this project has
built -- 11,000 or so master regulations -- and not one disagrees with its replicas, because
every one of them was cloned whole. The rule matters the first time somebody builds a phase
with a group count the prototype did not have, which is exactly what the new Champions League
format is.

## Country.bin: nations are positional, and that is a trap (2026-09-21)

214 rows of 1,420 bytes, and a row's position is the nation id: row 0 is Afghanistan, row 19 is
Macao, row 213 is South Sudan -- which lines up exactly with `flag_001.png` being Afghanistan
and `flag_020.png` Macao, so the picture key really is the nation id and the "214 flags, 214
regulations" coincidence is finally closed. The names sit in language slots inside the row
(Japanese first, then Spanish, Italian, English and the rest), and `+0x00` packs the row number
into its top bits.

The trap is worth writing down before somebody meets it: because the id is the position,
inserting a nation anywhere but the end renumbers every nation after it, and every flag,
player nationality and club country that pointed at them. A pack that adds a country must
append.

One more check on the emblems, because a placeholder that the game never asks for would be
wasted work: the strings that build the path (`symbol/emblemLc/`, `emb_`, `.png`, the variant
suffixes) have no instruction anywhere in the image pointing at them as a fixed address. They
sit in the same kind of constant pool as the `.\download\` strings -- reached by index from
script-like code, not by a `lea`. So nothing in the executable caps the competition id an
emblem can be asked for, and there is no bound to raise. Whether ours are drawn is a question
for the screen, not for the disassembler.

## Two player-count arrays the caps sets do not touch (2026-09-21, static)

Looking for the unpinned bounded OOB write behind the deep-save load crash, the question
"which constant of 30001 did we NOT raise" can be asked of the exe directly. Of the 132
`0x7531` constants in code, the deployed set covers 130. The two it does not:

* `0x1421b5e5b` -- inside the bundled OpenSSL (`nssl-1.1.0i/ssl/ssl_lib.c`). A coincidence of
  bytes, not a player count.
* `0x140c728c7` -- **real**: `mov ecx, 0x7531; rep stosd` fills 30,001 dwords at
  `[singleton 0x1436f9dc0] + 0xd8`, inside `0x140c72660`, the player-list screen
  (`PlayerListBasicInfo`, `PlayerListAbility`, `PlayerListGraph`, `PlayerListRole`,
  `PlayerListPlayPosition`). So there is a 120 KB player-indexed buffer, sized for the shipped
  30,001 players, that no caps set has ever raised -- while the deployed set runs the player
  array at 51,729. Nothing else in the 146 functions that reach that singleton indexes `+0xd8`
  with a scaled register, so how it is filled is not visible statically; whether it can be
  filled past 30,001 is the open question, and it is a question for a debugger, not a reader.
  If it can, the write lands just past a 120 KB allocation, which is the right shape for the
  crash.

And one that looked worse than it is: the subsystem at **edit block + 0x1676324** (the player
and member screens; see docs/competition-slot-ceiling.md for how it was found) holds two
arrays of **25,001** entries keyed by a u16 id, with 18 `0x61a9` constants in code. Every one
of them is a real bound: `cmp cx, ax` / `jb`, falling back to a default when the id is bigger.
So a world with ids above 25,000 -- ours is one -- does not overflow here; it silently gets
the default entry. Worth knowing when something on those screens looks wrong for a
high-numbered player, and worth not chasing as a crash.

## The season header above 127: thirteen trampolines instead of thirteen bytes (2026-09-21)

The season's standings object begins with a header of one entry per competition instance.
The shipped game holds 100; `hdr127` raised that to 127 by rewriting a single byte at each of
thirteen bounds. The measured world is now at **124 of those 127 in use, with 128 real
competitions**, so the cheap version is one step from being full again.

127 was never an engine limit. It is the largest value that fits in the 8-bit immediate of
`cmp r32, 0x64` (`83 /7 ib`), and all thirteen bounds use that form. The wider form,
`81 /7 id`, is three bytes longer than the instruction it replaces, so the site cannot hold
it -- which is why the generator used to refuse anything above 127.

What makes it cheap anyway: every one of the thirteen is the same shape,

    cmp ecx, 0x64        3 bytes (4 with a REX prefix for r8d)
    jb   <back edge>     2 bytes

five or six bytes together -- exactly what a `jmp rel32` needs, with at most one `nop` left
over. So each pair is redirected to a stub of its own holding the widened compare, the same
branch as a `rel32`, and a jump back to the instruction after the pair. Seventeen or eighteen
bytes each, 260 for all thirteen.

They go at `0x14252ea20`. `.trace` ends at `0x14252e800`, but sections are mapped a page at a
time, so `0x14252e800..0x14252f000` is executable memory that exists at runtime and has no
bytes in the file -- the same tail the nullguard modules already use. It reads as zero, and
the applier verifies that before it writes, so if another module got there first the whole
set aborts without touching anything. The nullguards hold up to `0x14252e8d0` and
`fl26chain`/`fl26cuphook` keep an observation ring at `0x14252e900..0x14252ea08`; the stubs
start clear of both and end at `0x14252eb24`, leaving about 1.2 KB.

Three things were checked before believing it, because replacing an instruction pair is only
safe if nothing else depends on those exact bytes:

* **Nothing branches into them.** A linear decode of all of `.trace` finds no jump or call
  aimed between the start of a pair and its end, and no aligned u32 anywhere in `.rdata`,
  `.trace` or `.data` holds an RVA pointing inside one -- so no jump table does either.
* **The flags are unchanged.** The stub performs the same `cmp` on the same register, and
  `jmp`/`nop` touch no flags, so whatever runs after the pair sees exactly what an in-place
  widened compare would have left it.
* **Every stub decodes back to what it claims.** The generated module is read back,
  disassembled, and each redirect matched to its stub: same register, the new bound, the
  original `jb` target, and a return to the original fall-through. Thirteen of thirteen.

The price stays small above 127 as well. The member boundary at `0x39a8f0` does not move, so
extra entries are paid for out of phase tables: 0xb4 per entry against 0x187c per table.

    entries   header bytes   phase tables that still fit
       100        0x4650              600
       127        0x594c              599
       192        0x8700              597
       256        0xb400              595

`python tools/hdr127.py 192` writes `sider/fl26hdr192.lua`: 42 patches -- 13 stubs, 13
redirects, the header initialiser's `mov r9d` count, and the phase-table base and count. The
work measured against the world: 124 in use of 127, 128 competitions wanting one. 192 leaves
room for about sixty more leagues without touching this again.

**Not run in a game.** Everything above is static. The one thing static checking cannot
answer is whether a header index is stored anywhere as a signed byte, in which case 128 and
up would misbehave in a way no bound scan shows; that is a question for a season.

## The player ceiling moves with the calendar: 51,729 -> 61,905 (2026-09-21)

51,729 was never a count the engine chose either. The player array is the one array that
cannot be relocated -- it begins at block offset 0, so its accesses carry no displacement --
and it can only grow into whatever sits above it. With the upper belt moved out of the way,
what sits above it is the season calendar at `0x16038a8`, and `0x16038a8 / 0x17c` is 51,729.
The world uses 51,327 of them, which is thirteen squads of thirty short of full.

The calendar set moves the calendar unit out of the block's middle and up past the old block
end (`0x1877070`). So in that set the ceiling is no longer the calendar's base but the
calendar's old *end*, and the whole 0x6cd00 the unit vacates belongs to the players.

What is above the vacated space was measured rather than assumed:

    python tools/blockrefs.py 16705a8 1877068
    r0  16705a8..1877068  3846 sites in 1193 functions

and the lowest block offset any of those 3,846 sites names is `0x16705a8` itself -- exactly
where the calendar unit ends. So the gap is the unit and nothing more, and the ceiling is
`calwiden.OLD_BASE + calwiden.OLD_UNIT = 0x16705a8`: 61,918 records, less the mode copy's
requirement that the cap be 17 mod 32, giving **61,905**.

    python tools/patchset.py teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures-calendar \
        --player-cap 61905 --date-keys <39 ids>

3,532 patches, exactly the sites the 51,729 build had -- no site appears or disappears, 152
change their value -- and the block is the same size, because the players grow into space
that is already inside it. `blockfit.py` reports 0 problems; the players now end at
`0x166f23c`, 0x136c below the calendar's old end.

That is 10,176 more players than 51,729: 339 squads of thirty, about seventeen more leagues
of twenty clubs. Making them is `mkplayers.py --per 30 --cap 61905`, which is world data and
a separate step.

**Not run in a game**, like the calendar widening it depends on.

## Every league we have ever built was a first division (2026-09-21, static)

The user saw our new clubs playing in the Champions League and asked how that squared with
the repository saying new clubs do not qualify. It does not square, and the repository was
wrong -- but the interesting part is why it happens, because the same field explains a
different failure we had been chasing with a DLL.

`mkleague.py` builds a league by copying the prototype competition's regulation record whole
(`ENGLAND_D1_LEAGUE` by default) and then changing the id, the competition id, the club count
and the name. Everything else is inherited, including `F+0x10` bits 15-17: the division.
Read out of the world that has been played:

    reg 17  (Premier League)    F+0x10 = 0020a020   tier 1
    reg 79  (Championship)      F+0x10 = 00212020   tier 2
    reg 11  (FL League 01)      F+0x10 = 0020a020   tier 1
    reg 49  (FL League 02)      F+0x10 = 0020a020   tier 1
    reg 60  (FL League 03)      F+0x10 = 0020a020   tier 1

All thirty-nine of ours are first divisions, in England's region, alongside the Premier
League. At runtime the field is `+0x304` bits 30-31, and 78 sites read it
(`regulation-record-decode.md`). Two families matter here:

* **European places go to tier-1 leagues of a region.** `0x141358bd0` and `0x141359a60`
  compute `tier == 1` and then call the rights resolver with right type `0xd`, which is
  "league position 1"; `0x1413b7910` collects a regulation id from the walk when its tier is
  1. So a first division in England's region is offered European places by construction --
  which is exactly what was seen on screen, and it is the engine behaving normally with the
  data we gave it, not a table overflow. Nothing was taken from anyone by a broken index.
* **Promotion needs the lower league to be tier 2 or more.** `0x141510430` reads `+0x7c`
  (the league above) only when the tier is >= 2, and `0x14131f430` gates the relegation-side
  check the same way. Our chain FL01 <-> FL02 <-> FL03 had the tier links set correctly and
  still moved no club (2026-09-19). The tier was never in that comparison, because it lives
  outside the `+0x70..+0x90` window that was diffed. Every league in the chain being a first
  division is a candidate root cause, and it is data, not a hook.

So the fix for both is the same one field. `mkleague.py` now takes `--tier`, `mkworld.py`
takes `--tiers 1,2,3` (cycled over the run), and `set_tier` writes bits 15-17. Checked: a
league built with `--tiers 1,2,3` comes out with `F+0x10 = 00212020` for tier 2, which is
byte for byte what the shipped Championship carries.

What this does NOT yet say: whether making FL02 a second division actually makes the engine
promote and relegate between our leagues. That needs a season. It does say that the earlier
conclusion -- "the tier link is necessary but not sufficient" -- was drawn with one of the
inputs wrong.

Not run in a game.

## Three tiers are handled by the engine, and the region is the other half (2026-09-21, static)

Asked whether a club can be relegated into a THIRD league, since the middle joint of our
chain was the thing that never worked. The resolver says yes, natively:

    0x141510430   +0x1a1  tier == 0x80000000 (2) -> 0x141547b60, then read +0x7c (above)
                  +0x1c5  a SECOND regulation's tier == 0xc0000000 (3) while this one is 2
    0x1415141c0   +0x09b  tier == 2 -> 0x141547b60
                  +0x0bd  tier == 3 -> the same call

So the pairing code is written for 1/2/3 and pairs a 2 with the 3 below it exactly as it
pairs a 1 with the 2. Nothing has to be added for a third division; what was missing was that
all three of ours were first divisions (previous section).

The region is the other half of the same question, because the engine reasons about a
pyramid inside ONE region: the leagues of a country, the cup filled from the first league of
a region, European places offered to the tier-1 leagues of a region. Our thirty-nine all sit
in England's, next to the Premier League.

`mkworld.py --group-regions N` now deals regions out per GROUP of leagues rather than per
league, so `--leagues 9 --tiers 1,2,3 --group-regions 3 --regions 24,32,40` builds three
three-division pyramids, one per region, instead of nine leagues scattered across three
countries with no relation to each other. Verified on a scratch world.

What is still undecided, and it is a design decision rather than a measurement: a pyramid
placed in a SHIPPED country makes our top flight a second first-division of that country.
The alternative is the four region ids that no shipped competition uses (11, 13, 14, 20),
which cost no executable change but have no row in the name table, so the menu header renders
with whatever the previous lookup left behind. Four free ids is four pyramids, twelve leagues.
Beyond that a pyramid either shares a shipped country or the name table has to grow.

The third possibility is the one the PES modding scene actually uses, and it is worth writing
down: add our leagues as the LOWER divisions of a real country and let them feed the shipped
top flight. That needs the tier link (+0x7c / +0x7e) to point at a shipped regulation, and
where those links are written from has not been found yet.

## A third division for France and Italy, and why there cannot be a fourth (2026-09-21, static)

France and Italy ship two divisions each. `tools/deepen.py` takes a league we built and puts
it underneath one of them: it copies the parent's region byte and calendar dword, sets the
tier to 3, writes `+0x04` (promotes into) on ours and `+0x00` (relegates into) on the parent.
Built on a scratch world:

    reg 20  FRANCE_D1_LEAGUE  region  24 tier 1  below=81
    reg 81  FRANCE_D2_LEAGUE  region  24 tier 2  above=20  below=186
    reg 186 FL_LEAGUE_01      region  24 tier 3  above=81
    reg 18  ITALY_D1_LEAGUE   region  40 tier 1  below=82
    reg 82  ITALY_D2_LEAGUE   region  40 tier 2  above=18  below=187
    reg 187 FL_LEAGUE_02      region  40 tier 3  above=82

This is the first thing in the project that writes into a SHIPPED competition's record -- the
parent's relegation pointer. Nothing is replaced or removed, and it lives in our own livecpk
copy of the table, so deleting the root undoes it; but Ligue 2's bottom clubs now have
somewhere to fall, and that is a change to shipped behaviour rather than an addition beside
it. Worth saying out loud because every other decision in this project has gone the other way.

**A fourth division is not possible as a tier.** The setter is three instructions:

    0x1414c9cc0   and dword [rcx+0x304], 0x3fffffff
                  movzx eax, dl ; shl eax, 30 ; or [rcx+0x304], eax

Two bits survive, whatever the file says: 1, 2, 3. Every reader compares against
0x40000000 / 0x80000000 / 0xc0000000 and nothing else, and the pairing code only ever pairs a
2 with the 1 above it and a 3 with the 2 above it -- nothing pairs a 3 with a 3. So a shipped
two-division country can be given exactly one more division, a country of ours can be three
deep, and a fourth or fifth would have to be moved by a module of our own rather than by the
engine.

Not run in a game. What a season would answer: whether clubs actually cross between Ligue 2
and ours at the rollover, which is the same question the three-tier chain of our own is
waiting on.


## The fourth division exists, and it is one byte away from working (2026-09-21, static)

Yesterday's wording -- "three tiers, and it is a hard three" -- was right about the field and
wrong about the consequence. The tier really is two bits at runtime (setter 0x1414c9cc0, four
values, one of them unused), so there is no tier 4 to write. But the tier value is not what
decides whether a fourth division moves clubs. That is decided by 0x141510430, the function
that answers "where does this club go at the end of the season", and it is built out of three
gates:

    0x1415104a1   tier >= 2                     -> +0x7c, the league above   (PROMOTION)
                  cmp eax,0x80000000 ; jb skip
    0x1415104d6   tier == 1, bottom three       -> +0x7e, the league below   (RELEGATION)
    0x1415105f5   below == 3 AND this == 2,
                  bottom three                  -> +0x7e, the league below   (RELEGATION)

The identity of the partner league never comes from the tier -- it comes from the link fields
+0x7c / +0x7e, which are ours to write. And the promotion gate is a `>=`, not an `==`. So a
fourth-level league marked tier 3 and pointed at a third-level league promotes its champion
with no patch at all. What does not happen is the other direction: a tier-3 league matches
neither relegation gate, so the third level never sends anybody down to the fourth. Clubs
climb and never fall.

The asymmetry is a single byte. The second relegation gate reads

    141510612  3d 00 00 00 80   cmp eax, 0x80000000
    141510617  75 b1            jne <no relegation>      ; require exactly tier 2

and `jne` -> `jb` makes it "tier 2 or 3", the same shape the promotion gate already has. The
other half of the gate -- the league below must be tier 3 -- is left alone and is exactly
right: everything below the second division is tier 3 anyway. sider/fl26deep4.lua writes that
byte, verified, all-or-nothing.

Nothing else objects. Every other read of the field tests tier == 1 (European places:
0x141358bd0, 0x141359a60, 0x1413b7910) or tier >= 2; the pairing helper 0x1415141c0 already
has a tier-3 branch that is identical to its tier-2 branch; and a scan of the whole code
section for the `and eax,0xc0000000` idiom finds thirteen comparison sites, none of which
searches for "the tier-3 league of this region". Two tier-3 leagues in one pyramid is not a
conflict anywhere.

Built and checked: tools/deepen.py now accepts a tier-3 parent, and three runs on the 39-league
world give France a five-deep pyramid --

    reg 20   FRANCE_D1_LEAGUE   tier 1   below=81
    reg 81   FRANCE_D2_LEAGUE   tier 2   above=20   below=60
    reg 60   FL_LEAGUE_03       tier 3   above=81   below=61
    reg 61   FL_LEAGUE_04       tier 3   above=60   below=62
    reg 62   FL_LEAGUE_05       tier 3   above=61

-- each child inheriting the parent's region (24) and calendar shape (0x0081a080). Not run in
a game yet, and the standings-position check in both relegation tails is hard-coded to the
bottom three, so the number that go down is not ours to choose from the data.

## The 39 leagues are off England at last (2026-09-21, built)

`tools/spreadregions.py --plan free` was written on the 19th and never applied to a deployed
world. It is now: `_FL26G39Reg` is a copy of `_FL26G39Tri` with our 39 leagues moved onto the
four region ids that no shipped competition uses --

    region 11   FL League 01..10      region 14   FL League 21..30
    region 13   FL League 11..20      region 20   FL League 31..39

-- ten each, none of them near the ~11-competition menu limit, and England is back to the five
competitions it ships with instead of forty-four. Nothing shipped moved; the FL01/FL02/FL03
pyramid stays inside one region, which is what promotion needs.

Two consequences to expect in the game, both wanted:

* the Master League country list should stop dropping our leagues, which is what the whole
  spread was for;
* our clubs should **stop** turning up in the Champions League. European places are granted
  per competition by the rights table at 0x1434f1fa0 and then filtered by the region of the
  source competition; regions 11/13/14/20 have no rows in that table, so no places are offered
  there. That is the same mechanism that put them in the Champions League while they were all
  tier-1 leagues in England's region -- nothing was ever stolen, and now nothing is offered.
  Granting a new league places of its own, deliberately, is still the open half of that job.

The four ids have no row in the exe's 24-record region-name table (0x1426770c0), so the
heading a region draws is whatever the previous lookup left behind. `tools/mkregioncats.py`
is the answer to that and has not been built into a set yet.

Not run in a game.

## France and Italy are five divisions deep, and it is deployed (2026-09-21, built)

`_FL26G39Deep` is the world to test: `_FL26Swiss36` (the 39 leagues plus the Swiss-format
FL Champions League), with `spreadregions.py --plan free` applied and then six runs of
`deepen.py`:

    FRANCE   Ligue 1 (20, t1) -> Ligue 2 (81, t2) -> FL 34 (180) -> FL 35 (181) -> FL 36 (182)
    ITALY    Serie A (18, t1) -> Serie B (82, t2) -> FL 37 (183) -> FL 38 (184) -> FL 39 (185)

all six children tier 3, each inheriting its parent's region and the +0x10 shape. The other
33 leagues stay on the free regions 11/13/14/20, and no region in the world now holds more
than ten competitions -- France 7, Italy 8 -- which is inside the menu's comfort zone.

Nothing was taken from France or Italy: European places are granted to tier-1 leagues of a
region and ours are tier 3, and a cup fills from the lowest competition id in its region,
which is still Ligue 1 and Serie A. `sider.ini` now carries `fl26deep4.lua`, so the third
division relegates into the fourth.

To test: pick a club in FL League 35 (French fourth division) or FL League 38 (Italian
fourth), both of which `fl26comptab.lua` gives a Select Team slot. What to watch at the end
of the season is the bottom three of FL 34 going down into FL 35 -- that is the byte -- and
the top of FL 35 going up, which needs no byte at all.

One label corrected while doing this: `mkleague.py` called regulation +0x00 `R_NAMEID`. It is
the id of the division this one relegates into. It was being zeroed, which is the right value
for a new league, so nothing built with it was ever wrong -- only the name was.

## A region with no name does not draw a blank, it draws the country before it (2026-09-21)

The heading table at 0x1426770c0 is 24 rows of {u64 picture name, u32 region id, u32 pad}, and
`tools/dataref.py` finds exactly **one** instruction in the whole exe pointing at it: the strip
builder 0x140acd3f0.

    140acd478  lea r10, [0x1426770c8]     ; the id column
    140acd47f  lea r11, [0x1426770c0]     ; the name column
    140acd490  cmp [rax], edx             ; this row's id?
    140acd496  add rax, 0x10
    140acd49a  cmp ecx, 0x18              ; 24 rows, then give up
    140acd4a6  mov rbx, [r11 + rax*8]     ; found: the picture

When nothing matches, the loop falls out **without touching rbx**, so the heading drawn is
whatever the previous lookup left there -- the country before ours in the list. That is worth
knowing for its own sake: an unnamed region is not invisible, it is a duplicate.

The ids with a row are 1-10, 12, 15-19, 21-28. The four without one are **11, 13, 14 and 20**,
which are exactly the four `spreadregions.py --plan free` moves our leagues onto.

`tools/mkregnames.py` generates `sider/fl26regnames.lua`: the 24 shipped rows byte for byte
into .rdata padding at 0x1426d1f20, four rows of ours after them, the two leas re-pointed and
the 0x18 raised to 0x1c. Four sites, one function, nothing shipped moved; the rows are written
and read back before the code is touched, so the loop is never aimed at a table that is not
there. Verified by disassembling the generated bytes: both displacements land on the copy.

What our regions are called is the part that is borrowed. A heading is a drawn picture, and its
name is a symbol inside the AFP package in common/menu/general/compeCategorySelect.bin (one
entry, `afp_compeCategorySelect.apk`, a TXP2 texture package). Adding a symbol of our own is a
job on that format and is not done, so the default mapping borrows the four generic headings
the game already draws -- 11 = rest of Europe, 13 = rest of Latin America, 14 = rest of Asia,
20 = events. Two regions then share a heading, which is untidy and still better than showing
another country's.

Deployed, not run in a game.

## Regions: 29 was one comparison and five bits, and the real ceiling is 64 (2026-09-21)

The bound has been on the list since section 9 and is now built. One function parses a
competition row into the runtime object, and the region is the first field it reads:

    1414f8390  8b08       mov   ecx, [rax]      ; dword 0 of the Competition.bin row
    1414f8392  c1e91b     shr   ecx, 0x1b       ; bits 27..31 -- five bits
    1414f8395  0fb6c1     movzx eax, cl
    1414f8398  241f       and   al, 0x1f
    1414f839a  3c1d       cmp   al, 0x1d        ; 29 or more?
    1414f839c  7304       jae   0x1414f83a2     ; thrown away, the default kept
    1414f839e  440fb6f1   movzx r14d, cl

Eighteen bytes, and both halves of the limit are in them. The runtime field is six bits
(`0x1414c9c10`: `and edx,0x3f ; shl edx,7` into `+0x30c` bits 7..12, and all thirty readers
use `shr 7 / and 0x3f`), so **64** is the ceiling that actually exists. The sixth bit only
has to come from somewhere in the file, and it is already there: `Competition.bin +3` holds
the region in bits 3..7 and its bits 0..2 are **zero in all 131 rows** of the installed
world. Bit 0 of that byte is bit 24 of the dword, the top of the 9-bit field below, whose
values never come near it.

`sider/fl26reg64.lua` replaces the eighteen bytes with eighteen:

    8b08 mov ecx,[rax] / 8bc1 mov eax,ecx / c1e91b shr ecx,0x1b / c1e813 shr eax,0x13
    83e020 and eax,0x20 / 0bc8 or ecx,eax / 448bf1 mov r14d,ecx

The compare is gone because a six-bit value cannot be out of range, and **every shipped row
keeps the region it has**: a byte with bit 0 clear -- which is all of them, and all of ours
today -- decodes to exactly what it decoded to before. Installing the module on a world that
does not use a high region changes nothing at all.

Checked the three ways the header stubs were: the eighteen bytes in the exe are what the
module claims; a linear decode of the whole code section finds no branch landing inside the
replaced run; and no aligned word in .rdata, .data or .trace holds an RVA pointing into it.

Tools, all of which now go through one pair of functions rather than shifting by three:

* `mkleague.enc_region(id)` / `dec_region(byte)` -- `((id & 0x1f) << 3) | ((id >> 5) & 1)`,
  which is plain `id * 8` for everything below 32, so nothing built before changes.
* `spreadregions.py --plan own` -- a region of its **own** for every one of our leagues.
  Leagues already placed inside a shipped country on purpose (the six `deepen.py` put into
  the French and Italian pyramids) keep the region they have; the other 33 take free ids,
  the four below 29 first and then 29..57.
* `mkregnames.py --root <world>` -- reads which regions a world actually uses, and writes a
  heading row for every one that has none.

Built: `_FL26G39Own` is `_FL26G39Deep` with that plan applied -- 33 countries of one league
each, plus three of ours in France and three in Italy. The active root is still
`_FL26G39Deep`; the module is installed either way because it changes nothing until a high
region is used.

What is still borrowed is the wording: 33 headings drawn from a pool of four generic
pictures means a lot of repeats, and a heading of our own needs a symbol added to the AFP
package in compeCategorySelect.bin. The count is solved; the labels are not.

Not run in a game.

## 2026-09-21 (night) -- the second 1536 wall is sized by a calendar field, not by a team table

Static, no game. The second of the two crash sites recorded for the 1,536-club wall
(`0x140cd6a21`, the one reached through the `d_schedule_` lookup) was read forwards from the
top of its function instead of backwards from the fault, and the vector it indexes turns out
to be built three instructions after the function starts:

```
140cd6960  lea  rcx, [rsp + 0x44]
140cd6965  call 0x1415765e0            ; [rsp+0x44] = dword [block + 0x1642a24]
140cd696a  xorps xmm0, xmm0
140cd696d  movdqu [rsp + 0x48], xmm0   ; an empty vector: first = last = 0
140cd6975  mov  [rsp + 0x58], rdi      ; end of storage = 0
140cd697a  mov  edx, [rsp + 0x44]      ; ... sized by that dword
140cd697e  lea  rcx, [rsp + 0x48]
140cd6983  call 0x14157b300
...
140cd6a18  mov   edx, [rsp + 0x40]     ; an index the 'd_schedule_' lookup wrote
140cd6a1c  mov   rcx, [rsp + 0x48]
140cd6a21  movzx edx, word ptr [rcx + rdx*4]      <-- faults
```

`0x1415765e0` is a two-line getter: it calls the singleton, takes the edit block from `+0x48`
and returns the dword at block `+0x1642a24`. That offset is already named in
`patches/calendar-tail-sites.json`: the season calendar is 365 records of 0x2c4 at block
`+0x16038a8`, and the three fields immediately after it are `+0x3f174` (the current day,
0x1642a1c), `+0x3f178` and `+0x3f17c`. `0x1642a24` is the third of them.

So the vector is one 4-byte entry per whatever that calendar field counts, and the index comes
out of the schedule lookup unchecked. This is the first size behind either wall that is a
**field we can read**, rather than a constant that does not exist anywhere in the file -- the
three previous scans were right that nothing is bounded at 1536, and this is why: the bound is
carried in the data block, not in the code.

Two consequences worth testing when the game is next run:

* the field is loaded in many places and, as far as a store scan can tell, written by the data
  loader rather than by code -- so its value comes from the shipped data and the save, which
  is exactly the shape that would produce a hard stop at a number the executable never
  mentions;
* it sits in the calendar tail, which the `...-calendar` patch set already relocates. Whether
  that set moves the second wall at all is now a one-run question rather than a search.

The first wall (`0x1413236e4`, the board's objective) is untouched by this and still needs its
own answer. Nothing here has been tested in a game, and nothing about the wall is fixed yet.

## 2026-09-21 (night) -- an audit of everything installed, and two things that were wrong

No game. Every module named in `sider.ini` was parsed, each `{va, old}` pair checked against
the bytes actually in `FL_2026.exe`, and every write range compared with every other module's.
2,760 + 69 patches across sixteen modules: **all bytes match**, and after the fix below there
are **no overlapping writes**. All 44 Lua files compile.

### fl26nullguard2 was silently not installed

Its trampoline sat at `0x14252e7e8`. Every other guard is on a 0x20 grid starting at
`0x14252e800`, which is where `.trace`'s file-backed bytes end and the loader's zero-fill
begins; this one was below that line, in the padding fl26caps also uses. The fixture-date
table caps writes there has grown to end at `0x14252e7f4` -- twelve bytes into the
trampoline. caps is first in `sider.ini`, so by the time nullguard2 verified, it found 0xff
where it expected padding, aborted itself exactly as designed and wrote nothing. The module's
own abort message anticipated this: *"If site 1 is the mismatch, another module has taken that
padding."* Nobody was reading for it.

Moved to `0x14252e880` with all three rel32s recomputed (the `jz` to `0x140fc93c6`, the `jmp`
back to `0x140fc923e`, and the site jump at `0x140fc9238`). The header now says why, and that
nothing may be placed below `0x14252e800`.

Worth noting what this means for the crash history: any run since the date table last grew was
made **without** that null guard, so a crash blamed on something else may have been this.

### the installed fl26comptab was the old one

The deployed copy was 159 lines; the repository's is 234 -- the version from
`33b48f9 comptab: give every remaining league a slot of its own`. So the install still had the
build that leaves thirteen of our leagues without a Select Team slot. Redeployed.

### what the audit says is fine

* the active root `_FL26G39Own`: 131 competitions, 254 regulations, 40 of ours with an emblem
  each, 2,340 club crests, 57 regions all of which have a heading row.
* promotion and relegation links: every link resolves, and no link of ours reaches into a
  shipped competition except the two `deepen.py` wrote on purpose (France D2 <-> our France D3,
  Italy D2 <-> our Italy D3).
* shipped regulation 52 still relegates into 145, which is ours. That is shipped data, not
  something we wrote, and the decision on it is still open.
* the caps set installed is `...-mlcopy-fixtures`, **not** the `-calendar` one, so the 280
  matches a day ceiling is still in force in this install.

### The stored ...-fixtures-calendar set could never have applied (same night)

Installing the 792-per-day set and re-running the byte check found seventeen of its
thirty-eight date patches mismatching, which would have aborted all 3,532 of them: the set
would have been in `sider.ini` doing nothing at all.

Two faults, both in `date_patches()` in `tools/patchset.py`:

* it assumed the case byte it is about to change is `DATE_CASE_EMPTY` (0x3e). For a
  regulation that reuses a shipped calendar it is that calendar's own case -- 0x19 for 74,
  0x03 for 76, 0x2c for 138 -- so the `old` was wrong for eight ids;
* it had no bound. The case table is 176 bytes at `0x1415802e7` and ends at `0x141580396`;
  a table of 16-bit values begins at `0x141580397`. Nine ids (176, 178-185) were being
  patched into that one. `cup_patches()` next to it has enforced `1 <= k <= 175` since it was
  written; the league path never got the same guard.

`date_patches()` now reads the current byte out of the exe instead of assuming it, and
refuses an id above 175 with the message that spread mode (`--date-offsets`) is the only
route to one. The set was regenerated with the date configuration the working
`...-fixtures` set records in its own JSON (39 keys, the `dayplan.py` shifts) plus
`--player-cap 61905`: **3,504 patches, every byte verified against the exe, no overlap with
any other module.** Installed.

The install therefore changed capacity, so every existing save is void -- a save is tied to
the set that made it.

## 2026-09-21 -- who plays in a cup: an explicit list, not a rule

Measured offline from `CompetitionEntry.bin` in `_FL26G39Own` (2,133 rows of 12 bytes, 120
competitions with an entry list). A cup's field is not derived from the league table or from
the region at all: every participant is a row of its own, `club id` at +0x00, a unique entry
id at +0x04, the competition at +0x08 and a **seeding position** at +0x09, numbered 1..N with
no gaps.

    Coppa Italia (comp 16)     40 entries = Serie A (20) + Serie B (20), exactly
    Coupe de France (comp 18)  36 entries = Ligue 1 (18) + 18 of Ligue 2's 21
    FA Cup (comp 15)           44 entries -- the largest shipped list
    Copa del Rey               42        Copa do Brasil 41

So a domestic cup here is the top two divisions and nothing else, and the count is whatever
the list says: 44 is not a power of two, so the bracket already copes with byes.

Seeding runs strongest-first and is only roughly sorted by division:

    Coppa Italia, by position:     AAABAAAAAAABAABBABAABBBBABABBABAABBBBBBB
    Coupe de France, by position:  211121112111111121122222222211122222

The regulation's team count at +0x0b is **not** the entry count for a cup -- Coppa Italia says
20 and has 40 entries -- so that field means something else here and cannot be used to size a
cup. A cup rulebook also carries no pointer to a league: +0x00 and +0x04, the promotion and
relegation links, are zero in every cup checked.

What this means for a deeper pyramid: adding France D3, D4 and D5 changes nothing about the
Coupe de France, because the cup never looks at them -- the risk is not that lower divisions
flood the cup, it is that our clubs are absent from it. Putting them in is a matter of
appending entry rows at positions after the current last, which is also where they belong as
the weakest seeds.

Two things a run still has to answer: whether the entry list survives a season rollover or is
rebuilt, and whether anything above 44 entries is accepted.

## 2026-09-22 -- a Master League season is created end to end, and the crash was three crashes

Creating a Master League season had been failing for a day. Splitting the patch set one step
at a time turned what looked like one crash into three unrelated ones, two of which are now
settled and one of which is cleanly attributed.

**The one that was never ours.** Fault `0x140aeee1e`, a string destructor whose `this` is
garbage, reached through `MLGeneralSettingsStart` and a vector inside the singleton at
`0x1436f9dd0` (`MenuUtilityDemoPlayer`, `0x620` bytes, constructor `0x140e9bde0`). That object
embeds an element of the vector's own type at `+0x80`, `0x230` bytes long, ending exactly on
`vector.begin` at `+0x2b0`, so anything running past it lands on the pointer -- which in one
run held UTF-16 text. A control run with our rank modules disabled and the regulation file
reverted reproduced it byte for byte, so it is a property of the shipped binary.

A read-only probe (`sider/fl26demoprobe.lua`) now reports that vector's three pointers
whenever they change and names the invariant that broke. In two runs it read the vector
healthy throughout -- three elements, then two -- and the crash did not recur. The trail is
closed until it comes back on its own.

**The one the calendar set makes.** Fault `0x1484ed4c0`, twice, byte-identical, always at the
manager-settings step: a write through a garbage pointer with every register holding garbage,
inside `.impdata`, on a thread whose stack runs through the low runtime functions rather than
the Master League flow. That is the shape of a corrupted heap, not of a bad index caught in
the act. The instruction itself cannot be read: the bytes in the file there are not code,
because the protector only decrypts them into memory, and the dump does not cover the page.

It is the calendar set, and nothing else. The same walker, the same club, the set **without**
`-calendar` walks straight through that step. `calwiden` grows a calendar day from 280 match
ids to 792 -- stride `0x2c4` to `0x6c4` -- across 519 sites in six kinds (base, stride, cap,
count, event, after). One site left on the old stride writes outside the block, which is
exactly the shape of the `+0x307` gap that the rank widening had. That is where to look.

Worth knowing before spending a night on it: our world's busiest day currently holds **75**
match ids against a cap of 280. The calendar widening is not needed yet.

**The one we fixed.** With the calendar set out of the way the flow reaches the board meeting
and dies there at `0x140cd6a21`, a plain null read. The code builds the name `d_schedule_`,
asks `0x14150d620` for the list and the index into it, checks the *return value* of the next
call and even has its own exit for "nothing here" at `0x140cd6ead` -- and then indexes the
list without ever checking the list pointer:

    140cd6a12  je     0x140cd6ead               ; the game's own "nothing here" path
    140cd6a18  mov    edx, dword ptr [rsp + 0x40]   ; the index -- 0
    140cd6a1c  mov    rcx, qword ptr [rsp + 0x48]   ; the list  -- NULL
    140cd6a21  movzx  edx, word ptr [rcx + rdx*4]   <-- faults

`sider/fl26nullguard9.lua` replaces those thirteen bytes with a trampoline at `0x14252e8e0`
that does the same three instructions with a null test between them and, when the list is
empty, takes the branch the game already has. It invents nothing.

**The result.** Set `teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures` plus
nullguard9: the whole creation walk completes, the season starts, and the scheduler lays out
**3775 matches with no day anywhere near full** -- busiest day 75 of 280, 205 to spare.

## 2026-09-22 (afternoon) -- why 32 of our 39 leagues never get a single match

Two fresh Master League seasons were created from the same patch set
(`teams-coaches-regs-players-dates-matches-upper-mlcopy-fixtures` + `fl26nullguard9`),
differing only in which club the walker picked, and both were measured at creation,
before a single day was advanced.

| measured at creation | club in Montenegro D1 (one of ours) | club in the first, shipped league |
|---|---|---|
| season starts on day | 30 | 231 |
| match records live | 3775 | 8832 |
| countries with a season | 24 | 55 |
| our leagues with fixtures | 2 (49, 60) | 7 (11, 180-185) |

### The rule

A competition is only given fixtures if it enters the season header, and it only enters
that header if the game's own competition list reaches it. Reading the data file makes
the pattern exact:

```
 81 Ligue 2 BKT   -> below 180 France D3 -> 181 France D4 -> 182 France D5
 82 Serie BKT     -> below 183 Italy D3  -> 184 Italy D4  -> 185 Italy D5
 11 Croatia D1    -> below  49 Slovenia D1 -> 60 Serbia D1
```

The six divisions hanging under Ligue 2 and Serie B get a complete 380-match season every
year. Competition 11 gets one because the game lists it outright. **The other 32 are
stand-alone first divisions in new countries of their own, hanging off nothing, and they
get no matches in any run.** This is not the calendar, not the date jump table, not the
club count: nothing ever registers them.

Ids above 175 are not the obstacle either. 180-185 are above it and work, because they are
reached through the chain rather than through the per-id jump table at `0x141345cc0`
(`cmp eax, 0xad; ja` -- ids 2..175 only, and 142 of those 174 ids point at the empty case
`0x141345f0a`, our 30 low ids among them).

### The second effect, which is what a player sees

Taking one of the orphan leagues as your own club does not merely leave that league empty;
it derails the whole world build -- 24 countries instead of 55, a season that starts in
January instead of August, and less than half the matches. That is the reported symptom:
no table, no fixtures, and a mid-season review cutscene in June on a world whose season the
game already considers finished.

### Where the season is assembled

* `0x141348470` builds the list of competition ids and calls `0x141348210` for each.
* `0x141345cc0(compid)` dispatches per id through the byte table `0x141345f74` (174 entries,
  id - 2) into the jump table `0x141345f48`; case 10 = `0x141345f0a` does nothing.
* `0x141590420(compid)` registers one competition: `0x1415451a0` reads the key from
  `regulation + 0x80` (the country id), `0x14158f420` finds or claims the header entry
  (100 entries of 0xb4, searched with `cmp ecx, 0x64`), `0x14158fd90` fills it and writes
  the season year into `regulation + 0x2fc` through the setter `0x1414ca0d0`.
* A regulation still outside a season keeps `+0x2fc = 0xffff` and `+0x300 = 0x02010016`
  with zero phases and fixture index `0xffffffff`; one inside a season reads `0x07e9`
  (2025) and `+0x300 = 0x03310016` with 38 phases. That pair of fields is the quickest
  live check of whether a competition made it in.

### Corrections to the entry above

* The crash `0x1484ed4c0` is **not** caused by the calendar-widening set. This document
  already records the same offset three times on 17 September during season generation on a
  set without that widening. The morning's attribution was a frequency observation, not a
  cause.
* "The calendar widening is not needed yet" was based on an unfinished season. Once the
  season fills, the busiest day holds 251 of 280, leaving a headroom of 29.

## 2026-09-22 (evening) -- measured live: the door admits every league of ours; nothing ever showed them to it

Four hooks in `tools/native/fl26join.c` (loaded by `sider/fl26joindll.lua`), every line
mirrored to `SiderAddons/fl26join.log` as it is written so a crash cannot lose it:
register_all `0x141343bf0`, enter_season `0x14158f420`, the season builder `0x1413156e0`
and the door `0x1413ac170`. A separate sampler (`tools/flagwatch.py`) read the regulation
records every half second from the title screen on.

### What the measurement showed

* `+0x304` bit 8 (the season flag) is off for every regulation on the title screen and is
  switched on for all of them at once during club confirmation, before the first build.
  The hypothesis that it stays off for ours is refuted.
* Competitions enter a season on **two** occasions, not one.
  1. At creation the builder `0x1413156e0` runs once with a fixed include list of 55 ids
     (the calendar-year competitions). 40 entered, among them our 49, 60 and 162, which
     reuse shipped calendar-year ids. The list is static and is not the lever.
  2. In play, when the calendar reaches a registration date, `0x141343bf0` is called with
     the ids due that day -- on day 41 it was a single id, 9 -- and registers each of them
     plus every regulation whose parent `+0x76` names one. That vector comes from the case
     table at `0x141345cc0` over ids 2..175 and cannot be extended by data.
* The door `0x1413ac170` answered YES to every one of our ids it was shown (41 of 41), and
  each went straight to enter_season from `0x1413ac37e`. Its only refusals are a missing
  record and a clear bit 8; `0x1413f3e00` is not a filter.

So 33 leagues had no season because nothing ever presented them, not because a check
rejected them. Two earlier patches that widened the builder's include list were aimed at
the wrong list.

### The fix, and its result

`fl26join.dll` appends our ids to the vector `0x141343bf0` receives (the game's ids first,
unchanged, then ours). On day 41 all 39 leagues of the world entered. Read live with
`calread.py --set ...-fixtures --matches --key N`:

| leagues | schedule |
|---|---|
| 36 | 38 match days, 10 matches each |
| 49, 60, 162 | doubled (20 per day): they had already entered at creation |
| 133 | entered, no fixtures (split system, kind 6, 12 clubs -- separate problem) |
| 62 | no regulation record in this world |

The match table went from 3,775 to 18,617 records; the busiest day holds 182 of 280.

Two more things the same run showed, and how the build that followed answers them:

* `0x141343bf0` is not called once a year. It is called on every registration date the
  calendar reaches -- day 41 (id 9), day 122 (id 160) -- and the first build appended our
  ids each time, so on day 122 every league of ours entered a second time. An id whose
  record already carries a season year (`+0x2fc != 0xffff`) is now left out.
* The three that entered at creation had been handed a calendar-year season by the builder
  (year set on the spot, an end-of-season pass over empty standings on day 116). When the
  builder is the caller (return address `0x141315c0b`) the door now answers no for our ids;
  the builder treats that as an ordinary skip, and they enter on day 41 with the rest.

Run 5 with that build: the builder's three asks were refused, the season started with
2,709 matches (3,775 minus exactly the three calendar-year schedules), on day 41 all 40
present leagues entered with "0 of ours already in a season", and live reads gave 49 and 60
38 rounds of 10 and 162 34 rounds of 9 -- single schedules, 17,551 matches in the table.
Not yet measured: the season's end (whether the game tears ours down and the hook
re-enters them the next year), and league 133's split format.

### A note on the manager-settings crash

Two runs in a row died at the manager-settings step in the protector's obfuscated code
with every register garbage (`0x1484ed4c0`, then `0x1531cc313`), while the observer's
door hook was calling the game's own lookup `0x1414bc860`. The third run, with hooks that
run no game code at all and the `...-fixtures` set, went through. That is not proof of the
cause -- this crash family is on record without any observer -- but the hooks now only
read memory.

## Fixes before the next season test (2026-09-22, evening)

1. **Season start (fl26augseason.lua).** A career in one of our stand-alone leagues started
   on 1 January because the career builder 0x1412695b0 takes the season type from the user's
   competition: 0x1415762a0(comp) -> region -> 0x141576140(region), a table of 25 (region,
   type) pairs for the shipped regions 2..28. Our leagues sit in regions 29..63
   (fl26reg64), the lookup falls through to `mov eax,5` at 0x14157623d, and 5 becomes
   type 1 = calendar year. The module redirects that fall-through to a trampoline at
   0x14252ee00 that answers 0 (European, August start) for regions 29..63 and 5 for
   everything else. Shipped regions cannot reach 29, so shipped competitions are unchanged.
   Deployed, verified in sider.log; not yet played.
2. **fl26chain "standings 0/0".** All three applies seen on 22.09. had no INPUT standings
   for 49/60, although both lists were written. The world was the calendar-year one (fix 1),
   so this may simply go away. The DLL now falls back to the league's season table
   (0x14158e000(id), 48 slots of 16 bytes at +0x10, the same read the INPUT filler
   0x14135e3a0 does) and logs whether the INPUT entry and the table were there.
3. **Swiss comp.** Regulation 186 (comp 174, 36 clubs) *is* in `_FL26G39Own`; it never
   played because fl26joindll's id list stopped at 185, so no season registered it. 186 is
   now in the list (42 ids).
4. **Deep-save load crash (vcruntime memset).** Not solved. The fault was at block+0x26d0000
   while clearing rec596 record 17321 of 46000; the block had 0x26cfff0 usable bytes, a size
   that matches no patch set's block size. The same save loaded on the next attempt. Kept:
   the supervisor's reload retry and blkwatch.py to catch the block size if it recurs.

Correction, same evening: fl26nullguard9 is NOT redundant. It guards the same read as
fl26nullguard3, but tools/guard3.py switches nullguard3 off for season generation (it breaks
generation), and nullguard9 is what covers that step. With both loaded nullguard9 aborts,
which is harmless. Turning nullguard9 off cost one generation attempt: 0x140cd6a21 during
the manager settings, exactly the crash it exists for. It is back on.

## Season 2 in an August world: what the rollover did and did not do (2026-09-23, night, live)

Run: career in our Montenegro league (reg 11), fl26augseason + fl26superguard + fl26join +
fl26chain loaded, set `...-upper-mlcopy-fixtures`, walked from day 15 of season 1 to day 302
of season 2 with `tools/seasonplay.py`.

* The Super Cup crash `0x1413605a9` did not come back once fl26superguard was installed
  (day 81 -> 302 of the next season, including the July rollover).
* At the rollover (1 July) our leagues were admitted again with 20 clubs each, and the
  season-2 fixtures of reg 11 start on 24/8.
* **No promotion or relegation happened anywhere in our chains** -- 49/60, France
  20/81/180/181/182, Italy 18/82/183/184/185 all kept their club sets.

### Why: the season-end filter works by region group, and the chains are in the wrong group

`0x141365c50` (called from the league end `0x141366380`) builds its list of competitions from
`0x1414ccd10` (all records whose type `+0x308 >> 23 & 0x3f` is in mask `0xf9c2`), then keeps
a record only if

1. its confederation code (`+0x300 >> 25 & 0xf`) equals the argument,
2. `0x141576140(0x1415415f0(id))` -- region -> season group, **the same lookup
   fl26augseason already patches** -- equals the group of the phase being ended
   (`0x14157f6f0`, table `0x14298ca00`); group 5 exits at once,
3. and, for types other than 1/6/11, it is closed there (`0x141363040`, `0x141363170`).

Region -> group read live for every regulation of the world:

| group | regions | ours in it |
|---|---|---|
| 0 (Aug-May) | 2,4,6-12,15,22,27 and, with augseason, 29-63 | 11 (region 11), 74-179 (regions 30-57) |
| 1 | 16,18,19,21,23,28 | 162 (region 28) |
| 2 | 13,14 | **49 (13), 60 (14)** |
| 3 | 17,20 | 61 (20) |
| 5 = never ended | 1,3,5,24,25,26 | **180-182 (France, region 3), 183-185 (Italy, region 5)** |

So the France and Italy extensions sit in regions the stock season end never visits -- the
same is true of the shipped French and Italian leagues themselves (20, 81 in region 3; 18,
82 in region 5). The pair 49 -> 60 is in group 2 and is ended in that group's phase, not at
the July rollover. Nothing here is a bug in our DLLs; the chains were put in regions whose
season type does not match the season they play.

Consequence for the design: a chain that should promote at the July rollover has to live in
a group-0 region. The additive way is our own regions 29..63 (augseason maps them to 0);
remapping 3/5 in the lookup would change how the shipped French and Italian leagues behave
and is off the table.

### The New Year emptying of 76, 93, 94, 96, 98 (and 162)

The season builder `0x1413156e0` is run at New Year with its calendar-year include list
(55 ids, static in the exe): `... 67 68 76 93 94 96 97 98 119 ... 162 ...`. Five of our
leagues reuse shipped ids that are on that list. In the log of the run through New Year the
door was never even called for 76/93/94/96/98: their season flag (`+0x304` bit 8) was
already clear and their club count 0 when the builder reached them, and from then on every
register_all offered them to the door, which refused ("flag OFF, clubs 0") until the July
rollover. 162 kept its flag, was refused by our own door_pre (builder at creation), and came
back through register_all with 0 clubs.

The flag has one setter, `0x1414ca020`, with seven callers (`0x14126f74c`, `0x14126f8be`,
`0x14126f942`, `0x141270074`, `0x141315a4f`, `0x1413631f0` in `0x141363170`, `0x141522c00`).
fl26join.dll now hooks the setter as an observer and logs every clear of one of our ids with
its caller and a rough stack, to name the one that fires at New Year.

## The July rollover, fixed: region groups, the no-movement path, and promote counts (2026-09-23, morning, live)

Test method: slot-3 save at day 116 of season 2 (August world), run past day 181, diff the
club sets of every tier (`tierwatch.py`), read `fl26join.log` / `sider.log`.

What was wrong, in the order it was found:

1. **Region group.** The season-end filter `0x141365c50` keeps a league only when the group of
   its region (`0x141576140`) equals the phase group. France (region 3) and Italy (region 5)
   map to 5 = never. `fl26seasonend` redirects the filter's call so regions 3 and 5 count as
   group 0. Only that call site; the career season type is untouched.
2. **All-or-nothing.** Any league in the list without a season table (`0x141590750`) sends the
   whole group down `0x141365ed0` (re-list members, move nobody). That is why nobody in
   England moved either and every table carried on (47 rounds by November).
3. **Erasing is not enough.** Erasing table-less leagues from the list let the mover run a
   pair (A,B) where B had no table; the mover then wrote B = only the clubs relegated from A.
   Ligue 2 (shipped) and our 49 ended with 3 clubs, the rest of their clubs in no league.
   Erasing A as well avoided that, but an erased league is not closed by the apply, so it is
   not re-admitted and plays the new season on its old table.
4. **Fix: split.** `fl26join.dll` hooks the mover (`0x141365110`, CALL-style): leagues with no
   table, or whose league below (`+0x7e`) has none, go through `0x141365ed0` first; the rest
   go to the mover. The apply then closes all of them and the builder re-admits them
   (door YES for 11, 49, 60, 81, 98, 100, 109, 110, 144). `fl26seasonend`'s guard passes
   everything when the DLL has set byte `0x14252eef0`, and falls back to erasing otherwise.
5. **Why 49/60 had no table.** They were closed at New Year and `register_all` skipped them as
   "already in a season" because `+0x2fc` (season year) survives the close. The test is now
   `+0x304` bit 8. This is the likely cause of tester issue #1 point 2.
6. **Promote counts.** The mover takes PromoteNumber/DemoteNumber from the static competition
   table (`0x1414fdbc0`, the table `fl26comptab` copies). Appended rows are template copies with
   0/0, so 180..185 were processed and nobody moved. `fl26comptab` now writes 3/3 (3/0 for
   the bottom tiers) and demote 3 for Ligue 2 and Serie B.
7. **Every other pair.** The mover skips a league that already has an OUTPUT entry, so in a
   chain only A<->B, C<->D... run. `fl26chain` now also completes 181->182, 184->185 and
   82->183.

Result (play13): 180<->181<->182 and 183<->184<->185 each exchange 3 up / 3 down, all at 20
clubs, Ligue 2 untouched. Play14 with the 82->183 pair: Serie B sent 1312, 10068, 16920 down
to 183 and took 183's top three, so the whole Italian pyramid below Serie A moves. Open: Ligue 2 (81) has no season table at the rollover, so
Ligue 1 <-> Ligue 2 <-> 180 stays still; 61 (region 20, group 3) is never in the July pass;
11<->49<->60 can only move from next season on, once 49/60 have a table.

## Three open items closed or narrowed (2026-09-25, night)

**Regulation 133 is not a bug.** It is the shipped Scottish Premiership, a split season
(type 6). Read live in `_FL26G39Size`, day 39 of season 2 (`regdump.py 133 134 135 136`,
`calread.py --matches --key N`): 133 itself has no fixtures and never did; the 33 rounds of
six matches all belong to 134 "First Phase", and 135/136 ("Top Six"/"Bottom six") are empty
until the split. The earlier "133 entered without fixtures" came from a `fl26join` list that
still held 133; the parent of a split season is supposed to be empty. Day 123: 135 and 136
hold 6 clubs each, 5 rounds of 3 matches (days 107-142): the split works end to end.

**Super Cup (regulation 7).** In the same world the Super Cup has one fixture, on day 222 of
the first season, so its setup ran through with the new-format Champions/Europa League
(`fl26swiss` enters 4 and 6 after the league phase). `fl26superguard` stays as a net: it logs
nothing when it skips, so its only cost is invisible. The real check is day ~222 of the
second season, the first Super Cup whose clubs come from a finished final.

**Our league 25 moves off 145.** The shipped J1 League (regulation 52) relegates into 145
(`+0x00` of its row). 145 has no row in the shipped regulation file, but the exe's
competition parameter table still has one (the old J2, slot 112), and `mkworld` handed 145 to
our league 25 -- so that league would take Japan's relegated clubs. Decision 2026-09-25: move
ours, leave J1 alone. `mkworld.py` swaps 145 for 190 in place (`MOVED_REG`), so every other
league keeps its id; 190 is above the European phases 186-189. What follows the id:

- fixture-date table (the 256-byte table at the end of the stub at `0x14252e690`): byte 190
  set to 145's value, in the `-fixtures` and `-fixtures-calendar` sets and their lua files
  (only that byte changes; `add190` script, scratchpad);
- id lists: `fl26joindll`, `fl26chain` PROTECT, `fl26comptab` (OUR_IDS, APPEND `{190, 112}`,
  `SHARED_OK[112] = 145`), `fl26swiss.c` OUR_LEAGUES, `fixcensus.py`, `leaguewatch.py`;
- `regidmove.py` now lists rows that still relegate into a moved id (and leaves them).

145 stays in every list, so worlds built earlier keep working unchanged. Test world:
`_FL26G39J190` (copy of `_FL26G39Size`, `regidmove --map 145:190`).

Tested in game the same night: a new Master League in `_FL26G39J190` -- regulation 190 gets
the door's yes, enters the season with all 16 clubs and has 30 dated rounds (`calread`,
`regdump`), and `fl26comptab` gives it row 185 on slot 112. Published as 0418a31.

And the thing the move guards against was never seen: over the New Year and the July rollover
of the long runs, `tiermembers.py` with `FL26_CHAIN=52,145` showed J1 moving no club into
145. The link is real in the data, the mover just does not act on it for J1 in what we played.
The move stays as protection.

**`fl26slotnames` (issue #2).** The rewrite with two hooks first failed to load:
`attempt to call global 'pcall' (a nil value)` -- sider's module environment has no `pcall`,
and it guarded the `ffi.cdef` of `VirtualAlloc` against a clash with `fl26comptab`. Declaring
it under its own name (`fl26slotnames_VirtualAlloc(...) __asm__("VirtualAlloc")`) cannot
clash, so no guard is needed. Checked in game both ways: in the J190 world the seven slots
show their league names in Select Team and Kick Off, and with `{185, 4}` taken out of a
deployed copy of comptab, slot 4 reads "Asia-Oceania" again.

Found on the way: Kick Off draws the same slot list, and slots 4, 5, 6 there are the
Asia-Oceania national teams and the two Classic Teams entries. With comptab our Italy D5, D4,
D3 stand in their place and show our clubs (`fl26clubs`). Documented as a side effect; no
spare slot is left to move them to except 0..2, which are the other national-team regions.

Also seen: in `_FL26G39J190` the emblems of 174, 176 and 179 are stale (QAT, UAE, IND on
England D3, England D4, Romania D2) -- the root was copied from an older world; the names
are right (`regdump` +0x04).

## Team Spirit 99 (public #5) not reproduced (2026-09-25, night)

`_FL26G39TS` = copy of `_FL26G39J190` with players from the PUBLIC `mkplayers.py` (base
`out/base-pesdb`, cap 51729). New ML, Buducnost (Montenegro D1), Team Sheet badge:

    --per 30 (clone of club 100, 30 of 38)   start 31, after R3 63
    --per 23                                 start 33, after R3 61

So the clone squads do not start at 99; the tester's value stays unexplained. Asked on #5
where it was seen, whose club, when, and which --per. The seasonnew with --per 23 crashed
once at 0x84ed4c0 (known, protector) and went through on the retry.

## hdr192 long run, stopped by memory pressure (2026-09-25, 04:15-05:33)

Deep career in `_FL26G39Size` (slot 2, season 2, day 235), `seasonplay.py --days 1100 --slot 2`,
hdr192 loaded as in every run since 2026-09-23. `hdrwatch.py` every 5 minutes:

    day 235 -> 298 -> 364 -> New Year -> 21     header 115 of 192 the whole way
    season slots 200 -> 225, phase tables 304 -> 380 of 597

So this stretch never went past 128 -- the signed-byte question stays open; it needs a
later season, not more days of this one. New Year crossed cleanly.

Two crashes, both not ours by their signature:
- 04:42, day ~302: `0x84ed4c0` (protector code, the known one). Recovery reloaded the day-298
  checkpoint and carried on.
- 05:30, day ~30: `ucrtbase.dll` fail-fast `0xc0000409` at +0xa527e (dump
  `fl26-dumps/FL_2026.exe.5348.dmp`); the callers are all in low engine code
  (0x14009b7d6, 0x140104fcb, ... 0x14149ff1e), the same shape as the archive-reader
  fail-fast seen at start-up and on 21.09.

During the second recovery's load Claude Code reaped the background shells for low memory
(the game climbs to ~3 GB while loading, 15.8 GB total), killing the runner and `padd.py`.
Same cause as the note that seasonload must run in the foreground. Slot 2 now holds the
career at day 21 of the new year (checkpoint 05:16).

## Become a Legend with our world (2026-09-25, 05:40-06:10)

World `_FL26G39Size`, the usual set (`...-upper-mlcopy-fixtures`), all modules as in ML.
Screens in `tools/shots/bal/`.

Walk: main menu `down, right, right` = BAL tile -> New -> General Settings OK -> Original
Player -> nationality (region list, then country) -> Edit Player. The name is mandatory
("No Name Entered."); letter keys type into the name box (VK codes through `drive.press`),
`enter` confirms, and **`esc`, not `z`, leaves the Player Name page**. Then OK -> position
mould -> stats -> **League** list.

- The BAL league list shows **all 39 of our leagues** after the shipped ones (England D3 ...
  Bosnia and Herzegovina D1), with the borrowed emblems. Picking one places the player at a
  club of that league straight away (BiH D1 -> Rudar Prijedor, 10 clubs); no club list.
- Career starts on day 232 (20 Aug). `leaguewatch`: 38 of 38 existing leagues have records,
  **16300** in all (ML on the same world: 16290). 62 has none (does not exist), 190 none
  (this world still uses 145).
- The hub is the ML hub: six tabs, Forward Time menu is `Next` on an ordinary day and
  `To Next Match` / `Skip Match` on a match day (two items, not four). Skip Match simulated
  round 1 (all 5 matches), results and table correct.
- System -> Save writes **`BL00000000`** (45 MB); BAL has its own three slots, the ML files
  are untouched. Game killed and restarted, BAL -> Continue loaded it in seconds: day 238,
  table intact, 38 leagues and 16300 records still there.

Not done: New Year, Europe, season end. `seasonrun.py` refuses to start without the pad
daemon, and `padd.py` was reaped at 05:33 and is not restarted without the user.

## The loose `sider/fl26caps.lua` diff, explained (2026-09-25)

`patchset.py` writes every set it generates to `sider/fl26caps.lua` as well as to
`sider/fl26caps.<set>.lua`. The uncommitted change was the byproduct of the -calendar regen in
fc94e1e: byte-identical to the committed `fl26caps.<...>-calendar.lua`. That regen used the
generator's default player cap, **51729** (the same as the -fixtures set every run uses), so
the 21.09 raise to 61905 and its 17 mode-copy patches are gone from the -calendar set; the
impdata calendar-base site is the one new patch (3504 -> 3505). Nothing in our worlds needs
more than 51729 (see the 30-player squads note). Committed as is.

## Day 49 of the third year: the matchday-results screen with an empty list (2026-09-25)

The "ucrtbase fail-fast at +0xa527e" of the night run was not an engine accident: it came back
at 07:25 on the same day, 49 of year three, after a fresh load (dumps `FL_2026.exe.5348.dmp`,
`.5580.dmp`, identical stacks). Day 49 is the first leg of the Europa and Conference League
knockout play-offs (fl26swiss, regulations 188/189).

- The fail-fast is `abort()` after MSVC's "invalid vector<T> subscript" report at
  **0x140ca2203**, in 0x140ca2060 = slot 0xd8 of **menu::MatchDayResultsBase** (vtable
  0x1427215e0; found by searching the vtables for the function, class name from RTTI). The
  last file read before it was `CmnMatchResultNormalFlow.json`: the screen that follows
  `Skip Match`.
- 0x140ca2060 sets the headline, then takes page [+0xa8] of a vector at +0x90 (32-byte
  entries, each with an item vector of 8-byte records whose +4 is an id looked up through
  0x1414b6a60 -> +0x48). An out-of-range page falls back to entry 0; an **empty vector** has no
  entry 0 and ends the game. 0x140ca21db is the same for an empty item vector.
- Fix: `sider/fl26resultsguard.lua` turns both reports into `jmp 0x140ca2289`, the function's
  own epilogue (al = 1). With it the career went 49 -> 67; both play-offs finished on day 56 and
  filled the rounds of 16 (reg 6 and 187, 16 clubs each).
- Open: why the list is empty for that day. Most likely the screen's builder does not know
  regulations 188/189 (the play-offs are ours); the guard only stops the crash.

## The crash is not the machine: restart, overlay, and one heap signature (2026-09-25/26 night)

Three series of five full-stack season generations (`tools/crashtrial.py full`, rows in
`data/crashtrials.csv`) after the evening where fifteen of nineteen attempts died:

    series 7   fresh boot                              3 pass, 2 x 0x84ed4c0 (mgr-dialog)
    series 8   overlay toggled but still injected      1 pass, 1 x 0x84ed4c0 (stopped)
    series 9   NVIDIA overlay app off (processes gone)  3 pass, cf444ae, 159fc14

`data/pool-run7.csv` logged kernel nonpaged/paged pool and the overlay's private memory every
30 s through series 7: flat (nonpaged 351-384 MB, paged 246-326 MB, overlay 320-352 MB). The
crashes neither need a long-running machine nor leave anything behind in it. With the overlay
app closed, `nvspcap64.dll` and `NvCamera64.dll` are still in the process: the driver loads
them, not the app.

The five dumps of the night (kept in the dump archive of that night) all run through the same
chain -- Lua VM, FoxCore, jemalloc (`14038f23e`, `14038f330`, `14038e482`) -- and differ only in
where the damage is noticed:

    0x1484ed4c0  x3   .impdata store through a wild unaligned pointer (the sky bake, above)
    0x14cf444ae  x1   .impdata read of 0x160948f17, also wild
    0x14159fc14  x1   0xc0000409, fast-fail code 2: a stack cookie

The cookie one names the fault better than the others. The function whose cookie failed is
`0x1403ac9f0`: 0x810 bytes of stack, a 0x800-byte path array of sixteen-byte entries, a walk down
a tree comparing `+0x20/+0x28` keys and following `+0x08/+0x10` links with the colour in bit 0
of `+0x10`. That is jemalloc's red-black tree insert (`rb_gen`), whose path array holds 128
levels -- more than any valid red-black tree over a 64-bit address space can reach. It overran,
so the tree it walked had a cycle or a wild link: **the allocator's own metadata was already
corrupt**. Every one of these crashes is the same heap corruption; the fault address only says
which consumer tripped first.

Earlier trials already had `clean` (no fl26 module, no fl26 root) dying 2 of 2 at 0x1fea5ba.
The overnight run `full clean lean:UIColors --rounds 10` (interleaved, `data/crashtrial-run10.log`)
is the sample size that question needed.

### The game's jemalloc has no fill support (2026-09-26)

`malloc_conf_init` (0x14038e780) dispatches on key length and knows only `abort`, `lg_chunk`,
`dss`, `narenas`, `lg_dirty_mult`, `lg_tcache_max`, `stats_print` and `tcache`. `junk`,
`redzone`, `quarantine`, `zero` fall through to "Invalid conf pair" (printed to stderr, which a
GUI process has not got) and change nothing -- the "Corrupt redzone" string is still in .rdata,
but the code that would use it is compiled out. So no redzone session can catch the heap
corruption on this build; `tools/dbgwrap-junk.cmd` is marked as not working.

What MALLOC_CONF can still do: `tcache:false` sends every free straight to the arena instead
of the per-thread cache, which changes where a stray free or a use-after-free lands.
`tools/dbgwrap-notcache.cmd` launches the game that way. Globals, readable from the live
process: opt_tcache byte 0x143402d73 (1 by default), opt_abort 0x1436dceb1, opt_stats_print
0x1436dcf22.

### Two more hard-coded league lists: slot -> country and region -> country (2026-09-26)

A scan of `.trace` for long runs of `mov dword [stack], small constant` (the shape of the Edit
list at 0x140d1d1cb) finds two more tables written into code, both tiny lookups with 0xffff
for "not listed":

- `0x1414cdda0(slot) -> country`: 29 pairs, e.g. slots 7 and 50 -> 204 (England), 9 and 53 ->
  215 (Italy), 8 and 52 -> 208, 11 and 51 -> 236, ..., 84 -> 124, 99 -> 148, 102 -> 7,
  119/16/17 -> 0xfffe/0xfffd/0xfffc. Its one caller, `0x141558b00(club id)` (33 callers, all
  Master League), returns a club's "league country": the country of the first of 24 slots
  listed at 0x1435097a0 (7 9 11 8 10 12 88 91 96 94 114 105 16 50 52 13 14 15 99 20 122 102
  119 18) whose club list holds the club, and otherwise the club's own country (team record
  +0x418). Our clubs are in none of those slots, so for them it is always +0x418. Slot 84 is
  in the table (-> 124) although the shipped competition table leaves it free; one of our
  leagues sits on it.
- `0x1414cdbe0(region index) -> country`: 25 pairs, 2 -> 204, 3 -> 208, 4 -> 236, 5 -> 215,
  6 -> 228, 7 -> 224, 8 -> 197, 9 -> 230, 10 -> 238, 11 -> 227, 12 -> 203, 13 -> 237,
  14 -> 226, 15 -> 232, 16 -> 146, 17 -> 144, 18 -> 147, 19 -> 148, 20 -> 124, 21 -> 7,
  22..24 -> 0xfffe..0xfffc, 27 -> 190, 28 -> 36. Indexes 1, 25, 26 and everything from 29 up
  give 0xffff. Callers include the scout screen (0x140b460b0: scoutSet, marketValue) and
  season code at 0x141354189 / 0x141357073. Our leagues in regions 29..60 have no country
  here; nothing has been seen to go wrong from it yet, but a transfer or scouting oddity
  limited to our leagues should start from this table.

### And two slot lists stored as data (2026-09-26)

Scanning `.rdata`/`.data` for runs of known slot numbers:

- `0x14267f5b0`, 26 u32 slots (88 105 7 50 8 52 9 53 10 12 91 114 11 51 94 96 16 14 13 122 15
  99 17 102 119 18), walked by `0x140ae35d0` (strings TeamSelect_Home / TeamSelect_Away /
  NationSelect_*): `lea rsi,[0x14267f5b0]` at 0x140ae3ce8, `mov ebp, 0x1a` at 0x140ae3cef, each
  slot handed to 0x140c94290 on the list at [rbx+0xd0]. Most likely the Home/Away team select
  of an exhibition match; not yet seen in game. None of our slots is on it. Widening it needs
  no stub: point the lea at a longer copy near the code and raise the count. That lea is the
  only reference to the array in the code. sider/fl26kickofflist.lua does exactly this
  (2026-09-26; not in sider.ini, not tried in game).
- `0x1427d5920`, 40+ u32 slots, including slots of ours (107 110 112 69 71 75 84 29 68), used
  by `0x140ead990` (callers 0x140c93596 / 0x140c935fb, next to the list builder 0x140c93780).
  It is the display ORDER: 0x140ead990(slot) returns the slot's position among 89 entries, and 89
  for a slot not listed -- which is why headings of ours always sort to the bottom of a list
  (and why seasonnew can pick our last league by pressing down more times than the list is long).

### Every club of ours is Malaysian (2026-09-26, measured live)

The club country the Master League code falls back on (block team record +0x418, see "Two more
hard-coded league lists" above) is, for all 780 clubs of the G39 world, **21 -- Malaysia**. They
are clones of Selangor FC, and the clone never touched the field. The shipped Dinamo Zagreb and
Hajduk Split read 200 (Croatia), Arsenal 204, Juventus 215.

In `Team.bin` the field is 9 bits at bit 562 of the record (byte 0x46, bit 2). Checked against
the live +0x418 of all 1523 clubs: 1523 match, 0 mismatch. A second 9-bit country at bit 521
(byte 0x41, bit 1) agrees for all but 13 clubs and is a secondary country (Wolverhampton 228,
Fulham 208, Rangers 204, Young Boys 89 ...), not the club's own.

Not changed yet. The fix is a world-builder one: write each league's country into its clubs at
bit 562 (the code of a shipped club from that country, or the nationality code Player.bin uses
for it). Effects to expect: the Master League's "league country" of our clubs, which feeds the
scout screen's regions and whatever else calls 0x141558b00 (33 Master League callers).

Tool: `tools/clubnation.py <pesdb dir> [--out Team.bin]` (dry run by default, never writes over
its input). The squads cannot give the country -- they are placeholder clones too, the same 23
nationalities at every club, mostly English -- so it takes the country of the club's LEAGUE:
CompetitionEntry -> Competition.bin +3 region -> country, from the game's 25 region pairs plus
fl26catlist's COUNTRY table. On _FL26G39Size: 602 clubs get a country (32 countries, 204 x48,
208 x60, 215 x60 ...), and only bytes 0x46-0x47 of those records change. The other 178 are
spare clubs the size world no longer puts in any league.

Found on the way: **Hungary (region 29, competition 134) was missing from fl26catlist's COUNTRY
table**, so its Competition Info heading would have been blank. Added `[29] = 212` in the repo
copy (212 is what Ferencvaros TC carries); deployed 2026-09-26 (boot log: 30 regions named), not yet
looked at in game.

Why the country may matter more than a label -- a lead, not measured yet. 0x141355750 is the
Master League's filler picker for a continental competition: it walks the live teams (stride
0x690, cap 0x2ee then a single overflow record), keeps those whose `+0x41c & 0x7f` equals its
second argument, and then -- unless its last byte argument is set -- throws out every club whose
country (+0x418) has a league in the game (0x1413540d0: every regulation of league type
`+0x304 & 0xc0000000 == 0x40000000`, region from `+0x30c >> 7 & 0x3f`, through 0x1414cdbe0).
Target counts by its third argument: 0->24, 1->16, 2->40, 3->28, 4->8, 7->32. 0x141363280
calls it three times with (2, 7), the last time with the country filter off. So the shipped
game fills from clubs of countries it has no league for (Ferencvaros 212, Celtic 232 ...), and
a club of ours reading Malaysia (no league) passes that filter -- but it never gets that far.
`+0x41c & 0x7f` is the club's competition SLOT: a scan of the 183 accesses to +0x41c finds it
compared with slot numbers everywhere (0x45, 0x46, 0x49, 0x4b, 0x16, 0x54, 0x12) and with 0x7b,
the 123 "no slot" sentinel; 0x141365907.. writes it at season time. So the picker only draws
from one slot (2 in the call above), our clubs sit in slots of their own, and the Malaysian
country does not put them in the filler pool. Lead closed. (On a clean run at the title screen
every club reads slot 0: the field is filled later.)

### One more slot switch: 0x14150d4c0 (2026-09-26, static only)

`0x14150d4c0(&team id)` reads the club's slot (+0x41c & 0x7f) and maps it through a jump table
(bytes at 0x14150d5c0, 85 entries, targets at 0x14150d5a8) to a small group number:
2 = slots 0, 7-12, 16, 50-53, 69; 3 = 1, 75; 5 = 2, 3, 13-15, 17, 73; 1 = 4, 18, 70; 4 = 84;
everything else, and any slot above 84, 7. Slot 22 is special-cased first: the club is swapped
for the one behind edit block +0x1789404 and that club's slot is used. Five callers, all UI
(0x140f98b50, 0x140fb1850); the result goes to screen object +0x6d4, which looks like a default
tab choice. Ours that hit it (fl26comptab keys rows by REGULATION id): Mexico D1 (regulation 170)
sits in slot 22 and takes the swap path; England D3 (174, slot 69), Romania D2 (179, slot 73)
and France D3 (180, slot 75) inherit the group their slot had in the shipped game. Cosmetic as far as can be seen -- noted in case a screen opens on the wrong tab
only for those four leagues. Slot 84 (Sweden D1, regulation 111, placed there by fl26comptab) is Mexico's
old slot: it maps to group 4 here and to 124 in 0x1414cdda0, but it is not among the 24 slots
0x141558b00 consults, so Swedish clubs do not become Mexican in the Master League -- only this
UI group follows the old owner. (Our Mexico D1 is on slot 22.)

### Slots 69, 70, 73 and 75 are club pools in the season code -- and three of ours sit on them (2026-09-26, static)

The scan of +0x41c (the club's slot, see above) finds four slot numbers the season code tests
directly. In the shipped competition table none of 69, 73, 75 has a competition (70 is the
shipped competition 32); their club lists are the "Other ..." filler groups fl26clubs names
("Other European Leagues" on 69, "Other Latin American Teams" on 73). fl26comptab put three of our
leagues on exactly those slots (regulation ids): 174 England D3 on 69, 179 Romania D2 on 73, 180
France D3 on 75. (The "Qatar"/"Indonesia" labels in fl26clubs.lua are from an older world.)

- `0x141358bd0` (the UEFA places builder, see "European places go to tier-1 leagues") ends by
  walking a 750-entry team list at block+0x16705a8 and adding the FIRST club whose slot is 69
  and whose 0x141558b00 country differs from r12w -- one filler club for a European field.
  It is only reached when competitions 105 and 107 both exist (0x141358230 asks 0x141590730
  for each, then hands the lists to 0x14135b8e0 as entrants of 105 and 107). Neither is in the
  G39 Competition.bin, so in our world this path does not run and England D3 on slot 69 is safe
  from it. The Club World Cup (competition 1) IS in our world, so the pools below are live.
- `0x14135ad80` collects every club on slot 75; `0x14135b080` every club on slot 73 (or passing
  0x141547fd0) with `+0x420 & 0x1c000000 == 0`; `0x14135a7d0` every club on slot 70 (or passing
  0x1415469f0). `0x14135b7e0` is a fourth pool (0x141353cd0, capped at 4).
- `0x141366200` (Master League only: block+0x1787a9c == 1; from 0x14136738c in the season
  chain) takes the user's league, reads its `+0x300 >> 25 & 0xf` group and runs the four pools
  in an order that depends on it (group 2: b7e0, 75, 73, 70; 3 or 5: 73, 70, b7e0, 75; other:
  b7e0, 70, 73, 75), then hands the result to 0x14135b8e0.

What the pools are FOR: `0x14135b8e0(ctx, competition id, clubs, flag)` (31 callers) sets
a competition's entrants, and all three pool orders call it with competition **1 =
FIFA_CLUB_WORLD_CUP**. So slots 70/73/75 (and the b7e0 pool) are where the Club World Cup finds
its clubs from outside the confederations the game models, in an order set by the user's own
league. What is certain: any club whose slot reads 69, 73 or 75
at that moment is a candidate, and three of our leagues own those slots. It also fits two
things already seen -- regulation 32 (slot 70) being one of the BAD_REG ids that "pulls
Libertadores and Asian clubs into a league's table", and the tester report (issue #7) of FL
clubs in the Copa Libertadores. Next: read +0x41c of our clubs live in a Master League (which
clubs actually carry 69/73/75), and trace 0x14135b8e0. If it holds, the fix is data: move 174,
179 and 180 to slots no season code tests (0, 1, 2 are the only free ones left; or share a slot).

Measured live 2026-09-26 03:18-03:26 (read-only, during crash series 10), club slot `+0x41c & 0x7f`
once a Master League exists (block+0x1787a9c = 1; at the title screen every club reads 0):

- lean round, no clubs of ours (730 teams): slot 69 = 36 clubs (Sparta Prague, APOEL, Young
  Boys, CFR Cluj ... the "Other European" group), 70 = 40 (Al Ain, Buriram, Esteghlal ... Asia),
  73 = 24 (Penarol, Cerro Porteno, LDU Quito, Libertad ... Latin America), 75 = 1 (Wydad).
- full round, G39 world (1224 teams live): slot 69 = 48 clubs, ALL ours (Stockport, Wycombe,
  Leyton Orient, Reading ...); 73 = 57, of which 50 ours (Rijeka, Dinamo Zagreb, Hajduk, Varazdin
  ... -- Croatia D1, regulation 11, whose comptab slot is 28, so the club slot is not simply the
  league's slot); 75 = 20, all ours (France D3 placeholders); 70 = 39 shipped, none ours; 22 = 18
  (Mexico D1), 84 = 16 (Sweden D1); 56 clubs of ours on 123 (none).

So the Club World Cup pools really do hold our clubs: 50 on the Latin American one (73) and 20
on 75, and the shipped filler groups there were largely displaced. Which of our leagues end up on
73 besides Croatia D1, and why, is the next read.

Per league (full round 5, 03:50, same read; regulation id, name -> club slot : clubs):
slot 73 = Croatia D1 (11) 10 + Poland D1 (74) 18 + Romania D2 (179) 22; slot 69 = England D3
(174) 24 + England D4 (176) 24; slot 75 = France D3 (180) 20; slot 123 = France D4 (181), France D5
(182), Czechia D1 (76). Every other league of ours sits on its own fl26comptab slot.

So the club slot is NOT the league's table slot: Croatia D1's row says 28, Poland D1's 74, England
D4's 71, France D4's 76 -- and those clubs read 73, 73, 69 and 123. It matches the per-slot club
lists the game builds at boot, the ones fl26clubs.dll corrects for the Select Team screen (69 was
"Other European Leagues", 73 "Other Latin American Teams", France D4/D5 and Czechia among the
nine broken slots): a Master League club is filed under whichever boot list holds it.
fl26clubs.dll only answers the two list READERS for the menu; the Master League's own copy of
the slot is untouched, and it is that copy the Club World Cup pools read.

Consequence: Croatia D1, Poland D1 and Romania D2 clubs are candidates of the Latin American
Club World Cup pool, France D3 of the slot-75 pool. How the boot lists are built (and why these
leagues land on 69/73) is the next thing to trace -- fixing the list builder, not the reader,
would fix menu and Master League together.

### The per-slot club lists: how they are built, and why they are NOT where the club slot comes from (2026-09-26, 04:00-04:30, static + live read-only)

The paragraph above guessed that a Master League club is filed under whichever boot list holds
it. Reading the lists live says otherwise.

**Layout.** One list object: 123 slots x 0x2ee u32 team ids (id << 14 like everywhere else is
NOT used here, these are plain ids; 0x3ffff pads), u16 counts at +0x5a168. Shipped offset
block+0xd0bd04; the caps set moves it, and the live offset is the disp32 of the patched lea at
0x1414f777e (measured 0x3b20898). Accessors: 0x1414d6290 get(list, slot, idx), 0x1414d62c0
count, 0x1414d6330 set entry (r9 = team id), 0x1414d6360 set count, 0x1414d62e0 clear.
fl26clubs.dll answers get/count for slots 4 5 69 72 73 75 76 77 80.

**Builder 0x1414f6e20** (from the DB load, call at 0x1414f5167):
- Phase A walks Team DB table 0x19 (stride 0x5fc). nibble = `[rec+0x4c] >> 28`, slot =
  table 0x14297d090[nibble] = {0:123, 1:5, 2:69, 3:70, 4:71, 5:72, 6:73, 7:75, 8:123, 9:74};
  a 123 falls back to `+0x50` bit 31 / the country's confederation (0x1414e35c0; conf. 5 ->
  75). Every club of ours has nibble 0 and identical +0x44..+0x50, so phase A files none of
  them. Shipped pool clubs carry nibble 2 (69), 6 (73), 7 (75).
- Phase B walks CompetitionEntry (table 6, 12-byte records, cid byte at +8), sorted. The slot
  of a cid is 0x1414cb030: the first comptab row whose regulation (0x1414cb660 ->
  0x1414bb000) has +0x80 == cid. **A competition's clubs are added only if that slot's list
  is still empty.** Slots 69, 73 and 75 already hold the phase-A pool clubs, so England D3
  (174 -> 69), Romania D2 (179 -> 73) and France D3 (180 -> 75) are left out at boot.
- Aggregate slots are appended afterwards: 76 <- slots 2, 3; 77 <- 5, 6; 78 <- 0..4; 79 <- the
  87 slots of table 0x14297d0e0; 80 <- 78, 77, 79. Our France D4 (76), France D5 (77) and
  Czechia D1 (80) sit on aggregate slots, so their lists are merged junk -- that is the
  "nine broken slots" of fl26clubs, explained.

Live check of the competition -> slot rule (simcomp.py, full round 6): every league of ours
resolves to its own fl26comptab slot. At boot the raw lists are right for Croatia D1 (28) and
Poland D1 (74) and wrong only for 69/73/75 (pool clubs) and 76/77/80 (aggregates).

**Mode entry rewrites 69 and 73.** At 04:12:05 (entering the mode, before the Master League
exists) lists 69 and 73 changed content but not count (36 and 24): 69 became England D3's 24
clubs (72158-72177, 71588-71591) + 12 pads, 73 Romania D2's 22 (72218-72237, 71596-71597) + 2
pads. That is the edit team-list apply: 0x141ef8d40 -> 0x141f14470 -> 0x141f14960, which
writes a category's clubs into a slot without touching the count. The 0x1230-byte category
struct (27 x 32 + 3 x 100 at +0xd80/+0xf10/+0x10a0; table 0x1434f45f0, 30 entries x 0x30,
getter +8, setter +0x10) is built by 0x141eefe50 from the cid -> category table 0x142b9c5d0;
categories 27/28/29 are the Team nibble groups 2/6/3 and are applied to slots 69/73/70. The
replacement-pair vector 0x141f14c80 fills is only freed afterwards (0x141ef91a4). The special
cases for cids 39/40/41 in 0x141ef8d40 only move counts between slots 16/17/18 and 69/73/70.

**But the Master League club slot does not follow the lists.** At Master League creation
(04:14:30) the club slots read 71578 (Croatia D1) 73, 71678 (Poland D1) 73, 72178 (England
D4) 69, 71592 (a club of regulation 176) 69, 72258 (France D4) 123 -- while list 28 holds
Croatia, 74 Poland and 71 England D4, and 73 holds only Romania D2. Nothing at load writes
+0x41c: the Team DB loader 0x1414f5120 sets +0x418 (country) and +0x420/+0x424 bits but never
+0x41c, and every club reads 0 until the Master League exists.

Writers of `+0x41c & 0x7f` in the whole exe (every instruction with disp 0x41c, 2026-09-26):
0x141262300 (the user's own club; one call, 0x14126fed9, in the Master League start
0x14126f7e0), 0x141365110 (the season-end promotion mover, one call 0x141365e83), and the
team copy 0x140b158d0 (23 callers, among them ModeDataCreationThread 0x141269090, which copies
a staged team vector into the live teams). 0x140af3680 and 0x141f11c80 write only bits 7 and
24-27. So the slots our clubs get are already in the staged vector; who fills it (0x1412630c0,
the step just before the thread in 0x141266ab0, is the next candidate) is still open.

Pattern of the wrong slots, from the world (_FL26G39Size) -- competition id, region -> club slot:
Croatia D1 130 / region 11 -> 73; Poland D1 135 / 30 -> 73; Romania D2 167 / 34 -> 73 (its own);
England D3 164 and D4 165 / region 2 -> 69 (D3's); France D3 168 / region 3 -> 75 (its own);
France D4 169 and D5 170 / region 3 -> 123. Italy D3-D5 (171-173, region 5) and the rest keep
their own slots.

### Found: the Master League club slot is a hard-coded remap of the slot lists (0x141263b40, 2026-09-26 04:40)

The writer the +0x41c scan could not see: 0x141266490 (per club, from the staged-world builder
0x14126c640 in the Master League creation thread, run method 0x141267040) copies the team
record into a stack buffer (rsp+0x50, 0x690 bytes) and writes the slot into the copy at
`[rbp+0x36c]` (= buffer+0x41c; rbp = rsp+0x100), so no instruction carries disp 0x41c. The slot
is 123 when the flag at [r9] is set, otherwise the return of **0x141263b40(ctx, &team id)**:

1. For every slot 0..122 and every entry of that slot's club list (the per-slot lists above,
   count included, so pads and stale entries count) equal to the club id, push a value:
   - slots 26, 27, 28, 67, 74 -> **73**; slot 30 -> **70**; slot 71 -> **69**;
   - slot 16 -> 69 and 17 -> 73, unless block+0x1789466 is set (then themselves);
   - slots 76..80 (the aggregates) -> nothing;
   - every other slot -> itself.
   (Switch at 0x141263c0c: byte index table 0x141264208 for slots 16..80, targets 0x1412641e8.)
2. Nothing pushed -> 123. A 123 among them -> 123 (0x14125fe50 find). Otherwise the FIRST value
   that is 69, 70 or 73 wins; failing that, the first value (the lowest slot).

So the shipped game treats slots 26/27/28/67/74 as sub-groups of the Latin American "others"
pool (73), 30 of the Asian one (70) and 71 of the European one (69), and the pool slots win
over a club's own league slot. Every wrong slot measured tonight follows:

| league (reg id) | comptab slot | club slot | why |
|---|---|---|---|
| Croatia D1 (11) | 28 | 73 | 28 -> 73 |
| Poland D1 (74) | 74 | 73 | 74 -> 73 |
| England D4 (176) | 71 | 69 | 71 -> 69 |
| England D3 (174) | 69 | 69 | pool slot itself |
| Romania D2 (179) | 73 | 73 | pool slot itself |
| France D3 (180) | 75 | 75 | its own slot, a Club World Cup pool |
| France D4 (181), D5 (182), Czechia D1 (76) | 76, 77, 80 | 123 | aggregates push nothing |

Fix options (not applied; the user decides):
- Data: move our leagues off every slot the rule or the pools touch -- 16, 17, 26, 27, 28, 30,
  67, 69, 70, 71, 73, 74, 75, 76..80. Nine leagues are on them and only slots 0..3 are still free,
  so data alone needs slot sharing (or more slots past the 123 sentinel,
  docs/competition-slot-ceiling.md).
- Code: point the switch bytes of slots 28, 71, 74, 76, 77, 80 at the default case (slot ->
  itself). Slots 71, 74, 76, 77, 80 have no shipped competition. 28 is id 11's shipped row, so
  what it does for the shipped game needs checking first. That still leaves 69/73/75, which are
  pools by their own number, so England D3, Romania D2 and France D3 would have to move either
  way.

**Applied and measured (2026-09-26, 901a12d, live 10:02).** Both halves, in fl26clubs:
`fl26clubs.lua` sets the switch bytes of slots 28, 71 and 74 to the default case's byte (7,
checked against slot 18's byte first, and each old byte checked before it is written), and
`fl26clubs.dll` no longer answers slots 69/73/75 with our clubs when the caller is 0x141263b40
(return addresses 0x1263bdb, 0x1263bfe, 0x12640cf), so England D3, Romania D2 and France D3 get
123 there like France D4/D5 and Czechia always had. The Select Team screen still gets our clubs
on those slots. A new Master League (full set, seasonmake attempt 2; attempt 1 died at
0x84ed4c0 as usual), read at the hub: switch bytes 28/71/74 = 7/7/7; our clubs on 69/70/73/75:
**0** (before: 48 on 69, 50 on 73, 20 on 75); Croatia D1 on 28 (10), Poland D1 on 74 (18),
England D4 on 71 (24), 122 on 123 (56 before + 24 + 22 + 20). The slot is written into the
save when the Master League is created, so only new careers get it. Not yet seen in game: the
Club World Cup and Libertadores entrants of a season played on from here.

### The compiled UEFA access list named other worlds' leagues (2026-09-26, public issue #8)

A tester's report (issue #8) had clubs of two new leagues, FL0036 and FL0025, in the Europa
League. fl26swiss.dll fills all three league phases from its access list, and that list was
compiled with the G39 world's regulation ids: 11 Croatia, 49 Slovenia, 60 Serbia and so on.
Those are not fixed ids -- the public world builder hands the free ids 11, 49, 60, ... to
whatever new leagues come first, so a public world got Croatia's, Slovenia's and Serbia's
European places for leagues that have nothing to do with them (11 champion -> Europa League,
49 champion -> Conference League, 60 champion -> Europa League, runners-up to the Conference
League).

Fixed in 4a55ae8: the compiled list keeps only the shipped leagues (regulations 17-22, 50, 117,
118, 134, 147, 155 -- the game's own ids, the same in every world), and without a list from the
loader Europe is rebuilt only in a world with added leagues (regulation 11 exists), as before.
The G39 world's full 108-entry list moved into `sider/fl26swiss.lua` as `ACCESS`, so this world
plays exactly as before. The public repo gets the compiled-list half only (local commit 691ecc6,
not pushed): its fl26swiss is older and has no `ACCESS` override; there the docs say to add
one's own leagues to the C list and rebuild.

### fl26editlist tried in game: 2 of 32 headings appear (2026-09-26, 11:00-11:40)

Loaded after fl26clubs with the full set; the boot line listed 32 slots (28 49 42 74 80 61 62
64 66 81-87 68 107-113 22 29 43 71 72 75 76 77) and the stub went in at 0x15e800000. Edit >
Teams and Edit > Players > Edit Player > Select Team show the same list (the whole list read
page by page): the shipped headings, England D3, Sweden D1, Romania D2, Mexico D1, Italy D5-D3
and "Other". **Sweden D1 (84) and Mexico D1 (22) are new** -- the stub's calls work for them --
the other thirty do not appear. Serbia and Bosnia (40/41, conditional) were not in the list
this time either.

Why not, so far:
- The per-slot club lists are full for all of them (read live: 28 -> 10 clubs, 49 -> 10,
  42 -> 12, 74 -> 18, 61/62 -> 12, 107 -> 12, 71 -> 24), and 0x141518610 reads exactly those
  lists through the two readers, so it is not an empty slot.
- 0x140c93780 keeps only the clubs that are also on the filter vector its caller passes
  (built by 0x14104ed30 from the screen's source object, minus teams with +0x424 bit 3 when
  [r13+0xb1]), and adds the heading (0x140c934f0) only if some club is left. A second build
  passed an empty vector instead (an empty filter means "no filter", 0x140c938c6): still only
  Mexico and Sweden, and "Other" disappeared -- consistent with our clubs now sitting under
  headings the screen does not draw, and "Other" (the leftover group) going empty. So the
  headings are probably added and then not drawn; the drawing side is the next place to read.
  The display-order table 0x1427d5920 is not the gate (28, 42, 71, 107 are in it and still
  missing; 84 and 22 are in it too).
- The empty-filter build was reverted (it loses "Other"); the committed module is the first
  build. sider.ini is back to its state before the test (fl26editlist not loaded).

### fl26editlist: the real cause, and all 32 headings in game (2026-09-26, 11:30)

The section above hooked the wrong screen. 0x140d1d010 (thirty hard-coded slots, then 40/41,
27, 67) is a method of OnlineMyClubTeamSelect (vtable 0x14274c358), not of the Edit screens
(MenuEditCmnTeamSelectBase, vtable 0x14278b898); Sweden and Mexico showed up because they
already sit on shipped slots of the Edit list (84, 22), not because of the stub.

How it was found: a scratch probe hooked the prologues of 0x140c93780 (add heading for slot)
and 0x140c934f0 (insert heading), logging each slot and the caller's caller into a page read
from outside. Edit > Teams asked exactly 39 slots, all through 0x140c93240 called from
0x140bfcb10, fed by **0x141ee70a0**: clear the vector, call **0x141ee68f0** (thirty unrolled
push_backs of slots 7, 50, 8, 52, 9, 53, 10, 11, 51, 12, 88, 91, 94, 96, 114, 105, 16, 69, 13,
122, 14, 15, 99, 17, 84, 73, 102, 119, 18, 22, 30, 70), then 0x141ee70d0 (push 0..6), then a
jump into 0x141ee67d0 (not touched). Eleven call sites use 0x141ee68f0, seven through
0x141ee70a0 (Teams 0x140bfcb3e, Players 0x140c05b06, and 0x140c07f5e, 0x140c0b84e,
0x140c2d6f8, 0x140c393cd, 0x140c48ce6), four directly (0x140c11bff, 0x140c1da4e, 0x140c256ae,
0x140c2d6ff).

Fix (sider/fl26editlist.lua, rewritten): the epilogue of 0x141ee68f0 at 0x141ee7086 (`mov rbx,
[rsp+0x38]`, 5 bytes) jumps to a stub that push_backs our 32 missing slots with the game's own
push_back 0x14047be40, replays the instruction and jumps back to 0x141ee708b. Checked first:
the hook bytes, the first slot move at 0x141ee690d, and that 0x141ee7081 calls 0x14047be40.

In game (full set, fl26comptab + fl26clubs loaded first): Edit > Teams and Edit > Players >
Edit Player > Select Team both build 71 headings plus "Other" (probe: 71 asked, 72 inserted,
the last 257). All 32 of ours are drawn (England D4, France D3-D5, Albania, Serbia, Bosnia,
Hungary, Czechia, Iran, Slovenia, Poland, Slovakia, Austria, Romania D1, Bulgaria,
Switzerland, Ukraine, Norway, Ireland, N. Macedonia, Montenegro, Uruguay, Paraguay, Ecuador,
Venezuela, ...). Transfer opens Venezuela D1 with clubs and squads; Managers lists our
leagues too (the manager names are the placeholder our world uses, not a module issue).

"Other" is not the leftover group: it is pseudo-slot 257 (0x101), filled by 0x140cbb7a0 from a
fixed table of six special teams at 0x14272a630 (0x3fff3, 0x3fff1, 0x3fff4, 0x3fff5, 0x3fff6,
0x3fff9; the 1 and 9 ones conditional) and inserted after the slot loop. It is still there
with the module on; it only moves: 0x140c934f0 sorts by 0x140ead990 and our slots rank after
it, so "Other" now sits after France D5 / Italy D3, in front of the last block of our leagues,
instead of at the very end. The earlier "Other disappeared" was the list not scrolled to the
right place (and a probe whose log is cumulative and caps at 256 entries).

Status: fl26editlist enabled in sider.ini (probe removed). Not yet run through a Master League
season with it on; the only thing it changes is what 0x141ee68f0 returns.

### fl26kickofflist is not needed for Kick Off > Local Match (2026-09-26)

Tried in game in three runs, full set each time: (1) fl26editlist + fl26kickofflist, (2) only
fl26kickofflist, (3) neither. In all three Kick Off > Local Match > Home/Away shows the same
list, with every league of ours (England D3/D4, France D3-D5, Italy D3-D5, Albania ...
Montenegro D1; no "Other" heading on this screen). So that screen does not take its headings
from the 26 slots at 0x14267f5b0 alone -- whatever builds it already sees our leagues -- and
the screen that 0x140ae35d0 serves is still unidentified (not Local Match; UEFA EURO, Random
Selection and Versus not checked). fl26kickofflist stays out of sider.ini (commented, with a
note); nothing in the list it widens is known to be missing on any screen.

### Every club of ours had the same manager, "Jorge Jesus" -- fixed with a Coach.bin (2026-09-26)

Seen in Edit > Managers once fl26editlist showed our leagues: every club of Bulgaria D1 (and of
every other added league) lists "Jorge Jesus". Cause: a club names its manager in the FIRST
dword of its Team.bin record (+0x00) -- Arsenal 102109 = Mikel Arteta, Juventus 1195 = Igor
Tudor, Selangor 100046 = Bob Bradley; all 743 shipped clubs point at a Coach.bin record. mkteams
calls +0x00 "a second id of some other kind" and gives each new club a fresh value, so the G39
world's 780 clubs point at 266247..267026, and the world has no Coach.bin: none of them exists.
The game then makes a manager up for each, a copy of Coach.bin's first record (id 2, Jorge Jesus).
(modscan/modremap say the manager is at Team +0x54; that is wrong -- +0x54 reads 15 for 729 of the
743 shipped clubs.)

Coach.bin: 100-byte records, 961 shipped (743 employed, 218 free, ids 2..266246). +0 id, +4 a
packed dword whose low 9 bits are the nationality (same codes as the club country: 215 Italy --
Ancelotti; 236 Spain -- Guardiola, Arteta, Xabi Alonso), bits 9..15 unknown, 16..31 zero, and
+0x08 and +0x36 the name twice, 46 bytes each. Bits 9..15 are NOT the age (corrected the same
day): Jorge Jesus reads 40, Guardiola 52, Arteta 41, Yasen Petrov 25; shipped values run 15..52.
So the record carries no age at all, and 780 managers cloned from one template do not share a
birthday the game could retire them all on.

Fix: `tools/mkcoaches.py <world pesdb> --coach <shipped Coach.bin> --out <world>/Coach.bin`
writes the shipped table plus one record per new club whose manager id is missing -- that id,
the name "FL M%04d" by the club's position (FL 0031 -> FL M0031), the nationality of the club's
league (clubnation's lookup; 178 clubs of spare/no-country leagues keep the template's), the
rest cloned from the last free shipped coach. Written into _FL26G39Size: 961 -> 1741 records.
In game: Edit > Managers > Bulgaria D1 lists FL M0201..FL M0216; the live block still holds
teams 1523, coaches 1544 (teams + 21, as before -- the loader keeps employed coaches plus 21
free ones, so the count did not grow); a Kick Off Buducnost v Petrovac (Montenegro D1) reaches
the pre-match screen. EDIT00000000 did not hide the change. Not yet through a Master League
season. Rollback: delete the world's Coach.bin.

Done the same day: modscan/modremap's T_COACH is +0x00 (private f090923). Public (local commit
98e0643, not pushed): a self-contained tools/mkcoaches.py that takes the nationality from the
club's own country bits (bit 562) instead of clubnation, and mkworld.py writes Coach.bin itself
when the base folder has one. Checked on a scratch 3-league world: 803 clubs, 1021 coaches, no
club's manager missing. Our G39 world's clubs still carry country 21 (clubnation not applied),
which is why the private tool, not the public one, was run on it.

### Which screens fl26editlist reaches: only Edit's team pickers (2026-09-26, static)

The 11 call sites of the slot list 0x141ee68f0 (seven through 0x141ee70a0), with the strings
their functions and callers use: Transfer (TransferBeforeTeamSelect, DefaultAgreement),
Managers (MenuEditCoachInfo, list_manager), the Teams / Players pickers (0x140bfcb10, selector,
setName), Search (0x140c2d6a0), a DialogSelect and a MessageDialog variant, and picture import
(PictureImport1st). Every one is a "pick a club by league" list. Nothing in Competition
Structure or Competitions calls it -- that curated list is built elsewhere (see "A new league is
playable -- the Competition Structure list is not the whole game"), so fl26editlist cannot
change those two screens. Not looked at in game.


## The regulation getter never says "not found" (2026-09-26, issue #9)

`0x1414bb000(blk, id)` walks the regulation table and, when the id is not there, returns a
blank record (`blk + 0xd0b77c` on the stock layout; the same for `0xffff`). It never returns 0.
`fl26clubs.c` already checked the record's own id; `fl26swiss.c` did not, so every
`get_rec(x)` "does this world have x" test passed. The tester's world (issue #9) was built with
mkreshape + mkuecl but without mkeuropo -- which could not have run there anyway, because it
wanted the Conference League to be competition 174 and mkphases gave it 130 in a world without
added leagues. So regulation 188 did not exist, `po_available` said it did, and the Europa
League play-off went into the blank record: `ranks 9-24 of reg 1029 into reg 188 (0 clubs)`,
then the results-screen fail-fast at ucrtbase +0xa527e on the play-off day.

Fixed at the source (public 9c3712f, ported here): `get_rec` returns a record only when its
+0 id is the one asked for; a missing play-off is logged once and the progression is left to
the game; mkeuropo reads the Conference competition from reg 186. In our world every id the DLL
asks for exists, so nothing changes here except the July teardown, which no longer appends ids
that are not in the world. The private DLL is rebuilt from this source but NOT deployed yet
(untested in game).

## A new career drops the league in region 29 (2026-09-26)

Hungary (reg 62, cid 134, region 29) was present at boot and in the main menu (256 live
regulation records, reg 62 among them) and gone from Database > Competition Info in the
career. Watching the live table while `seasonnew` built a career showed the count drop to
240 inside career creation (0x141266ab0): 47, 48 and the eight Custom Cup replicas
1071..8239, 99 (CUSTOM_LEAGUE), 149/150 (Denmark's bottom-round groups), 157/158 (Belgium's
play-off groups), and 62. Every one of those is shipped behaviour except 62. The table that
survives is compacted and sorted by id, then recounted (0x1414bc0a0 at 0x1412671f5).

What survives is the list 0x141264880 builds at [this+0x48]. Custom Cup and Custom League
go through an exclusion list at [this+0x60] (the u16 run 0x30, 0x2f, 0x42f .. 0x202f and
0x63 are pushed into it). Everything else goes through a per-regulation test, and the branch
a normal new career takes uses 0x1412645b0:

    14126464c  mov   eax, [rdi+0x30c]
    141264652  and   eax, 0x1f80               ; the region field
    141264657  je    skip                      ; region 0
    141264659  cmp   eax, 0xe80                ; region 29
    14126465e  je    skip
    141264660  ... [rdi+0x308] bits 23..28: 1..48 keep, 49..53 skip (the sub-phase groups)

Another branch (0x141264b3b, taken when [edit+0x1787a9c] == 1) has the same rule as a mask,
`mov r12d, 0x26000001` + `bt` (regions 0, 25, 26, 29). Patching only the mask first changed
nothing, which is how the real site was found: regions 25 and 26 have dozens of live
regulations after career creation, so the mask branch is not the one used.

Region 29 cannot occur in the stock game, whose parser throws away any region of 29 or
more, so both tests are dead there. With fl26reg64 it can, and Hungary is the only league
of ours in region 29 (30 and 31 survive).

Fix, in `sider/fl26reg64.lua`: `3d800e0000` -> `3d01000000` at 0x141264659 (a value masked
with 0x1f80 is never 1) and `41bc01000026` -> `41bc01000006` at 0x141264b51. Each constant
has one copy in the code section. Checked in game: a new career keeps 241 regulations and
62 is among them. Only careers created after the module is installed get it; an existing
career has already lost the regulation.

## Split seasons: the groups are filled by a generic function the switch never reaches (2026-09-26)

First run of `_FL26Split` (93 total, 194 regular 12 x2, 195/196 groups 6 x2): 194 played all
22 rounds by day 34, then 195 and 196 stayed empty -- no clubs, no dates.

The progression 0x141345cc0 is a switch over ids 2..0xaf (byte table 0x141345f74, jump table
0x141345f48); anything above 175 goes to the default, which does nothing. The Scottish
phases (134-136) and the other shipped splits (147, 148, 152-156, 172, 175) reach case 8 at
0x141345ec0:

    if (fmt(id) == 12) al = 0x141343d70(ctx, id, started);     // fmt = (rec+0x308 >> 23) & 0x3f

0x141343d70 is generic. It takes the finished table of `id` (0x141579b90), asks
0x1414cee10 for the phases that follow -- every row with the same competition key
((rec+0x30c >> 7) & 0x3f) and format 13, 14, 15 in that order -- and hands each group the
next N clubs of the table, N being the group's own club count. Our rows are shaped the same
way (194/195/196 formats 12/13/14 under key 32; 191/192/193 under key 37), so only the call
was missing.

Fix, in `tools/native/fl26swiss.c` `prog_handler`: for the regular phase of a `SPLITS` entry
above 175, call the game's own progression first (the default case, nothing) and then
0x141343d70 with the same three arguments case 8 passes (rcx ctx, dx id, r8 started list).
Checked in game, day-22 save of the first run: day 34 logs `reg 194 -- split regular phase
over on day 34, groups filled by 0x141343d70 -> 1`, and on day 36 195 holds DAC, Podbrezova,
Ruzomberok, Slovan, Spartak Trnava, Michalovce and 196 the other six, each 30 matches in 10
rounds on days 37..142.

Day 72, the second test split: `reg 191 -- split regular phase over on day 72, groups filled
by 0x141343d70 -> 1`, 192 and 193 hold 8 clubs each, 28 matches in 7 rounds on days 79..142.
The clubs follow the table exactly. `tools/splittab.py` dumps the phase table rows in the
order the split handler walks them (+0x318 of the phase table, rows of 0x14, count at
+0x3c0; with hdr192 the tables start at 192 * 0xb4): 191 finished Kudrivka, Rukh, Epitsentr,
LNZ, Karpaty, Zorya, Poltava, Obolon -- the eight in 192 -- with Shakhtar 9th and Dynamo 10th,
so the top group without either is the simulation's table, not a mix-up. 194's top six
(Podbrezova 40 .. DAC 30) are exactly 195.

### The groups start from the regular phase's points -- by key, in 0x14134a540

After the split worked, the groups played from zero, while the Scottish 135 kept every point
of 134 (Celtic 66 after 33 games, 76 after 5 more, with only the five group games in the row's
wins, draws and goals). Adding the points from outside does not hold: the group table is
rebuilt from its own results after every matchday (tried: carried on day 41, gone by day 51,
and the order had been sorted without them).

The game's carry is 0x14134a540(ctx, id), the last call of the table rebuild (0x14134aa33).
It takes the competition key of `id` (0x1415415f0), checks `id` is among the phases that
follow (0x1414cee10), finds the format-12 phase under the key (0x1414ce270), and then
switches on the key number itself:

    14134a66e  sub edi, 8 ; je 0x14134a796     key 8   -- second mode (halving? not yet read)
    14134a677  sub edi, 3 ; je 0x14134a796     key 11
    14134a680  sub edi, 1 ; je 0x14134a68e     key 12  -- full points
    14134a685  cmp edi, 3 ; jne 0x14134a8aa    key 15 (Scotland) -- full points; else none

`fl26swiss` replaces the 14 bytes at 0x14134a680 with a jump to a stub that repeats the key-12
and key-15 tests and then compares with up to eight more keys, filled in at run time from the
live format-12 rows of its `SPLITS` table. Day 36 with it: 195 starts Ruzomberok 40,
Podbrezova 39, Michalovce 37, Slovan 34, Spartak 32, Trencin 31 -- the 194 table's points,
sorted, before a game is played.
Day 74, after four group rounds: Ruzomberok 46 (40 + a win and three draws), and the table
still in points order -- the rebuild keeps the carry. 192 opened with LNZ 52 and Karpaty 50,
the top of 191.

### The groups need the July teardown too (2026-09-26)

Run 8 went from day 144 into the next season. On day 181 the regular phases 194 and 191 were
re-dated with 0 played, but the groups 195/196/192/193 still held last season's fixtures, all
played, on days 37..142. Scotland's 135/136 were off the calendar by then. The reason is the
teardown hook in `fl26join`: it appends our ids to the July list, but those are the ids in its
register list, and the group phases were never in it. They are not registered by us (the split
fills them), so they had no reason to be there. Without the teardown a group keeps +0x2fc on
the old year, and enter_season refuses it when the split comes round again.

`fl26join` now takes a second list through `fl26_join_teardown_extra(ids, n)`. Those ids go on
the July teardown list and are kept out of every other one, but never go into register_all.
The loader passes it from `TD_EXTRA` (empty in the repo copy; the split test uses 192, 193,
195, 196).

Run 9 from day 22: the July teardown listed `... 191 194 192 193 195 196`, and on day 181
all four groups were off the calendar, the same as 135/136. 194 and 191 had new schedules with
0 played. One 0x1484ed4c0 crash on the 180 -> 181 move in the first attempt. The retry from
day 145 went through clean, so the crash was not repeatable.

Second season, same run: day 34 of 2027 the 194 table (Trencin 42, Spartak 40, Michalovce 34,
Zilina 33, Presov 31, Slovan 28 / Kosice 27 ... Podbrezova 24) went into 195 and 196 in that
order with those points and 0 played; day 72 the 191 table (Kudrivka 52 ... Kryvbas 40 / Kolos
39 ... Veres 31) into 192 and 193 the same way. The New Year teardown kept our ids out as before.
The split holds across a season: step 1 of the plan is done.

## Club World Cup at 32: the groups have to be registered (2026-09-27)

`tools/mkcwc.py` reshapes competition 1 into a group stage (reg 1, groups 1025 ... 8193) and a
knockout (reg 200), and fl26swiss replaces the field and draws the groups when the game hands
the Club World Cup its entrants (day 332, rollover task 5). The first runs got the draw right --
reg 1 with 32 clubs, every group with 4 -- and no match at all: zero records for 1, the
groups or 200, and nothing on the calendar.

The reason is in how a group stage gets its fixtures. The door `0x1413ac170` builds for a
league (kind 1) and a knockout (kind 3); for a group master (kind 2) it builds nothing and only
enters it into the season. The groups are built by `register_all 0x141343bf0`, which after the
door for an id asks `0x14150d2b0` for that regulation's kind and, when it is 2, walks the
table and runs the door for every row whose parent field (`+0x76`) names the id. That is how
the Libertadores groups (1033 ...) get theirs when reg 9 comes due on a registration date.

The Club World Cup does not come through there. Task 5 hands the entrants over and the pass's
season builder `0x1413156e0` runs the door for reg 1 alone (the call at `0x141315c06`); the
replica walk is only in `register_all`. With the shipped one-row knockout that was enough.
With a group master it enters an empty shell.

Fix in fl26swiss: right after the draw, the eight group ids are handed to `register_all`.
Measured on the test career from day 295: the draw on day 332, then each group asked for its
dates under its own id (3 records, spread to days 153, 157, 161), and every group had 6 match
records, rounds 0-2, 48 in all. The runtime fields that looked suspicious beforehand were not
the cause: `+0x30c` bit 17 and `+0x308` bits 29-31 differ from the Libertadores rows only
because the Club World Cup groups are played once and not home and away.

A side effect to know about: fl26join appends its ids to every `register_all` call, so this
call carries them too. Ids already in a season are left out, and an id with no regulation in
this world (190 here) is skipped by the door's existence test, so nothing extra entered.

**Measured through a second season (run 6, 2026-09-27).** Same session, season 2: the draw
on day 332 again (32 clubs, eight groups of 4, three dates per group), all 48 group matches
played on days 153-161, the knockout (reg 200) got its 16 records in rounds 46 and 51-54 and
all 16 were played by day 179. The July teardown on day 181 added the 9 regulations back and
left no Club World Cup records behind. Season 1's knockout could not be checked (the records
are cleared at the teardown before the sampler ran); season 2 shows the whole path.

## Issue #10: the play-off "already drawn" a year later (2026-09-27)

Tester report: in seasons 2 and 3 the UEFA league phases ended and no play-off followed (UCL
screen with `%s` and eight empty rows, UEL and UECL stuck on the league phase), while a replay
from an earlier save sometimes worked, and a replay of season 3 from 1 January fixed the UCL
and UEL but never the Conference League.

The season-2 log shows the progression hook answering for all three --
`progression for reg 186 on day 351`, `reg 3 on day 29`, `reg 5 on day 31`, each "handled by
the play-off" -- with none of the tie lines that a real draw writes. `po_start` returned 1 from
its guard against drawing twice: it kept the day the play-off was last drawn and refused
another draw within 60 days after it. The game's day counter is the day of the calendar year,
so in the next season, in the same game session, the same February day (the same December day
for the Conference League) was "0 days after" and nothing was drawn, while the progression was
told it had been handled. A restart of the game cleared the memory -- that is the whole
"intermittent" part. The Conference League could not recover from the 1 January save because
its play-off is drawn in December: that save already had the progression spent.

The access list had the same flaw: the final tables kept at the July teardown were only
replaced when the last capture was more than 60 days old, so a third season in one session
would have drawn its UEFA field from the first season's tables.

Fix in fl26swiss: `abs_day()` counts on across New Year (a drop of more than half a year is a
new year, a jump forward of as much is an older save loaded) and every "N days since" guard
compares it instead of the raw day -- the play-off guard, the kept tables and cup winners, and
the Club World Cup's table read. The loader's tick calls it all year so the count never misses
a New Year. A skipped draw now says so in the log.

A save in which the progression was already spent (the tester's Conference League in
ML0000000C) is not repaired by this; the season has to be replayed from before the league
phase ended.

## Issue #11: flags in Select Team, and where a wrong flag comes from (2026-09-27)

Stagnant09 found the lookup and sent a working hook, tied to their own world. What the list
draws is `0x140c950d0(slot)`: 23 {slot dword, country word} pairs built on the stack, a linear
search, `0xffff` for anything else; `0x140c97429` compares with `0xffff` and skips the flag,
otherwise `0x140e5cc50` loads `flag_%03d.png`. The hook replays the 18-byte prologue and
resumes at `+0x12`; checked with capstone, the stub is right.

* **The flag id is the country id**, and Country.bin (214 rows of 1420 bytes, in
  `data_s2526.cpk`) carries it in bits 10-18 of the first dword. English name at +288, 18
  language columns of 70 bytes from +148 (+708 is the three-letter code). Every id in our
  `fl26catlist` COUNTRY table checks out against it; Hungary is 212, Lithuania 219.
* **The region table `0x1414cdbe0`** ({country, region}, 25 pairs, decoded from the stores):
  2 England, 3 France, 4 Spain, 5 Italy, 6 Portugal, 7 Netherlands, 8 Belgium, 9 Russia,
  **10 Switzerland** (the data puts Greece there), **11 Poland**, 12 Denmark, **13 Sweden,
  14 Norway**, 15 Scotland, 16 Brazil, 17 Argentina, 18 Chile, 19 Colombia, **20 Mexico**,
  21 China, 22/23/24 `0xfffe/0xfffd/0xfffc` (Germany/USA/Japan, "no country"), 27 Turkey,
  **28 Thailand** (the data puts Saudi Arabia there). The tester's copy had 10 and 28 wrong.
* **The Lithuanian league with a Scandinavian flag:** 11, 13, 14 and 20 hold no shipped league,
  so `spreadregions --plan own` hands them out, and the exe still answers its old country for
  them. The tester's world put Hungary and Lithuania on 13/14.
* **The rework:** `fl26comptab` builds the slot table at boot from `ID_COUNTRY` {reg id: flag}
  and the slots it has just installed (no dump, no slot guessing), and hooks only when at least
  one slot is named. `tools/mkflags.py` writes `ID_COUNTRY` and catlist's `COUNTRY` from the
  world (league names guessed against every language in Country.bin, or a `--countries` file),
  overrides 11/13/14/20 (with `0xfffe` when no country is known), leaves shipped regions alone.
  Our world: 38 of 39 guessed, South Korea from `data/flags-countries.txt`.

Seen in game 2026-09-27 03:25 (Kick Off > Local Match > team list, sider.log `flags -- stub at
0x15e200000, 39 slots carry a country`): England D3/D4, France D3-D5, Italy D3-D5, Sweden,
Croatia, South Korea, Albania, Romania D2, Serbia, Bosnia, Hungary, Mexico, Australia, Czechia,
Iran, Slovenia, Poland, Slovakia all with their own flag; shipped entries unchanged (Bundesliga
still none). Public commit fd5e52d is local, waiting for "pushaj".

## Step 3 groundwork: how the Libertadores and the AFC CL find their clubs (2026-09-27, read only)

Read out of the exe and live memory during run 6; nothing changed.

**The rights rows the two competitions own** (table `0x1434f1fa0`, source reg, right type):

| target | rows |
|---|---|
| 3 Libertadores | winners of 31, 59, 68, 160, 161; 29 (Brazil) 1st-4th, 30 (Argentina) 1st-4th, 67 (Chile) 1st, 166 and 167 (region 23, confederation 5) 1st |
| 4 Sudamericana | 29 5th-6th, 30 5th, 67 2nd-3rd, 51 1st; winners of 126, 54 |
| 7 AFC CL | winners of 127, 164, 55; 120 (China) 1st-3rd, 162 1st, 52 (Japan) 1st-3rd |

Everything short of a full field comes from the "other" pools: club slot 73 (Latin America)
and 70 (Asia), the same pools the Club World Cup draws on (see the Master League pools
section). `0x141355c90` tries the rights query and then these fallbacks in turn.

**The confederation code.** `0x1413561f0` builds the candidate leagues from `0x1414ccd10` and
keeps a league whose `+0x300 >> 25 & 0xf` matches the builder's confederation (UEFA 0 -> code
1, CONMEBOL 1 -> 5, AFC 2 -> 2). Live values: 1 Europe, 5 South America (8-10, 29-31, 51, 54,
59, 67, 68, 119, 126, 160, 161, 163, 166-169), 2 Asia (15, 16, 52, 55, 120, 127, 162, 164,
165), 7 club/world (1, 34, 35, 200 and the replicas), 3 and 6 two World Cup qualifiers, 8
special. **Every one of our leagues carries 1**, including the South American ones (139, 140,
143-146 in regions 45-50) and Korea, Australia and Iran (171, 173, 178).

**Why the code is not the lever.** The season-end filter `0x141365c50` also keeps a league
only when its confederation code equals its argument. Recoding our leagues to 5 or 2 would
move them out of the season end that currently runs their promotion and relegation. So
qualifying through the stock machinery means rights rows *and* a code change, and the code
change breaks the chains. That rules it out.

**The chokepoint instead.** `0x14135b8e0(ctx, competition id, clubs, flag)` sets a
competition's entrants and has 31 callers. The AFC builders call it with the id as an
immediate: `edx = 0xf` at `0x14136361e` and `0x141363a5e`. The Libertadores (and every other
target the continental builder serves) is set at `0x141355fe1`, the end of `0x141355c90`:
`0x1413535e0(ctx, target type)` turns the target type into the competition id, and the
gathered list (rights clubs, then the fallbacks) goes to `0x14135b8e0` with it. The
`0x14136042a` call, in `0x14135fef0` and run from the season step for event types 0x13/0x14,
is not it: that one fills the special competitions 103 and 58. A wrapper in fl26swiss
could see the list on its way in, for competitions 8/9 and 15. It would keep the rights clubs
and swap the pool clubs (slots 73/70) for our leagues' qualifiers from an ACCESS-style list.
That is the same shape as the Champions League access, without touching any shipped entry
and without recoding a league.

Not yet read: which of 8 and 9 is handed the list, and when in the season (the Libertadores
follows the calendar year in this world); how many pool clubs a field normally carries.
