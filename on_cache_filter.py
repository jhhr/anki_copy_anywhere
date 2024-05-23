import json
import math
import time
from operator import itemgetter

from anki.template import TemplateRenderContext
from aqt import mw

from .configuration import Config
from .utils import write_custom_data, filter_init

VALID_ARGS = ["cache_field", "only_empty", "ignore_if_cached"]


def on_cache_filter(
        text: str, field_name: str, filter_str: str, context: TemplateRenderContext
) -> str:
    """
     The filter syntax is like this:
     {{cache[
         cache_field='cache_field';
         only_empty='only_empty(=False)'
         ignore_if_cached='ignore_if_cached(=True)'
     ]:Field}}
        where Field is the field to be cached which can be the result of another
        custom filters.
        The field will be cached for the number of days set in the configuration.

    With the default behaviour the field will be displayed from the cache if it exists
    When rendering the card and the cache has expired, it is automatically updated.
    """

    if not (filter_str.startswith("cache[") and filter_str.endswith("]")):
        return text

    args_dict, is_cache, show_error_message = filter_init("cache", VALID_ARGS, filter_str, context)

    (
        cache_field,
        only_empty,
        ignore_if_cached
    ) = itemgetter(
        "cache_field",
        "only_empty",
        "ignore_if_cached"
    )(args_dict)

    if cache_field is None:
        show_error_message("Error in cache[]: cache_field is required")
        return text

    if ignore_if_cached is not None:
        ignore_if_cached = ignore_if_cached.lower() == "true" or ignore_if_cached == "1"
    else:
        ignore_if_cached = True

    config = Config()
    config.load()

    cache_is_expired = False
    if ignore_if_cached and not is_cache:
        # Check if the cache is still valid
        card = context.card()
        custom_data = card.custom_data
        if custom_data != "":
            custom_data = json.loads(custom_data)
            if "fc" in custom_data:
                cache_time = custom_data["fc"]
                if cache_time is not None:
                    cache_time = int(cache_time)
                    if time.time() - cache_time < config.days_to_cache_fields_auto * 86400:
                        # We don't return anything, so there isn't two sets of this data in the
                        # template when viewing the card
                        return ''
                    else:
                        # Cache is invalid, so we need to update it
                        cache_is_expired = True

    if not is_cache and not cache_is_expired:
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
            # only_empty can override the functionality of ignore_if_cached causing the card to be updated
            # that's why the default only_empty is False and ignore_if_cached is True
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
