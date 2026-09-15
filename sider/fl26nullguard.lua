--[[
fl26caps -- runtime patch applier (nullguard set).

Defensive fix, NOT a capacity patch. Written by hand (not by patchset.py) because it
installs a code-cave trampoline rather than resizing a field; every byte was computed and
verified against the exe before being written here.

Set:     nullguard
Summary: null-check at fn 0x141fea5b0, 2 patches (trampoline + prologue redirect)

The bug: fn 0x141fea5b0 does `mov rdi,[rcx+0x18]` at 0x141fea5ba with no null check, where
rcx is the result of graphics-resource factory 0x141fea410. When the factory returns null
(E_INVALIDARG on the resource create), the deref crashes. This was observed with ZERO of
our patches applied (the `none` set), reached through PES21_Hook.dll -- so it is a stock
game bug that our extra clubs only make more likely to hit.

The fix: overwrite the 10-byte prologue of 0x141fea5b0 with a jump to a trampoline in the
zero padding at the tail of .trace (0x14252e68c, executable, same section we already patch).
The trampoline returns 0 when rcx is null -- identical to the function's own internal
failure paths, which set rbx=0 and return it, an outcome the caller already handles -- and
otherwise runs the original prologue and jumps back to 0x141fea5ba. All-or-nothing: it
verifies every target byte first and writes only if all match.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26caps.lua
  2. add to sider.ini, in the [modules] list:   lua.module = "fl26caps.lua"
  3. start the game and read sider.log -- it says exactly what happened

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x14252e800, old="0000000000000000000000000000000000000000000000", new="4885c9740f48895c2418574883ec40e9a6bdabff31c0c3", why="null-guard trampoline: test rcx,rcx; jz null_ret; <relocated prologue>; jmp 0x141fea5ba; null_ret: xor eax,eax; ret"},
  {va=0x141fea5b0, old="48895c2418574883ec40", new="e94b4254009090909090", why="redirect fn 0x141fea5b0 prologue (10 bytes) to trampoline at 0x14252e68c (jmp rel32 + 5 nop)"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
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
                      .. "This usually means the exe is a different build than the one "
                      .. "the patch set was generated from.", bad, n))
    return
  end

  -- pass 2: write, then read back, because writing to the code section can silently fail
  -- if the page is not made writable for us. The trampoline (site 1) is written before the
  -- prologue redirect (site 2), so the jump target exists before the jump goes live.
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
    log(string.format("fl26caps: applied all %d patches -- %s", written, "nullguard: null-check at 0x141fea5b0"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
