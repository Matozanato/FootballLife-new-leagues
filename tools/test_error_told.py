"""A click that fails says so (12.11.2026).

    python tools/test_error_told.py

An unexpected error in a button's code went to errors.log and nowhere else: the button "did
nothing" (Xxspedd, #beta-reports: "Edit league opens no window") and the report had nothing to go
by. The status line now names the file. Windows refusing a write keeps its own box (B14).
"""
import os, sys, tempfile

TMP = tempfile.mkdtemp(prefix="fl26_told_")
os.environ["APPDATA"] = TMP
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication

qa = QApplication.instance() or QApplication([])
from modstudio import app as A, i18n

N = [0]


def ok(name, cond):
    N[0] += 1
    assert cond, name
    print("ok %d - %s" % (N[0], name))


class Win:
    def __init__(self):
        self.said = []

    def status(self, text):
        self.said.append(text)


def raised(err):
    try:
        raise err
    except BaseException:
        return sys.exc_info()


def main():
    w, before = Win(), []
    A.main_window = lambda: w
    hook = A.denied_hook(lambda *a: before.append(a[1]))
    log = os.path.join(A.APPDIR, "errors.log")
    ok("the folder of this test is the one written to", os.path.abspath(A.APPDIR).startswith(os.path.abspath(TMP)))
    hook(*raised(ValueError("the league has no row")))
    ok("an error of a click: written to errors.log", "the league has no row" in open(log, encoding="utf-8").read())
    ok("... the status line says so and names the file", len(w.said) == 1 and log in w.said[0]
       and "unexpected error" in w.said[0])
    ok("... and the hook before this one still gets it", len(before) == 1 and isinstance(before[0], ValueError))
    hook(*raised(KeyboardInterrupt()))
    ok("Ctrl+C is no error of a click: nothing said", len(w.said) == 1 and len(before) == 2)
    A.main_window = lambda: None
    hook(*raised(ValueError("no window yet")))
    ok("no window yet: written, nothing breaks", "no window yet" in open(log, encoding="utf-8").read() and len(before) == 3)

    class Bad:
        def status(self, text):
            raise RuntimeError("the window is going away")
    A.main_window = lambda: Bad()
    hook(*raised(ValueError("late")))
    ok("a window that cannot say it: the error is still written and passed on",
       "late" in open(log, encoding="utf-8").read() and len(before) == 4)
    en = "That did not work (an unexpected error). Send this file with your report: %s"
    for code in ("es", "fr", "pt", "hr"):
        i18n.set_language(code)
        t = i18n._(en)
        ok("%s: translated, the file's place kept (%s)" % (code, t[:28]), t != en and t.count("%s") == 1)
    i18n.set_language("en")
    print("all %d checks passed" % N[0])


if __name__ == "__main__":
    main()
