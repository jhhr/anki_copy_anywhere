from contextlib import suppress
from typing import Optional, TypedDict

from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QFormLayout,
    QPushButton,
    QGridLayout,
    qtmajor,
)

from .required_text_input import RequiredLineEdit
from ..configuration import ALL_FIELD_TO_VARIABLE_PROCESS_NAMES, CopyDefinition

if qtmajor > 5:
    QFrameStyledPanel = QFrame.Shape.StyledPanel
    QFrameShadowRaised = QFrame.Shadow.Raised
else:
    QFrameStyledPanel = QFrame.StyledPanel  # type: ignore
    QFrameShadowRaised = QFrame.Raised  # type: ignore

from .edit_extra_processing_dialog import EditExtraProcessingWidget
from .interpolated_text_edit import InterpolatedTextEditLayout
from ..logic.interpolate_fields import (
    BASE_NOTE_MENU_DICT,
    NOTE_ID,
    CARD_IVL,
    CARD_TYPE,
    intr_format,
)
from ..configuration import CopyFieldToVariable
from .edit_state import EditState


class VariableInputsDict(TypedDict):
    copy_into_variable: RequiredLineEdit
    copy_from_text: InterpolatedTextEditLayout
    process_chain: EditExtraProcessingWidget


class CopyFieldToVariableEditor(QWidget):
    """
    Class for editing a list of variables to generate from fields.
    Shows the list of current field-to-variable definitions. Add button for adding new definitions
    is at the bottom.
    Remove button for removing definitions is at the top-right of each definition.
    """

    def __init__(
        self,
        parent,
        state: EditState,
        copy_definition: Optional[CopyDefinition],
    ):
        super().__init__(parent)
        self.state = state
        self.fields_to_variable_defs: list[CopyFieldToVariable] = (
            copy_definition.get("field_to_variable_defs", []) if copy_definition else []
        )
        self.copy_definition = copy_definition

        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.middle_grid = QGridLayout()
        self.middle_grid.setColumnMinimumWidth(0, 400)
        self.middle_grid.setColumnMinimumWidth(1, 50)

        self.bottom_form = QFormLayout()

        self.add_new_button = QPushButton("Use variables")
        self.add_new_button.clicked.connect(self.show_editor)

        self.copy_field_inputs: list[VariableInputsDict] = []

        state.add_selected_model_callback(self.update_variables_options_dicts)

        # There has to be at least one definition so initialize with one
        if len(self.fields_to_variable_defs) == 0:
            self.vbox.addWidget(self.add_new_button)
        else:
            self.add_editor_layouts()
            for index, copy_field_to_variable_definition in enumerate(self.fields_to_variable_defs):
                self.add_copy_field_row(index, copy_field_to_variable_definition)

        self.update_variables_options_dicts(None)
        self.update_variable_names_in_state()

    def add_editor_layouts(self):
        self.vbox.addLayout(self.middle_grid)
        self.vbox.addLayout(self.bottom_form)
        self.add_new_button = QPushButton("Add another fields-to-variable definition")
        self.bottom_form.addRow("", self.add_new_button)
        self.add_new_button.clicked.connect(self.add_new_definition)

    def show_editor(self):
        self.vbox.removeWidget(self.add_new_button)
        self.add_new_button.deleteLater()
        self.add_editor_layouts()
        self.add_new_definition()

    def add_new_definition(self):
        new_definition: CopyFieldToVariable = {
            "copy_into_variable": "",
            "copy_from_text": "",
            "process_chain": [],
        }
        self.fields_to_variable_defs.append(new_definition)
        self.add_copy_field_row(len(self.fields_to_variable_defs) - 1, new_definition)

    def update_variable_names_in_state(self):
        self.state.update_variable_names(
            [inputs["copy_into_variable"].text() for inputs in self.copy_field_inputs]
        )

    def add_copy_field_row(self, index, copy_field_to_variable_definition):
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

        # Variable name
        variable_name_field = RequiredLineEdit(is_required=True)
        variable_name_field.setPlaceholderText(
            f"Example name = MyVariable --> Usage: {intr_format('MyVariable')}"
        )
        row_form.addRow("<h4>Variable name</h4>", variable_name_field)
        with suppress(KeyError):
            variable_name_field.setText(copy_field_to_variable_definition["copy_into_variable"])
            variable_name_field.update_required_style()

        variable_name_field.textChanged.connect(self.update_variable_names_in_state)

        # Copy from field
        copy_from_text_layout = InterpolatedTextEditLayout(
            is_required=True,
            label="<h4>Trigger note's fields' content to store in the variable</h4>",
            options_dict=BASE_NOTE_MENU_DICT.copy(),
            description=f"""<ul>
        <li>Reference the trigger note's fields with  {intr_format('Field Name')}.</li>
        <li>Right-click to select a  {intr_format('Field Name')} to paste</li>
        <li>There are many other data values you can use, such as the {intr_format(NOTE_ID)},
 {intr_format(CARD_IVL)}, {intr_format(CARD_TYPE)} etc.</li>
        </ul>""",
        )
        row_form.addRow(copy_from_text_layout)

        copy_from_text_layout.update_options(
            self.state.pre_query_menu_options_dict,
            self.state.pre_query_text_edit_validate_dict,
        )
        with suppress(KeyError):
            copy_from_text_layout.set_text(copy_field_to_variable_definition["copy_from_text"])

        # Extra processing
        process_chain_widget = EditExtraProcessingWidget(
            self,
            self.copy_definition,
            copy_field_to_variable_definition,
            ALL_FIELD_TO_VARIABLE_PROCESS_NAMES,
        )
        row_form.addRow(process_chain_widget)

        # Remove
        remove_button = QPushButton("Delete")

        copy_field_inputs_dict: VariableInputsDict = {
            "copy_into_variable": variable_name_field,
            "copy_from_text": copy_from_text_layout,
            "process_chain": process_chain_widget,
        }

        self.copy_field_inputs.append(copy_field_inputs_dict)

        def remove_row():
            for widget in [
                variable_name_field,
                remove_button,
                process_chain_widget,
            ]:
                widget.deleteLater()
                row_form.removeWidget(widget)
            for layout in [copy_from_text_layout]:
                for i in range(0, layout.count()):
                    item = layout.itemAt(i)
                    if item is not None and (item_widget := item.widget()):
                        item_widget.deleteLater()
                layout.deleteLater()
            self.middle_grid.removeWidget(frame)
            self.remove_definition(copy_field_to_variable_definition, copy_field_inputs_dict)

        remove_button.clicked.connect(remove_row)
        row_form.addRow("", remove_button)

    def remove_definition(self, definition, inputs_dict):
        """
        Removes the selected field-to-field definition and input dict.
        """
        self.fields_to_variable_defs.remove(definition)
        self.copy_field_inputs.remove(inputs_dict)
        self.update_variable_names_in_state()

    def get_field_to_variable_defs(self):
        """
        Returns the list of fields-to-variable definitions from the current state of the editor.
        """
        field_to_field_defs = []
        for copy_field_inputs in self.copy_field_inputs:
            copy_variable_definition = {
                "copy_into_variable": copy_field_inputs["copy_into_variable"].text(),
                "copy_from_text": copy_field_inputs["copy_from_text"].get_text(),
                "process_chain": copy_field_inputs["process_chain"].get_process_chain(),
            }
            field_to_field_defs.append(copy_variable_definition)
        return field_to_field_defs

    def update_variables_options_dicts(self, _):
        for copy_field_inputs in self.copy_field_inputs:
            copy_field_inputs["copy_from_text"].update_options(
                self.state.pre_query_menu_options_dict,
                self.state.pre_query_text_edit_validate_dict,
            )
