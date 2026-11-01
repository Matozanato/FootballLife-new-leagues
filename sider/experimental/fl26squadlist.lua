--[[
fl26squadlist -- Select Team: the Squad List is filled on the league rows too.

What the player sees. The Select Team screen (TeamSelectSingle@menu, vtable 0x14271d050) has two
columns: the leagues and, after Confirm, the clubs of that league. The panel on the right shows
"Squad List" (the players of the club under the cursor) while the cursor is in the club column.
In the league column it shows:
  - "League Info" (cups, promotion, higher and lower league) when the screen was built with
    League Info on: only the start of a new Master League (0x140adf1d0, "ML/MLTeamSel");
  - otherwise an EMPTY Squad List: Master League > Database > Team Info, League mode, and the
    other screens that list leagues and then clubs. So while scrolling through the leagues
    there is a red panel with empty rows and nothing in it.
The same in Konami's game, in FL26 (2.2) and in FL27 (1.00), with and without our modules.

What this writes. Two jumps.

1. The panel update (0x140c98ee0, vtable +0x250) asks the list whether the cursor is in the
league column (0x140c95790). If it is and League Info is off ([this+0xb8] != 1), it jumps to
0x140c98fde, which writes the invalid team id (dword 0x14351ae44) into [this+0x90] and so
empties the list. The jump is retargeted:

    0x140c98f57  jne 0x140c98fde  ->  jne 0x140c990b1

0x140c990b1 is the club column's own branch: "Squad List" title, then the club id from
0x140c94ff0 (the league's remembered row, 0x140c95300(list, -1, -1); the first club until the
cursor has been in that league's clubs; the invalid id when the league has none), stored in
[this+0x90], and the list refreshed (vtable +0x260, +0x268) when the club changed.

2. That refresh (0x140c991b0, vtable +0x268) asks the same question again and, in the league
column, skips loading the players (0x140ec4ef0(this, [this+0x90], 0, 1, 0)): with 1 alone the
title and the club were right and the rows still empty. The check is nopped:

    0x140c991f8  jne 0x140c99214  ->  nop nop

0x140ec4ef0 returns 0 rows for the invalid id, so a league without clubs stays empty as before.

So the league row shows the squad of the club that Confirm would put the cursor on. Scrolling
the leagues changes it; going into the clubs and back keeps the same club. Checked in FL27 1.00
on 2026-11-01 (Europack eu5, Master League > Database > Team Info): Jupiler Pro League,
Challenger Pro League, Championship, Turkish 1. League, fast scrolling, into the clubs and back.

Which screens. 0x140c98ee0 is +0x250 of every TeamSelect class (TeamSelectSingle, ...Request,
...RequestML, ...SingleSearch, ...DefaultTeamML and the MenuEdit*TeamSelect ones of Edit);
0x140c991b0 is +0x268 of TeamSelectSingle, ...Request, ...RequestML and MenuEditTm/Ex/
TransferBefore/Representative/CmnTeamSelectBase. ...SingleSearch and ...DefaultTeamML have
their own refresh, which 2 does not touch; MenuEditCoachTeamSelect has its own +0x258/+0x260
and a no-op +0x268.

Why it is safe. The branch of 1 uses nothing the league path set up. rbp is saved at 0x140c98f4b
because the league path changes it and restores it at 0x140c99092; the club branch never
changes rbp, so it needs no restore. The branch returns through the function's own epilogue,
as it does for the club column. Confirm, Return and the cursor are the list's, not this
function's. The start of a new Master League (League Info on) does not reach
the jump: it is taken only when [this+0xb8] != 1. 2 makes the refresh do in the league column
what it does in the club column: the same call with the id the update stored.

FL26 2.2 and FL27 1.00 have the same bytes at the same address (FL27's exe is FL26 2.2's code).
Same apply rule as every fl26 module: verify all sites first, write only if all match.
--]]

local m = {}

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

local patches = {
  -- the context: cmp byte [rbx+0xb8],1 / mov [rsp+0x48],rbp / mov byte [rbx+0xc0],1, unchanged
  {va=0x140c98f44, old="80bbb800000001", new="80bbb800000001",
   why="Select Team: is League Info on? (checked, not changed)"},
  {va=0x140c98f57, old="0f8581000000", new="0f8554010000",
   why="Select Team, league row without League Info: show the squad of the league's club (0x140c990b1) instead of an empty list (0x140c98fde)"},
  -- mov rcx,[rbx+0x98] / call 0x140c95790 (league column?) / test al,al / jne 0x140c99214
  {va=0x140c991ea, old="488b8b98000000e89ac5ffff84c0751a", new="488b8b98000000e89ac5ffff84c09090",
   why="Squad List refresh (0x140c991b0): load the club's players in the league column too"},
}

function m.init(ctx)
  local n = #patches
  log(string.format("fl26squadlist: %d sites, verifying", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26squadlist: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26squadlist: ABORTED, %d of %d sites did not match. "
                      .. "Nothing was written; the game is unmodified.", bad, n))
    return
  end

  -- pass 2: write, then read back
  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    if p.new ~= p.old then
      memory.write(p.va, new)
    end
    local back = memory.read(p.va, #new)
    if back == new then
      written = written + 1
      log(string.format("fl26squadlist: [%d/%d] 0x%x %d bytes  %s", i, n, p.va, #new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26squadlist: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  if failed == 0 then
    log(string.format("fl26squadlist: applied all %d patches -- Select Team shows a squad on the league rows too", written))
  else
    log(string.format("fl26squadlist: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
