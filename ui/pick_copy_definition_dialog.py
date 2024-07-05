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


class PickCopyDefinitionDialog(QDialog):
    """
    Class for the dialog box to choose which copy definition to apply now, edit or remove.
    Includes a button start the edit dialog for a new copy definition.
    """

    def __init__(self, parent, copy_definitions: [CopyDefinition], browser_card_ids):
        super().__init__(parent)

        self.copy_definitions = copy_definitions
        self.selected_definitions_applicable_cards = []
        self.selected_copy_definitions = []
        self.remove_row_funcs = []
        self.models = []
        self.checkboxes = []
        self.browser_card_ids = browser_card_ids

        # Build textbox
        self.setWindowModality(WindowModal)
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.cards_selected_label = QLabel("No cards applicable.")
        self.vbox.addWidget(self.cards_selected_label)

        self.update_card_counts_from_browser_card_ids()

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
        checkbox.stateChanged.connect(self.update_card_counts_for_all_cards)
        if self.browser_card_ids is not None and len(self.browser_card_ids):
            # Check if the definition would apply to the selected cards
            if definition["copy_into_note_type"] not in self.models:
                checkbox.setEnabled(False)

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
            for widget in [checkbox, edit_button, duplicate_button, remove_button]:
                widget.deleteLater()
                self.middle_grid.removeWidget(widget)

        self.remove_row_funcs.append(remove_row_ui)
        def remove_row():
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

    def update_card_counts_from_browser_card_ids(self):
        if self.browser_card_ids is not None and len(self.browser_card_ids):
            self.models = []
            self.selected_definitions_applicable_cards = []
            definition_note_types = [defn["copy_into_note_type"] for defn in self.copy_definitions]
            card_note_types = []
            for card_id in self.browser_card_ids:
                note = mw.col.get_card(card_id).note()
                note_type = note.note_type()["name"]
                if note_type not in card_note_types:
                    card_note_types.append(note.note_type())
                if note_type in definition_note_types:
                    self.selected_definitions_applicable_cards.append(card_id)
                    if note_type not in self.models:
                        self.models.append(note_type)
            self.cards_selected_label.setText(
                f"""{len(self.selected_definitions_applicable_cards)} cards selected. {len(self.models)} different note types.
            Copy definitions that would not apply are disabled.""")
            return True
        return False

    def update_card_counts_for_all_cards(self):
        """
        Sets the cards that would be applicable for the selected copy definitions
        """
        # If the function handling only the cards selected in the browser returns True, that means
        # we have those and shouldn't proceed with this
        if self.update_card_counts_from_browser_card_ids():
            return

        self.selected_definitions_applicable_cards = []
        self.models = []
        for index, checkbox in enumerate(self.checkboxes):
            if checkbox.isChecked():
                checked_definition = self.copy_definitions[index]
                limited_dids = []
                if checked_definition["only_copy_into_decks"]:
                    # Remove the quotes and split the string into a list of deck names
                    deck_names = checked_definition["only_copy_into_decks"].strip("\"\"''").split('", "')
                    for deck_name in deck_names:
                        did = mw.col.decks.id_for_name(deck_name)
                        if did is not None:
                            limited_dids.append(did)
                if len(limited_dids) > 0:
                    did_query = "(" + " OR ".join([f"did:{did}" for did in limited_dids]) + ")"
                else:
                    did_query = ""
                # Gotta wrap note in quotes, so it works with names containing spaces
                def_card_ids = mw.col.find_cards(f'"note:{checked_definition["copy_into_note_type"]}" {did_query}')
                self.selected_definitions_applicable_cards.extend(def_card_ids)
                if checked_definition["copy_into_note_type"] not in self.models:
                    self.models.append(checked_definition["copy_into_note_type"])
        if (len(self.selected_definitions_applicable_cards) > 0):
            self.cards_selected_label.setText(
                f"""{len(self.selected_definitions_applicable_cards)} cards applicable. {len(self.models)} different note types.
            Click apply to run the selected copy definitions on these cards.""")
        else:
            self.cards_selected_label.setText("No cards applicable.")

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
    if browser:
        card_ids = browser.selectedCards()

    # Put the saved configuration to show in the dialog box
    config = Config()
    config.load()
    copy_definitions = config.copy_definitions

    parent = mw.app.activeWindow()
    d = PickCopyDefinitionDialog(parent, copy_definitions, card_ids)
    if d.exec():
        # Run all selected copy definitions according to the checkboxes
        config.load()
        copy_definitions = config.copy_definitions
        for index, checkbox in enumerate(d.checkboxes):
            if checkbox.isChecked():
                # Run the copy definition
                copy_definition = copy_definitions[index]
                copy_fields(
                    copy_definition=copy_definition,
                    card_ids=card_ids,
                    parent=browser
                )
