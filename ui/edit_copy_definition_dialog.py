from contextlib import suppress
from typing import Optional, Union, Tuple, cast

from anki.models import NotetypeDict
from anki.decks import DeckId

from anki.utils import ids2str

from aqt import mw

from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSpacerItem,
    QTabWidget,
    QSizePolicy,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QGridLayout,
    QCheckBox,
    QIntValidator,
    QGuiApplication,
    Qt,
    qtmajor,
)

from aqt.utils import showInfo

from .add_intersecting_model_field_options_to_dict import (
    add_intersecting_model_field_options_to_dict,
)
from .add_model_options_to_dict import add_model_options_to_dict
from .copy_field_to_field_editor import (
    CopyFieldToFieldEditor,
    get_variable_names_from_copy_definition,
)
from .field_to_variable_editor import CopyFieldToVariableEditor
from .grouped_combo_box import GroupedComboBox
from .interpolated_text_edit import InterpolatedTextEditLayout
from .required_combobox import RequiredCombobox
from .required_text_input import RequiredLineEdit
from .scrollable_dialog import ScrollableQDialog
from .multi_combo_box import MultiComboBox
from ..configuration import (
    Config,
    CopyDefinition,
    COPY_MODE_WITHIN_NOTE,
    COPY_MODE_ACROSS_NOTES,
    DIRECTION_SOURCE_TO_DESTINATIONS,
    DIRECTION_DESTINATION_TO_SOURCES,
    CopyModeType,
    DirectionType,
    SelectCardByType,
    SELECT_CARD_BY_VALUES,
)
from ..logic.interpolate_fields import (
    VARIABLES_KEY,
    BASE_NOTE_MENU_DICT,
    intr_format,
)
from ..utils import block_signals

if qtmajor > 5:
    WindowModal = Qt.WindowModality.WindowModal
    QSizePolicyFixed = QSizePolicy.Policy.Fixed
    QSizePolicyPreferred = QSizePolicy.Policy.Preferred
    QSizePolicyMinimum = QSizePolicy.Policy.Minimum
    QSizePolicyExpanding = QSizePolicy.Policy.Expanding
    QAlignTop = Qt.AlignmentFlag.AlignTop
    QAlignCenter = Qt.AlignmentFlag.AlignCenter
else:
    WindowModal = Qt.WindowModal  # type: ignore
    QSizePolicyFixed = QSizePolicy.Fixed  # type: ignore
    QSizePolicyPreferred = QSizePolicy.Preferred  # type: ignore
    QSizePolicyMinimum = QSizePolicy.Minimum  # type: ignore
    QSizePolicyExpanding = QSizePolicy.Expanding  # type: ignore
    QAlignTop = Qt.AlignTop  # type: ignore
    QAlignCenter = Qt.AlignCenter  # type: ignore


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


