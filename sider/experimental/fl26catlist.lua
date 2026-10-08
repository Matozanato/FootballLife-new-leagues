--[[
fl26catlist -- show OUR countries in Master League -> Database -> Competition Info.

Why: the category list on that screen is built by 0x140ead9f0 from a static list of 28
region ids compiled into FL_2026.exe (.rdata 0x1427d5760: 1,26,8,12,2,...,25 -- the display
order). For every region in that list it looks for a live regulation whose region
(+0x30c bits 7..12) matches, and adds the region if one exists. Our leagues sit in regions
30..60 (fl26reg64 widened the field to 64), none of which is in the list, so a league in an
existing country shows up (France D3..D5 under France) and a league in a country of its own
does not appear at all.

The same list orders the categories in the sort helper 0x140eadae0. The only other thing
keyed on the region there is the category picture (0x140acd478, 24 entries, stride 16); a
region it does not know keeps the default 'compeCategory-interClub' image, so a new
country gets a generic picture, not a crash.

What this does, at boot, runtime only: copies the 28 shipped ids into a private table,
appends 29..63 (only regions with a live regulation get listed, so the unused ones cost
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
region 29..63 that has an entry in a 64-byte table, returns that region's code instead. The
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
]]
local m = {}

local SHIPPED = 0x1427d5760
local NSHIPPED = 28
local LAST_REGION = 63

-- {va, expected bytes (hex)}
local LEAS = {
  { 0x140eada38, "4c8d25217d9201" },   -- lea r12,[list]  (builder)
  { 0x140eadb9a, "488d05bf7b9201" },   -- lea rax,[list]  (sort helper)
}
-- {va, expected bytes, offset of the imm8}
local COUNT_SITES = {
  { 0x140eadab6, "83fb1c", 2 },        -- cmp ebx, 0x1c  (builder)
  { 0x140eadbb4, "83f91c", 2 },        -- cmp ecx, 0x1c  (sort helper)
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

-- the stub: 80 bytes of code, then two 64-entry u16 region -> country tables, COUNTRY at 80
-- and LABEL at 208
--   0  cmp ecx,0x3f ; ja orig          5  mov eax,ecx
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
  local back = rel32(stub + 73, COUNTRY_FN + 7)
  local into = rel32(COUNTRY_FN + 5, stub)
  if not (back and into) then log("fl26catlist: country stub out of jump range -- names left alone"); return end
  local code = "\131\249\63" .. "\119\56" .. "\137\200"
            .. "\72\186" .. u32le(LABEL_RET % 0x100000000) .. u32le(math.floor(LABEL_RET / 0x100000000))
            .. "\72\57\20\36" .. "\117\20"
            .. "\72\141\21" .. u32le(178) .. "\15\183\20\66" .. "\102\131\250\255" .. "\116\3"
            .. "\137\208" .. "\195"
            .. "\72\141\21" .. u32le(30) .. "\15\183\4\66" .. "\102\131\248\255" .. "\116\1" .. "\195"
            .. "\64\85\72\141\108\36\169" .. "\233" .. back .. string.rep("\204", 7)
  assert(#code == 80)
  local tbl, lbl, named = {}, {}, 0
  for r = 0, 63 do
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

-- region 29..63 -> confederation as Competition.bin / Country.bin write it (2..7), from the world
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

-- the stub: 35 bytes of code, then the 64-entry u8 region -> runtime code table (0xff = keep)
--   0  mov ecx,[rax+0x300] ; shr ecx,0x19 ; and ecx,0xf     (the original read)
--  12  cmp edx,0x3f ; ja done                               (edx = the league's region)
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
  local code = "\139\136\0\3\0\0" .. "\193\233\25" .. "\131\225\15"
            .. "\131\250\63" .. "\119\17"
            .. "\72\141\5" .. u32le(40) .. "\15\182\4\16"
            .. "\60\255" .. "\116\2" .. "\137\193"
            .. "\195"
  assert(#code == 35)
  code = code .. string.rep("\204", 64 - #code)
  local tbl, set = {}, {}
  for r = 0, 63 do
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

local ORDER = nil   -- the world file's `order` line: region ids in the order the lists show them

function m.init(ctx)
  local world = read_world(ctx)
  ORDER = world and world.order
  if world then
    COUNTRY = world_countries(world)
    local n = 0
    for _ in pairs(COUNTRY) do n = n + 1 end
    log(string.format("fl26catlist: world file -- %d leagues, %d countries of their own", #world, n))
  end
  if ffi == nil then log("fl26catlist: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[ void* VirtualAlloc(void*, size_t, uint32_t, uint32_t); ]])
  install_icons(world and world_confeds(world) or {})
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
  if n > 127 then log("fl26catlist: too many regions for an imm8 count -- aborting"); return end
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
  for _, s in ipairs(COUNT_SITES) do memory.write(s[1] + s[3], string.char(n)) end

  log(string.format("fl26catlist: category list copied to 0x%x, %d regions (%d shipped + %d ours)%s",
                    newbase, n, NSHIPPED, n - NSHIPPED, ORDER and ", in the world file's order" or ""))
  install_country()
end

return m
