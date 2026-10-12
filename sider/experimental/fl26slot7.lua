--[[
fl26slot7 -- a club's Master League league slot may be 0..249 (needs fl26slots250).

GENERATED FILE by mkslot7.py.  Every byte below was read from the exe at that address.

Summary: team league slot 7 -> 8 bits (+0x41c byte, flag moved to +0x41a), 59 patches

A team record keeps its league slot in bits 0-6 of +0x41c; bit 7 is a flag of the game's own
and bits 8-31 are other fields.  With fl26slots250 a league can sit on slots 124..249, but a
club of a league on 130 got slot 130 & 0x7f = 2 when a Master League was created (the slot of
another competition), and every Master League lookup by club slot then went wrong.

This module moves the flag to +0x41a (padding next to the country word +0x418) and makes the
slot the whole byte +0x41c:
  * every reader masks with 0xff instead of 0x7f, every writer stores the byte,
  * the flag is set, read, edited and copied at +0x41a,
  * the six callers of 0x141509c00 get the real slot up to 249 (not 7 above 127),
  * the Master League slot choice (0x141263b40) is the game's own: the first slot holding a
    league-format competition wins, so a league on 130 gets 130 when fl26comptab gives its
    row slot 130.

Careers: a Master League created without this module stores the flag in bit 7; loading it
with this module reads every flagged club's slot as slot+128.  Start a NEW career after
installing (fl26slots250 already asks for that), and keep the module for that career.

Load order: after fl26caps and fl26slots250 is fine; no byte overlaps any shipped module.
Page 0x163c00000 is its own.  Needs luajit.ext.enabled = 1 in sider.ini.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26slot7.lua
  2. add to sider.ini:   lua.module = "fl26slot7.lua"   (after fl26slots250.lua)
  3. start the game and read sider.log ("fl26slot7: applied all ...")
--]]

local m = {}

