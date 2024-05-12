import json

from anki.cards import Card


def write_custom_data(card: Card, key, value):
    if card.custom_data != "":
        custom_data = json.loads(card.custom_data)
        if value is None:
            custom_data.pop(key, None)
        else:
            custom_data[key] = value
    else:
        if value is None:
            return
        else:
            custom_data = {key: value}
    card.custom_data = json.dumps(custom_data)
