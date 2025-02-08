from functools import partial
import re
import sys
import json
import os
from typing import Callable, TypedDict, Literal, Optional, Tuple, NamedTuple, cast, Union

from .jpn_text_processing.kana_conv import to_katakana, to_hiragana
from .jpn_text_processing.get_conjugatable_okurigana_stem import (
    get_conjugatable_okurigana_stem,
)
from .jpn_text_processing.starts_with_okurigana_conjugation import (
    starts_with_okurigana_conjugation,
    OkuriResults,
)
from .jpn_text_processing.construct_wrapped_furi_word import (
    construct_wrapped_furi_word,
    FuriReconstruct,
)
from .jpn_text_processing.okurigana_dict import get_verb_noun_form_okuri


class KanjiData(TypedDict):
    onyomi: str
    kunyomi: str


# import all_kanji_data from the json file in .jpn_text_processing/all_kanji_data.json

current_dir = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.join(current_dir, "jpn_text_processing", "all_kanji_data.json")

all_kanji_data: dict[str, KanjiData] = {}
with open(json_file_path, "r", encoding="utf-8") as f:
    all_kanji_data = json.load(f)

RENDAKU_CONVERSION_DICT = {
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
    to_katakana(k): [to_katakana(v) for v in vs] for k, vs in RENDAKU_CONVERSION_DICT.items()
}

SMALL_TSU_POSSIBLE_HIRAGANA = ["つ", "ち", "く", "き", "り", "ん"]

HIRAGANA_RE = "([ぁ-ん])"

ALL_MORA = [
    # First the two kana mora, so that they are matched first
    "くぃ",
    "きゃ",
    "きゅ",
    "きぇ",
    "きょ",
    "ぐぃ",
    "ご",
    "ぎゃ",
    "ぎゅ",
    "ぎぇ",
    "ぎょ",
    "すぃ",
    "しゃ",
    "しゅ",
    "しぇ",
    "しょ",
    "ずぃ",
    "じゃ",
    "じゅ",
    "じぇ",
    "じょ",
    "てぃ",
    "とぅ",
    "ちゃ",
    "ちゅ",
    "ちぇ",
    "ちょ",
    "でぃ",
    "どぅ",
    "ぢゃ",
    "でゅ",
    "ぢゅ",
    "ぢぇ",
    "ぢょ",
    "つぁ",
    "つぃ",
    "つぇ",
    "つぉ",
    "づぁ",
    "づぃ",
    "づぇ",
    "づぉ",
    "ひぃ",
    "ほぅ",
    "ひゃ",
    "ひゅ",
    "ひぇ",
    "ひょ",
    "びぃ",
    "ぼ",
    "びゃ",
    "びゅ",
    "びぇ",
    "びょ",
    "ぴぃ",
    "ぴゃ",
    "ぴゅ",
    "ぴぇ",
    "ぴょ",
    "ふぁ",
    "ふぃ",
    "ふぇ",
    "ふぉ",
    "ゔぁ",
    "ゔぃ",
    "ゔ",
    "ゔぇ",
    "ゔぉ",
    "ぬぃ",
    "の",
    "にゃ",
    "にゅ",
    "にぇ",
    "にょ",
    "むぃ",
    "みゃ",
    "みゅ",
    "みぇ",
    "みょ",
    "るぃ",
    "りゃ",
    "りゅ",
    "りぇ",
    "りょ",
    "いぇ",
    # Then single kana mora
    "か",
    "く",
    "け",
    "こ",
    "き",
    "が",
    "ぐ",
    "げ",
    "ご",
    "ぎ",
    "さ",
    "す",
    "せ",
    "そ",
    "し",
    "ざ",
    "ず",
    "づ",
    "ぜ",
    "ぞ",
    "じ",
    "ぢ",
    "た",
    "とぅ",
    "て",
    "と",
    "ち",
    "だ",
    "で",
    "ど",
    "ぢ",
    "つ",
    "づ",
    "は",
    "へ",
    "ほ",
    "ひ",
    "ば",
    "ぶ",
    "べ",
    "ぼ",
    "ぼ",
    "び",
    "ぱ",
    "ぷ",
    "べ",
    "ぽ",
    "ぴ",
    "ふ",
    "ゔぃ",
    "ゔ",
    "な",
    "ぬ",
    "ね",
    "の",
    "に",
    "ま",
    "む",
    "め",
    "も",
    "み",
    "ら",
    "る",
    "れ",
    "ろ",
    "り",
    "あ",
    "い",
    "う",
    "え",
    "お",
    "や",
    "ゆ",
    "よ",
    "わ",
    "ゐ",
    "ゑ",
    "を",
]

# Add the small tsu versions of all mora to be matched first
ALL_MORA_RE = "|".join([m + "っ" for m in ALL_MORA] + ALL_MORA)
ALL_MORA_REC = re.compile(rf"({ALL_MORA_RE})")

VOWEL_CHANGE_DICT = {
    "お": ["よ", "ょ"],
    "あ": ["や", "ゃ"],
    "う": ["ゆ", "ゅ"],
}

# Regex matching any kanji characters
# Include the kanji repeater punctuation as something that will be cleaned off
# Also include numbers as they are sometimes used in furigana
KANJI_RE = r"([\d々\u4e00-\u9faf\u3400-\u4dbf]+)"
KANJI_REC = re.compile(KANJI_RE)
# Same as above but allows for being empty
KANJI_RE_OPT = r"([\d々\u4e00-\u9faf\u3400-\u4dbf]*)"

# Regex matching any furigana
FURIGANA_RE = r" ?([^ >]+?)\[(.+?)\]"
FURIGANA_REC = re.compile(FURIGANA_RE)

# Regex matching any kanji and furigana + hiragana after the furigana
KANJI_AND_FURIGANA_AND_OKURIGANA_RE = r"([\d々\u4e00-\u9faf\u3400-\u4dbf]+)\[(.+?)\]([ぁ-ん]*)"
KANJI_AND_FURIGANA_AND_OKURIGANA_REC = re.compile(KANJI_AND_FURIGANA_AND_OKURIGANA_RE)

NUMBER_TO_KANJI = {
    # normal number characters
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九",
    # jpn number characters
    "１": "一",
    "２": "二",
    "３": "三",
    "４": "四",
    "５": "五",
    "６": "六",
    "７": "七",
    "８": "八",
    "９": "九",
}

# Exceptions for words where the first kanji has a kunyomi reading that is the same as the
# the whole reading for the jukujikun compound. This is used to avoid matching the kunyomi
# reading for the first kanji as a separate word.
JUKUJIKUN_KUNYOMI_OVERLAP: dict[str, str] = {
    "風邪": "かぜ",
    "薔薇": "ばら",
    "真面": "まじ",
    "蕎麦": "そば",
}

# Regex for lone kanji with some hiragana to their right, then some kanji,
# then furigana that includes the hiragana in the middle
# This is used to match cases of furigana used for　kunyomi compound words with
# okurigana in the middle. For example
# (1) 消え去[きえさ]る
# (2) 隣り合わせ[となりあわせ]
# (3) 歯止め[はどめ]
OKURIGANA_MIX_CLEANING_RE = re.compile(
    rf"""
{KANJI_RE}  # match group 1, kanji                          (1)消　(2)隣 (3)歯止
([ぁ-ん]+)   # match group 2, hiragana                       (1)え　(2)り (3)め
{KANJI_RE_OPT}  # match group 3, potential kanji            (1)去　(2)合　(3)nothing
([ぁ-ん]*)   # match group 4, potential hiragana             (1)nothing　(2)わせ (3)nothing
\[          # opening bracket of furigana
(.+?)       # match group 5, furigana for kanji in group 1  (1)きえ　(2)となり (3)はど
\2          # group 2 occuring again                        (1)え　(2)り (3)め
(.*?)       # match group 6, furigana for kanji in group 3  (1)さ　(2)あわせ　(3)nothing
\4          # group 4 occuring again (if present)           (1)nothing　(2)わせ (3)nothing
]          # closing bracket of furigana
""",
    re.VERBOSE,
)


def okurigana_mix_cleaning_replacer(match):
    """
    re.sub replacer function for OKURIGANA_MIX_CLEANING_RE when it's only needed to
    clean the kanji and leave the furigana. The objective is to turn the hard to process
    case into a normal case. For example:
    (1) 消え去る[きえさ]る becomes 消[き]え去[さ]る
    (2) 隣り合わせ[となりあわせ] becomes 隣[とな]り合[あ]わせ
    (3) 歯止め[はどめ] becomes 歯[は]止[ど]め
    """
    kanji1 = match.group(1)  # first kanji
    furigana1 = match.group(5)  # furigana for first kanji
    hiragana1 = match.group(2)  # hiragana in the middle, after the first kanji
    kanji2 = match.group(3)  # second kanji
    furigana2 = match.group(6)  # furigana for second kanji
    hiragana2 = match.group(4)  # potential hiragana at the end, after the second kanji

    # Return the cleaned and restructured string
    result = f"{kanji1}[{furigana1}]{hiragana1}"
    if furigana2:
        result += f"{kanji2}[{furigana2}]{hiragana2}"
    return result


def re_match_from_right(text):
    return re.compile(rf"(.*)({text})(.*?)$")


def re_match_from_left(text):
    return re.compile(rf"^(.*?)({text})(.*)$")


def re_match_from_middle(text):
    return re.compile(rf"^(.*?)({text})(.*?)$")


def onyomi_replacer(match, wrap_readings_with_tags=True):
    """
    re.sub replacer function for onyomi used with the above regexes§
    """
    onyomi_kana = to_katakana(match.group(2))
    if wrap_readings_with_tags:
        onyomi_kana = f"<on>{onyomi_kana}</on>"
    return f"{match.group(1)}<b>{onyomi_kana}</b>{match.group(3)}"


def kunyomi_replacer(match, wrap_readings_with_tags=True):
    """
    re.sub replacer function for kunyomi used with the above regexes
    """
    kunyomi_kana = match.group(2)
    if wrap_readings_with_tags:
        kunyomi_kana = f"<kun>{kunyomi_kana}</kun>"
    return f"{match.group(1)}<b>{kunyomi_kana}</b>{match.group(3)}"


def kana_filter(text):
    """
    Implementation of the basic Anki kana filter
    This is needed to clean up the text in cases where we know there's no matches to the kanji
    This works differently as it directly matches kanji characters instead of [^ >] as in the Anki
    built-in version. For whatever reason a python version using that doesn't work as expected.
    :param text: The text to clean
    :return: The cleaned text
    """

    def bracket_replace(match):
        if match.group(1).startswith("sound:"):
            # [sound:...] should not be replaced
            return match.group(0)
        # Return the furigana inside the brackets
        return match.group(1)

    # First remove all brackets and then remove all kanji
    # Assuming every kanji had furigana, we'll be left with the correct kana
    return KANJI_REC.sub("", FURIGANA_REC.sub(bracket_replace, text.replace("&nbsp;", " ")))


def furigana_reverser(text):
    """
    Reverse the position of kanji and furigana in the text.
    :param text: The text to process
    :return: The text with kanji and furigana reversed
    """

    def bracket_reverser(match):
        if match.group(1).startswith("sound:"):
            # [sound:...] should not be reversed, do nothing
            return match.group(0)
        kanji = match.group(1)
        furigana = match.group(2)
        return f"{furigana}[{kanji}]"

    return re.sub(FURIGANA_RE, bracket_reverser, text.replace("&nbsp;", " "))


class WithTagsDef(NamedTuple):
    """
    NamedTuple for the definition of the tags to wrap the furigana in
    :param with_tags
    :param merge_consecutive
    :param assume_dictionary_form
    """

    with_tags: bool
    merge_consecutive: bool
    assume_dictionary_form: bool


Edge = Literal["left", "right", "middle", "whole", "none"]


class WordData(TypedDict):
    """
    TypedDict for data about a single word that was matched in the text for the kanji_to_match
    :param kanji_pos
    :param kanji_count
    :param word
    :param furigana
    :param okurigana
    :param edge
    """

    kanji_pos: int
    kanji_count: int
    word: str
    furigana: str
    okurigana: str
    edge: Edge


class HighlightArgs(TypedDict):
    """
    TypedDict for the base arguments passed to kana_highlight as these get passed around a lot
    :param text
    :param onyomi
    :param kunyomi
    :param kanji_to_match
    :param kanji_to_highlight
    :param add_highlight
    :param edge
    """

    onyomi: str
    kunyomi: str
    kanji_to_match: str
    kanji_to_highlight: str
    add_highlight: bool
    edge: Edge


MatchType = Literal["onyomi", "kunyomi", "jukujikun", "none"]


class YomiMatchResult(TypedDict):
    """
    TypedDict for the result of the onyomi or kunyomi match check
    :param text
    :param type
    :param match_edge
    :param actual_match
    :param matched_reading
    """

    text: str
    type: MatchType
    match_edge: Edge
    actual_match: str
    matched_reading: str


class PartialResult(TypedDict):
    """
    TypedDict for the partial result of the onyomi or kunyomi match check
    :param matched_furigana
    :param match_type
    :param rest_furigana
    :param okurigana
    :param rest_kana
    :param edge
    """

    matched_furigana: str
    match_type: MatchType
    rest_furigana: str
    okurigana: str
    rest_kana: str
    edge: Edge


class FinalResult(TypedDict):
    """
    TypedDict for the final result of the onyomi or kunyomi match check
    :param furigana
    :param okurigana
    :param rest_kana
    :param left_word
    :param middle_word
    :param right_word
    :param edge
    """

    furigana: str
    okurigana: str
    rest_kana: str
    left_word: str
    middle_word: str
    right_word: str
    edge: Edge


REPLACED_FURIGANA_MIDDLE_RE = re.compile(r"^(.+)<b>(.+)</b>(.+)$")
REPLACED_FURIGANA_RIGHT_RE = re.compile(r"^(.+)<b>(.+)</b>$")
REPLACED_FURIGANA_LEFT_RE = re.compile(r"^<b>(.+)</b>(.+)$")


class FuriganaParts(TypedDict):
    """
    TypedDict for the parts of the furigana that were matched
    :param has_highlight
    :param left_furigana
    :param middle_furigana
    :param right_furigana
    :param matched_edge
    """

    has_highlight: bool
    left_furigana: Optional[str]
    middle_furigana: Optional[str]
    right_furigana: Optional[str]
    matched_edge: Edge


def get_furigana_parts(
    furigana: str,
    edge: Edge,
) -> FuriganaParts:
    log(f"\nget_furigana_parts - furigana: {furigana}, edge: {edge}")
    result: FuriganaParts = {
        "has_highlight": "<b>" in furigana,
        "left_furigana": None,
        "middle_furigana": None,
        "right_furigana": None,
        "matched_edge": edge,
    }
    if edge == "whole":
        return result
    if match := REPLACED_FURIGANA_MIDDLE_RE.match(furigana):
        log(
            f"\nget_furigana_parts - middle match: {match.groups()}, edge was correct:"
            f" {edge == 'middle'}"
        )
        result["left_furigana"] = match.group(1)
        result["middle_furigana"] = match.group(2)
        result["right_furigana"] = match.group(3)
        result["matched_edge"] = "middle"
        return result
    elif match := REPLACED_FURIGANA_RIGHT_RE.match(furigana):
        log(
            f"\nget_furigana_parts - right match: {match.groups()}, edge was correct:"
            f" {edge == 'right'}"
        )
        result["left_furigana"] = match.group(1)
        result["middle_furigana"] = None
        result["right_furigana"] = match.group(2)
        result["matched_edge"] = "right"
        return result
    elif match := REPLACED_FURIGANA_LEFT_RE.match(furigana):
        log(
            f"\nget_furigana_parts - left match: {match.groups()}, edge was correct:"
            f" {edge == 'left'}"
        )
        result["left_furigana"] = match.group(1)
        result["middle_furigana"] = None
        result["right_furigana"] = match.group(2)
        result["matched_edge"] = "left"
        return result

    # Nothing matched
    log("\nget_furigana_parts - no match")
    return result


def reconstruct_furigana(
    furi_okuri_result: FinalResult,
    with_tags_def: WithTagsDef,
    reconstruct_type: FuriReconstruct = "furigana",
) -> str:
    """
    Reconstruct the furigana from the replace result

    :return: The reconstructed furigana with the kanji and that kanji's furigana highlighted
    """
    log(
        f"\nreconstruct_furigana - final_result: {furi_okuri_result}, reconstruct_type:"
        f" {reconstruct_type}, wrap_with_tags: {with_tags_def.with_tags}, merge_consecutive:"
        f" {with_tags_def.merge_consecutive}"
    )
    furigana = furi_okuri_result.get("furigana", "")
    okurigana = furi_okuri_result.get("okurigana", "")
    rest_kana = furi_okuri_result.get("rest_kana", "")
    left_word = furi_okuri_result.get("left_word", "")
    middle_word = furi_okuri_result.get("middle_word", "")
    right_word = furi_okuri_result.get("right_word", "")
    edge = furi_okuri_result.get("edge")
    if not edge:
        raise ValueError("reconstruct_furigana: edge missing in final_result")

    furigana_parts = get_furigana_parts(furigana, edge)
    log(f"\nreconstruct_furigana edge: {edge}, furigana_parts: {furigana_parts}")

    has_highlight = furigana_parts.get("has_highlight")
    left_furigana = furigana_parts.get("left_furigana")
    middle_furigana = furigana_parts.get("middle_furigana")
    right_furigana = furigana_parts.get("right_furigana")
    edge = furigana_parts.get("matched_edge")

    if not has_highlight:
        log("\nreconstruct_furigana - no highlight")
        # There was no match found during onyomi and kunyomi processing, so no <b> tags
        # we can just construct the furigana without splitting it
        if reconstruct_type == "kana_only" and not with_tags_def.merge_consecutive:
            # kana are already wrapped, if they are, and were not merging so
            # construct_wrapped_furi_word is not needed
            if with_tags_def.with_tags:
                okurigana = f"<oku>{okurigana}</oku>" if okurigana else ""
            return f"{furigana}{okurigana}{rest_kana}"
        if with_tags_def.with_tags:
            # we need to extract the wrap tags from the furigana and include the word and
            # furigana within them. All words will need to be split into separate furigana
            # sections
            if edge == "whole":
                whole_word = f"{left_word}{middle_word}{right_word}"
                wrapped_whole_word = construct_wrapped_furi_word(
                    whole_word, furigana, reconstruct_type, with_tags_def.merge_consecutive
                )
            else:
                wrapped_whole_word = ""
                for word, word_furigana in [
                    (left_word, left_furigana),
                    (middle_word, middle_furigana),
                    (right_word, right_furigana),
                ]:
                    if word and word_furigana:
                        wrapped_word = construct_wrapped_furi_word(
                            word, word_furigana, reconstruct_type, with_tags_def.merge_consecutive
                        )
                        wrapped_whole_word += wrapped_word

            log(
                f"\nreconstruct_furigana - whole_word: {right_word}{middle_word}{left_word},"
                f" furigana: {furigana}, wrapped_whole_word: {wrapped_whole_word}"
            )
            okurigana = f"<oku>{okurigana}</oku>" if okurigana else ""
            return f"{wrapped_whole_word}{okurigana}{rest_kana}"
        if reconstruct_type == "furikanji":
            return f" {furigana}[{left_word}{middle_word}{right_word}]{okurigana}{rest_kana}"
        return f" {left_word}{middle_word}{right_word}[{furigana}]{okurigana}{rest_kana}"

    if edge == "whole":
        # Same as above except we add the <b> tags around the whole thing
        # First remove <b> tags from the furigana
        furigana = re.sub(r"<b>|</b>", "", furigana)
        whole_word = f"{left_word}{middle_word}{right_word}"
        if with_tags_def.with_tags:
            wrapped_word = construct_wrapped_furi_word(
                whole_word, furigana, reconstruct_type, with_tags_def.merge_consecutive
            )
            okurigana = f"<oku>{okurigana}</oku>" if okurigana else ""
            return f"<b>{wrapped_word}{okurigana}</b>{rest_kana}"
        if reconstruct_type == "kana_only":
            return f"<b>{furigana}{okurigana}</b>{rest_kana}"
        if reconstruct_type == "furikanji":
            return f"<b> {furigana}[{whole_word}]{okurigana}</b>{rest_kana}"
        return f"<b> {whole_word}[{furigana}]{okurigana}</b>{rest_kana}"

    # There is highlighting, split the furigana and word into three parts and assemble them
    result = ""
    parts = [
        # The furigana and word parts should match exactly;
        # when one is missing so is the other
        (left_word, left_furigana, "left"),
        (middle_word, middle_furigana, "middle"),
        (right_word, right_furigana, "right"),
    ]
    for word, word_furigana, word_edge in parts:
        log(
            f"\nreconstruct_furigana - word: {word}, word_furigana: {word_furigana},"
            f" word_edge: {word_edge}"
        )
        if word and word_furigana:
            if with_tags_def.with_tags:
                part = construct_wrapped_furi_word(
                    word, word_furigana, reconstruct_type, with_tags_def.merge_consecutive
                )
            elif reconstruct_type == "kana_only":
                part = f"{word_furigana}"
            elif reconstruct_type == "furikanji":
                part = f" {word_furigana}[{word}]"
            else:
                part = f" {word}[{word_furigana}]"
            # If this is the edge that was matched, add the bold tags while
            # removing the existing ones in the furigana
            part = re.sub(r"<b>|</b>", "", part)
            if word_edge == "right":
                # If we're at the end, add the okurigana
                if with_tags_def.with_tags:
                    part += f"<oku>{okurigana}</oku>" if okurigana else ""
                else:
                    part += okurigana
            if edge == word_edge:
                # Finally, add the highlighting if this is the edge that was matched
                part = f"<b>{part}</b>"
            result += part
    return f"{result}{rest_kana}"


LOG = False


def log(*args):
    if LOG:
        print(*args)


MatchProcess = Literal["replace", "match", "juku"]


class ReadingProcessResult(NamedTuple):
    """
    NamedTuple for the result of the reading processing
    """

    yomi_match: YomiMatchResult
    okurigana: str
    rest_kana: str


