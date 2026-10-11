--[[
fl26slots -- competition slots 123 -> 128.

GENERATED FILE by mkslots.py.  Every byte below was read from the exe at that address.

Set:     slots128
Summary: competition slots 123 -> 128 (slot 123 kept as sentinel), per-slot capacity 706, slots 79/80 1600, 35 patches

The edit block keeps one club list per competition slot.  The game ships 123 slots of 750
entries.  The region they live in cannot grow, so this module gives every slot a capacity
of its own, kept in a table on a page this module allocates at 0x163400000:

    slot 79 and 80 (aggregates the game merges from almost every club)   1600 entries
    slots 0..5 and 69..78 (region-code and merged lists)                750 entries (as before)
    slot 123 (the engine's "no slot" sentinel, kept as it is)            0
    every other slot                                                     706 entries

and rewrites the five accessors (0x1414d6290..0x1414d637f, same entry addresses) to use it.
The bounds that used to say 123 now say 128, and still refuse 123 itself.

Limits that stay (read report.md):
  * a team record stores its league slot in 7 bits (+0x41c & 0x7f), so a club whose
    LEAGUE is on a slot >= 128 gets team.slot = 7, exactly what the game already does for
    a league with no row.  Put leagues on 0..122 / 124..127; slots 128..127 are fine for
    cups and other competitions.
  * slot 123 stays unusable.
  * a Master League career keeps its own copy of the region: start a NEW career after
    installing, and do not load a career made with this module without it.

Load order: this module touches no byte fl26caps touches, and its page is not fl26caps'
page, so the order does not matter.  Needs luajit.ext.enabled = 1 in sider.ini.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26slots128.lua
  2. add to sider.ini:   lua.module = "fl26slots128.lua"
  3. start the game and read sider.log
--]]

local m = {}

local patches = {
  {va=0x163400800, old="0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", new="00000000ee020000dc050000ca080000b80b0000a60e0000941100005614000018170000da1900009c1c00005e1f000020220000e2240000a4270000662a0000282d0000ea2f0000ac3200006e35000030380000f23a0000b43d00007640000038430000fa450000bc4800007e4b0000404e000002510000c453000086560000485900000a5c0000cc5e00008e6100005064000012670000d4690000966c0000586f00001a720000dc7400009e770000607a0000227d0000e47f0000a6820000688500002a880000ec8a0000ae8d00007090000032930000f4950000b6980000789b00003a9e0000fca00000bea3000080a6000042a9000004ac0000c6ae000088b100004ab400000cb70000ceb9000090bc000052bf000040c200002ec500001cc800000acb0000f8cd0000e6d00000d4d30000c2d60000b0d900009edc0000dee200001ee90000e0eb0000a2ee000064f1000026f40000e8f60000aaf900006cfc00002eff0000f0010100b204010074070100360a0100f80c0100ba0f01007c1201003e15010000180100c21a0100841d01004620010008230100ca2501008c2801004e2b0100102e0100d2300100943301005636010018390100da3b01009c3e01005e41010020440100e2460100a4490100664c0100284f0100ea510100ac5401006e570100305a0100f25c0100f25c0100b45f01007662010038650100",
   why="first entry of each slot's list (dword index into the region)"},
  {va=0x163400c00, old="0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", new="ee020000ee020000ee020000ee020000ee020000ee020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000ee020000ee020000ee020000ee020000ee020000ee020000ee020000ee020000ee020000ee0200004006000040060000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c2020000c202000000000000c2020000c2020000c2020000c2020000",
   why="capacity of each slot (slot 123 = 0)"},
  {va=0x163400000, old="000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", new="89d03d80000000732f3c7b742b0fb7944168a00500443bc2731e488d15df0b0000443b04827311488d15d20700008b14824401c28b0491c383c8ffc3",
   why="get accessor body, table driven"},
  {va=0x163400040, old="00000000000000000000000000000000000000000000000000000000000000000000000000000000000000", new="31c081fa80000000732083fa7b741b5289d0488d15a70b00008b14820fb7844168a0050039d00f47c25ac3",
   why="count accessor body, table driven"},
  {va=0x163400070, old="0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", new="89d03d8000000073223c7b741e488d157c0b0000443b04827311488d156f0700008b14824401c244890c91c3",
   why="set accessor body, table driven"},
  {va=0x1634000a0, old="00000000000000000000000000000000000000000000000000000000000000000000000000000000000000", new="81fa80000000732283fa7b741d5289d0488d15490b00008b1482664139d07709664489844168a005005ac3",
   why="setcount accessor body, table driven"},
  {va=0x1634000d0, old="00000000000000000000000000000000000000000000000000000000", new="4183f87b0f845eb10cde4181f8800000000f8d51b10cdee90eb00cde",
   why="stub for 0x1414cb0f0 -- guard: cmp r8d,123 -> rejected; cmp r8d,128; jge 0x1414cb238; jmp 0x1414cb0fa  [cid2slot: only real slots of the rows a competition id has]"},
  {va=0x1634000f0, old="0000000000000000000000000000000000000000000000000000", new="83fe7b0f8408750fde81fe800000000f8dfc740fdee94d740fde",
   why="stub for 0x1414f754e -- guard: cmp esi,123 -> rejected; cmp esi,128; jge 0x1414f7601; jmp 0x1414f7557  [slot-list builder: slot of a competition entry (first test)]"},
  {va=0x163400110, old="0000000000000000000000000000000000000000000000000000", new="83fe7b0f84eb740fde81fe800000000f8ddf740fdee94d740fde",
   why="stub for 0x1414f756e -- guard: cmp esi,123 -> rejected; cmp esi,128; jge 0x1414f7604; jmp 0x1414f7577  [slot-list builder: slot of a competition entry (second test)]"},
  {va=0x163400130, old="000000000000000000000000000000000000", new="4181fe800000000f83b3760fdee99e760fde",
   why="stub for 0x1414f77da -- loop: cmp r14d,128; jae 0x1414f77f0; jmp 0x1414f77e0  [slot-list builder: write every slot vector into the region]"},
  {va=0x163400150, old="0000000000000000000000000000000000000000000000000000", new="83f87b0f846488e6dd81f8800000000f8d5888e6dde97f87e6dd",
   why="stub for 0x1412688e0 -- guard: cmp eax,123 -> rejected; cmp eax,128; jge 0x1412689bd; jmp 0x1412688e9  [regulation fill: slot of the competition]"},
  {va=0x163400170, old="0000000000000000000000000000000000000000000000000000", new="83fd7b0f8415abefdd81fd800000000f824cabefdde904abefdd",
   why="stub for 0x1412fac89 -- guard: cmp ebp,123 -> rejected; cmp ebp,128; jb 0x1412facd1; jmp 0x1412fac8e  [Select Team list: a real slot, else the special list at +0xf0]"},
  {va=0x163400190, old="00000000000000000000000000000000000000000000000000000000", new="4183fc7b0f84bab0efdd4181fc800000000f82c1b0efdde9a8b0efdd",
   why="stub for 0x1412fb24e -- guard: cmp r12d,123 -> rejected; cmp r12d,128; jb 0x1412fb268; jmp 0x1412fb254  [Select Team list: a real slot, else the special list]"},
  {va=0x1634001b0, old="0000000000000000000000000000000000", new="81fe800000000f8295b3efdde9edb4efdd",
   why="stub for 0x1412fb6a5 -- loop: cmp esi,128; jb 0x1412fb551; jmp 0x1412fb6ae  [Select Team list: walk every slot]"},
  {va=0x1634001d0, old="000000000000000000000000000000000000", new="4181ff800000000f83813fe6dde9203fe6dd",
   why="stub for 0x1412640fc -- loop: cmp r15d,128; jae 0x14126415e; jmp 0x141264102  [user club categories: walk every slot looking for the club]"},
  {va=0x1634001f0, old="0000000000000000000000000000000000000000000000000000", new="b90700000083f87b74093d800000007d0289c189c8e9efaa6ce1",
   why="team slot: slot < 128 and != 123 kept, otherwise 7 (7-bit field +0x41c)"},
  {va=0x1414d6290, old="83fa7b7320", new="e96b9df221",
   why="get accessor 0x1414d6290 -> its new body at 0x163400000 (entry address kept)"},
  {va=0x1414d62c0, old="33c083fa7b", new="e97b9df221",
   why="count accessor 0x1414d62c0 -> its new body at 0x163400040 (entry address kept)"},
  {va=0x1414d6330, old="83fa7b731c", new="e93b9df221",
   why="set accessor 0x1414d6330 -> its new body at 0x163400070 (entry address kept)"},
  {va=0x1414d6360, old="83fa7b7316", new="e93b9df221",
   why="setcount accessor 0x1414d6360 -> its new body at 0x1634000a0 (entry address kept)"},
  {va=0x1414cb0f0, old="4183f87b0f8d3e010000", new="e9db4ff3219090909090",
   why="cmp r8d, 0x7b / jge 0x1414cb238 -> stub 0x1634000d0  [cid2slot: only real slots of the rows a competition id has]"},
  {va=0x1414f754e, old="83fe7b0f8daa000000", new="e99d8bf02190909090",
   why="cmp esi, 0x7b / jge 0x1414f7601 -> stub 0x1634000f0  [slot-list builder: slot of a competition entry (first test)]"},
  {va=0x1414f756e, old="83fe7b0f8d8d000000", new="e99d8bf02190909090",
   why="cmp esi, 0x7b / jge 0x1414f7604 -> stub 0x163400110  [slot-list builder: slot of a competition entry (second test)]"},
  {va=0x1414f77da, old="4183fe7b7310", new="e95189f02190",
   why="cmp r14d, 0x7b / jae 0x1414f77f0 -> stub 0x163400130  [slot-list builder: write every slot vector into the region]"},
  {va=0x1412688e0, old="83f87b0f8dd4000000", new="e96b78192290909090",
   why="cmp eax, 0x7b / jge 0x1412689bd -> stub 0x163400150  [regulation fill: slot of the competition]"},
  {va=0x1412fac89, old="83fd7b7243", new="e9e2541022",
   why="cmp ebp, 0x7b / jb 0x1412facd1 -> stub 0x163400170  [Select Team list: a real slot, else the special list at +0xf0]"},
  {va=0x1412fb24e, old="4183fc7b7214", new="e93d4f102290",
   why="cmp r12d, 0x7b / jb 0x1412fb268 -> stub 0x163400190  [Select Team list: a real slot, else the special list]"},
  {va=0x1412fb6a5, old="83fe7b0f82a3feffff", new="e9064b102290909090",
   why="cmp esi, 0x7b / jb 0x1412fb551 -> stub 0x1634001b0  [Select Team list: walk every slot]"},
  {va=0x1412640fc, old="4183ff7b735c", new="e9cfc0192290",
   why="cmp r15d, 0x7b / jae 0x14126415e -> stub 0x1634001d0  [user club categories: walk every slot looking for the club]"},
  {va=0x144acacec, old="83f87bb9070000000f4cc889c8", new="e9ff54931e9090909090909090",
   why=".impdata 0x144acace0: cmp eax,0x7b / mov ecx,7 / cmovl / mov eax,ecx -> stub 0x1634001f0"},
  {va=0x1414d62e5, old="7b000000", new="01000000",
   why="clear: one pass over all lists instead of 123 x 750"},
  {va=0x1414d62f2, old="ee020000", new="1a680100",
   why="clear: 92186 list dwords"},
  {va=0x1414d631e, old="68a10500", new="68a00500",
   why="clear: counts at +0x5a068"},
  {va=0x1414d6326, old="f6000000", new="00010000",
   why="clear: 128 counts"},
  {va=0x1414f6e49, old="7b000000", new="80000000",
   why="slot-list builder 0x1414f6e20: 128 slot vectors (mov edx,0x7b)"},
}

local PAGES = { 0x163400000 }

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
    log("fl26slots: global ffi is nil -- set luajit.ext.enabled = 1 in sider.ini")
    return false
  end
  if not m.cdef then
    -- a name of our own: another module may already have declared VirtualAlloc, and
    -- declaring it twice is an error
    ffi.cdef([[ void* fl26slots_VirtualAlloc(void*, size_t, uint32_t, uint32_t) asm("VirtualAlloc"); ]])
    m.cdef = true
  end
  local function try(kind)
    local p = ffi.C.fl26slots_VirtualAlloc(ffi.cast("void*", page), 0x1000, kind, 0x40)
    return p ~= nil and tonumber(ffi.cast("uint64_t", p)) or 0
  end
  -- MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE; MEM_COMMIT alone if the page was
  -- already reserved (fl26cave.lua from an older install does that)
  local got = try(0x3000)
  if got ~= page then got = try(0x1000) end
  if got ~= page then
    log(string.format("fl26slots: could not get the page at 0x%x (got 0x%x)", page, got))
    return false
  end
  log(string.format("fl26slots: page 0x%x..0x%x ready", page, page + 0x1000))
  return true
end

function m.init(ctx)
  local n = #patches
  for _, page in ipairs(PAGES) do
    if not reserve(page) then
      log("fl26slots: ABORTED before verifying. Nothing was written; the game is unmodified.")
      return
    end
  end
  log(string.format("fl26slots: set '%s', %d patches, verifying", "slots128", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26slots: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26slots: ABORTED, %d of %d sites did not match. "
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
      log(string.format("fl26slots: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26slots: WRITE FAILED at 0x%x (%s) -- read back %s",
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
    log(string.format("fl26slots: applied all %d patches -- %s", written, "competition slots 123 -> 128 (slot 123 kept as sentinel), per-slot capacity 706, slots 79/80 1600, 35 patches"))
  else
    log(string.format("fl26slots: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
