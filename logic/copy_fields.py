import base64
import random
import time
from operator import itemgetter
from typing import Callable, Union, Optional, Tuple, Sequence, Any

from anki.cards import Card, CardId
from anki.collection import Progress, OpChanges
from anki.notes import Note
from anki.utils import ids2str
from aqt import mw
from aqt.operations import CollectionOp
from aqt.progress import ProgressUpdate

from aqt.qt import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QScrollArea,
    QGuiApplication,
)
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
    CopyFieldToField,
    COPY_MODE_WITHIN_NOTE,
    COPY_MODE_ACROSS_NOTES,
    DIRECTION_SOURCE_TO_DESTINATIONS,
    DIRECTION_DESTINATION_TO_SOURCES,
    SelectCardByType,
    KanjiumToJavdejongProcess,
    RegexProcess,
    FontsCheckProcess,
    KanaHighlightProcess,
    is_kana_highlight_process,
    is_regex_process,
    is_fonts_check_process,
    is_kanjium_to_javdejong_process,
    SELECT_CARD_BY_VALUES,
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

    def __init__(self, message_list, title, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setWindowTitle(title)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self.content = QWidget()
        scroll.setWidget(self.content)
        lay = QVBoxLayout(self.content)
        textbox = AutoResizingTextEdit(self, readOnly=True)
        textbox.setPlainText("\n".join(message_list))
        lay.addWidget(textbox)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(scroll)
        self.setModal(False)
        # resize horizontally to a percentage of screen width or sizeHint, whichever is larger
        # but allow vertical resizing to follow sizeHint
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geometry = screen.availableGeometry()
            self.resize(
                max(self.sizeHint().height(), int(geometry.width() * 0.35)),
                self.sizeHint().height(),
            )
        else:
            self.resize(self.sizeHint())
        self.show()


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

    changes: OpChanges

    def __init__(self, result_text: str, changes):
        self.result_text = result_text
        self.changes = changes

    def set_result_text(self, result_text):
        self.result_text = result_text

    def add_result_text(self, result_text):
        self.result_text += result_text

    def get_result_text(self):
        return self.result_text


class ProgressUpdateDef:
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

    def __init__(
        self,
        label: Optional[str] = None,
        value: Optional[int] = None,
        max_value: Optional[int] = None,
    ):
        self.label = label
        self.value = value
        self.max_value = max_value

    def has_update(self):
        return self.label is not None or self.value is not None or self.max_value is not None

    def clear(self):
        self.label = None
        self.value = None
        self.max_value = None


class ProgressUpdater:
    """
    Helper class to update the progress bar and its label. This class is used to store
    the start time, definition name, total cards count, progress update definition and
    whether the copy is across notes. It also stores the current card count and the
    total processed sources and destinations. The update_counts method is used to
    increment the counts and the render_update method is used to update the progress
    bar and its label.
    """

    def __init__(
        self,
        start_time: float,
        definition_name: str,
        total_cards_count: int,
        progrss_update_def: ProgressUpdateDef,
        is_across: bool,
    ):
        self.start_time = start_time
        self.definition_name = definition_name
        self.total_cards_count = total_cards_count
        self.progress_update_def = progrss_update_def
        self.is_across = is_across
        self.card_cnt = 0
        self.total_processed_sources = 0
        self.total_processed_destinations = 0

    def update_counts(
        self,
        card_cnt_inc: Optional[int] = None,
        processed_sources_inc: Optional[int] = None,
        processed_destinations_inc: Optional[int] = None,
    ):
        if card_cnt_inc is not None:
            self.card_cnt += card_cnt_inc
        if processed_sources_inc is not None:
            self.total_processed_sources += processed_sources_inc
        if processed_destinations_inc is not None:
            self.total_processed_destinations += processed_destinations_inc

    def get_counts(self) -> Tuple[int, int, int]:
        return self.card_cnt, self.total_processed_sources, self.total_processed_destinations

    def render_update(self):
        elapsed_s = time.time() - self.start_time
        elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_s))
        self.progress_update_def.label = f"""<strong>{self.definition_name}</strong>:
        <br>Copied {self.card_cnt}/{self.total_cards_count} cards
        <br><small>Notes processed - destinations: {self.total_processed_destinations}
            {f', sources: {self.total_processed_sources}' if self.is_across else ''}</small>
        <br>Time: {elapsed_time}"""
        if self.card_cnt / self.total_cards_count > 0.10 or elapsed_s > 5:
            if self.card_cnt > 0:
                eta_s = (elapsed_s / self.card_cnt) * (self.total_cards_count - self.card_cnt)
                eta = time.strftime("%H:%M:%S", time.gmtime(eta_s))
                self.progress_update_def.label += f" - ETA: {eta}"
        self.progress_update_def.value = self.card_cnt
        self.progress_update_def.max_value = self.total_cards_count


