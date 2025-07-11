from typing import Optional, Union, Sequence
import uuid
import copy as copy_module
from anki.notes import NoteId
from aqt import mw

from aqt.qt import (
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    QWidget,
    Qt,
    qtmajor,
)

from .edit_copy_definition_dialog import EditCopyDefinitionDialog
from .scrollable_dialog import ScrollableQDialog
from ..configuration import (
    Config,
    CopyDefinition,
)
from ..logic.copy_fields import (
    copy_fields,
)
from ..utils.make_query_string import make_query_string

if qtmajor > 5:
    WindowModal = Qt.WindowModality.WindowModal
else:
    WindowModal = Qt.WindowModal  # type: ignore

DEFAULT_CARDS_SELECTED_LABEL = "Select some copy definitions to show what notes would apply."


class PickCopyDefinitionDialog(ScrollableQDialog):
    """
    Class for the dialog box to choose which copy definition to apply now, edit or remove.
    Includes a button start the edit dialog for a new copy definition.
    """

    def __init__(
        self,
        parent,
        copy_definitions: list[CopyDefinition],
        browser_note_ids: Optional[list[int]],
        browser_search: Optional[str],
    ):
        super().__init__(parent)

        self.copy_definitions = copy_definitions
        self.selected_definitions_applicable_notes: set[int] = set()
        self.selected_copy_definitions: list[CopyDefinition] = []
        self.applicable_note_type_names: list[str] = []
        self.checkboxes: list[QCheckBox] = []
        self.definition_note_ids: list[Sequence[Union[int, NoteId]]] = []
        self.browser_note_ids = browser_note_ids
        self.browser_search = browser_search

        # GUID-based definition UI tracking
        self.definition_ui_components: dict[str, dict] = (
            {}
        )  # Maps definition GUID to its UI components

        # Ensure all definitions have GUIDs
        for definition in self.copy_definitions:
            if "guid" not in definition:
                definition["guid"] = str(uuid.uuid4())

        # Build textbox
        self.setWindowModality(WindowModal)

        # ScrollableQDialog already creates the main layout, we need to set up the inner content
        self.vbox = QVBoxLayout(self.inner_widget)

        self.use_browser_selection_button = QPushButton(
            f"Use selected notes ({len(browser_note_ids or [])})"
        )
        self.use_browser_selection_button.clicked.connect(
            lambda: self.toggle_card_selected_button(self.use_browser_selection_button)
        )
        self.use_all_cards_button = QPushButton("Use all notes from current search")
        self.use_all_cards_button.clicked.connect(
            lambda: self.toggle_card_selected_button(self.use_all_cards_button)
        )
        self.vbox.addWidget(self.use_browser_selection_button)
        self.vbox.addWidget(self.use_all_cards_button)

        self.notes_selected_label = QLabel(DEFAULT_CARDS_SELECTED_LABEL)
        self.vbox.addWidget(self.notes_selected_label)
        self.toggle_card_selected_button(self.use_browser_selection_button)

        self.select_label = QLabel("Select copy definitions to apply")
        self.top_grid = self.make_grid()
        self.top_grid.addWidget(self.select_label, 1, 0, 1, 1)
        self.add_new_button = QPushButton("+ Add new definition")
        self.add_new_button.clicked.connect(lambda: self.edit_definition(None))
        self.top_grid.addWidget(self.add_new_button, 1, 3, 1, 1)

        # Create definitions container with vertical layout instead of grid
        definitions_container_widget = QWidget()
        self.definitions_layout = QVBoxLayout(definitions_container_widget)
        self.definitions_layout.setContentsMargins(0, 0, 0, 0)
        self.vbox.addWidget(definitions_container_widget)

        self.add_all_definition_rows()

        # Create footer layout for bottom buttons
        footer_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply")
        self.apply_button.setEnabled(False)
        self.close_button = QPushButton("Close")

        self.apply_button.clicked.connect(self.accept)
        self.close_button.clicked.connect(self.reject)

        footer_layout.addWidget(self.apply_button)
        footer_layout.addStretch()
        footer_layout.addWidget(self.close_button)

        # Add footer to the main layout (this will be outside the scroll area)
        self.main_layout.addLayout(footer_layout)

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
        # Ensure definition has GUID
        if "guid" not in definition:
            definition["guid"] = str(uuid.uuid4())

        definition_guid = definition["guid"]

        # Create a widget to contain this definition row
        definition_widget = QWidget()
        definition_layout = QHBoxLayout(definition_widget)
        definition_layout.setContentsMargins(5, 0, 5, 0)

        # Checkbox with definition name
        checkbox = QCheckBox(definition["definition_name"])
        definition_layout.addWidget(checkbox)
        self.checkboxes.append(checkbox)
        self.definition_note_ids.append([])
        checkbox.stateChanged.connect(self.update_card_counts_for_all_cards)

        # Add stretch to push buttons to the right
        definition_layout.addStretch()

        # Edit button
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda: self.edit_definition_by_guid(definition_guid))
        definition_layout.addWidget(edit_button)

        # Duplicate button
        duplicate_button = QPushButton("Duplicate")
        duplicate_button.clicked.connect(lambda: self.duplicate_definition_by_guid(definition_guid))
        definition_layout.addWidget(duplicate_button)

        # Remove button
        remove_button = QPushButton("Delete")

        def remove_row_ui():
            # Remove the entire definition widget from the layout
            self.definitions_layout.removeWidget(definition_widget)
            definition_widget.deleteLater()

            # Remove from checkboxes list
            if checkbox in self.checkboxes:
                checkbox_index = self.checkboxes.index(checkbox)
                self.checkboxes.remove(checkbox)
                if checkbox_index < len(self.definition_note_ids):
                    self.definition_note_ids.pop(checkbox_index)

        # Store UI components for this definition GUID
        self.definition_ui_components[definition_guid] = {
            "widget": definition_widget,
            "checkbox": checkbox,
            "edit_button": edit_button,
            "duplicate_button": duplicate_button,
            "remove_button": remove_button,
            "remove_ui_func": remove_row_ui,
            "index": index,
        }

        def remove_row():
            # Use targeted removal without needing to rebuild entire UI
            self.remove_definition_by_guid(definition_guid)

        remove_button.clicked.connect(remove_row)
        definition_layout.addWidget(remove_button)

        # Add the definition widget to the definitions layout
        self.definitions_layout.addWidget(definition_widget)

    def remove_definition_by_guid(self, definition_guid: str):
        """Remove a specific definition and its UI components by GUID without rebuilding the entire UI."""
        # Find and remove the definition from the list
        definition_to_remove = None
        for i, definition in enumerate(self.copy_definitions):
            if definition.get("guid") == definition_guid:
                definition_to_remove = definition
                self.copy_definitions.pop(i)
                break

        if definition_to_remove is None:
            return

        # Remove from configuration
        config = Config()
        config.load()
        try:
            # Find the definition in config by GUID and remove it
            for i, config_def in enumerate(config.copy_definitions):
                if config_def.get("guid") == definition_guid:
                    config.remove_definition_by_index(i)
                    break
        except (IndexError, KeyError):
            # Sometimes when removing things quickly an error can occur
            pass

        # Remove UI components
        if definition_guid in self.definition_ui_components:
            ui_components = self.definition_ui_components[definition_guid]
            ui_components["remove_ui_func"]()

            # Remove from tracking
            del self.definition_ui_components[definition_guid]

        # Update card counts
        self.update_card_counts_for_all_cards()

    def duplicate_definition_by_guid(self, definition_guid: str):
        """Duplicate a specific definition by GUID."""
        # Find the definition to duplicate
        definition_to_duplicate = None
        for definition in self.copy_definitions:
            if definition.get("guid") == definition_guid:
                definition_to_duplicate = definition
                break

        if definition_to_duplicate is None:
            return

        # Create a copy and assign new GUID
        config = Config()
        config.load()
        copy_definition = copy_module.deepcopy(definition_to_duplicate)
        copy_definition["definition_name"] += " (copy)"
        copy_definition["guid"] = str(uuid.uuid4())

        config.add_definition(copy_definition)

        # Add to local list and UI
        self.copy_definitions.append(copy_definition)
        self.add_definition_row(len(self.copy_definitions) - 1, copy_definition)

        # Reload config to stay in sync
        config.load()
        self.copy_definitions = config.copy_definitions

    def edit_definition_by_guid(self, definition_guid: str):
        """Edit a specific definition by GUID."""
        # Find the definition to edit
        definition_to_edit = None
        definition_index = None
        for i, definition in enumerate(self.copy_definitions):
            if definition.get("guid") == definition_guid:
                definition_to_edit = definition
                definition_index = i
                break

        if definition_to_edit is None:
            return

        return self.edit_definition(definition_index, definition_to_edit)

    def edit_definition(
        self, index: Optional[int] = None, copy_definition: Optional[CopyDefinition] = None
    ):
        """
        Opens the edit dialog for the selected copy definition
        """
        config = Config()
        config.load()
        if copy_definition is not None:
            definition = copy_definition
        elif index is None:
            definition = None
        else:
            definition = self.copy_definitions[index]

        dialog = EditCopyDefinitionDialog(self, definition)

        if dialog.exec():
            copy_definition = dialog.get_copy_definition()
            if index is None and copy_definition is not None:
                # Adding new definition
                if "guid" not in copy_definition:
                    copy_definition["guid"] = str(uuid.uuid4())
                config.add_definition(copy_definition)

                # Add to local list and UI
                self.copy_definitions.append(copy_definition)
                self.add_definition_row(len(self.copy_definitions) - 1, copy_definition)

            elif index is not None and copy_definition is not None:
                # Updating existing definition
                old_definition = self.copy_definitions[index]
                old_guid = old_definition.get("guid")

                # Preserve GUID if it exists
                if old_guid:
                    copy_definition["guid"] = old_guid
                elif "guid" not in copy_definition:
                    copy_definition["guid"] = str(uuid.uuid4())

                config.update_definition_by_index(index, copy_definition)

                # Update local list
                self.copy_definitions[index] = copy_definition

                # Update UI component text if GUID exists in tracking
                if old_guid and old_guid in self.definition_ui_components:
                    ui_components = self.definition_ui_components[old_guid]
                    checkbox = ui_components["checkbox"]
                    checkbox.setText(copy_definition["definition_name"])

            # Always reload configuration to ensure we have the latest definitions
            config.load()
            self.copy_definitions = config.copy_definitions

            # Update card counts without rebuilding UI
            self.update_card_counts_for_all_cards()
            return 0
        else:
            # "Cancel" was pressed
            return -1

    def toggle_card_selected_button(self, selected_button):
        # reset styles
        self.use_browser_selection_button.setStyleSheet("")
        self.use_all_cards_button.setStyleSheet("")
        style = "background-color: #e0e0e0; color: black;"
        if selected_button == self.use_browser_selection_button:
            self.use_browser_selection = True
            self.use_browser_selection_button.setStyleSheet(style)
        else:
            self.use_browser_selection = False
            self.use_all_cards_button.setStyleSheet(style)
        self.update_card_counts_for_all_cards()

    def update_card_counts_for_all_cards(self):
        """
        Sets the cards that would be applicable for the selected copy definitions
        """
        browser_query = ""
        if self.use_browser_selection and self.browser_note_ids:
            browser_query = f"nid:{','.join(map(str, self.browser_note_ids))}"
        elif self.browser_search:
            browser_query = self.browser_search

        self.selected_definitions_applicable_notes = set()
        total_applicable_notes: list[Union[int, NoteId]] = []
        self.applicable_note_type_names = []
        nothing_checked = True
        for index, checkbox in enumerate(self.checkboxes):
            if checkbox.isChecked():
                nothing_checked = False
                checked_definition = self.copy_definitions[index]
                decks_query = ""
                whitelist_decknames = checked_definition.get("only_copy_into_decks")
                if whitelist_decknames and whitelist_decknames != "-":
                    # Remove the quotes and split the string into a list of deck names
                    deck_names = whitelist_decknames.strip('""').split('", "')
                    decks_query = make_query_string("deck", deck_names)

                note_type_query = ""
                # Split by comma and remove the first wrapping " but keeping the last one
                note_type_names = checked_definition.get("copy_into_note_types")
                if note_type_names and note_type_names != "-":
                    note_type_names_list = note_type_names.strip('""').split('", "')
                    note_type_query = make_query_string("note", note_type_names_list)
                def_note_ids = mw.col.find_notes(f"{note_type_query} {decks_query} {browser_query}")

                self.selected_definitions_applicable_notes.update(def_note_ids)
                self.definition_note_ids[index] = def_note_ids
                total_applicable_notes.extend(def_note_ids)
                definition_name = checked_definition.get("definition_name", "")
                checkbox.setText(f"{definition_name} ({len(def_note_ids)})")
                for note_type_name in note_type_names_list:
                    if note_type_name not in self.applicable_note_type_names:
                        self.applicable_note_type_names.append(note_type_name)
            else:
                self.definition_note_ids[index] = []
        if nothing_checked:
            self.notes_selected_label.setText(DEFAULT_CARDS_SELECTED_LABEL)
        elif len(self.selected_definitions_applicable_notes) > 0:
            self.notes_selected_label.setText(
                f"{len(self.selected_definitions_applicable_notes)} notes apply over"
                f" {len(self.applicable_note_type_names)} different note types."
                f"<br>Total copy operations to be done: {len(total_applicable_notes)}."
                "Click apply to run the selected copy definitions on these notes."
            )
            self.apply_button.setEnabled(True)
        else:
            self.notes_selected_label.setText(
                "No notes applicable for the selected copy definitions."
            )
            self.apply_button.setEnabled(False)


