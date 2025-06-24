from functools import partial
import re
import json
import os
from typing import TypedDict, Literal, Optional, Tuple, NamedTuple, cast, Union

from .jpn_text_processing.number_to_kanji import NUMBER_TO_KANJI, number_to_kanji
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

try:
    from ..utils.logger import Logger
except ImportError:
    from utils.logger import Logger  # type: ignore[no-redef]


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

SMALL_TSU_POSSIBLE_HIRAGANA = ["つ", "ち", "く", "き", "り", "ん", "う"]

HIRAGANA_RE = "([ぁ-ん])"

# Palatilized (拗音) mora and other non-straight mora
PALATALIZED_MORA = [
    "くぃ",
    "きゃ",
    "きゅ",
    "きぇ",
    "きょ",
    "ぐぃ",
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
    "ゔぇ",
    "ゔぉ",
    "ぬぃ",
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
]

SINGLE_KANA_MORA = [
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
    "と",
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

# Elongated vowels of the single kana mora (直音)
LONG_STRAIGHT_MORA = [f"{kana}ー" for kana in SINGLE_KANA_MORA]

# First all two kana more, so they get matched first, then the single kana mora
ALL_MORA = (
    PALATALIZED_MORA
    + LONG_STRAIGHT_MORA
    + SINGLE_KANA_MORA
    + [
        "ん",
    ]
)

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

# Text that contains any kanji repeated, to be replaced by the kanji+々
DOUBLE_KANJI_RE = r"([\u4e00-\u9faf\u3400-\u4dbf])\1"
DOUBLE_KANJI_REC = re.compile(DOUBLE_KANJI_RE)

KANJI_AND_REPEATER_RE = r"([\u4e00-\u9faf\u3400-\u4dbf]々)"
KANJI_AND_REPEATER_REC = re.compile(KANJI_AND_REPEATER_RE)

# Regex matching any kanji and furigana + hiragana after the furigana
KANJI_AND_FURIGANA_AND_OKURIGANA_RE = r"([\d々\u4e00-\u9faf\u3400-\u4dbf]+)\[(.+?)\]([ぁ-ん]*)"
KANJI_AND_FURIGANA_AND_OKURIGANA_REC = re.compile(KANJI_AND_FURIGANA_AND_OKURIGANA_RE)

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
    kanji_to_highlight: Optional[str]
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
    logger: Logger = Logger("error"),
) -> FuriganaParts:
    logger.debug(f"get_furigana_parts - furigana: {furigana}, edge: {edge}")
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
        logger.debug(
            f"get_furigana_parts - middle match: {match.groups()}, edge was correct:"
            f" {edge == 'middle'}"
        )
        result["left_furigana"] = match.group(1)
        result["middle_furigana"] = match.group(2)
        result["right_furigana"] = match.group(3)
        result["matched_edge"] = "middle"
        return result
    elif match := REPLACED_FURIGANA_RIGHT_RE.match(furigana):
        logger.debug(
            f"get_furigana_parts - right match: {match.groups()}, edge was correct:"
            f" {edge == 'right'}"
        )
        result["left_furigana"] = match.group(1)
        result["middle_furigana"] = None
        result["right_furigana"] = match.group(2)
        result["matched_edge"] = "right"
        return result
    elif match := REPLACED_FURIGANA_LEFT_RE.match(furigana):
        logger.debug(
            f"get_furigana_parts - left match: {match.groups()}, edge was correct: {edge == 'left'}"
        )
        result["left_furigana"] = match.group(1)
        result["middle_furigana"] = None
        result["right_furigana"] = match.group(2)
        result["matched_edge"] = "left"
        return result

    # Nothing matched
    logger.debug("\nget_furigana_parts - no match")
    return result


