"""Real domestic editor widgets, fake league metadata; no game or Build required.

Run: python tools/test_cups_scrolling.py
"""
import copy
import unittest
from unittest.mock import patch

from test_cups_page import App, qa, recipe, B, GameCupsEditor, OurCupsEditor
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QStyle, QStyleOptionSlider


class DomesticScrolling(unittest.TestCase):
    def test_both_editors(self):
        for editor_class in (GameCupsEditor, OurCupsEditor):
            with self.subTest(editor=editor_class.__name__):
                self.check_editor(editor_class)

    def check_editor(self, editor_class):
        app = App()
        app.project.recipe = recipe()
        app.project.recipe['leagues'] = [
            dict(name='League %02d' % i, country='Test', clubs=20, cup=True)
            for i in range(45)]
        committed = copy.deepcopy(app.project.recipe)
        with patch.object(B.B, 'game_tops', return_value=[
                (i, 'Game %02d' % i, False) for i in range(45)]):
            editor = editor_class(None, app.project)
        self.addCleanup(editor.close)
        editor.resize(1000, 650)
        editor.show()
        qa.processEvents()
        table = editor.table
        scroll = table.verticalScrollBar()
        self.assertGreater(scroll.maximum(), 15)
        initial = editor.state()

        # Native mouseMoveEvent calls virtual edit() for each hovered cell.
        # Include partial rows and persistent checkbox/name/logo cell widgets.
        for y in (table.viewport().height() - 2, 1):
            for col in (0, 1, 2, 3):
                scroll.setValue(10)
                qa.processEvents()
                pos = QPointF(table.columnViewportPosition(col) + 15, y)
                focus = qa.focusWidget()
                event = QMouseEvent(QEvent.MouseMove, pos,
                                    QPointF(table.viewport().mapToGlobal(pos.toPoint())),
                                    Qt.NoButton, Qt.NoButton, Qt.NoModifier)
                qa.sendEvent(table.viewport(), event)
                QTest.qWait(80)
                self.assertEqual(scroll.value(), 10, (y, col))
                self.assertIs(qa.focusWidget(), focus)
        QTest.qWait(qa.doubleClickInterval() + 150)
        self.assertEqual(scroll.value(), 10)
        self.assertEqual(editor.state(), initial)

        # A click still focuses and edits an embedded name field.
        field = table.cellWidget(10, 2)
        QTest.mouseClick(field, Qt.LeftButton)
        QTest.keyClicks(field, 'Draft name')
        self.assertEqual(field.text(), 'Draft name')

        scroll.setValue(10)
        pos = QPointF(50, 70)
        wheel = QWheelEvent(pos, QPointF(table.viewport().mapToGlobal(pos.toPoint())),
                            QPoint(), QPoint(0, -120), Qt.NoButton,
                            Qt.NoModifier, Qt.NoScrollPhase, False)
        qa.sendEvent(table.viewport(), wheel)
        self.assertGreater(scroll.value(), 10)

        scroll.setValue(10)
        option = QStyleOptionSlider()
        scroll.initStyleOption(option)
        handle = scroll.style().subControlRect(QStyle.CC_ScrollBar, option,
                                               QStyle.SC_ScrollBarSlider, scroll)
        start = handle.center()
        QTest.mousePress(scroll, Qt.LeftButton, pos=start)
        QTest.mouseMove(scroll, start + QPoint(0, 60))
        QTest.mouseRelease(scroll, Qt.LeftButton, pos=start + QPoint(0, 60))
        self.assertGreater(scroll.value(), 10)

        table.setFocus()
        table.setCurrentCell(10, 0)
        before = table.currentRow()
        QTest.keyClick(table, Qt.Key_PageDown)
        self.assertGreater(table.currentRow(), before)
        self.assertGreater(scroll.value(), 10)
        self.assertTrue(table.hasAutoScroll())  # actual drag-selection remains native
        self.assertEqual(app.project.recipe, committed)
        self.assertEqual(field.text(), 'Draft name')


if __name__ == '__main__':
    unittest.main()
