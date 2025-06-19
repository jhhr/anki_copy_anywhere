from anki import notes_pb2
from anki.notes import Note


def duplicate_note(note: Note) -> Note:
    """
    Duplicate a note by creating a new instance and copying the fields.
    Using copy.deepcopy on a Note object does not work, and Note(id=note.id) does not
    work on a new note (where id is 0), thus this utility function.
    """
    dupe_note = Note(col=note.col, model=note.note_type())

    # Copied code from notes.py _to_backend_note method
    # the method calls hooks.note_will_flush(self) which is not desired here
    # This code may break if the Note class changes in the future.
    backend_note = notes_pb2.Note(
        id=note.id,
        guid=note.guid,
        notetype_id=note.mid,
        mtime_secs=note.mod,
        usn=note.usn,
        tags=note.tags,
        fields=note.fields,
    )
    # Calling internal method that is not part of the public API, so this may break if the
    # Note class changes in the future.
    dupe_note._load_from_backend_note(backend_note)
    return dupe_note
