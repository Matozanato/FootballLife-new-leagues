--[[
fl26cwc -- the Club World Cup ranking: loader for modules\fl26cwc.dll (see fl26cwc.c).

The confederation ranking screens of fl26contrank show the points won in the continental club
cups (kept per save, beside it: ML0000000N.fl26cwc). Load it AFTER fl26contrank in sider.ini.

In Sider's overlay (fl26cwc shown): the slot, the ledger and the top five clubs;
F8 writes every club's points and every entry to SiderAddons\fl26cwc-report.txt.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi).
--]]

-- The ranking resets right before every Club World Cup of four years: on day RESET_DAY
-- (0-based day of the year; 153 = the day fl26swiss starts the 32-club CWC) of FIRST_CWC_YEAR,
-- FIRST_CWC_YEAR + 4, ... Before the first one, everything since the start of the career counts.
local FIRST_CWC_YEAR = 2029
local RESET_DAY = 153
local EVERY = 4
local KO, IC, ICCID = 0, 0, 0   -- cwc32 ko= ic= iccid=: rows put into careers saved before the Build
-- cwcpts <reg>=<kind> ...: this world's ids of the continental rounds that give ranking points
-- (Mod Studio gives its own cups the first free ids of each world); nil = the game's cups only
local PTS = nil
-- Mod Studio's Club World Cup option writes the cycle into the world file:
--   cwc32 ko=<reg> every=<years> first=<year> ic=<reg> iccid=<cid>
-- and that line wins over the two numbers above (fl26swiss draws the cup on the same cycle)
local function read_cycle(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  if not f then return false end
  local on = false
  for line in f:lines() do
    local rest = line:match("^%s*cwc32%s+(.*)$")
    if rest then
      on = true
      FIRST_CWC_YEAR = tonumber(rest:match("first=(%d+)") or FIRST_CWC_YEAR) or FIRST_CWC_YEAR
      EVERY = tonumber(rest:match("every=(%d+)") or EVERY) or EVERY
      KO = tonumber(rest:match("ko=(%d+)") or 0) or 0
      IC = tonumber(rest:match("ic=(%d+)") or 0) or 0
      ICCID = tonumber(rest:match("iccid=(%d+)") or 0) or 0
    end
    local pts = line:match("^%s*cwcpts%s+(.-)%s*$")
    if pts then PTS = pts end
  end
  f:close()
  return on
end

local m = {}
local dll_log, dll_status, dll_report, logbuf, statbuf, report_path
local ticks = 0
local last = ""

local function drain()
  if not dll_log then return end
  local n = tonumber(dll_log(logbuf, 16384))
  if n > 0 then
    for line in ffi.string(logbuf, n):gmatch("[^\n]+") do log("fl26cwc: " .. line) end
  end
end

function m.make_key(ctx, filename)
  ticks = ticks + 1
  if ticks % 64 == 0 then drain() end
  return nil
end

function m.overlay_on(ctx)
  drain()
  local s = ""
  if dll_status then
    local n = tonumber(dll_status(statbuf, 2048))
    if n > 0 then s = ffi.string(statbuf, n) end
  end
  return "fl26cwc  (F8 = every club's points to fl26cwc-report.txt)\n" .. s .. last
end

function m.key_down(ctx, vkey)
  if vkey == 0x77 and dll_report then           -- F8
    local n = tonumber(dll_report(report_path))
    last = string.format("\nF8: %d club(s) -> %s", n, report_path)
    log("fl26cwc: " .. last:sub(2))
    drain()
  end
end

function m.init(ctx)
  if ffi == nil then log("fl26cwc: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  -- only in a world built with the Club World Cup of 32 (Mod Studio: Leagues > More > Club World Cup)
  if not read_cycle(ctx) then
    log("fl26cwc: the world file has no cwc32 line (Club World Cup of 32 off) -- nothing installed")
    return
  end
  ffi.cdef([[
    void* fl26cwc_LoadLibraryA(const char*) __asm__("LoadLibraryA");
    void* fl26cwc_GetProcAddress(void*, const char*) __asm__("GetProcAddress");
    typedef int (*fl26_cwc_install_t)(int, int);
    typedef int (*fl26_cwc_every_t)(int);
    typedef int (*fl26_cwc_oldsaves_t)(int, int, int);
    typedef int (*fl26_cwc_comps_t)(const char*);
    typedef int (*fl26_cwc_buf_t)(char*, int);
    typedef int (*fl26_cwc_report_t)(const char*);
  ]])
  local sep = string.char(92)
  local root = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "")
  local h = ffi.C.fl26cwc_LoadLibraryA(root .. sep .. "modules" .. sep .. "fl26cwc.dll")
  if h == nil then log("fl26cwc: cannot load modules\\fl26cwc.dll"); return end
  local function fn(t, name)
    local p = ffi.C.fl26cwc_GetProcAddress(h, name)
    if p == nil then return nil end
    return ffi.cast(t, p)
  end
  local inst = fn("fl26_cwc_install_t", "fl26_cwc_install")
  dll_log = fn("fl26_cwc_buf_t", "fl26_cwc_log")
  dll_status = fn("fl26_cwc_buf_t", "fl26_cwc_status")
  dll_report = fn("fl26_cwc_report_t", "fl26_cwc_report")
  if not (inst and dll_log and dll_status and dll_report) then
    log("fl26cwc: modules\\fl26cwc.dll is not the ranking build (an export is missing)")
    dll_log, dll_status, dll_report = nil, nil, nil
    return
  end
  logbuf = ffi.new("char[16384]")
  statbuf = ffi.new("char[2048]")
  report_path = root .. sep .. "fl26cwc-report.txt"
  local every = fn("fl26_cwc_every_t", "fl26_cwc_every")
  if every then every(EVERY) end
  local oldsaves = fn("fl26_cwc_oldsaves_t", "fl26_cwc_oldsaves")
  if oldsaves and KO > 0 then
    oldsaves(KO, IC, ICCID)
    log(string.format("fl26cwc: careers saved before the Club World Cup Build get its rows (knockout %d, Intercontinental %d of competition %d)", KO, IC, ICCID))
  end
  local comps = fn("fl26_cwc_comps_t", "fl26_cwc_comps")
  if comps then
    local n = tonumber(comps(PTS or ""))
    if PTS then
      log(string.format("fl26cwc: %d continental round(s) of this world give ranking points (cwcpts line)", n))
    else
      log("fl26cwc: the world file has no cwcpts line (a Build of before 18.11.): only the game's own " ..
          "continental cups give ranking points -- Build the world again")
    end
  else
    log("fl26cwc: modules\\fl26cwc.dll has no fl26_cwc_comps (an older build): the ids written in it stand")
  end
  local r = tonumber(inst(FIRST_CWC_YEAR, RESET_DAY))
  log(string.format("fl26cwc: the ranking's cycle: every %d year(s) from %d (day %d)", EVERY, FIRST_CWC_YEAR, RESET_DAY))
  drain()
  log(string.format("fl26cwc: %s (lists %s, saves %s)", r % 2 == 1 and "ranking installed" or "NOT installed",
                    math.floor(r / 2) % 2 == 1 and "yes" or "no", math.floor(r / 4) % 2 == 1 and "yes" or "no"))
  ctx.register("overlay_on", m.overlay_on)
  ctx.register("key_down", m.key_down)
  ctx.register("livecpk_make_key", m.make_key)
end

return m
