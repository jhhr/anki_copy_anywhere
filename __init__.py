import random

from anki import hooks
from anki.consts import *
from anki.template import TemplateRenderContext, TemplateRenderOutput
from anki.utils import ids2str
from aqt import mw
from aqt.utils import tooltip


def gc(arg, fail=False):
    try:
        out = mw.addonManager.getConfig(__name__).get(arg, fail)
    except:
        return fail
    else:
        return out


random_stable_dict = {}


def reset_random_stable_dict(output: TemplateRenderOutput, context: TemplateRenderContext):
    # After card render completes, reset the dict, so we start fresh on
    # 1. the next review
    # 2. if we close the reviewer and open it again
    # 3. edit the card which causes re-render
    random_stable_dict.clear()


hooks.card_did_render.append(reset_random_stable_dict)

def on_field_filter(
        text: str, field_name: str, filter: str, context: TemplateRenderContext
) -> str:
    """
     The filter syntax is like this:
     {{fetch=[
      did='deck_id';
      deck_name='deck_name';
      mid='note_type_id'
      note_type_name='note_type_name';
      card_id_fld_name='note_fld_name_to_get_card_by';
      fld_name_to_get_from_card='note_field_name_to_get';
      pick_card_by='random'/'random_stable'/'least_reps[ord]';
     ]:text}}
    """
    if not filter.startswith("fetch=[") and filter.endswith("]"):
        return ''

    # extract the field args
    # args don't have to be in the above order and  not necessarily have new lines
    args_string = filter.strip("fetch=[").strip("]")
    args_list = args_string.split(";")
    args_dict = {}

    # Get args from the string
    for arg_str in args_list:
        print("arg_str", arg_str)
        key, value = arg_str.split("=", maxsplit=1)
        # strip extra whitespace
        key = key.strip()
        # and also '' around value
        value = value.strip().strip("'")
        args_dict[key] = value

    print("args_dict", args_dict)
    # check each arg key is valid, gather a list of the invalid and then show tooltip about those
    valid_args = ["did", "deck_name", "mid", "note_type_name", "card_id_fld_name", "fld_name_to_get_from_card",
                  "pick_card_by"]
    invalid_keys = []
    for key in args_dict.keys():
        if key not in valid_args:
            invalid_keys.append(key)
    if len(invalid_keys) > 0:
        tooltip(
            f"Error in 'fetch=[]' field args: Unrecognized arguments: {', '.join(invalid_keys)}",
            period=10000,
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
            tooltip("Error in 'fetch=[]' field args: Either 'did=' or 'deck_name=' value must be provided",
                    period=10000)
            return ''

    # Get mid either directly or through note_type_name
    mid = check_key("mid")
    if mid is None:
        note_type_name = check_key("note_type_name")
        if note_type_name is not None:
            mid = mw.col.models.id_for_name(note_type_name)
            if mid is None:
                tooltip(
                    f"Error in 'fetch=[]' field args: Note type for note_type_name='{note_type_name}' not found, check your spelling",
                    period=10000)
                return ''
        else:
            tooltip("Error in 'fetch=[]' field args: Either 'mid=' or 'note_type_name=' value must be provided",
                    period=10000)
            return ''

    card_id_fld_name = check_key("card_id_fld_name")
    if card_id_fld_name is None:
        tooltip("Error in 'fetch=[]' field args: 'card_id_fld_name=' value must be provided", period=10000)
        return ''

    fld_name_to_get_from_card = check_key("fld_name_to_get_from_card")
    if fld_name_to_get_from_card is None:
        tooltip(
            "Error in 'fetch=[]' field args: 'fld_name_to_get_from_card=' value must be provided",
            period=10000
        )
        return ''

    pick_card_by = check_key("pick_card_by")
    pick_card_by_valid_values = ('random', 'random_stable', 'least_reps')
    if pick_card_by is None:
        tooltip("Error in 'fetch=[]' field args: 'pick_card_by=' value must be provided", period=10000)
        return ''
    elif pick_card_by not in pick_card_by_valid_values:
        tooltip(f"Error in 'fetch=[]' field args: 'pick_card_by=' value must be one of {pick_card_by_valid_values}",
                period=10000)

    # First, fetch the ord value of the card_id_fld_name
    model = mw.col.models.get(mid)
    if model is None:
        tooltip(f"Error in 'fetch=[]' field args: Note type for mid='{mid}' not found, check your spelling",
                period=10000)
        return ''

    def get_ord_from_model(fld_name):
        card_id_fld = next((f for f in model["flds"] if f["name"] == fld_name), None)
        if card_id_fld is not None:
            return card_id_fld["ord"]
        else:
            tooltip(
                f"Error in 'fetch=[]' field args: No field with name '{fld_name}' found in the note type '{model['name']}'",
                period=10000
            )
            return ''

    fld_ord_to_id_card = get_ord_from_model(card_id_fld_name)
    fld_ord_to_get = get_ord_from_model(fld_name_to_get_from_card)

    # Now select from the notes table the ones we have a matching field value
    # `flds` is a string containing a list of values separated by a 0x1f character)
    # We need to get the value in that list in index `fld_ord_to_id_card`
    # and test whether it has a substring `text`
    note_ids = []
    for note_id, fields_str in mw.col.db.all(f"select id, flds from notes where mid={mid}"):
        if fields_str is not None:
            fields = fields_str.split("\x1f")
            if text in fields[fld_ord_to_id_card]:
                note_ids.append(note_id)

    if len(note_ids) == 0:
        tooltip(f"Error in 'fetch=[]' query: Did not find any notes where '{card_id_fld_name}' contains '{text}'",
                period=10000)
        return ''
    note_ids_str = ids2str(note_ids)

    # Next, find cards with did and nid in the note_ids
    cards = mw.col.db.all(
        f"""
        SELECT
            id,
            nid
        FROM cards
        WHERE (did = {did} OR odid = {did})
        AND nid IN {note_ids_str}
        """
    )
    selected_card = None
    if pick_card_by == 'random':
        selected_card = random.choice(cards)
    elif pick_card_by == 'random_stable':
        # pick the same random card for the same deck_id and mid combination
        random_key = did + mid
        try:
            selected_card = random_stable_dict[random_key]
        except KeyError:
            selected_card = random.choice(cards)
            random_stable_dict[random_key] = selected_card
    elif pick_card_by == 'least_reps':
        # Loop through cards and find the one with the least reviews
        selected_card = min(cards, key=lambda c: mw.col.db.scalar(f"SELECT COUNT() FROM revlog WHERE cid = {c[0]}"))
    if selected_card is None:
        tooltip("Error in 'fetch=[]' query: could not select card", period=10000)
    selected_note_id = selected_card[1]

    # And finally, return the value from the field in the note
    target_note_vals_str = mw.col.db.scalar(f"SELECT flds FROM notes WHERE id = {selected_note_id}")
    if target_note_vals_str is not None:
        target_note_vals = target_note_vals_str.split("\x1f")
        return target_note_vals[fld_ord_to_get]
    return ''


hooks.field_filter.append(on_field_filter)
