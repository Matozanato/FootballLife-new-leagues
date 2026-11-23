--[[
fl26confgroups -- loader for fl26confgroups.dll (FL 2027 only): Select Team and Competition Info
by confederation, then country.

What the player sees. With a big world the league column of Select Team (Master League > New,
Kick Off, Edit) and the category grid of Competition Info are one long list. With the DLL both go
down one level at a time: first one row per confederation -- "+ UEFA (164)", "+ CONMEBOL (31)" ...
in Select Team, "+ UEFA" ... in Competition Info -- and the rows of no confederation (national
teams, the "Other" groups, Classic Teams, the club competitions) where they were. Confirm on a
confederation shows only its countries under a "- UEFA" row; in Select Team Confirm on a country
shows only its leagues under a "- Albania" row (every country is a level of its own, one league or
more), and a league is entered exactly as before. Back, or Confirm on a "- ..." row, goes up one
level; on the top level it is the game's Back. On the right side of Competition Info a
confederation shows its continental cups and the Club World Cup. How it does that is in
tools/native/fl26confgroups.c.

The world file's lines, written by FL Mod Studio's League Builder for FL 2027 only
(leaguebuilder.confgroups_lines):

  confgroups slots=<slot>:<group>,... regions=<region>:<group>,... [countries=<slot>:<country>,...]
             [cups=<group>:<competition id>,...] [heads=<group>:<slot>,...]
             [emblems=<group>:<competition id>,...] [trace=1]
  confnames <country>:<name>|<country>:<name>|...

groups 0 UEFA, 1 CONMEBOL, 2 CONCACAF, 3 AFC, 4 CAF, 5 OFC. `slots` are Select Team's league
slots, `regions` Competition Info's categories, `countries` a slot's country (Country.bin id; a
grouped slot of none is a row of its own in its confederation), `cups` the club competitions on a
confederation's right side in Competition Info, `confnames` the countries' row names. `heads`
(optional) gives a group's row the emblem of that slot instead of none (slot 123); League Info on a
group's row shows its `cups` without the Club World Cup (B402), whatever its slot;
`emblems` (optional) the emblem of competition id (emb_<id>*.png, the confederation's logo Mod
Studio writes into the world) on a group's row instead;
`trace=1` writes what the lists did to modules\fl26confgroups-trace.txt (the first 300 lines), for
a test in game.

No line (a world built before, or FL26), or FL_2026.exe: the module says so and does nothing.
Every vtable entry and every function the DLL calls or hooks is checked byte for byte before
anything is written; one mismatch and nothing is (sider.log: "confgroups: off ...").

Select Team's attack / midfield / defence numbers (FL 2027 only). The game shows no number below
39, so the three numbers of every weak club are 39 / 39 / 39. One byte of the game's code in
memory (the DLL's fl26_confgroups_numbers, explained in fl26confgroups.c) lets a weak line show
its own number, down to 26; a number of 40 or more stays what it was. It is on its own: asked
for in FL_2027.exe before the world's lines are read, so it is there with any world (one
confederation, no line, no world file) and whether or not the lists above went in. Its 25 bytes
are checked first; if they are not the game's, nothing is written and the numbers stay as the
game shows them. sider.log: "confgroups: team numbers: ok -- ..." or "confgroups: team numbers:
off <why>". In FL_2026.exe it is not asked for at all (the DLL is not loaded for it).

Install:
  1. copy fl26confgroups.dll and this file to <game>\SiderAddons\modules\
  2. sider.ini, after lua.module = "fl26squadlist.lua":   lua.module = "fl26confgroups.lua"
  3. start the game; sider.log says "confgroups: team numbers: ok -- ..." and "confgroups: ok -- ..."

Requires sider.ini: luajit.ext.enabled = 1 (global ffi).
--]]

local m = {}

local function load_dll(path)
  local n = ffi.C.fl26confgroups_MultiByteToWideChar(65001, 0, path, -1, nil, 0)
  if n > 0 then
    local w = ffi.new("uint16_t[?]", n)
    ffi.C.fl26confgroups_MultiByteToWideChar(65001, 0, path, -1, w, n)
    local h = ffi.C.fl26confgroups_LoadLibraryW(w)
    if h ~= nil then return h end
  end
  return ffi.C.fl26confgroups_LoadLibraryA(path)
