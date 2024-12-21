
import re
from typing import Union, Callable, TypedDict, Literal, Optional

try:
    from .jpn_text_processing.kana_conv import to_katakana, to_hiragana
    from .jpn_text_processing.get_conjugatable_okurigana_stem import get_conjugatable_okurigana_stem
    from .jpn_text_processing.starts_with_okurigana_conjugation import starts_with_okurigana_conjugation, OkuriResults
except ImportError:
    # For testing
    import sys
    from jpn_text_processing.kana_conv import to_katakana, to_hiragana
    from jpn_text_processing.get_conjugatable_okurigana_stem import get_conjugatable_okurigana_stem
    from jpn_text_processing.starts_with_okurigana_conjugation import starts_with_okurigana_conjugation, OkuriResults

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

# Include う just for the special case of 秘蔵[ひぞ]っ子[こ]
SMALL_TSU_POSSIBLE_HIRAGANA = ["つ", "ち", "く", "き", "う", "り", "ん"]

HIRAGANA_RE = "([ぁ-ん])"

ALL_MORA = [
    # First the two kana mora, so that they are matched first
    "くぃ", "きゃ", "きゅ", "きぇ", "きょ", "ぐぃ", "ご",
    "ぎゃ", "ぎゅ", "ぎぇ", "ぎょ", "すぃ", "しゃ", "しゅ", "しぇ", "しょ",
    "ずぃ", "じゃ", "じゅ", "じぇ", "じょ", "てぃ", "とぅ",
    "ちゃ", "ちゅ", "ちぇ", "ちょ", "でぃ", "どぅ", "ぢゃ", "でゅ",
    "ぢゅ", "ぢぇ", "ぢょ", "つぁ", "つぃ", "つぇ", "つぉ", "づぁ", "づぃ", "づぇ", "づぉ",
    "ひぃ", "ほぅ", "ひゃ", "ひゅ", "ひぇ", "ひょ", "びぃ", "ぼ",
    "びゃ", "びゅ", "びぇ", "びょ", "ぴぃ", "ぴゃ", "ぴゅ", "ぴぇ", "ぴょ",
    "ふぁ", "ふぃ", "ふぇ", "ふぉ", "ゔぁ", "ゔぃ", "ゔ", "ゔぇ", "ゔぉ", "ぬぃ", "の",
    "にゃ", "にゅ", "にぇ", "にょ", "むぃ", "みゃ", "みゅ", "みぇ", "みょ",
    "るぃ", "りゃ", "りゅ", "りぇ", "りょ",
    "いぇ",
    # Then single kana mora
    "か", "く", "け", "こ", "き", "が", "ぐ", "げ", "ご",
    "ぎ", "さ", "す", "せ", "そ", "し",
    "ざ", "ず", "づ", "ぜ", "ぞ", "じ", "ぢ", "た", "とぅ",
    "て", "と", "ち", "だ", "で", "ど", "ぢ",
    "つ", "づ", "は",
    "へ", "ほ", "ひ", "ば", "ぶ", "べ", "ぼ", "ぼ",
    "び", "ぱ", "ぷ", "べ", "ぽ", "ぴ",
    "ふ", "ゔぃ", "ゔ", "な", "ぬ", "ね", "の",
    "に", "ま", "む", "め", "も", "み",
    "ら", "る", "れ", "ろ", "り", "あ", "い", "う", "え", "お", "や",
    "ゆ", "よ", "わ", "ゐ", "ゑ", "を"
]

ALL_MORA_RE = "|".join(ALL_MORA)
ALL_MORA_REC = re.compile(rf"({ALL_MORA_RE})")

# Regex matching any kanji characters
# Include the kanji repeater punctuation as something that will be cleaned off
# Also include numbers as they are sometimes used in furigana
KANJI_RE = "([\d々\u4e00-\u9faf\u3400-\u4dbf]+)"
KANJI_REC = re.compile(rf"{KANJI_RE}")
# Same as above but allows for being empty
KANJI_RE_OPT = "([\d々\u4e00-\u9faf\u3400-\u4dbf]*)"

# Regex matching any furigana
FURIGANA_RE = " ?([^ >]+?)\[(.+?)\]"
FURIGANA_REC = re.compile(rf"{FURIGANA_RE}")

# Regex matching any kanji and furigana + hiragana after the furigana
KANJI_AND_FURIGANA_AND_OKURIGANA_RE = "([\d々\u4e00-\u9faf\u3400-\u4dbf]+)\[(.+?)\]([ぁ-ん]*)"
KANJI_AND_FURIGANA_AND_OKURIGANA_REC = re.compile(rf"{KANJI_AND_FURIGANA_AND_OKURIGANA_RE}")

# Regex for lone kanji with some hiragana to their right, then some kanji,
# then furigana that includes the hiragana in the middle
# This is used to match cases of furigana used for　kunyomi compound words with
# okurigana in the middle. For example
# (1) 消え去[きえさ]る
# (2) 隣り合わせ[となりあわせ]
# (3) 歯止め[はどめ]
OKURIGANA_MIX_CLEANING_RE = re.compile(rf"""
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
""", re.VERBOSE)


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
    result = f'{kanji1}[{furigana1}]{hiragana1}'
    if furigana2:
        result += f'{kanji2}[{furigana2}]{hiragana2}'
    return result


def re_match_from_right(text):
    return re.compile(rf"(.*)({text})(.*?)$")


def re_match_from_left(text):
    return re.compile(rf"^(.*?)({text})(.*)$")


def re_match_from_middle(text):
    return re.compile(rf"^(.*?)({text})(.*?)$")


def onyomi_replacer(match):
    """
    re.sub replacer function for onyomi used with the above regexes
    """
    return f'{match.group(1)}<b>{to_katakana(match.group(2))}</b>{match.group(3)}'


def kunyomi_replacer(match):
    """
    re.sub replacer function for kunyomi used with the above regexes
    """
    return f'{match.group(1)}<b>{match.group(2)}</b>{match.group(3)}'


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
        return f'{furigana}[{kanji}]'

    return re.sub(FURIGANA_RE, bracket_reverser, text.replace("&nbsp;", " "))


# Arg typing
LEFT = "left"
RIGHT = "right"
MIDDLE = "middle"
WHOLE = "whole"
Edge: str = Union[LEFT, RIGHT, MIDDLE, WHOLE]


class WordData(TypedDict):
    """
    TypedDict for data about a single word that was matched in the text for the kanji_to_highlight
    """
    kanji_pos: int  # position of the kanji_to_highlight in the word
    kanji_count: int  # number of kanji in the word
    word: str  # the word itself
    furigana: str  # the furigana for the word
    okurigana: str  # the okurigana for the word
    edge: Edge  # Where in the word the kanji_to_highlight is at


class HighlightArgs(TypedDict):
    """
    TypedDict for the base arguments passed to kana_highlight as these get passed around a lot
    """
    text: str
    onyomi: str
    kunyomi: str
    kanji_to_highlight: str


class MainResult(TypedDict):
    """
    TypedDict for the result of the onyomi or kunyomi match check
    """
    text: str
    type: Literal["onyomi", "kunyomi", "none"]


class FinalResult(TypedDict):
    """
    TypedDict for the final result of the onyomi or kunyomi match check
    """
    furigana: str
    okurigana: str
    rest_kana: str
    left_word: str
    middle_word: str
    right_word: str
    edge: Edge


REPLACED_FURIGANA_MIDDLE_RE = re.compile(r'^(.+)<b>(.+)</b>(.+)$')
REPLACED_FURIGANA_RIGHT_RE = re.compile(r'^(.+)<b>(.+)</b>$')
REPLACED_FURIGANA_LEFT_RE = re.compile(r'^<b>(.+)</b>(.+)$')


class FuriganaParts(TypedDict):
    """
    TypedDict for the parts of the furigana that were matched
    """
    has_highlight: bool
    left_furigana: Optional[str]
    middle_furigana: Optional[str]
    right_furigana: Optional[str]


