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

from .add_intersecting_model_field_options_to_dict import (
    get_intersecting_model_fields,
    add_intersecting_model_field_options_to_dict,
)
from .required_text_input import RequiredLineEdit
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
        clean_model_names = (
            copy_definition.get("copy_into_note_types", "").strip('""').split('", "')
        )
        self.selected_copy_into_models = list(
            filter(
                None,
                [mw.col.models.by_name(model_name) for model_name in clean_model_names],
            )
        )
        self.intersecting_fields = get_intersecting_model_fields(
            self.selected_copy_into_models
        )

        self.copy_from_menu_options_dict = BASE_NOTE_MENU_DICT.copy()
        self.update_copy_from_options_dict()

        self.copy_definition = copy_definition

        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.middle_grid = QGridLayout()
        self.middle_grid.setColumnMinimumWidth(0, 400)
        self.middle_grid.setColumnMinimumWidth(1, 50)

        self.bottom_form = QFormLayout()

        self.add_new_button = QPushButton("Use variables")
        self.add_new_button.clicked.connect(self.show_editor)

        self.copy_field_inputs = []

        # There has to be at least one definition so initialize with one
        if len(self.fields_to_variable_defs) == 0:
            self.vbox.addWidget(self.add_new_button)
        else:
            self.add_editor_layouts()
            for index, copy_field_to_variable_definition in enumerate(
                self.fields_to_variable_defs
            ):
                self.add_copy_field_row(index, copy_field_to_variable_definition)

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
        variable_name_field = RequiredLineEdit(is_required=True)
        variable_name_field.setPlaceholderText(
            f"Example name = MyVariable --> Usage: {intr_format('MyVariable')}"
        )
        copy_field_inputs_dict["copy_into_variable"] = variable_name_field
        row_form.addRow("<h4>Variable name</h4>", variable_name_field)
        with suppress(KeyError):
            variable_name_field.setText(
                copy_field_to_variable_definition["copy_into_variable"]
            )
            variable_name_field.update_required_style()

        # Copy from field
        copy_from_text_layout = InterpolatedTextEditLayout(
            is_required=True,
            label="<h4>Trigger note's fields' content to store in the variable</h4>",
            options_dict=BASE_NOTE_MENU_DICT.copy(),
            description=f"""<ul>
        <li>Reference the trigger note's fields with  {intr_format('Field Name')}.</li>
        <li>Right-click to select a  {intr_format('Field Name')} to paste</li>
        <li>There are many other data values you can use, such as the {intr_format(NOTE_ID)}, {intr_format(CARD_IVL)}, {intr_format(CARD_TYPE)} etc.</li>
        </ul>""",
        )
        copy_field_inputs_dict["copy_from_text"] = copy_from_text_layout

        row_form.addRow(copy_from_text_layout)

        copy_from_text_layout.update_options(self.copy_from_menu_options_dict)
        with suppress(KeyError):
            copy_from_text_layout.set_text(
                copy_field_to_variable_definition["copy_from_text"]
            )

        # Extra processing
        process_chain_widget = EditExtraProcessingWidget(
            self,
            self.copy_definition,
            copy_field_to_variable_definition,
            ALL_FIELD_TO_VARIABLE_PROCESS_NAMES,
        )
        copy_field_inputs_dict["process_chain"] = process_chain_widget
        row_form.addRow(process_chain_widget)

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
            for layout in [copy_from_text_layout]:
                for i in range(0, layout.count()):
                    layout.itemAt(i).widget().deleteLater()
                layout.deleteLater()
            self.middle_grid.removeWidget(frame)
            self.remove_definition(
                copy_field_to_variable_definition, copy_field_inputs_dict
            )

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

    def set_selected_copy_into_models(self, models):
        self.selected_copy_into_models = models
        self.update_copy_from_options_dict()
        for copy_field_inputs in self.copy_field_inputs:
            copy_field_inputs["copy_from_text"].update_options(
                self.copy_from_menu_options_dict
            )

    def update_copy_from_options_dict(self):
        """
        Updates the raw options dict used for the "Define content for variable" TextEdit right-click menu.
        The raw dict is used for validating the text in the TextEdit.
        """
        field_names_by_model_dict = BASE_NOTE_MENU_DICT.copy()

        if len(self.selected_copy_into_models) > 1:
            # If there are multiple models, add the intersecting fields only
            self.intersecting_fields = get_intersecting_model_fields(
                self.selected_copy_into_models
            )
            add_intersecting_model_field_options_to_dict(
                models=self.selected_copy_into_models,
                target_dict=field_names_by_model_dict,
                intersecting_fields=self.intersecting_fields,
            )
        elif len(self.selected_copy_into_models) == 1:
            model = self.selected_copy_into_models[0]
            add_model_options_to_dict(
                model_name=model["name"],
                model_id=model["id"],
                target_dict=field_names_by_model_dict,
            )

        self.copy_from_menu_options_dict = field_names_by_model_dict