end

-- the world file's confgroups line: { slots = {{s, g}...}, regions = {{r, g}...}, countries = {{s, c}...},
-- cups = {{g, cid}...}, heads = {{g, s}...}, emblems = {{g, cid}...}, trace = bool, names = {{c, name}...} }
local function read_line(dir)
  local f = io.open(dir .. "fl26world.txt", "r")
  if not f then return nil, "no world file" end
  local out, names = nil, {}
  local subs, subnames = {}, {}   -- lab 23/11/2026: folders inside a country (confsub / confsubnames)
  for line in f:lines() do
    local sl = line:match("^%s*confsub%s+slots=([%d:,]+)")
    if sl then for a, b in sl:gmatch("(%d+):(%d+)") do subs[#subs + 1] = { tonumber(a), tonumber(b) } end end
    local sn = line:match("^%s*confsubnames%s+(.*)$")
    if sn then
      for fo, pa, ci, nm in sn:gmatch("(%d+):(%d+):(%d+):([^|]+)") do
        subnames[#subnames + 1] = { tonumber(fo), tonumber(pa), tonumber(ci), (nm:gsub("%s+$", "")) }
      end
    end
    local rest = line:match("^%s*confgroups%s+(.*)$")
    local nl = line:match("^%s*confnames%s+(.*)$")
    if nl then
      for c, nm in nl:gmatch("(%d+):([^|]+)") do names[#names + 1] = { tonumber(c), (nm:gsub("%s+$", "")) } end
    end
    if rest then
      out = { slots = {}, regions = {}, countries = {}, cups = {}, heads = {}, emblems = {}, trace = false }
      for key, list in rest:gmatch("(%a+)=([%d:,]+)") do
        local t = out[key]
        if key == "trace" then
          out.trace = list == "1"
        elseif t then
          for a, b in list:gmatch("(%d+):(%d+)") do t[#t + 1] = { tonumber(a), tonumber(b) } end
        end
      end
    end
  end
  f:close()
  if not out then return nil, "no confgroups line in the world file" end
  out.names = names
  out.subs, out.subnames = subs, subnames
  return out
end

function m.init(ctx)
  if ffi == nil then log("confgroups: off global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[
    void*    fl26confgroups_LoadLibraryA(const char*) __asm__("LoadLibraryA");
    void*    fl26confgroups_LoadLibraryW(const uint16_t*) __asm__("LoadLibraryW");
    int      fl26confgroups_MultiByteToWideChar(unsigned int, unsigned long, const char*, int, uint16_t*, int) __asm__("MultiByteToWideChar");
    void*    fl26confgroups_GetProcAddress(void*, const char*) __asm__("GetProcAddress");
    void*    fl26confgroups_GetModuleHandleA(const char*) __asm__("GetModuleHandleA");
    unsigned long fl26confgroups_GetLastError(void) __asm__("GetLastError");
    uint32_t fl26confgroups_GetModuleFileNameA(void*, char*, uint32_t) __asm__("GetModuleFileNameA");
    typedef int  (*fl26_confgroups_install_t)(uint64_t);
    typedef int  (*fl26_confgroups_log_t)(char*, int);
    typedef void (*fl26_confgroups_set_t)(int, int);
    typedef void (*fl26_confgroups_name_t)(int, const char*);
    typedef void (*fl26_confgroups_fname_t)(int, int, int, const char*);
  ]])
  local sep = string.char(92)
  local dir = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep
  local dllpath = dir .. "fl26confgroups.dll"
  local base = ffi.cast("uint64_t", ffi.C.fl26confgroups_GetModuleHandleA(nil))
  local h
  local function fn(name, ty)
    local p = ffi.C.fl26confgroups_GetProcAddress(h, name)
    return p ~= nil and ffi.cast(ty, p) or nil
  end
  local function drain(getlog)
    local buf = ffi.new("char[2048]")
    getlog(buf, 2048)
    for l in ffi.string(buf):gmatch("[^\n]+") do log(l) end
  end
  -- Select Team's attack / midfield / defence numbers below 39 (fl26_confgroups_numbers): FL 2027
  -- only, and with any world, so before the world's lines are read -- a world of one confederation
  -- has no confgroups line and has weak clubs all the same. FL_2026.exe: nothing is loaded for it.
  local name = ffi.new("char[?]", 1040)
  local n = ffi.C.fl26confgroups_GetModuleFileNameA(nil, name, 1040)
  local exe = ffi.string(name, n):match("([^" .. sep .. "/]+)$") or ""
  if exe:lower() == "fl_2027.exe" then
    h = load_dll(dllpath)
    if h == nil then
      log(string.format("confgroups: team numbers: off LoadLibraryA failed (err %d): %s",
                        tonumber(ffi.C.fl26confgroups_GetLastError()), dllpath))
    else
      local numbers = fn("fl26_confgroups_numbers", "fl26_confgroups_install_t")
      local numlog = fn("fl26_confgroups_log", "fl26_confgroups_log_t")
      if numbers and numlog then
        numbers(base)
        drain(numlog)
      else
        log("confgroups: team numbers: off -- they need a newer fl26confgroups.dll")
      end
    end
  end
  local line, why = read_line(dir)
  if not line then log("confgroups: off " .. why); return end
  if h == nil then h = load_dll(dllpath) end
  if h == nil then
    log(string.format("confgroups: off LoadLibraryA failed (err %d): %s",
                      tonumber(ffi.C.fl26confgroups_GetLastError()), dllpath))
    return
  end
  local install = fn("fl26_confgroups_install", "fl26_confgroups_install_t")
  local getlog = fn("fl26_confgroups_log", "fl26_confgroups_log_t")
  local setslot = fn("fl26_confgroups_slot", "fl26_confgroups_set_t")
  local setreg = fn("fl26_confgroups_region", "fl26_confgroups_set_t")
  local sethead = fn("fl26_confgroups_head", "fl26_confgroups_set_t")
  local settrace = fn("fl26_confgroups_trace", "fl26_confgroups_set_t")
  local setctry = fn("fl26_confgroups_country", "fl26_confgroups_set_t")
  local setcup = fn("fl26_confgroups_cup", "fl26_confgroups_set_t")
  local setname = fn("fl26_confgroups_cname", "fl26_confgroups_name_t")
  if not (install and getlog and setslot and setreg and sethead and settrace and setctry and setcup and setname) then
    log("confgroups: off GetProcAddress failed (an old fl26confgroups.dll?)"); return
  end
  for _, e in ipairs(line.slots) do setslot(e[1], e[2]) end
  for _, e in ipairs(line.regions) do setreg(e[1], e[2]) end
  for _, e in ipairs(line.countries) do setctry(e[1], e[2]) end
  for _, e in ipairs(line.cups) do setcup(e[1], e[2]) end
  for _, e in ipairs(line.names) do setname(e[1], e[2]) end
  for _, e in ipairs(line.heads) do sethead(e[1], e[2]) end
  local setemb = fn("fl26_confgroups_emblem", "fl26_confgroups_set_t")   -- a DLL before 09.11. has none
  if setemb then
    for _, e in ipairs(line.emblems) do setemb(e[1], e[2]) end
  elseif #line.emblems > 0 then
    log("confgroups: the confederations' emblems need a newer fl26confgroups.dll -- the rows keep none")
  end
  local setfold = fn("fl26_confgroups_fold", "fl26_confgroups_set_t")
  local setfname = fn("fl26_confgroups_fname", "fl26_confgroups_fname_t")
  if setfold and setfname then
    for _, e in ipairs(line.subnames) do setfname(e[1], e[2], e[3], e[4]) end
    for _, e in ipairs(line.subs) do setfold(e[1], e[2]) end
    if #line.subs > 0 then log(string.format("confgroups: %d league(s) in %d folder(s)", #line.subs, #line.subnames)) end
  elseif #line.subs > 0 then
    log("confgroups: the folders (confsub) need a newer fl26confgroups.dll -- the leagues stay in their country")
  end
  if line.trace then settrace(1, 0) end
  local status = tonumber(install(base))
  drain(getlog)
  if status ~= 0 and status ~= 1 then log(string.format("confgroups: not installed (%d)", status)) end
end

return m