class BasicEditorFormLayout(QFormLayout):
    """
    Editor for the basic fields of a copy definition that both AcrossNotesCopyEditor
    and WithinNoteCopyEditor share.
    """

    def __init__(
        self,
        parent,
        copy_definition: Optional[CopyDefinition] = None,
        extra_top_widgets: Optional[list[Tuple[QLabel, QWidget]]] = None,
    ):
        super().__init__(parent)

        self.copy_definition = copy_definition

        # Get the names of all the decks
        model_names_list = []
        for model in mw.col.models.all_names_and_ids():
            model_names_list.append(model.name)

        self.selected_models: list[NotetypeDict] = []

        if extra_top_widgets:
            for label, widget in extra_top_widgets:
                self.addRow(label, widget)
            spacer = QSpacerItem(100, 20, QSizePolicyExpanding, QSizePolicyMinimum)
            self.addItem(spacer)

        self.note_type_target_cbox = MultiComboBox(
            placeholder_text="Select note types",
            is_required=True,
        )
        self.note_type_target_cbox.setMinimumWidth(300)
        # Wrap name in "" to avoid issues with commas in the name
        self.note_type_target_cbox.addItems([f'"{model_name}"' for model_name in model_names_list])
        self.target_note_type_label = QLabel("<h3>Trigger (destination) note type</h3>")
        self.addRow(self.target_note_type_label, self.note_type_target_cbox)
        self.note_type_target_cbox.currentTextChanged.connect(self.set_current_models)

        # Set up a label for showing a warning, if selecting multiple models
        self.note_type_target_warning = QLabel("")
        self.addRow("", self.note_type_target_warning)

        self.decks_limit_multibox = MultiComboBox(
            placeholder_text="First, select a trigger note type"
        )
        self.decks_limit_multibox.setMinimumWidth(300)
        self.decks_init_done = False
        self.deck_limit_label = QLabel("<h4>Trigger (destination) deck limit</h4>")
        self.addRow(self.deck_limit_label, self.decks_limit_multibox)
        self.addRow(
            "",
            QLabel("""<small>Cards belong to decks, not notes.<br>
        If your note type has multiple card types, the whitelisting applies to the note,<rb>
        if any of its cards belong to a whitelisted deck.</small>"""),
        )

        self.copy_on_sync_checkbox = QCheckBox("Run on sync for reviewed cards")
        self.copy_on_sync_checkbox.setChecked(False)
        self.addRow("", self.copy_on_sync_checkbox)

        self.copy_on_add_checkbox = QCheckBox("Run when adding new note")
        self.copy_on_add_checkbox.setChecked(False)
        self.addRow("", self.copy_on_add_checkbox)

        self.copy_on_review_checkbox = QCheckBox("Run on review")
        self.copy_on_review_checkbox.setChecked(False)
        self.addRow("", self.copy_on_review_checkbox)

        spacer = QSpacerItem(100, 40, QSizePolicyExpanding, QSizePolicyMinimum)
        self.addItem(spacer)

        self.init_fields(copy_definition)

    def update_direction_labels(self, direction):
        if direction == DIRECTION_SOURCE_TO_DESTINATIONS:
            target_type = "source"
        else:
            target_type = "destination"
        self.target_note_type_label.setText(f"<h3>Trigger ({target_type}) note type</h3>")
        self.deck_limit_label.setText(f"<h4>Trigger ({target_type}) deck limit</h4>")

    def init_fields(self, copy_definition: Optional[CopyDefinition]):
        if copy_definition:
            with suppress(KeyError):
                self.note_type_target_cbox.setCurrentText(copy_definition["copy_into_note_types"])
                self.note_type_target_cbox.update_required_style()
                self.set_current_models()
            with suppress(KeyError):
                self.copy_on_sync_checkbox.setChecked(copy_definition["copy_on_sync"])
            with suppress(KeyError):
                self.copy_on_add_checkbox.setChecked(copy_definition["copy_on_add"])
            with suppress(KeyError):
                self.copy_on_review_checkbox.setChecked(copy_definition["copy_on_review"])
            with suppress(KeyError):
                self.decks_limit_multibox.setCurrentText(copy_definition["only_copy_into_decks"])
            with suppress(KeyError):
                copy_mode: CopyModeType = copy_definition["copy_mode"]
                if copy_mode == COPY_MODE_ACROSS_NOTES:
                    direction = (
                        copy_definition.get("across_mode_direction")
                        or DIRECTION_DESTINATION_TO_SOURCES
                    )
                    self.update_direction_labels(direction)

    def set_current_models(self):
        models = list(
            filter(
                None,
                [
                    mw.col.models.by_name(name.strip('""'))
                    for name in self.note_type_target_cbox.currentData()
                ],
            )
        )
        self.selected_models = models

        if len(models) > 1:
            text = (
                "When selecting multiple note types, only the fields that are common to all"
                + " note types will be available as destinations."
            )
            # Check that each model has a single card template only
            models_first_templates = []
            for model in models:
                if len(model["tmpls"]) > 1:
                    models_first_templates.append((model["name"], model["tmpls"][0]["name"]))
            if models_first_templates:
                text += """<br><span style='color: orange'>WARNING:</span>
                The following note types have multiple card types.
                Only the first one will be used when applying special card values:
                <ul>"""
                for model_name, template_name in models_first_templates:
                    text += f"<li>{model_name}: {template_name}</li>"
                text += "</ul>"
            self.note_type_target_warning.setText(text)
        else:
            self.note_type_target_warning.setText("")

    def set_current_decks(self):
        assert mw.col.db is not None
        mids: list[int] = [model["id"] for model in self.selected_models]
        dids: list[DeckId] = mw.col.db.list(f"""
                SELECT DISTINCT CASE WHEN odid==0 THEN did ELSE odid END
                FROM cards c, notes n
                WHERE n.mid IN {ids2str(mids)}
                AND c.nid = n.id
            """)

        if self.decks_init_done:
            current_deck_names = [d.strip('""') for d in self.decks_limit_multibox.currentData()]
        elif self.copy_definition:
            current_deck_names = (
                self.copy_definition.get("only_copy_into_decks", "").strip('""').split('", "')
            )
        else:
            current_deck_names = []
        self.decks_limit_multibox.clear()
        for deck in [mw.col.decks.get(did) for did in dids]:
            if deck is None:
                continue
            # Wrap name in "" to avoid issues with commas in the name
            self.decks_limit_multibox.addItem(f'"{deck["name"]}"')
            if deck["name"] in current_deck_names:
                self.decks_limit_multibox.addSelectedItem(f'"{deck["name"]}"')

        self.decks_limit_multibox.set_popup_and_box_width()

        # Update placeholder text
        if len(self.selected_models) == 0:
            self.decks_limit_multibox.setPlaceholderText("First, select a trigger note type")
            self.decks_limit_multibox.setDisabled(True)
        elif len(dids) > 0:
            self.decks_limit_multibox.setPlaceholderText("Select decks (optional)")
            self.decks_limit_multibox.setDisabled(False)
        else:
            self.decks_limit_multibox.setPlaceholderText("No decks found for selected note types")
            self.decks_limit_multibox.setDisabled(True)

    def get_selected_models(self):
        return self.selected_models


