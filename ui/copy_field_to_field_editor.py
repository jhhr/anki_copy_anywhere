from contextlib import suppress

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
    QFormLayout,
    QPushButton,
    QGridLayout,
    QCheckBox,
    Qt,
    qtmajor,
)

if qtmajor > 5:
    QFrameStyledPanel = QFrame.Shape.StyledPanel
    QFrameShadowRaised = QFrame.Shadow.Raised
else:
    QFrameStyledPanel = QFrame.StyledPanel
    QFrameShadowRaised = QFrame.Raised

from ..configuration import (
    COPY_MODE_WITHIN_NOTE,
    COPY_MODE_ACROSS_NOTES,
    ALL_FIELD_TO_FIELD_PROCESS_NAMES,
    CopyDefinition,
)

from .add_model_options_to_dict import add_model_options_to_dict
from .add_intersecting_model_field_options_to_dict import add_intersecting_model_field_options_to_dict, \
    get_intersecting_model_fields
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


def get_variable_names_from_copy_definition(copy_definition: CopyDefinition) -> dict:
    variable_menu_dict = {}
    for variable_def in copy_definition.get("field_to_variable_defs", []):
        variable_name = variable_def["copy_into_variable"]
        if variable_name is not None:
            variable_menu_dict[variable_name] = intr_format(variable_name)
    return variable_menu_dict


def get_new_base_dict(copy_mode):
    if copy_mode == COPY_MODE_WITHIN_NOTE:
        return DESTINATION_NOTE_MENU_DICT.copy()
    return DESTINATION_NOTE_MENU_DICT | BASE_NOTE_MENU_DICT


