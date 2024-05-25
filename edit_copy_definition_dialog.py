from contextlib import suppress

from aqt import mw
from aqt.qt import (
    QDialog,
    QComboBox,
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
else:
    from .multi_combo_box import MultiComboBoxQt5 as MultiComboBox

    WindowModal = Qt.WindowModal


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


class EditCopyDefinitionDialog(QDialog):
    """
    Class for the dialog box to choose decks and note fields, has to be in a class so that the functions that update
    the dropdown boxes can access the text chosen in the other dropdown boxes.
    """

    def __init__(self, parent, copy_definition):
        super().__init__(parent)
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
        self.form = QFormLayout()
        self.setLayout(self.form)

        self.definition_name = QLineEdit()
        self.form.addRow("Name for this copy definition", self.definition_name)

        self.note_type_target_cbox = QComboBox()
        self.note_type_target_cbox.addItem("-")
        self.note_type_target_cbox.addItems(model_names_list)
        self.form.addRow("Note type to copy into", self.note_type_target_cbox)

        self.field_target_cbox = QComboBox()
        self.form.addRow("Note field to copy into", self.field_target_cbox)

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

        self.copy_from_field_cbox = GroupedComboBox()
        self.form.addRow("What field to copy from", self.copy_from_field_cbox)

        self.copy_if_empty = QCheckBox()
        self.form.addRow("Only copy into field, if it's empty", self.copy_if_empty)

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

        # Set the current text in the comboboxes to what we had in memory in the configuration (if we had something)
        if copy_definition:
            with suppress(KeyError): self.definition_name.setText(copy_definition["definition_name"])
            with suppress(KeyError): self.note_type_target_cbox.setCurrentText(copy_definition["copy_into_note_type"])
            with suppress(KeyError): self.update_note_target_field_items_and_target_limit_decks()
            with suppress(KeyError): self.field_target_cbox.setCurrentText(copy_definition["copy_into_note_field"])
            with suppress(KeyError): self.search_field_cbox.setCurrentText(copy_definition["search_with_field"])
            with suppress(KeyError): self.decks_limit_multibox.setCurrentText(copy_definition["only_copy_into_decks"])
            with suppress(KeyError): self.card_query_text.setText(copy_definition["copy_from_cards_query"])
            with suppress(KeyError): self.update_copy_from_field_items()
            with suppress(KeyError): self.copy_from_field_cbox.setCurrentText(copy_definition["copy_from_field"])
            with suppress(KeyError): self.copy_if_empty.setChecked(copy_definition["copy_if_empty"])
            with suppress(KeyError): self.card_select_cbox.setCurrentText(copy_definition["select_card_by"])
            with suppress(KeyError): self.card_select_count.setText(copy_definition["select_card_count"])
            with suppress(KeyError): self.card_select_separator.setText(copy_definition["select_card_separator"])

        # Connect signals
        self.note_type_target_cbox.currentTextChanged.connect(
            self.update_note_target_field_items_and_target_limit_decks)
        self.card_query_text.editingFinished.connect(self.update_copy_from_field_items)

        self.process_chain_widget = EditExtraProcessingWidget(
            self,
            copy_definition,
        )
        self.form.addRow(self.process_chain_widget)

        # Add Ok and Cancel buttons as QPushButtons
        self.ok_button = QPushButton("Save")
        self.close_button = QPushButton("Cancel")

        self.ok_button.clicked.connect(self.check_fields)
        self.close_button.clicked.connect(self.reject)

        self.bottom_grid = QGridLayout()
        self.bottom_grid.setColumnMinimumWidth(0, 150)
        self.bottom_grid.setColumnMinimumWidth(1, 150)
        self.bottom_grid.setColumnMinimumWidth(2, 150)
        self.form.addRow(self.bottom_grid)

        self.bottom_grid.addWidget(self.ok_button, 0, 0)
        self.bottom_grid.addWidget(self.close_button, 0, 2)

    def check_fields(self):
        if (self.note_type_target_cbox.currentText() == "-"
                or self.card_query_text.text() == ""
                or self.field_target_cbox.currentText() == "-"
                or self.card_select_cbox.currentText() == "-"
                or self.copy_from_field_cbox.currentText() == "-"):
            showInfo(
                "Please select a value for the required fields: Note type, Note field, Search field, Copy from field and Card selection.")
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

        self.field_target_cbox.clear()
        self.field_target_cbox.addItem("-")
        self.search_field_cbox.clear()
        self.search_field_cbox.addItem("-")
        for field_name in mw.col.models.field_names(model):
            self.field_target_cbox.addItem(field_name)
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

    def update_copy_from_field_items(self):
        models = mw.col.models.all_names_and_ids()

        self.copy_from_field_cbox.clear()
        self.copy_from_field_cbox.addItem("-")
        for model in models:
            self.copy_from_field_cbox.addGroup(model.name)
            for field_name in mw.col.models.field_names(mw.col.models.get(model.id)):
                self.copy_from_field_cbox.addItemToGroup(model.name, field_name)