def get_furigana_parts(furigana: str, edge: Edge):
    log(f"\nget_furigana_parts - furigana: {furigana}, edge: {edge}")
    result = {
        "has_highlight": '<b>' in furigana,
        "left_furigana": None,
        "middle_furigana": None,
        "right_furigana": None,
    }
    if edge == WHOLE:
        return result
    if edge == MIDDLE:
        match = REPLACED_FURIGANA_MIDDLE_RE.match(furigana)
        if match is None:
            return result
        result["left_furigana"] = match.group(1)
        result["middle_furigana"] = match.group(2)
        result["right_furigana"] = match.group(3)
        return result
    if edge == RIGHT:
        match = REPLACED_FURIGANA_RIGHT_RE.match(furigana)
        if match is None:
            return result
        result["left_furigana"] = match.group(1)
        result["middle_furigana"] = None
        result["right_furigana"] = match.group(2)
        return result
    if edge == LEFT:
        match = REPLACED_FURIGANA_LEFT_RE.match(furigana)
        if match is None:
            return result
        result["left_furigana"] = match.group(1)
        result["middle_furigana"] = None
        result["right_furigana"] = match.group(2)
        return result


FuriReconstruct = Literal["furigana", "furikanji", "kana_only"]


def reconstruct_furigana(
        final_result: FinalResult,
        reconstruct_type: FuriReconstruct = "furigana",
) -> str:
    """
    Reconstruct the furigana from the final result
    :param final_result: The final result of the onyomi or kunyomi match check
    :param reconstruct_type: Return the furigana with the kanji and furigana highlighted,
    :return: The reconstructed furigana with the kanji and that kanji's furigana highlighted
    """
    log(f"\nreconstruct_furigana - final_result: {final_result}, reconstruct_type: {reconstruct_type}")
    furigana = final_result.get("furigana")
    okurigana = final_result.get("okurigana")
    rest_kana = final_result.get("rest_kana")
    left_word = final_result.get("left_word")
    middle_word = final_result.get("middle_word")
    right_word = final_result.get("right_word")
    edge = final_result.get("edge")

    furigana_parts = get_furigana_parts(furigana, edge)
    log(f"\nreconstruct_furigana edge: {edge}, furigana_parts: {furigana_parts}")

    has_highlight = furigana_parts.get("has_highlight")
    left_furigana = furigana_parts.get("left_furigana")
    middle_furigana = furigana_parts.get("middle_furigana")
    right_furigana = furigana_parts.get("right_furigana")

    if not has_highlight:
        log("\nreconstruct_furigana - no highlight")
        # There was no match found during onyomi and kunyomi processing, so no <b> tags
        # we can just construct the furigana without splitting it
        if reconstruct_type == "kana_only":
            return f'{furigana}{okurigana}{rest_kana}'
        if reconstruct_type == "furikanji":
            return f' {furigana}[{right_word}{middle_word}{left_word}]{okurigana}{rest_kana}'
        return f' {left_word}{middle_word}{right_word}[{furigana}]{okurigana}{rest_kana}'

    if edge == WHOLE:
        # Same as above except we add the <b> tags around the whole thing
        # First remove <b> tags from the furigana
        furigana = re.sub(r'<b>|</b>', '', furigana)
        if reconstruct_type == "kana_only":
            return f'<b>{furigana}{okurigana}</b>{rest_kana}'
        if reconstruct_type == "furikanji":
            return f'<b> {furigana}[{right_word}{middle_word}{left_word}]{okurigana}</b>{rest_kana}'
        return f'<b> {left_word}{middle_word}{right_word}[{furigana}]{okurigana}</b>{rest_kana}'

    # There is highlighting, we need to split the furigana and word into three parts and assemble them
    result = ""
    parts = [
        # The furigana and word parts should match exactly;
        # when one is missing so is the other
        (left_word, left_furigana, LEFT),
        (middle_word, middle_furigana, MIDDLE),
        (right_word, right_furigana, RIGHT),
    ]
    for word, word_furigana, word_edge in parts:
        log(f"\nreconstruct_furigana - word: {word}, word_furigana: {word_furigana}, word_edge: {word_edge}")
        if word and word_furigana:
            if reconstruct_type == "kana_only":
                part = f'{word_furigana}'
            elif reconstruct_type == "furikanji":
                part = f' {word_furigana}[{word}]'
            else:
                part = f' {word}[{word_furigana}]'
            # If this is the edge that was matched, add the bold tags while
            # removing the existing ones in the furigana
            part = re.sub(r'<b>|</b>', '', part)
            if word_edge == RIGHT:
                # If we're at the end, add the okurigana
                part += okurigana
            if edge == word_edge:
                # Finally, add the highlighting if this is the edge that was matched
                part = f'<b>{part}</b>'
            result += part
    return f'{result}{rest_kana}'


LOG = False

def log(*args):
    if LOG:
        print(*args)


def process_readings(
        highlight_args: HighlightArgs,
        word_data: WordData,
        return_on_or_kun_match_only: bool = False,
        show_error_message: Callable = print
) -> (MainResult, str, str):
    """
    Function that processes furigana by checking all possible onyomi and kunyomi readings on it
    Either returns the furigana as-is when there is no match or modifies the furigana by
    adding <b> tags around the part that matches the reading

    :param highlight_args: dict, the base arguments passed to kana_highlight
    :param word_data: dict, all the data about the word that was matched
    :param return_on_or_kun_match_only: bool, return [True, False] if an onyomi match is found
        and [False, True] if a kunyomi match is found
    :param show_error_message: Callable, function to call when an error message is needed
    :return: string, the modified furigana
        or (True, False) / (False, True) if return_on_or_kun_match_only
    """
    target_furigana_section = get_target_furigana_section(
        word_data.get("furigana"),
        word_data.get("edge"),
        show_error_message
    )
    if target_furigana_section is None:
        return highlight_args.get("text"), "", word_data.get("okurigana")

    onyomi_match = check_onyomi_readings(
        highlight_args.get("onyomi"),
        word_data.get("furigana"),
        target_furigana_section,
        word_data.get("edge"),
        return_on_or_kun_match_only
    )
    if onyomi_match["type"] == "onyomi":
        return onyomi_match, "", word_data.get("okurigana")

    kunyomi_results = check_kunyomi_readings(
        highlight_args.get("kunyomi"),
        word_data.get("furigana"),
        target_furigana_section,
        word_data.get("edge"),
        return_on_or_kun_match_only
    )
    log(f"\nkunyomi_results: {kunyomi_results}, word_data: {word_data}, kana_highlight: {highlight_args}")
    if kunyomi_results["type"] == "kunyomi" and word_data["edge"] in [RIGHT, WHOLE]:
        okurigana = word_data.get("okurigana")
        okurigana_to_highlight = ""
        partial_okuri = None
        partial_okuri_rest = None
        rest_kana = okurigana
        kunyomi_readings = iter(highlight_args.get("kunyomi").split("、"))
        while not okurigana_to_highlight and (next_kunyomi := next(kunyomi_readings, None)):
            log(f"\ncheck_kunyomi_readings - okurigana: {not okurigana_to_highlight}, next_kunyomi: {next_kunyomi}")
            try:
                log(f"\ncheck_kunyomi_readings while - next_kunyomi: {next_kunyomi}")
                kunyomi_reading, kunyomi_okurigana = next_kunyomi.split(".")
            except ValueError:
                continue
            res = check_okurigana_for_kunyomi_inflection(
                kunyomi_okurigana, kunyomi_reading, word_data, highlight_args
            )
            if res.result == 'partial_okuri' or res.result == 'empty_okuri':
                # If we only got a partial or empty okurigana match, continue looking
                # in case we get a full match instead
                partial_okuri = res.okurigana
                partial_okuri_rest = res.rest_kana
                log(f"\ncheck_kunyomi_readings while got a partial_okuri: {partial_okuri}, rest_kana: {partial_okuri_rest}")
                continue
            if res.result == 'full_okuri':
                log(f"\ncheck_kunyomi_readings while got a full_okuri: {res.okurigana}, rest_kana: {res.rest_kana}")
                okurigana_to_highlight = res.okurigana
                rest_kana = res.rest_kana
        if partial_okuri and not okurigana_to_highlight:
            log(f"\ncheck_kunyomi_readings while final partial_okuri: {partial_okuri}, rest_kana: {partial_okuri_rest}")
            okurigana_to_highlight = partial_okuri
            rest_kana = partial_okuri_rest
        log(f"\ncheck_kunyomi_readings while result - okurigana: {okurigana_to_highlight}, rest_kana: {rest_kana}")
        return kunyomi_results, okurigana_to_highlight, rest_kana

    if kunyomi_results["type"] == "kunyomi":
        return kunyomi_results, "", word_data.get("okurigana")

    kanji_count = word_data.get("kanji_count")
    kanji_pos = word_data.get("kanji_pos")

    if kanji_count is None or kanji_pos is None:
        show_error_message(
            "Error in kana_highlight[]: process_readings() called with no kanji_count or kanji_pos specified")
        return {"text": word_data.get("furigana"), "type": "none"}, "", word_data.get("okurigana")

    return handle_jukujigun_case(word_data), "", word_data.get("okurigana")