class CopyFieldToFieldEditor(QWidget):
    """
    Class for editing the list of fields to copy from and fields to copy into.
    Shows the list of current field-to-field definitions. Add button for adding new definitions is at the bottom.
    Remove button for removing definitions is at the top-right of each definition.
    """

    def __init__(self, parent, copy_definition, copy_mode):
        super().__init__(parent)
        self.field_to_field_defs = copy_definition.get("field_to_field_defs", [])
        self.copy_definition = copy_definition
        self.copy_mode = copy_mode
        clean_model_names = copy_definition.get("copy_into_note_types", "").strip('""').split('", "')
        self.selected_copy_into_models = list(
            filter(None, [mw.col.models.by_name(model_name) for model_name in clean_model_names]))
        self.intersecting_fields = get_intersecting_model_fields(self.selected_copy_into_models)

        self.copy_from_menu_options_dict = get_new_base_dict(copy_mode)
        self.intersecting_fields = []
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
            "copy_from_text": "",
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
        row_form.addRow("Destination note field", field_target_cbox)
        self.update_field_target_options(field_target_cbox)
        with suppress(KeyError):
            field_target_cbox.setCurrentText(copy_field_to_field_definition["copy_into_note_field"])

        across = self.copy_mode == COPY_MODE_ACROSS_NOTES
        # Copy from field
        copy_from_text_layout = InterpolatedTextEditLayout(
            label="Source fields' content that will replace the field",
            options_dict=get_new_base_dict(self.copy_mode),
            description=f"""<ul>
        <li>Reference any {'source' if across else ""} notes field with
            {intr_format('Field Name')}.</li>
        {f'''<li>Reference any destination note fields with
            {intr_format(f'{DESTINATION_PREFIX}Field Name')}, including the current target</li>
        <li>Referencing the destination field by name will use the value from the source
            notes!</li>''' if across else ""}
        <li>Right-click to select a {intr_format('Field Name')} to paste</li>
        <li>There are many other data values you can use, such as the
            {intr_format(NOTE_ID)}, {intr_format(CARD_IVL)}, {intr_format(CARD_TYPE)} etc.</li>
        </ul>"""
        )
        copy_field_inputs_dict["copy_from_text"] = copy_from_text_layout

        row_form.addRow(copy_from_text_layout)

        copy_from_text_layout.update_options(self.copy_from_menu_options_dict)
        with suppress(KeyError):
            copy_from_text_layout.set_text(copy_field_to_field_definition["copy_from_text"])

        copy_if_empty = QCheckBox("Only copy into field, if it's empty")
        copy_field_inputs_dict["copy_if_empty"] = copy_if_empty
        row_form.addRow("", copy_if_empty)
        with suppress(KeyError):
            copy_if_empty.setChecked(copy_field_to_field_definition["copy_if_empty"])
            
        copy_on_unfocus = QCheckBox("Copy on unfocusing the field in the note editor")
        copy_field_inputs_dict["copy_on_unfocus"] = copy_on_unfocus
        row_form.addRow("", copy_on_unfocus)
        with suppress(KeyError):
            copy_on_unfocus.setChecked(copy_field_to_field_definition.get("copy_on_unfocus", False))

        process_chain_widget = EditExtraProcessingWidget(
            self,
            self.copy_definition,
            copy_field_to_field_definition,
            ALL_FIELD_TO_FIELD_PROCESS_NAMES,
        )
        copy_field_inputs_dict["process_chain"] = process_chain_widget
        row_form.addRow("Extra processing", process_chain_widget)

        # Remove
        remove_button = QPushButton("Delete")

        self.copy_field_inputs.append(copy_field_inputs_dict)

        def remove_row():
            for widget in [
                field_target_cbox,
                copy_if_empty,
                copy_on_unfocus,
                remove_button,
                process_chain_widget,
            ]:
                widget.deleteLater()
                row_form.removeWidget(widget)
                widget = None
            for layout in [
                copy_from_text_layout
            ]:
                for i in range(0, layout.count()):
                    layout.itemAt(i).widget().deleteLater()
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
            copy_field_definition = {
                "copy_into_note_field": copy_field_inputs["copy_into_note_field"].currentText(),
                "copy_from_text": copy_field_inputs["copy_from_text"].get_text(),
                "copy_if_empty": copy_field_inputs["copy_if_empty"].isChecked(),
                "copy_on_unfocus": copy_field_inputs["copy_on_unfocus"].isChecked(),
                "process_chain": copy_field_inputs["process_chain"].get_process_chain(),
            }
            field_to_field_defs.append(copy_field_definition)
        return field_to_field_defs

    def set_selected_copy_into_models(self, models):
        self.selected_copy_into_models = models
        self.update_copy_from_options_dict()
        for copy_field_inputs in self.copy_field_inputs:
            self.update_field_target_options(copy_field_inputs["copy_into_note_field"])
            copy_field_inputs["copy_from_text"].update_options(self.copy_from_menu_options_dict)

    def update_field_target_options(self, field_target_cbox):
        """
        Updates the options in the "Note field to copy into" dropdown box.
        """
        if not self.selected_copy_into_models:
            return

        previous_text = field_target_cbox.currentText()
        previous_text_in_new_options = False
        # Clear will unset the current selected text
        field_target_cbox.clear()
        field_target_cbox.addItem("-")
        if len(self.selected_copy_into_models) > 1:
            # intersecting fields should be set
            if not self.intersecting_fields:
                self.intersecting_fields = get_intersecting_model_fields(self.selected_copy_into_models)
            for field_name in self.intersecting_fields:
                field_target_cbox.addItem(field_name)
        else:
            model = self.selected_copy_into_models[0]
            for field_name in mw.col.models.field_names(model):
                if field_name == previous_text:
                    previous_text_in_new_options = True
                field_target_cbox.addItem(field_name)

        # Reset the selected text, if the new options still include it
        if previous_text_in_new_options:
            field_target_cbox.setCurrentText(previous_text)

    def update_copy_from_options_dict(self):
        """
        Updates the raw options dict used for the "Define what to copy from" TextEdit right-click menu.
        The raw dict is used for validating the text in the TextEdit.
        """
        options_dict = get_new_base_dict(self.copy_mode)
        variables_dict = get_variable_names_from_copy_definition(self.copy_definition)
        if variables_dict:
            options_dict[VARIABLES_KEY] = variables_dict

        cur_model_names = [model["name"] for model in self.selected_copy_into_models]

        if self.copy_mode == COPY_MODE_WITHIN_NOTE:
            # If there are multiple models, add the intersecting fields only
            if len(self.selected_copy_into_models) > 1:
                self.intersecting_fields = get_intersecting_model_fields(self.selected_copy_into_models)
                add_intersecting_model_field_options_to_dict(
                    models=self.selected_copy_into_models,
                    target_dict=options_dict,
                    intersecting_fields=self.intersecting_fields
                )
            elif len(self.selected_copy_into_models) == 1:
                # Otherwise only add the single model as the target
                model = self.selected_copy_into_models[0]
                add_model_options_to_dict(model["name"], model["id"], options_dict)
        else:
            # In ACROSS_NOTES modes, add fields from all models
            models = mw.col.models.all_names_and_ids()
            for model in models:
                # The destination note type will be a special case that goes 1 level deeper
                # Essentially including this means you can do within-note copying too,
                # though the idea is to be mixing any source and any destination fields into
                # a single destination field
                if model.name in cur_model_names:
                    add_model_options_to_dict(
                        f'(Destination) {model.name}',
                        model.id,
                        options_dict,
                        DESTINATION_PREFIX
                    )
                # Remember that the source note fields should also be added for the same note type!
                add_model_options_to_dict(model.name, model.id, options_dict)

        self.copy_from_menu_options_dict = options_dict
