r"""mkregioncats.py -- give OUR leagues a heading of their own in the competition list.

What the game does today (measured 2026-09-21)

  A competition's heading comes from a table of 80 rows of eight bytes at 0x14351e0e0,
  {u32 competition id, u32 category}. Two functions read it and nothing else does
  (tools/dataref.py: exactly two instructions point at it):

    0x141e5b220   competition id -> category, walking 0x50 rows; no row found -> 0x18
    0x141e5b270   category -> the list of competitions in it, walking the same 0x50 rows

  The category is an index into a table of 24 string pointers at 0x14351e020, each the
  name of a picture in common/menu/general/compeCategorySelect.bin -- "compeCategory-england"
  and so on. 0x141e5b250 reads that table and refuses anything from 0x18 up, which is why
  the default means "no heading". The list screen at 0x140c151a0 builds its headings by
  asking for categories 0..0x17 in turn and keeping the ones that hold at least one
  competition.

  Our 39 leagues have no row, so they get no heading. The eleven shipped competitions
  without a row (28-32, 45, 46, 47, 90, 97, 103) are in the same position, and this patch
  deliberately leaves them there.

What this patch does

  1. copies the 80 shipped rows into the unused .rdata run at 0x143394568 (1,908 bytes that
     no instruction reaches, tools/cave.py --check) and adds one row per league of ours,
     all pointing at a new category 24;
  2. re-points the two readers at the copy and raises their row count 0x50 -> the new count;
  3. writes a 25th string pointer into the eight bytes the old row table just freed -- they
     sit immediately after the key table, which is why this costs one relocation and not
     two -- aimed at "compeCategory-event" at 0x142677240. That name is already in the
     atlas and already in the exe's own region-name table (record 1, region 26); no shipped
     key indexes it, so the picture ships unused;
  4. raises the key reader's limit 0x18 -> 0x19 and the list screen's 0..0x17 loop to 0..0x18
     so the new category is asked for and drawn;
  5. moves the "no row" default 0x18 -> 0x19 so that the eleven shipped rowless competitions
     keep having no heading instead of inheriting ours.

  Shipped rows are copied byte for byte, so no shipped competition changes heading.

Order of writing matters and the module below follows it: the cave is filled and read back
first, and the code is only touched once the rows are known to be there. The other order
would leave the readers pointing at 952 zero bytes -- no competition in any category, and a
list screen with nothing on it.

    python mkregioncats.py --root <livecpk-root>
    python mkregioncats.py --root <livecpk-root> --write
    python mkregioncats.py --root <root> --comps 130,131 --out <file> --write
                                  (the league builder: these ids, this file, no patches/ json)

Writes patches/regioncats.json and sider/fl26regions.lua.
"""
import json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boundscan
import pesdb

ROWS_VA   = 0x14351e0e0        # the shipped 80 rows
ROWS_N    = 0x50
KEYS_VA   = 0x14351e020        # 24 string pointers, ending exactly where the rows begin
KEYS_N    = 0x18
CAVE_VA   = 0x143394568        # 8-aligned start inside the 0x143394564 run
CAVE_END  = 0x143394564 + 1908
EVENT_VA  = 0x142677240        # "compeCategory-event"
NEW_CAT   = 0x18               # the category number the new key takes

SITES = [
    (0x141e5b220, "rows", "id -> category: base of the row table"),
    (0x141e5b23a, "count", "id -> category: how many rows to walk"),
    (0x141e5b23f, "default", "id -> category: what an unlisted competition gets"),
    (0x141e5b253, "keylimit", "category -> picture name: how many keys exist"),
    (0x141e5b290, "rows", "category -> competitions: base of the row table"),
    (0x141e5b297, "count", "category -> competitions: how many rows to walk"),
    (0x140c152c3, "screen", "list screen: how many categories to ask for"),
]


def image():
    d, secs, base = boundscan.image()

    def off(va):
        for _, sva, vsz, rp, rsz in secs:
            if base + sva <= va < base + sva + max(vsz, rsz):
                o = rp + (va - base - sva)
                if o < rp + rsz:
                    return o
        raise SystemExit("%x is not in the file image" % va)
    return d, off


def our_comps(root):
    """{comp id: name} for everything of ours, read from the pack's own regulation names.

    Ours is anything whose regulation name begins "FL " -- the 39 leagues, and any
    competition built on top of them, such as the 36-club Champions League.
    """
    p = os.path.join(root, "common", "etc", "pesdb", "CompetitionRegulation.bin")
    reg = pesdb.reg_rows(pesdb.wesys_unpack(open(p, "rb").read()))
    out = {}
    for r in reg:
        if r["name"].startswith("FL "):
            out.setdefault(r["comp"], r["name"])
    return out


