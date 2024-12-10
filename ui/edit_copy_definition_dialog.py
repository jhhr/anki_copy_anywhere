from contextlib import suppress

# noinspection PyUnresolvedReferences
from anki.utils import ids2str
# noinspection PyUnresolvedReferences
from aqt import mw
# noinspection PyUnresolvedReferences
from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QLabel,
    QDialog,
    QComboBox,
    QTabWidget,
    QSizePolicy,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QGridLayout,
    QCheckBox,
    QIntValidator,
    Qt,
    qtmajor,
)
# noinspection PyUnresolvedReferences
from aqt.utils import showInfo

from .add_intersecting_model_field_options_to_dict import add_intersecting_model_field_options_to_dict
from .add_model_options_to_dict import add_model_options_to_dict
from .copy_field_to_field_editor import CopyFieldToFieldEditor, get_variable_names_from_copy_definition
from .field_to_variable_editor import CopyFieldToVariableEditor
from .interpolated_text_edit import InterpolatedTextEditLayout
from .scrollable_dialog import ScrollableQDialog
from ..configuration import (
    Config,
    CopyDefinition,
    COPY_MODE_WITHIN_NOTE,
    COPY_MODE_ACROSS_NOTES,
)
from ..logic.interpolate_fields import (
    VARIABLES_KEY,
    BASE_NOTE_MENU_DICT,
    intr_format,
)

if qtmajor > 5:
    from .multi_combo_box import MultiComboBoxQt6 as MultiComboBox

    WindowModal = Qt.WindowModality.WindowModal
    QSizePolicyFixed = QSizePolicy.Policy.Fixed
    QSizePolicyPreferred = QSizePolicy.Policy.Preferred
    QAlignTop = Qt.AlignmentFlag.AlignTop
else:
    from .multi_combo_box import MultiComboBoxQt5 as MultiComboBox

    WindowModal = Qt.WindowModal
    QSizePolicyFixed = QSizePolicy.Fixed
    QSizePolicyPreferred = QSizePolicy.Preferred
    QAlignTop = Qt.AlignTop


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


class FieldsToVariableEditorVBox(QVBoxLayout):
    def __init__(self, parent, copy_definition):
        super().__init__(parent)
        self.addWidget(QLabel("Fields to copy into variables"))
        self.field_to_variable_editor = CopyFieldToVariableEditor(parent, copy_definition)
        self.addWidget(self.field_to_variable_editor)
        set_size_policy_for_all_widgets(self, QSizePolicyPreferred, QSizePolicyFixed)


