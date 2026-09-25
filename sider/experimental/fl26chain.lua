--[[
fl26chain -- loader for fl26chain.dll: completes a promotion/relegation chain deeper than two
tiers at season end. The CHAINS and PROTECT lists below are OUR test world's (third, fourth
and fifth divisions under Ligue 2 and Serie B, ids 180..185) -- replace them with your own
league ids before you load this.

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

  cfg = ffi.new("fl26_chain_cfg_t[?]", #CHAINS)
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
