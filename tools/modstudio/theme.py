"""the look (0.2.4, the "flight deck" design the testers picked, 15.10.): near-black slate, sharp
1 px lines, Windows' own Segoe UI for all text (Segoe UI Variable where Windows 11 has it; its
Semibold for titles and section names), Consolas only for logs. Colours carry meaning only:
green  OK, it is there and it works
orange an action, the open section, something to look at
red    a problem, said by name
blue   information, links, what is chosen
(15.10.: the user picked the Windows font over JetBrains Mono / IBM Plex.)"""
import os

BG = "#0F1319"          # window
PANEL = "#141921"       # cards, lists, tables
PANEL2 = "#1A212B"      # inputs, buttons
BORDER = "#252D39"
LINE2 = "#2E3846"       # a button's edge
TEXT = "#E6EBF2"
SUBTLE = "#9AA5B4"      # muted text; no darker (jibibi 15.10.: not enough contrast)
DIM = "#6E7989"          # disabled controls and placeholders only
ACCENT = "#4AA3FF"      # blue: information, links, focus, selection
ORANGE = "#F5A524"      # actions, the open section, look at this
SELECTION = "#1B2B40"
DANGER = "#FF6B6B"
GOOD = "#3ECF8E"
WARN = ORANGE
WARN_BG, WARN_FG = "#2B2112", "#F5C46A"
ERROR_BG = "#2A1619"
OK_BG = "#11261D"
BAR = "#0C1015"          # top bar, sections and status bar
PLAY = ORANGE
PRIMARY = "#1F5FAE"      # the main button of a page
BLUE_BG, BLUE_BORDER = "#122033", "#244A75"
# tables (jibibi, 15.10.: "there isn't enough contrast in each table"): rows that alternate clearly,
# a header on its own band, lines between the rows, the chosen row in blue with an edge
ROW, ROW_ALT = "#141921", "#1A212C"
HEAD_BG, HEAD_FG, HEAD_LINE = "#1F2733", "#C9D2DE", "#2F3A4A"
ROW_LINE = "#2A3341"
ROW_SEL, ROW_HOVER = "rgba(74, 163, 255, 64)", "rgba(74, 163, 255, 28)"

# the families; fonts() picks the Windows 11 ones (Segoe UI Variable) when they are there
SANS = "Segoe UI"
HEAD = "Segoe UI Semibold"
MONO = "Consolas"

