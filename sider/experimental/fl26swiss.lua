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

The world file. When SiderAddons\modules\fl26world.txt exists (written by FL26 Mod Studio's
League Builder), the module hands the DLL three things from it: the world's league list
(whose calendars then follow each league's own size), its split seasons (`split` lines:
regular phase and group phases) and its UEFA places (`uefa` lines, the access list; a world
file without any leaves the DLL's compiled list in place). A DLL too old to take one of these
keeps its built-in one and the log says so. Without the file it behaves as before.

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

-- The UEFA access list comes from the world file's uefa lines; without one,
-- fl26swiss.dll's compiled list is used (it knows only the shipped leagues, whose ids are the
-- same in every world, and tops the rest up from the big five). One entry per place:
-- { regulation, position, competition, alt }. competition: 0 = Champions League, 1 = Europa
-- League, 2 = Conference League, 3 = Libertadores, 4 = Libertadores qualifying, 5 = AFC
-- Champions League (an older DLL skips 3-5). Position 0 means the winner of that regulation (a
-- domestic cup); when the winner already has a place, or there is none, the place goes to the
-- next free position of league alt (0 = the place is lost). Places are handed out in list
-- order, so list the Champions League first. Example: { 17, 1, 0, 0 } = Premier League
-- champion to the Champions League; { 23, 0, 1, 17 } = cup 23's winner to the Europa League,
-- else the next Premier League club. A table set here is used when there is no world file.
local ACCESS = nil

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

