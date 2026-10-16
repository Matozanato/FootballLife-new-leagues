"""the program speaks English; lang/<code>.json gives another language.

    {"text": {"English text": "translation", ...},
     "log":  [["regular expression", "replacement"], ...]}   # for lines the core prints

The English text is the key, so a string with no translation simply stays English.  The League
Builder's own file (tools/lang/<code>.json) is read too, so its texts need no second copy.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT, RULES = {}, []
CODE = "en"
LANGUAGES = [("en", "English"), ("hr", "Hrvatski"), ("es", "Español"), ("pt", "Português"),
             ("fr", "Français")]


def _(s):
    return TEXT.get(s, s)


def tr(line):
    for pat, rep in RULES:
        line = re.sub(pat, rep, line)
    return line


def _dirs():
    base = getattr(sys, "_MEIPASS", None)
    out = [os.path.join(HERE, "lang"), os.path.join(os.path.dirname(HERE), "lang")]
    if base:
        out = [os.path.join(base, "modstudio", "lang"), os.path.join(base, "lang")] + out
    return out


_QT = []
_QT_FILE = {"pt": "qtbase_pt_BR"}


def _qt_buttons():
    """0.2.4: the buttons Qt draws itself (Yes / No of a question, OK / Cancel of a name box)
    stayed English in every language; Qt's own translations ship with PySide6"""
    try:
        from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator
    except ImportError:
        return
    app = QCoreApplication.instance()
    if app is None:
        return
    for t in _QT:
        app.removeTranslator(t)
    del _QT[:]
    if CODE == "en":
        return
    t = QTranslator()
    if t.load(_QT_FILE.get(CODE, "qtbase_" + CODE), QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(t)
        _QT.append(t)


def set_language(code):
    global CODE
    CODE = code or "en"
    TEXT.clear()
    del RULES[:]
    _qt_buttons()
    if CODE == "en":
        return
    for d in reversed(_dirs()):              # the builder's file first, ours on top of it
        p = os.path.join(d, CODE + ".json")
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    j = json.load(f)
            except (OSError, ValueError):
                continue
            TEXT.update(j.get("text", {}))
            RULES[:0] = j.get("log", [])
