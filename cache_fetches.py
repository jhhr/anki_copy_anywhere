import copy
import re
import time
from string import Template

from anki.consts import CARD_TYPE_REV, CARD_TYPE_NEW, CARD_TYPE_LRN, QUEUE_TYPE_SUSPENDED
from anki.decks import DeckManager
from anki.template import TemplateRenderContext
from anki.utils import ids2str
from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import QWidget
from aqt.utils import tooltip

from .configuration import Config
from .utils import CacheResults

# regex pattern to identify {{fetch=[...]}} calls in template
ANY_OTHER_STUFF = r'(?:[^}{])*?'
ARBITRARY_TEXT_NON_MATCHING = r'(?:[^:}{]+)'
# The field name can have spaces and pretty much any characters except :
CACHE_FILTER = r'(?:cache\[' + ARBITRARY_TEXT_NON_MATCHING + r']:)'
OTHER_FILTERS = r'(?:\w*:)*?'
FETCH_FILTER_RE = re.compile(
    # start of field replacement
    r'(\{\{' +
    # Cache filter first
    CACHE_FILTER +
    # potentially other filters chained before fetch filter
    OTHER_FILTERS +
    # start of the fetch filter
    r'fetch\[' +
    # All args in fetch filter
    ANY_OTHER_STUFF +
    # end of args and filter match group
    r']:' +
    # potentially other filters chained after fetch filter
    OTHER_FILTERS +
    # the text identifying the field in the note, field names can have spaces
    # and pretty much any characters except :
    ARBITRARY_TEXT_NON_MATCHING +
    # end of field replacement
    r'}})',
    # flags, allow . to match newlines
    re.S
)



