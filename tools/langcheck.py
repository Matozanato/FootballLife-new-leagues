"""Which UI texts a translation is missing, and which translations nothing asks for any more.

    python tools/langcheck.py                 per language: strings translated, strings missing
    python tools/langcheck.py --missing es    the English strings es.json has no translation for
    python tools/langcheck.py --unused        keys in lang/*.json that no _("...") uses any more

The strings are collected from the _("...") / _('...') calls in modstudio/*.py and
modstudio/pages/*.py with ast, so a text split over several lines with implicit concatenation
counts as one string, and a _( ) whose argument is not a plain string literal is reported and
left out (it cannot be compared with a json key).

Translation files: modstudio/lang/<code>.json is the file this tool reads; i18n.py reads
tools/lang/<code>.json (the League Builder's own) as well, so the summary also says how many
strings that second file covers.
"""
import argparse, ast, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(HERE, "modstudio")
PAGES = os.path.join(MOD, "pages")
LANGS = ("es", "fr", "hr")


def sources():
    """the modstudio python files the UI text lives in (modstudio/*.py, modstudio/pages/*.py)"""
    out = []
    for d in (MOD, PAGES):
        if os.path.isdir(d):
            out += [os.path.join(d, n) for n in sorted(os.listdir(d)) if n.endswith(".py")]
    return out


def ui_strings():
    """(the strings _("...") asks for, ["file:line", ...] calls with a non-literal argument)"""
    seen, odd = set(), []
    for path in sources():
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "_":
                continue
            a = node.args[0] if len(node.args) == 1 else None
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                seen.add(a.value)
            else:
                odd.append("%s:%d" % (os.path.relpath(path, HERE).replace("\\", "/"), node.lineno))
    return seen, odd


def translations(code):
    """{"text": {...}} of modstudio/lang/<code>.json, and the same for tools/lang/<code>.json"""
    out = []
    for d in (os.path.join(MOD, "lang"), os.path.join(HERE, "lang")):
        p = os.path.join(d, "%s.json" % code)
        if not os.path.exists(p):
            out.append({})
            continue
        try:
            with open(p, encoding="utf-8") as f:
                j = json.load(f)
        except ValueError as e:
            print("langcheck: %s is not valid json (%s)" % (p, e), file=sys.stderr)
            j = {}
        out.append(dict(j.get("text") or {}))
    return out[0], out[1]


def report():
    used, odd = ui_strings()
    print("%d UI strings in %d files" % (len(used), len(sources())))
    for code in LANGS:
        main, lb = translations(code)
        have = set(main) | set(lb)
        miss = used - have
        print("%s: %4d translated, %4d missing (%.0f%%), %d from tools/lang/%s.json" % (
            code, len(have & used), len(miss), 100.0 * len(miss) / len(used) if used else 0.0,
            len((set(lb) & used) - set(main)), code))
    if odd:
        print("%d _( ) calls have a non-literal argument and were left out: %s"
              % (len(odd), ", ".join(odd[:8]) + (" ..." if len(odd) > 8 else "")))


def missing(code):
    used, _odd = ui_strings()
    main, lb = translations(code)
    for s in sorted(used - (set(main) | set(lb))):
        print(s)


def unused():
    used, _odd = ui_strings()
    src = "".join(open(p, encoding="utf-8").read() for p in sources())
    total = nowhere = 0
    for code in LANGS:
        main, _lb = translations(code)
        stale = sorted(set(main) - used)
        total += len(stale)
        gone = [k for k in stale if json.dumps(k)[1:-1] not in src]
        nowhere += len(gone)
        print("%s.json: %d keys no _(\"...\") asks for (%d of them still show up in the sources, so"
              " they are probably passed to _( ) as a variable; %d show up nowhere)"
              % (code, len(stale), len(stale) - len(gone), len(gone)))
        for k in stale:
            print("   %s" % k.replace("\n", "\\n"))
    print("total: %d keys, %d of them nowhere in the sources" % (total, nowhere))


def main(a):
    if a and a[0] == "--missing":
        code = a[1] if len(a) > 1 else ""
        if code not in LANGS:
            print("usage: langcheck.py --missing %s" % "|".join(LANGS), file=sys.stderr)
            return 2
        missing(code)
    elif a and a[0] == "--unused":
        unused()
    elif a and a[0] in ("-h", "--help"):
        print(__doc__)
    elif a:
        print(__doc__, file=sys.stderr)
        return 2
    else:
        report()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
