--[[
fl26slotnames -- stop seven of our leagues from borrowing a shipped section name.

Measured in a running game on 2026-09-21. The Select Team list showed "Other European
Leagues" where Qatar D1 should be, "Other Clubs (Africa)" where France D3 should be,
"Classic Teams" for the two lower Italian divisions, and so on -- while Sweden D1, on a
neighbouring row of the same table, read correctly. Reading the live competition parameter
table settled why: every one of our appended rows carries 0xffffffff in the name field
(+0x38), so the name cannot be coming from the row. It comes from the slot.

0x140ea08e0 is the helper that turns a competition slot into a display name. It is a plain
switch on the slot: values above 0x4b fall straight to the default, and of the 76 below it
only twelve have a case of their own --

     0 Europe          1 Africa      2 North & Central America   3 South America
     4 Asia-Oceania    5 Classic Teams   6 Classic Teams
    69 Other European Leagues      70 Other Clubs (Asia)      71 Other
    73 Other Latin American Teams  75 Other Clubs (Africa)

-- and every other slot takes the default, which leaves the string empty. The caller then
checks for the empty string (0x140ea0a0e) and falls back to the competition's own name.
That fallback is the whole reason Sweden D1 on slot 84 reads right, and it is what this
module hands the other seven.

The switch is a two-level jump table: a byte per slot at 0x140ea0b3c picks one of twelve
case offsets at 0x140ea0b0c, and case 11 is the default. So blanking a slot's name is one
byte -- point its entry at case 11.

Seven slots are patched: 4, 5, 6, 69, 71, 73 and 75. Slots 0, 1, 2 and 3 are left alone
(nothing of ours is on them), and so is 70, which still carries the two shipped competitions
it always did.

2026-09-25, after GitHub issue #2: freeing a slot is only right when a competition is
actually on it. The same slots also carry shipped categories (Classic Teams, Asian national
teams, other European and Latin American clubs), and a world that does not build the league
this module expected on a slot was left with a blank heading. So a freed slot now falls back
twice: first to the name of a live competition on it, as before, and when there is none,
back to the heading the slot always had. Two small hooks in 0x140ea08e0 do that:

  0x140ea0a37  remember the slot just before the fallback looks for a competition on it;
  0x140ea0af7  on the way out, if the name is still empty and the slot is one of these
               seven, ask the game for the slot's original text (0x1414969e0 with the text
               id its own case uses).

The two stubs live in a page this module allocates within rel32 reach of the code, so no
shared code cave is involved.

What this does NOT fix: rows of ours that were inherited from a shipped competition and
still hold that competition's label in +0x38. Those are a row, not a slot, and fl26comptab
clears them.

Load order does not matter; this module touches no address any other module touches.
Needs luajit.ext.enabled = 1 in sider.ini (the global ffi), like fl26comptab.

Install:
  1. copy to <game>\SiderAddons\modules\fl26slotnames.lua
  2. sider.ini, in the [modules] list:   lua.module = "fl26slotnames.lua"
--]]

local m = {}

local BYTE_TABLE = 0x140ea0b3c   -- one byte per slot, 0x4c entries, value = case index
local DEFAULT    = 11            -- the case that leaves the name empty

-- {slot, the case byte it must currently hold, what that case says today, its text id}
local SLOTS = {
  {  4, 4,  "Asia-Oceania",               0x660081 },
  {  5, 5,  "Classic Teams",              0x6600f7 },
  {  6, 5,  "Classic Teams",              0x6600f7 },
  { 69, 6,  "Other European Leagues",     0x6600d2 },
  { 71, 8,  "Other",                      0x660093 },
  { 73, 9,  "Other Latin American Teams", 0x6600d3 },
  { 75, 10, "Other Clubs (Africa)",       0x66010f },
}

local HOOK_SLOT     = 0x140ea0a37        -- mov ecx, ebp; call 0x1414ce170 (slot -> its competitions)
local HOOK_SLOT_OLD = "8bcde832d76200"
local HOOK_OUT      = 0x140ea0af7        -- mov rbx, [rsp+0x50] (the epilogue)
local HOOK_OUT_OLD  = "488b5c2450"
local SLOTREGS      = 0x1414ce170
local SETTEXT       = 0x1414969e0

local function hex(s) return (s:gsub(".", function(c) return string.format("%02x", c:byte()) end)) end
local function u32(v)
  v = v % 0x100000000
  return string.char(v % 256, math.floor(v / 256) % 256, math.floor(v / 65536) % 256,
                     math.floor(v / 16777216) % 256)
end
local function u64(v) return u32(v % 0x100000000) .. u32(math.floor(v / 0x100000000)) end
local function rel(next_ip, to)
  local d = to - next_ip
  if d >= 0x80000000 or d < -0x80000000 then return nil end
  return u32(d)
end
local function b(...) return string.char(...) end

