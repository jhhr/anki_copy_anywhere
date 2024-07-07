# noinspection PyUnresolvedReferences
from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QLabel,
    QDialog,
    QComboBox,
    QTabWidget,
    QSizePolicy,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QGridLayout,
    QCheckBox,
    QIntValidator,
    Qt,
    qtmajor,
)

from .pasteable_text_edit import PasteableTextEdit
from ..logic.interpolate_fields import (
    get_fields_from_text,
)


class InterpolatedTextEditLayout(QVBoxLayout):
    """
    Layout containing a PasteableTextEdit that allows for interpolation of fields.
    """

    def __init__(
            self,
            label: str = "",
            options_dict=None,
            parent=None,
            description: str = None,
            height: int = None,
    ):
        super().__init__(parent)
        # options dict is a 2-level dict
        # with menu group names as keys and a list of options as values
        if options_dict is None:
            options_dict = {}
        self.options_dict = options_dict
        # validation dict is 1-level dict with all possible fields as keys
        self.validate_dict = {}

        self.text_edit = PasteableTextEdit(options_dict=options_dict, height=height)
        self.error_label = QLabel()
        # Use red color for error label
        self.error_label.setStyleSheet("color: red;")
        # Connect text changed to validation
        self.text_edit.textChanged.connect(self.validate_text)
        main_label = QLabel(label)

        self.addWidget(main_label)

        if description:
            optional_description = QLabel(description)
            # Set description font size smaller
            optional_description.setStyleSheet("font-size: 10px;")
            self.addWidget(optional_description)

        self.addWidget(self.text_edit)
        self.addWidget(self.error_label)

        self.update_options(options_dict)

    def get_text(self):
        """Get current text from the text field."""
        return self.text_edit.toPlainText()

    def set_text(self, text):
        """Set the text in the text field."""
        self.text_edit.setText(text)

    def update_options(self, new_options_dict):
        """
        Updates the options in the "Define what to copy from" TextEdit right-click menu.
        """
        self.text_edit.clear_options()
        self.options_dict = new_options_dict
        self.validate_dict = {}

        for group_name, field_names in new_options_dict.items():
            for field in field_names:
                self.text_edit.add_option_to_group(group_name, field, f"{{{{{field}}}}}")
                self.validate_dict[field.lower()] = True

    def validate_text(self):
        """
         Validates text that's using {{}} syntax for note fields.
         Returns none if a source field is empty.
        """
        # Regex to pull out any words enclosed in double curly braces
        fields = get_fields_from_text(self.text_edit.toPlainText())

        invalid_fields = []
        # Validate that all fields are present in the dict
        for field in fields:
            try:
                self.validate_dict[field.lower()]
            except KeyError:
                invalid_fields.append(field)

        if len(invalid_fields) > 0:
            self.error_label.setText(f"Invalid fields: {', '.join(invalid_fields)}")
        else:
            self.error_label.setText("")
