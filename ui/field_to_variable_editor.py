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
    QLineEdit,
    QFormLayout,
    QPushButton,
    QGridLayout,
    QCheckBox,
    Qt,
    qtmajor,
)

from ..configuration import ALL_FIELD_TO_VARIABLE_PROCESS_NAMES

if qtmajor > 5:
    QFrameStyledPanel = QFrame.Shape.StyledPanel
    QFrameShadowRaised = QFrame.Shadow.Raised
else:
    QFrameStyledPanel = QFrame.StyledPanel
    QFrameShadowRaised = QFrame.Raised

from .edit_extra_processing_dialog import EditExtraProcessingWidget
from .interpolated_text_edit import InterpolatedTextEditLayout
from ..logic.interpolate_fields import (
    BASE_NOTE_MENU_DICT,
    NOTE_ID,
    CARD_IVL,
    CARD_TYPE,
    intr_format,
)

from .add_model_options_to_dict import add_model_options_to_dict


class CopyFieldToVariableEditor(QWidget):
    """
    Class for editing a list of variables to generate from fields.
    Shows the list of current field-to-variable definitions. Add button for adding new definitions is at the bottom.
    Remove button for removing definitions is at the top-right of each definition.
    """

    def __init__(self, parent, copy_definition):
        super().__init__(parent)
        self.fields_to_variable_defs = copy_definition.get("field_to_variable_defs", [])
        self.selected_copy_from_model = mw.col.models.by_name(copy_definition.get("copy_into_note_type"))

        self.copy_from_menu_options_dict = BASE_NOTE_MENU_DICT.copy()
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

        self.add_new_button = QPushButton("Add another fields-to-variable definition")
        self.bottom_form.addRow("", self.add_new_button)
        self.add_new_button.clicked.connect(self.add_new_definition)

        self.copy_field_inputs = []

        # There has to be at least one definition so initialize with one
        if len(self.fields_to_variable_defs) == 0:
            self.add_new_definition()
        else:
            for index, copy_field_to_field_definition in enumerate(self.fields_to_variable_defs):
                self.add_copy_field_row(index, copy_field_to_field_definition)

    def add_new_definition(self):
        new_definition = {
            "copy_into_variable": "",
            "copy_from_text": "",
        }
        self.fields_to_variable_defs.append(new_definition)
        self.add_copy_field_row(len(self.fields_to_variable_defs) - 1, new_definition)

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

        copy_field_inputs_dict = {}

        # Variable name
        variable_name_field = QLineEdit()
        copy_field_inputs_dict["copy_into_variable"] = variable_name_field
        row_form.addRow("Variable name", variable_name_field)
        with suppress(KeyError):
            variable_name_field.setText(copy_field_to_variable_definition["copy_into_variable"])

        # Copy from field
        copy_from_text_layout = InterpolatedTextEditLayout(
            label="Destination fields' content to store in the variable",
            options_dict=BASE_NOTE_MENU_DICT.copy(),
            description=f"""<ul>
        <li>Reference the source notes' fields with  {intr_format('Field Name')}.</li>
        <li>Right-click to select a  {intr_format('Field Name')} to paste</li>
        <li>There are many other data values you can use, such as the {intr_format(NOTE_ID)}, {intr_format(CARD_IVL)}, {intr_format(CARD_TYPE)} etc.</li>
        </ul>"""
        )
        copy_field_inputs_dict["copy_from_text"] = copy_from_text_layout

        row_form.addRow(copy_from_text_layout)

        copy_from_text_layout.update_options(self.copy_from_menu_options_dict)
        with suppress(KeyError):
            copy_from_text_layout.set_text(copy_field_to_variable_definition["copy_from_text"])

        # Extra processing
        process_chain_widget = EditExtraProcessingWidget(
            self,
            self.copy_definition,
            copy_field_to_variable_definition,
            ALL_FIELD_TO_VARIABLE_PROCESS_NAMES,
        )
        copy_field_inputs_dict["process_chain"] = process_chain_widget
        row_form.addRow("Extra processing", process_chain_widget)

        # Remove
        remove_button = QPushButton("Delete")

        self.copy_field_inputs.append(copy_field_inputs_dict)

        def remove_row():
            for widget in [
                variable_name_field,
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
            self.remove_definition(copy_field_to_variable_definition, copy_field_inputs_dict)

        remove_button.clicked.connect(remove_row)
        row_form.addRow("", remove_button)

    def remove_definition(self, definition, inputs_dict):
        """
        Removes the selected field-to-field definition and input dict.
        """
        self.fields_to_variable_defs.remove(definition)
        self.copy_field_inputs.remove(inputs_dict)

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

    def set_selected_copy_into_model(self, model):
        self.selected_copy_from_model = model
        self.update_copy_from_options_dict()
        for copy_field_inputs in self.copy_field_inputs:
            copy_field_inputs["copy_from_text"].update_options(self.copy_from_menu_options_dict)

    def update_field_target_options(self, field_target_cbox):
        """
        Updates the options in the "Note field to copy into" dropdown box.
        """
        if self.selected_copy_from_model is None:
            return

        previous_text = field_target_cbox.currentText()
        previous_text_in_new_options = False
        # Clear will unset the current selected text
        field_target_cbox.clear()
        field_target_cbox.addItem("-")
        for field_name in mw.col.models.field_names(self.selected_copy_from_model["name"]):
            if field_name == previous_text:
                previous_text_in_new_options = True
            field_target_cbox.addItem(field_name)

        # Reset the selected text, if the new options still include it
        if previous_text_in_new_options:
            field_target_cbox.setCurrentText(previous_text)

    def update_copy_from_options_dict(self):
        """
        Updates the raw options dict used for the "Define content for variable" TextEdit right-click menu.
        The raw dict is used for validating the text in the TextEdit.
        """
        field_names_by_model_dict = BASE_NOTE_MENU_DICT.copy()

        if self.selected_copy_from_model is not None:
            add_model_options_to_dict(
                model_name=self.selected_copy_from_model["name"],
                model_id=self.selected_copy_from_model["id"],
                target_dict=field_names_by_model_dict,
            )

        self.copy_from_menu_options_dict = field_names_by_model_dict
