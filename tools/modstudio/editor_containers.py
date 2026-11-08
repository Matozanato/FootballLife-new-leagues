"""Size tab/stack containers from the active editor, keeping hidden views out of layout."""
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QTabWidget, QStackedWidget, QStyle, QStyleOptionTabWidgetFrame


class SectionTabs(QTabWidget):
    """A hidden domestic table must not set Continental's minimum page height."""

    def tabbed_size(self, content):
        bar = self.tabBar().minimumSizeHint()
        size = QSize(max(content.width(), bar.width()), content.height() + bar.height())
        option = QStyleOptionTabWidgetFrame()
        self.initStyleOption(option)
        return self.style().sizeFromContents(QStyle.CT_TabWidget, option, size, self)

    def minimumSizeHint(self):
        current = self.currentWidget()
        if current is None:
            return super().minimumSizeHint()
        return self.tabbed_size(current.minimumSizeHint().expandedTo(current.minimumSize()))

    def sizeHint(self):
        current = self.currentWidget()
        return self.tabbed_size(current.sizeHint()) if current else super().sizeHint()

    def hasHeightForWidth(self):
        current = self.currentWidget()
        return bool(current and current.hasHeightForWidth())

    def heightForWidth(self, width):
        current = self.currentWidget()
        if not current or not current.hasHeightForWidth():
            return -1
        frame = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth, None, self)
        height = current.layout().minimumHeightForWidth(max(0, width - 2 * frame))
        return self.tabbed_size(QSize(0, height)).height()



class EditorStack(QStackedWidget):
    def minimumSizeHint(self):
        current = self.currentWidget()
        return current.minimumSizeHint().expandedTo(current.minimumSize()) if current else super().minimumSizeHint()

    def sizeHint(self):
        current = self.currentWidget()
        return current.sizeHint() if current else super().sizeHint()

    def hasHeightForWidth(self):
        current = self.currentWidget()
        return bool(current and current.hasHeightForWidth())

    def heightForWidth(self, width):
        current = self.currentWidget()
        if not current or not current.hasHeightForWidth():
            return -1
        return current.layout().minimumHeightForWidth(width) if current.layout() else current.heightForWidth(width)
