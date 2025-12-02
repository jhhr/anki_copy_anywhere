import base64
import random
import time
import html
import re
from typing import Callable, Union, Optional, Tuple, Sequence, Any

from anki.collection import OpChanges
from anki.cards import Card
from anki.notes import Note, NoteId
from anki.decks import DeckId
from anki.utils import ids2str
from aqt import mw
from aqt.operations import CollectionOp

from aqt.qt import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QScrollArea,
    QGuiApplication,
)
from aqt.utils import tooltip

from ..utils.file_exists_in_media_folder import file_exists_in_media_folder
from ..utils.write_to_media_folder import write_to_media_folder
from ..utils.write_custom_data import write_custom_data
from ..utils.logger import Logger
from ..utils.move_card_to_deck import move_card_to_deck

from .FatalProcessError import FatalProcessError
from .fonts_check_process import fonts_check_process
from .interpolate_fields import interpolate_from_text, TARGET_NOTES_COUNT
from .kana_highlight_process import kana_highlight_process
from .kana_highlight_process import WithTagsDef
from .kanjium_to_javdejong_process import kanjium_to_javdejong_process
from .regex_process import regex_process
from ..configuration import (
    CARD_TYPE_SEPARATOR,
    Config,
    CopyDefinition,
    definition_modifies_other_notes,
    CopyFieldToVariable,
    CopyFieldToField,
    CopyFieldToFile,
    CardAction,
    get_field_to_field_unfocus_trigger_fields,
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
from ..utils.duplicate_note import (
    duplicate_note,
)

CONSOLE_COLOR_RE = r"\x1b\[[0-9;]*m"


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
        # remove console colors as they can't be displayed in the text box
        message_list = [
            re.sub(CONSOLE_COLOR_RE, "", line) if isinstance(line, str) else str(line)
            for line in message_list
        ]
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

    def __init__(self, result_text: str, changes, count: int = 0):
        self.result_text = result_text
        self.changes = changes
        self.count = count

    def set_result_text(self, result_text):
        self.result_text = result_text

    def add_result_text(self, result_text):
        self.result_text += result_text

    def get_result_text(self):
        return self.result_text

    def incr_count(self, count: int):
        self.count += count

    def get_count(self):
        return self.count


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
        total_notes_count: int,
        is_across: bool,
        title: Optional[str],
    ):
        self.start_time = start_time
        self.definition_name = definition_name
        self.total_notes_count = total_notes_count
        self.is_across = is_across
        self.note_cnt = 0
        self.total_processed_sources = 0
        self.total_processed_destinations = 0
        self.total_processed_files = 0
        self.last_render_update = 0.0
        if title is None:
            title = "Copying fields"
        self.set_title(title)

    def update_counts(
        self,
        note_cnt_inc: Optional[int] = None,
        processed_sources_inc: Optional[int] = None,
        processed_destinations_inc: Optional[int] = None,
        processed_files_inc: Optional[int] = None,
    ):
        if note_cnt_inc is not None:
            self.note_cnt += note_cnt_inc
        if processed_sources_inc is not None:
            self.total_processed_sources += processed_sources_inc
        if processed_destinations_inc is not None:
            self.total_processed_destinations += processed_destinations_inc
        if processed_files_inc is not None:
            self.total_processed_files += processed_files_inc

    def get_counts(self) -> Tuple[int, int, int, int]:
        return (
            self.note_cnt,
            self.total_processed_sources,
            self.total_processed_destinations,
            self.total_processed_files,
        )

    def maybe_render_update(self, force: bool = False):
        elapsed_s = time.time() - self.start_time
        elapsed_since_last_update = elapsed_s - self.last_render_update
        is_last_note = self.note_cnt == self.total_notes_count
        no_notes = not self.total_notes_count > 0
        if (elapsed_since_last_update < 0.5 and not (force or is_last_note)) or no_notes:
            return
        self.last_render_update = elapsed_s

        elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_s))
        label = f"""<strong>{html.escape(self.definition_name)}</strong>:
        <br>Copied {self.note_cnt}/{self.total_notes_count} notes
        <br><small>Processed{f'-  destination notes: {self.total_processed_destinations}'
                    if self.total_processed_destinations > 0 else ''}
            {f'- files: {self.total_processed_files}' if self.total_processed_files > 0 else ''}
            {f', sources: {self.total_processed_sources}' if self.is_across else ''}</small>
        <br>Time: {elapsed_time}"""
        if self.note_cnt / self.total_notes_count > 0.10 or elapsed_s > 1:
            if self.note_cnt > 0:
                eta_s = (elapsed_s / self.note_cnt) * (self.total_notes_count - self.note_cnt)
                eta = time.strftime("%H:%M:%S", time.gmtime(eta_s))
                label += f" - ETA: {eta}"
        value = self.note_cnt
        max_value = self.total_notes_count

        mw.taskman.run_on_main(
            lambda: mw.progress.update(
                label=label,
                value=value,
                max=max_value,
            )
        )

    def set_title(self, title: str):
        mw.taskman.run_on_main(lambda: mw.progress.set_title(title))