def copy_fields(
    copy_definitions: list[CopyDefinition],
    card_ids=None,
    card_ids_per_definition: Optional[list[Sequence[Union[int, CardId]]]] = None,
    parent=None,
    is_sync: bool = False,
):
    start_time = time.time()
    debug_texts = []

    def show_error_message(message: str):
        nonlocal debug_texts
        debug_texts.append(message)
        print(message)

    def on_done(copy_results: CacheResults):
        mw.progress.finish()
        result = copy_results.get_result_text()
        # Don't show a blank tooltip with just the time
        if result:
            main_time = (
                f"{time.time() - start_time:.2f}s total time<br>"
                if len(copy_definitions) > 1
                else "Finished in "
            )
            tooltip(
                f"{main_time}{result}",
                parent=parent,
                period=5000 + len(copy_definitions) * 1000,
                # Position the tooltip higher so other tooltips don't get covered
                # 100 is the default offset, see aqt.utils.tooltip
                y_offset=200 if is_sync else 100,
            )
        if not is_sync and len(debug_texts) > 0:
            ScrollMessageBox(debug_texts, title="Copy fields debug Messages", parent=parent)

    def on_failure(exception):
        mw.progress.finish()
        show_error_message(f"Copying failed: {exception}")
        if not is_sync and len(debug_texts) > 0:
            ScrollMessageBox(debug_texts, title="Copy Fields debug Messages", parent=parent)
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

    def op(_) -> CacheResults:
        copied_into_cards: list[Card] = []
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
            return CacheResults(result_text="", changes=None)
        undo_entry = mw.col.add_custom_undo_entry(undo_text)
        results = CacheResults(
            result_text="",
            changes=mw.col.merge_undo_entries(undo_entry),
        )

        for i, copy_definition in enumerate(copy_definitions):
            results = copy_fields_in_background(
                copy_definition=copy_definition,
                card_ids=(
                    card_ids_per_definition[i] if card_ids_per_definition is not None else card_ids
                ),
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
    card_ids: Optional[Sequence[int]] = None,
    show_message: Optional[Callable[[str], None]] = None,
) -> CacheResults:
    """
    Function run to copy stuff into many notes at once.
    :param copy_definition: The definition of what to copy, includes process chains
    :param copied_into_cards: An initially empty list of cards that will be appended to with the
        cards that were copied into
    :param undo_entry: The undo entry to merge the changes into
    :param results: The results object to update with the final result text
    :param progress_update_def: The progress update object to update the progress bar with
    :param card_ids: The card ids to copy into. this would replace the copy_into_field from
       the copy_definition
    :param show_message: Function to show error messages
    :param is_sync: Whether this is a sync operation or not
    :return: the CacheResults object passed as results
    """
    (copy_into_note_types, definition_name) = itemgetter("copy_into_note_types", "definition_name")(
        copy_definition
    )

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

    assert mw.col.db is not None

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
            f"Error in copy fields: Did not find any cards of note type(s) {copy_into_note_types}"
        )
        return results

    cards = [mw.col.get_card(card_id) for card_id in filtered_card_ids]
    total_cards_count = len(cards)
    is_across = copy_definition["copy_mode"] == COPY_MODE_ACROSS_NOTES

    progress_updater = ProgressUpdater(
        start_time=start_time,
        definition_name=definition_name,
        total_cards_count=total_cards_count,
        progrss_update_def=progress_update_def,
        is_across=is_across,
    )

    # Cache any opened files, so process chains can use them instead of needing to open them again
    # contents will be cached by file name
    # Key: file name, Value: whatever a process would need from the file
    file_cache: dict[str, Any] = {}

    total_processed_sources = 0
    total_processed_destinations = 0
    for card in cards:
        if card_cnt % 10 == 0 and card_cnt > 0:
            progress_updater.render_update()

        card_cnt += 1

        copy_into_note = card.note()

        success = copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=copy_into_note,
            results=results,
            undo_entry=undo_entry,
            deck_id=card.odid or card.did,
            multiple_note_types=multiple_note_types,
            show_error_message=show_error_message,
            file_cache=file_cache,
            progress_updater=progress_updater,
        )

        progress_updater.update_counts(card_cnt_inc=1)

        copied_into_cards.append(card)

        if mw.progress.want_cancel():
            break

        if not success:
            return results

    # When syncing, don't show a pointless message that nothing was done
    # Otherwise, when copy fields is run manually, you want to know the result in any case
    should_report_result = len(cards) > 0 if is_sync else True
    if should_report_result:
        #  Get counts from ProgressUpdater and render the final update
        _, total_processed_sources, total_processed_destinations = progress_updater.get_counts()
        results.add_result_text(f"""<br><span>
            {time.time() - start_time:.2f}s - 
            <i>{copy_definition['definition_name']}:</i> 
            {total_processed_destinations} destinations
            {f'''processed with {total_processed_sources} sources''' if is_across else "processed"}
        </span>""")
    return results


