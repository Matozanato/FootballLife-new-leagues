--[[
fl26augseason -- let a Master League career in one of our leagues start in August.

Why the world started on 1 January. When a career is created, 0x1412695b0 picks the season
type from the user's competition: 0x1415762a0(comp) -> region -> 0x141576140(region), a
lookup in a table of 25 (region, type) pairs covering the shipped regions 2..28. Type 0 is
the European calendar (the August start dates 0x10807e9 / 0x10707e9); type 1 is the
calendar year. Our standalone leagues live in regions 29..63 (fl26reg64), which the table
does not know, so the lookup fell through to `mov eax,5` at 0x14157623d -- and 0x1412695b0
turns 5 into 1. The whole world then ran January-December, with the leagues' August-May
fixture calendar folded into it and no promotion at year end.

What this writes. The fall-through `mov eax,5` (5 bytes) becomes a jmp to a trampoline that
returns type 0 for regions 29..63 and 5 for everything else, then resumes at 0x141576242:

    14252ee00  lea  eax, [r8-0x1d]     ; r8d = the region being looked up
    14252ee04  cmp  eax, 0x23          ; 29..63 ?
    14252ee07  mov  eax, 5             ; the original answer
    14252ee0c  jae  +2
    14252ee0e  xor  eax, eax           ; ours: European calendar
    14252ee10  jmp  0x141576242

Shipped regions cannot reach 29 (the stock parser rejects them, see fl26reg64), so every
shipped competition keeps exactly the answer it had. 0x141576140 has eleven callers; all of
them now see our leagues as European, which is what they are.

The trampoline sits at 0x14252ee00, above fl26joindll's ring (0x14252ebe0 + 0x208).

Same apply rule as every fl26 module: verify all sites first, write only if all match.
--]]

local m = {}

local patches = {
  {va=0x14252ee00, old="000000000000000000000000000000000000000000", new="418d40e383f823b805000000730231c0e92d7404ff", why="season-type trampoline: regions 29..63 (ours) -> type 0 (European, August start), others keep 5; jmp 0x141576242"},
  {va=0x14157623d, old="b805000000", new="e9be8bfb00", why="redirect the not-found answer of the region->season-type lookup 0x141576140 (mov eax,5) to the trampoline at 0x14252ee00"},
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
  log(string.format("fl26augseason: set '%s', %d patches, verifying", "augseason", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26augseason: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26augseason: ABORTED, %d of %d sites did not match. "
                      .. "Nothing was written; the game is unmodified. "
                      .. "This usually means the exe is a different build than the one "
                      .. "the patch set was generated from.", bad, n))
    return
  end

  -- pass 2: write, then read back, because writing to the code section can silently fail
  -- if the page is not made writable for us. Each site is logged as it goes, so that if a
  -- write throws and Sider stops the module, the log still names the last one that worked.
  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    local back = memory.read(p.va, #new)
    if back == new then
      written = written + 1
      log(string.format("fl26augseason: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26augseason: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  -- The patch has to land before the game allocates the edit block, and the log proves
  -- that it does: everything above is written during module init, which Sider finishes
  -- before it reports "Sider initialization complete", and the first `read_file::` line
  -- comes thousands of lines later. An earlier version of this file also registered a
  -- livecpk_get_filepath handler to re-read the first site at the first file request. It
  -- worked, but it made Sider log "lua ERROR from module_get_filepath" on every single
  -- file lookup -- 27811 of them in one session -- so it is gone. The ordering was never
  -- in doubt; the check was.

  if failed == 0 then
    log(string.format("fl26augseason: applied all %d patches -- %s", written, "our regions 29..63 get the European season type, so a career in our league starts in August"))
  else
    log(string.format("fl26augseason: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
