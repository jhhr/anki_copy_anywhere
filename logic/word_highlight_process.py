from anki.notes import Note

from .jp_text_processing.word.word_highlight import (
    word_highlight,
)

from ..utils.logger import Logger


def word_highlight_process(
    text: str,
    word_field: str,
    note: Note,
    logger: Logger = Logger("error"),
) -> str:
    """
    Wraps the word_highlight function to be used as an extra processing step in the copy fields
    chain.
    """

    # Get the word to highlight
    word_to_highlight = None
    if word_field:
        for name, field_text in note.items():
            if name == word_field:
                word_to_highlight = field_text
                if word_to_highlight:
                    break
        if not word_to_highlight:
            logger.error(f"Error in word_highlight: word_field '{word_field}' not found in note.")
    logger.debug(f"word_to_highlight: {word_to_highlight}, text: {text}")
    result = word_highlight(text, word_to_highlight, logger)
    logger.debug(f"word_highlight result: {result}")
    return result
