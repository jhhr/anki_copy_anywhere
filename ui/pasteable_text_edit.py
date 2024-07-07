from functools import partial

# noinspection PyUnresolvedReferences
from aqt.qt import (
    QTextEdit,
    QMenu,
    QContextMenuEvent,
    QAction,
)


class GroupedQMenu(QMenu):
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.groups = {}

    def add_group(self, group_name):
        """Add a new group to the menu."""
        if group_name not in self.groups:
            self.groups[group_name] = []

    def add_item_to_group(self, group_name, item_name, callback):
        """Add an item to a specific group."""
        if group_name not in self.groups:
            self.add_group(group_name)
        action = QAction(item_name, self)
        action.triggered.connect(callback)
        self.groups[group_name].append(action)

    def showEvent(self, event):
        """Override showEvent to organize and display groups and items."""
        self.clear()  # Clear existing actions to reorganize
        for group_name, actions in self.groups.items():
            self.addSection(group_name)
            for action in actions:
                self.addAction(action)
        super().showEvent(event)


class PasteableTextEdit(QTextEdit):
    """
    Custom QTextEdit that allows for pasting predefined text options
    selected from a right-click context menu.
    """

    def __init__(self, parent=None, options_dict: dict = None, height: int = None):
        super().__init__(parent)
        # Define predefined options and their associated text
        self.options_dict = options_dict
        # Set the size of the text edit
        if height is not None:
            self.setFixedHeight(height)

    def contextMenuEvent(self, event: QContextMenuEvent):
        if not self.options_dict:
            return

        context_menu = QMenu(parent=self)

        options_list = self.options_dict.items()

        def add_option_to_menu(menu, option, text):
            # Create a partial function to pass the text to
            callback = partial(self.insert_text_at_cursor, text)
            action = QAction(option, self)
            action.triggered.connect(callback)
            menu.addAction(action)

        # Make a two level menu with the first level being the group name
        for group_name, options in options_list:
            group_menu = QMenu(group_name, parent=self)
            context_menu.addMenu(group_menu)
            for option, text in options.items():
                add_option_to_menu(group_menu, option, text)

        # Show the context menu at the event position
        context_menu.exec(event.globalPos())

    def insert_text_at_cursor(self, text):
        # Get the current text cursor from the QTextEdit
        cursor = self.textCursor()
        # Insert text at the current cursor position
        cursor.insertText(text)
        # Set the modified cursor back to the QTextEdit
        self.setTextCursor(cursor)

    def set_options_dict(self, options_dict: dict):
        self.options_dict = options_dict

    def clear_options(self):
        self.options_dict = {}

    def add_option_group(self, group_name):
        if self.options_dict is None:
            self.options_dict = {}
        self.options_dict[group_name] = {}

    def add_option_to_group(self, group_name, option_name, option_text):
        if group_name not in self.options_dict:
            self.add_option_group(group_name)
        self.options_dict[group_name][option_name] = option_text
