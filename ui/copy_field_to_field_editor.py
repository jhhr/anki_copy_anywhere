from contextlib import suppress
from typing import Optional, TypedDict, cast
from aqt import mw

from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QLabel,
    QFormLayout,
    QPushButton,
    QGridLayout,
    QCheckBox,
    qtmajor,
)

if qtmajor > 5:
    QFrameStyledPanel = QFrame.Shape.StyledPanel
    QFrameShadowRaised = QFrame.Shadow.Raised
else:
    QFrameStyledPanel = QFrame.StyledPanel  # type: ignore
    QFrameShadowRaised = QFrame.Raised  # type: ignore

from ..configuration import (
    COPY_MODE_WITHIN_NOTE,
    COPY_MODE_ACROSS_NOTES,
    ALL_FIELD_TO_FIELD_PROCESS_NAMES,
    CopyDefinition,
    CopyFieldToField,
    DirectionType,
    CopyModeType,
    DIRECTION_SOURCE_TO_DESTINATIONS,
    DIRECTION_DESTINATION_TO_SOURCES,
    get_variable_names_from_copy_definition,
)

from .multi_combo_box import MultiComboBox
from .grouped_combo_box import GroupedComboBox
from .add_model_options_to_dict import add_model_options_to_dict
from .add_intersecting_model_field_options_to_dict import (
    add_intersecting_model_field_options_to_dict,
    get_intersecting_model_fields,
)
from .edit_extra_processing_dialog import EditExtraProcessingWidget
from .interpolated_text_edit import InterpolatedTextEditLayout
from ..logic.interpolate_fields import (
    BASE_NOTE_MENU_DICT,
    DESTINATION_PREFIX,
    VARIABLES_KEY,
    DESTINATION_NOTE_MENU_DICT,
    NOTE_ID,
    CARD_IVL,
    CARD_TYPE,
    intr_format,
)


def get_new_base_dict(copy_mode: CopyModeType) -> dict:
    if copy_mode == COPY_MODE_WITHIN_NOTE:
        return DESTINATION_NOTE_MENU_DICT.copy()
    return DESTINATION_NOTE_MENU_DICT | BASE_NOTE_MENU_DICT


class FieldInputsDict(TypedDict):
    copy_into_note_field: GroupedComboBox
    target_note_field_label: QLabel
    copy_from_text_label: QLabel
    copy_from_text: InterpolatedTextEditLayout
    copy_if_empty: QCheckBox
    copy_on_unfocus_when_edit: QCheckBox
    copy_on_unfocus_when_add: QCheckBox
    copy_on_unfocus_trigger_label: QLabel
    copy_on_unfocus_trigger_field: MultiComboBox
    process_chain: EditExtraProcessingWidget


