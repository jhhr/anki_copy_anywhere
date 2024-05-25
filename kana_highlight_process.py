from typing import Callable

from anki.notes import Note

from .kana_highlight import kana_highlight, kana_filter

# Name to use for detecting the process in the
# and also the GUI
KANA_HIGHLIGHT_PROCESS_NAME = "Kana Highlight"


def kana_highlight_process(
        text: str,
        onyomi_field: str,
        kunyomi_field: str,
        kanji_field: str,
        is_cache: bool,
        note: Note,
        show_error_message: Callable[[str], None] = None
) -> str:
    """
     Wraps the kana_highlight function to be used as an extra processing step in the copy fields
     chain.
    """
    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    # show_error_message(f"kana_highlight_process: {onyomi_field}, {kunyomi_field}, {kanji_field}, {text}")
            
    if onyomi_field is None:
        show_error_message(f"Error in kana_highlight: Missing 'onyomi_field'")
        return kana_filter(text)

    if kunyomi_field is None:
        show_error_message(f"Error in kana_highlight: Missing 'kunyomi_field'")
        return kana_filter(text)

    if kanji_field is None:
        show_error_message(f"Error in kana_highlight: Missing 'kanji_field'")
        return kana_filter(text)

    # Get field contents from the note
    kanji_to_highlight = None
    onyomi = None
    kunyomi = None
    for name, field_text in note.items():
        if name == kanji_field:
            kanji_to_highlight = field_text
        if name == onyomi_field:
            onyomi = field_text
        if name == kunyomi_field:
            kunyomi = field_text
        if kanji_to_highlight and onyomi and kunyomi:
            break
    if kanji_to_highlight is None or onyomi is None or kunyomi is None:
        show_error_message(
            f"Error in kana_highlight: note doesn't contain fields: Kanji ({kanji_to_highlight}), Onyomi ({onyomi}), Kunyomi ({kunyomi})")
        return kana_filter(text)

    return kana_highlight(kanji_to_highlight, onyomi, kunyomi, text)
