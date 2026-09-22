--[[
fl26caps -- runtime patch applier (nullguard9 set).

Defensive fix, NOT a capacity patch.  Like the other nullguards it installs a code-cave
trampoline rather than resizing a field; every byte below was computed against the exe and
disassembled back before being written here.

Set:     nullguard9
Summary: empty-schedule guard at 0x140cd6a18, 2 patches (trampoline + site redirect)

The bug: a lookup that finds nothing is used as if it had found something.
0x140cd69cc builds the name "d_schedule_" and hands it to 0x14150d620, which is expected
to fill two out-parameters: an index at [rsp+0x40] and the list it indexes at [rsp+0x48].
The code checks the function's RETURN value and has its own exit for "not found" --
and then indexes the list anyway, without ever checking the list pointer:

    140cd69cc  lea    rdx, [rip + 0x1a5914d]     ; "d_schedule_"
    140cd69f0  call   0x14150d620                ; fills [rsp+0x40] and [rsp+0x48]
    140cd6a07  call   0x140e4cd10
    140cd6a0f  test   rax, rax
    140cd6a12  je     0x140cd6ead                ; the game's own "nothing here" path
    140cd6a18  mov    edx, dword ptr [rsp + 0x40]    ; the index  -- 0
    140cd6a1c  mov    rcx, qword ptr [rsp + 0x48]    ; the list   -- NULL
    140cd6a21  movzx  edx, word ptr [rcx + rdx*4]    <-- faults

On 22 September 2026 a season created from the Master League menu died here during the
board meeting, fault offset 0xcd6a21: rcx = rdx = 0, an access violation reading address
zero.  The world had no schedule entry under that name, so the lookup returned empty.

The guard invents nothing.  When the list pointer is null it takes the branch the game
already has for this case, 0x140cd6ead -- the same place the function goes when the
preceding lookup comes back empty.  When the pointer is real the original three
instructions run unchanged.

Thirteen bytes at 0x140cd6a18 -- the two loads plus the faulting index -- are replaced by
a jump to a trampoline that does all three with a null test between them.  Eight nops pad
the rest.

The trampoline sits at 0x14252e8e0.  .trace holds 0x252d800 bytes of virtual data and so
ends at 0x14252e800; everything from there to where .rdata begins at 0x14252f000 is the
zero-filled tail of the last page.  Reading those addresses out of the exe *file* shows
non-zero bytes, because the file offset runs on into .rdata's raw data -- the running
process is the authority there, and the applier verifies the zeros before writing.
nullguard5, 2, 7 and 8 hold 0x14252e860 .. 0x14252e8c0; this is the next slot.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26nullguard9.lua
  2. add to sider.ini, in the lua.module list:   lua.module = "fl26nullguard9.lua"
     -- after fl26nullguard8.lua, so the trampolines are written in a fixed order
  3. start the game and read sider.log

The exe has no ASLR (DllCharacteristics 0x8120), so the addresses are absolute and stable.
The applier checks that anyway by verifying the bytes.
--]]

local m = {}

local patches = {
  {va=0x14252e8e0,
   old="0000000000000000000000000000000000000000000000000000000000000000",
   new="8b542440488b4c24484885c974090fb71491e92e817afee9b1857afe00000000",
   why="empty-schedule guard trampoline: mov edx,[rsp+0x40]; mov rcx,[rsp+0x48]; "
    .. "test rcx,rcx; je out; movzx edx,word [rcx+rdx*4]; jmp 0x140cd6a25; "
    .. "out: jmp 0x140cd6ead"},
  {va=0x140cd6a18, old="8b542440488b4c24480fb71491",
   new="e9c37e85019090909090909090",
   why="redirect the unchecked schedule read at 0x140cd6a18 to the trampoline "
    .. "(jmp rel32 + 8 nop)"},
}

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

function m.init(ctx)
  local n = #patches
  log(string.format("fl26caps: set '%s', %d patches, verifying", "nullguard9", n))

  -- pass 1: read only.  Nothing is written until every site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26caps: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26caps: ABORTED, %d of %d sites did not match. "
                      .. "Nothing was written; the game is unmodified. "
                      .. "If site 1 is the mismatch, another module has taken that padding.",
                      bad, n))
    return
  end

  -- pass 2: write, then read back, because a write into the code section can silently fail
  -- if the page is not writable for us.  The trampoline goes first, so the jump target
  -- exists before the jump does.
  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    local back = memory.read(p.va, #new)
    if back == new then
      written = written + 1
      log(string.format("fl26caps: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26caps: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  if failed == 0 then
    log(string.format("fl26caps: applied all %d patches -- %s", written,
                      "nullguard9: empty schedule list guarded at 0x140cd6a18"))
  else
    log(string.format("fl26caps: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