-- First-season list (optional): modules\fl26swiss-first.txt. While no final table has been kept
-- (the first season of a career, or after a restart between the end of a season and the August
-- draw), the three competitions take these clubs first, in this order; the access list fills
-- whatever is left. A line naming a competition starts its section; after that, every number in
-- brackets is a team id, and the rest of the line is ignored:
--   Champions League
--   Paris Saint-Germain (114)    Manchester City (173)
--   Europa League
--   AS Roma (125)
--   Conference League
--   ...
-- A number in brackets followed by a colon is a count in a heading ("IN DATABASE (34):") and is
-- skipped. Ids the game does not have are left out, and sider.log names them.
-- The world file: modules\fl26world.txt, written by FL26 Mod Studio's League Builder.
-- One table per league -- id, then whatever the line gives: cid, region, country, slot, tier,
-- above, promote, demote, clubs, legs (numbers), name (text) -- in file order. nil when there
-- is no file: the module then keeps the DLL's own lists, as it always has. Second result: the
-- split seasons, { total, regular, g1, g2, g3 } from `split <total> regular=<id> groups=<id>,<id>`.
-- Third: the UEFA access list, { regulation, position, competition, alt } from
-- `uefa <regulation> <position> <competition> <alt>`, in file order (see ACCESS). Fourth: the
-- continental cups the DLL runs itself (tools/mkccup.py, the League Builder's CAF, AFC Champions
-- League Two and Copa Sudamericana), { reg, ko, groups, {{reg, position}...} } from
-- `ccup <groups master> ko=<id> groups=<n> entry=<reg>:<position>,... name=<text>`, and the
-- options a league cup or a pre-season cup adds: fill=<day> national=1 days=<d>,<d>,...
-- clubs=<team id>,... (c.opts, fl26_swiss_ccup_opts). Sixth: the qualifying rounds in front of
-- the August play-offs, { competition, round, regulation } from `qround <competition> <round>
-- <regulation>` (10 / 11 / 12, round 3 or 2; fl26_swiss_qrounds). Seventh: the league cups'
-- pre-rounds, { reg, cup knockout, fill day, {day, day}, {{reg, position}...} } from
-- `lpre <reg> cup=<ko> fill=<day> days=<d>,<d> entry=<reg>:<position>,...` (fl26_swiss_lpre).
local confed = {}               -- read_world: the confed line, { flag, code } pairs
local function read_world(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  if not f then return nil end
  local leagues, splits, uefa, ccups, dlike, qrounds, lpres = {}, {}, {}, {}, {}, {}, {}
  confed = {}
  for line in f:lines() do
    local lr, lrest = line:match("^%s*lpre%s+(%d+)(.*)$")
    if lr then
      local L = { tonumber(lr), tonumber(lrest:match("cup=(%d+)") or 0), tonumber(lrest:match("fill=(%d+)") or 0), {}, {} }
      for d in (lrest:match("days=([%d,]+)") or ""):gmatch("%d+") do L[4][#L[4] + 1] = tonumber(d) end
      for er, ep in (lrest:match("entry=([%d:,]+)") or ""):gmatch("(%d+):(%d+)") do
        L[5][#L[5] + 1] = { tonumber(er), tonumber(ep) }
      end
      if L[2] > 0 and #L[4] == 2 and #L[5] >= 2 then lpres[#lpres + 1] = L end
    end
    local qc, qn, qr = line:match("^%s*qround%s+(%d+)%s+(%d+)%s+(%d+)")
    if qc then qrounds[#qrounds + 1] = { tonumber(qc), tonumber(qn), tonumber(qr) } end
    -- `dates <our cup> like=<shipped cup>`: a national cup or super cup of a new country is
    -- dated as the shipped cup it was copied from (the game dates cups by id, 2..175 only)
    local dr, dl = line:match("^%s*dates%s+(%d+)%s+like=(%d+)")
    if dr then dlike[#dlike + 1] = { tonumber(dr), tonumber(dl) } end
    local cid, crest = line:match("^%s*ccup%s+(%d+)(.*)$")
    if cid then
      local c = { tonumber(cid), tonumber(crest:match("ko=(%d+)") or 0), tonumber(crest:match("groups=(%d+)") or 0), {} }
      for er, ep in (crest:match("entry=([%d:,]+)") or ""):gmatch("(%d+):(%d+)") do
        c[4][#c[4] + 1] = { tonumber(er), tonumber(ep) }
      end
      local fill, nat = tonumber(crest:match("fill=(%d+)") or 0), tonumber(crest:match("national=(%d+)") or 0)
      local days, clubs = {}, {}
      for d in (crest:match("days=([%d,]+)") or ""):gmatch("%d+") do days[#days + 1] = tonumber(d) end
      for t in (crest:match("clubs=([%d,]+)") or ""):gmatch("%d+") do clubs[#clubs + 1] = tonumber(t) end
      if fill > 0 or nat > 0 or #days > 0 or #clubs > 0 then
        c.opts = { fill = fill, national = nat, days = days, clubs = clubs }
      end
      -- alt=<entry>:<league>[:<from>],...: a national cup winner's entry, the league its place
      -- falls back to and the first position of it to try (0.2.0, fl26_swiss_ccup_alt: the
      -- position rides in the bits above the league's ten)
      for a in (crest:match("alt=([%d:,]+)") or ""):gmatch("[^,]+") do
        local ae, al, af = a:match("^(%d+):(%d+):?(%d*)$")
        if ae then
          c.alt = c.alt or {}
          c.alt[#c.alt + 1] = { tonumber(ae), tonumber(al) + 1024 * math.min(tonumber(af) or 0, 63) }
        end
      end
      if c[2] > 0 then ccups[#ccups + 1] = c end   -- groups=0: a straight knockout
    end
    -- confed <flag>:<code>,...: each country's confederation, so a continental champion of
    -- ours replaces a club of its own confederation in the game's Club World Cup (0.2.0)
    local cf = line:match("^%s*confed%s+([%d:,]+)")
    if cf then
      for f, c in cf:gmatch("(%d+):(%d+)") do confed[#confed + 1] = { tonumber(f), tonumber(c) } end
    end
    local ur, up, uc, ua = line:match("^%s*uefa%s+(%d+)%s+(%d+)%s+(%d+)%s+(%d+)")
    if ur then uefa[#uefa + 1] = { tonumber(ur), tonumber(up), tonumber(uc), tonumber(ua) } end
    local sid, srest = line:match("^%s*split%s+(%d+)(.*)$")
    if sid then
      local s = { tonumber(sid), tonumber(srest:match("regular=(%d+)") or 0), 0, 0, 0 }
      local g = 3
      for v in (srest:match("groups=([%d,]+)") or ""):gmatch("%d+") do
        if g <= 5 then s[g] = tonumber(v); g = g + 1 end
      end
      -- carry=0: Apertura/Clausura, the group starts from zero points (fl26_swiss_nocarry)
      if srest:match("carry=0") then s.nocarry = true end
      if s[2] > 0 and s[3] > 0 then splits[#splits + 1] = s end
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
  return leagues, splits, uefa, ccups, dlike, qrounds, lpres
end

-- `july <reg> <day>` lines of the world file: { {reg, day}, ... }
local function world_july(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  local out = {}
  if not f then return out end
  for line in f:lines() do
    local r, d = line:match("^%s*july%s+(%d+)%s+(%d+)")
    if r then out[#out + 1] = { tonumber(r), tonumber(d) } end
  end
  f:close()
  return out
end

-- `first <competition> <team id> ...` lines of the world file (0 Champions League, 1 Europa
-- League, 2 Conference League): the clubs Mod Studio's "First-season European clubs" put in
-- the league phases of a new career's first season; { {competition, team id}, ... } or nil
local function world_first(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  if not f then return nil end
  local out = {}
  for line in f:lines() do
    local c, ids = line:match("^%s*first%s+(%d)%s+([%d%s]+)$")
    if c and tonumber(c) <= 2 then
      for t in ids:gmatch("%d+") do out[#out + 1] = { tonumber(c), tonumber(t) } end
    end
  end
  f:close()
  return #out > 0 and out or nil
end

-- `season <region> <type>` lines of the world file: { [region] = type }, 0 August-May, 1
-- January-December (fl26joindll hands the same lines to fl26join.dll, which answers the game)
local function world_seasons(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  local out = {}
  if not f then return out end
  for line in f:lines() do
    local r, t = line:match("^%s*season%s+(%d+)%s+(%d+)")
    if r then out[tonumber(r)] = tonumber(t) end
  end
  f:close()
  return out
end

-- The game's own leagues of a calendar-year region a `season <region> 0` line moves to
-- August-May: they are dated on the European league calendar (fl26_swiss_european). Only the
-- leagues: the region's cups take `dates <cup> like=<European cup>` lines. Experimental.
-- (leaguebuilder GAME_SEASONS): Brazil, Chile, China, Japan, Saudi Arabia
local SHIPPED_REGION_LEAGUES = { [16] = { 29, 163 }, [18] = { 67 }, [21] = { 120 }, [24] = { 52 }, [28] = { 162 } }

local FIRST_FILE = "fl26swiss-first.txt"
local function read_first(path)
  local f = io.open(path, "r")
  if not f then return nil end
  local list, comp = {}, nil
  for line in f:lines() do
    local up = line:upper()
    if up:find("CHAMPIONS") then comp = 0
    elseif up:find("EUROPA") then comp = 1
    elseif up:find("CONFERENCE") then comp = 2
    elseif comp then
      for id, after in line:gmatch("%((%d+)%)(%s*:?)") do
        if not after:find(":") then list[#list + 1] = { comp, tonumber(id) } end
      end
    end
  end
  f:close()
  return #list > 0 and list or nil
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
    typedef int  (*fl26_swiss_access_t)(const uint16_t*, int);
    typedef int  (*fl26_swiss_first_t)(const uint32_t*, int);
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
    -- the leagues whose calendar follows their own size: the world file's, when there is one
    local world, splits, uefa, ccups, dlike, qrounds, lpres = read_world(ctx)
    if world then
      if #qrounds > 0 then
        local pq = ffi.C.GetProcAddress(h, "fl26_swiss_qrounds")
        if pq == nil then
          log("fl26swiss: this fl26swiss.dll has no qualifying rounds (fl26_swiss_qrounds); the play-offs are played alone")
        else
          local qbuf = ffi.new("uint16_t[?]", 3 * #qrounds)
          for i, q in ipairs(qrounds) do qbuf[3 * i - 3], qbuf[3 * i - 2], qbuf[3 * i - 1] = q[1], q[2], q[3] end
          local k = tonumber(ffi.cast("fl26_swiss_access_t", pq)(qbuf, #qrounds))
          log(string.format("fl26swiss: world file -- %d qualifying round(s), %d taken", #qrounds, k))
        end
      end
      -- a world brings its own access list, or gets the DLL's
      if #uefa > 0 then ACCESS = uefa else ACCESS = nil end
      log(string.format("fl26swiss: world file -- %d leagues, %d split(s), %d UEFA place(s)%s", #world,
                        #splits, #uefa, #uefa == 0 and " (none: the DLL's own list)" or ""))
      local ps = ffi.C.GetProcAddress(h, "fl26_swiss_splits")
      if ps == nil then
        log("fl26swiss: this fl26swiss.dll takes no split list (fl26_swiss_splits); its built-in one stands")
      else
        local sbuf = ffi.new("uint16_t[?]", math.max(#splits * 5, 1))
        for i, s in ipairs(splits) do for j = 1, 5 do sbuf[(i - 1) * 5 + j - 1] = s[j] end end
        ffi.cast("fl26_swiss_access_t", ps)(sbuf, #splits)
        local nc = {}
        for _, s in ipairs(splits) do if s.nocarry then nc[#nc + 1] = s[1] end end
        if #nc > 0 then
          local pn = ffi.C.GetProcAddress(h, "fl26_swiss_nocarry")
          if pn == nil then
            log("fl26swiss: this fl26swiss.dll cannot start a Clausura from zero (fl26_swiss_nocarry); it keeps the Apertura's points")
          else
            local nbuf = ffi.new("uint16_t[?]", #nc)
            for i, t in ipairs(nc) do nbuf[i - 1] = t end
            ffi.cast("fl26_swiss_access_t", pn)(nbuf, #nc)
            log(string.format("fl26swiss: world file -- %d Apertura/Clausura season(s), no points carried", #nc))
          end
        end
      end
      if #ccups > 0 then
        local pc = ffi.C.GetProcAddress(h, "fl26_swiss_ccup")
        if pc == nil then
          log("fl26swiss: this fl26swiss.dll runs no continental cups (fl26_swiss_ccup); the world file's are not played")
        else
          local len = 0
          for _, c in ipairs(ccups) do len = len + 4 + 2 * #c[4] end
          local cbuf, p = ffi.new("uint16_t[?]", len), 0
          for _, c in ipairs(ccups) do
            cbuf[p], cbuf[p + 1], cbuf[p + 2], cbuf[p + 3] = c[1], c[2], c[3], #c[4]; p = p + 4
            for _, e in ipairs(c[4]) do cbuf[p], cbuf[p + 1] = e[1], e[2]; p = p + 2 end
          end
          local k = tonumber(ffi.cast("fl26_swiss_access_t", pc)(cbuf, #ccups))
          log(string.format("fl26swiss: world file -- %d continental cup(s), %d accepted", #ccups, k))
          local olen, nopt = 0, 0
          for _, c in ipairs(ccups) do
            if c.opts then olen = olen + 5 + #c.opts.days + #c.opts.clubs; nopt = nopt + 1 end
          end
          if nopt > 0 then
            local po = ffi.C.GetProcAddress(h, "fl26_swiss_ccup_opts")
            if po == nil then
              log("fl26swiss: this fl26swiss.dll takes no cup options (fl26_swiss_ccup_opts); league and pre-season cups run as continental ones")
            else
              local obuf, q = ffi.new("uint32_t[?]", olen), 0
              for _, c in ipairs(ccups) do
                local o = c.opts
                if o then
                  obuf[q], obuf[q + 1], obuf[q + 2], obuf[q + 3] = c[2], o.fill, o.national, #o.days; q = q + 4
                  for _, d in ipairs(o.days) do obuf[q] = d; q = q + 1 end
                  obuf[q] = #o.clubs; q = q + 1
                  for _, t in ipairs(o.clubs) do obuf[q] = t; q = q + 1 end
                end
              end
              local m = tonumber(ffi.cast("fl26_swiss_first_t", po)(obuf, nopt))
              log(string.format("fl26swiss: world file -- options for %d cup(s), %d matched", nopt, m))
            end
          end
          local alen = 0
          for _, c in ipairs(ccups) do alen = alen + (c.alt and #c.alt or 0) end
          if alen > 0 then
            local pa = ffi.C.GetProcAddress(h, "fl26_swiss_ccup_alt")
            if pa == nil then
              log("fl26swiss: this fl26swiss.dll has no fl26_swiss_ccup_alt; a cup winner's place stays empty when there is no winner")
            else
              local abuf, q = ffi.new("uint16_t[?]", 3 * alen), 0
              for _, c in ipairs(ccups) do
                for _, a in ipairs(c.alt or {}) do abuf[q], abuf[q + 1], abuf[q + 2] = c[2], a[1], a[2]; q = q + 3 end
              end
              local m = tonumber(ffi.cast("fl26_swiss_access_t", pa)(abuf, alen))
              log(string.format("fl26swiss: world file -- %d cup winner place(s), %d taken", alen, m))
            end
          end
          if #confed > 0 then
            local pc = ffi.C.GetProcAddress(h, "fl26_swiss_confed")
            if pc == nil then
              log("fl26swiss: this fl26swiss.dll has no fl26_swiss_confed; our champions replace an African club in the game's Club World Cup")
            else
              local cbuf = ffi.new("uint16_t[?]", 2 * #confed)
              for i, p in ipairs(confed) do cbuf[2 * i - 2], cbuf[2 * i - 1] = p[1], p[2] end
              local m = tonumber(ffi.cast("fl26_swiss_access_t", pc)(cbuf, #confed))
              log(string.format("fl26swiss: world file -- confederations of %d countries", m))
            end
          end
          -- the league cups' pre-rounds, after the cups their winners go on to
          if lpres and #lpres > 0 then
            local pl = ffi.C.GetProcAddress(h, "fl26_swiss_lpre")
            if pl == nil then
              log("fl26swiss: this fl26swiss.dll plays no league cup pre-rounds (fl26_swiss_lpre); those league cups will not start")
            else
              local llen = 0
              for _, L in ipairs(lpres) do llen = llen + 6 + 2 * #L[5] end
              local lbuf, q = ffi.new("uint16_t[?]", llen), 0
              for _, L in ipairs(lpres) do
                lbuf[q], lbuf[q + 1], lbuf[q + 2], lbuf[q + 3], lbuf[q + 4], lbuf[q + 5] = L[1], L[2], L[3], L[4][1], L[4][2], #L[5]
                q = q + 6
                for _, e in ipairs(L[5]) do lbuf[q], lbuf[q + 1] = e[1], e[2]; q = q + 2 end
              end
              local m = tonumber(ffi.cast("fl26_swiss_access_t", pl)(lbuf, #lpres))
              log(string.format("fl26swiss: world file -- %d league cup pre-round(s), %d taken", #lpres, m))
            end
          end
        end
      end
      if dlike and #dlike > 0 then
        local pd = ffi.C.GetProcAddress(h, "fl26_swiss_datelike")
        if pd == nil then
          log("fl26swiss: this fl26swiss.dll cannot date a new country's cups (fl26_swiss_datelike); they will not be played")
        else
          local dbuf = ffi.new("uint16_t[?]", 2 * #dlike)
          for i, d in ipairs(dlike) do dbuf[2 * i - 2], dbuf[2 * i - 1] = d[1], d[2] end
          local k = tonumber(ffi.cast("fl26_swiss_access_t", pd)(dbuf, #dlike))
          log(string.format("fl26swiss: world file -- %d cup(s) dated as the cup they were copied from", k))
        end
      end
      local pw = ffi.C.GetProcAddress(h, "fl26_swiss_leagues")
      if pw == nil then
        log("fl26swiss: this fl26swiss.dll takes no world file (fl26_swiss_leagues); its built-in league list stands")
      else
        local wbuf = ffi.new("uint16_t[?]", math.max(#world, 1))
        for i, L in ipairs(world) do wbuf[i - 1] = L.id end
        ffi.cast("fl26_swiss_access_t", pw)(wbuf, #world)
      end
      -- the league-phase draw keeps clubs of one country apart: which country each league slot is
      local pn = ffi.C.GetProcAddress(h, "fl26_swiss_nations")
      if pn ~= nil then
        local nat = {}
        for _, L in ipairs(world) do
          if L.slot and L.country and L.slot >= 0 and L.slot < 123 and L.country > 0 then nat[#nat + 1] = L end
        end
        local nbuf = ffi.new("uint16_t[?]", math.max(2 * #nat, 2))
        for i, L in ipairs(nat) do nbuf[2 * i - 2] = L.slot; nbuf[2 * i - 1] = L.country end
        ffi.cast("fl26_swiss_access_t", pn)(nbuf, #nat)
      end
      -- leagues of ours in a January-December region (Brazil, Argentina, Colombia, China, Chile,
      -- Saudi Arabia, Japan): rounds from mid February to early December (GitHub #27)
      -- ... or the regions a world file's `season <region> 1` line makes January-December (and
      -- not those a `season <region> 0` line makes August-May), as fl26joindll reads them
      local CAL_REGIONS = { [16] = true, [18] = true, [19] = true, [21] = true, [23] = true, [24] = true, [28] = true }
      local seasons = world_seasons(ctx)
      local cal = {}
      for _, L in ipairs(world) do
        local r = L.region
        local c = r ~= nil and (seasons[r] ~= nil and seasons[r] == 1 or seasons[r] == nil and CAL_REGIONS[r] == true)
        if c then cal[#cal + 1] = L.id end
      end
      local pc = ffi.C.GetProcAddress(h, "fl26_swiss_calendar_year")
      if #cal > 0 and pc ~= nil then
        local cbuf = ffi.new("uint16_t[?]", #cal)
        for i, v in ipairs(cal) do cbuf[i - 1] = v end
        ffi.cast("fl26_swiss_access_t", pc)(cbuf, #cal)
      elseif #cal > 0 then
        log("fl26swiss: this fl26swiss.dll has no fl26_swiss_calendar_year -- January-December leagues keep the European dates")
      end
      -- `july <reg> <day>`: a league that starts in July (Poland, Denmark, Croatia ...), its
      -- first round from that day on, from the second season (fl26_swiss_july)
      local july = world_july(ctx)
      local pj = ffi.C.GetProcAddress(h, "fl26_swiss_july")
      if #july > 0 and pj ~= nil then
        local jbuf = ffi.new("uint16_t[?]", 2 * #july)
        for i, v in ipairs(july) do jbuf[2 * i - 2] = v[1]; jbuf[2 * i - 1] = v[2] end
        ffi.cast("fl26_swiss_access_t", pj)(jbuf, #july)
      elseif #july > 0 then
        log("fl26swiss: this fl26swiss.dll has no fl26_swiss_july -- July leagues start in August")
      end
      local eu = {}
      for r, t in pairs(seasons) do
        if t == 0 and CAL_REGIONS[r] and SHIPPED_REGION_LEAGUES[r] then
          for _, id in ipairs(SHIPPED_REGION_LEAGUES[r]) do eu[#eu + 1] = id end
        end
      end
      local pe = ffi.C.GetProcAddress(h, "fl26_swiss_european")
      if #eu > 0 and pe ~= nil then
        local ebuf = ffi.new("uint16_t[?]", #eu)
        for i, v in ipairs(eu) do ebuf[i - 1] = v end
        ffi.cast("fl26_swiss_access_t", pe)(ebuf, #eu)
      elseif #eu > 0 then
        log("fl26swiss: this fl26swiss.dll has no fl26_swiss_european -- the moved league keeps its calendar-year dates")
      end
    end
    if ACCESS then
      local pa = ffi.C.GetProcAddress(h, "fl26_swiss_access")
      if pa == nil then
        log("fl26swiss: this fl26swiss.dll has no access list entry; the compiled list stands")
      else
        local abuf = ffi.new("uint16_t[?]", 4 * #ACCESS)
        for i, e in ipairs(ACCESS) do
          for j = 1, 4 do abuf[4 * (i - 1) + j - 1] = e[j] or 0 end
        end
        local k = tonumber(ffi.cast("fl26_swiss_access_t", pa)(abuf, #ACCESS))
        if k < 0 then log("fl26swiss: ACCESS has no valid entry; the compiled list stands")
        else log(string.format("fl26swiss: access list from this file, %d of %d places", k, #ACCESS)) end
      end
    end
    -- the world file's list first (Mod Studio), else a hand-written fl26swiss-first.txt
    local first, from = world_first(ctx), "the world file"
    if not first then
      first, from = read_first(ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. FIRST_FILE), FIRST_FILE
    end
    if first then
      local pf = ffi.C.GetProcAddress(h, "fl26_swiss_first")
      if pf == nil then
        log("fl26swiss: this fl26swiss.dll takes no first-season list; " .. FIRST_FILE .. " is not used")
      else
        local fbuf = ffi.new("uint32_t[?]", 2 * #first)
        local per = { 0, 0, 0 }
        for i, e in ipairs(first) do
          fbuf[2 * i - 2] = e[1]; fbuf[2 * i - 1] = e[2]; per[e[1] + 1] = per[e[1] + 1] + 1
        end
        local k = tonumber(ffi.cast("fl26_swiss_first_t", pf)(fbuf, #first))
        log(string.format("fl26swiss: first-season list from %s: %d / %d / %d team ids (%d taken)",
                          from, per[1], per[2], per[3], k))
      end
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
