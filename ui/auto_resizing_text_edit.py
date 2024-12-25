from .required_text_input import RequiredTextEdit


class AutoResizingTextEdit(RequiredTextEdit):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.textChanged.connect(self.autoResize)

    def autoResize(self):
        margins = self.contentsMargins()
        height = 0
        document = self.document()
        margin = (margins.top() + margins.bottom()) * 2
        if not document:
            # Set a reasonable one-line height
            self.setFixedHeight(self.fontMetrics().height() + margin)
            return

        block = document.begin()
        while block.isValid():
            height += int(self.blockBoundingRect(block).height())
            block = block.next()

        height += margin
        self.setFixedHeight(int(height))

    def resizeEvent(self, event):
        self.autoResize()
        super().resizeEvent(event)
