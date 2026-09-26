--[[
fl26editlist -- show ALL our leagues in Edit mode's team lists (Edit > Teams, Edit > Players >
Edit Player > Select Team, Managers, Transfer ... every Edit screen that lists clubs by league).

Why: those lists are not built from the regulation data, nor from the Select Team table that
fl26comptab widens. Every Edit team list asks one function for its competition SLOTS,
0x141ee68f0, and that function is thirty push_backs of slot numbers written into its own code
(7, 50, 8, 52, ... 30, 70). The caller then adds 0..6 and turns each slot into a heading with
the clubs of that slot (0x140c93240 -> 0x140c93780, which skips a slot already listed and a
slot without clubs). So a league of ours appears only when it sits on one of those slots:
England D3 (69), Romania D2 (73), Sweden D1 (84), Mexico D1 (22) and Italy D3..D5 (slots 6/5/4)
-- which is what the screen showed. Measured 2026-09-26 in game with a probe on 0x140c93780: the
Teams screen asked exactly 39 slots, all through 0x140c93240 called from 0x140bfcb10, fed by
0x141ee70a0 -> 0x141ee68f0. Eleven call sites use 0x141ee68f0 (seven through 0x141ee70a0).

(An earlier version hooked 0x140d1d010, which has a similar hard-coded list of thirty slots --
but that one belongs to OnlineMyClubTeamSelect, not to Edit; it never ran on the Edit screens.)

What this does, at boot, runtime only: the epilogue of 0x141ee68f0 (0x141ee7086, `mov rbx,
[rsp+0x38]`, five bytes nothing jumps into) becomes a jump to a stub that push_backs every slot
of ours the list lacks -- with the game's own push_back, 0x14047be40(vector, &value), the one the
function itself uses -- then runs the replaced instruction and jumps back. 0x140c934f0 sorts the
headings by the display order 0x140ead990, which ranks most of our slots after the game's own,
so they come last -- and the "Other" heading (pseudo-slot 257, six special teams) now sits in
front of that last block instead of at the very end. Nothing is removed and no shipped slot
changes. The hook bytes, the first of the thirty slot moves and the push_back call target are
checked first; a different build is left alone.

The slots are not written here: at boot this reads the competition table fl26comptab has just
put in place (through the lookup-by-id lea it re-points, 0x1414fdbda, and the row count getter
0x1414fe1e0) and takes the slot of every regulation id in OUR_IDS, the same list fl26comptab
works from. Slots the list has already and the no-slot sentinel 123 are left out. If fl26comptab
did not run, the shipped table is read and whatever of ours has a slot there is still added.

Requires sider.ini: luajit.ext.enabled = 1 (global ffi). Load after fl26comptab.lua.
--]]

local m = {}

-- every regulation id our world uses; keep in step with OUR_IDS in fl26comptab.lua.
-- These are OUR test world's leagues; put your own ids here (the same list as in fl26comptab).
local OUR_IDS = {
  11, 49, 60, 61, 62, 74, 76, 93, 94, 96, 98, 100, 109, 110, 111, 112, 113, 114, 121,
  138, 139, 140, 143, 144, 145, 146, 170, 171, 173, 174, 176, 178, 179, 180, 181, 182,
  183, 184, 185, 190,
}
-- what the Edit lists hold without us, in the order the Teams screen asked for them (probe,
-- 2026-09-26): the thirty slots of 0x141ee68f0, then 0..6 added by its caller
local LISTED = {
  7, 50, 8, 52, 9, 53, 10, 11, 51, 12, 88, 91, 94, 96, 114, 105, 16, 69, 13, 122, 14, 15, 99, 17,
  84, 73, 102, 119, 18, 22, 30, 70,  0, 1, 2, 3, 4, 5, 6,
}
local NO_SLOT = 123

local TABLE_LEA  = 0x1414fdbda    -- lea r12,[table] in the lookup by id (re-pointed by fl26comptab)
local COUNT_IMM  = 0x1414fe1e1    -- imm32 of mov eax, count in the row count getter
local STRIDE     = 0x108

local HOOK      = 0x141ee7086     -- mov rbx, [rsp+0x38]  (epilogue of 0x141ee68f0)
local HOOK_OLD  = "488b5c2438"
local BACK      = 0x141ee708b
local LIST0     = 0x141ee690d     -- mov dword [rbp+0x10], 7  (the first of the thirty)
local LIST0_OLD = "c7451007000000"
local PUSH_CALL = 0x141ee7081     -- call 0x14047be40, the function's own last push_back
local PUSH      = 0x14047be40     -- push_back(vector*, const uint32_t*)

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

