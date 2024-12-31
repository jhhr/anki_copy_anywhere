from typing import Union, Tuple
from anki.hooks import note_will_be_added
from anki.cards import Card
from anki.notes import Note, NoteId
from aqt.editor import Editor, EditorMode
from aqt import mw
from aqt.gui_hooks import (
    reviewer_did_answer_card,
    editor_did_unfocus_field,
    editor_did_load_note,
    add_cards_did_add_note,
)

from ..utils import write_custom_data, definition_modifies_other_notes
from ..configuration import (
    Config,
    CopyDefinition,
)
from ..logic.copy_fields import copy_for_single_trigger_note, copy_fields


def run_copy_fields_on_add(note: Note, deck_id: int):
    """
    Copy fields when a note is about to be added. This applies to notes being added
    by AnkiConnect or the Add cards dialog. Because the note is not yet added to the
    database, we can't get the note ID, so we can't copy fields that affect other notes.
    """
    config = Config()
    config.load()

    note_type = note.note_type()
    if not note_type:
        # Error situation, note_type should exist when adding note
        return
    note_type_name = note_type["name"]

    # Copy definitions that affect other notes need an undo entry as we want to be able to undo
    # editing_other_notes_definitions: list[CopyDefinition] = []

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

        # if not definition_edits_other_notes(copy_definition):
        #     editing_other_notes_definitions.append(copy_definition)
        # else:
        # No need to merge undo entries for adding a note as undoing the add
        # will remove the note entirely, just run these right away
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


editor_for_note_id: dict[EditorMode, Union[Tuple[Editor, NoteId], None]] = {
    EditorMode.ADD_CARDS: None,
    EditorMode.BROWSER: None,
    EditorMode.EDIT_CURRENT: None,
}


def on_editor_did_load_note(editor: Editor):
    """
    Store the editor and note_id in a global dict for later use in other hooks.
    This is a hack to get around the fact that the editor is not passed to the
    unfocus_field hook.
    """
    global editor_for_note_id
    editor_for_note_id[editor.editorMode] = editor, editor.note.id if editor.note else NoteId(0)


def run_copy_fields_on_unfocus_field(changed: bool, note: Note, field_idx: int) -> bool:
    is_new_note = note.id == 0

    editors_matching_note_id = [
        # There can be three editors open at the same time:
        # ADD_CARDS = the new note adder
        # BROWSER = the note/card browser
        # EDIT CURRENT = the note editor in the reviewer
        #
        # The note_id in the ADD_CARDS editor is always 0, and there can only be one of them.
        # So, if the current note.id == 0, the only editor in the list will be the ADD_CARDS editor.
        #
        # However, the BROWSER and EDIT_CURRENT editors could potentially be both open to the
        # same note. Only one of them has actually triggered the unfocus_field event, but
        # we can't know which one. As a workaround, we'll just trigger the loadNote() on both
        # in such a case
    ]
    for maybe_editor_tuple in editor_for_note_id.values():
        if not maybe_editor_tuple:
            continue
        editor, note_id = maybe_editor_tuple
        if note.id == note_id and editor:
            editors_matching_note_id.append(editor)

    config = Config()
    config.load()
    changed = False
    note_type = note.note_type()
    if not note_type:
        # Error situation, note_type should exist when unfocusing field
        return changed
    note_type_name = note_type["name"]
    field_name = note.keys()[field_idx]
    initial_field_value = note.fields[field_idx]

    # Copy definitions that affect other notes need an undo entry as we want to be able to undo
    editing_other_notes_definitions: list[CopyDefinition] = []

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

        if is_new_note and not field_to_field_def.get("copy_on_unfocus_when_add"):
            continue

        if not is_new_note and not field_to_field_def.get("copy_on_unfocus_when_edit"):
            continue

        if (
            definition_modifies_other_notes(copy_definition)
            # Do not run ops that edit other notes while editing a new note. Such ops should only
            # be run when the new note is saved.
            and not is_new_note
        ):
            editing_other_notes_definitions.append(copy_definition)
        else:
            # Either within note or destination to sources, we can run these right away
            success = copy_for_single_trigger_note(
                copy_definition=copy_definition,
                trigger_note=note,
                field_only=field_name,
                multiple_note_types=multiple_note_types,
                is_note_editor=True,
            )

            changed = success or changed

    if editing_other_notes_definitions:
        # Use the CollectionOp version so we get the full report and undo_entry
        copy_fields(
            copy_definitions=editing_other_notes_definitions,
            note_ids=[note.id],
            field_only=field_name,
            undo_text_suffix=f"triggered by unfocus field '{field_name}'",
            is_note_editor=True,
        )

    cur_field_value = note[field_name]
    if changed and editors_matching_note_id and cur_field_value != initial_field_value:
        for editor in editors_matching_note_id:
            editor.loadNote()
    return changed


def init_note_hooks():
    editor_did_load_note.append(on_editor_did_load_note)
    note_will_be_added.append(lambda _col, note, deck_id: run_copy_fields_on_add(note, deck_id))
    reviewer_did_answer_card.append(lambda reviewer, card, ease: run_copy_fields_on_review(card))
    editor_did_unfocus_field.append(run_copy_fields_on_unfocus_field)
