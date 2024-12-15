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

from .required_combobox import RequiredCombobox, ComboboxPlaceholderListView

if qtmajor > 5:
    QCheckState = Qt.CheckState
    QCheckStateRole = Qt.ItemDataRole.CheckStateRole
    QtKeys = Qt.Key
    QEventTypes = QEvent.Type
else:
    QCheckState = Qt
    QCheckStateRole = Qt.CheckStateRole
    QtKeys = Qt
    QEventTypes = QEvent.Type


class MultiComboBoxQt5(RequiredCombobox):
    """
    from https://gis.stackexchange.com/a/351152
    """

    # Subclass Delegate to increase item height
    class Delegate(QStyledItemDelegate):
        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            size.setHeight(20)
            return size

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Make the combo editable to set a custom text, but readonly
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        # Make the lineedit the same color as QPushButton
        # palette = qApp.palette()
        # palette.setBrush(QPalette.Base, palette.button())
        # self.lineEdit().setPalette(palette)

        # Use custom delegate
        self.setItemDelegate(MultiComboBoxQt5.Delegate())

        # Update the text when an item is toggled
        self.model().dataChanged.connect(self.updateText)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False

        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

    def resizeEvent(self, event):
        # Recompute text to elide as needed
        self.updateText()
        super().resizeEvent(event)

    def eventFilter(self, object, event):
        if object == self.lineEdit():
            if event.type() == QEventTypes.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False

        if object == self.view().viewport():
            if event.type() == QEventTypes.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().item(index.row())

                if item.checkState() == QCheckState.Checked:
                    item.setCheckState(QCheckState.Unchecked)
                else:
                    item.setCheckState(QCheckState.Checked)
                return True
        return False

    def showPopup(self):
        super().showPopup()
        # When the popup is displayed, a click on the lineedit should close it
        self.closeOnLineEditClick = True

    def hidePopup(self):
        super().hidePopup()
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event):
        # After timeout, kill timer, and reenable click on line edit
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False

    def updateText(self):
        texts = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == QCheckState.Checked:
                texts.append(self.model().item(i).text())
        text = ", ".join(texts)

        # Compute elided text (with "...")
        metrics = QFontMetrics(self.lineEdit().font())
        elidedText = metrics.elidedText(text, Qt.ElideRight, self.lineEdit().width())
        self.lineEdit().setText(elidedText)

    def addItem(self, text, data=None):
        item = QStandardItem()
        item.setText(text)
        if data is None:
            item.setData(text)
        else:
            item.setData(data)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setData(QCheckState.Unchecked, QCheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts, datalist=None):
        for i, text in enumerate(texts):
            try:
                data = datalist[i]
            except (TypeError, IndexError):
                data = None
            self.addItem(text, data)

    def currentData(self):
        # Return the list of selected items data
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == QCheckState.Checked:
                res.append(self.model().item(i).data())
        return res

    def setCurrentText(self, selected_text: str):
        # Uncheck all items first
        for i in range(self.model().rowCount()):
            self.model().item(i).setCheckState(QCheckState.Unchecked)

        # Check the items specified in selected_text
        for text in selected_text.split(", "):
            for i in range(self.model().rowCount()):
                if self.model().item(i).text() == text:
                    self.model().item(i).setCheckState(QCheckState.Checked)
                    break
        self.updateText()

    def addSelectedItem(self, text: str):
        for i in range(self.model().rowCount()):
            if self.model().item(i).text() == text:
                self.model().item(i).setCheckState(QCheckState.Checked)
                break

    def hasMultipleSelected(self):
        return len(self.currentData()) > 1

    def setWidthToLargestItem(self):
        max_width = 0
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            width = self.fontMetrics().boundingRect(item.text()).width()
            if width > max_width:
                max_width = width
        self.setMinimumWidth(max_width + 20)
        self.updateGeometry()
        self.view().setMinimumWidth(max_width + 20)


class CustomCheckboxListView(ComboboxPlaceholderListView):
    def mousePressEvent(self, event):
        # Allow toggling the check state by clicking the label
        # Without this only clicking the checkbox would toggle the check state
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                item = self.model().itemFromIndex(index)
                if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    if item.checkState() == Qt.CheckState.Checked:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        item.setCheckState(Qt.CheckState.Checked)
                return
        # Calling the default mousePressEvent would make it so that the check state
        # is toggled while pressing and reset on releasing the mouse button
        # super().mousePressEvent(event)

    def keyPressEvent(self, event):
        # Selecting an item
        if event.key() in (QtKeys.Key_Space, QtKeys.Key_Return, QtKeys.Key_Enter):
            index = self.currentIndex()
            if index.isValid():
                item = self.model().itemFromIndex(index)
                if item.checkState() == Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setCheckState(Qt.CheckState.Checked)
        # Always call the default keyPressEvent to allow navigation
        # and for ComboboxPlaceholderListView to handle keeping the popup open
        super().keyPressEvent(event)


class MultiComboBoxQt6(RequiredCombobox):
    """
    Originally from https://stackoverflow.com/a/77755095 but much edited
    A QComboBox that allows multiple items to be selected using checkboxes.
    Clicking the checkbox or item will toggle the check state.
    The selected value is a concatenation of the checked items' text in the QLineEdit.
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, auto_size=True, **kwargs)
        # self.setEditable(True)
        # Use the custom view
        self.setView(CustomCheckboxListView(self))

        # Connect to the dataChanged signal to update the text
        self.model().dataChanged.connect(self.updateText)

    def make_item_from_text(self, text: str, data=None):
        item = QStandardItem()
        item.setText(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(QCheckState.Unchecked, QCheckStateRole)
        if data:
            item.setData(data)
        return item

    def addItem(self, text: str, data=None):
        item = self.make_item_from_text(text, data)
        # Use the PlaceHolderCombobox method to add the item,
        # so it can manage the placeholder text
        super().addItem(item)

    def addItems(self, items_list: list[str]):
        items = [self.make_item_from_text(item) for item in items_list]
        super().addItems(items)

    def updateText(self):
        selected_items = [self.model().item(i).text() for i in range(self.model().rowCount())
                          if self.model().item(i).checkState() == QCheckState.Checked]
        self.lineEdit().setText(", ".join(selected_items))

    def showPopup(self):
        super().showPopup()
        # Set the state of each item in the dropdown
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            combo_box_view = self.view()
            combo_box_view.setRowHidden(i, False)
            check_box = combo_box_view.indexWidget(item.index())
            if check_box:
                check_box.setChecked(item.checkState() == QCheckState.Checked)

    def hidePopup(self):
        # Update the check state of each item based on the checkbox state
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            combo_box_view = self.view()
            check_box = combo_box_view.indexWidget(item.index())
            if check_box:
                item.setCheckState(QCheckState.Checked if check_box.isChecked() else QCheckState.Unchecked)
        super().hidePopup()

    def setCurrentText(self, selected_text: str):
        for text in selected_text.split(", "):
            for i in range(self.model().rowCount()):
                if self.model().item(i).text() == text:
                    self.model().item(i).setCheckState(QCheckState.Checked)
                    break
        self.updateText()

    def currentData(self):
        # Return the list of selected items data
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == QCheckState.Checked:
                res.append(self.model().item(i).text())
        return res

    def addSelectedItem(self, text: str):
        for i in range(self.model().rowCount()):
            if self.model().item(i).text() == text:
                self.model().item(i).setCheckState(QCheckState.Checked)
                break

    def hasMultipleSelected(self):
        return len(self.currentData()) > 1