def make_copy_fields_undo_text(
    copy_definitions: list[CopyDefinition],
    note_count: Optional[int] = None,
    suffix: Optional[str] = "",
) -> str:
    """
    Create an undo text for a copy fields operation
    :param copy_definitions: The definitions of what to copy, includes process chains
    :param note_count: The number of notes that will be copied into
    :param suffix: A suffix to add to the undo text
    :return: The undo text
    """
    if len(copy_definitions) == 1:
        undo_text = f"Copy fields ({copy_definitions[0]['definition_name']})"
    else:
        undo_text = f"Copy fields with {len(copy_definitions)} definitions"

    if note_count:
        undo_text += f" for {note_count} notes"
    if suffix:
        undo_text += f" {suffix}"
    return undo_text


def copy_fields(
    copy_definitions: list[CopyDefinition],
    note_ids: Optional[Sequence[Union[int, NoteId]]] = None,
    note_ids_per_definition: Optional[list[Sequence[Union[int, NoteId]]]] = None,
    parent=None,
    field_only: Optional[str] = None,
    undo_entry: Optional[int] = None,
    undo_text_suffix: Optional[str] = "",
    update_sync_result: Optional[Callable[[str, int], None]] = None,
    on_done: Optional[Callable[[], None]] = None,
    progress_title: Optional[str] = None,
):
    """
    Run many copy definitions at once using CollectionOp. Includes fancy progress updates
    :param copy_definitions: The definitions of what to copy
    :param note_ids: The note ids to copy into, if None, all notes of the note type are copied into
    :param note_ids_per_definition: An alternate of note_ids, a list of note ids to copy into for
        each definition used by PickCopyDefinitionsDialog
    :param parent: The parent widget
    :param undo_entry: The undo entry to merge the changes into, if None, a custom entry
        is created
    :param field_only: Optional field to limit copying to. Used when copying is applied
      in the note editor
    :param undo_text_suffix: Optional suffix to add to the undo text.
        Useless, if undo_entry is passed
    :param update_sync_result: Provided when this is a sync operation. Used to update the sync
        result text and count
    :param on_done: Optional function to run when the operation is done
    :param progress_title: Optional title for the progress dialog
    """
    start_time = time.time()
    debug_texts = []
    is_sync = update_sync_result is not None
    config = Config()
    config.load()
    logger = Logger()

    def log(message: str):
        nonlocal debug_texts
        debug_texts.append(message)
        print(message)

    logger = Logger(config.log_level, log=log)

    def on_success(copy_results: CacheResults):
        mw.progress.finish()
        result = copy_results.get_result_text()
        # Don't show a blank tooltip with just the time
        if result:
            main_time = (
                f"{time.time() - start_time:.2f}s total time"
                if len(copy_definitions) > 1
                else "Finished in "
            )
            result_text = f"{main_time}{result}"
            count = copy_results.get_count()
            if update_sync_result is not None:
                update_sync_result(result_text, count)
            else:
                tooltip(
                    result_text,
                    parent=parent,
                    period=5000 + len(copy_definitions) * 1000,
                    y_offset=100,
                )
        if not is_sync and len(debug_texts) > 0:
            ScrollMessageBox(debug_texts, title="Copy fields debug Messages", parent=parent)
        if on_done is not None:
            on_done()

    def on_failure(exception):
        mw.progress.finish()
        logger.error(f"Copying failed: {exception}")
        if not is_sync and len(debug_texts) > 0:
            ScrollMessageBox(debug_texts, title="Copy Fields debug Messages", parent=parent)
        if on_done is not None:
            on_done()
        # Need to raise the exception to get the traceback to the cause in the console
        raise exception

    def op(_) -> CacheResults:
        if not copy_definitions:
            logger.error("Error in copy fields: No definitions given")
            return CacheResults(result_text="", changes=None)

        copied_into_cards: list[Card] = []
        copied_into_notes: list[Note] = []
        # If an undo_entry isn't passed, create one
        nonlocal undo_entry
        if undo_entry is None:
            note_count = None
            if note_ids is not None:
                note_count = len(note_ids)
            elif note_ids_per_definition is not None:
                note_count = sum(len(ids) for ids in note_ids_per_definition)
            undo_text = make_copy_fields_undo_text(
                copy_definitions=copy_definitions,
                note_count=note_count,
                suffix=undo_text_suffix,
            )
            undo_entry = mw.col.add_custom_undo_entry(undo_text)
        results = CacheResults(
            result_text="",
            changes=mw.col.merge_undo_entries(undo_entry),
        )

        for i, copy_definition in enumerate(copy_definitions):
            results = copy_fields_in_background(
                copy_definition=copy_definition,
                note_ids=(
                    note_ids_per_definition[i] if note_ids_per_definition is not None else note_ids
                ),
                logger=logger,
                is_sync=is_sync,
                copied_into_cards=copied_into_cards,
                copied_into_notes=copied_into_notes,
                results=results,
                field_only=field_only,
                progress_title=progress_title,
            )
            # Update each modified note after every operation, so that if multiple ops are updating
            # the same note, all changes are saved
            # Because of this, if multiple ops use the same note data as a source, the final result
            # depends on the order of the ops
            mw.col.update_notes(copied_into_notes)
            # undo_entry has to be updated after every undoable op or the last_step will
            # increment causing an "target undo op not found" error!
            results.changes = mw.col.merge_undo_entries(undo_entry)
            if mw.progress.want_cancel():
                break
        if is_sync:
            # Update card custom-data after all ops are complete
            for card in copied_into_cards:
                write_custom_data(card, key="fc", value=1)
            mw.col.update_cards(copied_into_cards)
            results.changes = mw.col.merge_undo_entries(undo_entry)
        return results

    return (
        CollectionOp(
            parent=parent,
            op=op,
        )
        .success(on_success)
        .failure(on_failure)
        .run_in_background()
    )


