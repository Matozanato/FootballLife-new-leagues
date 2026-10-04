"""python siderroot.py <_FL26Root>   -> make that the one active _FL26* cpk.root in sider.ini

Every test world is a livecpk root, and only one of them may be live at a time or the
pesdb tables layer in an order nobody asked for.  This comments out every _FL26 root and
uncomments (or inserts, above the first root) the one named, then prints what is active.
"""
import os, sys

INI = os.path.join(os.environ.get("FL26_DIR", r"C:\Football Life 2026"), "SiderAddons", "sider.ini")


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
        first = next(i for i, l in enumerate(out) if l.strip().startswith("cpk.root"))
        out.insert(first, r'cpk.root = ".\livecpk\%s"' % want)
    open(INI, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("active:", [l for l in out if l.strip().startswith("cpk.root") and "_FL26" in l])
    return 0


if __name__ == "__main__":
    sys.exit(main())
