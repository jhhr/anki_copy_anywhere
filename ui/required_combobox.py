from typing import Union

# noinspection PyUnresolvedReferences
from aqt.qt import (
    QComboBox,
    QStandardItemModel,
    QStandardItem,
    QListView,
    QLineEdit,
    QStyledItemDelegate,
    QPalette,
    QFontMetrics,
    Qt,
    QEvent,
    qtmajor,
)

if qtmajor > 5:
    QtKeys = Qt.Key
    QEventTypes = QEvent.Type
else:
    QtKeys = Qt
    QEventTypes = QEvent.Type


# Make a dict of QEvent type values to their names for debugging
# QEventTypesByNum = {}
# for name in dir(QEventTypes):
#     value = getattr(QEventTypes, name)
#     if isinstance(value, int):
#         QEventTypesByNum[value] = name

class ComboboxPlaceholderListView(QListView):
    def __init__(self, combobox, **kwargs):
        super().__init__(**kwargs)
        self.combobox = combobox

    def keyPressEvent(self, event):
        # Selecting an item
        if event.key() in (QtKeys.Key_Space, QtKeys.Key_Return, QtKeys.Key_Enter):
            self.combobox.lineEdit().popup_open = True
            return
        super().keyPressEvent(event)


class ComboBoxPlaceholderLineEdit(QLineEdit):
    """
    A QLineEdit that is not editable but still shows a placeholder text. Use with QComboBox.
    To allow showing a placeholder test we must have isReadOnly()=false and isEditable()=true.
    This would let the user type in the line edit, so we need to manually ignore input events.
    """

    def __init__(
            self,
            parent=None,
            placeholder_text: str = None,
            **kwargs
    ):
        super().__init__(
            parent,
            **kwargs
        )
        # Set the default style to vertically center the text so that the
        # text's y's and g's are not cut off at the bottom
        self.setStyleSheet("padding-bottom: 0px; padding-top: 0px;")
        self.setReadOnly(True)
        self.popup_open = False
        if placeholder_text:
            self.setPlaceholderText(placeholder_text)

    def event(self, event):
        # If keyPress is Esc, then proceed normally so you can close the dialog even
        # if the line edit has focus
        if event.type() == QEventTypes.KeyPress and event.key() == QtKeys.Key_Escape:
            return super().event(event)
        # Ignore other key events to prevent user input
        if event.type() in (
                QEventTypes.KeyPress,
                QEventTypes.KeyRelease,
                QEventTypes.InputMethodQuery
        ):
            return True
        return super().event(event)

    def mouseReleaseEvent(self, _):
        # Toggle the QComboBox popup when clicking on the line edit
        # view() is the QListView, the popup, within the QComboBox
        if self.parent().view().isVisible():
            self.parent().hidePopup()
        else:
            self.parent().showPopup()


class RequiredCombobox(QComboBox):
    def __init__(
            self,
            parent=None,
            placeholder_text: str = None,
            is_required: bool = False,
            auto_size: bool = False,
            minimum_width: int = 250,
            **kwargs
    ):
        super().__init__(parent, **kwargs)
        #### Placeholder management
        self.setLineEdit(ComboBoxPlaceholderLineEdit(
            placeholder_text=placeholder_text,
        ))
        self.is_required = is_required
        self.was_valid = True
        self.default_style = self.styleSheet()
        self.required_style = "QComboBox { border: 1px solid darkred; }"
        # Set current index to -1 to show the placeholder text
        self.setCurrentIndex(-1)
        self.setModel(QStandardItemModel(self))

        #### Size management
        self.auto_size = auto_size
        self.max_width = 0
        self.setMinimumWidth(minimum_width)
        if auto_size:
            self.currentTextChanged.connect(self.check_text_width)
        if is_required:
            self.update_required_style()
            # self.currentTextChanged.connect(self.update_required_style)

    def update_required_style(self):
        if self.is_required and not self.currentText() and self.was_valid:
            self.setStyleSheet(self.default_style + self.required_style)
            self.was_valid = False
        elif (not self.is_required or self.currentText()) and not self.was_valid:
            self.setStyleSheet(self.default_style)
            self.was_valid = True

    def set_required_style(self, style: str):
        self.required_style = style
        self.update_required_style()

    def set_required(self, is_required: bool):
        self.is_required = is_required
        self.update_required_style()
        # if not is_required and self.currentTextChanged.isConnected():
        #     self.currentTextChanged.disconnect(self.update_required_style)
        # elif is_required and not self.currentTextChanged.isConnected():
        #     self.currentTextChanged.connect(self.update_required_style)

    def event(self, event: QEvent):
        if hasattr(self, 'is_required') and self.is_required and event.type() in (
                QEventTypes.FocusIn,
                QEventTypes.FocusOut,
                QEventTypes.KeyPress,
                QEventTypes.KeyRelease
        ):
            self.update_required_style()
        return super().event(event)

    def check_text_width(self, text: str):
        item_width = self.view().fontMetrics().boundingRect(text).width()
        self.update_max_width(item_width)

    def update_max_width(self, width: int):
        if width > self.max_width:
            self.max_width = width
            self.set_popup_and_box_width()

    def set_popup_and_box_width(self):
        self.setMaximumWidth(max(self.max_width + 40, self.minimumWidth()))

    def clear(self):
        self.max_width = 0
        super().clear()

    def setPlaceholderText(self, text: str):
        self.lineEdit().setPlaceholderText(text)

    def placeholderText(self):
        return self.lineEdit().placeholderText()

    def unset_current_index(self):
        self.setCurrentIndex(-1)

    def addItem(self, item: Union[str, QStandardItem]):
        if isinstance(item, str):
            item = QStandardItem(item)
        nothing_was_selected = self.currentText() == ""
        self.model().appendRow(item)
        # If there was nothing selected, adding data sets the line edit text to non-empty which
        # hides the placeholder text. Undo this by setting the current index to -1.
        if nothing_was_selected:
            self.unset_current_index()

        if self.auto_size:
            self.check_text_width(item.text())

    def addItems(self, items: list[QStandardItem]):
        nothing_was_selected = self.currentText() == ""
        for item in items:
            self.model().appendRow(item)
            if self.auto_size:
                self.check_text_width(item.text())
        if nothing_was_selected:
            self.unset_current_index()

    def showPopup(self):
        # When the popup is opened by clicking on the line edit, we need to set a flag to prevent
        # it from closing when clicking anywhere else. We check this flag in hidePopup().
        self.lineEdit().popup_open = True
        if self.auto_size:
            self.set_popup_and_box_width()
        super().showPopup()

    def hidePopup(self):
        # When the popup was opened by clicking on the line edit, it's inevitable that the next
        # click anywhere will close it. We can prevent by having a flag that we set when the
        # popup is opened by clicking on the line edit and then checking it here.
        if self.lineEdit().popup_open:
            self.lineEdit().popup_open = False
            return
        self.lineEdit().popup_open = False
        super().hidePopup()