def apply_process_chain(
    process_chain: Sequence[
        Union[
            KanjiumToJavdejongProcess,
            RegexProcess,
            FontsCheckProcess,
            KanaHighlightProcess,
        ]
    ],
    text: str,
    destination_note: Note,
    show_error_message: Optional[Callable[[str], None]] = None,
    file_cache: Optional[dict] = None,
) -> Union[str, None]:
    """
    Apply a list of processes to a text
    :param process_chain: The list of processes to apply
    :param text: The text to apply the processes to
    :param destination_note: The note to use for the processes
    :param show_error_message: A function to show error messages
    :param file_cache: A dictionary to cache opened files' content
    :return: The text after the processes have been applied or None if there was an error
    """
    if not show_error_message:

        def show_error_message(message: str):
            print(message)

    for process in process_chain:
        try:
            if is_kana_highlight_process(process):
                text = kana_highlight_process(
                    text=text,
                    kanji_field=process.get("kanji_field", ""),
                    return_type=process.get("return_type", "kana_only"),
                    note=destination_note,
                    show_error_message=show_error_message,
                )

            elif is_regex_process(process):
                text = regex_process(
                    text=text,
                    regex=process.get("regex", None),
                    replacement=process.get("replacement", None),
                    flags=process.get("flags", None),
                    show_error_message=show_error_message,
                )

            elif is_fonts_check_process(process):
                text = fonts_check_process(
                    text=text,
                    fonts_dict_file=process.get("fonts_dict_file", ""),
                    limit_to_fonts=process.get("limit_to_fonts", None),
                    character_limit_regex=process.get("character_limit_regex", None),
                    show_error_message=show_error_message,
                    file_cache=file_cache,
                )

            elif is_kanjium_to_javdejong_process(process):
                text = kanjium_to_javdejong_process(
                    text=text,
                    delimiter=process.get("delimiter", ""),
                    show_error_message=show_error_message,
                )
        except FatalProcessError as e:
            # If some process fails in a way that will always fail, we stop the whole op
            # so the user can fix the issue without needing to wait for the whole op to finish
            show_error_message(f"Error in {process['name']} process: {e}")
            return None
    return text


