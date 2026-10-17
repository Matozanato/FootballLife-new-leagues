"""The quick tour: the first start of Mod Studio 0.2.4 shows where things are now, one place at a
time (mato 18.10.: "kod prvog pokretanja 0.2.4 pojavi wizard koji objasni gdje se sto nalazi").

A card with the step's words and Back / Next / Skip floats over the main window next to the thing it
talks about, which gets an orange frame. Nothing is opened, clicked or changed: the window works as
usual under it, and an update box or the first unpack of the game's tables goes on beside it.
Finished or skipped, it is not shown again (settings "tour"); Help > Quick tour shows it again."""
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import theme
from .i18n import _

TOUR = "0.2.4"          # the version whose tour the settings remember; a new one shows its own


def steps(app):
    """[(title, text, the widget it points at or None)] -- found by name, so a step whose widget is
    not there (a section renamed later) points at nothing instead of failing"""
    nb, nh = getattr(app, "nav_buttons", {}), getattr(app, "nav_heads", {})
    return [
        (_("Welcome to Mod Studio 0.2.4"),
         _("The window has a new look, and things moved. This short tour shows where everything is now: "
           "ten steps, one minute. Nothing is changed while it runs. Help > Quick tour shows it again."), None),
        (_("Language"),
         _("Language at the top: English, Spanish, French, Portuguese or Croatian. The new language comes "
           "when you start Mod Studio again (this tour too, if you did not finish it)."),
         getattr(app, "lang_btn", None)),
        (_("What is in the game now"),
         _("These boxes are the game as it is now: the game folder, Sider, the world in the game, the modules, "
           "the leagues and the pack. A red box names the problem; click it to go where it is fixed."),
         app.findChild(QWidget, "topbar")),
        (_("Start the game"),
         _("Next to it, whether everything is ready. Start the game from here, or from your usual shortcut: "
           "the setup is the same."), getattr(app, "play_btn", None)),
        (_("1. Home"),
         _("Home checks that everything is in place (game, Sider, modules) and names what is missing, "
           "with the button that puts it right."), nb.get("Overview")),
        (_("2. My world"),
         _("Your worlds, as cards: the one in the game is green. The first tab, Build, makes the world and puts "
           "it in the game (Build and install). The tabs next to it change it: Leagues, Clubs, Players, Kits, "
           "Stadiums. + Add... takes a world zip (a Modpack), a league package or the NewLife Database; "
           "NewLife Database has its own button too."), nb.get("World")),
        (_("3. Game content"),
         _("Balls, commentary, music and the other servers: what the game uses in matches, for all worlds."),
         nh.get("GAME CONTENT")),
        (_("4. Tools"),
         _("Lua modules, Content folders (which worlds and mods are on), profiles, Restore points (every copy "
           "Mod Studio made, to put back) and Diagnostics (when something does not work: it reads sider.log)."),
         nh.get("TOOLS")),
        (_("5. Settings"),
         _("The game folder, the game's tables and the other options."), nb.get("Settings")),
        (_("Help"),
         _("The user guide, updates and this tour again. Questions and bugs: our Discord, FL Mod Studio. "
           "Have fun!"), getattr(app, "help_btn", None)),
    ]