def copy_fields_in_background(
    copy_definition: CopyDefinition,
    copied_into_cards: list[Card],
    copied_into_notes: list[Note],
    results: CacheResults,
    is_sync: Optional[bool] = False,
    note_ids: Optional[Sequence[int]] = None,
    field_only: Optional[str] = None,
    logger: Logger = Logger("error"),
    progress_title: Optional[str] = None,
) -> CacheResults:
    """
    Function run to copy stuff into many notes at once.
    :param copy_definition: The definition of what to copy, includes process chains
    :param copied_into_cards: An initially empty list of cards that will be appended to with the
        cards of the notes that were copied into
    :param copied_into_notes: An initially empty list of notes that will be appended to with the
        notes that were copied into
    :param results: The results object to update with the final result text
    :param note_ids: The note ids to copy into, if None, all notes of the note type are copied into
    :param field_only: Optional field to limit copying to. Used when copying is applied
      in the note editor
    :param logger: Logger to use for errors and debug messages
    :param is_sync: Whether this is a sync operation or not
    :param progress_title: Optional title for the progress dialog
    :return: the CacheResults object passed as results
    """
    copy_into_note_types = copy_definition.get("copy_into_note_types", None)
    definition_name = copy_definition.get("definition_name", "")

    start_time = time.time()

    note_cnt = 0

    if copy_into_note_types is None:
        logger.error(
            f"""Error in copy fields: Note type for copy_into_note_types '{copy_into_note_types}'
            not found, check your spelling""",
        )
        return results

    # Split by comma and remove the first wrapping " but keeping the last one
    note_type_names = copy_into_note_types.strip('""').split('", "')
    note_type_ids = list(
        filter(None, [mw.col.models.id_for_name(name) for name in note_type_names])
    )

    copy_on_review = copy_definition.get("copy_on_review", False)
    copy_on_sync = copy_definition.get("copy_on_sync", False)
    copy_on_sync_after_review = not copy_on_review and copy_on_sync

    assert mw.col.db is not None

    nids_query = f"AND n.id IN {ids2str(note_ids)}" if note_ids is not None else ""
    notes = [
        mw.col.get_note(nid)
        for nid in mw.col.db.list(
            # When syncing, only copy into notes that have been been flagged for a field change
            # in the custom scheduler by setting the field changed flag to 0 or -1 in note_hooks.py
            # and filter by any given note_ids
            f"""
        SELECT n.id
        FROM notes n, cards c
        WHERE n.mid IN {ids2str(note_type_ids)}
        AND c.nid = n.id
        AND json_extract(json_extract(c.data, '$.cd'), '$.fc') {f"IN (0, -1)"
                                                                if copy_on_sync_after_review
                                                                else "= 0"}
        {nids_query}
        """
            if is_sync
            # Otherwise, copy into all notes and filter by any given note_ids
            else f"""
        SELECT n.id
        FROM notes n
        WHERE n.mid IN {ids2str(note_type_ids)}
        {nids_query}
        """
        )
    ]

    if not is_sync and len(notes) == 0:
        # When syncing, it's normal to get zero results if no cards have been reviewed
        logger.error(
            f"Error in copy fields: Did not find any notes of note type(s) {copy_into_note_types}"
        )
        return results

    total_notes_count = len(notes)
    is_across = copy_definition["copy_mode"] == COPY_MODE_ACROSS_NOTES

    progress_updater = ProgressUpdater(
        start_time=start_time,
        definition_name=definition_name,
        total_notes_count=total_notes_count,
        is_across=is_across,
        title=progress_title,
    )

    # Cache any opened files, so process chains can use them instead of needing to open them again
    # contents will be cached by file name
    # Key: file name, Value: whatever a process would need from the file
    file_cache: dict[str, Any] = {}

    total_processed_sources = 0
    total_processed_dests = 0
    for note in notes:
        note_cnt += 1

        success = copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            is_sync=is_sync,
            copied_into_notes=copied_into_notes,
            copied_into_cards=copied_into_cards,
            field_only=field_only,
            logger=logger,
            file_cache=file_cache,
            progress_updater=progress_updater,
        )

        progress_updater.update_counts(note_cnt_inc=1)

        progress_updater.maybe_render_update()

        if mw.progress.want_cancel():
            break

        if not success:
            # Something went wrong, stop operation so the issue can be debugged
            return results

    # When syncing, don't show a pointless message that nothing was done
    # Otherwise, when copy fields is run manually, you want to know the result in any case
    should_report_result = len(notes) > 0 if is_sync else True
    if should_report_result:
        #  Get counts from ProgressUpdater and render the final update
        _, total_processed_sources, total_processed_dests, total_processed_files = (
            progress_updater.get_counts()
        )
        results.add_result_text(f"""<br><span>
            {time.time() - start_time:.2f}s -
            <i>{html.escape(copy_definition['definition_name'])}:</i>
            {f'{total_processed_dests} destinations' if total_processed_dests > 0 else ''}
            {f'{total_processed_files} files' if total_processed_files > 0 else ''}
            {f'''processed with {total_processed_sources} sources''' if is_across else "processed"}
        </span>""")
        results.incr_count(1)
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
    notes: list[Note],
    dest_note: Note = None,
    variable_values_dict: Optional[dict] = None,
    multiple_note_types: bool = False,
    progress_updater: Optional[ProgressUpdater] = None,
    logger: Logger = Logger("error"),
    file_cache: Optional[dict] = None,
) -> Union[str, None]:
    """
    Apply a list of processes to a text
    :param process_chain: The list of processes to apply
    :param text: The text to apply the processes to
    :param dest_note: The note to use for the processes that is the destination of the result value
    :param notes: Other source notes to use for the processes, used for interpolation
    :param variable_values_dict: A dictionary of variable values to use for interpolation
    :param multiple_note_types: Whether the copy is across multiple note types
    :param progress_updater: Optional object to update the progress bar
    :param logger: Logger to use for errors and debug messages
    :param file_cache: A dictionary to cache opened files' content
    :return: The text after the processes have been applied or None if there was an error
    """

    for process in process_chain:
        try:
            if is_kana_highlight_process(process):
                text = kana_highlight_process(
                    text=text,
                    kanji_field=process.get("kanji_field", ""),
                    return_type=process.get("return_type", "kana_only"),
                    with_tags_def=WithTagsDef(
                        process.get("wrap_readings_in_tags", True),
                        process.get("merge_consecutive_tags", True),
                        process.get("onyomi_to_katakana", False),
                        False,  # include_suru_okuri always false
                    ),
                    note=dest_note,
                    logger=logger,
                )

            elif is_regex_process(process):
                use_all_notes = process.get("use_all_notes", False)
                interpolated_regex = get_field_values_from_notes(
                    copy_from_text=process.get("regex", ""),
                    notes=notes if use_all_notes and len(notes) > 1 else [dest_note],
                    dest_note=dest_note if use_all_notes and len(notes) > 1 else None,
                    variable_values_dict=variable_values_dict,
                    select_card_separator=process.get("regex_separator", ""),
                    multiple_note_types=multiple_note_types,
                    logger=logger,
                    progress_updater=progress_updater,
                )

                interpolated_replacement = get_field_values_from_notes(
                    copy_from_text=process.get("replacement", ""),
                    notes=notes if use_all_notes and len(notes) > 1 else [dest_note],
                    dest_note=dest_note if use_all_notes and len(notes) > 1 else None,
                    variable_values_dict=variable_values_dict,
                    select_card_separator=process.get("replacement_separator", ""),
                    multiple_note_types=multiple_note_types,
                    logger=logger,
                    progress_updater=progress_updater,
                )
                text = regex_process(
                    text=text,
                    regex=interpolated_regex,
                    replacement=interpolated_replacement,
                    flags=process.get("flags", None),
                    logger=logger,
                )

            elif is_fonts_check_process(process):
                text = fonts_check_process(
                    text=text,
                    fonts_dict_file=process.get("fonts_dict_file", ""),
                    limit_to_fonts=process.get("limit_to_fonts", None),
                    character_limit_regex=process.get("character_limit_regex", None),
                    logger=logger,
                    file_cache=file_cache,
                )

            elif is_kanjium_to_javdejong_process(process):
                text = kanjium_to_javdejong_process(
                    text=text,
                    delimiter=process.get("delimiter", ""),
                    logger=logger,
                )
        except FatalProcessError as e:
            # If some process fails in a way that will always fail, we stop the whole op
            # so the user can fix the issue without needing to wait for the whole op to finish
            logger.error(f"Error in {process['name']} process: {e}")
            return None
    return text


