--[[
fl26regs -- regulation records: the live count follows fl26caps' cap (300 -> 1200).

GENERATED FILE by mkregs.py.  Every 'old' below was read from the exe at that address.

Set:     regs1200
Summary: regulation records 1200: live recount stub, re-initialisers and the 0x140fbdc70 walk raised, 5 patches

fl26caps grows the regulation array to 1200 records, but the game recounts its records
after every mode-copy write-back, at mode-data creation and on load (0x1414bc0a0), and that
recount is unrolled six records a pass over 50 passes: it never looks past record 300.  The
array is sorted by key, so with more than 300 regulations the highest keys (late cup and
European ties) stop being found and are left out of the Master League save.  This module
makes the recount cover all 1200, and moves the three other bounds still at 300 (the two
in-place re-initialisers and one walk's back edge).

Needs fl26caps.lua with a regulation cap of exactly 1200, loaded BEFORE this module: it
checks the block constructor and destructor and writes nothing if they do not say 1200.
Touches no byte fl26caps, fl26slots, fl26hdr* or fl26regfast touch.  Its page is 0x163800000 (40 bytes of code), not fl26caps' or fl26slots'. Needs luajit.ext.enabled = 1.
A career saved with this module carries more than 300 regulations; load it with it.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26regs1200.lua
  2. sider.ini, after lua.module = "fl26caps.lua":   lua.module = "fl26regs1200.lua"
  3. start the game; sider.log says "fl26regs: applied all ..."
--]]

local m = {}

local requires = {
  {va=0x1414b87dd, want="41beb0040000", why="block constructor: __ehvec_ctor(regulations, 0x314, N) (fl26caps)"},
  {va=0x1414ba5e8, want="41b8b0040000", why="block destructor: __ehvec_dtor(regulations, 0x314, N) (fl26caps)"},
}

local patches = {
  {va=0x163800000, old="00000000000000000000000000000000000000000000000000000000000000000000000000000000", new="4981e81403000041b9b004000066418138ffff7402ffc14981c01403000041ffc975eae90dc2cbdd",
   why="recount stub: valid regulation records among the first 1200 (r8 = record 0 + 0x314 from the game's own relocated lea), then back to 0x1414bc235"},
  {va=0x1414bc1c3, old="448d4d3241baffff00000f1f00", new="e9383e34229090909090909090",
   why="recount 0x1414bc0a0: unrolled 50 x 6 = 300 regulation records -> jmp to the stub at 0x163800000"},
  {va=0x1414bba63, old="be2c010000", new="beb0040000",
   why="initialiser 0x1414bb970: regulation records re-constructed in place (mov esi; 0x1414c98f0 per record): 300 -> 1200"},
  {va=0x1414bbeec, old="be2c010000", new="beb0040000",
   why="reset 0x1414bbe60, run before a mode copy writes the block back: regulation records cleared in place: 300 -> 1200"},
  {va=0x140fbdfbf, old="3d2c010000", new="3db0040000",
   why="back edge of the regulation walk in 0x140fbdc70 (competitions a player's clubs are in; cmp eax / jae out / jmp home): 300 -> 1200"},
}

local PAGES = { 0x163800000 }

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
    log("fl26regs: global ffi is nil -- set luajit.ext.enabled = 1 in sider.ini")
    return false
  end
  if not m.cdef then
    -- a name of our own: another module may already have declared VirtualAlloc
    ffi.cdef([[ void* fl26regs_VirtualAlloc(void*, size_t, uint32_t, uint32_t) asm("VirtualAlloc"); ]])
    m.cdef = true
  end
  local function try(kind)
    local p = ffi.C.fl26regs_VirtualAlloc(ffi.cast("void*", page), 0x1000, kind, 0x40)
    return p ~= nil and tonumber(ffi.cast("uint64_t", p)) or 0
  end
  -- MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE; MEM_COMMIT alone if already reserved
  local got = try(0x3000)
  if got ~= page then got = try(0x1000) end
  if got ~= page then
    log(string.format("fl26regs: could not get the page at 0x%x (got 0x%x)", page, got))
    return false
  end
  log(string.format("fl26regs: page 0x%x..0x%x ready", page, page + 0x1000))
  return true
end

function m.init(ctx)
  local n = #patches

  -- pass 0: fl26caps must already have grown the array to the same cap. Read only.
  for _, r in ipairs(requires) do
    local want = unhex(r.want)
    local cur = memory.read(r.va, #want)
    if cur ~= want then
      log(string.format("fl26regs: ABORTED, 0x%x is %s, expected %s [%s]. Is fl26caps.lua "
                        .. "loaded before this module, with a regulation cap of 1200? "
                        .. "Nothing was written; the game is unmodified.",
                        r.va, tohex(cur), r.want, r.why))
      return
    end
  end

  for _, page in ipairs(PAGES) do
    if not reserve(page) then
      log("fl26regs: ABORTED before verifying. Nothing was written; the game is unmodified.")
      return
    end
  end
  log(string.format("fl26regs: set '%s', %d patches, verifying", "regs1200", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26regs: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26regs: ABORTED, %d of %d sites did not match. "
                      .. "Nothing was written; the game is unmodified. "
                      .. "A different exe build, or a fl26caps that already carries these "
                      .. "sites (then use the --recount-only build).", bad, n))
    return
  end

  -- pass 2: write, then read back. Page contents first, the jump into them last.
  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    local back = memory.read(p.va, #new)
    if back == new then
      written = written + 1
      log(string.format("fl26regs: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26regs: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  if failed == 0 then
    log(string.format("fl26regs: applied all %d patches -- %s", written, "regulation records 1200: live recount stub, re-initialisers and the 0x140fbdc70 walk raised, 5 patches"))
  else
    log(string.format("fl26regs: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