def build(root, comps=None):
    """comps: the competition ids to list (default: every "FL " one of the root)"""
    d, off = image()
    ours = {c: "" for c in comps} if comps else our_comps(root)
    shipped = d[off(ROWS_VA):off(ROWS_VA) + ROWS_N * 8]
    have = {struct.unpack_from("<I", shipped, i * 8)[0] for i in range(ROWS_N)}
    added = []
    for cid in sorted(ours):
        if cid in have:                       # a shipped competition already owns this id
            print("  comp %d already has a heading; left alone" % cid)
            continue
        added.append(struct.pack("<II", cid, NEW_CAT))
    rows = shipped + b"".join(added)
    n = len(rows) // 8
    if CAVE_VA + len(rows) > CAVE_END:
        raise SystemExit("the rows do not fit in the cave")

    patches = [{
        "va": "0x%x" % CAVE_VA,
        "old": bytes(len(rows)).hex(),
        "new": rows.hex(),
        "why": "the %d shipped rows, copied byte for byte, plus %d of ours under category %d"
               % (ROWS_N, len(added), NEW_CAT),
    }]

    def code(va, size, newbytes, why):
        cur = d[off(va):off(va) + size]
        patches.append({"va": "0x%x" % va, "old": cur.hex(), "new": newbytes.hex(),
                        "why": why})
        return cur

    for va, kind, why in SITES:
        if kind == "rows":                    # lea reg, [rip + disp]
            cur = d[off(va):off(va) + 7]
            disp = struct.unpack_from("<i", cur, 3)[0]
            if va + 7 + disp != ROWS_VA:
                raise SystemExit("%x does not point at the row table" % va)
            new = cur[:3] + struct.pack("<i", CAVE_VA - (va + 7))
            code(va, 7, new, "%s -> the copy in the cave at 0x%x" % (why, CAVE_VA))
        elif kind == "count":                 # cmp eax, 0x50  /  mov ebp, 0x50
            cur = d[off(va):off(va) + 8]
            if cur[:2] == b"\x83\xf8" and cur[2] == ROWS_N:
                code(va, 3, cur[:2] + bytes([n]), "%s: %d -> %d" % (why, ROWS_N, n))
            elif cur[0] == 0xbd and struct.unpack_from("<I", cur, 1)[0] == ROWS_N:
                code(va, 5, cur[:1] + struct.pack("<I", n), "%s: %d -> %d" % (why, ROWS_N, n))
            else:
                raise SystemExit("%x is not the row count I measured" % va)
        elif kind == "default":               # mov eax, 0x18
            cur = d[off(va):off(va) + 5]
            if cur[0] != 0xb8 or struct.unpack_from("<I", cur, 1)[0] != KEYS_N:
                raise SystemExit("%x is not the default category" % va)
            code(va, 5, b"\xb8" + struct.pack("<I", KEYS_N + 1),
                 "%s: %d -> %d, so it still means none" % (why, KEYS_N, KEYS_N + 1))
        elif kind in ("keylimit", "screen"):  # cmp eax, 0x18  /  cmp edi, 0x18
            cur = d[off(va):off(va) + 3]
            if cur[0] != 0x83 or cur[2] != KEYS_N:
                raise SystemExit("%x is not the key limit I measured" % va)
            code(va, 3, cur[:2] + bytes([KEYS_N + 1]),
                 "%s: %d -> %d" % (why, KEYS_N, KEYS_N + 1))

    # the 25th key, in the eight bytes the row table leaves behind
    key_va = KEYS_VA + KEYS_N * 8
    assert key_va == ROWS_VA
    code(key_va, 8, struct.pack("<Q", EVENT_VA),
         "key %d -> compeCategory-event (0x%x), the picture no shipped key uses"
         % (NEW_CAT, EVENT_VA))
    return patches, n, len(added)