-- The page: +0x20 the stub, +0x100 the slots (u32, 0xffffffff ends the list).
local function build(C, slots)
  local A, T = C + 0x20, C + 0x100
  -- rbx is the vector, rdi is free (the epilogue restores it), rsp is 16-aligned with the
  -- function's own 0x20 of shadow space below it
  local s = b(0x48, 0x8d, 0x3d) .. u32(T - (A + 7))    --  0 lea rdi, [rip->slots]
         .. b(0x83, 0x3f, 0xff)                         --  7 loop: cmp dword [rdi], -1
         .. b(0x74, 0x18)                               -- 10 je done (+0x18 -> 36)
         .. b(0x48, 0x89, 0xfa)                         -- 12 mov rdx, rdi
         .. b(0x48, 0x89, 0xd9)                         -- 15 mov rcx, rbx
         .. b(0x48, 0xb8) .. u64(PUSH)                  -- 18 mov rax, 0x14047be40
         .. b(0xff, 0xd0)                               -- 28 call rax
         .. b(0x48, 0x83, 0xc7, 0x04)                   -- 30 add rdi, 4
         .. b(0xeb, 0xe3)                               -- 34 jmp loop (-0x1d -> 7)
  -- the two jumps above are counted from these offsets; keep them in step with any edit
  assert(#s == 36)
  s = s .. b(0x48, 0x8b, 0x5c, 0x24, 0x38)              -- 36 done: mov rbx, [rsp+0x38]
  local back = rel(A + #s + 5, BACK)
  if not back then return nil end
  s = s .. b(0xe9) .. back                              -- 41 jmp 0x141ee708b

  local t = {}
  for _, v in ipairs(slots) do t[#t + 1] = u32(v) end
  t[#t + 1] = u32(0xffffffff)

  local body = string.rep("\0", 0x20) .. s
  body = body .. string.rep("\0", 0x100 - #body) .. table.concat(t)
  return body
end

-- the slots of our leagues that the list does not show, in OUR_IDS order, or nil on a table
-- that does not look like the competition table
function m.slots()
  local lea = memory.read(TABLE_LEA, 7)
  if hex(lea:sub(1, 3)) ~= "4c8d25" then
    log("fl26editlist: the table lea at 0x" .. string.format("%x", TABLE_LEA) .. " is not lea r12 -- nothing written")
    return nil
  end
  local base = TABLE_LEA + 7 + memory.unpack("i32", lea:sub(4, 7))
  local n = memory.unpack("u32", memory.read(COUNT_IMM, 4))
  if n < 0xa5 or n > 0x400 then
    log(string.format("fl26editlist: row count %d is not believable -- nothing written", n))
    return nil
  end
  local rows = memory.read(base, n * STRIDE)
  local slot_of = {}
  for i = 0, n - 1 do
    local id = memory.unpack("u32", rows:sub(i * STRIDE + 1, i * STRIDE + 4))
    if slot_of[id] == nil then
      slot_of[id] = memory.unpack("u32", rows:sub(i * STRIDE + 5, i * STRIDE + 8))
    end
  end
  local skip = { [NO_SLOT] = true }
  for _, v in ipairs(LISTED) do skip[v] = true end
  local out, missing = {}, {}
  for _, id in ipairs(OUR_IDS) do
    local slot = slot_of[id]
    if slot == nil then
      missing[#missing + 1] = tostring(id)
    elseif slot < NO_SLOT and not skip[slot] then
      skip[slot] = true
      out[#out + 1] = slot
    end
  end
  if #missing > 0 then
    log("fl26editlist: no row for id(s) " .. table.concat(missing, " ") .. " (fl26comptab not loaded first?)")
  end
  return out
end

function m.init(ctx)
  local call = memory.read(PUSH_CALL, 5)
  if call:byte(1) ~= 0xe8 or PUSH_CALL + 5 + memory.unpack("i32", call:sub(2, 5)) ~= PUSH then
    log(string.format("fl26editlist: 0x%x does not call push_back at 0x%x -- nothing written", PUSH_CALL, PUSH))
    return
  end
  for _, h in ipairs({ { HOOK, HOOK_OLD }, { LIST0, LIST0_OLD } }) do
    local got = hex(memory.read(h[1], #h[2] / 2))
    if got ~= h[2] then
      log(string.format("fl26editlist: bytes at 0x%x are %s, expected %s -- nothing written",
                        h[1], got, h[2]))
      return
    end
  end
  local slots = m.slots()
  if not slots then return end
  if #slots == 0 then
    log("fl26editlist: every league of ours is listed already -- nothing written")
    return
  end
  if ffi == nil then
    log("fl26editlist: global ffi is nil (set luajit.ext.enabled = 1) -- nothing written")
    return
  end
  ffi.cdef([[ void* fl26editlist_VirtualAlloc(void*, size_t, uint32_t, uint32_t)
               __asm__("VirtualAlloc"); ]])

  local C, body
  for _, pref in ipairs({ 0x15e800000, 0x15f800000, 0x161800000, 0x162800000, 0x171800000 }) do
    local p = ffi.C.fl26editlist_VirtualAlloc(ffi.cast("void*", pref), 0x1000, 0x3000, 0x40)  -- RWX
    if p ~= nil then
      C = tonumber(ffi.cast("uint64_t", p))
      body = build(C, slots)
      if body then break end
    end
  end
  if not body then
    log("fl26editlist: no page within reach of the code -- nothing written")
    return
  end
  ffi.copy(ffi.cast("void*", C), body, #body)

  local j = b(0xe9) .. rel(HOOK + 5, C + 0x20)
  memory.write(HOOK, j)
  if memory.read(HOOK, #j) ~= j then
    log("fl26editlist: WRITE FAILED at the hook -- quit and report")
    return
  end
  log(string.format("fl26editlist: %d more league headings in the Edit team lists, slots %s (stub at 0x%x)",
                    #slots, table.concat(slots, " "), C))
end

return m
