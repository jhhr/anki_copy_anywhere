import base64
import random
import time
from operator import itemgetter
from typing import Callable, Union, Optional

from anki.cards import Card
from anki.collection import Progress
from anki.notes import Note
from anki.utils import ids2str
from aqt import mw
from aqt.operations import CollectionOp
from aqt.progress import ProgressUpdate
# noinspection PyUnresolvedReferences
from aqt.qt import QWidget, QDialog, QVBoxLayout, QLabel, QScrollArea, QGuiApplication, QTextEdit
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
from ..ui.auto_resizing_text_edit import AutoResizingTextEdit
from ..utils import (
    write_custom_data,
)


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
        textbox = AutoResizingTextEdit(self, readOnly=True)
        textbox.setPlainText("\n".join(message_list))
        lay.addWidget(textbox)
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


class CacheResults:
    """
    Helper class used with CollectionOp, as suggested in qt/aqt/operations/__init__.py:
        '''
        `op` should either return OpChanges, or an object with a 'changes'
        property. The changes will be passed to `operation_did_execute` so that
        the UI can decide whether it needs to update itself.
        '''
    The result of merge_undo_entries(undo_entry) should be entered into the 'changes' property.
    Any other properties can be used to store additional information.
    Here, result_text is used to store a text that will be displayed in the UI after
    an op finishes.
    """

    def __init__(self, result_text: str, changes):
        self.result_text = result_text
        self.changes = changes

    def set_result_text(self, result_text):
        self.result_text = result_text

    def add_result_text(self, result_text):
        self.result_text += result_text

    def get_result_text(self):
        return self.result_text


class ProgressUpdateDef():
    """
    Helper class used with CollectionOp.with_backend_progress(progress_update) to
    update the progress bar and its label. In qt/aqt/progress.py the progress-update
    function is used like this:
        '''
        update = ProgressUpdate(user_wants_abort=user_wants_abort)
        progress = self.mw.backend.latest_progress()
        progress_update(progress, update)
        '''
    The update.label, update.value and update.max are used to update the progress bar.
    The progress_update function then needs a way to get information from the within the
    op while it runs. This class is used to store the label, value and max_value in
    a mutable object that the progress_update function can access.
    """

    def __init__(self, label: str = None, value: int = None, max_value: int = None):
        self.label = label
        self.value = value
        self.max_value = max_value

    def has_update(self):
        return self.label is not None or self.value is not None or self.max_value is not None

    def clear(self):
        self.label = None
        self.value = None
        self.max_value = None


