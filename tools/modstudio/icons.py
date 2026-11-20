"""Icons drawn in code (beta 3, mato 11.11.: "ikonica za povratak naprijed i nazad je cudna").

Back and Forward were the characters "◀" and "▶" of whatever font had them: another size and
another weight on every PC, and soft at 125 % and 150 %. Here they are lines drawn at the size
they are shown in, sharp at every scale of the screen, in the colours of the section buttons next
to them: muted, white under the pointer, dim while there is nowhere to go."""
from PySide6.QtCore import QPoint, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QIconEngine, QPainter, QPainterPath, QPen, QPixmap

NORMAL, HOT, OFF = "#AEB7C4", "#FFFFFF", "#4B5563"


class _Chevron(QIconEngine):
    """way -1: points left, 1: right"""

    def __init__(self, way, normal=NORMAL, hot=HOT, off=OFF):
        super().__init__()
        self._way, self._normal, self._hot, self._off = way, normal, hot, off

    def paint(self, p, rect, mode, _state):
        colour = {QIcon.Disabled: self._off, QIcon.Active: self._hot, QIcon.Selected: self._hot}.get(mode, self._normal)
        s = float(min(rect.width(), rect.height()))
        cx, cy = rect.x() + rect.width() / 2.0, rect.y() + rect.height() / 2.0
        h, w = s * 0.29, s * 0.17                  # half the height, half the depth of the angle
        pen = QPen(QColor(colour), max(1.5, s * 0.125))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        path = QPainterPath()
        path.moveTo(QPointF(cx - self._way * w, cy - h))
        path.lineTo(QPointF(cx + self._way * w, cy))
        path.lineTo(QPointF(cx - self._way * w, cy + h))
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.restore()

    def pixmap(self, size, mode, state):
        pm = QPixmap(size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        self.paint(p, QRect(QPoint(0, 0), size), mode, state)
        p.end()
        return pm

    def actualSize(self, size, _mode, _state):
        return QSize(size)

    def clone(self):
        return _Chevron(self._way, self._normal, self._hot, self._off)


def chevron(way):
    """the Back (-1) or Forward (1) icon"""
    return QIcon(_Chevron(way))
