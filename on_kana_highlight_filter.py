import re
from operator import itemgetter

from anki.template import TemplateRenderContext
from aqt.utils import tooltip

from .kana_conv import is_kana_char, to_katakana, to_hiragana
from .utils import parse_filter_args

FURIGANA_RE = re.compile(r" ?([^ >]+?)\[(.+?)\]")

HIRAGANA_CONVERSION_DICT = {
    "か": ["が"],
    "き": ["ぎ"],
    "く": ["ぐ"],
    "け": ["げ"],
    "こ": ["ご"],
    "さ": ["ざ"],
    "し": ["じ"],
    "す": ["ず"],
    "せ": ["ぜ"],
    "そ": ["ぞ"],
    "た": ["だ"],
    "ち": ["ぢ"],
    "つ": ["づ"],
    "て": ["で"],
    "と": ["ど"],
    "は": ["ば", "ぱ"],
    "ひ": ["び", "ぴ"],
    "ふ": ["ぶ", "ぷ"],
    "へ": ["べ", "ぺ"],
    "ほ": ["ぼ", "ぽ"],
}
# Convert HIRAGANA_CONVERSION_DICT to katakana with to_katakana
KATAKANA_CONVERSION_DICT = {
    to_katakana(k): [to_katakana(v) for v in vs] if isinstance(vs, list) else to_katakana(vs)
    for k, vs in HIRAGANA_CONVERSION_DICT.items()
}

SMALL_TSU_POSSIBLE_KATAKANA = [to_katakana(k) for k in [
    "ぱ", "ぴ", "ぷ", "ぺ", "ぽ", "こ", "か", "く", "き"
]]


def kana_filter(text):
    def replace_func(match):
        if match.group(2).startswith("sound:"):
            return match.group(0)
        else:
            return match.group(2)

    return FURIGANA_RE.sub(replace_func, text.replace("&nbsp;", " "))


VALID_ARGS = ["onyomi_field_name", "kunyomi_field_name", "kanji_field_name"]


