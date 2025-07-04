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
    CopyFieldToFile,
    CopyModeType,
    DIRECTION_SOURCE_TO_DESTINATIONS,
    DIRECTION_DESTINATION_TO_SOURCES,
)

from .multi_combo_box import MultiComboBox
from .edit_extra_processing_dialog import EditExtraProcessingWidget
from .interpolated_text_edit import InterpolatedTextEditLayout
from ..logic.interpolate_fields import (
    BASE_NOTE_MENU_DICT,
    DESTINATION_PREFIX,
    DESTINATION_NOTE_MENU_DICT,
    NOTE_ID,
    CARD_IVL,
    CARD_TYPE,
    intr_format,
)
from .edit_state import EditState


def get_new_base_dict(copy_mode: CopyModeType) -> dict:
    if copy_mode == COPY_MODE_WITHIN_NOTE:
        return DESTINATION_NOTE_MENU_DICT.copy()
    return DESTINATION_NOTE_MENU_DICT | BASE_NOTE_MENU_DICT


class FieldInputsDict(TypedDict):
    copy_into_filename: InterpolatedTextEditLayout
    copy_from_text_label: QLabel
    copy_from_text: InterpolatedTextEditLayout
    copy_if_empty: QCheckBox
    copy_on_unfocus_when_edit: QCheckBox
    copy_on_unfocus_when_add: QCheckBox
    copy_on_unfocus_trigger_label: QLabel
    copy_on_unfocus_trigger_field: MultiComboBox
    process_chain: EditExtraProcessingWidget


