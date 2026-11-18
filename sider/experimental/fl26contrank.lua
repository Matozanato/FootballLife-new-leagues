--[[
fl26contrank -- continental club rankings in the Master League: the Club Ranking screen,
filtered to one confederation and numbered 1..N inside it.

Replaces fl26menutest.lua (its button patch is included here). Load it in place of that one.

What the game already has
  * Club Ranking (750 entries of 16 bytes at block+0x16705a8, count at +0x2ee0):
    {u32 team id, u32 world position, u16 points, u16 points}. The screen RankingTeam
    (fill = vtable slot 27, 0x140b108c0) copies every entry into a vector of its own
    (this+0x98/+0xa0), sorts it by position and shows it.
  * The flow files Common/CmnLeagueRankingEU.json and ...SA.json, and the shipped ML menu
    flow already sends button 86 ("leaguerankeu", event 23) to Common/CmnLeagueRankingEU.
    Only the screen was never registered in the exe.

What this does
  1. Screens. The screen registry is a hash table of 887 buckets (0x1436f9df0) that the game
     fills once, on the first menu it opens (0x140a956c0, guarded by 0x1436f5149), from
     40-byte entries {factory, class name, unit path, flag, next} with 0x140e9fc90. Nothing
     ever clears it. The call at 0x140a956c9 is pointed at a stub that does the game's
     registration and then adds two entries of ours: Common/CmnLeagueRankingEU and
     Common/CmnLeagueRankingSA. Their factories set the confederation filter and go on into
     RankingTeam::CreateObject (0x140b107e0). The factory of Common/CmnClubRanking (pointer at
     0x1434a7a98, read at every lookup) is pointed at a stub that clears the filter first, so
     the normal Club Ranking stays the world list.
  2. Filter. In the fill's club loop, the call that copies one entry into the vector
     (0x140b10ab3 -> 0x140b115c0) goes through a stub: with a filter set, the club's
     country (team record +0x418, through the game's own lookup 0x1414bb580) is looked up in
     a 512-byte country -> confederation table, and the entry is copied only on a match.
  3. Numbering. Right after the sort (0x140b10af0) the copies are renumbered 1..N, so the
     position column shows the continental place. The game's own ranking is never written.
  4. Count. The list size given to the screen (0x140b10b50, mov r8d,[rbp+0x2ee0]) becomes the
     vector's own size, and the first-rows loop's out-of-range throw (0x140b10b2a) skips the
     row instead, so a list shorter than the screen cannot index past its end.
  5. Buttons. The ML menu shows at most 7 buttons per page (tested 2026-11-17: an 8th one on
     the Data page is not shown), and the Data page already has 6. So the rankings get a
     category of their own on the ML main menu, "Ranking" (button 91, text 0x46), beside
     Data: the root page has 6 categories and room for a 7th. Its page holds Club Ranking
     (88), National Ranking (89), League Ranking (Europe) (86) and League Ranking (South
     America) (87). TEST 3 showed the root page never shows a 7th category, so "Ranking"
     is the 7th button of the Data page instead (its 6 shipped buttons kept), a submenu.
     * Button table. The ML button table (0x1426add20) holds exactly 52 entries, so it is
       copied into the page (+0x500) with two more: {87, text 0x229, "leagueranksa"} and
       {91, text 0x46, no name: a category}. Only two places read it, each with a lea and a
       count of 0x34: the lookup by id (MainMenuMLData vtable slot 2, 0x140b86a30, cmp at
       0x140b86a4a) and the mailbox scan (0x140b87052, cmp at 0x140b87085). Both are pointed
       at the copy, count 0x36.
     * Pages. The menu's page tables (0x1426ae2e0, or 0x1426ae420 by [menu+0xa0]; 7 pages of
       {category, 10 ids} = 0x2c bytes) are given to the tree builder 0x140cd0bb0 at
       0x140b84f23..0x140b84f43. Both are copied into the page (+0x880, +0xa00) with an 8th
       page {91, 88, 89, 86, 87} and 91 in the root page's 7th slot, and the count becomes 8.
       The builder makes a button whose id is some page's category into a submenu.
     The shipped ML flow already has "23_leaguerankeu" and "27_leagueranksa" -> the two
     screens, and the menu asks for the event by the button's name, so no JSON change.

  6. Clubs past the world ranking (2026-11-17). The world ranking is built once by 0x141324d00:
     it walks the team array and takes the first 750 clubs that pass its checks (id not the
     empty one, no 0x1c000000 flag at +0x420, slot byte +0x41c & 0x7f not 0x7b); with fl26caps
     the array holds up to 2400 clubs, so every club past the 750th (Liga MX, Honduras, Jamaica,
     the new leagues) is in no ranking at all. With a filter set, right after the copy loop
     (0x140b10ac2) a stub walks the team array the same way, skips the first <world count>
     clubs that pass, and adds the rest of the confederation with the game's own points
     (0x1413225d0: the best 11 players). Then every entry's +4 becomes 0x10000 - points, so the
     sort orders the list by points, which is the world ranking's own order (0x1413222e0).
     The team array, its count, the world count and the empty id are read from the patched
     code at init (fl26caps moves the array). Built and checked by gen3.py.
  7. Labels: five strings of our own in text category 0x1a (ids 0x2ac..0x2b0: UEFA, CONMEBOL,
     CONCACAF, AFC, CAF), added to livecpk/root/bra/string/all.str by mkstr.py.

Confederations come from the world file's confed line (fl26world.txt, written by Mod Studio
from Country.bin +5): 2 UEFA, 3 AFC, 4 CONMEBOL, 5 CAF, 6 CONCACAF, 7 OFC. Without that
line nothing is installed.

Mod Studio (feature/cwc32): in the pack, but it works only when the world file has the cwc32
line (Leagues > More > Club World Cup). That Build also puts into the world's livecpk root the
flows (ML/MLMainManu.json, League/LeagueMainMenu.json with the leaguerankna/as/af events,
Common/CmnLeagueRankingNA/AS/AF.json) and every language's string/all.str with our texts
(cat 0x1a 0x2ac..0x2b6) -- tools/lbcwcmenu.py.

All or nothing: every site is read first; if one differs, nothing is written.
--]]

