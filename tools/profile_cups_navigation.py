"""Read-only navigation benchmark using the actual Main.open_page path.

python tools/profile_cups_navigation.py --tables <pesdb> [--recipe <recipe.json>]
Settings/autosaves live in a temporary APPDATA; source tables/recipes are only read.
The default fixture has 86 top divisions with cup logos. No Build is performed.
"""
import argparse
import cProfile
import io
import json
import os
from pathlib import Path
import pstats
import statistics
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", required=True)
    parser.add_argument("--recipe")
    parser.add_argument("--leagues", type=int, default=86)
    parser.add_argument("--repeat", type=int, default=7)
    parser.add_argument("--section", type=int, choices=(0, 1, 2), default=0,
                        help="CUPS section during repeated navigation (Game/Our/Continental)")
    parser.add_argument("--json")
    parser.add_argument("--qualification", action="store_true",
                        help="Measure Continental navigation after its Qualification metadata has loaded")
    args = parser.parse_args()
    tables = str(Path(args.tables).resolve())
    recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8")) if args.recipe else None
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.pop("FL26_DIR", None)
    with tempfile.TemporaryDirectory(prefix="cups-profile-") as root:
        os.environ["APPDATA"] = root
        settings = Path(root, "FL26ModStudio", "settings.json")
        settings.parent.mkdir()
        settings.write_text(json.dumps({"tables": tables, "check_updates": False,
                                        "page": "Settings"}), encoding="utf-8")
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtGui import QImage, QColor
        from PySide6.QtWidgets import QApplication
        from modstudio.app import Main
        from modstudio import theme
        qa = QApplication.instance() or QApplication([])
        theme.apply(qa)
        window = Main()
        window.resize(1400, 860)
        # Main may have no installed game; the cup editors only need these tables.
        window.project.base = tables
        logo = str(Path(root, "cup.png"))
        image = QImage(64, 64, QImage.Format_ARGB32)
        image.fill(QColor("#68ba87"))
        image.save(logo)
        if recipe is None:
            recipe = {"world": "_FL26CupProfile", "leagues": [
                dict(name="League %03d" % i, country="Test", clubs=16,
                     cup=True, cup_logo=logo, supercup=True, supercup_logo=logo,
                     league_cup=True, league_cup_logo=logo) for i in range(args.leagues)]}
        window.project.recipe = recipe
        window.project.path = None
        window.project._forget()
        window.show()

        def settle():
            qa.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            qa.processEvents()

        def switch(name):
            start = time.perf_counter()
            window.open_page(name)
            settle()
            return 1000 * (time.perf_counter() - start)

        switch("Settings")
        first = switch("Cups")
        window.page("Cups").tabs.setCurrentIndex(args.section)
        settle()
        qualification_ms = None
        if args.qualification:
            if args.section != 2:
                parser.error("--qualification requires --section 2")
            start = time.perf_counter()
            continental = window.page("Cups").continental_section["editor"]
            continental.tabs.setCurrentIndex(1)
            deadline = time.monotonic() + 10
            while continental.qualification._loading and time.monotonic() < deadline:
                settle()
            qualification_ms = round(1000 * (time.perf_counter() - start), 3)
            settle()
        timings, others = [], []
        for _ in range(args.repeat):
            others.append(switch("Settings"))
            timings.append(switch("Cups"))
        profile = cProfile.Profile()
        switch("Settings")
        profile.enable()
        switch("Cups")
        profile.disable()
        result = {"fixture_leagues": len(recipe.get("leagues") or []), "section": args.section,
                  "game_rows": window.page("Cups").sections[0]["editor"].table.rowCount(),
                  "first_ms": round(first, 3), "reopen_ms": [round(t, 3) for t in timings],
                  "median_ms": round(statistics.median(timings), 3),
                  "settings_median_ms": round(statistics.median(others), 3)}
        if qualification_ms is not None:
            result["qualification_initial_ms"] = qualification_ms
        print(json.dumps(result, indent=2))
        if args.json:
            Path(args.json).write_text(json.dumps(result, indent=2), encoding="utf-8")
        output = io.StringIO()
        pstats.Stats(profile, stream=output).strip_dirs().sort_stats("cumulative").print_stats(25)
        print(output.getvalue())
        window.close()
        settle()


if __name__ == "__main__":
    main()
