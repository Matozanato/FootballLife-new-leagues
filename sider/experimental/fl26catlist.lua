--[[
fl26catlist -- show OUR countries in Master League -> Database -> Competition Info.

Why: the category list on that screen is built by 0x140ead9f0 from a static list of 28
region ids compiled into FL_2026.exe (.rdata 0x1427d5760: 1,26,8,12,2,...,25 -- the display
order). For every region in that list it looks for a live regulation whose region
(+0x30c bits 7..12) matches, and adds the region if one exists. Our leagues sit in regions
30 and up (fl26reg64 widened the field to 64, fl26reg128 to 128), none of which is in the list, so a league in an
existing country shows up (France D3..D5 under France) and a league in a country of its own
does not appear at all.

The same list orders the categories in the sort helper 0x140eadae0. The only other thing
keyed on the region there is the category picture (0x140acd478, 24 entries, stride 16); a
region it does not know keeps the default 'compeCategory-interClub' image, so a new
country gets a generic picture, not a crash.

What this does, at boot, runtime only: copies the 28 shipped ids into a private table,
appends the rest of 1..127 (only regions with a live regulation get listed, so the unused ones cost
nothing), re-points the two rip-relative leas at the copy and raises the two loop counts.
All four code sites are checked against their expected bytes first (all-or-nothing).

The category NAME is the country's name: 0x1415787c0 asks 0x1414cdbe0 for the country of a
region and prints that country record. 0x1414cdbe0 knows 25 {country, region} pairs built on
its stack and answers 0xffff for anything else, so every one of our countries showed a blank
label. A five-byte jump at its entry sends it to a small stub first: a region that has an
entry in COUNTRY below gets that country, any other region runs the original code unchanged.
Region 11 is in the shipped pairs as Poland, which no shipped league uses; our world put
Croatia there, so it is overridden too. The other callers compare a league's country with
club or player nationality (the season code at 0x141354189 / 0x141357073), which is what
every shipped league already gets.

COUNTRY is keyed by the regions tools/spreadregions.py --plan own hands out; the values are
country ids (Country.bin, +0x48 & 0x1ff). A world with a different region plan needs this
table changed with it.

The competition icons on a league's page (GitHub #33, 1b). The League Info panel (menu code
0x140b3bb50, also 0x140ac3230 and 0x140c98bc2) shows up to six competition emblems
(emblemCompe_0..5) and the leagues above and below. All three get them from one builder,
0x140c6ccb0, which walks every live regulation and keeps a competition id (+0x80) when
  * the regulation is in the league's own region (+0x30c bits 7..12) and 0x1414cf180 or
    0x1414cfeb0 accepts it -- the country's cups; or
  * it is in region 1 (the club-continental region) and its confederation code (+0x300 bits
    25..28) is 7 (world: the Club World Cup) or equals the league's own code.
So the list keys on the league's CONFEDERATION, not on its region, and nothing in it stops at
region 28. The code is parsed from Competition.bin +6 (low three bits) through the table at
0x14297d270 (parser 0x1414f81ca): file 2 UEFA -> 1, 3 AFC -> 2, 4 CONMEBOL -> 5, 5 CAF -> 6,
6 CONCACAF -> 3, 7 OFC -> 0. Up to Mod Studio 0.1.2 every new league copied England D1's
competition row and so carried UEFA (1): a Peruvian league in region 29 got the Club World
Cup, Champions League, Europa League and Super Cup -- exactly the four in the report. The
league builder writes the country's confederation into the row since Mod Studio 0.1.3; a world
built before that keeps the European icons until it is rebuilt.

This fixes the page itself, for old worlds and new: a 12-byte run at 0x140c6cd97 (the read of
the league's code) becomes a call to a stub that reads the code as before and then, for a
region 29..127 that has an entry in a 128-byte table, returns that region's code instead. The
entry comes from the world file: the league's `conf=` (the builder writes the country's
confederation, 2..7), else the continent its `uefa` places go to (0-2 UEFA, 3/4/9 CONMEBOL,
5/8 AFC, 6/7 CAF), else the league above it. Regions 0..28 have no entry, so every shipped
league reads its own code exactly as before; the season code, which filters on the same
field, is not touched -- only this builder calls the stub. With the right code the game's own
rule gives a South American league the Club World Cup and the Libertadores (and our Copa
Sudamericana when the world has it), an Asian one the AFC Champions League, an African one
the CAF cups -- the same icons a shipped league of that continent shows, next to its own cups.

The world file. When SiderAddons\modules\fl26world.txt exists (written by FL26 Mod Studio's
League Builder), COUNTRY is built from it instead: the region= and country= of every league
on a region no shipped league uses (29 and up, and the headless 11, 13, 14 and 20). A shipped
region is never overridden. Without the file the built-in table below is used, as before.

Regions 128..255 (FL 2027, a caps set with the regions step -- tools/regions.py, 06.11.2026).
When the world file has a league in a region above 127, the list goes on to 255 and the stubs'
tables grow to 256 entries. The two loop counts are then the byte compares `cmp bl, n` /
`cmp cl, n` (80 fb / 80 f9, unsigned: the loops count up from 0 with jb), the same three bytes;
the stubs' `cmp r32, 0x7f` becomes `cmp r32, 0xff` (six bytes, the code after it moved by three).
A world with no region above 127 gets exactly the bytes it got before.
]]
local m = {}

