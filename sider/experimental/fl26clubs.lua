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

Requires sider.ini: luajit.ext.enabled = 1 (global ffi). Load after fl26comptab.lua.
--]]

local m = {}

-- {slot, regulation id} -- the nine slots the game fills wrongly
local SLOTS = {
  {  4, 185 },   -- Italy D5   (was: national teams)
  {  5, 184 },   -- Italy D4   (was: classic teams)
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
  ]])
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

  cfg = ffi.new("fl26_clubs_cfg_t[?]", #SLOTS)
  for i, s in ipairs(SLOTS) do
    cfg[i - 1].slot, cfg[i - 1].reg = s[1], s[2]
  end

  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(install(base, cfg, #SLOTS))
  if status == 0 then
    local parts = {}
    for _, s in ipairs(SLOTS) do parts[#parts + 1] = string.format("%d<-%d", s[1], s[2]) end
    log("fl26clubs: live -- " .. #SLOTS .. " slots served from our own regulations: " ..
        table.concat(parts, " ") .. " (F10 = report)")
    ctx.register("livecpk_make_key", m.make_key)
    ctx.register("key_down", m.key_down)
    drain(nil)
  else
    local msg = ({ [2] = "count-reader signature mismatch", [3] = "get-reader signature mismatch",
                   [4] = "VirtualProtect failed on the count reader",
                   [5] = "VirtualProtect failed on the get reader",
                   [9] = "bad slot list" })[status] or "unknown"
    log("fl26clubs: install FAILED (status " .. status .. ") -- " .. msg .. ". The game is unmodified.")
  end
end

return m
