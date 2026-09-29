--[[
fl26chain -- loader for fl26chain.dll: completes a promotion/relegation chain deeper than two
tiers at season end. The CHAINS and PROTECT lists below are OUR test world's (third, fourth
and fifth divisions under Ligue 2 and Serie B, ids 180..185) -- replace them with your own
league ids before you load this, or let a world file supply them (see below).

Why: the game's season-end pass exchanges clubs between a league and the league below it
only once per pass, and the middle tier of a chain is skipped because the tier above already
produced its list (docs/season-rollover-decode.md). The DLL hooks the apply step, reads the
final standings of the middle and bottom tier through the game's own functions, moves the
bottom DEMOTE clubs of the middle tier down and the top PROMOTE eligible clubs of the bottom
tier up, and re-writes both lists through the game's own list writer. Nothing else is touched.

Configure CHAINS below: {middle league id, bottom league id, demote from middle, promote
from bottom}. The counts must match the promotion/relegation counts in fl26comptab.lua
(COUNTS[middle][2] and COUNTS[bottom][1]) so the top<->middle exchange and ours agree.

Log: the DLL keeps a small text log; this loader drains it into sider.log on every tick
and on F10. It keeps a small observation ring in the code section's spare tail at
0x14252e900..0x14252ea08.

The world file. When SiderAddons\modules\fl26world.txt exists (written by FL26 Mod Studio's
League Builder), CHAINS and PROTECT below are ignored and both are built from the file:
every league in it is protected, and a chain pair is made for every league on division 3, 5
or 7 that names the league above it -- exactly the pairs the game's mover skips -- with the
league's promote count (3 if it gives none) both ways. Without the file the built-in lists
below are used, as before.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi). Sider's sandbox has no pcall/require.
--]]

local m = {}

-- middle -> bottom: 3 down, 3 up. The game's mover exchanges only every other pair of a chain
-- (A<->B, then C<->D), so each pair it skips is listed here: Serie B (82) -> 183 is skipped
-- because Serie A's visit already wrote Serie B, and Ligue 2 (81) -> 180 for the same reason
-- with Ligue 1. (Ligue 2 used to lack a season table here; that was fl26hdr192 missing the
-- table-state byte at 0x14159edca, fixed there.)
-- In the league-size world (sider/experimental/README.md, the European format) regulation 174
-- is a third division below the Championship; there, add { 79, 174, 3, 3 } as a fifth chain.
-- Do not add it anywhere else: in a world where 174 is a first division it would move clubs
-- between the Championship and that league. Up to 8 chains.
local CHAINS = { { 81, 180, 3, 3 }, { 82, 183, 3, 3 }, { 181, 182, 3, 3 }, { 184, 185, 3, 3 } }

-- Our regulations (the fl26joindll list). None of them may be rewritten with an EMPTY club
-- list while it holds clubs: on 2026-09-22 the New Year pass of the calendar-year world did
-- exactly that to 76, 93, 94, 96, 98 and 162 in the middle of their August-May season.
local PROTECT = { 11, 49, 60, 61, 62, 74, 76, 93, 94, 96, 98, 100, 109, 110, 111, 112, 113, 114,
                  121, 138, 139, 140, 143, 144, 145, 146, 170, 171, 173, 174, 176,
                  178, 179, 180, 181, 182, 183, 184, 185, 190 }

-- The world file: modules\fl26world.txt, written by FL26 Mod Studio's League Builder.
-- One table per league -- id, then whatever the line gives: cid, region, country, slot, tier,
-- above, promote, demote, clubs, legs, cup (numbers), name (text) -- in file order. nil when
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

