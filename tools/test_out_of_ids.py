r"""python tools/test_out_of_ids.py

B154 (Tysonche35 18.10.): a league added to the Europack (220/255 competitions) and Build stopped
with "no free competition or regulation ids left for FA Trophy" -- nothing about what to do, so the
world's folder was then deleted by hand. The message now says the world is full and what to untick,
in every language of Mod Studio.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import leaguebuilder as B
from modstudio import i18n

N = 0


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


e = B.out_of_ids("FA Trophy")
ok("a BuildError naming the cup and what to untick", isinstance(e, B.BuildError)
   and "FA Trophy" in str(e) and "Cups of our countries" in str(e) and "255" in str(e))
for code, word in (("hr", "Kupovi naših država"), ("es", "Copas de nuestros países"),
                   ("fr", "Coupes de nos pays"), ("pt", "Taças dos nossos países")):
    i18n.set_language(code)
    t = i18n.tr("error: " + str(e))
    ok("%s: translated, the cup's name kept" % code, word in t and "FA Trophy" in t and "Untick" not in t)
i18n.set_language("en")
ok("continental cups too", "Cups of our countries" in str(B.out_of_ids("the continental cups")))
print("test_out_of_ids: ok (%d)" % N)
