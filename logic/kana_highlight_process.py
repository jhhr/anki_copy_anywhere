from typing import Optional

from anki.notes import Note

from .kana_highlight import (
    kana_filter,
    kana_highlight,
)
from ..utils.logger import Logger

from .jpn_text_processing.types import WithTagsDef
from .jpn_text_processing.construct_wrapped_furi_word import FuriReconstruct


def kana_highlight_process(
    text: str,
    kanji_field: str,
    return_type: FuriReconstruct,
    note: Note,
    with_tags_def: Optional[WithTagsDef] = None,
    logger: Logger = Logger("error"),
) -> str:
    """
    Wraps the kana_highlight function to be used as an extra processing step in the copy fields
    chain.
    """
    if not return_type:
        logger.error("Error in kana_highlight: Missing 'return_type'")
        return kana_filter(text)

    # Get the kanji to highlight and initial kanji data
    kanji_to_highlight = None
    if kanji_field:
        for name, field_text in note.items():
            if name == kanji_field:
                kanji_to_highlight = field_text
                if kanji_to_highlight:
                    break
        if not kanji_to_highlight:
            logger.error(f"Error in kana_highlight: kanji_field '{kanji_field}' not found in note.")
    logger.debug(
        f"kanji_to_highlight: {kanji_to_highlight}, text: {text}, return_type: {return_type},"
        f" with_tags_def: {with_tags_def}"
    )
    return kana_highlight(kanji_to_highlight, text, return_type, with_tags_def, logger)
