"""the look: flat, dark, Segoe UI -- the palette of PlaylistForge (UI/Theme.cs), which is the
Visual Studio Dark+ one.  No rounded corners, no shadows, 1 px borders, the accent for what is
active or pressed and the selection colour for hover."""

BG = "#1E1E1E"          # window
PANEL = "#252526"       # lists, content
PANEL2 = "#2D2D30"      # toolbars, headers, buttons, inputs, alternate rows
BORDER = "#3F3F46"
TEXT = "#DEDEDE"
SUBTLE = "#969696"
ACCENT = "#007ACC"
SELECTION = "#094771"
DANGER = "#E57373"
GOOD = "#81C995"
WARN = "#DBBC60"
WARN_BG, WARN_FG = "#5A4A12", "#FFE082"
ERROR_BG = "#5A2828"

QSS = """
* { font-family: "Segoe UI"; font-size: 9pt; color: %(TEXT)s; }
QMainWindow, QDialog, QWidget#page { background: %(BG)s; }
QWidget { background: transparent; }
QToolTip { background: %(PANEL2)s; color: %(TEXT)s; border: 1px solid %(BORDER)s; padding: 4px; }

/* top bar */
QWidget#topbar { background: %(PANEL2)s; border-bottom: 1px solid %(BORDER)s; }
QWidget#header { background: %(BG)s; border-bottom: 1px solid %(BORDER)s; }
QLabel#title { font-size: 10pt; font-weight: bold; }
QLabel#subtle, QLabel.subtle { color: %(SUBTLE)s; }
QToolButton#menu { background: transparent; border: 1px solid transparent; padding: 4px 10px; }
QToolButton#menu:hover { background: %(SELECTION)s; border-color: %(BORDER)s; }
QToolButton#menu::menu-indicator { image: none; width: 0; }
QPushButton#play { background: %(ACCENT)s; color: white; border: 1px solid %(ACCENT)s; padding: 5px 18px;
                   font-weight: bold; }
QPushButton#play:hover { background: #1C8AD6; }
QPushButton#play:pressed { background: %(SELECTION)s; }

/* left navigation */
QWidget#nav { background: %(PANEL)s; border-right: 1px solid %(BORDER)s; }
QLabel#navcaption { background: %(PANEL2)s; color: %(SUBTLE)s; font-weight: bold; padding: 5px 10px;
                    letter-spacing: 1px; border-top: 1px solid %(BORDER)s; border-bottom: 1px solid %(BORDER)s; }
QPushButton#navitem { text-align: left; background: transparent; border: none; padding: 6px 14px 6px 18px; }
QPushButton#navitem:hover { background: %(PANEL2)s; }
QPushButton#navitem:checked { background: %(SELECTION)s; border-left: 3px solid %(ACCENT)s; padding-left: 15px; }

/* page header */
QLabel#pagetitle { font-size: 13pt; font-weight: bold; }
QLabel#section { color: %(ACCENT)s; font-weight: bold; letter-spacing: 1px; }
QLabel#hint { color: %(SUBTLE)s; }
QLabel#banner_warn { background: %(WARN_BG)s; color: %(WARN_FG)s; padding: 7px 10px; }
QLabel#banner_err { background: %(ERROR_BG)s; color: %(TEXT)s; padding: 7px 10px; }
QLabel#banner_ok { background: #1F3B2A; color: %(GOOD)s; padding: 7px 10px; }

/* buttons */
QPushButton { background: %(PANEL2)s; border: 1px solid %(BORDER)s; padding: 5px 12px; min-height: 18px; }
QPushButton:hover { background: %(SELECTION)s; }
QPushButton:pressed { background: %(ACCENT)s; }
QPushButton:disabled { color: #6A6A6A; background: %(PANEL)s; }
QPushButton#primary { background: %(ACCENT)s; color: white; border-color: %(ACCENT)s; }
QPushButton#primary:hover { background: #1C8AD6; }
QPushButton#danger { color: %(DANGER)s; }
QPushButton#primary:disabled, QPushButton#danger:disabled { color: #6A6A6A; background: %(PANEL)s; border-color: %(BORDER)s; }
QPushButton#tab { background: %(PANEL2)s; border: 1px solid %(BORDER)s; padding: 5px 16px; }
QPushButton#tab:checked { background: %(ACCENT)s; color: white; border-color: %(ACCENT)s; }

/* inputs */
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
    background: %(PANEL2)s; border: 1px solid %(BORDER)s; padding: 3px 5px; selection-background-color: %(SELECTION)s; }
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
QTableView::item, QTreeView::item { padding: 3px 4px; }
QTreeView::item:hover, QListView::item:hover { background: #2A2D2E; }
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
QFrame#card { background: %(PANEL)s; border: 1px solid %(BORDER)s; }
QLabel#cardvalue { font-size: 18pt; font-weight: 600; }
QLabel#cardlabel { color: %(SUBTLE)s; }
QFrame#drop { background: %(PANEL)s; border: 1px dashed %(BORDER)s; }
QFrame#drop[hot="true"] { border: 1px dashed %(ACCENT)s; background: #1B2733; }
""" % dict(BG=BG, PANEL=PANEL, PANEL2=PANEL2, BORDER=BORDER, TEXT=TEXT, SUBTLE=SUBTLE,
           ACCENT=ACCENT, SELECTION=SELECTION, DANGER=DANGER, GOOD=GOOD, WARN=WARN,
           WARN_BG=WARN_BG, WARN_FG=WARN_FG, ERROR_BG=ERROR_BG)


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
