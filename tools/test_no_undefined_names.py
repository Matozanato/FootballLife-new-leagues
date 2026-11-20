r"""python tools/test_no_undefined_names.py

A gate: no undefined name in the code that goes into FL26ModStudio.exe. Candidate beta4t (18.11.2026)
went to FL Testovi with every GUI Export of a world stopping on

    NameError: name 'rpath' is not defined

(a local of do_export used in export_as's go(), which runs only after a click, a worker and a dialog,
so no test that called installer.export_world itself ever ran it). pyflakes sees it without running
anything; this test runs pyflakes over

  * tools/modstudio (every .py: mszip puts the whole package into the exe), and
  * the tools modules the exe takes: mszip.HIDDEN and modstudio_main.py, then every tools module any of
    them imports (import x / from x import y, also inside functions), as PyInstaller follows them,

and fails on any undefined name, undefined local (referenced before assignment) or undefined name in
__all__. Without pyflakes it says SKIPPED loudly and checks nothing (pip install pyflakes).
"""
import ast, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def tools_module(name):
    """tools\\<name>.py for a top-level module of tools, else None"""
    p = os.path.join(HERE, name.split(".")[0] + ".py")
    return p if os.path.isfile(p) else None


def imported(path):
    """the top-level module names a file imports (anywhere in it)"""
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), path)
    except SyntaxError as e:
        raise AssertionError("%s does not parse: %s" % (path, e))
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and not n.level and n.module:
            out.add(n.module.split(".")[0])
    return out


def exe_files():
    """the .py files of the exe: modstudio's, modstudio_main.py and the tools modules they reach"""
    files = set()
    pkg = os.path.join(HERE, "modstudio")
    for d, subs, fs in os.walk(pkg):
        subs[:] = [s for s in subs if s != "__pycache__"]
        files.update(os.path.join(d, f) for f in fs if f.endswith(".py"))
    import mszip
    todo = [p for p in (tools_module(h) for h in mszip.HIDDEN) if p]
    main = os.path.join(HERE, "modstudio_main.py")
    if os.path.isfile(main):
        todo.append(main)
    todo += sorted(files)
    seen = set()
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        for m in imported(p):
            q = tools_module(m)
            if q and q not in seen:
                todo.append(q)
    return sorted(seen | files)


def main():
    try:
        from pyflakes import api, messages, reporter as R
    except ImportError:
        bar = "!" * 78
        print("%s\nSKIPPED: pyflakes is not importable (pip install pyflakes) -- NOTHING WAS CHECKED,\n"
              "the exe's code may have undefined names (beta4t: NameError rpath in Export)\n%s" % (bar, bar))
        sys.stderr.write("test_no_undefined_names: SKIPPED (no pyflakes)\n")
        sys.exit(0)
    bad_kinds = (messages.UndefinedName, messages.UndefinedLocal, messages.UndefinedExport)

    # the checker itself first: it must see the beta4t bug in a copy of its shape
    probe = ("def do_export(self, mine):\n    rpath = self.path if mine else None\n    return rpath\n\n"
             "def export_as(self, mine):\n    def go(log):\n        return rpath\n    return go\n")
    got = []

    class Keep(R.Reporter):
        def __init__(self):
            super().__init__(sys.stdout, sys.stderr)

        def flake(self, m):
            got.append(m)

        def syntaxError(self, filename, msg, lineno, offset, text):
            got.append(("syntax", filename, lineno, msg))

        def unexpectedError(self, filename, msg):
            got.append(("unexpected", filename, msg))

    api.check(probe, "probe.py", Keep())
    assert [m for m in got if isinstance(m, messages.UndefinedName) and m.message_args == ("rpath",)], \
        "pyflakes did not see the undefined rpath of the probe: %r" % got
    print("ok 1 - pyflakes %s sees the beta4t bug (undefined rpath in a nested go())"
          % __import__("pyflakes").__version__)

    files = exe_files()
    rel = lambda p: os.path.relpath(p, HERE)
    must = ["modstudio\\pages\\builder.py", "modstudio\\ui.py", "leaguebuilder.py", "idledger.py", "lbplayers.py"]
    have = {os.path.normcase(rel(p)) for p in files}
    assert all(os.path.normcase(m) in have for m in must), [m for m in must if os.path.normcase(m) not in have]
    print("ok 2 - %d files of the exe (%d of modstudio, %d tools modules)"
          % (len(files), sum(1 for p in files if rel(p).startswith("modstudio")),
             sum(1 for p in files if not rel(p).startswith("modstudio"))))

    del got[:]
    for p in files:
        api.check(open(p, encoding="utf-8").read(), rel(p), Keep())
    broken = [g for g in got if isinstance(g, tuple)]
    assert not broken, "pyflakes could not read: %r" % broken
    bad = [m for m in got if isinstance(m, bad_kinds)]
    for m in bad:
        print("  %s:%d: %s" % (m.filename, m.lineno, m.message % m.message_args))
    assert not bad, "%d undefined name(s) in the exe's code (each a NameError when that line runs)" % len(bad)
    print("ok 3 - no undefined name, undefined local or undefined __all__ name in the %d files" % len(files))
    print("test_no_undefined_names: ok (3)")


if __name__ == "__main__":
    main()
