import re
from contextlib import suppress
from typing import Union

# noinspection PyUnresolvedReferences
from aqt import mw
# noinspection PyUnresolvedReferences
from aqt.qt import (
    QWidget,
    QFormLayout,
    QComboBox,
    QLabel,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QGridLayout,
    QVBoxLayout,
    QFont,
    QToolTip,
    QPoint,
    Qt,
    qtmajor,
)
# noinspection PyUnresolvedReferences
from aqt.utils import tooltip

from .list_input import ListInputWidget
from ..configuration import CopyDefinition

if qtmajor > 5:
    from .multi_combo_box import MultiComboBoxQt6 as MultiComboBox
else:
    from .multi_combo_box import MultiComboBoxQt5 as MultiComboBox

from ..configuration import (
    CopyFieldToField,
    CopyFieldToVariable,
    KanaHighlightProcess,
    RegexProcess,
    get_regex_process_label,
    FontsCheckProcess,
    get_fonts_check_process_label,
    KanjiumToJavdejongProcess,
    NEW_PROCESS_DEFAULTS,
    KANJIUM_TO_JAVDEJONG_PROCESS,
    REGEX_PROCESS,
    FONTS_CHECK_PROCESS,
    KANA_HIGHLIGHT_PROCESS,
    MULTIPLE_ALLOWED_PROCESS_NAMES,
)

if qtmajor > 5:
    WindowModal = Qt.WindowModality.WindowModal
else:
    WindowModal = Qt.WindowModal


class ClickableLabel(QLabel):
    def __init__(self, text, tooltip_text, parent=None):
        super().__init__(f'{text} (?)', parent)
        self.tooltip_text = tooltip_text
        self.setFont(QFont('SansSerif', 10))

    def mousePressEvent(self, event):
        # Show tooltip near the label when clicked
        QToolTip.showText(self.mapToGlobal(QPoint(0, self.height())), self.tooltip_text)

    def setLabelText(self, text):
        self.setText(f'{text} (?)')


class KanjiumToJavdejongProcessDialog(QDialog):
    def __init__(self, parent, process: KanjiumToJavdejongProcess):
        super().__init__(parent)
        self.process = process

        self.description = """
        Convert a field containing pitch accents in the Kanjium format into to the JavdeJong format.
        If the field doesn't contain Kanjium format pitch accents, nothing is done.
        """
        self.form = QFormLayout()
        self.setWindowModality(WindowModal)
        self.setLayout(self.form)

        self.top_label = QLabel(self.description)
        self.form.addRow(self.top_label)

        self.delimiter_field = QLineEdit()
        self.form.addRow("Delimiter between multiple pitch accents", self.delimiter_field)

        with suppress(KeyError): self.delimiter_field.setText(self.process["delimiter"])

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
            "name": KANJIUM_TO_JAVDEJONG_PROCESS,
            "delimiter": self.delimiter_field.text(),
        }
        self.accept()


def validate_regex(dialog):
    try:
        re.compile(dialog.regex_field.text())
        dialog.regex_error_display.setText("")
    except re.error as e:
        dialog.regex_error_display.setText(f"Error: {e}")
        return False
    return True


REGEX_FLAGS_DESCRIPTION = """
ASCII - A: Make \\w, \\W, \\b, \\B, \\d, \\D, \\s and \\S match only ASCII characters.<br/>
IGNORECASE - I: Perform case-insensitive matching.<br/>
VERBOSE - X: Write regex on multiple lines with whitespace and comments.<br/>
MULTILINE - M: Make ^ and $ match the start/end of each line.<br/>
DOTALL - S: Make . match any character, including newlines. Use to match across multiple lines.<br/>
"""

