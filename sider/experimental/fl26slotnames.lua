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

Seven slots are patched: 4, 5, 6, 69, 71, 73 and 75. Every one of them is held by a league
of ours and by nothing else -- checked against the live table in the same run, not against
the shipped file. Slots 0, 1, 2 and 3 are left alone (nothing of ours is on them), and so
is 70, which still carries the two shipped competitions it always did.

What this does NOT fix: rows of ours that were inherited from a shipped competition and
still hold that competition's label in +0x38. Those are a row, not a slot, and fl26comptab
clears them.

Load order does not matter; this module touches no address any other module touches.

Install:
  1. copy to <game>\SiderAddons\modules\fl26slotnames.lua
  2. sider.ini, in the [modules] list:   lua.module = "fl26slotnames.lua"
--]]

local m = {}

local BYTE_TABLE = 0x140ea0b3c   -- one byte per slot, 0x4c entries, value = case index
local DEFAULT    = 11            -- the case that leaves the name empty

-- {slot, the case byte it must currently hold, what that case says today}
local SLOTS = {
  {  4, 4,  "Asia-Oceania" },
  {  5, 5,  "Classic Teams" },
  {  6, 5,  "Classic Teams" },
  { 69, 6,  "Other European Leagues" },
  { 71, 8,  "Other" },
  { 73, 9,  "Other Latin American Teams" },
  { 75, 10, "Other Clubs (Africa)" },
}

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

  for _, s in ipairs(SLOTS) do
    local va = BYTE_TABLE + s[1]
    memory.write(va, string.char(DEFAULT))
    if memory.read(va, 1):byte() ~= DEFAULT then
      log(string.format("fl26slotnames: WRITE FAILED at 0x%x (slot %d)", va, s[1]))
      return
    end
    log(string.format("fl26slotnames: slot %d no longer reads \"%s\" -- the league on it "
                      .. "names itself", s[1], s[3]))
  end
  log(string.format("fl26slotnames: %d slots freed", #SLOTS))
end

return m