-- From the world file: every league is protected, and a chain entry is made for each pair the
-- game's mover skips. The mover exchanges a league with the one below it every other pair,
-- starting at the top (1<->2, 3<->4, ...), so the pairs it skips are the ones whose lower
-- league is division 3, 5 or 7: {league above, league, its promote count both ways}. The league
-- above may be a shipped one (Ligue 2 above a French third division) -- it is named by id, not
-- looked up.
-- A league line with cup= is a second division under a shipped top flight that had none:
-- {that country's cup, the league above, this league}. The DLL keeps the cup to the top
-- league's clubs (GitHub #21: the game would put this league into it, or only this league).
-- scup= on the same line is that country's super cup (GitHub #29): {super cup, the league
-- above, this league}; the DLL swaps a club of this league out of it.
local function from_world(world)
  local chains, protect, cups, scups = {}, {}, {}, {}
  for _, L in ipairs(world) do
    protect[#protect + 1] = L.id
    if L.above and L.tier and L.tier >= 3 and L.tier % 2 == 1 then
      local n = L.promote or 3
      chains[#chains + 1] = { L.above, L.id, n, n }
    end
    if L.cup and L.above then cups[#cups + 1] = { L.cup, L.above, L.id } end
    if L.scup and L.above then scups[#scups + 1] = { L.scup, L.above, L.id } end
  end
  return chains, protect, cups, scups
end

local CAVE_VA, CAVE_PAGE, CAVE_LEN = 0x14252e900, 0x14252e000, 0x108
local PAGE_EXECUTE_READWRITE = 0x40

local dll_log, dll_stats, logbuf, statbuf, cfg
local ticks = 0

local function drain(reason)
  if not dll_log then return end
  local n = tonumber(dll_log(logbuf, 4096))
  if n > 0 then
    for line in ffi.string(logbuf, n):gmatch("[^\n]+") do log("fl26chain: " .. line) end
  end
  if reason then
    dll_stats(statbuf)
    log(string.format("fl26chain: %s -- applies %d, fixes %d, refused %d, anomalies %d", reason,
                      tonumber(statbuf[0]), tonumber(statbuf[1]), tonumber(statbuf[2]), tonumber(statbuf[3])))
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
  if ffi == nil then log("fl26chain: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[
    void*    LoadLibraryA(const char*);
    void*    GetProcAddress(void*, const char*);
    void*    GetModuleHandleA(const char*);
    unsigned long GetLastError(void);
    int      VirtualProtect(void*, size_t, uint32_t, uint32_t*);
    typedef struct { uint16_t mid, low; uint8_t demote_mid, promote_low; uint8_t pad[2]; } fl26_chain_cfg_t;
    typedef int  (*fl26_chain_install_t)(uint64_t, uint64_t, const fl26_chain_cfg_t*, int);
    typedef int  (*fl26_chain_log_t)(char*, int);
    typedef void (*fl26_chain_stats_t)(uint32_t*);
    typedef int  (*fl26_chain_protect_t)(const uint16_t*, int);
    typedef int  (*fl26_chain_cups_t)(const uint16_t*, int);
  ]])

  local old = ffi.new("uint32_t[1]")
  if ffi.C.VirtualProtect(ffi.cast("void*", CAVE_PAGE), 0x1000, PAGE_EXECUTE_READWRITE, old) == 0 then
    log("fl26chain: VirtualProtect(cave) failed -- aborting"); return
  end
  memory.write(CAVE_VA, string.rep("\0", CAVE_LEN))

  local sep = string.char(92)
  local dllpath = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26chain.dll"
  local h = ffi.C.LoadLibraryA(dllpath)
  if h == nil then
    log(string.format("fl26chain: LoadLibraryA failed (err %d): %s", tonumber(ffi.C.GetLastError()), dllpath)); return
  end
  local pi, pl, ps = ffi.C.GetProcAddress(h, "fl26_chain_install"), ffi.C.GetProcAddress(h, "fl26_chain_log"), ffi.C.GetProcAddress(h, "fl26_chain_stats")
  if pi == nil or pl == nil or ps == nil then log("fl26chain: GetProcAddress failed"); return end
  local install = ffi.cast("fl26_chain_install_t", pi)
  dll_log   = ffi.cast("fl26_chain_log_t", pl)
  dll_stats = ffi.cast("fl26_chain_stats_t", ps)
  logbuf, statbuf = ffi.new("char[4096]"), ffi.new("uint32_t[4]")

  local world, CUPS, SCUPS = read_world(ctx), {}, {}
  if world then
    CHAINS, PROTECT, CUPS, SCUPS = from_world(world)
    log(string.format("fl26chain: world file -- %d leagues, %d chain pair(s) the game skips", #PROTECT, #CHAINS))
  end
  cfg = ffi.new("fl26_chain_cfg_t[?]", math.max(#CHAINS, 1))
  for i, c in ipairs(CHAINS) do
    cfg[i - 1].mid, cfg[i - 1].low, cfg[i - 1].demote_mid, cfg[i - 1].promote_low = c[1], c[2], c[3], c[4]
  end

  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(install(base, CAVE_VA, cfg, #CHAINS))
  if status == 0 then
    local pp = ffi.C.GetProcAddress(h, "fl26_chain_protect")
    if pp ~= nil then
      local ids = ffi.new("uint16_t[?]", #PROTECT)
      for i, v in ipairs(PROTECT) do ids[i - 1] = v end
      ffi.cast("fl26_chain_protect_t", pp)(ids, #PROTECT)
    else
      log("fl26chain: this fl26chain.dll has no empty-list guard (fl26_chain_protect)")
    end
    if #CUPS > 0 then
      local pc = ffi.C.GetProcAddress(h, "fl26_chain_cups")
      if pc ~= nil then
        local t = ffi.new("uint16_t[?]", 3 * #CUPS)
        for i, c in ipairs(CUPS) do
          t[3 * i - 3], t[3 * i - 2], t[3 * i - 1] = c[1], c[2], c[3]
          log(string.format("fl26chain: live -- cup %d keeps the clubs of %d, not of %d below it", c[1], c[2], c[3]))
        end
        ffi.cast("fl26_chain_cups_t", pc)(t, #CUPS)
      else
        log("fl26chain: this fl26chain.dll cannot keep a cup to its league (no fl26_chain_cups) -- rebuild it")
      end
    end
    if #SCUPS > 0 then
      local ps2 = ffi.C.GetProcAddress(h, "fl26_chain_supercups")
      if ps2 ~= nil then
        local t = ffi.new("uint16_t[?]", 3 * #SCUPS)
        for i, c in ipairs(SCUPS) do
          t[3 * i - 3], t[3 * i - 2], t[3 * i - 1] = c[1], c[2], c[3]
          log(string.format("fl26chain: live -- super cup %d takes no club of %d (only of %d)", c[1], c[3], c[2]))
        end
        ffi.cast("fl26_chain_cups_t", ps2)(t, #SCUPS)
      else
        log("fl26chain: this fl26chain.dll cannot keep a super cup free of a new league (no fl26_chain_supercups) -- rebuild it")
      end
    end
    for _, c in ipairs(CHAINS) do
      log(string.format("fl26chain: live -- chain %d -> %d: %d down, %d up at season end (F10 = report)", c[1], c[2], c[3], c[4]))
    end
    ctx.register("livecpk_make_key", m.make_key)
    ctx.register("key_down", m.key_down)
    drain(nil)
  else
    local msg = ({ [2] = "set-hook signature mismatch", [3] = "VirtualAlloc failed", [4] = "VirtualProtect failed",
                   [12] = "apply-hook signature mismatch", [13] = "VirtualAlloc failed", [14] = "VirtualProtect failed",
                   [9] = "bad config" })[status] or "unknown"
    log("fl26chain: install FAILED (status " .. status .. ") -- " .. msg .. ". The game is unmodified.")
  end
end

return m