class FieldToFieldEditorVBox(QVBoxLayout):
    def __init__(self, parent, copy_definition: Optional[CopyDefinition], copy_mode: CopyModeType):
        super().__init__(parent)
        self.addWidget(QLabel("<h2>Define copied content</h2>"))
        self.field_to_field_editor = CopyFieldToFieldEditor(parent, copy_definition, copy_mode)
        self.addWidget(self.field_to_field_editor)
        spacer = QSpacerItem(100, 20, QSizePolicyExpanding, QSizePolicyMinimum)
        self.addItem(spacer)
        set_size_policy_for_all_widgets(self, QSizePolicyPreferred, QSizePolicyFixed)


class FieldsToVariableEditorVBox(QVBoxLayout):
    def __init__(self, parent, copy_definition: Optional[CopyDefinition]):
        super().__init__(parent)
        self.addWidget(QLabel("<h3>Fields to copy into variables</h3>"))
        self.field_to_variable_editor = CopyFieldToVariableEditor(parent, copy_definition)
        self.addWidget(self.field_to_variable_editor)
        spacer = QSpacerItem(100, 40, QSizePolicyExpanding, QSizePolicyMinimum)
        self.addItem(spacer)
        set_size_policy_for_all_widgets(self, QSizePolicyPreferred, QSizePolicyFixed)


