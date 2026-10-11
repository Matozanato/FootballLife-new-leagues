--[[
fl26reg128 -- raise the number of regions (countries) from 64 to 128.

This replaces fl26reg64. Load one or the other, not both. If both are listed, either order
works: this module accepts fl26reg64's bytes at the three sites they share, and fl26reg64
leaves alone any site it does not recognise.

Why 64 was the ceiling. fl26reg64 widened the parser to six bits. The runtime record (stride
0x314) keeps the region in a 6-bit field, +0x30c bits 7..12. One setter writes that field
(0x1414c9c10, called once, from the parser), and 31 inline sites plus one getter
(0x1415415f0) read it back with `mov r,[b+0x30c] ; shr r,7 ; and r,0x3f`.

Where the seventh bit goes. Each record has a u16 at +0x2fe that the game writes and never
reads. Writers were the parser (Competition.bin d0 bits 18..26 through setter 0x1414c9f30),
two resets (0xffff) and two word copiers. A scan of the whole exe found no reader. So:

  * the region setter is rewritten in its own 32 bytes (body plus int3 padding). It stores the
    full region as the word at +0x2fe (byte +0x2fe = region, byte +0x2ff = 0) and
    min(region,63) in the 6-bit field. 63 in the 6-bit field now means "63 or higher";
  * the parser's call that copied d0 bits 18..26 into +0x2fe (13 bytes at 0x1414f83d1)
    becomes `mov byte [rdi+0x2ff], 0x5a`: a mark that says byte +0x2fe holds a region.
    Bits 24/25 of that dword are region bits now, and a record saved before this module
    never carries the mark (it held 0xffff, or 0x00../0x01.. from those nine bits);
  * the two resets leave +0x2fe/+0x2ff at 0 instead of 0xffff;
  * all 32 readers become `movzx r32, byte [b+0x2fe]` of the same length, padded with NOPs;
  * the three `and 0x1f80` region tests (region 0 at 0x14126464c, region == 1 at 0x14150c9d2
    and 0x14151c95e) read the full region too. The two copiers that merge 0x1f80 bits
    (0x14126206d, 0x1414ef38e) copy +0x2fe with their own word copies (0x141261df9/e01,
    0x1414ef119/121), mark included, so they need nothing.

File encoding. The region is the Competition.bin +3 byte: bits 3..7 = region bits 0..4,
bit 0 = region bit 5 (fl26reg64), bit 1 = region bit 6 (new). Bit 1 was zero in every row
ever written, so a world that never uses a region >= 64 decodes exactly as it did before.
tools/mkleague.py enc_region/dec_region hold the rule.

Region 29. The stock game had a few `cmp eax,0x1d` tests that could not fire while the parser
stopped at 28. Three of them (0x141575f1d, 0x1415773af, 0x141577414) now compare with 0, so
29 is an ordinary region. The career-list skips at 0x141264659 / 0x141264b51 (fl26reg64's
patches) are kept, and the compare is now `cmp eax,-1` because eax holds the full region
there. 0x1414cf160 ("does this region have a UI heading group", 3 UI callers) is left alone:
it answers false for 29..63 already, and fl26swiss relies on that. 64..127 behave like 29..63.

Checked before writing, statically:
  * every old= below matches the on-disk FL_2026.exe;
  * a linear decode of the code section (10.5M instructions, plus 22k resynced at 11k
    misaligned branch targets) finds no direct branch into any replaced range, and no
    RVA/VA in .rdata/.data/.pdata points inside one;
  * no patch overlaps fl26caps or fl26catlist, and none overlaps another patch here.

Old careers. A save made before this module has no mark at +0x2ff, so byte +0x2fe is junk
there. fl26join.dll (fl26_join_regions, called by fl26joindll) repairs those records whenever
the game recounts a career: region = the 6-bit field, which is the whole region in a career
saved under fl26reg64 or before, and the mark is set. Without the DLL, an old career shows
wrong regions in its menus. New careers are fine either way.

All or nothing. Every site is checked first. If any site holds bytes that are neither old=,
new= nor alt=, nothing is written: half of this patch set would read +0x2fe while the
other half still wrote only the 6-bit field.

Install:
  1. copy to <game>\SiderAddons\modules\fl26reg128.lua
  2. sider.ini, in the [modules] list, in place of fl26reg64:
       lua.module = "fl26reg128.lua"
--]]

local m = {}