class RegexProcessDialog(QDialog):
    def __init__(self, parent, process: RegexProcess):
        super().__init__(parent)
        self.process = process

        self.description = """
        Basic regex processing step that replaces the text that matches the regex with the replacement.
        """
        self.form = QFormLayout()
        self.setWindowModality(WindowModal)
        self.setLayout(self.form)

        self.top_label = QLabel(self.description)
        self.form.addRow(self.top_label)

        self.regex_field = QLineEdit()
        self.form.addRow("Regex", self.regex_field)
        self.regex_field.textChanged.connect(lambda: validate_regex(self))

        self.regex_error_display = QLabel()
        self.regex_error_display.setStyleSheet("color: red;")
        self.form.addRow("", self.regex_error_display)

        self.replacement_field = QLineEdit()
        self.form.addRow("Replacement", self.replacement_field)

        self.flags_field = MultiComboBox()
        self.flags_field.addItems([
            "ASCII",
            "IGNORECASE",
            "VERBOSE",
            "MULTILINE",
            "DOTALL",
        ])
        regex_label = ClickableLabel("Flags", REGEX_FLAGS_DESCRIPTION, self)
        self.form.addRow(regex_label, self.flags_field)

        with suppress(KeyError): self.regex_field.setText(self.process["regex"])
        with suppress(KeyError): self.replacement_field.setText(self.process["replacement"])
        with suppress(KeyError): self.flags_field.setCurrentText(self.process["flags"])

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
            "name": REGEX_PROCESS,
            "regex": self.regex_field.text(),
            "replacement": self.replacement_field.text(),
            "flags": self.flags_field.currentText(),
        }
        self.accept()


class FontsCheckProcess(QDialog):
    def __init__(self, parent, process: FontsCheckProcess):
        super().__init__(parent)
        self.process = process

        self.description = """
        For the given text, go through all the characters and return the fonts for which every character has an entry in the JSON file for.
        The JSON file is intended be something pre-generated from a script that checks which fonts support which characters.
        """
        self.form = QFormLayout()
        self.setWindowModality(WindowModal)
        self.setLayout(self.form)

        self.top_label = QLabel(self.description)
        self.form.addRow(self.top_label)

        self.fonts_dict_file_field = QLineEdit()
        self.form.addRow("Fonts dict JSON file", self.fonts_dict_file_field)
        self.form.addRow("", QLabel("""<small>Provide the file name only, e.g. 'fonts_by_char.json'.
        <br/>
        The file is assumed to be in your Anki collection.media folder.
        <br/>
        The content should be <code>{"char": ["font1", "font2", ...], "char2": ...}</code>
        </small>"""))

        self.limit_to_fonts_field = ListInputWidget()
        self.form.addRow("Limit to fonts", self.limit_to_fonts_field)
        self.form.addRow("", QLabel("""<small>
        (Optional) A list of font file names (without the file ending) to limit the output to.
        <br/>
        You can add multiple fonts at once inputting a single item of comma separated values
        </small>"""))

        self.regex_field = QLineEdit()
        self.form.addRow("Char limit", self.regex_field)
        self.regex_field.textChanged.connect(lambda: validate_regex(self))
        self.form.addRow("", QLabel("""<small>(Optional) Regex used to limit the characters checked.
        <br/>
        When using regex your dictionary should contain an "all_fonts" key that contains all possible fonts.
        <br/>
        When all characters are excluded, the output will either the limit_to_fonts or all_fonts.
        <br/>
        If neither are provided, an empty string is returned.
        <br/>
        You probably want this to be a character range
        <br/>
        e.g. <code>[a-z]</code> or <code>[\u4E00-\u9FFF]</code>.
        </small>"""))

        self.regex_error_display = QLabel()
        self.regex_error_display.setStyleSheet("color: red;")
        self.form.addRow("", self.regex_error_display)

        with suppress(KeyError): self.fonts_dict_file_field.setText(self.process["fonts_dict_file"])
        with suppress(KeyError):
            for font in self.process["limit_to_fonts"]:
                self.limit_to_fonts_field.add_item(font)
        with suppress(KeyError): self.regex_field.setText(self.process["character_limit_regex"])

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
            "name": FONTS_CHECK_PROCESS,
            "fonts_dict_file": self.fonts_dict_file_field.text(),
            "limit_to_fonts": self.limit_to_fonts_field.get_items(),
            "character_limit_regex": self.regex_field.text(),
        }
        self.accept()


