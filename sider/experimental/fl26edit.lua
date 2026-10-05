--[[
fl26edit -- loader for fl26edit.dll: Edit mode keeps the changes made to our clubs (GitHub #55).

Why: the Edit data has room for 750 clubs per table (team data, squad, tactics), and every save
fills it with the game's own 749 first, so a change to a club of ours (name, colours, kit numbers,
formation, a squad imported from a .ted file) is never stored and is gone after the next load.

The DLL gives those tables room for 2048 clubs in memory. The EDIT file stays exactly what the
game writes: the first 749 clubs of each table, so a game without this module still loads it.
The clubs past 749 -- ours -- go to EDIT00000000.fl26x next to it, and come back on the next load;
the one before stays as EDIT00000000.fl26x.prev, for a save answered No at "Overwrite data. Proceed?".

It has to install before the game makes its Edit data (at start-up); if the Edit data is already
there, the DLL patches nothing and says so in sider.log.

Log: the DLL keeps a small text log; this loader drains it into sider.log now and then and on F10.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi).
--]]

local m = {}
local dll_log, dll_stats, logbuf, statbuf
local ticks = 0

local function drain(reason)
  if not dll_log then return end
  local n = tonumber(dll_log(logbuf, 4096))
  if n > 0 then
    for line in ffi.string(logbuf, n):gmatch("[^\n]+") do log("fl26edit: " .. line) end
  end
  if reason then
    dll_stats(statbuf)
    log(string.format("fl26edit: %s -- tables built %d, clubs read from .fl26x %d, saves %d, clubs written to .fl26x %d, full tables %d",
                      reason, tonumber(statbuf[0]), tonumber(statbuf[1]), tonumber(statbuf[2]),
                      tonumber(statbuf[3]), tonumber(statbuf[4])))
  end
end

function m.make_key(ctx, filename)
  ticks = ticks + 1
  if ticks % 64 == 0 then drain(nil) end
  return nil
end

function m.key_down(ctx, vkey)
  if vkey == 0x79 then drain("F10 report") end      -- F10
end

function m.init(ctx)
  if ffi == nil then log("fl26edit: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[
    void*    LoadLibraryA(const char*);
    void*    GetProcAddress(void*, const char*);
    void*    GetModuleHandleA(const char*);
    unsigned long GetLastError(void);
    typedef int  (*fl26_edit_install_t)(uint64_t);
    typedef int  (*fl26_edit_log_t)(char*, int);
    typedef void (*fl26_edit_stats_t)(uint32_t*);
  ]])
  local sep = string.char(92)
  local dllpath = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26edit.dll"
  local h = ffi.C.LoadLibraryA(dllpath)
  if h == nil then
    log(string.format("fl26edit: LoadLibraryA failed (err %d): %s", tonumber(ffi.C.GetLastError()), dllpath)); return
  end
  local pi = ffi.C.GetProcAddress(h, "fl26_edit_install")
  local pl = ffi.C.GetProcAddress(h, "fl26_edit_log")
  local ps = ffi.C.GetProcAddress(h, "fl26_edit_stats")
  if pi == nil or pl == nil or ps == nil then log("fl26edit: GetProcAddress failed"); return end
  dll_log   = ffi.cast("fl26_edit_log_t", pl)
  dll_stats = ffi.cast("fl26_edit_stats_t", ps)
  logbuf, statbuf = ffi.new("char[4096]"), ffi.new("uint32_t[6]")
  local base = ffi.cast("uint64_t", ffi.C.GetModuleHandleA(nil))
  local status = tonumber(ffi.cast("fl26_edit_install_t", pi)(base))
  drain(nil)
  if status == 0 then
    ctx.register("livecpk_make_key", m.make_key)
    ctx.register("key_down", m.key_down)
  else
    local msg = ({ [2] = "the game's code is not what this module expects",
                   [3] = "the Edit data was made before the module loaded",
                   [4] = "out of memory", [5] = "a patch failed" })[status] or "unknown"
    log("fl26edit: install FAILED (status " .. status .. ") -- " .. msg .. ". Edit mode works as before.")
  end
end

return m