class CopyFieldToFileEditor(QWidget):
    """
    Class for editing the list of fields to copy from and write to a file
    Shows the list of current field-to-file definitions. Add button for adding new definitions is
    at the bottom.
    Remove button for removing definitions is at the top-right of each definition.
    """

    def __init__(
        self,
        parent,
        state: EditState,
        copy_definition: Optional[CopyDefinition],
        copy_mode: CopyModeType,
    ):
        super().__init__(parent)
        self.state = state
        self.field_to_file_defs = (
            copy_definition.get("field_to_file_defs", []) if copy_definition else []
        )
        self.copy_definition = copy_definition
        self.copy_mode = copy_mode
        self.copy_definition = copy_definition

        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.middle_grid = QGridLayout()
        self.middle_grid.setColumnMinimumWidth(0, 400)
        self.middle_grid.setColumnMinimumWidth(1, 50)
        self.vbox.addLayout(self.middle_grid)

        self.bottom_form = QFormLayout()
        self.vbox.addLayout(self.bottom_form)

        self.add_new_button = QPushButton("Add another field-to-file definition")
        self.bottom_form.addRow("", self.add_new_button)
        self.add_new_button.clicked.connect(self.add_new_definition)

        state.add_selected_model_callback(self.update_all_field_target_cboxes)
        state.add_copy_direction_callback(self.update_direction_labels)
        state.add_copy_direction_callback(self.update_all_field_target_cboxes)

        self.copy_field_inputs: list[FieldInputsDict] = []

        if len(self.field_to_file_defs) > 0:
            for index, copy_field_to_file_def in enumerate(self.field_to_file_defs):
                self.add_copy_field_row(index, copy_field_to_file_def)

    def add_new_definition(self):
        new_definition: CopyFieldToFile = {
            "copy_into_filename": "",
            "copy_from_text": "",
            "copy_if_empty": False,
            "copy_on_unfocus_when_edit": False,
            "copy_on_unfocus_when_add": False,
            "copy_on_unfocus_trigger_field": "",
            "process_chain": [],
        }
        self.field_to_file_defs.append(new_definition)
        self.add_copy_field_row(len(self.field_to_file_defs) - 1, new_definition)

    def add_copy_field_row(self, index, copy_field_to_field_definition: CopyFieldToFile):
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
        filename_label = QLabel("<h3>Filename to write to</h3>")
        filename_description = """<ul>
        <li>Reference the destination notes' field with {intr_format('Field Name')}.</li>
        <li>Source notes' fields are not included in the filename.</li>
        <li>The filename will be prefixed with _ if it doesn't start with it.</li>
        """
        filename_text_layout = InterpolatedTextEditLayout(
            is_required=True,
            options_dict=get_new_base_dict(self.copy_mode),
            label=filename_label,
            description=filename_description,
        )
        row_form.addRow(filename_text_layout)
        filename_text_layout.update_options(
            self.state.post_query_menu_options_dict,
            self.state.post_query_text_edit_validate_dict,
        )
        with suppress(KeyError):
            filename_text_layout.set_text(copy_field_to_field_definition["copy_into_filename"])

        # Copy from field
        copy_from_text_label = QLabel(
            # Default to within mode texts, these only need to be modifed in across mode
            "<h3>Trigger note fields' content to write to file</h3>"
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

        copy_from_text_layout.update_options(
            self.state.post_query_menu_options_dict,
            self.state.post_query_text_edit_validate_dict,
        )
        with suppress(KeyError):
            copy_from_text_layout.set_text(copy_field_to_field_definition["copy_from_text"])

        copy_if_empty = QCheckBox("Only write to file, if it doesn't exist")
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
            self.update_direction_labels(self.state.copy_direction)

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
            "copy_into_filename": filename_text_layout,
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
                copy_if_empty,
                copy_on_unfocus_when_edit,
                remove_button,
                process_chain_widget,
            ]:
                widget.deleteLater()
                row_form.removeWidget(widget)
            for layout in [filename_text_layout, copy_from_text_layout]:
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
        Removes the selected field-to-file definition and input dict.
        """
        self.field_to_file_defs.remove(definition)
        self.copy_field_inputs.remove(inputs_dict)

    def get_field_to_file_defs(self):
        """
        Returns the list of field-to-file definitions from the current state of the editor.
        """
        field_to_file_defs = []
        for copy_field_inputs in self.copy_field_inputs:
            copy_on_unfocus_when_add = cast(
                QCheckBox, copy_field_inputs["copy_on_unfocus_when_add"]
            )
            copy_field_definition = {
                "copy_into_filename": copy_field_inputs["copy_into_filename"].get_text(),
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
            field_to_file_defs.append(copy_field_definition)
        return field_to_file_defs

    def update_all_field_target_cboxes(self, _):
        for copy_field_inputs in self.copy_field_inputs:
            self.update_an_unfocus_trigger_field_cbox(
                copy_field_inputs["copy_on_unfocus_trigger_field"]
            )
            copy_field_inputs["copy_from_text"].update_options(
                self.state.post_query_menu_options_dict
            )
            copy_field_inputs["copy_into_filename"].update_options(
                self.state.post_query_menu_options_dict
            )

    def update_direction_labels(self, _):
        if self.state.copy_direction == DIRECTION_DESTINATION_TO_SOURCES:
            copy_from_text_clarification = "from the search"
        else:
            copy_from_text_clarification = "from the trigger note"

        new_copy_from_text_label = (
            f"<h4>Source fields' ({copy_from_text_clarification}) content that will replace the"
            " field</h4>"
        )

        for copy_field_inputs in self.copy_field_inputs:
            copy_from_text_label = cast(QLabel, copy_field_inputs["copy_from_text_label"])
            copy_from_text_label.setText(new_copy_from_text_label)
            # Copy on unfocus when adding is not allowed when source to destination, disable it
            copy_on_unfocus_when_add = cast(
                QCheckBox, copy_field_inputs["copy_on_unfocus_when_add"]
            )
            copy_on_unfocus_trigger_field = cast(
                MultiComboBox, copy_field_inputs["copy_on_unfocus_trigger_field"]
            )
            if self.state.copy_direction == DIRECTION_SOURCE_TO_DESTINATIONS:
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
        if (
            self.copy_mode == COPY_MODE_WITHIN_NOTE
            or self.state.copy_direction == DIRECTION_SOURCE_TO_DESTINATIONS
        ):
            if len(self.state.selected_models) > 0:
                unfocus_field_trigger_multibox.setPlaceholderText(
                    "Select note fields of the trigger note that will trigger the copy"
                )
            else:
                unfocus_field_trigger_multibox.setPlaceholderText(
                    "First select a trigger note type"
                )
        elif self.state.copy_direction == DIRECTION_DESTINATION_TO_SOURCES:
            unfocus_field_trigger_multibox.setPlaceholderText("Cannot be used in this mode")

    def update_an_unfocus_trigger_field_cbox(self, unfocus_field_trigger_multibox: MultiComboBox):
        """
        Updates the options in the "Copy on unfocus trigger field" dropdown box with the
        selected trigger note type's fields.
        """
        previous_text = unfocus_field_trigger_multibox.currentText()
        unfocus_field_trigger_multibox.clear()
        self.update_unfocus_trigger_field_placeholder(unfocus_field_trigger_multibox)
        if self.state.copy_direction == DIRECTION_SOURCE_TO_DESTINATIONS:
            if len(self.state.selected_models) == 1:
                model = self.state.selected_models[0]
                unfocus_field_trigger_multibox.addItems(
                    [f'"{field_name}"' for field_name in mw.col.models.field_names(model)]
                )
            elif len(self.state.selected_models) > 1:
                unfocus_field_trigger_multibox.addItems(
                    [f'"{field_name}"' for field_name in self.state.intersecting_fields]
                )
        unfocus_field_trigger_multibox.setCurrentText(previous_text)
        unfocus_field_trigger_multibox.set_popup_and_box_width()
