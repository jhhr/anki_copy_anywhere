import re
from typing import Tuple, Union, List

from anki.notes import Note

from ..utils import to_lowercase_dict

# Regex to find all fields in a text that uses double curly brace syntax
FROM_TEXT_FIELD_REGEX = re.compile(r"{{(.+?)}}")

# General special fields value
SPECIAL_FIELDS_KEY = "__Special fields"
NOTE_ID_FIELD = "__Note ID"

# Special fields that can be used in the "Define what to copy from" PasteableTextEdit
# Prefix them with __ to avoid conflicts with actual note field names
DESTINATION_FIELD_VALUE = "__Current target value"
# Dict for the right-click menu to show the special fields in the from_text TextEdit
SOURCE_SPECIAL_FIELDS_DICT = {
    SPECIAL_FIELDS_KEY: [
        NOTE_ID_FIELD,
        DESTINATION_FIELD_VALUE,
    ]
}


def get_special_field_value_for_note(note: Note, field_name: str) -> Union[str, None]:
    """
    Get the value for a single special field.
    """
    if field_name == NOTE_ID_FIELD.lower():
        return note.id
    return None


def interpolate_from_text(text: str, note: Note, current_field_value: str = None) -> Tuple[
    Union[str, None], List[str]]:
    """
    Interpolates a text that uses curly brace syntax.
    Also returns a list of all invalid fields in the text for debugging.
    """
    # Bunch of extra logic to make this whole process case.insensitive

    # Regex to pull out any words enclosed in double curly braces
    fields = get_fields_from_text(text)

    # field.lower() -> value map
    all_note_fields = to_lowercase_dict(note)

    # Lowercase the characters inside {{}} in the from_text
    text = FROM_TEXT_FIELD_REGEX.sub(lambda x: "{{" + x.group(1).lower() + "}}", text)

    # Sub values in text
    invalid_fields = []
    for field in fields:
        field_lower = field.lower()
        value = all_note_fields.get(field_lower, None)
        if not value:
            value = get_special_field_value_for_note(note, field_lower)
        if (not value
                and current_field_value is not None
                and field_lower == DESTINATION_FIELD_VALUE.lower()):
            value = current_field_value
        text = text.replace("{{" + field_lower + "}}", str(value))

    return text, invalid_fields


def get_fields_from_text(from_text: str) -> List[str]:
    """
    Get all fields from a text that uses double curly brace syntax.
    """
    fields = FROM_TEXT_FIELD_REGEX.findall(from_text)
    return fields
