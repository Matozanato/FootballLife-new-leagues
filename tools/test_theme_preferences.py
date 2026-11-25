"""the saved appearance preferences update the shared Qt theme without stacking event filters.

    python test_theme_preferences.py
"""
import os
import sys
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QScrollArea

from modstudio import theme
from modstudio.pages.manager import ModManager, _ReportView
from modstudio.pages.settings import Settings


app = QApplication.instance() or QApplication([])
base = theme.qss()
large = theme.qss({"text_size": "extra-large"})
violet = theme.qss({"accent": "violet", "high_contrast": True})
teal = theme.qss({"accent": "teal"})

assert "font-size: 10.00pt" in base
assert "font-size: 13.00pt" in large
assert "QTreeWidget#jsonReportTree" in base
assert "color: #FFFFFF; border-color: #3D4B5F; font-size: 11.00pt" in base
assert "background: #18212D; alternate-background-color: #243143" in base
assert "#2A394D" in violet
assert "#B38CFF" in violet
assert "#D4DBE5" in violet
assert "background: #238C7E" in teal

report = _ReportView()
report.set_data({"rows": [{"name": "Kit atlas", "status": "Ready"}]})
assert report.tree.objectName() == "jsonReportTree"
assert report.details.objectName() == "jsonReportDetails"
assert report.tree.topLevelItem(0).text(0) == "rows"

manager = ModManager(SimpleNamespace(
    game=SimpleNamespace(folder="", sider_dir=""), settings={}, section_of={},
))
assert manager.tabs.count() == 3
assert manager.tabs.tabText(0) == "CPK archives"

theme.apply(app)
caps_filter = theme._CAPS
theme.apply(app, {"text_size": "extra-large", "accent": "violet", "high_contrast": True})
assert theme._CAPS is caps_filter
assert app.font().pointSize() == 13
assert app.palette().color(QPalette.Link).name().upper() == "#B38CFF"
assert app.palette().color(QPalette.Highlight).name().upper() == "#32264B"
assert "#D4DBE5" in app.styleSheet()

model = SimpleNamespace(settings={}, saves=0)
model.save_settings = lambda: setattr(model, "saves", model.saves + 1)
page = Settings(model)
assert page.findChild(QScrollArea) is not None

print("ok - the shared Qt theme follows the saved preferences and stays scrollable")
