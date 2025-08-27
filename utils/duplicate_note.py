from anki.notes import Note

from copy import deepcopy


def duplicate_note(note: Note) -> Note:
    """
    Duplicate a note with deepcopy, copying everything except the col attribute
    as that needs to identical to the original note
    """
    new_note = type(note).__new__(type(note))

    for k, v in note.__dict__.items():
        if k == "col":
            setattr(new_note, k, note.col)
        else:
            setattr(new_note, k, deepcopy(v))
    return new_note
