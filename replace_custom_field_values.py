from typing import Sequence, Union

from anki.cards import CardId, Card
from anki.utils import ids2str
from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import QWidget
from aqt.utils import tooltip

from .utils import write_custom_data
    

def replace_custom_field_values(
        *,
        parent: QWidget,
        reset_field_key_values: Sequence[tuple[str, Union[str,int,None], Union[str,int,None], Union[str, None]]],
        card_ids: Sequence[CardId] = None,
):
    """
     Reset values of custom_data fields for cards that have them
    """
    edited_cids = []

    card_count = 0
    def update_op(col, edited_cids=None):
        nonlocal card_count
        if edited_cids is None:
            edited_cids = []
        card_ids_query = ''
        if card_ids and len(card_ids) > 0:
            card_ids_query = f"AND id IN {ids2str(card_ids)}"

        undo_entry = col.add_custom_undo_entry(
            f"Reset customData values"
        )
        for reset_field, prev_value, new_value, new_field in reset_field_key_values:
            # Find the cards that have a custom_data field
            card_ids_to_update = mw.col.db.list(
                f"""
                SELECT id
                FROM cards
                WHERE data != ''
                AND json_extract(data, '$.cd') IS NOT NULL
                AND json_extract(json_extract(data, '$.cd'), '$.{reset_field}') {'== ' + repr(prev_value) if prev_value is not None else 'IS NOT NULL'}
                {card_ids_query}
                """
            )
            card_count += len(card_ids_to_update)
            cards_to_update = [Card(col=mw.col, id=cid) for cid in card_ids_to_update]
            for card in cards_to_update:
                edited_cids.append(card.id)
                write_custom_data(
                    card,
                    key=reset_field,
                    value=new_value,
                    new_key=new_field
                    )
            col.update_cards(cards_to_update)
        return col.merge_undo_entries(undo_entry)

    return CollectionOp(
        parent=parent,
        op=lambda col: update_op(col, edited_cids),
    ).success(
        lambda out: tooltip(
            f"Reset customData for in {len(edited_cids)}/{card_count} selected notes.",
            parent=parent,
            period=5000,
        )
    ).run_in_background()