def copy_for_single_trigger_note(
    copy_definition: CopyDefinition,
    trigger_note: Note,
    results: Optional[CacheResults] = None,
    undo_entry: Optional[int] = None,
    field_only: Optional[str] = None,
    deck_id: Optional[int] = None,
    multiple_note_types: bool = False,
    show_error_message: Optional[Callable[[str], None]] = None,
    file_cache: Optional[dict] = None,
    progress_updater: Optional[ProgressUpdater] = None,
) -> bool:
    """
    Copy fields into a single note
    :param copy_definition: The definition of what to copy, includes process chains
    :param trigger_note: Note that triggered this copy or was targeted otherwise
    :param results: The results object to update the changes with
    :param undo_entry: The undo entry to merge the changes into
    :param field_only: Optional field to limit copying to. Used when copying is applied
      in the note editor
    :param deck_id: Deck ID where the cards are going into, only needed when adding
      a note since cards don't exist yet. Otherwise, the deck_ids are checked from the cards
      of the note
    :param multiple_note_types: Whether the copy is into multiple note types
    :param show_error_message: Optional function to show error messages
    :param file_cache: A dictionary to cache opened files' content
    :param progress_updater: Optional object to update the progress bar
    :return: Tuple of the op success + number of destination and source notes processed
    """
    if not show_error_message:

        def show_error_message(message: str):
            print(message)

    field_to_field_defs = copy_definition.get("field_to_field_defs", [])
    field_to_variable_defs = copy_definition.get("field_to_variable_defs", [])
    only_copy_into_decks = copy_definition.get("only_copy_into_decks", None)
    copy_from_cards_query = copy_definition.get("copy_from_cards_query", None)
    select_card_by = copy_definition.get("select_card_by", None)
    select_card_count = copy_definition.get("select_card_count", None)
    select_card_separator = copy_definition.get("select_card_separator", None)
    copy_mode = copy_definition.get("copy_mode", None)
    across_mode_direction = copy_definition.get("across_mode_direction", None)

    extra_state: dict[str, Any] = {}

    # Step 0: Get variable values for the note
    variable_values_dict = None
    if field_to_variable_defs is not None:
        variable_values_dict = get_variable_values_for_note(
            field_to_variable_defs=field_to_variable_defs,
            note=trigger_note,
            show_error_message=show_error_message,
            file_cache=file_cache,
        )

    # Step 1: get source/destination notes for this card
    destination_notes = []
    source_notes = []
    if copy_mode == COPY_MODE_WITHIN_NOTE:
        destination_notes = [trigger_note]
        source_notes = [trigger_note]
    elif copy_mode == COPY_MODE_ACROSS_NOTES:
        if across_mode_direction not in [
            DIRECTION_DESTINATION_TO_SOURCES,
            DIRECTION_SOURCE_TO_DESTINATIONS,
        ]:
            show_error_message("Error in copy fields: missing across mode direction value")
            return False
        target_notes = get_across_target_notes(
            copy_from_cards_query=copy_from_cards_query or "",
            trigger_note=trigger_note,
            deck_id=deck_id,
            extra_state=extra_state,
            only_copy_into_decks=only_copy_into_decks,
            select_card_by=select_card_by,
            select_card_count=select_card_count,
            show_error_message=show_error_message,
            variable_values_dict=variable_values_dict,
        )
        if across_mode_direction == DIRECTION_DESTINATION_TO_SOURCES:
            destination_notes = [trigger_note]
            source_notes = target_notes
        elif across_mode_direction == DIRECTION_SOURCE_TO_DESTINATIONS:
            destination_notes = target_notes
            source_notes = [trigger_note]
    else:
        show_error_message("Error in copy fields: missing copy mode value")
        return False

    if len(source_notes) == 0:
        show_error_message(
            f"Error in copy fields: No source/destination notes for note {trigger_note.id}"
        )

    # Step 2: Get value for each field we are copying into
    for destination_note in destination_notes:
        success = copy_into_single_note(
            field_to_field_defs=field_to_field_defs,
            destination_note=destination_note,
            source_notes=source_notes,
            variable_values_dict=variable_values_dict,
            field_only=field_only,
            multiple_note_types=multiple_note_types,
            select_card_separator=select_card_separator,
            file_cache=file_cache,
            show_error_message=show_error_message,
            progress_updater=progress_updater,
        )
        if progress_updater is not None:
            progress_updater.update_counts(
                processed_destinations_inc=1,
            )
            progress_updater.render_update()
        mw.col.update_note(destination_note)
        # undo_entry has to be updated after every undoable op or the last_step will
        # increment causing an "target undo op not found" error!
        changes = None
        if undo_entry is not None:
            changes = mw.col.merge_undo_entries(undo_entry)
        if results is not None and changes is not None:
            results.changes = changes
        if not success:
            return False

    return True


