import json
from contextlib import contextmanager
from typing import Optional, Dict, Any, Union, TypedDict, Protocol, Iterable, Tuple
from pathlib import Path


from anki import notes_pb2
from anki.notes import Note
from anki.cards import Card

from aqt.qt import QFontMetrics, QComboBox
from aqt import mw


def add_dict_key_value(
    dict: dict,
    key: Optional[str] = None,
    value: Optional[Union[str, int, float, bool]] = None,
    new_key: Optional[str] = None,
):
    if new_key is not None and value is None and key is not None:
        # rename key
        dict[new_key] = dict.pop(key, None)
    elif new_key is not None and value is not None:
        # rename key and change value
        dict.pop(key, None)
        dict[new_key] = value
    elif value is not None:
        # set value for key
        dict[key] = value
    elif key is not None:
        # remove key
        dict.pop(key, None)


class KeyValueDict(TypedDict):
    key: str
    value: Optional[Union[str, int, float, bool]]
    new_key: Optional[str]


def write_custom_data(
    card: Card,
    key: Optional[str] = None,
    value: Optional[Union[str, int, float, bool]] = None,
    new_key: Optional[str] = None,
    key_values: Optional[list[KeyValueDict]] = None,
):
    """
    Write custom data to the card.
    :param card: The card to write the custom data to.
    :param key: The key to write the value to.
    :param value: The value to write to the key. If None, the key will be removed.
    :param new_key: The new key to rename the key to.
                If value is None, the key will be renamed while keeping the old value.
                If value is not None, the key will be renamed and the value will changed.
    :param key_values: A list of (key, value, new key) tuples. Used for performance as calling
                this function multiple times would perform json.loads and json.dumps multiple times.

    """
    if card.custom_data != "":
        custom_data = json.loads(card.custom_data)
    else:
        custom_data = {}
    if key_values is not None:
        for kv in key_values:
            add_dict_key_value(
                custom_data,
                kv.get("key"),
                kv.get("value", ""),
                kv.get("new_key"),
            )
    else:
        add_dict_key_value(custom_data, key, value, new_key)
    compressed_data = json.dumps(custom_data, separators=(",", ":"))
    if len(compressed_data) > 100:
        raise ValueError("Custom data exceeds 100 bytes after compression.")
    card.custom_data = compressed_data


# Type that'll match anki's Note class
class DictLike(Protocol):
    def items(self) -> Iterable[Tuple[str, Any]]: ...
    def keys(self) -> Iterable[str]: ...
    def values(self) -> Iterable[Any]: ...


def to_lowercase_dict(d: Union[Dict[str, Any], DictLike, None]) -> Dict[str, Any]:
    """Converts a dictionary to lowercase keys"""
    if d is None:
        return {}
    return {k.lower(): v for k, v in d.items()}


def make_query_string(prefix: str, values: list[str]) -> str:
    """Converts a list of values to a query string for the card browser"""
    if not prefix or not values:
        return ""
    query = "("
    for i, value in enumerate(values):
        query += f'"{prefix}:{value}"'
        if i < len(values) - 1:
            query += " OR "
    query += ")"
    return query


def adjust_width_to_largest_item(combo_box: QComboBox):
    """Adjusts the width of a standard combo box to the largest item"""
    max_width = 0
    for i in range(combo_box.count()):
        item_text = combo_box.itemText(i)
        item_width = QFontMetrics(combo_box.font()).horizontalAdvance(item_text)
        if item_width > max_width:
            max_width = item_width
    view = combo_box.view()
    if view is not None:
        view.setMinimumWidth(max_width + 20)


@contextmanager
def block_signals(*widgets):
    try:
        for widget in widgets:
            widget.blockSignals(True)
        yield
    finally:
        for widget in widgets:
            widget.blockSignals(False)


def write_to_media_folder(filename: str, text: str) -> None:
    """
    Write text to a file in the media folder
    """
    if not filename:
        raise ValueError("Filename must not be empty")
    # If filename doesn't start with _, add it
    if not filename.startswith("_"):
        filename = f"_{filename}"

    media_path = Path(mw.pm.profileFolder(), "collection.media")

    file_path = Path(media_path, filename)

    # Write the text to the file, overwriting, if it already exists
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text)


def file_exists_in_media_folder(filename: str) -> bool:
    """
    Check if a file exists in the media folder
    """
    if not filename:
        raise ValueError("Filename must not be empty")
    # If filename doesn't start with _, add it
    if not filename.startswith("_"):
        filename = f"_{filename}"

    media_path = Path(mw.pm.profileFolder(), "collection.media")

    file_path = Path(media_path, filename)

    return file_path.exists()


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