def on_kana_highlight_filter(
        text: str, field_name: str, filter: str, context: TemplateRenderContext
) -> str:
    """
     The filter syntax is like this:
     {{kana_highlight[
        onyomi_field_name='onyomi_field_name';
        kunyomi_field_name='kunyomi_field_name';
        kanji_field_name='kanji_field_name';
     ]:Field}}
        where kanji_to_highlight is the kanji that will be highlighted in the text
        gotten from Field.
        Assuming that the text contains furigana, the furigana to be highlighted
        will be the one that corresponds to the kanji_to_highlight.
        The kanji is then stripped from the text and the kana from the furigana is left.

        If anything goes wrong, returns the text with kanji removed but
        no kana highlighted.
    """
    if not (filter.startswith("kana_highlight[") and filter.endswith("]")):
        return text

    is_cache = None
    try:
        is_cache = context.extra_state["is_cache"]
    except KeyError:
        is_cache = False

    def show_error_message(message: str):
        if not is_cache:
            tooltip(message, period=10000)
        else:
            print(message)

    args_dict = parse_filter_args("kana_highlight", VALID_ARGS, filter, show_error_message)

    onyomi_field_name, kunyomi_field_name, kanji_field_name = itemgetter(
        "onyomi_field_name", "kunyomi_field_name", "kanji_field_name")(args_dict)

    if onyomi_field_name is None:
        show_error_message(f"Error in 'kana_highlight[]' field args: Missing 'onyomi_field_name'")
        return kana_filter(text)

    if kunyomi_field_name is None:
        show_error_message(f"Error in 'kana_highlight[]' field args: Missing 'kunyomi_field_name'")
        return kana_filter(text)

    if kanji_field_name is None:
        show_error_message(f"Error in 'kana_highlight[]' field args: Missing 'kanji_field_name'")
        return kana_filter(text)

    note = context.card().note()
    # Get field contents from the note
    kanji_to_highlight = None
    onyomi = None
    kunyomi = None
    for name, field_text in note.items():
        if name == kanji_field_name:
            kanji_to_highlight = field_text
        if name == onyomi_field_name:
            onyomi = field_text
        if name == kunyomi_field_name:
            kunyomi = field_text
        if kanji_to_highlight and onyomi and kunyomi:
            break
    if kanji_to_highlight is None or onyomi is None or kunyomi is None:
        show_error_message(
            f"Error in kana_highlight[]: note doesn't contain fields: Kanji ({kanji_to_highlight}), Onyomi ({onyomi}), Kunyomi ({kunyomi})")
        return kana_filter(text)

    # kanji_to_highlight = filter[13:-1]
    # Find the position of the kanji in the text
    kanji_pos = text.find(kanji_to_highlight)
    if kanji_pos == -1:
        show_error_message(f"Error in kana_highlight[]: Kanji ({kanji_to_highlight}) not found in text ({text})")
        return kana_filter(text)

    # Find the furigana that corresponds to the kanji
    # It will be the next brackets after the kanji where they may be 0 or more
    # other kanji in between but no hiragana or katakana
    # At the same time we'll construct the word that the kanji is part of
    furigana = ""
    word = f"{kanji_to_highlight}"
    is_kanji = True
    furigana_start_pos = -1
    furigana_end_pos = -1
    for i in range(kanji_pos + len(kanji_to_highlight), len(text)):
        if text[i] == "[":
            furigana = ""
            is_kanji = False
            furigana_start_pos = i + 1
        elif text[i] == "]":
            furigana_end_pos = i - 1
            break
        elif is_kanji:
            word += text[i]
        else:
            furigana += text[i]

    # Then go backward to find the other kanji to the left of the kanji_to_highlight
    for i in range(kanji_pos - 1, -1, -1):
        if is_kana_char(text[i]):
            break
        word = text[i] + word

    # Now the hard part
    # We need to find the kana that corresponds to the kanji within the furigana
    def process_readings(furigana):
        # We'll loop through all onyomi and kunyomi readings and find the one that has a match in the furigana
        # If we find a match, we'll highlight that part of the furigana
        for onyomi_reading in onyomi.split("、"):
            # remove text in () in the reading
            onyomi_reading = re.sub(r"\(.*?\)", "", onyomi_reading).strip()
            # Convert the onyomi to hiragana since the furigana is in hiragana
            onyomi_reading = to_hiragana(onyomi_reading)
            if onyomi_reading in furigana:
                return furigana.replace(onyomi_reading, f"<b>{onyomi_reading}</b>")
            # The reading might have a match with a changed kana like シ->ジ, フ->プ, etc.
            # This only applies to the first kana in the reading
            if onyomi_reading[0] in HIRAGANA_CONVERSION_DICT:
                if isinstance(HIRAGANA_CONVERSION_DICT[onyomi_reading[0]], list):
                    for kana in HIRAGANA_CONVERSION_DICT[onyomi_reading[0]]:
                        converted_onyomi = onyomi_reading.replace(onyomi_reading[0], kana, 1)
                        if converted_onyomi in furigana:
                            return furigana.replace(converted_onyomi, f"<b>{converted_onyomi}</b>")
        # Then also check for small tsu conversion of some consonants
        # this only happens in the last kana of the reading
        for kana in SMALL_TSU_POSSIBLE_KATAKANA:
            if onyomi[-1] == kana:
                converted_onyomi = onyomi[:-1] + "っ"
                if converted_onyomi in furigana:
                    return furigana.replace(converted_onyomi, f"<b>{converted_onyomi}</b>")
        # Then check the kunyomi readings
        for kunyomi_reading in kunyomi.split("、"):
            # Remove the okurigana in the reading which are split by a dot
            kunyomi_stem = re.sub(r"\..+", "", kunyomi_reading).strip()
            # For kunyomi we just check for a match with the stem
            if kunyomi_stem in furigana:
                return furigana.replace(kunyomi_stem, f"<b>{kunyomi_stem}</b>")
            # Also check for changed kana
            if kunyomi_stem[0] in HIRAGANA_CONVERSION_DICT:
                if isinstance(HIRAGANA_CONVERSION_DICT[kunyomi_stem[0]], list):
                    for kana in HIRAGANA_CONVERSION_DICT[kunyomi_stem[0]]:
                        converted_kunyomi = kunyomi_stem.replace(kunyomi_stem[0], kana, 1)
                        if converted_kunyomi in furigana:
                            return furigana.replace(converted_kunyomi, f"<b>{converted_kunyomi}</b>")

    new_furigana = process_readings(furigana)
    if new_furigana is None:
        show_error_message(
            f"Error in kana_highlight[]: No reading found for furigana ({furigana}) among onyomi ({onyomi}) and kunyomi ({kunyomi})")
        return kana_filter(text)

    # Replace furigana in the text with the new furigana
    # using furigana_start_pos and furigana_end_pos
    text = text[:furigana_start_pos] + new_furigana + text[furigana_end_pos + 1:]

    # Finally strip all kanji from the text
    return kana_filter(text)
