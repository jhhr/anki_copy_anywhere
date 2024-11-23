import re
import time
from functools import partial
from typing import Tuple, Union, List, Optional, Callable

# noinspection PyUnresolvedReferences
from anki.cards import Card
# noinspection PyUnresolvedReferences
from anki.notes import Note
# noinspection PyUnresolvedReferences
from aqt import mw

from ..utils import to_lowercase_dict

# PREFIX_SEPARATOR = ">>"
# Arg usage: {{__Card_Last_Reps==5}} or {{__Note_Has_Tag==some_tag}}
ARG_SEPARATOR = "=="

SOURCE_NOTE_DATA_KEY = "__Source_Note_Data"
DESTINATION_NOTE_DATA_KEY = "__Destination_Note_Data"
DESTINATION_PREFIX = "__Dest__"

NOTE_TYPE_ID = "__Note_Type_ID"
NOTE_ID = "__Note_ID"
NOTE_TAGS = "__Note_Tags"
NOTE_HAS_TAG = f"__Note_Has_Tag{ARG_SEPARATOR}"
NOTE_CARD_COUNT = "__Note_Card_Count"

NOTE_VALUES = [
    NOTE_TYPE_ID,
    NOTE_ID,
    NOTE_TAGS,
    NOTE_HAS_TAG,
    NOTE_CARD_COUNT,
]
NOTE_VALUE_DICT = {key: None for key in NOTE_VALUES}

VARIABLES_KEY = "__Variables"

DESTINATION_CARDS_DATA_KEY = "__Destination_Card_Data"
CARD_ID = "__Card_ID"
OTHER_CARD_IDS = "__Other_Card_IDs"
CARD_NID = "__Card_NID"
CARD_CREATED = "__Card_Created"
CARD_FIRST_REVIEW = "__Card_First_Review"
CARD_LATEST_REVIEW = "__Card_Latest_Review"
CARD_DUE = "__Card_Dues"
CARD_IVL = "__Card_Intervals"
CARD_EASE = "__Card_Ease"
CARD_REP_COUNT = "__Card_Rep_Count"
CARD_LAPSE_COUNT = "__Card_Lapse_Count"
CARD_AVERAGE_TIME = "__Card_Average_Time"
CARD_TOTAL_TIME = "__Card_Total_Time"
CARD_CUSTOM_DATA = "__Card_Custom_Data"
CARD_TYPE = "__Card_Type"

# A special value that takes an argument for how many reps to retrieve
CARD_LAST_REPS = f"__Card_Last_Reps{ARG_SEPARATOR}"

# Card values are all predetermined stuff
# So this is all the keys the card data menus will have
CARD_VALUES = [
    CARD_ID,
    OTHER_CARD_IDS,
    CARD_NID,
    CARD_CREATED,
    CARD_FIRST_REVIEW,
    CARD_LATEST_REVIEW,
    CARD_DUE,
    CARD_IVL,
    CARD_EASE,
    CARD_REP_COUNT,
    CARD_LAPSE_COUNT,
    CARD_AVERAGE_TIME,
    CARD_TOTAL_TIME,
    CARD_CUSTOM_DATA,
    CARD_TYPE,
    CARD_LAST_REPS,
]
# Dict for quick matching between interpolated fields and special values
CARD_VALUES_DICT = {key: None for key in CARD_VALUES}

# The prefix for the interpolation syntax
INTR_PREFIX = "{{"
INTR_SUFFIX = "}}"


def intr_format(s: str) -> str:
    """
    Wrap a string in the currently used interpolation syntax.
    """
    return f"{INTR_PREFIX}{s}{INTR_SUFFIX}"


# Regex to find all fields in a text that uses double curly brace syntax
FROM_TEXT_FIELD_REGEX = re.compile(rf"{INTR_PREFIX}(.+?){INTR_SUFFIX}")


def get_fields_from_text(from_text: str) -> List[str]:
    """
    Get all fields from a text that uses double curly brace syntax.
    """
    fields = FROM_TEXT_FIELD_REGEX.findall(from_text)
    return fields


def basic_arg_validator(arg: str) -> str:
    """
    A basic argument validator that checks if the arg is empty.
    :param arg: The arg passed after ARG_SEPARATOR
    :return: If ok "", else an error message
    """
    # Should not use the interpolation syntax or the arg will get interpolated!
    if INTR_PREFIX in arg or INTR_SUFFIX in arg:
        return f'should not contain {INTR_PREFIX} or {INTR_SUFFIX}'
    return ""


ARG_VALIDATORS: dict[str, Callable[[str], str]] = {
    # A tag could be any string, so everything is valid
    NOTE_HAS_TAG: lambda arg: "",
    # Reps should be parseable as an integer and > 0
    CARD_LAST_REPS: lambda arg: "" if arg.isdigit() and int(arg) > 0 \
        else "should be a positive integer",
}

