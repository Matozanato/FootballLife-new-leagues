--[[
fl26caps -- runtime patch applier (nullguard5 set).

Defensive fix, NOT a capacity patch.  Written by hand, like the other nullguards, because it
installs a code-cave trampoline rather than resizing a field; every byte below was computed
against the exe and disassembled back before being written here.

Set:     nullguard5
Summary: null-check at 0x1414c66c0, 2 patches (trampoline + entry redirect)

The bug.  Minidump thread 3032, c0000005 at 0x1414c674d,
a read of 0x0000000000000004.  0x1414c66c0 is a jump-table field getter --
get(rcx = record, edx = field_id, r8 = out) -- with 108 cases, table at 0x1414c6cdc.  Entry 0
of that table is 0x1414c674d:

    1414c674d  mov    eax, dword ptr [rcx + 4]         <-- rcx = 0, so this reads 0x4
    1414c6750  shr    eax, 0x1c
    1414c6753  mov    dword ptr [r8], eax

A null record plus the field's own offset, not a corrupted pointer (rax 0, rcx 0 in the dump).

Where the null comes from.  The caller is 0x141500ef0 (AI squad/lineup assignment), return
address 0x14150267d.  It does NOT come from a pointer lookup that failed; it comes from an
*index* sentinel used without a range check:

    1415024d5  call   0x141503cc0      ; "find next unassigned candidate"
    1415024da  mov    r15d, eax        ; 0xff when the candidate vector is empty
    ...
    141502649  mov    edx, r15d        ; <-- no range test
    14150264c  mov    r14, qword ptr [rbp - 0x68]
    141502650  mov    rcx, r14
    141502653  call   0x141502e60
    141502658  mov    rsi, rax
    14150265b  mov    edx, r15d
    14150265e  mov    rcx, r14
    141502661  call   0x141502e60      ; returns 0 for index >= 0x28
    141502666  mov    dword ptr [rsp + 0x68], 0xc
    14150266e  lea    r8, [rsp + 0x68]
    141502673  xor    edx, edx         ; field 0
    141502675  mov    rcx, rax         ; <-- 0
    141502678  call   0x1414c66c0      ; crash

0x141503cc0 returns 0xff for "nothing found": at 0x141503cd9 when the vector is empty
(begin == end) and at 0x141503d6a when the cursor runs off the end.  The dump's r15 = 0xff is
exactly that value.  0x141502e60 then rejects it -- `cmp edx, 0x28; jge 0x141502e8e;
xor eax, eax; ret` -- and returns null for any index past the 40-slot scratch array that
0x141504580 allocates fresh for this pass (`mov edx, 0x17c; call 0x14159eff8` at 0x141504604;
0x17c is the player-record stride, 40 slots of it).

That the sentinel is expected here is not a guess.  0x141503cc0 range-checks the same value
against the same bound inside its own body (`cmp r8d, 0x28; jae` at 0x141503d33), and further
down the very same loop the game checks it properly before marking a slot taken:

    1415027ee  cmp    r15d, 0xff
    1415027f5  je     0x141502809                      <-- do not mark the slot
    1415027f7  cmp    r15d, 0x28
    1415027fb  jae    0x141502809
    141502804  mov    byte ptr [rax + rcx + 0x34], 1

That check is downstream of three unguarded dereferences of the same null (0x141502678,
0x14150271e, and 0x14150273a via 0x141502eb0), so on the 0xff path the function faults before
it can reach its own handling.  Shipped bug: none of the eight functions on the crash chain --
0x141500ef0, 0x141504580, 0x1414c66c0, 0x141502e60, 0x141503cc0, 0x141505be0, 0x141571ec0,
0x140f13e90 -- carries a single byte from any fl26caps set.

Why the guard is here and not at 0x141502649.  Redirecting 0x141502649 to one of the loop's
own bail targets (0x14150281c / 0x141502822) was considered and rejected.  Those targets are
reached only from 0x1415026e6 and 0x1415026c5, where ebx has already been reloaded from
[rsp+0x40]; the edge 0x1415024e7 -> 0x141502649 does not reload it, and rsi is reused as a
candidate index at 0x141502507, so esi, ebx, rdx and r15 have different liveness on the two
predecessor edges.  `inc ebx` at 0x14150282c drives the outer loop bound (`cmp ebx, 0xb`), so
a stale ebx there could mis-terminate it.  Jumping into the middle of that function is not
provably safe, and a season limping on a half-updated slot table is worse than a crash.

The fix instead gives the getter the behaviour it already has for a bad request.  Its own
out-of-range path is at 0x1414c6cd8:

    1414c6cd8  xor    al, al
    1414c6cda  ret

-- return false, leave the caller's out buffer untouched.  Every caller already handles that,
because it is the path taken whenever edx > 0x6b.  The guard routes a null rcx to the exact
same two instructions, so a null record reads as "field not available" rather than faulting.
At the three sites in 0x141500ef0 the out slot keeps the 0xc the caller wrote immediately
before the call (0x141502666, 0x14150270c, 0x14150272b), the slot record at [rbp+rbx*4+0x50]
keeps the {0xff, 0xd, 0} the prologue loop at 0x141500f60 initialised it with, and the loop
then falls into the game's own 0xff handling at 0x1415027ee.

Scope.  0x1414c66c0 has 890 call sites, so this guard is broader than nullguard4's.  That
breadth is deliberate: the change is not new behaviour, it is an existing failure path reached
by one more condition, and a null rcx at this function is unconditionally a fault today.  On
any run that does not currently crash here the `je` is never taken and not one byte of
observable state differs.  The cost is that a future null at this getter will be swallowed
instead of dumping, which is the trade this module makes.

The fix: the first nine bytes of 0x1414c66c0 -- `cmp edx, 0x6b` (3) and `ja 0x1414c6cd8` (6),
both whole instructions -- are replaced by a jump to a trampoline plus four nops.  The
trampoline tests rcx, sends null to 0x1414c6cd8, then runs the relocated bounds check and
jumps back to 0x1414c66c9 (`mov eax, edx`), an instruction boundary.  `test rcx, rcx` runs
before the relocated `cmp edx, 0x6b`, so the flags the `ja` reads are the ones it expects.
Nothing jumps into 0x1414c66c0+3..+8: every one of the 108 jump-table targets is >= 0x1414c66df.
The function is a leaf with no prologue, so no unwind data is disturbed.

The trampoline sits at 0x14252e860, in the tail of the last page of .trace: past the raw data
the file ends at (0x14252e800), before .rdata begins (0x14252f000), and after every cave range
this project already uses -- the caps date-spread stub and table at 0x14252e690..0x14252e7e6,
nullguard2's 20 bytes at 0x14252e880, fl26nullguard.lua's 23 bytes at 0x14252e800, nullguard3's
23 bytes at 0x14252e820, and nullguard4's 18 bytes at 0x14252e840..0x14252e851.  The page is
zero-filled there by the loader; because it is beyond the file's raw data it cannot be confirmed
from the exe on disk, so pass 1 confirms it in the live process instead and refuses to write if
anything else has claimed it.  The stub is 23 bytes, taking 0x14252e860..0x14252e876.
All-or-nothing: every target byte is checked first and nothing is written unless all match.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard5.lua
  2. add to sider.ini, in the [modules] list:   lua.module = "fl26nullguard5.lua"
     -- after fl26nullguard4.lua if that one is ever enabled, so the trampolines are written
     in a fixed order; the two caves do not overlap either way
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x14252e860, old="0000000000000000000000000000000000000000000000",
   new="4885c90f846f84f9fe83fa6b0f876684f9fee9527ef9fe",
   why="null-guard trampoline: test rcx,rcx; je 0x1414c6cd8; cmp edx,0x6b; ja 0x1414c6cd8; jmp 0x1414c66c9"},
  {va=0x1414c66c0, old="83fa6b0f870f060000", new="e99b81060190909090",
   why="redirect fn 0x1414c66c0 entry (9 bytes: cmp+ja) to the trampoline at 0x14252e860 (jmp rel32 + 4 nop)"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard5", n))

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
  -- if the page is not writable for us.  The trampoline goes first, so the jump target
  -- exists before the jump does.
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
                      "nullguard5: null-check at 0x1414c66c0"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
