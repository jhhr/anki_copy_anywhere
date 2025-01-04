from typing import Union, Tuple
from anki.hooks import (
    note_will_be_added,
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

from ..utils import (
    write_custom_data,
    definition_modifies_other_notes,
    definition_modifies_trigger_note,
)
from ..configuration import (
    Config,
    CopyDefinition,
)
from ..logic.copy_fields import (
    copy_for_single_trigger_note,
    copy_fields,
    make_copy_fields_undo_text,
)


def get_copy_definitions_for_add_note(note: Note) -> list[CopyDefinition]:
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


def run_copy_fields_on_will_add_note(note: Note, deck_id: int):
    """
    Copy fields when a note is about to be added. This applies to notes being added
    by AnkiConnect or the Add cards dialog. Because the note is not yet added to the
    database, we can't get the note ID, so we can't copy fields that affect other notes.
    """
    definitions_editing_new_note = list(
        filter(definition_modifies_trigger_note, get_copy_definitions_for_add_note(note))
    )

    # Run the definitions that only modify the new note, no undo entry needed
    copied_into_notes: list[Note] = []
    for copy_definition in definitions_editing_new_note:
        copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            copied_into_notes=copied_into_notes,
            deck_id=deck_id,
        )


def run_copy_fields_on_added_note(note: Note):
    definitions_editing_new_note = list(
        filter(definition_modifies_other_notes, get_copy_definitions_for_add_note(note))
    )
    # Run the definitions that affect other notes with an undo entry created
    # Thus the changes on other notes can be undone while the changes on the new note
    # will remain, as that seems more user-friendly.
    copied_into_notes: list[Note] = []
    for copy_definition in definitions_editing_new_note:
        # Can't use copy_fields here as it'd lead to a
        # "bug: run_in_background not called from main thread" exception
        # TODO: non CollectionOp version of copy_fields
        copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            copied_into_notes=copied_into_notes,
        )
    undo_text = make_copy_fields_undo_text(
        copy_definitions=definitions_editing_new_note,
        note_count=1,
        suffix="triggered by adding note",
    )
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

    for copy_definition in config.copy_definitions:
        copy_on_review = copy_definition.get("copy_on_review", False)
        if not copy_on_review:
            continue
        copy_into_note_types = copy_definition.get("copy_into_note_types", None)
        # Split note_types by comma
        if not copy_into_note_types:
            continue
        note_type_names = copy_into_note_types.strip('""').split('", "')
        if note_type_name not in note_type_names:
            continue

        # Get the current Answer card undo entry
        undo_status = mw.col.undo_status()
        answer_card_undo_entry = undo_status.last_step
        copied_into_notes: list[Note] = []
        copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            copied_into_notes=copied_into_notes,
        )
        write_custom_data(card, key="fc", value="1")
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
    editor_for_note_id[editor.editorMode] = editor, (editor.note.id if editor.note else NoteId(0))


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
        note_type_names = copy_into_note_types.strip('""').split('", "')
        if note_type_name not in note_type_names:
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

        # Do not run ops that edit other notes while editing a new note. Such ops should only
        # be run when the new note is saved.
        if definition_modifies_other_notes(copy_definition) and not is_new_note:
            editing_other_notes_definitions.append(copy_definition)
        else:
            # Either within note or destination to sources, we can run these right away
            success = copy_for_single_trigger_note(
                copy_definition=copy_definition,
                trigger_note=note,
                copied_into_notes=[],
                field_only=field_name,
            )

            changed = success or changed

    if editing_other_notes_definitions:
        # Use the CollectionOp version so we get the full report and undo_entry
        copy_fields(
            copy_definitions=editing_other_notes_definitions,
            note_ids=[note.id],
            field_only=field_name,
            undo_text_suffix=f"triggered by unfocus field '{field_name}'",
        )

    # If the field value has changed, reload the note in the editors that are open to it
    cur_field_value = note[field_name]
    if changed and editors_matching_note_id and cur_field_value != initial_field_value:
        for editor in editors_matching_note_id:
            editor.loadNote()
    return changed


def init_note_hooks():
    editor_did_load_note.append(on_editor_did_load_note)
    note_will_be_added.append(
        lambda _col, note, deck_id: run_copy_fields_on_will_add_note(note, deck_id)
    )
    note_added.append(lambda _col, note: run_copy_fields_on_added_note(note))
    reviewer_did_answer_card.append(lambda reviewer, card, ease: run_copy_fields_on_review(card))
    editor_did_unfocus_field.append(run_copy_fields_on_unfocus_field)