local patches = {
  {va=0x163c00000, old="000000000000000000000000000000000000000000000000000000000000000000000000000000", new="4883ec280fb709e8d4b28cdd83f87b740c3dfa00000073054883c428c3b8070000004883c428c3",
   why="league slot of a competition id: id2slot, 7 only for 123 or >= 250 (0x141509c00 caps at 128)"},
  {va=0x140b08f74, old="7f", new="ff",
   why="slot reader 0x140b08f6b: and cl, 0x7f -> 0xff"},
  {va=0x140c6c0c0, old="7f", new="ff",
   why="slot reader 0x140c6c0b7: and cl, 0x7f -> 0xff"},
  {va=0x140fa3077, old="7f", new="ff",
   why="slot reader 0x140fa306f: and al, 0x7f -> 0xff"},
  {va=0x140fd2a7f, old="7f", new="ff",
   why="slot reader 0x140fd2a77: and al, 0x7f -> 0xff"},
  {va=0x140fd8eae, old="7f", new="ff",
   why="slot reader 0x140fd8ea6: and al, 0x7f -> 0xff"},
  {va=0x141262384, old="7f", new="ff",
   why="slot reader 0x141262379: and r15d, 0x7f -> 0xff"},
  {va=0x1412628f4, old="7f", new="ff",
   why="slot reader 0x1412628ec: and al, 0x7f -> 0xff"},
  {va=0x141262b84, old="7f", new="ff",
   why="slot reader 0x141262b7c: and al, 0x7f -> 0xff"},
  {va=0x141324df5, old="7f", new="ff",
   why="slot reader 0x141324ded: and al, 0x7f -> 0xff"},
  {va=0x14132a045, old="7f", new="ff",
   why="slot reader 0x14132a03d: and al, 0x7f -> 0xff"},
  {va=0x14133396d, old="7f", new="ff",
   why="slot reader 0x141333964: and eax, 0x7f -> 0xff"},
  {va=0x141354dd1, old="7f", new="ff",
   why="slot reader 0x141354dc9: and al, 0x7f -> 0xff"},
  {va=0x1413558d6, old="7f", new="ff",
   why="slot reader 0x1413558cd: and eax, 0x7f -> 0xff"},
  {va=0x141358f7d, old="7f", new="ff",
   why="slot reader 0x141358f74: and cl, 0x7f -> 0xff"},
  {va=0x14135a8cd, old="7f", new="ff",
   why="slot reader 0x14135a8c5: and al, 0x7f -> 0xff"},
  {va=0x14135ae11, old="7f", new="ff",
   why="slot reader 0x14135ae09: and al, 0x7f -> 0xff"},
  {va=0x14135b17d, old="7f", new="ff",
   why="slot reader 0x14135b175: and al, 0x7f -> 0xff"},
  {va=0x14135d790, old="7f", new="ff",
   why="slot reader 0x14135d787: and ecx, 0x7f -> 0xff"},
  {va=0x14136037d, old="7f", new="ff",
   why="slot reader 0x141360372: and r15b, 0x7f -> 0xff"},
  {va=0x1413603f4, old="7f", new="ff",
   why="slot reader 0x1413603eb: and cl, 0x7f -> 0xff"},
  {va=0x141361121, old="7f", new="ff",
   why="slot reader 0x141361119: and al, 0x7f -> 0xff"},
  {va=0x141365911, old="7f", new="ff",
   why="slot reader 0x141365906: and r15b, 0x7f -> 0xff"},
  {va=0x14136593a, old="7f", new="ff",
   why="slot reader 0x141365930: and dil, 0x7f -> 0xff"},
  {va=0x141509575, old="7f", new="ff",
   why="slot reader 0x14150956c: and ebp, 0x7f -> 0xff"},
  {va=0x14150d4ee, old="7f", new="ff",
   why="slot reader 0x14150d4e5: and edx, 0x7f -> 0xff"},
  {va=0x14150d528, old="7f", new="ff",
   why="slot reader 0x14150d51f: and edx, 0x7f -> 0xff"},
  {va=0x141511253, old="7f", new="ff",
   why="slot reader 0x141511243: and ecx, 0x7f -> 0xff"},
  {va=0x1415191dc, old="7f", new="ff",
   why="slot reader 0x1415191d3: and eax, 0x7f -> 0xff"},
  {va=0x141527ebf, old="7f", new="ff",
   why="slot reader 0x141527eb7: and al, 0x7f -> 0xff"},
  {va=0x141541f6b, old="7f", new="ff",
   why="slot reader 0x141541f62: and ecx, 0x7f -> 0xff"},
  {va=0x141546a12, old="7f", new="ff",
   why="slot reader 0x141546a09: and ecx, 0x7f -> 0xff"},
  {va=0x141547ff2, old="7f", new="ff",
   why="slot reader 0x141547fe9: and ecx, 0x7f -> 0xff"},
  {va=0x141262760, old="4183a51c040000800fb6c083e07f4109851c040000", new="4188851c0400009090909090909090909090909090",
   why="user's club: slot from 0x141509c00 -> byte +0x41c (flag in +0x41a untouched, as and 0xffffff80 kept bit 7)"},
  {va=0x1412627df, old="4183a4241c040000800fb645ef83e07f410984241c040000", new="0fb645ef418884241c040000909090909090909090909090",
   why="user's club path: other club gets the saved slot [rbp-0x11] -> byte +0x41c"},
  {va=0x1412628f5, old="4183a51c040000800fb6c04109851c040000", new="4188851c0400009090909090909090909090",
   why="user's club takes another club's slot (al) -> byte +0x41c"},
  {va=0x141262930, old="418b8704030000c1e807a80175060fbaf207eb040fbaea074189951c040000", new="418b8704030000c1e80724014188851a040000909090909090909090909090",
   why="flag of the regulation (+0x304 bit 7) -> +0x41a instead of bit 7 of +0x41c"},
  {va=0x14126294f, old="83a11c040000800fb645ef83e07f09811c040000", new="0fb645ef88811c04000090909090909090909090",
   why="other club gets the saved slot [rbp-0x11] -> byte +0x41c"},
  {va=0x141262b85, old="4183a51c040000800fb6c04109851c040000", new="4188851c0400009090909090909090909090",
   why="user's club takes another club's slot (al) -> byte +0x41c"},
  {va=0x141262bc0, old="8b8604030000c1e807a80175060fbaf207eb040fbaea074189951c040000", new="8b8604030000c1e80724014188851a040000909090909090909090909090",
   why="flag of the regulation (+0x304 bit 7) -> +0x41a instead of bit 7 of +0x41c"},
  {va=0x141262bde, old="83a11c04000080410fb6c783e07f09811c040000", new="410fb6c788811c04000090909090909090909090",
   why="other club gets slot r15b -> byte +0x41c"},
  {va=0x141262e90, old="0fb6c841338d1c04000083e17f41338d1c04000041898d1c040000418b8704030000c1e807a80175060fbaf107eb040fbae90741898d1c040000", new="4188851c040000418b8704030000c1e80724014188851a0400009090909090909090909090909090909090909090909090909090909090909090",
   why="user's club: slot (al) -> byte +0x41c, regulation flag -> +0x41a"},
  {va=0x141262f77, old="83a01c040000800fb645ef83e07f09811c040000", new="0fb645ef88811c04000090909090909090909090",
   why="other club (rax == rcx) gets the saved slot [rbp-0x11] -> byte +0x41c"},
  {va=0x14136595f, old="83a01c04000080400fb6cf09881c040000", new="4088b81c04000090909090909090909090",
   why="season mover: club takes slot dil -> byte +0x41c"},
  {va=0x14136599f, old="83a01c04000080410fb6cf09881c040000", new="4488b81c04000090909090909090909090",
   why="season mover: club takes slot r15b -> byte +0x41c"},
  {va=0x14126655e, old="8b856c03000083e0fb83c87b", new="8b856c030000b07b90909090",
   why="staged world: no slot -> byte = 123 (was low 7 bits = 123, bit 7 kept)"},
  {va=0x1412665cb, old="0fb6c88b856c03000033c883e17f33c1", new="8b8d6c03000088c189c8909090909090",
   why="staged world: slot from 0x141263b40 -> whole byte +0x41c of the staged copy"},
  {va=0x1414c5b41, old="818b1c04000080000000", new="c6831a04000001909090",
   why="team init: flag = 1 now in +0x41a (was or [+0x41c],0x80)"},
  {va=0x141f12004, old="81a61c0400007fffffff098e1c040000", new="c1e907888e1a04000090909090909090",
   why="edit field setter: flag (ecx = 0x80 or 0) -> +0x41a bit 0"},
  {va=0x141eddb4f, old="8b801c040000c1e8072401", new="0fb6801a04000024019090",
   why="flag reader: +0x41a bit 0"},
  {va=0x141f116af, old="8b851c040000458bc6c1e8072401", new="0fb6851a040000458bc624019090",
   why="edit field getter: flag from +0x41a bit 0"},
  {va=0x140b15aa9, old="0fb78718040000", new="8b871804000090",
   why="team copy: country word +0x418 copied as a dword, so +0x41a (flag) travels with it"},
  {va=0x140b15ab0, old="66898318040000", new="89831804000090",
   why="team copy: store the dword +0x418..+0x41b"},
  {va=0x140ae3de8, old="e8135ea200", new="e813c21123",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x140ae44d3, old="e82857a200", new="e828bb1123",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x14126275b, old="e8a0742a00", new="e8a0d89922",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x141262e8b, old="e8706d2a00", new="e870d19922",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x14135964b, old="e8b0051b00", new="e8b0698a22",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x14135a50b, old="e8f0f61a00", new="e8f05a8a22",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
}

local PAGES = { 0x163c00000 }

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
    log("fl26slot7: global ffi is nil -- set luajit.ext.enabled = 1 in sider.ini")
    return false
  end
  if not m.cdef then
    -- a name of our own: another module may already have declared VirtualAlloc, and
    -- declaring it twice is an error
    ffi.cdef([[ void* fl26slot7_VirtualAlloc(void*, size_t, uint32_t, uint32_t) asm("VirtualAlloc"); ]])
    m.cdef = true
  end
  local function try(kind)
    local p = ffi.C.fl26slot7_VirtualAlloc(ffi.cast("void*", page), 0x1000, kind, 0x40)
    return p ~= nil and tonumber(ffi.cast("uint64_t", p)) or 0
  end
  -- MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE; MEM_COMMIT alone if the page was
  -- already reserved (fl26cave.lua from an older install does that)
  local got = try(0x3000)
  if got ~= page then got = try(0x1000) end
  if got ~= page then
    log(string.format("fl26slot7: could not get the page at 0x%x (got 0x%x)", page, got))
    return false
  end
  log(string.format("fl26slot7: page 0x%x..0x%x ready", page, page + 0x1000))
  return true
end

function m.init(ctx)
  local n = #patches
  for _, page in ipairs(PAGES) do
    if not reserve(page) then
      log("fl26slot7: ABORTED before verifying. Nothing was written; the game is unmodified.")
      return
    end
  end
  log(string.format("fl26slot7: set '%s', %d patches, verifying", "slot7", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26slot7: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26slot7: ABORTED, %d of %d sites did not match. "
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
      log(string.format("fl26slot7: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26slot7: WRITE FAILED at 0x%x (%s) -- read back %s",
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
    log(string.format("fl26slot7: applied all %d patches -- %s", written, "team league slot 7 -> 8 bits (+0x41c byte, flag moved to +0x41a), 59 patches"))
  else
    log(string.format("fl26slot7: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
