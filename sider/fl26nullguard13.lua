--[[
fl26caps -- runtime patch applier (nullguard13 set).

Defensive fix, NOT a capacity patch.  One block of code is rewritten in place and one jump is
pointed at its new start; no trampoline, no cave, no spare bytes anywhere else.

Set:     nullguard13
Summary: the pick of the clubs of the game's pre-season friendly cup (reg 106) stops when its
         list of candidates runs out, instead of reading below the list and crashing the game
         (2 patches, 55 bytes at 0x14135a379 and the loop's jump at 0x14135a404)

The bug.  Late in December the Master League picks the clubs of next year's pre-season friendly
cup.  0x1413598c0 finds regulation 0x6a (106, "Pre-season friendly Cup", 4 clubs), reads how many
clubs it takes (the low 7 bits at +0x30c) and has 0x141359a60 fill a list with them.  That
function gathers a list of candidates and then takes them from its end until the cup is full:

    14135a379  mov    rax, [rbp-0x39]        ; the candidates' end
    14135a380  add    rax, -4                <-- never compared with their start
    14135a384  mov    edx, [rax]             ; the next candidate
    ...                                      ; already picked? skipped; else pushed
    14135a3f0  mov    [rbp-0x39], rax
    14135a401  cmp    rcx, rbx               ; picked < wanted
    14135a404  jb     0x14135a380

With fewer different candidates than places the loop goes on below the list's start: with no
candidate at all it reads address -4 -- access violation at 0x14135a384.  Seen 24.10.2026 in a
loaded World Modpack career (Sporting FC, Costa Rica, after a sacking at the end of the first
season), three times out of three from the same save, on day 346-348, with the 0.2.5 beta's
module and with the 0.2.5 one alike.

The game already knows what to do with too few: back in 0x1413598c0 a list shorter than the cup
is topped up by 0x1413624c0, and if it is still short the cup is left alone (the function returns
0).  Only the loop never stopped.  The fix gives it the missing test at its head:

    14135a379  mov    rax, [rbp-0x39]
    14135a37d  cmp    rax, [rbp-0x41]        ; the candidates' start
    14135a381  jbe    0x14135a40a            ; none left: out of the loop, as when the cup is full
    14135a387  add    rax, -4
    14135a38b  mov    edx, [rax]             ; ... the rest as it was, 7 bytes on
    14135a3a8  8-byte nop                    ; was 15 bytes of nops aligning 0x14135a3b0
    14135a404  jb     0x14135a37d            ; the loop comes back to the test

0x14135a40a frees the candidate list as before.  Nothing else jumps into the block (checked over
the whole function, 0x141359a60..0x14135a47f).  With enough candidates the clubs picked are the
same, in the same order, and the list's end is left where it was: the block was run in an
emulator against the original over 12,000 random lists of candidates (with duplicates, and with
clubs already picked); with too few, the original crashed and the new block stopped.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard13.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard13.lua"
     -- after fl26nullguard12.lua (or let fl26guards.lua carry it)
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x14135a379,
   old="488b45c70f1f004883c0fc8b108955bb498b4c24084d8b0c244c3bc97445448bda4181e3ff3f00000f1f40006666660f1f840000000000",
   new="488b45c7483b45bf0f86830000004883c0fc8b108955bb498b4c24084d8b0c244c3bc9743e448bda4181e3ff3f00000f1f840000000000",
   why="pre-season friendly cup's pick: stop when the candidates run out (was: read below their start)"},
  {va=0x14135a404,
   old="0f8276ffffff",
   new="0f8273ffffff",
   why="the pick's loop comes back to the new test at 0x14135a37d"},
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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard13", n))

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
                      "nullguard13: the pre-season friendly cup's pick stops when its candidates run out (0x14135a379)"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
