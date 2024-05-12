import base64
import math
import random
import time

from anki.consts import QUEUE_TYPE_SUSPENDED
from anki.decks import DeckManager
from anki.template import TemplateRenderContext
from anki.utils import ids2str
from aqt import mw
from aqt.utils import tooltip

from .utils import write_custom_data


def get_ord_from_model(model, fld_name):
    card_id_fld = next((f for f in model["flds"] if f["name"] == fld_name), None)
    if card_id_fld is not None:
        return card_id_fld["ord"]
    return None


def on_field_filter(
        text: str, field_name: str, filter: str, context: TemplateRenderContext
) -> str:
    """
     The filter syntax is like this:
     {{fetch[
      did='deck_id';
      deck_name='deck_name';
      mid='note_type_id'
      note_type_name='note_type_name';
      card_id_fld_name='note_fld_name_to_get_card_by';
      fld_name_to_get_from_card='note_field_name_to_get';
      pick_card_by='random'/'random_stable'/'least_reps[ord]';
      cache_field='cache_field'
     ]:text}}
    """
    if not (filter.startswith("fetch[") and filter.endswith("]")):
        return text

    is_cache = None
    try:
        is_cache = context.extra_state["is_cache"]
    except KeyError:
        is_cache = False

    def show_error_message(message: str):
        # caching op is background, so we can't show tooltip
        if not is_cache:
            tooltip(message, period=10000)
        else:
            print(message)

    # extract the field args
    # args don't have to be in the above order and  not necessarily have new lines
    args_string = filter.strip("fetch[").strip("]")
    args_list = args_string.split(";")
    args_dict = {}

    # Get args from the string
    for arg_str in args_list:
        try:
            key, value = arg_str.split("=", maxsplit=1)
        except ValueError:
            show_error_message(f"Error in 'fetch=[]' field args: Invalid argument '{arg_str}', did you forget '='?")
            return ''
        # strip extra whitespace
        key = key.strip()
        # and also '' around value
        value = value.strip().strip("'")
        args_dict[key] = value

    # check each arg key is valid, gather a list of the invalid and then show error about those
    valid_args = ["did", "deck_name", "mid", "note_type_name", "card_id_fld_name", "fld_name_to_get_from_card",
                  "pick_card_by", "cache_field"]
    invalid_keys = []
    for key in args_dict.keys():
        if key not in valid_args:
            invalid_keys.append(key)
    if len(invalid_keys) > 0:
        show_error_message(
            f"Error in 'fetch=[]' field args: Unrecognized arguments: {', '.join(invalid_keys)}"
        )
        return ''

    # No extra invalid keys? Check that we have all valid keys then
    def check_key(key):
        try:
            return args_dict[key]
        except KeyError:
            return None

    # Get did either directly or through deck_name
    did = check_key("did")
    if did is None:
        deck_name = check_key("deck_name")
        if deck_name is not None:
            did = mw.col.decks.id_for_name(deck_name)
        else:
            show_error_message(
                "Error in 'fetch=[]' field args: Either 'did=' or 'deck_name=' value must be provided"
            )
            return ''

    # Get mid either directly or through note_type_name
    mid = check_key("mid")
    if mid is None:
        note_type_name = check_key("note_type_name")
        if note_type_name is not None:
            mid = mw.col.models.id_for_name(note_type_name)
            if mid is None:
                show_error_message(
                    f"Error in 'fetch=[]' field args: Note type for note_type_name='{note_type_name}' not found, check your spelling",
                )
                return ''
        else:
            show_error_message(
                "Error in 'fetch=[]' field args: Either 'mid=' or 'note_type_name=' value must be provided")
            return ''

    card_id_fld_name = check_key("card_id_fld_name")
    if card_id_fld_name is None:
        show_error_message("Error in 'fetch=[]' field args: 'card_id_fld_name=' value must be provided")
        return ''

    fld_name_to_get_from_card = check_key("fld_name_to_get_from_card")
    if fld_name_to_get_from_card is None:
        show_error_message(
            "Error in 'fetch=[]' field args: 'fld_name_to_get_from_card=' value must be provided",
        )
        return ''

    pick_card_by = check_key("pick_card_by")
    pick_card_by_valid_values = ('random', 'random_stable', 'least_reps')
    if pick_card_by is None:
        show_error_message("Error in 'fetch=[]' field args: 'pick_card_by=' value must be provided")
        return ''
    elif pick_card_by not in pick_card_by_valid_values:
        show_error_message(
            f"Error in 'fetch=[]' field args: 'pick_card_by=' value must be one of {pick_card_by_valid_values}",
        )

    # First, fetch the ord value of the card_id_fld_name
    model = mw.col.models.get(mid)
    if model is None:
        show_error_message(
            f"Error in 'fetch=[]' field args: Note type for mid='{mid}' not found, check your spelling"
        )
        return ''

    fld_ord_to_id_card = get_ord_from_model(model, card_id_fld_name)
    fld_ord_to_get = get_ord_from_model(model, fld_name_to_get_from_card)
    if fld_ord_to_get is None:
        show_error_message(
            f"Error in 'fetch=[]' field args: No field with name '{fld_name_to_get_from_card}' found in the note type '{model['name']}'"
        )
        return ''

    # Now select from the notes table the ones we have a matching field value
    # `flds` is a string containing a list of values separated by a 0x1f character)
    # We need to get the value in that list in index `fld_ord_to_id_card`
    # and test whether it has a substring `text`
    note_ids = None
    # First, check if we have cached the note_ids from a similar query already in extra_state
    notes_query_id = base64.b64encode(f"note_ids{mid}{fld_ord_to_id_card}{text}".encode()).decode()
    try:
        note_ids = context.extra_state[notes_query_id]
    except KeyError:
        note_ids = []
        for note_id, fields_str in mw.col.db.all(f"select id, flds from notes where mid={mid}"):
            if fields_str is not None:
                fields = fields_str.split("\x1f")
                if text in fields[fld_ord_to_id_card]:
                    note_ids.append(note_id)
                    context.extra_state[notes_query_id] = note_ids

    if len(note_ids) == 0:
        show_error_message(
            f"Error in 'fetch=[]' query: Did not find any notes where '{card_id_fld_name}' contains '{text}'"
        )
        if is_cache:
            # Set cache time into card.customData, so we don't keep querying this again
            write_custom_data(context.card(), "fc", math.floor(time.time()))
            mw.col.update_card(context.card())
        return ''
    else:
        print(f"Found {len(note_ids)} notes with '{card_id_fld_name}' containing '{text}'")
    note_ids_str = ids2str(note_ids)

    # Next, find cards with did and nid in the note_ids
    # Check for cached result again
    DM = DeckManager(mw.col)

    did_list = ids2str(DM.deck_and_child_ids(did))

    cards_query_id = base64.b64encode(f"cards{did_list}{mid}{note_ids_str}".encode()).decode()
    try:
        cards = context.extra_state[cards_query_id]
    except KeyError:
        cards = mw.col.db.all(
            f"""
            SELECT
                id,
                nid
            FROM cards
            WHERE (did IN {did_list} OR odid IN {did_list})
            AND nid IN {note_ids_str}
            AND queue != {QUEUE_TYPE_SUSPENDED}
            """
        )
        context.extra_state[cards_query_id] = cards

    if (len(cards) == 0):
        show_error_message(
            f"Error in 'fetch=[]' query: Did not find any non-suspended cards with did={did} for the notes whose '{card_id_fld_name}' contains '{text}'")
        if is_cache:
            # Set cache time into card.customData, so we don't keep querying this again
            write_custom_data(context.card(), "fc", math.floor(time.time()))
            mw.col.update_card(context.card())
        return ''

    # select a card based on the pick_card_by value
    selected_card = None
    card_select_key = base64.b64encode(f"selected_card{did_list}{mid}{note_ids_str}{pick_card_by}".encode()).decode()
    if pick_card_by == 'random':
        # We don't want to cache this as it should in fact be different each time
        selected_card = random.choice(cards)
    elif pick_card_by == 'random_stable':
        # pick the same random card for the same deck_id and mid combination
        try:
            selected_card = context.extra_state[card_select_key]
        except KeyError:
            selected_card = random.choice(cards)
            context.extra_state[card_select_key] = selected_card
    elif pick_card_by == 'least_reps':
        # Loop through cards and find the one with the least reviews
        # Check cache first
        try:
            selected_card = context.extra_state[card_select_key]
        except KeyError:
            selected_card = min(cards, key=lambda c: mw.col.db.scalar(f"SELECT COUNT() FROM revlog WHERE cid = {c[0]}"))
            context.extra_state = {}
            context.extra_state[card_select_key] = selected_card
    if selected_card is None:
        show_error_message("Error in 'fetch=[]' query: could not select card")

    selected_note_id = selected_card[1]

    # And finally, return the value from the field in the note
    # Check for cached result again
    result_val_key = base64.b64encode(f"{selected_note_id}{fld_ord_to_get}".encode()).decode()
    try:
        return context.extra_state[result_val_key]
    except KeyError:
        pass

    target_note_vals_str = mw.col.db.scalar(f"SELECT flds FROM notes WHERE id = {selected_note_id}")
    if target_note_vals_str is not None:
        target_note_vals = target_note_vals_str.split("\x1f")
        result_val = target_note_vals[fld_ord_to_get]
        context.extra_state[result_val_key] = result_val
        if is_cache:
            # Cache result into the note's cache_field if we have one
            cache_field = check_key("cache_field")
            if cache_field is not None:
                try:
                    cache_field_ord = context.note().keys().index(cache_field)
                    context.note().fields[cache_field_ord] = result_val
                    mw.col.update_note(context.note())
                    # Set cache time into card.customDate
                    card = context.card()
                    write_custom_data(card, "fc", math.floor(time.time()))
                    mw.col.update_card(card)
                    print(f"Result: note_id={context.note().id} ", result_val)
                except ValueError:
                    return ''
        else:
            return result_val

    return ''
