from typing import Union
from aqt import mw
from anki.cards import Card

from .logger import Logger


def move_card_to_deck(
    card: Card,
    deck: Union[int, str],
    logger: Logger = None,
) -> None:
    """Move the given card to the specified deck.

    If deck is an integer, it will be used as the deck ID directly. If deck is a string, it will be used as the deck name to find the deck ID. A new deck cannot be created by this function.
    """
    dm = mw.col.decks
    deck_name = None
    deck_id = None
    if isinstance(deck, int):
        deck_id = deck
    elif isinstance(deck, str):
        deck_name = deck
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

    # will not call mw.col.update_card(card) here.
    # Instead the caller should do that in the most appropriate point to manage performance
    # and undo entries.
