from anki import hooks
from anki.cards import Card
from anki.notes import Note
from aqt.gui_hooks import reviewer_did_answer_card
from aqt import mw


from ..configuration import Config
from ..logic.copy_fields import copy_for_single_note


def run_copy_fields_on_add(note: Note, deck_id: int):
    config = Config()
    config.load()

    for copy_definition in config.copy_definitions:
        copy_on_add = copy_definition.get("copy_on_add", False)
        if not copy_on_add:
            continue
        copy_into_note_types = copy_definition.get("copy_into_note_types", None)
        if not copy_into_note_types:
            continue
        # Split note_types by comma
        copy_into_note_types = copy_into_note_types.strip('""').split('", "')
        multiple_note_types = len(copy_into_note_types) > 1
        if note.note_type()["name"] not in copy_into_note_types:
            continue

        copy_for_single_note(
            copy_definition=copy_definition,
            note=note,
            deck_id=deck_id,
            multiple_note_types=multiple_note_types,
        )


def run_copy_fields_on_review(card: Card):
    """
    Copy fields when a card is reviewed. Check whether the card's
    note type is in the list of copy_into_note_types for the copy_definition
    and run those.
    """
    config = Config()
    config.load()

    for copy_definition in config.copy_definitions:
        copy_on_review = copy_definition.get("copy_on_review", False)
        if not copy_on_review:
            continue
        copy_into_note_types = copy_definition.get("copy_into_note_types", None)
        # Split note_types by comma
        if not copy_into_note_types:
            continue
        copy_into_note_types = copy_into_note_types.strip('""').split('", "')
        multiple_note_types = len(copy_into_note_types) > 1
        note = card.note()
        if card.note().note_type()["name"] not in copy_into_note_types:
            continue

        # Merge undo entry for the review
        undo_status = mw.col.undo_status()
        undo_entry = undo_status.last_step
        copy_for_single_note(
            copy_definition=copy_definition,
            note=note,
            deck_id=card.did,
            multiple_note_types=multiple_note_types,
        )
        mw.col.update_note(note)
        mw.col.merge_undo_entries(undo_entry)


def init_note_hooks():
    hooks.note_will_be_added.append(
        lambda _col, note, deck_id: run_copy_fields_on_add(note, deck_id)
    )
    reviewer_did_answer_card.append(
        lambda reviewer, card, ease: run_copy_fields_on_review(card)
    )
