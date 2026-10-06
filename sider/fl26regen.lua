--[[
fl26regen -- loader for fl26regen.dll: regens are new players.

In Master League the game never adds a player. A retiring player is turned back into a
16-year-old in place -- same id, same name, same face, and the same potential, so a
regenerated star is the same star again. The DLL wraps that function (0x141534cc0) and the
save loader (0x1412e5eb0):

  * a regen gets a new potential before the game rebuilds him, so the game's own passes make
    him an ordinary 16-year-old most of the time (a bell curve around the database's middle,
    and now and then a real talent) -- you cannot tell which one from his ratings at 16;
  * a regen gets a new name: a family name and a given name of two other players of the same
    country, in that country's order, with the shirt spelling of the family name;
  * the save does not keep names, so after every load the DLL finds the regens again (younger
    than the database says they should be by now) and gives each the same name back;
  * a regen does not keep the old player's face: the game finds a real face and a portrait by the
    player id alone, so this loader sends those two file requests of a regen to a name that does
    not exist, and the game draws the generic face from his appearance data (FACES below);
  * with the face pack (modules\fl26regen_faces.bin and a livecpk root with
    common\render\symbol\player\regen\<n>.dds) a regen gets one of the pack's faces of his part
    of the world, and the portrait that goes with it. The pack holds game renders, so it is
    not in this repository: Mod Studio's module pack carries it, and "Install the modules"
    puts it in place. Without it a regen keeps the generic face.
  * the world's own new players (a new club's squad, an imported squad) would all have the same
    default look: the world file (modulesl26world.txt) lists their ids in "newfaces" lines,
    and with the face pack each gets a pack face of his part of the world and its portrait, as a
    regen does ("newfaces3d": the 3D face only, the player keeps his own portrait). A player
    with his own face is not listed.
  * a player given a face made for another player (Mod Studio's Face) takes that player's
    appearance as well, from "faceapp <his id>:<the face's id>" lines: the face model brings
    the head, the appearance record the body and its skin colour (GitHub #102).

FLAGS: 1 = new names, 2 = new potential; 3 = both.

Log: the DLL keeps a small text log; this loader drains it into sider.log every so often and
on F10, which also prints the counts.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi).
--]]

local m = {}
local FLAGS = 3
local FACES = true        -- hide the real face and portrait of a regen
local DEBUG = false       -- log the first face/portrait file names seen

local dll_log, dll_stats, dll_is, dll_face, dll_faces, logbuf, statbuf
local nfaces = 0
local ncopies = 0
local ticks = 0
local hidden = 0

local function drain(reason)
  if not dll_log then return end
  local n = tonumber(dll_log(logbuf, 4096))
  if n > 0 then
    for line in ffi.string(logbuf, n):gmatch("[^\n]+") do log("fl26regen: " .. line) end
  end
  if reason then
    dll_stats(statbuf)
    log(string.format("fl26regen: %s -- regens %d (named %d, new potential %d, past the side table %d); loads %d, named again %d, %d year(s) played; %d names in the pools",
                      reason, tonumber(statbuf[0]), tonumber(statbuf[1]), tonumber(statbuf[6]), tonumber(statbuf[7]),
                      tonumber(statbuf[2]), tonumber(statbuf[3]), tonumber(statbuf[4]), tonumber(statbuf[5])))
    log(string.format("fl26regen: %d face/portrait requests of regens hidden", hidden))
  end
end

function m.make_key(ctx, filename)
  ticks = ticks + 1
  if ticks % 32 == 0 then
    drain(nil)
    if nfaces > 0 or ncopies > 0 then dll_faces() end
  end
  return nil
end

-- Asset\model\character\face\real\<id>\...  and  common\render\symbol\player\<id>.dds
local sep = string.char(92)
local FACE = "face" .. sep .. "real" .. sep .. "(%d+)" .. sep
local PORTRAIT = "symbol" .. sep .. "player" .. sep .. "(%d+)%.dds$"
local seen = 0
function m.rewrite(ctx, filename)
  local id = filename:match(FACE)
  local what = "face"
  if not id then id = filename:match(PORTRAIT); what = "portrait" end
  if not id then return nil end
  if DEBUG and seen < 80 then seen = seen + 1; log("fl26regen: [debug] " .. filename) end
  if dll_is(tonumber(id)) == 0 then
    -- a new player of the world: only his portrait, the pack face is in his appearance data
    if what == "face" or nfaces == 0 then return nil end
    local k = tonumber(dll_face(tonumber(id)))
    if k < 0 then return nil end
    return (filename:gsub(PORTRAIT, "symbol" .. sep .. "player" .. sep .. "regen" .. sep .. k .. ".dds", 1))
  end
  hidden = hidden + 1
  if hidden <= 20 then log(string.format("fl26regen: %s of regen %s hidden (%s)", what, id, filename)) end
  if what == "face" then
    return (filename:gsub(FACE, "face" .. sep .. "real" .. sep .. "regen" .. sep, 1))
  end
  local k = nfaces > 0 and tonumber(dll_face(tonumber(id))) or -1
  if k >= 0 then
    return (filename:gsub(PORTRAIT, "symbol" .. sep .. "player" .. sep .. "regen" .. sep .. k .. ".dds", 1))
  end
  return (filename:gsub(PORTRAIT, "symbol" .. sep .. "player" .. sep .. "regen.dds", 1))
end

function m.key_down(ctx, vkey)
  if vkey == 0x79 then drain("F10 report") end      -- F10
end

