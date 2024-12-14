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
    def __init__(self, combobox, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.combobox = combobox

    def keyPressEvent(self, event):
        print(f"event.key(): {event.key()}")
        # Selecting an item
        if event.key() in (QtKeys.Key_Space, QtKeys.Key_Return, QtKeys.Key_Enter):
            print("Space, Return, or Enter key pressed")
            self.combobox.lineEdit().popup_open = True
            return
        super().keyPressEvent(event)


class ComboBoxPlaceholderLineEdit(QLineEdit):
    """
    A QLineEdit that is not editable but still shows a placeholder text. Use with QComboBox.
    To allow showing a placeholder test we must have isReadOnly()=false and isEditable()=true.
    This would let the user type in the line edit, so we need to manually ignore input events.
    """

    def __init__(self, placeholder_text: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
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


class PlaceHolderCombobox(QComboBox):
    def __init__(self, parent=None, placeholder_text: str = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setLineEdit(ComboBoxPlaceholderLineEdit(placeholder_text))
        # Set current index to -1 to show the placeholder text
        self.setCurrentIndex(-1)
        self.setModel(QStandardItemModel(self))

    def addItem(self, item: QStandardItem):
        nothing_was_selected = self.currentText() == ""
        self.model().appendRow(item)
        # If there was nothing selected, adding data sets the line edit text to non-empty which
        # hides the placeholder text. Undo this by setting the current index to -1.
        if nothing_was_selected:
            self.setCurrentIndex(-1)

    def addItems(self, items: list[QStandardItem]):
        nothing_was_selected = self.currentText() == ""
        for item in items:
            self.model().appendRow(item)
        if nothing_was_selected:
            self.setCurrentIndex(-1)

    def showPopup(self):
        # When the popup is opened by clicking on the line edit, we need to set a flag to prevent
        # it from closing when clicking anywhere else. We check this flag in hidePopup().
        self.lineEdit().popup_open = True
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