def get_target_furigana_section(
        furigana: str,
        edge: Edge,
        show_error_message: Callable
):
    """
    Function that returns the part of the furigana that should be matched against the onyomi or kunyomi
    :param furigana: string, the furigana to process
    :param edge: string, [left, right, middle, whole], the part of the furigana to match
        against the onyomi or kunyomi
    :param show_error_message: Callable, function to call when an error message is needed
    :return: string, the part of the furigana that should be matched against the onyomi or kunyomi
    """
    if edge == WHOLE:
        # Highlight the whole furigana
        return furigana
    if edge == LEFT:
        # Leave out the last character of the furigana
        return furigana[:-1]
    if edge == RIGHT:
        # Leave out the first character of the furigana
        return furigana[1:]
    if edge == MIDDLE:
        # Leave out both the first and last characters of the furigana
        return furigana[1:-1]
    show_error_message(
        "Error in kana_highlight[]: process_readings() called with no edge specified")
    return None


def check_onyomi_readings(
        onyomi: str,
        furigana: str,
        target_furigana_section: str,
        edge: Edge,
        return_on_or_kun_match_only: bool
) -> MainResult:
    """
    Function that checks the onyomi readings against the target furigana section
    
    :param onyomi: string, the onyomi readings for the kanji
    :param furigana: string, the furigana to process
    :param target_furigana_section: string, the part of the furigana that should be matched against the onyomi
    The following passed to replace_onyomi_match
    :param edge: string, [left, right, middle, whole], the part of the furigana to match
    :param return_on_or_kun_match_only: bool

    :return: string, the modified furigana
      or [True, False] when return_on_or_kun_match_only
    """
    onyomi_readings = onyomi.split("、")
    # order readings by length so that we try to match the longest reading first
    onyomi_readings.sort(key=len, reverse=True)

    for onyomi_reading in onyomi_readings:
        # remove text in () in the reading
        onyomi_reading = re.sub(r"\(.*?\)", "", onyomi_reading).strip()
        # Convert the onyomi to hiragana since the furigana is in hiragana
        onyomi_reading = to_hiragana(onyomi_reading)
        if onyomi_reading in target_furigana_section:
            log(f"\n1 onyomi_reading: {onyomi_reading}")
            if return_on_or_kun_match_only:
                return {"text": "", "type": "onyomi"}
            return {"text": replace_onyomi_match(
                furigana,
                onyomi_reading,
                edge,
            ), "type": "onyomi"}
        # The reading might have a match with a changed kana like シ->ジ, フ->プ, etc.
        # This only applies to the first kana in the reading and if the reading isn't a single kana
        if len(onyomi_reading) != 1 and onyomi_reading[0] in HIRAGANA_CONVERSION_DICT:
            for onyomi_kana in HIRAGANA_CONVERSION_DICT[onyomi_reading[0]]:
                converted_onyomi = onyomi_reading.replace(onyomi_reading[0], onyomi_kana, 1)
                if converted_onyomi in target_furigana_section:
                    log(f"\n2 converted_onyomi: {converted_onyomi}")
                    if return_on_or_kun_match_only:
                        return {"text": "", "type": "onyomi"}
                    return {"text": replace_onyomi_match(
                        furigana,
                        converted_onyomi,
                        edge,
                    ), "type": "onyomi"}
        # Then also check for small tsu conversion of some consonants
        # this only happens in the last kana of the reading
        for tsu_kana in SMALL_TSU_POSSIBLE_HIRAGANA:
            if onyomi_reading[-1] == tsu_kana:
                converted_onyomi = onyomi_reading[:-1] + "っ"
                if converted_onyomi in target_furigana_section:
                    log(f"\n3 converted_onyomi: {converted_onyomi}")
                    if return_on_or_kun_match_only:
                        return {"text": "", "type": "onyomi"}
                    return {"text": replace_onyomi_match(
                        furigana,
                        converted_onyomi,
                        edge,
                    ), "type": "onyomi"}
    return {"text": "", "type": "none"}


def replace_onyomi_match(
        furigana: str,
        onyomi_that_matched: str,
        edge: Edge,
):
    """
    Function that replaces the furigana with the onyomi reading that matched
    :param furigana: string, the furigana to process
    :param onyomi_that_matched: string, the onyomi reading that matched
    :param edge: string, [left, right, middle, whole], the part of the furigana to match

    :return: string, the modified furigana
    """
    if edge == RIGHT:
        reg = re_match_from_right(onyomi_that_matched)
    elif edge == LEFT:
        reg = re_match_from_left(onyomi_that_matched)
    else:
        reg = re_match_from_middle(onyomi_that_matched)
    return re.sub(reg, onyomi_replacer, furigana)


def check_okurigana_for_kunyomi_inflection(
        kunyomi_okurigana: str,
        kunyomi_reading: str,
        word_data: WordData,
        highlight_args: HighlightArgs
) -> OkuriResults:
    """
    Function that checks the okurigana for a match with the kunyomi okurigana
    :param kunyomi_okurigana: string, the okurigana from the kunyomi reading
    :param word_data: dict, all the data about the word that was matched
    :param highlight_args: dict, the base arguments passed to kana_highlight
    :return: (string, string) the okurigana that should be highlighted and the rest of the okurigana
    """
    # Kana text occurring after the kanji in the word, may not be okurigana and can
    # contain other kana after the okurigana
    maybe_okuri_text = word_data.get("okurigana")
    log(f"\ncheck okurigana 0 - kunyomi_okurigana: {kunyomi_okurigana}, maybe_okurigana: {maybe_okuri_text}")

    if not kunyomi_okurigana or not maybe_okuri_text:
        return OkuriResults("", "", "no_okuri")

    # Simple case, exact match, no need to check conjugations
    if kunyomi_okurigana == maybe_okuri_text:
        return OkuriResults(kunyomi_okurigana, "", "full_okuri")

    # Check what kind of inflections we should be looking for from the kunyomi okurigana
    conjugatable_stem = get_conjugatable_okurigana_stem(kunyomi_okurigana)
    log(f"\ncheck okurigana 1 - conjugatable_stem: {conjugatable_stem}")
    if conjugatable_stem is None or not maybe_okuri_text.startswith(conjugatable_stem):
        log(f"\ncheck okurigana 2 - no conjugatable_stem")
        # Not a verb or i-adjective, so just check for an exact match within the okurigana
        if maybe_okuri_text.startswith(kunyomi_okurigana):
            log(f"\ncheck okurigana 3 - maybe_okuri_text: {maybe_okuri_text}")
            return OkuriResults(kunyomi_okurigana, maybe_okuri_text[len(kunyomi_okurigana):], "full_okuri")
        log(f"\ncheck okurigana 4 - no match")
        return OkuriResults("", maybe_okuri_text, "no_okuri")

    # Remove the conjugatable_stem from maybe_okurigana
    trimmed_maybe_okuri = maybe_okuri_text[len(conjugatable_stem):]
    log(f"\ncheck okurigana 5 - trimmed_maybe_okuri: {trimmed_maybe_okuri}")

    # Then check if that contains a conjugation for what we're looking for
    conjugated_okuri, rest, return_type = starts_with_okurigana_conjugation(
        trimmed_maybe_okuri,
        kunyomi_okurigana,
        highlight_args["kanji_to_highlight"],
        kunyomi_reading,
    )
    log(f"\ncheck okurigana 6 - conjugated_okuri: {conjugated_okuri}, rest: {rest}, return_type: {return_type}")

    if return_type != "no_okuri":
        log(f"\ncheck okurigana 7 - result: {conjugatable_stem + conjugated_okuri}, rest: {rest}")
        # remember to add the stem back!
        return OkuriResults(conjugatable_stem + conjugated_okuri, rest, return_type)

    # No match, this text doesn't contain okurigana for the kunyomi word
    log(f"\ncheck okurigana 8 - no match")
    return OkuriResults("", maybe_okuri_text, "no_okuri")


