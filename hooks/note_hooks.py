from anki import hooks

from ..configuration import Config
from ..logic.copy_fields import copy_for_single_note


def run_copy_fields_on_add(note, deck_id):
    config = Config()
    config.load()

    for copy_definition in config.copy_definitions:
        copy_on_add = copy_definition.get("copy_on_add", False)
        copy_into_note_type = copy_definition.get("copy_into_note_type", None)

        if not copy_on_add:
            continue
        if not copy_into_note_type == note.note_type()["name"]:
            continue

        copy_for_single_note(
            copy_definition=copy_definition,
            note=note,
            deck_id=deck_id,
        )


def init_note_hooks():
    hooks.note_will_be_added.append(
        lambda _col, note, deck_id: run_copy_fields_on_add(note, deck_id)
    )
