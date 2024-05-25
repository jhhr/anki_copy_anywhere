from contextlib import suppress

from aqt import mw
from aqt.qt import (
    QWidget,
    QFormLayout,
    QComboBox,
    QLabel,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QGridLayout,
    QVBoxLayout,
    QFont,
    QToolTip,
    QPoint,
    qtmajor,
    Qt,
)
from aqt.utils import tooltip

from .configuration import CopyDefinition, KanaHighlightProcess, Config
from .kana_highlight_process import KANA_HIGHLIGHT_PROCESS_NAME

if qtmajor > 5:
    WindowModal = Qt.WindowModality.WindowModal
else:
    WindowModal = Qt.WindowModal


class ClickableLabel(QLabel):
    def __init__(self, text, tooltip_text, parent=None):
        super().__init__(text, parent)
        self.tooltip_text = tooltip_text
        self.setFont(QFont('SansSerif', 10))

    def mousePressEvent(self, event):
        # Show tooltip near the label when clicked
        QToolTip.showText(self.mapToGlobal(QPoint(0, self.height())), self.tooltip_text)


KANA_HIGHLIGHT_DESCRIPTION = """
Kana highlight processing takes in kanji text that has furigana.
It then bolds the furigana that corresponds to the kanji text, and removes the kanji
leaving only the kana.
The kanji, onyomi and kunyomi fields are gotten from the original note type you are copying into.
"""


class KanaHighlightProcessDialog(QDialog):
    def __init__(self, parent, process: KanaHighlightProcess, copy_into_note_type):
        super().__init__(parent)
        self.process = process
        self.copy_into_note_type = copy_into_note_type

        self.description = KANA_HIGHLIGHT_DESCRIPTION
        self.form = QFormLayout()
        self.setWindowModality(WindowModal)
        self.setLayout(self.form)

        self.top_label = QLabel(self.description)
        self.form.addRow(self.top_label)

        self.onyomi_field_cbox = QComboBox()
        self.onyomi_field_cbox.addItem("-")
        self.form.addRow("Onyomi field name", self.onyomi_field_cbox)

        self.kunyomi_field_cbox = QComboBox()
        self.kunyomi_field_cbox.addItem("-")
        self.form.addRow("Kunyomi field name", self.kunyomi_field_cbox)

        self.kanji_field_cbox = QComboBox()
        self.kanji_field_cbox.addItem("-")
        self.form.addRow("Kanji field name", self.kanji_field_cbox)

        self.update_combobox_options()

        with suppress(KeyError): self.onyomi_field_cbox.setCurrentText(self.process["onyomi_field"])
        with suppress(KeyError): self.kunyomi_field_cbox.setCurrentText(self.process["kunyomi_field"])
        with suppress(KeyError): self.kanji_field_cbox.setCurrentText(self.process["kanji_field"])

        # Add Ok and Cancel buttons as QPushButtons
        self.ok_button = QPushButton("OK")
        self.close_button = QPushButton("Cancel")

        self.ok_button.clicked.connect(self.save_process)
        self.close_button.clicked.connect(self.reject)

        self.bottom_grid = QGridLayout()
        self.bottom_grid.setColumnMinimumWidth(0, 150)
        self.bottom_grid.setColumnMinimumWidth(1, 150)
        self.bottom_grid.setColumnMinimumWidth(2, 150)
        self.form.addRow(self.bottom_grid)

        self.bottom_grid.addWidget(self.ok_button, 0, 0)
        self.bottom_grid.addWidget(self.close_button, 0, 2)

    def save_process(self):
        self.process = {
            "name": KANA_HIGHLIGHT_PROCESS_NAME,
            "onyomi_field": self.onyomi_field_cbox.currentText(),
            "kunyomi_field": self.kunyomi_field_cbox.currentText(),
            "kanji_field": self.kanji_field_cbox.currentText(),
        }
        self.accept()

    def update_combobox_options(self):
        for field_name in mw.col.models.field_names(mw.col.models.by_name(self.copy_into_note_type)):
            self.onyomi_field_cbox.addItem(field_name)
            self.kunyomi_field_cbox.addItem(field_name)
            self.kanji_field_cbox.addItem(field_name)


