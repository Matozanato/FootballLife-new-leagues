--[[
fl26comptab -- make OUR added leagues selectable in "Select Team" (Master League / Kick Off).

Why: the Select Team competition list is not built from the regulation data. It walks a
static per-competition parameter table compiled into FL_2026.exe (.data 0x1434fdf00,
165 rows x 0x108, one row per PES-era regulation id, ids up to 177), keeps one entry per
"internal competition slot" (row +0x04, values 0..122; 123 = none) and takes the display
name / club list from that slot. So an added regulation id is selectable only if
  (a) a row for that id exists in the table, and
  (b) its slot is not 123 and is not shared with (or hard-named as) another competition.
Our 39 leagues: 15 ids happen to own clean rows (11,60,61,62,93,94,96,98,138..146); 49 and 74
sit in slot 123 (hidden); 76 and 100 sit in slots 27/67 whose names are hard-coded in the UI
("Copa Libertadores 2017" / "Copa Sudamericana 2016"); the other 20 ids have no row at all.
Lookups go through exactly three functions (0x1414fdbc0 by id, 0x1414fdd60 by index,
0x1414fde20 range check) plus a count getter (0x1414fe1e0 -> 0xa5); the table base is an
rip-relative lea in each of them.

What this does, at boot, runtime only (nothing persisted, shipped rows untouched):
  1. allocates a private copy of the table (VirtualAlloc, within rip range of the code),
  2. copies the 165 shipped rows, then re-slots OUR rows 49/74/100 and rebuilds row 76 as a
     league-shaped row, and appends new league-shaped rows for our row-less ids,
     each on a slot that is free in the shipped table AND empty in the live club table,
  3. writes our promotion/relegation counts into the copy (was fl26promote's job),
  4. re-points the three leas at the copy and raises the four count constants.
All code writes are verified against expected bytes first (all-or-nothing).

Slots: the engine has 123 competition slots; the shipped table leaves 27 of them free. As of
21 September this module hands out 20 of those 27, which is every one of our leagues that
lacked a row or sat on the hidden slot 123 -- so all 39 are meant to be selectable now, none
is season-only any more, and seven slots are still spare. Sharing a slot is normal in the
shipped data (24 slots carry more than one competition, one of them carries ten), but nothing
of ours needs to share, so nothing of ours does.

The 123 is a sentinel, not a field width -- the slot field is a dword, and 123 is what
0x1414cb2e0 returns for a competition with no row. Raising it is possible and costed in
docs/competition-slot-ceiling.md, and is not needed for 39 leagues.

Where the displayed name comes from, measured in a running game on 2026-09-21: the row's own
label (+0x38) if it has one, otherwise the slot's hard-coded name if that slot is one of the
twelve that have one, otherwise the competition's name out of the regulation data. Both of the
first two were stealing our names -- twelve rows we inherited still held a shipped label, and
seven of our slots are hard-named. Step 2c below clears the labels; fl26slotnames frees the
seven slots. Neither is needed for a row we built on a slot nobody named, which is why Sweden
D1 on slot 84 read correctly from the first run.

One correction to the description above, measured 2026-09-21: the table is in .data but it is
not in the file. Read straight out of FL_2026.exe, all 165 rows are zero except row 0, and the
only three code references to the whole 69 KB are the three lookups listed here. So the table
is filled at startup, which is why this module copies it from memory at boot rather than
deriving it from the executable -- and why nothing about it can be checked without running the
game.

The world file. When SiderAddons\modules\fl26world.txt exists (written by FL26 Mod Studio's
League Builder), the world's half of the tables below comes from the file instead of the
built-in lists: OUR_IDS, APPEND (every league with slot= goes on that slot -- appended when
the exe has no row for it, moved when it has, left alone when it is already there), COUNTS
(promote=/demote=), SHIPPED_DEMOTE (a league whose above= is a shipped league raises that
league's demote count to its own promote count) and ID_COUNTRY (country=). RESLOT is emptied.
The executable's half stays: RESHAPE (only for ids the world uses), SHARED_OK and the template
row. Without the file the built-in lists are used, as before.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi).
--]]

local m = {}

local BASE, STRIDE, NROWS = 0x1434fdf00, 0x108, 165
local OFF_ID, OFF_SLOT, OFF_PROMOTE, OFF_DEMOTE = 0x00, 0x04, 0x30, 0x34
local OFF_NAME, OFF_SHORT = 0x38, 0x3c
local OFF_SPLIT_TEXT, OFF_INFO_TEXT = 0x44, 0x48   -- League Info lines (split format, "eligibility")
local NO_LABEL = "\255\255\255\255"

-- Every regulation id our world uses (not 186, the FL Champions League, which has no row).
-- Rows we build ourselves are copies of the template and already carry no label; rows we
-- inherited from a shipped competition carry that competition's, and that is what the list
-- then displays -- Slovenia D1 read "PDII League", Croatia/Czechia/Greece all read the same
-- borrowed name. Clearing the field sends the UI to its fallback, which is the competition's
-- own name out of our regulation data (see fl26slotnames for the other half of this).
local OUR_IDS = {
  11, 49, 60, 61, 62, 74, 76, 93, 94, 96, 98, 100, 109, 110, 111, 112, 113, 114, 121,
  138, 139, 140, 143, 144, 145, 146, 170, 171, 173, 174, 176, 178, 179, 180, 181, 182,
  183, 184, 185, 190,
}
-- 145 stays in the list for worlds built before 2026-09-25. It is the shipped J2's id: the
-- exe's table has a row for it (slot 112) and the shipped J1 relegates into it, so a league on
-- 145 takes J1's relegated clubs. mkworld now puts that league on 190 instead.

-- our ids that already own a row: new slot
local RESLOT = { [49] = 49, [74] = 74, [100] = 81 }
-- Slots we knowingly share with a shipped competition: {our slot = the competition already on it}.
-- Sharing is normal in the shipped table (24 of its slots carry more than one competition, one
-- carries ten), and this one has been in every build so far, so it stays rather than being moved
-- for tidiness. Anything NOT listed here that lands on an occupied slot is a mistake and aborts.
local SHARED_OK = { [49] = 177, [112] = 145 }
-- row 76 is cup-shaped (inherited from the Libertadores slot): rebuild it from a league row
local RESHAPE = { [76] = { from = 100, slot = 80 } }
-- our ids with no row: appended as copies of the row of TEMPLATE_ID, on these slots
local TEMPLATE_ID = 61
-- The 27 slots free in the shipped table are 0..6, 22, 29, 43, 68, 69, 71..77, 80..87
-- (Appendix A of docs/competition-param-table-decode.md; 74 goes to our id 74 above, 80 and 81
-- to the two reshaped rows). Every one of our row-less ids can therefore have a slot of its
-- own -- there is no need to share one, and no need to raise the 123-slot ceiling, which is a
-- sentinel rather than a field width (docs/competition-slot-ceiling.md).
-- Added 21 September: the thirteen leagues that had neither a row nor a slot. Slots 0, 1 and 2
-- are deliberately left alone: they are the three most likely to mean something to code that
-- has never had to handle them, and we do not need them.
local APPEND = {
  {109, 82}, {110, 83}, {111, 84}, {112, 85}, {113, 86}, {114, 87}, {121, 68},
  {170, 22}, {171, 29}, {173, 43}, {174, 69}, {176, 71},
  {178, 72}, {179, 73}, {180, 75}, {181, 76}, {182, 77},
  -- 183, 184 and 185 sat on slots 6, 5 and 4 until 28 September; see PROTECTED below
  -- the 25th league: on 190 in worlds built from 2026-09-25 on, on 145 before. It takes 145's
  -- slot, which no live competition holds once the league has left 145.
  {190, 112},
}
-- Not here on purpose: 186, the FL Champions League. It is not a competition anyone manages a
-- club through, so it does not belong in the Select Team list.
-- promotion/relegation counts (OUR chain FL01 <-> FL02 <-> FL03): {promote, demote}
-- These are OUR test world's leagues; put your own ids here.
local COUNTS = {
  -- 11, 49 and 60 are three separate top leagues (Croatia, Slovenia, Serbia), not a chain
  [11] = {0, 0}, [49] = {0, 0}, [60] = {0, 0},
  -- the leagues below Ligue 2 and Serie B: every row this module appends is a copy of a
  -- template and carries 0/0, so without these the mover processed 180..185 and moved nobody
  [180] = {3, 3}, [181] = {3, 3}, [182] = {3, 0},
  [183] = {3, 3}, [184] = {3, 3}, [185] = {3, 0},
}
-- Shipped rows whose relegation count is raised so that a league of ours below them can fill:
-- Ligue 2 (81) and Serie B (82) are bottom tiers in the shipped game and relegate nobody.
-- Only the demote count is written; their promote count stays what it was.
local SHIPPED_DEMOTE = { [81] = 3, [82] = 3 }

-- Flags in the Select Team list: {regulation id = flag id}. tools/mkflags.py writes this from
-- the world's own data (the league's name, or a --countries file) and Country.bin, where the
-- flag id is the country id; an id left out keeps the list's old answer, which is no flag.
-- These are OUR test world's leagues; run mkflags.py --write for your own.
local ID_COUNTRY = {
  [11] = 200,   -- Croatia (Croatia D1)
  [49] = 235,   -- Slovenia (Slovenia D1)
  [60] = 303,   -- Serbia (Serbia D1)
  [61] = 198,   -- Bosnia and Herzegovina (Bosnia and Herzegovina D1)
  [62] = 212,   -- Hungary (Hungary D1)
  [74] = 227,   -- Poland (Poland D1)
  [76] = 202,   -- Czech Republic (Czechia D1)
  [93] = 234,   -- Slovakia (Slovakia D1)
  [94] = 194,   -- Austria (Austria D1)
  [96] = 229,   -- Romania (Romania D1)
  [98] = 199,   -- Bulgaria (Bulgaria D1)
  [100] = 238,   -- Switzerland (Switzerland D1)
  [109] = 239,   -- Ukraine (Ukraine D1)
  [110] = 226,   -- Norway (Norway D1)
  [111] = 237,   -- Sweden (Sweden D1)
  [112] = 214,   -- Ireland (Ireland D1)
  [113] = 221,   -- North Macedonia (North Macedonia D1)
  [114] = 304,   -- Montenegro (Montenegro D1)
  [121] = 191,   -- Albania (Albania D1)
  [138] = 207,   -- Finland (Finland D1)
  [139] = 152,   -- Uruguay (Uruguay D1)
  [140] = 150,   -- Paraguay (Paraguay D1)
  [143] = 151,   -- Peru (Peru D1)
  [144] = 149,   -- Ecuador (Ecuador D1)
  [145] = 145,   -- Bolivia (Bolivia D1)
  [146] = 153,   -- Venezuela (Venezuela D1)
  [170] = 124,   -- Mexico (Mexico D1)
  [171] = 16,    -- Republic of Korea (South Korea D1)
  [173] = 162,   -- Australia (Australia D1)
  [174] = 204,   -- England (England D3)
  [176] = 204,   -- England (England D4)
  [178] = 11,    -- Iran (Iran D1)
  [179] = 229,   -- Romania (Romania D2)
  [180] = 208,   -- France (France D3)
  [181] = 208,   -- France (France D4)
  [182] = 208,   -- France (France D5)
  [183] = 215,   -- Italy (Italy D3)
  [184] = 215,   -- Italy (Italy D4)
  [185] = 215,   -- Italy (Italy D5)
}

