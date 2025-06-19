from typing import Optional, TypedDict, Union


from anki.cards import Card


import json


def add_dict_key_value(
    dict: dict,
    key: Optional[str] = None,
    value: Optional[Union[str, int, float, bool]] = None,
    new_key: Optional[str] = None,
):
    if new_key is not None and value is None and key is not None:
        # rename key
        dict[new_key] = dict.pop(key, None)
    elif new_key is not None and value is not None:
        # rename key and change value
        dict.pop(key, None)
        dict[new_key] = value
    elif value is not None:
        # set value for key
        dict[key] = value
    elif key is not None:
        # remove key
        dict.pop(key, None)


class KeyValueDict(TypedDict):
    key: str
    value: Optional[Union[str, int, float, bool]]
    new_key: Optional[str]


def write_custom_data(
    card: Card,
    key: Optional[str] = None,
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
                kv.get("value", ""),
                kv.get("new_key"),
            )
    else:
        add_dict_key_value(custom_data, key, value, new_key)
    compressed_data = json.dumps(custom_data, separators=(",", ":"))
    if len(compressed_data) > 100:
        raise ValueError("Custom data exceeds 100 bytes after compression.")
    card.custom_data = compressed_data
