from typing import Union

# noinspection PyUnresolvedReferences
from aqt.qt import (
    QComboBox,
    QStyledItemDelegate,
    QListView,
    QStandardItemModel,
    QStandardItem,
    QFont,
    Qt,
    qtmajor,
)

from .placeholder_combobox import PlaceHolderCombobox

if qtmajor > 5:
    QAlignCenter = Qt.AlignmentFlag.AlignCenter
    # QTextAlignmentRole = Qt.ItemDataRole.TextAlignmentRole
    # QUserRole = Qt.ItemDataRole.UserRole
    QtKeys = Qt.Key
    QBold = QFont.Weight.Bold
else:
    QAlignCenter = Qt.AlignCenter
    # QTextAlignmentRole = Qt.TextAlignmentRole
    # QUserRole = Qt.UserRole
    QtKeys = Qt
    QBold = QFont.Bold


class CenteredItemDelegate(QStyledItemDelegate):
    # Adding this ItemDelegate that seems to do nothing but it's needed
    # for the AlignCenter to work on the group items
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)


class GroupedComboBox(PlaceHolderCombobox):
    """
    Custom QComboBox that allows for grouping of items.
    """

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.groups = {}
        self.max_width = 0
        self.setModel(QStandardItemModel(self))
        self.setItemDelegate(CenteredItemDelegate(self))  # Set the custom item delegate

    def showPopup(self):
        self.setPopupAndBoxWidth()
        super().showPopup()

    def updateMaxWidth(self, width: int):
        if width > self.max_width:
            self.max_width = width
            self.setPopupAndBoxWidth()

    def setPopupAndBoxWidth(self):
        self.setMaximumWidth(self.max_width + 40)  # Add some padding

    def clear(self):
        self.max_width = 0
        super().clear()

    def addItem(self, item: Union[str, QStandardItem]):
        if isinstance(item, str):
            text = item
            item = QStandardItem(item)
            item.setText(text)
        else:
            text = item.text()
        self.model().appendRow(item)
        item_width = self.view().fontMetrics().boundingRect(text).width()
        self.updateMaxWidth(item_width)

    def addGroup(self, group_name):
        item = QStandardItem()
        item.setEnabled(False)
        item.setText(group_name)
        item.setFont(QFont(item.font().family(), item.font().pointSize(), QBold))
        item.setTextAlignment(QAlignCenter)
        self.groups[group_name] = []
        self.addItem(item)
        item_width = self.view().fontMetrics().boundingRect(group_name).width()
        self.updateMaxWidth(item_width)

    def addItemToGroup(self, group_name, item_name):
        item_name = item_name.strip()
        if group_name in self.groups:
            self.groups[group_name].append(item_name)
            self.addItem(item_name)

    def setCurrentText(self, text):
        # Override to handle setting text with consideration for item formatting
        for i in range(self.count()):
            if self.model().item(i).text().strip() == text.strip():
                self.setCurrentIndex(i)
                super().setCurrentText(text.strip())
                break
        else:
            # If no matching item is found, optionally log a warning or handle as needed
            print(f"Warning: No matching item for text '{text}'")

    def currentText(self):
        # Override to handle getting text with consideration for item formatting
        return super().currentText().strip()
