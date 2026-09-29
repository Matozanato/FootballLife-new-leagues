--[[
fl26joindll -- loader for fl26join.dll, the module that gets the added leagues into a
Master League season.

The problem it solves. A league can exist, show its clubs in every menu, be picked as your
own club -- and never be given a single match. Measured on 2026-09-22 on a world of 41 added
leagues, each a first division standing in a country of its own: 8 entered the season, 33
never did, in any run. Picking a club from one of the 33 also derailed the whole world build
(a season starting in January, 24 countries with a season instead of 55, less than half the
matches) -- no table, no fixtures, and a mid-season review in June.

Why. Competitions enter a season on two occasions. At creation the season builder
0x1413156e0 admits a fixed list of calendar-year competitions. Everything else enters in
play, when the calendar reaches a registration date and register_all 0x141343bf0 is called
with the ids due that day. That list of ids comes from a case table over ids 2..175 compiled
into the exe; it cannot be extended by data, and most free ids in it point at an empty case.
The door every competition goes through, 0x1413ac170, said YES to every one of our ids it
was ever shown. Nothing ever showed them.

What the DLL does. It appends the ids listed below to the vector register_all receives (the
game's ids first, in their order, then ours), leaving out any id whose record already
carries a season year, so a league that entered by another route is never registered twice.
When the season builder asks the door about one of our ids at creation, the DLL answers no
(the builder treats that as a skip) -- the three of our ids that reuse a shipped
calendar-year id would otherwise get two schedules. Result: 39 of the 40 leagues present
were dealt a full 38-round season; the 40th is a split-season format, which is a separate
problem. Nothing is written to any table; the game's own registration then runs exactly as
it does for its own leagues.

What it does not do. It does not invent dates: the fixture dates still come from the
rulebook id, see docs/how-it-works.md.

The season rollover (added 2026-09-23). The game closes last season's competitions in July
and the calendar-year ones at New Year, from a list compiled into the exe, and the added
leagues were never on it: they kept last season's year, their points and matches added up
season on season, and the next registration refused them. The DLL now adds the listed ids to
the July list (and keeps them off the New Year one, since their season runs August to May),
so they close and re-open with the shipped leagues: new year, empty tables, a fresh
schedule. Measured through a July rollover and on past New Year of the next season. Still
not measured: a season created with a shipped club as your team.

The world file. When SiderAddons\modules\fl26world.txt exists (written by FL26 Mod Studio's
League Builder), the module takes its list of league ids from the file's `league` lines
instead of the built-in IDS list below; a world file with no leagues registers nothing.
Without the file it behaves as before. Split-season group phases (the world file's
`split ... groups=` ids, collected in TD_EXTRA) are only put on the July close list, never
registered; this needs an fl26join.dll that exports fl26_join_teardown_extra, and the log says
so when it does not.

The other three hooks only watch: enter_season 0x14158f420 (every id that enters, with the
return address that asked), the builder (the include list it was handed) and the door (for
our ids: its answer, the record's flag, kind and club count, and the caller). None of them
runs any game code -- the record is found by walking the regulation array. Every line is
also appended to fl26join.log in the SiderAddons folder the moment it is written, so a crash
during season creation cannot lose the answer. That file is worth attaching to a report.

The observation ring lives at 0x14252ebe0, 0x208 bytes: a counter, a write index, and 256
slots. It sits above 0x14252e800 and clear of every module that claims padding there: the
nullguards (..0x14252e900), fl26chain's ring (..0x14252ea08), fl26hdr192's trampolines
(..0x14252eb24), and, above this ring, the experimental fl26augseason, fl26superguard and
fl26seasonend (0x14252ee00..0x14252eef0). Do not take cave space without checking all of
sider/*.lua first -- a module that finds its padding occupied refuses its patches and says
so in one line that is easy to miss.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi). Sider's sandbox has no pcall.
Load it after the null guards and before fl26hdr127.lua / fl26hdr192.lua.
--]]

local m = {}

-- The rulebook (regulation) ids of YOUR added leagues: the `regulation` column mkworld.py
-- printed. These are the 39 ids a default mkworld.py run hands out, in order. An id that
-- has no record in your world is harmless (the door refuses it and the log says so); an id
-- of yours that is missing here is a league that may never get a season.
local IDS = { 11, 49, 60, 61, 62, 74, 76, 93, 94, 96, 98, 100, 109, 110, 111, 112, 113, 114,
              121, 138, 139, 140, 143, 144, 145, 146, 170, 171, 173, 174, 176,
              178, 179, 180, 181, 182, 183, 184, 185, 190 }

-- Split-season group phases: closed on the July teardown with the added leagues, never
-- registered (fl26swiss fills them when the regular phase ends). Filled from the world file's
-- split lines (groups=); empty when the world has no split.
local TD_EXTRA = {}

-- The world file: modules\fl26world.txt, written by FL26 Mod Studio's League Builder.
-- One table per league -- id, then whatever the line gives: cid, region, country, slot, tier,
-- above, promote, demote, clubs, legs (numbers), name (text) -- in file order. nil when
-- there is no file: the module then keeps the built-in list above.
local function read_world(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  if not f then return nil end
  local leagues, regular, groups, seasons = {}, {}, {}, {}
  for line in f:lines() do
    -- `season <region> <type>`: the region's season type, 0 August-May, 1 January-December
    local sr, st = line:match("^%s*season%s+(%d+)%s+(%d+)")
    if sr then seasons[tonumber(sr)] = tonumber(st) end
    local tot, reg = line:match("^%s*split%s+(%d+)%s+regular=(%d+)")
    if tot then
      regular[tonumber(tot)] = tonumber(reg)
      local g = {}
      for v in (line:match("groups=([%d,]+)") or ""):gmatch("%d+") do g[#g + 1] = tonumber(v) end
      groups[tonumber(tot)] = g
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
  return leagues, regular, groups, seasons
end

-- Shipped regions whose season is the calendar year (season type 1 in the exe's region table
-- read by 0x141576140: Brazil, Argentina, Colombia, China, Chile, Saudi Arabia, Japan). A league
-- of ours there closes at New Year with its region, not in July (GitHub #27). Regions 29 and up
-- are ours and European (fl26augseason).
local CAL_REGIONS = { [16] = true, [18] = true, [19] = true, [21] = true, [23] = true, [24] = true, [28] = true }
-- ... unless the world file's `season` lines say otherwise (a new country that plays February
-- to December: `season 45 1`); fl26join.dll then answers the game the same way.
local SEASONS = {}
local function cal_region(r)
  if r == nil then return false end
  if SEASONS[r] ~= nil then return SEASONS[r] == 1 end
  return CAL_REGIONS[r] == true
end

local CAVE_VA, CAVE_PAGE, CAVE_LEN = 0x14252ebe0, 0x14252e000, 0x208
local PAGE_EXECUTE_READWRITE = 0x40

local dll_log, dll_stats, logbuf, statbuf, idbuf
local ticks = 0

local function drain(reason)
  if not dll_log then return end
  for _ = 1, 32 do                       -- the season build writes more than one buffer's worth
    local n = tonumber(dll_log(logbuf, 4096))
    if n <= 0 then break end
    for line in ffi.string(logbuf, n):gmatch("[^\n]+") do log("fl26joindll: " .. line) end
  end
  if reason then
    dll_stats(statbuf)
    log(string.format("fl26joindll: %s -- register_all %d, ids appended %d, refused %d, entered %d, builds %d, door %d (refused %d, ours %d)",
                      reason, tonumber(statbuf[0]), tonumber(statbuf[1]), tonumber(statbuf[2]),
                      tonumber(statbuf[3]), tonumber(statbuf[4]), tonumber(statbuf[5]),
                      tonumber(statbuf[6]), tonumber(statbuf[7])))
  end
end

function m.make_key(ctx, filename)
  ticks = ticks + 1
  -- Every 32 ticks the DLL's text log is emptied into sider.log; every 512 ticks the
  -- counters come too. The counters are the only way to tell "the hook never fired" from
  -- "the hook fired and had nothing to say", and on 22.09 those two looked identical.
  if ticks % 512 == 0 then drain("tick")
  elseif ticks % 32 == 0 then drain(nil) end
  return nil
end

function m.key_down(ctx, vkey)
  if vkey == 0x79 then drain("F10 report") end      -- F10
end

function m.init(ctx)
  if ffi == nil then log("fl26joindll: global ffi is nil -- set luajit.ext.enabled = 1 in sider.ini"); return end
  ffi.cdef([[
    void*    LoadLibraryA(const char*);
    void*    GetProcAddress(void*, const char*);
    void*    GetModuleHandleA(const char*);
    unsigned long GetLastError(void);
    int      VirtualProtect(void*, size_t, uint32_t, uint32_t*);
    typedef int  (*fl26_join_install_t)(uint64_t, uint64_t, const uint16_t*, int, const char*);
    typedef int  (*fl26_join_log_t)(char*, int);
    typedef void (*fl26_join_stats_t)(uint32_t*);
    typedef int  (*fl26_join_teardown_extra_t)(const uint16_t*, int);
    typedef int  (*fl26_join_calendar_t)(const uint16_t*, int);
    typedef int  (*fl26_join_season_types_t)(const uint8_t*, int);
  ]])

  local old = ffi.new("uint32_t[1]")
  if ffi.C.VirtualProtect(ffi.cast("void*", CAVE_PAGE), 0x1000, PAGE_EXECUTE_READWRITE, old) == 0 then
    log("fl26joindll: VirtualProtect(cave) failed -- aborting"); return
  end
  memory.write(CAVE_VA, string.rep("\0", CAVE_LEN))

  local sep = string.char(92)
  local sider_dir = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "")
  local dllpath = sider_dir .. sep .. "modules" .. sep .. "fl26join.dll"
  local logpath = sider_dir .. sep .. "fl26join.log"
  local h = ffi.C.LoadLibraryA(dllpath)
  if h == nil then
    log(string.format("fl26joindll: LoadLibraryA failed (err %d): %s -- is fl26join.dll next to this file in modules?",
                      tonumber(ffi.C.GetLastError()), dllpath)); return
  end
  local pi = ffi.C.GetProcAddress(h, "fl26_join_install")
  local pl = ffi.C.GetProcAddress(h, "fl26_join_log")
  local ps = ffi.C.GetProcAddress(h, "fl26_join_stats")
  if pi == nil or pl == nil or ps == nil then log("fl26joindll: GetProcAddress failed"); return end
  local install = ffi.cast("fl26_join_install_t", pi)
  dll_log   = ffi.cast("fl26_join_log_t", pl)
  dll_stats = ffi.cast("fl26_join_stats_t", ps)
  logbuf, statbuf = ffi.new("char[4096]"), ffi.new("uint32_t[8]")

  local world, regular, groups, seasons = read_world(ctx)
  SEASONS = seasons or {}
  if world then
    IDS = {}
    local shown = 0
    for _, L in ipairs(world) do
      -- an exhibition league (exhibition=1) is for Kick Off only: never registered in a season
      if (L.exhibition or 0) == 0 then IDS[#IDS + 1] = L.id else shown = shown + 1 end
      -- A split league's regular phase goes in with it. At creation the season builder admits
      -- the phase along with its total, but register_all enters only the ids it is handed: a
      -- split registered there (a league outside the creation list) entered its total and
      -- never its regular phase, and played nothing. The groups stay out: fl26swiss fills them
      -- when the regular phase ends.
      if (L.exhibition or 0) == 0 and regular[L.id] then IDS[#IDS + 1] = regular[L.id] end
      -- ... but they are closed in July with the rest: left open, the Clausura kept its played
      -- matches and its season into the second season, and that finished season is the one the
      -- Apertura asks for in September (fl26join reg_post).
      if (L.exhibition or 0) == 0 and groups[L.id] then
        for _, g in ipairs(groups[L.id]) do TD_EXTRA[#TD_EXTRA + 1] = g end
      end
    end
    -- the count is the world file's leagues, as Checks compares it; the split phases that go
    -- in with them are named apart (Iceland, two Apertura/Clausura leagues, GitHub #45: "4
    -- leagues <- the file has 2" when nothing was wrong with the count)
    local phases = 0
    for _, L in ipairs(world) do
      if (L.exhibition or 0) == 0 and regular[L.id] then phases = phases + 1 end
    end
    log(string.format("fl26joindll: world file -- %d leagues%s%s", #IDS - phases + shown,
                      phases > 0 and string.format(" (+%d split phase(s) registered with them)", phases) or "",
                      shown > 0 and string.format(", %d exhibition only (not registered)", shown) or ""))
    if #IDS == 0 then log("fl26joindll: the world has no leagues -- nothing to register"); return end
  end
  idbuf = ffi.new("uint16_t[?]", #IDS)
  for i, v in ipairs(IDS) do idbuf[i - 1] = v end

  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(install(base, CAVE_VA, idbuf, #IDS, logpath))
  if status == 0 then
    log(string.format("fl26joindll: installed -- %d added leagues will be registered on the first registration day of the season; the DLL's own log is %s (F10 = counters)", #IDS, logpath))
    if #TD_EXTRA > 0 then
      local pt = ffi.C.GetProcAddress(h, "fl26_join_teardown_extra")
      if pt == nil then log("fl26joindll: this fl26join.dll has no fl26_join_teardown_extra -- split groups will not be closed")
      else
        local tdbuf = ffi.new("uint16_t[?]", #TD_EXTRA)
        for i, v in ipairs(TD_EXTRA) do tdbuf[i - 1] = v end
        local kept = tonumber(ffi.cast("fl26_join_teardown_extra_t", pt)(tdbuf, #TD_EXTRA))
        log(string.format("fl26joindll: %d split group ids go on the July teardown only", kept))
      end
    end
    local CAL = {}
    for _, L in ipairs(world or {}) do
      if cal_region(L.region) and (L.exhibition or 0) == 0 then CAL[#CAL + 1] = L.id end
    end
    local SP = {}
    for r, t in pairs(SEASONS) do if r >= 0 and r < 64 and t >= 0 and t <= 3 then SP[#SP + 1] = { r, t } end end
    if #SP > 0 then
      local pst = ffi.C.GetProcAddress(h, "fl26_join_season_types")
      if pst == nil then log("fl26joindll: this fl26join.dll has no fl26_join_season_types -- the world's season lines are ignored")
      else
        local sbuf = ffi.new("uint8_t[?]", 2 * #SP)
        for i, e in ipairs(SP) do sbuf[2 * i - 2] = e[1]; sbuf[2 * i - 1] = e[2] end
        local k = tonumber(ffi.cast("fl26_join_season_types_t", pst)(sbuf, #SP))
        if k < 0 then log(string.format("fl26joindll: season types NOT set (status %d) -- see fl26join.log", k))
        else log(string.format("fl26joindll: %d region(s) given their season type by the world file", k)) end
      end
    end
    if #CAL > 0 then
      local pc = ffi.C.GetProcAddress(h, "fl26_join_calendar")
      if pc == nil then log("fl26joindll: this fl26join.dll has no fl26_join_calendar -- January-December leagues close in July")
      else
        local cbuf = ffi.new("uint16_t[?]", #CAL)
        for i, v in ipairs(CAL) do cbuf[i - 1] = v end
        local n = tonumber(ffi.cast("fl26_join_calendar_t", pc)(cbuf, #CAL))
        log(string.format("fl26joindll: %d January-December league(s) close at New Year with their region", n))
      end
    end
    ctx.register("livecpk_make_key", m.make_key)
    ctx.register("key_down", m.key_down)
    drain(nil)
  else
    local msg = ({ [2] = "register_all signature mismatch", [3] = "VirtualAlloc failed", [4] = "VirtualProtect failed",
                   [12] = "enter_season signature mismatch", [13] = "VirtualAlloc failed", [14] = "VirtualProtect failed",
                   [22] = "builder signature mismatch", [23] = "VirtualAlloc failed", [24] = "VirtualProtect failed",
                   [32] = "door signature mismatch", [33] = "VirtualAlloc failed", [34] = "VirtualProtect failed",
                   [9] = "bad id list" })[status] or "unknown"
    log("fl26joindll: install FAILED (status " .. status .. ") -- " .. msg .. ". The game is unmodified.")
  end
end

return m
