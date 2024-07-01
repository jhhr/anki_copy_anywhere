from contextlib import suppress

from aqt import mw
from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QLabel,
    QDialog,
    QComboBox,
    QScrollArea,
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

from .configuration import Config
from .copy_fields import SEARCH_FIELD_VALUE_PLACEHOLDER
from .edit_extra_processing_dialog import EditExtraProcessingWidget

if qtmajor > 5:
    from .multi_combo_box import MultiComboBoxQt6 as MultiComboBox

    WindowModal = Qt.WindowModality.WindowModal
    QFrameStyledPanel = QFrame.Shape.StyledPanel
    QFrameShadowRaised = QFrame.Shadow.Raised
else:
    from .multi_combo_box import MultiComboBoxQt5 as MultiComboBox

    WindowModal = Qt.WindowModal
    QFrameStyledPanel = QFrame.StyledPanel
    QFrameShadowRaised = QFrame.Raised

from PyQt6.QtGui import QGuiApplication


class ScrollableQDialog(QDialog):
    def __init__(self, parent=None, footer_layout=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.scrollArea = QScrollArea(self)
        self.layout.addWidget(self.scrollArea)
        self.scrollArea.setWidgetResizable(True)

        self.innerWidget = QWidget()
        self.scrollArea.setWidget(self.innerWidget)

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
        if group_name in self.groups:
            self.groups[group_name].append(item_name)
            self.items.append("  " + item_name)
            self.addItem("  " + item_name)
            index = self.findText("  " + item_name)
            self.model().setData(self.model().index(index, 0), False, Qt.ItemDataRole.UserRole + 1)  # Mark as item


class GroupedItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.data(Qt.ItemDataRole.UserRole + 1):  # Group
            option.font.setBold(True)
        else:  # Item
            option.font.setBold(False)
        QStyledItemDelegate.paint(self, painter, option, index)


def set_copy_from_options(copy_from_field_cbox):
    """
    Updates the options in the "What field to copy from" dropdown box.
    The options don't change depending on any input so this function is static.
    """
    models = mw.col.models.all_names_and_ids()

    copy_from_field_cbox.clear()
    copy_from_field_cbox.addItem("-")
    for model in models:
        copy_from_field_cbox.addGroup(model.name)
        for field_name in mw.col.models.field_names(mw.col.models.get(model.id)):
            copy_from_field_cbox.addItemToGroup(model.name, field_name)


class CopyFieldToFieldEditor(QWidget):
    """
    Class for editing the list of fields to copy from and fields to copy into.
    Shows the list of current field-to-field definitions. Add button for adding new definitions is at the bottom.
    Remove button for removing definitions is at the top-right of each definition.
    """

    def __init__(self, parent, copy_definition):
        super().__init__(parent)
        self.field_to_field_defs = copy_definition.get("field_to_field_defs", [])

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
            print(copy_field_to_field_definition["copy_into_note_field"])
            field_target_cbox.setCurrentText(copy_field_to_field_definition["copy_into_note_field"])

        # Copy from field
        copy_from_field_cbox = GroupedComboBox()
        copy_field_inputs_dict["copy_from_field"] = copy_from_field_cbox
        row_form.addRow("What field to copy from", copy_from_field_cbox)
        set_copy_from_options(copy_from_field_cbox)
        with suppress(KeyError):
            copy_from_field_cbox.setCurrentText(copy_field_to_field_definition["copy_from_field"])

        copy_if_empty = QCheckBox()
        copy_field_inputs_dict["copy_if_empty"] = copy_if_empty
        row_form.addRow("Only copy into field, if it's empty", copy_if_empty)
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
                "copy_from_field": copy_field_inputs["copy_from_field"].currentText(),
                "copy_if_empty": copy_field_inputs["copy_if_empty"].isChecked(),
                "process_chain": copy_field_inputs["process_chain"].get_process_chain(),
            }
            field_to_field_defs.append(copy_field_definition)
        return field_to_field_defs

    def set_selected_copy_into_model(self, model_name):
        self.selected_copy_into_model_name = model_name
        for copy_field_inputs in self.copy_field_inputs:
            self.update_field_target_options(copy_field_inputs["copy_into_note_field"])

    def update_field_target_options(self, field_target_cbox):
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
        self.main_layout = QVBoxLayout(self.innerWidget)
        self.setLayout(self.main_layout)
        self.form = QFormLayout()
        self.main_layout.addLayout(self.form)

        self.definition_name = QLineEdit()
        self.form.addRow("Name for this copy definition", self.definition_name)

        self.note_type_target_cbox = QComboBox()
        self.note_type_target_cbox.addItem("-")
        self.note_type_target_cbox.addItems(model_names_list)
        self.form.addRow("Note type to copy into", self.note_type_target_cbox)

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

        self.decks_limit_multibox = MultiComboBox()
        self.form.addRow("Deck to limit copying to (optional)", self.decks_limit_multibox)

        self.card_select_count = QLineEdit()
        self.card_select_count.setValidator(QIntValidator())
        self.card_select_count.setMaxLength(2)
        self.card_select_count.setFixedWidth(60)
        self.card_select_count.setText("1")
        self.form.addRow("Select multiple cards? (optional)", self.card_select_count)

        self.card_select_separator = QLineEdit()
        self.card_select_separator.setText(", ")
        self.form.addRow("Separator for multiple values (optional)", self.card_select_separator)

        self.bottom_vbox = QVBoxLayout()
        self.main_layout.addLayout(self.bottom_vbox)
        self.copy_fields_label = QLabel("Fields to copy from and to")
        self.field_to_field_editor = CopyFieldToFieldEditor(self, copy_definition)
        self.bottom_vbox.addWidget(self.copy_fields_label)
        self.bottom_vbox.addWidget(self.field_to_field_editor)

        # Set the current text in the combo boxes to what we had in memory in the configuration (if we had something)
        if copy_definition:
            with suppress(KeyError): self.definition_name.setText(copy_definition["definition_name"])
            with suppress(KeyError): self.note_type_target_cbox.setCurrentText(copy_definition["copy_into_note_type"])
            with suppress(KeyError): self.update_note_target_field_items_and_target_limit_decks()
            with suppress(KeyError): self.search_field_cbox.setCurrentText(copy_definition["search_with_field"])
            with suppress(KeyError): self.decks_limit_multibox.setCurrentText(copy_definition["only_copy_into_decks"])
            with suppress(KeyError): self.card_query_text.setText(copy_definition["copy_from_cards_query"])
            with suppress(KeyError): self.card_select_cbox.setCurrentText(copy_definition["select_card_by"])
            with suppress(KeyError): self.card_select_count.setText(copy_definition["select_card_count"])
            with suppress(KeyError): self.card_select_separator.setText(copy_definition["select_card_separator"])

        # Connect signals
        self.note_type_target_cbox.currentTextChanged.connect(
            self.update_note_target_field_items_and_target_limit_decks)


    def check_fields(self):
        show_error = False
        missing_copy_into_error = ""
        missing_copy_from_error = ""
        missing_card_query_error = ""
        missing_card_select_error = ""
        for field_to_field_definition in self.field_to_field_editor.get_field_to_field_defs():
            if field_to_field_definition["copy_into_note_field"] == "":
                missing_copy_into_error = "Copy into field cannot be empty."
                show_error = True
            if field_to_field_definition["copy_from_field"] == "":
                missing_copy_from_error = "Copy from field cannot be empty."
                show_error = True

        if self.card_query_text.text() == "":
            show_error = True
            missing_card_query_error = "Search query cannot be empty"
        if self.card_select_cbox.currentText() == "-":
            show_error = True
            missing_card_select_error = "Card selection method must be selected"
        if (show_error):
            showInfo(f"""Some required required fields are missing:
            {missing_copy_into_error if missing_copy_into_error else ""}
            {missing_copy_from_error if missing_copy_into_error else ""}
            {missing_card_query_error if self.card_query_text.text() == "" else ""}
            {missing_card_select_error if self.card_select_cbox.currentText() == "-" else ""}
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

    def update_note_target_field_items_and_target_limit_decks(self):
        """
        Updates the "Note field to copy into" and "Note field to search with" dropdown boxes
         according to choice made in the "Note type to copy into" dropdown box.
        """
        model = mw.col.models.by_name(self.note_type_target_cbox.currentText())
        if model is None:
            return

        self.field_to_field_editor.set_selected_copy_into_model(model["name"])

        self.search_field_cbox.clear()
        self.search_field_cbox.addItem("-")
        for field_name in mw.col.models.field_names(model):
            self.search_field_cbox.addItem(field_name)

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
