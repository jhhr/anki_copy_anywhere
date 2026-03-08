from contextlib import suppress
import uuid
from typing import Optional, TypedDict

from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QFormLayout,
    QPushButton,
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
from .code_edit_layout import CodeEditLayout
from .toggle_switch import ToggleSwitch
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
    text_mode_container: QWidget
    use_code: ToggleSwitch
    copy_as_code: CodeEditLayout
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

        # GUID-based variable UI tracking
        self.variable_ui_components: dict[str, dict] = {}  # Maps variable GUID to its UI components

        # Create variables container with vertical layout instead of grid
        self.variables_container_widget = QWidget()
        self.variables_layout = QVBoxLayout(self.variables_container_widget)
        self.variables_layout.setContentsMargins(0, 0, 0, 0)

        self.bottom_form = QFormLayout()

        self.add_new_button = QPushButton("Use variables")
        self.add_new_button.clicked.connect(self.show_editor)

        self.copy_field_inputs: list[VariableInputsDict] = []

        # Store callback entry for controlling visibility
        self.selected_model_callback = state.add_selected_model_callback(
            self.update_variables_options_dicts, is_visible=False
        )

        self.initialized = False

        # There has to be at least one definition so initialize with one
        if len(self.fields_to_variable_defs) == 0:
            self.vbox.addWidget(self.add_new_button)
        else:
            self.add_editor_layouts()
            for index, copy_field_to_variable_definition in enumerate(self.fields_to_variable_defs):
                self.add_copy_field_row(index, copy_field_to_variable_definition)

    def enable_callbacks(self):
        self.selected_model_callback.is_visible = True

    def disable_callbacks(self):
        self.selected_model_callback.is_visible = False

    def initialize_ui_state(self):
        """Perform expensive UI state initialization when component is first shown"""
        if self.initialized:
            return

        self.enable_callbacks()

        # Perform the expensive initialization
        self.update_variables_options_dicts()
        self.update_variable_names_in_state()

        self.initialized = True

    def add_editor_layouts(self):
        self.vbox.addWidget(self.variables_container_widget)
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
            "guid": str(uuid.uuid4()),
            "copy_into_variable": "",
            "copy_from_text": "",
            "copy_as_code": "",
            "use_code": False,
            "process_chain": [],
        }
        self.fields_to_variable_defs.append(new_definition)
        self.add_copy_field_row(len(self.fields_to_variable_defs) - 1, new_definition)

    def update_variable_names_in_state(self):
        self.state.update_variable_names(
            [inputs["copy_into_variable"].text() for inputs in self.copy_field_inputs]
        )

    def add_copy_field_row(self, index, copy_field_to_variable_definition):
        # Ensure definition has GUID
        if "guid" not in copy_field_to_variable_definition:
            copy_field_to_variable_definition["guid"] = str(uuid.uuid4())

        variable_guid = copy_field_to_variable_definition["guid"]

        # Create a QFrame
        frame = QFrame(self)
        frame.setFrameShape(QFrameStyledPanel)
        frame.setFrameShadow(QFrameShadowRaised)

        # Create a layout for the frame
        frame_layout = QVBoxLayout(frame)

        # Add the frame to the variables layout
        self.variables_layout.addWidget(frame)
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

        copy_from_text_description = f"""<ul>
        <li>Reference the trigger note's fields with  {intr_format('Field Name')}.</li>
        <li>Right-click to select a  {intr_format('Field Name')} to paste</li>
        <li>There are many other data values you can use, such as the {intr_format(NOTE_ID)},
 {intr_format(CARD_IVL)}, {intr_format(CARD_TYPE)} etc.</li>
        </ul>"""

        # Code mode toggle — placed first so it stays above whichever editor is shown
        use_code_checkbox = ToggleSwitch("Execute content as Python code")
        row_form.addRow(use_code_checkbox)

        # Copy from field — wrap in a container widget so it can be hidden when
        # the user switches to code mode without losing the entered text.
        text_mode_container = QWidget()
        text_mode_vbox = QVBoxLayout(text_mode_container)
        text_mode_vbox.setContentsMargins(0, 0, 0, 0)
        copy_from_text_layout = InterpolatedTextEditLayout(
            is_required=True,
            label="<h4>Trigger note's fields' content to store in the variable</h4>",
            options_dict=BASE_NOTE_MENU_DICT.copy(),
            description=copy_from_text_description,
        )
        text_mode_vbox.addLayout(copy_from_text_layout)
        row_form.addRow(text_mode_container)

        copy_from_text_layout.update_options(
            self.state.pre_query_menu_options_dict,
            self.state.pre_query_text_edit_validate_dict,
        )
        with suppress(KeyError):
            copy_from_text_layout.set_text(copy_field_to_variable_definition["copy_from_text"])

        # Code editor (hidden while text mode is active)
        copy_as_code_widget = CodeEditLayout(
            parent=self,
            options_dict=BASE_NOTE_MENU_DICT.copy(),
            is_required=False,
            label="<h4>Trigger note's fields' content to store in the variable</h4>",
            description=copy_from_text_description,
        )
        copy_as_code_widget.hide()
        row_form.addRow(copy_as_code_widget)

        copy_as_code_widget.update_options(
            self.state.pre_query_menu_options_dict,
            self.state.pre_query_text_edit_validate_dict,
        )
        with suppress(KeyError):
            saved_code = copy_field_to_variable_definition.get("copy_as_code", "")
            if saved_code:
                copy_as_code_widget.set_text(saved_code)

        # Apply initial mode and wire toggle
        initial_use_code = copy_field_to_variable_definition.get("use_code", False)
        if initial_use_code:
            use_code_checkbox.setChecked(True)
            text_mode_container.hide()
            copy_as_code_widget.show()

        def on_use_code_toggled(checked: bool):
            text_mode_container.setVisible(not checked)
            copy_as_code_widget.setVisible(checked)
            if checked and not copy_as_code_widget.get_text().strip():
                copy_as_code_widget.set_text(
                    f"return {repr(copy_from_text_layout.get_text())}"
                )

        use_code_checkbox.toggled.connect(on_use_code_toggled)

        # Extra processing
        process_chain_widget = EditExtraProcessingWidget(
            self,
            self.copy_definition,
            copy_field_to_variable_definition,
            ALL_FIELD_TO_VARIABLE_PROCESS_NAMES,
            state=self.state,
            is_variable_extra_processing=True,
        )
        row_form.addRow(process_chain_widget)

        # Remove
        remove_button = QPushButton("Delete")

        copy_field_inputs_dict: VariableInputsDict = {
            "copy_into_variable": variable_name_field,
            "copy_from_text": copy_from_text_layout,
            "text_mode_container": text_mode_container,
            "use_code": use_code_checkbox,
            "copy_as_code": copy_as_code_widget,
            "process_chain": process_chain_widget,
        }

        self.copy_field_inputs.append(copy_field_inputs_dict)

        def remove_row_ui():
            # Remove the entire variable widget from the layout
            self.variables_layout.removeWidget(frame)
            frame.deleteLater()

        # Store UI components for this variable GUID
        self.variable_ui_components[variable_guid] = {
            "widget": frame,
            "variable_name_field": variable_name_field,
            "copy_from_text": copy_from_text_layout,
            "process_chain": process_chain_widget,
            "remove_button": remove_button,
            "remove_ui_func": remove_row_ui,
        }

        def remove_row():
            # Use targeted removal without needing to rebuild entire UI
            self.remove_definition_by_guid(variable_guid)

        remove_button.clicked.connect(remove_row)
        row_form.addRow("", remove_button)

    def remove_definition_by_guid(self, variable_guid: str):
        """Remove a specific variable definition and its UI components by GUID without rebuilding the entire UI."""
        # Find and remove the definition from the list
        definition_to_remove = None
        for i, definition in enumerate(self.fields_to_variable_defs):
            if definition.get("guid") == variable_guid:
                definition_to_remove = definition
                self.fields_to_variable_defs.pop(i)
                break

        if definition_to_remove is None:
            return

        # Remove UI components
        if variable_guid in self.variable_ui_components:
            ui_components = self.variable_ui_components[variable_guid]
            ui_components["remove_ui_func"]()

            # Remove from tracking
            del self.variable_ui_components[variable_guid]

        # Remove from copy_field_inputs list
        for i, copy_field_inputs in enumerate(self.copy_field_inputs):
            if copy_field_inputs.get("copy_into_variable") == ui_components.get(
                "variable_name_field"
            ):
                self.copy_field_inputs.pop(i)
                break

        # Update variable names in state
        self.update_variable_names_in_state()

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
                "copy_as_code": copy_field_inputs["copy_as_code"].get_text(),
                "use_code": copy_field_inputs["use_code"].isChecked(),
                "process_chain": copy_field_inputs["process_chain"].get_process_chain(),
            }
            field_to_field_defs.append(copy_variable_definition)
        return field_to_field_defs

    def update_variables_options_dicts(self):
        for copy_field_inputs in self.copy_field_inputs:
            copy_field_inputs["copy_from_text"].update_options(
                self.state.pre_query_menu_options_dict,
                self.state.pre_query_text_edit_validate_dict,
            )
            copy_field_inputs["copy_as_code"].update_options(
                self.state.pre_query_menu_options_dict,
                self.state.pre_query_text_edit_validate_dict,
            )
