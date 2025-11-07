import re
import time
from functools import partial
from typing import Tuple, Union, List, Optional, Callable, Sequence, cast

from anki.cards import Card, CardId

from anki.consts import (
    CARD_TYPE_NEW,
    CARD_TYPE_LRN,
    CARD_TYPE_REV,
    CARD_TYPE_RELEARNING,
)

from anki.notes import Note

from aqt import mw


from ..utils.to_lowercase_dict import to_lowercase_dict

# PREFIX_SEPARATOR = ">>"
# Arg usage: {{__Card_Last_Reps==5}} or {{__Note_Has_Tag==some_tag}}
ARG_SEPARATOR = "=="

SOURCE_NOTE_DATA_KEY = "__Source_Note_Data"
DESTINATION_NOTE_DATA_KEY = "__Destination_Note_Data"
DESTINATION_PREFIX = "__Dest__"
SOURCE_PREFIX = "__Source__"

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
TARGET_NOTES_COUNT = "__Target_Notes_Count"

DESTINATION_CARDS_DATA_KEY = "__Destination_Card_Data"
CARD_ID = "__Card_ID"
OTHER_CARD_IDS = "__Other_Card_IDs"
CARD_NID = "__Card_NID"
CARD_CREATED = "__Card_Created"
CARD_FIRST_REVIEW = "__Card_First_Review"
CARD_LATEST_REVIEW = "__Card_Latest_Review"
CARD_DUE = "__Card_Due"
CARD_IVL = "__Card_Interval"
CARD_EASE = "__Card_Ease"
CARD_STABILITY = "__Card_Stability"
CARD_DIFFICULTY = "__Card_Difficulty"
CARD_REP_COUNT = "__Card_Rep_Count"
CARD_LAPSE_COUNT = "__Card_Lapse_Count"
CARD_AVERAGE_TIME = "__Card_Average_Time"
CARD_TOTAL_TIME = "__Card_Total_Time"
CARD_CUSTOM_DATA = "__Card_Custom_Data"
CARD_TYPE = "__Card_Type"

# A special value that takes an argument for how many reps to retrieve
CARD_LAST_EASES = f"__Card_Last_Reps{ARG_SEPARATOR}"
CARD_LAST_FACTORS = f"__Card_Last_Factors{ARG_SEPARATOR}"
CARD_LAST_IVLS = f"__Card_Last_Intervals{ARG_SEPARATOR}"
CARD_LAST_REV_TYPES = f"__Card_Last_Review_Types{ARG_SEPARATOR}"
CARD_LAST_REV_TIMES = f"__Card_Last_Review_Times{ARG_SEPARATOR}"

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
    CARD_STABILITY,
    CARD_DIFFICULTY,
    CARD_REP_COUNT,
    CARD_LAPSE_COUNT,
    CARD_AVERAGE_TIME,
    CARD_TOTAL_TIME,
    CARD_CUSTOM_DATA,
    CARD_TYPE,
    CARD_LAST_EASES,
    CARD_LAST_FACTORS,
    CARD_LAST_IVLS,
    CARD_LAST_REV_TYPES,
    CARD_LAST_REV_TIMES,
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
        return f"should not contain {INTR_PREFIX} or {INTR_SUFFIX}"
    return ""


# Basic query for how many to get should either "all"
# #or parseable as an integer and > 0
def BASE_NUM_ARG_VALIDATOR(arg):
    if (arg.isdigit() and int(arg) > 0) or arg == "all":
        return ""
    else:
        return "should be a positive integer"


ARG_VALIDATORS: dict[str, Callable[[str], str]] = {
    # A tag could be any string, so everything is valid
    NOTE_HAS_TAG: BASE_NUM_ARG_VALIDATOR,
    CARD_LAST_EASES: BASE_NUM_ARG_VALIDATOR,
    CARD_LAST_FACTORS: BASE_NUM_ARG_VALIDATOR,
    CARD_LAST_IVLS: BASE_NUM_ARG_VALIDATOR,
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
        "Destination No. different card types": intr_format(
            f"{DESTINATION_PREFIX}{NOTE_CARD_COUNT}"
        ),
    },
}


