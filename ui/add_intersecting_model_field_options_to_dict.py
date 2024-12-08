from typing import Optional

from anki.models import NotetypeDict
from aqt import mw

from ..logic.interpolate_fields import CARD_VALUES, intr_format


def get_intersecting_model_fields(
        models: list[NotetypeDict],
) -> set[str]:
    """
    Get the fields that are common to all the models.
    :param models: List of model dicts
    :return: Set of intersecting field names
    """
    if not models:
        return set()
    model_fields = [set(mw.col.models.field_names(model)) for model in models]
    return set.intersection(*model_fields)


def add_intersecting_model_field_options_to_dict(
        models: list[NotetypeDict],
        target_dict: dict,
        intersecting_fields: Optional[set[str]] = None,
        prefix: Optional[str] = None,
):
    """
    Get the fields that are common to all the models.
    Add those and all card values to the target_dict.
    :param models: List of model dicts
    :param target_dict: Could be the base SOURCE_NOTE_DATA_DICT or a sub-dict
    :param intersecting_fields: Optional pre-calculated set of intersecting fields
    :param prefix: Optional prefix to add to the field names, used to separate
        source vs destination fields. Not necessary if PasteableTextEdit is used
        and the prefix is acquired from the menu group names.
    """
    if not models:
        return target_dict
    if intersecting_fields is None:
        intersecting_fields = get_intersecting_model_fields(models)

    cards_key = 'Card values'

    target_dict[cards_key] = {}
    cards_target = target_dict[cards_key]
    fields_target = target_dict

    # Add card values to their own sub-menu
    for card_value in CARD_VALUES:
        value = card_value
        if prefix:
            value = f'{prefix}{card_value}'
        cards_target[card_value] = intr_format(value)

    if intersecting_fields:
        for field_name in intersecting_fields:
            field_value = field_name if prefix is None else f'{prefix}{field_name}'
            fields_target[field_name] = intr_format(field_value)
