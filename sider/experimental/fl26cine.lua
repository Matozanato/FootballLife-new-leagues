--[[
fl26cine -- the scenes of a final of ours.

The base game knows no final of a new league: its match has no entrance of its own. The cinematics
packs under SiderAddons\content\cinematics hold one folder per competition (LIB, UEFA Champions
League F, ...): the entrance, the stadium dressing and the ceremony's animations and trophy, which
the shared cinematics module (common\cinematics.lua) picks by the game's tournament.

This module picks one for our finals, from the world file's lines

    cine <reg> <final|all> <folder>

  final|all  the competition's final only (the match the game calls the final, match_info 53), or
             every match of it (a one-match final, a super cup)
  folder     the folder under content\cinematics every file of the match comes from first
             ("LIB": the Copa Libertadores' final)

A file the folder has not got is left to the next module (sider takes the first module whose file
exists), so this one must load before common\cinematics.lua. Mod Studio writes the lines (the
"cinematics" recipe key) and puts the module there.
--]]

local m = {}
local root
local finals = {}

local function world_file(ctx)
  local sep = string.char(92)
  return ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
end

local function read_world(ctx)
  local f = io.open(world_file(ctx), "r")
  local n = 0
  if not f then return 0 end
  for line in f:lines() do
    local reg, when, folder = line:match("^%s*cine%s+(%d+)%s+(%a+)%s+(.-)%s*$")
    if reg and folder ~= "" then
      finals[tonumber(reg)] = { all = when == "all", folder = folder }
      n = n + 1
    end
  end
  f:close()
  return n
end

function m.make_key(ctx, filename)
  local c = finals[ctx.tournament_id]
  if not c or not filename or not (c.all or ctx.match_info == 53) then return nil end
  return "fl26cine:" .. root .. "\\" .. c.folder .. "\\" .. filename:gsub("/", "\\")
end

function m.get_filepath(ctx, filename, key)
  if key and key:sub(1, 9) == "fl26cine:" then return key:sub(10) end
end

function m.init(ctx)
  root = ctx.sider_dir:gsub("[/\\]+$", "") .. "\\content\\cinematics"
  if read_world(ctx) == 0 then
    log("fl26cine: the world file has no cine line -- nothing to do")
    return
  end
  for reg, c in pairs(finals) do
    log(string.format("fl26cine: reg %d (%s) -- the scenes of %s", reg, c.all and "every match" or "its final", c.folder))
  end
  ctx.register("livecpk_make_key", m.make_key)
  ctx.register("livecpk_get_filepath", m.get_filepath)
end

return m
