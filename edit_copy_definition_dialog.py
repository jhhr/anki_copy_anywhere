from contextlib import suppress

from aqt import mw
from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QLabel,
    QDialog,
    QComboBox,
    QTabWidget,
    QSizePolicy,
    QScrollArea,
    QGuiApplication,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QGridLayout,
    QCheckBox,
    QIntValidator,
    QStyledItemDelegate,
    Qt,
    qtmajor,
)
from aqt.utils import showInfo

from .configuration import (
    Config,
    CopyDefinition,
    COPY_MODE_WITHIN_NOTE,
    COPY_MODE_ACROSS_NOTES,
)
from .copy_fields import SEARCH_FIELD_VALUE_PLACEHOLDER
from .edit_extra_processing_dialog import EditExtraProcessingWidget

if qtmajor > 5:
    from .multi_combo_box import MultiComboBoxQt6 as MultiComboBox

    WindowModal = Qt.WindowModality.WindowModal
    QFrameStyledPanel = QFrame.Shape.StyledPanel
    QFrameShadowRaised = QFrame.Shadow.Raised
    QSizePolicyFixed = QSizePolicy.Policy.Fixed
    QSizePolicyPreferred = QSizePolicy.Policy.Preferred
    QAlignTop = Qt.AlignmentFlag.AlignTop
else:
    from .multi_combo_box import MultiComboBoxQt5 as MultiComboBox

    WindowModal = Qt.WindowModal
    QFrameStyledPanel = QFrame.StyledPanel
    QFrameShadowRaised = QFrame.Raised
    QSizePolicyFixed = QSizePolicy.Fixed
    QSizePolicyPreferred = QSizePolicy.Preferred
    QAlignTop = Qt.AlignTop