JSONSerializableValue = Union[
    None,
    bool,
    int,
    float,
    str,
    Sequence["JSONSerializableValue"],
    dict[str, "JSONSerializableValue"],
]
ValueOrValueGetter = Union[JSONSerializableValue, Callable[[str], JSONSerializableValue]]


def get_note_data_value(
    note: Note,
    field_name: str,
) -> ValueOrValueGetter:
    """
    Get the value for a single special field.
    """

    def has_tag(arg: str):
        return arg if note.has_tag(arg) else "-"

    if field_name == NOTE_TYPE_ID:
        note_type = note.note_type()
        return note_type["id"] if note_type else ""
    if field_name == NOTE_ID:
        return note.id
    if field_name == NOTE_TAGS:
        return " ".join(note.tags)
    if field_name == NOTE_HAS_TAG:
        return has_tag
    if field_name == NOTE_CARD_COUNT:
        return len(note.card_ids())
    return None


def timespan(t):
    return mw.col.format_timespan(t)


def format_timestamp(e, time_format=None):
    # "%a, %d %b %Y %H:%M:%S"
    return time.strftime(time_format or "%Y-%m-%d %H:%M:%S", time.localtime(e))


def format_timestamp_days(e, time_format=None):
    return time.strftime(time_format or "%Y-%m-%d", time.localtime(e))


def get_card_last_reps(
    card_id: CardId,
    rep_count: str,
    get_ease: bool = False,
    get_ivl: bool = False,
    get_fct: bool = False,
    get_type: bool = False,
    get_time: bool = False,
) -> Union[
    # Return  or a flat list of values
    Sequence[Union[int, float]],
    # or a list of lists of values when two or more rev_log fields are requested
    Sequence[Sequence[Union[int, float]]],
]:
    if not get_ease and not get_ivl and not get_fct and not get_type and not get_time:
        return []
    all = rep_count == "all"
    if not all:
        try:
            rep_count_int = int(rep_count)
        except ValueError:
            return []
        if rep_count_int < 1:
            return []
    assert mw.col.db is not None
    # Get rep eases, excluding manual schedules, identified by ease = 0
    select_cols = ",".join(
        filter(
            None,
            [
                "ease" if get_ease else "",
                "ivl" if get_ivl else "",
                "factor" if get_fct else "",
                "type" if get_type else "",
                # id is the epoch-milliseconds timestamp of when the review happened
                # time is the time spent in milliseconds
                "id" if get_time else "",
            ],
        )
    )
    reps = mw.col.db.list(f"""SELECT
                {select_cols}
                FROM revlog
                WHERE cid = {card_id}
                AND ease != 0
                ORDER BY id
                {f"DESC LIMIT {rep_count_int}" if not all else ""}
            """)
    return reps


ValuesDict = dict[str, ValueOrValueGetter]


def get_value_for_card(
    card: Card,
    note: Note,
) -> ValuesDict:
    assert mw.col.db is not None
    result = mw.col.db.first(
        f"select min(id), max(id), count(), sum(time)/1000 from revlog where cid = {card.id}"
    )
    if result:
        (first, last, cnt, total) = result
    else:
        first, last, cnt, total = None, None, None, None
    return {
        CARD_ID: card.id or 0,
        OTHER_CARD_IDS: [cid for cid in note.card_ids() if cid != card.id],
        CARD_NID: card.nid or 0,
        CARD_DUE: card.due or 0,
        CARD_IVL: card.ivl or 0,
        CARD_EASE: card.factor / 10 or 0,
        # If FSRS is not enabled, memory_state will be None
        CARD_STABILITY: round(card.memory_state.stability, 1) if card.memory_state else 0,
        CARD_DIFFICULTY: round(card.memory_state.difficulty, 1) if card.memory_state else 0,
        CARD_REP_COUNT: card.reps or 0,
        CARD_LAPSE_COUNT: card.lapses or 0,
        CARD_FIRST_REVIEW: format_timestamp(first / 1000) if first else "-",
        CARD_LATEST_REVIEW: format_timestamp(last / 1000) if last else "-",
        CARD_AVERAGE_TIME: timespan(total / float(cnt)) if cnt is not None and cnt > 0 else "-",
        CARD_TOTAL_TIME: timespan(total),
        CARD_TYPE: (
            "Review"
            if card.type == CARD_TYPE_REV
            else (
                "New"
                if card.type == CARD_TYPE_NEW
                else (
                    "Learning"
                    if card.type == CARD_TYPE_LRN
                    else "Relearning" if card.type == CARD_TYPE_RELEARNING else ""
                )
            )
        ),
        CARD_CREATED: format_timestamp(card.nid / 1000) if card.nid else "-",
        CARD_CUSTOM_DATA: card.custom_data or {},
        CARD_LAST_EASES: partial(get_card_last_reps, card.id, get_ease=True),
        CARD_LAST_FACTORS: partial(get_card_last_reps, card.id, get_fct=True),
        CARD_LAST_IVLS: partial(get_card_last_reps, card.id, get_ivl=True),
        CARD_LAST_REV_TYPES: partial(get_card_last_reps, card.id, get_type=True),
        CARD_LAST_REV_TIMES: partial(get_card_last_reps, card.id, get_time=True),
    }


