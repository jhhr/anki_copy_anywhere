# noinspection PyUnresolvedReferences
from aqt.qt import (
    QComboBox,
    QStyledItemDelegate,
    Qt,
    qtmajor,
)

if qtmajor > 5:
    QAlignCenter = Qt.AlignmentFlag.AlignCenter
    QTextAlignmentRole = Qt.ItemDataRole.TextAlignmentRole
    QUserRole = Qt.ItemDataRole.UserRole
else:
    QAlignCenter = Qt.AlignCenter
    QTextAlignmentRole = Qt.TextAlignmentRole
    QUserRole = Qt.UserRole


class GroupedItemDelegate(QStyledItemDelegate):
    """
    Custom item delegate for QComboBox for styling group items differently.
    """

    def paint(self, painter, option, index):
        if index.data(Qt.ItemDataRole.UserRole + 1):  # Group
            option.font.setBold(True)
        else:  # Item
            option.font.setBold(False)
        QStyledItemDelegate.paint(self, painter, option, index)


class GroupedComboBox(QComboBox):
    """
    Custom QComboBox that allows for grouping of items.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.groups = {}

        self.setItemDelegate(GroupedItemDelegate(self))

    def addGroup(self, group_name):
        self.groups[group_name] = []
        self.items.append(group_name)
        self.addItem(group_name)
        index = self.findText(group_name)
        model = self.model()
        model.setData(model.index(index, 0), QAlignCenter, QTextAlignmentRole)
        model.setData(model.index(index, 0), True, QUserRole + 1)  # Mark as group

    def addItemToGroup(self, group_name, item_name):
        item_name = item_name.strip()
        if group_name in self.groups:
            self.groups[group_name].append(item_name)
            self.items.append("  " + item_name)
            self.addItem("  " + item_name)
            index = self.findText("  " + item_name)
            self.model().setData(self.model().index(index, 0), False, Qt.ItemDataRole.UserRole + 1)  # Mark as item

    def setCurrentText(self, text):
        # Override to handle setting text with consideration for item formatting
        for i in range(self.count()):
            if self.itemText(i).strip() == text.strip():
                self.setCurrentIndex(i)
                break
        else:
            # If no matching item is found, optionally log a warning or handle as needed
            print(f"Warning: No matching item for text '{text}'")
