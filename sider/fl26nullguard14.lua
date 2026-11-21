--[[
fl26caps -- runtime patch applier (nullguard14 set).

Defensive fix, NOT a capacity patch.  One block of code is rewritten in place; no trampoline, no
cave, no spare bytes anywhere else.  FL26 and FL 2027 have the same bytes at the same address.

Set:     nullguard14
Summary: a cup's bracket screen with a field it has no bye layout for (17, 19, 21-23, 25-27, 29,
         31 clubs, or 0/1) hides the empty places at the end instead of reading a NULL table and
         crashing the game (1 patch, 73 bytes at 0x140b344b8)

The bug.  The knockout bracket screen of a cup (Database -> Competition Info -> the cup ->
Fixtures, and the cup's page the game opens after the user's match of a round) puts the cup's
clubs on 32 places.  0x140b344a0 hides the places nobody plays on (the byes): it asks
0x140b33340 for the list of the 32 - n places to hide, n being the cup's club count (+0x30a of
its regulation, copied to +0x94 of the screen):

    140b344b3  call   0x140b33340            ; bye places for n clubs
    140b344b8  mov    rbx, rax               ; NULL unless n is 2-16, 18, 20, 24, 28 or 30
    ...                                      ; the 32 places shown (+0x99..+0xb8 = 1)
    140b344e7  cmp    ecx, 0x20 / je out     ; 32: no byes
    140b344ec  mov    eax, 0x20 / sub eax, ecx / je out
    140b344ff  mov    edi, eax               ; 32 - n places to hide
    140b34501  mov    eax, [rbx]             <-- NULL: access violation

For any other field the list is NULL and the screen crashes the game at 0x140b34501 (above 32 the
count goes negative and it reads NULL as well).  The game fills a country's cup from its leagues
when the season is built, so a top league that ships with fewer clubs than its cup's bracket
gives the cup a field like that: B475 (edln 16.11.2026, FL 2027, Worldpack r12, Boca Juniors):
the world's Liga Profesional (30) has 26 clubs, the Copa Argentina (59) was filled with them,
and the page the game opens after Boca's first-round match of it crashed at 0x140b34501
(Application Error, FL_2027.exe offset 0xb34501), with and without the tester's other modules.
B278 (29.10.) was the same screen; fl26chain only cuts the cups of a world's chained leagues to a
field the screen draws, and a shipped cup like this one is not one of them.

The fix.  The same block, packed tighter (rep stosb for the 32 shown places), keeps every
supported field exactly as it was and gives the others the places from n to 31 to hide: a
0..31 table of dwords the exe already has in .rdata at 0x14260ce80, read from its n-th entry.
So the screen shows the cup's n clubs on the first n places, in the order the game pairs them
for the first round (1 v 2, 3 v 4 ...), and hides the rest -- the places the screen's other
functions walk (0x140b33480 maps a place to a club past the hidden ones, 0x140b34f20 fills the
shown ones) then never ask for a club past the n it has.  A field of 32 or more hides nothing
and returns, as 32 always did:

    140b344b8  mov    [rsp+0x30], rbp        ; saved first now (restored at 0x140b34552)
    140b344bd  mov    [rsp+0x38], rdi
    140b344c2  mov    rbx, rax               ; the game's bye places, or NULL
    140b344c5  lea    rdi, [rsi+0x99]
    140b344cc  mov    ecx, 0x20
    140b344d1  mov    al, 1
    140b344d3  rep stosb                     ; the 32 places shown, as the four stores did
    140b344d5  mov    ecx, [rsi+0x94]        ; n
    140b344db  test   rbx, rbx
    140b344de  jne    0x140b344eb            ; a field the game has a layout for: as before
    140b344e0  lea    rbx, [rip+0x1ad8999]   ; 0x14260ce80: dwords 0, 1, 2 ... 31
    140b344e7  lea    rbx, [rbx+rcx*4]       ; from n: places n..31 hidden
    140b344eb  mov    eax, 0x20
    140b344f0  sub    eax, ecx
    140b344f2  jbe    0x140b34552            ; n >= 32: nothing to hide (rdi/rbp restored there)
    140b344f4  mov    edi, eax
    140b344f6  11 bytes of nop               ; then the game's loop at 0x140b34501 as it was

Nothing else jumps into the block (checked over the function 0x140b344a0..0x140b34566 and every
rel32 jump and call of the exe).  Checked offline (tools/native/test_nullguard14.py): the
function run in an emulator from both exes, original and patched, for every n from 0 to 127 --
the same places shown and the same places hidden for every field the game has a layout for, the
original crashing at 0x140b34501 for the others and the patched one hiding n..31 (nothing past
31), callee-saved registers and the stack as they were.

What it does not do: a cup of 26 still plays as the game makes it (13 first-round ties).  The
field itself is the world's: a top league with fewer clubs than its cup's bracket.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard14.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard14.lua"
     -- after fl26nullguard13.lua (or let fl26guards.lua carry it)
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes, and the table it points at.
--]]

local m = {}

local patches = {
  {va=0x140b344b8,
   old="488bd848b8010101010101010148898699000000488986a1000000488986a9000000488986b10000008b8e9400000083f9207470b8200000002bc1746748896c243048897c24388bf8",
   new="48896c243048897c2438488bd8488dbe99000000b920000000b001f3aa8b8e940000004885db750b488d1d9989ad01488d1c8bb8200000002bc1765e8bf80f1f8400000000000f1f00",
   why="cup bracket screen: a field with no bye layout hides places n..31 (was: read a NULL table at 0x140b34501)"},
}

-- the exe's own dwords 0..31 the new block reads its places from (checked, never written)
local TABLE_VA = 0x14260ce80

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

local function seq32()
  local out = {}
  for i = 0, 31 do
    out[#out + 1] = string.format("%02x000000", i)
  end
  return table.concat(out)
end

function m.init(ctx)
  local n = #patches
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard14", n))

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
  local tab = memory.read(TABLE_VA, 128)
  if tab ~= unhex(seq32()) then
    log(string.format("fl26caps: MISMATCH at 0x%x: the table of places 0..31 is not there (found %s...)",
                      TABLE_VA, tohex(tab and string.sub(tab, 1, 16))))
    bad = bad + 1
  end
  if bad > 0 then
    log(string.format("fl26caps: ABORTED, %d of %d sites did not match. "
                      .. "Nothing was written; the game is unmodified.", bad, n + 1))
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
                      "nullguard14: a cup's bracket screen draws a field it has no bye layout for (0x140b344b8)"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
