import base64
import math
import random
import time
from operator import itemgetter
from typing import Callable, Union

from anki.notes import Note
from anki.utils import ids2str
from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import QWidget, QDialog, QVBoxLayout, QLabel, QScrollArea, QGuiApplication
from aqt.utils import tooltip

from .FatalProcessError import FatalProcessError
from .fonts_check_process import fonts_check_process
from .interpolate_fields import interpolate_from_text
from .kana_highlight_process import kana_highlight_process
from .kanjium_to_javdejong_process import kanjium_to_javdejong_process
from .regex_process import regex_process
from ..configuration import (
    CopyDefinition,
    CopyFieldToVariable,
    COPY_MODE_WITHIN_NOTE,
    COPY_MODE_ACROSS_NOTES,
    KANA_HIGHLIGHT_PROCESS,
    REGEX_PROCESS,
    FONTS_CHECK_PROCESS,
    KANJIUM_TO_JAVDEJONG_PROCESS,
    KanjiumToJavdejongProcess,
    RegexProcess,
    FontsCheckProcess,
    KanaHighlightProcess
)
from ..utils import (
    write_custom_data,
    CacheResults
)

SEARCH_FIELD_VALUE_PLACEHOLDER = "$SEARCH_FIELD_VALUE$"


class ScrollMessageBox(QDialog):
    """
    A simple class to show a scrollable message box to display debug messages

    :param message_list: A list of messages to display
    :param title: The title of the message box
    :param parent: The parent widget
    """

    def __init__(self, message_list, title, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setWindowTitle(title)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self.content = QWidget()
        scroll.setWidget(self.content)
        lay = QVBoxLayout(self.content)
        for item in message_list:
            label = QLabel(item, self)
            label.setWordWrap(True)
            lay.addWidget(label)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(scroll)
        self.setModal(False)
        # resize horizontally to a percentage of screen width or sizeHint, whichever is larger
        # but allow vertical resizing to follow sizeHint
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(max(self.sizeHint().height(), int(screen.width() * 0.35)), self.sizeHint().height())
        self.show()


def get_ord_from_model(model, fld_name):
    card_id_fld = next((f for f in model["flds"] if f["name"] == fld_name), None)
    if card_id_fld is not None:
        return card_id_fld["ord"]
    return None


PICK_CARD_BY_VALID_VALUES = ('Random', 'Random_stable', 'Least_reps')


def copy_fields(
        copy_definition: CopyDefinition,
        card_ids=None,
        result_text: str = "",
        parent=None,
        is_sync: bool = False,
):
    start_time = time.time()
    debug_texts = []

    def show_error_message(message: str):
        nonlocal debug_texts
        debug_texts.append(message)
        print(message)

    def on_done(copy_results):
        mw.progress.finish()
        tooltip(f"{copy_results.result_text} in {time.time() - start_time:.2f} seconds", parent=parent, period=5000)
        if not is_sync and len(debug_texts) > 0:
            ScrollMessageBox(
                debug_texts,
                title=f'{copy_definition["definition_name"]} Debug Messages',
                parent=parent)

    return (
        CollectionOp(
            parent=parent,
            op=lambda col: copy_fields_in_background(
                copy_definition=copy_definition,
                card_ids=card_ids,
                result_text=result_text,
                show_message=show_error_message,
                is_sync=is_sync,
            ),
        )
        .success(on_done)
        .run_in_background()
    )


def copy_fields_in_background(
        copy_definition: CopyDefinition,
        card_ids=None,
        result_text: str = "",
        show_message: Callable[[str], None] = None,
        is_sync: bool = False,
):
    """
    Function run to copy stuff into many notes at once.
    :param copy_definition: The definition of what to copy, includes process chains
    :param card_ids: The card ids to copy into. this would replace the copy_into_field from
       the copy_definition
    :param result_text: Text to be appended to and shown in the final result tooltip
    :param show_message: Function to show error messages
    :param is_sync: Whether this is a sync operation or not
    :return: CacheResults object
    """
    (
        copy_into_note_type,
        definition_name
    ) = itemgetter(
        "copy_into_note_type",
        "definition_name"
    )(copy_definition)

    undo_text = f"Copy fields ({definition_name})"
    if card_ids:
        undo_text += f" for {len(card_ids)} cards"

    undo_entry = mw.col.add_custom_undo_entry(undo_text)

    results = CacheResults(
        result_text="",
        changes=mw.col.merge_undo_entries(undo_entry),
    )

    mw.taskman.run_on_main(
        lambda: mw.progress.start(
            label=f"Copying fields ({definition_name})", max=0, immediate=False
        )
    )

    card_cnt = 0
    debug_text = ""
    if not show_message:
        def show_error_message(message: str):
            nonlocal debug_text
            debug_text += f"<br/>{card_cnt}--{message}"
            print(message)
    else:
        def show_error_message(message: str):
            show_message(f"\n{card_cnt}--{message}")

    # Get from_note_type_id either directly or through copy_into_note_type
    if copy_into_note_type is None:
        show_error_message(
            f"Error in copy fields: Note type for copy_into_note_type '{copy_into_note_type}' not found, check your spelling",
        )
        return results
    elif card_ids is None:
        show_error_message(
            "Error in copy fields: Both 'card_ids' and 'copy_into_note_type' were missing. Either one is required")
        return results

    # Get cards of the target note type
    if card_ids is not None:
        # If we received a list of ids, we need to filter them by the note type
        # as this could include cards of different note types
        # We'll need to all note_ids as mid is not available in the card object, only in the note
        note_ids = mw.col.find_notes(f'"note:{copy_into_note_type}"')
        if len(note_ids) == 0:
            show_error_message(
                f"Error in copy fields: Did not find any notes of note type '{copy_into_note_type}'")
            return results

        note_ids_str = ids2str(note_ids)
        card_ids_str = ids2str(card_ids)

        filtered_card_ids = mw.col.db.list(f"""
            SELECT id
            FROM cards
            WHERE nid IN {note_ids_str}
            {f"AND id IN {card_ids_str}" if len(card_ids) > 0 else ""}
            {"AND json_extract(json_extract(data, '$.cd'), '$.fc') == 0" if is_sync else ""}
        """)

        cards = [mw.col.get_card(card_id) for card_id in filtered_card_ids]
    else:
        # Otherwise, get all cards of the note type
        card_ids = mw.col.find_cards(f'"note:{copy_into_note_type}" {"prop:cdn:fc=0" if is_sync else ""}')
        if not is_sync and len(card_ids) == 0:
            show_error_message(
                f"Error in copy fields: Did not find any cards of note type '{copy_into_note_type}'")
            return results

        cards = [mw.col.get_card(card_id) for card_id in card_ids]

    total_cards_count = len(cards)

    mw.taskman.run_on_main(
        lambda: mw.progress.update(
            label=f"<strong>{definition_name}</strong><br/>{card_cnt}/{total_cards_count} notes copied into",
            value=card_cnt,
            max=total_cards_count,
        )
    )

    # Cache any opened files, so process chains can use them instead of needing to open them again
    # contents will be cached by file name
    file_cache = {}

    for card in cards:
        card_cnt += 1

        copy_into_note = card.note()

        success = copy_for_single_note(
            copy_definition=copy_definition,
            note=copy_into_note,
            deck_id=card.odid or card.did,
            show_error_message=show_error_message,
            file_cache=file_cache,
        )

        mw.col.update_note(copy_into_note)

        # Set cache time into card.custom_data
        write_custom_data(card, "fc", math.floor(time.time()))
        mw.col.update_card(card)

        if card_cnt % 10 == 0:
            mw.taskman.run_on_main(
                lambda: mw.progress.update(
                    label=f"<strong>{definition_name}</strong><br/>{card_cnt}/{total_cards_count} notes copied into",
                    value=card_cnt,
                    max=total_cards_count,
                )
            )
        if mw.progress.want_cancel():
            break

        if undo_entry is not None:
            mw.col.merge_undo_entries(undo_entry)

        if not success:
            return results

    results.set_result_text(f"{result_text + '<br>' if result_text != '' else ''}{card_cnt} cards' copied into")
    return results


def apply_process_chain(
        process_chain: list[Union[KanjiumToJavdejongProcess, RegexProcess, FontsCheckProcess, KanaHighlightProcess]],
        text: str,
        note: Note,
        show_error_message: Callable[[str], None] = None,
        file_cache: dict = None,
) -> Union[str, None]:
    """
    Apply a list of processes to a text
    :param process_chain: The list of processes to apply
    :param text: The text to apply the processes to
    :param note: The note to use for the processes
    :param show_error_message: A function to show error messages
    :param file_cache: A dictionary to cache opened files' content
    :return: The text after the processes have been applied or None if there was an error
    """
    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    for process in process_chain:
        try:
            if process["name"] == KANA_HIGHLIGHT_PROCESS:
                text = kana_highlight_process(
                    text=text,
                    onyomi_field=process.get("onyomi_field", None),
                    kunyomi_field=process.get("kunyomi_field", None),
                    kanji_field=process.get("kanji_field", None),
                    note=note,
                    show_error_message=show_error_message,
                )
            if process["name"] == REGEX_PROCESS:
                text = regex_process(
                    text=text,
                    regex=process.get("regex", None),
                    replacement=process.get("replacement", None),
                    flags=process.get("flags", None),
                    show_error_message=show_error_message,
                )
            if process["name"] == FONTS_CHECK_PROCESS:
                text = fonts_check_process(
                    text=text,
                    fonts_dict_file=process.get("fonts_dict_file", None),
                    limit_to_fonts=process.get("limit_to_fonts", None),
                    character_limit_regex=process.get("character_limit_regex", None),
                    show_error_message=show_error_message,
                    file_cache=file_cache,
                )
            if process["name"] == KANJIUM_TO_JAVDEJONG_PROCESS:
                text = kanjium_to_javdejong_process(
                    text=text,
                    delimiter=process.get("delimiter", None),
                    show_error_message=show_error_message,
                )
        except FatalProcessError as e:
            # If some process fails in a way that will always fail, we stop the whole operation
            # so the user can fix the issue without needing to wait for all the other notes to be copied
            show_error_message(f"Error in {process['name']} process: {e}")
            return None
    return text


def copy_for_single_note(
        copy_definition: CopyDefinition,
        note: Note,
        deck_id: int,
        show_error_message: Callable[[str], None] = None,
        file_cache: dict = None,
):
    """
    Copy fields into a single note
    :param copy_definition: The definition of what to copy, includes process chains
    :param note: Note to copy into
    :param deck_id: Deck ID where the cards are going into
    :param show_error_message: Optional function to show error messages
    :param file_cache: A dictionary to cache opened files' content
    :return:
    """
    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    (
        field_to_field_defs,
        field_to_variable_defs,
        only_copy_into_decks,
        copy_from_cards_query,
        select_card_by,
        select_card_count,
        select_card_separator,
        copy_mode,
    ) = itemgetter(
        "field_to_field_defs",
        "field_to_variable_defs",
        "only_copy_into_decks",
        "copy_from_cards_query",
        "select_card_by",
        "select_card_count",
        "select_card_separator",
        "copy_mode"
    )(copy_definition)

    extra_state = {}

    # Step 0: Get variable values for the note
    variable_values_dict = None
    if field_to_variable_defs is not None:
        variable_values_dict = get_variable_values_for_note(
            field_to_variable_defs=field_to_variable_defs,
            note=note,
            show_error_message=show_error_message,
            file_cache=file_cache,
        )

    # Step 1: get notes to copy from for this card
    notes_to_copy_from = []
    if copy_mode == COPY_MODE_WITHIN_NOTE:
        notes_to_copy_from = [note]
    elif copy_mode == COPY_MODE_ACROSS_NOTES:
        notes_to_copy_from = get_notes_to_copy_from(
            copy_from_cards_query=copy_from_cards_query,
            copy_into_note=note,
            deck_id=deck_id,
            extra_state=extra_state,
            only_copy_into_decks=only_copy_into_decks,
            select_card_by=select_card_by,
            select_card_count=select_card_count,
            show_error_message=show_error_message,
            variable_values_dict=variable_values_dict,
        )
    else:
        show_error_message("Error in copy fields: missing copy mode value")
        return False

    if len(notes_to_copy_from) == 0:
        show_error_message(f"Error in copy fields: No notes to copy from for note {note.id}")

    # Step 2: Get value for each field we are copying into
    for field_to_field_def in field_to_field_defs:
        copy_from_text = field_to_field_def["copy_from_text"]
        copy_into_note_field = field_to_field_def["copy_into_note_field"]
        copy_if_empty = field_to_field_def["copy_if_empty"]
        process_chain = field_to_field_def.get("process_chain", None)

        # Step 2.1: Get the value from the notes, usually it's just one note
        result_val = get_field_values_from_notes(
            copy_from_text=copy_from_text,
            notes=notes_to_copy_from,
            current_target_value=note[copy_into_note_field],
            select_card_separator=select_card_separator,
            show_error_message=show_error_message,
        )
        # Step 2.2: If we have further processing steps, run them
        if process_chain is not None:
            result_val = apply_process_chain(
                process_chain=process_chain,
                text=result_val,
                note=note,
                show_error_message=show_error_message,
                file_cache=file_cache,
            )
            if result_val is None:
                return False

        # Step 2.3: Set the value into the target note's field
        try:
            # only_empty can override the functionality of ignore_if_cached causing the card to be updated
            # that's why the default only_empty is False and ignore_if_cached is True
            if copy_if_empty and note[copy_into_note_field] != "":
                break
            note[copy_into_note_field] = result_val

        except ValueError:
            show_error_message(f"Error copy fields: a field '{copy_into_note_field}' was not found in note")

    return True


def get_variable_values_for_note(
        field_to_variable_defs: list[CopyFieldToVariable],
        note: Note,
        file_cache: dict = None,
        show_error_message: Callable[[str], None] = None,
) -> Union[dict, None]:
    """
    Get the values for the variables from the note
    :param field_to_variable_defs: The definitions of the variables to get
    :param note: The note to get the values from
    :param file_cache: A dictionary to cache opened files' content for process chains
    :param show_error_message: A function to show error messages
    :return: A dictionary of the values for the variables or None if there was an error
    """
    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    variable_values_dict = {}
    for field_to_variable_def in field_to_variable_defs:
        copy_into_variable = field_to_variable_def["copy_into_variable"]
        copy_from_text = field_to_variable_def["copy_from_text"]
        process_chain = field_to_variable_def.get("process_chain", None)

        # Step 1: Interpolate the text with values from the note
        interpolated_value, invalid_fields = interpolate_from_text(
            copy_from_text,
            note=note,
        )
        if len(invalid_fields) > 0:
            show_error_message(
                f"Error getting variable values: Invalid fields in copy_from_text: {', '.join(invalid_fields)}")

        # Step 2: If we have further processing steps, run them
        if process_chain is not None:
            interpolated_value = apply_process_chain(
                process_chain=process_chain,
                text=interpolated_value,
                note=note,
                show_error_message=show_error_message,
                file_cache=file_cache,
            )
            if interpolated_value is None:
                return None

        variable_values_dict[copy_into_variable] = interpolated_value

    return variable_values_dict


def get_notes_to_copy_from(
        copy_from_cards_query: str,
        copy_into_note: Note,
        select_card_by: str,
        deck_id,
        extra_state: dict,
        variable_values_dict: dict = None,
        only_copy_into_decks: str = None,
        select_card_count: str = '1',
        show_error_message: Callable[[str], None] = None,
) -> list[Note]:
    """
    Get the notes to copy from based on the search value and the query.
    :param copy_from_cards_query: The query to find the cards to copy from.
            Uses {{}} syntax for note fields and special values
    :param copy_into_note: The note to copy into, used to interpolate the query
    :param select_card_by: How to select the card to copy from, if we get multiple results using the
            the query
    :param deck_id: The current deck id, used to filter the cards to copy from
    :param extra_state: A dictionary to store cached values to re-use in subsequent calls of this function
    :param variable_values_dict: A dictionary of custom variable values to use in interpolating text
    :param only_copy_into_decks: A comma separated whitelist of deck names. Limits the cards to copy from
            to only those in the decks in the whitelist
    :param select_card_count: How many cards to select from the query. Default is 1
    :param show_error_message: A function to show error messages, used for storing all messages until the
            end of the whole operation to show them in a GUI element at the end
    :return: A list of notes to copy from
    """
    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    if select_card_by is None:
        show_error_message("Error in copy fields: Required value 'select_card_by' was missing.")
        return []

    if select_card_by not in PICK_CARD_BY_VALID_VALUES:
        show_error_message(
            f"Error in copy fields: incorrect 'select_card_by' value '{select_card_by}'. It must be one of {PICK_CARD_BY_VALID_VALUES}",
        )
        return []

    if select_card_count:
        try:
            select_card_count = int(select_card_count)
            if select_card_count < 1:
                raise ValueError
        except ValueError:
            show_error_message(
                f"Error in copy fields: Incorrect 'select_card_count' value '{select_card_count}' value must be a positive integer"
            )
            return []
    else:
        select_card_count = 1

    if only_copy_into_decks not in [None, "-"]:
        # Check if the current deck is in the white list, otherwise we don't copy into this note
        # whitelist deck is a list of deck or sub deck names
        # parent names can't be included since adding :: would break the filter text
        target_deck_names = only_copy_into_decks.split(", ")

        whitelist_dids = [
            mw.col.decks.id_for_name(target_deck_name.strip('""')) for
            target_deck_name in target_deck_names
        ]
        whitelist_dids = set(whitelist_dids)
        if deck_id not in whitelist_dids:
            return []

    interpolated_cards_query, invalid_fields = interpolate_from_text(
        copy_from_cards_query,
        note=copy_into_note,
        variable_values_dict=variable_values_dict,
    )
    cards_query_id = base64.b64encode(f"cards{interpolated_cards_query}".encode()).decode()
    try:
        card_ids = extra_state[cards_query_id]
    except KeyError:
        # Always exclude suspended cards
        card_ids = mw.col.find_cards(interpolated_cards_query)
        extra_state[cards_query_id] = card_ids

    if len(invalid_fields) > 0:
        show_error_message(
            f"Error in copy fields: Invalid fields in copy_from_cards_query: {', '.join(invalid_fields)}")

    if (len(card_ids) == 0):
        show_error_message(
            f"Error in copy fields: Did not find any cards with copy_from_cards_query='{interpolated_cards_query}'")
        return []

    # select a card or cards based on the select_card_by value
    selected_notes = []
    for i in range(select_card_count):
        selected_card_id = None
        # We don't make this key entirely unique as we want to cache the selected card for the same
        # deck_id and from_note_type_id combination, so that getting a different field from the same
        # card type will still return the same card

        card_select_key = base64.b64encode(
            f"selected_card{interpolated_cards_query}{select_card_by}{i}".encode()).decode()

        if select_card_by == 'Random':
            # We don't want to cache this as it should in fact be different each time
            selected_card_id = random.choice(card_ids)
        elif select_card_by == 'Least_reps':
            # Loop through cards and find the one with the least reviews
            # Check cache first
            try:
                selected_card_id = extra_state[card_select_key]
            except KeyError:
                selected_card_id = min(card_ids,
                                       key=lambda c: mw.col.db.scalar(f"SELECT COUNT() FROM revlog WHERE cid = {c}"))
                extra_state = {}
                extra_state[card_select_key] = selected_card_id
        if selected_card_id is None:
            show_error_message("Error in copy fields: could not select card")
            break

        # Remove selected card so it can't be picked again
        card_ids = [c for c in card_ids if c != selected_card_id]
        selected_note_id = mw.col.get_card(selected_card_id).nid

        selected_note = mw.col.get_note(selected_note_id)
        selected_notes.append(selected_note)

        # If we've run out of cards, stop and return what we got
        if len(card_ids) == 0:
            break

    return selected_notes


def get_field_values_from_notes(
        copy_from_text: str,
        notes: list[Note],
        current_target_value: str = "",
        variable_values_dict: dict = None,
        select_card_separator: str = ', ',
        show_error_message: Callable[[str], None] = None,
) -> str:
    """
    Get the value from the field in the selected notes gotten with get_notes_to_copy_from.
    :param copy_from_text: Text defining the content to copy into the note's target field. Contains
            text and field names and special values enclosed in double curly braces that need to be
            replaced with the actual values from the notes.
    :param notes: The selected notes to get the value from
    :param current_target_value: The current value of the target field in the note
    :param variable_values_dict: A dictionary of custom variable values to use in interpolating text
    :param select_card_separator: The separator to use when joining the values from the notes. Irrelevant
            if there is only one note
    :param show_error_message: A function to show error messages, used for storing all messages until the
            end of the whole operation to show them in a GUI element at the end
    :return: String with the values from the field in the notes
    """
    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    if copy_from_text is None:
        show_error_message(
            "Error in copy fields: Required value 'copy_from_text' was missing.",
        )
        return ""

    if select_card_separator is None:
        select_card_separator = ", "

    result_val = ""
    for i, note in enumerate(notes):
        # Return the interpolated value using the note
        interpolated_value, invalid_fields = interpolate_from_text(
            copy_from_text,
            note,
            current_field_value=current_target_value,
            variable_values_dict=variable_values_dict,
        )
        if len(invalid_fields) > 0:
            show_error_message(
                f"Error in copy fields: Invalid fields in copy_from_text: {', '.join(invalid_fields)}")

        result_val += f"{select_card_separator if i > 0 else ''}{interpolated_value}"

    return result_val
