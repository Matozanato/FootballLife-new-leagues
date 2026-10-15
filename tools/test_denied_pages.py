"""python tools/test_denied_pages.py

B43 (ZeDosCaes21, 15.10.): with the game under C:\Program Files (x86), Import kits on the Kits
page stopped with a raw "[WinError 5] Acesso negado: '...\content\kits\1o divisao'" box, the
Windows message in the user's language, and said nothing about what to do. The pages that write
into the game folder and catch the error themselves (Import kits, a content server's Save, a
restore point put back, Move the Edit save aside) now hand a refused write to ui.denied: the box
that says "run Mod Studio as administrator or move the game out of Program Files", with a
Restart as administrator button. Import kits also asks before the matching (ui.can_write).

The box is caught (ui.denied_box replaced), no window is shown. No game.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from modstudio import ui

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    QApplication.instance() or QApplication([])
    shown = []
    ui.denied_box = lambda parent, path, game_folder=None, title="": shown.append(path)

    kits = r"C:\Program Files (x86)\SP Football Life 2026\SiderAddons\content\kits\1º divisão"
    e = OSError(None, "Acesso negado", kits, 5)          # what shutil raised on his PC
    ok("WinError 5 is a PermissionError", isinstance(e, PermissionError))
    ok("a refused write gets the box", ui.denied(None, e) is True)
    ok("the box names the folder Windows refused", shown == [kits])

    shown.clear()
    ok("a missing file is not a refused write", ui.denied(None, FileNotFoundError(2, "gone", "x")) is False)
    ok("a ValueError is not a refused write", ui.denied(None, ValueError("bad map line")) is False)
    ok("no box for them", shown == [])

    # each page that catches the write error itself goes through ui.denied first
    pages = os.path.join(HERE, "modstudio", "pages")
    for f, what in (("kits.py", "Could not copy the kits"), ("content.py", "_(\"Could not save: %s\") % e"),
                    ("restore.py", 'error(self, "Restore points", str(e))'),
                    ("builder.py", '"Move the Edit save aside", str(e)')):
        lines = open(os.path.join(pages, f), encoding="utf-8").read().splitlines()
        hits = [k for k, l in enumerate(lines) if what in l]
        ok("%s: %s comes after ui.denied" % (f, what),
           hits and any(re.search(r"if not denied\(self, e\):", lines[k - 1]) for k in hits))
    src = open(os.path.join(pages, "kits.py"), encoding="utf-8").read()
    j = src.index("def import_kits")
    ok("Import kits asks can_write before the matching dialog",
       src.index("can_write(self, self.app.game)", j) < src.index("_dialog_class()(v)", j))
    print("test_denied_pages: ok (%d)" % N)


if __name__ == "__main__":
    main()
