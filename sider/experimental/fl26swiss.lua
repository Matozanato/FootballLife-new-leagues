--[[
fl26swiss -- loader for fl26swiss.dll: gives a 36-club league phase the modern UEFA draw
(Champions League and Europa League since 2024), which the engine cannot express in data.

Why (docs/league-phase-swiss-decode.md): a league regulation always plays a complete round
robin. The schedule context is built by 0x1413f29e0, which fixes the number of matchdays at
rounds * (clubs - 1), and the pairings come from the circle method written out inline in
0x1413f3e00. Thirty-six clubs therefore means 35 matchdays and 630 matches. No field anywhere
says "each club plays eight opponents". The DLL replaces 0x1413f3e00 for the regulations listed
below and writes the draw itself; every other competition keeps the original code.

The draw is generated and checked by tools/mkswiss.py: 144 matches, every club with 8 different
opponents, exactly two from each pot of nine, exactly four home and four away. Each of the eight
rounds is a perfect matching of all 36 clubs, split over two matchdays of nine, because a
fixture record holds 16 match slots and the emitter drops the rest without a word. So the
competition runs over 16 matchdays and needs 16 dates.

What this module does NOT do, and what still has to be set up separately:
  * the regulations themselves -- one league row of 36 clubs with a single round (rounds = 1),
    plus a play-off of 16 and a knockout of 16 under the same competition, the way the shipped
    Champions League already carries reg 2 and reg 4;
  * the 36 entries in CompetitionEntry.bin, in seeding order, pot 1 first: the draw treats
    positions 0-8 as pot 1, 9-17 as pot 2, 18-26 as pot 3 and 27-35 as pot 4;
  * fixture dates. They are chosen by regulation id from a table in the exe (0x1415802e8) and
    our free ids land in the case that returns no dates at all. That is a patch of its own.

Configure REGS below with the regulation ids of the league-phase rows. Anything not listed is
untouched. It is safe to list an id that does not exist yet.

Log: the DLL keeps a small text log; this loader drains it into sider.log every 32 file opens
and on F8. Requires sider.ini: luajit.ext.enabled = 1 (global ffi). Sider's sandbox has no
pcall and no require.
--]]

local m = {}

-- regulation ids of the 36-club league phases, in date order: the first plays on the module's
-- sixteen days, each next one two days later. 1027 = the Champions League's one group of 36,
-- 1029 = the Europa League's, both reshaped in place by tools/mkreshape.py (world _FL26G39UCL36):
-- the draw only fills groups, so the league phase is a single group, and the DLL also takes the
-- group builder 0x1413f3c30 aside for it. 1210 = the Conference League's group of 36
-- (competition 174, regulation 186, cloned from the reshaped Europa League by tools/mkphases.py,
-- world _FL26G39UECL); in a world without it the DLL says so and leaves it out.
local REGS = { 1027, 1029, 1210 }

-- Conference League entrants the first time round, after the Europa League's cut-offs and the
-- regulation's own entries: clubs from the European first divisions that are in neither the
-- Champions League nor the Europa League entries of the world (tools/mkuecl.py prints them).
local UECL = { 4071, 4145, 320, 4124, 403, 242, 5845, 174, 5196, 270, 5202, 2067, 1219, 4180,
               361, 4219, 227, 180, 246, 2380, 5191, 9016, 1948, 1989, 1832, 2621, 377, 259,
               4220, 129, 1329, 344, 5954, 2009, 5295, 2020 }

local dll_log, dll_stats, dll_ko_tick, logbuf, statbuf, regbuf
local ticks = 0

local function drain(reason)
  if not dll_log then return end
  for _ = 1, 32 do                       -- the club-list watch can write more than one buffer
    local n = tonumber(dll_log(logbuf, 4096))
    if n <= 0 then break end
    for line in ffi.string(logbuf, n):gmatch("[^\n]+") do log(line) end
  end
  if reason then
    dll_stats(statbuf)
    log(string.format("fl26swiss: %s -- calls %d, league phases written %d, left to the game %d, "
                      .. "pairs off the grid %d, calendars written %d",
                      reason, tonumber(statbuf[0]), tonumber(statbuf[1]), tonumber(statbuf[2]),
                      tonumber(statbuf[3]), tonumber(statbuf[4])))
  end