def process_readings(
    highlight_args: HighlightArgs,
    word_data: WordData,
    process_type: MatchProcess,
    with_tags_def: WithTagsDef,
    show_error_message: Callable = print,
) -> Union[ReadingProcessResult, None]:
    """
    Function that processes furigana by checking all possible onyomi and kunyomi readings on it
    Either returns the furigana as-is when there is no match or modifies the furigana by
    adding <b> tags around the part that matches the reading

    :return: string, the modified furigana
        or (True, False) / (False, True) if return_on_or_kun_match_only
    """
    furigana = word_data.get("furigana", "")
    maybe_okuri = word_data.get("okurigana", "")
    edge = word_data.get("edge")
    assert edge is not None, "process_readings[]: edge missing in word_data"
    target_furigana_section = get_target_furigana_section(
        furigana,
        word_data.get("edge"),
        show_error_message,
    )
    # Check both onyomi and kunyomi readings and use the longest match we get
    onyomi_match = check_onyomi_readings(
        highlight_args.get("onyomi", ""),
        furigana,
        word_data.get("okurigana", ""),
        target_furigana_section,
        edge,
        process_type=process_type,
        wrap_readings_with_tags=with_tags_def.with_tags,
    )
    onyomi_process_result = None
    if onyomi_match["type"] == "onyomi":
        onyomi_process_result = ReadingProcessResult(onyomi_match, "", maybe_okuri)

    kunyomi_results = check_kunyomi_readings(
        highlight_args,
        word_data,
        furigana,
        target_furigana_section,
        edge,
        process_type=process_type,
        wrap_readings_with_tags=with_tags_def.with_tags,
    )
    kunyomi_process_result = None
    log(
        f"\nkunyomi_results: {kunyomi_results}, word_data: {word_data}, kana_highlight:"
        f" {highlight_args}"
    )
    if (
        not with_tags_def.assume_dictionary_form
        and kunyomi_results["type"] == "kunyomi"
        and word_data["edge"] in ["right", "whole"]
    ):
        kunyomi = highlight_args.get("kunyomi", "")
        okurigana_to_highlight = ""
        partial_okuri_results: list[OkuriResults] = []
        rest_kana = maybe_okuri
        kunyomi_readings = iter(kunyomi.split("、"))
        matched_kunyomi_stem = kunyomi_results["matched_reading"].split(".")[0]
        log(f"\ncheck_kunyomi_readings - matched_kunyomi_stem: {matched_kunyomi_stem}")
        while not okurigana_to_highlight and (next_kunyomi := next(kunyomi_readings, None)):
            log(
                f"\ncheck_kunyomi_readings - okurigana: {not okurigana_to_highlight},"
                f" next_kunyomi: {next_kunyomi}"
            )
            try:
                log(f"\ncheck_kunyomi_readings while - next_kunyomi: {next_kunyomi}")
                kunyomi_reading, kunyomi_okurigana = next_kunyomi.split(".")
            except ValueError:
                continue
            # The reading stems must match
            if kunyomi_reading != matched_kunyomi_stem:
                log(f"\ncheck_kunyomi_readings while - non-matching stem: {kunyomi_reading}")
                continue
            res = check_okurigana_for_kunyomi_inflection(
                kunyomi_okurigana, kunyomi_reading, word_data, highlight_args
            )
            if res.result in ["partial_okuri", "empty_okuri"]:
                # If we only got a partial or empty okurigana match, continue looking
                # in case we get a full match instead
                partial_okuri_results.append(res)
                log(
                    "\ncheck_kunyomi_readings while got a partial result:"
                    f" {res.okurigana}, rest_kana: {res.okurigana}, type: {res.result}"
                )
                continue
            if res.result == "full_okuri":
                log(
                    f"\ncheck_kunyomi_readings while got a full_okuri: {res.okurigana},"
                    f" rest_kana: {res.rest_kana}"
                )
                okurigana_to_highlight = res.okurigana
                rest_kana = res.rest_kana
        # If multiple partial okuri results were found, use the one that matches the most
        if partial_okuri_results and not okurigana_to_highlight:
            log(f"\ncheck_kunyomi_readings while got {len(partial_okuri_results)} partial results")
            best_res = max(partial_okuri_results, key=lambda x: len(x.okurigana))
            log(
                f"\ncheck_kunyomi_readings while final partial_okuri: {best_res.okurigana},"
                f" rest_kana: {best_res.rest_kana}, type: {best_res.result}"
            )
            okurigana_to_highlight = best_res.okurigana
            rest_kana = best_res.rest_kana
        log(
            "\ncheck_kunyomi_readings while result - okurigana:"
            f" {okurigana_to_highlight}, rest_kana: {rest_kana}"
        )
        kunyomi_process_result = ReadingProcessResult(
            kunyomi_results, okurigana_to_highlight, rest_kana
        )
    elif kunyomi_results["type"] == "kunyomi":
        if with_tags_def.assume_dictionary_form:
            # If we assume that this is a dictionary form word, we don't need to process
            # just return the okurigana as-is
            log("\nassuming dictionary form - kunyomi_process_result with okurigana")
            kunyomi_process_result = ReadingProcessResult(kunyomi_results, maybe_okuri, "")
        # Ohterwise, we can only assume its rest_kana
        else:
            log("\nnot assuming dictionary form - kunyomi_process_result with rest_kana")
            kunyomi_process_result = ReadingProcessResult(kunyomi_results, "", maybe_okuri)

    # Compare the onyomi and kunyomi results and return the one that matched the most
    if onyomi_process_result and kunyomi_process_result:
        on_length = len(onyomi_process_result.yomi_match["matched_reading"])
        kun_length = len(kunyomi_process_result.yomi_match["matched_reading"].split(".")[0])
        log(
            "\nfound both onyomi and kunyomi - on_match:"
            f" {onyomi_process_result.yomi_match['matched_reading']}, kun_match:"
            f" {kunyomi_process_result.yomi_match['matched_reading']}"
        )
        # If one is longer than the other, return the longer one
        if on_length > kun_length:
            log("\nonyomi_process_result is longer")
            return onyomi_process_result
        if kun_length > on_length:
            log("\nkunyomi_process_result is longer")
            return kunyomi_process_result
        # If same length, return kunyomi if we have okurigana
        if kunyomi_process_result.okurigana:
            log("\nsame length kunyomi_process_result has okurigana")
            return kunyomi_process_result
        # Otherwise return onyomi
        log("\nreturn same length onyomi_process_result")
        return onyomi_process_result
    if onyomi_process_result:
        log("\nonyomi_process_result is returned")
        return onyomi_process_result
    if kunyomi_process_result:
        log("\nkunyomi_process_result is returned")
        return kunyomi_process_result

    return None


def process_jukujikun_reading(
    highlight_args: HighlightArgs,
    word_data: WordData,
    with_tags_def: WithTagsDef,
    show_error_message: Callable = print,
) -> ReadingProcessResult:

    maybe_okuri = word_data.get("okurigana", "")
    edge = word_data.get("edge", "none")

    # Neither onyomi nor kunyomi matched, get jukujikun or nothing
    kanji_count = word_data.get("kanji_count")
    kanji_pos = word_data.get("kanji_pos")

    if kanji_count is None or kanji_pos is None:
        show_error_message(
            "Error in kana_highlight[]: process_readings() called with no kanji_count"
            " or kanji_pos specified"
        )
        return ReadingProcessResult(
            {
                "text": word_data.get("furigana", ""),
                "type": "none",
                "match_edge": edge,
                "actual_match": "",
                "matched_reading": "",
            },
            "",
            maybe_okuri,
        )

    return ReadingProcessResult(
        handle_jukujikun_case(word_data, highlight_args, with_tags_def.with_tags),
        maybe_okuri if with_tags_def.assume_dictionary_form else "",
        maybe_okuri if not with_tags_def.assume_dictionary_form else "",
    )


def get_target_furigana_section(
    furigana: str, edge: Optional[Edge], show_error_message: Callable
) -> str:
    """
    Function that returns the part of the furigana that should be matched against the onyomi or
    kunyomi

    :return: string, the part of the furigana that should be matched against the onyomi or kunyomi
        None for empty furigana or incorrect edge
    """
    if len(furigana) == 1:
        # If the furigana is only one character, we can't split it
        return furigana
    if edge == "whole":
        # Highlight the whole furigana
        return furigana
    if edge == "left":
        # Leave out the last character of the furigana
        return furigana[:-1]
    if edge == "right":
        # Leave out the first character of the furigana
        return furigana[1:]
    if edge == "middle":
        # Leave out both the first and last characters of the furigana
        return furigana[1:-1]
    show_error_message(
        "Error in kana_highlight[]: get_target_furigana_section() called with"
        f" incorrect edge='{edge}'"
    )
    # return the original to be safe
    return furigana


ReadingType = Literal["none", "plain", "rendaku", "small_tsu", "rendaku_small_tsu", "vowel_change"]


def is_reading_in_furigana_section(
    reading: str,
    furigana_section: str,
    okurigana: str,
    edge: Edge,
) -> Tuple[str, ReadingType]:
    """
    Function that checks if a reading is in the furigana section

    :return: str, the reading that matched the furigana section
    """
    if not reading:
        return "", "none"
    # The reading might have a match with a changed kana like シ->ジ, フ->プ, etc.
    # This only applies to the first kana in the reading and if the reading isn't a single kana
    rendaku_readings = []
    if possible_rendaku_kana := RENDAKU_CONVERSION_DICT.get(reading[0]):
        for kana in possible_rendaku_kana:
            rendaku_readings.append(f"{kana}{reading[1:]}")
    # Then also check for small tsu conversion of some consonants
    # this only happens in the last kana of the reading
    small_tsu_readings = []
    for kana in SMALL_TSU_POSSIBLE_HIRAGANA:
        if reading[-1] == kana:
            small_tsu_readings.append(f"{reading[:-1]}っ")
    # Handle う-->っ cases, these can have the っ in the okurigana so it's more like
    # the う is dropped in these cases. So, check if the first okuri char is っ and this
    # reading ends in う. If so, add a reading with う removed
    # These only apply when the okuri could belong to this reading, so "whole" or "right" edge
    u_dropped_readings = []
    if okurigana and okurigana[0] == "っ" and reading[-1] == "う":
        u_dropped_readings.append(f"{reading[:-1]}")
        for rendaku_reading in rendaku_readings:
            u_dropped_readings.append(f"{rendaku_reading[:-1]}")
    # Handle vowel change
    vowel_change_readings = []
    if reading[0] in VOWEL_CHANGE_DICT:
        for kana in VOWEL_CHANGE_DICT[reading[0]]:
            vowel_change_readings.append(f"{kana}{reading[1:]}")

    if edge == "whole":
        # match the whole furigana or repeat twice in it, possibly with rendaku or small tsu
        # (eg. the next kanji is the same or 々)
        if reading == furigana_section:
            return reading, "plain"
        for u_dropped_reading in u_dropped_readings:
            if u_dropped_reading == furigana_section:
                return u_dropped_reading, "small_tsu"
        if reading * 2 == furigana_section:
            return reading * 2, "plain"
        for rendaku_reading in rendaku_readings:
            if rendaku_reading == furigana_section:
                return rendaku_reading, "rendaku"
            if f"{reading}{rendaku_reading}" == furigana_section:
                return f"{reading}{rendaku_reading}", "rendaku"
        for small_tsu_reading in small_tsu_readings:
            if small_tsu_reading == furigana_section:
                return small_tsu_reading, "small_tsu"
            if f"{small_tsu_reading}{reading}" == furigana_section:
                return f"{small_tsu_reading}{reading}", "small_tsu"
        for vowel_change_reading in vowel_change_readings:
            if vowel_change_reading == furigana_section:
                return vowel_change_reading, "vowel_change"
        return "", "none"
    # For non-whole edge, also check readings are both rendaku and small tsu
    rendaku_small_tsu_readings = []
    for rendaku_reading in rendaku_readings:
        for kana in SMALL_TSU_POSSIBLE_HIRAGANA:
            if rendaku_reading[-1] == kana:
                rendaku_small_tsu_readings.append(f"{rendaku_reading[:-1]}っ")
    all_readings = (
        [(reading, "plain")]
        + [(r, "rendaku") for r in rendaku_readings]
        + [(r, "small_tsu") for r in small_tsu_readings]
        + [(r, "rendaku_small_tsu") for r in rendaku_small_tsu_readings]
        + [(r, "vowel_change") for r in vowel_change_readings]
    )
    if edge == "left":
        for r, t in all_readings:
            if furigana_section.startswith(r):
                return r, cast(ReadingType, t)
        return "", "none"
    if edge == "right":
        for r, t in all_readings:
            if furigana_section.endswith(r):
                return r, cast(ReadingType, t)
        for u_dropped_reading in u_dropped_readings:
            if u_dropped_reading == furigana_section:
                return u_dropped_reading, "small_tsu"
        return "", "none"
    # middle
    for r, t in all_readings:
        if r in furigana_section:
            return r, cast(ReadingType, t)
    return "", "none"


def check_onyomi_readings(
    onyomi: str,
    furigana: str,
    okurigana: str,
    target_furigana_section: str,
    edge: Edge,
    wrap_readings_with_tags: bool = True,
    process_type: MatchProcess = "match",
) -> YomiMatchResult:
    """
    Function that checks the onyomi readings against the target furigana section

    :return: string, the modified furigana
      or [True, False] when return_on_or_kun_match_only
    """
    if not onyomi:
        return {
            "text": "",
            "type": "none",
            "match_edge": "none",
            "actual_match": "",
            "matched_reading": "",
        }
    onyomi_readings = onyomi.split("、")
    # order readings by length so that we try to match the longest reading first
    onyomi_readings.sort(key=len, reverse=True)

    log(
        f"\ncheck_onyomi_readings - target_furigana_section: {target_furigana_section}, edge:"
        f" {edge}"
    )

    for onyomi_reading in onyomi_readings:
        # remove text in () in the reading
        onyomi_reading = re.sub(r"\(.*?\)", "", onyomi_reading).strip()
        log(f"\ncheck_onyomi_readings - onyomi_reading: {onyomi_reading}")
        if not onyomi_reading:
            continue
        # Convert the onyomi to hiragana since the furigana is in hiragana
        onyomi_reading = to_hiragana(onyomi_reading)
        match_in_section, match_type = is_reading_in_furigana_section(
            onyomi_reading,
            target_furigana_section,
            okurigana,
            edge,
        )
        log(
            f"\ncheck_onyomi_readings - onyomi_reading: {onyomi_reading}, in_section:"
            f" {match_in_section}, type: {match_type}"
        )
        if match_in_section:
            return {
                "text": process_onyomi_match(
                    furigana,
                    match_in_section,
                    edge,
                    process_type,
                    wrap_readings_with_tags,
                ),
                "type": "onyomi",
                "match_edge": edge,
                "actual_match": match_in_section,
                "matched_reading": onyomi_reading,
            }
    return {
        "text": "",
        "type": "none",
        "match_edge": "none",
        "actual_match": "",
        "matched_reading": "",
    }


def process_onyomi_match(
    furigana: str,
    onyomi_that_matched: str,
    edge: Edge,
    process_type: MatchProcess,
    wrap_readings_with_tags: bool,
) -> str:
    """
    Function that replaces the furigana with the onyomi reading that matched

    :return: string, the modified furigana or the matched part, depending on the process_type
    """
    if edge == "right":
        reg = re_match_from_right(onyomi_that_matched)
    elif edge == "left":
        reg = re_match_from_left(onyomi_that_matched)
    else:
        reg = re_match_from_middle(onyomi_that_matched)
    if process_type == "match":
        match = reg.match(furigana)
        if match:
            return to_katakana(match.group(2))
        # return nothing if we have no match
        return ""
    replacer = partial(onyomi_replacer, wrap_readings_with_tags=wrap_readings_with_tags)
    return re.sub(reg, replacer, furigana)


def check_okurigana_for_kunyomi_inflection(
    kunyomi_okurigana: str,
    kunyomi_reading: str,
    word_data: WordData,
    highlight_args: HighlightArgs,
) -> OkuriResults:
    """
    Function that checks the okurigana for a match with the kunyomi okurigana

    :return: (string, string) the okurigana that should be highlighted and the rest of the okurigana
    """
    # Kana text occurring after the kanji in the word, may not be okurigana and can
    # contain other kana after the okurigana
    maybe_okuri_text = word_data.get("okurigana")
    log(
        f"\ncheck okurigana 0 - kunyomi_okurigana: {kunyomi_okurigana},"
        f" maybe_okurigana: {maybe_okuri_text}"
    )

    if not kunyomi_okurigana or not maybe_okuri_text:
        return OkuriResults("", "", "no_okuri")

    # Simple case, exact match, no need to check conjugations
    if kunyomi_okurigana == maybe_okuri_text:
        return OkuriResults(kunyomi_okurigana, "", "full_okuri")

    # Check what kind of inflections we should be looking for from the kunyomi okurigana
    conjugatable_stem = get_conjugatable_okurigana_stem(kunyomi_okurigana)

    # Another simple case, stem is the same as the okurigana, no need to check conjugations
    if conjugatable_stem == maybe_okuri_text:
        return OkuriResults(conjugatable_stem, "", "full_okuri")

    log(f"\ncheck okurigana 1 - conjugatable_stem: {conjugatable_stem}")
    if conjugatable_stem is None or not maybe_okuri_text.startswith(conjugatable_stem):
        log("\ncheck okurigana 2 - no conjugatable_stem or no match")
        # Not a verb or i-adjective, so just check for an exact match within the okurigana
        if maybe_okuri_text.startswith(kunyomi_okurigana):
            log(f"\ncheck okurigana 3 - maybe_okuri_text: {maybe_okuri_text}")
            return OkuriResults(
                kunyomi_okurigana,
                maybe_okuri_text[len(kunyomi_okurigana) :],
                "full_okuri",
            )
        log("\ncheck okurigana 4 - no match")
        return OkuriResults("", maybe_okuri_text, "no_okuri")

    # Remove the conjugatable_stem from maybe_okurigana
    trimmed_maybe_okuri = maybe_okuri_text[len(conjugatable_stem) :]
    log(f"\ncheck okurigana 5 - trimmed_maybe_okuri: {trimmed_maybe_okuri}")

    # Then check if that contains a conjugation for what we're looking for
    conjugated_okuri, rest, return_type = starts_with_okurigana_conjugation(
        trimmed_maybe_okuri,
        kunyomi_okurigana,
        highlight_args["kanji_to_match"],
        kunyomi_reading,
    )
    log(
        f"\ncheck okurigana 6 - conjugated_okuri: {conjugated_okuri}, rest: {rest},"
        f" return_type: {return_type}"
    )

    if return_type != "no_okuri":
        log(f"\ncheck okurigana 7 - result: {conjugatable_stem + conjugated_okuri}, rest: {rest}")
        # remember to add the stem back!
        return OkuriResults(conjugatable_stem + conjugated_okuri, rest, return_type)

    # No match, this text doesn't contain okurigana for the kunyomi word
    log("\ncheck okurigana 8 - no match")
    return OkuriResults("", maybe_okuri_text, "no_okuri")


def check_kunyomi_readings(
    highlight_args: HighlightArgs,
    word_data: WordData,
    furigana: str,
    target_furigana_section: str,
    edge: Edge,
    wrap_readings_with_tags: bool = True,
    process_type: MatchProcess = "match",
) -> YomiMatchResult:
    """
    Function that checks the kunyomi readings against the target furigana section and okurigana

    :return: Result dict with the modified furigana
    """
    kunyomi = highlight_args.get("kunyomi", "")
    if not kunyomi:
        return {
            "text": "",
            "type": "none",
            "match_edge": "none",
            "actual_match": "",
            "matched_reading": "",
        }

    kunyomi_readings = kunyomi.split("、")
    stem_match_results: list[YomiMatchResult] = []
    kunyomi_stems: set[Tuple[str, str]] = set()
    kunyomi_stem_and_okuris: list[Tuple[str, str, str]] = []
    for kunyomi_reading in kunyomi_readings:
        if not kunyomi_reading:
            continue
        log(f"\ncheck_kunyomi_readings - kunyomi_reading: {kunyomi_reading}")
        # Split the reading into the stem and the okurigana
        kunyomi_stem = kunyomi_reading
        kunyomi_dict_form_okuri = ""
        if "." in kunyomi_reading:
            try:
                kunyomi_stem, kunyomi_dict_form_okuri = kunyomi_reading.split(".")
            except ValueError:
                log(
                    "\nError in kana_highlight[]: kunyomi contained multiple dots:"
                    f" {kunyomi_reading}"
                )
                return {
                    "text": furigana,
                    "type": "kunyomi",
                    "match_edge": edge,
                    "actual_match": "",
                    "matched_reading": "",
                }
        # We only need to check unique stems
        kunyomi_stems.add((kunyomi_stem, kunyomi_reading))
        # And noun forms for readings that have okuri
        if kunyomi_dict_form_okuri:
            kunyomi_stem_and_okuris.append((kunyomi_stem, kunyomi_dict_form_okuri, kunyomi_reading))

    okurigana = word_data.get("okurigana", "")
    # First check matches against the stem
    for kunyomi_stem, full_reading in kunyomi_stems:
        if not kunyomi_stem:
            continue
        match_in_section, match_type = is_reading_in_furigana_section(
            kunyomi_stem, target_furigana_section, okurigana, edge
        )
        log(
            f"\ncheck_kunyomi_readings - kunyomi_stem: {kunyomi_stem}, in_section:"
            f" {match_in_section}, type: {match_type}"
        )
        if match_in_section:
            stem_match_results.append({
                "text": process_kunyomi_match(
                    furigana,
                    match_in_section,
                    edge,
                    process_type,
                    wrap_readings_with_tags,
                ),
                "match_edge": edge,
                "type": "kunyomi",
                "actual_match": match_in_section,
                "matched_reading": full_reading,
            })
    kanji_to_match = highlight_args.get("kanji_to_match", "")
    log(
        f"\ncheck_kunyomi_readings - noun form: {kunyomi_stem}, kunyomi_dict_form_okuri:"
        f" {kunyomi_dict_form_okuri}\nokurigana: {{okurigana}}, kanji_to_match:"
        " {kanji_to_match}"
    )

    # Then also readings with okurigana included in the furigana, noun forms and others
    # In this case there should be no okurigana as it would be a reading where those are omitted
    # e.g. 曳舟--曳き舟, 取調--取り調べ, 書留--書き留め
    okuri_included_results: list[YomiMatchResult] = []
    for kunyomi_stem, kunyomi_dict_form_okuri, full_reading in kunyomi_stem_and_okuris:
        noun_form_okuri = get_verb_noun_form_okuri(
            kunyomi_dict_form_okuri, kanji_to_match, kunyomi_reading
        )
        if (
            (not okurigana and edge in ["right", "whole"]) or (edge in ["left", "middle"])
        ) and kunyomi_dict_form_okuri:
            # Replace last kana in dict form okuri with the noun form ending
            okuri_included_reading = f"{kunyomi_stem}{kunyomi_dict_form_okuri}"
            if noun_form_okuri:
                okuri_included_reading = f"{kunyomi_stem}{noun_form_okuri}"
            match_in_section, match_type = is_reading_in_furigana_section(
                okuri_included_reading, target_furigana_section, okurigana, edge
            )
            log(
                f"\ncheck_kunyomi_readings - okuri_included form: {okuri_included_reading},"
                f" in_section: {match_in_section}, type: {match_type}"
            )
            if match_in_section:
                okuri_included_results.append({
                    "text": process_kunyomi_match(
                        furigana,
                        match_in_section,
                        edge,
                        process_type,
                        wrap_readings_with_tags,
                    ),
                    "match_edge": edge,
                    "type": "kunyomi",
                    "actual_match": match_in_section,
                    "matched_reading": full_reading,
                })
    log(
        f"\ncheck_kunyomi_readings - stem_match_results: {stem_match_results},"
        f" okuri_included_results: {okuri_included_results}"
    )
    # If both results are found, return the one with the longest match
    results_by_length: list[list[YomiMatchResult]] = []
    for result in stem_match_results + okuri_included_results:
        result_length = len(result["actual_match"])
        while len(results_by_length) < result_length:
            results_by_length.append([])
        results_by_length[result_length - 1].append(result)
    if results_by_length:
        longest_results = results_by_length[-1]
        # Even if there are multiple results with the same length, just return the first one
        # they all have the same kana, after all
        return longest_results[0]

    # No match for either check exceptions...

    # Exception for 尻尾[しっぽ] where 尾[ぽ] should be considered a kunyomi, not jukujikun
    # 尻 already gets matched with small tsu conversion so handle 尾[ぽ] here
    if highlight_args["kanji_to_match"] == "尾" and furigana == "ぽ":
        return {
            "text": process_kunyomi_match(
                furigana,
                "ぽ",
                edge,
                process_type,
                wrap_readings_with_tags,
            ),
            "match_edge": edge,
            "type": "kunyomi",
            "actual_match": "ぽ",
            "matched_reading": "ほ",
        }
    log("\ncheck_kunyomi_readings - no match")
    return {
        "text": "",
        "type": "none",
        "match_edge": "none",
        "actual_match": "",
        "matched_reading": "",
    }


def process_kunyomi_match(
    furigana: str,
    kunyomi_that_matched: str,
    edge: Edge,
    process_type: MatchProcess,
    wrap_readings_with_tags: bool,
) -> str:
    """
    Function that replaces the furigana with the kunyomi reading that matched
    :return: string, the modified furigana or the matched part, depending on the process_type
    """
    if edge == "right":
        reg = re_match_from_right(kunyomi_that_matched)
    elif edge == "left":
        reg = re_match_from_left(kunyomi_that_matched)
    else:
        reg = re_match_from_middle(kunyomi_that_matched)
    if process_type == "match":
        match = reg.match(furigana)
        if match:
            return match.group(2)
        return ""
    replacer = partial(kunyomi_replacer, wrap_readings_with_tags=wrap_readings_with_tags)
    return re.sub(reg, replacer, furigana)


