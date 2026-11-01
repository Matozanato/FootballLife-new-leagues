r"""mkteamcrest.py -- a crest cell in the rows of the Select Team panel (Team List).

Master League > Database > Team Info (and the other Select Team screens) is the layout
common/menu/general/teamSelectSingle.bin. Its panel's rows (c_player_*, sprite 16) have a position
badge (position), a name (playerName) and the highlight (rect): made for players, so no crest.
fl26squadlist.dll lists a league's clubs in that panel on a league row (Team List); with this
layout each of those rows gets the club's crest where the badge is, and the DLL hides the badge
there. The players of a club (Squad List) keep their badges: the DLL hides the crest on their
rows. Without this layout the DLL finds no crest cell and a club row keeps the empty badge.

    python mkteamcrest.py --root <world livecpk root> --game <game folder> [--base <layout>]
    python mkteamcrest.py --base <layout> --out <file>

  --root   the world's livecpk root: the layout is written there
  --game   where the game's layout comes from: the sider.ini roots other than the world, in their
           order, then the game's CPKs (mkcatflags.Source)
  --base   this layout instead
  --out    write here instead of the root

What changes, in the AP2 movie (the container work is mkmpcol.rebuild):
  - the row sprite gets flTeamEmblem, a uirEmblemCompe instance (character 3, the class the
    layout's league logo leagueUpper_emblem already uses), copied from that logo's tag: 38 px at
    (11, 2), the badge's place, at depth 2 (between the badge, 1, and the name, 3: a depth inside
    the row's own 1..5, since the rows sit 6 depths apart in the page). It is the last tag of
    frame 0, as mkmpcol's cells are;
  - the game's own crest pass over list rows draws only uirEmblem (node type 0xd) cells, so it
    never touches this one (0xe): the DLL fills it (0x140e5cda0, the call that pass makes) and
    nothing else does, on any screen that uses this layout.
The layout is checked against the one this was made for (classes, the row's cells and frames)
first; another one (another mod's) is left as it is. Checked in FL27 1.00 on 2026-11-01: every
league row's clubs with their crests, Squad List as the game's, after a restart too.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkmpcol as M

PACKAGE = "common/menu/general/teamSelectSingle.bin"
NEW = "flTeamEmblem"
ROW, TEMPLATE_SPRITE, TEMPLATE = 16, 20, "leagueUpper_emblem"
DEPTH, TX, TY = 2, 11, 2
SCALE = 0x30a2                      # 0x30a2 / 0x8000 = 0.38: the 100-unit crest -> 38 px
Unknown = M.Unknown


def class_table(m):
    off = struct.unpack_from('<I', m.D, 0x38)[0]
    _, n = struct.unpack_from('<HH', m.D, off)
    return {struct.unpack_from('<H', m.D, off + 4 + 4 * i)[0]:
            m.string_at(struct.unpack_from('<H', m.D, off + 6 + 4 * i)[0]) for i in range(n)}


def edit(m):
    if m.find_string(NEW) is not None:
        raise Unknown("it has the crest cell already")
    ct = class_table(m)
    if ct.get(3) != "uirEmblemCompe" or ct.get(8) != "uirIconPosition" or ct.get(11) != "uirText":
        raise Unknown("classes %r" % {k: ct.get(k) for k in (3, 8, 11)})
    _, sub = m.sprite(ROW)
    tags, frames = m.tags_of(sub), m.frames(sub)
    if [(v & 0xfffff, v >> 20) for _, v in frames] != [(0, 3), (3, 1), (4, 0), (4, 2), (6, 0)]:
        raise Unknown("row frames %r" % frames)
    cells = [m.place_info(p) for p, _, _ in tags[:3]]
    if [(c.get('name'), c['depth']) for c in cells] != [("position", 1), ("playerName", 3), ("rect", 5)]:
        raise Unknown("row cells %r" % cells)
    if DEPTH in {m.place_info(p)['depth'] for p, tid, _ in tags if tid == 0x7f}:
        raise Unknown("depth %d taken" % DEPTH)
    objid = struct.unpack_from('<H', m.D, tags[0][0] + 10)[0]
    _, tsub = m.sprite(TEMPLATE_SPRITE)
    tp = next((p for p, tid, _ in m.tags_of(tsub)
               if tid == 0x7f and m.place_info(p).get('name') == TEMPLATE), None)
    if tp is None:
        raise Unknown("no %s" % TEMPLATE)
    _, size, t = m.tag(tp)
    if struct.unpack_from('<I', t, 4)[0] != 0x40426 or struct.unpack_from('<H', t, 12)[0] != 3 or size != 0x18:
        raise Unknown("%s is not the tag this copies" % TEMPLATE)
    sw = m.swaps_in(tp, 4 + size)
    name = m.name_offset(NEW)
    struct.pack_into('<HH', t, 8, DEPTH, objid)
    struct.pack_into('<H', t, 14, name)
    struct.pack_into('<ii', t, 16, TX * 20, TY * 20)
    struct.pack_into('<HH', t, 24, SCALE, SCALE)
    tw, sub = m.sprite(ROW)
    tags, frames = m.tags_of(sub), m.frames(sub)
    last = tags[2]
    m.insert(last[0] + ((last[2] + 3) & ~3) + 4, bytes(t), sw)
    struct.pack_into('<I', m.D, sub + 8, struct.unpack_from('<I', m.D, sub + 8)[0] + 1)
    for k, (fp, v) in enumerate(frames):
        start, n = v & 0xfffff, v >> 20
        if k == 0:
            n += 1
        else:
            start += 1
        struct.pack_into('<I', m.D, fp, start | (n << 20))
    w = struct.unpack_from('<I', m.D, tw)[0]
    struct.pack_into('<I', m.D, tw, (w & ~0x3fffff) | ((w & 0x3fffff) + len(t)))


def make(data):
    """the layout's bytes (WESYS or raw) -> the layout with the crest cell (WESYS)"""
    return M.rebuild(data, edit)


def has_crest(path):
    """a layout this wrote"""
    try:
        make(open(path, "rb").read())
    except Unknown as e:
        return "crest cell already" in str(e)
    except Exception:
        return False
    return False


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    get = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    root, game, base, out = get("--root"), get("--game"), get("--base"), get("--out")
    if not (root and game) and not (base and out):
        raise SystemExit(__doc__)
    src = None
    try:
        if not base:
            import mkcatflags
            src = mkcatflags.Source(game, root)
            # never a layout of ours (another world's, or this one installed elsewhere) as the base
            base = src.find(PACKAGE, lambda p: not has_crest(p))
            if not base:
                raise SystemExit("no %s in the sider roots or the game's CPKs" % PACKAGE)
        try:
            data = make(open(base, "rb").read())
        except Unknown as e:
            print("left as it is: %s is not the Select Team layout this knows (%s)" % (base, e))
            return 0
        out = out or os.path.join(root, *PACKAGE.split("/"))
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        open(out, "wb").write(data)
    finally:
        if src:
            src.close()
    print("wrote %s: crests in the Team List rows, from %s" % (out, base))
    return 0


if __name__ == "__main__":
    sys.exit(main())
