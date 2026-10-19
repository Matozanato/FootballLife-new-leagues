"""python test_restore_reasons.py -- Restore points says why a copy was kept in the window's language
(B134, UI test in French 18.10.: "Switch on: kits map" and the rest stayed English). The index keeps
the reason in English, so old restore points are said in the language too, the names in them as
they are; a reason it does not know stays as it is."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modstudio import i18n
from modstudio.pages import restore as R

N = 0
B = chr(92)
# the reasons on a PC that ran 0.2.4 (E:, backups.json, 19.10.)
SEEN = ["replaced by FL26 Modpack NL15B r2", "Your world: switch on _FL26MyWorld",
        "world _FL26Old renamed to _FL26New", "Switch on: home stadiums map", "Switch on: menus map",
        "Switch on _FL26M2400S: the world file", "Switch on _FL26M2400S: its leagues in the Kick Off list",
        "Switch on: scoreboards map", "Build and install _FL26MyWorld", "Switch on: kits map",
        "Switch on _FL26M2400S: its own module", "Import your world: switch on _FL26M2400E",
        "merge from FL26-Modpack-NL15B7-r12", "removing FL26-Modpack-Europe-eu1", "Install the modules",
        "Install the modules: replaced by Mod Studio's", "profile As found", "installed FL26-Modpack-Europe-eu4",
        "Mod Studio's modules switched on", "Install the modules: livecpk" + B + "_FL26X loaded",
        "world _FL26Gone deleted: its lines taken out", "world _FL26Gone deleted"]


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


def main():
    i18n.set_language("en")
    ok("English as it is", all(R.reason_text(r) == r for r in SEEN))
    ok("an unknown reason as it is", R.reason_text("something else") == "something else" and R.reason_text("") == "")
    for code in ("es", "fr", "pt", "hr"):
        i18n.set_language(code)
        said = {r: R.reason_text(r) for r in SEEN}
        left = [r for r, t in said.items() if t == r and not r.startswith("profile ")]
        ok("%s: every reason said in the language %s" % (code, left[:2]), not left)
        names = [w.rstrip(":") for r in SEEN for w in r.split() if w.startswith(("_FL26", "FL26")) or "livecpk" in w]
        ok("%s: the world and mod names kept" % code,
           all(any(n in t for t in said.values()) for n in names))
        ok("%s: %s" % (code, said["Switch on _FL26M2400S: the world file"]),
           "_FL26M2400S" in said["Switch on _FL26M2400S: the world file"])
        ok("%s: renamed keeps both names in order" % code,
           0 <= said["world _FL26Old renamed to _FL26New"].index("_FL26Old")
           < said["world _FL26Old renamed to _FL26New"].index("_FL26New"))
    i18n.set_language("en")
    print("1..%d" % N)


if __name__ == "__main__":
    main()
