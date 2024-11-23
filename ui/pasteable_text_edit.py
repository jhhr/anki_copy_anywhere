from functools import partial
from typing import Union

# noinspection PyUnresolvedReferences
from aqt.qt import (
    QTextEdit,
    QMenu,
    QContextMenuEvent,
    QAction,
)

from .auto_resizing_text_edit import AutoResizingTextEdit


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


class PasteableTextEdit(AutoResizingTextEdit):
    """
    Custom QTextEdit that allows for pasting predefined text options
    selected from a right-click context menu.
    """

    def __init__(
            self,
            parent=None,
            options_dict: dict = None,
            height: int = None,
            placeholder_text: str = None,
    ):
        super().__init__(parent)
        # Define predefined options and their associated text
        self.options_dict = options_dict
        # Set the size of the text edit
        if height is not None:
            self.setFixedHeight(height)
        # Set placeholder text if provided
        if placeholder_text:
            self.setPlaceholderText(placeholder_text)

    def contextMenuEvent(self, event: QContextMenuEvent):
        if not self.options_dict:
            return

        context_menu = QMenu(parent=self)

        def add_option_to_menu(menu: QMenu, option_name: str, option_text: str):
            """
            Add the final option to the context menu that will perform the
            text insertion when clicked.
            :param menu: Menu or submenu to add the option to
            :param option_name: Text to display in the menu
            :param option_text: Text to insert into the QTextEdit
            :return:
            """
            callback = partial(self.insert_text_at_cursor, option_text)
            action = QAction(option_name, self)
            action.triggered.connect(callback)
            menu.addAction(action)

        def add_list_to_menu(menu: QMenu, option_list: list[str]):
            """
            Add a list of options to the context menu.
            Lists are assumed to contain only strings, not further dicts.
            :param menu: Menu or submenu to add the options to
            :param option_list: List of options to add
            :return:
            """
            for option in option_list:
                add_option_to_menu(menu, option, option)

        def populate_menu(menu: QMenu, options: Union[list, dict, str], ):
            """
            Recursively add options to the context menu to
            allow arbitrary nesting of options and submenus.
            :param menu: QMenu to add options to
            :param options: dict of options to add, possibly containing sub-dicts
            :return: None
            """
            if isinstance(options, dict):
                for key, value in options.items():
                    if isinstance(value, dict):
                        sub_menu = QMenu(key, parent=self)
                        menu.addMenu(sub_menu)
                        # If value is a dict, will recursively add sub-menu
                        # Else, option(s) will be added to the sub-menu
                        populate_menu(sub_menu, value)
                    elif isinstance(value, list):
                        add_list_to_menu(menu, value)
                    else:
                        add_option_to_menu(menu, key, value)
            elif isinstance(options, list):
                add_list_to_menu(menu, options)
            else:
                add_option_to_menu(menu, options, options)

        populate_menu(context_menu, self.options_dict)

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
        return self.options_dict[group_name]

    def add_option_to_group(self, group_name: str, option_name: str, option_text: str, target_level: dict = None):
        current_level = (self.options_dict if target_level is None else target_level)
        if group_name not in current_level:
            current_level[group_name] = {}
        current_level[group_name][option_name] = option_text
