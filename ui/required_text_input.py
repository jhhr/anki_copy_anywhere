# noinspection PyUnresolvedReferences
from aqt.qt import (
    QLineEdit,
    QTextEdit,
    QEvent,
    qtmajor,
)

if qtmajor > 5:
    QEventTypes = QEvent.Type
else:
    QEventTypes = QEvent.Type


class RequiredLineEdit(QLineEdit):
    """
    A QLineEdit that shows a required style when empty.
    """

    def __init__(
            self,
            parent=None,
            is_required: bool = False,
            required_style: str = "border: 1px solid darkred;",
            default_style: str = "",
            **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.is_required = is_required
        self.required_style = required_style
        self.default_style = default_style
        self.was_valid = True
        if default_style:
            self.setStyleSheet(default_style)
        if is_required:
            self.update_required_style()
            # self.textChanged.connect(self.update_required_style)

    def update_required_style(self) -> str:
        if self.is_required and not self.text() and self.was_valid:
            self.setStyleSheet(self.default_style + self.required_style)
            self.was_valid = False
        elif (not self.is_required or self.text()) and not self.was_valid:
            self.setStyleSheet(self.default_style)
            self.was_valid = True

    def event(self, event: QEvent):
        if hasattr(self, 'is_required') and self.is_required and event.type() in (
                QEventTypes.FocusIn,
                QEventTypes.FocusOut,
                QEventTypes.KeyPress,
                QEventTypes.KeyRelease
        ):
            self.update_required_style()
        return super().event(event)

    def set_required_style(self, style: str):
        self.required_style = style
        self.update_required_style()

    def set_required(self, is_required: bool):
        self.is_required = is_required
        self.update_required_style()
        # if not is_required and self.textChanged.isConnected():
        #     self.textChanged.disconnect(self.update_required_style)
        # elif is_required and not self.textChanged.isConnected():
        #     self.textChanged.connect(self.update_required_style)


class RequiredTextEdit(QTextEdit):
    """
    A QLineEdit that shows a required style when empty.
    """

    def __init__(
            self,
            parent=None,
            is_required: bool = False,
            required_style: str = "border: 1px solid darkred;",
            default_style: str = "",
            **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.is_required = is_required
        self.was_valid = True
        self.required_style = required_style
        self.default_style = default_style
        # Set this as a default for all text edits as editing fields
        # with this addons requires plain text pretty much always
        self.setAcceptRichText(False)
        if default_style:
            self.setStyleSheet(default_style)
        if is_required:
            self.update_required_style()
            # self.textChanged.connect(self.update_required_style)

    def update_required_style(self):
        if self.is_required and not self.toPlainText() and self.was_valid:
            self.setStyleSheet(self.default_style + self.required_style)
            self.was_valid = False
        elif (not self.is_required or self.toPlainText()) and not self.was_valid:
            self.setStyleSheet(self.default_style)
            self.was_valid = True

    def event(self, event: QEvent):
        if hasattr(self, 'is_required') and self.is_required and event.type() in (
                QEventTypes.FocusIn,
                QEventTypes.FocusOut,
                QEventTypes.KeyPress,
                QEventTypes.KeyRelease
        ):
            self.update_required_style()
        return super().event(event)

    def set_required_style(self, style: str):
        self.required_style = style
        self.update_required_style()

    def set_required(self, is_required: bool):
        self.is_required = is_required
        self.update_required_style()
        # if not is_required and self.textChanged.isConnected():
        #     self.textChanged.disconnect(self.update_required_style)
        # elif is_required and not self.textChanged.isConnected():
        #     self.textChanged.connect(self.update_required_style)