def copy_into_single_note(
    field_to_field_defs: list[CopyFieldToField],
    destination_note: Note,
    source_notes: list[Note],
    variable_values_dict: Optional[dict] = None,
    field_only: Optional[str] = None,
    multiple_note_types: bool = False,
    select_card_separator: Optional[str] = None,
    file_cache: Optional[dict] = None,
    show_error_message: Optional[Callable[[str], None]] = None,
    progress_updater: Optional[ProgressUpdater] = None,
) -> bool:
    if not show_error_message:

        def show_error_message(message: str):
            print(message)

    for field_to_field_def in field_to_field_defs:
        copy_into_note_field = field_to_field_def.get("copy_into_note_field", "")
        if field_only is not None and copy_into_note_field != field_only:
            continue
        copy_from_text = field_to_field_def.get("copy_from_text", "")
        copy_if_empty = field_to_field_def.get("copy_if_empty", False)
        process_chain = field_to_field_def.get("process_chain", None)

        try:
            cur_field_value = destination_note[copy_into_note_field]
        except KeyError:
            show_error_message(
                f"Error in copy fields: Field '{copy_into_note_field}' not found in note"
            )
            return False

        if copy_if_empty and cur_field_value != "":
            continue

        # Step 2.1: Get the value from the notes, usually it's just one note
        result_val = get_field_values_from_notes(
            copy_from_text=copy_from_text,
            notes=source_notes,
            dest_note=destination_note,
            multiple_note_types=multiple_note_types,
            select_card_separator=select_card_separator,
            show_error_message=show_error_message,
            variable_values_dict=variable_values_dict,
            progress_updater=progress_updater,
        )
        # Step 2.2: If we have further processing steps, run them
        if process_chain is not None:
            processed_val = apply_process_chain(
                process_chain=process_chain,
                text=result_val,
                destination_note=destination_note,
                show_error_message=show_error_message,
                file_cache=file_cache,
            )
            # result_val should always be at least "", None indicates an error
            if processed_val is None:
                show_error_message(
                    f"Error in copy fields: Process chain failed for field {copy_into_note_field}"
                )
                return False
            result_val = processed_val

        # Finally, copy the value into the note
        destination_note[copy_into_note_field] = result_val
    return True


def get_variable_values_for_note(
    field_to_variable_defs: list[CopyFieldToVariable],
    note: Note,
    file_cache: Optional[dict] = None,
    show_error_message: Optional[Callable[[str], None]] = None,
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
                "Error getting variable values: Invalid fields in copy_from_text:"
                f" {', '.join(invalid_fields)}"
            )

        # Step 2: If we have further processing steps, run them
        if process_chain is not None and interpolated_value is not None:
            interpolated_value = apply_process_chain(
                process_chain=process_chain,
                text=interpolated_value,
                destination_note=note,
                show_error_message=show_error_message,
                file_cache=file_cache,
            )
            if interpolated_value is None:
                return None

        variable_values_dict[copy_into_variable] = interpolated_value

    return variable_values_dict


