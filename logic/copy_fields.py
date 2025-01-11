import base64
import random
import time
import html
from typing import Callable, Union, Optional, Tuple, Sequence, Any

from anki.collection import Progress, OpChanges
from anki.cards import Card
from anki.notes import Note, NoteId
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
from .interpolate_fields import interpolate_from_text, TARGET_NOTES_COUNT
from .kana_highlight_process import kana_highlight_process
from .kana_highlight_process import WithTagsDef
from .kanjium_to_javdejong_process import kanjium_to_javdejong_process
from .regex_process import regex_process
from ..configuration import (
    CopyDefinition,
    definition_modifies_other_notes,
    CopyFieldToVariable,
    CopyFieldToField,
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
        total_notes_count: int,
        progrss_update_def: ProgressUpdateDef,
        is_across: bool,
    ):
        self.start_time = start_time
        self.definition_name = definition_name
        self.total_notes_count = total_notes_count
        self.progress_update_def = progrss_update_def
        self.is_across = is_across
        self.note_cnt = 0
        self.total_processed_sources = 0
        self.total_processed_destinations = 0
        self.last_render_update = 0.0

    def update_counts(
        self,
        note_cnt_inc: Optional[int] = None,
        processed_sources_inc: Optional[int] = None,
        processed_destinations_inc: Optional[int] = None,
    ):
        if note_cnt_inc is not None:
            self.note_cnt += note_cnt_inc
        if processed_sources_inc is not None:
            self.total_processed_sources += processed_sources_inc
        if processed_destinations_inc is not None:
            self.total_processed_destinations += processed_destinations_inc

    def get_counts(self) -> Tuple[int, int, int]:
        return self.note_cnt, self.total_processed_sources, self.total_processed_destinations

    def maybe_render_update(self):
        elapsed_s = time.time() - self.start_time
        elapsed_since_last_update = elapsed_s - self.last_render_update
        if elapsed_since_last_update < 1.0:
            # Don't update the progress bar too often, it can cause a crash as apparently
            # two progress updates could happen simultaneously causing
            # self.progress_update_def.label to be None
            return
        self.last_render_update = elapsed_s

        elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_s))
        self.progress_update_def.label = f"""<strong>{html.escape(self.definition_name)}</strong>:
        <br>Copied {self.note_cnt}/{self.total_notes_count} notes
        <br><small>Notes processed - destinations: {self.total_processed_destinations}
            {f', sources: {self.total_processed_sources}' if self.is_across else ''}</small>
        <br>Time: {elapsed_time}"""
        if self.note_cnt / self.total_notes_count > 0.10 or elapsed_s > 5:
            if self.note_cnt > 0:
                eta_s = (elapsed_s / self.note_cnt) * (self.total_notes_count - self.note_cnt)
                eta = time.strftime("%H:%M:%S", time.gmtime(eta_s))
                self.progress_update_def.label += f" - ETA: {eta}"
        self.progress_update_def.value = self.note_cnt
        self.progress_update_def.max_value = self.total_notes_count


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
    is_sync: bool = False,
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
    :param is_sync: Whether this is a sync operation or not. Affects what notes are queried
        and results reporting
    """
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
        if not copy_definitions:
            show_error_message("Error in copy fields: No definitions given")
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
                show_message=show_error_message,
                is_sync=is_sync,
                copied_into_cards=copied_into_cards,
                copied_into_notes=copied_into_notes,
                results=results,
                progress_update_def=progress_update_def,
                field_only=field_only,
            )
            if mw.progress.want_cancel():
                break
        if is_sync:
            for card in copied_into_cards:
                write_custom_data(card, key="fc", value="1")
            mw.col.update_cards(copied_into_cards)
            results.changes = mw.col.merge_undo_entries(undo_entry)
        # undo_entry has to be updated after every undoable op or the last_step will
        # increment causing an "target undo op not found" error!
        mw.col.update_notes(copied_into_notes)
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
    copied_into_notes: list[Note],
    results: CacheResults,
    progress_update_def: ProgressUpdateDef,
    is_sync: Optional[bool] = False,
    note_ids: Optional[Sequence[int]] = None,
    field_only: Optional[str] = None,
    show_message: Optional[Callable[[str], None]] = None,
) -> CacheResults:
    """
    Function run to copy stuff into many notes at once.
    :param copy_definition: The definition of what to copy, includes process chains
    :param copied_into_cards: An initially empty list of cards that will be appended to with the
        cards of the notes that were copied into
    :param copied_into_notes: An initially empty list of notes that will be appended to with the
        notes that were copied into
    :param undo_entry: The undo entry to merge the changes into
    :param results: The results object to update with the final result text
    :param progress_update_def: The progress update object to update the progress bar with
    :param note_ids: The note ids to copy into, if None, all notes of the note type are copied into
    :param field_only: Optional field to limit copying to. Used when copying is applied
      in the note editor
    :param show_message: Function to show error messages
    :param is_sync: Whether this is a sync operation or not
    :return: the CacheResults object passed as results
    """
    copy_into_note_types = copy_definition.get("copy_into_note_types", None)
    definition_name = copy_definition.get("definition_name", "")

    start_time = time.time()

    note_cnt = 0
    debug_text = ""
    if not show_message:

        def show_error_message(message: str):
            nonlocal debug_text
            debug_text += f"<br/>{note_cnt}--{message}"
            print(message)

    else:

        def show_error_message(message: str):
            show_message(f"\n{note_cnt}--{message}")

    if copy_into_note_types is None:
        show_error_message(
            f"""Error in copy fields: Note type for copy_into_note_types '{copy_into_note_types}'
            not found, check your spelling""",
        )
        return results

    # Split by comma and remove the first wrapping " but keeping the last one
    note_type_names = copy_into_note_types.strip('""').split('", "')
    note_type_ids = list(
        filter(None, [mw.col.models.id_for_name(name) for name in note_type_names])
    )

    assert mw.col.db is not None

    nids_query = f"AND n.id IN {ids2str(note_ids)}" if note_ids is not None else ""
    notes = [
        mw.col.get_note(nid)
        for nid in mw.col.db.list(
            # When syncing, only copy into notes that have been been flagged for a field change
            # in the custom scheduler by setting the field changed flag to 1
            # and filter by any given note_ids
            f"""
        SELECT n.id
        FROM notes n, cards c
        WHERE n.mid IN {ids2str(note_type_ids)}
        AND c.nid = n.id
        AND json_extract(json_extract(c.data, '$.cd'), '$.fc') = 0
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
        show_error_message(
            f"Error in copy fields: Did not find any notes of note type(s) {copy_into_note_types}"
        )
        return results

    total_notes_count = len(notes)
    is_across = copy_definition["copy_mode"] == COPY_MODE_ACROSS_NOTES

    progress_updater = ProgressUpdater(
        start_time=start_time,
        definition_name=definition_name,
        total_notes_count=total_notes_count,
        progrss_update_def=progress_update_def,
        is_across=is_across,
    )

    # Cache any opened files, so process chains can use them instead of needing to open them again
    # contents will be cached by file name
    # Key: file name, Value: whatever a process would need from the file
    file_cache: dict[str, Any] = {}

    total_processed_sources = 0
    total_processed_destinations = 0
    for note in notes:
        note_cnt += 1

        success = copy_for_single_trigger_note(
            copy_definition=copy_definition,
            trigger_note=note,
            copied_into_notes=copied_into_notes,
            field_only=field_only,
            show_error_message=show_error_message,
            file_cache=file_cache,
            progress_updater=progress_updater,
        )

        progress_updater.update_counts(note_cnt_inc=1)

        copied_into_cards.extend(note.cards())

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
                    with_tags_def=WithTagsDef(
                        process.get("wrap_readings_in_tags", True),
                        process.get("merge_consecutive_tags", True),
                        process.get("assume_dictionary_form", False),
                    ),
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
    copied_into_notes: Optional[list[Note]] = None,
    field_only: Optional[str] = None,
    deck_id: Optional[int] = None,
    show_error_message: Optional[Callable[[str], None]] = None,
    file_cache: Optional[dict] = None,
    progress_updater: Optional[ProgressUpdater] = None,
) -> bool:
    """
    Copy fields into a single note
    :param copy_definition: The definition of what to copy, includes process chains
    :param trigger_note: Note that triggered this copy or was targeted otherwise
    :param copied_into_notes: A list of notes that were copied into, to be appended to
        with the destination notes. Can be omitted, if it's not necessary to run
        mw.col.update_notes(copied_into_notes) after the operation
    :param field_only: Optional field to limit copying to. Used when copying is applied
      in the note editor
    :param deck_id: Deck ID where the cards are going into, only needed when adding
      a note since cards don't exist yet. Otherwise, the deck_ids are checked from the cards
      of the note
    :param is_note_editor: Whether copy fields is being triggered in the note editor
    :param show_error_message: Optional function to show error messages
    :param file_cache: A dictionary to cache opened files' content
    :param progress_updater: Optional object to update the progress bar
    :return: bool indicating success
    """
    if not show_error_message:

        def show_error_message(message: str):
            print(message)

    field_to_field_defs = copy_definition.get("field_to_field_defs", [])
    field_to_variable_defs = copy_definition.get("field_to_variable_defs", [])
    only_copy_into_decks = copy_definition.get("only_copy_into_decks", None)
    copy_from_cards_query = copy_definition.get("copy_from_cards_query", None)
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
            sort_by_field=sort_by_field,
            only_copy_into_decks=only_copy_into_decks,
            select_card_by=select_card_by,
            select_card_count=select_card_count,
            show_error_message=show_error_message,
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
        show_error_message("Error in copy fields: missing copy mode value")
        return False

    if len(source_notes) == 0:
        # This case is ok, there's just nothing to do
        # But we need to end early here so that the target fields aren't wiped
        # So, return True
        return True

    # Step 2: Get value for each field we are copying into
    for i, destination_note in enumerate(destination_notes):
        success = copy_into_single_note(
            field_to_field_defs=field_to_field_defs,
            destination_note=destination_note,
            source_notes=source_notes,
            variable_values_dict=variable_values_dict,
            field_only=field_only,
            modifies_other_notes=definition_modifies_other_notes(copy_definition),
            multiple_note_types=multiple_note_types,
            select_card_separator=select_card_separator,
            file_cache=file_cache,
            show_error_message=show_error_message,
            progress_updater=progress_updater,
        )
        if progress_updater is not None:
            progress_updater.update_counts(processed_destinations_inc=1)
            progress_updater.maybe_render_update()
        if copied_into_notes is not None:
            copied_into_notes.append(destination_note)
        if not success:
            return False

    return True


def copy_into_single_note(
    field_to_field_defs: list[CopyFieldToField],
    destination_note: Note,
    source_notes: list[Note],
    variable_values_dict: Optional[dict] = None,
    field_only: Optional[str] = None,
    modifies_other_notes: bool = False,
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
) -> dict:
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
    copy_from_cards_query: str,
    trigger_note: Note,
    extra_state: dict,
    select_card_by: Optional[SelectCardByType] = "Random",
    sort_by_field: Optional[str] = None,
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

    return sort_notes(selected_notes)


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
            progress_updater.maybe_render_update()
        result_val += f"{select_card_separator if i > 0 else ''}{interpolated_value}"

    return result_val
