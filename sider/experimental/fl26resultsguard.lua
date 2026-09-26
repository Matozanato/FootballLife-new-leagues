--[[
fl26resultsguard -- keep an empty matchday-results list from ending the game.

What crashed. menu::MatchDayResultsBase (vtable 0x1427215e0) opens the results screen that
follows `Skip Match`. Its slot 0xd8, 0x140ca2060, draws the headline and then picks a page out
of a vector at +0x90 (32-byte entries, each holding a vector of 8-byte items). When the page
index at +0xa8 is out of range it falls back to entry 0 -- and when the vector is empty it
reports "invalid vector<T> subscript" (0x140ca2203), which ends in ucrtbase's fail-fast
0xc0000409 at +0xa527e. The same happens when entry 0's own item vector is empty (0x140ca21db).

On 25 September a Master League career in our world died there twice, both times on day 49
of its third year -- the first leg of the Europa and Conference League knockout play-offs
that fl26swiss puts into regulations 188/189 -- with the same stack (0x14149ff1e ... 0x140e43462
-> 0x140ca2060). A tester hit the same fault (ucrtbase, offset 0xa527e) at the Europa League
knockout in another world (issue #9). Why that screen gets no entries for that day is a
separate question; this module only keeps the empty list from taking the whole game with it.

What this writes. The two `lea rcx, "invalid vector<T> subscript"` in front of the reports
become a jmp to 0x140ca2289, the function's own epilogue (restore rbx/rsi, al = 1, pop rdi,
ret). Nothing else in the function has run yet that needs undoing: the headline has been
set, the page is simply left empty. When the list has entries, nothing changes.

Same apply rule as every fl26 module: verify all sites first, write only if all match.
--]]

local m = {}

local patches = {
  {va=0x140ca21db, old="488d0df6fd8f01", new="e9a90000009090", why="results screen: entry 0 has no items -> leave through the epilogue at 0x140ca2289 instead of reporting a bad subscript"},
  {va=0x140ca2203, old="488d0dcefd8f01", new="e9810000009090", why="results screen: no entries at all -> leave through the epilogue at 0x140ca2289 instead of reporting a bad subscript"},
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
  log(string.format("fl26resultsguard: set '%s', %d patches, verifying", "resultsguard", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26resultsguard: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26resultsguard: ABORTED, %d of %d sites did not match. "
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
      log(string.format("fl26resultsguard: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26resultsguard: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  if failed == 0 then
    log(string.format("fl26resultsguard: applied all %d patches -- %s", written, "an empty matchday-results list leaves the screen empty instead of crashing"))
  else
    log(string.format("fl26resultsguard: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