LUA = '''--[[
fl26regions -- GENERATED by tools/mkregioncats.py. Do not edit by hand.

Gives our %(added)d leagues a heading of their own in the competition list: the 80 shipped
heading rows are copied into unused read-only space at 0x%(cave)x, ours are added after them
under a new category %(cat)d, the two readers are re-pointed at the copy, and the freed eight
bytes after the key table become a 25th picture name -- compeCategory-event, which the game
ships and no shipped key uses. Shipped rows are copied byte for byte, so nothing that had a
heading changes heading. Full reasoning: tools/mkregioncats.py.

Two passes, in this order, and the order is the safety:
  1. verify every site against the bytes the generator read out of the exe; one mismatch and
     nothing at all is written;
  2. write the rows first and read them back. Only if they are really there does the code get
     touched -- the other way round leaves the readers walking zeroes, which is a competition
     list with nothing in it.

Install: copy to <game>\\SiderAddons\\modules\\fl26regions.lua and add to sider.ini:
    lua.module = "fl26regions.lua"
--]]

local m = {}

local rows = %(rows)s

local patches = {
%(patches)s}

local function unhex(s)
  local out = {}
  for b in s:gmatch("%%x%%x") do out[#out + 1] = string.char(tonumber(b, 16)) end
  return table.concat(out)
end

function m.init(ctx)
  log(string.format("fl26regions: %%d sites, verifying", #patches + 1))
  local bad = 0
  if memory.read(rows.va, #unhex(rows.old)) ~= unhex(rows.old) then
    log(string.format("fl26regions: MISMATCH in the cave at 0x%%x -- it is not empty", rows.va))
    bad = bad + 1
  end
  for i = 1, #patches do
    local p = patches[i]
    local want = unhex(p.old)
    if memory.read(p.va, #want) ~= want then
      log(string.format("fl26regions: MISMATCH at 0x%%x: expected %%s  [%%s]", p.va, p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26regions: ABORTED, %%d site(s) did not match. Nothing was written.", bad))
    return
  end

  local new = unhex(rows.new)
  memory.write(rows.va, new)
  if memory.read(rows.va, #new) ~= new then
    log(string.format("fl26regions: the rows did not stick at 0x%%x -- ABORTED before "
                      .. "touching any code, the game is unmodified", rows.va))
    return
  end
  log(string.format("fl26regions: %%d heading rows written at 0x%%x", #new / 8, rows.va))

  local written, failed = 0, 0
  for i = 1, #patches do
    local p = patches[i]
    local nb = unhex(p.new)
    memory.write(p.va, nb)
    if memory.read(p.va, #nb) == nb then
      written = written + 1
      log(string.format("fl26regions: [%%d/%%d] 0x%%x %%s -> %%s  %%s", i, #patches, p.va,
                        p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26regions: WRITE FAILED at 0x%%x (%%s)", p.va, p.why))
    end
  end
  if failed == 0 then
    log(string.format("fl26regions: applied all %%d, %%d leagues now sit under their own heading",
                      written, %(added)d))
  else
    log(string.format("fl26regions: PARTIAL: %%d written, %%d failed -- quit the game and report",
                      written, failed))
  end
end

return m
'''


def main():
    a = sys.argv[1:]
    root = a[a.index("--root") + 1] if "--root" in a else None
    if not root:
        print(__doc__)
        return 1
    comps = [int(c) for c in a[a.index("--comps") + 1].split(",")] if "--comps" in a else None
    patches, n, added = build(root, comps)
    rows, code = patches[0], patches[1:]
    print("%d heading rows (%d shipped + %d ours), %d code sites"
          % (n, ROWS_N, added, len(code)))
    for p in code:
        print("  %s  %-16s -> %-16s %s" % (p["va"], p["old"], p["new"], p["why"]))
    if "--write" not in a:
        print("\nnothing written. Re-run with --write.")
        return 0

    top = os.path.dirname(HERE)
    jp = "(no json with --out)"
    if "--out" not in a:
        os.makedirs(os.path.join(top, "patches"), exist_ok=True)
        jp = os.path.join(top, "patches", "regioncats.json")
        json.dump({"set": "regioncats", "rows": rows, "patches": code}, open(jp, "w"), indent=1)

    def lit(p):
        return ('  {va=%s, old="%s", new="%s", why="%s"},\n'
                % (p["va"], p["old"], p["new"], p["why"].replace('"', "'")))
    lp = a[a.index("--out") + 1] if "--out" in a else os.path.join(top, "sider", "fl26regions.lua")
    open(lp, "w").write(LUA % {
        "added": added, "cave": CAVE_VA, "cat": NEW_CAT,
        "rows": '{va=%s, old="%s", new="%s"}' % (rows["va"], rows["old"], rows["new"]),
        "patches": "".join(lit(p) for p in code),
    })
    print("\nwrote %s\n      %s" % (jp, lp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
