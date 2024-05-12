import base64
import math
import random
import time
from operator import itemgetter

from anki.consts import QUEUE_TYPE_SUSPENDED
from anki.decks import DeckManager
from anki.template import TemplateRenderContext
from anki.utils import ids2str
from aqt import mw

from .utils import write_custom_data, filter_init


def get_ord_from_model(model, fld_name):
    card_id_fld = next((f for f in model["flds"] if f["name"] == fld_name), None)
    if card_id_fld is not None:
        return card_id_fld["ord"]
    return None


VALID_ARGS = ["did", "deck_name", "mid",
              "note_type_name", "card_id_fld_name",
              "fld_name_to_get_from_card",
              "pick_card_by", "multiple", "multi_sep"]

PICK_CARD_BY_VALID_VALUES = ('random', 'random_stable', 'least_reps')


def on_fetch_filter(
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
      multiple='number_of_cards_to_get';
      multi_sep='separator_for_multiple_results(default=", ")';
     ]:Field}}
    """
    if not (filter.startswith("fetch[") and filter.endswith("]")):
        return text

    args_dict, is_cache, show_error_message = filter_init("fetch", VALID_ARGS, filter, context)

    (
        did,
        deck_name,
        mid,
        note_type_name,
        card_id_fld_name,
        fld_name_to_get_from_card,
        pick_card_by,
        multiple,
        multi_sep
    ) = itemgetter(
        "did",
        "deck_name",
        "mid",
        "note_type_name",
        "card_id_fld_name",
        "fld_name_to_get_from_card",
        "pick_card_by",
        "multiple",
        "multi_sep"
    )(args_dict)

    # Get did either directly or through deck_name
    if did is None:
        if deck_name is not None:
            did = mw.col.decks.id_for_name(deck_name)
        else:
            show_error_message(
                "Error in 'fetch[]' field args: Either 'did=' or 'deck_name=' value must be provided"
            )
            return ''

    # Get mid either directly or through note_type_name
    if mid is None:
        if note_type_name is not None:
            mid = mw.col.models.id_for_name(note_type_name)
            if mid is None:
                show_error_message(
                    f"Error in 'fetch[]' field args: Note type for note_type_name='{note_type_name}' not found, check your spelling",
                )
                return ''
        else:
            show_error_message(
                "Error in 'fetch[]' field args: Either 'mid=' or 'note_type_name=' value must be provided")
            return ''

    if card_id_fld_name is None:
        show_error_message("Error in 'fetch[]' field args: 'card_id_fld_name=' value must be provided")
        return ''

    if fld_name_to_get_from_card is None:
        show_error_message(
            "Error in 'fetch[]' field args: 'fld_name_to_get_from_card=' value must be provided",
        )
        return ''

    if pick_card_by is None:
        show_error_message("Error in 'fetch[]' field args: 'pick_card_by=' value must be provided")
        return ''
    elif pick_card_by not in PICK_CARD_BY_VALID_VALUES:
        show_error_message(
            f"Error in 'fetch[]' field args: 'pick_card_by=' value must be one of {PICK_CARD_BY_VALID_VALUES}",
        )
        return ''

    if multiple:
        try:
            multiple = int(multiple)
            if multiple < 1:
                raise ValueError
        except ValueError:
            show_error_message(
                "Error in 'fetch[]' field args: 'multiple=' value must be a positive integer"
            )
            return ''
    else:
        multiple = 1

    if multi_sep is None:
        multi_sep = ", "

    # First, fetch the ord value of the card_id_fld_name
    model = mw.col.models.get(mid)
    if model is None:
        show_error_message(
            f"Error in 'fetch[]' field args: Note type for mid='{mid}' not found, check your spelling"
        )
        return ''

    fld_ord_to_id_card = get_ord_from_model(model, card_id_fld_name)
    fld_ord_to_get = get_ord_from_model(model, fld_name_to_get_from_card)
    if fld_ord_to_get is None:
        show_error_message(
            f"Error in 'fetch[]' field args: No field with name '{fld_name_to_get_from_card}' found in the note type '{model['name']}'"
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
            f"Error in 'fetch[]' query: Did not find any notes where '{card_id_fld_name}' contains '{text}'"
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

    cards_query_id = base64.b64encode(f"cards{did_list}{mid}{card_id_fld_name}".encode()).decode()
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
            f"Error in 'fetch[]' query: Did not find any non-suspended cards with did={did} for the notes whose '{card_id_fld_name}' contains '{text}'")
        if is_cache:
            # Set cache time into card.customData, so we don't keep querying this again
            write_custom_data(context.card(), "fc", math.floor(time.time()))
            mw.col.update_card(context.card())
        return ''

    # select a card or cards based on the pick_card_by value
    selected_cards = []
    result_val = ""
    for i in range(multiple):
        # remove already selected cards from cards
        selected_card = None
        selected_val = ""
        card_select_key = base64.b64encode(
            f"selected_card{did_list}{mid}{fld_name_to_get_from_card}{pick_card_by}{i}".encode()).decode()
        if pick_card_by == 'random':
            # We don't want to cache this as it should in fact be different each time
            selected_card = random.choice(cards)
        elif pick_card_by == 'random_stable':
            # pick the same random card for the same deck_id and mid combination
            # this will still work for multiple as we're caching the selected card by the index too
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
                selected_card = min(cards,
                                    key=lambda c: mw.col.db.scalar(f"SELECT COUNT() FROM revlog WHERE cid = {c[0]}"))
                context.extra_state = {}
                context.extra_state[card_select_key] = selected_card
        if selected_card is None:
            show_error_message("Error in 'fetch[]' query: could not select card")

        selected_cards.append(selected_card)
        # Remove selected card so it can't be picked again
        cards = [c for c in cards if c != selected_card]
        selected_note_id = selected_card[1]

        # And finally, return the value from the field in the note
        # Check for cached result again
        result_val_key = base64.b64encode(f"{selected_note_id}{fld_ord_to_get}{i}".encode()).decode()
        try:
            selected_val = context.extra_state[result_val_key]
        except KeyError:
            target_note_vals_str = mw.col.db.scalar(f"SELECT flds FROM notes WHERE id = {selected_note_id}")
            if target_note_vals_str is not None:
                target_note_vals = target_note_vals_str.split("\x1f")
                selected_val = target_note_vals[fld_ord_to_get]
                context.extra_state[result_val_key] = selected_val

        result_val += f"{multi_sep if i > 0 else ''}{selected_val}"

        # If we've run out of cards, stop and return what we got
        if len(cards) == 0:
            break

    return result_val
