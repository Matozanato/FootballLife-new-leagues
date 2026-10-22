--[[
fl26caps -- runtime patch applier (nullguard12 set).

Defensive fix, NOT a capacity patch.  One block of code is rewritten in place; no
trampoline, no cave, no spare bytes anywhere else.

Set:     nullguard12
Summary: a squad entry whose player no longer exists is skipped when the game adds to a 7-bit
         value of every player of a team during a Master League season, instead of crashing
         the game (1 patch, 72 bytes at 0x141321d00)

The bug.  A loop in the Master League calendar code walks the players of a team (count in the
low 7 bits of the word at team+0x426, 8-byte player handles from team+0x14c), looks each one
up with 0x1414bc9a0 -- the same lookup as nullguard11 -- and adds a signed amount (edi) to a
7-bit field of the player record, bits 18..24 of the dword at +0x13c, kept within 0..100:

    141321cf8  mov    rcx, rsi
    141321cfb  call   0x1414bc9a0            ; rax = player record, or 0 when he is not there
    141321d00  mov    ecx, [rax+0x13c]       <-- reads through rax, never checked
    141321d06  ...    field + edi, below 0 -> 0, 100 or more -> 100, else as it is
    141321d2d  mov    [rax+0x13c], ecx  (or edx at 141321d42)
    141321d48  inc    ebx                    ; next player

The lookup returns 0 when the handle names a player who is not in Player.bin: access violation
at 0x141321d00.  Seen 22.10.2026, twice in two new careers on one world (FK Banga, Lithuania;
day 301 of the first, day 75 of the second), with an Edit Data file saved on an older build of
that world in the save folder.  nullguard11 lets the career start past such a squad entry;
the entry is still in the squad, and this loop met it in the season.

The fix rewrites the 72 bytes 0x141321d00..0x141321d48 with the same arithmetic in one path
and a null check in front:

    141321d00  test   rax, rax
    141321d03  je     0x141321d48             ; no such player: next one
    141321d05  mov    ecx, [rax+0x13c]
    141321d0b  mov    edx, ecx / shr edx, 18 / and edx, 0x7f / add edx, edi
    141321d15  jns    +2 ; xor edx, edx       ; below 0 -> 0
    141321d19  cmp    edx, 100 ; jb +5 ; mov edx, 100
    141321d23  and    ecx, 0xfe03ffff ; shl edx, 18 ; or ecx, edx
    141321d2e  mov    [rax+0x13c], ecx
    141321d34  jmp    0x141321d48 ; 18 x nop

The three paths of the original (below 0: field cleared; 100 or more: and 0xff93ffff / or
0x1900000; else the field replaced) all come to "field = clamp(field + edi, 0, 100)", and the
new block gives the same dword for all of them (checked over 200,000 random dwords and amounts).
Nothing outside the block jumps into it; ecx and edx are written before they are read at the
loop head, as before.  A team whose players all exist gets exactly what it got before.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard12.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard12.lua"
     -- after fl26nullguard11.lua (or let fl26guards.lua carry it)
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x141321d00,
   old="8b883c0100008bd1c1ea1283e27f03d7790881e1ffff03feeb1383fa647d02761481e1ffff93ff81c90000900189883c010000eb13c1e21233d181e20000fc0133d189903c010000",
   new="4885c074438b883c01000089cac1ea1283e27f01fa790231d283fa647205ba6400000081e1ffff03fec1e21209d189883c010000eb12909090909090909090909090909090909090",
   why="team players' 7-bit value at +0x13c: skip a squad entry whose player lookup returned 0 (was: read [rax+0x13c] with rax=0)"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard12", n))

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
                      "nullguard12: a missing player is skipped when a team's players are updated (0x141321d00)"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
