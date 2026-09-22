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
rulebook id, see docs/how-it-works.md. It has been measured for one season, on a season
created with one of the added clubs, up to day 123 of the calendar. Not yet measured: a
season created with a shipped club, and what happens at the season rollover.

The other three hooks only watch: enter_season 0x14158f420 (every id that enters, with the
return address that asked), the builder (the include list it was handed) and the door (for
our ids: its answer, the record's flag, kind and club count, and the caller). None of them
runs any game code -- the record is found by walking the regulation array. Every line is
also appended to fl26join.log in the SiderAddons folder the moment it is written, so a crash
during season creation cannot lose the answer. That file is worth attaching to a report.

The observation ring lives at 0x14252ebe0 -- above 0x14252e800, and after every module that
already claimed padding there: the nullguards (..0x14252e900) and fl26hdr192's trampolines
(..0x14252eb24). 0x208 bytes: a counter, a write index, and 256 slots. Do not take cave
space without checking all of sider/*.lua first -- a module that finds its padding occupied
refuses its patches and says so in one line that is easy to miss.

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
              178, 179, 180, 181, 182, 183, 184, 185 }

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

  idbuf = ffi.new("uint16_t[?]", #IDS)
  for i, v in ipairs(IDS) do idbuf[i - 1] = v end

  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(install(base, CAVE_VA, idbuf, #IDS, logpath))
  if status == 0 then
    log(string.format("fl26joindll: installed -- %d added leagues will be registered on the first registration day of the season; the DLL's own log is %s (F10 = counters)", #IDS, logpath))
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
