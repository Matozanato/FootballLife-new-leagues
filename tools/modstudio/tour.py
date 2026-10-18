"""The quick tour: the first start of Mod Studio 0.2.4 shows where things are now, one place at a
time (mato 18.10.: "kod prvog pokretanja 0.2.4 pojavi wizard koji objasni gdje se sto nalazi").

A card with the step's words and Back / Next / Skip floats over the main window next to the thing it
talks about, which gets an orange frame. Nothing is opened, clicked or changed: the window works as
usual under it, and an update box or the first unpack of the game's tables goes on beside it.
Finished or skipped, it is not shown again (settings "tour"); Help > Quick tour shows it again.

The same card walks a player through putting a Modpack in the game (modpack_steps; mato 18.10.: "jel
ima wizard upute kak ubaciti modpack, step by step? To usto treba"): Help > Install a Modpack, step
by step, or the button on the last card of the quick tour. It opens 2. My world so the frame can show
+ Add..., and clicks nothing. A third (edit_steps; mato 18.10.: "wizard i za uredjivanje packova, znas
da ce ljudi to htjeti") changes a Modpack already in the game: Make it editable... (B85), the tabs,
Build and install, a new Master League, and Restore points to have it back as it came: Help > Edit a
Modpack, step by step, or the button on the last card of the Modpack guide."""
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

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
         _("The user guide, updates, this tour again and Install a Modpack, step by step. Questions and "
           "bugs: our Discord, FL Mod Studio. Have fun!"), getattr(app, "help_btn", None)),
    ]


def _my_world(app):
    """2. My world open (the tab that was open stays), for the step that points into it"""
    mw = getattr(app, "my_world", None)
    if mw is not None and not mw.isVisible():
        app.open_page("Build")


def modpack_steps(app):
    """putting a Modpack (a world zip) in the game, every click in order; the same words as Way A of
    guides/*/install-a-pack.md. A step's widget can be a function: found when the step shows, after
    its opener (the fourth item) ran"""
    nb = getattr(app, "nav_buttons", {})
    return [
        (_("Install a Modpack, step by step"),
         _("A Modpack is a ready world in one zip: leagues, clubs, players, kits and scoreboards. Close the "
           "game first, and do not unpack the zip. The orange frame shows where to click: you click, this "
           "card does not."), None),
        (_("Open My world"),
         _("Click 2. My world. Your worlds are there, as cards."), nb.get("World")),
        (_("+ Add..."),
         _("Click + Add..., then Choose a file... and pick the Modpack zip (or drag the zip onto that "
           "window). A green line says Found: a world zip. Click Add."),
         lambda: getattr(getattr(app, "my_world", None), "add_btn", None), _my_world),
        (_("Wait while it looks inside"),
         _("The page Import your world opens and looks inside the zip. A big Modpack takes a minute or two. "
           "Then it says what it is (a ready world to play) and how many leagues it has."), None),
        (_("Install the world"),
         _("Click Install the world. If an older Modpack is installed, it asks to replace it: Yes (your "
           "saves are not touched). Mod Studio copies the world, puts its modules in the game and switches "
           "the world on: no Build needed. Wait for the window Ready to play."), None),
        (_("Start the game"),
         _("Click Start the game and start a NEW Master League: an old career does not get the new "
           "leagues."), getattr(app, "play_btn", None)),
        (_("Another world later"),
         _("Every world is a card in 2. My world; the green one is in the game. Activate on another card "
           "puts that one in the game, and each world keeps its own careers. Stuck? Help > User guide, or "
           "ask on our Discord, FL Mod Studio."), nb.get("World")),
    ]


def _build_tab(app):
    """the Build tab of 2. My world, where Build and install is"""
    b = getattr(app, "pages", {}).get("Build")
    if b is None or not b.isVisible():
        app.open_page("Build")