def get_across_target_notes(
    copy_from_cards_query: str,
    trigger_note: Note,
    extra_state: dict,
    select_card_by: Optional[SelectCardByType] = "Random",
    deck_id: Optional[int] = None,
    variable_values_dict: Optional[dict] = None,
    only_copy_into_decks: Optional[str] = None,
    select_card_count: Optional[str] = "1",
    show_error_message: Optional[Callable[[str], None]] = None,
) -> list[Note]:
    """
    Get the target notes based on the search value and the query. These will either be
    the source notes or the destination notes depending on the across mode direction

    :param copy_from_cards_query: The query to find the cards to copy from.
            Uses {{}} syntax for note fields and special values
    :param trigger_note: The note to copy into, used to interpolate the query
    :param select_card_by: How to select the card to copy from, if we get multiple results using the
            the query
    :param deck_id: Optional deck id of the note to copy into
    :param extra_state: A dictionary to store cached values to re-use in subsequent calls
    :param variable_values_dict: A dictionary of custom variable values to use in interpolating text
    :param only_copy_into_decks: A comma separated whitelist of deck names. Limits the cards to copy
        from to only those in the decks in the whitelist
    :param select_card_count: How many cards to select from the query. Default is 1
    :param show_error_message: A function to show error messages, used for storing all messages
        until the end of the whole operation to show them in a GUI element at the end
    :return: A list of notes to copy from
    """
    if not show_error_message:

        def show_error_message(message: str):
            print(message)

    if not select_card_by:
        show_error_message("Error in copy fields: Required value 'select_card_by' was missing.")
        return []

    if select_card_by not in SELECT_CARD_BY_VALUES:
        show_error_message(
            f"""Error in copy fields: incorrect 'select_card_by' value '{select_card_by}'.
            It must be one of {SELECT_CARD_BY_VALUES}""",
        )
        return []

    if select_card_count:
        try:
            select_card_count_int = int(select_card_count)
            if select_card_count_int < 0:
                raise ValueError
        except ValueError:
            show_error_message(
                "Error in copy fields: Incorrect 'select_card_count' value"
                f" '{select_card_count_int}'. Value must be a positive integer or 0"
            )
            return []
    else:
        select_card_count_int = 1

    if only_copy_into_decks and only_copy_into_decks != "-":
        # Check if the current deck is in the white list, otherwise we don't copy into this note
        # whitelist deck is a list of deck or sub deck names
        # parent names can't be included since adding :: would break the filter text
        target_deck_names = only_copy_into_decks.strip('""').split('", "')

        whitelist_dids = [
            mw.col.decks.id_for_name(target_deck_name) for target_deck_name in target_deck_names
        ]
        unique_whitelist_dids = set(whitelist_dids)
        deck_ids = []
        if deck_id is not None:
            deck_ids.append(deck_id)
        else:
            for card in trigger_note.cards():
                deck_ids.append(card.odid or card.did)
        if deck_ids and not any(deck_id in unique_whitelist_dids for deck_id in deck_ids):
            return []

    interpolated_cards_query, invalid_fields = interpolate_from_text(
        copy_from_cards_query,
        source_note=trigger_note,
        variable_values_dict=variable_values_dict,
    )
    if not interpolated_cards_query:
        show_error_message("Error in copy fields: Could not interpolate copy_from_cards_query")
        return []
    cards_query_id = base64.b64encode(f"cards{interpolated_cards_query}".encode()).decode()
    try:
        card_ids = extra_state[cards_query_id]
    except KeyError:
        card_ids = mw.col.find_cards(interpolated_cards_query)
        extra_state[cards_query_id] = card_ids

    if len(invalid_fields) > 0:
        show_error_message(
            "Error in copy fields: Invalid fields in copy_from_cards_query:"
            f" {', '.join(invalid_fields)}"
        )

    if len(card_ids) == 0:
        show_error_message(
            "Error in copy fields: Did not find any cards with"
            f" copy_from_cards_query='{interpolated_cards_query}'"
        )
        return []

    assert mw.col.db is not None
    db = mw.col.db
    # zero is a special value that means all cards
    if select_card_count_int == 0:
        distinct_note_ids = db.list(
            f"SELECT DISTINCT nid FROM cards c WHERE c.id IN {ids2str(card_ids)}"
        )
        return [mw.col.get_note(note_id) for note_id in distinct_note_ids]

    # select a card or cards based on the select_card_by value
    selected_notes = []
    for i in range(select_card_count_int):
        selected_card_id = None
        # just iterate the list
        if select_card_by == "None" and len(card_ids) > 0:
            selected_card_id = card_ids.pop()
            if selected_card_id:
                selected_notes.append(mw.col.get_note(mw.col.get_card(selected_card_id).nid))
            continue
        elif len(card_ids) == 0:
            break
        # We don't make this key entirely unique as we want to cache the selected card for the same
        # deck_id and from_note_type_id combination, so that getting a different field from the same
        # card type will still return the same card

        card_select_key = base64.b64encode(
            f"selected_card{interpolated_cards_query}{select_card_by}{i}".encode()
        ).decode()

        if select_card_by == "Random":
            # We don't want to cache this as it should in fact be different each time
            selected_card_id = random.choice(card_ids)
        elif select_card_by == "Least_reps":
            # Loop through cards and find the one with the least reviews
            # Check cache first
            try:
                selected_card_id = extra_state[card_select_key]
            except KeyError:
                selected_card_id = min(
                    card_ids,
                    key=lambda c: db.scalar(f"SELECT COUNT() FROM revlog WHERE cid = {c}"),
                )
                extra_state = {card_select_key: selected_card_id}
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
    variable_values_dict: Optional[dict] = None,
    select_card_separator: Optional[str] = ", ",
    show_error_message: Optional[Callable[[str], None]] = None,
    progress_updater: Optional[ProgressUpdater] = None,
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
    :param select_card_separator: The separator to use when joining the values from the notes.
        Irrelevant if there is only one note
    :param show_error_message: A function to show error messages, used for storing all messages
        until the end of the whole operation to show them in a GUI element at the end
    :param progress_updater: An object to update the progress bar with
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
                destination_note=dest_note,
                variable_values_dict=variable_values_dict,
                multiple_note_types=multiple_note_types,
            )
        except ValueError as e:
            show_error_message(f"Error in text interpolation: {e}")
            break

        if len(invalid_fields) > 0:
            show_error_message(
                "Error in copy fields: Invalid fields in copy_from_text:"
                f" {', '.join(invalid_fields)}"
            )

        if progress_updater is not None:
            progress_updater.update_counts(processed_sources_inc=1)
            progress_updater.render_update()
        result_val += f"{select_card_separator if i > 0 else ''}{interpolated_value}"

    return result_val
