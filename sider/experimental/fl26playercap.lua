--[[
fl26playercap -- the 30,000-entry player index stops filling instead of writing past its table.

Why: a world with more than ~65,000 players crashed while the game built one of its player
indexes.  Measured 2026-10-24 with Frida (76): the caller at 0x14F4966 inserts player indices
one by one into a structure whose storage is 30,000 dwords and whose count lives at +0x1d510,
and the insert 0x1414d6940 starts by reading that count and comparing it with 0x7530:

    0x1414d6945  mov  r13d, [rcx + 0x1d510]     ; how many entries it holds
    0x1414d6954  cmp  r13d, 0x7530              ; 30000, the table's size
    0x1414d695b  je   0x1414d6b06               ; full -> pop/pop/pop/ret, it does nothing

`je` only catches exactly 30,000.  A world with more players reached 30,001 and the insert
wrote past the table, over the bucket starts/counts that follow it, and the next call read a
garbage count (one dump: r13 = 0x13FF60037) and walked to -1.  This is the "menu-mode object
with a 30,001-dword table ... still not grown" that research-findings.md lists as residual
risk.

What this does: one byte at 0x1414d695c, 0x84 (je) -> 0x83 (jae), so the function returns as
soon as the table is full, at 30,000 or past it.  The players beyond the table's capacity are
simply not in that index -- the same trade the module already makes for the appearance table
(players past 30,023 keep the default look).  Nothing is moved and no count is lowered.

Install:
  1. copy this file to <game>\SiderAddons\modules\
  2. sider.ini: lua.module = "fl26playercap.lua" (next to fl26comptab.lua)
  3. start the game; sider.log says "fl26playercap: ... returns when it reaches 30000"

Third fix, same day: the lookup 0x141502e60 returns NULL for any player index from 40 on, and a
menu that builds a line-up hands it the sentinel 255 ("no player") and dereferences the answer.
The limit cannot grow (it is an imm8, and the array behind it is the block's 123825 players),
so the branch is replaced by a stub: below 40 the original code runs untouched, from 40 on the
lookup answers with player 0's record instead of NULL, and the menu draws that instead of
crashing.

Requires sider.ini: luajit.ext.enabled = 1 (the global ffi and `memory`), like fl26comptab.
--]]

local m = {}

local CMP, CMP_BYTES = 0x1414d6954, "4181fd30750000"   -- cmp r13d, 0x7530
local JE,  JE_BYTES  = 0x1414d695b, "0f84a50100"       -- je 0x1414d6b06
-- the squad lookup: cmp edx, 0x28 / jge -> null.  edx indexes the block's player array
-- (stride 0x17c), whose cap is 123825, so 40 is not the array's size.

local function hex(s)
  return (s:gsub(".", function(c) return string.format("%02x", c:byte()) end))
end

local LK, LK_BYTES = 0x141502e63, "83fa287d26"   -- cmp edx,0x28 ; jge -> null
local LK_NEXT      = 0x141502e68                 -- movsxd rax,edx (the original path)

local function hex2bin(h)
  return (h:gsub("%x%x", function(b) return string.char(tonumber(b, 16)) end))
end

local function u32(v)
  return string.char(v % 256, math.floor(v / 256) % 256, math.floor(v / 65536) % 256,
                     math.floor(v / 16777216) % 256)
end

local function rel32(from_next, to)
  local d = to - from_next
  if d >= 0x80000000 or d < -0x80000000 then return nil end
  if d < 0 then d = d + 0x100000000 end
  return u32(d)
end

local function install_lookup(ctx)
  local got = memory.read(LK, #LK_BYTES / 2)
  if got == nil or hex(got) ~= LK_BYTES then
    log("fl26playercap: lookup bytes are " .. tostring(got and hex(got)) .. " -- left alone")
    return
  end
  if ffi == nil then log("fl26playercap: no ffi, the lookup stub needs it"); return end
  ffi.cdef([[ void* VirtualAlloc(void*, unsigned long, unsigned long, unsigned long); ]])
  local cave
  for _, pref in ipairs({ 0x15e000000, 0x15f000000, 0x161000000, 0x171000000 }) do
    local p = ffi.C.VirtualAlloc(ffi.cast("void*", pref), 0x1000, 0x3000, 0x40)
    if p ~= nil then cave = tonumber(ffi.cast("uint64_t", p)); break end
  end
  if not cave then log("fl26playercap: VirtualAlloc failed -- lookup left alone"); return end
  local back = rel32(cave + 9, LK_NEXT)
  if not back then log("fl26playercap: cave out of range"); return end
  local stub = hex2bin("83fa28") .. hex2bin("0f8c") .. back .. hex2bin("498d4008c3")
  memory.write(cave, stub)
  local jmp = rel32(LK + 5, cave)
  if not jmp then log("fl26playercap: cave out of jump range"); return end
  memory.write(LK, "\233" .. jmp)
  local now = memory.read(LK, 5)
  if now == nil or now:byte(1) ~= 0xE9 then
    log("fl26playercap: the lookup jump did not stick -- the 40 cap stays")
    return
  end
  log("fl26playercap: the line-up lookup answers player 0 instead of NULL from index 40 on")
end

function m.init(ctx)
  local a = memory.read(CMP, #CMP_BYTES / 2)
  local b = memory.read(JE, #JE_BYTES / 2)
  if a == nil or b == nil then
    log("fl26playercap: cannot read the insert's prologue -- nothing written")
    return
  end
  if hex(a) ~= CMP_BYTES or hex(b) ~= JE_BYTES then
    log(string.format("fl26playercap: bytes at %#x are %s / %s, expected %s / %s -- nothing written",
                      JE, hex(a), hex(b), CMP_BYTES, JE_BYTES))
    return
  end
  -- raise the index's capacity from 30000 to 123825 players (0x7530 -> 0x1e3b1)
  memory.write(CMP + 3, string.char(0xb1, 0xe3, 0x01, 0x00))
  memory.write(JE + 1, string.char(0x83))
  log("fl26playercap: player index capacity raised to 123825 (0x7530 -> 0x1e3b1) and returns when full")
  install_lookup(ctx)
end

return m