class CopyFailedException(Exception):
    pass


def copy_for_single_trigger_note(
    copy_definition: CopyDefinition,
    trigger_note: Note,
    is_sync: Optional[bool] = False,
    copied_into_notes: Optional[list[Note]] = None,
    copied_into_cards: Optional[list[Card]] = None,
    field_only: Optional[str] = None,
    deck_id: Optional[int] = None,
    logger: Logger = Logger("error"),
    file_cache: Optional[dict] = None,
    progress_updater: Optional[ProgressUpdater] = None,
) -> bool:
    """
    Copy fields into a single note
    :param copy_definition: The definition of what to copy, includes process chains
    :param trigger_note: Note that triggered this copy or was targeted otherwise
    :param is_sync: Whether this is a sync operation or not
    :param copied_into_notes: A list of notes that were copied into, to be appended to
        with the destination notes. Can be omitted, if it's not necessary to run
        mw.col.update_notes(copied_into_notes) after the operation
    :param copied_into_cards: A list of cards that were copied into, to be appended to
        with the cards of the destination notes. Can be omitted, if it's not necessary to run
        mw.col.update_cards(copied_into_cards) after the operation
    :param field_only: Optional field to limit copying to. Used when copying is applied
      in the note editor
    :param deck_id: Deck ID where the cards are going into, only needed when adding
      a note since cards don't exist yet. Otherwise, the deck_ids are checked from the cards
      of the note
    :param is_note_editor: Whether copy fields is being triggered in the note editor
    :param logger: Logger to use for errors and debug messages
    :param file_cache: A dictionary to cache opened files' content
    :param progress_updater: Optional object to update the progress bar
    :return: bool indicating success
    """

    field_to_field_defs = copy_definition.get("field_to_field_defs", [])
    field_to_file_defs = copy_definition.get("field_to_file_defs", [])
    field_to_variable_defs = copy_definition.get("field_to_variable_defs", [])
    card_actions = copy_definition.get("card_actions", [])
    only_copy_into_decks = copy_definition.get("only_copy_into_decks", None)
    include_subdecks = copy_definition.get("include_subdecks", False)
    copy_from_cards_query = copy_definition.get("copy_from_cards_query", None)
    copy_condition_query = copy_definition.get("copy_condition_query", None)
    condition_only_on_sync = copy_definition.get("condition_only_on_sync", False)
    add_tags = copy_definition.get("add_tags", "")
    remove_tags = copy_definition.get("remove_tags", "")
    sort_by_field = copy_definition.get("sort_by_field", None)
    select_card_by = copy_definition.get("select_card_by", None)
    select_card_count = copy_definition.get("select_card_count", None)
    select_card_separator = copy_definition.get("select_card_separator", None)
    copy_mode = copy_definition.get("copy_mode", None)
    across_mode_direction = copy_definition.get("across_mode_direction", None)

    copy_into_note_types = copy_definition.get("copy_into_note_types", "")
    note_type_names = copy_into_note_types.strip('""').split('", "')
    multiple_note_types = len(note_type_names) > 1

    extra_state: dict[str, Any] = {}

    # Step 0: Get variable values for the note
    variable_values_dict = None
    if field_to_variable_defs is not None:
        variable_values_dict = get_variable_values_for_note(
            field_to_variable_defs=field_to_variable_defs,
            note=trigger_note,
            logger=logger,
            file_cache=file_cache,
        )

    # Step 1: Check if possibly defined condition matches for this note
    condition_check = bool(copy_condition_query)
    if condition_only_on_sync and not is_sync:
        condition_check = False
    if condition_check:
        interpolated_condition_query, invalid_fields = interpolate_from_text(
            copy_condition_query,
            source_note=trigger_note,
            variable_values_dict=variable_values_dict,
        )
        if interpolated_condition_query:
            # Search for notes, this works for card properties just as well
            note_ids = mw.col.find_notes(f"{interpolated_condition_query} nid:{trigger_note.id}")
            if (note_ids is None) or (len(note_ids) == 0):
                logger.debug(
                    "copy_for_single_trigger_note: "
                    f"Condition query '{interpolated_condition_query}' did not match for note "
                    f"id {trigger_note.id}"
                )
                # Condition did not match, so skip this note, things are ok, so return True
                return True
        else:
            logger.error(
                f"Error in copy fields: Condition query '{copy_condition_query}' "
                f"could not be interpolated for note id {trigger_note.id} "
                f"due to missing fields: {', '.join(invalid_fields)}"
            )
            return False

    # Step 2: Get source/destination notes for this card
    destination_notes = []
    source_notes = []
    if copy_mode == COPY_MODE_WITHIN_NOTE:
        destination_notes = [trigger_note]
        # Duplicate the trigger note so that the source and destination note are not the same object
        # otherwise, as field-to-field defs are processed, the source note will be modified
        # resulting in the final result depending on the order of the defs. In particular swapping
        # two fields would not work as expected
        source_notes = [duplicate_note(trigger_note)]
    elif copy_mode == COPY_MODE_ACROSS_NOTES:
        if across_mode_direction not in [
            DIRECTION_DESTINATION_TO_SOURCES,
            DIRECTION_SOURCE_TO_DESTINATIONS,
        ]:
            logger.error("Error in copy fields: missing across mode direction value")
            return False
        target_notes = get_across_target_notes(
            copy_definition=copy_definition,
            copy_from_cards_query=copy_from_cards_query or "",
            trigger_note=trigger_note,
            deck_id=deck_id,
            extra_state=extra_state,
            sort_by_field=sort_by_field,
            only_copy_into_decks=only_copy_into_decks,
            include_subdecks=include_subdecks,
            select_card_by=select_card_by,
            select_card_count=select_card_count,
            logger=logger,
            variable_values_dict=variable_values_dict,
        )
        variable_values_dict[TARGET_NOTES_COUNT] = len(target_notes)
        if across_mode_direction == DIRECTION_DESTINATION_TO_SOURCES:
            destination_notes = [trigger_note]
            source_notes = target_notes
        elif across_mode_direction == DIRECTION_SOURCE_TO_DESTINATIONS:
            destination_notes = target_notes
            source_notes = [trigger_note]
    else:
        logger.error("Error in copy fields: missing copy mode value")
        return False

    if len(source_notes) == 0:
        if progress_updater is not None:
            progress_updater.update_counts(processed_destinations_inc=len(destination_notes))
        # This case is ok, there's just nothing to do
        # But we need to end early here so that the target fields aren't wiped
        # So, return True
        return True

    if progress_updater is not None:
        progress_updater.update_counts(processed_sources_inc=len(source_notes))
    # Step 3: Get value for each field we are copying into
    for destination_note in destination_notes:
        try:
            copied_into_dest_note, copied_into_file, dest_note_cards = copy_into_single_note(
                field_to_field_defs=field_to_field_defs,
                field_to_file_defs=field_to_file_defs,
                card_actions=card_actions,
                destination_note=destination_note,
                source_notes=source_notes,
                add_tags=add_tags,
                remove_tags=remove_tags,
                variable_values_dict=variable_values_dict,
                field_only=field_only,
                modifies_other_notes=definition_modifies_other_notes(copy_definition),
                multiple_note_types=multiple_note_types,
                select_card_separator=select_card_separator,
                file_cache=file_cache,
                logger=logger,
                progress_updater=progress_updater,
            )
            if progress_updater is not None:
                progress_updater.update_counts(
                    processed_destinations_inc=1 if copied_into_dest_note else None,
                    processed_files_inc=1 if copied_into_file else None,
                )
            if copied_into_notes is not None and copied_into_dest_note:
                copied_into_notes.append(destination_note)
            if copied_into_cards is not None and dest_note_cards:
                copied_into_cards.extend(dest_note_cards)
        except CopyFailedException:
            return False

    return True