def copy_fields(
        copy_definitions: list[CopyDefinition],
        card_ids=None,
        card_ids_per_definition: list[list[int]] = None,
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
        result = copy_results.get_result_text()
        # Don't show a blank tooltip with just the time
        if result:
            main_time = f"{time.time() - start_time:.2f}s total time<br>" \
                if len(copy_definitions) > 1 else "Finished in "
            tooltip(f"{main_time}{result}",
                    parent=parent,
                    period=5000 + len(copy_definitions) * 1000,
                    # Position the tooltip higher so other tooltips don't get covered
                    # 100 is the default offset, see aqt.utils.tooltip
                    y_offset=200 if is_sync else 100
                    )
        if not is_sync and len(debug_texts) > 0:
            ScrollMessageBox(
                debug_texts,
                title="Copy fields debug Messages",
                parent=parent)

    def on_failure(exception):
        mw.progress.finish()
        show_error_message(f"Copying failed: {exception}")
        if not is_sync and len(debug_texts) > 0:
            ScrollMessageBox(
                debug_texts,
                title="Copy Fields debug Messages",
                parent=parent)
        # Need to raise the exception to get the traceback to the cause in the console
        raise exception

    # We'll mutate this object in copy_fields_in_background, so that when
    # the progress callback is called, it will have the latest values
    progress_update_def = ProgressUpdateDef()

    def on_progress(_: Progress, update: ProgressUpdate):
        # progress contains some text that the sync progress bar uses, so it's useless
        # here as it never changes
        nonlocal progress_update_def
        if progress_update_def.has_update():
            update.label = progress_update_def.label
            update.value = progress_update_def.value
            update.max = progress_update_def.max_value
            progress_update_def.clear()

    def op(_):
        copied_into_cards = []
        if len(copy_definitions) == 1:
            undo_text = f"Copy fields ({copy_definitions[0]['definition_name']})"
            if card_ids:
                undo_text += f" for {len(card_ids)} cards"
        elif len(copy_definitions) > 1:
            undo_text = f"Copying with {len(copy_definitions)} definitions"
            total_card_count = None
            if card_ids:
                total_card_count = len(card_ids) * len(copy_definitions)
            elif card_ids_per_definition:
                total_card_count = sum(len(ids) for ids in card_ids_per_definition)
            if total_card_count:
                undo_text += f" for a {total_card_count} cards"
            else:
                undo_text += " for all possible target cards"
        else:
            show_error_message("Error in copy fields: No definitions given")
            return
        undo_entry = mw.col.add_custom_undo_entry(undo_text)
        results = CacheResults(
            result_text="",
            changes=mw.col.merge_undo_entries(undo_entry),
        )

        for i, copy_definition in enumerate(copy_definitions):
            results = copy_fields_in_background(
                copy_definition=copy_definition,
                card_ids=card_ids_per_definition[i] if card_ids_per_definition is not None else card_ids,
                show_message=show_error_message,
                is_sync=is_sync,
                copied_into_cards=copied_into_cards,
                undo_entry=undo_entry,
                results=results,
                progress_update_def=progress_update_def,
            )
            if mw.progress.want_cancel():
                break
        for card in copied_into_cards:
            write_custom_data(card, key="fc", value="1")
            mw.col.update_card(card)
            # undo_entry has to be updated after every undoable op or the last_step will
            # increment causing an "target undo op not found" error!
            results.changes = mw.col.merge_undo_entries(undo_entry)
        return results

    return (
        CollectionOp(
            parent=parent,
            op=op,
        )
        .success(on_done)
        .failure(on_failure)
        .with_backend_progress(on_progress)
        .run_in_background()
    )


def copy_fields_in_background(
        copy_definition: CopyDefinition,
        copied_into_cards: list[Card],
        undo_entry: int,
        results: CacheResults,
        progress_update_def: ProgressUpdateDef,
        is_sync: Optional[bool] = False,
        card_ids: Optional[list[int]] = None,
        show_message: Optional[Callable[[str], None]] = None,
):
    """
    Function run to copy stuff into many notes at once.
    :param copy_definition: The definition of what to copy, includes process chains
    :param copied_into_cards: An initially empty list of cards that will be appended to with the cards
         that were copied into
    :param undo_entry: The undo entry to merge the changes into
    :param results: The results object to update with the final result text
    :param card_ids: The card ids to copy into. this would replace the copy_into_field from
       the copy_definition
    :param show_message: Function to show error messages
    :param is_sync: Whether this is a sync operation or not
    :return: the CacheResults object passed as results
    """
    (
        copy_into_note_types,
        definition_name
    ) = itemgetter(
        "copy_into_note_types",
        "definition_name"
    )(copy_definition)

    start_time = time.time()

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

    # Get from_note_type_id either directly or through copy_into_note_types
    if copy_into_note_types is None:
        show_error_message(
            f"""Error in copy fields: Note type for copy_into_note_types '{copy_into_note_types}'
            not found, check your spelling""",
        )
        return results

    # Split by comma and remove the first wrapping " but keeping the last one
    note_type_names = copy_into_note_types.strip('""').split('", "')
    # Note: adding "" between each so that we get "note:Some note type" OR "note:Some other note type"
    note_type_ids = filter(None, [mw.col.models.id_for_name(name) for name in note_type_names])

    multiple_note_types = len(note_type_names) > 1
    fc_query = "AND json_extract(json_extract(c.data, '$.cd'), '$.fc') = 0" if is_sync else ""

    if card_ids is not None and len(card_ids) > 0:
        # Filter card_ids further into only the cards of the note type
        cids_query = f"AND c.id IN {ids2str(card_ids)}"
    elif card_ids is None:
        # Get all cards of the note type
        cids_query = ""
    else:
        # This is an error. If card_ids is an empty list, we won't do anything
        # To copy into all cards card_ids should explicitly be None
        return results

    filtered_card_ids = mw.col.db.list(f"""
            SELECT c.id
            FROM cards c, notes n
            WHERE n.mid IN {ids2str(note_type_ids)}
            AND c.nid = n.id
            {cids_query}
            {fc_query}
            """)

    if not is_sync and len(filtered_card_ids) == 0:
        show_error_message(
            f"Error in copy fields: Did not find any cards of note type(s) {copy_into_note_types}")
        return results

    cards = [mw.col.get_card(card_id) for card_id in filtered_card_ids]
    total_cards_count = len(cards)

    # Cache any opened files, so process chains can use them instead of needing to open them again
    # contents will be cached by file name
    file_cache = {}

    for card in cards:
        if card_cnt % 10 == 0:
            elapsed_s = time.time() - start_time
            elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_s))
            progress_update_def.label = f"""<strong>{definition_name}</strong>:
            <br>Copied {card_cnt}/{total_cards_count} cards
            <br>Time: {elapsed_time}"""
            if card_cnt / total_cards_count > 0.10 or elapsed_s > 5:
                eta_s = (elapsed_s / card_cnt) * (total_cards_count - card_cnt)
                eta = time.strftime("%H:%M:%S", time.gmtime(eta_s))
                progress_update_def.label += f" - ETA: {eta}"
            progress_update_def.value = card_cnt
            progress_update_def.max_value = total_cards_count

        card_cnt += 1

        copy_into_note = card.note()

        success = copy_for_single_note(
            copy_definition=copy_definition,
            note=copy_into_note,
            deck_id=card.odid or card.did,
            multiple_note_types=multiple_note_types,
            show_error_message=show_error_message,
            file_cache=file_cache,
        )

        mw.col.update_note(copy_into_note)
        # undo_entry has to be updated after every undoable op or the last_step will
        # increment causing an "target undo op not found" error!
        results.changes = mw.col.merge_undo_entries(undo_entry)

        copied_into_cards.append(card)

        if mw.progress.want_cancel():
            break

        if not success:
            return results

    # When syncing, don't show a pointless message that nothing was done
    # Otherwise, when copy fields is run manually, you want to know the result in any case
    should_report_result = len(cards) > 0 if is_sync else True
    if should_report_result:
        results.add_result_text(
            f"<br>{time.time() - start_time:.2f}s - <i>{copy_definition['definition_name']}:</i> {card_cnt} cards"
        )
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
        field_only: str = None,
        deck_id: int = None,
        multiple_note_types: bool = False,
        show_error_message: Callable[[str], None] = None,
        file_cache: dict = None,
):
    """
    Copy fields into a single note
    :param copy_definition: The definition of what to copy, includes process chains
    :param note: Note to copy into
    :param field_only: Optional field to limit copying to. Used when copying is applied
      in the note editor
    :param deck_id: Deck ID where the cards are going into, only needed when adding
      a note since cards don't exist yet. Otherwise, the deck_ids are checked from the cards
      of the note
    :param multiple_note_types: Whether the copy is into multiple note types
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
        copy_into_note_field = field_to_field_def["copy_into_note_field"]
        if field_only is not None and copy_into_note_field != field_only:
            continue
        copy_from_text = field_to_field_def["copy_from_text"]
        copy_if_empty = field_to_field_def["copy_if_empty"]
        process_chain = field_to_field_def.get("process_chain", None)

        try:
            cur_field_value = note[copy_into_note_field]
        except KeyError:
            show_error_message(f"Error in copy fields: Field '{copy_into_note_field}' not found in note")
            return False

        if copy_if_empty and cur_field_value != "":
            continue

        # Step 2.1: Get the value from the notes, usually it's just one note
        result_val = get_field_values_from_notes(
            copy_from_text=copy_from_text,
            notes=notes_to_copy_from,
            dest_note=note,
            multiple_note_types=multiple_note_types,
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

        print(f"result_val after process chain: {result_val}")
        # Finally, copy the value into the note
        note[copy_into_note_field] = result_val

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
            source_note=note,
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
        extra_state: dict,
        deck_id: int = None,
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
    :param deck_id: Optional deck id of the note to copy into
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
            f"""Error in copy fields: incorrect 'select_card_by' value '{select_card_by}'.
            It must be one of {PICK_CARD_BY_VALID_VALUES}""",
        )
        return []

    if select_card_count:
        try:
            select_card_count = int(select_card_count)
            if select_card_count < 1:
                raise ValueError
        except ValueError:
            show_error_message(
                f"""Error in copy fields: Incorrect 'select_card_count' value '{select_card_count}'
                value must be a positive integer"""
            )
            return []
    else:
        select_card_count = 1

    if only_copy_into_decks and only_copy_into_decks != "-":
        # Check if the current deck is in the white list, otherwise we don't copy into this note
        # whitelist deck is a list of deck or sub deck names
        # parent names can't be included since adding :: would break the filter text
        target_deck_names = only_copy_into_decks.strip('""').split('", "')

        whitelist_dids = [
            mw.col.decks.id_for_name(target_deck_name) for
            target_deck_name in target_deck_names
        ]
        whitelist_dids = set(whitelist_dids)
        deck_ids = []
        if deck_id is not None:
            deck_ids.append(deck_id)
        else:
            for card in copy_into_note.cards():
                deck_ids.append(card.odid or card.did)
        if deck_ids and not any(deck_id in whitelist_dids for deck_id in deck_ids):
            return []

    interpolated_cards_query, invalid_fields = interpolate_from_text(
        copy_from_cards_query,
        source_note=copy_into_note,
        variable_values_dict=variable_values_dict,
    )
    cards_query_id = base64.b64encode(f"cards{interpolated_cards_query}".encode()).decode()
    try:
        card_ids = extra_state[cards_query_id]
    except KeyError:
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
        dest_note: Optional[Note],
        multiple_note_types: bool = False,
        variable_values_dict: dict = None,
        select_card_separator: str = ', ',
        show_error_message: Callable[[str], None] = None,
) -> str:
    """
    Get the value from the field in the selected notes gotten with get_notes_to_copy_from.
    :param copy_from_text: Text defining the content to copy into the note's target field. Contains
            text and field names and special values enclosed in double curly braces that need to be
            replaced with the actual values from the notes.
    :param notes: The selected notes to get the value from. In the case of COPY_MODE_WITHIN_NOTE,
            this will be a list with only one note
    :param dest_note: The note to copy into, omitted in COPY_MODE_WITHIN_NOTE
    :param multiple_note_types: Whether the copy is into multiple note types
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
        try:
            # Return the interpolated value using the note
            interpolated_value, invalid_fields = interpolate_from_text(
                copy_from_text,
                source_note=note,
                dest_note=dest_note,
                variable_values_dict=variable_values_dict,
                multiple_note_types=multiple_note_types,
            )
        except ValueError as e:
            show_error_message(f"Error in text interpolation: {e}")
            break

        if len(invalid_fields) > 0:
            show_error_message(
                f"Error in copy fields: Invalid fields in copy_from_text: {', '.join(invalid_fields)}")

        result_val += f"{select_card_separator if i > 0 else ''}{interpolated_value}"

    return result_val
