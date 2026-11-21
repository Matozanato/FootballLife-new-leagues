r"""python tools/test_b480_edit_noop.py [folder with the game's tables]

B480 round 3 (beta4r exe test, 17.11.2026): New leagues > Edit league... > OK with nothing changed
on the GigaPack's Kategoria Superiore wrote the recipe (md5 4908763b -> b40e59cf): the dialog sorted
the league's European places, [[1, 10], [0, 12], [2, 12]] became [[0, 12], [1, 10], [2, 12]], and
the page then remembered an Undo step (a compare of the whole recipe, 6.2-6.6 s of a stopped
window with the GigaPack) and saved. Now the same places keep the recipe's order, and OK with
nothing changed leaves the recipe as it was: the same bytes, no touch(), no Undo step, nothing to
save. A real change (one place more) is still kept and sorted as before.

The real LeagueDialog and New leagues page in this process (QT_QPA_PLATFORM=offscreen), the game's
tables (FL27's tables27, else FL26's). No game, nothing written.
"""
import copy, hashlib, json, os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QDialog


def md5(r):
    return hashlib.md5(json.dumps(r, indent=1, ensure_ascii=False).encode("utf-8")).hexdigest()


def main(tables):
    QApplication.instance() or QApplication([])
    import leaguebuilder as B
    from modstudio.project import Project
    from modstudio.pages import builder as PB
    p = Project(None)
    p.load_tables(tables)
    assert p.base and p.countries, "the tables in %s: %s" % (tables, p.tables_error)
    country = "Albania" if "Albania" in p.countries else sorted(p.countries)[0]
    ks = {"name": "Kategoria Superiore", "country": country, "clubs": 10, "legs": 4, "format": "league",
          "exchange": 3, "europe": [[1, 10], [0, 12], [2, 12]], "cup": True, "cup_name": "Kupa",
          "club_names": ["Club %d" % i for i in range(10)]}
    plain = {"name": "Kategoria e Pare", "country": country, "clubs": 12, "legs": 2, "format": "league",
             "exchange": 1, "above": "Kategoria Superiore", "club_names": ["Second %d" % i for i in range(12)]}
    p.recipe["leagues"] = [ks, plain]
    app = types.SimpleNamespace(project=p, game=types.SimpleNamespace(ok=lambda: False, folder=""), settings={},
                                page=lambda n: None, pages={}, open_page=lambda n: None,
                                say=lambda *a, **k: None, busy=lambda *a: None)
    page = PB.NewLeagues(app)
    touched = []
    real_touch = p.touch
    p.touch = lambda: (touched.append(1), real_touch())
    p._forget()
    plan = {}

    def finish(self):
        # OK pressed on the dialog as it opened, or after plan["more"] added a place
        if plan.get("more"):
            plan["more"](self)
        self.ok()
        return self.result() == QDialog.Accepted
    real = PB.LeagueDialog.finish

    def box(*a, **k):                   # a message box would wait for a click offscreen
        raise AssertionError("a box came up: %r" % (a[1:],))
    PB.error = PB.info = PB.ask = box
    PB.LeagueDialog.finish = finish
    try:
        for i, name in ((0, "Kategoria Superiore"), (1, "Kategoria e Pare")):
            page.selected = lambda i=i: i
            before, held = md5(p.recipe), p.recipe["leagues"][i]
            touched.clear()
            page.edit()
            assert md5(p.recipe) == before, "%s: OK with nothing changed keeps the recipe's bytes" % name
            assert p.recipe["leagues"][i] is held, "%s: the league's own dict stays" % name
            assert not touched and not p.dirty and not p.can_undo(), \
                "%s: no touch, nothing to save, no Undo step (touched %d, dirty %s)" % (name, len(touched), p.dirty)
        assert p.recipe["leagues"][0]["europe"] == [[1, 10], [0, 12], [2, 12]], p.recipe["leagues"][0]["europe"]

        # a real change: one more place; kept, sorted as before, remembered for Undo
        def more(d):
            d.europe.set_places(list(d.europe.places()) + [[3, 12]])
        plan["more"] = more
        page.selected = lambda: 0
        page.edit()
        got = p.recipe["leagues"][0]["europe"]
        assert got == sorted([[1, 10], [0, 12], [2, 12], [3, 12]]), got
        assert touched and p.dirty and p.can_undo(), "a real change is touched and remembered"
    finally:
        PB.LeagueDialog.finish = real
    print("test_b480_edit_noop: ok (OK with nothing changed: same bytes, no touch; a new place: kept and sorted)")


if __name__ == "__main__":
    t27 = os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables27")
    main(sys.argv[1] if len(sys.argv) > 1 else (t27 if os.path.isdir(t27) else
                                                os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables")))