CardValuesDict = dict[str, ValuesDict]


def get_card_values_dict_for_note(
    note: Note,
) -> CardValuesDict:
    """
    Get a dictionary of special fields that are card-specific.
    """
    card_values = {}

    current_cards = note.cards()
    note_type = note.note_type()
    all_card_templates = note_type["tmpls"] if note_type else []
    # all cards will be empty for a new note being added
    # and some cards may be missing, if the template is conditional
    template_names_with_current_card = {card.template()["name"] for card in current_cards}
    # For each card type that doesn't have a card yet, add default values
    for card_template in all_card_templates:
        if card_template["name"] not in template_names_with_current_card:
            # Make a fake card to get the default values
            card_values[card_template["name"]] = get_value_for_card(Card(mw.col), note)
    # Add values as a dict by card_type_name
    for card in note.cards():
        card_type_name = card.template()["name"]

        card_values[card_type_name] = get_value_for_card(card, note)
    return card_values


NOTE_VALUE_RE = re.compile(
    rf"""
^ # must start with __ or this is not a note value
(__\w+ # match group 1, the note value key
    (?:{ARG_SEPARATOR})? # the arg separator, optional
)
(.*)? # match group 2, the note value arg, only present when the arg separator is present
$
""",
    re.VERBOSE,
)

# Normal card values have to specify the card type name
CARD_VALUE_RE = re.compile(
    rf"""
^
(.+) # match group 1, the card type name
(__\w+ # match group 2, the card value key
  (?:{ARG_SEPARATOR})? # the arg separator, optional
)
(.*)? # match group 3, the card value arg, only present when the arg separator is present
$
""",
    re.VERBOSE,
)

# In multi note type definitions, the card type name is omitted, as we just assume there is only one
# Same as above but actually simpler as the card type is omitted
MULTI_CARD_VALUE_RE = re.compile(
    rf"""
^
(__\w+ # match group 1, the card value key
  (?:{ARG_SEPARATOR})? # the arg separator, optional
)
(.*)? # match group 2, the card value arg, only present when the arg separator is present
$
""",
    re.VERBOSE,
)


