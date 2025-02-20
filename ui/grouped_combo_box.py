from typing import cast
from aqt.qt import (
    QStyledItemDelegate,
    QStandardItemModel,
    QStandardItem,
    QFont,
    Qt,
    qtmajor,
)

from .required_combobox import RequiredCombobox

if qtmajor > 5:
    QAlignCenter = Qt.AlignmentFlag.AlignCenter
    # QTextAlignmentRole = Qt.ItemDataRole.TextAlignmentRole
    # QUserRole = Qt.ItemDataRole.UserRole
    QtKeys = Qt.Key
    QBold = QFont.Weight.Bold
else:
    QAlignCenter = Qt.AlignCenter  # type: ignore
    # QTextAlignmentRole = Qt.TextAlignmentRole # type: ignore
    # QUserRole = Qt.UserRole # type: ignore
    QtKeys = Qt  # type: ignore
    QBold = QFont.Bold  # type: ignore


class CenteredItemDelegate(QStyledItemDelegate):
    # Adding this ItemDelegate that seems to do nothing but it's needed
    # for the AlignCenter to work on the group items
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)


class GroupedComboBox(RequiredCombobox):
    """
    Custom QComboBox that allows for grouping of items.
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, auto_size=True, **kwargs)
        self.groups = {}
        self.max_width = 0
        self.setModel(QStandardItemModel(self))
        self.setItemDelegate(CenteredItemDelegate(self))  # Set the custom item delegate

    def addGroup(self, group_name):
        item = QStandardItem()
        item.setEnabled(False)
        item.setText(group_name)
        item.setFont(QFont(item.font().family(), item.font().pointSize(), QBold))
        item.setTextAlignment(QAlignCenter)
        self.groups[group_name] = []
        super().addItem(item)

    def addItemToGroup(self, group_name, item_name):
        item_name = item_name.strip()
        if group_name in self.groups:
            self.groups[group_name].append(item_name)
            self.addItem(item_name)

    def setCurrentText(self, text):
        if not text:
            return
        # Override to handle setting text with consideration for item formatting
        model = cast(QStandardItemModel, self.model())
        for i in range(self.count()):
            item = model.item(i)
            if item and item.text().strip() == text.strip():
                self.setCurrentIndex(i)
                super().setCurrentText(text.strip())
                break
        else:
            # If no matching item is found, optionally log a warning or handle as needed
            print(f"Warning: No matching item for text '{text}'")

    def currentText(self):
        # Override to handle getting text with consideration for item formatting
        return super().currentText().strip()
