from anki.cards import Card


def merge_cards(card: Card, card_to_merge: Card) -> None:
    """Merge the editable details of card_to_merge into card. Mutates card.

    Used to ensure that when performing mw.col.update_card on a card,
    all changes are included. This is because performing an update_card on a card
    with the same id will overwrite previous changes made to that card in the same
    operation.

    :param card: The card to merge into, will be mutated.
    :param card_to_merge: The card to merge from.
    """
    # Sanity check, ids should match
    if card.id != card_to_merge.id:
        raise ValueError("Cannot merge cards with different IDs.")
    # Merge custom data
    card.custom_data = card_to_merge.custom_data

    # Merge all other editable properties
    card.due = card_to_merge.due
    card.ivl = card_to_merge.ivl
    card.factor = card_to_merge.factor
    card.reps = card_to_merge.reps
    card.queue = card_to_merge.queue
    card.type = card_to_merge.type
    card.odid = card_to_merge.odid
    card.did = card_to_merge.did
    card.flags = card_to_merge.flags