-- "newfaces 179673-179900 179950" / "newfaces3d 179901": the world's new players
local function new_players(add, dllpath)
  local f = io.open((dllpath:gsub("fl26regen%.dll$", "fl26world.txt")), "r")
  if not f then return end
  local n, players = 0, 0
  for line in f:lines() do
    local kind, rest = line:match("^%s*(newfaces3?d?)%s+(.*)$")
    if kind == "newfaces" or kind == "newfaces3d" then
      for a, b in rest:gmatch("(%d+)%-?(%d*)") do
        local lo = tonumber(a)
        local hi = b ~= "" and tonumber(b) or lo
        n = tonumber(add(lo, hi, kind == "newfaces3d" and 1 or 0))
        players = players + hi - lo + 1
      end
    end
  end
  f:close()
  if players > 0 then log(string.format("fl26regen: %d new players of the world get pack faces (%d ranges)", players, n)) end
end

-- "faceapp 179700:36912 179701:40510": player 179700 wears the face made for 36912 (#102)
local function face_copies(copy, dllpath)
  local f = io.open((dllpath:gsub("fl26regen%.dll$", "fl26world.txt")), "r")
  if not f then return 0 end
  local n = 0
  for line in f:lines() do
    local rest = line:match("^%s*faceapp%s+(.*)$")
    if rest then
      for to, from in rest:gmatch("(%d+):(%d+)") do n = tonumber(copy(tonumber(to), tonumber(from))) end
    end
  end
  f:close()
  if n > 0 then log(string.format("fl26regen: %d player(s) take the appearance of the face they were given", n)) end
  return n
end

function m.init(ctx)
  if ffi == nil then log("fl26regen: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[
    void*    LoadLibraryA(const char*);
    void*    GetProcAddress(void*, const char*);
    void*    GetModuleHandleA(const char*);
    unsigned long GetLastError(void);
    typedef int  (*fl26_regen_install_t)(uint64_t, int);
    typedef int  (*fl26_regen_log_t)(char*, int);
    typedef void (*fl26_regen_stats_t)(uint32_t*);
    typedef int  (*fl26_regen_is_t)(uint32_t);
    typedef int  (*fl26_regen_faces_load_t)(const char*);
    typedef int  (*fl26_regen_faces_t)(void);
    typedef int  (*fl26_regen_new_t)(uint32_t, uint32_t, int);
    typedef int  (*fl26_regen_copy_t)(uint32_t, uint32_t);
  ]])
  local sep = string.char(92)
  local dllpath = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26regen.dll"
  local h = ffi.C.LoadLibraryA(dllpath)
  if h == nil then
    log(string.format("fl26regen: LoadLibraryA failed (err %d): %s", tonumber(ffi.C.GetLastError()), dllpath)); return
  end
  local pi = ffi.C.GetProcAddress(h, "fl26_regen_install")
  local pl = ffi.C.GetProcAddress(h, "fl26_regen_log")
  local ps = ffi.C.GetProcAddress(h, "fl26_regen_stats")
  local pq = ffi.C.GetProcAddress(h, "fl26_regen_is")
  if pi == nil or pl == nil or ps == nil or pq == nil then log("fl26regen: GetProcAddress failed"); return end
  local install = ffi.cast("fl26_regen_install_t", pi)
  dll_log   = ffi.cast("fl26_regen_log_t", pl)
  dll_stats = ffi.cast("fl26_regen_stats_t", ps)
  dll_is    = ffi.cast("fl26_regen_is_t", pq)
  logbuf, statbuf = ffi.new("char[4096]"), ffi.new("uint32_t[8]")
  local pfl = ffi.C.GetProcAddress(h, "fl26_regen_faces_load")
  local pf1 = ffi.C.GetProcAddress(h, "fl26_regen_face")
  local pfa = ffi.C.GetProcAddress(h, "fl26_regen_faces")

  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(install(base, FLAGS))
  if status == 0 then
    ctx.register("livecpk_make_key", m.make_key)
    ctx.register("key_down", m.key_down)
    if FACES and pfl ~= nil and pf1 ~= nil and pfa ~= nil then
      dll_face  = ffi.cast("fl26_regen_is_t", pf1)
      dll_faces = ffi.cast("fl26_regen_faces_t", pfa)
      local pack = dllpath:gsub("fl26regen%.dll$", "fl26regen_faces.bin")
      nfaces = tonumber(ffi.cast("fl26_regen_faces_load_t", pfl)(pack))
      log(nfaces > 0 and string.format("fl26regen: face pack loaded, %d faces", nfaces)
                     or "fl26regen: no face pack (" .. pack .. "), regens keep the generic face")
      local pnew = ffi.C.GetProcAddress(h, "fl26_regen_new")
      if nfaces > 0 and pnew ~= nil then new_players(ffi.cast("fl26_regen_new_t", pnew), dllpath) end
    end
    local pcopy = ffi.C.GetProcAddress(h, "fl26_regen_copy")
    if pfa ~= nil and pcopy ~= nil then
      dll_faces = dll_faces or ffi.cast("fl26_regen_faces_t", pfa)
      ncopies = face_copies(ffi.cast("fl26_regen_copy_t", pcopy), dllpath)
    end
    if FACES then ctx.register("livecpk_rewrite", m.rewrite) end
    drain(nil)
    log("fl26regen: live (F10 = report)")
  else
    local msg = ({ [2] = "regen function signature mismatch", [3] = "save loader signature mismatch",
                   [4] = "an operand is not what this build expects", [5] = "out of memory",
                   [6] = "could not wrap a function" })[status] or "unknown"
    log("fl26regen: install FAILED (status " .. status .. ") -- " .. msg .. ". The game is unmodified.")
  end
end

return m