class Tour(QObject):
    """the card and the frame over `app`, the main window; closes itself when finished or skipped"""

    def __init__(self, app, done=None):
        super().__init__(app)
        self.app, self.done, self.i = app, done, 0
        self.steps = steps(app)
        self.frame = QFrame(app)
        self.frame.setObjectName("tourframe")
        self.frame.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.frame.setStyleSheet("#tourframe { border: 3px solid %s; border-radius: 6px; background: transparent; }"
                                 % theme.ORANGE)
        self.frame.hide()
        self.card = QFrame(app)
        self.card.setObjectName("tourcard")
        self.card.setAttribute(Qt.WA_StyledBackground, True)
        self.card.setStyleSheet("#tourcard { background: %s; border: 2px solid %s; border-radius: 8px; }"
                                "#tourcard QLabel { background: transparent; border: none; }"
                                % (theme.PANEL, theme.ORANGE))
        self.card.setFixedWidth(460)
        self.card.hide()
        v = QVBoxLayout(self.card)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(8)
        self.count = QLabel()
        self.count.setStyleSheet("color: %s; font-size: 8pt;" % theme.SUBTLE)
        self.title = QLabel()
        self.title.setStyleSheet("color: %s; font-size: 13pt; font-family: '%s';" % (theme.TEXT, theme.HEAD))
        self.title.setWordWrap(True)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setStyleSheet("color: %s; font-size: 10pt;" % theme.TEXT)
        for w in (self.count, self.title, self.text):
            v.addWidget(w)
        h = QHBoxLayout()
        h.setSpacing(6)
        self.skip = QPushButton(_("Skip the tour"))
        self.skip.clicked.connect(self.finish)
        self.back = QPushButton(_("Back"))
        self.back.clicked.connect(lambda: self.show_step(self.i - 1))
        self.next = QPushButton()
        self.next.setObjectName("primary")
        self.next.setDefault(True)
        self.next.clicked.connect(self.forward)
        h.addWidget(self.skip)
        h.addStretch(1)
        h.addWidget(self.back)
        h.addWidget(self.next)
        v.addLayout(h)
        app.installEventFilter(self)

    def start(self):
        self.show_step(0)
        return self

    def eventFilter(self, obj, ev):
        if obj is self.app and ev.type() in (QEvent.Resize, QEvent.Show):
            self.place()
        return False

    def forward(self):
        if self.i + 1 < len(self.steps):
            self.show_step(self.i + 1)
        else:
            self.finish()

    def target(self):
        w = self.steps[self.i][2]
        try:
            return w if w is not None and w.isVisible() else None
        except RuntimeError:               # deleted
            return None

    def show_step(self, i):
        self.i = max(0, min(i, len(self.steps) - 1))
        title, text, _w = self.steps[self.i]
        self.count.setText(_("Step %d of %d") % (self.i + 1, len(self.steps)))
        self.title.setText(title)
        self.text.setText(text)
        self.back.setEnabled(self.i > 0)
        self.next.setText(_("Done") if self.i + 1 == len(self.steps) else _("Next"))
        self.card.show()
        self.place()
        self.next.setFocus()

    def place(self):
        """the frame around the step's widget, the card under it (above it when there is no room
        below), inside the window; a step with nothing to point at has its card in the middle"""
        if self.card.isHidden():
            return
        W, H = self.app.width(), self.app.height()
        cw = self.card.width()
        ch = self.card.heightForWidth(cw) if self.card.hasHeightForWidth() else -1
        ch = max(ch, self.card.sizeHint().height())
        t = self.target()
        if t is None:
            self.frame.hide()
            self.card.setGeometry(QRect(max(0, (W - cw) // 2), max(0, (H - ch) // 3), cw, ch))
            self.card.raise_()
            return
        tl = t.mapTo(self.app, QPoint(0, 0))
        r = QRect(tl, t.size()).adjusted(-4, -4, 4, 4)
        self.frame.setGeometry(r)
        self.frame.show()
        self.frame.raise_()
        x = min(max(8, r.left()), max(8, W - cw - 8))
        y = r.bottom() + 10
        if y + ch > H - 8:
            y = max(8, r.top() - ch - 10)
        self.card.setGeometry(QRect(x, y, cw, ch))
        self.card.raise_()

    def finish(self):
        """seen: not shown at the next start (Help > Quick tour still shows it)"""
        self.app.removeEventFilter(self)
        self.frame.hide()
        self.card.hide()
        self.frame.deleteLater()
        self.card.deleteLater()
        try:
            self.app.settings["tour"] = TOUR
            self.app.save_settings()
        except Exception:
            pass
        if self.done:
            self.done()
        self.deleteLater()


def due(settings):
    """the tour has not been finished or skipped in this version"""
    return settings.get("tour") != TOUR
