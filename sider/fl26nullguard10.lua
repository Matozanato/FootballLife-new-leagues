--[[
fl26caps -- runtime patch applier (nullguard10 set).

Defensive fix, NOT a capacity patch.  Two jumps get a new target; no trampoline, no spare
code bytes used.

Set:     nullguard10
Summary: endless league-link walk in 0x140caee00 stopped, 2 patches (two jmp targets)

The bug: a loop that never ends.  0x140caee00 goes over every regulation and, for each one,
walks a chain of linked leagues.  It starts from the league named by +0x78 of the record;
when that is 0xffff it starts from +0x7c instead (the league above).  It then follows +0x78
from league to league.  The walk is meant to stop at 0xffff, but the test for 0xffff sits at
the head of the loop, 0x140cafad0, which is also the place that falls back to +0x7c:

    140cafad0  cmp    bx, ax                    ; next league == 0xffff ?
    140cafad3  jne    0x140cafae9
    140cafad5  movzx  ebx, word ptr [r12 + 0x7c]  ; yes: take the league above ... again
    140cafae0  cmp    bx, ax
    140cafae3  je     0x140cafdb1               ; only a missing league above ends it

So for a league whose +0x78 is 0xffff and whose +0x7c is set (a second division pointing
at the first), the walk goes: league above, its +0x78 is 0xffff, back to the league above,
and so on forever.  Two of the three ways back to the head do this:

    140cafc35  jmp 0x140cafac0      ; after "movzx ebx, word [rax+0x78]"
    140cafdac  jmp 0x140cafac5      ; after "movzx ebx, word [rsi+0x78]" and a free

The third, 0x140cafc5f .. 0x140cafc76, already does the right thing: it stores the next
league, ends the walk on 0xffff (je 0x140cafdb1) and only otherwise goes back to 0x140cafad0.
Only a finished competition leads there, so the walk ends as long as the league above has
finished its season.

The two loops differ in what they cost.  One turn of the second one pushes a 32-byte entry
plus a copy of the league's date list into a vector.  On 30 September 2026 a Korea career
(K League 2 pointing up at K League 1, February-December seasons) died on day 30 of its
second year, while the Europa League play-off was being drawn: an out-of-memory write inside
the 12-byte copy 0x140affed0, fault offset 0xaffe1b.  Loading the save from day 356 and
playing on repeated it -- the game grew from 3.4 to more than 8 GB in under a minute on the
same day.  RIP samples during the growth sit in the "is this
competition finished" check 0x14151c300 / 0x14150b860, the regulation lookup 0x1414bb000 and
that copy.  Day 30 of the first year, before any European draw, was fine.

The fix sends both jumps to the existing correct tail instead of the loop head:

    140cafc35  jmp 0x140cafc63      ; store bx; 0xffff -> end; else jmp 0x140cafad0
    140cafdac  jmp 0x140cafc68      ; (bx is stored already)   same test

rbx is callee-saved, so bx survives the free before 0x140cafdac.  Leagues linked by +0x78
(2 -> 3 -> 4 in England) are walked exactly as before; only the step back to +0x7c after
the end of a chain is gone.  The first step from +0x7c (at the start of a walk) is kept.

Verified 2026-09-30 on the same save: with this module day 30 passed at 3.3 GB with no growth,
and on day 41 both Korean leagues joined their new season (33 and 18 matchdays placed).

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard10.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard10.lua"
     -- after fl26nullguard9.lua
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x140cafc35, old="e986feffff", new="e929000000",
   why="league-link walk, plain step: jmp 0x140cafac0 -> jmp 0x140cafc63 (0xffff ends the walk)"},
  {va=0x140cafdac, old="e914fdffff", new="e9b7feffff",
   why="league-link walk, dated step: jmp 0x140cafac5 -> jmp 0x140cafc68 (0xffff ends the walk)"},
}

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

function m.init(ctx)
  local n = #patches
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard10", n))

  -- pass 1: read only.  Nothing is written until every site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26caps: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26caps: ABORTED, %d of %d sites did not match. "
                      .. "Nothing was written; the game is unmodified. "
                      .. "If site 1 is the mismatch, another module has taken that padding.",
                      bad, n))
    return
  end

  -- pass 2: write, then read back, because a write into the code section can silently fail
  -- if the page is not writable for us.
  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    local back = memory.read(p.va, #new)
    if back == new then
      written = written + 1
      log(string.format("fl26caps: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26caps: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  if failed == 0 then
    log(string.format("fl26caps: applied all %d patches -- %s", written,
                      "nullguard10: league-link walk ends at the last league (0x140cafc35, 0x140cafdac)"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