local m = {}

-- unit path, class name, confederation; offsets of its entry, strings and factory in the page
local UNITS = {
  { path = "Common/CmnLeagueRankingEU", name = "RankingTeam::CreateObjectEU", confed = 2,
    entry = 0x010, spath = 0x060, sname = 0x0a0, factory = 0x320 },
  { path = "Common/CmnLeagueRankingSA", name = "RankingTeam::CreateObjectSA", confed = 4,
    entry = 0x038, spath = 0x080, sname = 0x0c0, factory = 0x340 },
  -- 2026-11-17: CONCACAF, AFC, CAF. Unit paths of our own: their flow files (copies of
  -- CmnLeagueRankingEU.json) are in livecpk/root/common/script/flow/Common.
  { path = "Common/CmnLeagueRankingNA", name = "RankingTeam::CreateObjectNA", confed = 6,
    entry = 0x500, spath = 0x580, sname = 0x5e0, factory = 0x640 },
  { path = "Common/CmnLeagueRankingAS", name = "RankingTeam::CreateObjectAS", confed = 3,
    entry = 0x528, spath = 0x5a0, sname = 0x600, factory = 0x660 },
  { path = "Common/CmnLeagueRankingAF", name = "RankingTeam::CreateObjectAF", confed = 5,
    entry = 0x550, spath = 0x5c0, sname = 0x620, factory = 0x680 },
}
-- factories 640/660/680: mov dword [page+0], 6/3/5 ; jmp 0x140b107e0
-- 6a0 reg2: call 0x140a95d80 ; 0x140e9fc90(page + 10/38/500/528/550) ; ret
-- (built and checked with capstone, gen2.py, 2026-11-17). The old reg stub at 440 is unused.
local NEW_CODE = {
  [0x640] = "c705b6f9ffff06000000ff2500000000e007b14001000000",
  [0x660] = "c70596f9ffff03000000ff2500000000e007b14001000000",
  [0x680] = "c70576f9ffff05000000ff2500000000e007b14001000000",
  [0x6a0] = "4883ec2848b8805da94001000000ffd0488d0d59f9ffff48b890fce94001000000ffd0488d0d6ef9ffff"
         .. "48b890fce94001000000ffd0488d0d23feffff48b890fce94001000000ffd0488d0d38feffff48b890"
         .. "fce94001000000ffd0488d0d4dfeffff48b890fce94001000000ffd04883c428c3",
}
local REG2 = 0x6a0
local TABLE, CODE = 0x100, 0x300
local F_ALL, FILTER, RENUM, COUNT, REG = 0x300, 0x360, 0x3d0, 0x420, 0x440
-- National Ranking is the same RankingTeam screen (0x140b10850 = CreateObject with r9b = 1):
-- its factory must clear the filter too. mov dword [page+0],0 ; jmp 0x140b10850
local F_NAT = 0x4a0
local F_NAT_HEX = "c70556fbffff00000000ff25000000005008b14001000000"

