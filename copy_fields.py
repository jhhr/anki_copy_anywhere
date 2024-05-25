import base64
import math
import random
import time
from operator import itemgetter
from typing import Callable

from anki.cards import Card
from anki.decks import DeckManager
from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import QWidget, QVBoxLayout, QLabel, QScrollArea, QMessageBox
from aqt.utils import tooltip

from .configuration import CopyDefinition
from .kana_highlight_process import KANA_HIGHLIGHT_PROCESS_NAME, kana_highlight_process
from .utils import write_custom_data, CacheResults

SEARCH_FIELD_VALUE_PLACEHOLDER = "$SEARCH_FIELD_VALUE$"


# Since printing into console on Windows breaks the characters to be unreadable,
# I'll use a GUI element to show debug messages
class ScrollMessageBox(QMessageBox):
    def __init__(self, l, *args, **kwargs):
        QMessageBox.__init__(self, *args, **kwargs)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self.content = QWidget()
        scroll.setWidget(self.content)
        lay = QVBoxLayout(self.content)
        for item in l:
            lay.addWidget(QLabel(item, self))
        self.layout().addWidget(scroll, 0, 0, 1, self.layout().columnCount())
        self.setStyleSheet("QScrollArea{min-width:300 px; min-height: 400px}")


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
):
    start_time = time.time()
    debug_text = ""

    def show_error_message(message: str):
        nonlocal debug_text
        debug_text += f"<br/>{message}"
        print(message)

    def on_done(copy_results):
        mw.progress.finish()
        tooltip(f"{copy_results.result_text} in {time.time() - start_time:.2f} seconds", parent=parent, period=5000)
        # For finding sentences to debug
        ScrollMessageBox.information(parent, "Debug results", debug_text)

    return (
        CollectionOp(
            parent=parent,
            op=lambda col: copy_fields_in_backgrounds(
                copy_definition=copy_definition,
                card_ids=card_ids,
                result_text=result_text,
                show_message=show_error_message,
            ),
        )
        .success(on_done)
        .run_in_background()
    )