def handle_jukujikun_case(
    word_data: WordData,
    highlightArgs: HighlightArgs,
    wrap_readings_with_tags: bool,
) -> YomiMatchResult:
    """
    Function that handles the case of a jukujikun/ateji word where the furigana
    doesn't match the onyomi or kunyomi. Highlights the part of the furigana matching
    the kanji position
    :return: Result dict with the modified furigana
    """
    kanji_to_highlight = highlightArgs.get("kanji_to_highlight", "")
    kanji_count = word_data.get("kanji_count", 0)
    assert (
        kanji_count > 0
    ), f"handle_jukujikun_case[]: incorrect kanji_count: {word_data.get('kanji_count')}"
    word = word_data.get("word", "")
    kanji_pos = word.find(kanji_to_highlight)
    # kanji_pos can be -1, in which case no highlighting happens
    assert kanji_pos < kanji_count, (
        f"handle_jukujikun_case[]: incorrect kanji_pos: {kanji_pos}, kanji_to_highlight:"
        f" {kanji_to_highlight}"
    )
    furigana = word_data.get("furigana", "")

    # First split the word into mora
    mora_list = ALL_MORA_REC.findall(furigana)
    # Divide the mora by the number of kanji in the word
    mora_count = len(mora_list)
    mora_per_kanji = mora_count // kanji_count
    # Split the remainder evenly among the kanji,
    # by adding one mora to each kanji until the remainder is 0
    remainder = mora_count % kanji_count
    new_furigana = ""
    match_edge: Edge = "left"
    cur_mora_index = 0
    kanji_index = 0
    actual_match = ""
    is_kanji_match = False
    while kanji_index < kanji_count:
        next_kanji = word[kanji_index + 1] if kanji_index < kanji_count - 1 else ""
        cur_mora_range_max = cur_mora_index + mora_per_kanji
        is_rep_kanji = next_kanji == "々"
        log(
            f"\njuku mora 1, kanji_index: {kanji_index}, kanji_pos: {kanji_pos}, cur_mora_index:"
            f" {cur_mora_index}, cur_mora_range_max: {cur_mora_range_max}, mora_per_kanji:"
            f" {mora_per_kanji}, remainder: {remainder}, cur_kanji: {word[kanji_index]} next_kanji:"
            f" {next_kanji}"
        )
        if is_rep_kanji:
            # If the next kanji is the repeater, this tag should get one set of mora
            cur_mora_range_max += mora_per_kanji
        if remainder > 0:
            cur_mora_range_max += 1
            remainder -= 1
        is_kanji_match = kanji_index == kanji_pos
        if is_kanji_match:
            new_furigana += "<b>"
            if kanji_index == 0:
                match_edge = "left"
            elif kanji_index == kanji_count - 1:
                match_edge = "right"
            else:
                match_edge = "middle"
        elif kanji_index == kanji_pos + 1 and kanji_pos != -1:
            log(
                f"\njuku mora 3 closing bold - kanji_index: {kanji_index}, kanji_pos: {kanji_pos},"
                f" has_bold: {new_furigana[-3:] == '<b>'}, new_furigana: {new_furigana}"
            )
            new_furigana += "</b>" if new_furigana[-4:] != "</b>" else ""

        mora = "".join(mora_list[cur_mora_index:cur_mora_range_max])
        log(f"\njuku mora 2 - mora: {mora}")
        if wrap_readings_with_tags:
            new_furigana += f"<juk>{mora}</juk>"
        else:
            new_furigana += mora
        if is_kanji_match:
            actual_match = mora
        log(f"\njuku mora 5 - new_furigana: {new_furigana}")

        if kanji_index == kanji_pos:
            log(
                f"\njuku mora 4 closing bold - kanji_index: {kanji_index}, kanji_pos: {kanji_pos},"
                f" has_bold: {new_furigana[-3:] == '<b>'}, new_furigana: {new_furigana}"
            )
            new_furigana += "</b>" if new_furigana[-4:] != "</b>" else ""
        cur_mora_index = cur_mora_range_max
        if is_rep_kanji:
            # Skip the next kanji since it's the repeater and we handled it already
            kanji_index += 2
        else:
            kanji_index += 1
    log(f"\nhandle_jukujikun_case - new_furigana: {new_furigana}")
    return {
        "text": new_furigana,
        "type": "jukujikun",
        "match_edge": match_edge,
        "actual_match": actual_match,
        "matched_reading": "",
    }


def handle_whole_word_case(
    highlight_args,
    word: str,
    furigana: str,
    okurigana: str,
    with_tags_def: WithTagsDef,
    show_error_message: Callable,
) -> FinalResult:
    """
    The case when the whole word contains the kanji to highlight.
    So, either it's a single kanji word or the kanji is repeated.

    :return: string, the modified furigana entirely highlighted, additionally
        in katakana for onyomi
    """
    word_data: WordData = {
        "kanji_pos": 0,
        "kanji_count": 1,
        "furigana": furigana,
        "edge": "whole",
        "word": word,
        "okurigana": okurigana,
    }
    res = process_readings(
        highlight_args,
        word_data,
        process_type="replace",
        with_tags_def=with_tags_def,
        show_error_message=show_error_message,
    )
    if res is None:
        log("\nhandle_whole_word_case - handle as jukujikun")
        res = process_jukujikun_reading(
            highlight_args,
            word_data,
            with_tags_def=with_tags_def,
            show_error_message=show_error_message,
        )
    result, okurigana_to_highlight, rest_kana = res
    log(
        f"\nhandle_whole_word_case - word: {word}, result: {result}, okurigana:"
        f" {okurigana_to_highlight}, rest_kana: {rest_kana}"
    )

    if result["type"] == "onyomi":
        onyomi_kana = to_katakana(furigana)
        if with_tags_def.with_tags:
            onyomi_kana = f"<on>{onyomi_kana}</on>"
        # For onyomi matches the furigana should be in katakana
        final_furigana = f"<b>{onyomi_kana}</b>"
    elif result["type"] == "kunyomi":
        if with_tags_def.with_tags:
            furigana = f"<kun>{furigana}</kun>"
        final_furigana = f"<b>{furigana}</b>"
    elif result["type"] == "jukujikun":
        final_furigana = result["text"]
    return {
        "furigana": final_furigana,
        "okurigana": okurigana_to_highlight,
        "rest_kana": rest_kana,
        "left_word": "",
        "middle_word": word,
        "right_word": "",
        "edge": "whole",
    }


def handle_partial_word_case(
    highlight_args: HighlightArgs,
    word: str,
    furigana: str,
    okurigana: str,
    with_tags_def: WithTagsDef,
    show_error_message: Callable,
) -> Union[PartialResult, None]:
    """
    The case when the word contains other kanji in addition to the kanji to highlight.
    Could be 2 or more kanji in the word.

    :return: string, the modified furigana with the kanji to highlight highlighted
    """
    kanji_to_match = highlight_args.get("kanji_to_match", "")

    kanji_pos = word.find(kanji_to_match)
    if kanji_pos == -1:
        # No match found, return the furigana as-is
        return {
            "matched_furigana": "",
            "match_type": "none",
            "rest_furigana": furigana,
            "okurigana": okurigana,
            "rest_kana": "",
            "edge": "whole",
        }

    edge = highlight_args.get("edge")

    if not edge:
        show_error_message(
            "Error in kana_highlight[]: handle_partial_word_case() called with no edge specified"
        )
        return {
            "matched_furigana": "",
            "match_type": "none",
            "rest_furigana": furigana,
            "okurigana": okurigana,
            "rest_kana": "",
            "edge": "whole",
        }

    word_data: WordData = {
        "kanji_pos": kanji_pos,
        "kanji_count": len(word),
        "furigana": furigana,
        "edge": edge,
        "word": word,
        "okurigana": okurigana,
    }

    log(
        f"\nhandle_partial_word_case - word: {word}, furigana: {furigana}, okurigana: {okurigana},"
        f" kanji_to_match: {kanji_to_match}, kanji_data: {all_kanji_data.get(kanji_to_match)},"
        f" edge: {edge}"
    )

    # Handle cases that should be a jukujikun reading but the first kanji has a matching kunyomi
    if (
        # All these cases are 2-kanji long
        len(word) >= 2
        and (juku_reading := JUKUJIKUN_KUNYOMI_OVERLAP.get(word[:2]))
        and furigana.startswith(juku_reading)
    ):
        # Force these into the jukujikun processing
        return None

    res = process_readings(
        highlight_args,
        word_data,
        process_type="match",
        with_tags_def=with_tags_def,
        show_error_message=show_error_message,
    )
    if res is None:
        log("\nhandle_partial_word_case - no result from process_readings")
        return None

    main_result, okurigana_to_highlight, rest_kana = res

    furi_okuri_result: PartialResult = {
        "matched_furigana": "",
        "match_type": main_result["type"],
        "rest_furigana": "",
        "okurigana": "",
        "rest_kana": "",
        "edge": main_result["match_edge"],
    }

    matched_furigana = main_result["text"]
    rest_furigana = furigana[len(matched_furigana) :]
    if okurigana_to_highlight:
        furi_okuri_result["matched_furigana"] = matched_furigana
        furi_okuri_result["rest_furigana"] = rest_furigana
        furi_okuri_result["okurigana"] = okurigana_to_highlight
        furi_okuri_result["rest_kana"] = rest_kana
    else:
        furi_okuri_result["matched_furigana"] = matched_furigana
        furi_okuri_result["rest_furigana"] = rest_furigana
        furi_okuri_result["okurigana"] = ""
        furi_okuri_result["rest_kana"] = rest_kana
    log(f"\nhandle_partial_word_case - final_result: {furi_okuri_result}")
    return furi_okuri_result


def kana_highlight(
    kanji_to_highlight: str,
    text: str,
    return_type: FuriReconstruct = "kana_only",
    with_tags_def: Optional[WithTagsDef] = None,
    show_error_message: Callable = print,
) -> str:
    if with_tags_def is None:
        with_tags_def = WithTagsDef(
            True, True, False  # with_tags  # merge_consecutive  # assume dictionary form
        )
    """
    Function that replaces the furigana of a kanji with the furigana that corresponds to the kanji's
    onyomi or kunyomi reading. The furigana is then highlighted with <b> tags.
    Text received could be a sentence or a single word with furigana.
    :param kanji_to_highlight: should be a single kanji character
    :param text: The text to process
    :param return_type: string. Return either normal furigana, reversed furigana AKA furikanji or
        remove the kanji and return only the kana
    :param with_tags_def: tuple, with_tags and merge_consecutive keys. Whether to wrap the readings
        with tags and whether to merge consecutive tags
    :param show_error_message: Callable, function to call when an error message is needed
    :return: The text cleaned from any previous <b> tags and <b> added around the furigana
        when the furigana corresponds to the kanji_to_highlight
    """

    def furigana_replacer(match: re.Match):
        """
        Replacer function for KANJI_AND_FURIGANA_REC. This function is called for every match
        found by the regex. It processes the furigana and returns the modified furigana.
        :param match: re.Match, the match object
        :return: string, the modified furigana
        """
        word = match.group(1)
        furigana = match.group(2)
        okurigana = match.group(3)
        log(f"\nword: {word}, furigana: {furigana}, okurigana: {okurigana}")

        if furigana.startswith("sound:"):
            # This was something like 漢字[sound:...], we shouldn't modify the text in the brackets
            # as it'd break the audio tag. But we know the text to the right is kanji
            # (what is it doing there next to a sound tag?) so we'll just leave it out anyway
            return furigana + okurigana

        highlight_kanji_is_whole_word = (
            word == kanji_to_highlight
            or f"{kanji_to_highlight}々" == word
            or kanji_to_highlight * 2 == word
        )

        # Whole word case is easy, just highlight the whole furigana
        if highlight_kanji_is_whole_word:
            kanji_data = all_kanji_data.get(kanji_to_highlight)
            if not kanji_data:
                show_error_message(
                    f"Error in kana_highlight[]: kanji '{kanji_to_highlight}' not found in"
                    " all_kanji_data"
                )
                return furigana + okurigana
            highlight_args: HighlightArgs = {
                "kanji_to_highlight": kanji_to_highlight,
                "kanji_to_match": kanji_to_highlight,
                "onyomi": kanji_data.get("onyomi", ""),
                "kunyomi": kanji_data.get("kunyomi", ""),
                "add_highlight": True,
                "edge": "whole",
            }
            final_result = handle_whole_word_case(
                highlight_args,
                word,
                furigana,
                okurigana,
                with_tags_def,
                show_error_message,
            )
            return reconstruct_furigana(
                final_result,
                with_tags_def,
                reconstruct_type=return_type,
            )

        cur_furigana_section = furigana
        cur_word = word
        cur_edge: Edge = "left"
        kanji_to_highlight_passed = False
        final_furigana = ""
        final_okurigana = ""
        final_rest_kana = ""
        final_edge: Edge = "whole"
        final_left_word = ""
        final_middle_word = ""
        final_right_word = ""

        juku_word_start = None
        juku_word_end = None
        juku_furigana = None
        juku_word_start_edge = None
        juku_word_pos_to_highlight: Union[Literal["left", "middle", "right"], None] = None
        # For the partial case, we need to split the furigana for each kanji using the kanji_data
        # for each one, highlight the kanji_to_match and reconstruct the furigana
        for index, kanji in enumerate(word):
            if kanji == "々":
                # Skip repeater as this will have been handled in the previous iteration
                continue
            is_first_kanji = index == 0
            is_last_kanji = index == len(word) - 1
            is_middle_kanji = not is_first_kanji and not is_last_kanji
            if is_middle_kanji:
                cur_edge = "middle"
            elif is_last_kanji:
                cur_edge = "right"
            kanji_data_key = NUMBER_TO_KANJI.get(kanji, kanji)
            kanji_data = all_kanji_data.get(kanji_data_key)
            if not kanji_data:
                show_error_message(
                    f"Error in kana_highlight[]: kanji '{kanji}' not found in all_kanji_data"
                )
                return furigana + okurigana
            is_kanji_to_highlight = kanji == kanji_to_highlight
            highlight_args = {
                "kanji_to_highlight": kanji_to_highlight,
                "kanji_to_match": kanji,
                "onyomi": kanji_data.get("onyomi", ""),
                "kunyomi": kanji_data.get("kunyomi", ""),
                "add_highlight": is_kanji_to_highlight,
                # Since we advance one kanji at a time, removing the furigana for the previous match
                # the edge is "left" until the last kanji. Since the last kanji is a single kanji
                # the edge is "whole" and not "right"
                "edge": "left" if not is_last_kanji else "whole",
            }
            partial_result = handle_partial_word_case(
                highlight_args,
                cur_word,
                cur_furigana_section,
                okurigana if is_last_kanji else "",
                with_tags_def=with_tags_def,
                show_error_message=show_error_message,
            )
            log(
                f"\npartial_result: {partial_result}, is_kanji_to_highlight:"
                f" {is_kanji_to_highlight}"
            )
            if partial_result is None:
                # Need to handle this as jukujikun, break and
                # proceed to reverse processing of the rest of the word
                juku_word_start_edge = cur_edge
                juku_word_start = index
                juku_furigana = cur_furigana_section
                if kanji_to_highlight_passed:
                    juku_word_pos_to_highlight = "right"
                break
            matched_furigana = partial_result["matched_furigana"]
            wrapped_furigana = matched_furigana

            next_kanji = word[index + 1] if not is_last_kanji else ""
            if next_kanji == "々":
                log(f"\nrepeater kanji: {next_kanji}")
                rep_kanji = next_kanji
                cur_word = cur_word[2:]
                # if we had the repeater kanji, we should add more furigana to this result
                # If this was a normal match, the furigana should be repeating
                log(f"\nrepeater kanji - doubling furigana: {matched_furigana}")
                matched_furigana *= 2
                wrapped_furigana = matched_furigana
            else:
                rep_kanji = ""
                cur_word = cur_word[1:]

            if with_tags_def.with_tags:
                if partial_result["match_type"] == "onyomi":
                    wrapped_furigana = f"<on>{matched_furigana}</on>"
                elif partial_result["match_type"] == "kunyomi":
                    wrapped_furigana = f"<kun>{matched_furigana}</kun>"

            if is_kanji_to_highlight and wrapped_furigana:
                final_furigana += f"<b>{wrapped_furigana}</b>"
            elif matched_furigana:
                final_furigana += wrapped_furigana
            # Slice the furigana and word to remove the part that was already processed
            cur_furigana_section = cur_furigana_section[len(matched_furigana) :]
            log(
                f"\nwrapped_furigana: {wrapped_furigana}, matched_furigana: {matched_furigana},"
                f" cur_furigana_section: {cur_furigana_section}, cur_word: {cur_word}"
            )
            # If this was the kanji to highlight, this edge should be in the final_result as
            # reconstructed furigana needs it
            if is_kanji_to_highlight:
                final_edge = cur_edge
                kanji_to_highlight_passed = True

            # The complex part is putting the furigana back together
            # Left word: every kanji before the kanji to highlight or the first kanji, if
            #   the kanji to highlight is the first one
            # Middle word: the kanji to highlight if it's in the middle, otherwise empty
            # Right word: every kanji after the kanji to highlight or the last kanji, if
            #   the kanji to highlight is the last one
            if is_first_kanji:
                final_left_word += kanji + rep_kanji
            elif is_middle_kanji and is_kanji_to_highlight:
                final_middle_word += kanji + rep_kanji
            elif is_middle_kanji and not kanji_to_highlight_passed:
                final_left_word += kanji + rep_kanji
            elif is_middle_kanji and kanji_to_highlight_passed:
                final_right_word += kanji + rep_kanji
            elif is_last_kanji:
                final_right_word += kanji + rep_kanji

            # Rest_kana and okurigana is only added on processing the last kanji
            if is_last_kanji:
                final_rest_kana = partial_result["rest_kana"]
                final_okurigana = partial_result["okurigana"]

            if not matched_furigana:
                show_error_message(
                    f"Error in kana_highlight[]: no match found for kanji {kanji} in word {word}"
                )
                # Something went wrong with the matching, we can't slice the furigana so we can't
                # continue. Return what we got so far
                final_furigana += cur_furigana_section
                final_okurigana += okurigana
                final_right_word += cur_word
                cur_word = ""
                cur_furigana_section = ""
                break

        # If cur_word is not empty, we need to handle the rest of the word as jukujikun
        # Process backward until we once more get to a non-match marking the juku_word_end
        # the kanji from juku_word_start to juku_word_end is what is considered jukujikun
        # Then get the intersection of juku_furigana and the remaining cur_furigana_section
        # to get the furigana for the jukujikun part
        reverse_final_furigana = ""
        reverse_final_left_word = ""
        reverse_final_middle_word = ""
        reverse_final_right_word = ""
        juku_word_length = len(cur_word)
        juku_word_reversed = "".join(list(reversed(cur_word)))
        log(
            f"\npartial_result is None - juku_word_start: {juku_word_start}, juku_furigana:"
            f" {juku_furigana} juku_word_pos_to_highlight:"
            f" {juku_word_pos_to_highlight} juku_word_start_edge: {juku_word_start_edge},"
            f" juku_word_reversed: {juku_word_reversed}"
        )
        for i, kanji in enumerate(juku_word_reversed):
            if kanji == "々":
                # Skip repeater as this will be handled in the next iteration
                continue
            # The edge is reversed now, so the first kanji is the right edge
            is_first_kanji = i == juku_word_length - 1
            is_last_kanji = i == 0
            original_word_index = len(word) - i - 1
            # Last kanji is where we left off with the previous loop, so we can stop there
            if is_first_kanji:
                juku_word_end = original_word_index
                continue

            is_middle_kanji = not is_first_kanji and not is_last_kanji
            if is_first_kanji:
                cur_edge = juku_word_start_edge
            elif is_middle_kanji:
                cur_edge = "middle"
            kanji_data_key = NUMBER_TO_KANJI.get(kanji, kanji)
            kanji_data = all_kanji_data.get(kanji_data_key)
            if not kanji_data:
                show_error_message(
                    f"Error in kana_highlight[]: kanji '{kanji}' not found in all_kanji_data"
                )
                return furigana + okurigana
            is_kanji_to_highlight = kanji == kanji_to_highlight
            highlight_args = {
                "kanji_to_highlight": kanji_to_highlight,
                "kanji_to_match": kanji,
                "onyomi": kanji_data.get("onyomi", ""),
                "kunyomi": kanji_data.get("kunyomi", ""),
                "add_highlight": is_kanji_to_highlight,
                # Right edge now, as we're going backwards
                "edge": "right" if not is_first_kanji else "whole",
            }
            cur_word = kanji
            partial_result = handle_partial_word_case(
                highlight_args,
                cur_word,
                cur_furigana_section,
                okurigana if is_last_kanji else "",
                with_tags_def=with_tags_def,
                show_error_message=show_error_message,
            )
            log(
                f"\nreversing, partial_result: {partial_result}, is_kanji_to_highlight:"
                f" {is_kanji_to_highlight}"
            )
            if partial_result is None:
                # Found the end of the jukujikun part, this can be the same as juku_word_start
                juku_word_end = original_word_index
                log(f"\nreversing end juku_word_end: {juku_word_end}")
                break
            matched_furigana = partial_result["matched_furigana"]
            wrapped_furigana = matched_furigana

            prev_kanji = juku_word_reversed[i - 1] if i > 0 else ""
            if prev_kanji == "々":
                # Add the repeater to be processed as part of the current kanji
                kanji = f"{kanji}{prev_kanji}"
                rep_kanji = prev_kanji
                # if we had the repeater kanji, we should add more furigana to this result
                # If this was a normal match, the furigana should be repeating
                log(f"\nreversing, repeater kanji - doubling furigana: {matched_furigana}")
                matched_furigana *= 2
                wrapped_furigana = matched_furigana
            else:
                rep_kanji = ""

            if with_tags_def.with_tags:
                if partial_result["match_type"] == "onyomi":
                    wrapped_furigana = f"<on>{matched_furigana}</on>"
                elif partial_result["match_type"] == "kunyomi":
                    wrapped_furigana = f"<kun>{matched_furigana}</kun>"

            if is_kanji_to_highlight and wrapped_furigana:
                reverse_final_furigana = f"<b>{wrapped_furigana}</b>" + reverse_final_furigana
            elif matched_furigana:
                reverse_final_furigana = wrapped_furigana + reverse_final_furigana

            # Slice the furigana and word from the end to remove the part that was already processed
            cur_furigana_section = cur_furigana_section[: -len(matched_furigana)]
            # This is also the furigana to be eventually processed as jukujikun
            juku_furigana = cur_furigana_section
            log(
                f"\nwrapped_furigana: {wrapped_furigana}, matched_furigana: {matched_furigana},"
                f" cur_furigana_section: {cur_furigana_section}, cur_word: {cur_word}"
            )
            # If this was the kanji to highlight, this edge should be in the final_result as
            # reconstructed furigana needs it
            if is_kanji_to_highlight:
                final_edge = cur_edge
                kanji_to_highlight_passed = True
                juku_word_pos_to_highlight = "left"

            # The complex part is putting the furigana back together
            # A bit more so now that we're going backwards
            if is_last_kanji:
                reverse_final_right_word = kanji + rep_kanji + reverse_final_right_word
            elif is_middle_kanji and is_kanji_to_highlight:
                # Same as before
                reverse_final_middle_word = kanji + rep_kanji + reverse_final_middle_word
            elif is_middle_kanji and not kanji_to_highlight_passed:
                # Reversed to right word
                reverse_final_right_word = kanji + rep_kanji + reverse_final_right_word
            if is_middle_kanji and kanji_to_highlight_passed:
                # Reversed to left word
                reverse_final_left_word = kanji + rep_kanji + reverse_final_left_word
            # Final kanji (at juku_word_start) should never be encountered here as we'll break out
            # of the loop at latest on it due not finding a match

            if is_last_kanji:
                final_rest_kana = partial_result["rest_kana"]
                final_okurigana = partial_result["okurigana"]

        log(
            f"\nreversing processed, juku_word_start: {juku_word_start}, juku_word_end:"
            f" {juku_word_end}, juku_furigana: {juku_furigana}"
        )
        if juku_word_start is not None and juku_word_end is not None and juku_furigana is not None:
            juku_word = word[juku_word_start : juku_word_end + 1]
            juku_at_word_right_edge = juku_word_end == len(word) - 1
            juku_at_word_left_edge = juku_word_start == 0
            log(
                f"\nreversed handle_jukujikun_case - juku_word: {juku_word}, juku_furigana:"
                f" {juku_furigana}"
            )
            kanji_pos = juku_word.find(kanji_to_highlight)
            word_data: WordData = {
                "kanji_pos": kanji_pos,
                "kanji_count": len(juku_word),
                "furigana": juku_furigana,
                "edge": "whole",
                "word": juku_word,
                "okurigana": okurigana if juku_at_word_right_edge else "",
            }
            juku_highlight_args: HighlightArgs = {
                "kanji_to_highlight": kanji_to_highlight,
                "kanji_to_match": kanji_to_highlight,
                # Jukujikun processing doesn't need readings, just pass empty strings
                "onyomi": "",
                "kunyomi": "",
                "add_highlight": True,
                "edge": "whole",
            }
            juku_result, juku_okuri, juku_rest_kana = process_jukujikun_reading(
                juku_highlight_args,
                word_data,
                with_tags_def=with_tags_def,
                show_error_message=show_error_message,
            )
            log(f"\nhandle_jukujikun_case - juku_result: {juku_result}")
            reverse_final_furigana = juku_result["text"] + reverse_final_furigana
            if juku_word_pos_to_highlight == "left":
                reverse_final_left_word = juku_word + reverse_final_left_word
            elif juku_word_pos_to_highlight == "right":
                reverse_final_right_word = juku_word + reverse_final_right_word
            elif kanji_pos != -1:
                # Kanji to highlight is in the juku word
                kanji_to_left = juku_word[:kanji_pos]
                kanji_to_right = juku_word[kanji_pos + 1 :]
                highlight_word = kanji_to_highlight
                if kanji_to_right and kanji_to_right[0] == "々":
                    kanji_to_right = kanji_to_right[1:]
                    highlight_word += "々"
                final_edge = juku_result["match_edge"]
                # Correct edge if this was a single kanji juku word
                if len(juku_word) == 1:
                    final_edge = "left" if juku_at_word_left_edge else "right"
                elif reverse_final_right_word and final_edge == "right":
                    # multi-kanji jukujikun, highlight is at the right edge of the juku word
                    # but there's another non-juku word after it, so the final edge is middle
                    final_edge = "middle"
                elif not juku_at_word_left_edge and final_edge == "left":
                    # multi-kanji jukujikun, highlight is at the left edge of the juku word
                    # but there's another non-juku word before it, so the final edge is middle
                    final_edge = "middle"

                log(
                    f"\nreversed handle_jukujikun_case - juku_word: {juku_word}, kanji_to_left:"
                    f" {kanji_to_left}",
                    f" kanji_to_right: {kanji_to_right}, highlight_word: {highlight_word}",
                    f" final_edge: {final_edge}",
                )
                if final_edge == "left":
                    reverse_final_left_word = highlight_word + reverse_final_left_word
                    reverse_final_right_word = kanji_to_right + reverse_final_right_word
                elif final_edge == "right":
                    reverse_final_right_word = highlight_word + reverse_final_right_word
                    reverse_final_left_word = kanji_to_left + reverse_final_left_word
                elif final_edge == "middle":
                    reverse_final_right_word = kanji_to_right + reverse_final_right_word
                    reverse_final_left_word = kanji_to_left + reverse_final_left_word
                    reverse_final_middle_word = highlight_word + reverse_final_middle_word
                else:
                    # whole or kanji in juku word not highlighted
                    reverse_final_middle_word = juku_word + reverse_final_middle_word
            else:
                # No kanji_to_highlight was passed
                reverse_final_left_word = juku_word + reverse_final_left_word

            if not final_okurigana and juku_at_word_right_edge:
                final_okurigana = juku_okuri
                final_rest_kana = juku_rest_kana

        final_result = {
            "furigana": final_furigana + reverse_final_furigana,
            "okurigana": final_okurigana,
            "rest_kana": final_rest_kana,
            "left_word": final_left_word + reverse_final_left_word,
            "middle_word": final_middle_word + reverse_final_middle_word,
            "right_word": final_right_word + reverse_final_right_word,
            "edge": final_edge,
        }
        return reconstruct_furigana(
            final_result,
            with_tags_def=with_tags_def,
            reconstruct_type=return_type,
        )

    # Clean any potential mixed okurigana cases, turning them normal
    clean_text = OKURIGANA_MIX_CLEANING_RE.sub(okurigana_mix_cleaning_replacer, text)
    processed_text = KANJI_AND_FURIGANA_AND_OKURIGANA_REC.sub(furigana_replacer, clean_text)
    # Clean any double spaces that might have been created by the furigana reconstruction
    # Including those right before a <b> tag as the space is added with those
    processed_text = re.sub(r" {2}", " ", processed_text)
    return re.sub(r" <b> ", "<b> ", processed_text)