# For both copy modes
# In withing copy mode, the source note = destination note
# Also generating variables is basically within copy mode
# In across copy mode, the source note != destination note
BASE_NOTE_MENU_DICT = {
    SOURCE_NOTE_DATA_KEY: {
        "Note Type ID (mid:)": intr_format(NOTE_TYPE_ID),
        "Note ID (nid:)": intr_format(NOTE_ID),
        "All tags": intr_format(NOTE_TAGS),
        "Has tag": intr_format(NOTE_HAS_TAG),
        "No. of different card types": intr_format(NOTE_CARD_COUNT),
    },
}

# For across copy mode only, used for the destination note
DESTINATION_NOTE_MENU_DICT = {
    # The note being used to query
    DESTINATION_NOTE_DATA_KEY: {
        "Destination Note Type ID (mid:)": intr_format(f"{DESTINATION_PREFIX}{NOTE_TYPE_ID}"),
        "Destination Note ID (nid:)": intr_format(f"{DESTINATION_PREFIX}{NOTE_ID}"),
        "Destination note all tags": intr_format(f"{DESTINATION_PREFIX}{NOTE_TAGS}"),
        "Destination note has tag": intr_format(f"{DESTINATION_PREFIX}{NOTE_HAS_TAG}"),
        "Destination No. different card types": intr_format(f"{DESTINATION_PREFIX}{NOTE_CARD_COUNT}"),
    },
}


def get_note_data_value(
        note: Note,
        field_name: str,
        return_str: bool = True
) -> Union[str, int, None, Callable[[str], Union[str, any]]]:
    """
    Get the value for a single special field.
    """

    def has_tag(arg: str):
        if return_str:
            return arg if note.has_tag(arg) else ""
        return note.has_tag(arg)

    if field_name == NOTE_TYPE_ID:
        return note.model()["id"]
    if field_name == NOTE_ID:
        return note.id
    if field_name == NOTE_TAGS:
        return " ".join(note.tags)
    if field_name == NOTE_HAS_TAG:
        return has_tag
    if field_name == NOTE_CARD_COUNT:
        return str(len(note.card_ids()))
    return None


def timespan(t):
    return mw.col.format_timespan(t)


def format_timestamp(e, time_format=None):
    # "%a, %d %b %Y %H:%M:%S"
    return time.strftime(time_format or "%Y-%m-%d %H:%M:%S", time.localtime(e))


def format_timestamp_days(e, time_format=None):
    return time.strftime(time_format or "%Y-%m-%d", time.localtime(e))


def get_card_values_dict_for_note(
        note: Note,
        return_str: bool = True
) -> dict[
    str,
    dict[
        str,
        Union[str, Callable[[str], Union[str, any]]]
    ]
]:
    """
    Get a dictionary of special fields that are card-specific.
    """
    card_values = {}

    def get_card_last_reps(card_id: str, rep_count: str):
        try:
            rep_count = int(rep_count)
        except ValueError:
            return "" if return_str else None
        if rep_count < 1:
            return "" if return_str else None
        reps = mw.col.db.scalar(
            f"SELECT ease FROM revlog WHERE cid = {card_id} ORDER BY id DESC LIMIT {rep_count}"
        )
        return str(reps) if return_str else reps

    # Add values as a dict by card_type_name
    for card in note.cards():
        card_type_name = card.template()["name"]

        (first, last, cnt, total) = mw.col.db.first(
            f"select min(id), max(id), count(), sum(time)/1000 from revlog where cid = {card.id}"
        )

        card_values[card_type_name] = {
            CARD_ID: card.id,
            OTHER_CARD_IDS: [cid for cid in note.card_ids() if cid != card.id],
            CARD_NID: card.nid,
            CARD_DUE: card.due,
            CARD_IVL: card.ivl,
            CARD_EASE: card.factor / 10,
            CARD_REP_COUNT: card.reps,
            CARD_LAPSE_COUNT: card.lapses,
            CARD_FIRST_REVIEW: format_timestamp(first / 1000),
            CARD_LATEST_REVIEW: format_timestamp(last / 1000),
            CARD_AVERAGE_TIME: timespan(total / float(cnt)),
            CARD_TOTAL_TIME: timespan(total),
            CARD_TYPE: "Review" if card.type == Card.TYPE_REV else \
                "New" if card.type == Card.TYPE_NEW else \
                    "Learning" if card.type == Card.TYPE_LRN else \
                        "Relearning",
            CARD_CREATED: format_timestamp(card.nid / 1000),
            CARD_CUSTOM_DATA: card.custom_data,
            CARD_LAST_REPS: partial(get_card_last_reps, card.id),
        }
    return card_values


NOTE_VALUE_RE = re.compile(rf"""
^ # must start with __ or this is not a note value
(__\w+ # match group 1, the note value key
    (?:{ARG_SEPARATOR})? # the arg separator, optional
)
(.*)? # match group 2, the note value arg, only present when the arg separator is present
$
""", re.VERBOSE)

