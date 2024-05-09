from anki import hooks
from anki.consts import *
from anki.template import TemplateRenderContext
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




def on_field_filter(
    text: str, field_name: str, filter: str, context: TemplateRenderContext
) -> str:
    if not filter.startswith("fetch-"):
        return ''

    # extract the field args
    _, args = filter.split("-", maxsplit=1)

    # args should be a ;-separated list of values like
    # "did=<deck_id>;deck_name=<deck_name>;mid=<note_type_id>note_type_name=<note_type_name>;card_id_fld_name=<note_fld_name_to_get_card_by>;fld_name_to_get_from_card=<note_field_name_to_get>;pick_card_by=random/least_reps[ord]"
    # but not necessarily in that order
    # extract each arg
    args_list = args.split(";")
    args_dict = {}
    for arg in args_list:
        key, value = arg.split("=")
        args_dict[key] = value.strip()
    # check each arg key is valid, gather a list of the invalid and then show tooltip about those
    valid_args = ["did", "deck_name", "mid", "note_type_name", "card_id_fld_name", "fld_name_to_get_from_card", "pick_card_by"]
    present_args = []
    invalid_keys = []
    for key in args_dict.keys():
        if key not in valid_args:
            invalid_keys.append(key)
    if len(invalid_keys) > 0:
        tooltip(
            f"Error in 'fetch-' field args: Unrecognized arguments: {', '.join(invalid_keys)}",
            parent=mw.app.activeWindow(),
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
            tooltip("Error in 'fetch-' field args: Either 'did=' or 'deck_name=' value must be provided")
            return ''

    # Get mid either directly or through note_type_name
    mid = check_key("mid")
    if mid is None:
        note_type_name = check_key("note_type_name")
        if note_type_name is not None:
            mid = mw.col.models.id_for_name(note_type_name)
            if mid is None:
                tooltip(f"Error in 'fetch-' field args: Note type for note_type_name='{note_type_name}' not found, check your spelling")
                return ''
        else:
            tooltip("Error in 'fetch-' field args: Either 'mid=' or 'note_type_name=' value must be provided")
            return ''

    card_id_fld_name = check_key("card_id_fld_name")
    if card_id_fld_name is None:
        tooltip("Error in 'fetch-' field args: 'card_id_fld_name=' value must be provided")
        return ''

    fld_name_to_get_from_card = check_key("fld_name_to_get_from_card")
    if fld_name_to_get_from_card is None:
        tooltip(
            "Error in 'fetch-' field args: 'fld_name_to_get_from_card=' value must be provided")
        return ''

    pick_card_by = check_key("pick_card_by")
    if pick_card_by is None:
        tooltip("Error in 'fetch-' field args: 'pick_card_by=' value must be provided")
        return ''

    # First, fetch the ord value of the card_id_fld_name
    model = mw.col.models.get(mid)
    if model is None:
        tooltip(f"Error in 'fetch-' field args: Note type for mid='{mid}' not found, check your spelling")
        return ''

    def get_ord_from_model(fld_name):
        card_id_fld = next((f for f in model["flds"] if f["name"] == fld_name), None)
        if card_id_fld is not None:
            return card_id_fld["ord"]
        else:
            tooltip(
                f"Error in 'fetch-' field args: No field with name '{fld_name}' found in the note type '{model['name']}'")
            return ''

    fld_ord_to_id_card = get_ord_from_model(card_id_fld_name)
    fld_ord_to_get = get_ord_from_model(fld_name_to_get_from_card)

    # Now use the ord value to query the notes
    notes = mw.col.db.all(
        f"""
        SELECT
            id,
            flds
        FROM notes
        WHERE mid = {mid}
        AND 
        AND (
            SELECT SUBSTR(
                SUBSTR(flds, 0, INSTR(flds, X'1f', 1, {fld_ord_to_id_card} * 2) + 1),
                INSTR(flds, X'1f', 1, {fld_ord_to_id_card} * 2) - INSTR(flds, X'1f', 1, {fld_ord_to_id_card} * 2, 1) - 1
            )
        ) LIKE '{text}'
        """
    )
    # Make note ids str for the next query
    note_ids = [note[0] for note in notes]
    if len(note_ids) == 0:
        tooltip(f"Error in 'fetch-' query: Did not find any notes where '{card_id_fld_name}' contains '{text}'")
        return ''
    note_ids_str = ids2str(note_ids)

    # Next, find cards with did and nid in the note_ids
    cards = mw.col.db.all(
        f"""
        SELECT
            id
            nid
        FROM cards
        WHERE (did = {did} OR odid = {did})
        AND nid IN ({note_ids_str})
        """
    )
    # Loop through cards and find the one with the least reviews
    least_revs_card = min(cards, key=lambda c: mw.col.db.scalar(f"SELECT COUNT() FROM revlog WHERE cid = {c[0]}"))
    least_revs_note_id = least_revs_card[1]

    # And finally, return the value from the field in the note
    target_note_vals_str = mw.col.db.scalar(f"SELECT flds FROM notes WHERE id = {least_revs_note_id}")
    target_note_vals = target_note_vals_str.split("\x1f")
    return target_note_vals[fld_ord_to_get]


hooks.field_filter.append(on_field_filter)