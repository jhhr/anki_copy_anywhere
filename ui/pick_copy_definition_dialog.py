# noinspection PyUnresolvedReferences
from aqt import mw
# noinspection PyUnresolvedReferences
from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    Qt,
    qtmajor,
    QTimer,
)

from .edit_copy_definition_dialog import EditCopyDefinitionDialog
from ..configuration import (
    Config,
    CopyDefinition,
)
from ..logic.copy_fields import (
    copy_fields,
)

if qtmajor > 5:
    WindowModal = Qt.WindowModality.WindowModal
else:
    WindowModal = Qt.WindowModal

DEFAULT_CARDS_SELECTED_LABEL = "Select some copy definitions to show what cards would apply."


class PickCopyDefinitionDialog(QDialog):
    """
    Class for the dialog box to choose which copy definition to apply now, edit or remove.
    Includes a button start the edit dialog for a new copy definition.
    """

    def __init__(self, parent, copy_definitions: [CopyDefinition], browser_card_ids, browser_search):
        super().__init__(parent)

        self.copy_definitions = copy_definitions
        self.selected_definitions_applicable_cards = []
        self.selected_copy_definitions = []
        self.remove_row_funcs = []
        self.models = []
        self.checkboxes = []
        self.definition_card_ids = []
        self.browser_card_ids = browser_card_ids
        self.browser_search = browser_search

        # Build textbox
        self.setWindowModality(WindowModal)
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.use_selected_cards_button = QPushButton(f"Use selected cards ({len(browser_card_ids)})")
        self.use_selected_cards_button.clicked.connect(
            lambda: self.toggle_card_selected_button(self.use_selected_cards_button))
        self.use_all_cards_button = QPushButton("Use all cards from current search")
        self.use_all_cards_button.clicked.connect(lambda: self.toggle_card_selected_button(self.use_all_cards_button))
        self.vbox.addWidget(self.use_selected_cards_button)
        self.vbox.addWidget(self.use_all_cards_button)

        self.cards_selected_label = QLabel(DEFAULT_CARDS_SELECTED_LABEL)
        self.vbox.addWidget(self.cards_selected_label)
        self.toggle_card_selected_button(self.use_selected_cards_button)

        self.select_label = QLabel("Select copy definitions to apply")
        self.top_grid = self.make_grid()
        self.top_grid.addWidget(self.select_label, 1, 0, 1, 1)
        self.add_new_button = QPushButton("+ Add new definition")
        self.add_new_button.clicked.connect(lambda: self.edit_definition(None))
        self.top_grid.addWidget(self.add_new_button, 1, 3, 1, 1)

        self.middle_grid = self.make_grid()
        self.add_all_definition_rows()

        self.bottom_grid = self.make_grid()
        self.apply_button = QPushButton("Apply")
        self.apply_button.setEnabled(False)
        self.close_button = QPushButton("Close")

        self.apply_button.clicked.connect(self.accept)
        self.close_button.clicked.connect(self.reject)

        self.bottom_grid.addWidget(self.apply_button, 0, 0)
        self.bottom_grid.addWidget(self.close_button, 0, 4, 0, -1)

    def add_all_definition_rows(self):
        for index, definition in enumerate(self.copy_definitions):
            self.add_definition_row(index, definition)

    def make_grid(self):
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 25)
        grid.setColumnMinimumWidth(1, 200)
        grid.setColumnMinimumWidth(2, 50)
        grid.setColumnMinimumWidth(3, 50)
        grid.setColumnMinimumWidth(4, 50)
        self.vbox.addLayout(grid)
        return grid

    def add_definition_row(self, index, definition):
        # By setting the name into a box layout where we'll allow it expand
        # its empty space rightward also pushing the buttons there to the
        # edge
        hbox = QHBoxLayout()
        self.middle_grid.addLayout(hbox, index, 1)
        checkbox = QCheckBox(definition["definition_name"])
        hbox.addWidget(checkbox, index)
        self.checkboxes.append(checkbox)
        self.definition_card_ids.append([])
        checkbox.stateChanged.connect(self.update_card_counts_for_all_cards)

        hbox.addStretch(1)

        # Edit
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda: self.edit_definition(index))
        self.middle_grid.addWidget(edit_button, index, 2)

        # Duplicate
        duplicate_button = QPushButton("Duplicate")
        duplicate_button.clicked.connect(lambda: self.duplicate_definition(index))
        self.middle_grid.addWidget(duplicate_button, index, 3)

        # Remove
        remove_button = QPushButton("Delete")

        def remove_row_ui():
            self.checkboxes.remove(checkbox)
            self.definition_card_ids.pop(0)
            for widget in [checkbox, edit_button, duplicate_button, remove_button]:
                widget.deleteLater()
                self.middle_grid.removeWidget(widget)

        self.remove_row_funcs.append(remove_row_ui)

        def remove_row():
            # When removing a definition, we in fact remake the whole grid
            # Thus we remove all definition's UI, remove the one definition
            # and then add the remaining definitions back
            for func in self.remove_row_funcs:
                func()
            self.remove_row_funcs = []
            self.remove_definition(index)

        remove_button.clicked.connect(remove_row)
        self.middle_grid.addWidget(remove_button, index, 4)

    def remove_definition(self, index: int):
        """
        Removes the selected copy definition
        """
        config = Config()
        config.load()
        try:
            config.remove_definition_by_index(index)
        except IndexError:
            # Sometimes when removing things quickly a pop index out of range
            # error can occur. Things seem to work ok despite it, just
            # ignoring it for now.
            pass
        config.load()
        self.copy_definitions = config.copy_definitions
        self.add_all_definition_rows()
        self.update_card_counts_for_all_cards()

    def duplicate_definition(self, index: int):
        """
        Duplicates the selected copy definition
        """
        config = Config()
        config.load()
        copy_definition = config.copy_definitions[index]
        # Make a copy of the definition
        copy_definition = copy_definition.copy()
        copy_definition["definition_name"] += " (copy)"
        config.add_definition(copy_definition)
        self.add_definition_row(len(self.copy_definitions), copy_definition)
        config.load()
        self.copy_definitions = config.copy_definitions
        # Since we're creating an identical copy of an existing definition,
        # the applicable cards aren't changing this time

    def edit_definition(self, index: int = None, copy_definition: CopyDefinition = None):
        """
        Opens the edit dialog for the selected copy definition
        """
        config = Config()
        config.load()
        if copy_definition is not None:
            definition = copy_definition
        elif index is None:
            definition = {}
        else:
            definition = self.copy_definitions[index]

        dialog = EditCopyDefinitionDialog(self, definition)

        if dialog.exec():
            copy_definition = dialog.get_copy_definition()
            if index is None:
                config.add_definition(copy_definition)
                self.add_definition_row(len(self.copy_definitions), copy_definition)
            else:
                config.update_definition_by_index(index, copy_definition)
                for func in self.remove_row_funcs:
                    func()
                self.remove_row_funcs = []
            config.load()
            self.copy_definitions = config.copy_definitions
            self.add_all_definition_rows()
            self.update_card_counts_for_all_cards()
            return 0
        else:
            # "Cancel" was pressed
            return -1

    def toggle_card_selected_button(self, selected_button):
        # reset styles
        self.use_selected_cards_button.setStyleSheet("")
        self.use_all_cards_button.setStyleSheet("")
        style = "background-color: #e0e0e0; color: black;"
        if selected_button == self.use_selected_cards_button:
            self.use_selected_cards = True
            self.use_selected_cards_button.setStyleSheet(style)
        else:
            self.use_selected_cards = False
            self.use_all_cards_button.setStyleSheet(style)
        self.update_card_counts_for_all_cards()

    def update_card_counts_for_all_cards(self):
        """
        Sets the cards that would be applicable for the selected copy definitions
        """
        browser_query = ""
        if self.use_selected_cards and self.browser_card_ids is not None and len(self.browser_card_ids):
            card_ids = self.browser_card_ids
            browser_query = f"cid:{','.join(map(str, card_ids))}"
        elif self.browser_search:
            browser_query = self.browser_search

        self.selected_definitions_applicable_cards = set()
        total_applicable_cards = []
        self.models = []
        nothing_checked = True
        for index, checkbox in enumerate(self.checkboxes):
            if checkbox.isChecked():
                nothing_checked = False
                checked_definition = self.copy_definitions[index]
                limited_dids = []
                if checked_definition["only_copy_into_decks"]:
                    # Remove the quotes and split the string into a list of deck names
                    deck_names = checked_definition["only_copy_into_decks"].strip('""').split('", "')
                    for deck_name in deck_names:
                        did = mw.col.decks.id_for_name(deck_name)
                        if did is not None:
                            limited_dids.append(did)
                if len(limited_dids) > 0:
                    did_query = f'did:{",".join(map(str, limited_dids))}'
                else:
                    did_query = ""
                # Split by comma and remove the first wrapping " but keeping the last one
                note_type_names = checked_definition["copy_into_note_types"].strip('""').split('", "')
                # Note: adding "" between each so that we get "note:Some note type" OR "note:Some other note type"
                note_type_query = '" OR "note:'.join(note_type_names)
                # Final "" added here!
                note_type_query = f'("note:{note_type_query}")'
                def_card_ids = mw.col.find_cards(
                    f'{note_type_query} {did_query} {browser_query}')

                self.selected_definitions_applicable_cards.update(def_card_ids)
                self.definition_card_ids[index] = def_card_ids
                total_applicable_cards.extend(def_card_ids)
                checkbox.setText(f"{checked_definition['definition_name']} ({len(def_card_ids)})")
                if checked_definition["copy_into_note_types"] not in self.models:
                    self.models.append(checked_definition["copy_into_note_types"])
            else:
                self.definition_card_ids[index] = []
        if nothing_checked:
            self.cards_selected_label.setText(DEFAULT_CARDS_SELECTED_LABEL)
        elif len(self.selected_definitions_applicable_cards) > 0:
            self.cards_selected_label.setText(
                f"""{len(self.selected_definitions_applicable_cards)} cards apply over {len(self.models)} different note types.
            Total copy operations to be done: {len(total_applicable_cards)}.                
            Click apply to run the selected copy definitions on these cards.""")
            self.apply_button.setEnabled(True)
        else:
            self.cards_selected_label.setText("No cards applicable for the selected copy definitions.")
            self.apply_button.setEnabled(False)

    def get_selected_definition_index(self):
        """
        Returns the selected definition index
        """
        return self.copy_definition_cbox.currentIndex()

    def get_selected_definition_name(self):
        """
        Returns the selected definition name
        """
        return self.copy_definition_cbox.currentText()


