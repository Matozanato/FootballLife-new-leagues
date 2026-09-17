--[[
fl26caps -- runtime patch applier (nullguard7 set).

Defensive fix, NOT a capacity patch.  Like the other nullguards it installs a code-cave
trampoline rather than resizing a field; every byte below was computed against the exe and
disassembled back before being written here.

Set:     nullguard7
Summary: empty-vector check at 0x14128a3a3, 2 patches (trampoline + site redirect)

The bug: the board meeting at the start of a Master League season looks a club up in a
table of (handle, value) pairs and pre-loads the first pair before checking that the table
has anything in it.

    14128a3a3  mov   rax, qword ptr [rbp - 0x50]   ; begin
    14128a3a7  mov   r8d, esi
    14128a3aa  mov   r9d, dword ptr [rax + 4]      <-- faults when begin is null
    14128a3ae  mov   ebx, dword ptr [rsp + 0x40]
    14128a3b2  mov   r11, qword ptr [rbp - 0x48]   ; end
    14128a3b6  cmp   rax, r11
    14128a3b9  je    0x14128a411                   <-- the empty case the function already has

The emptiness test is two instructions too late.  On 17 September 2026 a 39-league season
died here 28 confirmations into the board meeting, dump FL_2026.exe.3756.dmp: rax = 0, the
access violation reading address 4.  Nothing is corrupt -- the table is simply empty.

The function's own answer for "this club is not in the table" is 0x14128a411, `or edi, -1`,
so the fix takes that branch.  The empty path still loads ebx from [rsp+0x40], which the
code after the loop reads back at 0x14128a427.

Eleven bytes at 0x14128a3a3 (the two moves plus the faulting load) are replaced by a jump
to a trampoline that performs both moves, tests the pointer, and either continues into the
original loop at 0x14128a3ae or jumps to the not-found branch.  Six nops pad the rest; the
bytes left behind are unreachable and deliberately untouched.

The trampoline sits at 0x14252e8a0, in the zero-filled tail of the last page of .trace,
after nullguard6's 31 bytes at 0x14252e880 and well before .rdata begins at 0x14252f000.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard7.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard7.lua"
     -- after fl26nullguard.lua, so the trampolines are written in a fixed order
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x14252e8a0, old="000000000000000000000000000000000000000000000000000000000000",
   new="488b45b0448bc64885c07409448b4804e9f9bad5fe8b5c2440e953bbd5fe",
   why="squad-table null-guard trampoline: mov rax,[rbp-0x50]; mov r8d,esi; test rax,rax; "
    .. "jz empty; mov r9d,[rax+4]; jmp 0x14128a3ae; empty: mov ebx,[rsp+0x40]; jmp 0x14128a411"},
  {va=0x14128a3a3, old="488b45b0448bc6448b4804", new="e9f8442a01909090909090",
   why="redirect the unchecked first-element load at 0x14128a3a3 to the trampoline (jmp rel32 + 6 nop)"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard7", n))

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
                      "nullguard7: empty squad table guarded at 0x14128a3a3"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
