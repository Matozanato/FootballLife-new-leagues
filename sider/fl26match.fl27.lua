-- fl26match.lua: the match table's allocator and lookup from fl26match.dll (u32 match ids, step M1)
-- FL 2027's copy (lbpack FL27): ids from 65536 and players past 65535 on, as the GigaPack was
-- tested with (B408: a season of its 345 leagues has over 65535 matches, a database 134,551 players)
--
-- Goes after fl26caps.lua in sider.ini: the DLL reads where fl26caps put the match table and how
-- big it made it from the patched code. With FIRST = 0 and MASK = 0xffff the game sees no
-- difference; FIRST = 65536 and MASK = 0xffffffff come once the id travels 32-bit everywhere,
-- and then every lookup that misses is a site still cutting the id to 16 bits (F10: the list;
-- modules\fl26match.stats has the same every 5 s).
-- needs luajit.ext.enabled = 1 (the global ffi); C names under this module's own, so no clash
local m = { version = "0.1" }

local FIRST, MASK = 65536, 0xffffffff
local PLAYERS = true -- players past 65535 (lift16f): a key whose index word is 0xffff is found by its id, plus the line-up guard
local PLAYER_CAP = 0  -- records searched by id; 0 = the set's search bound (0x1414bc0d5); more than that bound is refused
local TWINS = false   -- test: true = ids low and high in turn (twins from the first match); a number n = wrap after n ids from 65536

ffi.cdef [[
  void* fl26match_LoadLibraryA(const char*) __asm__("LoadLibraryA");
  void* fl26match_LoadLibraryW(const uint16_t*) __asm__("LoadLibraryW");
  int   fl26match_MultiByteToWideChar(uint32_t, uint32_t, const char*, int, uint16_t*, int) __asm__("MultiByteToWideChar");
  void* fl26match_GetProcAddress(void*, const char*) __asm__("GetProcAddress");
  typedef int  (*fl26match_install_t)(uint32_t, uint32_t);
  typedef void (*fl26match_stats_t)(uint32_t*);
  typedef int  (*fl26match_misses_t)(uint32_t*, uint64_t*, int);
  typedef int  (*fl26match_statsfile_t)(const char*);
  typedef void (*fl26match_twins_t)(int);
  typedef int  (*fl26match_player_install_t)(uint32_t);
  typedef int  (*fl26match_player_stats_t)(uint64_t*);
  uint32_t fl26match_GetModuleFileNameA(void*, char*, uint32_t) __asm__("GetModuleFileNameA");
]]

local h

local function load_dll(path)
  local n = ffi.C.fl26match_MultiByteToWideChar(65001, 0, path, -1, nil, 0)
  if n > 0 then
    local w = ffi.new("uint16_t[?]", n)
    ffi.C.fl26match_MultiByteToWideChar(65001, 0, path, -1, w, n)
    local r = ffi.C.fl26match_LoadLibraryW(w)
    if r ~= nil then return r end
  end
  return ffi.C.fl26match_LoadLibraryA(path)
end

local function report(why)
  local s = ffi.new("uint32_t[10]")
  ffi.cast("fl26match_stats_t", ffi.C.fl26match_GetProcAddress(h, "fl26_match_stats"))(s)
  log(string.format("fl26match: %s -- table +0x%x, %d records, first %d, mask 0x%x; %d handed out, %d refused (full), "
    .. "%d found, %d found by scan, %d missed, %d asked for no match",
    why, s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9]))
  local ids, rets = ffi.new("uint32_t[32]"), ffi.new("uint64_t[96]")
  local n = ffi.cast("fl26match_misses_t", ffi.C.fl26match_GetProcAddress(h, "fl26_match_misses"))(ids, rets, 32)
  for i = 0, n - 1 do
    log(string.format("fl26match: miss %d id %d from %x %x %x", i, ids[i],
      tonumber(rets[3 * i]), tonumber(rets[3 * i + 1]), tonumber(rets[3 * i + 2])))
  end
  local ps = ffi.C.fl26match_GetProcAddress(h, "fl26_player_stats")
  local p = ffi.new("uint64_t[10]")
  if ps ~= nil and ffi.cast("fl26match_player_stats_t", ps)(p) ~= 0 then
    log(string.format("fl26match: players cap %d: word steps %d, full scans %d (last key %x at %d), map hits %d, misses %d (last %x), line-up guard %d",
      tonumber(p[8]), tonumber(p[0]), tonumber(p[1]), tonumber(p[4]), tonumber(p[5]), tonumber(p[6]), tonumber(p[2]), tonumber(p[3]), tonumber(p[7])))
  end
end

function m.key_down(ctx, vkey)
  if vkey == 0x79 and h then report("F10") end
end

function m.init(ctx)
  local sep = string.char(92)
  -- B408 (morpheus 10.11.2026, GigaPack beta 1): FL 2027 only. Mod Studio installs it for both
  -- games; FL26's caps set keeps 16-bit match ids, so in FL_2026.exe it does nothing
  local buf = ffi.new("char[?]", 1040)
  local n = ffi.C.fl26match_GetModuleFileNameA(nil, buf, 1040)
  local exe = ffi.string(buf, n):match("([^" .. sep .. "/]+)$") or ""
  if exe:lower() ~= "fl_2027.exe" then
    log("fl26match: " .. exe .. " is not FL 2027 -- the game keeps its own match table (FL 2027 only)")
    return
  end
  local dir = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep
  local dllpath = dir .. "fl26match.dll"
  h = load_dll(dllpath)
  if h == nil then log("fl26match: fl26match.dll did not load -- the game keeps its own 16-bit match table"); return end
  local rc = ffi.cast("fl26match_install_t", ffi.C.fl26match_GetProcAddress(h, "fl26_match_install"))(FIRST, MASK)
  if rc ~= 0 then
    log(string.format("fl26match: not installed (%d: %s) -- the game keeps its own match table", rc,
      ({ [2] = "allocator is not the game's", [3] = "lookup is not the game's (or fl26caps did not run first)",
         [4] = "first index past the table", [5] = "VirtualProtect failed", [6] = "slot reader is not the game's" })[rc] or "?"))
    h = nil; return
  end
  if PLAYERS then
    local p = ffi.C.fl26match_GetProcAddress(h, "fl26_player_install")
    local prc = p ~= nil and ffi.cast("fl26match_player_install_t", p)(PLAYER_CAP) or -1
    log("fl26match: players past 65535 " .. (prc == 0 and "on" or ("not hooked (" .. prc .. ": " .. (({
      [2] = "a signature is not the game's (or already hooked)", [3] = "PLAYER_CAP past the set's bound",
      [4] = "no memory near the exe", [5] = "VirtualProtect failed" })[prc] or "?") .. ")")))
  end
  if TWINS then
    local t = ffi.C.fl26match_GetProcAddress(h, "fl26_match_twins")
    if t ~= nil then ffi.cast("fl26match_twins_t", t)(TWINS == true and 1 or TWINS); log("fl26match: twins on (" .. tostring(TWINS) .. ")") end
  end
  report("installed")
  ffi.cast("fl26match_statsfile_t", ffi.C.fl26match_GetProcAddress(h, "fl26_match_statsfile"))(dir .. "fl26match.stats")
  ctx.register("key_down", m.key_down)
end

return m