def check_kunyomi_readings(
        kunyomi: str,
        furigana: str,
        target_furigana_section: str,
        edge: Edge,
        return_on_or_kun_match_only: bool
) -> MainResult:
    """
    Function that checks the kunyomi readings against the target furigana section and okurigana

    :param kunyomi: string, the kunyomi readings for the kanji
    :param furigana: string, the furigana to process
    :param target_furigana_section: string, the part of the furigana that should be matched against the kunyomi
    The following passed to replace_kunyomi_match
    :param edge: string, [left, right, middle, whole], the part of the furigana to match
        against the onyomi or kunyomi
    :param return_on_or_kun_match_only: bool

    :return: Result dict with the modified furigana
    """
    kunyomi_readings = kunyomi.split("、")
    for kunyomi_reading in kunyomi_readings:
        # Split the reading into the stem and the okurigana
        kunyomi_stem = kunyomi_reading
        if '.' in kunyomi_reading:
            try:
                kunyomi_stem, _ = kunyomi_reading.split(".")
            except ValueError:
                log(f"\nError in kana_highlight[]: kunyomi contained multiple dots: {kunyomi_reading}")
                return {"text": furigana, "type": "kunyomi"}

        # For kunyomi we just check for a match with the stem
        if kunyomi_stem in target_furigana_section:
            log(f"\n1 kunyomi_stem: {kunyomi_stem}")
            if return_on_or_kun_match_only:
                return {"text": "", "type": "kunyomi"}
            return replace_kunyomi_match(
                furigana,
                kunyomi_stem,
                edge,
            )

        # Also check for changed kana
        if kunyomi_stem[0] in HIRAGANA_CONVERSION_DICT:
            for kunyomi_kana in HIRAGANA_CONVERSION_DICT[kunyomi_stem[0]]:
                converted_kunyomi = kunyomi_stem.replace(kunyomi_stem[0], kunyomi_kana, 1)
                if converted_kunyomi in target_furigana_section:
                    log(f"\n2 converted_kunyomi: {converted_kunyomi}")
                    if return_on_or_kun_match_only:
                        return {"text": "", "type": "kunyomi"}
                    return replace_kunyomi_match(
                        furigana,
                        converted_kunyomi,
                        edge,
                    )

        # Then also check for small tsu conversion of some consonants
        # this only happens in the last kana of the reading
        for tsu_kana in SMALL_TSU_POSSIBLE_HIRAGANA:
            if kunyomi_stem[-1] == tsu_kana:
                converted_kunyomi = kunyomi_stem[:-1] + "っ"
                if converted_kunyomi in target_furigana_section:
                    log(f"\n3 converted_kunyomi: {converted_kunyomi}")
                    if return_on_or_kun_match_only:
                        return {"text": "", "type": "kunyomi"}
                    return replace_kunyomi_match(
                        furigana,
                        converted_kunyomi,
                        edge,
                    )
    log("\ncheck_kunyomi_readings - no match")
    return {"text": "", "type": "none"}


def replace_kunyomi_match(
        furigana: str,
        kunyomi_that_matched: str,
        edge: Edge,
):
    """
    Function that replaces the furigana with the kunyomi reading that matched
    :param furigana: string, the furigana to process
    :param kunyomi_that_matched: string, the kunyomi reading that matched
    :param edge: string, [left, right, middle, whole], the part of the furigana to match
    :return: string, the modified furigana
    """
    if edge == RIGHT:
        reg = re_match_from_right(kunyomi_that_matched)
    elif edge == LEFT:
        reg = re_match_from_left(kunyomi_that_matched)
    else:
        reg = re_match_from_middle(kunyomi_that_matched)
    return {"text": re.sub(reg, kunyomi_replacer, furigana), "type": "kunyomi"}


def handle_jukujigun_case(
        word_data: WordData,
):
    """
    Function that handles the case of a jukujigun/ateji word where the furigana
    doesn't match the onyomi or kunyomi. Highlights the part of the furigana matching
    the kanji position
    :param word_data: dict, all the data about the word that was matched
    :return: Result dict with the modified furigana
    """
    kanji_count = word_data.get("kanji_count")
    kanji_pos = word_data.get("kanji_pos")
    furigana = word_data.get("furigana")

    # First split the word into mora
    mora_list = ALL_MORA_REC.findall(furigana)
    # Divide the mora by the number of kanji in the word
    mora_count = len(mora_list)
    mora_per_kanji = mora_count // kanji_count
    # Split the remainder evenly among the kanji, by adding one mora to each kanji until the remainder is 0
    remainder = mora_count % kanji_count
    new_furigana = ""
    cur_mora_index = 0
    for kanji_index in range(kanji_count):
        cur_mora_range_max = cur_mora_index + mora_per_kanji
        if remainder > 0:
            cur_mora_range_max += 1
            remainder -= 1
        if kanji_index == kanji_pos:
            new_furigana += "<b>"
        elif kanji_index == kanji_pos + 1:
            new_furigana += "</b>"

        for mora_index in range(cur_mora_index, cur_mora_range_max):
            new_furigana += mora_list[mora_index]

        if kanji_index == kanji_pos and kanji_index == kanji_count - 1:
            new_furigana += "</b>"
        cur_mora_index = cur_mora_range_max

    log(f"\nhandle_jukujigun_case - new_furigana: {new_furigana}")
    return {"text": new_furigana, "type": "kunyomi"}


def handle_whole_kanji_case(
        highlight_args,
        word: str,
        furigana: str,
        okurigana: str,
        show_error_message: Callable
) -> FinalResult:
    """
    The case when the whole word contains the kanji to highlight.
    So, either it's a single kanji word or the kanji is repeated.

    :param highlight_args: dict, the base arguments passed to kana_highlight
    :param word: string, the word
    :param furigana: string, the whole furigana for the word
    :param okurigana: string, possible okurigana following the furigana
    :param show_error_message: Callable, function to call when an error message is needed

    :return: string, the modified furigana entirely highlighted, additionally
        in katakana for onyomi
    """
    word_data = {
        "kanji_pos": 0,
        "kanji_count": 1,
        "furigana": furigana,
        "edge": WHOLE,
        "word": word,
        "okurigana": okurigana
    }
    result, okurigana_to_highlight, rest_kana = process_readings(
        highlight_args,
        word_data,
        return_on_or_kun_match_only=True,
        show_error_message=show_error_message,
    )
    log(f"\nhandle_whole_kanji_case - word: {word}, result: {result}, okurigana: {okurigana_to_highlight}, rest_kana: {rest_kana}")

    if result["type"] == "onyomi":
        # For onyomi matches the furigana should be in katakana
        final_furigana = f"<b>{to_katakana(furigana)}</b>"
    else:
        final_furigana = f"<b>{furigana}</b>"
    return {
        "furigana": final_furigana,
        "okurigana": okurigana_to_highlight,
        "rest_kana": rest_kana,
        "left_word": "",
        "middle_word": word,
        "right_word": "",
        "edge": WHOLE,
    }