-- The page: +0x00 the remembered slot, +0x20 stub A, +0x60 stub B, +0x100 slot -> text id.
-- Returns nil when C is too far from the code for a rel32 jump.
local function build(C)
  local A, B, T = C + 0x20, C + 0x60, C + 0x100
  local a = b(0x89, 0x2d) .. u32(C - (A + 6))          -- mov [rip->slot], ebp
         .. b(0x89, 0xe9)                               -- mov ecx, ebp
         .. b(0x48, 0xb8) .. u64(SLOTREGS)              -- mov rax, 0x1414ce170
         .. b(0xff, 0xd0)                               -- call rax
  local back = rel(A + #a + 5, HOOK_SLOT + 7)
  if not back then return nil end
  a = a .. b(0xe9) .. back                              -- jmp 0x140ea0a3e

  local s = b(0x48, 0x83, 0x7f, 0x10, 0x00)            --  0 cmp qword [rdi+0x10], 0
         .. b(0x75, 0x2b)                               --  5 jne done
         .. b(0x8b, 0x05) .. u32(C - (B + 13))          --  7 mov eax, [rip->slot]
         .. b(0x83, 0xf8, 0x4b)                         -- 13 cmp eax, 0x4b
         .. b(0x77, 0x20)                               -- 16 ja done
         .. b(0x48, 0x8d, 0x0d) .. u32(T - (B + 25))    -- 18 lea rcx, [rip->table]
         .. b(0x8b, 0x14, 0x81)                         -- 25 mov edx, [rcx+rax*4]
         .. b(0x85, 0xd2)                               -- 28 test edx, edx
         .. b(0x74, 0x12)                               -- 30 je done
         .. b(0x48, 0x89, 0xf9)                         -- 32 mov rcx, rdi
         .. b(0x48, 0xb8) .. u64(SETTEXT)               -- 35 mov rax, 0x1414969e0
         .. b(0xff, 0xd0)                               -- 45 call rax
         .. b(0x48, 0x89, 0xf8)                         -- 47 mov rax, rdi
         .. b(0x48, 0x8b, 0x5c, 0x24, 0x50)             -- 50 done: mov rbx, [rsp+0x50]
  back = rel(B + #s + 5, HOOK_OUT + 5)
  if not back then return nil end
  s = s .. b(0xe9) .. back                              -- 55 jmp 0x140ea0afc

  local ids = {}
  for i = 0, 0x4b do ids[i] = 0 end
  for _, e in ipairs(SLOTS) do ids[e[1]] = e[4] end
  local t = {}
  for i = 0, 0x4b do t[#t + 1] = u32(ids[i]) end

  local body = u32(0xffffffff) .. string.rep("\0", 0x1c) .. a
  body = body .. string.rep("\0", 0x60 - #body) .. s
  body = body .. string.rep("\0", 0x100 - #body) .. table.concat(t)
  return body
end

function m.init(ctx)
  -- verify every byte before writing any of them: a build whose switch is laid out
  -- differently must be left completely alone, not half-patched.
  for _, s in ipairs(SLOTS) do
    local va = BYTE_TABLE + s[1]
    local got = memory.read(va, 1):byte()
    if got ~= s[2] then
      log(string.format("fl26slotnames: slot %d at 0x%x is case %d, expected %d -- nothing "
                        .. "written. This is a different build than the one the switch was "
                        .. "read from.", s[1], va, got, s[2]))
      return
    end
  end
  for _, h in ipairs({ { HOOK_SLOT, HOOK_SLOT_OLD }, { HOOK_OUT, HOOK_OUT_OLD } }) do
    local got = hex(memory.read(h[1], #h[2] / 2))
    if got ~= h[2] then
      log(string.format("fl26slotnames: bytes at 0x%x are %s, expected %s -- nothing written",
                        h[1], got, h[2]))
      return
    end
  end
  if ffi == nil then
    log("fl26slotnames: global ffi is nil (set luajit.ext.enabled = 1) -- nothing written")
    return
  end
  -- declared under a name of our own (the symbol is still kernel32's VirtualAlloc), so it can
  -- never clash with fl26comptab's declaration; sider's module env has no pcall to catch that
  ffi.cdef([[ void* fl26slotnames_VirtualAlloc(void*, size_t, uint32_t, uint32_t)
               __asm__("VirtualAlloc"); ]])

  -- a page of our own for the two stubs, near enough for a rel32 jump both ways
  local C, body
  for _, pref in ipairs({ 0x15e000000, 0x15f000000, 0x161000000, 0x162000000, 0x171000000 }) do
    local p = ffi.C.fl26slotnames_VirtualAlloc(ffi.cast("void*", pref), 0x1000, 0x3000, 0x40)  -- RWX
    if p ~= nil then
      C = tonumber(ffi.cast("uint64_t", p))
      body = build(C)
      if body then break end
    end
  end
  if not body then
    log("fl26slotnames: no page within reach of the code -- nothing written")
    return
  end
  ffi.copy(ffi.cast("void*", C), body, #body)

  -- the stubs exist; now the jumps into them, then the slots
  local ja = b(0xe9) .. rel(HOOK_SLOT + 5, C + 0x20) .. b(0x90, 0x90)
  local jb = b(0xe9) .. rel(HOOK_OUT + 5, C + 0x60)
  memory.write(HOOK_SLOT, ja)
  memory.write(HOOK_OUT, jb)
  if memory.read(HOOK_SLOT, #ja) ~= ja or memory.read(HOOK_OUT, #jb) ~= jb then
    log("fl26slotnames: WRITE FAILED at the hooks -- quit and report")
    return
  end
  log(string.format("fl26slotnames: headings fall back to the original text (stubs at 0x%x)", C))

  for _, s in ipairs(SLOTS) do
    local va = BYTE_TABLE + s[1]
    memory.write(va, string.char(DEFAULT))
    if memory.read(va, 1):byte() ~= DEFAULT then
      log(string.format("fl26slotnames: WRITE FAILED at 0x%x (slot %d)", va, s[1]))
      return
    end
    log(string.format("fl26slotnames: slot %d is named after its league, or \"%s\" if it has "
                      .. "none", s[1], s[3]))
  end
  log(string.format("fl26slotnames: %d slots freed", #SLOTS))
end

return m
