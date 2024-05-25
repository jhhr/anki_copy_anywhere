import json

from anki.cards import Card
from aqt.utils import tooltip


class CacheResults:
    def __init__(self, result_text: str, changes):
        self.result_text = result_text
        self.changes = changes
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


def filter_init(filter_prefix, valid_args, filter_str, context):
    is_cache = None
    try:
        is_cache = context.extra_state["is_cache"]
    except KeyError:
        is_cache = False

    def show_error_message(message: str):
        if not is_cache:
            tooltip(message, period=10000)
        else:
            print(message)

    # extract the field args
    # args don't have to be in the above order and  not necessarily have new lines
    args_string = filter_str.strip(f"{filter_prefix}[").strip("]")
    args_list = args_string.split(";")
    args_dict = {}
    for arg_str in args_list:
        # The last ; will produce an empty string as the last element, skip it
        if arg_str.strip() != "":
            try:
                key, value = arg_str.split("=")
            except ValueError:
                show_error_message(
                    f"Error in '{filter_prefix}[]' field args: Invalid argument '{arg_str}', did you forget '='?")
                return {}, is_cache, show_error_message
            # strip extra whitespace
            key = key.strip()
            # if the value is wrapped with [], it's an array of ''-wrapped values separated by comma
            if value.startswith("[") and value.endswith("]"):
                value = value.strip("[]").split(",")
                value = [v.strip().strip("'") for v in value]
            else:
                # it's a single ''-wrapped value
                value = value.strip().strip("'")
            args_dict[key] = value

    # check each arg key is valid, gather a list of the invalid and then show error about those
    invalid_keys = []
    for key in args_dict.keys():
        if key not in valid_args:
            invalid_keys.append(key)
    if len(invalid_keys) > 0:
        show_error_message(
            f"Error in '{filter_prefix}[]' field args: Unrecognized arguments: {', '.join(invalid_keys)}"
        )
        return {}, is_cache, show_error_message

    # No extra invalid keys? Check that we have all valid keys then
    def check_key(key):
        try:
            return args_dict[key]
        except KeyError:
            return None

    return {key: check_key(key) for key in valid_args}, is_cache, show_error_message
