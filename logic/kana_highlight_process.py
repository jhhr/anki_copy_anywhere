from typing import Callable, Union

from anki.notes import Note

from .kana_highlight import kana_highlight, kana_filter, furigana_reverser, FuriReconstruct


def kana_highlight_process(
        text: str,
        onyomi_field: str,
        kunyomi_field: str,
        kanji_field: str,
        return_type: Union[FuriReconstruct, None],
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

    # show_error_message(f"kana_highlight_process: {onyomi_field}, {kunyomi_field}, {kanji_field}, {text}, {return_type}")
            
    if onyomi_field is None:
        show_error_message("Error in kana_highlight: Missing 'onyomi_field'")
        return kana_filter(text)

    if kunyomi_field is None:
        show_error_message("Error in kana_highlight: Missing 'kunyomi_field'")
        return kana_filter(text)

    if kanji_field is None:
        show_error_message("Error in kana_highlight: Missing 'kanji_field'")
        return kana_filter(text)
    if return_type is None:
        show_error_message("Error in kana_highlight: Missing 'return_type'")
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
        if return_type == "kana_only":
            return kana_filter(text)
        if return_type == "furikanji":
            return furigana_reverser(text)
        else:
            return text

    return kana_highlight(kanji_to_highlight, onyomi, kunyomi, text, return_type, show_error_message)