QSS_T = """
* { font-family: %(SANS_STACK)s; font-size: 10pt; color: %(TEXT)s; }
QMainWindow, QDialog, QWidget#page { background: %(BG)s; }
QWidget { background: transparent; }
QToolTip { background: %(PANEL2)s; color: %(TEXT)s; border: 1px solid %(LINE2)s; padding: 5px; }
QMessageBox, QInputDialog, QFileDialog { background: %(BG)s; }

/* the bar at the top: name, the state boxes, readiness, Start the game */
QWidget#topbar { background: %(BAR)s; border-bottom: 1px solid %(BORDER)s; }
QWidget#menubar { background: %(BAR)s; }
QLabel#brand { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 12pt; }
QLabel#brandmark { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 12pt; color: %(ORANGE)s; }
QLabel#version { font-family: %(SANS_STACK)s; font-size: 8pt; color: %(ORANGE)s; border: 1px solid %(ORANGE)s;
                 padding: 1px 6px; }
QFrame#stat { background: %(PANEL)s; border: 1px solid %(BORDER)s; }
QFrame#stat[state="err"] { background: %(ERROR_BG)s; border-color: #5A2A30; }
QLabel#statcap { font-family: %(SANS_STACK)s; font-size: 7pt; color: %(SUBTLE)s; }
QLabel#statval { font-family: %(SANS_STACK)s; font-size: 10pt; color: %(TEXT)s; }
QLabel#statval[state="ok"] { color: %(GOOD)s; }
QLabel#statval[state="err"] { color: %(DANGER)s; }
QLabel#statval[state="info"] { color: %(ACCENT)s; }
QLabel#pill { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 9pt; padding: 7px 12px;
              color: %(GOOD)s; background: %(OK_BG)s; border: 1px solid #1F5A40; }
QLabel#pill[state="err"] { color: %(DANGER)s; background: %(ERROR_BG)s; border-color: #5A2A30; }
QLabel#pill[state="warn"] { color: %(ORANGE)s; background: %(WARN_BG)s; border-color: #5A4418; }
QLabel#title { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 10pt; }
QLabel#subtle, QLabel.subtle { color: %(SUBTLE)s; }
QToolButton#menu { font-family: %(SANS_STACK)s; font-size: 8pt; color: %(SUBTLE)s; background: transparent;
                   border: 1px solid transparent; padding: 3px 9px; }
QToolButton#menu:hover { color: %(TEXT)s; background: %(PANEL2)s; border-color: %(BORDER)s; }
QToolButton#menu::menu-indicator { image: none; width: 0; }
QLabel#running { font-family: %(SANS_STACK)s; font-size: 8pt; }
QPushButton#play { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 9pt;
                   background: %(PLAY)s; color: #14100A; border: 1px solid %(PLAY)s; padding: 6px 18px; border-radius: 0; }
QPushButton#play:hover { background: #FFB943; border-color: #FFB943; }
QPushButton#play:pressed { background: #D88D12; }
QPushButton#play:disabled { background: %(PANEL2)s; color: %(SUBTLE)s; border-color: %(LINE2)s; }

/* the sections, numbered, across the top */
QWidget#nav { background: %(BAR)s; border-bottom: 1px solid %(BORDER)s; }
QPushButton#navitem, QToolButton#navitem { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 9pt;
                      text-align: left; background: transparent; border: none; border-bottom: 2px solid transparent;
                      border-radius: 0; color: #AEB7C4; padding: 8px 11px 6px 11px; margin: 0; min-height: 0; }
QPushButton#navitem:hover, QToolButton#navitem:hover { color: white; background: %(PANEL)s; }
QPushButton#navitem:checked, QToolButton#navitem:checked { color: %(ORANGE)s; border-bottom: 2px solid %(ORANGE)s; background: transparent; }
QToolButton#navitem::menu-indicator { image: none; width: 0; }

/* page header */
QLabel#pagetitle { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 11pt; color: %(ORANGE)s; }
QLabel#section { font-family: %(HEAD_STACK)s; font-weight: 600; color: %(ACCENT)s; font-size: 9pt; }
QLabel#section_o { font-family: %(HEAD_STACK)s; font-weight: 600; color: %(ORANGE)s; font-size: 9pt; }
QLabel#hint { color: %(SUBTLE)s; }
QToolButton#helpmark { font-family: %(SANS_STACK)s; background: %(PANEL2)s; color: %(ACCENT)s; border: 1px solid %(LINE2)s; border-radius: 0;
                       font-weight: 600; min-width: 14px; max-width: 14px; min-height: 14px; max-height: 14px; padding: 0; }
QToolButton#helpmark:hover { background: %(SELECTION)s; color: white; }
QLabel#banner_warn { background: %(WARN_BG)s; color: %(WARN_FG)s; border: 1px solid #5A4418; padding: 9px 12px; }
QLabel#banner_err { background: %(ERROR_BG)s; color: %(TEXT)s; border: 1px solid #5A2A30; padding: 9px 12px; }
QLabel#banner_ok { background: %(OK_BG)s; color: %(GOOD)s; border: 1px solid #1F5A40; padding: 9px 12px; }

/* the red bar that names the problem */
QFrame#problembar { background: %(ERROR_BG)s; border: 1px solid #5A2A30; }
QLabel#problemcap { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 9pt; color: %(DANGER)s; }
QLabel#problemtext { color: %(TEXT)s; }

/* buttons */
QPushButton, QToolButton { font-family: %(SANS_STACK)s; font-size: 9pt; }
QPushButton { background: %(PANEL2)s; border: 1px solid %(LINE2)s; border-radius: 0; padding: 6px 14px; min-height: 18px; }
QPushButton:hover { background: %(SELECTION)s; border-color: %(ACCENT)s; }
QPushButton:pressed { background: #23406A; }
QPushButton:disabled { color: %(DIM)s; background: %(PANEL)s; border-color: %(BORDER)s; }
QPushButton:checked { background: %(SELECTION)s; border-color: %(ACCENT)s; }
QToolButton { background: %(PANEL2)s; border: 1px solid %(LINE2)s; border-radius: 0; padding: 6px 12px; }
QToolButton:hover { background: %(SELECTION)s; border-color: %(ACCENT)s; }
QToolButton::menu-indicator { image: none; width: 0; }
QPushButton#primary { background: %(PRIMARY)s; color: white; border-color: %(PRIMARY)s; font-weight: 600; }
QPushButton#primary:hover { background: #2A72CC; border-color: %(ACCENT)s; }
QPushButton#primary:pressed { background: #184C8C; }
QPushButton#action { color: %(ORANGE)s; border-color: %(ORANGE)s; background: transparent; font-weight: 600; padding: 3px 10px; min-height: 14px; }
QPushButton#action:hover { background: %(WARN_BG)s; }
QPushButton#rowbtn { padding: 3px 10px; min-height: 14px; }
QPushButton#quick { text-align: left; padding: 11px 16px; font-weight: 600; background: %(PANEL2)s; }
QPushButton#quickmain { text-align: left; padding: 11px 16px; font-weight: 600;
                        background: %(PRIMARY)s; color: white; border-color: %(PRIMARY)s; }
QPushButton#quickmain:hover { background: #2A72CC; }
QPushButton#big { font-size: 10pt; font-weight: 600; padding: 10px 26px; }
QPushButton#danger { color: %(DANGER)s; }
QPushButton#danger:hover { border-color: %(DANGER)s; background: %(ERROR_BG)s; }
QPushButton#fold { text-align: left; background: transparent; border: none; color: %(ACCENT)s; font-weight: 600; padding: 4px 2px; }
QPushButton#fold:hover { color: white; background: transparent; }
QFrame#foldbody { background: %(PANEL)s; border: 1px solid %(BORDER)s; }
QPushButton#primary:disabled, QPushButton#danger:disabled { color: %(DIM)s; background: %(PANEL)s; border-color: %(BORDER)s; }
QPushButton#tab, QPushButton#chip { background: %(PANEL2)s; border: 1px solid %(LINE2)s; padding: 5px 12px; font-weight: 600; }
QPushButton#tab:checked, QPushButton#chip:checked { background: %(ORANGE)s; color: #14100A; border-color: %(ORANGE)s; font-weight: 600; }
QPushButton:flat { background: transparent; border: none; }
QPushButton#statusbtn { background: transparent; border: none; padding: 0 8px; min-height: 0; font-size: 8pt; color: %(GOOD)s; }
QPushButton#statusbtn:hover { color: white; }

/* inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit, QDateEdit {
    background: %(PANEL)s; border: 1px solid %(LINE2)s; border-radius: 0; padding: 4px 6px;
    selection-background-color: %(SELECTION)s; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus { border-color: %(ACCENT)s; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { color: %(DIM)s; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox::down-arrow { image: url("%(ASSETS)s/arrow-down.png"); width: 10px; height: 8px; margin-right: 6px; }
QComboBox::down-arrow:hover, QComboBox::down-arrow:on { image: url("%(ASSETS)s/arrow-down-hot.png"); }
QComboBox QAbstractItemView { background: %(PANEL2)s; border: 1px solid %(LINE2)s; selection-background-color: %(SELECTION)s; }
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { background: %(PANEL2)s; border: none; width: 16px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: %(SELECTION)s; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("%(ASSETS)s/arrow-up.png"); width: 8px; height: 6px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("%(ASSETS)s/arrow-down.png"); width: 8px; height: 6px; }
QPlainTextEdit#log { background: %(PANEL)s; font-family: %(MONO_STACK)s; font-size: 9pt; }
QCheckBox, QRadioButton { spacing: 7px; }
QCheckBox::indicator, QRadioButton::indicator { width: 12px; height: 12px; border: 1px solid %(LINE2)s; background: %(PANEL2)s; }
QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: %(ACCENT)s; }
QCheckBox::indicator:checked { background: %(GOOD)s; border-color: %(GOOD)s; }
QCheckBox::indicator:indeterminate { background: %(ORANGE)s; border-color: %(ORANGE)s; }
QCheckBox::indicator:disabled { background: %(PANEL)s; border-color: %(BORDER)s; }
QRadioButton::indicator { border-radius: 7px; }
QRadioButton::indicator:checked { background: %(ACCENT)s; border-color: %(ACCENT)s; }

/* tables and lists */
QTableView, QTreeView, QListView, QListWidget, QTreeWidget, QTableWidget {
    background: %(ROW)s; alternate-background-color: %(ROW_ALT)s; border: 1px solid %(BORDER)s; color: %(TEXT)s;
    gridline-color: %(ROW_LINE)s; selection-background-color: %(ROW_SEL)s; selection-color: white; outline: 0; }
QTableView::item, QTreeView::item { padding: 4px 4px; border-bottom: 1px solid %(ROW_LINE)s; }
QListView::item { padding: 5px 6px; border-bottom: 1px solid %(ROW_LINE)s; }
QTreeView::item:hover, QListView::item:hover, QTableView::item:hover { background: %(ROW_HOVER)s; }
QTreeView::item:selected, QListView::item:selected, QTableView::item:selected { background: %(ROW_SEL)s; color: white; }
QTreeView::item:selected:first, QTreeView::item:selected:only-one, QListView::item:selected { border-left: 3px solid %(ACCENT)s; }
QHeaderView { background: %(HEAD_BG)s; }
QHeaderView::section { font-family: %(SANS_STACK)s; font-size: 8pt; color: %(HEAD_FG)s; background: %(HEAD_BG)s; border: none;
                       border-bottom: 1px solid %(HEAD_LINE)s; padding: 7px 8px; font-weight: 600; }
QHeaderView::section:hover { color: white; }
QTableCornerButton::section { background: %(HEAD_BG)s; border: none; border-bottom: 1px solid %(HEAD_LINE)s; }

/* splitters, scroll bars, tabs */
QSplitter::handle { background: %(BORDER)s; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QScrollBar:vertical { background: %(BG)s; width: 10px; margin: 0; }
QScrollBar:horizontal { background: %(BG)s; height: 10px; margin: 0; }
QScrollBar::handle { background: #2F3947; min-height: 24px; min-width: 24px; }
QScrollBar::handle:hover { background: #46546A; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QTabWidget::pane { border: none; border-top: 1px solid %(BORDER)s; top: -1px; background: %(BG)s; }
QTabBar::tab { font-family: %(SANS_STACK)s; font-size: 9pt; color: %(SUBTLE)s; background: transparent;
               border: none; border-bottom: 2px solid transparent; padding: 7px 14px; margin-right: 2px; }
QTabBar::tab:selected { color: %(ORANGE)s; border-bottom: 2px solid %(ORANGE)s; font-weight: 600; }
QTabBar::tab:hover:!selected { color: %(TEXT)s; background: %(PANEL)s; }
QGroupBox { border: 1px solid %(BORDER)s; background: %(PANEL)s; margin-top: 16px; padding: 12px 10px 10px 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: %(ACCENT)s;
                   font-family: %(SANS_STACK)s; font-size: 9pt; font-weight: 600; }

/* menus, status bar, progress */
QMenu { background: %(PANEL2)s; border: 1px solid %(LINE2)s; padding: 3px; }
QMenu::item { padding: 6px 26px 6px 20px; }
QMenu::item:selected { background: %(SELECTION)s; color: white; }
QMenu::item:disabled { color: %(DIM)s; }
QMenu::separator { height: 1px; background: %(BORDER)s; margin: 3px 6px; }
QStatusBar { background: %(BAR)s; border-top: 1px solid %(BORDER)s; color: %(SUBTLE)s; min-height: 24px; }
QStatusBar::item { border: none; }
QStatusBar QLabel { font-family: %(SANS_STACK)s; font-size: 8pt; color: %(SUBTLE)s; padding: 0 8px; }
QLabel#sbstate { font-weight: 600; color: %(GOOD)s; }
QLabel#sbstate[state="err"] { color: %(DANGER)s; }
QLabel#sbstate[state="warn"] { color: %(ORANGE)s; }
QProgressBar { background: %(PANEL2)s; border: 1px solid %(BORDER)s; height: 10px; text-align: center; color: transparent; }
QProgressBar::chunk { background: %(GOOD)s; }

/* cards */
QFrame#card { background: %(PANEL)s; border: 1px solid %(BORDER)s; }
QFrame#bluecard { background: %(BLUE_BG)s; border: 1px solid %(BLUE_BORDER)s; }
QFrame#okcard { background: %(OK_BG)s; border: 1px solid #1F5A40; }
QLabel#eyebrow { font-family: %(HEAD_STACK)s; font-weight: 600; color: %(GOOD)s; font-size: 8pt; }
QLabel#bigtitle { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 15pt; }
QLabel#cardtitle { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 10pt; }
QLabel#mono { font-family: %(MONO_STACK)s; color: #C9CED6; }
QLabel#tick_ok { font-family: %(HEAD_STACK)s; font-weight: 600; color: %(GOOD)s; }
QLabel#tick_warn { font-family: %(HEAD_STACK)s; font-weight: 600; color: %(ORANGE)s; }
QLabel#tick_bad { font-family: %(HEAD_STACK)s; font-weight: 600; color: %(DANGER)s; }
QFrame#rowline { background: %(ROW_LINE)s; max-height: 1px; min-height: 1px; border: none; }
QLabel#cardvalue { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 15pt; }
QLabel#cardlabel { color: %(SUBTLE)s; }
QFrame#drop { background: %(PANEL)s; border: 1px dashed %(LINE2)s; }
QFrame#drop[hot="true"] { border: 1px dashed %(ORANGE)s; background: %(WARN_BG)s; }

/* Home: the ready check as a table */
QWidget#checkrow { background: %(ROW)s; border-bottom: 1px solid %(ROW_LINE)s; }
QWidget#checkrow[alt="true"] { background: %(ROW_ALT)s; }
QWidget#checkrow[level="warn"] { background: %(WARN_BG)s; }
QWidget#checkrow[level="err"] { background: %(ERROR_BG)s; }
QWidget#checkrow[level="head"] { background: %(HEAD_BG)s; border-bottom: 1px solid %(HEAD_LINE)s; }
QLabel#colhead { font-family: %(SANS_STACK)s; font-size: 8pt; color: %(HEAD_FG)s; font-weight: 600; }
QLabel#state { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 9pt; }
QLabel#state[level="ok"] { color: %(GOOD)s; }
QLabel#state[level="warn"] { color: %(ORANGE)s; }
QLabel#state[level="err"] { color: %(DANGER)s; }
QLabel#value { font-family: %(SANS_STACK)s; font-size: 9pt; }
QLabel#value[level="ok"] { color: %(GOOD)s; }
QLabel#value[level="err"] { color: %(DANGER)s; }
QLabel#when { font-family: %(SANS_STACK)s; font-size: 9pt; color: %(SUBTLE)s; }
QLabel#srctag { font-family: %(HEAD_STACK)s; font-weight: 600; font-size: 8pt; padding: 2px 8px; border: 1px solid %(LINE2)s; color: %(SUBTLE)s; }
QLabel#srctag[state="zip"] { color: %(ACCENT)s; background: %(BLUE_BG)s; border-color: %(BLUE_BORDER)s; }
QLabel#srctag[state="built"] { color: %(GOOD)s; background: %(OK_BG)s; border-color: #1F5A40; }
QLabel#cardnote { font-family: %(SANS_STACK)s; font-size: 9pt; color: %(SUBTLE)s; }
"""


