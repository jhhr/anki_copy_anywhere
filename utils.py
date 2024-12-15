import json
from contextlib import contextmanager
from typing import Optional, Dict, Any, Union, TypedDict

# noinspection PyUnresolvedReferences
from anki.cards import Card
# noinspection PyUnresolvedReferences
from aqt.qt import QFontMetrics, QComboBox
# noinspection PyUnresolvedReferences
from aqt.utils import tooltip


def add_dict_key_value(
    dict: dict,
    key: str,
    value: Optional[str] = None,
    new_key: Optional[str] = None,
    ):
    if new_key is not None and value is None:
        # rename key
        dict[new_key] = dict.pop(key, None)
    elif new_key is not None and value is not None:
        # rename key and change value
        dict.pop(key, None)
        dict[new_key] = value
    elif value is not None:
        # set value for key
        dict[key] = value
    else:
        # remove key
        dict.pop(key, None)

class KeyValueDict(TypedDict):
    key: str
    value: Optional[Union[str, int, float, bool]]
    new_key: Optional[str]

def write_custom_data(
    card: Card,
    key: str = None,
    value: Optional[Union[str, int, float, bool]] = None,
    new_key: Optional[str] = None,
    key_values: Optional[list[KeyValueDict]] = None,
):
    """
    Write custom data to the card.
    :param card: The card to write the custom data to.
    :param key: The key to write the value to.
    :param value: The value to write to the key. If None, the key will be removed.
    :param new_key: The new key to rename the key to.
                If value is None, the key will be renamed while keeping the old value.
                If value is not None, the key will be renamed and the value will changed.
    :param key_values: A list of (key, value, new key) tuples. Used for performance as calling
                this function multiple times would perform json.loads and json.dumps multiple times.

    """
    if card.custom_data != "":
        custom_data = json.loads(card.custom_data)
    else:
        custom_data = {}
    if key_values is not None:
        for kv in key_values:
            add_dict_key_value(
                custom_data,
                kv.get("key"),
                kv.get("value"),
                kv.get("new_key"),
            )
    else:
        add_dict_key_value(custom_data, key, value, new_key)
    compressed_data = json.dumps(custom_data, separators=(',', ':'))
    if len(compressed_data) > 100:
        raise ValueError("Custom data exceeds 100 bytes after compression.")
    card.custom_data = compressed_data


def to_lowercase_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Converts a dictionary to lowercase keys"""
    if d is None:
        return {}
    return {k.lower(): v for k, v in d.items()}

def make_query_string(prefix: str, values: list[str]) -> str:
    """Converts a list of values to a query string for the card browser"""
    if not prefix or not values:
        return ""
    query = "("
    for i, value in enumerate(values):
        query += f'"{prefix}:{value}"'
        if i < len(values) - 1:
            query += " OR "
    query += ")"
    return query


def adjust_width_to_largest_item(combo_box: QComboBox):
    """Adjusts the width of a standard combo box to the largest item"""
    max_width = 0
    for i in range(combo_box.count()):
        item_text = combo_box.itemText(i)
        item_width = QFontMetrics(combo_box.font()).width(item_text)
        if item_width > max_width:
            max_width = item_width
    combo_box.view().setMinimumWidth(max_width + 20)


@contextmanager
def block_signals(*widgets):
    try:
        for widget in widgets:
            widget.blockSignals(True)
        yield
    finally:
        for widget in widgets:
            widget.blockSignals(False)
