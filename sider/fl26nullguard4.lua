--[[
fl26caps -- runtime patch applier (nullguard4 set).

Defensive fix, NOT a capacity patch.  Written by hand, like the other nullguards, because it
installs a code-cave trampoline rather than resizing a field; every byte below was computed
against the exe and disassembled back before being written here.

Set:     nullguard4
Summary: null-check at 0x1415720d0, 2 patches (trampoline + prologue redirect)

The bug: the function at 0x1415720d0 takes a coach record in `rdx` (stride 0x258, with a
40-byte id table at +0x220), saves it in rbx, and walks that table without ever checking the
pointer:

    1415720d0  mov    qword ptr [rsp + 0x20], rbx      <-- prologue, 5 bytes
    ...
    141572100  mov    rbx, rdx                         <-- argument 2, the coach record
    ...
    14157211e  lea    r8, [rbx + 0x220]
    141572125  movzx  ecx, byte ptr [r8]               <-- rbx can be 0

The fault is at 0x141572125, a read of address 0x220 -- a null pointer plus the field's own
offset rather than a corrupted one.  The null arrives from the caller at 0x140f143a0, which
passes the result of the coach lookup 0x1414bc780 straight through:

    140f14384  call   0x1414bc780
    ...
    140f1439d  mov    rdx, rax                         <-- unchecked
    140f143a0  call   0x1415720d0

Its sibling at 0x141522a51 does exactly the check that is missing:

    141522a27  call   0x1414bc780
    141522a2c  mov    r13, rax
    141522a2f  test   rax, rax
    141522a32  je     0x141522b3c                      <-- skips the call entirely
    ...
    141522a51  call   0x1415720d0

So the game's own answer for "there is no coach record" is: do not call this function.  The
guard gives 0x1415720d0 that same behaviour from the inside -- when rdx is null it returns
at once, which is what the checked caller already arranges.

The return value is safe to fake.  0x1415720d0 has a single exit (0x14157238d, per .pdata
the function spans 0x1415720d0..0x14157238e) and it never sets rax on the way out; whatever
is in rax is the leftover of the stack-cookie check at 0x14159f3e0.  All seven callers --
0x140f143a0, 0x1412638b5, 0x14126fd69, 0x1413184ec, 0x141522a51, 0x14156adf3, 0x14156e9a2 --
discard rax: each either overwrites it before any use or ignores it outright.  The function
is effectively void, so `xor eax, eax; ret` matches the normal path.

The fix: the first five bytes of the prologue (`mov [rsp+0x20], rbx`) are replaced by a jump
to a trampoline.  The trampoline tests rdx, returns 0 when it is null, and otherwise runs the
relocated prologue and jumps back to 0x1415720d5 -- an instruction boundary (`push rbp`), so
nothing is split.  The relocated `mov` is a home-slot spill only; when the guard returns early
it is skipped along with the epilogue that would have restored it, and rbx itself is untouched.

The trampoline sits at 0x14252e840, in the tail of the last page of .trace: past the raw data
the file ends at (0x14252e800), before .rdata begins (0x14252f000), and after every cave range
this project already uses -- the caps date-spread stub and table at 0x14252e690..0x14252e7e6,
nullguard2's 20 bytes at 0x14252e880, fl26nullguard.lua's 23 bytes at 0x14252e800, and
nullguard3's 23 bytes at 0x14252e820.  The page is zero-filled there by the loader; because it
is beyond the file's raw data it cannot be confirmed from the exe on disk, so pass 1 confirms
it in the live process instead and refuses to write if anything else has claimed it.  The stub
is 18 bytes, taking 0x14252e840..0x14252e851.  All-or-nothing: every target byte is checked
first and nothing is written unless all of them match.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard4.lua
  2. add to sider.ini, in the [modules] list:   lua.module = "fl26nullguard4.lua"
     -- after fl26nullguard3.lua, so the trampolines are written in a fixed order
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x14252e840, old="000000000000000000000000000000000000",
   new="4885d2740a48895c2420e9863804ff31c0c3",
   why="null-guard trampoline: test rdx,rdx; jz null_ret; mov [rsp+0x20],rbx; jmp 0x1415720d5; null_ret: xor eax,eax; ret"},
  {va=0x1415720d0, old="48895c2420", new="e96bc7fb00",
   why="redirect fn 0x1415720d0 prologue (5 bytes) to the trampoline at 0x14252e840 (jmp rel32)"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard4", n))

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
                      "nullguard4: null-check at 0x1415720d0"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