def fonts():
    """the families this Windows has: Segoe UI Variable (Windows 11) or Segoe UI (10); the stacks
    for the style sheet"""
    from PySide6.QtGui import QFontDatabase
    have = set(QFontDatabase.families())
    global SANS, HEAD
    if "Segoe UI Variable Text" in have:
        SANS = "Segoe UI Variable Text"
        HEAD = ("Segoe UI Variable Display Semibold" if "Segoe UI Variable Display Semibold" in have
                else "Segoe UI Semibold")
    return dict(SANS_STACK='"%s", "Segoe UI", sans-serif' % SANS,
                HEAD_STACK='"%s", "Segoe UI Semibold", "Segoe UI", sans-serif' % HEAD,
                MONO_STACK='"%s", "Cascadia Mono", monospace' % MONO)


def qss():
    return QSS_T % dict(BG=BG, PANEL=PANEL, PANEL2=PANEL2, BORDER=BORDER, LINE2=LINE2, TEXT=TEXT, SUBTLE=SUBTLE,
                        DIM=DIM, ACCENT=ACCENT, ORANGE=ORANGE, SELECTION=SELECTION, DANGER=DANGER, GOOD=GOOD,
                        WARN_BG=WARN_BG, WARN_FG=WARN_FG, ERROR_BG=ERROR_BG, OK_BG=OK_BG, BAR=BAR, PLAY=PLAY,
                        PRIMARY=PRIMARY, BLUE_BG=BLUE_BG, BLUE_BORDER=BLUE_BORDER,
                        ROW=ROW, ROW_ALT=ROW_ALT, HEAD_BG=HEAD_BG, HEAD_FG=HEAD_FG, HEAD_LINE=HEAD_LINE,
                        ROW_LINE=ROW_LINE, ROW_SEL=ROW_SEL, ROW_HOVER=ROW_HOVER,
                        ASSETS=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets").replace("\\", "/"),
                        **fonts())