class AcrossNotesCopyEditor(QWidget):
    def __init__(self, parent, copy_definition: Optional[CopyDefinition]):
        super().__init__(parent)
        self.copy_definition = copy_definition

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(QAlignTop)
        self.setLayout(self.main_layout)

        self.get_copy_mode = lambda: parent.get_copy_mode()

        self.direction_radio_buttons = QHBoxLayout()
        self.destination_to_source_radio = QRadioButton(DIRECTION_DESTINATION_TO_SOURCES)
        self.direction_radio_buttons.addWidget(self.destination_to_source_radio)
        self.source_to_destination_radio = QRadioButton(DIRECTION_SOURCE_TO_DESTINATIONS)
        self.direction_radio_buttons.addWidget(self.source_to_destination_radio)
        # Connect the radio buttons to update the labels in the basic editor form layout
        self.source_to_destination_radio.toggled.connect(
            lambda: self.update_direction_labels(DIRECTION_SOURCE_TO_DESTINATIONS)
        )
        self.destination_to_source_radio.toggled.connect(
            lambda: self.update_direction_labels(DIRECTION_DESTINATION_TO_SOURCES)
        )
        self.direction_radio_buttons.addStretch(1)

        self.basic_editor_form_layout = BasicEditorFormLayout(
            self,
            copy_definition,
            extra_top_widgets=[(
                QLabel("<h3>Copy direction</h3>"),
                self.wrap_in_widget(self.direction_radio_buttons),
            )],
        )
        self.main_layout.addLayout(self.basic_editor_form_layout)

        self.variables_vbox = FieldsToVariableEditorVBox(self, copy_definition)
        self.main_layout.addLayout(self.variables_vbox)

        self.form = QFormLayout()
        self.main_layout.addLayout(self.form)

        self.card_query_text_label = QLabel("<h3>Search query to get source notes</h3>")
        self.card_query_text_layout = InterpolatedTextEditLayout(
            label=self.card_query_text_label,
            is_required=True,
            # No special fields for search, just the destination note fields will be used
            options_dict={},
            description=f"""<ul>
            <li>Use the same query syntax as in the card/note browser</li>
            <li>Reference the destination notes' fields with {intr_format('Field Name')}.</li>
            <li>Right-click to select a {intr_format('Field Name')} or special values to paste</li>
            </ul>""",
            height=100,
            placeholder_text=(
                f'"deck:My deck" "A Different Field:*{intr_format("Field_Name")}*" -is:suspended'
            ),
        )

        self.form.addRow(self.card_query_text_layout)

        self.sort_by_field_cbox = GroupedComboBox(is_required=False)
        self.form.addRow("<h4>Sort queried notes by field</h4>", self.sort_by_field_cbox)
        # Add all fields from all note types
        self.sort_by_field_cbox.addItem("-")
        self.sort_by_field_cbox.setCurrentText("-")
        for model in mw.col.models.all():
            self.sort_by_field_cbox.addGroup(model["name"])
            for field in model["flds"]:
                self.sort_by_field_cbox.addItemToGroup(model["name"], field["name"])

        self.card_select_hbox = QHBoxLayout()
        self.card_select_cbox = RequiredCombobox()
        self.card_select_cbox.setMaximumWidth(100)
        for value in SELECT_CARD_BY_VALUES:
            self.card_select_cbox.addItem(value)
        self.card_select_cbox.setCurrentText("Random")
        self.card_select_by_right_label = QLabel("")
        self.card_select_hbox.addWidget(self.card_select_cbox)
        self.card_select_hbox.addWidget(self.card_select_by_right_label)
        self.form.addRow("<h4>How to select a card to copy from</h4>", self.card_select_hbox)

        card_select_count_hbox = QHBoxLayout()
        self.card_select_count = QLineEdit()
        # Validate that the input is a positive integer, or 0 for all
        self.card_select_count.setValidator(QIntValidator(0, 999))
        self.card_select_count.setMaxLength(3)
        self.card_select_count.setFixedWidth(60)
        self.card_select_count.setText("1")
        self.card_select_count_right_label = QLabel("")
        card_select_count_hbox.addWidget(self.card_select_count)
        card_select_count_hbox.addWidget(self.card_select_count_right_label)
        card_select_count_hbox.addStretch(1)
        self.form.addRow("<h5>Select multiple cards? (set 0 for all)</h5>", card_select_count_hbox)

        self.card_select_count.textChanged.connect(self.on_card_select_count_changed)

        self.card_select_separator = RequiredLineEdit()
        self.card_select_separator.setText(", ")
        self.form.addRow("<h5>Separator for multiple values</h5>", self.card_select_separator)
        spacer = QSpacerItem(100, 40, QSizePolicyExpanding, QSizePolicyMinimum)
        self.form.addItem(spacer)

        # Add field-to-field editor
        self.fields_vbox = FieldToFieldEditorVBox(self, copy_definition, COPY_MODE_ACROSS_NOTES)
        self.main_layout.addLayout(self.fields_vbox)

        # Set the current text in the combo boxes to what we had in memory in the configuration
        # (if we had something)
        if copy_definition:
            with suppress(KeyError):
                self.card_query_text_layout.set_text(copy_definition["copy_from_cards_query"])
            with suppress(KeyError):
                self.sort_by_field_cbox.setCurrentText(copy_definition["sort_by_field"])
            with suppress(KeyError):
                self.card_select_cbox.setCurrentText(copy_definition["select_card_by"])
            with suppress(KeyError):
                self.card_select_count.setText(copy_definition["select_card_count"])
            with suppress(KeyError):
                self.card_select_separator.setText(copy_definition["select_card_separator"])
        # Always init the direction, as this will set the checkboxes state, and various
        # labels everywhere
        direction = copy_definition.get("across_mode_direction") if copy_definition else None
        if direction == DIRECTION_SOURCE_TO_DESTINATIONS:
            self.update_direction_labels(DIRECTION_SOURCE_TO_DESTINATIONS)
        else:
            self.update_direction_labels(DIRECTION_DESTINATION_TO_SOURCES)

    # If card_select_count is > 1, separator is required, otherwise it's ok to be empty
    def on_card_select_count_changed(self, text: str):
        if (
            self.get_copy_mode() == COPY_MODE_ACROSS_NOTES
            and self.get_selected_direction() == DIRECTION_SOURCE_TO_DESTINATIONS
        ):
            # If the direction is source to destinations, the card separator is not relevant
            # as we're copying from a single source to multiple destinations one-by-one
            self.card_select_separator.set_required(False)
            self.card_select_count_right_label.setText("")
            self.card_select_separator.setPlaceholderText(
                "Is not used in source to destination mode"
            )
        try:
            count = int(text)
        except ValueError:
            count = 1
        if count == 1:
            self.card_select_separator.set_required(False)
            self.card_select_count_right_label.setText("")
            self.card_select_separator.setPlaceholderText("Can be empty, if count = 1")
            self.card_select_by_right_label.setText("")
        elif count > 1:
            self.card_select_separator.set_required(True)
            self.card_select_separator.setPlaceholderText("Required, if count > 1")
            self.card_select_by_right_label.setText("")
        elif count == 0:
            self.card_select_count_right_label.setText(
                '<span style="color: orange">All searched cards will be used</span>'
            )
            self.card_select_separator.setPlaceholderText("Required, if count > 1")
            self.card_select_by_right_label.setText(
                '<span style="color: darkgray">Does nothing, all cards will be used</span>'
            )
        else:
            # Shouldn't happen with the validator, but just in case
            self.card_select_count_right_label.setText("Invalid number")

    def wrap_in_widget(self, layout):
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def update_direction_labels(self, direction: DirectionType):
        self.basic_editor_form_layout.update_direction_labels(direction)
        self.get_field_to_field_editor().update_direction_labels(direction)

        with block_signals(self.source_to_destination_radio, self.destination_to_source_radio):
            if direction == DIRECTION_SOURCE_TO_DESTINATIONS:
                self.source_to_destination_radio.setChecked(True)
                self.destination_to_source_radio.setChecked(False)
                self.card_query_text_label.setText("<h3>Search query to get source cards</h3>")
                self.fields_vbox.field_to_field_editor.update_all_field_target_cboxes()
            else:
                self.destination_to_source_radio.setChecked(True)
                self.source_to_destination_radio.setChecked(False)
                self.card_query_text_label.setText("<h3>Search query to get destination cards</h3>")

    def get_selected_direction(self) -> DirectionType:
        if self.source_to_destination_radio.isChecked():
            return DIRECTION_SOURCE_TO_DESTINATIONS
        else:
            return DIRECTION_DESTINATION_TO_SOURCES

    def update_fields_by_target_note_type(self, models: list[NotetypeDict]):
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

    def get_field_to_field_editor(self) -> CopyFieldToFieldEditor:
        return self.fields_vbox.field_to_field_editor

    def get_field_to_variable_editor(self) -> CopyFieldToVariableEditor:
        return self.variables_vbox.field_to_variable_editor


