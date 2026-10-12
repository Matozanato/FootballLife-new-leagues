--[[
fl26boardguard -- the board objective reads the club's league position as an index into a
table of 32 ints at 0x1428e52e0 with no bound:

    1413236e1  8b4577      mov  eax, [rbp+0x77]       ; position from the league table (+4)
    1413236e4  412b0c80    sub  ecx, [r8+rax*4]       ; r8 = 0x1428e52e0

A league that has no fixtures (a regulation id whose date case was never sent to the stub)
leaves the position at -1, and that read is the crash 0x1413236e4 on team confirm.  The cause
is fixed in the patch set; this makes any future case of it a wrong objective instead of a
crash: a position above 31 (unsigned, so -1 too) reads as 0.

    stub (page 0x163600000):  mov eax,[rbp+0x77] / cmp eax,0x1f / jbe +2 / xor eax,eax /
                              sub ecx,[r8+rax*4] / jmp 0x1413236e8
    site:                     jmp stub / nop / nop   (the next instruction is a cmp, so the
                              flags of the sub are not needed)

Limits branch, 2026-10-11, not released.  Touches no byte fl26caps touches.
Needs luajit.ext.enabled = 1 in sider.ini.
--]]

local m = {}

local patches = {
  {va=0x163600000, old="00000000000000000000000000000000000000", new="8b457783f81f760231c0412b0c80e9d536d2dd",
   why="stub: clamp the league position to 0..31"},
  {va=0x1413236e1, old="8b4577412b0c80", new="e91ac92d229090",
   why="mov eax,[rbp+0x77] / sub ecx,[r8+rax*4] -> stub 0x163600000"},
}

local PAGES = { 0x163600000 }

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

local function reserve(page)
  if ffi == nil then
    log("fl26boardguard: global ffi is nil -- set luajit.ext.enabled = 1 in sider.ini")
    return false
  end
  if not m.cdef then
    -- a name of our own: another module may already have declared VirtualAlloc, and
    -- declaring it twice is an error
    ffi.cdef([[ void* fl26board_VirtualAlloc(void*, size_t, uint32_t, uint32_t) asm("VirtualAlloc"); ]])
    m.cdef = true
  end
  local function try(kind)
    local p = ffi.C.fl26board_VirtualAlloc(ffi.cast("void*", page), 0x1000, kind, 0x40)
    return p ~= nil and tonumber(ffi.cast("uint64_t", p)) or 0
  end
  -- MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE; MEM_COMMIT alone if the page was
  -- already reserved (fl26cave.lua from an older install does that)
  local got = try(0x3000)
  if got ~= page then got = try(0x1000) end
  if got ~= page then
    log(string.format("fl26boardguard: could not get the page at 0x%x (got 0x%x)", page, got))
    return false
  end
  log(string.format("fl26boardguard: page 0x%x..0x%x ready", page, page + 0x1000))
  return true
end

function m.init(ctx)
  local n = #patches
  for _, page in ipairs(PAGES) do
    if not reserve(page) then
      log("fl26boardguard: ABORTED before verifying. Nothing was written; the game is unmodified.")
      return
    end
  end
  log(string.format("fl26boardguard: set '%s', %d patches, verifying", "boardguard", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26boardguard: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26boardguard: ABORTED, %d of %d sites did not match. "
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
      log(string.format("fl26boardguard: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26boardguard: WRITE FAILED at 0x%x (%s) -- read back %s",
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
    log(string.format("fl26boardguard: applied all %d patches -- %s", written, "board objective: league position outside 0..31 reads as 0"))
  else
    log(string.format("fl26boardguard: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
