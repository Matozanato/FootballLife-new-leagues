local m = {}

local function wide(path)
  local n = ffi.C.candidate_utf8(65001, 0, path, -1, nil, 0)
  if n <= 0 then return nil end
  local result = ffi.new("uint16_t[?]", n)
  if ffi.C.candidate_utf8(65001, 0, path, -1, result, n) ~= n then return nil end
  return result
end

function m.init(ctx)

  if ffi == nil then log("fl26candidate: LuaJIT ffi unavailable"); return end
  ffi.cdef([[
    unsigned long candidate_getenv(const char*, char*, unsigned long) __asm__("GetEnvironmentVariableA");
    void* candidate_load(const uint16_t*) __asm__("LoadLibraryW");
    int candidate_utf8(unsigned int, unsigned long, const char*, int, uint16_t*, int) __asm__("MultiByteToWideChar");
    void* candidate_module(const void*) __asm__("GetModuleHandleW");
    void* candidate_proc(void*, const char*) __asm__("GetProcAddress");
    typedef int (*candidate_install_t)(uintptr_t);
  ]])
  local value = ffi.new("char[32]")
  local length = tonumber(ffi.C.candidate_getenv("FL27_CANDIDATE_SORT", value, 32))
  local setting = length > 0 and length < 32 and ffi.string(value, length) or ""
  if setting ~= "blocked" then return end
  local dir = ctx.sider_dir:gsub("[/\\]+$", "") .. "\\modules\\"
  local dll = wide(dir .. "fl26candidate.dll")
  if dll == nil then log("fl26candidate: path conversion failed"); return end
  local lib = ffi.C.candidate_load(dll)
  if lib == nil then log("fl26candidate: DLL load failed"); return end
  local install = ffi.C.candidate_proc(lib, "fl26_candidate_install")
  if install == nil then log("fl26candidate: export missing"); return end
  local base = ffi.cast("uintptr_t", ffi.C.candidate_module(nil))
  if base == 0 then log("fl26candidate: executable base unavailable"); return end
  local status = ffi.cast("candidate_install_t", install)(base)
  log(string.format("fl26candidate: mode=%s status=%d", setting, status))
end

return m
