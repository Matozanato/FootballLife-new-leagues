--[[
fl26slotnames -- stop seven of our leagues from borrowing a shipped section name.

Measured in a running game on 2026-09-21. The Select Team list showed "Other European
Leagues" where Qatar D1 should be, "Other Clubs (Africa)" where France D3 should be,
"Classic Teams" for the two lower Italian divisions, and so on -- while Sweden D1, on a
neighbouring row of the same table, read correctly. Reading the live competition parameter
table settled why: every one of our appended rows carries 0xffffffff in the name field
(+0x38), so the name cannot be coming from the row. It comes from the slot.

0x140ea08e0 is the helper that turns a competition slot into a display name. It is a plain
switch on the slot: values above 0x4b fall straight to the default, and of the 76 below it
only twelve have a case of their own --

     0 Europe          1 Africa      2 North & Central America   3 South America
     4 Asia-Oceania    5 Classic Teams   6 Classic Teams
    69 Other European Leagues      70 Other Clubs (Asia)      71 Other
    73 Other Latin American Teams  75 Other Clubs (Africa)

-- and every other slot takes the default, which leaves the string empty. The caller then
checks for the empty string (0x140ea0a0e) and falls back to the competition's own name.
That fallback is the whole reason Sweden D1 on slot 84 reads right, and it is what this
module hands the other seven.

The switch is a two-level jump table: a byte per slot at 0x140ea0b3c picks one of twelve
case offsets at 0x140ea0b0c, and case 11 is the default. So blanking a slot's name is one
byte -- point its entry at case 11.

Seven slots are patched: 4, 5, 6, 69, 71, 73 and 75. Slots 0, 1, 2 and 3 are left alone
(nothing of ours is on them), and so is 70, which still carries the two shipped competitions
it always did.

2026-09-25, after GitHub issue #2: freeing a slot is only right when a competition is
actually on it. The same slots also carry shipped categories (Classic Teams, Asian national
teams, other European and Latin American clubs), and a world that does not build the league
this module expected on a slot was left with a blank heading. So a freed slot now falls back
twice: first to the name of a live competition on it, as before, and when there is none,
back to the heading the slot always had. Two small hooks in 0x140ea08e0 do that:

  0x140ea0a37  remember the slot just before the fallback looks for a competition on it;
  0x140ea0af7  on the way out, if the name is still empty and the slot is one of these
               seven, ask the game for the slot's original text (0x1414969e0 with the text
               id its own case uses).

The two stubs live in a page this module allocates within rel32 reach of the code, so no
shared code cave is involved.

What this does NOT fix: rows of ours that were inherited from a shipped competition and
still hold that competition's label in +0x38. Those are a row, not a slot, and fl26comptab
clears them.

The world file. When SiderAddons\modules\fl26world.txt exists (written by FL26 Mod Studio's
League Builder), only the slots of the seven that a league of the world actually sits on
(its slot=) are freed; the others keep their shipped heading, and when none is used the
module writes nothing at all. Without the file all seven are freed, as before.

Load order does not matter; this module touches no address any other module touches.
Needs luajit.ext.enabled = 1 in sider.ini (the global ffi), like fl26comptab.

Install:
  1. copy to <game>\SiderAddons\modules\fl26slotnames.lua
  2. sider.ini, in the [modules] list:   lua.module = "fl26slotnames.lua"
--]]

local m = {}

local BYTE_TABLE = 0x140ea0b3c   -- one byte per slot, 0x4c entries, value = case index
local DEFAULT    = 11            -- the case that leaves the name empty

-- {slot, the case byte it must currently hold, what that case says today, its text id}
local SLOTS = {
  {  4, 4,  "Asia-Oceania",               0x660081 },
  {  5, 5,  "Classic Teams",              0x6600f7 },
  {  6, 5,  "Classic Teams",              0x6600f7 },
  { 69, 6,  "Other European Leagues",     0x6600d2 },
  { 71, 8,  "Other",                      0x660093 },
  { 73, 9,  "Other Latin American Teams", 0x6600d3 },
  { 75, 10, "Other Clubs (Africa)",       0x66010f },
}

-- The world file: modules\fl26world.txt, written by FL26 Mod Studio's League Builder.
-- One table per league -- id, then whatever the line gives: cid, region, country, slot, tier,
-- above, promote, demote, clubs, legs (numbers), name (text) -- in file order. nil when
-- there is no file: the module then keeps the built-in list above.
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