class CopyFieldToFieldEditor(QWidget):
    """
    Class for editing the list of fields to copy from and fields to copy into.
    Shows the list of current field-to-field definitions. Add button for adding new definitions is
    at the bottom.
    Remove button for removing definitions is at the top-right of each definition.
    """

    def __init__(
        self,
        parent,
        copy_definition: Optional[CopyDefinition],
        copy_mode: CopyModeType,
    ):
        super().__init__(parent)
        if copy_definition is None:
            self.field_to_field_defs = []
            field_to_file_defs = []
        else:
            self.field_to_field_defs = copy_definition.get("field_to_field_defs", [])
            field_to_file_defs = copy_definition.get("field_to_file_defs", [])
        self.copy_definition = copy_definition
        self.copy_mode = copy_mode
        self.across_mode_direction = (
            copy_definition.get("across_mode_direction", DIRECTION_DESTINATION_TO_SOURCES)
            if copy_definition
            else DIRECTION_DESTINATION_TO_SOURCES
        )
        clean_model_names = (
            (copy_definition.get("copy_into_note_types", "").strip('""').split('", "'))
            if copy_definition
            else []
        )
        self.selected_copy_into_models = list(
            filter(
                None,
                [mw.col.models.by_name(model_name) for model_name in clean_model_names],
            )
        )
        self.intersecting_fields = get_intersecting_model_fields(self.selected_copy_into_models)

        self.copy_from_menu_options_dict = get_new_base_dict(copy_mode)
        self.update_copy_from_options_dict()

        self.copy_definition = copy_definition

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

        self.copy_field_inputs: list[FieldInputsDict] = []

        # Most copy definitions copy to note fields, so
        # Initialize with one definition, if there are none, and there are no field-to-file defs
        if len(self.field_to_field_defs) == 0 and len(field_to_file_defs) == 0:
            self.add_new_definition()
        elif len(self.field_to_field_defs) > 0:
            for index, copy_field_to_field_definition in enumerate(self.field_to_field_defs):
                self.add_copy_field_row(index, copy_field_to_field_definition)

    def add_new_definition(self):
        new_definition: CopyFieldToField = {
            "copy_into_note_field": "",
            "copy_from_text": "",
            "copy_if_empty": False,
            "copy_on_unfocus_when_edit": False,
            "copy_on_unfocus_when_add": False,
            "copy_on_unfocus_trigger_field": "",
            "process_chain": [],
        }
        self.field_to_field_defs.append(new_definition)
        self.add_copy_field_row(len(self.field_to_field_defs) - 1, new_definition)

    def add_copy_field_row(self, index, copy_field_to_field_definition: CopyFieldToField):
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

        # Copy into field
        field_target_cbox = GroupedComboBox(
            placeholder_text="First select a trigger note type",
            is_required=True,
        )
        target_note_field_label = QLabel("<h3>Destination field (in the trigger note)</h3>")
        row_form.addRow(target_note_field_label, field_target_cbox)
        self.update_a_destination_field_target_cbox(field_target_cbox)
        with suppress(KeyError):
            field_target_cbox.setCurrentText(copy_field_to_field_definition["copy_into_note_field"])
            field_target_cbox.update_required_style()

        # Copy from field
        copy_from_text_label = QLabel(
            # Default to within mode texts, these only need to be modifed in across mode
            "<h3>Trigger note fields' content that will replace the field</h3>"
        )
        across = self.copy_mode == COPY_MODE_ACROSS_NOTES
        notes_word = "source notes'" if across else "note"
        copy_from_text_description = f"""<ul>
        <li>Reference any {notes_word} field with {intr_format('Field Name')}.</li>
        {f'''<li>Reference any destination fields with
            {intr_format(f'{DESTINATION_PREFIX}Field Name')}, including the current target</li>
        <li>Referencing the destination field by name will use the value from the source
            notes!</li>''' if across else ""}
        <li>Right-click to select a {intr_format('Field Name')} to paste</li>
        <li>There are many other data values you can use, such as the
            {intr_format(NOTE_ID)}, {intr_format(CARD_IVL)}, {intr_format(CARD_TYPE)} etc.</li>
        </ul>"""
        copy_from_text_layout = InterpolatedTextEditLayout(
            is_required=True,
            label=copy_from_text_label,
            options_dict=get_new_base_dict(self.copy_mode),
            description=copy_from_text_description,
        )

        row_form.addRow(copy_from_text_layout)

        copy_from_text_layout.update_options(self.copy_from_menu_options_dict)
        with suppress(KeyError):
            copy_from_text_layout.set_text(copy_field_to_field_definition["copy_from_text"])

        copy_if_empty = QCheckBox("Only copy into field, if it's empty")
        row_form.addRow("", copy_if_empty)
        with suppress(KeyError):
            copy_if_empty.setChecked(copy_field_to_field_definition["copy_if_empty"])

        copy_on_unfocus_when_edit = QCheckBox(
            "Copy on unfocusing the field when editing an existing note"
        )
        row_form.addRow("", copy_on_unfocus_when_edit)
        with suppress(KeyError):
            copy_on_unfocus_when_edit.setChecked(
                copy_field_to_field_definition.get("copy_on_unfocus_when_edit", False)
            )

        copy_on_unfocus_when_add = QCheckBox("Copy on unfocusing the field when adding a new note")
        row_form.addRow("", copy_on_unfocus_when_add)
        with suppress(KeyError):
            copy_on_unfocus_when_add.setChecked(
                copy_field_to_field_definition.get("copy_on_unfocus_when_add", False)
            )

        # When copying from source to destination, the trigger field should be one of the
        # trigger note's fields, so we'll need to show an extra checkbox to set that
        copy_on_unfocus_trigger_field = MultiComboBox(
            placeholder_text="First select a trigger note type",
        )
        copy_on_unfocus_trigger_label = QLabel("Copy on unfocus trigger field")
        row_form.addRow(copy_on_unfocus_trigger_label, copy_on_unfocus_trigger_field)
        # Options need to exist before we can set the initial text
        if self.copy_mode == COPY_MODE_ACROSS_NOTES:
            self.update_an_unfocus_trigger_field_cbox(copy_on_unfocus_trigger_field)
            self.update_direction_labels(self.across_mode_direction)
        with suppress(KeyError):
            copy_on_unfocus_trigger_field.setCurrentText(
                copy_field_to_field_definition["copy_on_unfocus_trigger_field"]
            )

        process_chain_widget = EditExtraProcessingWidget(
            self,
            self.copy_definition,
            copy_field_to_field_definition,
            ALL_FIELD_TO_FIELD_PROCESS_NAMES,
        )
        copy_field_inputs_dict: FieldInputsDict = {
            "copy_into_note_field": field_target_cbox,
            "target_note_field_label": target_note_field_label,
            "copy_from_text_label": copy_from_text_label,
            "copy_from_text": copy_from_text_layout,
            "copy_if_empty": copy_if_empty,
            "copy_on_unfocus_trigger_label": copy_on_unfocus_trigger_label,
            "copy_on_unfocus_trigger_field": copy_on_unfocus_trigger_field,
            "copy_on_unfocus_when_edit": copy_on_unfocus_when_edit,
            "copy_on_unfocus_when_add": copy_on_unfocus_when_add,
            "process_chain": process_chain_widget,
        }

        row_form.addRow(process_chain_widget)

        # Remove
        remove_button = QPushButton("Delete")

        self.copy_field_inputs.append(copy_field_inputs_dict)

        def remove_row():
            for widget in [
                field_target_cbox,
                copy_if_empty,
                copy_on_unfocus_when_edit,
                remove_button,
                process_chain_widget,
            ]:
                widget.deleteLater()
                row_form.removeWidget(widget)
            for layout in [copy_from_text_layout]:
                for i in range(0, layout.count()):
                    item = layout.itemAt(i)
                    if item and (item_widget := item.widget()):
                        item_widget.deleteLater()
                layout.deleteLater()
            self.middle_grid.removeWidget(frame)
            self.remove_definition(copy_field_to_field_definition, copy_field_inputs_dict)

        remove_button.clicked.connect(remove_row)
        row_form.addRow("", remove_button)

    def remove_definition(self, definition, inputs_dict):
        """
        Removes the selected field-to-field definition and input dict.
        """
        self.field_to_field_defs.remove(definition)
        self.copy_field_inputs.remove(inputs_dict)

    def get_field_to_field_defs(self):
        """
        Returns the list of field-to-field definitions from the current state of the editor.
        """
        field_to_field_defs = []
        for copy_field_inputs in self.copy_field_inputs:
            copy_on_unfocus_when_add = cast(
                QCheckBox, copy_field_inputs["copy_on_unfocus_when_add"]
            )
            copy_field_definition = {
                "copy_into_note_field": copy_field_inputs["copy_into_note_field"].currentText(),
                "copy_from_text": copy_field_inputs["copy_from_text"].get_text(),
                "copy_if_empty": copy_field_inputs["copy_if_empty"].isChecked(),
                "copy_on_unfocus_when_edit": (
                    copy_field_inputs["copy_on_unfocus_when_edit"].isChecked()
                ),
                "copy_on_unfocus_when_add": (
                    copy_on_unfocus_when_add.isChecked() and (copy_on_unfocus_when_add.isEnabled())
                ),
                "copy_on_unfocus_trigger_field": (
                    copy_field_inputs["copy_on_unfocus_trigger_field"].currentText()
                ),
                "process_chain": copy_field_inputs["process_chain"].get_process_chain(),
            }
            field_to_field_defs.append(copy_field_definition)
        return field_to_field_defs

    def set_selected_copy_into_models(self, models):
        self.selected_copy_into_models = models
        self.update_copy_from_options_dict()
        self.update_all_field_target_cboxes()

    def update_all_field_target_cboxes(self):
        for copy_field_inputs in self.copy_field_inputs:
            self.update_a_destination_field_target_cbox(copy_field_inputs["copy_into_note_field"])
            self.update_an_unfocus_trigger_field_cbox(
                copy_field_inputs["copy_on_unfocus_trigger_field"]
            )
            copy_field_inputs["copy_from_text"].update_options(self.copy_from_menu_options_dict)

    def update_direction_labels(self, direction: Optional[DirectionType]):
        self.across_mode_direction = direction

        if self.across_mode_direction == DIRECTION_DESTINATION_TO_SOURCES:
            copy_into_label_clarification = "in the trigger note"
            copy_from_text_clarification = "from the search"
        else:
            copy_into_label_clarification = "a searched note"
            copy_from_text_clarification = "from the trigger note"

        new_copy_into_label = f"<h3>Destination field ({copy_into_label_clarification})</h3>"
        new_copy_from_text_label = (
            f"<h4>Source fields' ({copy_from_text_clarification}) content that will replace the"
            " field</h4>"
        )

        for copy_field_inputs in self.copy_field_inputs:
            target_note_field_label = cast(QLabel, copy_field_inputs["target_note_field_label"])
            target_note_field_label.setText(new_copy_into_label)
            copy_from_text_label = cast(QLabel, copy_field_inputs["copy_from_text_label"])
            copy_from_text_label.setText(new_copy_from_text_label)
            # Copy on unfocus when adding is not allowed when source to destination, disable it
            copy_on_unfocus_when_add = cast(
                QCheckBox, copy_field_inputs["copy_on_unfocus_when_add"]
            )
            copy_on_unfocus_trigger_field = cast(
                MultiComboBox, copy_field_inputs["copy_on_unfocus_trigger_field"]
            )
            if self.across_mode_direction == DIRECTION_SOURCE_TO_DESTINATIONS:
                copy_on_unfocus_when_add.setDisabled(True)
                copy_on_unfocus_trigger_field.setDisabled(False)
            else:
                copy_on_unfocus_when_add.setDisabled(False)
                copy_on_unfocus_trigger_field.setDisabled(True)
            self.update_unfocus_trigger_field_placeholder(copy_on_unfocus_trigger_field)

    def update_unfocus_trigger_field_placeholder(
        self, unfocus_field_trigger_multibox: MultiComboBox
    ):
        """
        Updates the placeholder text of the "Copy on unfocus trigger field" dropdown box.
        """
        if self.across_mode_direction == DIRECTION_SOURCE_TO_DESTINATIONS:
            if len(self.selected_copy_into_models) > 0:
                unfocus_field_trigger_multibox.setPlaceholderText(
                    "Select note fields of the trigger note that will trigger the copy"
                )
            else:
                unfocus_field_trigger_multibox.setPlaceholderText(
                    "First select a trigger note type"
                )
        else:
            unfocus_field_trigger_multibox.setPlaceholderText("Not required in this mode")

    def update_an_unfocus_trigger_field_cbox(self, unfocus_field_trigger_multibox: MultiComboBox):
        """
        Updates the options in the "Copy on unfocus trigger field" dropdown box with the
        selected trigger note type's fields.
        """
        previous_text = unfocus_field_trigger_multibox.currentText()
        unfocus_field_trigger_multibox.clear()
        self.update_unfocus_trigger_field_placeholder(unfocus_field_trigger_multibox)
        if self.across_mode_direction == DIRECTION_SOURCE_TO_DESTINATIONS:
            if len(self.selected_copy_into_models) == 1:
                model = self.selected_copy_into_models[0]
                unfocus_field_trigger_multibox.addItems(
                    [f'"{field_name}"' for field_name in mw.col.models.field_names(model)]
                )
            elif len(self.selected_copy_into_models) > 1:
                unfocus_field_trigger_multibox.addItems(
                    [f'"{field_name}"' for field_name in self.intersecting_fields]
                )
        unfocus_field_trigger_multibox.setCurrentText(previous_text)
        unfocus_field_trigger_multibox.set_popup_and_box_width()

    def update_a_destination_field_target_cbox(self, field_target_cbox: GroupedComboBox):
        """
        Updates the options in the "Destination field" dropdown box.
        """
        previous_text = field_target_cbox.currentText()
        previous_text_in_new_options = False
        # Clear will unset the current selected text
        field_target_cbox.clear()
        # within note mode is by definition destination to source, because
        # the trigger note is both the source and the destination
        is_destination_to_sources = (
            self.copy_mode == COPY_MODE_WITHIN_NOTE
            or self.across_mode_direction == DIRECTION_DESTINATION_TO_SOURCES
        )
        if is_destination_to_sources:
            # Options are based on the selected trigger note types
            if len(self.selected_copy_into_models) > 1:
                # intersecting fields should be set
                if not self.intersecting_fields:
                    self.intersecting_fields = get_intersecting_model_fields(
                        self.selected_copy_into_models
                    )
                group_name = (
                    "Intersecting fields of"
                    f" {', '.join([model['name'] for model in self.selected_copy_into_models])}"
                )
                field_target_cbox.addGroup(group_name)
                for field_name in self.intersecting_fields:
                    field_target_cbox.addItemToGroup(group_name, field_name)
            elif len(self.selected_copy_into_models) == 1:
                model = self.selected_copy_into_models[0]
                field_target_cbox.addGroup(model["name"])
                for field_name in mw.col.models.field_names(model):
                    if field_name == previous_text:
                        previous_text_in_new_options = True
                    field_target_cbox.addItemToGroup(model["name"], field_name)
        else:
            # Options are based on the possible note types defined by the card_query search in
            # crossNotesCopyEditor, however we'll just make it all fields in all note types for now
            for model in mw.col.models.all():
                field_target_cbox.addGroup(model["name"])
                for field_name in mw.col.models.field_names(model):
                    if field_name == previous_text:
                        previous_text_in_new_options = True
                    field_target_cbox.addItemToGroup(model["name"], field_name)

        # Reset the selected text, if the new options still include it
        if previous_text_in_new_options:
            field_target_cbox.setCurrentText(previous_text)

        # Change placeholder text if we have some options
        if field_target_cbox.count() > 0:
            field_target_cbox.setPlaceholderText("Select a note field")
            field_target_cbox.setDisabled(False)
        else:
            field_target_cbox.setPlaceholderText("First select a trigger note type")
            field_target_cbox.setDisabled(True)

        field_target_cbox.set_popup_and_box_width()

    def update_copy_from_options_dict(self):
        """
        Updates the raw options dict used for the "Define what to copy from" TextEdit right-click
        menu. The raw dict is used for validating the text in the TextEdit.
        """
        options_dict = get_new_base_dict(self.copy_mode)
        variables_dict = get_variable_names_from_copy_definition(self.copy_definition)
        if variables_dict:
            options_dict[VARIABLES_KEY] = variables_dict

        trigger_model_names = [model["name"] for model in self.selected_copy_into_models]

        if self.copy_mode == COPY_MODE_WITHIN_NOTE:
            # If there are multiple models, add the intersecting fields only
            if len(self.selected_copy_into_models) > 1:
                self.intersecting_fields = get_intersecting_model_fields(
                    self.selected_copy_into_models
                )
                add_intersecting_model_field_options_to_dict(
                    models=self.selected_copy_into_models,
                    target_dict=options_dict,
                    intersecting_fields=self.intersecting_fields,
                )
            elif len(self.selected_copy_into_models) == 1:
                # Otherwise only add the single model as the target
                model = self.selected_copy_into_models[0]
                add_model_options_to_dict(model["name"], model["id"], options_dict)
        else:
            # In across notes modes, add fields from all models
            models = mw.col.models.all_names_and_ids()
            if self.across_mode_direction == DIRECTION_DESTINATION_TO_SOURCES:
                # One destination model, many source models
                for model in models:
                    # Only the trigger note models are potential destinations
                    # The destination note will get added twice, as a source and as a destination
                    if model.name in trigger_model_names:
                        add_model_options_to_dict(
                            f"(Destination) {model.name}",
                            model.id,
                            options_dict,
                            DESTINATION_PREFIX,
                        )
                    # But every model is a potential source
                    add_model_options_to_dict(model.name, model.id, options_dict)
            else:
                # Many destination models, one source model
                for model in models:
                    # Every model is a potential destination
                    add_model_options_to_dict(
                        f"(Destination) {model.name}",
                        model.id,
                        options_dict,
                        DESTINATION_PREFIX,
                    )
                    # Only the trigger note models are potential sources
                    # The source note will get added twice, as a source and once as a destination
                    if model.name in trigger_model_names:
                        add_model_options_to_dict(model.name, model.id, options_dict)

        self.copy_from_menu_options_dict = options_dict
