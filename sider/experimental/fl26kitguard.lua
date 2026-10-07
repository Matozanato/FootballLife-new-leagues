--[[
fl26kitguard -- the Kit Server's goalkeeper pick on a club with no kit of the game.

What went wrong. With "Kits you can edit in the game" (the recipe's editable_kits) a new club
borrows no kit from a club of the game, so it has no licensed kit and ctx.kits.get(team, kit)
answers nil for it. The Kit Server (common\kits.lua) picks the goalkeepers' kits at every
kick-off in choose_gk_kits, which reads p_home.ShirtColor1 off that answer without looking:

    [string "common\kits.lua"]:1143: attempt to index local 'p_home' (a nil value)

and the match never starts (Discord, LumpierTheGunner, 2026-10-07: every match crashed with
the box ticked).

What this does. ctx.kits.get is looked up on every call, so it can be wrapped once here for
every module. Only when the answer is nil AND the caller is choose_gk_kits does the wrapper
hand back a neutral grey kit: that function wants nothing but the two shirt colours, to pick
goalkeeper kits that stand out from them. Every other caller still gets nil, so the Kit
Server's "unlicensed, kits disabled" test (has_kit = ctx.kits.get(team, 0)) and its fallbacks
work as before. Sider has no debug library, so the caller is told apart by the order of calls
instead: choose_gk_kits asks ctx.kits.get_current_kit_id(side) and right away
ctx.kits.get(<that side's team>, <that kit id>). The id is remembered when it is asked and used up
by the next get; get_current_team forgets it, because the licence test in load_configs_for_team is
always reached after a get_current_team or with no kit id asked at all.
]]

local m = {}
local GREY = "#808080"

function m.init(ctx)
  local k = ctx.kits
  if type(k) ~= "table" or type(k.get) ~= "function" or type(k.get_current_kit_id) ~= "function" then
    log("fl26kitguard: ctx.kits.get not there -- nothing to guard")
    return
  end
  local get, cur_kit, cur_team = k.get, k.get_current_kit_id, k.get_current_team
  local armed_side, armed_kit = nil, nil
  local count = 0
  k.get_current_kit_id = function(side, ...)
    local id, is_gk = cur_kit(side, ...)
    armed_side, armed_kit = side, id
    return id, is_gk
  end
  if type(cur_team) == "function" then
    k.get_current_team = function(...)
      armed_side, armed_kit = nil, nil
      return cur_team(...)
    end
  end
  k.get = function(team, kit, ...)
    local side, akit = armed_side, armed_kit
    armed_side, armed_kit = nil, nil
    local r = get(team, kit, ...)
    if r == nil and side ~= nil and kit == akit then
      local want = (side == 0) and ctx.home_team or ctx.away_team
      if want ~= nil and team == want then
        count = count + 1
        if count <= 20 then
          log(string.format("fl26kitguard: team %s has no kit of the game (kit %s) -- grey for the goalkeeper pick",
                            tostring(team), tostring(kit)))
        end
        return { ShirtColor1 = GREY, ShirtColor2 = GREY }
      end
    end
    return r
  end
  log("fl26kitguard: ctx.kits.get wrapped -- a club without a kit of the game no longer stops the goalkeeper pick")
end

return m
