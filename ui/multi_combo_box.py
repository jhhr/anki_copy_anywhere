from typing import Optional, cast, Iterable
from aqt.qt import (
    QStandardItem,
    QStandardItemModel,
    QCheckBox,
    QEvent,
    Qt,
    qtmajor,
)

from .required_combobox import RequiredCombobox, ComboboxPlaceholderListView

if qtmajor > 5:
    QCheckState = Qt.CheckState
    QCheckStateRole = Qt.ItemDataRole.CheckStateRole
    QItemIsUserCheckable = Qt.ItemFlag.ItemIsUserCheckable
    QItemIsEnabled = Qt.ItemFlag.ItemIsEnabled
    QtKeys = Qt.Key
    QEventTypes = QEvent.Type
    QDisplayRole = Qt.ItemDataRole.DisplayRole
else:
    QCheckState = Qt  # type: ignore
    QCheckStateRole = Qt.CheckStateRole  # type: ignore
    QItemIsUserCheckable = Qt.ItemIsUserCheckable  # type: ignore
    QItemIsEnabled = Qt.ItemIsEnabled  # type: ignore
    QtKeys = Qt  # type: ignore
    QEventTypes = QEvent.Type  # type: ignore
    QDisplayRole = Qt.DisplayRole  # type: ignore


class CustomCheckboxListView(ComboboxPlaceholderListView):
    def mousePressEvent(self, event):
        # Allow toggling the check state by clicking the label
        # Without this only clicking the checkbox would toggle the check state
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                model = cast(QStandardItemModel, self.model())
                item = model.itemFromIndex(index)
                if item is None:
                    return
                if item.flags() & QItemIsUserCheckable:
                    if item.checkState() == Qt.CheckState.Checked:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        item.setCheckState(Qt.CheckState.Checked)
                return
        # Calling the default mousePressEvent would make it so that the check state
        # is toggled while pressing and reset on releasing the mouse button
        # super().mousePressEvent(event)

    def keyPressEvent(self, event):
        model = cast(QStandardItemModel, self.model())
        # Selecting an item
        if event.key() in (QtKeys.Key_Space, QtKeys.Key_Return, QtKeys.Key_Enter):
            index = self.currentIndex()
            if index.isValid():
                item = model.itemFromIndex(index)
                if item is None:
                    return
                if item.checkState() == Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setCheckState(Qt.CheckState.Checked)
        # Always call the default keyPressEvent to allow navigation
        # and for ComboboxPlaceholderListView to handle keeping the popup open
        super().keyPressEvent(event)


class MultiComboBox(RequiredCombobox):
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
        model = cast(QStandardItemModel, self.model())
        model.dataChanged.connect(self.updateText)

    def make_item_from_text(self, text: str, data=None):
        item = QStandardItem()
        item.setText(text)
        item.setFlags(QItemIsEnabled | QItemIsUserCheckable)
        item.setData(QCheckState.Unchecked, QCheckStateRole)
        if data:
            item.setData(data)
        return item

    def addItem(self, text: str, userData=None):  # type: ignore[override]
        item = self.make_item_from_text(text, userData)
        # Use the PlaceHolderCombobox method to add the item,
        # so it can manage the placeholder text
        super().addItem(item)

    def addItems(self, items_list: Iterable[str]):  # type: ignore[override]
        items = [self.make_item_from_text(item) for item in items_list]
        super().addItems(items)

    def updateText(self):
        model = cast(QStandardItemModel, self.model())
        line_edit = self.lineEdit()
        if line_edit is None:
            return
        selected_item_texts: list[str] = []
        for i in range(model.rowCount()):
            item = cast(QStandardItem, model.item(i))
            if item is None:
                continue
            if item.checkState() == QCheckState.Checked:
                selected_item_texts.append(item.text())
        line_edit.setText(", ".join(selected_item_texts))

    def showPopup(self):
        super().showPopup()
        model = cast(QStandardItemModel, self.model())
        combo_box_view = cast(CustomCheckboxListView, self.view())
        if combo_box_view is None:
            return
        # Set the state of each item in the dropdown
        for i in range(model.rowCount()):
            item = cast(QStandardItem, model.item(i))
            if not item:
                continue
            combo_box_view.setRowHidden(i, False)
            check_box = cast(QCheckBox, combo_box_view.indexWidget(item.index()))
            if check_box:
                check_box.setChecked(item.checkState() == QCheckState.Checked)

    def hidePopup(self):
        model = cast(QStandardItemModel, self.model())
        combo_box_view = self.view()
        if combo_box_view is None:
            return
        # Update the check state of each item based on the checkbox state
        for i in range(model.rowCount()):
            item = cast(QStandardItem, model.item(i))
            if not item:
                continue

            check_box = cast(QCheckBox, combo_box_view.indexWidget(item.index()))
            if check_box:
                item.setCheckState(
                    QCheckState.Checked if check_box.isChecked() else QCheckState.Unchecked
                )
        super().hidePopup()

    def setCurrentText(self, selected_text: Optional[str]):
        model = cast(QStandardItemModel, self.model())
        if model is None:
            return
        if selected_text is None:
            selected_text = ""
        for text in selected_text.split(", "):
            for i in range(model.rowCount()):
                item = model.item(i)
                if item is not None and item.text() == text:
                    item.setCheckState(QCheckState.Checked)
                    break
        self.updateText()

    def currentData(self, role: int = QDisplayRole):
        model = cast(QStandardItemModel, self.model())
        # Return the list of selected items data
        res = []
        for i in range(model.rowCount()):
            item = model.item(i)
            if item is not None and item.checkState() == QCheckState.Checked:
                res.append(item.text())
        return res

    def addSelectedItem(self, text: str):
        model = cast(QStandardItemModel, self.model())
        if model is None:
            return
        for i in range(model.rowCount()):
            item = model.item(i)
            if item is not None and item.text() == text:
                item.setCheckState(QCheckState.Checked)
                break

    def hasMultipleSelected(self):
        return len(self.currentData()) > 1