-- The world file: modules\fl26world.txt, written by FL26 Mod Studio's League Builder.
-- One table per league -- id, then whatever the line gives: cid, region, country, slot, tier,
-- above, promote, demote, clubs, legs (numbers), name (text) -- in file order. nil when
-- there is no file: the module then keeps the built-in lists above.
local function read_world(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  if not f then return nil end
  local leagues = {}
  for line in f:lines() do
    local id, rest = line:match("^%s*league%s+(%d+)(.*)$")
    if id then
      local L = { id = tonumber(id) }
      local name = rest:match("%sname=(.-)%s*$")
      if name then L.name = name; rest = rest:gsub("%sname=.*$", "") end
      for k, v in rest:gmatch("(%a+)=(%-?%d+)") do L[k] = tonumber(v) end
      leagues[#leagues + 1] = L
    end
  end
  f:close()
  return leagues
end

-- The world file replaces the world's half of the tables above; the executable's half stays:
-- which shipped row is cup-shaped (RESHAPE, used only when that id is in the world), which slot
-- sharing is known to be fine (SHARED_OK), the template row. A league with slot= is put on that
-- slot -- appended when the exe has no row for it, moved when it has -- and one without keeps
-- whatever row and slot the exe gives it. promote=/demote= become its counts; a league whose
-- above= is not in the world raises that shipped league's demote count to its own promote
-- count, as SHIPPED_DEMOTE does for Ligue 2 and Serie B.
-- Slots that look free in the parameter table but are not: the Select Team / Kick Off list keeps
-- the Asia-Oceania national teams and the two Classic Teams entries on 4, 5 and 6, and a league
-- put there takes their place (GitHub #26). A world file written before 28 September may still
-- name them; such a league keeps playing its season, it is only left out of the list.
-- A league on slot=123 (or moved off a protected slot) still gets a row of its own, on the
-- hidden slot: the row carries its promotion/relegation counts (COUNTS), which it needs whether
-- or not it can be picked.
local PROTECTED = { [4] = true, [5] = true, [6] = true }

local function apply_world(world)
  local inworld = {}
  for _, L in ipairs(world) do inworld[L.id] = L end
  OUR_IDS, RESLOT, APPEND, COUNTS, SHIPPED_DEMOTE, ID_COUNTRY = {}, {}, {}, {}, {}, {}
  local reshape = {}
  for id, spec in pairs(RESHAPE) do
    local L = inworld[id]
    if L then reshape[id] = { from = spec.from, slot = (L.slot and L.slot ~= 123) and L.slot or spec.slot } end
  end
  RESHAPE = reshape
  for _, L in ipairs(world) do
    OUR_IDS[#OUR_IDS + 1] = L.id
    if L.slot and PROTECTED[L.slot] then
      log(string.format("fl26comptab: league %d asks for slot %d, which the national teams / Classic "
                        .. "Teams use -- it plays, but is not in the Select Team list", L.id, L.slot))
      APPEND[#APPEND + 1] = { L.id, 123 }
    elseif L.slot and not RESHAPE[L.id] then APPEND[#APPEND + 1] = { L.id, L.slot } end
    if L.promote or L.demote then COUNTS[L.id] = { L.promote or 0, L.demote or 0 } end
    if L.above and not inworld[L.above] then
      SHIPPED_DEMOTE[L.above] = math.max(SHIPPED_DEMOTE[L.above] or 0, L.promote or 3)
    end
    if L.country then ID_COUNTRY[L.id] = L.country end
  end
end

-- code sites: {va, expected bytes (hex)}
local LEAS = {
  { 0x1414fdbda, "4c8d251f030002" },   -- lea r12,[table]  (lookup by id)
  { 0x1414fdd71, "488d0588010002" },   -- lea rax,[table]  (lookup by index)
  { 0x1414fde07, "4c8d35f2000002" },   -- lea r14,[table]  (range check)
}
-- {va, expected bytes, offset of the imm32 inside the instruction}
local COUNT_SITES = {
  { 0x1414fdc4a, "81fea5000000", 2 },  -- cmp esi, 0xa5
  { 0x1414fdd60, "81f9a5000000", 2 },  -- cmp ecx, 0xa5
  { 0x1414fde1b, "41bca5000000", 2 },  -- mov r12d, 0xa5
  { 0x1414fe1e0, "b8a5000000",   1 },  -- mov eax, 0xa5  (count getter)
}

local function u32le(v)
  return string.char(v % 256, math.floor(v / 256) % 256, math.floor(v / 65536) % 256, math.floor(v / 16777216) % 256)
end
local function bin2hex(s) return (s:gsub(".", function(c) return string.format("%02x", c:byte()) end)) end
local function hex2bin(h)
  return (h:gsub("%x%x", function(b) return string.char(tonumber(b, 16)) end))
end
local function rel32(from_next, to)
  local d = to - from_next
  if d >= 0x80000000 or d < -0x80000000 then return nil end
  if d < 0 then d = d + 0x100000000 end
  return u32le(d)
end
local function row_u32(row, off) return memory.unpack("u32", row:sub(off + 1, off + 4)) end
local function row_set(row, off, bytes) return row:sub(1, off) .. bytes .. row:sub(off + #bytes + 1) end

-- The flag next to a league in the Select Team list comes from 0x140c950d0(slot), which
-- builds 23 {slot, country} pairs on the stack and answers 0xffff for any other slot -- so
-- for every slot of ours, and the caller (0x140c97429) then draws no flag. There is no table
-- to extend, so the function is hooked with one of our own, keyed on the slots this module
-- has just handed out. A slot the table leaves at 0xffff falls through to the original code,
-- so the 23 shipped answers do not change. The stub (Stagnant09's, issue #11):
--   0x00 cmp ecx,0x7b ; ja 0x21        slots are 0..123; anything above is not ours
--   0x09 mov eax,ecx ; lea rdx,[tbl]
--   0x12 movzx eax,word [rdx+rax*2]    our country for that slot
--   0x16 cmp ax,-1 ; je 0x21 ; ret     0xffff: not ours, let the engine answer
--   0x21 the engine's own 18 prologue bytes, replayed, then jmp SLOT_FN+0x12
--   0x38 124 u16, one per slot
-- The stub writes nothing to the stack, so the replayed prologue is all the frame the
-- original needs; the rip-relative load at +0x12 still runs where it was compiled.
local SLOT_FN = 0x140c950d0
local SLOT_FN_PROLOGUE = "48895c240855488d6c24a94881ecd0000000"   -- 18 bytes
local SLOT_FN_RESUME = 0x12
local NSLOTS = 124

local function install_flags(slot_country, named)
  local got = bin2hex(memory.read(SLOT_FN, #SLOT_FN_PROLOGUE / 2))
  if got ~= SLOT_FN_PROLOGUE then
    log(string.format("fl26comptab: bytes at 0x%x are %s, expected %s -- no flags",
                      SLOT_FN, got, SLOT_FN_PROLOGUE))
    return
  end
  local stub
  for _, pref in ipairs({ 0x15e200000, 0x15f200000, 0x161200000, 0x171200000 }) do
    local p = ffi.C.VirtualAlloc(ffi.cast("void*", pref), 0x1000, 0x3000, 0x40)  -- PAGE_EXECUTE_READWRITE
    if p ~= nil then stub = tonumber(ffi.cast("uint64_t", p)); break end
  end
  if not stub then log("fl26comptab: VirtualAlloc for the flag stub failed -- no flags"); return end
  local back = rel32(stub + 0x38, SLOT_FN + SLOT_FN_RESUME)
  local into = rel32(SLOT_FN + 5, stub)
  if not (back and into) then log("fl26comptab: flag stub out of jump range -- no flags"); return end
  local code = "\131\249\123" .. "\15\135\24\0\0\0" .. "\137\200" .. "\72\141\21\38\0\0\0"
            .. "\15\183\4\66" .. "\102\61\255\255" .. "\15\132\1\0\0\0" .. "\195"
            .. hex2bin(SLOT_FN_PROLOGUE) .. "\233" .. back
  assert(#code == 0x38, #code)
  local tbl = {}
  for sl = 0, NSLOTS - 1 do
    local c = slot_country[sl] or 0xffff
    tbl[#tbl + 1] = string.char(c % 256, math.floor(c / 256) % 256)
  end
  ffi.copy(ffi.cast("void*", stub), code .. table.concat(tbl))
  memory.write(SLOT_FN, "\233" .. into)
  log(string.format("fl26comptab: flags -- stub at 0x%x, %d slots carry a country", stub, named))
end

-- The Kick Off and Edit team lists sort their headings by 0x140ead990(slot): the slot's place in
-- a fixed list of 89 slots (0x1427d5920), and 89 for a slot not on it, which the list builder
-- (0x140c9359e, its only reader of the constant 0x1427d5754) then appends at the very end --
-- after Classic Teams. Peru on slot 49 sat there (2026-09-28). The world file's kickoff=<slot>
-- says which slot a league of ours follows; the function is rewritten in place to search a
-- list of ours instead: the shipped 89 without our slots, each of ours put back after its
-- slot (and after the leagues already put after that one), and the "not listed" answer and
-- its constant raised to the new length together.
--   mov rdx,<list> ; xor eax,eax ; L: cmp [rdx],ecx ; je R ; inc eax ; add rdx,4
--   cmp eax,<n> ; jb L ; mov eax,<n> ; R: ret                        (35 of its 48 bytes)
local ORDER_FN, ORDER_TBL, ORDER_N, ORDER_UNLISTED = 0x140ead990, 0x1427d5920, 89, 0x1427d5754
local ORDER_FN_BYTES = "33c0488d15877f92010f1f8000000000390a7410ffc04883c20483f85972f1b859000000c3"
local ORDER_SITES = { { ORDER_FN, ORDER_FN_BYTES }, { ORDER_UNLISTED, "59000000" },
                      { 0x140c9359e, "3b05b021b401" } }   -- cmp eax,[0x1427d5754]

local function install_order(slot_after, order)
  local any = false                      -- sider's sandbox has no next()
  for _ in pairs(slot_after) do any = true; break end
  if not any then return end
  for _, s in ipairs(ORDER_SITES) do
    local got = bin2hex(memory.read(s[1], #s[2] / 2))
    if got ~= s[2] then
      log(string.format("fl26comptab: bytes at 0x%x are %s, expected %s -- Kick Off order left as it is", s[1], got, s[2]))
      return
    end
  end
  local list = {}
  for i = 0, ORDER_N - 1 do
    local sl = memory.unpack("u32", memory.read(ORDER_TBL + 4 * i, 4))
    if not slot_after[sl] then list[#list + 1] = sl end
  end
  local function follows(s, a)          -- s was put after a, directly or through leagues of ours
    for _ = 1, 64 do
      s = slot_after[s]
      if s == nil then return false end
      if s == a then return true end
    end
    return false
  end
  -- in the world file's order (the order the Mod Studio shows), so leagues after the same
  -- slot keep it: each goes after the ones already put there
  local pending = {}
  for _, sl in ipairs(order) do pending[#pending + 1] = sl end
  local placed, late = 0, {}
  repeat
    local progress, rest = false, {}
    for _, sl in ipairs(pending) do
      local a, at = slot_after[sl], nil
      for i, v in ipairs(list) do if v == a then at = i; break end end
      if at then
        while list[at + 1] and follows(list[at + 1], a) do at = at + 1 end
        for j = #list, at + 1, -1 do list[j + 1] = list[j] end
        list[at + 1] = sl
        placed, progress = placed + 1, true
      else
        rest[#rest + 1] = sl
      end
    end
    pending = rest
  until not progress or #pending == 0
  for _, sl in ipairs(pending) do list[#list + 1] = sl; late[#late + 1] = tostring(sl) end
  local n = #list
  local buf = ffi.C.VirtualAlloc(nil, 4 * n, 0x3000, 0x04)
  if buf == nil then log("fl26comptab: VirtualAlloc for the Kick Off order failed -- left as it is"); return end
  local t = ffi.cast("uint32_t*", buf)
  for i, v in ipairs(list) do t[i - 1] = v end
  local addr = tonumber(ffi.cast("uint64_t", buf))
  local lo, hi = addr % 0x100000000, math.floor(addr / 0x100000000)
  local code = "\72\186" .. u32le(lo) .. u32le(hi) .. "\49\192" .. "\57\10" .. "\116\18" .. "\255\192"
            .. "\72\131\194\4" .. "\61" .. u32le(n) .. "\114\239" .. "\184" .. u32le(n) .. "\195"
  assert(#code == 35, #code)
  memory.write(ORDER_UNLISTED, u32le(n))
  memory.write(ORDER_FN, code)
  log(string.format("fl26comptab: Kick Off order -- %d slots, %d of ours placed after their league or continent%s",
                    n, placed, #late > 0 and (", " .. table.concat(late, ",") .. " at the end (no such slot)") or ""))
end

local function check_sites(list)
  for _, s in ipairs(list) do
    local n = #s[2] / 2
    local got = bin2hex(memory.read(s[1], n))
    if got ~= s[2] then
      log(string.format("fl26comptab: bytes at 0x%x are %s, expected %s -- aborting", s[1], got, s[2]))
      return false
    end
  end
  return true
end

function m.init(ctx)
  if ffi == nil then log("fl26comptab: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[ void* VirtualAlloc(void*, size_t, uint32_t, uint32_t); ]])

  -- 0. verify every code site before touching anything
  if not (check_sites(LEAS) and check_sites(COUNT_SITES)) then return end

  local world = read_world(ctx)
  if world then
    apply_world(world)
    local own = 0
    for _, a in ipairs(APPEND) do if a[2] ~= 123 then own = own + 1 end end
    log(string.format("fl26comptab: world file -- %d leagues, %d with a slot of their own", #OUR_IDS, own))
  end

  -- 1. read the shipped table, index rows by id
  local rows, byid = {}, {}
  for i = 0, NROWS - 1 do
    local r = memory.read(BASE + i * STRIDE, STRIDE)
    rows[#rows + 1] = r
    local id = row_u32(r, OFF_ID)
    if not byid[id] then byid[id] = i + 1 end
  end
  for id in pairs(RESLOT) do
    if not byid[id] then log("fl26comptab: no row for id " .. id .. " -- aborting"); return end
  end
  if not byid[TEMPLATE_ID] then log("fl26comptab: no template row -- aborting"); return end

  -- 2. re-slot / reshape / append (our ids only)
  for id, slot in pairs(RESLOT) do
    local i = byid[id]; rows[i] = row_set(rows[i], OFF_SLOT, u32le(slot))
  end
  for id, spec in pairs(RESHAPE) do
    local src, i = byid[spec.from], byid[id]
    if not (src and i) then log("fl26comptab: reshape source/target missing for id " .. id .. " -- aborting"); return end
    rows[i] = row_set(row_set(rows[src], OFF_ID, u32le(id)), OFF_SLOT, u32le(spec.slot))
  end
  local tmpl = rows[byid[TEMPLATE_ID]]
  local ours = {}
  for id in pairs(RESLOT) do ours[id] = true end
  for id in pairs(RESHAPE) do ours[id] = true end
  for _, a in ipairs(APPEND) do
    local id, slot = a[1], a[2]
    if byid[id] and row_u32(rows[byid[id]], OFF_SLOT) == slot then
      -- the world file names every league's slot, also the ones the exe already puts there
      -- (a league on a shipped row that already has the slot): nothing to do, and the row
      -- stays the exe's
    elseif byid[id] then
      -- the table is built at startup, so one of our ids may already have a row (usually on the
      -- hidden slot 123). It is ours either way: move it to the slot we picked rather than
      -- leaving it where it cannot be seen.
      local i = byid[id]
      log(string.format("fl26comptab: id %d already has a row (slot %d) -- moving it to slot %d",
                        id, row_u32(rows[i], OFF_SLOT), slot))
      rows[i] = row_set(rows[i], OFF_SLOT, u32le(slot))
      ours[id] = true
    else
      rows[#rows + 1] = row_set(row_set(tmpl, OFF_ID, u32le(id)), OFF_SLOT, u32le(slot))
      byid[id] = #rows
      ours[id] = true
    end
  end
  -- 2b. a slot of ours must not land on a shipped competition. The free-slot list was read
  -- from a table dumped out of a run (Appendix A), and the table is built at startup, so it
  -- can differ from what this run actually has: check it against this run rather than trust it.
  do
    local taken = {}
    for i = 1, #rows do
      local id = row_u32(rows[i], OFF_ID)
      if not ours[id] then
        local sl = row_u32(rows[i], OFF_SLOT)
        if sl ~= 123 then taken[sl] = id end
      end
    end
    local mine = {}
    local clash = false
    for i = 1, #rows do
      local id = row_u32(rows[i], OFF_ID)
      if ours[id] then
        local sl = row_u32(rows[i], OFF_SLOT)
        if sl ~= 123 then
          if taken[sl] and SHARED_OK[sl] == taken[sl] then
            log(string.format("fl26comptab: slot %d shared with competition %d, as intended", sl, taken[sl]))
          elseif taken[sl] then
            log(string.format("fl26comptab: slot %d is already competition %d, not free -- aborting", sl, taken[sl]))
            clash = true
          elseif mine[sl] then
            log(string.format("fl26comptab: slot %d asked for twice, by %d and %d -- aborting", sl, mine[sl], id))
            clash = true
          end
          mine[sl] = id
        end
      end
    end
    if clash then return end
  end

  -- 2c. clear the name label on every row of ours. Measured 2026-09-21: twelve of our rows
  -- were inherited from a shipped competition and still held its label in +0x38, so the list
  -- showed that competition's name instead of ours. 0xffffffff is what the rows we build
  -- ourselves carry, and it is the value the UI treats as "no label of my own".
  -- The same goes for the two League Info lines (+0x44 split format, +0x48 "You can choose to
  -- play in any of the South American based leagues." and the like): a new Asian league on a
  -- South American row showed that text (issue #43). Without a label the line is left out.
  do
    local cleared, texts = 0, 0
    for _, id in ipairs(OUR_IDS) do
      local i = byid[id]
      if i then
        if row_u32(rows[i], OFF_NAME) ~= 0xffffffff then cleared = cleared + 1 end
        if row_u32(rows[i], OFF_SPLIT_TEXT) ~= 0xffffffff or row_u32(rows[i], OFF_INFO_TEXT) ~= 0xffffffff then
          texts = texts + 1
        end
        rows[i] = row_set(row_set(rows[i], OFF_NAME, NO_LABEL), OFF_SHORT, NO_LABEL)
        rows[i] = row_set(row_set(rows[i], OFF_SPLIT_TEXT, NO_LABEL), OFF_INFO_TEXT, NO_LABEL)
      end
    end
    log(string.format("fl26comptab: name labels cleared on %d rows that had borrowed one, "
                      .. "League Info text on %d", cleared, texts))
  end

  -- 3. promotion/relegation counts
  for id, pd in pairs(COUNTS) do
    local i = byid[id]
    if i then rows[i] = row_set(row_set(rows[i], OFF_PROMOTE, string.char(pd[1])), OFF_DEMOTE, string.char(pd[2])) end
  end
  for id, d in pairs(SHIPPED_DEMOTE) do
    local i = byid[id]
    if i then rows[i] = row_set(rows[i], OFF_DEMOTE, string.char(d)) end
  end
  local n = #rows
  if n > 255 then log("fl26comptab: too many rows -- aborting"); return end

  -- 4. allocate the copy within +-2GB of the code, write it
  local body = table.concat(rows)
  local newbase
  for _, pref in ipairs({ 0x15c000000, 0x15d000000, 0x160000000, 0x170000000, 0x180000000 }) do
    local p = ffi.C.VirtualAlloc(ffi.cast("void*", pref), #body, 0x3000, 0x04)  -- MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE
    if p ~= nil then newbase = tonumber(ffi.cast("uint64_t", p)); break end
  end
  if not newbase then log("fl26comptab: VirtualAlloc failed at every preferred address -- aborting"); return end
  ffi.copy(ffi.cast("void*", newbase), body, #body)

  -- 5. re-point the code (disp32 relative to the end of each 7-byte lea), then the counts
  for _, s in ipairs(LEAS) do
    local disp = newbase - (s[1] + 7)
    if disp >= 0x80000000 or disp < -0x80000000 then log("fl26comptab: copy out of rip range -- aborting"); return end
    if disp < 0 then disp = disp + 0x100000000 end
    memory.write(s[1] + 3, u32le(disp))
  end
  for _, s in ipairs(COUNT_SITES) do memory.write(s[1] + s[3], u32le(n)) end

  -- 6. flags: the slot each id of ID_COUNTRY ended up on, read back from the rows just
  -- installed, so the stub follows whatever slots steps 2 and 2b settled on
  do
    local slot_country, named = {}, 0
    for id, c in pairs(ID_COUNTRY) do
      local i = byid[id]
      local sl = i and row_u32(rows[i], OFF_SLOT)
      if not sl or sl >= NSLOTS or sl == 123 then
        log(string.format("fl26comptab: id %d has no slot in the list -- no flag for it", id))
      elseif slot_country[sl] and slot_country[sl] ~= c then
        log(string.format("fl26comptab: slot %d carries two countries (%d, %d) -- keeping %d",
                          sl, slot_country[sl], c, slot_country[sl]))
      elseif not slot_country[sl] then
        slot_country[sl] = c
        named = named + 1
      end
    end
    if named > 0 then install_flags(slot_country, named) end
  end

  -- 7. the Kick Off / Edit list order: each league of ours after the slot its kickoff= names
  if world then
    local slot_after, order = {}, {}
    for _, L in ipairs(world) do
      local i = byid[L.id]
      local sl = i and row_u32(rows[i], OFF_SLOT)
      if L.kickoff and sl and sl < 123 and sl ~= L.kickoff and not slot_after[sl] then
        slot_after[sl] = L.kickoff; order[#order + 1] = sl
      end
    end
    install_order(slot_after, order)
  end

  log(string.format("fl26comptab: table copied to 0x%x, %d rows (%d shipped + %d ours)", newbase, n, NROWS, n - NROWS))
  for id in pairs(ours) do
    local i = byid[id]
    log(string.format("fl26comptab:   id %3d -> row %3d slot %3d", id, i - 1, row_u32(rows[i], OFF_SLOT)))
  end
end

return m
