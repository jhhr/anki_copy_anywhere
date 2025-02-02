from typing import Union, Tuple
from anki.hooks import (
    note_will_be_added,
    # note_will_flush,
)
from anki.cards import Card
from anki.notes import Note, NoteId
from aqt.editor import Editor, EditorMode
from aqt import mw
from aqt.gui_hooks import (
    reviewer_did_answer_card,
    editor_did_unfocus_field,
    editor_did_load_note,
)

from ..utils import write_custom_data
from ..configuration import (
    Config,
    CopyDefinition,
    get_triggered_field_to_field_def_for_field,
    definition_modifies_other_notes,
)
from ..logic.copy_fields import (
    copy_for_single_trigger_note,
    copy_fields,
    make_copy_fields_undo_text,
)


def get_copy_definitions_for_add_note(note: Note, deck_id) -> list[CopyDefinition]:
    config = Config()
    config.load()
    note_type = note.note_type()
    if not note_type:
        # Error situation, note_type should exist when adding note
        return []
    note_type_name = note_type["name"]

    copy_definitions: list[CopyDefinition] = []

    for copy_definition in config.copy_definitions:
        copy_on_add = copy_definition.get("copy_on_add", False)
        if not copy_on_add:
            continue
        copy_into_note_types = copy_definition.get("copy_into_note_types", None)
        if not copy_into_note_types:
            continue
        # Split note_types by comma
        copy_into_note_types = copy_into_note_types.strip('""').split('", "')
        if note_type_name not in copy_into_note_types:
            continue

        copy_definitions.append(copy_definition)

    return copy_definitions


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
    editing_other_notes_definitions: list[CopyDefinition] = []

    for copy_definition in config.copy_definitions:
        copy_on_add = copy_definition.get("copy_on_add", False)
        if not copy_on_add:
            continue
        copy_into_note_types = copy_definition.get("copy_into_note_types", None)
        if not copy_into_note_types:
            continue
        # Split note_types by comma
        note_type_names = copy_into_note_types.strip('""').split('", "')
        if note_type_name not in note_type_names:
            continue

        # If this definition modifies other notes, we need to defer it until the note is added
        if definition_modifies_other_notes(copy_definition):
            editing_other_notes_definitions.append(copy_definition)
            continue
        copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            deck_id=deck_id,
        )

    if not editing_other_notes_definitions:
        return

    # Run the definitions that affect other notes with an undo entry created
    # Thus the changes on other notes can be undone while the changes on the new note
    # will remain, as that seems more user-friendly.
    copied_into_notes: list[Note] = []
    for copy_definition in editing_other_notes_definitions:
        # Can't use copy_fields here as it'd lead to a
        # "bug: run_in_background not called from main thread" exception
        # TODO: non CollectionOp version of copy_fields
        copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            copied_into_notes=copied_into_notes,
            deck_id=deck_id,
        )
    undo_text = make_copy_fields_undo_text(
        copy_definitions=editing_other_notes_definitions,
        note_count=1,
        suffix="triggered by adding note",
    )
    # Unfortunately, note_will_be_added is called *before* the note is actually added so after
    # this undo entry will come the "Add Note" undo entry. This is not ideal, but it's the most
    # reliable thing do while a note_was_added hook doesn't exist.
    #
    # Other altenatives would be to add a flag to new notes and run the deferred copy definitions
    # on syncing but that seems less user-friendly.
    undo_entry = mw.col.add_custom_undo_entry(undo_text)
    mw.col.update_notes(copied_into_notes)
    mw.col.merge_undo_entries(undo_entry)


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

    copy_definitions_to_run: list[CopyDefinition] = []
    has_definitions_to_process_on_sync = False

    for copy_definition in config.copy_definitions:
        copy_on_review = copy_definition.get("copy_on_review", False)
        if not copy_on_review:
            copy_on_sync = copy_definition.get("copy_on_sync", False)
            if copy_on_sync:
                has_definitions_to_process_on_sync = True
            continue
        copy_into_note_types = copy_definition.get("copy_into_note_types", None)
        # Split note_types by comma
        if not copy_into_note_types:
            continue
        note_type_names = copy_into_note_types.strip('""').split('", "')
        if note_type_name not in note_type_names:
            continue

        copy_definitions_to_run.append(copy_definition)

    if not copy_definitions_to_run:
        return

        # Get the current Answer card undo entry
    undo_status = mw.col.undo_status()
    answer_card_undo_entry = undo_status.last_step
    copied_into_notes: list[Note] = []
    for copy_definition in copy_definitions_to_run:
        copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            copied_into_notes=copied_into_notes,
        )
    if has_definitions_to_process_on_sync:
        # In order to not have on_sync definitions run twice, we'll set a different fc value
        write_custom_data(card, key="fc", value=-1)
    else:
        write_custom_data(card, key="fc", value=1)
    # update_card adds a new undo entry Update card
    mw.col.update_card(card)
    # update_note adds a new undo entry Update note
    mw.col.update_notes(copied_into_notes)
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
    # Make a copy because values() returns a reference
    initial_field_values = note.values().copy()

    # Copy definitions that affect other notes need an undo entry as we want to be able to undo
    editing_other_notes_definitions: list[CopyDefinition] = []

    for copy_definition in config.copy_definitions:
        copy_into_note_types = copy_definition.get("copy_into_note_types", None)
        if not copy_into_note_types:
            continue
        # Split note_types by comma
        note_type_names = copy_into_note_types.strip('""').split('", "')
        if note_type_name not in note_type_names:
            continue

        # Check field-to-field defs for a match on this field
        field_to_field_defs = copy_definition.get("field_to_field_defs")
        if not field_to_field_defs:
            continue

        modifies_other_notes = definition_modifies_other_notes(copy_definition)

        if modifies_other_notes and is_new_note:
            # Do not run ops that edit other notes while editing a new note. Such ops should only
            # be run when the new note is saved.
            continue

        # get field-to-field matching this field
        field_to_field_def = get_triggered_field_to_field_def_for_field(
            field_to_field_defs, field_name, modifies_other_notes
        )
        if not field_to_field_def:
            continue

        if is_new_note and not field_to_field_def.get("copy_on_unfocus_when_add"):
            continue

        if not is_new_note and not field_to_field_def.get("copy_on_unfocus_when_edit"):
            continue

        if modifies_other_notes:
            # Run these separate with an undo entry
            editing_other_notes_definitions.append(copy_definition)
        else:
            # Either within note or destination to sources, we can run these right away
            # without an undo entry needed
            copy_for_single_trigger_note(
                copy_definition=copy_definition,
                trigger_note=note,
                copied_into_notes=[],
                field_only=field_name,
            )

    if editing_other_notes_definitions:
        # Use the CollectionOp version so we get the full report and progress dialog
        copy_fields(
            copy_definitions=editing_other_notes_definitions,
            note_ids=[note.id],
            field_only=field_name,
            undo_text_suffix=f"triggered by unfocus field '{field_name}'",
        )

    # Copy definitions may not just edit this field but any field in the current note
    # Check if any field has changed and reload then
    current_field_values = note.values()
    changed = initial_field_values != current_field_values
    if changed:
        for editor in editors_matching_note_id:
            editor.loadNote()
    return changed


def init_note_hooks():
    editor_did_load_note.append(on_editor_did_load_note)
    note_will_be_added.append(lambda _col, note, deck_id: run_copy_fields_on_add(note, deck_id))
    reviewer_did_answer_card.append(lambda reviewer, card, ease: run_copy_fields_on_review(card))
    editor_did_unfocus_field.append(run_copy_fields_on_unfocus_field)
