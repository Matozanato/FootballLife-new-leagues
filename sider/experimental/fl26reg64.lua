--[[
fl26reg64 -- raise the number of regions (countries) from 29 to 64.

Where the 29 came from. One function parses a competition row into the runtime object, and
the region is the first field it reads:

    1414f8390  8b08        mov   ecx, [rax]          ; dword 0 of the Competition.bin row
    1414f8392  c1e91b      shr   ecx, 0x1b           ; bits 27..31 -- five bits
    1414f8395  0fb6c1      movzx eax, cl
    1414f8398  241f        and   al, 0x1f
    1414f839a  3c1d        cmp   al, 0x1d            ; 29 or more?
    1414f839c  7304        jae   0x1414f83a2         ; throw it away, keep the default
    1414f839e  440fb6f1    movzx r14d, cl
    1414f83a2  418bd6      mov   edx, r14d
    1414f83a8  e8...       call  0x1414c9c10         ; the setter

So 29 was never a table size or a menu limit -- it is one `cmp`, and the five bits below it.
Two things sit above:

  * the runtime field is **six** bits (`0x1414c9c10`: `and edx,0x3f ; shl edx,7` into
    `+0x30c` bits 7..12), and all thirty sites that read it back use the same `shr 7 /
    and 0x3f`. Six bits is 64 regions, and that is the real ceiling.
  * in the file, the region byte is `Competition.bin +3`, holding the region in bits 3..7.
    Bits 0..2 are **zero in all 131 rows** of the installed world, and bit 0 of that byte is
    bit 24 of the dword, which belongs to the top of the field below -- a 9-bit field whose
    values never come near needing it.

What this writes. The eighteen bytes above are replaced by eighteen bytes that read a sixth
bit out of that spare bit 0 and drop the compare, because a six-bit value cannot be out of
range:

    1414f8390  8b08        mov   ecx, [rax]
    1414f8392  8bc1        mov   eax, ecx
    1414f8394  c1e91b      shr   ecx, 0x1b           ; bits 27..31 -> the low five
    1414f8397  c1e813      shr   eax, 0x13           ; bit 24 -> bit 5
    1414f839a  83e020      and   eax, 0x20
    1414f839d  0bc8        or    ecx, eax            ; the region, 0..63
    1414f839f  448bf1      mov   r14d, ecx

**Every shipped row keeps the region it has.** A row with bit 0 clear -- which is all of
them, shipped and ours alike, today -- decodes to exactly the value it decoded to before.
The new bit is only ever set by data written deliberately, so installing this module on a
world that does not use it changes nothing at all.

Checked before believing it, the same three ways the header stubs were:

  * the eighteen bytes in the exe are exactly what the header above claims;
  * a linear decode of the whole code section finds **no** branch landing anywhere inside
    the replaced run, so nothing jumps into the middle of it;
  * no aligned word in .rdata, .data or .trace holds an RVA pointing inside it, so no jump
    table does either.

The other half of the job is the heading, and it is a separate module: a region with no row
in the table at 0x1426770c0 does not draw a blank, it draws the heading of the country before
it. tools/mkregnames.py generates fl26regnames.lua, which relocates that table and can hold
up to 127 rows.

Not run in a game yet. Built 2026-09-21.

Install:
  1. copy to <game>\SiderAddons\modules\fl26reg64.lua
  2. sider.ini, in the [modules] list:   lua.module = "fl26reg64.lua"
--]]

local m = {}

local VA = 0x1414f8390
local OLD = "8b08c1e91b0fb6c1241f3c1d7304440fb6f1"
local NEW = "8b088bc1c1e91bc1e81383e0200bc8448bf1"

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
  local want, new = unhex(OLD), unhex(NEW)
  local cur = memory.read(VA, #want)
  if cur ~= want then
    log(string.format("fl26reg64: bytes at 0x%x are %s, expected %s -- nothing written, "
                      .. "the game is unmodified", VA, tohex(cur), OLD))
    return
  end
  memory.write(VA, new)
  if memory.read(VA, #new) == new then
    log(string.format("fl26reg64: 0x%x rewritten -- regions now run 0..63 instead of 0..28, "
                      .. "and every shipped row keeps the region it had", VA))
  else
    log(string.format("fl26reg64: WRITE FAILED at 0x%x", VA))
  end
end

return m