local PATCHES = {
  {va=0x140acce1f, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): LeagueSelectCategory list (0x140accce0) -> 0x1414cf160"},
  {va=0x140acd68f, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): personalDataSelect (0x140acd560) -> 0x1414cf160"},
  {va=0x140b6a856, old="8b830c030000c1e80783e03f", new="0fb683fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): menu: region == r12d"},
  {va=0x140b81ba3, old="8b800c030000c1e80783e03f", new="0fb680fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): menu object +0x64c (later 0x140ead9c0 lookup / == +0x5ac)"},
  {va=0x140b82750, old="8b800c030000c1e80783e03f", new="0fb680fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): menu object +0x5ac (0x140ead9c0 lookup / == +0x64c)"},
  {va=0x140c6bdac, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): Select Team headings (0x140c6bd60) -> 0x1414cf160"},
  {va=0x140c6cd88, old="8b900c030000c1ea0783e23f", new="0fb690fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): League Info icons 0x140c6ccb0: the league's own region (edx, read by fl26catlist's stub)"},
  {va=0x140c6ce00, old="8b830c030000c1e80783e03f", new="0fb683fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): League Info icons 0x140c6ccb0: a regulation's region == the league's"},
  {va=0x140eada89, old="8b890c030000c1e90783e13f", new="0fb689fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): Competition Info list 0x140ead9f0: region == the list entry"},
  {va=0x140eadb73, old="448b8e0c03000033d2448b970c03000041c1e90741c1ea074183e13f4183e23f", new="440fb68efe02000033d2440fb697fe0200000f1f840000000000660f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): Competition Info sort helper 0x140eadae0: both regions, the xor edx,edx between them kept"},
  {va=0x140f1f641, old="8b800c030000c1e80783e03f", new="0fb680fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): menu: region == r15d"},
  {va=0x140fa1bb1, old="8b8b0c030000c1e90783e13f", new="0fb68bfe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): menu: region looked up in a list"},
  {va=0x14126464c, old="8b870c03000025801f0000", new="0fb687fe02000085c06690",
   why="career list 0x1412645b0: region 0 test reads the full region (movzx + test eax,eax, je skip unchanged)"},
  {va=0x141264659, old="3d800e0000", new="3dffffffff", alt="3d01000000",
   why="career list 0x1412645b0: the region-29 skip never fires (a byte never equals -1); fl26reg64 had cmp eax,1, which with the full region would now skip region 1"},
  {va=0x141264a5f, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): career list 0x141264880 -> 0x1414ce270"},
  {va=0x141264b51, old="41bc01000026", new="41bc01000006", alt="41bc01000006",
   why="career list 0x141264880, other branch: the skip mask loses bit 29 (regions 0, 25, 26 stay; as fl26reg64)"},
  {va=0x141264b7d, old="8b860c030000c1e80783e03f", new="0fb686fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): career list 0x141264880, other branch (cmp 0x1d / bt mask after it)"},
  {va=0x1414c94af, old="c683fe020000ff66898bff020000", new="c783fd020000ff0000ff0f1f4000",
   why="record constructor 0x1414c93b0: +0x2fe and +0x2ff = 0 instead of 0xffff (one dword store to +0x2fd..+0x300 = ff 00 00 ff keeps +0x2fd and +0x300 at 0xff as before)"},
  {va=0x1414c99c8, old="c783fc020000ffffffff", new="c783fc020000ffff0000",
   why="record re-init 0x1414c98f0: +0x2fc = 0xffff, +0x2fe = 0 (region 0, as the memset left +0x30c)"},
  {va=0x1414c9c10, old="81a10c0300007fe0ffff83e23fc1e20709910c030000c3cccccccccccccccccc", new="488d8100030000668950fe80fa3f7602b23fc1e2076681600c7fe06609500cc3",
   why="region setter (one caller, the parser): full region -> byte +0x2fe (word store, +0x2ff = 0 until the parser marks it), min(region,63) -> +0x30c bits 7..12 (63 = 'not a 6-bit region'); rewritten in its own 32 bytes (body + int3 padding), no cave"},
  {va=0x1414cce96, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' -> 0x1414ce270"},
  {va=0x1414cdb5d, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' -> 0x1414ce270"},
  {va=0x1414ce2d4, old="8b810c030000c1e80783e03f", new="0fb681fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): 0x1414ce270 (region -> the competitions of that region): region == wanted"},
  {va=0x1414ced48, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' -> 0x1414ce270"},
  {va=0x1414cee9d, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' -> 0x1414ce270"},
  {va=0x1414f8390, old="8b08c1e91b0fb6c1241f3c1d7304440fb6f1", new="8b088bc1c1e91bc1e81383e0600bc8448bf1", alt="8b088bc1c1e91bc1e81383e0200bc8448bf1",
   why="parser: region = Competition.bin +3 bits 3..7 (low five) | bit 0 -> 5 | bit 1 -> 6, 0..127; every row with bits 0..1 clear decodes as before"},
  {va=0x1414f83d1, old="740b0fb7d1488bcfe8521bfdff", new="c687ff0200005a660f1f440000",
   why="parser: the call that copied Competition.bin d0 bits 18..26 into +0x2fe (0x1414c9f30) becomes mov byte [rdi+0x2ff],0x5a -- the mark that says +0x2fe holds a region (old careers lack it)"},
  {va=0x14150c9d2, old="8b860c03000025801f00003d80000000", new="0fb686fe02000083f801660f1f440000",
   why="region == 1 (interClub) test: full region compared with 1 (was and 0x1f80 / cmp 0x80)"},
  {va=0x14151c95e, old="8b860c03000081e3ff0f000025801f00003d80000000", new="0fb686fe02000081e3ff0f000083f801660f1f440000",
   why="region == 1 (interClub) test: full region compared with 1 (and ebx,0xfff kept)"},
  {va=0x141541288, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' -> 0x1414ce270"},
  {va=0x141541639, old="8b800c030000c1e80783e03f", new="0fb680fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): the getter 0x1415415f0(comp) -> region, 63 callers"},
  {va=0x141542dd8, old="448bb00c03000041c1ee074183e63f", new="440fb6b0fe0200000f1f8000000000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x141542e6a, old="8bb80c030000c1ef0783e73f", new="0fb6b8fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x1415430a8, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x1415432a8, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x141543498, old="448ba00c03000041c1ec074183e43f", new="440fb6a0fe0200000f1f8000000000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x141543898, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x141543e65, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x141544ff8, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x141545088, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x141545528, old="8b880c030000c1e90783e13f", new="0fb688fe0200000f1f440000",
   why="full region (movzx byte +0x2fe, was +0x30c shr 7 / and 0x3f): inline 'region of competition' (0x14154xxxx block)"},
  {va=0x141575f1d, old="83f81d", new="83f800",
   why="0x141575ea0: region 29 is a region like any other (cmp eax,0x1d -> cmp eax,0; the test eax,eax / je after it already sends region 0 to the same place)"},
  {va=0x1415773af, old="83f81d", new="83f800",
   why="0x141577380: region 29 is a region like any other (cmp eax,0x1d -> cmp eax,0; the test eax,eax / je after it already sends region 0 to the same place)"},
  {va=0x141577414, old="83f81d", new="83f800",
   why="0x1415773e0: region 29 is a region like any other (cmp eax,0x1d -> cmp eax,0; the test eax,eax / je after it already sends region 0 to the same place)"},
}

local function unhex(s)
  local out = {}
  for b in s:gmatch("%x%x") do out[#out + 1] = string.char(tonumber(b, 16)) end
  return table.concat(out)
end

local function tohex(s)
  local out = {}
  for i = 1, #s do out[#out + 1] = string.format("%02x", string.byte(s, i)) end
  return table.concat(out)
end

function m.init(ctx)
  -- pass 1: check every site, write nothing
  local todo, done, bad = {}, 0, 0
  for _, p in ipairs(PATCHES) do
    local old, new = unhex(p.old), unhex(p.new)
    local cur = memory.read(p.va, #old)
    if cur == new then
      done = done + 1
    elseif cur == old or (p.alt and cur == unhex(p.alt)) then
      todo[#todo + 1] = p
    else
      bad = bad + 1
      log(string.format("fl26reg128: bytes at 0x%x are %s, expected %s -- %s",
                        p.va, tohex(cur), p.old, p.why))
    end
  end
  if bad > 0 then
    log(string.format("fl26reg128: %d site(s) unexpected -- NOTHING written, regions stay as they were", bad))
    return
  end
  -- pass 2: write and read back
  local fail = 0
  for _, p in ipairs(todo) do
    local new = unhex(p.new)
    memory.write(p.va, new)
    if memory.read(p.va, #new) ~= new then
      fail = fail + 1
      log(string.format("fl26reg128: WRITE FAILED at 0x%x", p.va))
    end
  end
  log(string.format("fl26reg128: %d of %d sites rewritten, %d already were%s -- regions 0..127",
                    #todo - fail, #PATCHES, done, fail > 0 and " (WRITE FAILURES above)" or ""))
end

return m
