--[[
fl26caps -- runtime patch applier (nullguard8 set).

Defensive fix, NOT a capacity patch.  Like the other nullguards it installs a code-cave
trampoline rather than resizing a field; every byte below was computed against the exe and
disassembled back before being written here.

Set:     nullguard8
Summary: negative-position guard at 0x1413236e1, 2 patches (trampoline + site redirect)

The bug: a league position is used as an array index without being checked.
0x1413235a0 walks the twenty standings entries of a competition looking for a club, and
when it finds one it takes the entry's `+4` field -- the club's position in the table --
and indexes a table with it:

    1413235ca  mov    dword ptr [rbp + 0x77], 3        ; the default
    14132366f  mov    dword ptr [rbp + 0x77], r12d     ; = 0 before the loop
    141323682  <loop over r13d = 0x14 = twenty entries>
    1413236b2  test   ecx, 0xffffc000                  ; packed club id, low 14 bits ignored
    1413236c3  mov    eax, dword ptr [r14 + 4]         ; found: the position field
    1413236c7  mov    dword ptr [rbp + 0x77], eax
    1413236e1  mov    eax, dword ptr [rbp + 0x77]
    1413236e4  sub    ecx, dword ptr [r8 + rax*4]      <-- faults

A standings pair that has never been filled in carries -1 in that field, and -1 is exactly
what the read at +4 returns for a club whose competition has produced no results yet.  On
17 September 2026 a fresh 39-league world died here on day 360 of its first season, fault
0x13236e4: rax = rcx = rdx = 0xffffffff, an access violation reading 0x5428e52dc, which is
0x1428e52e0 + 0xffffffff * 4 -- the element one before the start of the table.

The guard does not invent a position.  It skips the subtraction when the index is negative,
which leaves ecx holding the value it was given three instructions earlier (`mov ecx, edx`
at 0x1413236df), i.e. the same result as subtracting zero: an unranked club contributes no
adjustment.  The code immediately after the site (`cmp edx, 5` / `cmp ecx, edx`) reads both
registers and is unaffected by taking the branch.

Seven bytes at 0x1413236e1 -- the load of the position plus the faulting subtraction -- are
replaced by a jump to a trampoline that does both with a sign test between them.  Two nops
pad the rest.

The trampoline sits at 0x14252e8c0.  .trace holds 0x252d800 bytes of virtual data and so
ends at 0x14252e800; everything from there to where .rdata begins at 0x14252f000 is the
zero-filled tail of the last page.  Reading those addresses out of the exe *file* shows
non-zero bytes, because the file offset runs on into .rdata's raw data -- the running
process is the authority there, and the applier verifies the zeros before writing.
nullguard5, 6 and 7 hold 0x14252e860, 0x14252e880 and 0x14252e8a0; this is the next slot.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard8.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard8.lua"
     -- after fl26nullguard7.lua, so the trampolines are written in a fixed order
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x14252e8c0, old="00000000000000000000000000000000",
   new="8b457785c07c04412b0c80e9184edffe",
   why="standings-position guard trampoline: mov eax,[rbp+0x77]; test eax,eax; "
    .. "jl skip; sub ecx,[r8+rax*4]; skip: jmp 0x1413236e8"},
  {va=0x1413236e1, old="8b4577412b0c80", new="e9dab120019090",
   why="redirect the unchecked position index at 0x1413236e1 to the trampoline (jmp rel32 + 2 nop)"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard8", n))

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
                      "nullguard8: negative standings position guarded at 0x1413236e1"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
