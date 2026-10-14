--[[
fl26caps -- runtime patch applier (nullguard11 set).

Defensive fix, NOT a capacity patch.  One block of code is rewritten in place; no
trampoline, no cave, no spare bytes anywhere else.

Set:     nullguard11
Summary: a squad entry whose player no longer exists is skipped when a new Master League
         is set up, instead of crashing the game (1 patch, 67 bytes at 0x140f3258e)

The bug.  0x140f32470 runs once when a new Master League is created.  It walks every team of
the Edit block (count at +0xd0bcec, 1,939 on 14.10.2026), fetches the team's squad list with
0x140f2b670 (32-byte records, the player handle in the first qword, flags in the dword at
+0x1c), looks each player up with 0x1414bc9a0(edit block, handle) and sets captain / kicker
bits in the player record at +0x148 according to the flags:

    140f32589  call   0x1414bc9a0            ; rax = player record, or 0 when he is not there
    140f3258e  movups xmm0, [rsp+0x20]       ; the record's second half
    140f32593  psrldq xmm0, 0xc
    140f32598  movd   ecx, xmm0              ; ecx = flags (record +0x1c)
    140f3259c  test   ecx, 0xd0
    140f325a2  jbe    0x140f325ae
    140f325a4  or     dword [rax+0x148], 0x20000   <-- writes through rax, never checked
    ...        two more "test / jbe / or dword [rax+0x148], 0x40000"
    140f325d1  add    rbx, 0x20              ; next record

The lookup returns 0 when the handle names a player who is not in Player.bin, and the
first "or" then writes to address 0x148: access violation at 0x140f325a4.  Seen four times on
14.10.2026 (dumps in D:\dev\fl26-dumps): team index 11 (Aston Villa, team 107), player
213663 -- a player the previous world had and the rebuilt one numbers differently.  The
squad list that still names him is not in the world's tables (all seven, scanned) but in
the game's own saved state, so a player who installs a rebuilt world over an older one
hits it the moment he starts a Master League; the crash in #beta-chat (Tysonche35) is the
same.  The other two writes at 0x140f325b3 / 0x140f325c7 go through the same rax.

The fix rewrites the 67 bytes 0x140f3258e..0x140f325d1 so that the flags are read straight
from the stack (the dword at [rsp+0x2c] is exactly what psrldq/movd produced) and a null
rax skips the whole record:

    140f3258e  mov    ecx, [rsp+0x2c]
    140f32592  test   rax, rax
    140f32595  je     0x140f325d1             ; no such player: next record
    140f32597  test   cl, 0xd0  / je          ; the three flag tests as before
    140f3259c  or     dword [rax+0x148], 0x20000
    140f325a6  test   cl, 0x50  / je
    140f325ab  or     dword [rax+0x148], 0x40000
    140f325b5  test   cl, 0x20  / je ; test cl, 8 / je
    140f325bf  or     dword [rax+0x148], 0x40000
    140f325c9  8 x nop

"jbe" after "test" is "je" (test clears CF), and "test ecx, 0xd0" only looks at the low
byte, so "test cl, 0xd0" is the same test.  xmm0 is not used after this block (the loop head
reloads it), ecx and rdx are rewritten at the next iteration.  Nothing else changes: a team
whose players all exist gets exactly the bits it got before.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard11.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard11.lua"
     -- after fl26nullguard10.lua (or let fl26guards.lua carry it)
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x140f3258e,
   old="0f10442420660f73d80c660f7ec1f7c1d0000000760a81884801000000000200f6c150760a81884801000000000400f6c120760ff6c108760a81884801000000000400",
   new="8b4c242c4885c0743af6c1d0740a81884801000000000200f6c150740a81884801000000000400f6c1207417f6c1087412818848010000000004009090909090909090",
   why="new Master League squad flags: skip a record whose player lookup returned 0 (was: or dword [rax+0x148] with rax=0)"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard11", n))

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
                      .. "Nothing was written; the game is unmodified.", bad, n))
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
      log(string.format("fl26caps: [%d/%d] 0x%x %s  %s", i, n, p.va, "rewritten", p.why))
    else
      failed = failed + 1
      log(string.format("fl26caps: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  if failed == 0 then
    log(string.format("fl26caps: applied all %d patches -- %s", written,
                      "nullguard11: a missing player is skipped at Master League setup (0x140f3258e)"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
