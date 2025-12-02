from aqt import mw
from anki.cards import Card

from .logger import Logger


def move_card_to_deck(
    card: Card,
    deck_name: str = "",
    deck_id: int = None,
    logger: Logger = None,
) -> None:
    """Move the given card to the specified deck.

    If deck_id is provided, it will be used directly. Otherwise,
    the deck_name will be used to find the deck. A new deck cannot be created
    by this function.
    """
    dm = mw.col.decks
    if deck_id is None and deck_name is not None:
        deck_id = dm.id_for_name(deck_name)
        if not deck_id:
            if logger:
                logger.error(f"Deck '{deck_name}' not found. Cannot move card.")
            return
    elif deck_id is None:
        if logger:
            logger.error("Deck ID and name not provided. Cannot move card.")
        return

    # If odid is set, it means the card is in a filtered deck, we change the odid
    if card.odid != 0:
        card.odid = deck_id
    else:
        card.did = deck_id

    # undo action needs to be managed by the caller
