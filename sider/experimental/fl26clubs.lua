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

local dll_log, dll_stats, logbuf, statbuf, cfg
local ticks = 0

local function drain(reason)
  if not dll_log then return end
  local n = tonumber(dll_log(logbuf, 4096))
  if n > 0 then
    for line in ffi.string(logbuf, n):gmatch("[^\n]+") do log("fl26clubs: " .. line) end
  end
  if reason then
    dll_stats(statbuf)
    log(string.format("fl26clubs: %s -- lists served %d, clubs handed out %d, rebuilds %d, left to the game %d",
                      reason, tonumber(statbuf[0]), tonumber(statbuf[1]), tonumber(statbuf[2]), tonumber(statbuf[3])))
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
  ]])

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
