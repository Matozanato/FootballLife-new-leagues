--[[
fl26seasonend -- let the season end run for our leagues and for the French and Italian chains.

Measured 2026-09-23: at the July rollover of season 2 nobody was promoted or relegated in
any league of the European group, England included, and the league tables carried on from
season 1 (47 rounds by November). The season-end filter 0x141365c50 has two gates that
explain it:

1. Region -> season group (call at 0x141365d7f to 0x141576140). France (region 3) and Italy
   (region 5) map to 5, "never", so the leagues we add below Ligue 2 and Serie B could never
   move. The trampoline at 0x14252ee40 answers 0 (the European group, ended on day 181) for
   regions 3 and 5 and asks the game's lookup for every other region. Only this call site
   is redirected: the season type chosen when a career is created is not touched.

2. Every competition left in the list is asked for its season object (0x141590750). One
   "no" -- and five of ours (76, 93, 94, 96, 98) lose theirs at New Year -- sends the WHOLE
   group down 0x141365ed0, which re-lists members and moves nobody. The guard at 0x14252ee60
   erases such a competition from the list the way the filter erases everything else
   (memmove through [0x14252fd68], end -= 2) and lets the rest of the group through.
   It also erases a competition whose league BELOW (+0x7e) has no season object: the mover
   builds the lower league's new list from that league's final table, and with no table it
   writes only the clubs relegated into it. First version (without this) emptied Ligue 2
   (81) and our 49 down to 3 clubs at the 2026-09-23 rollover. Skipping the upper league
   costs only its exchange with that one league, which is what the game did anyway.
   But an erased league is never closed and re-opened either, and plays on with its old
   table. So when fl26join.dll is loaded it sets the byte at 0x14252eef0 and this guard
   lets every league through: the DLL hooks the mover and sends the leagues that cannot be
   moved down the game's own no-movement path 0x141365ed0 instead. The erase above is only
   the fallback for a setup without the DLL.

Trampolines sit after fl26superguard (0x14252ee20..0x14252ee3c).
--]]

local m = {}

local patches = {
  {va=0x14252ee40, old="0000000000000000000000000000000000000000000000", new="448b014183f803740b4183f8057405e9ec7204ff31c0c3", why="region-group trampoline for the season end: regions 3 (France) and 5 (Italy) -> group 0, everything else through 0x141576140"},
  {va=0x14252ee60, old="0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", new="803d8900000000755c0fb70be8df1806ff84c0742e488b05946f1d01488b48480fb713e878c1f8fe0fb71366391075350fb7487e6683f9ff742be8b11806ff84c07522488d53024c8b45e84929d04889d9ff15b10e000048836de802488b45e8e99c6fe3fe488b45e8e98f6fe3fe", why="season guard: when fl26join.dll has set the byte at 0x14252eef0 every league goes on to its season-end split; without the DLL a league is erased from the list when it, or the league below it (+0x7e), has no season table"},
  {va=0x141365d7f, old="e8bc032100", new="e8bc901c01", why="the filter's region->group call -> the trampoline at 0x14252ee40"},
  {va=0x141365e48, old="0fb70be800a92200400fb6f684c00f44f7488b45e8", new="e913901c0190909090909090909090909090909090", why="the filter's season-object check -> the guard at 0x14252ee60"},
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
  log(string.format("fl26seasonend: set '%s', %d patches, verifying", "seasonend", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26seasonend: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26seasonend: ABORTED, %d of %d sites did not match. "
                      .. "Nothing was written; the game is unmodified. "
                      .. "This usually means the exe is a different build than the one "
                      .. "the patch set was generated from.", bad, n))
    return
  end

  -- pass 2: write, then read back, because writing to the code section can silently fail
  -- if the page is not made writable for us. Each site is logged as it goes, so that if a
  -- write throws and Sider stops the module, the log still names the last one that worked.
  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    local back = memory.read(p.va, #new)
    if back == new then
      written = written + 1
      log(string.format("fl26seasonend: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26seasonend: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  -- The patch has to land before the game allocates the edit block, and the log proves
  -- that it does: everything above is written during module init, which Sider finishes
  -- before it reports "Sider initialization complete", and the first `read_file::` line
  -- comes thousands of lines later. An earlier version of this file also registered a
  -- livecpk_get_filepath handler to re-read the first site at the first file request. It
  -- worked, but it made Sider log "lua ERROR from module_get_filepath" on every single
  -- file lookup -- 27811 of them in one session -- so it is gone. The ordering was never
  -- in doubt; the check was.

  if failed == 0 then
    log(string.format("fl26seasonend: applied all %d patches -- %s", written, "France and Italy are ended with the European group, and a competition with no season no longer blocks its group"))
  else
    log(string.format("fl26seasonend: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
