--[[
fl26compcache -- loader for fl26compcache.dll: no 20-30 minute loading screen at the end of the
transfer window in a big world.

Speed fix, NOT a capacity patch.  Measured 13.10.2026 on a 0.2.2 world (2400 clubs, 600
regulations, 61905 players): day 30 (end of January) sat on the loading screen for more than
half an hour.  The game scores every player's club against every competition, and for every
player it looks each competition up again from scratch -- the same answer sixty thousand times.
The DLL keeps each competition's lookup for the length of that one loop.  See
tools/native/fl26compcache.c.

Install:
  1. copy fl26compcache.dll and this file to <game>\SiderAddons\modules\
  2. sider.ini, after lua.module = "fl26walk.lua":   lua.module = "fl26compcache.lua"
  3. start the game; sider.log says "fl26compcache: the per-player competition scan ..."
     and every such loop leaves a line in modules\fl26compcache.log (its time, cache hits)

Requires sider.ini: luajit.ext.enabled = 1 (global ffi).
--]]

local m = {}

-- B294 (Pelda 30.10.): ctx.sider_dir is UTF-8, and LoadLibraryA reads a name in the system's
-- code page: with the game in a folder named with a Czech u-ring, no DLL of ours loaded (error 126)
-- and the leagues had no fixtures. LoadLibraryW takes any folder name; LoadLibraryA is what is
-- left when another mod declared the wide calls otherwise.
local function load_dll(path)
  -- one declaration a call: one another module made already must not stop the next
  pcall(ffi.cdef, "int MultiByteToWideChar(unsigned int, unsigned long, const char*, int, uint16_t*, int);")
  pcall(ffi.cdef, "void* LoadLibraryW(const uint16_t*);")
  local ok, h = pcall(function()
    local n = ffi.C.MultiByteToWideChar(65001, 0, path, -1, nil, 0)
    if n <= 0 then return nil end
    local w = ffi.new("uint16_t[?]", n)
    ffi.C.MultiByteToWideChar(65001, 0, path, -1, w, n)
    return ffi.C.LoadLibraryW(w)
  end)
  if ok and h ~= nil then return h end
  return ffi.C.LoadLibraryA(path)
end

function m.init(ctx)
  if ffi == nil then log("fl26compcache: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[
    void*    LoadLibraryA(const char*);
    void*    GetProcAddress(void*, const char*);
    void*    GetModuleHandleA(const char*);
    unsigned long GetLastError(void);
    typedef int (*fl26_compcache_install_t)(uint64_t);
    typedef int (*fl26_compcache_log_t)(char*, int);
  ]])
  local sep = string.char(92)
  local dllpath = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26compcache.dll"
  local h = load_dll(dllpath)
  if h == nil then
    log(string.format("fl26compcache: LoadLibraryA failed (err %d): %s", tonumber(ffi.C.GetLastError()), dllpath)); return
  end
  local pi = ffi.C.GetProcAddress(h, "fl26_compcache_install")
  local pl = ffi.C.GetProcAddress(h, "fl26_compcache_log")
  if pi == nil or pl == nil then log("fl26compcache: GetProcAddress failed"); return end
  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(ffi.cast("fl26_compcache_install_t", pi)(base))
  local buf = ffi.new("char[2048]")
  ffi.cast("fl26_compcache_log_t", pl)(buf, 2048)
  for line in ffi.string(buf):gmatch("[^\n]+") do log(line) end
  if status ~= 0 then log(string.format("fl26compcache: not installed (%d)", status)) end
end

return m