-- The stubs, position independent (rip-relative inside the page, absolute into the exe).
-- Built and checked with capstone by gen.py (session of 2026-11-17):
--   300 f_all / 320 f_eu / 340 f_sa: mov dword [page+0], 0/2/4 ; jmp 0x140b107e0
--   360 filter: mode 0 -> push_back; else team = 0x1414bb580(r15, [rdx]); c = table[team+0x418];
--               c == mode -> push_back, else inc dword [page+4] ; ret
--   3d0 renum:  mode != 0 -> vector[i].+4 = i+1 ; mov rcx,rsi ; xor edi,edi ; jmp 0x140b10af5
--   420 count:  r8 = (end - begin) >> 4 ; jmp 0x140b10b57
--   440 reg:    call 0x140a95d80 ; 0x140e9fc90(page+0x10) ; 0x140e9fc90(page+0x38) ; ret
local CAVE_HEX = table.concat({
  "c705f6fcffff00000000ff2500000000e007b14001000000ccccccccccccccccc705d6fcffff02000000ff2500000000",
  "e007b14001000000ccccccccccccccccc705b6fcffff04000000ff2500000000e007b14001000000cccccccccccccccc",
  "833d99fcffff00744a51524883ec288b124c89f948b880b54b4101000000ffd00fb780180400004531c03d0002000073",
  "0c4c8d0d68fdffff450fb604014883c4285a59443b0556fcffff7407ff0552fcffffc3ff2500000000c015b140010000",
  "00cccccccccccccccccccccccccccccc833d29fcffff007430488b83a00000004c8b83980000004c29c048c1e80431c9",
  "4839c173148d51014989c949c1e104438954080448ffc1ebe74889f131ffff2500000000f50ab14001000000cccccccc",
  "4c8b83a00000004c2b839800000049c1e804ff2500000000570bb140010000004883ec2848b8805da94001000000ffd0",
  "488d0db9fbffff48b890fce94001000000ffd0488d0dcefbffff48b890fce94001000000ffd04883c428c3",
})

local SITES = {
  { va = 0x140b10ab3, old = "e8080b0000",       why = "club loop: call vector push_back" },
  { va = 0x140b10af0, old = "488bce33ff",       why = "after the sort: mov rcx,rsi; xor edi,edi" },
  { va = 0x140b10b2a, old = "0f86ce000000",     why = "first rows: jbe to the out-of-range throw" },
  { va = 0x140b10b50, old = "448b85e02e0000",   why = "list size: mov r8d,[rbp+0x2ee0]" },
  { va = 0x140a956c9, old = "e8b2060000",       why = "screen registration: call 0x140a95d80" },
  { va = 0x1434a7a98, old = "e007b14001000000", why = "registry: Common/CmnClubRanking factory" },
  { va = 0x1434a7ac0, old = "5008b14001000000", why = "registry: Common/CmnNationalRanking factory" },
  { va = 0x1426adfe0, old = "5600000028021a00", why = "button table: entry 86 'leaguerankeu'" },
  { va = 0x140b10ac2, old = "488b93a0000000",   why = "after the club loop: mov rdx,[rbx+0xa0]" },
  { va = 0x140b1096b, old = "e8a03d3400",       why = "screen title: call set text (edx 0x190085)" },
}