class WithinNoteCopyEditor(QWidget):
    def __init__(
        self,
        parent,
        copy_definition: Optional[CopyDefinition],
    ):
        super().__init__(parent)
        self.copy_definition = copy_definition

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(QAlignTop)
        self.setLayout(self.main_layout)

        self.basic_editor_form_layout = BasicEditorFormLayout(self, copy_definition)
        self.main_layout.addLayout(self.basic_editor_form_layout)

        # Add field-to-field editor
        self.fields_vbox = FieldToFieldEditorVBox(self, copy_definition, COPY_MODE_WITHIN_NOTE)
        self.main_layout.addLayout(self.fields_vbox)

    def get_field_to_field_editor(self):
        return self.fields_vbox.field_to_field_editor

    def update_fields_by_target_note_type(self, models):
        self.fields_vbox.field_to_field_editor.set_selected_copy_into_models(models)


class EditCopyDefinitionDialog(ScrollableQDialog):
    """
    Class for the dialog box to choose decks and note fields, has to be in a class so that the
    functions that update the dropdown boxes can access the text chosen in the other dropdown boxes.
    """

    def __init__(self, parent, copy_definition: Optional[CopyDefinition] = None):
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

        # Build form layout
        self.setWindowModality(WindowModal)
        self.main_layout = QVBoxLayout(self.inner_widget)
        self.top_form = QFormLayout()
        self.main_layout.addLayout(self.top_form)

        self.definition_name = RequiredLineEdit(is_required=True)
        self.top_form.addRow("<h2>Name for this copy definition</h2>", self.definition_name)

        self.tabs_vbox = QVBoxLayout()
        self.main_layout.addLayout(self.tabs_vbox)
        self.selected_editor_type: CopyModeType = COPY_MODE_ACROSS_NOTES

        self.editor_type_label = QLabel("<h2>Select copy type</h2>")
        self.editor_type_label.setAlignment(QAlignCenter)
        self.tabs_vbox.addWidget(self.editor_type_label)
        self.editor_type_tabs = QTabWidget()
        self.editor_type_tabs.setStyleSheet("""
        QTabBar::tab {
            font-size: 14px;
            font-weight: bold;
        }
        """)

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
                self.definition_name.setText(copy_definition["definition_name"])
                self.definition_name.update_required_style()
            with suppress(KeyError):
                self.selected_editor_type = copy_definition["copy_mode"]
            with suppress(KeyError):
                self.selected_editor_type = copy_definition["copy_mode"]
                # Set the initially opened tab according to copy_mode
                if self.selected_editor_type == COPY_MODE_ACROSS_NOTES:
                    self.editor_type_tabs.setCurrentIndex(0)
                    self.active_field_to_field_editor = (
                        self.across_notes_editor_tab.get_field_to_field_editor()
                    )
                elif self.selected_editor_type == COPY_MODE_WITHIN_NOTE:
                    self.editor_type_tabs.setCurrentIndex(1)
                    self.active_field_to_field_editor = (
                        self.within_note_editor_tab.get_field_to_field_editor()
                    )

        # Connect signals
        across_target_cbox = (
            self.across_notes_editor_tab.basic_editor_form_layout.note_type_target_cbox
        )
        within_target_cbox = (
            self.within_note_editor_tab.basic_editor_form_layout.note_type_target_cbox
        )
        across_target_cbox.currentTextChanged.connect(
            lambda _: self.update_fields_by_target_note_type(
                self.across_notes_editor_tab.basic_editor_form_layout
            )
        )
        within_target_cbox.currentTextChanged.connect(
            lambda _: self.update_fields_by_target_note_type(
                self.within_note_editor_tab.basic_editor_form_layout
            )
        )

        # Initialize the fields in the editor tabs
        self.update_fields_by_target_note_type(
            self.across_notes_editor_tab.basic_editor_form_layout
        )
        self.update_fields_by_target_note_type(self.within_note_editor_tab.basic_editor_form_layout)

        # Set dialog width window width
        screen = QGuiApplication.primaryScreen()
        if screen:
            available_geometry = screen.availableGeometry()
            self.resize(
                max(self.sizeHint().width(), int(available_geometry.width() * 0.80)),
                int(min(self.sizeHint().height() * 1.5, int(available_geometry.height()))),
            )

    def check_fields(self):
        show_error = False
        missing_name_error = ""
        missing_copy_into_error = ""
        missing_copy_from_error = ""
        missing_card_query_error = ""
        missing_card_select_error = ""
        if self.definition_name.text() == "":
            missing_name_error = "Definition name cannot be empty."
            show_error = True
        for (
            field_to_field_definition
        ) in self.active_field_to_field_editor.get_field_to_field_defs():
            if field_to_field_definition["copy_into_note_field"] == "":
                missing_copy_into_error = "Destination field cannot be empty."
                show_error = True
            if field_to_field_definition["copy_from_text"] == "":
                missing_copy_from_error = "Copied content cannot be empty."
                show_error = True

        if self.selected_editor_type == COPY_MODE_ACROSS_NOTES:
            if self.across_notes_editor_tab.card_query_text_layout.get_text() == "":
                show_error = True
                missing_card_query_error = "Search text cannot be empty"
            if (
                self.across_notes_editor_tab.card_select_cbox.currentText()
                not in SELECT_CARD_BY_VALUES
            ):
                show_error = True
                missing_card_select_error = "Card selection method must be selected"
        if show_error:
            showInfo(f"""Some required required fields are missing:
                {missing_name_error if missing_name_error else ""}
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
                showInfo(
                    "There is another copy definition with the same name. Please choose a unique"
                    " name."
                )
            self.accept()

    def update_editor_type(self, index: int):
        if index == 0:
            self.selected_editor_type = COPY_MODE_ACROSS_NOTES
            self.active_field_to_field_editor = (
                self.across_notes_editor_tab.get_field_to_field_editor()
            )
        elif index == 1:
            self.selected_editor_type = COPY_MODE_WITHIN_NOTE
            self.active_field_to_field_editor = (
                self.within_note_editor_tab.get_field_to_field_editor()
            )

    def update_fields_by_target_note_type(self, basic_editor_layout: BasicEditorFormLayout):
        """
        Updates the "Note field to copy into" and whatever fields in the editor widgets that depend
        on the note type chosen in the "Note type to copy into" dropdown box.
        """
        models = basic_editor_layout.get_selected_models()

        # Update fields in editor tabs
        self.across_notes_editor_tab.update_fields_by_target_note_type(models)
        self.within_note_editor_tab.update_fields_by_target_note_type(models)

        # Update deck options in the basic editor form layout
        self.across_notes_editor_tab.basic_editor_form_layout.set_current_decks()
        self.within_note_editor_tab.basic_editor_form_layout.set_current_decks()

    def get_copy_mode(self) -> CopyModeType:
        return self.selected_editor_type or COPY_MODE_ACROSS_NOTES

    def get_copy_definition(self) -> Union[CopyDefinition, None]:
        if self.selected_editor_type == COPY_MODE_ACROSS_NOTES:
            basic_editor = self.across_notes_editor_tab.basic_editor_form_layout
            field_to_field_editor = self.across_notes_editor_tab.get_field_to_field_editor()
            field_to_variable_editor = self.across_notes_editor_tab.get_field_to_variable_editor()
            # select_card_by has been validated in check_fields()
            select_card_by = cast(
                SelectCardByType, self.across_notes_editor_tab.card_select_cbox.currentText()
            )
            across_copy_definition: CopyDefinition = {
                "definition_name": self.definition_name.text(),
                "copy_into_note_types": basic_editor.note_type_target_cbox.currentText(),
                "only_copy_into_decks": basic_editor.decks_limit_multibox.currentText(),
                "copy_on_sync": basic_editor.copy_on_sync_checkbox.isChecked(),
                "copy_on_add": basic_editor.copy_on_add_checkbox.isChecked(),
                "copy_on_review": basic_editor.copy_on_review_checkbox.isChecked(),
                "field_to_field_defs": field_to_field_editor.get_field_to_field_defs(),
                "field_to_variable_defs": field_to_variable_editor.get_field_to_variable_defs(),
                "copy_from_cards_query": (
                    self.across_notes_editor_tab.card_query_text_layout.get_text()
                ),
                "sort_by_field": self.across_notes_editor_tab.sort_by_field_cbox.currentText(),
                "select_card_by": select_card_by,
                "select_card_count": self.across_notes_editor_tab.card_select_count.text(),
                "select_card_separator": self.across_notes_editor_tab.card_select_separator.text(),
                "copy_mode": COPY_MODE_ACROSS_NOTES,
                "across_mode_direction": self.across_notes_editor_tab.get_selected_direction(),
            }
            return across_copy_definition
        elif self.selected_editor_type == COPY_MODE_WITHIN_NOTE:
            basic_editor = self.within_note_editor_tab.basic_editor_form_layout
            field_to_field_editor = self.within_note_editor_tab.get_field_to_field_editor()
            within_copy_definition: CopyDefinition = {
                "definition_name": self.definition_name.text(),
                "copy_into_note_types": basic_editor.note_type_target_cbox.currentText(),
                "only_copy_into_decks": basic_editor.decks_limit_multibox.currentText(),
                "copy_on_sync": basic_editor.copy_on_sync_checkbox.isChecked(),
                "copy_on_add": basic_editor.copy_on_add_checkbox.isChecked(),
                "copy_on_review": basic_editor.copy_on_review_checkbox.isChecked(),
                "field_to_variable_defs": [],
                "field_to_field_defs": field_to_field_editor.get_field_to_field_defs(),
                "copy_mode": COPY_MODE_WITHIN_NOTE,
                "across_mode_direction": None,
                "copy_from_cards_query": None,
                "sort_by_field": None,
                "select_card_by": "None",
                "select_card_count": None,
                "select_card_separator": None,
            }
            return within_copy_definition
        return None