def caps(widget):
    """show a widget's text in capitals (the bar, the section names) and keep the text itself as
    it is: what Windows reads out, and what a test finds, is still "Import your world" """
    from PySide6.QtGui import QFont
    f = widget.font()
    f.setCapitalization(QFont.AllUppercase)
    widget.setFont(f)
    return widget


def repolish(widget):
    """after a dynamic property changed (state, level): let the style sheet look again"""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


_CAPS = None


def _caps_filter():
    from PySide6.QtCore import QObject, QEvent
    from PySide6.QtWidgets import (QAbstractButton, QHeaderView, QTabBar, QCheckBox, QRadioButton, QTreeView,
                                   QTableView)

    class Caps(QObject):
        def eventFilter(self, obj, ev):
            if ev.type() != QEvent.Polish:
                return False
            # every table and tree: rows that alternate (jibibi, 15.10.: not enough contrast)
            if isinstance(obj, (QTreeView, QTableView)) and not obj.property("_alt"):
                obj.setProperty("_alt", True)
                obj.setAlternatingRowColors(True)
            if (isinstance(obj, (QAbstractButton, QHeaderView, QTabBar))
                    and not isinstance(obj, (QCheckBox, QRadioButton)) and not obj.property("_caps")
                    and obj.objectName() not in ("helpmark", "fold", "statusbtn")):
                obj.setProperty("_caps", True)
                caps(obj)
            return False
    return Caps


