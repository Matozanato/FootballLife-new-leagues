--[[
fl26ctlguard -- after a club change, give the old club back to the computer.

What went wrong. Byte +0x41d of a team record says who plays it: 0 is the user's pad, 0xff
is the computer. On 25 September a Master League career had two clubs at 0: the one the
manager runs (club C) and club B, the club the manager had been sacked from. The manager
history at block+0x17b5780 shows A -> B -> C. The first move handed A back to the computer
and the second did not.

What that breaks. The hub's "Next" shows the old club's fixtures (through the day schedule,
below), Skip Match lists its
results with the pad icon, the current-match context keeps picking its games, and the save
list names the career after it: the save header takes the FIRST club at 0, and B (row 548)
comes before C (row 1056).

Why it is not fixed at the source. The club change (0x140adde80) finds the old club
through the global at 0x1436f9a60, which 41 menu call sites overwrite through its setter
0x140e40f90. A sacking and a job offer go through several of those menus, so the handle it
builds can name the wrong club. Proving which one needs a sacking, and a sacking cannot be
produced on demand. This guard makes the result right whatever the path was.

What this writes. The day loop's call to 0x1412fd680 at 0x1413071ff (the routine that
writes the match screen's controller sides onto the two match-context teams) goes through
a trampoline at 0x14252ef00. The trampoline makes the original call and then sweeps the team
array:

    user   = [block+0x1798ab0]             the user club's handle (0x1414bb650 reads it)
    only if that club exists and is itself at 0 (a Master League career, not BAL)
    for every team at 0 that is not the user club:
        skip the two match-context teams, but only when the user club is one of them
        (the match screen may put the pad on the other side of the user's own match)
        otherwise set it to 0xff, and mark the user's day schedule as stale

The day schedule. The hub's fixture strip ("Next") does not read the controller bytes. It
reads a per-controller table of one entry per day, {match id, competition, round, kind,
team}, at block+0x19115f0 + controller*0x16dc (0x1642a28 before the -calendar set of 0.2.0) (365 entries of 16 bytes after an 8-byte
head whose +4 is the owner club's handle). 0x14158cfb0 files every scheduled match into the
table of each side's controller (0x14151ad90 = the team's +0x41d), so while the old club was
still at 0 its whole season went into the user's table, and it stays there after the byte is
fixed. The day loop (0x1413071e1 -> 0x1413007d0 -> 0x141350650) rebuilds table 0 with
0x14158c820 whenever the owner handle at block+0x19115f4 (was 0x1642a2c) is not the user club. Writing -1
there is how this guard asks for that rebuild; it happens the next day, from the corrected
controller bytes.

Nothing else is touched: other controller values (a second pad = 1, 2, ...) stay as they
are. The teams base and count are read from the relocated lookup 0x1414bca80 after
fl26caps has run, so the guard follows whatever set is installed. This module must be
listed AFTER fl26caps in sider.ini.

Cave 0x14252ef00..0x14252eff9, the last free stretch before .rdata (0x14252f000), after
fl26seasonend's flag byte at 0x14252eef0.

Same apply rule as every fl26 module: verify all sites first, write only if all match.
--]]

local m = {}

local CAVE = 0x14252ef00
-- built for teams at +0x1877070 and the count at +0x3b20880; both are replaced below
local TRAMP = "4883ec28e877e7dcfe488b05006f1d014885c00f84dc0000004c8b40484d85c00f84cf00000041bbff"
  .. "ffffffbaffffffff4c8b50504d85d2740e458b9a985a0300418b9228610300458b88b08a79014539cb"
  .. "74104439ca740b41bbffffffffbaffffffff4489c825ff3f00003dfd3f00000f837e0000004869c090"
  .. "060000498d8c00707087014439090f856600000080b91d040000000f8559000000498d887070870141"
  .. "8b808008b20385c00f84430000003d004000000f873800000080b91d040000007524448b114539ca74"
  .. "1c4539da74174139d27412c6811d040000ff41c780f4159101ffffffff4881c190060000ffc875c848"
  .. "83c428c3"
local TEAMS_LE, COUNT_LE = "70708701", "8008b203"

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
  -- the relocated lookup: `lea rdi,[r8+teams]` at 0x1414bcade, `mov eax,[r8+count]` at 0x1414bcb24
  local lea = memory.read(0x1414bcade, 7)
  local cnt = memory.read(0x1414bcb24, 7)
  if lea == nil or cnt == nil or string.sub(lea, 1, 3) ~= unhex("498db8")
     or string.sub(cnt, 1, 3) ~= unhex("418b80") then
    log(string.format("fl26ctlguard: ABORTED, the team lookup at 0x1414bca80 is not the "
                      .. "expected code (%s / %s); nothing was written", tohex(lea), tohex(cnt)))
    return
  end
  local teams_le, count_le = tohex(string.sub(lea, 4, 7)), tohex(string.sub(cnt, 4, 7))
  local tramp = string.gsub(TRAMP, TEAMS_LE, teams_le)
  tramp = string.gsub(tramp, COUNT_LE, count_le)

  local patches = {
    {va=CAVE, old=string.rep("00", #tramp / 2), new=tramp,
     why="trampoline: call 0x1412fd680, then give every club at controller 0 except the user's back to the computer"},
    {va=0x1413071ff, old="e87c64ffff", new="e8fc7c2201",
     why="the day loop's call to 0x1412fd680 -> the trampoline at 0x14252ef00"},
  }
  local n = #patches
  log(string.format("fl26ctlguard: teams at +0x%s, count at +0x%s, %d patches, verifying",
                    teams_le, count_le, n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26ctlguard: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26ctlguard: ABORTED, %d of %d sites did not match. "
                      .. "Nothing was written; the game is unmodified.", bad, n))
    return
  end

  -- pass 2: write, then read back. The trampoline goes first, so the call is never
  -- redirected into a cave that is not there.
  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    local back = memory.read(p.va, #new)
    if back == new then
      written = written + 1
      log(string.format("fl26ctlguard: [%d/%d] 0x%x %d bytes  %s", i, n, p.va, #new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26ctlguard: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  if failed == 0 then
    log(string.format("fl26ctlguard: applied all %d patches -- only the user's club keeps the user's controller", written))
  else
    log(string.format("fl26ctlguard: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
