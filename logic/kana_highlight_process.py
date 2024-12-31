from typing import Optional, Callable

from anki.notes import Note

from .kana_highlight import (
    furigana_reverser,
    FuriReconstruct,
    WithTagsDef,
    kana_filter,
    kana_highlight,
)


def kana_highlight_process(
    text: str,
    kanji_field: str,
    return_type: FuriReconstruct,
    note: Note,
    with_tags_def: Optional[WithTagsDef] = None,
    show_error_message: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Wraps the kana_highlight function to be used as an extra processing step in the copy fields
    chain.
    """
    if not show_error_message:

        def show_error_message(message: str):
            print(message)

    # show_error_message(
    #     f"kana_highlight_process: {onyomi_field}, {kunyomi_field}, {kanji_field}, {text},"
    #     f" {return_type}"
    # )

    if not kanji_field:
        show_error_message("Error in kana_highlight: Missing 'kanji_field'")
        return kana_filter(text)
    if not return_type:
        show_error_message("Error in kana_highlight: Missing 'return_type'")
        return kana_filter(text)

    # Get the kanji to highlight and initial kanji data
    kanji_to_highlight = None
    for name, field_text in note.items():
        if name == kanji_field:
            kanji_to_highlight = field_text
            if kanji_to_highlight:
                break

    if kanji_to_highlight is None:
        if return_type == "kana_only":
            return kana_filter(text)
        if return_type == "furikanji":
            return furigana_reverser(text)
        else:
            return text

    return kana_highlight(kanji_to_highlight, text, return_type, with_tags_def, show_error_message)
