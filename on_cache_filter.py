import math
import time

from anki.template import TemplateRenderContext
from aqt import mw

from .utils import write_custom_data


def on_cache_filter(
        text: str, field_name: str, filter: str, context: TemplateRenderContext
) -> str:
    """
     The filter syntax is like this:
     {{cache[cache_field]:Field}}
        where Field is the field to be cached which can be the result of another
        custom filters.
        The field will be cached for the number of days set in the configuration.
    """

    if not (filter.startswith("cache[") and filter.endswith("]")):
        print("Not cache filter")
        return text

    is_cache = None
    try:
        is_cache = context.extra_state["is_cache"]
    except KeyError:
        is_cache = False

    if not is_cache:
        # If we are not caching, no need to do anything
        return text

    cache_field = filter[6:-1]

    # Cache result into the note's cache_field if we have one
    if cache_field is not None:
        try:
            cache_field_ord = context.note().keys().index(cache_field)
            context.note().fields[cache_field_ord] = text
            mw.col.update_note(context.note())
            # Set cache time into card.custom_data
            card = context.card()
            write_custom_data(card, "fc", math.floor(time.time()))
            mw.col.update_card(card)
        except ValueError:
            print(f"Error: cache_field {cache_field} not found in note")
            pass

    return text