def _Caps(app):
    return _caps_filter()(app)


def apply(app):
    from PySide6.QtGui import QPalette, QColor, QFont
    app.setStyle("Fusion")
    fonts()
    f = QFont(SANS, 10)
    f.setStyleHint(QFont.SansSerif)
    app.setFont(f)
    # buttons, tabs and column heads in capitals, as the sections are (the text itself stays as
    # written). The style sheet's font replaces a font set per class, so each one gets it when
    # it is first polished
    global _CAPS
    _CAPS = _Caps(app)
    app.installEventFilter(_CAPS)
    p = QPalette()
    for role, c in ((QPalette.Window, BG), (QPalette.Base, PANEL), (QPalette.AlternateBase, ROW_ALT),
                    (QPalette.Button, PANEL2), (QPalette.Text, TEXT), (QPalette.WindowText, TEXT),
                    (QPalette.ButtonText, TEXT), (QPalette.Highlight, SELECTION),
                    (QPalette.HighlightedText, "#FFFFFF"), (QPalette.ToolTipBase, PANEL2),
                    (QPalette.ToolTipText, TEXT), (QPalette.PlaceholderText, DIM),
                    (QPalette.Link, ACCENT), (QPalette.LinkVisited, ACCENT)):
        p.setColor(role, QColor(c))
    app.setPalette(p)
    app.setStyleSheet(qss())


def dark_title_bar(widget):
    """ask Windows for a dark title bar (DWMWA_USE_IMMERSIVE_DARK_MODE); harmless elsewhere"""
    try:
        import ctypes
        hwnd = int(widget.winId())
        v = ctypes.c_int(1)
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), 4) == 0:
                break
    except Exception:
        pass
