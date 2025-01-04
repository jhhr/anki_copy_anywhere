from typing import Optional, Union

from aqt.qt import (
    QVBoxLayout,
    QLabel,
)

from .pasteable_text_edit import PasteableTextEdit
from ..logic.interpolate_fields import (
    get_fields_from_text,
    intr_format,
    ARG_SEPARATOR,
    basic_arg_validator,
    ARG_VALIDATORS,
    CARD_VALUE_RE,
    NOTE_VALUE_RE,
)


class InterpolatedTextEditLayout(QVBoxLayout):
    """
    Layout containing a PasteableTextEdit that allows for interpolation of fields.
    """

    def __init__(
        self,
        parent=None,
        label: Optional[Union[QLabel, str]] = None,
        options_dict=None,
        description: Optional[str] = None,
        height: Optional[int] = None,
        placeholder_text: Optional[str] = None,
        is_required: bool = False,
    ):
        super().__init__(parent)
        # options dict is a 2-level dict
        # with menu group names as keys and a list of options as values
        if options_dict is None:
            options_dict = {}
        self.options_dict = options_dict
        # validation dict is 1-level dict with all possible fields as keys
        self.validate_dict: dict[str, bool] = {}

        self.text_edit = PasteableTextEdit(
            parent,
            options_dict=options_dict,
            height=height,
            placeholder_text=placeholder_text,
            is_required=is_required,
        )
        self.error_label = QLabel()
        # Connect text changed to validation
        self.text_edit.textChanged.connect(self.validate_text)
        # Allow providing a QLabel that the provider can then modify
        main_label = QLabel(label) if isinstance(label, str) else label

        self.addWidget(main_label)

        self.optional_description = QLabel("")
        # Set description font size smaller
        self.optional_description.setStyleSheet("font-size: 10px;")
        self.addWidget(self.optional_description)
        self.set_description(description)

        self.addWidget(self.text_edit)
        self.addWidget(self.error_label)

        self.update_options(options_dict)

    def get_text(self):
        """Get current text from the text field."""
        return self.text_edit.toPlainText()

    def set_text(self, text):
        """Set the text in the text field."""
        self.text_edit.setPlainText(text)
        self.text_edit.update_required_style()

    def set_description(self, description):
        """Set the description text."""
        if description:
            self.optional_description.setText(description)
            self.optional_description.show()
        else:
            self.optional_description.hide()

    def update_options(self, new_options_dict):
        """
        Updates the options in the "Define what to copy from" TextEdit right-click menu.
        """
        self.text_edit.clear_options()
        self.options_dict = new_options_dict
        self.validate_dict = {}

        # Recursively add options to the context menu to
        # allow arbitrary nesting of options and submenus
        def add_options_to_validate_dict(option: Union[list, dict, str]):
            if isinstance(option, dict):
                for field, value in option.items():
                    # new_dict_level = self.text_edit.add_option_group(menu_key)
                    add_options_to_validate_dict(value)
            elif isinstance(option, list):
                for field in option:
                    self.validate_dict[field.lower()] = True
            else:
                self.validate_dict[option.lower()] = True

        add_options_to_validate_dict(new_options_dict)
        self.text_edit.set_options_dict(new_options_dict)
        self.validate_text()

    def validate_text(self):
        """
        Validates text that's using interpolation syntax for note fields.
        Returns none if a source field is empty.
        """
        fields = get_fields_from_text(self.text_edit.toPlainText())

        invalid_fields = []
        # Validate that all fields are present in the dict
        for field in fields:
            arg = None
            card_type_name = None
            if ARG_SEPARATOR in field and "__" in field:
                match = NOTE_VALUE_RE.match(field)
                if match:
                    field, arg = match.group(1, 2)
                else:
                    match = CARD_VALUE_RE.match(field)
                    if match:
                        card_type_name, field, arg = match.group(1, 2, 3)
                        field = card_type_name + field

            try:
                self.validate_dict[intr_format(field.lower())]
            except KeyError:
                invalid_fields.append(f'<b style="color:red">{field}</b>: Not a valid field')
                continue

            if arg is not None:
                validator = None
                if card_type_name is not None:
                    # ARG_VALIDATORS is a dict with the card value key only, no card type name
                    validator = ARG_VALIDATORS.get(field[len(card_type_name) :], None)
                else:
                    validator = ARG_VALIDATORS.get(field, None)

                if validator is not None:
                    error_msg = basic_arg_validator(arg) or validator(arg)
                    if error_msg:
                        invalid_fields.append(f"""{field}
                            <span style="color: orange;"><b style="color:red">
                              {arg or "[blank]"}</b>: {error_msg}
                            </span>""")

        if len(invalid_fields) > 0:
            self.error_label.setText("<br/>".join(invalid_fields))
        else:
            self.error_label.setText("")
