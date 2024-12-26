from anki import hooks
from anki.cards import Card
from anki.notes import Note
from aqt import mw
from aqt.gui_hooks import reviewer_did_answer_card, editor_did_unfocus_field

from ..utils import write_custom_data
from ..configuration import Config
from ..logic.copy_fields import copy_for_single_trigger_note


def run_copy_fields_on_add(note: Note, deck_id: int):
    config = Config()
    config.load()

    note_type = note.note_type()
    if not note_type:
        # Error situation, note_type should exist when adding note
        return
    note_type_name = note_type["name"]

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
        if note_type_name not in copy_into_note_types:
            continue

        # No need to merge undo entries for adding a note as undoing the add
        # will remove the note entirely
        copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
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
    note = card.note()
    note_type = note.note_type()
    if not note_type:
        # Error situation, note_type should exist when reviewing card
        return
    note_type_name = note_type["name"]

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
        if note_type_name not in copy_into_note_types:
            continue

        # Get the current Answer card undo entry
        undo_status = mw.col.undo_status()
        answer_card_undo_entry = undo_status.last_step
        copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            multiple_note_types=multiple_note_types,
            undo_entry=answer_card_undo_entry,
        )
        write_custom_data(card, key="fc", value="1")
        # update_card adds a new undo entry Update card
        mw.col.update_card(card)
        # update_note adds a new undo entry Update note
        mw.col.update_note(note)
        # But now they are both merged into the Answer card undo entry
        mw.col.merge_undo_entries(answer_card_undo_entry)


def run_copy_fields_on_unfocus_field(changed: bool, note: Note, field_name: str):
    config = Config()
    config.load()
    changed = False
    note_type = note.note_type()
    if not note_type:
        # Error situation, note_type should exist when unfocusing field
        return changed
    note_type_name = note_type["name"]

    for copy_definition in config.copy_definitions:
        copy_into_note_types = copy_definition.get("copy_into_note_types", None)
        if not copy_into_note_types:
            continue
        # Split note_types by comma
        copy_into_note_types = copy_into_note_types.strip('""').split('", "')
        multiple_note_types = len(copy_into_note_types) > 1
        if note_type_name not in copy_into_note_types:
            continue

        # Check field-to-field defs for a match on this field
        field_to_field_defs = copy_definition.get("field_to_field_defs")
        if not field_to_field_defs:
            continue

        # get field-to-field matching this field
        field_to_field_def = None
        for f in field_to_field_defs:
            if f.get("copy_into_note_field") == field_name:
                field_to_field_def = f
                break
        if not field_to_field_def:
            continue

        if not field_to_field_def.get("copy_on_unfocus"):
            continue

        # Don't need to merge undo entries for unfocusing a field
        changed = copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            field_only=field_name,
            multiple_note_types=multiple_note_types,
        )

    return changed


def init_note_hooks():
    hooks.note_will_be_added.append(
        lambda _col, note, deck_id: run_copy_fields_on_add(note, deck_id)
    )
    reviewer_did_answer_card.append(
        lambda reviewer, card, ease: run_copy_fields_on_review(card)
    )
    editor_did_unfocus_field.append(
        lambda changed, note, field_idx: run_copy_fields_on_unfocus_field(
            changed, note, note.keys()[field_idx]
        )
    )
