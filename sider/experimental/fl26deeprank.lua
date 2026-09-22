--[[
fl26deeprank -- make the relegation gate work for a pyramid of any depth, now that the rank
is a real number.

This replaces fl26deep4.lua. Load it AFTER fl26rank.lua, and turn fl26deep4 off.

Background. The function that answers "where does this club go at the end of the season",
0x141510430, is three gates:

  0x1415104a1   rank >= 2                -> promoted into the league named at +0x7c
  0x1415104d6   rank == 1, bottom three  -> relegated into the league named at +0x7e
  0x1415105f5   the league below is rank 3 AND this league is rank 2
                                         -> relegated into the league named at +0x7e

The same third gate is written out a second time in 0x1415141c0, the one the screens ask
"is this club going down", and both copies are patched here.

The first two are fine at any depth once fl26rank has widened the field: ">= 2" and "== 1"
mean the same thing they always did. The third is not, and it is the only one that sends
anybody down from below the second division.

While every deep league carried the value 3 (which is all two bits could hold), fl26deep4
made that gate work with a single byte: "this league is exactly 2" became "2 or more", and
the other half -- "the league below is 3" -- was already true of every division below the
second. With real ranks that stops being true: below France D3 sits D4, whose rank is now 4,
so the gate never fires and clubs climb without ever falling.

The gate also does something odd in the middle. It masks the league's own flags word with
the rank it just read out of the league BELOW:

  141510609  mov  eax, [r13+0x304]
  141510610  and  eax, ecx          ; ecx is the lower league's rank bits, not a mask
  141510612  cmp  eax, 0x80000000

That works by accident when the lower rank is 3 (0b11 covers both bits), and gives nonsense
for any other value. So the two instructions are replaced outright -- same seven bytes:

  141510607  jne  -> jb             ; the league below is rank 3 OR DEEPER
  141510610  shr  eax, 0x1d         ; this league's rank, as a number
  141510613  cmp  eax, 2
  141510616  nop                    ; the byte the old five-byte cmp leaves over
  141510617  jne  -> jb             ; this league is rank 2 OR DEEPER

So: a league relegates into the league at +0x7e whenever it is at least the second division
and the league below it is at least the third. D2 -> D3, D3 -> D4, D4 -> D5, as deep as the
chain goes, and the first division keeps its own gate.

The old bytes checked here are the ones fl26rank leaves behind (it turns the two compares in
this gate into 0x60000000 and 0x40000000), so loading this without fl26rank, or before it,
reports a mismatch and writes nothing.

Install:
  1. copy to <game>\SiderAddons\modules\fl26deeprank.lua
  2. sider.ini:   lua.module = "fl26deeprank.lua"     after fl26rank.lua
  3. sider.ini:   comment out  lua.module = "fl26deep4.lua"

Not run in a game yet. Built and verified against the exe on 2026-09-22.
--]]

local m = {}

-- The same gate is written out twice: once in 0x141510430, which answers "where does this
-- club move to", and once in 0x1415141c0, which answers "is this club going down" for the
-- screens. Both are patched, and each is verified whole so there is no half-written state.
local SITES = {
  { va = 0x141510607, why = "0x141510430 -- where does this club move to",
    old = "75c1418b850403000023c13d0000004075b1",
    new = "72c1418b8504030000c1e81d83f8029072b1" },
  { va = 0x1415143ec, why = "0x1415141c0 -- is this club being relegated",
    old = "75c4418b870403000023c13d0000004075b4",
    new = "72c4418b8704030000c1e81d83f8029072b4" },
}

local function bin2hex(s)
  return (s:gsub(".", function(c) return string.format("%02x", string.byte(c)) end))
end

local function hex2bin(s)
  return (s:gsub("%x%x", function(h) return string.char(tonumber(h, 16)) end))
end

function m.init(ctx)
  for _, s in ipairs(SITES) do
    local got = bin2hex(memory.read(s.va, #s.old / 2))
    if got ~= s.old then
      log(string.format("fl26deeprank: bytes at 0x%x are %s, expected %s (%s) -- nothing " ..
                        "written. This module needs fl26rank.lua loaded before it.",
                        s.va, got, s.old, s.why))
      return
    end
  end
  for _, s in ipairs(SITES) do
    memory.write(s.va, hex2bin(s.new))
    if bin2hex(memory.read(s.va, #s.new / 2)) ~= s.new then
      log(string.format("fl26deeprank: the write at 0x%x did not take", s.va))
      return
    end
  end
  log("fl26deeprank: live -- both relegation gates: a league goes down into the one at " ..
      "+0x7e whenever it is the second division or deeper and the league below it is the " ..
      "third or deeper")
end

return m
