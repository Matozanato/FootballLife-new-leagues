r"""mkregnames.py -- give OUR regions a heading of their own instead of the previous country's.

What the game does today (measured 2026-09-21)

  A region id becomes a heading picture in exactly one place. 0x140acd3f0 builds the
  category strip, and inside it:

      140acd478  lea r10, [0x1426770c8]      ; the id field of row 0
      140acd47f  lea r11, [0x1426770c0]      ; the name field of row 0
      140acd490  cmp [rax], edx              ; this row's id == the region we want?
      140acd496  add rax, 0x10               ; 16 bytes a row
      140acd49a  cmp ecx, 0x18               ; 24 rows, and then give up
      140acd4a6  mov rbx, [r11 + rax*8]      ; found: the picture name

  tools/dataref.py finds exactly one instruction in the whole exe pointing at that table, so
  this loop is the only thing that reads it.

  When no row matches, the loop simply falls out -- and `rbx` is left holding whatever the
  PREVIOUS lookup put there. So a region with no row does not draw a blank heading: it draws
  the heading of the country before it. The shipped table has a row for every region the
  shipped data uses; the four ids it has no row for are 11, 13, 14 and 20, which are exactly
  the four free ids tools/spreadregions.py moves our leagues onto.

What this writes

  1. the 24 shipped rows, byte for byte, into unused read-only space, plus one row per region
     of ours;
  2. the two leas re-pointed at the copy, and the 0x18 raised to the new row count.

  Three code sites, one function, nothing shipped moved.

The picture names

  A heading is a drawn picture inside common/menu/general/compeCategorySelect.bin, and its
  name is a symbol inside the AFP package in that file. Adding a symbol of our own is a
  separate job on that format, so until it is done our regions borrow headings the game
  already draws. The default mapping uses the four generic ones rather than a country's:

      11 -> compeCategory-PEU      ("rest of Europe", also region 22)
      13 -> compeCategory-PLA      ("rest of Latin America", also region 23)
      14 -> compeCategory-PAS      ("rest of Asia", also region 24)
      20 -> compeCategory-event    ("events", also region 26)

  Two regions then carry the same heading, which is untidy; drawing the previous country's
  heading over our leagues is worse, and that is what happens today.

    python mkregnames.py                 -> sider/fl26regnames.lua with the defaults
    python mkregnames.py --map 11=PEU,13=PLA,14=PAS,20=event
    python mkregnames.py --root <livecpk root>   -> a row for every region that world uses
    python mkregnames.py --root <root> --out <file>   (the league builder: write there)
                                                    and has no row, generic headings cycled
    python mkregnames.py --show          -> the shipped table, decoded

With --root, ids above 28 also need sider/fl26reg64.lua: without it the game never sees a
region above 28 in the first place.

Nothing here has been run in a game.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import caltab

TABLE, NROWS, STRIDE = 0x1426770c0, 24, 16
CAVE = 0x1426d1f20                      # 28,858 bytes of .rdata padding (tools/cave.py)
LEA_ID = (0x140acd478, "4c8d15499cba01", 3)    # lea r10, [table+8]
LEA_NM = (0x140acd47f, "4c8d1d3a9cba01", 3)    # lea r11, [table]
COUNT = (0x140acd49a, "83f918", 2)             # cmp ecx, 0x18
DEFAULT_MAP = "11=PEU,13=PLA,14=PAS,20=event"
GENERIC = ["PEU", "PLA", "PAS", "event"]       # the four headings that name no country


def cstr(img, va):
    o = img.off(va)
    return img.data[o:img.data.index(b"\0", o)].decode("latin1")


def rows(img):
    out = []
    for i in range(NROWS):
        b = img.data[img.off(TABLE + i * STRIDE):img.off(TABLE + i * STRIDE) + STRIDE]
        ptr, rid, pad = struct.unpack("<QII", b)
        out.append((ptr, rid, pad, cstr(img, ptr)))
    return out


def names(img):
    """picture name -> the address of that string, from the shipped rows"""
    return dict((r[3].split("compeCategory-")[-1], r[0]) for r in rows(img))


def check(img, site):
    va, want, _ = site
    got = img.data[img.off(va):img.off(va) + len(want) // 2].hex()
    if got != want:
        raise SystemExit("bytes at 0x%x are %s, expected %s" % (va, got, want))


def rel32(at, ins_len, target):
    return (target - (at + ins_len)) & 0xffffffff


def main(argv):
    get = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    img = caltab.Image()
    shipped = rows(img)

    if "--show" in argv:
        for i, (ptr, rid, pad, nm) in enumerate(shipped):
            print("  row %2d  id %3d  %s" % (i, rid, nm))
        used = sorted(r[1] for r in shipped)
        print("ids with a row: %s" % used)
        print("ids 1..28 without one: %s" % [i for i in range(1, 29) if i not in used])
        return 0

    for s in (LEA_ID, LEA_NM, COUNT):
        check(img, s)

    known = names(img)
    added = []
    root = get("--root")
    if root:
        import collections
        sys.path.insert(0, HERE)
        import pesdb
        import mkleague as M
        raw = pesdb.wesys_unpack(open(os.path.join(root, "common", "etc", "pesdb",
                                                   "Competition.bin"), "rb").read())
        used = sorted(set(M.dec_region(raw[i * M.COMP + M.REGION_OFF])
                          for i in range(len(raw) // M.COMP)))
        have = set(r[1] for r in shipped)
        need = [rid for rid in used if rid not in have]
        if "--map" in argv:
            raise SystemExit("--root computes the map; do not also pass --map")
        argv = argv + ["--map", ",".join("%d=%s" % (rid, GENERIC[i % len(GENERIC)])
                                         for i, rid in enumerate(need))]
        print("%s uses %d regions; %d of them have no heading: %s"
              % (os.path.basename(root.rstrip("/\\")), len(used), len(need), need))
        if need and max(need) > 28:
            print("  ids above 28 also need sider/fl26reg64.lua to be read at all")
    for part in get("--map", DEFAULT_MAP).split(","):
        if not part:                # an empty map: every league sits in a region that has a heading
            continue
        rid, nm = part.split("=")
        rid = int(rid)
        if nm not in known:
            raise SystemExit("no shipped heading called compeCategory-%s; have %s"
                             % (nm, ", ".join(sorted(known))))
        if any(r[1] == rid for r in shipped):
            raise SystemExit("region %d already has a heading -- refusing to change a shipped one" % rid)
        added.append((known[nm], rid, 0, "compeCategory-" + nm))

    table = b"".join(struct.pack("<QII", p, rid, pad) for p, rid, pad, _ in shipped + added)
    total = NROWS + len(added)
    if total > 0x7f:
        raise SystemExit("%d rows does not fit the 8-bit compare at 0x%x" % (total, COUNT[0]))

    patches = [
        (CAVE, "00" * len(table), table.hex(),
         "%d heading rows: the %d shipped ones byte for byte, then %s"
         % (total, NROWS, ", ".join("region %d -> %s" % (r[1], r[3]) for r in added))),
        (LEA_ID[0], LEA_ID[1],
         LEA_ID[1][:LEA_ID[2] * 2] + struct.pack("<I", rel32(LEA_ID[0], 7, CAVE + 8)).hex(),
         "the id column -> the copy"),
        (LEA_NM[0], LEA_NM[1],
         LEA_NM[1][:LEA_NM[2] * 2] + struct.pack("<I", rel32(LEA_NM[0], 7, CAVE)).hex(),
         "the name column -> the copy"),
        (COUNT[0], COUNT[1], COUNT[1][:COUNT[2] * 2] + "%02x" % total,
         "how many rows the loop walks: %d -> %d" % (NROWS, total)),
    ]

    out = get("--out") or os.path.join(os.path.dirname(HERE), "sider", "fl26regnames.lua")
    f = open(out, "w", encoding="utf-8", newline="\n")
    f.write(HEADER % (total, ", ".join("%d" % r[1] for r in added)))
    f.write("local patches = {\n")
    for va, old, new, why in patches:
        f.write('  {va=0x%x, old="%s", new="%s", why="%s"},\n' % (va, old, new, why))
    f.write("}\n" + BODY)
    f.close()
    print("wrote %s: %d rows (%d shipped + %d ours), %d sites"
          % (out, total, NROWS, len(added), len(patches)))
    for _, rid, _, nm in added:
        print("  region %-3d -> %s" % (rid, nm))
    return 0


HEADER = '''--[[
fl26regnames -- GENERATED by tools/mkregnames.py. Do not edit by hand.

A region with no row in the heading table at 0x1426770c0 does not draw a blank heading: the
one loop that reads the table (0x140acd490) falls out without touching the register, so it
draws the heading of the country looked up before it. The four ids our leagues sit on -- 11,
13, 14 and 20 -- have no row.

This copies the 24 shipped rows into unused read-only space, adds one per region of ours
(%d rows in all, for regions %s), re-points the two leas at the copy and raises the row
count. Shipped rows are copied byte for byte, so no country's heading changes.

Two passes, and the order is the safety: verify every site against the bytes the generator
read out of the exe, and only then write -- the rows first and read back, the code last, so
the loop is never pointed at a table that is not there yet.

Install: copy to <game>\\SiderAddons\\modules\\fl26regnames.lua and add to sider.ini:
    lua.module = "fl26regnames.lua"
--]]

local m = {}

'''

BODY = '''
local function unhex(s)
  local out = {}
  for b in s:gmatch("%x%x") do out[#out + 1] = string.char(tonumber(b, 16)) end
  return table.concat(out)
end

function m.init(ctx)
  log(string.format("fl26regnames: %d sites, verifying", #patches))
  for i = 1, #patches do
    local p = patches[i]
    local want = unhex(p.old)
    if memory.read(p.va, #want) ~= want then
      log(string.format("fl26regnames: MISMATCH at 0x%x -- nothing written  [%s]", p.va, p.why))
      return
    end
  end
  for i = 1, #patches do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    if memory.read(p.va, #new) ~= new then
      log(string.format("fl26regnames: WRITE FAILED at 0x%x (%s)", p.va, p.why))
      if i == 1 then return end     -- the rows are not there; do not point the loop at them
      log("fl26regnames: PARTIAL -- quit and report this")
      return
    end
    log(string.format("fl26regnames: [%d/%d] 0x%x  %s", i, #patches, p.va, p.why))
  end
  log("fl26regnames: done -- our regions draw a heading of their own")
end

return m
'''

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
