from aqt import mw

from ..logic.interpolate_fields import CARD_VALUES, intr_format
from typing import Optional


def add_model_options_to_dict(
    model_name: str, model_id: int, target_dict: dict, prefix: Optional[str] = None
):
    """
    Add the field names and card values to the target_dict.
    :param model_name:
    :param model_id:
    :param target_dict: Could be the base SOURCE_NOTE_DATA_DICT or a sub-dict
    :param prefix: Optional prefix to add to the field names, used to separate
        source vs destination fields. Not necessary if PasteableTextEdit is used
        and the prefix is acquired from the menu group names.

    :return: void, modifies target_dict in place
    """
    fields_key = "Note fields"
    cards_key = "Card types"
    # Field replacement values will be 2-level menu
    model_key = model_name
    target_dict[model_key] = {fields_key: {}, cards_key: {}}
    cards_target = target_dict[model_key][cards_key]
    fields_target = target_dict[model_key][fields_key]
    card_templates = mw.col.models.get(model_id)["tmpls"]

    # If there is only 1 card template, don't add a sub-menu
    # Card replacement values will be 3-level menu, model: card_type: card_value
    for card_template in card_templates:
        cards_target[card_template["name"]] = {}
        for card_value in CARD_VALUES:
            value = f'{card_template["name"]}{card_value}'
            if prefix:
                value = f"{prefix}{value}"
            cards_target[card_template["name"]][card_value] = intr_format(value)

    for field_name in mw.col.models.field_names(mw.col.models.get(model_id)):
        field_value = field_name if prefix is None else f"{prefix}{field_name}"
        fields_target[field_name] = intr_format(field_value)
