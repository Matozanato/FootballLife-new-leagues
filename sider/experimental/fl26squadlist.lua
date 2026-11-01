--[[
fl26squadlist -- loader for fl26squadlist.dll: Select Team lists the league's clubs on a league
row, and the players of the club under the cursor inside the league.

What the player sees. The Select Team screen (Master League > Database > Team Info, League mode,
Edit and the other screens that list leagues and then clubs) has two columns: the leagues and,
after Confirm, the clubs of that league. The panel on the right shows "Squad List", the players
of the club under the cursor, while the cursor is in the club column. In the league column the
game leaves that panel empty: red rows with nothing in them while scrolling through the leagues
(the same in Konami's game, in FL26 2.2 and in FL27 1.00). Only the start of a new Master League,
built with League Info on, shows cups and promotion there instead, and that stays as it is.

With the DLL a league row lists that league's clubs, in the order the club column has them, one
club per row with its crest. Confirm, and the panel shows the players of the club under the cursor, as before.
How it does that is in tools/native/fl26squadlist.c: the panel's list already knows how to draw
clubs (other screens use it for that); the DLL gives it the league's clubs in the league column,
draws a squad row's name as the club's name and puts the club's crest where the position badge
is. The crest cell is not in the game's layout: Mod Studio writes the world a copy of it with one
(teamSelectSingle.bin, tools/mkteamcrest.py), at Build and when a world built before is switched
on. Without it (another mod's layout) the badge is left empty.

(2026-11-01: the first version of this module, pure Lua, showed the squad of the league's first
club on a league row. That is not what a league row is for: it lists the clubs now.)

Install:
  1. copy fl26squadlist.dll and this file to <game>\SiderAddons\modules\
  2. sider.ini, after lua.module = "fl26catlist.lua":   lua.module = "fl26squadlist.lua"
  3. start the game; sider.log says "fl26squadlist: Select Team lists the league's clubs ..."

Every site is checked byte for byte before anything is written; one mismatch and nothing is
patched (sider.log: MISMATCH, ABORTED). FL26 2.2 and FL27 1.00 have the same bytes at the same
addresses.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi).
--]]

local m = {}

local function load_dll(path)
  local n = ffi.C.fl26squadlist_MultiByteToWideChar(65001, 0, path, -1, nil, 0)
  if n > 0 then
    local w = ffi.new("uint16_t[?]", n)
    ffi.C.fl26squadlist_MultiByteToWideChar(65001, 0, path, -1, w, n)
    local h = ffi.C.fl26squadlist_LoadLibraryW(w)
    if h ~= nil then return h end
  end
  return ffi.C.fl26squadlist_LoadLibraryA(path)
end

function m.init(ctx)
  if ffi == nil then log("fl26squadlist: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[
    void*    fl26squadlist_LoadLibraryA(const char*) __asm__("LoadLibraryA");
    void*    fl26squadlist_LoadLibraryW(const uint16_t*) __asm__("LoadLibraryW");
    int      fl26squadlist_MultiByteToWideChar(unsigned int, unsigned long, const char*, int, uint16_t*, int) __asm__("MultiByteToWideChar");
    void*    fl26squadlist_GetProcAddress(void*, const char*) __asm__("GetProcAddress");
    void*    fl26squadlist_GetModuleHandleA(const char*) __asm__("GetModuleHandleA");
    unsigned long fl26squadlist_GetLastError(void) __asm__("GetLastError");
    typedef int (*fl26_squadlist_install_t)(uint64_t);
    typedef int (*fl26_squadlist_log_t)(char*, int);
  ]])
  local sep = string.char(92)
  local dllpath = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26squadlist.dll"
  local h = load_dll(dllpath)
  if h == nil then
    log(string.format("fl26squadlist: LoadLibraryA failed (err %d): %s",
                      tonumber(ffi.C.fl26squadlist_GetLastError()), dllpath))
    return
  end
  local pi = ffi.C.fl26squadlist_GetProcAddress(h, "fl26_squadlist_install")
  local pl = ffi.C.fl26squadlist_GetProcAddress(h, "fl26_squadlist_log")
  if pi == nil or pl == nil then log("fl26squadlist: GetProcAddress failed"); return end
  local base = ffi.cast("uint64_t", ffi.C.fl26squadlist_GetModuleHandleA(nil))
  local status = tonumber(ffi.cast("fl26_squadlist_install_t", pi)(base))
  local buf = ffi.new("char[2048]")
  ffi.cast("fl26_squadlist_log_t", pl)(buf, 2048)
  for line in ffi.string(buf):gmatch("[^\n]+") do log(line) end
  if status ~= 0 then log(string.format("fl26squadlist: not installed (%d)", status)) end
end

return m
