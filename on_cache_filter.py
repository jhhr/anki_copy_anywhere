import math
import time
from operator import itemgetter

from anki.template import TemplateRenderContext
from aqt import mw

from .utils import write_custom_data, filter_init

VALID_ARGS = ["cache_field", "only_empty"]


def on_cache_filter(
        text: str, field_name: str, filter: str, context: TemplateRenderContext
) -> str:
    """
     The filter syntax is like this:
     {{cache[
         cache_field='cache_field';
         only_empty='only_empty(=False)'
     ]:Field}}
        where Field is the field to be cached which can be the result of another
        custom filters.
        The field will be cached for the number of days set in the configuration.
    """

    if not (filter.startswith("cache[") and filter.endswith("]")):
        return text

    args_dict, is_cache, show_error_message = filter_init("cache", VALID_ARGS, filter, context)

    cache_field, only_empty = itemgetter("cache_field", "only_empty")(args_dict)

    if cache_field is None:
        show_error_message("Error in cache[]: cache_field is required")
        return text

    if not is_cache:
        # We're not caching, so we don't need to do anything
        return text

    if only_empty is not None:
        only_empty = only_empty.lower() == "true" or only_empty == "1"
    else:
        only_empty = False

    # Cache result into the note's cache_field if we have one
    if cache_field is not None:
        try:
            cache_field_ord = context.note().keys().index(cache_field)
            if only_empty and context.note().fields[cache_field_ord] != "":
                return text
            context.note().fields[cache_field_ord] = text
            mw.col.update_note(context.note())
            # Set cache time into card.custom_data
            card = context.card()
            write_custom_data(card, "fc", math.floor(time.time()))
            mw.col.update_card(card)
        except ValueError:
            show_error_message(f"Error in cache[]: cache_field {cache_field} not found in note")
            pass

    return text