end

function m.make_key(ctx, filename)
  ticks = ticks + 1
  -- the knockout bracket check (fl26_swiss_ko_tick) returns at once outside spring
  if dll_ko_tick and ticks % 64 == 0 then dll_ko_tick() end
  if ticks % 32 == 0 then drain(nil) end
  return nil
end

function m.key_down(ctx, vkey)
  if vkey == 0x77 then drain("F8 report") end      -- F8
end

function m.init(ctx)
  if ffi == nil then log("fl26swiss: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[
    void*    LoadLibraryA(const char*);
    void*    GetProcAddress(void*, const char*);
    void*    GetModuleHandleA(const char*);
    unsigned long GetLastError(void);
    typedef int  (*fl26_swiss_install_t)(uint64_t, const uint16_t*, int);
    typedef int  (*fl26_swiss_log_t)(char*, int);
    typedef void (*fl26_swiss_stats_t)(uint32_t*);
    typedef void (*fl26_swiss_uecl_t)(const uint32_t*, int);
    typedef void (*fl26_swiss_ko_tick_t)(void);
  ]])

  local sep = string.char(92)
  local dllpath = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26swiss.dll"
  local h = ffi.C.LoadLibraryA(dllpath)
  if h == nil then
    log(string.format("fl26swiss: LoadLibraryA failed (err %d): %s", tonumber(ffi.C.GetLastError()), dllpath)); return
  end
  local pi = ffi.C.GetProcAddress(h, "fl26_swiss_install")
  local pl = ffi.C.GetProcAddress(h, "fl26_swiss_log")
  local ps = ffi.C.GetProcAddress(h, "fl26_swiss_stats")
  if pi == nil or pl == nil or ps == nil then log("fl26swiss: GetProcAddress failed"); return end
  local install = ffi.cast("fl26_swiss_install_t", pi)
  dll_log   = ffi.cast("fl26_swiss_log_t", pl)
  dll_stats = ffi.cast("fl26_swiss_stats_t", ps)
  logbuf, statbuf = ffi.new("char[4096]"), ffi.new("uint32_t[5]")

  regbuf = ffi.new("uint16_t[?]", #REGS)
  for i, r in ipairs(REGS) do regbuf[i - 1] = r end

  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(install(base, regbuf, #REGS))
  if status == 0 then
    local pu = ffi.C.GetProcAddress(h, "fl26_swiss_uecl")
    if pu ~= nil then
      local ubuf = ffi.new("uint32_t[?]", #UECL)
      for i, c in ipairs(UECL) do ubuf[i - 1] = c end
      ffi.cast("fl26_swiss_uecl_t", pu)(ubuf, #UECL)
    end
    local pk = ffi.C.GetProcAddress(h, "fl26_swiss_ko_tick")
    if pk ~= nil then dll_ko_tick = ffi.cast("fl26_swiss_ko_tick_t", pk) end
    local ids = {}
    for _, r in ipairs(REGS) do ids[#ids + 1] = tostring(r) end
    log("fl26swiss: live -- 36-club league phase for regulation " .. table.concat(ids, ", ")
        .. "; 8 opponents each over 16 matchdays (F8 = report)")
    ctx.register("livecpk_make_key", m.make_key)
    ctx.register("key_down", m.key_down)
    drain(nil)
  else
    local msg = ({ [2] = "signature mismatch at 0x1413f3e00 -- wrong game build",
                   [12] = "signature mismatch at 0x14157f810 -- wrong game build",
                   [22] = "signature mismatch at 0x1413f3c30 -- wrong game build",
                   [3] = "VirtualAlloc failed", [4] = "VirtualProtect failed",
                   [9] = "bad config (REGS empty or more than 8)" })[status] or "unknown"
    log("fl26swiss: install FAILED (status " .. status .. ") -- " .. msg .. ". The game is unmodified.")
  end
end

return m
