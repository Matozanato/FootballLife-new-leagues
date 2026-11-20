"""Does a world zip name a folder of the PC that made it? (B430, 12.11.2026)

    python tools/checkworldzip.py <world.zip> [word ...]

Reads every text file of the zip (json, txt, ini, lua, xml, csv, md) and says PASS when none of
them holds a path of a disk ("C:/Users/...", "D:" and a backslash) or of a share, and when no
file's name or text holds one of the words given (a maker's own check: his name, a folder of
his). Game files (bin, ftex, ...) are not read. Exit code 1 on a FAIL.
"""
import re, sys, zipfile

BS = chr(92)
QUOTES = chr(34) + chr(39)
TEXT = re.compile(r"\.(json|txt|ini|lua|xml|csv|tsv|md|log|cfg)$", re.I)
# a letter, a colon, a slash of either kind, something that is no space; or a share
DISK = "(?<![A-Za-z0-9])[A-Za-z]:(?:/|" + BS * 2 + "{1,2})[^" + BS * 2 + "/" + BS + "s" + QUOTES + "]"
# a share begins a word with two backslashes; in a JSON text those are written as four, and two
# there are one backslash of a path that starts nowhere on a disk ("league" + "club" inside a pack)
SHARE = "(?<![^" + BS + "s=(,:" + QUOTES + "])" + BS * 2 + "{%d}[A-Za-z0-9][^" + BS + "s" + QUOTES + "]*" + BS * 2 + "[^" + BS + "s" + QUOTES + "]"
PATH = re.compile(DISK + "|" + SHARE % 2)
PATH_JSON = re.compile(DISK + "|" + SHARE % 4)


def paths(text, json_text=False):
    """the paths of a disk or a share in a text (the start of each, 90 characters at most)"""
    return [text[m.start():m.start() + 90].split(chr(10))[0] for m in (PATH_JSON if json_text else PATH).finditer(text)]


def check(zip_path, words=()):
    """-> (text files read, [(file, what was found)])"""
    bad, n = [], 0
    low = [w.lower() for w in words if w]
    with zipfile.ZipFile(zip_path) as z:
        for i in z.infolist():
            name = i.filename
            for w in low:
                if w in name.lower():
                    bad.append((name, "name holds %r" % w))
            if i.is_dir() or not TEXT.search(name):
                continue
            n += 1
            text = z.read(name).decode("utf-8", "replace")
            got = paths(text, name.lower().endswith(".json"))
            if got:
                bad.append((name, "%d path(s), the first: %s" % (len(got), got[0])))
            if low:
                tl = text.lower()
                for w in low:
                    k = tl.count(w)
                    if k:
                        at = tl.find(w)
                        bad.append((name, "%d x %r, the first: ...%s..." % (k, w, text[max(0, at - 30):at + 40].replace("\n", " "))))
    return n, bad


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    n, bad = check(sys.argv[1], sys.argv[2:])
    for name, what in bad[:60]:
        print("  %s: %s" % (name, what))
    if len(bad) > 60:
        print("  ... and %d more" % (len(bad) - 60))
    print("%s: %d text file(s) read, %d with a path of the maker's PC%s"
          % ("FAIL" if bad else "PASS", n, len(bad), " or a word given" if len(sys.argv) > 2 else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