CARD_VALUE_RE = re.compile(rf"""
^
(.+) # match group 1, the card type name
(__\w+ # match group 2, the card value key
  (?:{ARG_SEPARATOR})? # the arg separator, optional
) 
(.*)? # match group 3, the card value arg, only present when the arg separator is present
$
""", re.VERBOSE)


def get_from_note_fields(
        field: str,
        note: Note,
        note_fields: dict,
        card_values_dict: dict = None
) -> Tuple[Union[str, None], Union[dict, None]]:
    """
    Get a value from a note, source or destination. The note's fields or its cards' fields.
    :param field: interpolation field key
    :param note: note to get data values from
    :param note_fields: pre-made dict of note fields
    :param card_values_dict: not pre-made dict of card values, it will be made once needed
           and not, if not needed. The same dict will be passed around to avoid re-making it.
    :return: value, card_values_dict
    """
    if not note:
        raise ValueError("Note is None in get_from_note_fields")

    # The most common case is just getting a note field so check that first
    field_lower = field.lower()
    # Even if the value is empty, we still want to return it when the field matches
    if field_lower in note_fields:
        return note_fields.get(field_lower), card_values_dict

    # Checking note fields is easy, so let's do that second
    note_match = NOTE_VALUE_RE.match(field)
    if note_match:
        maybe_note_value_key, maybe_note_value_arg = note_match.group(1, 2)
        # Check if the note value key is valid
        if maybe_note_value_key in NOTE_VALUES:
            value = get_note_data_value(note, maybe_note_value_key)
            # Check if this value is a function that needs the argument
            if isinstance(value, partial):
                return value(maybe_note_value_arg), card_values_dict
            return value, card_values_dict
    # And last, cards are harder since they need to specify the card type name too
    card_match = CARD_VALUE_RE.match(field)
    if card_match:
        maybe_card_type_name, maybe_card_value_key, maybe_card_value_arg = card_match.group(1, 2, 3)
        # Check if the card type name is valid
        if maybe_card_value_key in CARD_VALUES_DICT:
            # If we haven't made the card values dict yet, do it now
            if card_values_dict is None:
                card_values_dict = get_card_values_dict_for_note(note)

            value_dict = card_values_dict.get(maybe_card_type_name)
            if value_dict and maybe_card_value_key in value_dict:
                value = value_dict.get(maybe_card_value_key)
                # Check if this value is a function that needs the argument
                if isinstance(value, partial):
                    return value(maybe_card_value_arg), card_values_dict
                return value_dict.get(maybe_card_value_key), card_values_dict
    # If we get here, the field is invalid
    return None, card_values_dict


def interpolate_from_text(
        text: str,
        source_note: Note,
        dest_note: Optional[Note] = None,
        variable_values_dict: dict = None
) -> Tuple[
    Union[str, None], List[str]]:
    """
    Interpolates a text that uses curly brace syntax.
    Also returns a list of all invalid fields in the text for debugging.

    :param text: The text to interpolate
    :param source_note: The note to get the values from for non-prefixed note fields
    :param dest_note: The note to get the values from for DESTINATION_PREFIX-ed note fields
    :param variable_values_dict: A dictionary of custom variables to use in the interpolation
    """
    # Bunch of extra logic to make this whole process case-insensitive

    # Regex to pull out any words enclosed in double curly braces
    fields = get_fields_from_text(text)

    # field.lower() -> value map
    all_note_fields = to_lowercase_dict(source_note)
    all_dest_note_fields = to_lowercase_dict(dest_note)
    variable_fields = to_lowercase_dict(variable_values_dict)

    # Lowercase the characters inside {{}} in the from_text
    text = FROM_TEXT_FIELD_REGEX.sub(lambda x: "{{" + x.group(1).lower() + "}}", text)

    card_values_dict = None
    dest_card_values_dict = None

    # Sub values in text
    invalid_fields = []
    for field in fields:
        # It's possible to input invalid stuff like destination fields in within copy mode
        if field.startswith(DESTINATION_PREFIX) and dest_note:
            field = field[len(DESTINATION_PREFIX):]
            value, dest_card_values_dict = get_from_note_fields(
                field, dest_note, all_dest_note_fields, dest_card_values_dict
            )
        else:
            value, card_values_dict = get_from_note_fields(
                field, source_note, all_note_fields, card_values_dict
            )
        field_lower = field.lower()
        if not value:
            value = variable_fields.get(field_lower, None)
        # value being "" is ok, but None is not
        if value is None:
            if field_lower not in invalid_fields:
                invalid_fields.append(field_lower)
            # Set value to empty string so the text doesn't break,
            # we don't leave un-interpolated fields
            value = ""

        text = text.replace("{{" + field_lower + "}}", str(value))

    return text, invalid_fields
