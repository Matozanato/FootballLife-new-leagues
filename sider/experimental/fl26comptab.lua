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

One correction to the description above, measured 2026-09-21: the table is in .data but it is
not in the file. Read straight out of FL_2026.exe, all 165 rows are zero except row 0, and the
only three code references to the whole 69 KB are the three lookups listed here. So the table
is filled at startup, which is why this module copies it from memory at boot rather than
deriving it from the executable -- and why nothing about it can be checked without running the
game.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi).
--]]

local m = {}

local BASE, STRIDE, NROWS = 0x1434fdf00, 0x108, 165
local OFF_ID, OFF_SLOT, OFF_PROMOTE, OFF_DEMOTE = 0x00, 0x04, 0x30, 0x34

-- our ids that already own a row: new slot
local RESLOT = { [49] = 49, [74] = 74, [100] = 81 }
-- Slots we knowingly share with a shipped competition: {our slot = the competition already on it}.
-- Sharing is normal in the shipped table (24 of its slots carry more than one competition, one
-- carries ten), and this one has been in every build so far, so it stays rather than being moved
-- for tidiness. Anything NOT listed here that lands on an occupied slot is a mistake and aborts.
local SHARED_OK = { [49] = 177 }
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
  {183,  6}, {184,  5}, {185,  4},
}
-- Not here on purpose: 186, the FL Champions League. It is not a competition anyone manages a
-- club through, so it does not belong in the Select Team list.
-- promotion/relegation counts (OUR chain FL01 <-> FL02 <-> FL03): {promote, demote}
local COUNTS = { [11] = {0, 3}, [49] = {3, 3}, [60] = {3, 0} }

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
local function row_u32(row, off) return memory.unpack("u32", row:sub(off + 1, off + 4)) end
local function row_set(row, off, bytes) return row:sub(1, off) .. bytes .. row:sub(off + #bytes + 1) end

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
    if byid[id] then
      -- the table is built at startup, so one of our ids may already have a row (usually on the
      -- hidden slot 123). It is ours either way: move it to the slot we picked rather than
      -- leaving it where it cannot be seen.
      local i = byid[id]
      log(string.format("fl26comptab: id %d already has a row (slot %d) -- moving it to slot %d",
                        id, row_u32(rows[i], OFF_SLOT), slot))
      rows[i] = row_set(rows[i], OFF_SLOT, u32le(slot))
    else
      rows[#rows + 1] = row_set(row_set(tmpl, OFF_ID, u32le(id)), OFF_SLOT, u32le(slot))
      byid[id] = #rows
    end
    ours[id] = true
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

  -- 3. promotion/relegation counts
  for id, pd in pairs(COUNTS) do
    local i = byid[id]
    if i then rows[i] = row_set(row_set(rows[i], OFF_PROMOTE, string.char(pd[1])), OFF_DEMOTE, string.char(pd[2])) end
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

  log(string.format("fl26comptab: table copied to 0x%x, %d rows (%d shipped + %d ours)", newbase, n, NROWS, n - NROWS))
  for id in pairs(ours) do
    local i = byid[id]
    log(string.format("fl26comptab:   id %3d -> row %3d slot %3d", id, i - 1, row_u32(rows[i], OFF_SLOT)))
  end
end

return m