class AcrossNotesCopyEditor(QWidget):
    def __init__(self, parent, copy_definition):
        super().__init__(parent)
        self.copy_definition = copy_definition

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(QAlignTop)
        self.setLayout(self.main_layout)

        self.variables_vbox = FieldsToVariableEditorVBox(self, copy_definition)
        self.main_layout.addLayout(self.variables_vbox)

        self.form = QFormLayout()
        self.main_layout.addLayout(self.form)

        self.card_query_text_layout = InterpolatedTextEditLayout(
            label="Search query to get source cards",
            # No special fields for search, just the destination note fields will be used
            options_dict={},
            description=f"""<ul>
            <li>Use the same query syntax as in the card browser</li> 
            <li>Reference the destination notes' fields with {intr_format('Field Name')}.</li>
            <li>Right-click to select a {intr_format('Field Name')} or special values to paste</li>
            </ul>""",
            height=100,
            placeholder_text=f'\"deck:My deck\" "A Different Field:*{intr_format("Field_Name")}*" -is:suspended',
        )

        self.form.addRow(self.card_query_text_layout)

        self.card_select_cbox = QComboBox()
        self.card_select_cbox.addItem("Random")
        self.card_select_cbox.addItem("Least_reps")
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
            with suppress(KeyError):
                self.card_query_text_layout.set_text(copy_definition["copy_from_cards_query"])
            with suppress(KeyError):
                self.card_select_cbox.setCurrentText(copy_definition["select_card_by"])
            with suppress(KeyError):
                self.card_select_count.setText(copy_definition["select_card_count"])
            with suppress(KeyError):
                self.card_select_separator.setText(copy_definition["select_card_separator"])

    def update_fields_by_target_note_type(self, models):
        self.fields_vbox.field_to_field_editor.set_selected_copy_into_models(models)
        self.variables_vbox.field_to_variable_editor.set_selected_copy_into_models(models)

        new_options_dict = BASE_NOTE_MENU_DICT.copy()
        variables_dict = get_variable_names_from_copy_definition(self.copy_definition)
        if variables_dict:
            new_options_dict[VARIABLES_KEY] = variables_dict

        # If there are multiple models, add the intersecting fields only
        if len(models) > 1:
            add_intersecting_model_field_options_to_dict(
                models,
                new_options_dict,
            )
        elif len(models) == 1:
            model = models[0]
            add_model_options_to_dict(model["name"], model["id"], new_options_dict)

        self.card_query_text_layout.update_options(new_options_dict)
        self.card_query_text_layout.validate_text()

    def get_field_to_field_editor(self):
        return self.fields_vbox.field_to_field_editor

    def get_field_to_variable_editor(self):
        return self.variables_vbox.field_to_variable_editor


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

    def update_fields_by_target_note_type(self, models):
        self.fields_vbox.field_to_field_editor.set_selected_copy_into_models(models)


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
        self.top_form = QFormLayout()
        self.main_layout.addLayout(self.top_form)

        self.definition_name = QLineEdit()
        self.top_form.addRow("Name for this copy definition", self.definition_name)

        self.middle_form = QFormLayout()
        self.main_layout.addLayout(self.middle_form)

        self.note_type_target_cbox = MultiComboBox()
        self.note_type_target_cbox.addItem("-")
        # Wrap name in "" to avoid issues with commas in the name
        self.note_type_target_cbox.addItems([f'"{model_name}"' for model_name in model_names_list])
        self.middle_form.addRow("Destination note type", self.note_type_target_cbox)
        # Set up a label for showing a warning, if selecting multiple models
        self.note_type_target_warning = QLabel("")
        self.middle_form.addRow("", self.note_type_target_warning)

        self.decks_limit_multibox = MultiComboBox()
        self.middle_form.addRow("Destination deck limit (optional)", self.decks_limit_multibox)

        self.copy_on_sync_checkbox = QCheckBox("Run on sync for reviewed cards")
        self.copy_on_sync_checkbox.setChecked(False)
        self.middle_form.addRow("", self.copy_on_sync_checkbox)

        self.copy_on_add_checkbox = QCheckBox("Run when adding new note")
        self.copy_on_add_checkbox.setChecked(False)
        self.middle_form.addRow("", self.copy_on_add_checkbox)

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
            with suppress(KeyError):
                self.note_type_target_cbox.setCurrentText(copy_definition["copy_into_note_types"])
            self.update_fields_by_target_note_type()
            with suppress(KeyError):
                self.definition_name.setText(copy_definition["definition_name"])
            with suppress(KeyError):
                self.copy_on_sync_checkbox.setChecked(copy_definition["copy_on_sync"])
            with suppress(KeyError):
                self.copy_on_add_checkbox.setChecked(copy_definition["copy_on_add"])
            with suppress(KeyError):
                self.decks_limit_multibox.setCurrentText(copy_definition["only_copy_into_decks"])
            with suppress(KeyError):
                self.selected_editor_type = copy_definition["copy_mode"]
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
            if field_to_field_definition["copy_from_text"] == "":
                missing_copy_from_error = "Copy from text cannot be empty."
                show_error = True

        if self.selected_editor_type == COPY_MODE_ACROSS_NOTES:
            if self.across_notes_editor_tab.card_query_text_layout.get_text() == "":
                show_error = True
                missing_card_query_error = "Search query cannot be empty"
            if self.across_notes_editor_tab.card_select_cbox.currentText() == "-":
                show_error = True
                missing_card_select_error = "Card selection method must be selected"
        if (show_error):
            showInfo(f"""Some required required fields are missing:
                {missing_copy_into_error if missing_copy_into_error else ""}
                {missing_copy_from_error if missing_copy_from_error else ""}
                {missing_card_query_error if missing_card_query_error else ""}
                {missing_card_select_error if missing_card_select_error else ""}
                """)
        else:  # Check that name is unique
            definition_name = self.definition_name.text()
            config = Config()
            config.load()
            name_match_count = 0
            for definition in config.copy_definitions:
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
        models = list(filter(None, [mw.col.models.by_name(name.strip('""')) for name in
                                    self.note_type_target_cbox.currentData()]))
        if not models:
            return

        if len(models) > 1:
            text = "When selecting multiple note types, only the fields that are common to all note types will be available as destinations."
            # Check that each model has a single card template only
            models_first_templates = []
            for model in models:
                if len(model["tmpls"]) > 1:
                    models_first_templates.append((model["name"], model["tmpls"][0]["name"]))
            if models_first_templates:
                text += f"<br><span style='color: orange'>WARNING:</span> The following note types have multiple card types. Only the first one will be used when applying special card values:<ul>"
                for model_name, template_name in models_first_templates:
                    text += f"<li>{model_name}: {template_name}</li>"
                text += "</ul>"
            self.note_type_target_warning.setText(text)
        else:
            self.note_type_target_warning.setText("")

        # Update fields in editor tabs
        self.across_notes_editor_tab.update_fields_by_target_note_type(models)
        self.within_note_editor_tab.update_fields_by_target_note_type(models)

        mids = [model["id"] for model in models]

        dids = mw.col.db.list(f"""
                SELECT DISTINCT CASE WHEN odid==0 THEN did ELSE odid END
                FROM cards c, notes n
                WHERE n.mid IN {ids2str(mids)}
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
                "copy_into_note_types": self.note_type_target_cbox.currentText(),
                "only_copy_into_decks": self.decks_limit_multibox.currentText(),
                "field_to_field_defs": self.across_notes_editor_tab.get_field_to_field_editor().get_field_to_field_defs(),
                "field_to_variable_defs": self.across_notes_editor_tab.get_field_to_variable_editor().get_field_to_variable_defs(),
                "copy_from_cards_query": self.across_notes_editor_tab.card_query_text_layout.get_text(),
                "select_card_by": self.across_notes_editor_tab.card_select_cbox.currentText(),
                "select_card_count": self.across_notes_editor_tab.card_select_count.text(),
                "select_card_separator": self.across_notes_editor_tab.card_select_separator.text(),
                "copy_on_sync": self.copy_on_sync_checkbox.isChecked(),
                "copy_on_add": self.copy_on_add_checkbox.isChecked(),
                "copy_mode": self.selected_editor_type,
            }
            return copy_definition
        elif self.selected_editor_type == COPY_MODE_WITHIN_NOTE:
            copy_definition: CopyDefinition = {
                "definition_name": self.definition_name.text(),
                "copy_into_note_types": self.note_type_target_cbox.currentText(),
                "only_copy_into_decks": self.decks_limit_multibox.currentText(),
                "field_to_variable_defs": [],
                "field_to_field_defs": self.within_note_editor_tab.get_field_to_field_editor().get_field_to_field_defs(),
                "copy_on_sync": self.copy_on_sync_checkbox.isChecked(),
                "copy_on_add": self.copy_on_add_checkbox.isChecked(),
                "copy_mode": self.selected_editor_type,
                "copy_from_cards_query": None,
                "select_card_by": None,
                "select_card_count": None,
                "select_card_separator": None,
            }
            return copy_definition
        return None
