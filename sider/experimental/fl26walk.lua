--[[
fl26walk -- loader for fl26walk.dll: faster Master League creation (and every day advance)
when the user's club plays in one of the added leagues.

Speed fix, NOT a capacity patch.  Measured 08.10.2026, after fl26regfast and the fl26swiss
regulation index: creating a Master League with a Druga NL club still took 113 s on the
loading screen, a Bosnian club 60 s, a League Two club no time at all.  The game asks
"what is this day for the user's club" (0x14150d990) once per day while it walks the
calendar to the next match, up to 365 days ahead, and every one of those questions starts
by looking up the user's club and which league it plays in -- the same answer each day.
The DLL keeps that answer for the length of one walk.  See tools/native/fl26walk.c.

Install:
  1. copy fl26walk.dll and this file to <game>\SiderAddons\modules\
  2. sider.ini, after lua.module = "fl26regfast.lua":   lua.module = "fl26walk.lua"
  3. start the game; sider.log says "fl26walk: day walks reuse the user's club ..."

Requires sider.ini: luajit.ext.enabled = 1 (global ffi).
--]]

local m = {}

function m.init(ctx)
  if ffi == nil then log("fl26walk: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[
    void*    LoadLibraryA(const char*);
    void*    GetProcAddress(void*, const char*);
    void*    GetModuleHandleA(const char*);
    unsigned long GetLastError(void);
    typedef int (*fl26_walk_install_t)(uint64_t);
    typedef int (*fl26_walk_log_t)(char*, int);
  ]])
  local sep = string.char(92)
  local dllpath = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26walk.dll"
  local h = ffi.C.LoadLibraryA(dllpath)
  if h == nil then
    log(string.format("fl26walk: LoadLibraryA failed (err %d): %s", tonumber(ffi.C.GetLastError()), dllpath)); return
  end
  local pi = ffi.C.GetProcAddress(h, "fl26_walk_install")
  local pl = ffi.C.GetProcAddress(h, "fl26_walk_log")
  if pi == nil or pl == nil then log("fl26walk: GetProcAddress failed"); return end
  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(ffi.cast("fl26_walk_install_t", pi)(base))
  local buf = ffi.new("char[2048]")
  ffi.cast("fl26_walk_log_t", pl)(buf, 2048)
  for line in ffi.string(buf):gmatch("[^\n]+") do log(line) end
  if status ~= 0 then log(string.format("fl26walk: not installed (%d)", status)) end
end

return m
