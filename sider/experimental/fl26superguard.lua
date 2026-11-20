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

B470 (FL Testovi, GigaPack beta 3, season 2, 17.11.): the Super Cup was never played after the
first summer, and the log could not say whether this exit was the reason -- it was silent. Now
the exit goes through a counter stub before the epilogue, and the module logs when a counter
moves (checked on livecpk_make_key, as fl26joindll's ring is):

    14252ee38  out: jmp 0x14252eed0
    14252eed0  cmp  r8d, -1            ; Champions League entry missing
    14252eed4  jne  +6
    14252eed6  inc  dword [0x14252eef4]
    14252eedc  cmp  ebx, -1            ; Europa League entry missing
    14252eedf  jne  +6
    14252eee1  inc  dword [0x14252eef8]
    14252eee7  jmp  0x141360b0a        ; the function's epilogue, as before

Both counters moving at once means the entry vector was empty. The stub sits after
fl26seasonend's guard (..0x14252eece), the counters after its flag byte (0x14252eef0), all before
fl26ctlguard (0x14252ef00). The game's code writes the counters, so the page is made
PAGE_EXECUTE_READWRITE here (fl26joindll does the same for its ring); with no ffi, or if that
fails, the exit stays the plain jmp to the epilogue and nothing is counted. fl26swiss.dll fills
the Super Cup itself when the game leaves it empty (uefa_scup_fill_days).

Same apply rule as every fl26 module: verify all sites first, write only if all match.
--]]

local m = {}

local TRAMP_PLAIN = "4183f8ff741283fbff740d4b8d044048c1e004e96a17e3fee9cd1ce3fe"    -- out: jmp 0x141360b0a
local TRAMP_COUNT = "4183f8ff741283fbff740d4b8d044048c1e004e96a17e3fee993000000"    -- out: jmp 0x14252eed0
local STUB_VA     = 0x14252eed0
local STUB        = "4183f8ff7506ff051800000083fbff7506ff0511000000e91e1ce3fe"
local CNT_VA      = 0x14252eef4      -- u32 Champions League entry missing, u32 Europa League entry missing
local CAVE_PAGE   = 0x14252e000

local patches = {
  {va=0x14252ee20, old="0000000000000000000000000000000000000000000000000000000000", new=TRAMP_PLAIN, why="Super Cup trampoline: leave 0x1413604a0 through its epilogue when the UCL (4) or UEL (6) entry is missing, else lea/shl and resume at 0x1413605a2"},
  {va=0x14136059a, old="4b8d044048c1e004", new="e981e81c01909090", why="jmp from the unchecked index into the trampoline at 0x14252ee20"},
}
local counted = {
  {va=STUB_VA, old=string.rep("00", #STUB / 2), new=STUB, why="B470: count which entry was missing (UCL at 0x14252eef4, UEL at 0x14252eef8), then the epilogue"},
  {va=CNT_VA, old=string.rep("00", 8), new=string.rep("00", 8), why="B470: the two skip counters, zero"},
}

-- the page the counters are on, writable by the game's code; false without ffi or if it fails
local function page_rwx()
  if ffi == nil then return false end
  ffi.cdef([[ int fl26superguard_VirtualProtect(void*, size_t, uint32_t, uint32_t*) __asm__("VirtualProtect"); ]])
  local old = ffi.new("uint32_t[1]")
  return ffi.C.fl26superguard_VirtualProtect(ffi.cast("void*", CAVE_PAGE), 0x1000, 0x40, old) ~= 0
end

local seen = { 0, 0 }
local ticks = 0
local function poll()
  local s = memory.read(CNT_VA, 8)
  if s == nil or #s ~= 8 then return end
  local c = { memory.unpack("u32", s:sub(1, 4)), memory.unpack("u32", s:sub(5, 8)) }
  if c[1] ~= seen[1] or c[2] ~= seen[2] then
    local what = (c[1] ~= seen[1] and c[2] ~= seen[2]) and "both entries missing (the entry vector is empty)"
              or (c[1] ~= seen[1]) and "the Champions League entry (4) missing"
              or "the Europa League entry (6) missing"
    log(string.format("fl26superguard: Super Cup setup skipped -- %s (UCL missing %d, UEL missing %d time(s) in all)",
                      what, c[1], c[2]))
    seen[1], seen[2] = c[1], c[2]
  end
end
function m.make_key(ctx, filename)
  ticks = ticks + 1
  if ticks % 64 == 0 then poll() end
  return nil
end

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
  local count = page_rwx()
  if count then
    local ok = true
    for _, p in ipairs(counted) do
      if memory.read(p.va, #p.old / 2) ~= unhex(p.old) then
        ok = false
        log(string.format("fl26superguard: 0x%x is not free (%s) -- the skips are not counted", p.va, p.why))
      end
    end
    count = ok
  else
    log("fl26superguard: no ffi or the cave page stayed read-only -- the skips are not counted")
  end
  if count then
    patches[1].new = TRAMP_COUNT
    for _, p in ipairs(counted) do patches[#patches + 1] = p end
  end
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
    log(string.format("fl26superguard: applied all %d patches -- %s%s", written, "a missing Champions League or Europa League entry skips the Super Cup setup instead of crashing",
                      count and "; each skip is logged" or ""))
    if count then ctx.register("livecpk_make_key", m.make_key) end
  else
    log(string.format("fl26superguard: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
