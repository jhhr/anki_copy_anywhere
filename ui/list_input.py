from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QLineEdit,
    QHBoxLayout,
)


class ListInputWidget(QWidget):
    """
    Widget that allows for adding and removing items from a list.
    Adding an item can be done by typing in the input field and pressing the "Add Item(s)" button.
    Multiple items can be added at once by inputting a comma-separated list in the input field.
    Items can be removed one by one or all at once.
    """

    def __init__(self):
        super().__init__()

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.list_widget = QListWidget()
        self.main_layout.addWidget(self.list_widget)

        self.input_field = QLineEdit()
        self.main_layout.addWidget(self.input_field)

        self.button_layout = QHBoxLayout()
        self.main_layout.addLayout(self.button_layout)

        self.add_button = QPushButton("Add Item(s)")
        self.add_button.clicked.connect(self.add_item)
        self.button_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_item)
        self.button_layout.addWidget(self.remove_button)

        self.remove_all_button = QPushButton("Remove All")
        self.remove_all_button.clicked.connect(self.remove_all)
        self.button_layout.addWidget(self.remove_all_button)

    def add_item(self, text=None):
        # When pre-filling the list, add_item can be called with the text argument
        if text:
            item_text = text
        else:
            item_text = self.input_field.text()
        if item_text:
            # Handle possibly adding multiple items at once
            if len(item_text.split(",")) > 1:
                for item in item_text.split(","):
                    item = item.strip()
                    if not item:
                        # Skip empty items, if the input has a trailing comma or multiple commas
                        continue
                    # stripping whitespace is important
                    self.list_widget.addItem(item)
                self.input_field.clear()
            else:
                self.list_widget.addItem(item_text)
                self.input_field.clear()

    def remove_item(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.list_widget.takeItem(self.list_widget.row(item))

    def remove_all(self):
        self.list_widget.clear()

    def get_items(self):
        items = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item:
                items.append(item.text())
        return items