def copy_into_single_note(
    field_to_field_defs: list[CopyFieldToField],
    field_to_file_defs: list[CopyFieldToFile],
    card_actions: list[CardAction],
    destination_note: Note,
    source_notes: list[Note],
    add_tags: Optional[str] = "",
    remove_tags: Optional[str] = "",
    variable_values_dict: Optional[dict] = None,
    field_only: Optional[str] = None,
    modifies_other_notes: bool = False,
    multiple_note_types: bool = False,
    select_card_separator: Optional[str] = None,
    file_cache: Optional[dict] = None,
    logger: Logger = Logger("error"),
    progress_updater: Optional[ProgressUpdater] = None,
) -> Tuple[bool, bool, list[Card]]:

    modified_dest_note = False
    wrote_to_file = False

    # Duplicate the destination note so field-to-field defs that use the destination note's fields
    # as source values all use the same initial values, instead of the source values being modified
    # as the field-to-field defs are processed
    destination_note_copy = duplicate_note(destination_note)

    for field_to_field_def in field_to_field_defs:
        copy_into_note_field = field_to_field_def.get("copy_into_note_field", "")
        trigger_fields = get_field_to_field_unfocus_trigger_fields(
            field_to_field_def, modifies_other_notes
        )
        if field_only is not None and field_only not in trigger_fields:
            # If we're only meant to copy a specific def, defined by the field_only parameter
            # Note, depending on the mode, may be that field_only == copy_into_note_field
            continue
        copy_from_text = field_to_field_def.get("copy_from_text", "")
        copy_if_empty = field_to_field_def.get("copy_if_empty", False)
        process_chain = field_to_field_def.get("process_chain", None)

        try:
            cur_field_value = destination_note[copy_into_note_field]
        except KeyError:
            logger.error(f"Error in copy fields: Field '{copy_into_note_field}' not found in note")
            # Rest of defs are not processed
            raise CopyFailedException

        if copy_if_empty and cur_field_value != "":
            continue

        result_val = get_field_values_from_notes(
            copy_from_text=copy_from_text,
            notes=source_notes,
            dest_note=destination_note_copy,
            multiple_note_types=multiple_note_types,
            select_card_separator=select_card_separator,
            logger=logger,
            variable_values_dict=variable_values_dict,
            progress_updater=progress_updater,
        )
        if process_chain is not None:
            processed_val = apply_process_chain(
                process_chain=process_chain,
                text=result_val,
                notes=source_notes,
                dest_note=destination_note_copy,
                multiple_note_types=multiple_note_types,
                variable_values_dict=variable_values_dict,
                progress_updater=progress_updater,
                logger=logger,
                file_cache=file_cache,
            )
            # result_val should always be at least "", None indicates an error
            if processed_val is None:
                logger.error(
                    f"Error in copy fields: Process chain failed for field {copy_into_note_field}"
                )
                raise CopyFailedException
            result_val = processed_val

        # Finally, copy the value into the note
        destination_note[copy_into_note_field] = result_val
        modified_dest_note = True

    for tag in add_tags.strip('""').split('", "'):
        if destination_note.has_tag(tag):
            continue
        destination_note.add_tag(tag)
        modified_dest_note = True

    for tag in remove_tags.strip('""').split('", "'):
        if not destination_note.has_tag(tag):
            continue
        destination_note.remove_tag(tag)
        modified_dest_note = True

    for field_to_file_def in field_to_file_defs:
        copy_into_filename = field_to_file_def.get("copy_into_filename", "")
        copy_from_text = field_to_file_def.get("copy_from_text", "")
        process_chain = field_to_file_def.get("process_chain", None)
        dont_overwrite = field_to_file_def.get("copy_if_empty", False)

        if not copy_into_filename:
            logger.error("Error in copy fields: No file name provided")
            raise CopyFailedException

        # Interpolate filename with values from the note
        copy_into_filename = get_field_values_from_notes(
            copy_from_text=copy_into_filename,
            notes=[destination_note],
            dest_note=destination_note_copy,
            multiple_note_types=multiple_note_types,
            select_card_separator=select_card_separator,
            logger=logger,
            variable_values_dict=variable_values_dict,
            progress_updater=progress_updater,
        )

        if dont_overwrite and file_exists_in_media_folder(copy_into_filename):
            continue

        result_val = get_field_values_from_notes(
            copy_from_text=copy_from_text,
            notes=source_notes,
            dest_note=destination_note_copy,
            multiple_note_types=multiple_note_types,
            select_card_separator=select_card_separator,
            logger=logger,
            variable_values_dict=variable_values_dict,
            progress_updater=progress_updater,
        )
        if process_chain is not None:
            processed_val = apply_process_chain(
                process_chain=process_chain,
                text=result_val,
                notes=source_notes,
                dest_note=destination_note_copy,
                multiple_note_types=multiple_note_types,
                variable_values_dict=variable_values_dict,
                progress_updater=progress_updater,
                logger=logger,
                file_cache=file_cache,
            )
            # result_val should always be at least "", None indicates an error
            if processed_val is None:
                logger.error(
                    f"Error in copy fields: Process chain failed for file {copy_into_filename}"
                )
                raise CopyFailedException
            result_val = processed_val

        # Finally, copy the value into the file
        try:
            write_to_media_folder(copy_into_filename, result_val)
            wrote_to_file = True
        except Exception as e:
            logger.error(f"Error in writing to file: {e}")
            raise CopyFailedException

    card_actions_by_template_name = {}
    dest_note_type = destination_note.note_type()
    for card_action in card_actions:
        # The card_type_name contains the note type and card type separated by CARD_TYPE_SEPARATOR
        note_type_and_card_type = card_action.get("card_type_name ", "")
        if CARD_TYPE_SEPARATOR not in note_type_and_card_type:
            logger.error(
                f"Error in copy fields: Invalid card type name '{note_type_and_card_type}'"
            )
            # Skip this card action
            continue
        note_type_name, card_type_name = note_type_and_card_type.split(CARD_TYPE_SEPARATOR, 1)
        if note_type_name != dest_note_type["name"]:
            # This card action is not for this note type
            continue
        card_actions_by_template_name[card_type_name] = card_action

    dest_note_cards = destination_note.cards()
    for card in dest_note_cards:
        card_template_name = card.template()["name"]
        card_action = card_actions_by_template_name.get(card_template_name, None)
        if card_action is None:
            continue
        change_deck = card_action.get("change_deck", None)
        suspend_card = card_action.get("suspend", None)
        bury_card = card_action.get("bury", None)
        set_flag = card_action.get("set_flag", None)
        if change_deck != "-" and change_deck is not None:
            move_card_to_deck(card, change_deck, logger=logger)
        if suspend_card in [True, False]:
            # see pylib/anki/cards.py for queue values
            if suspend_card:
                card.queue = -1
            else:
                card.queue = card.type
        if bury_card in [True, False] and card.queue != -1:
            # Card cannot be buried, if it is suspended
            # To bury a suspended card, it must first be unsuspended with a suspend action
            if bury_card:
                card.queue = -2
            else:
                card.queue = card.type
        if isinstance(set_flag, int) and 0 <= set_flag <= 7:
            card.set_user_flag(set_flag)
    return (modified_dest_note, wrote_to_file, dest_note_cards)


