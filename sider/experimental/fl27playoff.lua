-- FL27 27.1.1 standings artwork. The active world supplies visual overrides.
local m = {}

function m.read_config(file, place, quota)
  for line in file:lines() do
    local cup = line:match("^%s*poff%s+(%d+)%s")
    if cup then
      local upper = tonumber(line:match("%sup=(%d+)"))
      local lower = tonumber(line:match("%slow=(%d+)"))
      local hold, spot = line:match("%shold=(%d+):(%d+)")
      hold, spot = tonumber(hold), tonumber(spot)
      local entries = {}
      for token in (line:match("%sentry=(%S+)") or ""):gmatch("[^,]+") do
        local reg, rank = token:match("^(%d+):(%d+)$")
        reg, rank = tonumber(reg), tonumber(rank)
        if reg and reg < 65535 and rank > 0 and rank <= 64 then
          entries[#entries + 1] = { reg, rank }
        end
      end
      if upper and lower and #entries >= 2 and (hold or not line:find("%shold=")) then
        local marks = {}
        for _, entry in ipairs(entries) do
          local reg, rank = entry[1], entry[2]
          if reg ~= upper and (hold or reg == lower) then
            marks[#marks + 1] = {reg, rank, (reg == hold and rank == spot or not hold) and 1 or 0}
          end
        end
        if #marks > 0 then
          place(lower, 0, 0) -- A configured lower division overrides the stock profile.
          for _, mark in ipairs(marks) do place(mark[1], mark[2], mark[3]) end
        end
      end
    elseif line:match("^%s*gset%s") then
      for token in (line:match("%slow=(%S+)") or ""):gmatch("[^,]+") do
        local reg, slots = token:match("^(%d+):(%d+):%d+$")
        if reg then quota(tonumber(reg), tonumber(slots)) end
      end
    end
  end
end

function m.init(ctx)
  if not ffi then return end
  local root = ctx.sider_dir:gsub("[/\\]+$", "")
  ffi.cdef[[
    void* fl27playoff_LoadLibraryW(const uint16_t*) __asm__("LoadLibraryW");
    int fl27playoff_MultiByteToWideChar(unsigned int, unsigned long, const char*, int, uint16_t*, int)
      __asm__("MultiByteToWideChar");
    void* fl27playoff_GetProcAddress(void*, const char*) __asm__("GetProcAddress");
  ]]
  local function wide_path(path)
    local n = ffi.C.fl27playoff_MultiByteToWideChar(65001, 0, path, -1, nil, 0)
    if n <= 0 then return end
    local wide = ffi.new("uint16_t[?]", n)
    if ffi.C.fl27playoff_MultiByteToWideChar(65001, 0, path, -1, wide, n) == n then return wide end
  end
  local module = wide_path(root .. "\\modules\\fl27playoff.dll")
  local asset = wide_path(root .. "\\livecpk\\FL27 Playoff Indicators\\common\\menu\\parts\\cmnIconRankPromotion.bin")
  if not (module and asset) then return end
  local dll = ffi.C.fl27playoff_LoadLibraryW(module)
  if dll == nil then log("FL27 playoff arrows: could not load DLL"); return end

  local function resolve(name, signature)
    local address = ffi.C.fl27playoff_GetProcAddress(dll, "fl27_playoff_" .. name)
    if address ~= nil then return ffi.cast(signature, address) end
  end
  local install = resolve("install", "int(*)(const uint16_t*)")
  local place = resolve("place", "void(*)(unsigned,unsigned,unsigned)")
  local quota = resolve("group_quota", "void(*)(unsigned,unsigned)")
  if not (install and place and quota) then
    log("FL27 playoff arrows: DLL exports missing"); return
  end
  local world = io.open(root .. "\\modules\\fl26world.txt", "r")
  if world then
    m.read_config(world, place, quota)
    world:close()
  end
  local result = tonumber(install(asset))
  log("FL27 playoff arrows: install status " .. result)
end

return m
