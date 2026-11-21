-- Run with lua or luajit from the repository root.
local module = dofile("sider/experimental/fl27playoff.lua")
local input = {
    "poff 1000 up=17 low=79 hold=79:4 entry=79:2,79:4,79:6,79:8",
    "poff 756 up=96 low=252 hold=252:2 entry=252:2,955:2",
    "poff 717 up=100 low=253 entry=100:16,253:3",
    "poff 779 up=118 low=423 hold=bogus entry=423:2,423:3",
    "poff 720 up=67 low=338 hold=338:2 entry=garbage",
    "gset 0 up=96:3 low=252:2:96,955:1:96",
}
local file = {lines = function()
    local i = 0
    return function() i = i + 1; return input[i] end
end}
local places, quotas = {}, {}
module.read_config(file, function(reg, rank, contested)
    places[reg] = places[reg] or {}
    places[reg][rank] = contested
end, function(reg, count) quotas[reg] = count end)
assert(places[79][0] == 0 and places[79][2] == 0 and places[79][4] == 1)
assert(places[79][6] == 0 and places[79][8] == 0 and places[79][3] == nil)
assert(places[252][2] == 1 and places[955][2] == 0)
assert(quotas[252] == 2 and quotas[955] == 1)
assert(places[253][3] == 1 and places[100] == nil)
assert(places[423] == nil and places[338] == nil)
print("FL27 custom playoff config passed")

local exports = {}
local installed, marks, group_quotas, logs = 0, 0, 0, {}
exports.fl27_playoff_place = function() marks = marks + 1 end
exports.fl27_playoff_group_quota = function() group_quotas = group_quotas + 1 end
local result = 0
exports.fl27_playoff_install = function(asset)
    assert(asset.path:find("cmnIconRankPromotion.bin", 1, true))
    assert(marks > 0 and group_quotas > 0)
    installed = installed + 1
    return result
end
ffi = {
    cdef = function() end,
    new = function() return {} end,
    cast = function(_, address) return address end,
    C = {
        fl27playoff_MultiByteToWideChar = function(_, _, path, _, buffer)
            if buffer then buffer.path = path end
            return #path + 1
        end,
        fl27playoff_LoadLibraryW = function(path) return path end,
        fl27playoff_GetProcAddress = function(_, name)
            assert(exports[name], "unexpected native export lookup: " .. name)
            return exports[name]
        end,
    },
}
log = function(message) logs[#logs + 1] = message end
local open = io.open
io.open = function(path)
    assert(path == "probe\\modules\\fl26world.txt")
    return {lines = file.lines, close = function() end}
end
local ctx = {
    sider_dir = "probe\\",
    register = function(event) error("playoff module registered " .. event) end,
}
module.init(ctx)
result = 2
module.init(ctx)
io.open = open
assert(installed == 2 and #logs == 2)
assert(logs[1] == "FL27 playoff arrows: install status 0")
assert(logs[2] == "FL27 playoff arrows: install status 2")
print("FL27 startup keeps status logging without registering Sider events")