-- With a world file only the slots a league of the world sits on lose their borrowed heading;
-- the rest keep it, so a small world does not blank "Classic Teams" for nothing.
local function world_slots(world)
  local used, kept = {}, {}
  for _, L in ipairs(world) do if L.slot then used[L.slot] = true end end
  for _, s in ipairs(SLOTS) do if used[s[1]] then kept[#kept + 1] = s end end
  return kept
end

-- B427 (11.11.2026, pop1806: "u srpskoj ligi stoji bedz od J-lige") -- Kick Off between two clubs
-- of a league whose competition id is past 255 (FL 2027 worlds).
--
-- SmokePatch's lib\CommonLib.lua tells its scoreboard, referee, adboard and sleeve badge modules
-- which league a Kick Off match is of: it reads CompetitionEntry.bin (12 bytes a row: club u32 at
-- +0, competition id at +8) into teams_in_playable_leagues_map[competition id] and answers
-- tid_same_league(home, away) from it. It reads the competition id as ONE byte. A league of the
-- world with id 553 (its high byte is at +0x0b of the row) is read as 41, the J.League: the 16
-- clubs of Srpska liga Istok stood in the J.League's list, and a Kick Off between two of them wore
-- the J.League's sleeve badge and scoreboard. In GigaPack 43 of 198 such leagues fell on a league
-- of the game this way; the other 155 were in no list at all, so their Kick Off was a plain
-- exhibition (Mod Studio's line in CommonLib's playable list names 553, which a byte never is).
--
-- Here, from our side and without touching SmokePatch's file: the same file is read with the whole
-- id, the clubs that were read into a league they are not in are taken out of its list, and each
-- league of the world past 255 gets a list of its own under its full id, with the league's
-- tournament id (the `league <id>` of the world file: its first regulation). CommonLib fills its
-- lists again whenever the game reads the file again, so this is done again after every read.
local KO = { chunks = {}, raw = nil, dirty = false, world = nil }

-- cl: CommonLib's table; bytes: CompetitionEntry.bin unpacked; world: the world file's leagues.
-- Returns clubs taken out of lists they were wrongly in, lists made, and one example for the log.
local function ko_apply(cl, bytes, world)
  local wide, real = {}, {}
  for o = 1, #bytes - 11, 12 do
    local b0, b1, b2, b3 = bytes:byte(o, o + 3)
    local team = b0 + b1 * 256 + b2 * 65536 + b3 * 16777216
    local lo, hi = bytes:byte(o + 8), bytes:byte(o + 11)
    if hi > 0 then
      local cid = lo + hi * 256
      local t = wide[cid]
      if not t then t = { list = {}, has = {} }; wide[cid] = t end
      if not t.has[team] then t.has[team] = true; t.list[#t.list + 1] = team end
    else
      local t = real[lo]
      if not t then t = {}; real[lo] = t end
      t[team] = true
    end
  end
  local out, example = 0, nil
  for cid, t in pairs(wide) do
    local low = cid % 256
    local list = cl.teams_in_playable_leagues_map[low]
    if type(list) == "table" then
      local keep = real[low] or {}
      for i = #list, 1, -1 do
        if t.has[list[i]] and not keep[list[i]] then
          table.remove(list, i)
          out = out + 1
          example = example or string.format("competition %d had been read as %d", cid, low)
        end
      end
    end
  end
  local made = 0
  for _, L in ipairs(world or {}) do
    local t = L.cid and L.cid > 255 and wide[L.cid]
    if t then
      local list = {}
      for i, team in ipairs(t.list) do list[i] = team end
      cl.teams_in_playable_leagues_map[L.cid] = list
      cl.compID_to_tournamentID_map[L.cid] = L.id
      if type(cl.tournamentID_to_compID_map) == "table" then cl.tournamentID_to_compID_map[L.id] = L.cid end
      made = made + 1
    end
  end
  return out, made, example
end

local function ko_fix(ctx)
  KO.dirty = false
  local cl = ctx.common_lib
  if not (cl and cl.try_unzlib and cl.teams_in_playable_leagues_map and cl.compID_to_tournamentID_map) then
    if not KO.said then
      KO.said = true
      log("fl26slotnames: Kick Off -- no CommonLib (lib\\CommonLib.lua) in this game, nothing to set right")
    end
    return
  end
  -- (sider's module env has no pcall: nothing here may raise. The file was read whole, the lists
  -- are tables -- looked at just above and below -- and ko_apply only reads and writes them)
  if type(KO.raw) ~= "string" or #KO.raw < 12 then
    log("fl26slotnames: Kick Off -- CompetitionEntry.bin came empty, CommonLib's lists left as they are")
    return
  end
  local bytes, err = cl.try_unzlib(KO.raw)
  if type(bytes) ~= "string" or (err and err ~= "ERR_NOT_ZLIBBED") then
    log("fl26slotnames: Kick Off -- CompetitionEntry.bin not unpacked (" .. tostring(err) .. "), CommonLib's lists left as they are")
    return
  end
  if type(cl.teams_in_playable_leagues_map) ~= "table" or type(cl.compID_to_tournamentID_map) ~= "table" then
    log("fl26slotnames: Kick Off -- CommonLib's lists are not tables in this game, left as they are")
    return
  end
  local out, made, example = ko_apply(cl, bytes, KO.world)
  KO.times = (KO.times or 0) + 1
  if KO.times <= 3 then
    log(string.format("fl26slotnames: Kick Off -- %d league(s) of the world past competition id 255 given to CommonLib "
                      .. "under their own id; %d club(s) taken out of leagues of the game they had been read into%s",
                      made, out, example and (" (" .. example .. ")") or ""))
  end
end

local function ko_read(ctx, filename, addr, len, total_size, offset)
  if not filename:lower():match("common\\etc\\pesdb\\competitionentry%d?%.bin") then return end
  if offset == 0 then KO.chunks = {} end
  KO.chunks[#KO.chunks + 1] = memory.read(addr, len)
  if offset + len >= total_size then
    KO.raw = table.concat(KO.chunks)
    KO.chunks = {}
    KO.dirty = true      -- CommonLib reads the same chunk after us (it is loaded later): set right at the next event
  end
end

local function ko_make_key(ctx, filename)
  if KO.dirty then ko_fix(ctx) end
end

local function ko_set_teams(ctx, home, away)
  if KO.dirty then ko_fix(ctx) end
end

local function ko_init(ctx, world)
  local n = 0
  for _, L in ipairs(world or {}) do if L.cid and L.cid > 255 then n = n + 1 end end
  if n == 0 then return end           -- FL 2026, or a world with no competition id past 255: nothing to do
  KO.world = world
  ctx.register("livecpk_read", ko_read)
  ctx.register("livecpk_make_key", ko_make_key)
  ctx.register("set_teams", ko_set_teams)
  log(string.format("fl26slotnames: Kick Off -- %d league(s) of the world have a competition id past 255; "
                    .. "CommonLib's league lists are set right after it reads CompetitionEntry.bin", n))
end

local HOOK_SLOT     = 0x140ea0a37        -- mov ecx, ebp; call 0x1414ce170 (slot -> its competitions)
local HOOK_SLOT_OLD = "8bcde832d76200"
local HOOK_OUT      = 0x140ea0af7        -- mov rbx, [rsp+0x50] (the epilogue)
local HOOK_OUT_OLD  = "488b5c2450"
local SLOTREGS      = 0x1414ce170
local SETTEXT       = 0x1414969e0

local function hex(s) return (s:gsub(".", function(c) return string.format("%02x", c:byte()) end)) end
local function u32(v)
  v = v % 0x100000000
  return string.char(v % 256, math.floor(v / 256) % 256, math.floor(v / 65536) % 256,
                     math.floor(v / 16777216) % 256)
end
local function u64(v) return u32(v % 0x100000000) .. u32(math.floor(v / 0x100000000)) end
local function rel(next_ip, to)
  local d = to - next_ip
  if d >= 0x80000000 or d < -0x80000000 then return nil end
  return u32(d)
end
local function b(...) return string.char(...) end

-- The page: +0x00 the remembered slot, +0x20 stub A, +0x60 stub B, +0x100 slot -> text id.
-- Returns nil when C is too far from the code for a rel32 jump.
local function build(C)
  local A, B, T = C + 0x20, C + 0x60, C + 0x100
  local a = b(0x89, 0x2d) .. u32(C - (A + 6))          -- mov [rip->slot], ebp
         .. b(0x89, 0xe9)                               -- mov ecx, ebp
         .. b(0x48, 0xb8) .. u64(SLOTREGS)              -- mov rax, 0x1414ce170
         .. b(0xff, 0xd0)                               -- call rax
  local back = rel(A + #a + 5, HOOK_SLOT + 7)
  if not back then return nil end
  a = a .. b(0xe9) .. back                              -- jmp 0x140ea0a3e

  local s = b(0x48, 0x83, 0x7f, 0x10, 0x00)            --  0 cmp qword [rdi+0x10], 0
         .. b(0x75, 0x2b)                               --  5 jne done
         .. b(0x8b, 0x05) .. u32(C - (B + 13))          --  7 mov eax, [rip->slot]
         .. b(0x83, 0xf8, 0x4b)                         -- 13 cmp eax, 0x4b
         .. b(0x77, 0x20)                               -- 16 ja done
         .. b(0x48, 0x8d, 0x0d) .. u32(T - (B + 25))    -- 18 lea rcx, [rip->table]
         .. b(0x8b, 0x14, 0x81)                         -- 25 mov edx, [rcx+rax*4]
         .. b(0x85, 0xd2)                               -- 28 test edx, edx
         .. b(0x74, 0x12)                               -- 30 je done
         .. b(0x48, 0x89, 0xf9)                         -- 32 mov rcx, rdi
         .. b(0x48, 0xb8) .. u64(SETTEXT)               -- 35 mov rax, 0x1414969e0
         .. b(0xff, 0xd0)                               -- 45 call rax
         .. b(0x48, 0x89, 0xf8)                         -- 47 mov rax, rdi
         .. b(0x48, 0x8b, 0x5c, 0x24, 0x50)             -- 50 done: mov rbx, [rsp+0x50]
  back = rel(B + #s + 5, HOOK_OUT + 5)
  if not back then return nil end
  s = s .. b(0xe9) .. back                              -- 55 jmp 0x140ea0afc

  local ids = {}
  for i = 0, 0x4b do ids[i] = 0 end
  for _, e in ipairs(SLOTS) do ids[e[1]] = e[4] end
  local t = {}
  for i = 0, 0x4b do t[#t + 1] = u32(ids[i]) end

  local body = u32(0xffffffff) .. string.rep("\0", 0x1c) .. a
  body = body .. string.rep("\0", 0x60 - #body) .. s
  body = body .. string.rep("\0", 0x100 - #body) .. table.concat(t)
  return body
end

function m.init(ctx)
  local world = read_world(ctx)
  ko_init(ctx, world)     -- B427, before anything below can stop: it writes nothing into the game
  if world then
    SLOTS = world_slots(world)
    log(string.format("fl26slotnames: world file -- %d leagues, %d of them on a slot with a borrowed heading", #world, #SLOTS))
    if #SLOTS == 0 then return end
  end
  -- verify every byte before writing any of them: a build whose switch is laid out
  -- differently must be left completely alone, not half-patched.
  for _, s in ipairs(SLOTS) do
    local va = BYTE_TABLE + s[1]
    local got = memory.read(va, 1):byte()
    if got ~= s[2] then
      log(string.format("fl26slotnames: slot %d at 0x%x is case %d, expected %d -- nothing "
                        .. "written. This is a different build than the one the switch was "
                        .. "read from.", s[1], va, got, s[2]))
      return
    end
  end
  for _, h in ipairs({ { HOOK_SLOT, HOOK_SLOT_OLD }, { HOOK_OUT, HOOK_OUT_OLD } }) do
    local got = hex(memory.read(h[1], #h[2] / 2))
    if got ~= h[2] then
      log(string.format("fl26slotnames: bytes at 0x%x are %s, expected %s -- nothing written",
                        h[1], got, h[2]))
      return
    end
  end
  if ffi == nil then
    log("fl26slotnames: global ffi is nil (set luajit.ext.enabled = 1) -- nothing written")
    return
  end
  -- declared under a name of our own (the symbol is still kernel32's VirtualAlloc), so it can
  -- never clash with fl26comptab's declaration; sider's module env has no pcall to catch that
  ffi.cdef([[ void* fl26slotnames_VirtualAlloc(void*, size_t, uint32_t, uint32_t)
               __asm__("VirtualAlloc"); ]])

  -- a page of our own for the two stubs, near enough for a rel32 jump both ways
  local C, body
  for _, pref in ipairs({ 0x15e000000, 0x15f000000, 0x161000000, 0x162000000, 0x171000000 }) do
    local p = ffi.C.fl26slotnames_VirtualAlloc(ffi.cast("void*", pref), 0x1000, 0x3000, 0x40)  -- RWX
    if p ~= nil then
      C = tonumber(ffi.cast("uint64_t", p))
      body = build(C)
      if body then break end
    end
  end
  if not body then
    log("fl26slotnames: no page within reach of the code -- nothing written")
    return
  end
  ffi.copy(ffi.cast("void*", C), body, #body)

  -- the stubs exist; now the jumps into them, then the slots
  local ja = b(0xe9) .. rel(HOOK_SLOT + 5, C + 0x20) .. b(0x90, 0x90)
  local jb = b(0xe9) .. rel(HOOK_OUT + 5, C + 0x60)
  memory.write(HOOK_SLOT, ja)
  memory.write(HOOK_OUT, jb)
  if memory.read(HOOK_SLOT, #ja) ~= ja or memory.read(HOOK_OUT, #jb) ~= jb then
    log("fl26slotnames: WRITE FAILED at the hooks -- quit and report")
    return
  end
  log(string.format("fl26slotnames: headings fall back to the original text (stubs at 0x%x)", C))

  for _, s in ipairs(SLOTS) do
    local va = BYTE_TABLE + s[1]
    memory.write(va, string.char(DEFAULT))
    if memory.read(va, 1):byte() ~= DEFAULT then
      log(string.format("fl26slotnames: WRITE FAILED at 0x%x (slot %d)", va, s[1]))
      return
    end
    log(string.format("fl26slotnames: slot %d is named after its league, or \"%s\" if it has "
                      .. "none", s[1], s[3]))
  end
  log(string.format("fl26slotnames: %d slots freed", #SLOTS))
end

return m
