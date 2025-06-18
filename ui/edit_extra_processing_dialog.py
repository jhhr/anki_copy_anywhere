import re
from contextlib import suppress
from typing import Union, Optional, Callable, cast, Sequence

from aqt import mw

from aqt.qt import (
    QWidget,
    QFormLayout,
    QLabel,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QCheckBox,
    QLineEdit,
    QGridLayout,
    QVBoxLayout,
    QFont,
    QFontDatabase,
    QToolTip,
    QPoint,
    Qt,
    qtmajor,
)

from aqt.utils import tooltip

from .auto_resizing_text_edit import AutoResizingTextEdit
from .list_input import ListInputWidget
from .required_combobox import RequiredCombobox
from ..configuration import CopyDefinition
from .multi_combo_box import MultiComboBox

if qtmajor > 5:
    WindowModal = Qt.WindowModality.WindowModal
    QFixedFont = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    QAlignLeft = Qt.AlignmentFlag.AlignLeft
else:
    WindowModal = Qt.WindowModal  # type: ignore
    QFixedFont = QFontDatabase.systemFont(QFontDatabase.FixedFont)  # type: ignore
    QAlignLeft = Qt.AlignLeft  # type: ignore

from ..configuration import (
    AnyProcess,
    CopyFieldToField,
    CopyFieldToVariable,
    CopyFieldToFile,
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
from ..logic.kana_highlight import FuriReconstruct


class ClickableLabel(QLabel):
    def __init__(self, text, tooltip_text, parent=None):
        super().__init__(f"{text} (?)", parent)
        self.tooltip_text = tooltip_text
        self.setFont(QFont("SansSerif", 10))

    def mousePressEvent(self, event):
        # Show tooltip near the label when clicked
        QToolTip.showText(self.mapToGlobal(QPoint(0, self.height())), self.tooltip_text)

    def setLabelText(self, text):
        self.setText(f"{text} (?)")


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

        with suppress(KeyError):
            self.delimiter_field.setText(self.process["delimiter"])

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
        re.compile(dialog.regex_field.toPlainText())
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
        Basic regex processing step that replaces the text that matches the regex with the
        replacement.
        """
        self.form = QFormLayout()
        self.setWindowModality(WindowModal)
        self.setLayout(self.form)

        self.top_label = QLabel(self.description)
        self.form.addRow(self.top_label)

        self.regex_field = AutoResizingTextEdit(is_required=True)
        # Since this is code, set a mono font
        self.regex_field.setFont(QFixedFont)
        self.form.addRow("Regex", self.regex_field)
        self.regex_field.textChanged.connect(lambda: validate_regex(self))

        self.regex_error_display = QLabel()
        self.regex_error_display.setStyleSheet("color: red;")
        self.form.addRow("", self.regex_error_display)

        self.replacement_field = QLineEdit()
        self.form.addRow("Replacement", self.replacement_field)

        self.flags_field = MultiComboBox(placeholder_text="Select flags (optional)")
        self.flags_field.addItems([
            "ASCII",
            "IGNORECASE",
            "VERBOSE",
            "MULTILINE",
            "DOTALL",
        ])
        regex_label = ClickableLabel("Flags", REGEX_FLAGS_DESCRIPTION, self)
        self.form.addRow(regex_label, self.flags_field)

        with suppress(KeyError):
            self.regex_field.setPlainText(self.process["regex"])
        with suppress(KeyError):
            self.replacement_field.setText(self.process["replacement"])
        with suppress(KeyError):
            flags = self.process["flags"]
            if flags:
                self.flags_field.setCurrentText(flags)

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
            "regex": self.regex_field.toPlainText(),
            "replacement": self.replacement_field.text(),
            "flags": self.flags_field.currentText(),
        }
        self.accept()


class FontsCheckProcessDialog(QDialog):
    def __init__(self, parent, process: FontsCheckProcess):
        super().__init__(parent)
        self.process = process

        self.description = """
        For the given text, go through all the characters and return the fonts for which every
        character has an entry in the JSON file for.
        The JSON file is intended be something pre-generated from a script that checks which fonts
        support which characters.
        """
        self.form = QFormLayout()
        self.setWindowModality(WindowModal)
        self.setLayout(self.form)

        self.top_label = QLabel(self.description)
        self.form.addRow(self.top_label)

        self.fonts_dict_file_field = QLineEdit()
        self.form.addRow("Fonts dict JSON file", self.fonts_dict_file_field)
        self.form.addRow(
            "",
            QLabel("""<small>Provide the file name only, e.g. 'fonts_by_char.json'.
        <br/>
        The file is assumed to be in your Anki collection.media folder.
        <br/>
        The content should be <code>{"char": ["font1", "font2", ...], "char2": ...}</code>
        </small>"""),
        )

        self.limit_to_fonts_field = ListInputWidget()
        self.form.addRow("Limit to fonts", self.limit_to_fonts_field)
        self.form.addRow(
            "",
            QLabel("""<small>
        (Optional) A list of font file names (without the file ending) to limit the output to.
        <br/>
        You can add multiple fonts at once inputting a single item of comma separated values
        </small>"""),
        )

        self.regex_field = AutoResizingTextEdit()
        self.regex_field.setFont(QFixedFont)
        self.form.addRow("Char limit", self.regex_field)
        self.regex_field.textChanged.connect(lambda: validate_regex(self))
        self.form.addRow(
            "",
            QLabel("""<small>(Optional) Regex used to limit the characters checked.
        <br/>
        When using regex your dictionary should contain an "all_fonts" key that contains all
        possible fonts.
        <br/>
        When all characters are excluded, the output will either the limit_to_fonts or all_fonts.
        <br/>
        If neither are provided, an empty string is returned.
        <br/>
        You probably want this to be a character range
        <br/>
        e.g. <code>[a-z]</code> or <code>[\u4e00-\u9fff]</code>.
        </small>"""),
        )

        self.regex_error_display = QLabel()
        self.regex_error_display.setStyleSheet("color: red;")
        self.form.addRow("", self.regex_error_display)

        with suppress(KeyError):
            self.fonts_dict_file_field.setText(self.process["fonts_dict_file"])
        with suppress(KeyError):
            limit_to_fonts = self.process.get("limit_to_fonts")
            if limit_to_fonts:
                for font in limit_to_fonts:
                    self.limit_to_fonts_field.add_item(font)
        with suppress(KeyError):
            self.regex_field.setPlainText(self.process["character_limit_regex"])

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
            "character_limit_regex": self.regex_field.toPlainText(),
        }
        self.accept()


KANA_HIGHLIGHT_DESCRIPTION = """
Kana highlight processing takes in kanji text that has furigana.
It then bolds the furigana that corresponds to the kanji text, and removes the kanji
leaving only the kana.
The kanji, onyomi and kunyomi fields are gotten from the destination note type.
"""


class KanaHighlightProcessDialog(QDialog):
    def __init__(self, parent, process: KanaHighlightProcess, copy_into_note_types: Optional[str]):
        super().__init__(parent)
        self.process = process
        self.copy_into_note_types = copy_into_note_types

        self.description = KANA_HIGHLIGHT_DESCRIPTION
        self.form = QFormLayout()
        self.setWindowModality(WindowModal)
        self.setLayout(self.form)

        self.top_label = QLabel(self.description)
        self.form.addRow(self.top_label)

        self.kanji_field_cbox = RequiredCombobox(placeholder_text="Select field (optional)")
        self.form.addRow("Kanji field", self.kanji_field_cbox)

        self.return_type_cbox = RequiredCombobox(
            placeholder_text="Select return type (required)", is_required=True
        )
        self.return_type_cbox.addItems(["furigana", "furikanji", "kana_only"])
        self.return_type_cbox.setCurrentText("kana_only")
        self.form.addRow("Return type", self.return_type_cbox)

        self.assume_dictionary_form_checkbox = QCheckBox("Assume content is in dictionary form")
        self.form.addRow("", self.assume_dictionary_form_checkbox)

        self.wrap_readings_checkbox = QCheckBox(
            "Wrap readings in <on>, <kun>, <juk> and <oku> tags"
        )
        self.form.addRow("", self.wrap_readings_checkbox)

        self.merge_consecutive_tags_checkbox = QCheckBox("Merge consecutive tags")
        self.form.addRow("", self.merge_consecutive_tags_checkbox)

        self.update_combobox_options()

        with suppress(KeyError):
            self.kanji_field_cbox.setCurrentText(self.process.get("kanji_field"))
        with suppress(KeyError):
            self.return_type_cbox.setCurrentText(self.process.get("return_type"))
        with suppress(KeyError):
            self.assume_dictionary_form_checkbox.setChecked(
                self.process.get("assume_dictionary_form", False)
            )
        with suppress(KeyError):
            self.wrap_readings_checkbox.setChecked(self.process.get("wrap_readings_in_tags", False))
        with suppress(KeyError):
            self.merge_consecutive_tags_checkbox.setChecked(
                self.process.get("merge_consecutive_tags", False)
            )

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
        return_type = cast(FuriReconstruct, self.return_type_cbox.currentText())
        self.process = {
            "name": KANA_HIGHLIGHT_PROCESS,
            "kanji_field": self.kanji_field_cbox.currentText(),
            "return_type": return_type,
            "assume_dictionary_form": self.assume_dictionary_form_checkbox.isChecked(),
            "wrap_readings_in_tags": self.wrap_readings_checkbox.isChecked(),
            "merge_consecutive_tags": self.merge_consecutive_tags_checkbox.isChecked(),
        }
        self.accept()

    def update_combobox_options(self):
        if self.copy_into_note_types is None:
            return
        for note_type_name in self.copy_into_note_types.strip('""').split('", "'):
            note_type = mw.col.models.by_name(note_type_name)
            if note_type is None:
                continue
            for field_name in mw.col.models.field_names(note_type):
                self.kanji_field_cbox.addItem(field_name)


class EditExtraProcessingWidget(QWidget):

    def __init__(
        self,
        parent,
        copy_definition: Optional[CopyDefinition],
        field_to_x_def: Union[CopyFieldToField, CopyFieldToVariable, CopyFieldToFile],
        allowed_process_names: list[str],
    ):
        super().__init__(parent)
        self.field_to_x_def = field_to_x_def
        self.allowed_process_names = allowed_process_names
        self.copy_definition = copy_definition
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.process_dialogs: list[QDialog] = []
        self.remove_row_funcs: list[Callable[[], None]] = []
        try:
            self.process_chain = cast(list[AnyProcess], field_to_x_def["process_chain"])
        except KeyError:
            self.process_chain = []

        def make_grid():
            grid = QGridLayout()
            grid.setColumnMinimumWidth(0, 200)
            grid.setColumnMinimumWidth(1, 200)
            grid.setColumnMinimumWidth(2, 50)
            grid.setColumnMinimumWidth(3, 50)
            grid.setColumnMinimumWidth(4, 50)
            self.vbox.addLayout(grid)
            return grid

        left_vbox = QVBoxLayout()
        self.middle_grid = make_grid()
        self.middle_grid.addLayout(left_vbox, 0, 0, 1, 1, QAlignLeft)
        left_vbox.addWidget(QLabel("<h4>Extra processing</h4>"))

        for index, process in enumerate(self.process_chain):
            self.add_process_row(index, process)

        self.add_process_chain_button = RequiredCombobox(
            placeholder_text="Select process to add (optional)",
        )
        self.add_process_chain_button.setMaximumWidth(250)
        self.init_options_to_process_combobox()
        left_vbox.addWidget(self.add_process_chain_button)

    def init_options_to_process_combobox(self):
        currently_active_processes = [process["name"] for process in self.process_chain]

        self.add_process_chain_button.clear()
        # Add options not currently active to the combobox
        for process in self.allowed_process_names:
            if (
                process not in currently_active_processes
                or process in MULTIPLE_ALLOWED_PROCESS_NAMES
            ):
                self.add_process_chain_button.addItem(process)
        # Reconnect signal now that we're done calling addItem
        self.add_process_chain_button.currentTextChanged.connect(self.add_process)

    def remove_process(self, process, process_dialog):
        self.process_chain.remove(process)
        process_dialog.deleteLater()
        self.process_dialogs.remove(process_dialog)
        self.update_process_chain()

    def update_process_chain(
        self,
    ):
        # Disconnect signal to avoid calling add_process in an infinite loop
        # because init_options_to_process_combobox calls addItem which
        # triggers the currentTextChanged signal in the PlaceholderCombobox
        self.add_process_chain_button.currentTextChanged.disconnect(self.add_process)
        self.field_to_x_def["process_chain"] = cast(Sequence[AnyProcess], self.process_chain)
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
        self.add_process_chain_button.hidePopup()
        if not process_name:
            return
        new_process: AnyProcess = NEW_PROCESS_DEFAULTS[process_name]
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
            note_types = None
            with suppress(KeyError):
                if self.copy_definition:
                    note_types = self.copy_definition["copy_into_note_types"]
            return (
                KanaHighlightProcessDialog(self, process, note_types),
                lambda _: KANA_HIGHLIGHT_PROCESS,
            )
        if process_name == REGEX_PROCESS:
            return RegexProcessDialog(self, process), get_regex_process_label
        if process_name == FONTS_CHECK_PROCESS:
            return FontsCheckProcessDialog(self, process), get_fonts_check_process_label
        if process_name == KANJIUM_TO_JAVDEJONG_PROCESS:
            return (
                KanjiumToJavdejongProcessDialog(self, process),
                lambda _: KANJIUM_TO_JAVDEJONG_PROCESS,
            )

        return None, ""
