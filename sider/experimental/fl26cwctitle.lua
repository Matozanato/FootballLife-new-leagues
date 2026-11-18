--[[
fl26cwctitle -- the Club World Cup of 32 (world file line cwc32): its final gives the Master League
title, and the trophy ceremony when a Club World Cup trophy scene is installed.

The title. A live regulation record carries a "next phase" link at +0x78 (the loader sets it from
the phase chain, 0x1414f1cfd -> 0x1414c9f40). The knockout of the cwc32 line came out with
+0x78 = 1 -- regulation 1, the group stage, a chained phase (row dword +0x10 bits 18-20) -- at
least in a career saved before the Club World Cup Build that fl26cwc.dll's mg_check gave the
world's rows. The coach history's title filter (0x140fce0b0, fed by event 0x17 from
EventCompeResultListener) takes only a phase with no parent (+0x76) and no next phase
(+0x78 = 0xffff), so the final never reached the champion check (0x14151b3e0) although the game
knew the winner. Measured 2026-11-18 (a Mod Studio world, ML career, old save): knockout 314
finished, champion = the coach's club, +0x78 = 0001; the Champions League (4), Libertadores (10),
AFC Champions League (16) and Intercontinental knockouts all ffff. With the link cleared the title
went into the career history (checked in the game the same day).
So the knockout's +0x78 is put back to 0xffff -- what a final has. Nothing in the game moves
clubs from the knockout to regulation 1 (fl26swiss does the hand-over itself). It is done before
every match (set_teams) and every 256 file loads (a final skipped with Skip Match has no
set_teams), only in a world with the cwc32 line, only when the record exists, only that u16.

The trophy ceremony. The match's trophy id comes from a fixed table built in the exe at
0x141e54xxx (330 pairs {tournament, trophy}; not found = 0xd9, none). The knockout is not in it,
and the "has a ceremony" test 0x140a7f290 reads that id directly (Sider's trophy_rewrite only
swaps the scene's trophy at 0x141f51855), so the final ended with the generic celebration. The
shipped Club World Cup pair is tournament 1 -> trophy 0xb0 (`mov eax,1` at 0x141e54979, stored
at [rbp+0x658]); regulation 1 is the group stage now and never has a final, so the pair can go
to the knockout -- four bytes of code, checked before they are written.
That is only done when a Club World Cup trophy scene is installed (TROPHY_BASES / TROPHY_FOLDERS
below: SiderAddons\content\cinematics or content\Entrance), or when the cwc32 line says trophy=1;
trophy=0 keeps it off.
Without a scene the player keeps the game's generic celebration, as before.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi). Load it after fl26cwc.
--]]

local m = {}
local KO, TROPHY = 0, nil         -- TROPHY: nil = look for a scene, true / false = the world file says
local owner_fn, getrec_fn
local ticks, last_state = 0, nil

-- a Club World Cup trophy scene: <SiderAddons>\content\<base>\<folder>\<scene file>, base
-- "cinematics" (cinematics.lua of the SP Football Life patch) or "Entrance" (FL26's Entrance.lua);
-- folder as the packs lay it out: one folder, or the final's folder of a pack split by phase
-- (About PES's "PES 2021 Entrance FIFA Club World Cup 2025 V3": Final / Knockout / Groupstage).
-- The first one found counts.
local TROPHY_BASES = { "cinematics", "Entrance" }
local TROPHY_FOLDERS = {
  [[FIFA Club World Cup\Final]], [[FIFA Club World Cup 2025\Final]], "FIFA Club World Cup 2025",
  "FIFA Club World Cup", "CWC", "Club World Cup",
}
local TROPHY_FILE = [[common\demo\fixdemo\end\cut_data\end_trophy_01_acl.fdc]]

local function root_of(ctx)
  local sep = string.char(92)
  return ctx.sider_dir:gsub("[/" .. sep .. "]+$", ""), sep
end

local function read_world(ctx)
  local root, sep = root_of(ctx)
  local f = io.open(root .. sep .. "modules" .. sep .. "fl26world.txt", "r")
  if not f then return end
  for line in f:lines() do
    local rest = line:match("^%s*cwc32%s+(.*)$")
    if rest then
      KO = tonumber(rest:match("ko=(%d+)") or 0) or 0
      local t = rest:match("trophy=(%d)")
      if t then TROPHY = (t == "1") end
    end
  end
  f:close()
end

local function scene_installed(ctx)
  local root, sep = root_of(ctx)
  for _, base in ipairs(TROPHY_BASES) do
    for _, folder in ipairs(TROPHY_FOLDERS) do
      local rel = base .. sep .. folder
      local f = io.open(root .. sep .. "content" .. sep .. rel .. sep .. TROPHY_FILE, "rb")
      if f then f:close(); return rel end
    end
  end
  return nil
end

-- the title: the knockout's next-phase link cleared
local function fix(why)
  local owner = owner_fn()
  if owner == nil then return end
  local blk = ffi.cast("uint8_t**", ffi.cast("uint8_t*", owner) + 0x48)[0]
  if blk == nil then return end
  local r = getrec_fn(blk, KO)
  if r == nil or r == blk + 0xd0b77c then return end          -- not in this career
  local nxt = ffi.cast("uint16_t*", r + 0x78)
  if nxt[0] ~= 0xffff then
    local old = tonumber(nxt[0])
    nxt[0] = 0xffff
    log(string.format("fl26cwctitle: reg %d -- next phase %d cleared, the final gives the title (%s)", KO, old, why))
    last_state = "cleared"
  elseif last_state == nil then
    log(string.format("fl26cwctitle: reg %d -- no next phase already (%s)", KO, why))
    last_state = "none"
  end
end

-- the ceremony: the shipped Club World Cup trophy pair handed to the knockout
local TROPHY_AT = 0x141e54979
local TROPHY_ORIG = { 0xb8, 0x01, 0x00, 0x00, 0x00, 0x66, 0x89, 0x85, 0x58, 0x06, 0x00, 0x00 }
local function trophy_patch()
  local p = ffi.cast("uint8_t*", TROPHY_AT)
  if p[0] == 0xb8 and ffi.cast("uint32_t*", TROPHY_AT + 1)[0] == KO then
    log("fl26cwctitle: trophy -- tournament " .. KO .. " already has the Club World Cup trophy")
    return
  end
  for i = 1, #TROPHY_ORIG do
    if p[i - 1] ~= TROPHY_ORIG[i] then
      log(string.format("fl26cwctitle: trophy -- unexpected bytes at %x (byte %d = %02x): left alone, the final keeps the generic celebration",
          TROPHY_AT, i - 1, p[i - 1]))
      return
    end
  end
  local old = ffi.new("uint32_t[1]")
  if ffi.C.fl26cwctitle_VirtualProtect(ffi.cast("void*", TROPHY_AT), 16, 0x40, old) == 0 then
    log("fl26cwctitle: trophy -- VirtualProtect failed: left alone")
    return
  end
  ffi.cast("uint32_t*", TROPHY_AT + 1)[0] = KO
  ffi.C.fl26cwctitle_VirtualProtect(ffi.cast("void*", TROPHY_AT), 16, old[0], old)
  ffi.C.fl26cwctitle_FlushInstructionCache(ffi.C.fl26cwctitle_GetCurrentProcess(), ffi.cast("void*", TROPHY_AT), 16)
  log(string.format("fl26cwctitle: trophy -- the Club World Cup trophy (0xb0) goes to tournament %d instead of 1", KO))
end

function m.set_teams(ctx, home, away)
  fix("before the match")
end

function m.make_key(ctx, filename)
  ticks = ticks + 1
  if ticks % 256 == 0 then fix("day") end
  return nil
end

function m.init(ctx)
  if ffi == nil then log("fl26cwctitle: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  read_world(ctx)
  if KO <= 175 or KO >= 1024 then
    log("fl26cwctitle: the world file has no cwc32 line (Club World Cup of 32 off) -- nothing installed")
    return
  end
  owner_fn = ffi.cast("void* (*)(void)", 0x1414b6a60)
  getrec_fn = ffi.cast("uint8_t* (*)(void*, uint16_t)", 0x1414bb000)
  ffi.cdef([[
    int fl26cwctitle_VirtualProtect(void*, size_t, uint32_t, uint32_t*) __asm__("VirtualProtect");
    int fl26cwctitle_FlushInstructionCache(void*, void*, size_t) __asm__("FlushInstructionCache");
    void* fl26cwctitle_GetCurrentProcess(void) __asm__("GetCurrentProcess");
  ]])
  log("fl26cwctitle: the Club World Cup knockout is reg " .. KO .. "; its final gives the Master League title")
  local scene = scene_installed(ctx)
  if TROPHY == false then
    log("fl26cwctitle: trophy -- off (cwc32 trophy=0): the final keeps the generic celebration")
  elseif TROPHY == true or scene then
    if scene then log("fl26cwctitle: trophy -- scene found: content\\" .. scene) end
    trophy_patch()
  else
    log("fl26cwctitle: trophy -- no Club World Cup trophy scene in content\\cinematics or content\\Entrance: the final keeps the generic celebration " ..
        "(trophy=1 on the cwc32 line turns the game's own trophy on)")
  end
  ctx.register("set_teams", m.set_teams)
  ctx.register("livecpk_make_key", m.make_key)
end

return m