-- 8. Screen title (2026-11-17). The fill sets the title with 0x140e54710(rcx, 0x190085 "Club
-- Ranking", 0) at 0x140b1096b. That call goes to TITLE: with a filter set, edx becomes
-- TITLE_TAB[mode], our "Ranking <confed>" (cat 0x1a ids 0x2b1..0x2b5, mkstr2.py); a zero entry
-- or mode 0 keeps 0x190085. Uses rax/r11 only (rcx, rdx, r8 are the arguments). Checked with capstone.
--   mov eax,[page+0] ; cmp eax,7 ; ja go ; lea r11,[TITLE_TAB] ; mov eax,[r11+rax*4]
--   test eax,eax ; je go ; mov edx,eax ; go: jmp qword 0x140e54710
local TITLE, TITLE_TAB = 0x1400, 0x1440
local TITLE_HEX = "8b05faebffff83f80777114c8d1d2e000000418b048385c0740289c2ff25000000001047e54001000000"
local TITLE_IDS = { [2] = 0x1a02b1, [4] = 0x1a02b2, [6] = 0x1a02b3, [3] = 0x1a02b4, [5] = 0x1a02b5 }
local BTN_TABLE, BTN_COUNT = 0x1426add20, 0x34   -- the game's ML button table
local BTN_COPY = 0xc00                           -- its copy in the page (57 x 16 bytes)
-- Labels: our own strings in text category 0x1a (livecpk all.str, mkstr.py): UEFA 0x2ac,
-- CONMEBOL 0x2ad, CONCACAF 0x2ae, AFC 0x2af, CAF 0x2b0.
local BTN_NEW = {
  { id = 87, text = 0x2ad, cat = 0x1a, name = "leagueranksa", at = 0x0e0 },  -- CONMEBOL
  { id = 91, text = 0x2b6, cat = 0x1a },  -- "Ranking Copa de Clubes" / "Ranking CWC": a category, no name
  { id = 92, text = 0x2ae, cat = 0x1a, name = "leaguerankna", at = 0x720 },  -- CONCACAF
  { id = 93, text = 0x2af, cat = 0x1a, name = "leaguerankas", at = 0x730 },  -- AFC
  { id = 94, text = 0x2b0, cat = 0x1a, name = "leaguerankaf", at = 0x740 },  -- CAF
}
local BTN_RETEXT = { [86] = { 0x2ac, 0x1a } }   -- the game's 86 in the copy: "UEFA"

-- 6. the clubs past the world ranking (gen3.py, checked with capstone, 2026-11-17)
local PAGE_SIZE = 0x3000   -- 0x2000 until step 9 (the League Mode tree copy at +0x2000)
local EXTRA = 0x1000
local EXTRA_HEX = table.concat({
  "833df9efffff000f844c0100005356575541544155415641574883ec404d89fc488b05d90100004d8d2c04488b05d6",
  "010000458b3404488b05d3010000418b2c04488b05d00100008b3031ff4531ff4439f70f83c200000089f84869c09006",
  "0000498d5405008b0239f00f84a3000000f782200400000000001c0f85930000008a821c040000247f3c7b0f84830000",
  "0041ffc74139ef0f86770000000fb782180400003d000200000f8365000000488d0d4bf0ffff0fb604013b0541efffff",
  "0f854e000000488954243031c948b8d025324101000000ffd0488b5424308b0a894c2420c7442424000000006689442428",
  "668944242a488d8b98000000488d54242048b8c015b14001000000ffd0ff05f5eeffffffc7e935ffffff488b8398000000",
  "488b8ba00000004839c80f83180000000fb7500af7da81c2000001008950044883c010e9dfffffff4883c440415f415e",
  "415d415c5d5f5e5b488b93a0000000ff2500000000c90ab14001000000",
})
local ADDED = 0x008   -- dword: clubs the stub added, last time a filtered list was filled
-- page+1200 team array offset, +1208 team count offset, +1210 world count offset, +1218 &empty id
local D_TEAMS, D_COUNT, D_RCOUNT, D_SENT = 0x1200, 0x1208, 0x1210, 0x1218
-- the offsets, read from code at init: {va, opcode bytes before the disp32}
local DISP_SITES = {
  { va = 0x141324da5, op = "488db5", why = "world ranking build: lea rsi,[rbp+team array]" },
  { va = 0x141324d6d, op = "4439a5", why = "world ranking build: cmp [rbp+team count],r12d" },
  { va = 0x140b10a86, op = "4139bf", why = "club loop: cmp [r15+world count],edi" },
  { va = 0x141324d7a, op = "8b1d",   why = "world ranking build: mov ebx,[rip+empty id]" },
}
local CAT_RANK = 91
local PAGE_A, PAGE_B, PAGES, PSTRIDE = 0x1426ae2e0, 0x1426ae420, 7, 0x2c
local COPY_A, COPY_B = 0x880, 0xa00
-- 2026-11-17: Club Ranking (88) and National Ranking (89) left out, only the CWC ones
local RANK_PAGE = { CAT_RANK, 86, 87, 92, 93, 94 }
local BTN_SITES = {
  { va = 0x140b86a30, old = "4c8d0de972b201", op = "4c8d0d", copy = BTN_COPY, why = "lookup by id: lea r9,[table]" },
  { va = 0x140b86a4a, old = "83f834",         cnt = "83f8",  why = "lookup by id: cmp eax,0x34" },
  { va = 0x140b87052, old = "488d3dc76cb201", op = "488d3d", copy = BTN_COPY, why = "mailbox scan: lea rdi,[table]" },
  { va = 0x140b87085, old = "83fb34",         cnt = "83fb",  why = "mailbox scan: cmp ebx,0x34" },
  { va = 0x140b84f23, old = "41b807000000",   why = "ML menu: mov r8d,7 (pages)" },
  { va = 0x140b84f33, old = "488d15e694b201", op = "488d15", copy = COPY_B, why = "ML menu: lea rdx,[pages B]" },
  { va = 0x140b84f3c, old = "488d159d93b201", op = "488d15", copy = COPY_A, why = "ML menu: lea rdx,[pages A]" },
  { va = 0x1426ae2e0, old = "01000000020000000300000004000000050000000700000008000000",
    why = "root page (A): 1 | 2 3 4 5 7 8" },
  { va = 0x1426ae2fc, old = "00000000",       why = "root page (A): 7th slot free" },
  { va = 0x1426ae420, old = "01000000020000000300000004000000050000000700000008000000",
    why = "root page (B): 1 | 2 3 4 5 7 8" },
  { va = 0x1426ae43c, old = "00000000",       why = "root page (B): 7th slot free" },
  { va = 0x1426ae3bc, old = "070000003c0000003d0000001e0000005a0000005800000059000000",
    why = "Data page (A): 7 | 60 61 30 90 88 89" },
  { va = 0x1426ae4fc, old = "070000003c0000003d0000001e0000005a0000005800000059000000",
    why = "Data page (B): 7 | 60 61 30 90 88 89" },
}
local DATA_PAGE = 5   -- index of the Data page (category 7) in both tables

-- 9. League Mode (2026-11-17, gen4.py, checked with capstone). The League main menu is not
-- made of pages: its class asks for a node tree through vtable slot +0x298 (0x14271bc90 ->
-- 0x140c907f0), which builds six static trees once, returns one (by the game's state) in rax
-- and writes its node count to [this+0x9c]. A node is 0x50 bytes {u32 flag, u32 text
-- (cat << 16 | id), u32 id, pad, std::string name +0x10, std::string parent +0x30}; flag 0
-- for the root's items, 1 inside a page (it only picks the panel's fade). The consumer
-- 0x140c8db50 makes an object of every node and links each to the node its parent names.
-- Every tree has Data = ToData (compeinfo, teaminfo, and clubrank in three of them).
-- The slot goes to LG_WRAP: the original, its nodes copied to LG_BUF, LG_NODES appended
-- (Ranking under ToData + its five buttons), count + 6, LG_BUF returned. More than 32 nodes:
-- left as they were. The buttons send their names to the flow: the League flow
-- (livecpk League/LeagueMainMenu.json) has leaguerankeu/sa as shipped, plus na/as/af of ours.
local LG_SLOT, LG_SLOT_OLD = 0x14271bc90, "f007c94001000000"
local LG_WRAP, LG_NODES = 0x1600, 0x1700
local LG_WRAP_HEX = "5356574883ec204889cb48b8f007c94001000000ffd0448b8b9c0000004183f92077294889c6488d3dd309"
                 .. "0000574489c96bc950f3a4488d35c3000000b9e0010000f3a45883839c000000064883c4205f5e5bc3"
-- Back from a screen, 0x140c8e2e0 rebuilds the menu on a page one level up (Data, not
-- Ranking) with the cursor index of the button pressed ([this+0xa8]); an index past the page's
-- end read a null at 0x140c8e456 (crash after CAF, index 4, 2026-11-17). 0x140c8e420 goes to
-- LG_CLAMP: past the end -> the page's last item (Data: Ranking), written back. gen4.py.
local LG_CLAMP, LG_CLAMP_SITE, LG_CLAMP_OLD = 0x1660, 0x140c8e420, "448b83a80000004c3bc1720433c9eb26"
local LG_CLAMP_HEX = "448b83a80000004c3bc172104885c974194c8d41ff448983a8000000ff250000000030e4c840010000"
                  .. "00ff25000000002ce4c84001000000"
local LG_TREE = {   -- flag, text, id, name, parent
  { 1, 0x1a02b6, CAT_RANK, "ToRanking", "ToData" },   -- "Ranking Copa de Clubes" / "Ranking CWC"
  { 1, 0x1a02ac, 86, "leaguerankeu", "ToRanking" },   -- UEFA
  { 1, 0x1a02ad, 87, "leagueranksa", "ToRanking" },   -- CONMEBOL
  { 1, 0x1a02ae, 92, "leaguerankna", "ToRanking" },   -- CONCACAF
  { 1, 0x1a02af, 93, "leaguerankas", "ToRanking" },   -- AFC
  { 1, 0x1a02b0, 94, "leaguerankaf", "ToRanking" },   -- CAF
}
local REG_DONE = 0x1436f5149   -- byte: the game's screen registration has run

local function unhex(s)
  return (s:gsub("%x%x", function(h) return string.char(tonumber(h, 16)) end))
end
local function tohex(s)
  if s == nil then return "nil" end
  return (s:gsub(".", function(c) return string.format("%02x", c:byte()) end))
end
local function u32(v)
  v = v % 0x100000000
  return string.char(v % 256, math.floor(v / 256) % 256, math.floor(v / 65536) % 256,
                     math.floor(v / 16777216) % 256)
end
local function u64(v) return u32(v % 0x100000000) .. u32(math.floor(v / 0x100000000)) end
-- an MSVC std::string of up to 15 characters: the text inline, size +0x10, capacity 15 +0x18
local function sso(s)
  return s .. string.rep("\0", 16 - #s) .. u64(#s) .. u64(15)
end
local function rel32(from_end, to)
  local d = to - from_end
  if d < -0x80000000 or d > 0x7fffffff then return nil end
  return u32(d)
end

-- confed <country>:<code>,... from the world file
local function read_confed(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  if not f then return nil, "no fl26world.txt" end
  local map, n, cwc = {}, 0, false
  for line in f:lines() do
    if line:match("^%s*cwc32%s") then cwc = true end
    local cf = line:match("^%s*confed%s+([%d:,]+)")
    if cf then
      for c, k in cf:gmatch("(%d+):(%d+)") do
        c, k = tonumber(c), tonumber(k)
        if c < 512 and k < 256 then map[c] = k; n = n + 1 end
      end
    end
  end
  f:close()
  -- the rankings belong to the Club World Cup of 32: only in a world built with it
  if not cwc then return nil, "the world file has no cwc32 line (Club World Cup of 32 off)" end
  if n == 0 then return nil, "fl26world.txt has no confed line" end
  return map, n
end

local function alloc()
  if not m.cdef then
    -- a name of our own: other modules declare VirtualAlloc too, and a second cdef is an error
    ffi.cdef([[ void* fl26contrank_VirtualAlloc(void*, size_t, uint32_t, uint32_t) asm("VirtualAlloc"); ]])
    m.cdef = true
  end
  -- below the image first, then above it: every patched call/jmp needs rel32 reach
  local prefs = {}
  for k = 0, 47 do prefs[#prefs + 1] = 0x13e000000 - k * 0x100000 end
  for k = 0, 47 do prefs[#prefs + 1] = 0x150200000 + k * 0x100000 end
  for _, pref in ipairs(prefs) do
    local p = ffi.C.fl26contrank_VirtualAlloc(ffi.cast("void*", pref), PAGE_SIZE, 0x3000, 0x40)
    if p ~= nil then return tonumber(ffi.cast("uint64_t", p)) end
  end
  return nil
end

function m.init(ctx)
  if ffi == nil then log("fl26contrank: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  local confed, n = read_confed(ctx)
  if not confed then log("fl26contrank: " .. n .. " -- nothing installed"); return end
  for _, s in ipairs(BTN_SITES) do SITES[#SITES + 1] = s end
  SITES[#SITES + 1] = { va = LG_SLOT, old = LG_SLOT_OLD, why = "League Mode menu: vtable slot +0x298 (node tree)" }
  SITES[#SITES + 1] = { va = LG_CLAMP_SITE, old = LG_CLAMP_OLD, why = "League Mode menu: cursor index on return" }
  for _, s in ipairs(SITES) do
    local got = memory.read(s.va, #s.old / 2)
    if got ~= unhex(s.old) then
      log(string.format("fl26contrank: %x is %s, expected %s (%s) -- nothing written",
                        s.va, tohex(got), s.old, s.why))
      return
    end
  end
  -- the offsets the extra-clubs stub needs, from the code as it is now (after fl26caps)
  local disp = {}
  for _, s in ipairs(DISP_SITES) do
    local n = #s.op / 2
    local got = memory.read(s.va, n + 4)
    if got == nil or got:sub(1, n) ~= unhex(s.op) then
      log(string.format("fl26contrank: %x is %s, expected %s.. (%s) -- nothing written",
                        s.va, tohex(got), s.op, s.why))
      return
    end
    local b1, b2, b3, b4 = got:byte(n + 1, n + 4)
    local v = b1 + 256 * b2 + 65536 * b3 + 16777216 * b4
    if v >= 0x80000000 then v = v - 0x100000000 end
    disp[#disp + 1] = v
  end
  local d_sent = 0x141324d7a + 6 + disp[4]   -- rip-relative: the address of the empty id
  local cave = alloc()
  if not cave then log("fl26contrank: no page for the stubs -- nothing written"); return end
  local j_filter = rel32(0x140b10ab3 + 5, cave + FILTER)
  local j_renum  = rel32(0x140b10af0 + 5, cave + RENUM)
  local j_count  = rel32(0x140b10b50 + 5, cave + COUNT)
  local j_reg    = rel32(0x140a956c9 + 5, cave + REG2)
  local j_extra  = rel32(0x140b10ac2 + 5, cave + EXTRA)
  local j_title  = rel32(0x140b1096b + 5, cave + TITLE)
  local j_clamp  = rel32(LG_CLAMP_SITE + 5, cave + LG_CLAMP)
  local lea = {}
  for _, s in ipairs(BTN_SITES) do
    if s.op then lea[s.va] = rel32(s.va + 7, cave + s.copy) end
  end
  local lea_ok = true
  for _, s in ipairs(BTN_SITES) do if s.op and not lea[s.va] then lea_ok = false end end
  if not (j_filter and j_renum and j_count and j_reg and j_extra and j_title and j_clamp and lea_ok) then
    log(string.format("fl26contrank: page 0x%x is out of jump range -- nothing written", cave))
    return
  end

  -- the page: filter mode (+0), clubs left out (+4), registry entries, strings, table, code
  local page = ffi.cast("uint8_t*", cave)
  ffi.fill(page, PAGE_SIZE, 0)
  for _, u in ipairs(UNITS) do
    ffi.copy(page + u.spath, u.path)   -- a string copy: the terminating zero comes along
    ffi.copy(page + u.sname, u.name)
    ffi.copy(page + u.entry, u64(cave + u.factory) .. u64(cave + u.sname) .. u64(cave + u.spath)
                             .. u64(1) .. u64(0), 40)
  end
  local per = {}
  for c, k in pairs(confed) do page[TABLE + c] = k; per[k] = (per[k] or 0) + 1 end
  local code = unhex(CAVE_HEX)
  ffi.copy(page + CODE, code, #code)
  local fnat = unhex(F_NAT_HEX)
  ffi.copy(page + F_NAT, fnat, #fnat)
  for at, h in pairs(NEW_CODE) do local b = unhex(h); ffi.copy(page + at, b, #b) end
  local extra = unhex(EXTRA_HEX)
  ffi.copy(page + EXTRA, extra, #extra)
  local title = unhex(TITLE_HEX)
  ffi.copy(page + TITLE, title, #title)
  for k, id in pairs(TITLE_IDS) do ffi.copy(page + TITLE_TAB + 4 * k, u32(id), 4) end
  ffi.copy(page + D_TEAMS, u64(disp[1]) .. u64(disp[2]) .. u64(disp[3]) .. u64(d_sent), 32)
  -- the button table: the game's 52 entries as they are now, then ours
  local btns = memory.read(BTN_TABLE, BTN_COUNT * 16)
  ffi.copy(page + BTN_COPY, btns, #btns)
  for k = 0, BTN_COUNT - 1 do
    local e = BTN_COPY + 16 * k
    local id = page[e] + 256 * page[e + 1]
    local t = BTN_RETEXT[id]
    if t then
      ffi.copy(page + e + 4, string.char(t[1] % 256, math.floor(t[1] / 256), t[2] % 256,
               math.floor(t[2] / 256)), 4)
    end
  end
  for k, b in ipairs(BTN_NEW) do
    local name = 0
    if b.name then ffi.copy(page + b.at, b.name); name = cave + b.at end
    ffi.copy(page + BTN_COPY + #btns + 16 * (k - 1), u32(b.id) .. string.char(b.text % 256,
             math.floor(b.text / 256), b.cat % 256, math.floor(b.cat / 256)) .. u64(name), 16)
  end
  -- the page tables: the game's 7 pages, "Ranking" in the root page's 7th slot, then its page
  for _, c in ipairs({ { PAGE_A, COPY_A }, { PAGE_B, COPY_B } }) do
    local pages = memory.read(c[1], PAGES * PSTRIDE)
    ffi.copy(page + c[2], pages, #pages)
    -- TEST 3 (2026-11-17) showed: the root page never shows a 7th category, but a submenu
    -- inside Data works. So "Ranking" (91) is the Data page's 7th button (shipped 6 kept).
    ffi.copy(page + c[2] + DATA_PAGE * PSTRIDE + 4 + 6 * 4, u32(CAT_RANK), 4)
    local rp = ""
    for _, id in ipairs(RANK_PAGE) do rp = rp .. u32(id) end
    ffi.copy(page + c[2] + PAGES * PSTRIDE, rp, #rp)
  end

  -- League Mode: the wrapper and the six nodes it appends
  local lgw = unhex(LG_WRAP_HEX)
  ffi.copy(page + LG_WRAP, lgw, #lgw)
  local lgc = unhex(LG_CLAMP_HEX)
  ffi.copy(page + LG_CLAMP, lgc, #lgc)
  for k, nd in ipairs(LG_TREE) do
    local rec = u32(nd[1]) .. u32(nd[2]) .. u32(nd[3]) .. u32(0) .. sso(nd[4]) .. sso(nd[5])
    ffi.copy(page + LG_NODES + 0x50 * (k - 1), rec, 0x50)
  end

  -- the game (every site was checked above)
  memory.write(LG_CLAMP_SITE, "\233" .. j_clamp .. string.rep("\144", 11))
  memory.write(LG_SLOT, u64(cave + LG_WRAP))
  memory.write(0x140b10ab3, "\232" .. j_filter)
  memory.write(0x140b10af0, "\233" .. j_renum)
  memory.write(0x140b10b2a, unhex("0f8612000000"))        -- jbe 0x140b10b42: next row
  memory.write(0x140b10b50, "\233" .. j_count .. "\144\144")
  memory.write(0x140b10ac2, "\233" .. j_extra .. "\144\144")
  memory.write(0x140b1096b, "\232" .. j_title)
  memory.write(0x1434a7a98, u64(cave + F_ALL))
  memory.write(0x1434a7ac0, u64(cave + F_NAT))
  for _, s in ipairs(BTN_SITES) do
    if s.op then memory.write(s.va, unhex(s.op) .. lea[s.va])
    elseif s.cnt then memory.write(s.va, unhex(s.cnt) .. string.char(BTN_COUNT + #BTN_NEW)) end
  end
  memory.write(0x140b84f23, unhex("41b8") .. u32(PAGES + 1))
  if memory.read(REG_DONE, 1) == "\0" then
    memory.write(0x140a956c9, "\232" .. j_reg)
  else
    -- the game has registered its screens already: add ours now
    local reg = ffi.cast("void (*)(void*)", 0x140e9fc90)
    for _, u in ipairs(UNITS) do reg(page + u.entry) end
    log("fl26contrank: screens registered late (the game's registration had already run)")
  end
  log(string.format("fl26contrank: stubs at 0x%x; %d countries (UEFA %d, CONMEBOL %d, CONCACAF %d, AFC %d, CAF %d); "
                    .. "ML Data page 60 61 30 90 88 89 + Ranking (91): 86 87 92 93 94 -> EU/SA/NA/AS/AF (%s, %s, ...); titles 'Ranking <confed>'; League Mode Data + Ranking (vtable 0x14271bc90 -> 0x%x); National resets filter; clubs past the world ranking added (teams +0x%x, count +0x%x, world count +0x%x, empty id at 0x%x)", cave, n,
                    per[2] or 0, per[4] or 0, per[6] or 0, per[3] or 0, per[5] or 0, UNITS[1].path, UNITS[2].path, cave + LG_WRAP,
                    disp[1], disp[2], disp[3], d_sent))
  m.cave = cave
end

return m
