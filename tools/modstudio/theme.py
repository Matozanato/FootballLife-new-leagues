"""the look: dark slate with a blue accent, Segoe UI, rounded 6 px buttons and 10 px cards (the
0.1.8 design sketch).  1 px borders, no shadows; the accent for what is active or pressed and the
selection colour for what is chosen."""

BG = "#14181D"          # window
PANEL = "#1C2128"       # lists, content
PANEL2 = "#232A33"      # toolbars, headers, buttons, inputs, alternate rows
BORDER = "#2A313A"
TEXT = "#E6E8EB"
SUBTLE = "#8C96A3"
ACCENT = "#3D8BFD"
SELECTION = "#22344F"
DANGER = "#E57373"
GOOD = "#5CC08A"
WARN = "#E3B341"
WARN_BG, WARN_FG = "#5A4A12", "#FFE082"
ERROR_BG = "#5A2828"
BAR = "#171C22"          # top bar and navigation
PLAY = "#2E9E5B"
BLUE_BG, BLUE_BORDER = "#18263A", "#2B4A73"   # the build strip

QSS = """
* { font-family: "Segoe UI"; font-size: 10pt; color: %(TEXT)s; }
QMainWindow, QDialog, QWidget#page { background: %(BG)s; }
QWidget { background: transparent; }
QToolTip { background: %(PANEL2)s; color: %(TEXT)s; border: 1px solid %(BORDER)s; padding: 4px; }

/* top bar */
QWidget#topbar { background: %(BAR)s; border-bottom: 1px solid %(BORDER)s; }
QWidget#header { background: %(BG)s; border-bottom: 1px solid %(BORDER)s; }
QLabel#title { font-size: 10pt; font-weight: bold; }
QLabel#subtle, QLabel.subtle { color: %(SUBTLE)s; }
QToolButton#menu { background: transparent; border: 1px solid transparent; padding: 4px 10px; }
QToolButton#menu:hover { background: %(SELECTION)s; border-color: %(BORDER)s; }
QToolButton#menu::menu-indicator { image: none; width: 0; }
QPushButton#play { background: %(PLAY)s; color: white; border: 1px solid %(PLAY)s; padding: 6px 20px;
                   font-weight: bold; border-radius: 6px; }
QPushButton#play:hover { background: #36B068; }
QPushButton#play:pressed { background: %(SELECTION)s; }

/* left navigation */
QWidget#nav { background: %(BAR)s; border-right: 1px solid %(BORDER)s; }
QLabel#navcaption { color: #6F7986; font-size: 8pt; font-weight: bold; padding: 14px 14px 4px 14px; letter-spacing: 1px; }
QPushButton#navitem { text-align: left; background: transparent; border: none; border-radius: 6px; color: #C9CED6;
                      padding: 7px 12px; margin: 0 8px; }
QPushButton#navitem:hover { background: %(PANEL2)s; }
QPushButton#navitem:checked { background: %(SELECTION)s; color: white; font-weight: 600; }

/* page header */
QLabel#pagetitle { font-size: 13pt; font-weight: bold; }
QLabel#section { color: %(ACCENT)s; font-weight: bold; letter-spacing: 1px; }
QLabel#hint { color: %(SUBTLE)s; }
QToolButton#helpmark { background: %(PANEL2)s; color: %(ACCENT)s; border: 1px solid %(BORDER)s; border-radius: 8px;
                       font-weight: bold; min-width: 14px; max-width: 14px; min-height: 14px; max-height: 14px; padding: 0; }
QToolButton#helpmark:hover { background: %(SELECTION)s; color: white; }
QLabel#banner_warn { background: %(WARN_BG)s; color: %(WARN_FG)s; padding: 7px 10px; }
QLabel#banner_err { background: %(ERROR_BG)s; color: %(TEXT)s; padding: 7px 10px; }
QLabel#banner_ok { background: #1F3B2A; color: %(GOOD)s; padding: 7px 10px; }

/* buttons */
QPushButton { background: %(PANEL)s; border: 1px solid #39424D; border-radius: 6px; padding: 6px 14px; min-height: 20px; }
QPushButton:hover { background: %(SELECTION)s; border-color: %(ACCENT)s; }
QPushButton:pressed { background: %(ACCENT)s; }
QPushButton:disabled { color: #6A6A6A; background: %(PANEL)s; }
QPushButton#primary { background: #2563C9; color: white; border-color: #2563C9; font-weight: 600; }
QPushButton#primary:hover { background: #3D8BFD; border-color: #3D8BFD; }
QPushButton#big { font-size: 11pt; font-weight: bold; padding: 10px 26px; border-radius: 8px; }
QPushButton#danger { color: %(DANGER)s; }
QPushButton#primary:disabled, QPushButton#danger:disabled { color: #6A6A6A; background: %(PANEL)s; border-color: %(BORDER)s; }
QPushButton#tab { background: %(PANEL2)s; border: 1px solid %(BORDER)s; padding: 5px 16px; border-radius: 6px; }
QPushButton#tab:checked { background: #2563C9; color: white; border-color: #2563C9; }

/* inputs */
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
    background: %(PANEL)s; border: 1px solid #39424D; border-radius: 5px; padding: 4px 6px; selection-background-color: %(SELECTION)s; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: %(ACCENT)s; }
QLineEdit:disabled { color: #6A6A6A; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView { background: %(PANEL2)s; border: 1px solid %(BORDER)s; selection-background-color: %(SELECTION)s; }
QSpinBox::up-button, QSpinBox::down-button { background: %(PANEL2)s; border: none; width: 14px; }
QPlainTextEdit#log { background: %(PANEL)s; font-family: Consolas, "Cascadia Mono", monospace; font-size: 9pt; }
QCheckBox, QRadioButton { spacing: 6px; }
QCheckBox::indicator, QRadioButton::indicator { width: 13px; height: 13px; border: 1px solid %(BORDER)s; background: %(PANEL2)s; }
QCheckBox::indicator:checked { background: %(ACCENT)s; border-color: %(ACCENT)s; }
QRadioButton::indicator { border-radius: 7px; }
QRadioButton::indicator:checked { background: %(ACCENT)s; border-color: %(ACCENT)s; }

/* tables and lists */
QTableView, QTreeView, QListView, QListWidget, QTreeWidget, QTableWidget {
    background: %(PANEL)s; alternate-background-color: %(PANEL2)s; border: 1px solid %(BORDER)s;
    gridline-color: %(BORDER)s; selection-background-color: %(SELECTION)s; selection-color: white; outline: 0; }
QTableView::item, QTreeView::item { padding: 4px 4px; }
QListView::item { padding: 5px 6px; }
QTreeView::item:hover, QListView::item:hover { background: #20262E; }
QTreeView::item:selected, QListView::item:selected, QTableView::item:selected { background: %(SELECTION)s; }
QHeaderView::section { background: %(PANEL2)s; border: none; border-right: 1px solid %(BORDER)s;
                       border-bottom: 1px solid %(BORDER)s; padding: 5px 6px; font-weight: bold; }
QTableCornerButton::section { background: %(PANEL2)s; border: none; }

/* splitters, scroll bars, tabs */
QSplitter::handle { background: %(BORDER)s; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QScrollBar:vertical { background: %(PANEL)s; width: 12px; margin: 0; }
QScrollBar:horizontal { background: %(PANEL)s; height: 12px; margin: 0; }
QScrollBar::handle { background: #4E4E52; min-height: 24px; min-width: 24px; }
QScrollBar::handle:hover { background: #686868; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QTabWidget::pane { border: 1px solid %(BORDER)s; top: -1px; background: %(BG)s; }
QTabBar::tab { background: %(PANEL2)s; border: 1px solid %(BORDER)s; padding: 5px 14px; margin-right: 2px; }
QTabBar::tab:selected { background: %(ACCENT)s; color: white; border-color: %(ACCENT)s; }
QTabBar::tab:hover:!selected { background: %(SELECTION)s; }
QGroupBox { border: 1px solid %(BORDER)s; margin-top: 14px; padding: 10px 8px 8px 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: %(ACCENT)s; font-weight: bold; }

/* menus, status bar, progress */
QMenu { background: %(PANEL2)s; border: 1px solid %(BORDER)s; padding: 2px; }
QMenu::item { padding: 5px 24px 5px 20px; }
QMenu::item:selected { background: %(SELECTION)s; }
QMenu::item:disabled { color: #6A6A6A; }
QMenu::separator { height: 1px; background: %(BORDER)s; margin: 3px 6px; }
QStatusBar { background: %(PANEL2)s; border-top: 1px solid %(BORDER)s; color: %(SUBTLE)s; }
QStatusBar QLabel { color: %(SUBTLE)s; padding: 0 6px; }
QProgressBar { background: %(PANEL2)s; border: 1px solid %(BORDER)s; height: 12px; text-align: center; color: transparent; }
QProgressBar::chunk { background: %(ACCENT)s; }

/* overview cards */
QFrame#card { background: %(PANEL)s; border: 1px solid %(BORDER)s; border-radius: 10px; }
QFrame#bluecard { background: %(BLUE_BG)s; border: 1px solid %(BLUE_BORDER)s; border-radius: 10px; }
QLabel#eyebrow { color: %(GOOD)s; font-size: 8pt; font-weight: bold; letter-spacing: 1px; }
QLabel#bigtitle { font-size: 18pt; font-weight: 600; }
QLabel#cardtitle { font-size: 11pt; font-weight: 600; }
QLabel#mono { font-family: Consolas, "Cascadia Mono", monospace; color: #C9CED6; }
QLabel#tick_ok { color: %(GOOD)s; font-weight: bold; }
QLabel#tick_warn { color: %(WARN)s; font-weight: bold; }
QLabel#tick_bad { color: %(DANGER)s; font-weight: bold; }
QFrame#rowline { background: #252B33; max-height: 1px; min-height: 1px; border: none; }
QLabel#cardvalue { font-size: 18pt; font-weight: 600; }
QLabel#cardlabel { color: %(SUBTLE)s; }
QFrame#drop { background: %(PANEL)s; border: 1px dashed %(BORDER)s; }
QFrame#drop[hot="true"] { border: 1px dashed %(ACCENT)s; background: #1B2733; }
""" % dict(BG=BG, PANEL=PANEL, PANEL2=PANEL2, BORDER=BORDER, TEXT=TEXT, SUBTLE=SUBTLE,
           ACCENT=ACCENT, SELECTION=SELECTION, DANGER=DANGER, GOOD=GOOD, WARN=WARN,
           WARN_BG=WARN_BG, WARN_FG=WARN_FG, ERROR_BG=ERROR_BG, BAR=BAR, PLAY=PLAY,
           BLUE_BG=BLUE_BG, BLUE_BORDER=BLUE_BORDER)


def apply(app):
    from PySide6.QtGui import QPalette, QColor
    app.setStyle("Fusion")
    p = QPalette()
    for role, c in ((QPalette.Window, BG), (QPalette.Base, PANEL), (QPalette.AlternateBase, PANEL2),
                    (QPalette.Button, PANEL2), (QPalette.Text, TEXT), (QPalette.WindowText, TEXT),
                    (QPalette.ButtonText, TEXT), (QPalette.Highlight, SELECTION),
                    (QPalette.HighlightedText, "#FFFFFF"), (QPalette.ToolTipBase, PANEL2),
                    (QPalette.ToolTipText, TEXT), (QPalette.PlaceholderText, SUBTLE)):
        p.setColor(role, QColor(c))
    app.setPalette(p)
    app.setStyleSheet(QSS)


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
