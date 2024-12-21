from .required_text_input import RequiredTextEdit


class AutoResizingTextEdit(RequiredTextEdit):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.textChanged.connect(self.autoResize)

    def autoResize(self):
        document = self.document()
        margins = self.contentsMargins()
        height = 0

        block = document.begin()
        while block.isValid():
            height += self.blockBoundingRect(block).height()
            block = block.next()

        height += (margins.top() + margins.bottom()) * 2
        self.setFixedHeight(int(height))

    def resizeEvent(self, event):
        self.autoResize()
        super().resizeEvent(event)