def show_copy_dialog(browser):
    """
    Shows a dialog for the user to select a copy definition to apply, edit or remove.
    """
    card_ids = None
    current_search = None
    if browser:
        card_ids = browser.selectedCards()
        current_search = browser.current_search()

    # Put the saved configuration to show in the dialog box
    config = Config()
    config.load()
    copy_definitions = config.copy_definitions

    parent = mw.app.activeWindow()
    d = PickCopyDefinitionDialog(parent, copy_definitions, card_ids, current_search)
    if d.exec():
        # Run all selected copy definitions according to the checkboxes
        config.load()
        copy_definitions = config.copy_definitions
        checked_copy_definitions = []
        checked_copy_definition_card_ids = []
        for index, checkbox in enumerate(d.checkboxes):
            # The UI indicates that there are zero cards to copy, so we skip
            # If we passed that to the copy_fields function, it would actually
            # perform the copy operation on all cards in the collection as an empty list is falsy
            if checkbox.isChecked() and len(d.definition_card_ids[index]) > 0:
                checked_copy_definitions.append(copy_definitions[index])
                checked_copy_definition_card_ids.append(d.definition_card_ids[index])

        # Run the copy definitions
        copy_fields(
            copy_definitions=checked_copy_definitions,
            card_ids_per_definition=checked_copy_definition_card_ids,
            parent=browser,
        )