def get_from_note_fields(
    field: str,
    note: Note,
    note_fields: dict,
    card_values_dict: Optional[CardValuesDict] = None,
    multiple_note_types: bool = False,
) -> Tuple[Union[JSONSerializableValue, None], Union[CardValuesDict, None]]:
    """
    Get a value from a note, source or destination. The note's fields or its cards' fields.
    :param field: interpolation field key
    :param note: note to get data values from
    :param note_fields: pre-made dict of note fields
    :param card_values_dict: not pre-made dict of card values, it will be made once needed
           and not, if not needed. The same dict will be passed around to avoid re-making it.
    :param multiple_note_types: Whether the copy is into multiple note types
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
            value_or_partial = get_note_data_value(note, maybe_note_value_key)
            # Check if this value is a function that needs the argument
            if isinstance(value_or_partial, partial):
                value = value_or_partial(maybe_note_value_arg)
            else:
                value = cast(JSONSerializableValue, value_or_partial)
            return value, card_values_dict
    # And last, cards are harder since they need to specify the card type name too
    card_match = (
        CARD_VALUE_RE.match(field) if not multiple_note_types else MULTI_CARD_VALUE_RE.match(field)
    )
    if card_match:
        if multiple_note_types:
            maybe_card_value_key, maybe_card_value_arg = card_match.group(1, 2)
            maybe_card_type_name = ""
        else:
            maybe_card_type_name, maybe_card_value_key, maybe_card_value_arg = card_match.group(
                1, 2, 3
            )
        # Check if the card type name is valid
        if maybe_card_value_key in CARD_VALUES_DICT:
            # If we haven't made the card values dict yet, do it now
            if card_values_dict is None:
                card_values_dict = get_card_values_dict_for_note(note)

            # New notes will have no cards, so we can't get a value
            # Return "" so we don't flag this as an invalid field
            if not card_values_dict:
                return "", card_values_dict

            if multiple_note_types:
                # If there are multiple note types, we just assume there is only one card type
                dict_keys = list(card_values_dict.keys())
                if len(dict_keys) == 1:
                    maybe_card_type_name = dict_keys[0]
                elif len(dict_keys) > 1:
                    raise ValueError(
                        "ERROR: Multiple target note types should each only have a single card type"
                    )
                # If there somehow are zero card types, we of course can't get a value

            value_dict = card_values_dict.get(maybe_card_type_name)
            if value_dict and maybe_card_value_key in value_dict:
                value_or_partial = value_dict.get(maybe_card_value_key)
                # Check if this value is a function that needs the argument
                if isinstance(value_or_partial, partial):
                    value = value_or_partial(maybe_card_value_arg)
                else:
                    value = cast(JSONSerializableValue, value_or_partial)
                return value, card_values_dict
    # If we get here, the field is invalid
    return None, card_values_dict


def interpolate_from_text(
    text: str,
    source_note: Note,
    destination_note: Optional[Note] = None,
    variable_values_dict: Optional[dict] = None,
    multiple_note_types: bool = False,
) -> Tuple[Union[str, None], List[str]]:
    """
    Interpolates a text that uses curly brace syntax.
    Also returns a list of all invalid fields in the text for debugging.
    The destination note should not be modified in this function, only its values should be
    used.

    :param text: The text to interpolate
    :param source_note: The note to get the values from for non-prefixed note fields
    :param destination_note: The note to get the values from for DESTINATION_PREFIX-ed note fields
    :param variable_values_dict: A dictionary of custom variables to use in the interpolation
    :param multiple_note_types: Whether the copy is into multiple note types
    """
    # Bunch of extra logic to make this whole process case-insensitive

    # Regex to pull out any words enclosed in double curly braces
    fields = get_fields_from_text(text)

    # field.lower() -> value map
    all_note_fields = to_lowercase_dict(source_note)
    all_dest_note_fields = to_lowercase_dict(destination_note)
    variable_fields = to_lowercase_dict(variable_values_dict)

    # Lowercase the characters inside {{}} in the text
    text = FROM_TEXT_FIELD_REGEX.sub(lambda x: intr_format(x.group(1).lower()), text)

    card_values_dict = None
    dest_card_values_dict = None

    # Sub values in text
    invalid_fields = []
    for field in fields:
        # It's possible to input invalid stuff like destination fields in within copy mode
        if field.startswith(DESTINATION_PREFIX) and destination_note:
            value, dest_card_values_dict = get_from_note_fields(
                field[len(DESTINATION_PREFIX) :],
                destination_note,
                all_dest_note_fields,
                dest_card_values_dict,
                multiple_note_types,
            )
        else:
            value, card_values_dict = get_from_note_fields(
                field,
                source_note,
                all_note_fields,
                card_values_dict,
                multiple_note_types,
            )
        field_lower = field.lower()
        if value is None:
            value = variable_fields.get(field_lower, None)
        # value being "" or 0 is ok, but None is not
        if value is None:
            if field_lower not in invalid_fields:
                invalid_fields.append(field_lower)
            # Set value to empty string so the text doesn't break,
            # we don't leave un-interpolated fields
            value = ""

        text = text.replace(intr_format(field_lower), str(value))

    return text, invalid_fields