def edit_steps(app):
    """changing a Modpack (a ready world from a zip) that is in the game, every click in order: the
    B85 way (myworld.MyWorld.make_editable), then Build and install"""
    nb, nh = getattr(app, "nav_buttons", {}), getattr(app, "nav_heads", {})

    def mw(name):
        return lambda: getattr(getattr(app, "my_world", None), name, None)
    return [
        (_("Edit a Modpack, step by step"),
         _("A Modpack you installed can be changed: leagues out or in, clubs, players, kits, stadiums. It is "
           "changed where it is, under its own name, and all of it is copied first. Close the game first. "
           "The orange frame shows where to click: you click, this card does not."), None),
        (_("The Modpack in the game"),
         _("Click 2. My world. The Modpack's card must be green (in the game): if it is not, click Activate "
           "on its card."), nb.get("World")),
        (_("Make it editable..."),
         _("Click Make it editable... at the top of My world (it shows only for a world that came in a zip) "
           "and say Yes. Mod Studio copies all of it first; then the world is one you can change."),
         mw("b_edit"), _my_world),
        (_("Change it"),
         _("Make your changes in these tabs: Leagues (take a league out, add one, change one), Clubs, "
           "Players, Kits, Stadiums. Nothing reaches the game yet."),
         lambda: (getattr(getattr(app, "my_world", None), "tab_btn", None) or {}).get("Leagues"), _my_world),
        (_("Build and install"),
         _("On the Build tab click Build and install. A big Modpack takes a few minutes; wait until it says "
           "it is done. Only then do your changes reach the game."),
         lambda: getattr(getattr(app, "pages", {}).get("Build"), "b_all", None), _build_tab),
        (_("Start the game"),
         _("Click Start the game and start a NEW Master League: a career saved before keeps the world it "
           "started with."), getattr(app, "play_btn", None)),
        (_("Changed your mind?"),
         _("4. Tools > Restore points has the Modpack as it came: Put this copy back makes it the ready world "
           "again. Stuck? Help > User guide, or ask on our Discord, FL Mod Studio."), nh.get("TOOLS")),
    ]


class Tour(QObject):
    """the card and the frame over `app`, the main window; closes itself when finished or skipped.
    `guide` is "tour" (the quick tour, remembered in settings when seen), "modpack" or "edit";
    `follow` is (label, function): a button on the last card that ends this one and starts that"""

    def __init__(self, app, done=None, guide="tour", follow=None):
        super().__init__(app)
        self.app, self.done, self.i, self.guide, self.follow = app, done, 0, guide, follow
        self.steps = {"modpack": modpack_steps, "edit": edit_steps}.get(guide, steps)(app)
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
        self.skip = QPushButton(_("Skip the tour") if guide == "tour" else _("Close"))
        self.skip.clicked.connect(lambda: self.finish())
        self.then = QPushButton(follow[0] if follow else "")
        self.then.setObjectName("blue")
        self.then.clicked.connect(lambda: self.finish(then=True))
        self.then.hide()
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
        v.addWidget(self.then, 0, Qt.AlignRight)
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
            if w is not None and not isinstance(w, QWidget):
                w = w()
            return w if w is not None and w.isVisible() else None
        except RuntimeError:               # deleted
            return None

    def show_step(self, i):
        self.i = max(0, min(i, len(self.steps) - 1))
        title, text = self.steps[self.i][:2]
        if len(self.steps[self.i]) > 3:
            try:
                self.steps[self.i][3](self.app)        # opens what the step points into
            except Exception:
                pass
        self.count.setText(_("Step %d of %d") % (self.i + 1, len(self.steps)))
        self.title.setText(title)
        self.text.setText(text)
        self.back.setEnabled(self.i > 0)
        last = self.i + 1 == len(self.steps)
        self.next.setText(_("Done") if last else _("Next"))
        self.then.setVisible(bool(self.follow) and last)
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
        # a page taller than the window sits in a scroll area: scroll the widget into sight first,
        # or the frame and card point below the window's edge (Build and install on a small
        # window in French, the edit guide's step 5)
        p = t.parentWidget()
        while p is not None and p is not self.app:
            if isinstance(p, QScrollArea) and p.widget() is not None and p.widget().isAncestorOf(t):
                p.ensureWidgetVisible(t, 8, 8)
            p = p.parentWidget()
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

    def finish(self, then=False):
        """seen: not shown at the next start (Help > Quick tour still shows it); `then`: the
        follow button was pressed, its guide starts once this one is gone"""
        self.app.removeEventFilter(self)
        self.frame.hide()
        self.card.hide()
        self.frame.deleteLater()
        self.card.deleteLater()
        if self.guide == "tour":
            try:
                self.app.settings["tour"] = TOUR
                self.app.save_settings()
            except Exception:
                pass
        if self.done:
            self.done()
        if then and self.follow:
            self.follow[1]()
        self.deleteLater()


def due(settings):
    """the tour has not been finished or skipped in this version"""
    return settings.get("tour") != TOUR
