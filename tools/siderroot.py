"""python siderroot.py <_FL26Root>   -> make that the one active _FL26* cpk.root in sider.ini

Every test world is a livecpk root, and only one of them may be live at a time or the
pesdb tables layer in an order nobody asked for.  This comments out every _FL26 root and
uncomments (or inserts, above the first root) the one named. Use --require-livecpk for a world whose runtime depends on
its tables being loaded. Prints what is active.
"""
import os, re, sys

INI = os.path.join(os.environ.get("FL26_DIR", r"C:\Football Life 2026"), "SiderAddons", "sider.ini")
LIVECPK = re.compile(r"^\s*livecpk\.enabled\s*=", re.I)


def enable_livecpk(lines):
    """Write one active setting. Listing roots does not turn on Sider's file replacement."""
    positions = [i for i, line in enumerate(lines) if LIVECPK.match(line)]
    if positions:
        lines[positions[0]] = "livecpk.enabled = 1"
        for i in reversed(positions[1:]):
            del lines[i]
    else:
        section = next((i for i, line in enumerate(lines) if line.strip().lower() == "[sider]"), -1)
        lines.insert(section + 1, "livecpk.enabled = 1")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    want = sys.argv[1]
    lines = open(INI, encoding="utf-8", errors="replace").read().splitlines()
    # Match the root's own name, not a substring of the line.  Asking for _FL26Reg3 while
    # _FL26Reg39 is also listed used to activate _FL26Reg39 and say so in a line that reads
    # almost the same, which is a whole boot spent measuring the wrong world.
    def rootname(line):
        v = line.split("=", 1)[1].strip().strip('"').strip("'") if "=" in line else ""
        return v.replace("/", "\\").rstrip("\\").rsplit("\\", 1)[-1]

    out, found = [], False
    for l in lines:
        s = l.lstrip("#").strip()
        if s.startswith("cpk.root") and "_FL26" in s:
            if rootname(s) == want:
                if found:
                    raise SystemExit("sider.ini lists %s more than once" % want)
                l, found = s, True
            else:
                l = "#" + s
        out.append(l)
    if not found:
        first = next((i for i, l in enumerate(out) if l.strip().startswith("cpk.root")), len(out))
        out.insert(first, r'cpk.root = ".\livecpk\%s"' % want)
    if "--require-livecpk" in sys.argv[2:]:
        enable_livecpk(out)
    open(INI, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("active:", [l for l in out if l.strip().startswith("cpk.root") and "_FL26" in l])
    return 0


if __name__ == "__main__":
    sys.exit(main())
