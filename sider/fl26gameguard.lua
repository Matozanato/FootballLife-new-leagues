--[[
fl26gameguard -- a League Builder world made for the other game does not start in this one.

Why (mato 07.11.2026). A world FL Mod Studio builds for FL 2027 -- the Megapack: 204 leagues,
~103,000 players, FL 2027's 4800 clubs -- does not fit FL26, whose caps set holds 2400 clubs and
61905 players: the game would read the world's tables past the end of its arrays. An FL26 world
in FL 2027 replaces FL 2027's own tables with FL26's. Mod Studio refuses to install or switch on
such a world, but its folder can still be copied in by hand, with a cpk.root line typed into
sider.ini.

How it knows. Build writes the game into the world file, right after its `world` line
(tools/worldgame.py):  game fl27 teams=<clubs> players=<players>. This module is the first
lua.module in sider.ini, so it runs before fl26caps and before the game reads a single table.
It reads that line in the world file of every switched-on cpk.root folder (livecpk\<world>\
fl26world.txt) and in modules\fl26world.txt (what the other modules read), and compares it with
the game's exe (FL_2026.exe is FL26, FL_2027.exe FL 2027).

What it does. All agree, or a world has no game line (built before 07.11.2026): one log line,
nothing else. A world of the other game: sider.log says which and why, a message box says what to
do, and the game closes when it is answered -- before anything is read or written, so the game,
its Edit data and the careers are left exactly as they were. Without ffi (luajit.ext.enabled = 0)
it cannot read the exe's name and only logs that it did not check.
--]]

local m = {}
local SEP = string.char(92)
local TITLE = { fl26 = "FL26", fl27 = "FL 2027" }

local function declare()
  if m.cdef then return end
  -- names of our own: another module may have declared the plain ones already, and declaring a
  -- function twice is an error (fl26caps, fl26joindll do the same)
  ffi.cdef([[
    uint32_t fl26gameguard_GetModuleFileNameA(void*, char*, uint32_t) asm("GetModuleFileNameA");
    int fl26gameguard_MultiByteToWideChar(uint32_t, uint32_t, const char*, int, uint16_t*, int) asm("MultiByteToWideChar");
    int fl26gameguard_WideCharToMultiByte(uint32_t, uint32_t, const uint16_t*, int, char*, int, const char*, int*) asm("WideCharToMultiByte");
    int fl26gameguard_MessageBoxA(void*, const char*, const char*, uint32_t) asm("MessageBoxA");
    void* fl26gameguard_GetCurrentProcess(void) asm("GetCurrentProcess");
    int fl26gameguard_TerminateProcess(void*, uint32_t) asm("TerminateProcess");
  ]])
  m.cdef = true
end

-- the game this exe is: "fl27" for FL_2027.exe, else "fl26" (FL_2026.exe, PES2021.exe)
local function this_game()
  local buf = ffi.new("char[?]", 1040)
  local n = ffi.C.fl26gameguard_GetModuleFileNameA(nil, buf, 1040)
  if n == 0 then return nil, "?" end
  local exe = ffi.string(buf, n):match("([^" .. SEP .. "/]+)$") or ""
  return (exe:lower() == "fl_2027.exe") and "fl27" or "fl26", exe
end

-- B294: ctx.sider_dir is UTF-8 and io.open takes the system's code page
local function ansi(path)
  local n = ffi.C.fl26gameguard_MultiByteToWideChar(65001, 0, path, -1, nil, 0)
  if n <= 0 then return path end
  local w = ffi.new("uint16_t[?]", n)
  ffi.C.fl26gameguard_MultiByteToWideChar(65001, 0, path, -1, w, n)
  local k = ffi.C.fl26gameguard_WideCharToMultiByte(0, 0, w, -1, nil, 0, nil, nil)
  if k <= 0 then return path end
  local a = ffi.new("char[?]", k)
  ffi.C.fl26gameguard_WideCharToMultiByte(0, 0, w, -1, a, k, nil, nil)
  return ffi.string(a)
end

local function open(path)
  return io.open(ansi(path), "r") or io.open(path, "r")
