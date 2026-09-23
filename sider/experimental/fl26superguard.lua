--[[
fl26superguard -- stop the UEFA Super Cup setup from reading entry -1.

What crashed. 0x1413604a0 prepares the UEFA Super Cup (regulation 7). It walks the season's
entry vector (48-byte records, u16 regulation id first) for the Champions League entry (id 4)
and the Europa League entry (id 6), and indexes both results without checking them: a
missing entry leaves -1, `lea rax,[r8+r8*2]; shl rax,4` turns that into -48, and the read at
0x1413605a9 faults. On 23 September a Master League season in our Montenegrin league went
down exactly there between day 81 and day ~100 (fault offset 0x13605a9), in an August-start
world where one of the two entries was not in the vector. Why it is missing is a separate
question; this module only keeps a missing entry from taking the whole game with it.

What this writes. The 8 bytes at 0x14136059a (lea + shl) become a jmp to a trampoline that
leaves the function through its own epilogue when either lookup came back -1, and otherwise
runs the two original instructions and resumes at 0x1413605a2:

    14252ee20  cmp  r8d, -1            ; Champions League entry not found
    14252ee24  je   out
    14252ee26  cmp  ebx, -1            ; Europa League entry not found
    14252ee29  je   out
    14252ee2b  lea  rax, [r8+r8*2]     ; the original two instructions
    14252ee2f  shl  rax, 4
    14252ee33  jmp  0x1413605a2
    14252ee38  out: jmp 0x141360b0a    ; the function's epilogue

Leaving at 0x141360b0a is what the function already does when regulation 7 is absent: the
local vector at [rbp-0x28] is still empty at that point, so nothing is left allocated. The
cost of taking the exit is a Super Cup without its two entrants for that season -- when both
entries exist, nothing changes.

The trampoline sits at 0x14252ee20, after fl26augseason's (0x14252ee00, 0x15 bytes).

Same apply rule as every fl26 module: verify all sites first, write only if all match.
--]]

local m = {}

local patches = {
  {va=0x14252ee20, old="0000000000000000000000000000000000000000000000000000000000", new="4183f8ff741283fbff740d4b8d044048c1e004e96a17e3fee9cd1ce3fe", why="Super Cup trampoline: leave 0x1413604a0 through its epilogue when the UCL (4) or UEL (6) entry is missing, else lea/shl and resume at 0x1413605a2"},
  {va=0x14136059a, old="4b8d044048c1e004", new="e981e81c01909090", why="jmp from the unchecked index into the trampoline at 0x14252ee20"},
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
  log(string.format("fl26superguard: set '%s', %d patches, verifying", "superguard", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26superguard: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26superguard: ABORTED, %d of %d sites did not match. "
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
      log(string.format("fl26superguard: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26superguard: WRITE FAILED at 0x%x (%s) -- read back %s",
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
    log(string.format("fl26superguard: applied all %d patches -- %s", written, "a missing Champions League or Europa League entry skips the Super Cup setup instead of crashing"))
  else
    log(string.format("fl26superguard: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