def test(
    test_name: str,
    kanji: str,
    sentence: str,
    ignore_fail: bool = False,
    assume_dictionary_form: bool = False,
    expected_furigana: Optional[str] = None,
    expected_furigana_with_tags_split: Optional[str] = None,
    expected_furigana_with_tags_merged: Optional[str] = None,
    expected_furikanji: Optional[str] = None,
    expected_furikanji_with_tags_split: Optional[str] = None,
    expected_furikanji_with_tags_merged: Optional[str] = None,
    expected_kana_only: Optional[str] = None,
    expected_kana_only_with_tags_split: Optional[str] = None,
    expected_kana_only_with_tags_merged: Optional[str] = None,
):
    """
    Function that tests the kana_highlight function
    """
    cases: list[Tuple[FuriReconstruct, WithTagsDef, Optional[str]]] = [
        ("furigana", WithTagsDef(False, False, assume_dictionary_form), expected_furigana),
        (
            "furigana",
            WithTagsDef(True, False, assume_dictionary_form),
            expected_furigana_with_tags_split,
        ),
        (
            "furigana",
            WithTagsDef(True, True, assume_dictionary_form),
            expected_furigana_with_tags_merged,
        ),
        ("furikanji", WithTagsDef(False, False, assume_dictionary_form), expected_furikanji),
        (
            "furikanji",
            WithTagsDef(True, False, assume_dictionary_form),
            expected_furikanji_with_tags_split,
        ),
        (
            "furikanji",
            WithTagsDef(True, True, assume_dictionary_form),
            expected_furikanji_with_tags_merged,
        ),
        ("kana_only", WithTagsDef(False, False, assume_dictionary_form), expected_kana_only),
        (
            "kana_only",
            WithTagsDef(True, False, assume_dictionary_form),
            expected_kana_only_with_tags_split,
        ),
        (
            "kana_only",
            WithTagsDef(True, True, assume_dictionary_form),
            expected_kana_only_with_tags_merged,
        ),
    ]
    for return_type, with_tags_def, expected in cases:
        if not expected:
            continue
        result = kana_highlight(kanji, sentence, return_type, with_tags_def)
        try:
            assert result == expected
        except AssertionError:
            if ignore_fail:
                continue
            # Re-run with logging enabled to see what went wrong
            global LOG
            LOG = True
            kana_highlight(
                kanji,
                sentence,
                return_type,
                with_tags_def,
            )
            # Highlight the diff between the expected and the result
            print(f"""\033[91m{test_name}
Return type: {return_type}
{'With tags' if with_tags_def.with_tags else ''}
{'Tags merged' if with_tags_def.merge_consecutive else ''}
\033[93mExpected: {expected}
\033[92mGot:      {result}
\033[0m""")
            # Stop testing here
            sys.exit(0)
        finally:
            LOG = False