class EditExtraProcessingWidget(QWidget):
    def __init__(self, parent, copydefinition: CopyDefinition):
        super().__init__(parent)
        self.copydefinition = copydefinition
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.process_dialogs = []
        try:
            self.process_chain = copydefinition["process_chain"]
        except KeyError:
            self.process_chain = []

        def make_grid():
            grid = QGridLayout()
            grid.setColumnMinimumWidth(0, 25)
            grid.setColumnMinimumWidth(1, 200)
            grid.setColumnMinimumWidth(2, 50)
            grid.setColumnMinimumWidth(3, 50)
            grid.setColumnMinimumWidth(4, 50)
            self.vbox.addLayout(grid)
            return grid

        self.middle_grid = make_grid()

        for index, process in enumerate(self.process_chain):
            self.add_process_row(index, process)

        self.form = QFormLayout()
        self.vbox.addLayout(self.form)
        self.add_process_chain_button = QComboBox()
        self.init_options_to_process_combobox()
        self.add_process_chain_button.currentTextChanged.connect(self.add_process)
        self.form.addRow("Add further processing?", self.add_process_chain_button)

    def init_options_to_process_combobox(self):
        currently_active_processes = [process["name"] for process in self.process_chain]

        self.add_process_chain_button.clear()
        self.add_process_chain_button.addItem("-")
        # Add options not currently active to the combobox
        for process in [KANA_HIGHLIGHT_PROCESS_NAME]:
            if process not in currently_active_processes:
                self.add_process_chain_button.addItem(process)

    def remove_process(self, index):
        self.process_chain.pop(index)
        self.process_dialogs[index].deleteLater()
        self.process_dialogs.pop(index)
        self.update_process_chain()

    def update_process_chain(self, ):
        self.copydefinition["process_chain"] = self.process_chain

        self.init_options_to_process_combobox()

        config = Config()
        config.load()
        config.update_definition_by_name(self.copydefinition["definition_name"], self.copydefinition)
        config.save()

    def add_process_row(self, index, process):
        process_dialog, process_name = self.get_process_dialog_and_name(process)

        if process_dialog is None:
            return

        self.process_dialogs.append(process_dialog)

        # By setting the name into a box layout where we'll allow it expand
        # its empty space rightward also pushing the buttons there to the
        # edge
        hbox = QHBoxLayout()
        self.middle_grid.addLayout(hbox, index, 1)

        process_label = ClickableLabel(process_name, process_dialog.description, self)
        hbox.addStretch(1)
        hbox.addWidget(process_label)

        def process_dialog_exec(index):
            if self.process_dialogs[index].exec():
                self.process_chain[index] = process_dialog.process
                self.update_process_chain()
                return 0
            return -1

        # Edit
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda: process_dialog_exec(index))
        self.middle_grid.addWidget(edit_button, index, 2)

        # Remove
        remove_button = QPushButton("Delete")

        def remove_row():
            for widget in [process_label, edit_button, remove_button]:
                widget.deleteLater()
                self.middle_grid.removeWidget(widget)
                widget = None
            self.remove_process(index)

        remove_button.clicked.connect(remove_row)
        self.middle_grid.addWidget(remove_button, index, 4)

    def add_process(self, process_name):
        if process_name in ["-", "", None]:
            return
        if process_name == KANA_HIGHLIGHT_PROCESS_NAME:
            new_process = {
                "name": process_name,
                "onyomi_field": '',
                "kunyomi_field": '',
                "kanji_field": '',
            }
            self.add_process_row(len(self.process_chain), new_process)
            # Append after calling add row, since this increases the length of the process chain!
            self.process_chain.append(new_process)
        self.update_process_chain()

    def get_process_dialog_and_name(self, process):
        try:
            process_name = process["name"]
        except KeyError:
            tooltip(f"Error:Process name not found in process: {process}")
            return None, ""
        if process_name == KANA_HIGHLIGHT_PROCESS_NAME:
            with suppress(KeyError):
                note_type = self.copydefinition["copy_into_note_type"]
            return KanaHighlightProcessDialog(
                self,
                process,
                note_type
            ), KANA_HIGHLIGHT_PROCESS_NAME
        return None, ""
