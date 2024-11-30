# noinspection PyUnresolvedReferences
from aqt.qt import (
    QTextEdit,
    QSizePolicy,
    qtmajor,
)

if qtmajor > 5:
    SizePolicy = QSizePolicy.Policy
else:
    SizePolicy = QSizePolicy


class AutoResizingTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.autoResize)

    def autoResize(self):
        self.document().setTextWidth(self.viewport().width())
        margins = self.contentsMargins()
        height = int(self.document().size().height() + margins.top() + margins.bottom())
        self.setFixedHeight(height)

    def resizeEvent(self, event):
        self.autoResize()
        super().resizeEvent(event)