def reconstruct_furigana(
    furi_okuri_result: FinalResult,
    with_tags_def: WithTagsDef,
    reconstruct_type: FuriReconstruct = "furigana",
    force_merge: bool = False,
    logger: Logger = Logger("error"),
) -> str:
    """
    Reconstruct the furigana from the replace result

    :return: The reconstructed furigana with the kanji and that kanji's furigana highlighted
    """
    logger.debug(
        f"reconstruct_furigana - final_result: {furi_okuri_result}, reconstruct_type:"
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

    furigana_parts = get_furigana_parts(furigana, edge, logger=logger)
    logger.debug(f"reconstruct_furigana edge: {edge}, furigana_parts: {furigana_parts}")

    has_highlight = furigana_parts.get("has_highlight")
    left_furigana = furigana_parts.get("left_furigana")
    middle_furigana = furigana_parts.get("middle_furigana")
    right_furigana = furigana_parts.get("right_furigana")
    edge = furigana_parts.get("matched_edge")

    if not has_highlight:
        logger.debug("\nreconstruct_furigana - no highlight")
        # There was no match found during onyomi and kunyomi processing, so no<b> tags
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
            elif force_merge:
                if with_tags_def.with_tags:
                    okurigana = f"<oku>{okurigana}</oku>" if okurigana else ""
                if reconstruct_type == "kana_only":
                    if not with_tags_def.with_tags:
                        furigana = re.sub(r"<\w+>|</\w+>", "", furigana)
                    # If we're in kana_only mode, we just return the furigana
                    wrapped_whole_word = f"{furigana}{okurigana}{rest_kana}"
                else:
                    # Just merge the whole word with the furigana
                    # remove all tags from furigana and wrap everything with <mix> tags
                    furigana = re.sub(r"<\w+>|</\w+>", "", furigana)
                    whole_word = f"{left_word}{middle_word}{right_word}"
                    if with_tags_def.with_tags:
                        if reconstruct_type == "furigana":
                            wrapped_whole_word = f"<mix> {whole_word}[{furigana}]</mix>"
                        elif reconstruct_type == "furikanji":
                            wrapped_whole_word = f"<mix> {furigana}[{whole_word}]</mix>"
                    else:
                        if reconstruct_type == "furigana":
                            wrapped_whole_word = f" {whole_word}[{furigana}]"
                        elif reconstruct_type == "furikanji":
                            wrapped_whole_word = f" {furigana}[{whole_word}]"
                    wrapped_whole_word += okurigana + rest_kana
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

            logger.debug(
                f"reconstruct_furigana - whole_word: {left_word}{middle_word}{right_word},"
                f" furigana: {furigana}, wrapped_whole_word: {wrapped_whole_word}"
            )
            okurigana = f"<oku>{okurigana}</oku>" if okurigana else ""
            return f"{wrapped_whole_word}{okurigana}{rest_kana}"
        if reconstruct_type == "furikanji":
            return f" {furigana}[{left_word}{middle_word}{right_word}]{okurigana}{rest_kana}"
        return f" {left_word}{middle_word}{right_word}[{furigana}]{okurigana}{rest_kana}"

    if edge == "whole":
        # Same as above except we add the<b> tags around the whole thing
        # First remove<b> tags from the furigana
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
        logger.debug(
            f"reconstruct_furigana - word: {word}, word_furigana: {word_furigana},"
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
    logger: Logger = Logger("error"),
) -> Union[ReadingProcessResult, None]:
    """
    Function that processes furigana by checking all possible onyomi and kunyomi readings on it
    Either returns the furigana as-is when there is no match or modifies the furigana by
    adding<b> tags around the part that matches the reading

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
        logger,
    )
    logger.debug(
        f"process_readings - highlight_args: {highlight_args}, word_data: {word_data},"
        f" target_furigana_section: {target_furigana_section}, furigana: {furigana}, edge: {edge},"
        f" process_type: {process_type}, with_tags_def: {with_tags_def}"
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
        logger=logger,
    )
    onyomi_process_result = None
    if onyomi_match["type"] == "onyomi":
        onyomi_process_result = ReadingProcessResult(onyomi_match, "", maybe_okuri)

    logger.debug(
        f"onyomi_process_result: {onyomi_process_result}, word_data: {word_data},"
        f" kana_highlight: {highlight_args}"
    )
    kunyomi_results = check_kunyomi_readings(
        highlight_args,
        word_data,
        furigana,
        target_furigana_section,
        edge,
        process_type=process_type,
        wrap_readings_with_tags=with_tags_def.with_tags,
        logger=logger,
    )
    kunyomi_process_result = None
    kanji_count = word_data.get("kanji_count", 0)
    kanji_pos = word_data.get("kanji_pos", None)
    next_kanji_in_word_is_repeater = (
        kanji_pos is not None
        and kanji_pos + 1 < kanji_count
        and word_data["word"][kanji_pos + 1] == "々"
    )
    logger.debug(
        f"kunyomi_results: {kunyomi_results}, word_data: {word_data}, kana_highlight:"
        f" {highlight_args}, next_kanji_in_word_is_repeater:"
        f" {next_kanji_in_word_is_repeater}"
    )
    if (
        not with_tags_def.assume_dictionary_form
        and kunyomi_results["type"] == "kunyomi"
        and (
            word_data["edge"] in ["right", "whole"]
            or (word_data["edge"] == "left" and next_kanji_in_word_is_repeater)
        )
    ):
        kunyomi = highlight_args.get("kunyomi", "")
        okurigana_to_highlight = ""
        partial_okuri_results: list[OkuriResults] = []
        rest_kana = maybe_okuri
        kunyomi_readings = iter(kunyomi.split("、"))
        matched_kunyomi_stem = kunyomi_results["matched_reading"].split(".")[0]
        logger.debug(f"check_kunyomi_readings - matched_kunyomi_stem: {matched_kunyomi_stem}")
        while not okurigana_to_highlight and (next_kunyomi := next(kunyomi_readings, None)):
            logger.debug(
                f"check_kunyomi_readings - okurigana: {not okurigana_to_highlight},"
                f" next_kunyomi: {next_kunyomi}"
            )
            try:
                logger.debug(f"check_kunyomi_readings while - next_kunyomi: {next_kunyomi}")
                kunyomi_reading, kunyomi_okurigana = next_kunyomi.split(".")
            except ValueError:
                logger.debug("check_kunyomi_readings while - non okuri reading, skipping")
                continue
            # The reading stems must match
            if kunyomi_reading != matched_kunyomi_stem:
                logger.debug(f"check_kunyomi_readings while - non-matching stem: {kunyomi_reading}")
                continue
            res = check_okurigana_for_kunyomi_inflection(
                kunyomi_okurigana, kunyomi_reading, word_data, highlight_args, logger
            )
            logger.debug(f"check_kunyomi_readings while - check_okurigana result: {res}")
            if res.result in ["partial_okuri", "empty_okuri"]:
                # If we only got a partial or empty okurigana match, continue looking
                # in case we get a full match instead
                partial_okuri_results.append(res)
                logger.debug(
                    "\ncheck_kunyomi_readings while got a partial result:"
                    f" {res.okurigana}, rest_kana: {res.okurigana}, type: {res.result}"
                )
                continue
            if res.result == "full_okuri":
                logger.debug(
                    f"check_kunyomi_readings while got a full_okuri: {res.okurigana},"
                    f" rest_kana: {res.rest_kana}"
                )
                okurigana_to_highlight = res.okurigana
                rest_kana = res.rest_kana
        # If multiple partial okuri results were found, use the one that matches the most
        if partial_okuri_results and not okurigana_to_highlight:
            logger.debug(
                f"check_kunyomi_readings while got {len(partial_okuri_results)} partial results"
            )
            best_res = max(partial_okuri_results, key=lambda x: len(x.okurigana))
            logger.debug(
                f"check_kunyomi_readings while final partial_okuri: {best_res.okurigana},"
                f" rest_kana: {best_res.rest_kana}, type: {best_res.result}"
            )
            okurigana_to_highlight = best_res.okurigana
            rest_kana = best_res.rest_kana
        logger.debug(
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
            logger.debug("\nassuming dictionary form - kunyomi_process_result with okurigana")
            kunyomi_process_result = ReadingProcessResult(kunyomi_results, maybe_okuri, "")
        # Ohterwise, we can only assume its rest_kana
        else:
            logger.debug("\nnot assuming dictionary form - kunyomi_process_result with rest_kana")
            kunyomi_process_result = ReadingProcessResult(kunyomi_results, "", maybe_okuri)

    # Compare the onyomi and kunyomi results and return the one that matched the most
    if onyomi_process_result and kunyomi_process_result:
        on_length = len(onyomi_process_result.yomi_match["matched_reading"])
        kun_length = len(kunyomi_process_result.yomi_match["matched_reading"].split(".")[0])
        logger.debug(
            "\nfound both onyomi and kunyomi - on_match:"
            f" {onyomi_process_result.yomi_match['matched_reading']}, kun_match:"
            f" {kunyomi_process_result.yomi_match['matched_reading']}"
        )
        # If one is longer than the other, return the longer one
        if on_length > kun_length:
            logger.debug("\nonyomi_process_result is longer")
            return onyomi_process_result
        if kun_length > on_length:
            logger.debug("\nkunyomi_process_result is longer")
            return kunyomi_process_result
        # If same length, return kunyomi if we have okurigana
        if kunyomi_process_result.okurigana:
            logger.debug("\nsame length kunyomi_process_result has okurigana")
            return kunyomi_process_result
        # Otherwise return onyomi
        logger.debug("\nreturn same length onyomi_process_result")
        return onyomi_process_result
    if onyomi_process_result:
        logger.debug("\nonyomi_process_result is returned")
        return onyomi_process_result
    if kunyomi_process_result:
        logger.debug("\nkunyomi_process_result is returned")
        return kunyomi_process_result

    return None


def process_jukujikun_reading(
    highlight_args: HighlightArgs,
    word_data: WordData,
    with_tags_def: WithTagsDef,
    logger: Logger = Logger("error"),
) -> ReadingProcessResult:

    maybe_okuri = word_data.get("okurigana", "")
    edge = word_data.get("edge", "none")

    # Neither onyomi nor kunyomi matched, get jukujikun or nothing
    kanji_count = word_data.get("kanji_count")
    kanji_pos = word_data.get("kanji_pos")

    if kanji_count is None or kanji_pos is None:
        logger.error(
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
    furigana: str, edge: Optional[Edge], logger: Logger = Logger("error")
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
    logger.error(
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
    logger: Logger = Logger("error"),
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
        logger.debug(
            f"check_reading_in_furigana_section - left edge, furigana_section: {furigana_section}"
            f", all_readings: {all_readings}"
        )
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
    logger: Logger = Logger("error"),
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

    logger.debug(
        f"check_onyomi_readings - target_furigana_section: {target_furigana_section}, edge: {edge}"
    )

    # Exception for 麻雀[まーじゃん] where 麻[まー] should be a jukujikun, and we don't want to
    # match ま as a onyomi
    if furigana == "まーじゃん":
        return {
            "text": "",
            "type": "none",
            "match_edge": "none",
            "actual_match": "",
            "matched_reading": "",
        }

    for onyomi_reading in onyomi_readings:
        # remove text in () in the reading
        onyomi_reading = re.sub(r"\(.*?\)", "", onyomi_reading).strip()
        logger.debug(f"check_onyomi_readings 1 - onyomi_reading: {onyomi_reading}")
        if not onyomi_reading:
            continue
        # Convert the onyomi to hiragana since the furigana is in hiragana
        onyomi_reading = to_hiragana(onyomi_reading)
        match_in_section, match_type = is_reading_in_furigana_section(
            onyomi_reading,
            target_furigana_section,
            okurigana,
            edge,
            logger=logger,
        )
        logger.debug(
            f"check_onyomi_readings 2 - onyomi_reading: {onyomi_reading}, in_section:"
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
    logger: Logger = Logger("error"),
) -> OkuriResults:
    """
    Function that checks the okurigana for a match with the kunyomi okurigana

    :return: (string, string) the okurigana that should be highlighted and the rest of the okurigana
    """
    # Kana text occurring after the kanji in the word, may not be okurigana and can
    # contain other kana after the okurigana
    maybe_okuri_text = word_data.get("okurigana")
    logger.debug(
        f"check okurigana 0 - kunyomi_okurigana: {kunyomi_okurigana},"
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

    logger.debug(f"check okurigana 1 - conjugatable_stem: {conjugatable_stem}")
    if conjugatable_stem is None or not maybe_okuri_text.startswith(conjugatable_stem):
        logger.debug("\ncheck okurigana 2 - no conjugatable_stem or no match")
        # Not a verb or i-adjective, so just check for an exact match within the okurigana
        if maybe_okuri_text.startswith(kunyomi_okurigana):
            logger.debug(f"check okurigana 3 - maybe_okuri_text: {maybe_okuri_text}")
            return OkuriResults(
                kunyomi_okurigana,
                maybe_okuri_text[len(kunyomi_okurigana) :],
                "full_okuri",
            )
        logger.debug("\ncheck okurigana 4 - no match")
        return OkuriResults("", maybe_okuri_text, "no_okuri")

    # Remove the conjugatable_stem from maybe_okurigana
    trimmed_maybe_okuri = maybe_okuri_text[len(conjugatable_stem) :]
    logger.debug(f"check okurigana 5 - trimmed_maybe_okuri: {trimmed_maybe_okuri}")

    # Then check if that contains a conjugation for what we're looking for
    conjugated_okuri, rest, return_type = starts_with_okurigana_conjugation(
        trimmed_maybe_okuri,
        kunyomi_okurigana,
        highlight_args["kanji_to_match"],
        kunyomi_reading,
    )
    logger.debug(
        f"check okurigana 6 - conjugated_okuri: {conjugated_okuri}, rest: {rest},"
        f" return_type: {return_type}"
    )

    if return_type != "no_okuri":
        logger.debug(
            f"check okurigana 7 - result: {conjugatable_stem + conjugated_okuri}, rest: {rest}"
        )
        # remember to add the stem back!
        return OkuriResults(conjugatable_stem + conjugated_okuri, rest, return_type)

    # No match, this text doesn't contain okurigana for the kunyomi word
    logger.debug("\ncheck okurigana 8 - no match")
    return OkuriResults("", maybe_okuri_text, "no_okuri")


def check_kunyomi_readings(
    highlight_args: HighlightArgs,
    word_data: WordData,
    furigana: str,
    target_furigana_section: str,
    edge: Edge,
    wrap_readings_with_tags: bool = True,
    process_type: MatchProcess = "match",
    logger: Logger = Logger("error"),
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

    # Exception for 清々[すがすが]しい where すがすが should be a jukujikun, but the す would
    # match kunyomi reading す.む for 清, so this is needed
    if furigana.startswith("すがすが") and highlight_args.get("kanji_to_match") == "清":
        logger.debug(
            "\ncheck_kunyomi_readings - exception for 清々[すがすが]しい, returning empty result"
        )
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
        kunyomi_reading = to_hiragana(kunyomi_reading)
        logger.debug(f"check_kunyomi_readings - kunyomi_reading: {kunyomi_reading}")
        # Split the reading into the stem and the okurigana
        kunyomi_stem = kunyomi_reading
        kunyomi_dict_form_okuri = ""
        if "." in kunyomi_reading:
            try:
                kunyomi_stem, kunyomi_dict_form_okuri = kunyomi_reading.split(".")
            except ValueError:
                logger.debug(
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

    kanji_to_match = highlight_args.get("kanji_to_match", "")
    if kanji_to_match == "為":
        # Special case for 為, add し as a stem
        for kunyomi_stem in ["し", "さ"]:
            kunyomi_stems.add((kunyomi_stem, "す.る"))
            kunyomi_stem_and_okuris.append((kunyomi_stem, "", "す.る"))

    okurigana = word_data.get("okurigana", "")
    # First check matches against the stem
    for kunyomi_stem, full_reading in kunyomi_stems:
        if not kunyomi_stem:
            continue
        match_in_section, match_type = is_reading_in_furigana_section(
            kunyomi_stem, target_furigana_section, okurigana, edge, logger=logger
        )
        logger.debug(
            f"check_kunyomi_readings - kunyomi_stem: {kunyomi_stem}, in_section:"
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
    logger.debug(
        f"check_kunyomi_readings - noun form: {kunyomi_stem}, kunyomi_dict_form_okuri:"
        f" {kunyomi_dict_form_okuri}\nokurigana: {okurigana}, kanji_to_match:"
        f" {kanji_to_match}"
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
                okuri_included_reading, target_furigana_section, okurigana, edge, logger=logger
            )
            logger.debug(
                f"check_kunyomi_readings - okuri_included form: {okuri_included_reading},"
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
    logger.debug(
        f"check_kunyomi_readings - stem_match_results: {stem_match_results},"
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
    logger.debug("\ncheck_kunyomi_readings - no match")
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


def handle_furigana_doubling(
    partial_result: YomiMatchResult,
    cur_furigana_section: str,
    matched_furigana: str,
    logger: Logger = Logger("error"),
) -> str:
    """
    Function that handles the case of a word with doubled furigana, due it using the repeater
    kanji 々.
    """
    doubled_furigana = ""
    # If this was a normal match, the furigana should be repeating
    # check if there's rendaku in the following furigana
    furigana_after_matched = cur_furigana_section[len(matched_furigana) :]
    rendaku_matched_furigana = (
        [f"{kana}{matched_furigana[1:]}" for kana in RENDAKU_CONVERSION_DICT[matched_furigana[0]]]
        if matched_furigana[0] in RENDAKU_CONVERSION_DICT
        else []
    )
    rendaku_matched_furigana.append(to_hiragana(matched_furigana))  # Add the original
    logger.debug(
        f"repeater kanji - doubling furigana: {matched_furigana},"
        f" furigana_after_matched: {furigana_after_matched},"
        f" rendaku_matched_furigana:{rendaku_matched_furigana}"
    )
    if furigana_after_matched:
        for rf in rendaku_matched_furigana:
            if furigana_after_matched.startswith(rf):
                doubled_furigana = matched_furigana + (
                    to_katakana(rf) if partial_result["match_type"] == "onyomi" else rf
                )
                logger.debug(
                    f"repeater kanji - found rendaku match: {rf} in"
                    f" furigana_after_matched: {furigana_after_matched}"
                )
                break
    else:
        logger.debug(
            "repeater kanji - no furigana_after_matched, simply doubling with"
            f" matched_furigana: {matched_furigana}"
        )
        doubled_furigana = matched_furigana * 2

    return doubled_furigana


def handle_jukujikun_case(
    word_data: WordData,
    highlightArgs: HighlightArgs,
    wrap_readings_with_tags: bool,
    logger: Logger = Logger("error"),
) -> YomiMatchResult:
    """
    Function that handles the case of a jukujikun/ateji word where the furigana
    doesn't match the onyomi or kunyomi. Highlights the part of the furigana matching
    the kanji position
    :return: Result dict with the modified furigana
    """
    kanji_to_highlight = highlightArgs.get("kanji_to_highlight", "")
    kanji_count = word_data.get("kanji_count", 0)
    word = word_data.get("word", "")
    try:
        assert kanji_count > 0, (
            f"handle_jukujikun_case[]: incorrect kanji_count: {word_data.get('kanji_count')}, word:"
            f" {word}, kanji_to_highlight: {kanji_to_highlight}"
        )
    except AssertionError as e:
        logger.error(e)
        return {
            "text": word_data.get("furigana", ""),
            "type": "none",
            "match_edge": word_data.get("edge", "none"),
            "actual_match": "",
            "matched_reading": "",
        }
    kanji_pos = word.find(kanji_to_highlight) if kanji_to_highlight else -1
    # kanji_pos can be -1, in which case no highlighting happens
    assert kanji_pos < kanji_count, (
        f"handle_jukujikun_case[]: incorrect kanji_pos: {kanji_pos}, kanji_to_highlight:"
        f" {kanji_to_highlight}"
    )
    furigana = word_data.get("furigana", "")

    # First split the word into mora
    mora_list = ALL_MORA_REC.findall(furigana)
    # Merge ん with the previous mora into a new list
    if "ん" in mora_list:
        new_list: list[str] = []
        new_list_index = 0
        for mora in mora_list:
            if mora == "ん" and new_list_index > 0:
                new_list[new_list_index - 1] += mora
            else:
                new_list.append(mora)
                new_list_index += 1
        mora_list = new_list

    logger.debug(f"handle_jukujikun_case - mora_list: {mora_list}")
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
        logger.debug(
            f"juku mora 1, kanji_index: {kanji_index}, kanji_pos: {kanji_pos}, cur_mora_index:"
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
            logger.debug(
                f"juku mora 3 closing bold - kanji_index: {kanji_index}, kanji_pos: {kanji_pos},"
                f" has_bold: {new_furigana[-3:] == '<b>'}, new_furigana: {new_furigana}"
            )
            new_furigana += "</b>" if new_furigana[-4:] != "</b>" else ""

        mora = "".join(mora_list[cur_mora_index:cur_mora_range_max])
        logger.debug(f"juku mora 2 - mora: {mora}")
        if wrap_readings_with_tags:
            new_furigana += f"<juk>{mora}</juk>"
        else:
            new_furigana += mora
        if is_kanji_match:
            actual_match = mora
        logger.debug(f"juku mora 5 - new_furigana: {new_furigana}")

        if kanji_index == kanji_pos:
            logger.debug(
                f"juku mora 4 closing bold - kanji_index: {kanji_index}, kanji_pos: {kanji_pos},"
                f" has_bold: {new_furigana[-3:] == '<b>'}, new_furigana: {new_furigana}"
            )
            new_furigana += "</b>" if new_furigana[-4:] != "</b>" else ""
        cur_mora_index = cur_mora_range_max
        if is_rep_kanji:
            # Skip the next kanji since it's the repeater and we handled it already
            kanji_index += 2
        else:
            kanji_index += 1
    logger.debug(f"handle_jukujikun_case - new_furigana: {new_furigana}")
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
    logger: Logger = Logger("error"),
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
        logger=logger,
    )
    if res is None:
        logger.debug("\nhandle_whole_word_case - handle as jukujikun")
        res = process_jukujikun_reading(
            highlight_args,
            word_data,
            with_tags_def=with_tags_def,
            logger=logger,
        )
    result, okurigana_to_highlight, rest_kana = res
    logger.debug(
        f"handle_whole_word_case - word: {word}, result: {result}, okurigana:"
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
    logger: Logger = Logger("error"),
) -> Union[PartialResult, None]:
    """
    The case when the word contains other kanji in addition to the kanji to highlight.
    Could be 2 or more kanji in the word.

    :return: string, the modified furigana with the kanji to highlight highlighted
    """
    kanji_to_match = highlight_args.get("kanji_to_match", "")
    logger.debug(
        f"handle_partial_word_case - kanji_to_match: {kanji_to_match}, word: {word},"
        f" furigana: {furigana}, okurigana: {okurigana}"
    )

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
        logger.error(
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

    if edge == "whole" and len(word) > 1 and "々" not in word:
        # If the edge is whole but the word is longer than 1 kanji, treat it as a partial match
        if kanji_pos == 0:
            edge = "left"
        elif kanji_pos == len(word) - 1:
            edge = "right"
        else:
            edge = "middle"

    word_data: WordData = {
        "kanji_pos": kanji_pos,
        "kanji_count": len(word),
        "furigana": furigana,
        "edge": edge,
        "word": word,
        "okurigana": okurigana,
    }

    logger.debug(
        f"handle_partial_word_case - word: {word}, furigana: {furigana}, okurigana: {okurigana},"
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
        logger=logger,
    )
    if res is None:
        logger.debug("\nhandle_partial_word_case - no result from process_readings")
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
    logger.debug(f"handle_partial_word_case - final_result: {furi_okuri_result}")
    return furi_okuri_result


def kana_highlight(
    kanji_to_highlight: Optional[str],
    text: str,
    return_type: FuriReconstruct = "kana_only",
    with_tags_def: Optional[WithTagsDef] = None,
    logger: Logger = Logger("error"),
) -> str:
    if with_tags_def is None:
        with_tags_def = WithTagsDef(
            True, True, False  # with_tags  # merge_consecutive  # assume dictionary form
        )
    """
    Function that replaces the furigana of a kanji with the furigana that corresponds to the kanji's
    onyomi or kunyomi reading. The furigana is then highlighted with<b> tags.
    Text received could be a sentence or a single word with furigana.
    :param kanji_to_highlight: should be a single kanji character
    :param text: The text to process
    :param return_type: string. Return either normal furigana, reversed furigana AKA furikanji or
        remove the kanji and return only the kana
    :param with_tags_def: tuple, with_tags and merge_consecutive keys. Whether to wrap the readings
        with tags and whether to merge consecutive tags
    :param logger: Logger instance to log errors
    :return: The text cleaned from any previous<b> tags and<b> added around the furigana
        when the furigana corresponds to the kanji_to_highlight
    """

    def furigana_replacer(match: re.Match):
        """
        Replacer function for KANJI_AND_FURIGANA_REC. This function is called for every match
        found by the regex. It processes the furigana and returns the modified furigana.
        :param match: re.Match, the match object
        :return: string, the modified furigana
        """
        nonlocal kanji_to_highlight
        word = match.group(1)
        furigana = match.group(2)
        okurigana = match.group(3)
        logger.debug(
            f"furigana_replacer - word: {word}, furigana: {furigana}, okurigana: {okurigana}"
        )
        # Replace doubled kanji with the repeater character
        word = DOUBLE_KANJI_REC.sub(lambda m: m.group(1) + "々", word)
        logger.debug(f"furigana_replacer - word after double kanji: {word}")

        if furigana.startswith("sound:"):
            # This was something like 漢字[sound:...], we shouldn't modify the text in the brackets
            # as it'd break the audio tag. But we know the text to the right is kanji
            # (what is it doing there next to a sound tag?) so we'll just leave it out anyway
            return furigana + okurigana

        highlight_kanji_is_whole_word = kanji_to_highlight is not None and (
            word == kanji_to_highlight
            or f"{kanji_to_highlight}々" == word
            or kanji_to_highlight * 2 == word
        )

        # Whole word case is easy, just highlight the whole furigana
        if highlight_kanji_is_whole_word and kanji_to_highlight is not None:
            kanji_data = all_kanji_data.get(kanji_to_highlight)
            if not kanji_data:
                logger.error(
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
                logger,
            )
            return reconstruct_furigana(
                final_result,
                with_tags_def,
                reconstruct_type=return_type,
            )

        cur_furigana_section = furigana
        cur_word = word
        cur_edge: Edge = "left"
        is_last_kanji = False
        kanji_to_highlight_passed = False
        final_furigana = ""
        final_okurigana = ""
        final_rest_kana = ""
        final_edge: Edge = "whole"
        final_left_word = ""
        final_middle_word = ""
        final_right_word = ""
        force_merge = False

        juku_word_start = None
        juku_word_end = None
        juku_furigana = None
        juku_word_start_edge = None
        juku_word_pos_to_highlight: Union[Literal["left", "middle", "right"], None] = None

        replace_num_kanji = None
        num_in_kanji_to_replace = None
        last_replaced_kanji_index = None

        def process_kanji_in_word(
            kanji: str,
            index: int,
            word: str,
            cur_edge: Edge,
        ):
            nonlocal cur_furigana_section, cur_word, final_furigana, final_left_word
            nonlocal final_middle_word, final_right_word, final_edge, final_rest_kana
            nonlocal final_okurigana, juku_word_start, juku_word_end, juku_furigana
            nonlocal juku_word_start_edge, juku_word_pos_to_highlight, replace_num_kanji
            nonlocal num_in_kanji_to_replace, last_replaced_kanji_index, is_last_kanji
            nonlocal kanji_to_highlight_passed

            is_first_kanji = index == 0
            is_last_kanji = index >= max(len(cur_word), len(word)) - 1
            next_kanji_is_repeater_and_last = index + 1 < len(word) and word[index + 1] == "々"
            is_middle_kanji = not is_first_kanji and not is_last_kanji
            if is_middle_kanji:
                cur_edge = "middle"
            elif is_last_kanji:
                cur_edge = "right"

            logger.debug(
                f"process_kanji_in_word - kanji: {kanji}, index: {index}, word: {word},"
                f" cur_furigana_section: {cur_furigana_section}, cur_word: {cur_word}, cur_edge:"
                f" {cur_edge}, final_furigana: {final_furigana}, final_left_word:"
                f" {final_left_word}, final_middle_word: {final_middle_word}, final_right_word:"
                f" {final_right_word}, final_edge: {final_edge}, final_rest_kana:"
                f" {final_rest_kana}, final_okurigana: {final_okurigana},"
                f" {final_rest_kana}, okurigana: {okurigana}, is_first_kanji: {is_first_kanji},"
                f" is_last_kanji: {is_last_kanji}, is_middle_kanji: {is_middle_kanji},"
                f" kanji_to_highlight: {kanji_to_highlight}, next_kanji: {next_kanji}"
            )
            kanji_data_key = NUMBER_TO_KANJI.get(kanji, kanji)
            kanji_data = all_kanji_data.get(kanji_data_key)
            if not kanji_data:
                logger.error(
                    f"Error in kana_highlight[]: main word loop, kanji '{kanji}' not found in"
                    " all_kanji_data"
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
                okurigana if (is_last_kanji or next_kanji_is_repeater_and_last) else "",
                with_tags_def=with_tags_def,
                logger=logger,
            )
            logger.debug(
                f"partial_result: {partial_result}, is_kanji_to_highlight: {is_kanji_to_highlight}"
            )
            if partial_result is None:
                # Need to handle this as jukujikun, break and
                # proceed to reverse processing of the rest of the word
                juku_word_start_edge = cur_edge
                juku_word_start = index
                juku_furigana = cur_furigana_section
                if kanji_to_highlight_passed:
                    juku_word_pos_to_highlight = "right"
                return False
            matched_furigana = partial_result["matched_furigana"]
            wrapped_furigana = matched_furigana

            if next_kanji == "々":
                logger.debug(f"repeater kanji: {next_kanji}")
                rep_kanji = next_kanji
                cur_word = cur_word[2:]
                matched_furigana = handle_furigana_doubling(
                    partial_result,
                    cur_furigana_section,
                    matched_furigana,
                    logger=logger,
                )
                wrapped_furigana = matched_furigana
                # If the repeater is the last kanji, then edge should be "right" and not "middle"
                next_kanji_is_last = index + 2 == len(word)
                if next_kanji_is_last:
                    cur_edge = "right"
                    is_last_kanji = True
                    is_middle_kanji = False
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
            logger.debug(
                f"wrapped_furigana: {wrapped_furigana}, matched_furigana: {matched_furigana},"
                f" cur_furigana_section: {cur_furigana_section}, cur_word: {cur_word}"
            )
            # If this was the kanji to highlight, this edge should be in the final_result as
            # reconstructed furigana needs it
            if is_kanji_to_highlight:
                final_edge = cur_edge
                logger.debug(f"final_edge set to {final_edge} for kanji {kanji} at index {index}")
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

            logger.debug(
                f"rest_kana: {partial_result['rest_kana']}, okurigana:"
                f" {partial_result['okurigana']}, is_last_kanji: {is_last_kanji}"
            )
            # Rest_kana and okurigana is only added on processing the last kanji
            if is_last_kanji:
                final_rest_kana = partial_result["rest_kana"]
                final_okurigana = partial_result["okurigana"]

            logger.debug(
                f"final_furigana: {final_furigana}, final_left_word: {final_left_word},"
                f" final_middle_word: {final_middle_word}, final_right_word: {final_right_word},"
                f" final_edge: {final_edge}, final_rest_kana: {final_rest_kana},"
                f" final_okurigana: {final_okurigana}"
            )

            if not matched_furigana:
                logger.error(
                    f"Error in kana_highlight[]: no match found for kanji {kanji} in word {word}"
                )
                # Something went wrong with the matching, we can't slice the furigana so we can't
                # continue. Return what we got so far
                final_furigana += cur_furigana_section
                final_okurigana += okurigana
                final_right_word += cur_word
                cur_word = ""
                cur_furigana_section = ""
                return False
            return True

        # For the partial case, we need to split the furigana for each kanji using the kanji_data
        # for each one, highlight the kanji_to_match and reconstruct the furigana
        for index, kanji in enumerate(word):
            logger.debug(
                f"main word loop - kanji: {kanji}, index: {index}, word: {word},"
                f" cur_furigana_section: {cur_furigana_section}, cur_word: {cur_word}"
            )
            if kanji == "々":
                # Skip repeater as this will have been handled in the previous iteration
                continue
            if last_replaced_kanji_index is not None and index < last_replaced_kanji_index:
                # If we replaced roman numerals with kanji, skip until we reach normal kanji again
                logger.debug(
                    f"skipping kanji {kanji} at index {index} - last_replaced_kanji_index:"
                    f" {last_replaced_kanji_index}"
                )
                continue
            elif last_replaced_kanji_index is not None and index == last_replaced_kanji_index:
                logger.debug(
                    f"resuming kanji {kanji} at index {index} - last_replaced_kanji_index:"
                    f" {last_replaced_kanji_index}"
                )
                last_replaced_kanji_index = None
                continue
            elif last_replaced_kanji_index is not None and index > last_replaced_kanji_index:
                last_replaced_kanji_index = None

            is_last_kanji = index == len(word) - 1

            next_kanji = word[index + 1] if not is_last_kanji else ""
            # Get all next characters that are numbers that ought to be processed as kanji
            number_kanji = []
            num_index = index
            num_kanji = kanji
            while num_kanji and num_kanji in NUMBER_TO_KANJI:
                last_replaced_kanji_index = num_index
                number_kanji.append(num_kanji)
                num_index += 1
                if num_index < len(word):
                    num_kanji = word[num_index]
                else:
                    num_kanji = ""

            if number_kanji:
                # If the next kanjis contain numbers, we should replace them with kanji
                # and process them as kanji
                replace_num_kanji = "".join(number_kanji)
                if replace_num_kanji:
                    # Replace the kanji with the kanji from NUMBER_TO_KANJI
                    num_in_kanji_to_replace = number_to_kanji(replace_num_kanji, logger=logger)

                    logger.debug(
                        f"replacing kanji {replace_num_kanji} with {num_in_kanji_to_replace}"
                    )
                    cur_word = cur_word.replace(replace_num_kanji, num_in_kanji_to_replace, 1)
                    # Process all the number kanji
                    for num_kanji_index, num_kanji_char in enumerate(num_in_kanji_to_replace):
                        kanji_pos_in_cur_word = cur_word.find(num_kanji_char)
                        if kanji_pos_in_cur_word == 0 and len(cur_word) > 1:
                            cur_edge = "left"
                        should_continue = process_kanji_in_word(
                            kanji=num_kanji_char,
                            index=index + num_kanji_index,
                            word=num_in_kanji_to_replace,
                            cur_edge=cur_edge,
                        )
                        if not should_continue:
                            logger.debug(
                                f"replacing kanji {replace_num_kanji} - breaking out of loop"
                            )
                            break
                    # Return back to the main kanji loop, where we skip until the next kanji
                    # that is not a number kanji
                    logger.debug(
                        f"replacing kanji {replace_num_kanji} - completing the loop, index:"
                        f" {index}, last_replaced_kanji_index: {last_replaced_kanji_index},"
                        f" cur_word: {cur_word}, final_left_word: {final_left_word},"
                        f" final_middle_word: {final_middle_word}, final_right_word:"
                        f" {final_right_word}"
                        f", final_furigana: {final_furigana}, final_edge: {final_edge},"
                        f" final_rest_kana: {final_rest_kana}, final_okurigana: {final_okurigana}"
                    )
                    cur_word = cur_word.replace(num_in_kanji_to_replace, replace_num_kanji, 1)
                    # replace converted num_kanji in final_left_word, final_middle_word,
                    # final_right_word with the original characters
                    if (
                        len(num_in_kanji_to_replace) == 2
                        and len(final_left_word) == 1
                        and len(final_right_word) == 1
                    ):
                        logger.debug(
                            f"replacing kanji {replace_num_kanji} in final_left_word and"
                            f" final_right_word - final_left_word: {final_left_word},"
                            f" final_right_word: {final_right_word}, final_edge: {final_edge}"
                        )
                        # If the kanji is a 2-kanji number, we should replace it in the left and
                        # right words
                        final_left_word = final_left_word.replace(
                            num_in_kanji_to_replace[0], replace_num_kanji[0]
                        )
                        final_right_word = final_right_word.replace(
                            num_in_kanji_to_replace[1], replace_num_kanji[1]
                        )
                    elif len(num_in_kanji_to_replace) > 2:
                        # for more complex case, just merge them all together
                        force_merge = True
                        final_left_word += final_middle_word + final_right_word
                        final_middle_word = ""
                        final_right_word = ""
                        final_edge = "left"
                        logger.debug(
                            "merging all final words together - final_left_word:"
                            f" {final_left_word}, final_middle_word: {final_middle_word},"
                            f" final_right_word: {final_right_word}, final_edge: {final_edge}"
                            f" final_furigana: {final_furigana}, final_rest_kana:"
                            f" {final_rest_kana}, final_okurigana: {final_okurigana}"
                        )

                    continue

            kanji_pos = word.find(kanji)
            if kanji_pos == 0 and len(cur_word) > 1:
                # If the kanji is the first one in the word, the edge is "left"
                cur_edge = "left"
            should_continue = process_kanji_in_word(kanji, index, word, cur_edge)
            if not should_continue:
                logger.debug("process_kanji_in_word - breaking out of loop")
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
        logger.debug(
            f"partial_result is None - juku_word_start: {juku_word_start}, juku_furigana:"
            f" {juku_furigana} juku_word_pos_to_highlight:"
            f" {juku_word_pos_to_highlight} juku_word_start_edge: {juku_word_start_edge},"
            f" juku_word_reversed: {juku_word_reversed}"
        )
        for i, kanji in enumerate(juku_word_reversed):
            logger.debug(f"reversing loop - i: {i}, kanji: {kanji}")
            if kanji == "々":
                # Skip repeater as this will be handled in the next iteration
                continue
            # The edge is reversed now, so the first kanji is the right edge
            is_first_kanji = i == juku_word_length - 1
            is_last_kanji = i == 0
            original_word_index = len(word) - i - 1
            # Last kanji is where we left off with the previous loop, so we can stop there
            prev_kanji = juku_word_reversed[i - 1] if i > 0 else ""
            prev_kanji_is_repeater_and_last = prev_kanji == "々" and i == 1
            if is_first_kanji:
                juku_word_end = original_word_index
                if prev_kanji == "々" and juku_word_length >= 2:
                    juku_word_end += 1
                    juku_word_start = juku_word_end - 1
                    juku_word_pos_to_highlight = "right" if juku_word_length == 2 else "middle"
                    logger.debug(
                        "reversing whole word is kanji + repeater - juku_word_start:"
                        f" {juku_word_start}, juku_word_end: {juku_word_end}, word: {word}"
                        f" juku_word_start_edge: {juku_word_start_edge}"
                    )
                continue

            is_middle_kanji = not is_first_kanji and not is_last_kanji
            if is_first_kanji:
                cur_edge = juku_word_start_edge
            elif is_middle_kanji:
                cur_edge = "middle"
            kanji_data_key = NUMBER_TO_KANJI.get(kanji, kanji)
            kanji_data = all_kanji_data.get(kanji_data_key)
            if not kanji_data:
                logger.error(
                    f"Error in kana_highlight[]: reversing, kanji '{kanji}' not found in"
                    " all_kanji_data"
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
                okurigana if (is_last_kanji or prev_kanji_is_repeater_and_last) else "",
                with_tags_def=with_tags_def,
                logger=logger,
            )
            logger.debug(
                f"reversing, partial_result: {partial_result}, is_kanji_to_highlight:"
                f" {is_kanji_to_highlight}, cur_word: {cur_word}, cur_furigana_section:"
                f" {cur_furigana_section}, original_word_index: {original_word_index},"
                f" prev_kanji_is_repeater_and_last: {prev_kanji_is_repeater_and_last}"
            )
            if partial_result is None:
                # Found the end of the jukujikun part, this can be the same as juku_word_start
                juku_word_end = original_word_index
                logger.debug(
                    f"reversing end by partial_result is None, juku_word_end: {juku_word_end}"
                )
                if prev_kanji == "々":
                    juku_word_end += 1
                    juku_word_start = juku_word_end - 1
                    logger.debug(
                        "reversing partial, prev_kanji was repeater - juku_word_start:"
                        f" {juku_word_start}, juku_word_end: {juku_word_end}, word: {word}"
                    )
                break
            matched_furigana = partial_result["matched_furigana"]
            wrapped_furigana = matched_furigana

            if prev_kanji == "々":
                # Add the repeater to be processed as part of the current kanji
                # kanji = f"{kanji}{prev_kanji}"
                rep_kanji = prev_kanji
                # if we had the repeater kanji, we should add more furigana to this result
                # If this was a normal match, the furigana should be repeating
                # For the furigana doubling, we'll need to use only the part of the furigana section
                # that starts from the matched furigana, because the next furigana is currently
                # to the left instead of the right due to the reversing
                matched_furigana_start_index = cur_furigana_section.find(matched_furigana)
                furigana_section_starting_from_matched = cur_furigana_section[
                    matched_furigana_start_index:
                ]
                logger.debug(
                    f"reversing, repeater kanji - doubling furigana: {matched_furigana},"
                    f" cur_furigana_section: {cur_furigana_section}"
                    f"reversing, matched_furigana_start_index: {matched_furigana_start_index},"
                    " furigana_section_starting_from_matched:"
                    f" {furigana_section_starting_from_matched}"
                )
                matched_furigana = handle_furigana_doubling(
                    partial_result,
                    furigana_section_starting_from_matched,
                    matched_furigana,
                    logger=logger,
                )
                logger.debug(f"reversing, matched_furigana after doubling: {matched_furigana}")
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
            logger.debug(
                f"wrapped_furigana: {wrapped_furigana}, matched_furigana: {matched_furigana},"
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

            if is_last_kanji or prev_kanji_is_repeater_and_last:
                final_rest_kana = partial_result["rest_kana"]
                final_okurigana = partial_result["okurigana"]

        logger.debug(
            f"reversing processed, juku_word_start: {juku_word_start}, juku_word_end:"
            f" {juku_word_end}, juku_furigana: {juku_furigana}"
        )
        if juku_word_start is not None and juku_word_end is not None and juku_furigana is not None:
            juku_word = word[juku_word_start : juku_word_end + 1]
            juku_at_word_right_edge = juku_word_end == len(word) - 1
            juku_at_word_left_edge = juku_word_start == 0
            logger.debug(
                f"start processing reversed handle_jukujikun_case - juku_word: {juku_word},"
                f" final_edge: {final_edge}"
            )
            kanji_pos = juku_word.find(kanji_to_highlight) if kanji_to_highlight else -1
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
                # kanji_to_match not used in jukujikun processing
                "kanji_to_match": "",
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
                logger=logger,
            )
            logger.debug(
                f"handle_jukujikun_case - juku_result: {juku_result}, juku_word_pos_to_highlight:"
                f" {juku_word_pos_to_highlight}, juku_okuri: {juku_okuri}, juku_rest_kana:"
                f" {juku_rest_kana}, juku_word: {juku_word}, juku_at_word_right_edge:"
                f" {juku_at_word_right_edge}, juku_at_word_left_edge: {juku_at_word_left_edge},"
                f" kanji_pos: {kanji_pos}, kanji_to_highlight: {kanji_to_highlight}"
            )
            reverse_final_furigana = juku_result["text"] + reverse_final_furigana
            kanji_to_left = juku_word[:kanji_pos]
            kanji_to_right = juku_word[kanji_pos + 1 :]
            if juku_word_pos_to_highlight == "left":
                reverse_final_left_word = juku_word + reverse_final_left_word
            elif juku_word_pos_to_highlight == "right":
                reverse_final_right_word = juku_word + reverse_final_right_word
                if kanji_to_right and kanji_to_right[0] == "々":
                    final_edge = "right"
            elif kanji_pos != -1 and kanji_to_highlight is not None:
                # Kanji to highlight is in the juku word which is in the middle
                highlight_word = kanji_to_highlight
                had_rep_kanji = False
                if kanji_to_right and kanji_to_right[0] == "々":
                    had_rep_kanji = True
                    kanji_to_right = kanji_to_right[1:]
                    highlight_word += "々"
                final_edge = juku_result["match_edge"]
                logger.debug(
                    "handle_jukujikun_case with highlight and juku pos at middle edge"
                    f" -juku_at_word_right_edge: {juku_at_word_right_edge}, juku_at_word_left_edge:"
                    f" {juku_at_word_left_edge}, kanji_to_left: {kanji_to_left}, kanji_to_right:"
                    f" {kanji_to_right}, highlight_word: {highlight_word}"
                )
                # Correct edge if this was a single kanji juku word
                if len(juku_word) == 1 or (had_rep_kanji and len(juku_word) == 2):
                    if juku_at_word_left_edge:
                        final_edge = "left"
                    elif juku_at_word_right_edge:
                        final_edge = "right"
                    else:
                        final_edge = "middle"
                elif reverse_final_right_word and final_edge == "right":
                    # multi-kanji jukujikun, highlight is at the right edge of the juku word
                    # but there's another non-juku word after it, so the final edge is middle
                    final_edge = "middle"
                elif not juku_at_word_left_edge and final_edge == "left":
                    # multi-kanji jukujikun, highlight is at the left edge of the juku word
                    # but there's another non-juku word before it, so the final edge is middle
                    final_edge = "middle"

                logger.debug(
                    f"reversed handle_jukujikun_case with highlight - juku_word: {juku_word},"
                    f" kanji_to_left: {kanji_to_left} kanji_to_right: {kanji_to_right},"
                    f" highlight_word: {highlight_word} final_edge: {final_edge}"
                )
                if final_edge == "left":
                    reverse_final_left_word = highlight_word + reverse_final_left_word
                    reverse_final_right_word = kanji_to_right + reverse_final_right_word
                elif final_edge == "right":
                    reverse_final_right_word = highlight_word + reverse_final_right_word
                    reverse_final_left_word = kanji_to_left + reverse_final_left_word
                elif final_edge == "middle":
                    logger.debug(
                        "reversed handle_jukujikun_case with highlight - final_edge is middle"
                        f" - kanji_to_left: {kanji_to_left}, kanji_to_right: {kanji_to_right},"
                        f" highlight_word: {highlight_word}, reverse_final_right_word:"
                        f" {reverse_final_right_word}, reverse_final_left_word:"
                        f"{reverse_final_left_word},"
                        f" reverse_final_middle_word: {reverse_final_middle_word}"
                    )
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
        reconstructed_result = reconstruct_furigana(
            final_result,
            with_tags_def=with_tags_def,
            reconstruct_type=return_type,
            force_merge=force_merge,
            logger=logger,
        )
        if replace_num_kanji is not None:
            if num_in_kanji_to_replace is None:
                logger.error(
                    "Error in kana_highlight[]: replace_num_kanji is not None but"
                    " num_in_kanji_to_replace is None"
                )
                return reconstructed_result
            # If we replaced roman numerals with kanji, we need to replace them back
            # in the reconstructed result
            reconstructed_result = reconstructed_result.replace(
                num_in_kanji_to_replace, replace_num_kanji, 1
            )
        return reconstructed_result

    # Clean any potential mixed okurigana cases, turning them normal
    clean_text = OKURIGANA_MIX_CLEANING_RE.sub(okurigana_mix_cleaning_replacer, text)
    processed_text = KANJI_AND_FURIGANA_AND_OKURIGANA_REC.sub(furigana_replacer, clean_text)
    logger.debug(f"processed_text: {processed_text}")
    # Clean any double spaces that might have been created by the furigana reconstruction
    # Including those right before a<b> tag as the space is added with those
    processed_text = re.sub(r" {2}", " ", processed_text)
    processed_text = re.sub(r" <(b|on|kun|juk|mix)> ", r"<\1> ", processed_text)
    return re.sub(r" <b><(on|kun|juk|mix)> ", r"<b><\1> ", processed_text)