def handle_partial_kanji_case(
        highlight_args: HighlightArgs,
        word: str,
        furigana: str,
        okurigana: str,
        show_error_message: Callable
) -> FinalResult:
    """
    The case when the word contains other kanji in addition to the kanji to highlight.
    Could be 2 or more kanji in the word.

    :param highlight_args: dict, the base arguments passed to kana_highlight
    :param word: string, the word that was matched for kanji_to_highlight
    :param furigana: string, the furigana for the word
    :param okurigana: string, possible okurigana following the furigana
    :param show_error_message: Callable, function to call when an error message is needed

    :return: string, the modified furigana with the kanji to highlight highlighted
    """
    kanji_to_highlight = highlight_args.get("kanji_to_highlight")

    kanji_pos = word.find(kanji_to_highlight)
    if kanji_pos == -1:
        # No match found, return the furigana as-is
        return {
            "furigana": furigana,
            "okurigana": okurigana,
            "rest_kana": "",
            "left_word": "",
            "middle_word": word,
            "right_word": "",
            "edge": WHOLE,
        }
    # Take of note of which side of the word the kanji is found on
    # 1. left edge, the furigana replacement has to begin on the left edge and can't end on the right edge
    # 2. right edge, the furigana replacement has to end on the right edge and can't begin on the left edge
    # 3. both (the word is just the kanji or the kanji is repeated), we can just highlight the whole furigana
    # 4. or middle, the furigana replacement can't begin on the left or end on the right
    kanji_in_left_edge = kanji_pos == 0
    kanji_in_right_edge = kanji_pos == len(word) - 1
    # We've already ruled out case 3. so, the middle case
    # is 4. where the kanji is in the middle of the word
    kanji_in_middle = not kanji_in_left_edge and not kanji_in_right_edge

    word_data = {
        "kanji_pos": kanji_pos,
        "kanji_count": len(word),
        "furigana": furigana,
        "edge": MIDDLE if kanji_in_middle else (LEFT if kanji_in_left_edge else RIGHT),
        "word": word,
        "okurigana": okurigana
    }

    main_result, okurigana_to_highlight, rest_kana = process_readings(
        highlight_args,
        word_data,
        show_error_message=show_error_message
    )

    # Determine the word split according to the edge so we can highlight the correct part
    if kanji_in_middle:
        left_word = word[:kanji_pos]
        middle_word = kanji_to_highlight
        right_word = word[kanji_pos + 1:]
    elif kanji_in_left_edge:
        left_word = kanji_to_highlight
        middle_word = ""
        right_word = word[kanji_pos + 1:]
    else:
        left_word = word[:kanji_pos]
        middle_word = ""
        right_word = kanji_to_highlight

    final_result = {
        "left_word": left_word,
        "middle_word": middle_word,
        "right_word": right_word,
        "edge": word_data["edge"],
    }

    furigana_replacement = main_result["text"]
    if okurigana_to_highlight:
        final_result["furigana"] = furigana_replacement
        final_result["okurigana"] = okurigana_to_highlight
        final_result["rest_kana"] = rest_kana
    else:
        final_result["furigana"] = furigana_replacement
        final_result["okurigana"] = ""
        final_result["rest_kana"] = rest_kana
    log(f"\nhandle_partial_kanji_case - final_result: {final_result}")
    return final_result


def kana_highlight(
        kanji_to_highlight: str,
        onyomi: str,
        kunyomi: str,
        text: str,
        return_type: FuriReconstruct = "kana_only",
        show_error_message: Callable = print,
) -> str:
    """
    Function that replaces the furigana of a kanji with the furigana that corresponds to the kanji's
    onyomi or kunyomi reading. The furigana is then highlighted with <b> tags.
    Text received could be a sentence or a single word with furigana.
    :param kanji_to_highlight: should be a single kanji character
    :param onyomi: onyomi reading of the kanji, separated by commas if there are multiple readings
    :param kunyomi: kunyomi reading of the kanji, separated by commas if there are multiple readings
        okurigana should be separated by a dot
    :param text: The text to process
    :param return_type: string. Return either normal furigana, reversed furigana AKA furikanji or
        remove the kanji and return only the kana
    :param show_error_message: Callable, function to call when an error message is needed
    :return: The text cleaned from any previous <b> tags and with the furigana highlighted with <b> tags
        when the furigana corresponds to the kanji_to_highlight
    """

    highlight_args = {
        "text": text,
        "onyomi": onyomi,
        "kunyomi": kunyomi,
        "kanji_to_highlight": kanji_to_highlight
    }

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
            # as it'd break the audio tag. But we know the text to the right is kanji (what is it doing
            # there next to a sound tag?) so we'll just leave it out anyway
            return furigana + okurigana

        if word in (kanji_to_highlight, f"{kanji_to_highlight}々"):
            final_result = handle_whole_kanji_case(highlight_args, word, furigana, okurigana, show_error_message)
        else:
            final_result = handle_partial_kanji_case(highlight_args, word, furigana, okurigana, show_error_message)
        # Construct the final return format
        return reconstruct_furigana(final_result, reconstruct_type=return_type)

    # Clean any potential mixed okurigana cases, turning them normal
    clean_text = OKURIGANA_MIX_CLEANING_RE.sub(okurigana_mix_cleaning_replacer, text)
    # Special case 秘蔵[ひぞ]っ子[こ] needs to be converted to 秘蔵[ひぞっ]子[こ]
    clean_text = clean_text.replace("秘蔵[ひぞ]っ", "秘蔵[ひぞっ]")
    processed_text = KANJI_AND_FURIGANA_AND_OKURIGANA_REC.sub(furigana_replacer, clean_text)
    # Clean any double spaces that might have been created by the furigana reconstruction
    # Including those right before a <b> tag as the space is added with those
    processed_text = re.sub(r" {2}", " ", processed_text)
    return re.sub(r" <b> ", "<b> ", processed_text)


def test(
        test_name,
        sentence,
        kanji,
        onyomi,
        kunyomi,
        expected_furigana: str = None,
        expected_furikanji: str = None,
        expected_kana_only: str = None,
):
    """
    Function that tests the kana_highlight function
    """
    cases = [
        ("furigana", expected_furigana),
        ("furikanji", expected_furikanji),
        ("kana_only", expected_kana_only),
    ]
    for return_type, expected in cases:
        if not expected:
            continue
        result = kana_highlight(
            kanji,
            onyomi,
            kunyomi,
            sentence,
            return_type,
        )
        try:
            assert result == expected
        except AssertionError:
            # Re-run with logging enabled to see what went wrong
            global LOG
            LOG = True
            kana_highlight(
                kanji,
                onyomi,
                kunyomi,
                sentence,
                return_type,
            )
            # Highlight the diff between the expected and the result
            print(f"""\033[91m{test_name}
Return type: {return_type}
\033[93mExpected: {expected}
\033[92mGot:      {result}
\033[0m""")
            # Stop testing here
            sys.exit(1)
        finally:
            LOG = False


