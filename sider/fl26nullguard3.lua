--[[
fl26caps -- runtime patch applier (nullguard3 set).

Defensive fix, NOT a capacity patch.  Written by hand, like the other two nullguards,
because it installs a code-cave trampoline rather than resizing a field; every byte below
was computed against the exe and disassembled back before being written here.

Set:     nullguard3
Summary: null-check at 0x140cd6a1c, 2 patches (trampoline + site redirect)

The bug: loading a saved Master League season reads the fixture list without checking that
there is one.  The function asks for the schedule -- the string `d_schedule_` is loaded two
instructions before the call, and `schedule_date` a few after -- and gets back a count in
[rsp+0x40] and a pointer in [rsp+0x48]:

    140cd6a07  call  0x140e4cd10
    140cd6a0c  mov   r14, rax
    140cd6a0f  test  rax, rax                   <-- this result IS checked
    140cd6a12  je    0x140cd6ead
    140cd6a18  mov   edx, dword ptr [rsp + 0x40]
    140cd6a1c  mov   rcx, qword ptr [rsp + 0x48]
    140cd6a21  movzx edx, word ptr [rcx + rdx*4] <-- ... this one is not

On 15 September 2026 loading our slot-2 save died here twice in a row, deterministically,
with rcx and rdx both zero: a read of address 0, which is a null pointer rather than a
corrupted one.  Until this is guarded the save cannot be loaded at all, which makes saving
it pointless.

That the pointer can legitimately be null is not a guess -- the same function's own cleanup
says so, thirty instructions later:

    140cd6ecb  mov   rdx, qword ptr [rsp + 0x48]
    140cd6ed0  test  rdx, rdx
    140cd6ed3  je    0x140cd6ee8                 <-- nothing to free

So the read is the oversight, not the value.  The fix takes the branch the function already
has for "there is no schedule": 0x140cd6ead, the target of the `je` five instructions above,
which falls into that same cleanup and returns properly.

The five bytes of the `mov rcx, [rsp+0x48]` are replaced by a jump to a trampoline that
performs that load, tests it, jumps to 0x140cd6ead when it is null, and otherwise performs
the original `movzx` and returns to 0x140cd6a25.  Nothing between them needs the flags.  The
`movzx` left behind at 0x140cd6a21 becomes unreachable and is deliberately not touched.

The trampoline sits at 0x14252e820, in the tail of the last page of .trace: past the raw
data the file ends at (0x14252e800), before .rdata begins (0x14252f000), and after the 23
bytes fl26nullguard.lua already writes at 0x14252e800.  The page is zero-filled there by
the loader.  It does not collide with the caps set's date stub and table, which occupy
0x14252e690 to 0x14252e7e6, or with nullguard2's 20 bytes at 0x14252e880.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard3.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard3.lua"
     -- after fl26nullguard.lua, so the trampolines are written in a fixed order
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x14252e820, old="0000000000000000000000000000000000000000000000",
   new="488b4c24484885c90f847f867afe0fb71491e9ee817afe",
   why="schedule null-guard trampoline: mov rcx,[rsp+0x48]; test rcx,rcx; jz 0x140cd6ead; movzx edx,word [rcx+rdx*4]; jmp 0x140cd6a25"},
  {va=0x140cd6a1c, old="488b4c2448", new="e9ff7d8501",
   why="redirect the unchecked schedule load at 0x140cd6a1c to the trampoline (jmp rel32)"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard3", n))

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
                      "nullguard3: schedule null-check at 0x140cd6a1c"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