local SHIPPED = 0x1427d5760
local NSHIPPED = 28
local LAST_REGION = 127   -- fl26reg128; with fl26reg64 the ids above 63 simply never match
local WIDE_REGION = 255   -- a world with a region above 127 (fl26caps' regions step reads them)
local PARSER, PARSER_WIDE = 0x1414f8390, "0fb64803c0c903440fb6f1"   -- that step's region parser

-- {va, expected bytes (hex)}
local LEAS = {
  { 0x140eada38, "4c8d25217d9201" },   -- lea r12,[list]  (builder)
  { 0x140eadb9a, "488d05bf7b9201" },   -- lea rax,[list]  (sort helper)
}
-- {va, expected bytes, offset of the imm8, the byte compare for a count past 127}
local COUNT_SITES = {
  { 0x140eadab6, "83fb1c", 2, "\128\251" },   -- cmp ebx, 0x1c  (builder)      -> cmp bl, n
  { 0x140eadbb4, "83f91c", 2, "\128\249" },   -- cmp ecx, 0x1c  (sort helper)  -> cmp cl, n
}

-- region -> country id
local COUNTRY = {
  [11] = 200,   -- Croatia
  [29] = 212,   -- Hungary
  [30] = 227,   -- Poland
  [31] = 202,   -- Czech Republic
  [32] = 234,   -- Slovakia
  [33] = 194,   -- Austria
  [34] = 229,   -- Romania
  [35] = 199,   -- Bulgaria
  [36] = 238,   -- Switzerland
  [37] = 239,   -- Ukraine
  [38] = 226,   -- Norway
  [39] = 237,   -- Sweden
  [40] = 214,   -- Ireland
  [41] = 221,   -- North Macedonia
  [42] = 304,   -- Montenegro
  [43] = 191,   -- Albania
  [44] = 207,   -- Finland
  [45] = 152,   -- Uruguay
  [46] = 150,   -- Paraguay
  [47] = 151,   -- Peru
  [48] = 149,   -- Ecuador
  [49] = 145,   -- Bolivia
  [50] = 153,   -- Venezuela
  [51] = 124,   -- Mexico
  [52] = 16,    -- Republic of Korea
  [53] = 162,   -- Australia
  [56] = 11,    -- Iran
  [58] = 235,   -- Slovenia
  [59] = 303,   -- Serbia
  [60] = 198,   -- Bosnia and Herzegovina
}
-- The world file: modules\fl26world.txt, written by FL26 Mod Studio's League Builder.
-- One table per league -- id, then whatever the line gives: cid, region, country, slot, tier,
-- above, promote, demote, clubs, legs, conf (numbers), name (text) -- in file order; the `uefa`
-- places as leagues.uefa = { {regulation, position, competition}, ... }. nil when there is no
-- file: the module then keeps the built-in table above.
local function read_world(ctx)
  local sep = string.char(92)
  local path = ctx.sider_dir:gsub("[/" .. sep .. "]+$", "") .. sep .. "modules" .. sep .. "fl26world.txt"
  local f = io.open(path, "r")
  if not f then return nil end
  local leagues = {}
  for line in f:lines() do
    local order = line:match("^%s*order%s+([%d,]+)")
    if order then
      leagues.order = {}
      for v in order:gmatch("%d+") do leagues.order[#leagues.order + 1] = tonumber(v) end
    end
    local gs, glow = line:match("^%s*gset%s+(%d+).-%slow=([%d:,]+)")
    if gs then
      local lows = {}
      for r, n, up in glow:gmatch("(%d+):(%d+):(%d+)") do lows[#lows + 1] = { tonumber(r), tonumber(up) } end
      leagues.gsets = leagues.gsets or {}
      leagues.gsets[#leagues.gsets + 1] = lows
    end
    local st = line:match("^%s*split%s+(%d+)%s")
    if st then                                   -- a split league's phases, each a league record of its own
      local ph = {}
      local reg = line:match("%sregular=(%d+)")
      if reg then ph[#ph + 1] = tonumber(reg) end
      local grp = line:match("%sgroups=([%d,]+)")
      for g in (grp or ""):gmatch("%d+") do ph[#ph + 1] = tonumber(g) end
      leagues.splits = leagues.splits or {}
      leagues.splits[#leagues.splits + 1] = { tonumber(st), ph }
    end
    local u = { line:match("^%s*uefa%s+(%d+)%s+(%d+)%s+(%d+)") }
    if #u == 3 then
      leagues.uefa = leagues.uefa or {}
      leagues.uefa[#leagues.uefa + 1] = { tonumber(u[1]), tonumber(u[2]), tonumber(u[3]) }
    end
    local id, rest = line:match("^%s*league%s+(%d+)(.*)$")
    if id then
      local L = { id = tonumber(id) }
      local name = rest:match("%sname=(.-)%s*$")
      if name then L.name = name; rest = rest:gsub("%sname=.*$", "") end
      for k, v in rest:gmatch("(%a+)=(%-?%d+)") do L[k] = tonumber(v) end
      leagues[#leagues + 1] = L
    end
  end
  f:close()
  return leagues
end

-- Shipped regions the exe names wrongly. Its 25 {country, region} pairs are PES 2021's: region
-- 10 is Switzerland and 28 Thailand, while the game's data put the Greek Super League in 10 and
-- the Saudi Pro League in 28, and MLS's 23 (a special 0xfffd) printed as Mexico -- "SWITZERLAND"
-- over the Greek flag, "THAILAND" over the Saudi one (in game, 07.10.). Only the category label
-- takes these: the season code keeps the exe's answer for a shipped region, as it always had.
local LABEL = {
  [10] = 211,   -- Greece
  [20] = 135,   -- USA: the MLS row still read MEXICO with 23 alone, so the label asks for 20
  [23] = 135,   -- USA
  [28] = 31,    -- Saudi Arabia
}
local LABEL_RET = 0x1415788dc   -- where 0x1415787c0's call to COUNTRY_FN returns

-- From the world file: region -> country for the regions no shipped league uses -- 29 and up,
-- and the four headless ids 11, 13, 14, 20. A shipped region is never overridden: its country
-- is also what the season code compares club and player nationality with.
local OWN_REGION = { [11] = true, [13] = true, [14] = true, [20] = true }
local function world_countries(world)
  local c = {}
  for _, L in ipairs(world) do
    if L.region and L.country and (L.region >= 29 or OWN_REGION[L.region]) then c[L.region] = L.country end
  end
  return c
end

local COUNTRY_FN = 0x1414cdbe0
local COUNTRY_ENTRY = "4055488d6c24a9"   -- push rbp ; lea rbp,[rsp-0x57]

local function u32le(v)
  return string.char(v % 256, math.floor(v / 256) % 256, math.floor(v / 65536) % 256, math.floor(v / 16777216) % 256)
end
local function bin2hex(s) return (s:gsub(".", function(c) return string.format("%02x", c:byte()) end)) end

local function check_sites(list)
  for _, s in ipairs(list) do
    local got = bin2hex(memory.read(s[1], #s[2] / 2))
    if got ~= s[2] then
      log(string.format("fl26catlist: bytes at 0x%x are %s, expected %s -- aborting", s[1], got, s[2]))
      return false
    end
  end
  return true
end

local function rel32(from_next, to)
  local d = to - from_next
  if d >= 0x80000000 or d < -0x80000000 then return nil end
  if d < 0 then d = d + 0x100000000 end
  return u32le(d)
end

-- the stub: 80 bytes of code, then two 128-entry u16 region -> country tables, COUNTRY at 80
-- and LABEL at 336 (LAST_REGION 255: `cmp ecx,0xff`, everything below 3 bytes later, 96 bytes
-- of code, two 256-entry tables, COUNTRY at 96 and LABEL at 608)
--   0  cmp ecx,0x7f ; ja orig          5  mov eax,ecx
--   7  mov rdx,LABEL_RET ; cmp [rsp],rdx ; jne all      (the category label's call only)
--  23  lea rdx,[LABEL] ; movzx edx,word [rdx+rax*2] ; cmp dx,-1 ; je all ; mov eax,edx ; ret
--  43  all: lea rdx,[COUNTRY] ; movzx eax,word [rdx+rax*2] ; cmp ax,-1 ; je orig ; ret
--  61  orig: push rbp ; lea rbp,[rsp-0x57] ; jmp COUNTRY_FN+7
local function install_country()
  if bin2hex(memory.read(COUNTRY_FN, 7)) ~= COUNTRY_ENTRY then
    log(string.format("fl26catlist: bytes at 0x%x are %s, expected %s -- country names left alone",
                      COUNTRY_FN, bin2hex(memory.read(COUNTRY_FN, 7)), COUNTRY_ENTRY))
    return
  end
  local stub
  for _, pref in ipairs({ 0x15e100000, 0x15f100000, 0x161100000, 0x171100000 }) do
    local p = ffi.C.VirtualAlloc(ffi.cast("void*", pref), 0x1000, 0x3000, 0x40)  -- PAGE_EXECUTE_READWRITE
    if p ~= nil then stub = tonumber(ffi.cast("uint64_t", p)); break end
  end
  if not stub then log("fl26catlist: VirtualAlloc for the country stub failed -- names left alone"); return end
  local wide = LAST_REGION > 127
  local at, tables = wide and 3 or 0, wide and 96 or 80
  local back = rel32(stub + 73 + at, COUNTRY_FN + 7)
  local into = rel32(COUNTRY_FN + 5, stub)
  if not (back and into) then log("fl26catlist: country stub out of jump range -- names left alone"); return end
  local code = (wide and "\129\249\255\0\0\0" or "\131\249\127") .. "\119\56" .. "\137\200"
            .. "\72\186" .. u32le(LABEL_RET % 0x100000000) .. u32le(math.floor(LABEL_RET / 0x100000000))
            .. "\72\57\20\36" .. "\117\20"
            .. "\72\141\21" .. u32le(tables + 2 * (LAST_REGION + 1) - 30 - at) .. "\15\183\20\66" .. "\102\131\250\255" .. "\116\3"
            .. "\137\208" .. "\195"
            .. "\72\141\21" .. u32le(tables - 50 - at) .. "\15\183\4\66" .. "\102\131\248\255" .. "\116\1" .. "\195"
            .. "\64\85\72\141\108\36\169" .. "\233" .. back
  code = code .. string.rep("\204", tables - #code)
  assert(#code == tables)
  local tbl, lbl, named = {}, {}, 0
  for r = 0, LAST_REGION do
    local c = COUNTRY[r] or 0xffff
    if COUNTRY[r] then named = named + 1 end
    tbl[#tbl + 1] = string.char(c % 256, math.floor(c / 256))
    local l = (not COUNTRY[r] and LABEL[r]) or 0xffff
    lbl[#lbl + 1] = string.char(l % 256, math.floor(l / 256))
  end
  local body = code .. table.concat(tbl) .. table.concat(lbl)
  ffi.copy(ffi.cast("void*", stub), body, #body)
  memory.write(COUNTRY_FN, "\233" .. into .. "\144\144")
  log(string.format("fl26catlist: country names -- stub at 0x%x, %d regions named", stub, named))
end

-- The League Info icons (see the header): the builder's read of the league's confederation code.
local ICONS_SITE = 0x140c6cd97
local ICONS_OLD  = "8b8800030000c1e91983e10f" .. "894dbf"
--                  mov ecx,[rax+0x300] ; shr ecx,0x19 ; and ecx,0xf  | mov [rbp-0x41],ecx (stays)
local CONF_TABLE = 0x14297d270      -- Competition.bin +6 & 7 -> runtime code, u32 x 8 (parser 0x1414f81ca)
local CONF_TABLE_BYTES = "0800000007000000010000000200000005000000060000000300000000000000"
-- the continent a `uefa` place goes to (fl26world.COMPETITIONS / CCUPS), as a file code
local PLACE_CONF = { [0] = 2, [1] = 2, [2] = 2, [3] = 4, [4] = 4, [5] = 3, [6] = 5, [7] = 5, [8] = 3, [9] = 4 }

-- region 29..127 -> confederation as Competition.bin / Country.bin write it (2..7), from the world
-- file: a league's conf=, else where its places go, else the league above it
local function world_confeds(world)
  local conf_of, by_id = {}, {}
  for _, L in ipairs(world) do
    by_id[L.id] = L
    if L.conf and L.conf >= 2 and L.conf <= 7 then conf_of[L.id] = L.conf end
  end
  for _, u in ipairs(world.uefa or {}) do
    if by_id[u[1]] and not conf_of[u[1]] and PLACE_CONF[u[3]] then conf_of[u[1]] = PLACE_CONF[u[3]] end
  end
  local out = {}
  for _, L in ipairs(world) do
    local c, cur, hops = conf_of[L.id], L, 0
    while not c and cur and cur.above and hops < 8 do
      cur, hops = by_id[cur.above], hops + 1
      c = cur and conf_of[cur.id]
    end
    if c and L.region and L.region >= 29 and L.region <= LAST_REGION and not out[L.region] then
      out[L.region] = c
    end
  end
  return out
end

-- the stub: 35 bytes of code, then the 128-entry u8 region -> runtime code table (0xff = keep)
-- (LAST_REGION 255: `cmp edx,0xff`, 38 bytes, the table 256 entries, still at 64)
--   0  mov ecx,[rax+0x300] ; shr ecx,0x19 ; and ecx,0xf     (the original read)
--  12  cmp edx,0x7f ; ja done                               (edx = the league's region)
--  17  lea rax,[tbl] ; movzx eax,byte [rax+rdx]
--  28  cmp al,0xff ; je done ; mov ecx,eax
--  34  done: ret
-- rax is dead at the site (the next use of it loads it again) and edx is only read.
local function install_icons(confeds)
  local n = 0
  for _ in pairs(confeds) do n = n + 1 end
  if n == 0 then
    log("fl26catlist: League Info icons -- no region of ours has a known confederation, left alone")
    return
  end
  local got = bin2hex(memory.read(ICONS_SITE, #ICONS_OLD / 2))
  if got ~= ICONS_OLD then
    log(string.format("fl26catlist: bytes at 0x%x are %s, expected %s -- League Info icons left alone",
                      ICONS_SITE, got, ICONS_OLD))
    return
  end
  got = bin2hex(memory.read(CONF_TABLE, 32))
  if got ~= CONF_TABLE_BYTES then
    log(string.format("fl26catlist: confederation table at 0x%x is %s -- League Info icons left alone", CONF_TABLE, got))
    return
  end
  local runtime = {}
  for f = 0, 7 do runtime[f] = memory.unpack("u32", memory.read(CONF_TABLE + f * 4, 4)) end
  local stub
  for _, pref in ipairs({ 0x15ea00000, 0x15fa00000, 0x161a00000, 0x162a00000, 0x171a00000 }) do
    local p = ffi.C.VirtualAlloc(ffi.cast("void*", pref), 0x1000, 0x3000, 0x40)  -- PAGE_EXECUTE_READWRITE
    if p ~= nil then stub = tonumber(ffi.cast("uint64_t", p)); break end
  end
  if not stub then log("fl26catlist: VirtualAlloc for the icons stub failed -- League Info icons left alone"); return end
  local into = rel32(ICONS_SITE + 5, stub)
  if not into then log("fl26catlist: icons stub out of call range -- League Info icons left alone"); return end
  local wide = LAST_REGION > 127
  local code = "\139\136\0\3\0\0" .. "\193\233\25" .. "\131\225\15"
            .. (wide and "\129\250\255\0\0\0" or "\131\250\127") .. "\119\17"
            .. "\72\141\5" .. u32le(wide and 37 or 40) .. "\15\182\4\16"
            .. "\60\255" .. "\116\2" .. "\137\193"
            .. "\195"
  assert(#code == (wide and 38 or 35))
  code = code .. string.rep("\204", 64 - #code)
  local tbl, set = {}, {}
  for r = 0, LAST_REGION do
    local c = r >= 29 and confeds[r]
    if c then set[#set + 1] = string.format("%d=%d", r, runtime[c]) end
    tbl[#tbl + 1] = string.char(c and runtime[c] or 255)
  end
  local body = code .. table.concat(tbl)
  ffi.copy(ffi.cast("void*", stub), body, #body)
  memory.write(ICONS_SITE, "\232" .. into .. "\15\31\128\0\0\0\0")   -- call stub ; nop dword [rax+0]
  log(string.format("fl26catlist: League Info icons -- stub at 0x%x, %d regions by confederation (%s)",
                    stub, #set, table.concat(set, " ")))
end

-- The League Info promotion line (mato 08.11.2026: "for the regional leagues it says promotion
-- off"). The same builder ends by reading the league's runtime links: +0x7c (the league above) and
-- +0x7e (the league below), and the panel prints "Promotion/Relegation On" with the two names
-- only when one of them leads to a live regulation, else "Off" and two empty names. Our tables
-- leave many leagues unlinked although their clubs go up and down (fl26chain moves them): every
-- group of a set but the first (`gset`; linking them all makes the game move clubs through each,
-- #98, leaguebuilder.group_sets) -- National 1 Groupe A, NB III Delkelet -- and the leagues next to
-- a split one (Prva liga Srbije under the SuperLiga, the Cypriot First Division's league below).
-- Two 8-byte runs become calls to stubs: the read of +0x7c at 0x140c6d0fd and the read of +0x7e
-- at 0x140c6d148. Each reads the link as before and, when it is 0xffff for a league whose world
-- line names one (above=, or a league whose above= is this one), hands the builder that id --
-- but only while some regulation still has a live +0x7c: a Master League with
-- Promotion/Relegation Off cuts every link (0x14126ff30), and then the page reads "Off" as the
-- game's own leagues do. Only the builder's register changes: the runtime links stay what they
-- were, so no club moves differently.
--   A  0  movzx r9d,word [r10+0x7c] ; cmp r9w,-1 ; jne done      (r10 = the league's record)
--     12  movzx eax,word [r10] ; cmp eax,0x3ff ; ja done         (its regulation id)
--     23  lea rcx,[tbl] ; movzx eax,word [rcx+rax*2] ; cmp ax,-1 ; je done
--     40  xor edx,edx ; loop: cmp edx,[r15+0xd0bcf4] ; jae done ; imul rcx,rdx,0x314 ; inc edx
--         cmp word [rcx+r15+0xc12f18],-1 ; je loop                (a record's +0x7c, the game's walk)
--     72  mov r9d,eax ; done: mov edx,r12d ; ret                  (the second replaced instruction)
--   B  the same on +0x7e into edx, r9d counting, ending in test r8d,r8d (the second replaced one)
-- rax, rcx and (in B) r9 are dead at the sites, loaded again before their next read.
local LINKS_MAX, LINKS_TBL = 1023, 96
local LINKS = {
  { 0x140c6d0fd, "450fb74a7c418bd4", 30,     -- movzx r9d,word [r10+0x7c] ; mov edx,r12d
    "450fb74a7c664183f9ff753f410fb7023dff0300007734488d0d",
    "0fb704416683f8ff742331d2413b97f4bcd00073184869ca14030000ffc2664283bc39182fc100ff74e24189c1418bd4c3" },
  { 0x140c6d148, "410fb7527e4585c0", 29,     -- movzx edx,word [r10+0x7e] ; test r8d,r8d
    "410fb7527e6683faff7540410fb7023dff0300007735488d0d",
    "0fb704416683f8ff74244531c9453b8ff4bcd00073184969c91403000041ffc1664283bc39182fc100ff74e189c24585c0c3" },
}
-- "Lower League" of a league in the middle (B420, 11.11.2026: the National League showed itself as its lower
-- league, and so did the 2. Liga, Nationale 1 ACFF ...). The builder knows two leagues only: when the league
-- has one above (0x140c6d12e) it writes that one as the higher league and the league ITSELF as the lower one
-- (mov ebx,r14d ; jmp 0x140c6d188) and never looks below. Those five bytes become a jump to a third stub:
--    0  mov ebx,r14d ; mov rax,[rbp-0x19] ; movzx edx,word [rax+0x7e] ; cmp dx,-1 ; jne have
--   17  movzx eax,word [rax] ; cmp eax,0x3ff ; ja done ; lea rcx,[tbl] ; movzx edx,word [rcx+rax*2]
--   38  cmp dx,-1 ; je done                                        (the world's league below, as stub B)
--   44  have: mov ebx,edx ; mov rcx,r15 ; mov rax,0x1414bb000 ; call rax     (the game's record of an id)
--   61  cmp [rax],bx ; mov ebx,r14d ; jne done ; mov ebx,[rax+0x80]           (found: its competition id)
--   75  done: mov rax,0x140c6d188 ; jmp rax
-- A league with none below keeps the game's answer (itself), as the game's own second divisions do. The
-- lookup is the game's own function, so the stub holds no table offset (fl26caps moves the table).
local LOWER_SITE, LOWER_BYTES, LOWER_BACK = 0x140c6d143, "418bdeeb40", 0x140c6d188
local LOOKUP, LOOKUP_BYTES = 0x1414bb000, "40534883ec20b8ffff0000440fb7c2488bd9663bd0"
local function u64le(v)
  local lo, hi = v % 0x100000000, math.floor(v / 0x100000000)
  return u32le(lo) .. u32le(hi)
end
local function hex2bin(h) return (h:gsub("%x%x", function(x) return string.char(tonumber(x, 16)) end)) end
-- LOOKUP is only called: fl26compcache (loaded before) puts its jump on that entry (`e9 rel32 90`,
-- the call then goes through its index of the regulation ids and answers the same record). Its
-- bytes are the game's, or such a jump with nop / int3 padding and the game's bytes after it
-- (beta4p 17.11.: "bytes at 0x1414bb000 are e95350b2fe90b8ff... -- lower league left alone").
local function called_ok(got, want)
  if got == want then return true end
  if got:sub(1, 2) ~= "e9" then return false end
  local k = 5
  while k < #want / 2 and (got:sub(2 * k + 1, 2 * k + 2) == "90" or got:sub(2 * k + 1, 2 * k + 2) == "cc") do k = k + 1 end
  return k < #want / 2 and got:sub(2 * k + 1) == want:sub(2 * k + 1)
end
m._called_ok = called_ok   -- for tools/test_hook_stack.py
local function install_lower(stub, down)
  for _, c in ipairs({ { LOWER_SITE, LOWER_BYTES }, { LOOKUP, LOOKUP_BYTES, true } }) do
    local got = bin2hex(memory.read(c[1], #c[2] / 2))
    if not (got == c[2] or (c[3] and called_ok(got, c[2]))) then
      log(string.format("fl26catlist: bytes at 0x%x are %s, expected %s -- League Info's lower league left alone",
                        c[1], got, c[2]))
      return
    end
  end
  local into = rel32(LOWER_SITE + 5, stub)
  if not into then log("fl26catlist: lower-league stub out of jump range -- League Info's lower league left alone"); return end
  local code = hex2bin("418bde488b45e70fb7507e6683faff751b0fb7003dff0300007730488d0d") .. u32le(LINKS_TBL - 34)
            .. hex2bin("0fb714416683faff741f8bda498bcf48b8") .. u64le(LOOKUP)
            .. hex2bin("ffd0663918418bde75068b988000000048b8") .. u64le(LOWER_BACK) .. hex2bin("ffe0")
  assert(#code == 87)
  code = code .. string.rep("\204", LINKS_TBL - #code)
  local tbl, n = {}, 0
  for r = 0, LINKS_MAX do
    local v = down[r] or 0xffff
    if down[r] then n = n + 1 end
    tbl[#tbl + 1] = string.char(v % 256, math.floor(v / 256))
  end
  local body = code .. table.concat(tbl)
  ffi.copy(ffi.cast("void*", stub), body, #body)
  memory.write(LOWER_SITE, "\233" .. into)   -- jmp stub
  log(string.format("fl26catlist: League Info lower league -- stub at 0x%x, a league with one above shows the one below it (%d known)",
                    stub, n))
end
local function install_links(world)
  local up, down, n = {}, {}, 0
  for _, L in ipairs(world or {}) do
    if L.above and L.id <= LINKS_MAX then
      up[L.id] = L.above; n = n + 1
      if L.above <= LINKS_MAX and not down[L.above] then down[L.above] = L.id end
    end
  end
  for _, lows in ipairs(world and world.gsets or {}) do    -- a set's first group is its linked one
    local f = lows[1]
    if f and f[2] <= LINKS_MAX then down[f[2]] = f[1] end
  end
  -- a split league (Apertura/Clausura, a regular season and its groups): the page is a phase's,
  -- and a phase has no links of its own -- it shows the links of its split league (mato 08.11.:
  -- "i dalje ne pise na svim ligama promocija i relegacija": Bundesliga, Parva Liga, Ligat ha'Al)
  for _, sp in ipairs(world and world.splits or {}) do
    local t = sp[1]
    for _, r in ipairs(sp[2]) do
      if r <= LINKS_MAX then
        if up[t] and not up[r] then up[r] = up[t]; n = n + 1 end
        if down[t] and not down[r] then down[r] = down[t] end
      end
    end
  end
  if n == 0 and next(down) == nil then return end
  for _, s in ipairs(LINKS) do
    local got = bin2hex(memory.read(s[1], #s[2] / 2))
    if got ~= s[2] then
      log(string.format("fl26catlist: bytes at 0x%x are %s, expected %s -- League Info promotion left alone",
                        s[1], got, s[2]))
      return
    end
  end
  local stub
  for _, pref in ipairs({ 0x15eb00000, 0x15fb00000, 0x161b00000, 0x162b00000, 0x171b00000 }) do
    local p = ffi.C.VirtualAlloc(ffi.cast("void*", pref), 0x3000, 0x3000, 0x40)  -- PAGE_EXECUTE_READWRITE
    if p ~= nil then stub = tonumber(ffi.cast("uint64_t", p)); break end
  end
  if not stub then log("fl26catlist: VirtualAlloc for the links stubs failed -- League Info promotion left alone"); return end
  local into = {}
  for k, s in ipairs(LINKS) do
    into[k] = rel32(s[1] + 5, stub + 0x1000 * (k - 1))
    if not into[k] then log("fl26catlist: links stub out of call range -- League Info promotion left alone"); return end
  end
  for k, s in ipairs(LINKS) do
    local code = hex2bin(s[4]) .. u32le(LINKS_TBL - s[3]) .. hex2bin(s[5])
    assert(#code == 79)
    code = code .. string.rep("\204", LINKS_TBL - #code)
    local map, tbl = k == 1 and up or down, {}
    for r = 0, LINKS_MAX do
      local v = map[r] or 0xffff
      tbl[#tbl + 1] = string.char(v % 256, math.floor(v / 256))
    end
    local body = code .. table.concat(tbl)
    ffi.copy(ffi.cast("void*", stub + 0x1000 * (k - 1)), body, #body)
  end
  for k, s in ipairs(LINKS) do
    memory.write(s[1], "\232" .. into[k] .. "\144\144\144")   -- call stub ; three nops
  end
  local nd = 0
  for _ in pairs(down) do nd = nd + 1 end
  log(string.format("fl26catlist: League Info promotion -- stubs at 0x%x, %d leagues with one above, %d with one below",
                    stub, n, nd))
  install_lower(stub + 0x2000, down)
end

local ORDER = nil   -- the world file's `order` line: region ids in the order the lists show them

function m.init(ctx)
  local world = read_world(ctx)
  ORDER = world and world.order
  local top = 0
  for _, L in ipairs(world or {}) do if L.region and L.region > top then top = L.region end end
  if top > LAST_REGION then
    LAST_REGION = WIDE_REGION
    local wide = bin2hex(memory.read(PARSER, #PARSER_WIDE / 2)) == PARSER_WIDE
    log(string.format("fl26catlist: the world has region %d -- regions up to %d%s", top, LAST_REGION,
                      wide and "" or " (WARNING: the game's region parser is not the regions step's: it reads 128..255 as 0..127)"))
  end
  if world then
    COUNTRY = world_countries(world)
    local n = 0
    for _ in pairs(COUNTRY) do n = n + 1 end
    log(string.format("fl26catlist: world file -- %d leagues, %d countries of their own", #world, n))
  end
  if ffi == nil then log("fl26catlist: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[ void* VirtualAlloc(void*, size_t, uint32_t, uint32_t); ]])
  install_icons(world and world_confeds(world) or {})
  install_links(world)
  if not (check_sites(LEAS) and check_sites(COUNT_SITES)) then return end

  local ids, have = {}, {}
  -- The Select Team list is sorted by the position of a league's region in this list before
  -- anything else (0x140eadae0), so the order line is what puts a new country among the
  -- others of its continent instead of after all of them. Every shipped region still goes in.
  for _, id in ipairs(ORDER or {}) do
    if id >= 1 and id <= LAST_REGION and not have[id] then ids[#ids + 1] = id; have[id] = true end
  end
  for i = 0, NSHIPPED - 1 do
    local id = memory.unpack("u32", memory.read(SHIPPED + i * 4, 4))
    if not have[id] then ids[#ids + 1] = id; have[id] = true end
  end
  for id = 1, LAST_REGION do
    if not have[id] then ids[#ids + 1] = id; have[id] = true end
  end
  local n = #ids
  if n > 255 then log("fl26catlist: too many regions for an 8-bit count -- aborting"); return end
  local parts = {}
  for i, id in ipairs(ids) do parts[i] = u32le(id) end
  local body = table.concat(parts)

  local newbase
  for _, pref in ipairs({ 0x15e000000, 0x15f000000, 0x161000000, 0x171000000, 0x181000000 }) do
    local p = ffi.C.VirtualAlloc(ffi.cast("void*", pref), #body, 0x3000, 0x04)  -- MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE
    if p ~= nil then newbase = tonumber(ffi.cast("uint64_t", p)); break end
  end
  if not newbase then log("fl26catlist: VirtualAlloc failed at every preferred address -- aborting"); return end
  ffi.copy(ffi.cast("void*", newbase), body, #body)

  for _, s in ipairs(LEAS) do
    local disp = newbase - (s[1] + 7)
    if disp >= 0x80000000 or disp < -0x80000000 then log("fl26catlist: copy out of rip range -- aborting"); return end
  end
  for _, s in ipairs(LEAS) do
    local disp = newbase - (s[1] + 7)
    if disp < 0 then disp = disp + 0x100000000 end
    memory.write(s[1] + 3, u32le(disp))
  end
  for _, s in ipairs(COUNT_SITES) do
    if n > 127 then memory.write(s[1], s[4] .. string.char(n))     -- cmp r8, n: unsigned, up to 255
    else memory.write(s[1] + s[3], string.char(n)) end
  end

  log(string.format("fl26catlist: category list copied to 0x%x, %d regions (%d shipped + %d ours)%s",
                    newbase, n, NSHIPPED, n - NSHIPPED, ORDER and ", in the world file's order" or ""))
  install_country()
end

return m