def cache_fetches_in_background(
        did=None, card_ids=None, result_text="", from_menu=False
):
    """
    On sync finishing
    1. Get all due cards whose
      - templates contains fetch=[] field calls
      - those calls have specified a cache field
      - the card's customData "fc" > X days old
    2. Run the field calls to get their results
    3. Cache the results in the card's customData
    4. And set customData "fc" = <current_time>
    :return:
    """

    undo_text = "Cached fetches"
    if did:
        undo_text += f" for deck {mw.col.decks.get(did)['name']}"
    elif card_ids:
        undo_text += f" for selected {len(card_ids)} cards"

    undo_entry = mw.col.add_custom_undo_entry(undo_text)

    mw.taskman.run_on_main(
        lambda: mw.progress.start(
            label="Fetch Field Result Caching", max=0, immediate=False
        )
    )

    config = Config()
    config.load()
    DM = DeckManager(mw.col)

    tmpl_data_by_note_id = {}
    tmpl_data_by_model_id = {}

    for n in mw.col.models.all_names_and_ids():
        model = mw.col.models.get(n.id)

        # Get all models whose `tmpls` contain '{{fetch=[...]}}' calls
        tmpls = model["tmpls"]
        # Check each template with the regex and mark the ords that match
        for tmpl in tmpls:
            question_side_matches = re.findall(FETCH_FILTER_RE, tmpl["qfmt"])
            answer_side_matches = re.findall(FETCH_FILTER_RE, tmpl["afmt"])
            if len(question_side_matches) > 0 or len(answer_side_matches) > 0:
                all_matches = question_side_matches + answer_side_matches
                try:
                    tmpl_data_by_model_id[n.id]
                except KeyError:
                    tmpl_data_by_model_id[n.id] = {"ords": [], "fetch_filters": []}

                tmpl_data_by_model_id[n.id]["ords"].append(tmpl["ord"])
                # add each fetch filter match to the list
                for fetch_filter_groups in all_matches:
                    fetch_filter = fetch_filter_groups[0]
                    tmpl_data_by_model_id[n.id]["fetch_filters"].append(fetch_filter)

    # Get the notes matching the model_ids
    model_ids = ids2str(tmpl_data_by_model_id.keys())
    if model_ids == '()':
        return "There are no templates using fetch fields."

    notes = mw.col.db.all(f'SELECT id, mid FROM notes WHERE mid IN {model_ids}')

    if len(notes) == 0:
        return "There are no notes for any of the templates that are using fetch fields."

    for note_id, mid in notes:
        try:
            tmpl_data_by_note_id[note_id]
        except KeyError:
            tmpl_data_by_note_id[note_id] = {"ords": [], "fetch_filters": []}
        # add the ords from the model_id to the note_id
        tmpl_data_by_note_id[note_id]["ords"] = (tmpl_data_by_note_id[note_id]["ords"] +
                                                 tmpl_data_by_model_id[mid]["ords"])
        # add the fetch filters from the model_id to the note_id
        tmpl_data_by_note_id[note_id]["fetch_filters"] = (tmpl_data_by_note_id[note_id]["fetch_filters"] +
                                                          tmpl_data_by_model_id[mid]["fetch_filters"])

    cards = None

    # We'll find cards matching these notes
    note_ids = ids2str(tmpl_data_by_note_id.keys())

    # If we received a list of card_ids, we should only fetch for those cards
    if card_ids and len(card_ids) > 0:
        # Get the cards matching the card_ids without checking for fc cache value, due date or type
        # This is done when selecting cards to update from the browser, so we're assuming the user
        # wants to update the fetch fields for these specific cards
        # We'll still limit the cards to the notes that have fetch fields as we can only those anyway
        cards = mw.col.db.all(f"""
            SELECT
                id,
                nid,
                ord
            FROM cards
            WHERE id IN {ids2str(card_ids)} 
            AND nid IN {note_ids}
        """)
    else:
        # Otherwise update cards in the (possibly) specified deck
        did_query = ""
        if did:
            did_list = ids2str(DM.deck_and_child_ids(did))
            did_query = f"AND did in {did_list}"

        # This time we'll limit the cards to
        # review cards that are
        # - due in the next X days
        # - in the specified deck
        # - are not suspended
        # - have last updated the fetch fields more than Y days ago
        # or new cards that are
        # - limited to the first Z by order
        days_to_cache = config.days_to_cache_fields_auto
        if from_menu:
            days_to_cache = config.days_to_cache_fields_menu
        new_card_count = config.cache_new_cards_count

        query = Template(f"""
            SELECT 
                id,
                nid,
                ord
            FROM (
                SELECT 
                    *,
                    cast(json_extract(json_extract(data, '$$.cd'), '$$.fc') AS INTEGER) AS extracted_fc
                FROM cards
                WHERE nid IN {note_ids}
                AND queue != {QUEUE_TYPE_SUSPENDED}
                {did_query}
                
                $card_type_query
                
            ) AS subquery
            WHERE data = ''
            OR extracted_fc IS NULL
            OR (strftime('%s', 'now') - extracted_fc) / 86400 > {days_to_cache}
        """)

        review_cards = mw.col.db.all(query.substitute(card_type_query=f"""
                 AND (
                    (type = {CARD_TYPE_REV} AND due > 0 AND due <= {mw.col.sched.today} + {days_to_cache})
                    OR type = {CARD_TYPE_LRN}
                )
        """))
        new_cards = mw.col.db.all(query.substitute(card_type_query=f"""
                AND type = {CARD_TYPE_NEW}
                ORDER BY due ASC
                LIMIT {new_card_count}
        """))
        cards = review_cards + new_cards

    # We now have all cards for any notes, some cards may not have fetch fields
    # So, filter cards_due by matching on their nid to the ord in tmpl_ords_by_note_id
    filtered_cards = []
    for card_id, note_id, card_ord in cards:
        try:
            if card_ord in tmpl_data_by_note_id[note_id]["ords"]:
                filtered_cards.append([card_id, note_id, card_ord])
        except KeyError:
            continue

    total_cards_count = len(filtered_cards)
    card_cnt = 0

    mw.taskman.run_on_main(
        lambda: mw.progress.update(
            label=f"{card_cnt}/{total_cards_count} cards' fetches cached",
            value=card_cnt,
            max=total_cards_count,
        )
    )

    for card_id, note_id, card_ord in filtered_cards:
        card = mw.col.get_card(card_id)
        note = card.note()
        model = mw.col.models.get(note.mid)
        template = copy.copy(
            model["tmpls"][card_ord]
        )
        template["ord"] = card_ord
        render_context = TemplateRenderContext(
            col=mw.col,
            note=note,
            card=card,
            notetype=model,
            template=template,
            fill_empty=False,
        )
        render_context.extra_state["is_cache"] = True
        render_context.render()
        mw.col.merge_undo_entries(undo_entry)
        card_cnt += 1

        if card_cnt % 10 == 0:
            mw.taskman.run_on_main(
                lambda: mw.progress.update(
                    label=f"{card_cnt}/{total_cards_count} cards' fetches cached",
                    value=card_cnt,
                    max=total_cards_count,
                )
            )
        if mw.progress.want_cancel():
            break

    return CacheResults(
        result_text=f"{result_text + '<br>' if result_text != '' else ''}{card_cnt} cards' fetches cached",
        changes=mw.col.merge_undo_entries(undo_entry),
    )


def cache_fetches(did=None, card_ids=None, result_text="", from_menu=False, parent: QWidget = None):
    start_time = time.time()

    def on_done(cache_results):
        mw.progress.finish()
        tooltip(f"{cache_results.result_text} in {time.time() - start_time:.2f} seconds", parent=parent, period=5000)

    return (
        CollectionOp(
            parent=parent,
            op=lambda col: cache_fetches_in_background(did, card_ids, result_text, from_menu),
        )
        .success(on_done)
        .run_in_background()
    )
