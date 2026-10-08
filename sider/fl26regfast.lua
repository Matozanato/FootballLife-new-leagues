--[[
fl26regfast -- drop two redundant regulation-table searches from "which league is team X in".

Speed fix, NOT a capacity patch.  Found 08.10.2026 by sampling a Master League creation that
sat 5-10 minutes on the loading screen (Druga NL club): about 65 % of the game's time was in
one function, 0x141543510, which answers "which league does this team play in" by walking
every regulation record.  It is a finite grind, not a hang -- the load finished on its own.

For each league-type regulation id it does the same linear search three times:

    1415435a0  cmp  word [rdx + r13 + REGS], bx    ; search 1: finds index, rdx = index*0x314
    1415435b2  je   1415435c0
    1415435c0  movzx edx, bx
    1415435c3  mov  rcx, r13
    1415435c6  call 0x1414bb000                    ; search 2: the same search again -> rax
    ...
    1415435f0  cmp  word [rdx + r10 + REGS], bx    ; search 3: finds index, rdx = index*0x314
    14154360f  movzx edx, bx
    141543612  mov  rcx, r10
    141543615  call 0x1414bb000                    ; search 4: the same search again -> rax

and the helper 0x141543910 does it twice more (inline loop leaves rax on the record, then
calls 0x1414bb000 for the same record).  0x1414bb000 returns base + REGS + i*0x314 for the
first record whose id matches, scanning from 0 -- exactly the record the inline loop just
stopped on (regulation ids are unique; 300 distinct of 300 in our world, 08.10.).  So the
call can be replaced by the address the inline loop already has:

    1415435c0  lea  rax, [r13 + rdx + REGS] ; nop3       (11 bytes, was movzx/mov/call)
    14154360f  lea  rax, [r10 + rdx + REGS] ; nop3       (11 bytes)
    141543951  nop8                                       (rax already = the record)

Nothing after these sites reads rcx/rdx/r8-r11 or the flags before writing them, so the
only observable difference is that the work is done once instead of twice.  With 300
regulations this removes about 60 % of the samples in that function.

REGS is whatever displacement the cmp at 0x1415435a9 carries when this module runs: the
shipped 0xc12e9c, or the relocated base fl26caps writes there (0x1d4c330 for the
...-regs-... sets).  It is read at runtime, so the module follows the installed set --
load it AFTER fl26caps.lua.  If the two cmp sites disagree, nothing is written.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26regfast.lua
  2. sider.ini, after lua.module = "fl26caps.lua":   lua.module = "fl26regfast.lua"
  3. start the game; sider.log says "fl26regfast: applied all 3 patches"
--]]

local m = {}

local function unhex(s)
  local out = {}
  for i = 1, #s, 2 do
    out[#out + 1] = string.char(tonumber(string.sub(s, i, i + 1), 16))
  end
  return table.concat(out)
end

local function tohex(s)
  if s == nil then return "nil" end
  local out = {}
  for i = 1, #s do
    out[#out + 1] = string.format("%02x", string.byte(s, i))
  end
  return table.concat(out)
end

-- the cmp word [rdx + r13 + disp32], bx  /  cmp word [rdx + r10 + disp32], bx
local CMP1, CMP1_OP = 0x1415435a9, "6642399c2a"
local CMP2, CMP2_OP = 0x1415435fa, "6642399c12"

function m.init(ctx)
  local a = memory.read(CMP1, 9)
  local b = memory.read(CMP2, 9)
  if a == nil or b == nil or tohex(string.sub(a, 1, 5)) ~= CMP1_OP or tohex(string.sub(b, 1, 5)) ~= CMP2_OP
     or string.sub(a, 6, 9) ~= string.sub(b, 6, 9) then
    log(string.format("fl26regfast: ABORTED, the regulation searches are not what this module "
                      .. "expects (%s / %s). Nothing was written.", tohex(a), tohex(b)))
    return
  end
  local disp = string.sub(a, 6, 9)
  local patches = {
    {va=0x1415435c0, old="0fb7d3498bcde8357af7ff", new="498d8415" .. tohex(disp) .. "0f1f00",
     why="lea rax,[r13+rdx+REGS] instead of searching again via 0x1414bb000"},
    {va=0x14154360f, old="0fb7d3498bcae8e679f7ff", new="498d8412" .. tohex(disp) .. "0f1f00",
     why="lea rax,[r10+rdx+REGS] instead of searching again via 0x1414bb000"},
    {va=0x141543951, old="0fb7d3e8a776f7ff", new="0f1f840000000000",
     why="rax already holds the record; skip the second search"},
  }
  local n = #patches
  log(string.format("fl26regfast: REGS = 0x%s, %d patches, verifying", tohex(string.reverse(disp)), n))

  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26regfast: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26regfast: ABORTED, %d of %d sites did not match. Nothing was written.", bad, n))
    return
  end

  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    if memory.read(p.va, #new) == new then
      written = written + 1
      log(string.format("fl26regfast: [%d/%d] 0x%x %s -> %s  %s", i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26regfast: WRITE FAILED at 0x%x (%s)", p.va, p.why))
    end
  end
  if failed == 0 then
    log(string.format("fl26regfast: applied all %d patches -- team-to-league lookup searches once", written))
  else
    log(string.format("fl26regfast: PARTIAL: %d written, %d failed -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