class ScrollableQDialog(QDialog):
    def __init__(self, parent=None, footer_layout=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.scroll_area = QScrollArea(self)
        self.layout.addWidget(self.scroll_area)
        self.scroll_area.setWidgetResizable(True)

        self.inner_widget = QWidget()
        self.scroll_area.setWidget(self.inner_widget)

        # Get the screen size
        screen = QGuiApplication.primaryScreen().availableGeometry()

        # Set the initial size to a percentage of the screen size
        self.resize(screen.width() * 0.6, screen.height() * 0.95)

        # Add footer to the main layout
        if footer_layout:
            self.layout.addLayout(footer_layout)


class GroupedComboBox(QComboBox):
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
        model.setData(model.index(index, 0), Qt.AlignmentFlag.AlignCenter, Qt.ItemDataRole.TextAlignmentRole)
        model.setData(model.index(index, 0), True, Qt.ItemDataRole.UserRole + 1)  # Mark as group

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


class GroupedItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.data(Qt.ItemDataRole.UserRole + 1):  # Group
            option.font.setBold(True)
        else:  # Item
            option.font.setBold(False)
        QStyledItemDelegate.paint(self, painter, option, index)




class CopyFieldToFieldEditor(QWidget):
    """
    Class for editing the list of fields to copy from and fields to copy into.
    Shows the list of current field-to-field definitions. Add button for adding new definitions is at the bottom.
    Remove button for removing definitions is at the top-right of each definition.
    """

    def __init__(self, parent, copy_definition, copy_mode):
        super().__init__(parent)
        self.field_to_field_defs = copy_definition.get("field_to_field_defs", [])
        self.copy_mode = copy_mode

        self.copy_definition = copy_definition
        self.selected_copy_into_model_name = copy_definition.get("copy_into_note_type")

        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.middle_grid = QGridLayout()
        self.middle_grid.setColumnMinimumWidth(0, 400)
        self.middle_grid.setColumnMinimumWidth(1, 50)
        self.vbox.addLayout(self.middle_grid)

        self.bottom_form = QFormLayout()
        self.vbox.addLayout(self.bottom_form)

        self.add_new_button = QPushButton("Add another field-to-field definition")
        self.bottom_form.addRow("", self.add_new_button)
        self.add_new_button.clicked.connect(self.add_new_definition)

        self.copy_field_inputs = []

        # There has to be at least one definition so initialize with one
        if len(self.field_to_field_defs) == 0:
            self.add_new_definition()
        else:
            for index, copy_field_to_field_definition in enumerate(self.field_to_field_defs):
                self.add_copy_field_row(index, copy_field_to_field_definition)

    def add_new_definition(self):
        new_definition = {
            "copy_into_note_field": "",
            "copy_from_field": "",
            "copy_if_empty": False
        }
        self.field_to_field_defs.append(new_definition)
        self.add_copy_field_row(len(self.field_to_field_defs) - 1, new_definition)

    def add_copy_field_row(self, index, copy_field_to_field_definition):
        # Create a QFrame
        frame = QFrame(self)
        frame.setFrameShape(QFrameStyledPanel)
        frame.setFrameShadow(QFrameShadowRaised)

        # Create a layout for the frame
        frame_layout = QVBoxLayout(frame)

        # Add the frame to the main layout
        self.middle_grid.addWidget(frame, index, 0)
        row_form = QFormLayout()
        frame_layout.addLayout(row_form)

        copy_field_inputs_dict = {}

        # Copy into field
        field_target_cbox = QComboBox()
        copy_field_inputs_dict["copy_into_note_field"] = field_target_cbox
        row_form.addRow("Note field to copy into", field_target_cbox)
        self.update_field_target_options(field_target_cbox)
        with suppress(KeyError):
            field_target_cbox.setCurrentText(copy_field_to_field_definition["copy_into_note_field"])

        # Copy from field
        copy_from_field_cbox = GroupedComboBox()
        copy_field_inputs_dict["copy_from_field"] = copy_from_field_cbox
        row_form.addRow("What field to copy from", copy_from_field_cbox)
        self.update_copy_from_options(copy_from_field_cbox)
        with suppress(KeyError):
            copy_from_field_cbox.setCurrentText(copy_field_to_field_definition["copy_from_field"])

        copy_if_empty = QCheckBox("Only copy into field, if it's empty")
        copy_field_inputs_dict["copy_if_empty"] = copy_if_empty
        row_form.addRow("", copy_if_empty)
        with suppress(KeyError):
            copy_if_empty.setChecked(copy_field_to_field_definition["copy_if_empty"])

        process_chain_widget = EditExtraProcessingWidget(
            self,
            self.copy_definition,
            copy_field_to_field_definition,
        )
        copy_field_inputs_dict["process_chain"] = process_chain_widget
        row_form.addRow("Extra processing", process_chain_widget)

        # Remove
        remove_button = QPushButton("Delete")

        self.copy_field_inputs.append(copy_field_inputs_dict)

        def remove_row():
            for widget in [
                field_target_cbox,
                copy_from_field_cbox,
                copy_if_empty,
                remove_button,
                process_chain_widget,
            ]:
                widget.deleteLater()
                row_form.removeWidget(widget)
                widget = None
            self.middle_grid.removeWidget(frame)
            self.remove_definition(index)

        remove_button.clicked.connect(remove_row)
        row_form.addRow("", remove_button)

    def remove_definition(self, index):
        """
        Removes the selected field-to-field definition and input dict.
        """
        self.field_to_field_defs.pop(index)
        self.copy_field_inputs.pop(index)

    def get_field_to_field_defs(self):
        """
        Returns the list of field-to-field definitions from the current state of the editor.
        """
        field_to_field_defs = []
        for copy_field_inputs in self.copy_field_inputs:
            copy_field_definition = {
                "copy_into_note_field": copy_field_inputs["copy_into_note_field"].currentText(),
                "copy_from_field": copy_field_inputs["copy_from_field"].currentText().strip(),
                "copy_if_empty": copy_field_inputs["copy_if_empty"].isChecked(),
                "process_chain": copy_field_inputs["process_chain"].get_process_chain(),
            }
            field_to_field_defs.append(copy_field_definition)
        return field_to_field_defs

    def set_selected_copy_into_model(self, model_name):
        self.selected_copy_into_model_name = model_name
        for copy_field_inputs in self.copy_field_inputs:
            self.update_field_target_options(copy_field_inputs["copy_into_note_field"])
            if self.copy_mode == COPY_MODE_WITHIN_NOTE:
                self.update_copy_from_options(copy_field_inputs["copy_from_field"])

    def update_field_target_options(self, field_target_cbox):
        """
        Updates the options in the "Note field to copy into" dropdown box.
        """
        model = mw.col.models.by_name(self.selected_copy_into_model_name)
        if model is None:
            return

        previous_text = field_target_cbox.currentText()
        previous_text_in_new_options = False
        # Clear will unset the current selected text
        field_target_cbox.clear()
        field_target_cbox.addItem("-")
        for field_name in mw.col.models.field_names(model):
            if field_name == previous_text:
                previous_text_in_new_options = True
            field_target_cbox.addItem(field_name)

        # Reset the selected text, if the new options still include it
        if previous_text_in_new_options:
            field_target_cbox.setCurrentText(previous_text)

    def update_copy_from_options(self, copy_from_field_cbox):
        """
        Updates the options in the "What field to copy from" dropdown box.
        """
        previous_text = copy_from_field_cbox.currentText().strip()
        previous_text_in_new_options = False

        def add_model_option(model_name, model_id):
            nonlocal previous_text_in_new_options
            copy_from_field_cbox.addGroup(model_name)
            for field_name in mw.col.models.field_names(mw.col.models.get(model_id)):
                copy_from_field_cbox.addItemToGroup(model_name, field_name)
                if field_name == previous_text:
                    previous_text_in_new_options = True

        copy_from_field_cbox.clear()
        copy_from_field_cbox.addItem("-")

        if self.copy_mode == COPY_MODE_WITHIN_NOTE:
            # If we're in within note copy mode, only add the single model as the target
            model = mw.col.models.by_name(self.selected_copy_into_model_name)
            if model is None:
                return
            add_model_option(model["name"], model["id"])
        else:
            # Otherwise, add fields from all models
            models = mw.col.models.all_names_and_ids()
            for model in models:
                add_model_option(model.name, model.id)

        if previous_text_in_new_options:
            copy_from_field_cbox.setCurrentText(previous_text)


def set_size_policy_for_all_widgets(layout, h_policy, v_policy):
    for i in range(layout.count()):
        widget = layout.itemAt(i).widget()
        if widget:
            widget.setSizePolicy(h_policy, v_policy)
        else:
            # If it's not a widget, it might be another layout, so we recurse
            inner_layout = layout.itemAt(i).layout()
            if inner_layout:
                set_size_policy_for_all_widgets(inner_layout, h_policy, v_policy)


class FieldToFieldEditorVBox(QVBoxLayout):
    def __init__(self, parent, copy_definition, copy_mode):
        super().__init__(parent)
        self.addWidget(QLabel("Fields to copy from and to"))
        self.field_to_field_editor = CopyFieldToFieldEditor(parent, copy_definition, copy_mode)
        self.addWidget(self.field_to_field_editor)
        set_size_policy_for_all_widgets(self, QSizePolicyPreferred, QSizePolicyFixed)


class AcrossNotesCopyEditor(QWidget):
    def __init__(self, parent, copy_definition):
        super().__init__(parent)
        self.copy_definition = copy_definition

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(QAlignTop)
        self.setLayout(self.main_layout)
        self.form = QFormLayout()
        self.main_layout.addLayout(self.form)

        self.search_field_cbox = QComboBox()
        self.form.addRow("Note field to search with", self.search_field_cbox)

        self.card_query_text = QLineEdit()
        self.card_query_text.setPlaceholderText(
            f"\"deck:Deck name\" note:\"Note type\" some_field:*{SEARCH_FIELD_VALUE_PLACEHOLDER}*"
        )
        self.form.addRow(
            """Query to search for cards to copy from
(use $SEARCH_FIELD_VALUE$ as the value from the note field to search with)""",
            self.card_query_text,
        )

        self.card_select_cbox = QComboBox()
        self.card_select_cbox.addItem("Random")
        self.card_select_cbox.addItem("Least reps")
        self.card_select_cbox.setCurrentText("Random")
        self.form.addRow("How to select a card to copy from", self.card_select_cbox)

        self.card_select_count = QLineEdit()
        self.card_select_count.setValidator(QIntValidator())
        self.card_select_count.setMaxLength(2)
        self.card_select_count.setFixedWidth(60)
        self.card_select_count.setText("1")
        self.form.addRow("Select multiple cards? (optional)", self.card_select_count)

        self.card_select_separator = QLineEdit()
        self.card_select_separator.setText(", ")
        self.form.addRow("Separator for multiple values (optional)", self.card_select_separator)

        # Add field-to-field editor
        self.fields_vbox = FieldToFieldEditorVBox(self, copy_definition, COPY_MODE_ACROSS_NOTES)
        self.main_layout.addLayout(self.fields_vbox)

        # Set the current text in the combo boxes to what we had in memory in the configuration (if we had something)
        if copy_definition:
            with suppress(KeyError): self.search_field_cbox.setCurrentText(copy_definition["search_with_field"])
            with suppress(KeyError): self.card_query_text.setText(copy_definition["copy_from_cards_query"])
            with suppress(KeyError): self.card_select_cbox.setCurrentText(copy_definition["select_card_by"])
            with suppress(KeyError): self.card_select_count.setText(copy_definition["select_card_count"])
            with suppress(KeyError): self.card_select_separator.setText(copy_definition["select_card_separator"])

    def update_fields_by_target_note_type(self, model):
        self.search_field_cbox.clear()
        self.search_field_cbox.addItem("-")
        for field_name in mw.col.models.field_names(model):
            self.search_field_cbox.addItem(field_name)
            if field_name == self.copy_definition.get("search_with_field"):
                self.search_field_cbox.setCurrentText(field_name)

        self.fields_vbox.field_to_field_editor.set_selected_copy_into_model(model["name"])

    def get_field_to_field_editor(self):
        return self.fields_vbox.field_to_field_editor


class WithinNoteCopyEditor(QWidget):
    def __init__(self, parent, copy_definition):
        super().__init__(parent)
        self.copy_definition = copy_definition

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(QAlignTop)
        self.setLayout(self.main_layout)

        # Add field-to-field editor
        self.fields_vbox = FieldToFieldEditorVBox(self, copy_definition, COPY_MODE_WITHIN_NOTE)
        self.main_layout.addLayout(self.fields_vbox)

    def get_field_to_field_editor(self):
        return self.fields_vbox.field_to_field_editor

    def update_fields_by_target_note_type(self, model):
        self.fields_vbox.field_to_field_editor.set_selected_copy_into_model(model["name"])


class EditCopyDefinitionDialog(ScrollableQDialog):
    """
    Class for the dialog box to choose decks and note fields, has to be in a class so that the functions that update
    the dropdown boxes can access the text chosen in the other dropdown boxes.
    """

    def __init__(self, parent, copy_definition):
        # Define Ok and Cancel buttons as QPushButtons
        self.ok_button = QPushButton("Save")
        self.close_button = QPushButton("Cancel")

        self.ok_button.clicked.connect(self.check_fields)
        self.close_button.clicked.connect(self.reject)

        self.bottom_grid = QGridLayout()
        self.bottom_grid.setColumnMinimumWidth(0, 150)
        self.bottom_grid.setColumnMinimumWidth(1, 150)
        self.bottom_grid.setColumnMinimumWidth(2, 150)

        self.bottom_grid.addWidget(self.ok_button, 0, 0)
        self.bottom_grid.addWidget(self.close_button, 0, 2)

        super().__init__(parent, footer_layout=self.bottom_grid)
        self.copy_definition = copy_definition

        # Get the names of all the decks
        model_names_list = []
        for model in mw.col.models.all_names_and_ids():
            model_names_list.append(model.name)

        deck_names_list = []
        for deck in mw.col.decks.all_names_and_ids():
            # Wrap name in "" to avoid issues with commas in the name
            # multi-combo-box uses commas to separate items
            deck_names_list.append(f'"{deck.name}"')

        # Build form layout
        self.setWindowModality(WindowModal)
        self.main_layout = QVBoxLayout(self.inner_widget)
        self.form = QFormLayout()
        self.main_layout.addLayout(self.form)

        self.definition_name = QLineEdit()
        self.form.addRow("Name for this copy definition", self.definition_name)

        self.note_type_target_cbox = QComboBox()
        self.note_type_target_cbox.addItem("-")
        self.note_type_target_cbox.addItems(model_names_list)
        self.form.addRow("Note type to copy into", self.note_type_target_cbox)

        self.decks_limit_multibox = MultiComboBox()
        self.form.addRow("Deck to limit copying to (optional)", self.decks_limit_multibox)

        self.copy_on_sync = QCheckBox("Copy fields on sync for reviewed cards")
        self.copy_on_sync.setChecked(False)
        self.form.addRow("", self.copy_on_sync)

        # Both the across and within note editors will share the same field-to-field editor

        # Add tabs using QTabWidget to select between showing AcrossNotesCopyEditor and WithinNoteCopyEditor
        self.tabs_vbox = QVBoxLayout()
        self.main_layout.addLayout(self.tabs_vbox)
        self.selected_editor_type = COPY_MODE_ACROSS_NOTES

        self.editor_type_label = QLabel("Select copy type")
        self.tabs_vbox.addWidget(self.editor_type_label)
        self.editor_type_tabs = QTabWidget()

        self.across_notes_editor_tab = AcrossNotesCopyEditor(self, copy_definition)
        self.editor_type_tabs.addTab(self.across_notes_editor_tab, COPY_MODE_ACROSS_NOTES)
        self.active_field_to_field_editor = self.across_notes_editor_tab.get_field_to_field_editor()

        self.within_note_editor_tab = WithinNoteCopyEditor(self, copy_definition)
        self.editor_type_tabs.addTab(self.within_note_editor_tab, COPY_MODE_WITHIN_NOTE)

        self.tabs_vbox.addWidget(self.editor_type_tabs)
        set_size_policy_for_all_widgets(self.tabs_vbox, QSizePolicyPreferred, QSizePolicyFixed)

        # Connect the currentChanged signal to updateEditorType
        self.editor_type_tabs.currentChanged.connect(self.update_editor_type)

        if copy_definition:
            with suppress(KeyError): self.note_type_target_cbox.setCurrentText(copy_definition["copy_into_note_type"])
            with suppress(KeyError):
                self.definition_name.setText(copy_definition["definition_name"])
            with suppress(KeyError): self.copy_on_sync.setChecked(copy_definition["copy_on_sync"])
            with suppress(KeyError):
                self.decks_limit_multibox.setCurrentText(copy_definition["only_copy_into_decks"])
            with suppress(KeyError):
                self.selected_editor_type = copy_definition["copy_mode"]
            with suppress(KeyError):
                self.update_fields_by_target_note_type()
            with suppress(KeyError):
                self.selected_editor_type = copy_definition["copy_mode"]
                # Set the initially opened tab according to copy_mode
                if self.selected_editor_type == COPY_MODE_ACROSS_NOTES:
                    self.editor_type_tabs.setCurrentIndex(0)
                    self.active_field_to_field_editor = self.across_notes_editor_tab.get_field_to_field_editor()
                elif self.selected_editor_type == COPY_MODE_WITHIN_NOTE:
                    self.editor_type_tabs.setCurrentIndex(1)
                    self.active_field_to_field_editor = self.within_note_editor_tab.get_field_to_field_editor()


        # Connect signals
        self.note_type_target_cbox.currentTextChanged.connect(
            self.update_fields_by_target_note_type)

    def check_fields(self):
        show_error = False
        missing_copy_into_error = ""
        missing_copy_from_error = ""
        missing_card_query_error = ""
        missing_card_select_error = ""
        for field_to_field_definition in self.active_field_to_field_editor.get_field_to_field_defs():
            if field_to_field_definition["copy_into_note_field"] == "":
                missing_copy_into_error = "Copy into field cannot be empty."
                show_error = True
            if field_to_field_definition["copy_from_field"] == "":
                missing_copy_from_error = "Copy from field cannot be empty."
                show_error = True

        if self.selected_editor_type == COPY_MODE_ACROSS_NOTES:
            if self.across_notes_editor_tab.card_query_text.text() == "":
                show_error = True
                missing_card_query_error = "Search query cannot be empty"
            if self.across_notes_editor_tab.card_select_cbox.currentText() == "-":
                show_error = True
                missing_card_select_error = "Card selection method must be selected"
        if (show_error):
            showInfo(f"""Some required required fields are missing:
                {missing_copy_into_error if missing_copy_into_error else ""}
                {missing_copy_from_error if missing_copy_into_error else ""}
                {missing_card_query_error if missing_card_query_error else ""}
                {missing_card_select_error if missing_card_query_error else ""}
                """)
        else:  # Check that name is unique
            definition_name = self.definition_name.text()
            config = Config()
            config.load()
            name_match_count = 0
            for index, definition in enumerate(config.copy_definitions):
                if definition["definition_name"] == definition_name:
                    name_match_count += 1
            if name_match_count > 1:
                showInfo("There is another copy definition with the same name. Please choose a unique name.")
            return self.accept()

    def update_editor_type(self, index):
        if index == 0:
            self.selected_editor_type = COPY_MODE_ACROSS_NOTES
            self.active_field_to_field_editor = self.across_notes_editor_tab.get_field_to_field_editor()
        elif index == 1:
            self.selected_editor_type = COPY_MODE_WITHIN_NOTE
            self.active_field_to_field_editor = self.within_note_editor_tab.get_field_to_field_editor()

    def update_fields_by_target_note_type(self):
        """
        Updates the "Note field to copy into" and whatever fields in the editor widgets that depend
        on the note type chosen in the "Note type to copy into" dropdown box.
        """
        model = mw.col.models.by_name(self.note_type_target_cbox.currentText())
        if model is None:
            return

        # Update fields in editor tabs
        self.across_notes_editor_tab.update_fields_by_target_note_type(model)
        self.within_note_editor_tab.update_fields_by_target_note_type(model)

        mid = model["id"]

        dids = mw.col.db.list(f"""
                SELECT DISTINCT CASE WHEN odid==0 THEN did ELSE odid END
                FROM cards c, notes n
                WHERE n.mid = {mid}
                AND c.nid = n.id
            """)

        self.decks_limit_multibox.clear()
        self.decks_limit_multibox.addItem("-")
        for deck in [mw.col.decks.get(did) for did in dids]:
            # Wrap name in "" to avoid issues with commas in the name
            self.decks_limit_multibox.addItem(f'"{deck["name"]}"')

    def get_copy_definition(self):
        if self.selected_editor_type == COPY_MODE_ACROSS_NOTES:
            copy_definition: CopyDefinition = {
                "definition_name": self.definition_name.text(),
                "copy_into_note_type": self.note_type_target_cbox.currentText(),
                "only_copy_into_decks": self.decks_limit_multibox.currentText(),
                "field_to_field_defs": self.across_notes_editor_tab.get_field_to_field_editor().get_field_to_field_defs(),
                "search_with_field": self.across_notes_editor_tab.search_field_cbox.currentText(),
                "copy_from_cards_query": self.across_notes_editor_tab.card_query_text.text(),
                "select_card_by": self.across_notes_editor_tab.card_select_cbox.currentText(),
                "select_card_count": self.across_notes_editor_tab.card_select_count.text(),
                "select_card_separator": self.across_notes_editor_tab.card_select_separator.text(),
                "copy_on_sync": self.copy_on_sync.isChecked(),
                "copy_mode": self.selected_editor_type,
            }
            return copy_definition
        elif self.selected_editor_type == COPY_MODE_WITHIN_NOTE:
            copy_definition: CopyDefinition = {
                "definition_name": self.definition_name.text(),
                "copy_into_note_type": self.note_type_target_cbox.currentText(),
                "only_copy_into_decks": self.decks_limit_multibox.currentText(),
                "field_to_field_defs": self.within_note_editor_tab.get_field_to_field_editor().get_field_to_field_defs(),
                "copy_on_sync": self.copy_on_sync.isChecked(),
                "copy_mode": self.selected_editor_type,
                "search_with_field": None,
                "copy_from_cards_query": None,
                "select_card_by": None,
                "select_card_count": None,
                "select_card_separator": None,
            }
            return copy_definition
        return None
