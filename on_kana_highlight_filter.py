from operator import itemgetter

from anki.template import TemplateRenderContext

from .kana_highlight import kana_highlight, kana_filter
from .utils import filter_init

VALID_ARGS = ["onyomi_field", "kunyomi_field", "kanji_field"]


def on_kana_highlight_filter(
        text: str, field_name: str, filter_str: str, context: TemplateRenderContext
) -> str:
    """
     The filter syntax is like this:
     {{kana_highlight[
        onyomi_field='onyomi_field';
        kunyomi_field='kunyomi_field';
        kanji_field='kanji_field';
     ]:Field}}
        where kanji_to_highlight is the kanji that will be highlighted in the text
        gotten from Field.
        Assuming that the text contains furigana, the furigana to be highlighted
        will be the one that corresponds to the kanji_to_highlight.
        The kanji is then stripped from the text and the kana from the furigana is left.

        If anything goes wrong, returns the text with kanji removed but
        no kana highlighted.
    """
    if not (filter_str.startswith("kana_highlight[") and filter_str.endswith("]")):
        return text

    args_dict, is_cache, show_error_message = filter_init("kana_highlight", VALID_ARGS, filter_str, context)

    onyomi_field, kunyomi_field, kanji_field = itemgetter(
        "onyomi_field", "kunyomi_field", "kanji_field")(args_dict)

    if onyomi_field is None:
        show_error_message(f"Error in 'kana_highlight[]' field args: Missing 'onyomi_field'")
        return kana_filter(text)

    if kunyomi_field is None:
        show_error_message(f"Error in 'kana_highlight[]' field args: Missing 'kunyomi_field'")
        return kana_filter(text)

    if kanji_field is None:
        show_error_message(f"Error in 'kana_highlight[]' field args: Missing 'kanji_field'")
        return kana_filter(text)

    note = context.card().note()
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
            f"Error in kana_highlight[]: note doesn't contain fields: Kanji ({kanji_to_highlight}), Onyomi ({onyomi}), Kunyomi ({kunyomi})")
        return kana_filter(text)

    return kana_highlight(kanji_to_highlight, onyomi, kunyomi, text)
