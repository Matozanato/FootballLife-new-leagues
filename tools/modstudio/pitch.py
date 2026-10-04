"""A pitch with a formation on it: the eleven places, each with its role and optionally a name.

Places are mktactics' (place, role, depth, width): depth 3 (the goal line) .. 46 (up front),
width 0 (left) .. 100 (right) as the team attacks -- drawn attacking up the widget, or, when the
widget is wider than tall, attacking to the right (room for the names under a squad list)."""
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QVBoxLayout, QWidget

import mktactics
import lbplayers
from . import theme
from .i18n import _

GRASS, GRASS2, LINE = "#2E6B3A", "#2A6235", "#CFE3D2"
DEPTH = 50.0

# where the engine's fixed 4-2-3-1 (lbplayers.LINEUP) stands, for a club with no formation of its own
_SPOTS = {"GK": [(3, 50)], "CB": [(10, 38), (10, 62)], "RB": [(12, 85)], "LB": [(12, 15)],
          "DMF": [(19, 38), (19, 62)], "RMF": [(31, 85)], "LMF": [(31, 15)], "AMF": [(32, 50)],
          "CF": [(43, 50)]}


def default_places():
    used, out = {}, []
    for n, role in enumerate(lbplayers.LINEUP):
        k = used.get(role, 0)
        used[role] = k + 1
        d, w = _SPOTS[role][k]
        out.append((n, mktactics.ROLES.index(role), d, w))
    return out