def show_copy_dialog(browser):
    """
    Shows a dialog for the user to select a copy definition to apply, edit or remove.
    """
    current_search = None
    if browser:
        note_ids = browser.selected_notes()
        current_search = browser.current_search()

    # Put the saved configuration to show in the dialog box
    config = Config()
    config.load()
    copy_definitions = config.copy_definitions

    parent = mw.app.activeWindow()
    d = PickCopyDefinitionDialog(parent, copy_definitions, note_ids, current_search)
    if d.exec():
        # Run all selected copy definitions according to the checkboxes
        config.load()
        copy_definitions = config.copy_definitions
        checked_copy_definitions = []
        checked_copy_definition_note_ids = []
        for index, checkbox in enumerate(d.checkboxes):
            # The UI indicates that there are zero notes to copy, so we skip
            # If we passed that to the copy_fields function, it would actually
            # perform the copy operation on all notes in the collection as an empty list is falsy
            if checkbox.isChecked() and len(d.definition_note_ids[index]) > 0:
                checked_copy_definitions.append(copy_definitions[index])
                checked_copy_definition_note_ids.append(d.definition_note_ids[index])

        # Run the copy definitions
        copy_fields(
            copy_definitions=checked_copy_definitions,
            note_ids_per_definition=checked_copy_definition_note_ids,
            parent=browser,
        )
