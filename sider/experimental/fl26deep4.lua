--[[
fl26deep4 -- let a pyramid be four (or more) divisions deep.

The division of a competition is two bits at runtime (regulation +0x304, bits 30-31), so
the only values that exist are 1, 2 and 3. That is not what actually stops a fourth
division, though. The function that answers "where does this club move to at the end of
the season", 0x141510430, is built out of three gates:

  0x1415104a1   tier >= 2               -> promoted into the league named by +0x7c
  0x1415104d6   tier == 1, bottom three -> relegated into the league named by +0x7e
  0x1415105f5   the league below is tier 3 AND this league is tier 2, bottom three
                                        -> relegated into the league named by +0x7e

The promotion gate is `cmp eax,0x80000000 ; jb skip` -- a >= test -- so a fourth-level
league marked tier 3 and pointed at a third-level league with +0x7c promotes perfectly
well, with no patch at all. Relegation is the half that does not work: neither of the two
relegation gates matches a tier-3 league, so the third level never sends anybody down to
the fourth. Clubs climb and never fall.

The second relegation gate is what makes it asymmetric, and it is one byte:

  141510612  3d 00 00 00 80   cmp eax, 0x80000000     ; this league
  141510617  75 b1            jne <no relegation>     ; require exactly tier 2

`jne` -> `jb` turns "exactly 2" into "2 or 3", which is the same shape the promotion gate
already has. The other half of that gate -- the league below must be tier 3 -- is left
alone and is exactly right: every division below the second is tier 3 anyway.

With this byte, level 3 relegates into level 4, level 4 into level 5, and so on for as
many leagues as you chain with tools/deepen.py. Nothing else in the exe cares: all the
other places that read the division field test for tier 1 (European places, 0x141358bd0,
0x141359a60, 0x1413b7910) or tier >= 2, and the pairing helper 0x1415141c0 already has a
tier-3 branch of its own. No code anywhere searches for "the tier-3 league of this
region", so two of them in one pyramid is not a conflict.

Not run in a game yet. Built and verified against the exe on 2026-09-21.

Install:
  1. copy to <game>\SiderAddons\modules\fl26deep4.lua
  2. sider.ini, in the [modules] list:   lua.module = "fl26deep4.lua"
--]]

local m = {}

local VA  = 0x141510612
local OLD = "\061\000\000\000\128\117"   -- cmp eax,0x80000000 ; jne
local NEW = "\061\000\000\000\128\114"   -- cmp eax,0x80000000 ; jb

function m.init(ctx)
  local cur = memory.read(VA, #OLD)
  if cur ~= OLD then
    log(string.format("fl26deep4: MISMATCH at 0x%x -- nothing written, the game is "
                      .. "unmodified. This is a different build than the one the patch "
                      .. "was read from.", VA))
    return
  end
  memory.write(VA, NEW)
  if memory.read(VA, #NEW) == NEW then
    log(string.format("fl26deep4: 0x%x jne -> jb; a third division now relegates into a "
                      .. "fourth, and a fourth into a fifth", VA))
  else
    log(string.format("fl26deep4: WRITE FAILED at 0x%x", VA))
  end
end

return m
