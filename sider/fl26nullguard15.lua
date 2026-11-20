--[[
fl26caps -- runtime patch applier (nullguard15 set).

Defensive fix, NOT a capacity patch.  13 bytes are rewritten in place; no trampoline, no cave.

Set:     nullguard15
Summary: the players' value map's lookup (std::map::at, 0x140f59f40) gives 0 for a player key it
         does not hold, instead of throwing std::out_of_range, which nothing catches on the game's
         worker thread (abort -> __fastfail 7 -> c0000409 in msvcp140) (1 patch, 13 bytes at
         0x140f59fb5)

The bug.  B491 (vanni11 17.11.2026, FL 2027 1.1, Become a Legend, an edited Europack world, run
again without his other Lua modules): season 2, the step from 1.7. to 2.7. after
CmnUpdateSeasonEnd ends the game with c0000409.  The dump's C++ exception is std::out_of_range
("invalid map key") thrown on the game's worker thread, and the real unwind (from the exception
CONTEXT, no fl26 module on it) is:

    0x1413007d0  the day loop
    0x140f67630 -> 0x140f2e190 -> 0x140f28240   season update, its handler list
    0x140f9ad40 -> 0x140f9ac70 -> 0x140fb4c00   handlers of a group
    0x140fb4790  a season-end handler, only when mode 3 is on and mode 5 off (0x141576a20) and
                 the team's +0x63c & 0x6000000 == 0x2000000: for the 32-byte entries of a team
                 list (byte +0x18 <= 0x1b) it keeps the player with the highest value, starting
                 from the "none" key 0x14351ae30 with 0
    0x140f56320  the value of a player key {u16 index, u32 id}: the map at +0x78 of the
                 object's +0x140, else +0x148, else +0xa0
    0x140f59f40  std::map<key, u32>::at  -> 0x140f59fb5: _Xout_of_range("invalid map key")

A team-list entry whose key is not in the map (a player gone at the season end, an empty slot --
the "none" key {0xffff, 0} is never in it, ids start above 0 -- or a key whose index word no longer
matches) throws, and the game has no handler for it.  ML does not run this handler.

The fix.  The throw path of 0x140f59f40 returns a pointer to a dword 0 instead (the first entry of
the exe's .rdata table of dwords 0..31 at 0x14260ce80, the one nullguard14 reads too):

    140f59fb5  lea    rax, [rip+0x16b2ec4]   ; 0x14260ce80: dword 0
    140f59fbc  add    rsp, 0x28              ; the function's own frame
    140f59fc0  ret
    140f59fc1  int3

0x140f59f40 has one caller (0x140f56320, which reads the dword and returns it), and that has two:
the handler above (value 0 never beats its start of 0, so a missing player is skipped and an all-
missing list keeps the "none" key, as an empty list does) and 0x140ee7060, which itself gives 0
for the "none" key.  So 0 is the game's own "no player" value at both.  Nothing jumps into the
rewritten bytes but the function's own two branches to 0x140f59fb5.  Checked offline
(tools/native/test_nullguard15.py): 0x140f56320 run in an emulator from the exe, original and
patched, over a map built in memory: every key it holds gives the same value in both, a missing
key (and the "none" key) makes the original reach the throw and the patched one give 0, stack
and callee-saved registers as they were.

What it does not do: it does not put the missing player back in the map.  Whatever made the key
go missing (see B491 in the notes) is not fixed here; only the season end no longer dies of it.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard15.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard15.lua"
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes, and the dword it points at.
--]]

local m = {}

local patches = {
  {va=0x140f59fb5,
   old="488d0de4f87301ff156e5a5d01",
   new="488d05c42e6b014883c428c3cc",
   why="players' value map lookup: a missing player key gives 0 (was: std::out_of_range, uncaught -> c0000409)"},
}

-- the dword 0 the patched path returns a pointer to (exe .rdata, read only)
local ZERO_VA = 0x14260ce80

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
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard15", n))

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
  local zero = memory.read(ZERO_VA, 4)
  if zero ~= unhex("00000000") then
    log(string.format("fl26caps: MISMATCH at 0x%x: no dword 0 there (found %s)", ZERO_VA, tohex(zero)))
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
                      "nullguard15: a player key missing from the players' value map gives 0 (0x140f59fb5)"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