end

-- the game line of a world file: game, clubs, players, the world's name; nil without one (the
-- line comes right after the `world` line, before the leagues)
local function stamp(path)
  local f = open(path)
  if not f then return nil end
  local game, rest, name
  for line in f:lines() do
    name = name or line:match("^%s*world%s+(%S+)")
    game, rest = line:match("^%s*game%s+(%w+)(.*)$")
    if game or line:match("^league ") then break end
  end
  f:close()
  if not game or not TITLE[game:lower()] then return nil end
  return game:lower(), rest:match("teams=(%d+)"), rest:match("players=(%d+)"), name or "the world"
end

-- the folders of the switched-on cpk.root lines of sider.ini (relative ones are in the Sider folder)
local function roots(sd)
  local out = {}
  local f = open(sd .. SEP .. "sider.ini")
  if not f then return out end
  for line in f:lines() do
    local v = line:match("^%s*cpk%.root%s*=%s*(.-)%s*$")
    if v then
      v = v:gsub('^"(.*)"$', "%1"):gsub("[/" .. SEP .. "]+$", "")
      if not (v:match("^%a:") or v:match("^[/" .. SEP .. "][/" .. SEP .. "]")) then
        v = sd .. SEP .. v:gsub("^%.[/" .. SEP .. "]", "")
      end
      out[#out + 1] = v
    end
  end
  f:close()
  return out
end

local function refuse(game, exe, where, want, teams, players, name)
  local what = want == "fl27"
    and string.format("it is a world for FL 2027 (%s clubs, %s players; FL26 takes 2400 clubs and 61905 players) "
                      .. "and would break FL26", teams or "?", players or "?")
    or "it is a world for FL26, and FL 2027 has tables of its own"
  log(string.format("fl26gameguard: REFUSED %s (%s) -- %s. This is %s (%s). The game closes before it reads "
                    .. "anything; nothing was written. Switch the world off in FL Mod Studio, or delete its "
                    .. "cpk.root line in sider.ini.", name, where, what, TITLE[game], exe))
  local text = string.format("%s cannot be played here: %s.\n\nThis game is %s. Football Life closes now, "
    .. "before it reads anything, so nothing is damaged.\n\nTo play: open FL Mod Studio and put one of your "
    .. "%s worlds in the game (My world), or delete the line  cpk.root = ...%s  in SiderAddons%ssider.ini "
    .. "(and modules%sfl26world.txt). %s goes in %s.\n\n(%s)",
    name, what, TITLE[game], TITLE[game], name, SEP, SEP, name, TITLE[want], where)
  -- MB_ICONERROR | MB_SYSTEMMODAL | MB_SETFOREGROUND | MB_TOPMOST
  ffi.C.fl26gameguard_MessageBoxA(nil, text, "FL Mod Studio: a world for " .. TITLE[want], 0x10 + 0x1000 + 0x10000 + 0x40000)
  ffi.C.fl26gameguard_TerminateProcess(ffi.C.fl26gameguard_GetCurrentProcess(), 1)
end

function m.init(ctx)
  if ffi == nil then
    log("fl26gameguard: global ffi is nil (luajit.ext.enabled = 0) -- the worlds' game was not checked")
    return
  end
  declare()
  local game, exe = this_game()
  if not game then
    log("fl26gameguard: the exe's name could not be read -- the worlds' game was not checked")
    return
  end
  local sd = ctx.sider_dir:gsub("[/" .. SEP .. "]+$", "")
  local files = { sd .. SEP .. "modules" .. SEP .. "fl26world.txt" }
  for _, r in ipairs(roots(sd)) do files[#files + 1] = r .. SEP .. "fl26world.txt" end
  local seen = 0
  for _, path in ipairs(files) do
    local want, teams, players, name = stamp(path)
    if want then
      seen = seen + 1
      if want ~= game then
        refuse(game, exe, path, want, teams, players, name)
        return
      end
    end
  end
  log(string.format("fl26gameguard: %s (%s): %d world file(s) say their game, all %s", TITLE[game], exe, seen, TITLE[game]))
end

return m
