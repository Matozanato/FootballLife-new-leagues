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
  [11] = 200,  -- Croatia
  [30] = 227,  -- Poland
  [31] = 202,  -- Czech Republic
  [32] = 234,  -- Slovakia
  [33] = 194,  -- Austria
  [34] = 229,  -- Romania
  [35] = 199,  -- Bulgaria
  [36] = 238,  -- Switzerland
  [37] = 239,  -- Ukraine
  [38] = 226,  -- Norway
  [39] = 237,  -- Sweden
  [40] = 214,  -- Ireland
  [41] = 221,  -- North Macedonia
  [42] = 304,  -- Montenegro
  [43] = 191,  -- Albania
  [44] = 207,  -- Finland
  [45] = 152,  -- Uruguay
  [46] = 150,  -- Paraguay
  [47] = 151,  -- Peru
  [48] = 149,  -- Ecuador
  [49] = 145,  -- Bolivia
  [50] = 153,  -- Venezuela
  [51] = 124,  -- Mexico
  [52] = 16,   -- Republic of Korea
  [53] = 162,  -- Australia
  [56] = 11,   -- Iran
  [58] = 235,  -- Slovenia
  [59] = 303,  -- Serbia
  [60] = 198,  -- Bosnia and Herzegovina
}
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

-- the stub: 40 bytes of code, then the 64-entry u16 region -> country table
--   0  cmp ecx,0x3f ; ja orig          5  mov eax,ecx ; lea rdx,[tbl]
--  14  movzx eax,word [rdx+rax*2]      18  cmp ax,-1 ; je orig ; ret
--  25  orig: push rbp ; lea rbp,[rsp-0x57] ; jmp COUNTRY_FN+7
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
  local back = rel32(stub + 37, COUNTRY_FN + 7)
  local into = rel32(COUNTRY_FN + 5, stub)
  if not (back and into) then log("fl26catlist: country stub out of jump range -- names left alone"); return end
  local code = "\131\249\63" .. "\119\20" .. "\137\200" .. "\72\141\21" .. u32le(26)
            .. "\15\183\4\66" .. "\102\131\248\255" .. "\116\1" .. "\195"
            .. "\64\85\72\141\108\36\169" .. "\233" .. back .. "\204\204\204"
  assert(#code == 40)
  local tbl, named = {}, 0
  for r = 0, 63 do
    local c = COUNTRY[r] or 0xffff
    if COUNTRY[r] then named = named + 1 end
    tbl[#tbl + 1] = string.char(c % 256, math.floor(c / 256))
  end
  local body = code .. table.concat(tbl)
  ffi.copy(ffi.cast("void*", stub), body, #body)
  memory.write(COUNTRY_FN, "\233" .. into .. "\144\144")
  log(string.format("fl26catlist: country names -- stub at 0x%x, %d regions named", stub, named))
end

function m.init(ctx)
  if ffi == nil then log("fl26catlist: global ffi is nil -- set luajit.ext.enabled = 1"); return end
  ffi.cdef([[ void* VirtualAlloc(void*, size_t, uint32_t, uint32_t); ]])
  if not (check_sites(LEAS) and check_sites(COUNT_SITES)) then return end

  local ids, have = {}, {}
  for i = 0, NSHIPPED - 1 do
    local id = memory.unpack("u32", memory.read(SHIPPED + i * 4, 4))
    ids[#ids + 1] = id; have[id] = true
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

  log(string.format("fl26catlist: category list copied to 0x%x, %d regions (%d shipped + %d ours)",
                    newbase, n, NSHIPPED, n - NSHIPPED))
  install_country()
end

return m