def main():
    test(
        test_name="Should not crash with kanji that has empty onyomi or kunyomi",
        kanji="匂",
        # 匂 has no onyomi, 区 has no kunyomi
        sentence="この 区域[くいき]は 匂[にお]いがする。",
        expected_kana_only="この クイキは <b>におい</b>がする。",
        expected_furigana="この 区域[クイキ]は<b> 匂[にお]い</b>がする。",
        expected_furikanji="この クイキ[区域]は<b> にお[匂]い</b>がする。",
        expected_kana_only_with_tags_split=(
            "この <on>ク</on><on>イキ</on>は <b><kun>にお</kun><oku>い</oku></b>がする。"
        ),
        expected_furigana_with_tags_split=(
            "この <on> 区[ク]</on><on> 域[イキ]</on>は <b><kun> 匂[にお]</kun><oku>い</oku></b>がする。"
        ),
        expected_furikanji_with_tags_split=(
            "この <on> ク[区]</on><on> イキ[域]</on>は <b><kun> にお[匂]</kun><oku>い</oku></b>がする。"
        ),
        expected_kana_only_with_tags_merged=(
            "この <on>クイキ</on>は <b><kun>にお</kun><oku>い</oku></b>がする。"
        ),
        expected_furigana_with_tags_merged=(
            "この <on> 区域[クイキ]</on>は <b><kun> 匂[にお]</kun><oku>い</oku></b>がする。"
        ),
        expected_furikanji_with_tags_merged=(
            "この <on> クイキ[区域]</on>は <b><kun> にお[匂]</kun><oku>い</oku></b>がする。"
        ),
    )
    test(
        test_name="Should not incorrectly match onyomi twice 1/",
        kanji="視",
        # しちょうしゃ　has し in it twice but only the first one should be highlighted
        sentence="視聴者[しちょうしゃ]",
        expected_kana_only="<b>シ</b>チョウシャ",
        expected_furigana="<b> 視[シ]</b> 聴者[チョウシャ]",
        expected_furikanji="<b> シ[視]</b> チョウシャ[聴者]",
        expected_kana_only_with_tags_split="<b><on>シ</on></b><on>チョウ</on><on>シャ</on>",
        expected_furigana_with_tags_split="<b><on> 視[シ]</on></b><on> 聴[チョウ]</on><on> 者[シャ]</on>",
        expected_furikanji_with_tags_split="<b><on> シ[視]</on></b><on> チョウ[聴]</on><on> シャ[者]</on>",
        expected_kana_only_with_tags_merged="<b><on>シ</on></b><on>チョウシャ</on>",
        expected_furigana_with_tags_merged="<b><on> 視[シ]</on></b><on> 聴者[チョウシャ]</on>",
        expected_furikanji_with_tags_merged="<b><on> シ[視]</on></b><on> チョウシャ[聴者]</on>",
    )
    test(
        test_name="Should not incorrectly match onyomi twice 2/",
        kanji="儀",
        # ぎょうぎ　has ぎ in it twice but only the first one should be highlighted
        sentence="行儀[ぎょうぎ]",
        expected_kana_only="ギョウ<b>ギ</b>",
        expected_furigana=" 行[ギョウ]<b> 儀[ギ]</b>",
        expected_furikanji=" ギョウ[行]<b> ギ[儀]</b>",
        expected_kana_only_with_tags_split="<on>ギョウ</on><b><on>ギ</on></b>",
        expected_furigana_with_tags_split="<on> 行[ギョウ]</on><b><on> 儀[ギ]</on></b>",
        expected_furikanji_with_tags_split="<on> ギョウ[行]</on><b><on> ギ[儀]</on></b>",
        expected_kana_only_with_tags_merged="<on>ギョウ</on><b><on>ギ</on></b>",
        expected_furigana_with_tags_merged="<on> 行[ギョウ]</on><b><on> 儀[ギ]</on></b>",
        expected_furikanji_with_tags_merged="<on> ギョウ[行]</on><b><on> ギ[儀]</on></b>",
    )
    test(
        test_name="Should not match onyomi in whole edge match 1/",
        kanji="嗜",
        # the onyomi し occurs in the middle of the furigana but should not be matched
        sentence="嗜[たしな]まれたことは？",
        expected_kana_only="<b>たしなまれた</b>ことは？",
        expected_furigana="<b> 嗜[たしな]まれた</b>ことは？",
        expected_furikanji="<b> たしな[嗜]まれた</b>ことは？",
        expected_kana_only_with_tags_split="<b><kun>たしな</kun><oku>まれた</oku></b>ことは？",
        expected_furigana_with_tags_split="<b><kun> 嗜[たしな]</kun><oku>まれた</oku></b>ことは？",
        expected_furikanji_with_tags_split="<b><kun> たしな[嗜]</kun><oku>まれた</oku></b>ことは？",
        expected_kana_only_with_tags_merged="<b><kun>たしな</kun><oku>まれた</oku></b>ことは？",
        expected_furigana_with_tags_merged="<b><kun> 嗜[たしな]</kun><oku>まれた</oku></b>ことは？",
    )
    test(
        test_name="Should match onyomi twice in whole edge match 2/",
        kanji="悠",
        # the onyomi ユウ occurs twice in the furigana and should be matched both times
        sentence="悠々[ゆうゆう]とした時間[じかん]。",
        expected_kana_only="<b>ユウユウ</b>としたジカン。",
        expected_furigana="<b> 悠々[ユウユウ]</b>とした 時間[ジカン]。",
        expected_furikanji="<b> ユウユウ[悠々]</b>とした ジカン[時間]。",
        expected_kana_only_with_tags_split="<b><on>ユウユウ</on></b>とした<on>ジ</on><on>カン</on>。",
        expected_furigana_with_tags_split=(
            "<b><on> 悠々[ユウユウ]</on></b>とした<on> 時[ジ]</on><on> 間[カン]</on>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><on> ユウユウ[悠々]</on></b>とした<on> ジ[時]</on><on> カン[間]</on>。"
        ),
        expected_kana_only_with_tags_merged="<b><on>ユウユウ</on></b>とした<on>ジカン</on>。",
        expected_furigana_with_tags_merged="<b><on> 悠々[ユウユウ]</on></b>とした<on> 時間[ジカン]</on>。",
        expected_furikanji_with_tags_merged="<b><on> ユウユウ[悠々]</on></b>とした<on> ジカン[時間]</on>。",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 1/",
        kanji="去",
        # 消え去[きえさ]った　has え in the middle but った at the end is not included in the furigana
        sentence="団子[だんご]が 消え去[きえさ]った。",
        expected_kana_only="ダンごが きえ<b>さった</b>。",
        expected_furigana=" 団子[ダンご]が 消[き]え<b> 去[さ]った</b>。",
        expected_furikanji=" ダンご[団子]が き[消]え<b> さ[去]った</b>。",
        expected_kana_only_with_tags_split=(
            "<on>ダン</on><kun>ご</kun>が"
            " <kun>き</kun><oku>え</oku><b><kun>さ</kun><oku>った</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 団[ダン]</on><kun> 子[ご]</kun>が <kun> 消[き]</kun><oku>え</oku><b><kun>"
            " 去[さ]</kun><oku>った</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ダン[団]</on><kun> ご[子]</kun>が <kun> き[消]</kun><oku>え</oku><b><kun>"
            " さ[去]</kun><oku>った</oku></b>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>ダン</on><kun>ご</kun>が"
            " <kun>き</kun><oku>え</oku><b><kun>さ</kun><oku>った</oku></b>。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 団[ダン]</on><kun> 子[ご]</kun>が <kun> 消[き]</kun><oku>え</oku><b><kun>"
            " 去[さ]</kun><oku>った</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ダン[団]</on><kun> ご[子]</kun>が <kun> き[消]</kun><oku>え</oku><b><kun>"
            " さ[去]</kun><oku>った</oku></b>。"
        ),
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 2/",
        kanji="隣",
        # 隣り合わせ[となりあわせ]のまち　has り　in the middle and わせ　at the end of the group
        sentence="隣り合わせ[となりあわせ]の町[まち]。",
        expected_kana_only="<b>となり</b>あわせのまち。",
        expected_furigana="<b> 隣[とな]り</b> 合[あ]わせの 町[まち]。",
        expected_furikanji="<b> とな[隣]り</b> あ[合]わせの まち[町]。",
        expected_kana_only_with_tags_split=(
            "<b><kun>とな</kun><oku>り</oku></b><kun>あ</kun><oku>わせ</oku>の<kun>まち</kun>。"
        ),
        expected_furigana_with_tags_split=(
            "<b><kun> 隣[とな]</kun><oku>り</oku></b><kun> 合[あ]</kun><oku>わせ</oku>の"
            "<kun> 町[まち]</kun>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><kun> とな[隣]</kun><oku>り</oku></b><kun> あ[合]</kun><oku>わせ</oku>の"
            "<kun> まち[町]</kun>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><kun>とな</kun><oku>り</oku></b><kun>あ</kun><oku>わせ</oku>の<kun>まち</kun>。"
        ),
        expected_furigana_with_tags_merged=(
            "<b><kun> 隣[とな]</kun><oku>り</oku></b><kun> 合[あ]</kun><oku>わせ</oku>の"
            "<kun> 町[まち]</kun>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><kun> とな[隣]</kun><oku>り</oku></b><kun> あ[合]</kun><oku>わせ</oku>の"
            "<kun> まち[町]</kun>。"
        ),
    )
    test(
        test_name="Matches word that uses the repeater 々 with rendaku 1/",
        kanji="国",
        sentence="国々[くにぐに]の 関係[かんけい]が 深い[ふかい]。",
        expected_kana_only="<b>くにぐに</b>の カンケイが ふかい。",
        expected_furigana="<b> 国々[くにぐに]</b>の 関係[カンケイ]が 深[ふか]い。",
        expected_furikanji="<b> くにぐに[国々]</b>の カンケイ[関係]が ふか[深]い。",
        expected_kana_only_with_tags_split=(
            "<b><kun>くにぐに</kun></b>の <on>カン</on><on>ケイ</on>が <kun>ふか</kun><oku>い</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<b><kun> 国々[くにぐに]</kun></b>の <on> 関[カン]</on><on>"
            " 係[ケイ]</on>が <kun> 深[ふか]</kun><oku>い</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><kun> くにぐに[国々]</kun></b>の <on> カン[関]</on><on>"
            " ケイ[係]</on>が <kun> ふか[深]</kun><oku>い</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><kun>くにぐに</kun></b>の <on>カンケイ</on>が <kun>ふか</kun><oku>い</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<b><kun> 国々[くにぐに]</kun></b>の <on> 関係[カンケイ]</on>が <kun>"
            " 深[ふか]</kun><oku>い</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><kun> くにぐに[国々]</kun></b>の <on> カンケイ[関係]</on>が <kun>"
            " ふか[深]</kun><oku>い</oku>。"
        ),
    )
    test(
        test_name="Matches word that uses the repeater 々 with rendaku 2/",
        kanji="時",
        sentence="時々[ときどき] 雨[あめ]が 降る[ふる]。",
        expected_kana_only="<b>ときどき</b> あめが ふる。",
        expected_furigana="<b> 時々[ときどき]</b> 雨[あめ]が 降[ふ]る。",
        expected_furikanji="<b> ときどき[時々]</b> あめ[雨]が ふ[降]る。",
        expected_kana_only_with_tags_split=(
            "<b><kun>ときどき</kun></b> <kun>あめ</kun>が <kun>ふ</kun><oku>る</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<b><kun> 時々[ときどき]</kun></b> <kun> 雨[あめ]</kun>が <kun>"
            " 降[ふ]</kun><oku>る</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><kun> ときどき[時々]</kun></b> <kun> あめ[雨]</kun>が <kun>"
            " ふ[降]</kun><oku>る</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><kun>ときどき</kun></b> <kun>あめ</kun>が <kun>ふ</kun><oku>る</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<b><kun> 時々[ときどき]</kun></b> <kun> 雨[あめ]</kun>が <kun>"
            " 降[ふ]</kun><oku>る</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><kun> ときどき[時々]</kun></b> <kun> あめ[雨]</kun>が <kun>"
            " ふ[降]</kun><oku>る</oku>。"
        ),
    )
    test(
        test_name="Rendaku test 1/",
        kanji="婦",
        sentence="新婦[しんぷ]",
        expected_kana_only="シン<b>プ</b>",
        expected_furigana=" 新[シン]<b> 婦[プ]</b>",
        expected_furikanji=" シン[新]<b> プ[婦]</b>",
        expected_kana_only_with_tags_split="<on>シン</on><b><on>プ</on></b>",
        expected_furigana_with_tags_split="<on> 新[シン]</on><b><on> 婦[プ]</on></b>",
        expected_furikanji_with_tags_split="<on> シン[新]</on><b><on> プ[婦]</on></b>",
        expected_kana_only_with_tags_merged="<on>シン</on><b><on>プ</on></b>",
        expected_furigana_with_tags_merged="<on> 新[シン]</on><b><on> 婦[プ]</on></b>",
        expected_furikanji_with_tags_merged="<on> シン[新]</on><b><on> プ[婦]</on></b>",
    )
    test(
        test_name="Matches repeater in the middle of the word",
        kanji="菜",
        sentence="娃々菜[わわさい]",
        expected_kana_only="ワワ<b>サイ</b>",
        expected_furigana=" 娃々[ワワ]<b> 菜[サイ]</b>",
        expected_furikanji=" ワワ[娃々]<b> サイ[菜]</b>",
        expected_kana_only_with_tags_split="<on>ワワ</on><b><on>サイ</on></b>",
        expected_furigana_with_tags_split="<on> 娃々[ワワ]</on><b><on> 菜[サイ]</on></b>",
        expected_furikanji_with_tags_split="<on> ワワ[娃々]</on><b><on> サイ[菜]</on></b>",
        expected_kana_only_with_tags_merged="<on>ワワ</on><b><on>サイ</on></b>",
        expected_furigana_with_tags_merged="<on> 娃々[ワワ]</on><b><on> 菜[サイ]</on></b>",
        expected_furikanji_with_tags_merged="<on> ワワ[娃々]</on><b><on> サイ[菜]</on></b>",
    )
    test(
        test_name="Matches word that uses the repeater 々 with small tsu",
        kanji="刻",
        sentence="刻々[こっこく]と 変化[へんか]する。",
        expected_kana_only="<b>コッコク</b>と ヘンカする。",
        expected_furigana="<b> 刻々[コッコク]</b>と 変化[ヘンカ]する。",
        expected_furikanji="<b> コッコク[刻々]</b>と ヘンカ[変化]する。",
        expected_kana_only_with_tags_split="<b><on>コッコク</on></b>と <on>ヘン</on><on>カ</on>する。",
        expected_furigana_with_tags_split=(
            "<b><on> 刻々[コッコク]</on></b>と <on> 変[ヘン]</on><on> 化[カ]</on>する。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><on> コッコク[刻々]</on></b>と <on> ヘン[変]</on><on> カ[化]</on>する。"
        ),
        expected_kana_only_with_tags_merged="<b><on>コッコク</on></b>と <on>ヘンカ</on>する。",
        expected_furigana_with_tags_merged="<b><on> 刻々[コッコク]</on></b>と <on> 変化[ヘンカ]</on>する。",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 3/",
        kanji="止",
        # A third edge case: there is only okurigana at the end
        sentence="歯止め[はどめ]",
        expected_kana_only="は<b>どめ</b>",
        expected_furigana=" 歯[は]<b> 止[ど]め</b>",
        expected_furikanji=" は[歯]<b> ど[止]め</b>",
        expected_kana_only_with_tags_split="<kun>は</kun><b><kun>ど</kun><oku>め</oku></b>",
        expected_furigana_with_tags_split="<kun> 歯[は]</kun><b><kun> 止[ど]</kun><oku>め</oku></b>",
        expected_furikanji_with_tags_split="<kun> は[歯]</kun><b><kun> ど[止]</kun><oku>め</oku></b>",
        expected_kana_only_with_tags_merged="<kun>は</kun><b><kun>ど</kun><oku>め</oku></b>",
        expected_furigana_with_tags_merged="<kun> 歯[は]</kun><b><kun> 止[ど]</kun><oku>め</oku></b>",
        expected_furikanji_with_tags_merged="<kun> は[歯]</kun><b><kun> ど[止]</kun><oku>め</oku></b>",
    )
    test(
        test_name="Is able to match the same kanji occurring twice",
        kanji="閣",
        sentence="新[しん] 内閣[ないかく]の 組閣[そかく]が 発表[はっぴょう]された。",
        expected_kana_only="シン ナイ<b>カク</b>の ソ<b>カク</b>が ハッピョウされた。",
        expected_furigana=(
            " 新[シン] 内[ナイ]<b> 閣[カク]</b>の 組[ソ]<b> 閣[カク]</b>が 発表[ハッピョウ]された。"
        ),
        expected_furikanji=(
            " シン[新] ナイ[内]<b> カク[閣]</b>の ソ[組]<b> カク[閣]</b>が ハッピョウ[発表]された。"
        ),
    )
    test(
        test_name="Is able to match the same kanji occurring twice with other using small tsu",
        kanji="国",
        sentence="その2 国[こく]は 国交[こっこう]を 断絶[だんぜつ]した。",
        expected_kana_only="その2 <b>コク</b>は <b>コッ</b>コウを ダンゼツした。",
        expected_furigana="その2<b> 国[コク]</b>は<b> 国[コッ]</b> 交[コウ]を 断絶[ダンゼツ]した。",
        expected_furikanji="その2<b> コク[国]</b>は<b> コッ[国]</b> コウ[交]を ダンゼツ[断絶]した。",
        expected_kana_only_with_tags_split=(
            "その2 <b><on>コク</on></b>は <b><on>コッ</on></b><on>コウ</on>を"
            " <on>ダン</on><on>ゼツ</on>した。"
        ),
        expected_furigana_with_tags_split=(
            "その2 <b><on> 国[コク]</on></b>は <b><on> 国[コッ]</on></b><on> 交[コウ]</on>を <on>"
            " 断[ダン]</on><on> 絶[ゼツ]</on>した。"
        ),
        expected_furikanji_with_tags_split=(
            "その2 <b><on> コク[国]</on></b>は <b><on> コッ[国]</on></b><on> コウ[交]</on>を <on>"
            " ダン[断]</on><on> ゼツ[絶]</on>した。"
        ),
        expected_kana_only_with_tags_merged=(
            "その2 <b><on>コク</on></b>は <b><on>コッ</on></b><on>コウ</on>を <on>ダンゼツ</on>した。"
        ),
        expected_furigana_with_tags_merged=(
            "その2 <b><on> 国[コク]</on></b>は <b><on> 国[コッ]</on></b><on> 交[コウ]</on>を <on>"
            " 断絶[ダンゼツ]</on>した。"
        ),
        expected_furikanji_with_tags_merged=(
            "その2 <b><on> コク[国]</on></b>は <b><on> コッ[国]</on></b><on> コウ[交]</on>を <on>"
            " ダンゼツ[断絶]</on>した。"
        ),
    )
    test(
        test_name="Is able to pick the right reading when there are multiple matches 1/",
        kanji="靴",
        # ながぐつ　has が (onyomi か match) and ぐつ (kunyomi くつ) as matches
        sentence="お 前[まえ]いつも 長靴[ながぐつ]に 傘[かさ]さしてキメーんだよ！！",
        expected_kana_only="お まえいつも なが<b>ぐつ</b>に かささしてキメーんだよ！！",
        expected_furigana="お 前[まえ]いつも 長[なが]<b> 靴[ぐつ]</b>に 傘[かさ]さしてキメーんだよ！！",
        expected_furikanji="お まえ[前]いつも なが[長]<b> ぐつ[靴]</b>に かさ[傘]さしてキメーんだよ！！",
        expected_kana_only_with_tags_split=(
            "お <kun>まえ</kun>いつも <kun>なが</kun><b><kun>ぐつ</kun></b>に"
            " <kun>かさ</kun>さしてキメーんだよ！！"
        ),
        expected_furigana_with_tags_split=(
            "お <kun> 前[まえ]</kun>いつも <kun> 長[なが]</kun><b><kun> 靴[ぐつ]</kun></b>に"
            " <kun> 傘[かさ]</kun>さしてキメーんだよ！！"
        ),
        expected_furikanji_with_tags_split=(
            "お <kun> まえ[前]</kun>いつも <kun> なが[長]</kun><b><kun> ぐつ[靴]</kun></b>に"
            " <kun> かさ[傘]</kun>さしてキメーんだよ！！"
        ),
        expected_kana_only_with_tags_merged=(
            "お <kun>まえ</kun>いつも <kun>なが</kun><b><kun>ぐつ</kun></b>に"
            " <kun>かさ</kun>さしてキメーんだよ！！"
        ),
        expected_furigana_with_tags_merged=(
            "お <kun> 前[まえ]</kun>いつも <kun> 長[なが]</kun><b><kun> 靴[ぐつ]</kun></b>に"
            " <kun> 傘[かさ]</kun>さしてキメーんだよ！！"
        ),
        expected_furikanji_with_tags_merged=(
            "お <kun> まえ[前]</kun>いつも <kun> なが[長]</kun><b><kun> ぐつ[靴]</kun></b>に"
            " <kun> かさ[傘]</kun>さしてキメーんだよ！！"
        ),
    )
    test(
        test_name="Is able to pick the right reading when there are multiple matches 2/",
        kanji="輸",
        # 輸 has ゆ and しゅ as onyomi readings, should correctly match to the left edge
        sentence="輸出[ゆしゅつ]可能[かのう]。",
        expected_kana_only="<b>ユ</b>シュツカノウ。",
        expected_furigana="<b> 輸[ユ]</b> 出[シュツ] 可能[カノウ]。",
        expected_furikanji="<b> ユ[輸]</b> シュツ[出] カノウ[可能]。",
        expected_kana_only_with_tags_split="<b><on>ユ</on></b><on>シュツ</on><on>カ</on><on>ノウ</on>。",
        expected_furigana_with_tags_split=(
            "<b><on> 輸[ユ]</on></b><on> 出[シュツ]</on><on> 可[カ]</on><on> 能[ノウ]</on>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><on> ユ[輸]</on></b><on> シュツ[出]</on><on> カ[可]</on><on> ノウ[能]</on>。"
        ),
        expected_kana_only_with_tags_merged="<b><on>ユ</on></b><on>シュツ</on><on>カノウ</on>。",
        expected_furigana_with_tags_merged=(
            "<b><on> 輸[ユ]</on></b><on> 出[シュツ]</on><on> 可能[カノウ]</on>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><on> ユ[輸]</on></b><on> シュツ[出]</on><on> カノウ[可能]</on>。"
        ),
    )
    test(
        test_name="Should match reading in 4 kanji compound word",
        kanji="必",
        sentence="見敵必殺[けんてきひっさつ]の 指示[しじ]もないのに 戦闘[せんとう]は 不自然[ふしぜん]。",
        expected_kana_only="ケンテキ<b>ヒッ</b>サツの シジもないのに セントウは フシゼン。",
        expected_furigana=(
            " 見敵[ケンテキ]<b> 必[ヒッ]</b> 殺[サツ]の 指示[シジ]もないのに"
            " 戦闘[セントウ]は 不自然[フシゼン]。"
        ),
        expected_furikanji=(
            " ケンテキ[見敵]<b> ヒッ[必]</b> サツ[殺]の シジ[指示]もないのに"
            " セントウ[戦闘]は フシゼン[不自然]。"
        ),
        expected_kana_only_with_tags_split=(
            "<on>ケン</on><on>テキ</on><b><on>ヒッ</on></b><on>サツ</on>の"
            " <on>シ</on><on>ジ</on>もないのに <on>セン</on><on>トウ</on>は"
            " <on>フ</on><on>シ</on><on>ゼン</on>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 見[ケン]</on><on> 敵[テキ]</on><b><on> 必[ヒッ]</on></b><on> 殺[サツ]</on>の"
            " <on> 指[シ]</on><on> 示[ジ]</on>もないのに <on> 戦[セン]</on><on> 闘[トウ]</on>は"
            " <on> 不[フ]</on><on> 自[シ]</on><on> 然[ゼン]</on>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ケン[見]</on><on> テキ[敵]</on><b><on> ヒッ[必]</on></b><on> サツ[殺]</on>の"
            " <on> シ[指]</on><on> ジ[示]</on>もないのに <on> セン[戦]</on><on> トウ[闘]</on>は"
            " <on> フ[不]</on><on> シ[自]</on><on> ゼン[然]</on>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>ケンテキ</on><b><on>ヒッ</on></b><on>サツ</on>の <on>シジ</on>もないのに"
            " <on>セントウ</on>は <on>フシゼン</on>。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 見敵[ケンテキ]</on><b><on> 必[ヒッ]</on></b><on> 殺[サツ]</on>の"
            " <on> 指示[シジ]</on>もないのに <on> 戦闘[セントウ]</on>は <on> 不自然[フシゼン]</on>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ケンテキ[見敵]</on><b><on> ヒッ[必]</on></b><on> サツ[殺]</on>の"
            " <on> シジ[指示]</on>もないのに <on> セントウ[戦闘]</on>は <on> フシゼン[不自然]</on>。"
        ),
    )
    test(
        test_name="Should match reading in middle of 3 kanji kunyomi compound",
        kanji="馴",
        sentence="幼馴染[おさななじ]みと 久[ひさ]しぶりに 会[あ]った。",
        expected_kana_only="おさな<b>な</b>じみと ひさしぶりに あった。",
        expected_furigana=" 幼[おさな]<b> 馴[な]</b> 染[じ]みと 久[ひさ]しぶりに 会[あ]った。",
        expected_furikanji=" おさな[幼]<b> な[馴]</b> じ[染]みと ひさ[久]しぶりに あ[会]った。",
        expected_kana_only_with_tags_split=(
            "<kun>おさな</kun><b><kun>な</kun></b><kun>じ</kun><oku>み</oku>と"
            " <kun>ひさ</kun><oku>し</oku>ぶりに <kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 幼[おさな]</kun><b><kun> 馴[な]</kun></b><kun> 染[じ]</kun><oku>み</oku>と <kun>"
            " 久[ひさ]</kun><oku>し</oku>ぶりに <kun> 会[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> おさな[幼]</kun><b><kun> な[馴]</kun></b><kun> じ[染]</kun><oku>み</oku>と <kun>"
            " ひさ[久]</kun><oku>し</oku>ぶりに <kun> あ[会]</kun><oku>った</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>おさな</kun><b><kun>な</kun></b><kun>じ</kun><oku>み</oku>と"
            " <kun>ひさ</kun><oku>し</oku>ぶりに <kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 幼[おさな]</kun><b><kun> 馴[な]</kun></b><kun> 染[じ]</kun><oku>み</oku>と <kun>"
            " 久[ひさ]</kun><oku>し</oku>ぶりに <kun> 会[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> おさな[幼]</kun><b><kun> な[馴]</kun></b><kun> じ[染]</kun><oku>み</oku>と <kun>"
            " ひさ[久]</kun><oku>し</oku>ぶりに <kun> あ[会]</kun><oku>った</oku>。"
        ),
    )
    test(
        test_name="Should match furigana for numbers",
        kanji="賊",
        # Note: jpn number
        sentence="海賊[かいぞく]たちは ７[なな]つの 海[うみ]を 航海[こうかい]した。",
        expected_kana_only="カイ<b>ゾク</b>たちは ななつの うみを コウカイした。",
        expected_furigana=" 海[カイ]<b> 賊[ゾク]</b>たちは ７[なな]つの 海[うみ]を 航海[コウカイ]した。",
        expected_furikanji=" カイ[海]<b> ゾク[賊]</b>たちは なな[７]つの うみ[海]を コウカイ[航海]した。",
        expected_kana_only_with_tags_split=(
            "<on>カイ</on><b><on>ゾク</on></b>たちは <kun>なな</kun><oku>つ</oku>の <kun>うみ</kun>を"
            " <on>コウ</on><on>カイ</on>した。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 海[カイ]</on><b><on> 賊[ゾク]</on></b>たちは <kun> ７[なな]</kun><oku>つ</oku>の"
            " <kun>"
            " 海[うみ]</kun>を <on> 航[コウ]</on><on> 海[カイ]</on>した。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> カイ[海]</on><b><on> ゾク[賊]</on></b>たちは <kun> なな[７]</kun><oku>つ</oku>の"
            " <kun>"
            " うみ[海]</kun>を <on> コウ[航]</on><on> カイ[海]</on>した。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>カイ</on><b><on>ゾク</on></b>たちは <kun>なな</kun><oku>つ</oku>の <kun>うみ</kun>を"
            " <on>コウカイ</on>した。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 海[カイ]</on><b><on> 賊[ゾク]</on></b>たちは <kun> ７[なな]</kun><oku>つ</oku>の"
            " <kun>"
            " 海[うみ]</kun>を <on> 航海[コウカイ]</on>した。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> カイ[海]</on><b><on> ゾク[賊]</on></b>たちは <kun> なな[７]</kun><oku>つ</oku>の"
            " <kun>"
            " うみ[海]</kun>を <on> コウカイ[航海]</on>した。"
        ),
    )
    test(
        test_name="Should match the full reading match when there are multiple /1",
        kanji="由",
        # Both ゆ and ゆい are in the furigana but the correct match is ゆい
        sentence="彼女[かのじょ]は 由緒[ゆいしょ]ある 家柄[いえがら]の 出[で]だ。",
        expected_kana_only="かのジョは <b>ユイ</b>ショある いえがらの でだ。",
        expected_furigana=" 彼女[かのジョ]は<b> 由[ユイ]</b> 緒[ショ]ある 家柄[いえがら]の 出[で]だ。",
        expected_furikanji=" かのジョ[彼女]は<b> ユイ[由]</b> ショ[緒]ある いえがら[家柄]の で[出]だ。",
        expected_kana_only_with_tags_split=(
            "<kun>かの</kun><on>ジョ</on>は <b><on>ユイ</on></b><on>ショ</on>ある"
            " <kun>いえ</kun><kun>がら</kun>の <kun>で</kun>だ。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 彼[かの]</kun><on> 女[ジョ]</on>は <b><on> 由[ユイ]</on></b><on>"
            " 緒[ショ]</on>ある <kun> 家[いえ]</kun><kun> 柄[がら]</kun>の <kun>"
            " 出[で]</kun>だ。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> かの[彼]</kun><on> ジョ[女]</on>は <b><on> ユイ[由]</on></b><on>"
            " ショ[緒]</on>ある <kun> いえ[家]</kun><kun> がら[柄]</kun>の <kun>"
            " で[出]</kun>だ。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>かの</kun><on>ジョ</on>は <b><on>ユイ</on></b><on>ショ</on>ある"
            " <kun>いえがら</kun>の <kun>で</kun>だ。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 彼[かの]</kun><on> 女[ジョ]</on>は <b><on> 由[ユイ]</on></b><on>"
            " 緒[ショ]</on>ある <kun> 家柄[いえがら]</kun>の <kun> 出[で]</kun>だ。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> かの[彼]</kun><on> ジョ[女]</on>は <b><on> ユイ[由]</on></b><on>"
            " ショ[緒]</on>ある <kun> いえがら[家柄]</kun>の <kun> で[出]</kun>だ。"
        ),
    )
    test(
        test_name="Should match the full reading match when there are multiple 2/",
        kanji="口",
        # Both ク (on) and くち (kun) are in the furigana but the correct match is くち
        sentence="口紅[くちべに]",
        expected_kana_only="<b>くち</b>べに",
        expected_furigana="<b> 口[くち]</b> 紅[べに]",
        expected_furikanji="<b> くち[口]</b> べに[紅]",
        expected_kana_only_with_tags_split="<b><kun>くち</kun></b><kun>べに</kun>",
        expected_furigana_with_tags_split="<b><kun> 口[くち]</kun></b><kun> 紅[べに]</kun>",
        expected_furikanji_with_tags_split="<b><kun> くち[口]</kun></b><kun> べに[紅]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>くち</kun></b><kun>べに</kun>",
        expected_furigana_with_tags_merged="<b><kun> 口[くち]</kun></b><kun> 紅[べに]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> くち[口]</kun></b><kun> べに[紅]</kun>",
    )
    test(
        test_name="small tsu 1/",
        kanji="剔",
        sentence="剔抉[てっけつ]",
        expected_kana_only="<b>テッ</b>ケツ",
        expected_furigana="<b> 剔[テッ]</b> 抉[ケツ]",
        expected_furikanji="<b> テッ[剔]</b> ケツ[抉]",
        expected_kana_only_with_tags_split="<b><on>テッ</on></b><on>ケツ</on>",
        expected_furigana_with_tags_split="<b><on> 剔[テッ]</on></b><on> 抉[ケツ]</on>",
        expected_furikanji_with_tags_split="<b><on> テッ[剔]</on></b><on> ケツ[抉]</on>",
        expected_kana_only_with_tags_merged="<b><on>テッ</on></b><on>ケツ</on>",
        expected_furigana_with_tags_merged="<b><on> 剔[テッ]</on></b><on> 抉[ケツ]</on>",
        expected_furikanji_with_tags_merged="<b><on> テッ[剔]</on></b><on> ケツ[抉]</on>",
    )
    test(
        test_name="small tsu 2/",
        kanji="一",
        sentence="一見[いっけん]",
        expected_kana_only="<b>イッ</b>ケン",
        expected_furigana="<b> 一[イッ]</b> 見[ケン]",
        expected_furikanji="<b> イッ[一]</b> ケン[見]",
        expected_kana_only_with_tags_split="<b><on>イッ</on></b><on>ケン</on>",
        expected_furigana_with_tags_split="<b><on> 一[イッ]</on></b><on> 見[ケン]</on>",
        expected_furikanji_with_tags_split="<b><on> イッ[一]</on></b><on> ケン[見]</on>",
        expected_kana_only_with_tags_merged="<b><on>イッ</on></b><on>ケン</on>",
        expected_furigana_with_tags_merged="<b><on> 一[イッ]</on></b><on> 見[ケン]</on>",
        expected_furikanji_with_tags_merged="<b><on> イッ[一]</on></b><on> ケン[見]</on>",
    )
    test(
        test_name="small tsu 3/",
        kanji="各",
        sentence="各国[かっこく]",
        expected_kana_only="<b>カッ</b>コク",
        expected_furigana="<b> 各[カッ]</b> 国[コク]",
        expected_furikanji="<b> カッ[各]</b> コク[国]",
        expected_kana_only_with_tags_split="<b><on>カッ</on></b><on>コク</on>",
        expected_furigana_with_tags_split="<b><on> 各[カッ]</on></b><on> 国[コク]</on>",
        expected_furikanji_with_tags_split="<b><on> カッ[各]</on></b><on> コク[国]</on>",
        expected_kana_only_with_tags_merged="<b><on>カッ</on></b><on>コク</on>",
        expected_furigana_with_tags_merged="<b><on> 各[カッ]</on></b><on> 国[コク]</on>",
        expected_furikanji_with_tags_merged="<b><on> カッ[各]</on></b><on> コク[国]</on>",
    )
    test(
        test_name="small tsu 4/",
        kanji="吉",
        sentence="吉兆[きっちょう]",
        expected_kana_only="<b>キッ</b>チョウ",
        expected_furigana="<b> 吉[キッ]</b> 兆[チョウ]",
        expected_furikanji="<b> キッ[吉]</b> チョウ[兆]",
        expected_kana_only_with_tags_split="<b><on>キッ</on></b><on>チョウ</on>",
        expected_furigana_with_tags_split="<b><on> 吉[キッ]</on></b><on> 兆[チョウ]</on>",
        expected_furikanji_with_tags_split="<b><on> キッ[吉]</on></b><on> チョウ[兆]</on>",
        expected_kana_only_with_tags_merged="<b><on>キッ</on></b><on>チョウ</on>",
        expected_furigana_with_tags_merged="<b><on> 吉[キッ]</on></b><on> 兆[チョウ]</on>",
        expected_furikanji_with_tags_merged="<b><on> キッ[吉]</on></b><on> チョウ[兆]</on>",
    )
    test(
        test_name="small tsu 5/",
        kanji="尻",
        # Should be considered a kunyomi match, it's the only instance of お->ぽ conversion
        # with small tsu
        sentence="尻尾[しっぽ]",
        expected_kana_only="<b>しっ</b>ぽ",
        expected_furigana="<b> 尻[しっ]</b> 尾[ぽ]",
        expected_furikanji="<b> しっ[尻]</b> ぽ[尾]",
        expected_kana_only_with_tags_split="<b><kun>しっ</kun></b><kun>ぽ</kun>",
        expected_furigana_with_tags_split="<b><kun> 尻[しっ]</kun></b><kun> 尾[ぽ]</kun>",
        expected_furikanji_with_tags_split="<b><kun> しっ[尻]</kun></b><kun> ぽ[尾]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>しっ</kun></b><kun>ぽ</kun>",
        expected_furigana_with_tags_merged="<b><kun> 尻[しっ]</kun></b><kun> 尾[ぽ]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> しっ[尻]</kun></b><kun> ぽ[尾]</kun>",
    )
    test(
        test_name="small tsu 6/",
        kanji="呆",
        sentence="呆気[あっけ]ない",
        expected_kana_only="<b>あっ</b>ケない",
        expected_furigana="<b> 呆[あっ]</b> 気[ケ]ない",
        expected_furikanji="<b> あっ[呆]</b> ケ[気]ない",
        expected_kana_only_with_tags_split="<b><kun>あっ</kun></b><on>ケ</on>ない",
        expected_furigana_with_tags_split="<b><kun> 呆[あっ]</kun></b><on> 気[ケ]</on>ない",
        expected_furikanji_with_tags_split="<b><kun> あっ[呆]</kun></b><on> ケ[気]</on>ない",
        expected_kana_only_with_tags_merged="<b><kun>あっ</kun></b><on>ケ</on>ない",
        expected_furigana_with_tags_merged="<b><kun> 呆[あっ]</kun></b><on> 気[ケ]</on>ない",
        expected_furikanji_with_tags_merged="<b><kun> あっ[呆]</kun></b><on> ケ[気]</on>ない",
    )
    test(
        test_name="small tsu 7/",
        kanji="甲",
        sentence="甲冑[かっちゅう]の 試着[しちゃく]をお 願[ねが]いします｡",
        expected_kana_only="<b>カッ</b>チュウの シチャクをお ねがいします｡",
        expected_furigana="<b> 甲[カッ]</b> 冑[チュウ]の 試着[シチャク]をお 願[ねが]いします｡",
        expected_furikanji="<b> カッ[甲]</b> チュウ[冑]の シチャク[試着]をお ねが[願]いします｡",
        expected_kana_only_with_tags_split=(
            "<b><on>カッ</on></b><on>チュウ</on>の"
            " <on>シ</on><on>チャク</on>をお <kun>ねが</kun><oku>い</oku>します｡"
        ),
        expected_furigana_with_tags_split=(
            "<b><on> 甲[カッ]</on></b><on> 冑[チュウ]</on>の <on> 試[シ]</on><on>"
            " 着[チャク]</on>をお <kun> 願[ねが]</kun><oku>い</oku>します｡"
        ),
        expected_furikanji_with_tags_split=(
            "<b><on> カッ[甲]</on></b><on> チュウ[冑]</on>の <on> シ[試]</on><on>"
            " チャク[着]</on>をお <kun> ねが[願]</kun><oku>い</oku>します｡"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><on>カッ</on></b><on>チュウ</on>の"
            " <on>シチャク</on>をお <kun>ねが</kun><oku>い</oku>します｡"
        ),
        expected_furigana_with_tags_merged=(
            "<b><on> 甲[カッ]</on></b><on> 冑[チュウ]</on>の <on> 試着[シチャク]</on>をお <kun>"
            " 願[ねが]</kun><oku>い</oku>します｡"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><on> カッ[甲]</on></b><on> チュウ[冑]</on>の <on> シチャク[試着]</on>をお <kun>"
            " ねが[願]</kun><oku>い</oku>します｡"
        ),
    )
    test(
        test_name="small tsu 8/",
        kanji="百",
        sentence="百貨店[ひゃっかてん]",
        expected_kana_only="<b>ヒャッ</b>カテン",
        expected_furigana="<b> 百[ヒャッ]</b> 貨店[カテン]",
        expected_furikanji="<b> ヒャッ[百]</b> カテン[貨店]",
        expected_kana_only_with_tags_split="<b><on>ヒャッ</on></b><on>カ</on><on>テン</on>",
        expected_furigana_with_tags_split="<b><on> 百[ヒャッ]</on></b><on> 貨[カ]</on><on> 店[テン]</on>",
        expected_furikanji_with_tags_split=(
            "<b><on> ヒャッ[百]</on></b><on> カ[貨]</on><on> テン[店]</on>"
        ),
        expected_kana_only_with_tags_merged="<b><on>ヒャッ</on></b><on>カテン</on>",
        expected_furigana_with_tags_merged="<b><on> 百[ヒャッ]</on></b><on> 貨店[カテン]</on>",
        expected_furikanji_with_tags_merged="<b><on> ヒャッ[百]</on></b><on> カテン[貨店]</on>",
    )
    test(
        test_name="small tsu 秘蔵っ子 with う dropped",
        kanji="蔵",
        sentence="秘蔵っ子[ひぞっこ]",
        expected_kana_only="ヒ<b>ゾ</b>っこ",
        expected_furigana=" 秘[ヒ]<b> 蔵[ゾ]</b>っ 子[こ]",
        expected_furikanji=" ヒ[秘]<b> ゾ[蔵]</b>っ こ[子]",
        expected_kana_only_with_tags_split="<on>ヒ</on><b><on>ゾ</on></b>っ<kun>こ</kun>",
        expected_furigana_with_tags_split="<on> 秘[ヒ]</on><b><on> 蔵[ゾ]</on></b>っ<kun> 子[こ]</kun>",
        expected_furikanji_with_tags_split=(
            "<on> ヒ[秘]</on><b><on> ゾ[蔵]</on></b>っ<kun> こ[子]</kun>"
        ),
        expected_kana_only_with_tags_merged="<on>ヒ</on><b><on>ゾ</on></b>っ<kun>こ</kun>",
        expected_furigana_with_tags_merged=(
            "<on> 秘[ヒ]</on><b><on> 蔵[ゾ]</on></b>っ<kun> 子[こ]</kun>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ヒ[秘]</on><b><on> ゾ[蔵]</on></b>っ<kun> こ[子]</kun>"
        ),
    )
    test(
        test_name="small tsu 秘蔵っ子 with う included",
        kanji="蔵",
        sentence="秘蔵っ子[ひぞうっこ]",
        expected_kana_only="ヒ<b>ゾウ</b>っこ",
        expected_furigana=" 秘[ヒ]<b> 蔵[ゾウ]</b>っ 子[こ]",
        expected_furikanji=" ヒ[秘]<b> ゾウ[蔵]</b>っ こ[子]",
        expected_kana_only_with_tags_split="<on>ヒ</on><b><on>ゾウ</on></b>っ<kun>こ</kun>",
        expected_furigana_with_tags_split=(
            "<on> 秘[ヒ]</on><b><on> 蔵[ゾウ]</on></b>っ<kun> 子[こ]</kun>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ヒ[秘]</on><b><on> ゾウ[蔵]</on></b>っ<kun> こ[子]</kun>"
        ),
        expected_kana_only_with_tags_merged="<on>ヒ</on><b><on>ゾウ</on></b>っ<kun>こ</kun>",
        expected_furigana_with_tags_merged=(
            "<on> 秘[ヒ]</on><b><on> 蔵[ゾウ]</on></b>っ<kun> 子[こ]</kun>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ヒ[秘]</on><b><on> ゾウ[蔵]</on></b>っ<kun> こ[子]</kun>"
        ),
    )
    test(
        test_name="small tsu 放[ほ]ったら with う dropped",
        kanji="放",
        sentence="放[ほ]ったらかす",
        expected_kana_only="<b>ほったら</b>かす",
        expected_furigana="<b> 放[ほ]ったら</b>かす",
        expected_furikanji="<b> ほ[放]ったら</b>かす",
        expected_kana_only_with_tags_split="<b><kun>ほ</kun><oku>ったら</oku></b>かす",
        expected_furigana_with_tags_split="<b><kun> 放[ほ]</kun><oku>ったら</oku></b>かす",
        expected_furikanji_with_tags_split="<b><kun> ほ[放]</kun><oku>ったら</oku></b>かす",
        expected_kana_only_with_tags_merged="<b><kun>ほ</kun><oku>ったら</oku></b>かす",
        expected_furigana_with_tags_merged="<b><kun> 放[ほ]</kun><oku>ったら</oku></b>かす",
        expected_furikanji_with_tags_merged="<b><kun> ほ[放]</kun><oku>ったら</oku></b>かす",
    )
    test(
        test_name="small tsu 放[ほ]ったら with う included",
        kanji="放",
        sentence="放[ほう]ったらかす",
        expected_kana_only="<b>ほうったら</b>かす",
        expected_furigana="<b> 放[ほう]ったら</b>かす",
        expected_furikanji="<b> ほう[放]ったら</b>かす",
        expected_kana_only_with_tags_split="<b><kun>ほう</kun><oku>ったら</oku></b>かす",
        expected_furigana_with_tags_split="<b><kun> 放[ほう]</kun><oku>ったら</oku></b>かす",
        expected_furikanji_with_tags_split="<b><kun> ほう[放]</kun><oku>ったら</oku></b>かす",
        expected_kana_only_with_tags_merged="<b><kun>ほう</kun><oku>ったら</oku></b>かす",
        expected_furigana_with_tags_merged="<b><kun> 放[ほう]</kun><oku>ったら</oku></b>かす",
        expected_furikanji_with_tags_merged="<b><kun> ほう[放]</kun><oku>ったら</oku></b>かす",
    )
    test(
        test_name="sound change readings 1/",
        kanji="青",
        # あお -> さお
        sentence="真[ま]っ青[さお]",
        expected_kana_only="まっ<b>さお</b>",
        expected_furigana=" 真[ま]っ<b> 青[さお]</b>",
        expected_furikanji=" ま[真]っ<b> さお[青]</b>",
        expected_kana_only_with_tags_split="<kun>ま</kun>っ<b><kun>さお</kun></b>",
        expected_furigana_with_tags_split="<kun> 真[ま]</kun>っ<b><kun> 青[さお]</kun></b>",
        expected_furikanji_with_tags_split="<kun> ま[真]</kun>っ<b><kun> さお[青]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>ま</kun>っ<b><kun>さお</kun></b>",
        expected_furigana_with_tags_merged="<kun> 真[ま]</kun>っ<b><kun> 青[さお]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> ま[真]</kun>っ<b><kun> さお[青]</kun></b>",
    )
    test(
        test_name="sound change readings 2/",
        kanji="赤",
        # あか -> か
        sentence="真っ赤[まっか]",
        expected_kana_only="まっ<b>か</b>",
        expected_furigana=" 真[ま]っ<b> 赤[か]</b>",
        expected_furikanji=" ま[真]っ<b> か[赤]</b>",
        expected_kana_only_with_tags_split="<kun>ま</kun>っ<b><kun>か</kun></b>",
        expected_furigana_with_tags_split="<kun> 真[ま]</kun>っ<b><kun> 赤[か]</kun></b>",
        expected_furikanji_with_tags_split="<kun> ま[真]</kun>っ<b><kun> か[赤]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>ま</kun>っ<b><kun>か</kun></b>",
        expected_furigana_with_tags_merged="<kun> 真[ま]</kun>っ<b><kun> 赤[か]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> ま[真]</kun>っ<b><kun> か[赤]</kun></b>",
    )
    test(
        test_name="sound change readings 3/",
        kanji="新",
        # あら -> さら
        sentence="真っ新[まっさら]",
        expected_kana_only="まっ<b>さら</b>",
        expected_furigana=" 真[ま]っ<b> 新[さら]</b>",
        expected_furikanji=" ま[真]っ<b> さら[新]</b>",
        expected_kana_only_with_tags_split="<kun>ま</kun>っ<b><kun>さら</kun></b>",
        expected_furigana_with_tags_split="<kun> 真[ま]</kun>っ<b><kun> 新[さら]</kun></b>",
        expected_furikanji_with_tags_split="<kun> ま[真]</kun>っ<b><kun> さら[新]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>ま</kun>っ<b><kun>さら</kun></b>",
        expected_furigana_with_tags_merged="<kun> 真[ま]</kun>っ<b><kun> 新[さら]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> ま[真]</kun>っ<b><kun> さら[新]</kun></b>",
    )
    test(
        test_name="sound change readings 4/",
        kanji="雨",
        # あめ -> さめ
        sentence="春雨[はるさめ]",
        expected_kana_only="はる<b>さめ</b>",
        expected_furigana=" 春[はる]<b> 雨[さめ]</b>",
        expected_furikanji=" はる[春]<b> さめ[雨]</b>",
        expected_kana_only_with_tags_split="<kun>はる</kun><b><kun>さめ</kun></b>",
        expected_furigana_with_tags_split="<kun> 春[はる]</kun><b><kun> 雨[さめ]</kun></b>",
        expected_furikanji_with_tags_split="<kun> はる[春]</kun><b><kun> さめ[雨]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>はる</kun><b><kun>さめ</kun></b>",
        expected_furigana_with_tags_merged="<kun> 春[はる]</kun><b><kun> 雨[さめ]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> はる[春]</kun><b><kun> さめ[雨]</kun></b>",
    )
    test(
        test_name="sound change readings 4/",
        kanji="雨",
        # あめ -> あま
        sentence="雨傘[あまがさ]",
        expected_kana_only="<b>あま</b>がさ",
        expected_furigana="<b> 雨[あま]</b> 傘[がさ]",
        expected_furikanji="<b> あま[雨]</b> がさ[傘]",
        expected_kana_only_with_tags_split="<b><kun>あま</kun></b><kun>がさ</kun>",
        expected_furigana_with_tags_split="<b><kun> 雨[あま]</kun></b><kun> 傘[がさ]</kun>",
        expected_furikanji_with_tags_split="<b><kun> あま[雨]</kun></b><kun> がさ[傘]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>あま</kun></b><kun>がさ</kun>",
        expected_furigana_with_tags_merged="<b><kun> 雨[あま]</kun></b><kun> 傘[がさ]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> あま[雨]</kun></b><kun> がさ[傘]</kun>",
    )
    test(
        test_name="sound change readings 5/",
        kanji="酒",
        # さけ -> さか
        sentence="居酒屋[いざかや]",
        expected_kana_only="い<b>ざか</b>や",
        expected_furigana=" 居[い]<b> 酒[ざか]</b> 屋[や]",
        expected_furikanji=" い[居]<b> ざか[酒]</b> や[屋]",
        expected_kana_only_with_tags_split="<kun>い</kun><b><kun>ざか</kun></b><kun>や</kun>",
        expected_furigana_with_tags_split=(
            "<kun> 居[い]</kun><b><kun> 酒[ざか]</kun></b><kun> 屋[や]</kun>"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> い[居]</kun><b><kun> ざか[酒]</kun></b><kun> や[屋]</kun>"
        ),
        expected_kana_only_with_tags_merged="<kun>い</kun><b><kun>ざか</kun></b><kun>や</kun>",
        expected_furigana_with_tags_merged=(
            "<kun> 居[い]</kun><b><kun> 酒[ざか]</kun></b><kun> 屋[や]</kun>"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> い[居]</kun><b><kun> ざか[酒]</kun></b><kun> や[屋]</kun>"
        ),
    )
    test(
        test_name="sound change readings 6/",
        kanji="応",
        # おう -> のう
        sentence="反応[はんのう]",
        expected_kana_only="ハン<b>ノウ</b>",
        expected_furigana=" 反[ハン]<b> 応[ノウ]</b>",
        expected_furikanji=" ハン[反]<b> ノウ[応]</b>",
        expected_kana_only_with_tags_split="<on>ハン</on><b><on>ノウ</on></b>",
        expected_furigana_with_tags_split="<on> 反[ハン]</on><b><on> 応[ノウ]</on></b>",
        expected_furikanji_with_tags_split="<on> ハン[反]</on><b><on> ノウ[応]</on></b>",
        expected_kana_only_with_tags_merged="<on>ハン</on><b><on>ノウ</on></b>",
        expected_furigana_with_tags_merged="<on> 反[ハン]</on><b><on> 応[ノウ]</on></b>",
        expected_furikanji_with_tags_merged="<on> ハン[反]</on><b><on> ノウ[応]</on></b>",
    )
    test(
        test_name="sound change readings 7/",
        kanji="皇",
        # おう -> のう
        sentence="天皇[てんのう]",
        expected_kana_only="テン<b>ノウ</b>",
        expected_furigana=" 天[テン]<b> 皇[ノウ]</b>",
        expected_furikanji=" テン[天]<b> ノウ[皇]</b>",
        expected_kana_only_with_tags_split="<on>テン</on><b><on>ノウ</on></b>",
        expected_furigana_with_tags_split="<on> 天[テン]</on><b><on> 皇[ノウ]</on></b>",
        expected_furikanji_with_tags_split="<on> テン[天]</on><b><on> ノウ[皇]</on></b>",
        expected_kana_only_with_tags_merged="<on>テン</on><b><on>ノウ</on></b>",
        expected_furigana_with_tags_merged="<on> 天[テン]</on><b><on> 皇[ノウ]</on></b>",
        expected_furikanji_with_tags_merged="<on> テン[天]</on><b><on> ノウ[皇]</on></b>",
    )
    test(
        test_name="sound dropped readings 1/",
        kanji="裸",
        # はだか -> はだ
        sentence="裸足[はだあし]",
        expected_kana_only="<b>はだ</b>あし",
        expected_furigana="<b> 裸[はだ]</b> 足[あし]",
        expected_furikanji="<b> はだ[裸]</b> あし[足]",
        expected_kana_only_with_tags_split="<b><kun>はだ</kun></b><kun>あし</kun>",
        expected_furigana_with_tags_split="<b><kun> 裸[はだ]</kun></b><kun> 足[あし]</kun>",
        expected_furikanji_with_tags_split="<b><kun> はだ[裸]</kun></b><kun> あし[足]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>はだ</kun></b><kun>あし</kun>",
        expected_furigana_with_tags_merged="<b><kun> 裸[はだ]</kun></b><kun> 足[あし]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> はだ[裸]</kun></b><kun> あし[足]</kun>",
    )
    test(
        test_name="sound dropped readings 2/",
        kanji="原",
        # はら -> は
        sentence="河原[かわら]",
        expected_kana_only="かわ<b>ら</b>",
        expected_furigana=" 河[かわ]<b> 原[ら]</b>",
        expected_furikanji=" かわ[河]<b> ら[原]</b>",
        expected_kana_only_with_tags_split="<kun>かわ</kun><b><kun>ら</kun></b>",
        expected_furigana_with_tags_split="<kun> 河[かわ]</kun><b><kun> 原[ら]</kun></b>",
        expected_furikanji_with_tags_split="<kun> かわ[河]</kun><b><kun> ら[原]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>かわ</kun><b><kun>ら</kun></b>",
        expected_furigana_with_tags_merged="<kun> 河[かわ]</kun><b><kun> 原[ら]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> かわ[河]</kun><b><kun> ら[原]</kun></b>",
    )
    test(
        test_name="sound fusion readings 1/",
        kanji="胡",
        # Likely by 黄[き] + 瓜[うり] forming 黄瓜[きゅうり] through sound fusion
        # 胡瓜 is read as きゅうり making 胡[きゅ] techinically jukujikun
        # However, since 瓜[うり] is a normal kunyomi reading, 黄瓜[きゅうり] can't be considered
        # jukujikun, thus we'll note 胡[きゅ] as a kunyomi
        sentence="胡瓜[きゅうり]",
        expected_kana_only="<b>きゅ</b>うり",
        expected_furigana="<b> 胡[きゅ]</b> 瓜[うり]",
        expected_furikanji="<b> きゅ[胡]</b> うり[瓜]",
        expected_kana_only_with_tags_split="<b><kun>きゅ</kun></b><kun>うり</kun>",
        expected_furigana_with_tags_split="<b><kun> 胡[きゅ]</kun></b><kun> 瓜[うり]</kun>",
        expected_furikanji_with_tags_split="<b><kun> きゅ[胡]</kun></b><kun> うり[瓜]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>きゅ</kun></b><kun>うり</kun>",
        expected_furigana_with_tags_merged="<b><kun> 胡[きゅ]</kun></b><kun> 瓜[うり]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> きゅ[胡]</kun></b><kun> うり[瓜]</kun>",
    )
    test(
        test_name="sound fusion readings 2/",
        kanji="狩",
        sentence="狩人[かりゅうど]",
        expected_kana_only="<b>かりゅ</b>うど",
        expected_furigana="<b> 狩[かりゅ]</b> 人[うど]",
        expected_furikanji="<b> かりゅ[狩]</b> うど[人]",
        expected_kana_only_with_tags_split="<b><kun>かりゅ</kun></b><kun>うど</kun>",
        expected_furigana_with_tags_split="<b><kun> 狩[かりゅ]</kun></b><kun> 人[うど]</kun>",
        expected_furikanji_with_tags_split="<b><kun> かりゅ[狩]</kun></b><kun> うど[人]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>かりゅ</kun></b><kun>うど</kun>",
        expected_furigana_with_tags_merged="<b><kun> 狩[かりゅ]</kun></b><kun> 人[うど]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> かりゅ[狩]</kun></b><kun> うど[人]</kun>",
    )
    test(
        test_name="Single kana reading conversion 1/",
        # 祖 usually only lists ソ as the only onyomi
        kanji="祖",
        sentence="先祖[せんぞ]",
        expected_kana_only="セン<b>ゾ</b>",
        expected_furigana=" 先[セン]<b> 祖[ゾ]</b>",
        expected_furikanji=" セン[先]<b> ゾ[祖]</b>",
        expected_kana_only_with_tags_split="<on>セン</on><b><on>ゾ</on></b>",
        expected_furigana_with_tags_split="<on> 先[セン]</on><b><on> 祖[ゾ]</on></b>",
        expected_furikanji_with_tags_split="<on> セン[先]</on><b><on> ゾ[祖]</on></b>",
        expected_kana_only_with_tags_merged="<on>セン</on><b><on>ゾ</on></b>",
        expected_furigana_with_tags_merged="<on> 先[セン]</on><b><on> 祖[ゾ]</on></b>",
        expected_furikanji_with_tags_merged="<on> セン[先]</on><b><on> ゾ[祖]</on></b>",
    )
    test(
        test_name="Single kana reading conversion 2/",
        kanji="来",
        sentence="それは 私[わたし]たちの 日常生活[にちじょうせいかつ]の 仕来[しき]たりの １[ひと]つだ。",
        expected_kana_only="それは わたしたちの ニチジョウセイカツの シ<b>きたり</b>の ひとつだ。",
        expected_furigana=(
            "それは 私[わたし]たちの 日常生活[ニチジョウセイカツ]の 仕[シ]<b>"
            " 来[き]たり</b>の １[ひと]つだ。"
        ),
        expected_furikanji=(
            "それは わたし[私]たちの ニチジョウセイカツ[日常生活]の シ[仕]<b>"
            " き[来]たり</b>の ひと[１]つだ。"
        ),
        expected_kana_only_with_tags_split=(
            "それは <kun>わたし</kun>たちの <on>ニチ</on><on>ジョウ</on><on>セイ</on><on>カツ</on>の "
            "<on>シ</on><b><kun>き</kun><oku>たり</oku></b>の <kun>ひと</kun><oku>つ</oku>だ。"
        ),
        expected_furigana_with_tags_split=(
            "それは <kun> 私[わたし]</kun>たちの <on> 日[ニチ]</on><on> 常[ジョウ]</on><on>"
            " 生[セイ]</on>"
            "<on> 活[カツ]</on>の <on> 仕[シ]</on><b><kun> 来[き]</kun><oku>たり</oku></b>の <kun>"
            " １[ひと]</kun>"
            "<oku>つ</oku>だ。"
        ),
        expected_furikanji_with_tags_split=(
            "それは <kun> わたし[私]</kun>たちの <on> ニチ[日]</on><on> ジョウ[常]</on><on>"
            " セイ[生]</on>"
            "<on> カツ[活]</on>の <on> シ[仕]</on><b><kun> き[来]</kun><oku>たり</oku></b>の <kun>"
            " ひと[１]</kun>"
            "<oku>つ</oku>だ。"
        ),
        expected_kana_only_with_tags_merged=(
            "それは <kun>わたし</kun>たちの <on>ニチジョウセイカツ</on>の"
            " <on>シ</on><b><kun>き</kun><oku>たり</oku></b>の "
            "<kun>ひと</kun><oku>つ</oku>だ。"
        ),
        expected_furigana_with_tags_merged=(
            "それは <kun> 私[わたし]</kun>たちの <on> 日常生活[ニチジョウセイカツ]</on>の"
            " <on> 仕[シ]</on><b><kun> 来[き]</kun><oku>たり</oku></b>の <kun> １[ひと]</kun>"
            "<oku>つ</oku>だ。"
        ),
        expected_furikanji_with_tags_merged=(
            "それは <kun> わたし[私]</kun>たちの <on> ニチジョウセイカツ[日常生活]</on>の"
            " <on> シ[仕]</on><b><kun> き[来]</kun><oku>たり</oku></b>の <kun> ひと[１]</kun>"
            "<oku>つ</oku>だ。"
        ),
    )
    test(
        test_name="jukujikun test 大人 1/",
        kanji="大",
        sentence="大人[おとな] 達[たち]は 大[おお]きいですね",
        expected_kana_only="<b>おと</b>な タチは <b>おおきい</b>ですね",
        expected_furigana="<b> 大[おと]</b> 人[な] 達[タチ]は<b> 大[おお]きい</b>ですね",
        expected_furikanji="<b> おと[大]</b> な[人] タチ[達]は<b> おお[大]きい</b>ですね",
        expected_kana_only_with_tags_split=(
            "<b><juk>おと</juk></b><juk>な</juk> <on>タチ</on>は"
            " <b><kun>おお</kun><oku>きい</oku></b>ですね"
        ),
        expected_furigana_with_tags_split=(
            "<b><juk> 大[おと]</juk></b><juk> 人[な]</juk> <on> 達[タチ]</on>は <b><kun>"
            " 大[おお]</kun><oku>きい</oku></b>ですね"
        ),
        expected_furikanji_with_tags_split=(
            "<b><juk> おと[大]</juk></b><juk> な[人]</juk> <on> タチ[達]</on>は <b><kun>"
            " おお[大]</kun><oku>きい</oku></b>ですね"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><juk>おと</juk></b><juk>な</juk> <on>タチ</on>は"
            " <b><kun>おお</kun><oku>きい</oku></b>ですね"
        ),
        expected_furigana_with_tags_merged=(
            "<b><juk> 大[おと]</juk></b><juk> 人[な]</juk> <on> 達[タチ]</on>は <b><kun>"
            " 大[おお]</kun><oku>きい</oku></b>ですね"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><juk> おと[大]</juk></b><juk> な[人]</juk> <on> タチ[達]</on>は <b><kun>"
            " おお[大]</kun><oku>きい</oku></b>ですね"
        ),
    )
    test(
        test_name="jukujikun test 大人 2/",
        kanji="人",
        sentence="大人[おとな] 達[たち]は 人々[ひとびと]の 中[なか]に いる。",
        expected_kana_only="おと<b>な</b> タチは <b>ひとびと</b>の なかに いる。",
        expected_furigana=" 大[おと]<b> 人[な]</b> 達[タチ]は<b> 人々[ひとびと]</b>の 中[なか]に いる。",
        expected_furikanji=" おと[大]<b> な[人]</b> タチ[達]は<b> ひとびと[人々]</b>の なか[中]に いる。",
        expected_kana_only_with_tags_split=(
            "<juk>おと</juk><b><juk>な</juk></b> <on>タチ</on>は <b><kun>ひとびと</kun></b>の"
            " <kun>なか</kun>に いる。"
        ),
        expected_furigana_with_tags_split=(
            "<juk> 大[おと]</juk><b><juk> 人[な]</juk></b> <on> 達[タチ]</on>は <b><kun>"
            " 人々[ひとびと]</kun></b>"
            "の <kun> 中[なか]</kun>に いる。"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> おと[大]</juk><b><juk> な[人]</juk></b> <on> タチ[達]</on>は <b><kun>"
            " ひとびと[人々]</kun></b>"
            "の <kun> なか[中]</kun>に いる。"
        ),
        expected_kana_only_with_tags_merged=(
            "<juk>おと</juk><b><juk>な</juk></b> <on>タチ</on>は <b><kun>ひとびと</kun></b>の"
            " <kun>なか</kun>に いる。"
        ),
        expected_furigana_with_tags_merged=(
            "<juk> 大[おと]</juk><b><juk> 人[な]</juk></b> <on> 達[タチ]</on>は <b><kun>"
            " 人々[ひとびと]</kun></b>"
            "の <kun> 中[なか]</kun>に いる。"
        ),
        expected_furikanji_with_tags_merged=(
            "<juk> おと[大]</juk><b><juk> な[人]</juk></b> <on> タチ[達]</on>は <b><kun>"
            " ひとびと[人々]</kun></b>"
            "の <kun> なか[中]</kun>に いる。"
        ),
    )
    test(
        test_name="jukujikun test 昨日",
        kanji="展",
        sentence="昨日[きのう]、 絵[え]の 展覧[てんらん] 会[かい]に 行[い]ってきました。",
        expected_kana_only="きのう、 エの <b>テン</b>ラン カイに いってきました。",
        expected_furigana=" 昨日[きのう]、 絵[エ]の<b> 展[テン]</b> 覧[ラン] 会[カイ]に 行[い]ってきました。",
        expected_furikanji=" きのう[昨日]、 エ[絵]の<b> テン[展]</b> ラン[覧] カイ[会]に い[行]ってきました。",
        expected_kana_only_with_tags_split=(
            "<juk>きの</juk><juk>う</juk>、 <on>エ</on>の <b><on>テン</on></b><on>ラン</on>"
            " <on>カイ</on>に <kun>い</kun><oku>って</oku>きました。"
        ),
        expected_furigana_with_tags_split=(
            "<juk> 昨[きの]</juk><juk> 日[う]</juk>、 <on> 絵[エ]</on>の <b><on> 展[テン]</on></b>"
            "<on> 覧[ラン]</on> <on> 会[カイ]</on>に <kun> 行[い]</kun><oku>って</oku>きました。"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> きの[昨]</juk><juk> う[日]</juk>、 <on> エ[絵]</on>の <b><on> テン[展]</on></b>"
            "<on> ラン[覧]</on> <on> カイ[会]</on>に <kun> い[行]</kun><oku>って</oku>きました。"
        ),
        expected_kana_only_with_tags_merged=(
            "<juk>きのう</juk>、 <on>エ</on>の <b><on>テン</on></b><on>ラン</on>"
            " <on>カイ</on>に <kun>い</kun><oku>って</oku>きました。"
        ),
        expected_furigana_with_tags_merged=(
            "<juk> 昨日[きのう]</juk>、 <on> 絵[エ]</on>の <b><on> 展[テン]</on></b>"
            "<on> 覧[ラン]</on> <on> 会[カイ]</on>に <kun> 行[い]</kun><oku>って</oku>きました。"
        ),
        expected_furikanji_with_tags_merged=(
            "<juk> きのう[昨日]</juk>、 <on> エ[絵]</on>の <b><on> テン[展]</on></b>"
            "<on> ラン[覧]</on> <on> カイ[会]</on>に <kun> い[行]</kun><oku>って</oku>きました。"
        ),
    )
    test(
        test_name="jukujikun test with repeater 明々後日",
        kanji="明",
        sentence="明々後日[しあさって]",
        expected_kana_only="<b>しあ</b>さって",
        expected_furigana="<b> 明々[しあ]</b> 後日[さって]",
        expected_furikanji="<b> しあ[明々]</b> さって[後日]",
        expected_kana_only_with_tags_split="<b><juk>しあ</juk></b><juk>さっ</juk><juk>て</juk>",
        expected_furigana_with_tags_split=(
            "<b><juk> 明々[しあ]</juk></b><juk> 後[さっ]</juk><juk> 日[て]</juk>"
        ),
        expected_furikanji_with_tags_split=(
            "<b><juk> しあ[明々]</juk></b><juk> さっ[後]</juk><juk> て[日]</juk>"
        ),
        expected_kana_only_with_tags_merged="<b><juk>しあ</juk></b><juk>さって</juk>",
        expected_furigana_with_tags_merged="<b><juk> 明々[しあ]</juk></b><juk> 後日[さって]</juk>",
        expected_furikanji_with_tags_merged="<b><juk> しあ[明々]</juk></b><juk> さって[後日]</juk>",
    )
    test(
        test_name="jukujikun test 明後日",
        kanji="後",
        # Problem with あ.かり getting kunyoimi match on 明, so the reading is not fully
        # correctly identified as jukujikun
        sentence="明後日[あさって]",
        expected_kana_only="あ<b>さっ</b>て",
        expected_furigana=" 明[あ]<b> 後[さっ]</b> 日[て]",
        expected_furikanji=" あ[明]<b> さっ[後]</b> て[日]",
        expected_kana_only_with_tags_split="<kun>あ</kun><b><juk>さっ</juk></b><juk>て</juk>",
        expected_furigana_with_tags_split=(
            "<kun> 明[あ]</kun><b><juk> 後[さっ]</juk></b><juk> 日[て]</juk>"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> あ[明]</kun><b><juk> さっ[後]</juk></b><juk> て[日]</juk>"
        ),
        expected_kana_only_with_tags_merged="<kun>あ</kun><b><juk>さっ</juk></b><juk>て</juk>",
        expected_furigana_with_tags_merged=(
            "<kun> 明[あ]</kun><b><juk> 後[さっ]</juk></b><juk> 日[て]</juk>"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> あ[明]</kun><b><juk> さっ[後]</juk></b><juk> て[日]</juk>"
        ),
    )
    test(
        ignore_fail=True,
        test_name="jukujikun test 蕎麦 not matched",
        kanji="屋",
        sentence="蕎麦屋[そばや]",
        expected_kana_only="そば<b>や</b>",
        expected_kana_only_with_tags_split="<juk>そ</juk><juk>ば</juk><b><kun>や</kun></b>",
        expected_kana_only_with_tags_merged="<juk>そば</juk><b><kun>や</kun></b>",
    )
    test(
        test_name="jukujikun test 風邪 matched",
        kanji="風",
        # 風 has the kunyomi かぜ, but 風邪 should be read as the jukujikun かぜ
        sentence="風邪[かぜ]",
        expected_kana_only="<b>か</b>ぜ",
        expected_furigana="<b> 風[か]</b> 邪[ぜ]",
        expected_furikanji="<b> か[風]</b> ぜ[邪]",
        expected_kana_only_with_tags_split="<b><juk>か</juk></b><juk>ぜ</juk>",
        expected_furigana_with_tags_split="<b><juk> 風[か]</juk></b><juk> 邪[ぜ]</juk>",
        expected_furikanji_with_tags_split="<b><juk> か[風]</juk></b><juk> ぜ[邪]</juk>",
    )
    test(
        test_name="jukujikun test 風邪 not matched",
        kanji="引",
        # When not matched, jukujikun are automatically merged together
        # This is done intentionally in match_tags_with_kanji.py, so could be changed
        # Kind of makes sense you can't really choose which kanji matches with
        # which part of the furigana
        sentence="風邪[かぜ]を引[ひ]いた。",
        expected_kana_only="かぜを<b>ひいた</b>。",
        expected_furigana=" 風邪[かぜ]を<b> 引[ひ]いた</b>。",
        expected_furikanji=" かぜ[風邪]を<b> ひ[引]いた</b>。",
        expected_kana_only_with_tags_split=(
            "<juk>か</juk><juk>ぜ</juk>を<b><kun>ひ</kun><oku>いた</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<juk> 風[か]</juk><juk> 邪[ぜ]</juk>を<b><kun> 引[ひ]</kun><oku>いた</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> か[風]</juk><juk> ぜ[邪]</juk>を<b><kun> ひ[引]</kun><oku>いた</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<juk>かぜ</juk>を<b><kun>ひ</kun><oku>いた</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<juk> 風邪[かぜ]</juk>を<b><kun> 引[ひ]</kun><oku>いた</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<juk> かぜ[風邪]</juk>を<b><kun> ひ[引]</kun><oku>いた</oku></b>。"
        ),
    )
    test(
        test_name="jukujikun test with other readings after juku word /1",
        kanji="買",
        sentence="風邪薬[かぜぐすり]を買[か]った",
        expected_kana_only="かぜぐすりを<b>かった</b>",
        expected_furigana=" 風邪薬[かぜぐすり]を<b> 買[か]った</b>",
        expected_furikanji=" かぜぐすり[風邪薬]を<b> か[買]った</b>",
        expected_kana_only_with_tags_split=(
            "<juk>か</juk><juk>ぜ</juk><kun>ぐすり</kun>を<b><kun>か</kun><oku>った</oku></b>"
        ),
        expected_furigana_with_tags_split=(
            "<juk> 風[か]</juk><juk> 邪[ぜ]</juk><kun> 薬[ぐすり]</kun>を<b><kun>"
            " 買[か]</kun><oku>った</oku></b>"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> か[風]</juk><juk> ぜ[邪]</juk><kun> ぐすり[薬]</kun>を<b><kun>"
            " か[買]</kun><oku>った</oku></b>"
        ),
        expected_kana_only_with_tags_merged=(
            "<juk>かぜ</juk><kun>ぐすり</kun>を<b><kun>か</kun><oku>った</oku></b>"
        ),
        expected_furigana_with_tags_merged=(
            "<juk> 風邪[かぜ]</juk><kun> 薬[ぐすり]</kun>を<b><kun> 買[か]</kun><oku>った</oku></b>"
        ),
        expected_furikanji_with_tags_merged=(
            "<juk> かぜ[風邪]</juk><kun> ぐすり[薬]</kun>を<b><kun> か[買]</kun><oku>った</oku></b>"
        ),
    )
    test(
        test_name="jukujikun test with other readings after juku word /2",
        kanji="色",
        sentence="薔薇色[ばらいろ]",
        expected_kana_only="ばら<b>いろ</b>",
        expected_furigana=" 薔薇[ばら]<b> 色[いろ]</b>",
        expected_furikanji=" ばら[薔薇]<b> いろ[色]</b>",
        expected_kana_only_with_tags_split="<juk>ば</juk><juk>ら</juk><b><kun>いろ</kun></b>",
        expected_furigana_with_tags_split=(
            "<juk> 薔[ば]</juk><juk> 薇[ら]</juk><b><kun> 色[いろ]</kun></b>"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> ば[薔]</juk><juk> ら[薇]</juk><b><kun> いろ[色]</kun></b>"
        ),
        expected_kana_only_with_tags_merged="<juk>ばら</juk><b><kun>いろ</kun></b>",
        expected_furigana_with_tags_merged="<juk> 薔薇[ばら]</juk><b><kun> 色[いろ]</kun></b>",
        expected_furikanji_with_tags_merged="<juk> ばら[薔薇]</juk><b><kun> いろ[色]</kun></b>",
    )
    test(
        test_name="multi-kanji jukujikun word with other readings after juku word non-matched",
        kanji="目",
        sentence="真面目[まじめ]",
        expected_kana_only="まじ<b>め</b>",
        expected_kana_only_with_tags_split="<juk>ま</juk><juk>じ</juk><b><kun>め</kun></b>",
        expected_kana_only_with_tags_merged="<juk>まじ</juk><b><kun>め</kun></b>",
    )
    test(
        test_name="multi-kanji jukujikun word with other readings after juku word matched left ",
        kanji="真",
        sentence="真面目[まじめ]",
        expected_kana_only="<b>ま</b>じめ",
        expected_kana_only_with_tags_split="<b><juk>ま</juk></b><juk>じ</juk><kun>め</kun>",
        expected_kana_only_with_tags_merged="<b><juk>ま</juk></b><juk>じ</juk><kun>め</kun>",
    )
    test(
        test_name="multi-kanji jukujikun word with other readings after juku word matched right",
        kanji="面",
        sentence="真面目[まじめ]",
        expected_kana_only="ま<b>じ</b>め",
        expected_kana_only_with_tags_split="<juk>ま</juk><b><juk>じ</juk></b><kun>め</kun>",
        expected_kana_only_with_tags_merged="<juk>ま</juk><b><juk>じ</juk></b><kun>め</kun>",
    )
    test(
        test_name="multi-kanji jukujikun verb reading matched left",
        kanji="揶",
        sentence="揶揄[からか]う",
        expected_kana_only="<b>から</b>かう",
        expected_kana_only_with_tags_split="<b><juk>から</juk></b><juk>か</juk>う",
        expected_kana_only_with_tags_merged="<b><juk>から</juk></b><juk>か</juk>う",
    )
    test(
        test_name="multi-kanji jukujikun verb reading matched right",
        kanji="揄",
        sentence="揶揄[からか]う",
        expected_kana_only="から<b>か</b>う",
        expected_kana_only_with_tags_split="<juk>から</juk><b><juk>か</juk></b>う",
        expected_kana_only_with_tags_merged="<juk>から</juk><b><juk>か</juk></b>う",
    )
    test(
        test_name="Should be able to handle vowel change /1",
        kanji="端",
        sentence="端折[はしょ]る",
        expected_kana_only="<b>はし</b>ょる",
        expected_kana_only_with_tags_split="<b><kun>はし</kun></b><kun>ょ</kun><oku>る</oku>",
        expected_kana_only_with_tags_merged="<b><kun>はし</kun></b><kun>ょ</kun><oku>る</oku>",
        expected_furigana="<b> 端[はし]</b> 折[ょ]る",
        expected_furigana_with_tags_split="<b><kun> 端[はし]</kun></b><kun> 折[ょ]</kun><oku>る</oku>",
        expected_furigana_with_tags_merged="<b><kun> 端[はし]</kun></b><kun> 折[ょ]</kun><oku>る</oku>",
        expected_furikanji="<b> はし[端]</b> ょ[折]る",
        expected_furikanji_with_tags_split="<b><kun> はし[端]</kun></b><kun> ょ[折]</kun><oku>る</oku>",
        expected_furikanji_with_tags_merged="<b><kun> はし[端]</kun></b><kun> ょ[折]</kun><oku>る</oku>",
    )
    test(
        test_name="Should be able to get dictionary form okurigana of jukujikun reading",
        kanji="逆",
        # No kunyomi to match, the okurigana would need to be analyzed to get the dictionary form
        # and then determine where the okurigana ends
        sentence="逆上[のぼ]せる",
        # Only dictionary forms can be handled for now
        assume_dictionary_form=True,
        expected_kana_only="<b>の</b>ぼせる",
        expected_furigana="<b> 逆[の]</b> 上[ぼ]せる",
        expected_furikanji="<b> の[逆]</b> ぼ[上]せる",
        expected_kana_only_with_tags_split="<b><juk>の</juk></b><juk>ぼ</juk><oku>せる</oku>",
        expected_furigana_with_tags_split="<b><juk> 逆[の]</juk></b><juk> 上[ぼ]</juk><oku>せる</oku>",
        expected_furikanji_with_tags_split="<b><juk> の[逆]</juk></b><juk> ぼ[上]</juk><oku>せる</oku>",
        expected_kana_only_with_tags_merged="<b><juk>の</juk></b><juk>ぼ</juk><oku>せる</oku>",
        expected_furigana_with_tags_merged="<b><juk> 逆[の]</juk></b><juk> 上[ぼ]</juk><oku>せる</oku>",
        expected_furikanji_with_tags_merged="<b><juk> の[逆]</juk></b><juk> ぼ[上]</juk><oku>せる</oku>",
    )
    test(
        test_name="Should be able to get inflected okurigana of jukujikun reading",
        kanji="逆",
        sentence="逆上[のぼ]せたので",
        # Trying to get the okurigana of the inflected form from jukujikun is too hard
        # for now, ignore
        ignore_fail=True,
        expected_kana_only="<b>の</b>せたので",
        expected_furigana="<b> 逆[の]</b> 上[ぼ]せたので",
        expected_furikanji="<b> の[逆]</b> ぼ[上]せたので",
        expected_kana_only_with_tags_split="<b><juk>の</juk></b><juk>ぼ</juk><oku>せた</oku>ので",
        expected_furigana_with_tags_split=(
            "<b><juk> 逆[の]</juk></b><juk> 上[ぼ]</juk><oku>せた</oku>ので"
        ),
        expected_furikanji_with_tags_split=(
            "<b><juk> の[逆]</juk></b><juk> ぼ[上]</juk><oku>せた</oku>ので"
        ),
        expected_kana_only_with_tags_merged="<b><juk>の</juk></b><juk>ぼせた</juk>ので",
        expected_furigana_with_tags_merged=(
            "<b><juk> 逆[の]</juk></b><juk> 上[ぼ]</juk><oku>せた</oku>ので"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><juk> の[逆]</juk></b><juk> ぼ[上]</juk><oku>せた</oku>ので"
        ),
    )
    test(
        test_name="Should be able match noun form okuriganaless kunyomi reading 1/",
        kanji="曳",
        # ひ.く is a kunyomi for 曳 and both 曳き舟 and 曳船 are valid readings
        sentence="曳船[ひきふね]",
        expected_kana_only="<b>ひき</b>ふね",
        expected_furigana="<b> 曳[ひき]</b> 船[ふね]",
        expected_furikanji="<b> ひき[曳]</b> ふね[船]",
        expected_kana_only_with_tags_split="<b><kun>ひき</kun></b><kun>ふね</kun>",
        expected_furigana_with_tags_split="<b><kun> 曳[ひき]</kun></b><kun> 船[ふね]</kun>",
        expected_furikanji_with_tags_split="<b><kun> ひき[曳]</kun></b><kun> ふね[船]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>ひき</kun></b><kun>ふね</kun>",
        expected_furigana_with_tags_merged="<b><kun> 曳[ひき]</kun></b><kun> 船[ふね]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> ひき[曳]</kun></b><kun> ふね[船]</kun>",
    )
    test(
        test_name="Should be able match noun form okuriganaless kunyomi reading 2/",
        kanji="留",
        sentence="書留[かきとめ]",
        expected_kana_only="かき<b>とめ</b>",
        expected_furigana=" 書[かき]<b> 留[とめ]</b>",
        expected_furikanji=" かき[書]<b> とめ[留]</b>",
        expected_kana_only_with_tags_split="<kun>かき</kun><b><kun>とめ</kun></b>",
        expected_furigana_with_tags_split="<kun> 書[かき]</kun><b><kun> 留[とめ]</kun></b>",
        expected_furikanji_with_tags_split="<kun> かき[書]</kun><b><kun> とめ[留]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>かき</kun><b><kun>とめ</kun></b>",
        expected_furigana_with_tags_merged="<kun> 書[かき]</kun><b><kun> 留[とめ]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> かき[書]</kun><b><kun> とめ[留]</kun></b>",
    )
    test(
        test_name="Should be able to get okurigana of kunyomi reading 1/",
        kanji="置",
        sentence=" 風上[かざかみ]にも 置[お]けない",
        expected_kana_only=" かざかみにも <b>おけない</b>",
        expected_furigana=" 風上[かざかみ]にも<b> 置[お]けない</b>",
        expected_furikanji=" かざかみ[風上]にも<b> お[置]けない</b>",
        expected_kana_only_with_tags_split=(
            " <kun>かざ</kun><kun>かみ</kun>にも <b><kun>お</kun><oku>けない</oku></b>"
        ),
        expected_furigana_with_tags_split=(
            " <kun> 風[かざ]</kun><kun> 上[かみ]</kun>にも <b><kun>"
            " 置[お]</kun><oku>けない</oku></b>"
        ),
        expected_furikanji_with_tags_split=(
            " <kun> かざ[風]</kun><kun> かみ[上]</kun>にも <b><kun>"
            " お[置]</kun><oku>けない</oku></b>"
        ),
        expected_kana_only_with_tags_merged=(
            " <kun>かざかみ</kun>にも <b><kun>お</kun><oku>けない</oku></b>"
        ),
        expected_furigana_with_tags_merged=(
            " <kun> 風上[かざかみ]</kun>にも <b><kun> 置[お]</kun><oku>けない</oku></b>"
        ),
        expected_furikanji_with_tags_merged=(
            " <kun> かざかみ[風上]</kun>にも <b><kun> お[置]</kun><oku>けない</oku></b>"
        ),
    )
    test(
        test_name="Verb okurigana test 1/",
        kanji="来",
        sentence="今[いま]に 来[きた]るべし",
        expected_kana_only="いまに <b>きたる</b>べし",
        expected_furigana=" 今[いま]に<b> 来[きた]る</b>べし",
        expected_furikanji=" いま[今]に<b> きた[来]る</b>べし",
        expected_kana_only_with_tags_split="<kun>いま</kun>に <b><kun>きた</kun><oku>る</oku></b>べし",
        expected_furigana_with_tags_split=(
            "<kun> 今[いま]</kun>に <b><kun> 来[きた]</kun><oku>る</oku></b>べし"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> いま[今]</kun>に <b><kun> きた[来]</kun><oku>る</oku></b>べし"
        ),
        expected_kana_only_with_tags_merged="<kun>いま</kun>に <b><kun>きた</kun><oku>る</oku></b>べし",
        expected_furigana_with_tags_merged=(
            "<kun> 今[いま]</kun>に <b><kun> 来[きた]</kun><oku>る</oku></b>べし"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> いま[今]</kun>に <b><kun> きた[来]</kun><oku>る</oku></b>べし"
        ),
    )
    test(
        test_name="Verb okurigana test 2/",
        kanji="書",
        sentence="日記[にっき]を 書[か]いた。",
        expected_kana_only="ニッキを <b>かいた</b>。",
        expected_furigana=" 日記[ニッキ]を<b> 書[か]いた</b>。",
        expected_furikanji=" ニッキ[日記]を<b> か[書]いた</b>。",
        expected_kana_only_with_tags_split=(
            "<on>ニッ</on><on>キ</on>を <b><kun>か</kun><oku>いた</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 日[ニッ]</on><on> 記[キ]</on>を <b><kun> 書[か]</kun><oku>いた</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ニッ[日]</on><on> キ[記]</on>を <b><kun> か[書]</kun><oku>いた</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<on>ニッキ</on>を <b><kun>か</kun><oku>いた</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<on> 日記[ニッキ]</on>を <b><kun> 書[か]</kun><oku>いた</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ニッキ[日記]</on>を <b><kun> か[書]</kun><oku>いた</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 3/",
        kanji="話",
        sentence="友達[ともだち]と 話[はな]している。",
        expected_kana_only="ともダチと <b>はなして</b>いる。",
        expected_furigana=" 友達[ともダチ]と<b> 話[はな]して</b>いる。",
        expected_furikanji=" ともダチ[友達]と<b> はな[話]して</b>いる。",
        expected_kana_only_with_tags_split=(
            "<kun>とも</kun><on>ダチ</on>と <b><kun>はな</kun><oku>して</oku></b>いる。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 友[とも]</kun><on> 達[ダチ]</on>と <b><kun> 話[はな]</kun><oku>して</oku></b>いる。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> とも[友]</kun><on> ダチ[達]</on>と <b><kun> はな[話]</kun><oku>して</oku></b>いる。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>とも</kun><on>ダチ</on>と <b><kun>はな</kun><oku>して</oku></b>いる。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 友[とも]</kun><on> 達[ダチ]</on>と <b><kun> 話[はな]</kun><oku>して</oku></b>いる。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> とも[友]</kun><on> ダチ[達]</on>と <b><kun> はな[話]</kun><oku>して</oku></b>いる。"
        ),
    )
    test(
        test_name="Verb okurigana test 4/",
        kanji="聞",
        sentence="ニュースを 聞[き]きました。",
        expected_kana_only="ニュースを <b>ききました</b>。",
        expected_furigana="ニュースを<b> 聞[き]きました</b>。",
        expected_furikanji="ニュースを<b> き[聞]きました</b>。",
        expected_kana_only_with_tags_split="ニュースを <b><kun>き</kun><oku>きました</oku></b>。",
        expected_furigana_with_tags_split="ニュースを <b><kun> 聞[き]</kun><oku>きました</oku></b>。",
        expected_furikanji_with_tags_split="ニュースを <b><kun> き[聞]</kun><oku>きました</oku></b>。",
        expected_kana_only_with_tags_merged="ニュースを <b><kun>き</kun><oku>きました</oku></b>。",
        expected_furigana_with_tags_merged="ニュースを <b><kun> 聞[き]</kun><oku>きました</oku></b>。",
        expected_furikanji_with_tags_merged="ニュースを <b><kun> き[聞]</kun><oku>きました</oku></b>。",
    )
    test(
        test_name="Verb okurigana test 5/",
        kanji="走",
        sentence="公園[こうえん]で 走[はし]ろう。",
        expected_kana_only="コウエンで <b>はしろう</b>。",
        expected_furigana=" 公園[コウエン]で<b> 走[はし]ろう</b>。",
        expected_furikanji=" コウエン[公園]で<b> はし[走]ろう</b>。",
        expected_kana_only_with_tags_split=(
            "<on>コウ</on><on>エン</on>で <b><kun>はし</kun><oku>ろう</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 公[コウ]</on><on> 園[エン]</on>で <b><kun> 走[はし]</kun><oku>ろう</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> コウ[公]</on><on> エン[園]</on>で <b><kun> はし[走]</kun><oku>ろう</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<on>コウエン</on>で <b><kun>はし</kun><oku>ろう</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<on> 公園[コウエン]</on>で <b><kun> 走[はし]</kun><oku>ろう</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> コウエン[公園]</on>で <b><kun> はし[走]</kun><oku>ろう</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 6/",
        kanji="待",
        sentence="友達[ともだち]を 待[ま]つ。",
        expected_kana_only="ともダチを <b>まつ</b>。",
        expected_furigana=" 友達[ともダチ]を<b> 待[ま]つ</b>。",
        expected_furikanji=" ともダチ[友達]を<b> ま[待]つ</b>。",
        expected_kana_only_with_tags_split=(
            "<kun>とも</kun><on>ダチ</on>を <b><kun>ま</kun><oku>つ</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 友[とも]</kun><on> 達[ダチ]</on>を <b><kun> 待[ま]</kun><oku>つ</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> とも[友]</kun><on> ダチ[達]</on>を <b><kun> ま[待]</kun><oku>つ</oku></b>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>とも</kun><on>ダチ</on>を <b><kun>ま</kun><oku>つ</oku></b>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 友[とも]</kun><on> 達[ダチ]</on>を <b><kun> 待[ま]</kun><oku>つ</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> とも[友]</kun><on> ダチ[達]</on>を <b><kun> ま[待]</kun><oku>つ</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 7/",
        kanji="泳",
        sentence="海[うみ]で 泳[およ]ぐ。",
        expected_kana_only="うみで <b>およぐ</b>。",
        expected_furigana=" 海[うみ]で<b> 泳[およ]ぐ</b>。",
        expected_furikanji=" うみ[海]で<b> およ[泳]ぐ</b>。",
        expected_kana_only_with_tags_split="<kun>うみ</kun>で <b><kun>およ</kun><oku>ぐ</oku></b>。",
        expected_furigana_with_tags_split=(
            "<kun> 海[うみ]</kun>で <b><kun> 泳[およ]</kun><oku>ぐ</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> うみ[海]</kun>で <b><kun> およ[泳]</kun><oku>ぐ</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<kun>うみ</kun>で <b><kun>およ</kun><oku>ぐ</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<kun> 海[うみ]</kun>で <b><kun> 泳[およ]</kun><oku>ぐ</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> うみ[海]</kun>で <b><kun> およ[泳]</kun><oku>ぐ</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 8/",
        kanji="作",
        sentence="料理[りょうり]を 作[つく]る。",
        expected_kana_only="リョウリを <b>つくる</b>。",
        expected_furigana=" 料理[リョウリ]を<b> 作[つく]る</b>。",
        expected_furikanji=" リョウリ[料理]を<b> つく[作]る</b>。",
        expected_kana_only_with_tags_split=(
            "<on>リョウ</on><on>リ</on>を <b><kun>つく</kun><oku>る</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 料[リョウ]</on><on> 理[リ]</on>を <b><kun> 作[つく]</kun><oku>る</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> リョウ[料]</on><on> リ[理]</on>を <b><kun> つく[作]</kun><oku>る</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<on>リョウリ</on>を <b><kun>つく</kun><oku>る</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<on> 料理[リョウリ]</on>を <b><kun> 作[つく]</kun><oku>る</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> リョウリ[料理]</on>を <b><kun> つく[作]</kun><oku>る</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 9/",
        kanji="遊",
        sentence="子供[こども]と 遊[あそ]んでいるぞ。",
        expected_kana_only="こどもと <b>あそんで</b>いるぞ。",
        expected_furigana=" 子供[こども]と<b> 遊[あそ]んで</b>いるぞ。",
        expected_furikanji=" こども[子供]と<b> あそ[遊]んで</b>いるぞ。",
        expected_kana_only_with_tags_split=(
            "<kun>こ</kun><kun>ども</kun>と <b><kun>あそ</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 子[こ]</kun><kun> 供[ども]</kun>と <b><kun>"
            " 遊[あそ]</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> こ[子]</kun><kun> ども[供]</kun>と <b><kun>"
            " あそ[遊]</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>こども</kun>と <b><kun>あそ</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 子供[こども]</kun>と <b><kun> 遊[あそ]</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> こども[子供]</kun>と <b><kun> あそ[遊]</kun><oku>んで</oku></b>いるぞ。"
        ),
    )
    test(
        test_name="Verb okurigana test 10/",
        kanji="聞",
        # Both 聞く and 聞こえる will produce an okuri match but the correct should be 聞こえる
        sentence="音[おと]を 聞[き]こえたか？何[なに]も 聞[き]いていないよ",
        expected_kana_only="おとを <b>きこえた</b>か？なにも <b>きいて</b>いないよ",
        expected_furigana=" 音[おと]を<b> 聞[き]こえた</b>か？ 何[なに]も<b> 聞[き]いて</b>いないよ",
        expected_furikanji=" おと[音]を<b> き[聞]こえた</b>か？ なに[何]も<b> き[聞]いて</b>いないよ",
        expected_kana_only_with_tags_split=(
            "<kun>おと</kun>を <b><kun>き</kun><oku>こえた</oku></b>か？<kun>なに</kun>も"
            " <b><kun>き</kun><oku>いて</oku></b>いないよ"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 音[おと]</kun>を <b><kun> 聞[き]</kun><oku>こえた</oku></b>か？<kun>"
            " 何[なに]</kun>も"
            " <b><kun> 聞[き]</kun><oku>いて</oku></b>いないよ"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> おと[音]</kun>を <b><kun> き[聞]</kun><oku>こえた</oku></b>か？<kun>"
            " なに[何]</kun>も"
            " <b><kun> き[聞]</kun><oku>いて</oku></b>いないよ"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>おと</kun>を <b><kun>き</kun><oku>こえた</oku></b>か？<kun>なに</kun>も"
            " <b><kun>き</kun><oku>いて</oku></b>いないよ"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 音[おと]</kun>を <b><kun> 聞[き]</kun><oku>こえた</oku></b>か？<kun>"
            " 何[なに]</kun>も"
            " <b><kun> 聞[き]</kun><oku>いて</oku></b>いないよ"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> おと[音]</kun>を <b><kun> き[聞]</kun><oku>こえた</oku></b>か？<kun>"
            " なに[何]</kun>も"
            " <b><kun> き[聞]</kun><oku>いて</oku></b>いないよ"
        ),
    )
    test(
        test_name="Verb okurigana test 11/",
        kanji="抑",
        sentence="俳句[はいく]は 言葉[ことば]が 最小限[さいしょうげん]に 抑[おさ]えられている。",
        expected_kana_only="ハイクは ことばが サイショウゲンに <b>おさえられて</b>いる。",
        expected_furigana=(
            " 俳句[ハイク]は 言葉[ことば]が 最小限[サイショウゲン]に<b> 抑[おさ]えられて</b>いる。"
        ),
        expected_furikanji=(
            " ハイク[俳句]は ことば[言葉]が サイショウゲン[最小限]に<b> おさ[抑]えられて</b>いる。"
        ),
        expected_kana_only_with_tags_split=(
            "<on>ハイ</on><on>ク</on>は <kun>こと</kun><kun>ば</kun>が <on>サイ</on><on>ショウ</on>"
            "<on>ゲン</on>に <b><kun>おさ</kun><oku>えられて</oku></b>いる。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 俳[ハイ]</on><on> 句[ク]</on>は <kun> 言[こと]</kun><kun> 葉[ば]</kun>が <on>"
            " 最[サイ]</on><on>"
            " 小[ショウ]</on><on> 限[ゲン]</on>に <b><kun> 抑[おさ]</kun><oku>えられて</oku></b>いる。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ハイ[俳]</on><on> ク[句]</on>は <kun> こと[言]</kun><kun> ば[葉]</kun>が <on>"
            " サイ[最]</on><on>"
            " ショウ[小]</on><on> ゲン[限]</on>に <b><kun> おさ[抑]</kun><oku>えられて</oku></b>いる。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>ハイク</on>は <kun>ことば</kun>が <on>サイショウゲン</on>に"
            " <b><kun>おさ</kun><oku>えられて</oku></b>いる。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 俳句[ハイク]</on>は <kun> 言葉[ことば]</kun>が <on> 最小限[サイショウゲン]</on>に"
            " <b><kun> 抑[おさ]</kun><oku>えられて</oku></b>いる。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ハイク[俳句]</on>は <kun> ことば[言葉]</kun>が <on> サイショウゲン[最小限]</on>に"
            " <b><kun> おさ[抑]</kun><oku>えられて</oku></b>いる。"
        ),
    )
    test(
        test_name="Verb okurigana test 12/",
        kanji="染",
        sentence="幼馴染[おさななじ]みと 久[ひさ]しぶりに 会[あ]った。",
        expected_kana_only="おさなな<b>じみ</b>と ひさしぶりに あった。",
        expected_furigana=" 幼馴[おさなな]<b> 染[じ]み</b>と 久[ひさ]しぶりに 会[あ]った。",
        expected_furikanji=" おさなな[幼馴]<b> じ[染]み</b>と ひさ[久]しぶりに あ[会]った。",
        expected_kana_only_with_tags_split=(
            "<kun>おさな</kun><kun>な</kun><b><kun>じ</kun><oku>み</oku></b>と"
            " <kun>ひさ</kun><oku>し</oku>ぶりに <kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 幼[おさな]</kun><kun> 馴[な]</kun><b><kun> 染[じ]</kun><oku>み</oku></b>と <kun>"
            " 久[ひさ]</kun><oku>し</oku>ぶりに <kun> 会[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> おさな[幼]</kun><kun> な[馴]</kun><b><kun> じ[染]</kun><oku>み</oku></b>と <kun>"
            " ひさ[久]</kun><oku>し</oku>ぶりに <kun> あ[会]</kun><oku>った</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>おさなな</kun><b><kun>じ</kun><oku>み</oku></b>と <kun>ひさ</kun><oku>し</oku>ぶりに"
            " <kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 幼馴[おさなな]</kun><b><kun> 染[じ]</kun><oku>み</oku></b>と <kun>"
            " 久[ひさ]</kun><oku>し</oku>ぶりに <kun> 会[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> おさなな[幼馴]</kun><b><kun> じ[染]</kun><oku>み</oku></b>と <kun>"
            " ひさ[久]</kun><oku>し</oku>ぶりに <kun> あ[会]</kun><oku>った</oku>。"
        ),
    )
    test(
        test_name="Verb okurigana is gotten correctly when assuming dictionary form/",
        kanji="試",
        assume_dictionary_form=True,
        sentence="試[こころ]みる",
        expected_kana_only="<b>こころみる</b>",
        expected_furigana="<b> 試[こころ]みる</b>",
        expected_furikanji="<b> こころ[試]みる</b>",
        expected_kana_only_with_tags_split="<b><kun>こころ</kun><oku>みる</oku></b>",
        expected_furigana_with_tags_split="<b><kun> 試[こころ]</kun><oku>みる</oku></b>",
        expected_furikanji_with_tags_split="<b><kun> こころ[試]</kun><oku>みる</oku></b>",
    )
    test(
        test_name="Adjective okurigana test 1/",
        kanji="悲",
        sentence="彼[かれ]は 悲[かな]しくすぎるので、 悲[かな]しみの 悲[かな]しさを 悲[かな]しんでいる。",
        expected_kana_only=(
            "かれは <b>かなしく</b>すぎるので、 <b>かなしみ</b>の <b>かなしさ</b>を"
            " <b>かなしんで</b>いる。"
        ),
        expected_furigana=(
            " 彼[かれ]は<b> 悲[かな]しく</b>すぎるので、<b> 悲[かな]しみ</b>の<b>"
            " 悲[かな]しさ</b>を<b> 悲[かな]しんで</b>いる。"
        ),
        expected_furikanji=(
            " かれ[彼]は<b> かな[悲]しく</b>すぎるので、<b> かな[悲]しみ</b>の<b>"
            " かな[悲]しさ</b>を<b> かな[悲]しんで</b>いる。"
        ),
        expected_kana_only_with_tags_split=(
            "<kun>かれ</kun>は <b><kun>かな</kun><oku>しく</oku></b>すぎるので、"
            " <b><kun>かな</kun><oku>しみ</oku></b>の <b><kun>かな</kun><oku>しさ</oku></b>を"
            " <b><kun>かな</kun><oku>しんで</oku></b>いる。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 彼[かれ]</kun>は <b><kun> 悲[かな]</kun><oku>しく</oku></b>すぎるので、 <b><kun>"
            " 悲[かな]</kun><oku>しみ</oku></b>の <b><kun> 悲[かな]</kun><oku>しさ</oku></b>を"
            " <b><kun> 悲[かな]</kun><oku>しんで</oku></b>いる。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> かれ[彼]</kun>は <b><kun> かな[悲]</kun><oku>しく</oku></b>すぎるので、 <b><kun>"
            " かな[悲]</kun><oku>しみ</oku></b>の <b><kun> かな[悲]</kun><oku>しさ</oku></b>を"
            " <b><kun> かな[悲]</kun><oku>しんで</oku></b>いる。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>かれ</kun>は <b><kun>かな</kun><oku>しく</oku></b>すぎるので、"
            " <b><kun>かな</kun><oku>しみ</oku></b>の <b><kun>かな</kun><oku>しさ</oku></b>を"
            " <b><kun>かな</kun><oku>しんで</oku></b>いる。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 彼[かれ]</kun>は <b><kun> 悲[かな]</kun><oku>しく</oku></b>すぎるので、 <b><kun>"
            " 悲[かな]</kun><oku>しみ</oku></b>の <b><kun> 悲[かな]</kun><oku>しさ</oku></b>を"
            " <b><kun> 悲[かな]</kun><oku>しんで</oku></b>いる。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> かれ[彼]</kun>は <b><kun> かな[悲]</kun><oku>しく</oku></b>すぎるので、 <b><kun>"
            " かな[悲]</kun><oku>しみ</oku></b>の <b><kun> かな[悲]</kun><oku>しさ</oku></b>を"
            " <b><kun> かな[悲]</kun><oku>しんで</oku></b>いる。"
        ),
    )
    test(
        test_name="Adjective okurigana test 2/",
        kanji="青",
        sentence="空[そら]が 青[あお]かったら、 青[あお]くない 海[うみ]に 行[い]こう",
        expected_kana_only="そらが <b>あおかったら</b>、 <b>あおくない</b> うみに いこう",
        expected_furigana=" 空[そら]が<b> 青[あお]かったら</b>、<b> 青[あお]くない</b> 海[うみ]に 行[い]こう",
        expected_furikanji=" そら[空]が<b> あお[青]かったら</b>、<b> あお[青]くない</b> うみ[海]に い[行]こう",
        expected_kana_only_with_tags_split=(
            "<kun>そら</kun>が <b><kun>あお</kun><oku>かったら</oku></b>、"
            " <b><kun>あお</kun><oku>くない</oku></b> <kun>うみ</kun>に <kun>い</kun><oku>こう</oku>"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 空[そら]</kun>が <b><kun> 青[あお]</kun><oku>かったら</oku></b>、 <b><kun>"
            " 青[あお]</kun><oku>くない</oku></b> <kun> 海[うみ]</kun>に <kun>"
            " 行[い]</kun><oku>こう</oku>"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> そら[空]</kun>が <b><kun> あお[青]</kun><oku>かったら</oku></b>、 <b><kun>"
            " あお[青]</kun><oku>くない</oku></b> <kun> うみ[海]</kun>に <kun>"
            " い[行]</kun><oku>こう</oku>"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>そら</kun>が <b><kun>あお</kun><oku>かったら</oku></b>、"
            " <b><kun>あお</kun><oku>くない</oku></b> <kun>うみ</kun>に <kun>い</kun><oku>こう</oku>"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 空[そら]</kun>が <b><kun> 青[あお]</kun><oku>かったら</oku></b>、 <b><kun>"
            " 青[あお]</kun><oku>くない</oku></b> <kun> 海[うみ]</kun>に <kun>"
            " 行[い]</kun><oku>こう</oku>"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> そら[空]</kun>が <b><kun> あお[青]</kun><oku>かったら</oku></b>、 <b><kun>"
            " あお[青]</kun><oku>くない</oku></b> <kun> うみ[海]</kun>に <kun>"
            " い[行]</kun><oku>こう</oku>"
        ),
    )
    test(
        test_name="Adjective okurigana test 3/",
        kanji="高",
        sentence="山[やま]が 高[たか]ければ、 高層[こうそう]ビルが 高[たか]めてと 高[たか]ぶり",
        expected_kana_only=(
            "やまが <b>たかければ</b>、 <b>コウ</b>ソウビルが <b>たかめて</b>と <b>たかぶり</b>"
        ),
        expected_furigana=(
            " 山[やま]が<b> 高[たか]ければ</b>、<b> 高[コウ]</b> 層[ソウ]ビルが<b>"
            " 高[たか]めて</b>と<b> 高[たか]ぶり</b>"
        ),
        expected_furikanji=(
            " やま[山]が<b> たか[高]ければ</b>、<b> コウ[高]</b> ソウ[層]ビルが<b>"
            " たか[高]めて</b>と<b> たか[高]ぶり</b>"
        ),
        expected_kana_only_with_tags_split=(
            "<kun>やま</kun>が <b><kun>たか</kun><oku>ければ</oku></b>、"
            " <b><on>コウ</on></b><on>ソウ</on>ビルが <b><kun>たか</kun><oku>めて</oku></b>と"
            " <b><kun>たか</kun><oku>ぶり</oku></b>"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 山[やま]</kun>が <b><kun> 高[たか]</kun><oku>ければ</oku></b>、"
            " <b><on> 高[コウ]</on></b><on> 層[ソウ]</on>ビルが <b><kun>"
            " 高[たか]</kun><oku>めて</oku></b>と"
            " <b><kun> 高[たか]</kun><oku>ぶり</oku></b>"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> やま[山]</kun>が <b><kun> たか[高]</kun><oku>ければ</oku></b>、"
            " <b><on> コウ[高]</on></b><on> ソウ[層]</on>ビルが <b><kun>"
            " たか[高]</kun><oku>めて</oku></b>と"
            " <b><kun> たか[高]</kun><oku>ぶり</oku></b>"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>やま</kun>が <b><kun>たか</kun><oku>ければ</oku></b>、"
            " <b><on>コウ</on></b><on>ソウ</on>ビルが <b><kun>たか</kun><oku>めて</oku></b>と"
            " <b><kun>たか</kun><oku>ぶり</oku></b>"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 山[やま]</kun>が <b><kun> 高[たか]</kun><oku>ければ</oku></b>、"
            " <b><on> 高[コウ]</on></b><on> 層[ソウ]</on>ビルが <b><kun>"
            " 高[たか]</kun><oku>めて</oku></b>と"
            " <b><kun> 高[たか]</kun><oku>ぶり</oku></b>"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> やま[山]</kun>が <b><kun> たか[高]</kun><oku>ければ</oku></b>、"
            " <b><on> コウ[高]</on></b><on> ソウ[層]</on>ビルが <b><kun>"
            " たか[高]</kun><oku>めて</oku></b>と"
            " <b><kun> たか[高]</kun><oku>ぶり</oku></b>"
        ),
    )
    test(
        test_name="Adjective okurigana test 4/",
        kanji="厚",
        sentence="彼[かれ]は 厚かましい[あつかましい]。",
        expected_kana_only="かれは <b>あつかましい</b>。",
        expected_furigana=" 彼[かれ]は<b> 厚[あつ]かましい</b>。",
        expected_furikanji=" かれ[彼]は<b> あつ[厚]かましい</b>。",
        expected_kana_only_with_tags_split="<kun>かれ</kun>は <b><kun>あつ</kun><oku>かましい</oku></b>。",
        expected_furigana_with_tags_split=(
            "<kun> 彼[かれ]</kun>は <b><kun> 厚[あつ]</kun><oku>かましい</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> かれ[彼]</kun>は <b><kun> あつ[厚]</kun><oku>かましい</oku></b>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>かれ</kun>は <b><kun>あつ</kun><oku>かましい</oku></b>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 彼[かれ]</kun>は <b><kun> 厚[あつ]</kun><oku>かましい</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> かれ[彼]</kun>は <b><kun> あつ[厚]</kun><oku>かましい</oku></b>。"
        ),
    )
    test(
        test_name="Adjective okurigana test 5/",
        kanji="恥",
        sentence="恥[は]ずかしげな 顔[かお]で 恥[はじ]を 知[し]らない 振[ふ]りで 恥[は]じらってください。",
        expected_kana_only="<b>はずかし</b>げな かおで <b>はじ</b>を しらない ふりで <b>はじらって</b>ください。",
        expected_furigana=(
            "<b> 恥[は]ずかし</b>げな 顔[かお]で<b> 恥[はじ]</b>を 知[し]らない"
            " 振[ふ]りで<b> 恥[は]じらって</b>ください。"
        ),
        expected_furikanji=(
            "<b> は[恥]ずかし</b>げな かお[顔]で<b> はじ[恥]</b>を し[知]らない"
            " ふ[振]りで<b> は[恥]じらって</b>ください。"
        ),
        expected_kana_only_with_tags_split=(
            "<b><kun>は</kun><oku>ずかし</oku></b>げな <kun>かお</kun>で"
            " <b><kun>はじ</kun></b>を <kun>し</kun><oku>らない</oku>"
            " <kun>ふ</kun><oku>り</oku>で <b><kun>は</kun><oku>じらって</oku></b>ください。"
        ),
        expected_furigana_with_tags_split=(
            "<b><kun> 恥[は]</kun><oku>ずかし</oku></b>げな <kun> 顔[かお]</kun>で <b><kun>"
            " 恥[はじ]</kun></b>を <kun> 知[し]</kun><oku>らない</oku> <kun>"
            " 振[ふ]</kun><oku>り</oku>で <b><kun> 恥[は]</kun><oku>じらって</oku></b>ください。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><kun> は[恥]</kun><oku>ずかし</oku></b>げな <kun> かお[顔]</kun>で <b><kun>"
            " はじ[恥]</kun></b>を <kun> し[知]</kun><oku>らない</oku> <kun>"
            " ふ[振]</kun><oku>り</oku>で <b><kun> は[恥]</kun><oku>じらって</oku></b>"
            "ください。"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><kun>は</kun><oku>ずかし</oku></b>げな <kun>かお</kun>で"
            " <b><kun>はじ</kun></b>を <kun>し</kun><oku>らない</oku>"
            " <kun>ふ</kun><oku>り</oku>で <b><kun>は</kun><oku>じらって</oku></b>ください。"
        ),
        expected_furigana_with_tags_merged=(
            "<b><kun> 恥[は]</kun><oku>ずかし</oku></b>げな <kun> 顔[かお]</kun>で <b><kun>"
            " 恥[はじ]</kun></b>を <kun> 知[し]</kun><oku>らない</oku> <kun>"
            " 振[ふ]</kun><oku>り</oku>で <b><kun> 恥[は]</kun><oku>じらって</oku></b>ください。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><kun> は[恥]</kun><oku>ずかし</oku></b>げな <kun> かお[顔]</kun>で <b><kun>"
            " はじ[恥]</kun></b>を <kun> し[知]</kun><oku>らない</oku> <kun>"
            " ふ[振]</kun><oku>り</oku>で <b><kun> は[恥]</kun><oku>じらって</oku></b>ください。"
        ),
    )
    test(
        test_name="numbers of people /1",
        kanji="一",
        sentence="一人[ひとり]",
        expected_kana_only="<b>ひと</b>り",
        expected_furigana="<b> 一[ひと]</b> 人[り]",
        expected_furikanji="<b> ひと[一]</b> り[人]",
        expected_kana_only_with_tags_split="<b><kun>ひと</kun></b><kun>り</kun>",
        expected_furigana_with_tags_split="<b><kun> 一[ひと]</kun></b><kun> 人[り]</kun>",
        expected_furikanji_with_tags_split="<b><kun> ひと[一]</kun></b><kun> り[人]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>ひと</kun></b><kun>り</kun>",
        expected_furigana_with_tags_merged="<b><kun> 一[ひと]</kun></b><kun> 人[り]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> ひと[一]</kun></b><kun> り[人]</kun>",
    )
    test(
        test_name="numbers of people /2",
        kanji="沁",
        sentence="二人[ふたり]でしみじみと 語り合[かたりあ]った。",
        expected_kana_only="ふたりでしみじみと かたりあった。",
        expected_furigana=" 二人[ふたり]でしみじみと 語[かた]り 合[あ]った。",
        expected_furikanji=" ふたり[二人]でしみじみと かた[語]り あ[合]った。",
        expected_kana_only_with_tags_split=(
            "<kun>ふた</kun><kun>り</kun>でしみじみと"
            " <kun>かた</kun><oku>り</oku><kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 二[ふた]</kun><kun> 人[り]</kun>でしみじみと <kun>"
            " 語[かた]</kun><oku>り</oku><kun> 合[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> ふた[二]</kun><kun> り[人]</kun>でしみじみと <kun>"
            " かた[語]</kun><oku>り</oku><kun> あ[合]</kun><oku>った</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>ふたり</kun>でしみじみと <kun>かた</kun><oku>り</oku><kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 二人[ふたり]</kun>でしみじみと <kun> 語[かた]</kun><oku>り</oku><kun>"
            " 合[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> ふたり[二人]</kun>でしみじみと <kun> かた[語]</kun><oku>り</oku><kun>"
            " あ[合]</kun><oku>った</oku>。"
        ),
    )
    test(
        test_name="numbers of people /3",
        kanji="三",
        sentence="三人[さんにん]",
        expected_kana_only="<b>サン</b>ニン",
        expected_furigana="<b> 三[サン]</b> 人[ニン]",
        expected_furikanji="<b> サン[三]</b> ニン[人]",
        expected_kana_only_with_tags_split="<b><on>サン</on></b><on>ニン</on>",
        expected_furigana_with_tags_split="<b><on> 三[サン]</on></b><on> 人[ニン]</on>",
        expected_furikanji_with_tags_split="<b><on> サン[三]</on></b><on> ニン[人]</on>",
        expected_kana_only_with_tags_merged="<b><on>サン</on></b><on>ニン</on>",
        expected_furigana_with_tags_merged="<b><on> 三[サン]</on></b><on> 人[ニン]</on>",
        expected_furikanji_with_tags_merged="<b><on> サン[三]</on></b><on> ニン[人]</on>",
    )
    test(
        test_name="生 readings /1",
        kanji="生",
        sentence="生粋[きっすい]",
        expected_kana_only="<b>きっ</b>スイ",
        expected_furigana="<b> 生[きっ]</b> 粋[スイ]",
        expected_furikanji="<b> きっ[生]</b> スイ[粋]",
        expected_kana_only_with_tags_split="<b><kun>きっ</kun></b><on>スイ</on>",
        expected_furigana_with_tags_split="<b><kun> 生[きっ]</kun></b><on> 粋[スイ]</on>",
        expected_furikanji_with_tags_split="<b><kun> きっ[生]</kun></b><on> スイ[粋]</on>",
        expected_kana_only_with_tags_merged="<b><kun>きっ</kun></b><on>スイ</on>",
        expected_furigana_with_tags_merged="<b><kun> 生[きっ]</kun></b><on> 粋[スイ]</on>",
        expected_furikanji_with_tags_merged="<b><kun> きっ[生]</kun></b><on> スイ[粋]</on>",
    )
    test(
        test_name="生 readings /2",
        kanji="生",
        sentence="生地[きじ]",
        expected_kana_only="<b>き</b>ジ",
        expected_furigana="<b> 生[き]</b> 地[ジ]",
        expected_furikanji="<b> き[生]</b> ジ[地]",
        expected_kana_only_with_tags_split="<b><kun>き</kun></b><on>ジ</on>",
        expected_furigana_with_tags_split="<b><kun> 生[き]</kun></b><on> 地[ジ]</on>",
        expected_furikanji_with_tags_split="<b><kun> き[生]</kun></b><on> ジ[地]</on>",
        expected_kana_only_with_tags_merged="<b><kun>き</kun></b><on>ジ</on>",
        expected_furigana_with_tags_merged="<b><kun> 生[き]</kun></b><on> 地[ジ]</on>",
        expected_furikanji_with_tags_merged="<b><kun> き[生]</kun></b><on> ジ[地]</on>",
    )
    test(
        test_name="生 readings /3",
        kanji="生",
        sentence="弥生[やよい]",
        expected_kana_only="や<b>よい</b>",
        expected_kana_only_with_tags_split="<kun>や</kun><b><kun>よい</kun></b>",
        expected_kana_only_with_tags_merged="<kun>や</kun><b><kun>よい</kun></b>",
    )
    test(
        test_name="生 readings /4",
        kanji="生",
        sentence="芝生[しばふ]",
        expected_kana_only="しば<b>ふ</b>",
        expected_kana_only_with_tags_split="<kun>しば</kun><b><kun>ふ</kun></b>",
        expected_kana_only_with_tags_merged="<kun>しば</kun><b><kun>ふ</kun></b>",
    )
    test(
        test_name="生 readings /5",
        kanji="生",
        sentence="生憎[あいにく]",
        expected_kana_only="<b>あい</b>にく",
        expected_kana_only_with_tags_split="<b><kun>あい</kun></b><kun>にく</kun>",
        expected_kana_only_with_tags_merged="<b><kun>あい</kun></b><kun>にく</kun>",
    )
    print("\n\033[92mTests passed\033[0m")


if __name__ == "__main__":
    main()
