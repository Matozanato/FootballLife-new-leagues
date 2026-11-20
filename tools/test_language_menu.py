"""python tools/test_language_menu.py -- the Language menu says each language in its own words in every
language of the program (09.11., UI test in Spanish: "Inglés" among Hrvatski, Español, Français: the
flag that keeps a label untranslated compared a tuple with a list and was never true)."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from modstudio import i18n, app

qa = QApplication.instance() or QApplication([])
want = [name for code, name in i18n.LANGUAGES]
fails = 0
for code, _n in i18n.LANGUAGES:
    i18n.set_language(code)
    b = app.Main._menu_button(None, "Language", [(name, (lambda c=c: None), True) for c, name in i18n.LANGUAGES])
    got = [a.text() for a in b.menu().actions()]
    ok = got == want
    fails += not ok
    print(("ok   " if ok else "FAIL ") + "%s: %s" % (code, ", ".join(got)))
    # the other items still go through the translation
    b = app.Main._menu_button(None, "Help", [("User guide", lambda: None)])
    if code != "en" and b.menu().actions()[0].text() == "User guide" and i18n._("User guide") != "User guide":
        fails += 1
        print("FAIL %s: a translated item came out in English" % code)
i18n.set_language("en")
print("FAILED %d" % fails if fails else "all ok")
sys.exit(1 if fails else 0)