def copy_fields_in_backgrounds(
        copy_definition: CopyDefinition,
        card_ids=None,
        result_text: str = "",
        show_message: Callable[[str], None] = None,
):
    """
    Function run to copy stuff into many notes at once.
    :param copy_definition: The definition of what to copy, includes process chains
    :param card_ids: The card ids to copy into. this would replace the copy_into_field from
       the copy_definition
    :param result_text: Text to be appended to and shown in the final result tooltip
    :param show_message: Function to show error messages
    :return:
    """
    (
        copy_into_note_type,
        copy_into_note_field,
        search_with_field,
        only_copy_into_decks,
        copy_from_cards_query,
        copy_from_field,
        copy_if_empty,
        select_card_by,
        select_card_count,
        select_card_separator,
        process_chain,
    ) = itemgetter(
        "copy_into_note_type",
        "copy_into_note_field",
        "search_with_field",
        "only_copy_into_decks",
        "copy_from_cards_query",
        "copy_from_field",
        "copy_if_empty",
        "select_card_by",
        "select_card_count",
        "select_card_separator",
        "process_chain",
    )(copy_definition)

    undo_text = "Copy fields"
    if card_ids:
        undo_text += f" for selected {len(card_ids)} cards"

    undo_entry = mw.col.add_custom_undo_entry(undo_text)

    mw.taskman.run_on_main(
        lambda: mw.progress.start(
            label="Copying into fields", max=0, immediate=False
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

    if search_with_field is None:
        show_error_message("Error in copy fields: Required 'search_with_field' value was missing")
        return ''

    # Get from_note_type_id either directly or through copy_into_note_type
    if copy_into_note_type is None:
        show_error_message(
            f"Error in copy fields: Note type for copy_into_note_type '{copy_into_note_type}' not found, check your spelling",
        )
        return ''
    elif card_ids is None:
        show_error_message(
            "Error in copy fields: Both 'card_ids' and 'copy_into_note_type' were missing. Either one is required")
        return ''

    # Get all cards of the target note type
    if card_ids is not None:
        cards = [mw.col.get_card(card_id) for card_id in card_ids]
    else:
        card_ids = mw.col.find_cards(f'"note:{copy_into_note_type}"')
        cards = [mw.col.get_card(card_id) for card_id in card_ids]
        if len(cards) == 0:
            show_error_message(
                f"Error in copy fields: Did not find any cards of note type '{copy_into_note_type}'")
            return ''

    total_cards_count = len(cards)

    mw.taskman.run_on_main(
        lambda: mw.progress.update(
            label=f"{card_cnt}/{total_cards_count} cards' fetches cached",
            value=card_cnt,
            max=total_cards_count,
        )
    )

    for card in cards:
        copy_into_note = card.note()

        # Get the field value from the card
        search_value = ""
        for field_name, field_value in copy_into_note.items():
            if field_name == search_with_field:
                search_value = field_value
                break

        result_val = copy_fields_for_card(
            search_value=search_value,
            copy_from_field=copy_from_field,
            copy_from_cards_query=copy_from_cards_query,
            card=card,
            is_cache=True,
            extra_state={},
            only_copy_into_decks=only_copy_into_decks,
            select_card_by=select_card_by,
            select_card_count=select_card_count,
            select_card_separator=select_card_separator,
            show_error_message=show_error_message,
        )
        # If we have further processing steps, run them
        show_error_message(result_val)
        if process_chain is not None:
            for process in process_chain:
                if process["name"] == KANA_HIGHLIGHT_PROCESS_NAME:
                    result_val = kana_highlight_process(
                        text=result_val,
                        onyomi_field=process["onyomi_field"],
                        kunyomi_field=process["kunyomi_field"],
                        kanji_field=process["kanji_field"],
                        is_cache=True,
                        note=copy_into_note,
                        show_error_message=show_error_message,
                    )
                    show_error_message(result_val)

        # Set the value into the target note
        try:
            cache_field_ord = copy_into_note.keys().index(copy_into_note_field)

            # only_empty can override the functionality of ignore_if_cached causing the card to be updated
            # that's why the default only_empty is False and ignore_if_cached is True
            if copy_if_empty and copy_into_note.fields[cache_field_ord] != "":
                break
            copy_into_note.fields[cache_field_ord] = result_val
            mw.col.update_note(copy_into_note)
            # Set cache time into card.custom_data
            write_custom_data(card, "fc", math.floor(time.time()))
            mw.col.update_card(card)

            mw.col.merge_undo_entries(undo_entry)
            card_cnt += 1

            if card_cnt % 10 == 0:
                mw.taskman.run_on_main(
                    lambda: mw.progress.update(
                        label=f"{card_cnt}/{total_cards_count} notes copied into",
                        value=card_cnt,
                        max=total_cards_count,
                    )
                )
            if mw.progress.want_cancel():
                break
        except ValueError:
            show_error_message(f"Error copy fields: a field '{copy_into_note_field}' was not found in note")

    return CacheResults(
        result_text=f"{result_text + '<br>' if result_text != '' else ''}{card_cnt} cards' copied into",
        changes=mw.col.merge_undo_entries(undo_entry),
    )


def copy_fields_for_card(
        search_value: str,
        copy_from_field: str,
        copy_from_cards_query: str,
        select_card_by: str,
        card: Card,
        is_cache: bool,
        extra_state: dict,
        only_copy_into_decks: str = None,
        select_card_count: str = '1',
        select_card_separator: str = ', ',
        show_error_message: Callable[[str], None] = None,
) -> str:
    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    if copy_from_field is None:
        show_error_message(
            "Error in copy fields: Required value 'copy_from_field' was missing.",
        )
        return ''

    if select_card_by is None:
        show_error_message(f"Error in copy fields: Required value 'select_card_by' was missing.")
        return ''
    elif select_card_by not in PICK_CARD_BY_VALID_VALUES:
        show_error_message(
            f"Error in copy fields: incorrect 'select_card_by' value '{select_card_by}'. It must be one of {PICK_CARD_BY_VALID_VALUES}",
        )
        return ''

    if select_card_count:
        try:
            select_card_count = int(select_card_count)
            if select_card_count < 1:
                raise ValueError
        except ValueError:
            show_error_message(
                f"Error in copy fields: Incorrect 'select_card_count' value '{select_card_count}' value must be a positive integer"
            )
            return ''
    else:
        select_card_count = 1

    DM = DeckManager(mw.col)

    if only_copy_into_decks is not None:
        # Check if the current deck is in the white list, otherwise we don't fetch
        cur_deck_id = card.odid or card.did
        # whitelist deck is a list of deck or sub deck names
        # parent names can't be included since adding :: would break the filter text
        target_deck_names = only_copy_into_decks.split(", ")

        whitelist_dids = [
            mw.col.decks.id_for_name(target_deck_name.strip('""')) for
            target_deck_name in target_deck_names
        ]
        whitelist_dids = set(whitelist_dids)
        if cur_deck_id not in whitelist_dids:
            return ''

    if select_card_separator is None:
        select_card_separator = ", "

    # Check for cached result again
    if SEARCH_FIELD_VALUE_PLACEHOLDER in copy_from_cards_query:
        copy_from_cards_query = copy_from_cards_query.replace(SEARCH_FIELD_VALUE_PLACEHOLDER, search_value)
    cards_query_id = base64.b64encode(f"cards{copy_from_cards_query}".encode()).decode()
    try:
        card_ids = extra_state[cards_query_id]
    except KeyError:
        # Always exclude suspended cards
        card_ids = mw.col.find_cards(f"{copy_from_cards_query} -is:suspended")
        extra_state[cards_query_id] = card_ids

    if (len(card_ids) == 0):
        show_error_message(
            f"Error in copy fields: Did not find any non-suspended cards with copy_from_cards_query'{copy_from_cards_query}'")
        if is_cache:
            # Set cache time into card.customData, so we don't keep querying this again
            write_custom_data(card, "fc", math.floor(time.time()))
            mw.col.update_card(card)
        return ''

    # select a card or cards based on the select_card_by value
    selected_card_ids = []
    result_val = ""
    for i in range(select_card_count):
        # remove already selected cards from cards
        selected_card_id = None
        selected_value = ""
        # We don't make this key entirely unique as we want to cache the selected card for the same deck_id and
        # from_note_type_id combination, so that getting a different field from the same card type will still return the same card
        card_select_key = base64.b64encode(
            f"selected_card{copy_from_cards_query}{select_card_by}{i}".encode()).decode()

        if select_card_by == 'Random':
            # We don't want to cache this as it should in fact be different each time
            selected_card_id = random.choice(card_ids)
        elif select_card_by == 'Random_stable':
            # pick the same random card for the same deck_id and from_note_type_id combination
            # this will still work for select_card_count as we're caching the selected card by the index too
            try:
                selected_card_id = extra_state[card_select_key]
            except KeyError:
                selected_card_id = random.choice(card_ids)
                extra_state[card_select_key] = selected_card_id
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

        selected_card_ids.append(selected_card_id)
        # Remove selected card so it can't be picked again
        card_ids = [c for c in card_ids if c != selected_card_id]
        selected_note_id = mw.col.get_card(selected_card_id).nid

        show_error_message(f"copy_from_field: {copy_from_field}, selected_note_id: {selected_note_id}")
        # And finally, return the value from the field in the note
        # Check for cached result again
        result_val_key = base64.b64encode(f"{selected_note_id}{copy_from_field}{i}".encode()).decode()
        try:
            selected_value = extra_state[result_val_key]
        except KeyError:
            selected_value = ""
            selected_note = mw.col.get_note(selected_note_id)
            for field_name, field_value in selected_note.items():
                # THe copy_from_field comes from a combox which apparently adds some extra whitespace chars
                if field_name == copy_from_field.strip():
                    selected_value = field_value
                    break

        result_val += f"{select_card_separator if i > 0 else ''}{selected_value}"

        # If we've run out of cards, stop and return what we got
        if len(card_ids) == 0:
            break

    return result_val
