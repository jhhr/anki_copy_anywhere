# noinspection PyUnresolvedReferences
from aqt.qt import (
    QTextEdit,
    QSizePolicy,
    qtmajor,
)

from .required_text_input import RequiredTextEdit

if qtmajor > 5:
    SizePolicy = QSizePolicy.Policy
else:
    SizePolicy = QSizePolicy


class AutoResizingTextEdit(RequiredTextEdit):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.textChanged.connect(self.autoResize)

    def autoResize(self):
        self.document().setTextWidth(self.viewport().width())
        margins = self.contentsMargins()
        height = int(self.document().size().height() + margins.top() + margins.bottom())
        self.setFixedHeight(height)

    def resizeEvent(self, event):
        self.autoResize()
        super().resizeEvent(event)