class Pitch(QWidget):
    """the formation; clicking a place emits picked(place)"""
    picked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.places, self.names, self.mark = default_places(), {}, None
        self.setMinimumSize(220, 250)
        self.setMouseTracking(True)

    def show_places(self, places, names=None, mark=None):
        self.places = list(places) if places else default_places()
        self.names = names or {}
        self.mark = mark
        self.update()

    def _flat(self):
        return self.width() > self.height() * 1.2

    def _field(self):
        m = 8
        r = QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)
        if self._flat():
            w = min(r.width(), r.height() * 1.75)
            return QRectF(r.center().x() - w / 2, r.top(), w, r.height())
        h = r.height()
        w = min(r.width(), h * 0.85)                # a little wider than a real pitch: room for names
        return QRectF(r.center().x() - w / 2, r.top(), w, h)

    def _at(self, depth, width):
        f = self._field()
        if self._flat():
            return QPointF(f.left() + f.width() * (0.05 + 0.9 * depth / DEPTH),
                           f.top() + f.height() * (0.06 + 0.78 * width / 100.0))
        return QPointF(f.left() + f.width() * (0.08 + 0.84 * width / 100.0),
                       f.bottom() - f.height() * (0.04 + 0.9 * depth / DEPTH))

    def _rad(self):
        f = self._field()
        return max(10.0, min(f.width(), f.height()) / 22)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        f = self._field()
        p.fillRect(self.rect(), QColor(theme.PANEL))
        flat = self._flat()
        for i in range(8):                          # mown stripes
            if flat:
                band = QRectF(f.left() + f.width() * i / 8, f.top(), f.width() / 8, f.height())
            else:
                band = QRectF(f.left(), f.top() + f.height() * i / 8, f.width(), f.height() / 8)
            p.fillRect(band, QColor(GRASS if i % 2 else GRASS2))
        p.setPen(QPen(QColor(LINE), 1.2))
        p.drawRect(f)
        if flat:
            p.drawLine(QPointF(f.center().x(), f.top()), QPointF(f.center().x(), f.bottom()))
            p.drawEllipse(f.center(), f.height() * 0.14, f.height() * 0.14)
            for left in (True, False):              # penalty and goal areas
                bw, bh = f.width() * 0.15, f.height() * 0.58
                x = f.left() if left else f.right() - bw
                p.drawRect(QRectF(x, f.center().y() - bh / 2, bw, bh))
                gw, gh = f.width() * 0.055, f.height() * 0.26
                x = f.left() if left else f.right() - gw
                p.drawRect(QRectF(x, f.center().y() - gh / 2, gw, gh))
        else:
            p.drawLine(QPointF(f.left(), f.center().y()), QPointF(f.right(), f.center().y()))
            p.drawEllipse(f.center(), f.width() * 0.14, f.width() * 0.14)
        for top in (() if flat else (True, False)):     # penalty and goal areas
            bw, bh = f.width() * 0.58, f.height() * 0.15
            y = f.top() if top else f.bottom() - bh
            p.drawRect(QRectF(f.center().x() - bw / 2, y, bw, bh))
            gw, gh = f.width() * 0.26, f.height() * 0.055
            y = f.top() if top else f.bottom() - gh
            p.drawRect(QRectF(f.center().x() - gw / 2, y, gw, gh))
        small = QFont(self.font())
        small.setPointSizeF(max(8.0, self.font().pointSizeF() - 0.5))
        bold = QFont(small)
        bold.setBold(True)
        rad = self._rad()
        fm = QFontMetrics(small)
        line = fm.height()
        spots = [self._at(d, w) for _p, _r, d, w in self.places]
        for n, (place, role, depth, width) in enumerate(self.places):
            c = spots[n]
            # a label is as wide as the gap to the nearest place beside it, so two centre
            # backs side by side do not write their names over each other
            room = min([abs(o.x() - c.x()) for m, o in enumerate(spots)
                        if m != n and abs(o.y() - c.y()) < rad + 2 * line] + [170.0]) - 6
            on = place == self.mark
            p.setPen(QPen(QColor("#FFFFFF" if on else "#10301A"), 2 if on else 1))
            p.setBrush(QColor(theme.WARN if role == 0 else (theme.ACCENT if on else "#F2F5F3")))
            p.drawEllipse(c, rad, rad)
            p.setFont(bold)
            p.setPen(QColor("#FFFFFF" if on or role == 0 else "#10301A"))
            p.drawText(QRectF(c.x() - rad, c.y() - rad, 2 * rad, 2 * rad), Qt.AlignCenter, str(place))     # as the squad order counts
            label = mktactics.ROLES[role]
            name = self.names.get(place)
            p.setFont(small)
            if flat:
                # one line, the role and the surname: the places of a line stand close one under
                # the other; the label may reach the circle of the nearest place beside it
                gap = min([abs(o.x() - c.x()) for m, o in enumerate(spots)
                           if m != n and abs(o.y() - c.y()) < rad + line] + [120.0])
                room = 2 * (gap - rad) - 8
                if name:
                    label = fm.elidedText(label + " " + name.split()[-1], Qt.ElideRight, int(max(room, 2 * rad)))
                box = QRectF(c.x() - room / 2 - 20, c.y() + rad + 1, room + 40, line + 2)
                self._label(p, box, Qt.AlignHCenter | Qt.AlignTop, label)
                continue
            if name:
                label += "\n" + fm.elidedText(name, Qt.ElideRight, int(max(room, 2 * rad)))
            if role == 0 and not flat:              # the goalkeeper's label beside him: below is the line
                room = f.right() - c.x() - rad - 4
                box = QRectF(c.x() + rad + 4, c.y() - line, room, 2 * line + 2)
                if name:
                    label = mktactics.ROLES[role] + "\n" + fm.elidedText(name, Qt.ElideRight, int(room))
                self._label(p, box, Qt.AlignLeft | Qt.AlignTop, label)
                continue
            box = QRectF(c.x() - room / 2 - 20, c.y() + rad + 1, room + 40, 2 * line + 2)
            self._label(p, box, Qt.AlignHCenter | Qt.AlignTop, label)
        p.end()

    @staticmethod
    def _label(p, box, align, text):
        """text on a dark plate, so it reads over the grass and the lines"""
        r = p.boundingRect(box, align, text).adjusted(-4, -1, 4, 1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(10, 25, 15, 170))
        p.drawRoundedRect(r, 4, 4)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(box, align, text)

    def mousePressEvent(self, e):
        pos = e.position() if hasattr(e, "position") else QPointF(e.pos())
        best = None
        for place, _r, depth, width in self.places:
            c = self._at(depth, width)
            d = (c.x() - pos.x()) ** 2 + (c.y() - pos.y()) ** 2
            if best is None or d < best[0]:
                best = (d, place)
        if best and best[0] < (self._rad() * 2.2) ** 2:
            self.picked.emit(best[1])


class FormationPick(QWidget):
    """a formation list over a pitch that shows it. first: the label of the no-choice entry
    (the engine's 4-2-3-1, or the league's formation for a club)"""

    def __init__(self, formations, current="", first=None, first_places=None, parent=None):
        super().__init__(parent)
        self.formations = formations
        self.first_places = first_places
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.addItem(first or _("The game's default (4-2-3-1)"), "")
        for e in formations:
            self.combo.addItem("%s   (%s)" % (e["label"], _("%d clubs") % e["clubs"]), e["label"])
        cur = str(current or "")
        i = self.combo.findData(cur) if cur else 0
        if cur and i < 0:                           # a club id, or one no longer listed: keep it
            self.combo.addItem(cur, cur)
            i = self.combo.count() - 1
        self.combo.setCurrentIndex(max(0, i))
        v.addWidget(self.combo)
        self.pitch = Pitch()
        self.pitch.setFixedHeight(260)
        v.addWidget(self.pitch)
        self.combo.currentIndexChanged.connect(lambda _i: self.redraw())
        self.redraw()

    def value(self):
        return self.combo.currentData() or ""

    def redraw(self):
        self.pitch.show_places(places_of(self.formations, self.value()) or self.first_places)


def places_of(formations, label):
    """the places of formation `label` in the list, or None"""
    return next((e["places"] for e in formations if label and e["label"] == label), None)
