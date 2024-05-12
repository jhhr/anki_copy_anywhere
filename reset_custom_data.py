from typing import Sequence

from anki.cards import CardId, Card
from anki.utils import ids2str
from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import QWidget
from aqt.utils import tooltip

from .utils import write_custom_data


def reset_custom_data(
        *,
        parent: QWidget,
        card_ids: Sequence[CardId],
        reset_field: str = None,
):
    """
    Reset the custom_data "fc" field for cards that have it to None
    :return:
    """
    edited_cids = []

    def update_op(col, edited_cids=None):
        if edited_cids is None:
            edited_cids = []
        card_ids_query = ''
        if card_ids and len(card_ids) > 0:
            card_ids_query = f"AND id IN {ids2str(card_ids)}"

        undo_entry = col.add_custom_undo_entry(
            f"Reset customData '{reset_field if reset_field else 'all fields'}' field for {len(card_ids)} cards.")
        # Find the cards that have a custom_data field
        card_ids_to_update = mw.col.db.list(
            f"""
            SELECT id
            FROM cards
            WHERE data != ''
            AND json_extract(data, '$.cd') IS NOT NULL
            {card_ids_query}
            """
        )
        cards_to_update = [Card(col=mw.col, id=cid) for cid in card_ids_to_update]
        for card in cards_to_update:
            edited_cids.append(card.id)
            write_custom_data(card, reset_field, None)
        col.update_cards(cards_to_update)
        return col.merge_undo_entries(undo_entry)

    return CollectionOp(
        parent=parent,
        op=lambda col: update_op(col, edited_cids),
    ).success(
        lambda out: tooltip(
            f"Reset customData for in {len(edited_cids)}/{len(card_ids)} selected notes.",
            parent=parent,
            period=5000,
        )
    ).run_in_background()