def get_variable_values_for_note(
    field_to_variable_defs: list[CopyFieldToVariable],
    note: Note,
    file_cache: Optional[dict] = None,
    logger: Logger = Logger("error"),
) -> dict:
    """
    Get the values for the variables from the note
    :param field_to_variable_defs: The definitions of the variables to get
    :param note: The note to get the values from
    :param file_cache: A dictionary to cache opened files' content for process chains
    :param logger: Logger to use for errors and debug messages
    :return: A dictionary of the values for the variables or None if there was an error
    """

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
            logger.error(
                "Error getting variable values: Invalid fields in copy_from_text:"
                f" {', '.join(invalid_fields)}"
            )

        # Step 2: If we have further processing steps, run them
        if process_chain is not None and interpolated_value is not None:
            interpolated_value = apply_process_chain(
                process_chain=process_chain,
                text=interpolated_value,
                dest_note=note,
                notes=[note],
                multiple_note_types=False,
                logger=logger,
                file_cache=file_cache,
            )
            if interpolated_value is None:
                return {}

        variable_values_dict[copy_into_variable] = interpolated_value

    return variable_values_dict


def int_sort_by_field_value(note: Note, sort_by_field) -> int:
    try:
        return int(note[sort_by_field])
    except ValueError:
        return 0


