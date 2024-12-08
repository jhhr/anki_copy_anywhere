from anki import hooks

from ..configuration import Config
from ..logic.copy_fields import copy_for_single_note


def run_copy_fields_on_add(note, deck_id):
    config = Config()
    config.load()

    for copy_definition in config.copy_definitions:
        copy_on_add = copy_definition.get("copy_on_add", False)
        copy_into_note_types = copy_definition.get("copy_into_note_types", None)
        # Split note_types by comma
        copy_into_note_types = copy_into_note_types.strip('""').split('", "') if copy_into_note_types else []
        multiple_note_types = len(copy_into_note_types) > 1
        if not copy_on_add:
            continue
        if note.note_type()["name"] not in copy_into_note_types:
            continue

        copy_for_single_note(
            copy_definition=copy_definition,
            note=note,
            deck_id=deck_id,
            multiple_note_types=multiple_note_types,
        )


def init_note_hooks():
    hooks.note_will_be_added.append(
        lambda _col, note, deck_id: run_copy_fields_on_add(note, deck_id)
    )