def main():
    test(
        test_name="Should not incorrectly match onyomi twice 1/",
        kanji="視",
        onyomi="シ(漢)、ジ(呉)",
        kunyomi="み.る",
        # しちょうしゃ　has し in it twice but only the first one should be highlighted
        sentence="視聴者[しちょうしゃ]",
        expected_kana_only="<b>シ</b>ちょうしゃ",
        expected_furigana="<b> 視[シ]</b> 聴者[ちょうしゃ]",
        expected_furikanji="<b> シ[視]</b> ちょうしゃ[聴者]",
    )
    test(
        test_name="Should not incorrectly match onyomi twice 2/",
        kanji="儀",
        onyomi="ギ(呉)",
        kunyomi="のり、よ.い",
        # 　ぎょうぎ　has ぎ in it twice but only the first one should be highlighted
        sentence="行儀[ぎょうぎ]",
        expected_kana_only="ぎょう<b>ギ</b>",
        expected_furigana=" 行[ぎょう]<b> 儀[ギ]</b>",
        expected_furikanji=" ぎょう[行]<b> ギ[儀]</b>",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 1/",
        kanji="去",
        onyomi="キョ(漢)、コ(呉)",
        kunyomi="さ.る、ゆ.く、のぞ.く",
        # 消え去[きえさ]った　has え　in the middle of the kanji but った at the end is not included in the furigana
        sentence="団子[だんご]が 消え去[きえさ]った。",
        expected_kana_only="だんごが きえ<b>さった</b>。",
        expected_furigana=" 団子[だんご]が 消[き]え<b> 去[さ]った</b>。",
        expected_furikanji=" だんご[団子]が き[消]え<b> さ[去]った</b>。",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 2/",
        kanji="隣",
        onyomi="リン(呉)",
        kunyomi="とな.る、となり",
        # 隣り合わせ[となりあわせ]のまち　has り　in the middle and わせ　at the end of the group
        sentence="隣り合わせ[となりあわせ]の町[まち]。",
        expected_kana_only="<b>となり</b>あわせのまち。",
        expected_furigana="<b> 隣[とな]り</b> 合[あ]わせの 町[まち]。",
        expected_furikanji="<b> とな[隣]り</b> あ[合]わせの まち[町]。",
    )
    test(
        test_name="Matches word that uses the repeater 々 with rendaku 1/",
        kanji="国",
        onyomi="コク(呉)",
        kunyomi="くに",
        sentence="国々[くにぐに]の 関係[かんけい]が 深い[ふかい]。",
        expected_kana_only="<b>くにぐに</b>の かんけいが ふかい。",
        expected_furigana="<b> 国々[くにぐに]</b>の 関係[かんけい]が 深[ふか]い。",
        expected_furikanji="<b> くにぐに[国々]</b>の かんけい[関係]が ふか[深]い。",
    )
    test(
        test_name="Matches word that uses the repeater 々 with rendaku 2/",
        kanji="時",
        onyomi="ジ(呉)、シ(漢)",
        kunyomi="とき",
        sentence="時々[ときどき] 雨[あめ]が 降る[ふる]。",
        expected_kana_only="<b>ときどき</b> あめが ふる。",
        expected_furigana="<b> 時々[ときどき]</b> 雨[あめ]が 降[ふ]る。",
        expected_furikanji="<b> ときどき[時々]</b> あめ[雨]が ふ[降]る。",
    )
    test(
        test_name="Matches word that uses the repeater 々 with small tsu",
        kanji="刻",
        onyomi="コク(呉)",
        kunyomi="きざ.む、きざ.み、とき",
        sentence="刻々[こっこく]と 変化[へんか]する。",
        expected_kana_only="<b>コッコク</b>と へんかする。",
        expected_furigana="<b> 刻々[コッコク]</b>と 変化[へんか]する。",
        expected_furikanji="<b> コッコク[刻々]</b>と へんか[変化]する。",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 3/",
        kanji="止",
        onyomi="シ(呉)",
        kunyomi="と.まる、と.める、とど.める、とど.め、とど.まる、や.める、や.む、よ.す、さ.す",
        # A third edge case: there is only okurigana at the end
        sentence="歯止め[はどめ]",
        expected_kana_only="は<b>どめ</b>",
        expected_furigana=" 歯[は]<b> 止[ど]め</b>",
        expected_furikanji=" は[歯]<b> ど[止]め</b>",
    )
    test(
        test_name="Is able to match the same kanji occurring twice",
        kanji="閣",
        onyomi="カク(呉)",
        kunyomi="たかどの、たな",
        sentence="新[しん] 内閣[ないかく]の 組閣[そかく]が 発表[はっぴょう]された。",
        expected_kana_only="しん ない<b>カク</b>の そ<b>カク</b>が はっぴょうされた。",
        expected_furigana=" 新[しん] 内[ない]<b> 閣[カク]</b>の 組[そ]<b> 閣[カク]</b>が 発表[はっぴょう]された。",
        expected_furikanji=" しん[新] ない[内]<b> カク[閣]</b>の そ[組]<b> カク[閣]</b>が はっぴょう[発表]された。",
    )
    test(
        test_name="Is able to match the same kanji occurring twice with other using small tsu",
        kanji="国",
        onyomi="コク(呉)",
        kunyomi="くに",
        sentence="その2 国[こく]は 国交[こっこう]を 断絶[だんぜつ]した。",
        expected_kana_only="その2 <b>コク</b>は <b>コッ</b>こうを だんぜつした。",
        expected_furigana="その2<b> 国[コク]</b>は<b> 国[コッ]</b> 交[こう]を 断絶[だんぜつ]した。",
        expected_furikanji="その2<b> コク[国]</b>は<b> コッ[国]</b> こう[交]を だんぜつ[断絶]した。",

    )
    test(
        test_name="Is able to pick the right reading when there is multiple matches",
        kanji="靴",
        onyomi="カ(漢)、ケ(呉)",
        kunyomi="くつ",
        # ながぐつ　has が (onyomi か match) and ぐつ (kunyomi くつ) as matches
        sentence="お 前[まえ]いつも 長靴[ながぐつ]に 傘[かさ]さしてキメーんだよ！！",
        expected_kana_only="お まえいつも なが<b>ぐつ</b>に かささしてキメーんだよ！！",
        expected_furigana="お 前[まえ]いつも 長[なが]<b> 靴[ぐつ]</b>に 傘[かさ]さしてキメーんだよ！！",
        expected_furikanji="お まえ[前]いつも なが[長]<b> ぐつ[靴]</b>に かさ[傘]さしてキメーんだよ！！",
    )
    test(
        test_name="Should match reading in 4 kanji compound word",
        kanji="必",
        onyomi="ヒツ(漢)、ヒチ(呉)",
        kunyomi="かなら.ず",
        sentence="見敵必殺[けんてきひっさつ]の 指示[しじ]もないのに 戦闘[せんとう]は 不自然[ふしぜん]。",
        expected_kana_only="けんてき<b>ヒッ</b>さつの しじもないのに せんとうは ふしぜん。",
        expected_furigana=" 見敵[けんてき]<b> 必[ヒッ]</b> 殺[さつ]の 指示[しじ]もないのに 戦闘[せんとう]は 不自然[ふしぜん]。",
        expected_furikanji=" けんてき[見敵]<b> ヒッ[必]</b> さつ[殺]の しじ[指示]もないのに せんとう[戦闘]は ふしぜん[不自然]。",
    )
    test(
        test_name="Should match furigana for romaji numbers",
        kanji="賊",
        onyomi="ゾク(呉)、ソク(漢)",
        kunyomi="わるもの、そこ.なう",
        sentence="海賊[かいぞく]たちは ７[なな]つの 海[うみ]を 航海[こうかい]した。",
        expected_kana_only="かい<b>ゾク</b>たちは ななつの うみを こうかいした。",
        expected_furigana=" 海[かい]<b> 賊[ゾク]</b>たちは ７[なな]つの 海[うみ]を 航海[こうかい]した。",
        expected_furikanji=" かい[海]<b> ゾク[賊]</b>たちは なな[７]つの うみ[海]を こうかい[航海]した。",
    )
    test(
        test_name="Should match the full reading match when there are multiple",
        kanji="由",
        onyomi="ユ(呉)、ユウ(漢)、ユイ(慣)",
        kunyomi="よし、よ.る、なお",
        # Both ゆ and ゆい are in the furigana but the correct match is ゆい
        sentence="彼女[かのじょ]は 由緒[ゆいしょ]ある 家柄[いえがら]の 出[で]だ。",
        expected_kana_only="かのじょは <b>ユイ</b>しょある いえがらの でだ。",
        expected_furigana=" 彼女[かのじょ]は<b> 由[ユイ]</b> 緒[しょ]ある 家柄[いえがら]の 出[で]だ。",
        expected_furikanji=" かのじょ[彼女]は<b> ユイ[由]</b> しょ[緒]ある いえがら[家柄]の で[出]だ。",
    )
    test(
        test_name="small tsu 1/",
        kanji="剔",
        onyomi="テキ(漢)、チャク(呉)",
        kunyomi="えぐ.る、そ.る、のぞ.く",
        sentence="剔抉[てっけつ]",
        expected_kana_only="<b>テッ</b>けつ",
        expected_furigana="<b> 剔[テッ]</b> 抉[けつ]",
        expected_furikanji="<b> テッ[剔]</b> けつ[抉]",
    )
    test(
        test_name="small tsu 2/",
        kanji="一",
        onyomi="イチ(漢)、イツ(呉)",
        kunyomi="ひと、ひと.つ、はじ.め",
        sentence="一見[いっけん]",
        expected_kana_only="<b>イッ</b>けん",
        expected_furigana="<b> 一[イッ]</b> 見[けん]",
        expected_furikanji="<b> イッ[一]</b> けん[見]",
    )
    test(
        test_name="small tsu 3/",
        kanji="各",
        onyomi="カク(漢)、カ(呉)",
        kunyomi="おのおの",
        sentence="各国[かっこく]",
        expected_kana_only="<b>カッ</b>こく",
        expected_furigana="<b> 各[カッ]</b> 国[こく]",
        expected_furikanji="<b> カッ[各]</b> こく[国]",
    )
    test(
        test_name="small tsu 4/",
        kanji="吉",
        onyomi="キチ(漢)、キツ(呉)",
        kunyomi="よし",
        sentence="吉兆[きっちょう]",
        expected_kana_only="<b>キッ</b>ちょう",
        expected_furigana="<b> 吉[キッ]</b> 兆[ちょう]",
        expected_furikanji="<b> キッ[吉]</b> ちょう[兆]",
    )
    test(
        test_name="small tsu 5/",
        kanji="蔵",
        onyomi="ゾウ(漢)、ソウ(呉)",
        kunyomi="くら",
        sentence="秘蔵っ子[ひぞっこ]",
        expected_kana_only="ひ<b>ゾッ</b>こ",
        expected_furigana=" 秘[ひ]<b> 蔵[ゾッ]</b> 子[こ]",
        expected_furikanji=" ひ[秘]<b> ゾッ[蔵]</b> こ[子]",
    )
    test(
        test_name="small tsu 6/",
        kanji="尻",
        onyomi="コウ(呉)",
        kunyomi="しり",
        sentence="尻尾[しっぽ]",
        expected_kana_only="<b>しっ</b>ぽ",
        expected_furigana="<b> 尻[しっ]</b> 尾[ぽ]",
        expected_furikanji="<b> しっ[尻]</b> ぽ[尾]",
    )
    test(
        test_name="small tsu 7/",
        kanji="呆",
        onyomi="ホウ(漢)、ボウ(慣)、ホ(呉)、タイ(慣)、ガイ(呉)",
        kunyomi="ほけ.る、ぼ.ける、あき.れる、おろか、おろ.か",
        sentence="呆気[あっけ]ない",
        expected_kana_only="<b>あっ</b>けない",
        expected_furigana="<b> 呆[あっ]</b> 気[け]ない",
        expected_furikanji="<b> あっ[呆]</b> け[気]ない",
    )
    test(
        test_name="small tsu 8/",
        kanji="甲",
        onyomi="コウ(漢)、カン(慣)、キョウ(呉)",
        kunyomi="きのえ、かぶと、よろい、つめ",
        sentence="甲冑[かっちゅう]の 試着[しちゃく]をお 願[ねが]いします｡",
        expected_kana_only="<b>カッ</b>ちゅうの しちゃくをお ねがいします｡",
        expected_furigana="<b> 甲[カッ]</b> 冑[ちゅう]の 試着[しちゃく]をお 願[ねが]いします｡",
        expected_furikanji="<b> カッ[甲]</b> ちゅう[冑]の しちゃく[試着]をお ねが[願]いします｡",
    )
    test(
        test_name="small tsu 9/",
        kanji="百",
        onyomi="ヒャク(呉)、ハク(漢)",
        kunyomi="もも",
        sentence="百貨店[ひゃっかてん]",
        expected_kana_only="<b>ヒャッ</b>かてん",
        expected_furigana="<b> 百[ヒャッ]</b> 貨店[かてん]",
        expected_furikanji="<b> ヒャッ[百]</b> かてん[貨店]",
    )
    test(
        test_name="Single kana reading conversion 1/",
        kanji="祖",
        # 祖 usually only lists ソ as the only onyomi
        onyomi="ソ(呉)、ゾ",
        kunyomi="おや、じじ、はじ.め",
        sentence="先祖[せんぞ]",
        expected_kana_only="せん<b>ゾ</b>",
        expected_furigana=" 先[せん]<b> 祖[ゾ]</b>",
        expected_furikanji=" せん[先]<b> ゾ[祖]</b>",
    )
    test(
        test_name="Single kana reading conversion 2/",
        kanji="来",
        onyomi="ライ(呉)、タイ",
        kunyomi="く.る、きた.る、きた.す、き.たす、き.たる、き、こ、こ.し、き.し",
        sentence="それは 私[わたし]たちの 日常生活[にちじょうせいかつ]の 仕来[しき]たりの １[ひと]つだ。",
        expected_kana_only="それは わたしたちの にちじょうせいかつの し<b>きたり</b>の ひとつだ。",
        expected_furigana="それは 私[わたし]たちの 日常生活[にちじょうせいかつ]の 仕[し]<b> 来[き]たり</b>の １[ひと]つだ。",
        expected_furikanji="それは わたし[私]たちの にちじょうせいかつ[日常生活]の し[仕]<b> き[来]たり</b>の ひと[１]つだ。",
    )
    test(
        test_name="Jukujigun test 大人 1/",
        kanji="大",
        onyomi="ダイ(呉)、タイ(漢)、タ(漢)、ダ(呉)",
        kunyomi="おお、おお.きい、おお.いに",
        sentence="大人[おとな] 達[たち]は 大[おお]きいですね",
        expected_kana_only="<b>おと</b>な たちは <b>おおきい</b>ですね",
        expected_furigana="<b> 大[おと]</b> 人[な] 達[たち]は<b> 大[おお]きい</b>ですね",
        expected_furikanji="<b> おと[大]</b> な[人] たち[達]は<b> おお[大]きい</b>ですね",
    )
    test(
        test_name="Jukujigun test 大人 2/",
        kanji="人",
        onyomi="ジン(漢)、ニン(呉)",
        kunyomi="ひと",
        sentence="大人[おとな] 達[たち]は 人々[ひとびと]の 中[なか]に いる。",
        expected_kana_only="おと<b>な</b> たちは <b>ひとびと</b>の なかに いる。",
        expected_furigana=" 大[おと]<b> 人[な]</b> 達[たち]は<b> 人々[ひとびと]</b>の 中[なか]に いる。",
        expected_furikanji=" おと[大]<b> な[人]</b> たち[達]は<b> ひとびと[人々]</b>の なか[中]に いる。",
    )
    test(
        test_name="Verb okurigana test 1/",
        kanji="来",
        onyomi="ライ(呉)、タイ",
        kunyomi="く.る、きた.る、きた.す、き.たす、き.たる、き、こ、こ.し、き.し",
        sentence="今[いま]に 来[きた]るべし",
        expected_kana_only="いまに <b>きたる</b>べし",
        expected_furigana=" 今[いま]に<b> 来[きた]る</b>べし",
        expected_furikanji=" いま[今]に<b> きた[来]る</b>べし",
    )
    test(
        test_name="Verb okurigana test 2/",
        kanji="書",
        onyomi="ショ(呉)",
        kunyomi="か.く、ふみ",
        sentence="日記[にっき]を 書[か]いた。",
        expected_kana_only="にっきを <b>かいた</b>。",
        expected_furigana=" 日記[にっき]を<b> 書[か]いた</b>。",
        expected_furikanji=" にっき[日記]を<b> か[書]いた</b>。",
    )
    test(
        test_name="Verb okurigana test 3/",
        kanji="話",
        onyomi="ワ(呉)",
        kunyomi="はな.す、はなし",
        sentence="友達[ともだち]と 話[はな]している。",
        expected_kana_only="ともだちと <b>はなして</b>いる。",
        expected_furigana=" 友達[ともだち]と<b> 話[はな]して</b>いる。",
        expected_furikanji=" ともだち[友達]と<b> はな[話]して</b>いる。",
    )
    test(
        test_name="Verb okurigana test 4/",
        kanji="聞",
        onyomi="ブン(漢)、モン(呉)",
        kunyomi="き.く、き.こえる",
        sentence="ニュースを 聞[き]きました。",
        expected_kana_only="ニュースを <b>ききました</b>。",
        expected_furigana="ニュースを<b> 聞[き]きました</b>。",
        expected_furikanji="ニュースを<b> き[聞]きました</b>。",
    )
    test(
        test_name="Verb okurigana test 5/",
        kanji="走",
        onyomi="ソウ(呉)",
        kunyomi="はし.る",
        sentence="公園[こうえん]で 走[はし]ろう。",
        expected_kana_only="こうえんで <b>はしろう</b>。",
        expected_furigana=" 公園[こうえん]で<b> 走[はし]ろう</b>。",
        expected_furikanji=" こうえん[公園]で<b> はし[走]ろう</b>。",
    )
    test(
        test_name="Verb okurigana test 6/",
        kanji="待",
        onyomi="タイ(呉)",
        kunyomi="ま.つ、もてな.す",
        sentence="友達[ともだち]を 待[ま]つ。",
        expected_kana_only="ともだちを <b>まつ</b>。",
        expected_furigana=" 友達[ともだち]を<b> 待[ま]つ</b>。",
        expected_furikanji=" ともだち[友達]を<b> ま[待]つ</b>。",
    )
    test(
        test_name="Verb okurigana test 7/",
        kanji="泳",
        onyomi="エイ(呉)",
        kunyomi="およ.ぐ",
        sentence="海[うみ]で 泳[およ]ぐ。",
        expected_kana_only="うみで <b>およぐ</b>。",
        expected_furigana=" 海[うみ]で<b> 泳[およ]ぐ</b>。",
        expected_furikanji=" うみ[海]で<b> およ[泳]ぐ</b>。",
    )
    test(
        test_name="Verb okurigana test 8/",
        kanji="作",
        onyomi="サク(漢)、サ(呉)",
        kunyomi="つく.る、つく.り、な.す",
        sentence="料理[りょうり]を 作[つく]る。",
        expected_kana_only="りょうりを <b>つくる</b>。",
        expected_furigana=" 料理[りょうり]を<b> 作[つく]る</b>。",
        expected_furikanji=" りょうり[料理]を<b> つく[作]る</b>。",
    )
    test(
        test_name="Verb okurigana test 9/",
        kanji="遊",
        onyomi="ユウ(漢)、ユ(呉)",
        kunyomi="あそ.ぶ、あそ.ばす、すさ.び、すさ.ぶ",
        sentence="子供[こども]と 遊[あそ]んでいるぞ。",
        expected_kana_only="こどもと <b>あそんで</b>いるぞ。",
        expected_furigana=" 子供[こども]と<b> 遊[あそ]んで</b>いるぞ。",
        expected_furikanji=" こども[子供]と<b> あそ[遊]んで</b>いるぞ。",
    )
    test(
        test_name="Verb okurigana test 10/",
        kanji="聞",
        onyomi="ブン(漢)、モン(呉)",
        # Both 聞く and 聞こえる will produce an okuri match but the correct should be 聞こえる
        kunyomi="き.く、き.こえる",
        sentence="音[おと]を 聞[き]こえたか？何[なに]も 聞[き]いていないよ",
        expected_kana_only="おとを <b>きこえた</b>か？なにも <b>きいて</b>いないよ",
        expected_furigana=" 音[おと]を<b> 聞[き]こえた</b>か？ 何[なに]も<b> 聞[き]いて</b>いないよ",
        expected_furikanji=" おと[音]を<b> き[聞]こえた</b>か？ なに[何]も<b> き[聞]いて</b>いないよ",
    )
    test(
        test_name="Adjective okurigana test 1/",
        kanji="悲",
        onyomi="ヒ(呉)",
        kunyomi="かな.しい、かな.しむ",
        sentence="彼[かれ]は 悲[かな]しくすぎるので、 悲[かな]しみの 悲[かな]しさを 悲[かな]しんでいる。",
        expected_kana_only="かれは <b>かなしく</b>すぎるので、 <b>かなしみ</b>の <b>かなしさ</b>を <b>かなしんで</b>いる。",
        expected_furigana=" 彼[かれ]は<b> 悲[かな]しく</b>すぎるので、<b> 悲[かな]しみ</b>の<b> 悲[かな]しさ</b>を<b> 悲[かな]しんで</b>いる。",
        expected_furikanji=" かれ[彼]は<b> かな[悲]しく</b>すぎるので、<b> かな[悲]しみ</b>の<b> かな[悲]しさ</b>を<b> かな[悲]しんで</b>いる。",
    )
    test(
        test_name="Adjective okurigana test 2/",
        kanji="青",
        onyomi="セイ(漢)、ショウ(呉)",
        kunyomi="あお.い",
        sentence="空[そら]が 青[あお]かったら、 青[あお]くない 海[うみ]に 行[い]こう",
        expected_kana_only="そらが <b>あおかったら</b>、 <b>あおくない</b> うみに いこう",
        expected_furigana=" 空[そら]が<b> 青[あお]かったら</b>、<b> 青[あお]くない</b> 海[うみ]に 行[い]こう",
        expected_furikanji=" そら[空]が<b> あお[青]かったら</b>、<b> あお[青]くない</b> うみ[海]に い[行]こう",
    )
    test(
        test_name="Adjective okurigana test 3/",
        kanji="高",
        onyomi="コウ(呉)",
        kunyomi="たか.い、たか、だか、たか.まる、たか.める、たか.ぶる",
        sentence="山[やま]が 高[たか]ければ、 高層[こうそう]ビルが 高[たか]めてと 高[たか]ぶり",
        expected_kana_only="やまが <b>たかければ</b>、 <b>コウ</b>そうビルが <b>たかめて</b>と <b>たかぶり</b>",
        expected_furigana=" 山[やま]が<b> 高[たか]ければ</b>、<b> 高[コウ]</b> 層[そう]ビルが<b> 高[たか]めて</b>と<b> 高[たか]ぶり</b>",
        expected_furikanji=" やま[山]が<b> たか[高]ければ</b>、<b> コウ[高]</b> そう[層]ビルが<b> たか[高]めて</b>と<b> たか[高]ぶり</b>",
    )
    test(
        test_name="Adjective okurigana test 4/",
        kanji="厚",
        onyomi="コウ(呉)",
        kunyomi="あつ.かましい",
        sentence="彼[かれ]は 厚かましい[あつかましい]。",
        expected_kana_only="かれは <b>あつかましい</b>。",
        expected_furigana=" 彼[かれ]は<b> 厚[あつ]かましい</b>。",
        expected_furikanji=" かれ[彼]は<b> あつ[厚]かましい</b>。",
    )
    test(
        test_name="Adjective okurigana test 5/",
        kanji="恥",
        onyomi="チ(呉)",
        kunyomi="は.じる、はじ、は.じらう、は.ずかしい",
        sentence="恥[は]ずかしげな 顔[かお]で 恥[はじ]を 知[し]らない 振[ふ]りで 恥[は]じらってください。",
        expected_kana_only="<b>はずかし</b>げな かおで <b>はじ</b>を しらない ふりで <b>はじらって</b>ください。",
        expected_furigana="<b> 恥[は]ずかし</b>げな 顔[かお]で<b> 恥[はじ]</b>を 知[し]らない 振[ふ]りで<b> 恥[は]じらって</b>ください。",
        expected_furikanji="<b> は[恥]ずかし</b>げな かお[顔]で<b> はじ[恥]</b>を し[知]らない ふ[振]りで<b> は[恥]じらって</b>ください。",
    )
    print("Ok.")


if __name__ == "__main__":
    main()
