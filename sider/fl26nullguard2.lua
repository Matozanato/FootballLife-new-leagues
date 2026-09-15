--[[
fl26caps -- runtime patch applier (nullguard2 set).

Defensive fix, NOT a capacity patch.  Written by hand, like the first nullguard, because it
installs a code-cave trampoline rather than resizing a field; every byte below was computed
against the exe and disassembled back before being written here.

Set:     nullguard2
Summary: null-check at 0x140fc9238, 2 patches (trampoline + site redirect)

The bug: the function at 0x140fc9210 is handed an id in `dx`, looks it up with
`call 0x141579b90`, and reads the result without checking it:

    140fc922e  call  0x141579b90
    140fc9235  mov   r14, rax
    140fc9238  cmp   dword ptr [rax + 0x3c0], ebp     <-- rax can be 0
    140fc923e  jbe   0x140fc93c6                      <-- nothing to do

On 15 September 2026 that lookup returned null for id 0x405 and killed a season at day 257,
forty-two days into a run -- fault offset 0x140fc9238, a read of address 0x3c0, which is a
null pointer plus the field's own offset rather than a corrupted one.  Unlike 0x1484ed4c0
this is in `.trace`, the game's own code, so it can be reasoned about and guarded.

The fix: the function already has a path for "the list is empty" -- the `jbe` on the very
next line, to the epilogue at 0x140fc93c6.  A null result means there is no list at all,
which is the same outcome, so the guard simply takes that branch.  The six bytes of the
`cmp` are replaced by a jump to a trampoline that tests the pointer, jumps to 0x140fc93c6
when it is null, and otherwise performs the original `cmp` and returns to 0x140fc923e with
the flags it set -- nothing between the `cmp` and the `jbe` touches them.

The trampoline sits in the 26 bytes of zero padding between the date-spread stub's table
(ends 0x14252e7e6) and the first nullguard's trampoline (starts 0x14252e800), verified
empty in the exe.  It is 20 bytes.  All-or-nothing: every target byte is checked first and
nothing is written unless all of them match.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard2.lua
  2. add to sider.ini, in the [modules] list:   lua.module = "fl26nullguard2.lua"
     -- after fl26nullguard.lua, so the two trampolines are written in a fixed order
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x14252e7e8, old="0000000000000000000000000000000000000000",
   new="4885c00f84d5aba9fe39a8c0030000e942aaa9fe",
   why="null-guard trampoline: test rax,rax; jz 0x140fc93c6; cmp [rax+0x3c0],ebp; jmp 0x140fc923e"},
  {va=0x140fc9238, old="39a8c0030000", new="e9ab55560190",
   why="redirect the unchecked deref at 0x140fc9238 to the trampoline (jmp rel32 + nop)"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard2", n))

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
                      "nullguard2: null-check at 0x140fc9238"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
