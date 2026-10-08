--[[
fl26clubs -- loader for fl26clubs.dll: makes the Select Team screen show OUR clubs in the
nine leagues where the game puts someone else's.

Why: the club list that screen draws belongs to the competition *slot*, not to the
competition. The game builds those 123 lists once at boot, and for nine of our slots it gets
them wrong -- national teams in Italy D5, classic teams in Italy D4, the "Other" filler in
Qatar and Indonesia, nothing at all in Iran, France D3 and Czechia, and foreign extras piled
on top of France D4 and France D5 (three separate causes, two of them never established).

The DLL replaces the two functions that READ those lists and, for the slots named below only,
answers from the league's own regulation record instead -- the same clubs the season itself
plays with. Nothing is written: the game's stored lists stay exactly as it built them, and
every slot not named here behaves exactly as before. If a regulation cannot be read yet, that
slot falls back to the game's own answer, so a league can never come out emptier than today.

SLOTS below is {slot, regulation id}. The slot of each of our leagues is printed by
fl26comptab at boot ("id N -> row R slot S") -- read it from there, never guess it.

Log: the DLL keeps a small text log; this loader drains it into sider.log every so often and
on F10, which also prints how many answers we served.

The Master League club slot (2026-09-26): when a Master League is created, 0x141263b40 gives
every club a slot by finding it in these lists, and on the way remaps some slots by a switch:
26/27/28/67/74 become 73, 71 becomes 69, 30 becomes 70 -- the "other clubs" pools the season
code fills the Club World Cup from. Croatia D1 (28), Poland D1 (74) and England D4 (71) sit on
three of those, so their clubs went into the pools. REMAP_OWN below points those three switch
entries at the switch's default case (the slot stays itself); none of them carries a shipped
league in our world. And for that one function the DLL no longer answers 69/73/75 with our
clubs, so England D3, Romania D2 and France D3 no longer land in the pools either (their clubs
get no slot, 123, like France D4/D5 and Czechia have always had). See docs/known-issues.md,
"Fixed along the way" (2026-09-26, issue #8).

The world file. When SiderAddons\modules\fl26world.txt exists (written by FL26 Mod Studio's
League Builder), SLOTS and REMAP_OWN below are ignored and built from the file: every league
whose slot= is one the game fills with a list of its own (0..5, 69, 72, 73, 75, 76, 77, 80) is
served from its regulation, and every league on a slot the switch sends into a pool (26, 27,
28, 67, 71, 74) gets that switch entry pointed at the default case. If no league of the world
sits on a served slot, the DLL is not installed. Without the file the built-in lists below
are used, as before.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi). Load after fl26comptab.lua.
--]]

local m = {}