KANA_HIGHLIGHT_DESCRIPTION = """
Kana highlight processing takes in kanji text that has furigana.
It then bolds the furigana that corresponds to the kanji text, and removes the kanji
leaving only the kana.
The kanji, onyomi and kunyomi fields are gotten from the destination note type.
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
            "name": KANA_HIGHLIGHT_PROCESS,
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
    def __init__(
            self,
            parent,
            copy_definition: CopyDefinition,
            field_to_x_def: Union[CopyFieldToField, CopyFieldToVariable],
            allowed_process_names: list[str],
    ):
        super().__init__(parent)
        self.field_to_x_def = field_to_x_def
        self.allowed_process_names = allowed_process_names
        self.copy_definition = copy_definition
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.process_dialogs = []
        self.remove_row_funcs = []
        try:
            self.process_chain = field_to_x_def["process_chain"]
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
        for process in self.allowed_process_names:
            if (process not in currently_active_processes
                    or process in MULTIPLE_ALLOWED_PROCESS_NAMES):
                self.add_process_chain_button.addItem(process)

    def remove_process(self, process, process_dialog):
        self.process_chain.remove(process)
        process_dialog.deleteLater()
        self.process_dialogs.remove(process_dialog)
        self.update_process_chain()

    def update_process_chain(self, ):
        self.field_to_x_def["process_chain"] = self.process_chain
        self.init_options_to_process_combobox()

        for index, process in enumerate(self.process_chain):
            self.add_process_row(index, process)

    def get_process_chain(self):
        return self.process_chain

    def add_process_row(self, index, process):
        process_dialog, get_process_name = self.get_process_dialog_and_name(process)

        if process_dialog is None:
            return

        self.process_dialogs.append(process_dialog)

        # By setting the name into a box layout where we'll allow it expand
        # its empty space rightward also pushing the buttons there to the
        # edge
        hbox = QHBoxLayout()
        self.middle_grid.addLayout(hbox, index, 1)

        process_label = ClickableLabel(get_process_name(process), process_dialog.description, self)
        hbox.addStretch(1)
        hbox.addWidget(process_label)

        def process_dialog_exec():
            if process_dialog.exec():
                for i, cur_process in enumerate(self.process_chain):
                    if cur_process == process:
                        self.process_chain[i] = process_dialog.process
                # Remake the whole grid
                for func in self.remove_row_funcs:
                    func()
                self.remove_row_funcs = []
                self.update_process_chain()
                return 0
            return -1

        # Edit
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda: process_dialog_exec())
        self.middle_grid.addWidget(edit_button, index, 2)

        # Remove
        remove_button = QPushButton("Delete")

        def remove_row_ui():
            for widget in [process_label, edit_button, remove_button]:
                widget.deleteLater()
                self.middle_grid.removeWidget(widget)

        self.remove_row_funcs.append(remove_row_ui)

        def remove_row():
            # Remake the whole grid
            for func in self.remove_row_funcs:
                func()
            self.remove_row_funcs = []
            self.remove_process(process, process_dialog)

        remove_button.clicked.connect(remove_row)
        self.middle_grid.addWidget(remove_button, index, 4)

    def add_process(self, process_name):
        if process_name in ["-", "", None]:
            return
        new_process = NEW_PROCESS_DEFAULTS[process_name]
        if new_process is None:
            return
        self.add_process_row(len(self.process_chain), new_process)
        # Append after calling add row, since this increases the length of the process chain!
        self.process_chain.append(new_process)
        self.update_process_chain()

    def get_process_dialog_and_name(self, process):
        try:
            process_name = process["name"]
        except KeyError:
            tooltip(f"Error: Process name not found in process: {process}")
            return None, ""
        if process_name == KANA_HIGHLIGHT_PROCESS:
            with suppress(KeyError):
                note_type = self.copy_definition["copy_into_note_type"]
            return KanaHighlightProcessDialog(
                self,
                process,
                note_type
            ), get_fonts_check_process_label
        if process_name == REGEX_PROCESS:
            return RegexProcessDialog(self, process), get_regex_process_label
        if process_name == FONTS_CHECK_PROCESS:
            return FontsCheckProcess(self, process), lambda: FONTS_CHECK_PROCESS
        if process_name == KANJIUM_TO_JAVDEJONG_PROCESS:
            return KanjiumToJavdejongProcessDialog(self, process), lambda: KANJIUM_TO_JAVDEJONG_PROCESS

        return None, ""
