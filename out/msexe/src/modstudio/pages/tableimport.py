"""Import a squad from a table: any CSV of players (typed by hand, off a website, from Football
Manager or an EA FC database) becomes the squad of the club open on the Players page.  The
columns are matched by name and shown here to be changed; squadimport.py does the conversion."""
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QScrollArea,
                               QSpinBox, QVBoxLayout, QWidget)

import squadimport as Q
from ..i18n import _
from ..ui import hint, row, section


class ImportDialog(QDialog):
    """shows the table's columns with what each one is taken for; mapping() and level() after OK"""

    def __init__(self, parent, path, head, rows, room):
        super().__init__(parent)
        self.setWindowTitle(_("Import a squad from a table"))
        self.setMinimumSize(720, 560)
        self.head = head
        v = QVBoxLayout(self)
        v.addWidget(hint(_("%s: %d players. Each column is taken for what its name says; change any that "
                           "is wrong, or set it to (skip). What the table does not give -- abilities it has "
                           "no column for, height, playing style -- comes from the game's own players of the "
                           "same position and rating.") % (path, len(rows))))
        if room:
            v.addWidget(hint(room))
        v.addWidget(section("Columns"))
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.addWidget(QLabel("<b>%s</b>" % _("Column")), 0, 0)
        grid.addWidget(QLabel("<b>%s</b>" % _("First values")), 0, 1)
        grid.addWidget(QLabel("<b>%s</b>" % _("Taken as")), 0, 2)
        guess = Q.guess(head, rows)
        self.boxes = []
        for i, h in enumerate(head):
            sample = ", ".join(r[i] for r in rows[:3] if i < len(r) and r[i])
            s = QLabel(sample[:60])
            s.setObjectName("hint")
            box = QComboBox()
            box.addItem(_("(skip)"), None)
            for t in Q.TARGETS:
                box.addItem(_(Q.label(t)), t)
            box.setCurrentIndex(max(0, box.findData(guess.get(i))))
            grid.addWidget(QLabel(h or "(%d)" % (i + 1)), i + 1, 0)
            grid.addWidget(s, i + 1, 1)
            grid.addWidget(box, i + 1, 2)
            self.boxes.append(box)
        inner = QWidget()
        inner.setLayout(grid)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(inner)
        v.addWidget(sc, 1)
        self.lvl = QSpinBox()
        self.lvl.setRange(40, 99)
        self.lvl.setValue(65)
        v.addWidget(row(QLabel(_("Rating of a player the table gives no rating for")), self.lvl))
        v.addWidget(hint(_("Ratings in 1-20 (Football Manager) are stretched to the game's 40-99; others are "
                           "read as they are.")))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("Import"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def mapping(self):
        return {i: b.currentData() for i, b in enumerate(self.boxes) if b.currentData()}

    def level(self):
        return self.lvl.value()