-- {slot, regulation id} -- the nine slots the game fills wrongly
local SLOTS = {
  -- 2026-09-28: slots 4 and 5 (Italy D5/D4 until now) are left to the national teams and the
  -- classic teams again (GitHub #26); fl26comptab no longer puts a league there
  { 69, 174 },   -- Qatar      (was: "Other European Leagues" filler)
  { 72, 178 },   -- Iran       (was: 3 foreign clubs)
  { 73, 179 },   -- Indonesia  (was: "Other Latin American Teams" filler)
  { 75, 180 },   -- France D3  (was: 1 foreign club)
  { 76, 181 },   -- France D4  (ours, plus 22 foreign clubs)
  { 77, 182 },   -- France D5  (ours, plus classic teams and Italy D3)
  { 80,  76 },   -- Czechia    (was: empty)
}

-- 0x141263b40's switch: one byte per slot 16..80 at 0x141264208 picks the case. {slot, byte it
-- must hold now}; each is set to the byte slot 18 holds (the default case: slot -> itself).
local SWITCH_BYTES = 0x141264208
local SWITCH_FIRST = 16
local REMAP_OWN = {
  { 28, 3 },   -- Croatia D1 (id 11 keeps the exe's row on 28): was -> 73
  { 71, 5 },   -- England D4: was -> 69
  { 74, 3 },   -- Poland D1: was -> 73
}

-- The world file: modules\fl26world.txt, written by FL26 Mod Studio's League Builder.
-- One table per league -- id, then whatever the line gives: cid, region, country, slot, tier,
-- above, promote, demote, clubs, legs (numbers), name (text) -- in file order. nil when
-- there is no file: the module then keeps the built-in lists above. Second result: the team
-- ids of the "nopool" lines -- clubs the game already had that now play in a league of ours
-- (Mod Studio 0.1.4); the DLL leaves them out of the other-clubs pools 69/70/73/75.
local function read_world(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  if not f then return nil end
  local leagues, nopool = {}, {}
  for line in f:lines() do
    local np = line:match("^%s*nopool%s+([%d%s]+)$")
    if np then
      for t in np:gmatch("%d+") do nopool[#nopool + 1] = tonumber(t) end
    end
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
  return leagues, nopool
end

-- From the world file. SERVED: the slots the game fills with lists of its own (national teams,
-- classic teams, "other clubs" fillers, empty) -- a league on one of them needs its club list
-- answered from its regulation. POOL_CASE: the slots the club-slot switch sends into an
-- "other clubs" pool, with the switch byte each holds; a league there is pointed at the
-- default case. Both are facts about the executable; which slots the world uses is not.
local SERVED = { [0] = true, [1] = true, [2] = true, [3] = true,
                 [69] = true, [72] = true, [73] = true, [75] = true, [76] = true, [77] = true, [80] = true }
local POOL_CASE = { [26] = 3, [27] = 3, [28] = 3, [67] = 3, [74] = 3, [71] = 5 }
local function from_world(world)
  local slots, remap = {}, {}
  for _, L in ipairs(world) do
    if L.slot and SERVED[L.slot] then slots[#slots + 1] = { L.slot, L.id } end
    if L.slot and POOL_CASE[L.slot] then remap[#remap + 1] = { L.slot, POOL_CASE[L.slot] } end
  end
  return slots, remap
end

local function remap_own()
  local default = memory.read(SWITCH_BYTES + 18 - SWITCH_FIRST, 1):byte()
  if default ~= 7 then
    log(string.format("fl26clubs: club-slot switch default byte is %d, expected 7 -- switch left alone", default))
    return
  end
  local done = {}
  for _, r in ipairs(REMAP_OWN) do
    local va = SWITCH_BYTES + r[1] - SWITCH_FIRST
    local b = memory.read(va, 1):byte()
    if b == default then
      done[#done + 1] = r[1] .. "(already)"
    elseif b ~= r[2] then
      log(string.format("fl26clubs: club-slot switch byte for slot %d is %d, expected %d -- left alone", r[1], b, r[2]))
    else
      memory.write(va, string.char(default))
      done[#done + 1] = tostring(r[1])
    end
  end
  log("fl26clubs: Master League club slot keeps its own league for slot(s) " .. table.concat(done, " "))
end

local dll_log, dll_stats, dll_pool, logbuf, statbuf, cfg
local ticks = 0

local function drain(reason)
  if not dll_log then return end
  local n = tonumber(dll_log(logbuf, 4096))
  if n > 0 then
    for line in ffi.string(logbuf, n):gmatch("[^\n]+") do log("fl26clubs: " .. line) end
  end
  if reason then
    dll_stats(statbuf)
    log(string.format("fl26clubs: %s -- lists served %d, clubs handed out %d, rebuilds %d, left to the game %d, pool lists filtered %d",
                      reason, tonumber(statbuf[0]), tonumber(statbuf[1]), tonumber(statbuf[2]), tonumber(statbuf[3]),
                      dll_pool and tonumber(dll_pool()) or -1))
  end
end

function m.make_key(ctx, filename)
  ticks = ticks + 1
  if ticks % 32 == 0 then drain(nil) end
  return nil
end

function m.key_down(ctx, vkey)
  if vkey == 0x79 then drain("F10 report") end      -- F10
end

function m.init(ctx)
  if ffi == nil then log("fl26clubs: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[
    void*    LoadLibraryA(const char*);
    void*    GetProcAddress(void*, const char*);
    void*    GetModuleHandleA(const char*);
    unsigned long GetLastError(void);
    typedef struct { uint16_t slot, reg; } fl26_clubs_cfg_t;
    typedef int  (*fl26_clubs_install_t)(uint64_t, const fl26_clubs_cfg_t*, int);
    typedef int  (*fl26_clubs_log_t)(char*, int);
    typedef void (*fl26_clubs_stats_t)(uint32_t*);
    typedef uint32_t (*fl26_clubs_pool_t)(void);
    typedef int  (*fl26_clubs_keep_out_t)(const uint32_t*, int);
  ]])
  local world, nopool = read_world(ctx)
  nopool = nopool or {}
  if world then
    SLOTS, REMAP_OWN = from_world(world)
    log(string.format("fl26clubs: world file -- %d leagues, %d on slots the game fills itself, %d on pool slots",
                      #world, #SLOTS, #REMAP_OWN))
  end
  remap_own()

  local sep = string.char(92)
  local dllpath = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26clubs.dll"
  local h = ffi.C.LoadLibraryA(dllpath)
  if h == nil then
    log(string.format("fl26clubs: LoadLibraryA failed (err %d): %s", tonumber(ffi.C.GetLastError()), dllpath)); return
  end
  local pi = ffi.C.GetProcAddress(h, "fl26_clubs_install")
  local pl = ffi.C.GetProcAddress(h, "fl26_clubs_log")
  local ps = ffi.C.GetProcAddress(h, "fl26_clubs_stats")
  if pi == nil or pl == nil or ps == nil then log("fl26clubs: GetProcAddress failed"); return end
  local install = ffi.cast("fl26_clubs_install_t", pi)
  dll_log   = ffi.cast("fl26_clubs_log_t", pl)
  dll_stats = ffi.cast("fl26_clubs_stats_t", ps)
  logbuf, statbuf = ffi.new("char[4096]"), ffi.new("uint32_t[4]")
  local pp = ffi.C.GetProcAddress(h, "fl26_clubs_pool_calls")
  if pp ~= nil then dll_pool = ffi.cast("fl26_clubs_pool_t", pp) end

  local kept = 0
  if #nopool > 0 then
    local pk = ffi.C.GetProcAddress(h, "fl26_clubs_keep_out")
    if pk == nil then
      log("fl26clubs: this fl26clubs.dll is older than the world (no fl26_clubs_keep_out): " .. #nopool ..
          " club(s) of the game in our leagues may still show under the other clubs -- install the modules again")
    else
      local arr = ffi.new("uint32_t[?]", #nopool)
      for i, t in ipairs(nopool) do arr[i - 1] = t end
      kept = tonumber(ffi.cast("fl26_clubs_keep_out_t", pk)(arr, #nopool))
    end
  end
  -- with no slot and no kept club the readers are still replaced: the pool slots then only get
  -- the stale-count fix (an Edit list longer than the boot one, see fl26clubs.c keep_build)
  cfg = ffi.new("fl26_clubs_cfg_t[?]", math.max(#SLOTS, 1))
  for i, s in ipairs(SLOTS) do
    cfg[i - 1].slot, cfg[i - 1].reg = s[1], s[2]
  end

  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(install(base, cfg, #SLOTS))
  if status == 0 then
    local parts = {}
    for _, s in ipairs(SLOTS) do parts[#parts + 1] = string.format("%d<-%d", s[1], s[2]) end
    log("fl26clubs: live -- " .. #SLOTS .. " slots served from our own regulations: " ..
        table.concat(parts, " ") .. (kept > 0 and (", " .. kept .. " club(s) of the game kept out of the pools") or "") ..
        " (F10 = report)")
    ctx.register("livecpk_make_key", m.make_key)
    ctx.register("key_down", m.key_down)
    drain(nil)
  else
    local msg = ({ [2] = "count-reader signature mismatch", [3] = "get-reader signature mismatch",
                   [4] = "VirtualProtect failed on the count reader",
                   [5] = "VirtualProtect failed on the get reader",
                   [6] = "list-setter signature mismatch",
                   [7] = "VirtualProtect failed on the list setter",
                   [9] = "bad slot list" })[status] or "unknown"
    log("fl26clubs: install FAILED (status " .. status .. ") -- " .. msg .. ". The game is unmodified.")
  end
end

return m
