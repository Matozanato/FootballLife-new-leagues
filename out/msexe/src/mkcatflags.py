r"""mkcatflags.py -- a country's own flag as the heading picture of its category in
Master League -> Database -> Competition Info.

The category list draws its heading pictures from common/menu/general/compeCategorySelect.bin, an
AFP package (tools/afp.py) with one drawn flag per shipped country. A new country has no picture
there, so tools/mkregnames.py had it borrow a generic one. This writes a copy of that package into
the world with one more picture per country of the world -- 'compeCategory-f<flag id>', drawn from
the country's flag the way the shipped ones are drawn -- and prints the region -> picture map that
mkregnames.py --map takes.

    python mkcatflags.py --root <world livecpk root> --game <game folder> [--world <file>]
                         [--base <package>]

  --root   the world's livecpk root: the package is written there, and a flag picture it carries
           (common/render/symbol/flag/flag_<id>_l.png, written by the League Builder from the
           user's own picture) is used before the game's own
  --game   where the game's flags and the package come from: the sider.ini roots other than the
           world, in their order (FL26 ships its own package in CompMenus), then the game's CPKs
  --world  the world file that says which region is which country: fl26world.txt in the root
           (a League Builder package), else the game's SiderAddons/modules/fl26world.txt
  --base   this package instead

Nothing shipped changes: the new pictures go below the ones already there, in the world's copy.
"""
import glob, os, re, shutil, struct, sys, tempfile
import siderdir

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import afp

PACKAGE = "common/menu/general/compeCategorySelect.bin"
FLAGS = "common/render/symbol/flag/"
KEY = "compeCategory-f%d"
# the regions the shipped heading table already has a row for (python mkregnames.py --show):
# their heading is the game's, so they need no picture here
SHIPPED = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 28}


def world_countries(path):
    """{region: flag id} from a world file"""
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("league "):
            kv = dict(re.findall(r"(\w+)=(\S+)", line))
            if "region" in kv and "country" in kv:
                out.setdefault(int(kv["region"]), int(kv["country"]))
    return out


def sider_roots(game):
    """the cpk.root folders sider.ini switches on, in its order"""
    sider = siderdir.find(game)
    roots = []
    if os.path.exists(os.path.join(sider, "sider.ini")):
        for line in open(os.path.join(sider, "sider.ini"), encoding="utf-8", errors="replace"):
            m = re.match(r'\s*cpk\.root\s*=\s*"([^"]+)"', line)
            if m:
                roots.append(os.path.normpath(os.path.join(sider, m.group(1))))
    return roots


class Source:
    """a file of the game as the game sees it: the sider roots in order, then the CPKs"""

    def __init__(self, game, skip):
        self.game, self.skip = game, os.path.normcase(os.path.normpath(skip))
        self.roots = [r for r in sider_roots(game) if os.path.normcase(r) != self.skip]
        self.tmp, self.toc = None, {}

    def find(self, rel, ok=lambda p: True):
        for r in self.roots:
            p = os.path.join(r, *rel.split("/"))
            if os.path.exists(p) and ok(p):
                return p
        return self.from_cpk(rel)

    def from_cpk(self, rel):
        import cpkread
        if self.tmp is None:
            self.tmp = tempfile.mkdtemp(prefix="fl26cat")
        p = os.path.join(self.tmp, *rel.split("/"))
        if os.path.exists(p):
            return p
        cpks = sorted(glob.glob(os.path.join(self.game, "download", "*.cpk")), reverse=True) + \
            sorted(glob.glob(os.path.join(self.game, "Data", "*.cpk")), reverse=True)
        for c in cpks:
            if c not in self.toc:
                try:
                    self.toc[c] = set(cpkread.names(c))
                except (OSError, ValueError, KeyError, IndexError):
                    self.toc[c] = set()
            if rel in self.toc[c]:
                cpkread.extract(c, self.tmp, [rel])
                return p if os.path.exists(p) else None
        return None

    def close(self):
        if self.tmp:
            shutil.rmtree(self.tmp, ignore_errors=True)


def ours(path):
    """a package this already wrote (in another world, or this one installed elsewhere): never
    a base, or the pictures would pile up"""
    try:
        return any(re.match(r"compeCategory-f\d+$", nm)
                   for nm, _, _ in afp.Package(open(path, "rb").read()).pictures())
    except (OSError, ValueError, struct.error):
        return False


def heading(flag_png, cell=81):
    """the category picture of a flag, drawn as the shipped ones are: the flag 73 x 48 inside a
    black 2-pixel frame at (2, 15) of a transparent cell.  The game's flag_<id>_l.png is a 256
    square with the flag inside a grey border at (10, 48)-(246, 208); other sizes scale."""
    from PIL import Image
    src = Image.open(flag_png).convert("RGBA")
    s = src.width / 256.0
    flag = src.crop((round(10 * s), round(48 * s), round(246 * s), round(208 * s)))
    out = Image.new("RGBA", (cell, cell), (255, 255, 255, 0))
    out.paste(Image.new("RGBA", (77, 52), (0, 0, 0, 255)), (2, 15))
    out.paste(flag.resize((73, 48), Image.LANCZOS), (4, 17))
    return out


def main():
    argv = sys.argv[1:]
    get = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    root, game = get("--root"), get("--game")
    if not root or not game:
        raise SystemExit(__doc__)
    world = get("--world") or next((p for p in (os.path.join(root, "fl26world.txt"),
        os.path.join(siderdir.find(game), "modules", "fl26world.txt")) if os.path.exists(p)), None)
    if not world:
        raise SystemExit("no fl26world.txt in %s or the game's modules folder" % root)
    regions = dict((r, f) for r, f in world_countries(world).items() if r not in SHIPPED)
    if not regions:
        print("the world has no league with a region and a country; nothing to draw")
        return 0
    src = Source(game, root)
    try:
        base = get("--base") or src.find(PACKAGE, lambda p: not ours(p))
        if not base:
            raise SystemExit("no %s in the sider roots or the game's CPKs" % PACKAGE)
        pkg = afp.Package(open(base, "rb").read())
        have = {nm for nm, _, _ in pkg.pictures()}
        items, keys, missing = [], {}, []
        for fid in sorted(set(regions.values())):
            nm = KEY % fid
            own = os.path.join(root, *FLAGS.split("/"), "flag_%d_l.png" % fid)
            png = own if os.path.exists(own) else src.find(FLAGS + "flag_%d_l.png" % fid)
            if not png:
                missing.append(fid)
                continue
            if nm not in have:
                items.append((nm, heading(png)))
            keys[fid] = nm
        if items:
            pkg.add_pictures(items)
        out = os.path.join(root, *PACKAGE.split("/"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(pkg.pack())
    finally:
        src.close()
    print("wrote %s: %d pictures added to %s" % (out, len(items), base))
    if missing:
        print("  no flag picture for country %s -- those regions keep the generic heading"
              % ", ".join(map(str, missing)))
    print("map " + ",".join("%d=%s" % (rid, keys[fid][len("compeCategory-"):])
                            for rid, fid in sorted(regions.items()) if fid in keys))
    return 0


if __name__ == "__main__":
    sys.exit(main())