def sort_by_field_value(note: Note, sort_by_field) -> Any:
    try:
        return note[sort_by_field]
    except KeyError:
        return ""


def get_across_target_notes(
    copy_definition: CopyDefinition,
    copy_from_cards_query: str,
    trigger_note: Note,
    extra_state: dict,
    select_card_by: Optional[SelectCardByType] = "Random",
    sort_by_field: Optional[str] = None,
    deck_id: Optional[int] = None,
    variable_values_dict: Optional[dict] = None,
    only_copy_into_decks: Optional[str] = None,
    include_subdecks: bool = False,
    select_card_count: Optional[str] = "1",
    logger: Logger = Logger("error"),
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
    :param include_subdecks: Whether to include subdecks of the whitelisted decks
    :param select_card_count: How many cards to select from the query. Default is 1
    :param logger: Logger to use for errors and debug messages.
    :return: A list of notes to copy from
    """
    logger.debug(
        f"get_across_target_notes: copy_from_cards_query='{copy_from_cards_query}', "
        f"select_card_by='{select_card_by}', deck_id={deck_id}, "
        f"only_copy_into_decks='{only_copy_into_decks}', select_card_count='{select_card_count}', "
        f"include_subdecks={include_subdecks}"
    )

    if not select_card_by:
        logger.error("Error in copy fields: Required value 'select_card_by' was missing.")
        return []

    if select_card_by not in SELECT_CARD_BY_VALUES:
        logger.error(
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
            logger.error(
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

        unique_whitelist_dids: set[DeckId] = {
            mw.col.decks.id_for_name(target_deck_name) for target_deck_name in target_deck_names
        }
        if include_subdecks:
            parent_dids = set()
            for did in unique_whitelist_dids:
                child_dids = [d[1] for d in mw.col.decks.children(did)]
                parent_dids.update(child_dids)
            unique_whitelist_dids.update(parent_dids)
        deck_ids_of_cards = []
        if deck_id is not None:
            deck_ids_of_cards.append(deck_id)
        else:
            for card in trigger_note.cards():
                deck_ids_of_cards.append(card.odid or card.did)
        logger.debug(
            f"get_across_target_notes: deck_ids={deck_ids_of_cards},"
            f" unique_whitelist_dids={unique_whitelist_dids}"
        )
        if deck_ids_of_cards and not any(
            deck_id in unique_whitelist_dids for deck_id in deck_ids_of_cards
        ):
            logger.debug(
                "get_across_target_notes: No deck id in whitelist, skipping copy for note"
                f" {trigger_note.id}"
            )
            return []

    interpolated_cards_query, invalid_fields = interpolate_from_text(
        copy_from_cards_query,
        source_note=trigger_note,
        variable_values_dict=variable_values_dict,
    )
    logger.debug(
        f"get_across_target_notes: interpolated_cards_query='{interpolated_cards_query}',"
        f" invalid_fields={invalid_fields}"
    )
    if not interpolated_cards_query:
        logger.error("Error in copy fields: Could not interpolate copy_from_cards_query")
        return []
    cards_query_id = base64.b64encode(f"cards{interpolated_cards_query}".encode()).decode()
    try:
        card_ids = extra_state[cards_query_id]
    except KeyError:
        card_ids = mw.col.find_cards(interpolated_cards_query)
        extra_state[cards_query_id] = card_ids

    if len(invalid_fields) > 0:
        logger.error(
            "Error in copy fields: Invalid fields in copy_from_cards_query:"
            f" {', '.join(invalid_fields)}"
        )

    if len(card_ids) == 0:
        if copy_definition.get("show_error_if_none_found", False):
            logger.error(
                "Error in copy fields: Did not find any cards with"
                f" copy_from_cards_query='{interpolated_cards_query}'"
            )
        else:
            logger.debug(f'No cards found with copy_from_cards_query="{interpolated_cards_query}",')
        return []

    has_sort_by_field = sort_by_field and sort_by_field != "-"

    def sort_notes(notes: list[Note]):
        if has_sort_by_field:
            notes.sort(key=lambda n: int_sort_by_field_value(n, sort_by_field), reverse=True)
        return notes

    assert mw.col.db is not None
    db = mw.col.db
    # zero is a special value that means all cards
    if select_card_count_int == 0:
        distinct_note_ids = db.list(
            f"SELECT DISTINCT nid FROM cards c WHERE c.id IN {ids2str(card_ids)}"
        )
        return sort_notes([mw.col.get_note(note_id) for note_id in distinct_note_ids])

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
            logger.error("Error in copy fields: could not select card")
            break

        # Remove selected card so it can't be picked again
        card_ids = [c for c in card_ids if c != selected_card_id]
        selected_note_id = mw.col.get_card(selected_card_id).nid

        selected_note = mw.col.get_note(selected_note_id)
        selected_notes.append(selected_note)

        # If we've run out of cards, stop and return what we got
        if len(card_ids) == 0:
            break

    return sort_notes(selected_notes)


def get_field_values_from_notes(
    copy_from_text: str,
    notes: list[Note],
    dest_note: Optional[Note],
    multiple_note_types: bool = False,
    variable_values_dict: Optional[dict] = None,
    select_card_separator: Optional[str] = ", ",
    logger: Logger = Logger("error"),
    progress_updater: Optional[ProgressUpdater] = None,
) -> str:
    """
    Get the value from the field in the selected notes gotten with interpolation.
    :param copy_from_text: Text defining the content to copy. Contains text and field names and
            special values enclosed in double curly braces that need to be replaced with the actual
            values from the notes.
    :param notes: The selected notes to get the value from. In the case of COPY_MODE_WITHIN_NOTE,
            this will be a list with only one note
    :param dest_note: The note to copy into, omitted in COPY_MODE_WITHIN_NOTE
    :param multiple_note_types: Whether the copy is into multiple note types
    :param variable_values_dict: A dictionary of custom variable values to use in interpolating text
    :param select_card_separator: The separator to use when joining the values from the notes.
        Irrelevant if there is only one note
    :param logger: Logger to use for errors and debug messages, used for storing all messages
        until the end of the whole operation to show them in a GUI element at the end
    :param progress_updater: An object to update the progress bar with
    :return: String with the values from the field in the notes
    """

    if copy_from_text is None:
        logger.error(
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
            logger.error(f"Error in text interpolation: {e}")
            break

        if len(invalid_fields) > 0:
            logger.error(
                "Error in copy fields: Invalid fields in copy_from_text:"
                f" {', '.join(invalid_fields)}"
            )

        if progress_updater is not None:
            progress_updater.maybe_render_update()
        result_val += f"{select_card_separator if i > 0 else ''}{interpolated_value}"

    return result_val
