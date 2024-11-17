import re
from typing import Union, Callable, TypedDict

try:
    from .kana_conv import to_katakana, to_hiragana
except ImportError:
    # For testing
    from kana_conv import to_katakana, to_hiragana

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

# Regex matching any kanji and furigana
KANJI_AND_FURIGANA_RE = "([\d々\u4e00-\u9faf\u3400-\u4dbf]+)\[(.+?)\]"
KANJI_AND_FURIGANA_REC = re.compile(rf"{KANJI_AND_FURIGANA_RE}")


def re_match_from_right(text):
    return re.compile(rf"(.*)({text})(.*?)$")


def re_match_from_left(text):
    return re.compile(rf"^(.*?)({text})(.*)$")


def re_match_from_middle(text):
    return re.compile(rf"^(.*?)({text})(.*?)$")


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


# Arg typing
LEFT = "left"
RIGHT = "right"
MIDDLE = "middle"
WHOLE = "whole"
Edge: str = Union[LEFT, RIGHT, MIDDLE, WHOLE]


class KanjiData(TypedDict):
    """
    TypedDict for the kanji data in
    """
    pos: int
    count: int


def kana_highlight(
        kanji_to_highlight: str,
        onyomi: str,
        kunyomi: str,
        text: str,
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
    :return: The text cleaned from any previous <b> tags and with the furigana highlighted with <b> tags
        when the furigana corresponds to the kanji_to_highlight
    """
    debug_text = ""

    def debug_print(text):
        nonlocal debug_text
        debug_text += text + "\n"
        print(text)

    def process_readings(
            furigana: str,
            edge: Edge,
            kanji_data: KanjiData,
            return_on_or_kun_match_only: bool = False,
            show_error_message: Callable = print
    ):
        """
        Function that processes furigana by checking all possible onyomi and kunyomi readings on it
        Either returns the furigana as-is when there is no match or modifies the furigana by
        adding <b> tags around the part that matches the reading

        :param furigana: string, the furigana to process
        :param edge: string, [left, right, middle, whole], the part of the furigana to match
            against the onyomi or kunyomi
        :param kanji_data: dict, the position and count of the kanji in the word
        :param return_on_or_kun_match_only: bool, return [True, False] if an onyomi match is found
            and [False, True] if a kunyomi match is found
        :param show_error_message: Callable, function to call when an error message is needed
        :return: string, the modified furigana
            or [True, False] / [False, True] if return_on_or_kun_match_only
        """
        target_furigana_section = get_target_furigana_section(
            furigana, edge, show_error_message)
        if target_furigana_section is None:
            return text

        onyomi_match = check_onyomi_readings(
            furigana, target_furigana_section, edge, return_on_or_kun_match_only)
        if onyomi_match:
            return onyomi_match

        kunyomi_match = check_kunyomi_readings(
            furigana, target_furigana_section, edge, return_on_or_kun_match_only)
        if kunyomi_match:
            return kunyomi_match

        kanji_count = kanji_data.get("count")
        kanji_pos = kanji_data.get("pos")

        if kanji_count is None or kanji_pos is None:
            show_error_message(
                "Error in kana_highlight[]: process_readings() called with no kanji_count or kanji_pos specified")
            return [False, True] if return_on_or_kun_match_only else furigana

        return handle_jukujigun_case(furigana, kanji_data, return_on_or_kun_match_only)

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
            furigana: str,
            target_furigana_section: str,
            edge: Edge,
            return_on_or_kun_match_only: bool
    ):
        """
        Function that checks the onyomi readings against the target furigana section
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
                debug_print(f"\nonyomi_reading: {onyomi_reading}")
                return replace_onyomi_match(furigana, onyomi_reading, edge,
                                            return_on_or_kun_match_only)
            # The reading might have a match with a changed kana like シ->ジ, フ->プ, etc.
            # This only applies to the first kana in the reading and if the reading isn't a single kana
            if len(onyomi_reading) != 1 and onyomi_reading[0] in HIRAGANA_CONVERSION_DICT:
                for onyomi_kana in HIRAGANA_CONVERSION_DICT[onyomi_reading[0]]:
                    converted_kunyomi = onyomi_reading.replace(onyomi_reading[0], onyomi_kana, 1)
                    if converted_kunyomi in target_furigana_section:
                        debug_print(f"\nconverted_onyomi: {converted_kunyomi}")
                        return replace_onyomi_match(furigana, converted_kunyomi, edge,
                                                    return_on_or_kun_match_only)
            # Then also check for small tsu conversion of some consonants
            # this only happens in the last kana of the reading
            for tsu_kana in SMALL_TSU_POSSIBLE_HIRAGANA:
                if onyomi_reading[-1] == tsu_kana:
                    converted_kunyomi = onyomi_reading[:-1] + "っ"
                    if converted_kunyomi in target_furigana_section:
                        debug_print(f"\nconverted_onyomi: {converted_kunyomi}")
                        return replace_onyomi_match(furigana, converted_kunyomi, edge,
                                                    return_on_or_kun_match_only)
        return None

    def replace_onyomi_match(
            furigana: str,
            onyomi_that_matched: str,
            edge: Edge,
            return_on_or_kun_match_only: bool
    ):
        """
        Function that replaces the furigana with the onyomi reading that matched
        :param furigana: string, the furigana to process
        :param onyomi_that_matched: string, the onyomi reading that matched
        :param edge: string, [left, right, middle, whole], the part of the furigana to match
        :param return_on_or_kun_match_only: bool, return [True, False] if an onyomi match is found

        :return: string, the modified furigana
          or [True, False] when return_on_or_kun_match_only
        """
        if return_on_or_kun_match_only:
            return [True, False]

        if edge == RIGHT:
            reg = re_match_from_right(onyomi_that_matched)
        elif edge == LEFT:
            reg = re_match_from_left(onyomi_that_matched)
        else:
            reg = re_match_from_middle(onyomi_that_matched)
        return re.sub(reg, onyomi_replacer, furigana)

    def check_kunyomi_readings(
            furigana: str,
            target_furigana_section: str,
            edge: Edge,
            return_on_or_kun_match_only: bool
    ):
        """
        Function that checks the kunyomi readings against the target furigana section
        :param furigana: string, the furigana to process
        :param target_furigana_section: string, the part of the furigana that should be matched against the kunyomi
        The following passed to replace_kunyomi_match
        :param edge: string, [left, right, middle, whole], the part of the furigana to match
            against the onyomi or kunyomi
        :param return_on_or_kun_match_only: bool

        :return: string, the modified furigana
          or [False, True] when return_on_or_kun_match_only
        """
        for kunyomi_reading in kunyomi.split("、"):
            # Remove the okurigana in the reading which are split by a dot
            kunyomi_stem = re.sub(r"\..+", "", kunyomi_reading).strip()
            # For kunyomi we just check for a match with the stem
            if kunyomi_stem in target_furigana_section:
                debug_print(f"\nkunyomi_stem: {kunyomi_stem}")
                return replace_kunyomi_match(furigana, kunyomi_stem, edge, return_on_or_kun_match_only)
            # Also check for changed kana
            if kunyomi_stem[0] in HIRAGANA_CONVERSION_DICT:
                for kunyomi_kana in HIRAGANA_CONVERSION_DICT[kunyomi_stem[0]]:
                    converted_kunyomi = kunyomi_stem.replace(kunyomi_stem[0], kunyomi_kana, 1)
                    if converted_kunyomi in target_furigana_section:
                        debug_print(f"\nconverted_kunyomi: {converted_kunyomi}")
                        return replace_kunyomi_match(furigana, converted_kunyomi, edge,
                                                     return_on_or_kun_match_only)

            # Then also check for small tsu conversion of some consonants
            # this only happens in the last kana of the reading
            for tsu_kana in SMALL_TSU_POSSIBLE_HIRAGANA:
                if kunyomi_stem[-1] == tsu_kana:
                    converted_kunyomi = kunyomi_stem[:-1] + "っ"
                    if converted_kunyomi in target_furigana_section:
                        debug_print(f"\nconverted_kunyomi: {converted_kunyomi}")
                        return replace_kunyomi_match(furigana, converted_kunyomi, edge,
                                                     return_on_or_kun_match_only)
        return None

    def replace_kunyomi_match(
            furigana: str,
            kunyomi_that_matched: str,
            edge: Edge,
            return_on_or_kun_match_only: bool
    ):
        """
        Function that replaces the furigana with the kunyomi reading that matched
        :param furigana: string, the furigana to process
        :param kunyomi_that_matched: string, the kunyomi reading that matched
        :param edge: string, [left, right, middle, whole], the part of the furigana to match
        :param return_on_or_kun_match_only: bool, return [False, True] if a kunyomi match is found
        :return: string, the modified furigana
            or [False, True] when return_on_or_kun_match_only
        """
        if return_on_or_kun_match_only:
            return [False, True]

        if edge == RIGHT:
            reg = re_match_from_right(kunyomi_that_matched)
        elif edge == LEFT:
            reg = re_match_from_left(kunyomi_that_matched)
        else:
            reg = re_match_from_middle(kunyomi_that_matched)
        return re.sub(reg, kunyomi_replacer, furigana)

    def handle_jukujigun_case(
            furigana: str,
            kanji_data: KanjiData,
            return_on_or_kun_match_only: bool
    ):
        """
        Function that handles the case of a jukujigun/ateji word where the furigana
        doesn't match the onyomi or kunyomi. Highlights the part of the furigana matching
        the kanji position
        :param furigana: string, the furigana to process
        :param kanji_data: dict, the position and count of the kanji in the word
        :param return_on_or_kun_match_only: bool, return [False, True] if a kunyomi match is found
        :return: string, the modified furigana
            or [False, True] when return_on_or_kun_match_only
        """
        kanji_count = kanji_data.get("count")
        kanji_pos = kanji_data.get("pos")

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

        return [False, True] if return_on_or_kun_match_only else new_furigana

    def handle_whole_kanji_case(furigana: str):
        """
        The case when the whole word contains the kanji to highlight.
        So, either it's a single kanji word or the kanji is repeated.
        :param furigana: string, the whole furigana for the word
        :return: string, the modified furigana entirely highlighted, additionally
            in katakana for onyomi
        """
        [onyomi_match, _] = process_readings(
            furigana,
            kanji_data={"pos": 0, "count": 1},
            edge=WHOLE,
            return_on_or_kun_match_only=True
        )
        if onyomi_match:
            # For onyomi matches the furigana should be in katakana
            return f"<b>{to_katakana(furigana)}</b>"
        # For kunyomi matches keep in hiragana
        return f"<b>{furigana}</b>"

    def handle_partial_kanji_case(word: str, furigana: str):
        """
        The case when the word contains other kanji in addition to the kanji to highlight.
        Could be 2 or more kanji in the word.
        :param word: string, the word
        :param furigana: string, the whole furigana for the word
        :return: string, the modified furigana with the kanji to highlight highlighted
        """
        kanji_pos = word.find(kanji_to_highlight)
        if kanji_pos == -1:
            return furigana
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

        kanji_count = len(word)

        kanji_data = {
            "pos": kanji_pos,
            "count": kanji_count
        }

        if kanji_in_left_edge:
            return process_readings(furigana, LEFT, kanji_data)
        if kanji_in_right_edge:
            return process_readings(furigana, RIGHT, kanji_data)
        if kanji_in_middle:
            return process_readings(furigana, MIDDLE, kanji_data)
        # Sanity check, return something, we should never get here
        return furigana

    # Regex sub replacer function.
    def furigana_replacer(match: re.Match):
        """
        Replacer function for KANJI_AND_FURIGANA_REC. This function is called for every match
        found by the regex. It processes the furigana and returns the modified furigana.
        :param match: re.Match, the match object
        :return: string, the modified furigana
        """
        word = match.group(1)
        furigana = match.group(2)

        if furigana.startswith("sound:"):
            # This was something like 漢字[sound:...], we shouldn't modify the text in the brackets
            # as it'd break the audio tag. But we know the text to the right is kanji (what is it doing
            # there next to a sound tag?) so we'll just leave it out anyway
            return furigana

        if word in (kanji_to_highlight, f"{kanji_to_highlight}々"):
            return handle_whole_kanji_case(furigana)

        return handle_partial_kanji_case(word, furigana)

    # Clean any potential mixed okurigana cases, turning them normal
    clean_text = OKURIGANA_MIX_CLEANING_RE.sub(okurigana_mix_cleaning_replacer, text)
    # Special case 秘蔵[ひぞ]っ子[こ] needs to be converted to 秘蔵[ひぞっ]子[こ]
    clean_text = clean_text.replace("秘蔵[ひぞ]っ", "秘蔵[ひぞっ]")
    return KANJI_AND_FURIGANA_REC.sub(furigana_replacer, clean_text)


def test(test_name, expected, sentence, kanji, onyomi, kunyomi):
    """
    Function that tests the kana_highlight function
    """
    result = kana_highlight(
        kanji,
        onyomi,
        kunyomi,
        sentence,
    )
    try:
        assert result == expected
    except AssertionError:
        print(f"""{test_name}
Expected: {expected}
Got:      {result}
""")
        raise


def main():
    test(
        test_name="Should not incorrectly match onyomi twice 1/",
        kanji="視",
        onyomi="シ(漢)、ジ(呉)",
        kunyomi="み.る",
        # しちょうしゃ　has し in it twice but only the first one should be highlighted
        sentence="視聴者[しちょうしゃ]",
        expected="<b>シ</b>ちょうしゃ",
    )
    test(
        test_name="Should not incorrectly match onyomi twice 2/",
        kanji="儀",
        onyomi="ギ(呉)",
        kunyomi="のり、よ.い",
        # 　ぎょうぎ　has ぎ in it twice but only the first one should be highlighted
        sentence="行儀[ぎょうぎ]",
        expected="ぎょう<b>ギ</b>",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 1/",
        kanji="団",
        onyomi="ダン(呉)、トン(唐)、タン(漢)",
        kunyomi="かたまり、まる.い",
        # 消え去[きえさ]った　has え　in the middle of the kanji but った at the end is not included in the furigana
        sentence="団子[だんご]が 消え去[きえさ]った。",
        expected="<b>ダン</b>ごが きえさった。",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 2/",
        kanji="隣",
        onyomi="リン(呉)",
        kunyomi="とな.る、となり",
        # 隣り合わせ[となりあわせ]のまち　has り　in the middle and わせ　at the end of the group
        sentence="隣り合わせ[となりあわせ]の町[まち]。",
        expected="<b>とな</b>りあわせのまち。",
    )
    test(
        test_name="Matches word that uses the repeater 々 with rendaku 1/",
        kanji="国",
        onyomi="コク(呉)",
        kunyomi="くに",
        sentence="国々[くにぐに]の 関係[かんけい]が 深い[ふかい]。",
        expected="<b>くにぐに</b>の かんけいが ふかい。",
    )
    test(
        test_name="Matches word that uses the repeater 々 with rendaku 2/",
        kanji="時",
        onyomi="ジ(呉)、シ(漢)",
        kunyomi="とき",
        sentence="時々[ときどき] 雨[あめ]が 降る[ふる]。",
        expected="<b>ときどき</b> あめが ふる。",
    )
    test(
        test_name="Matches word that uses the repeater 々 with small tsu",
        kanji="刻",
        onyomi="コク(呉)",
        kunyomi="きざ.む、きざ.み、とき",
        sentence="刻々[こっこく]と 変化[へんか]する。",
        expected="<b>コッコク</b>と へんかする。",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 3/",
        kanji="歯",
        onyomi="シ(呉)",
        kunyomi="よわい、は、よわ.い、よわい.する",
        # A third edge case: there is only okurigana at the end
        sentence="歯止め[はどめ]",
        expected="<b>は</b>どめ",
    )
    test(
        test_name="Is able to match the same kanji occurring twice",
        kanji="閣",
        onyomi="カク(呉)",
        kunyomi="たかどの、たな",
        sentence="新[しん] 内閣[ないかく]の 組閣[そかく]が 発表[はっぴょう]された。",
        expected="しん ない<b>カク</b>の そ<b>カク</b>が はっぴょうされた。",
    )
    test(
        test_name="Is able to match the same kanji occurring twice with other using small tsu",
        kanji="国",
        onyomi="コク(呉)",
        kunyomi="くに",
        sentence="その2 国[こく]は 国交[こっこう]を 断絶[だんぜつ]した。",
        expected="その2 <b>コク</b>は <b>コッ</b>こうを だんぜつした。",
    )
    test(
        test_name="Is able to pick the right reading when there is multiple matches",
        kanji="靴",
        onyomi="カ(漢)、ケ(呉)",
        kunyomi="くつ",
        # ながぐつ　has が (onyomi か match) and ぐつ (kunyomi くつ) as matches
        sentence="お 前[まえ]いつも 長靴[ながぐつ]に 傘[かさ]さしてキメーんだよ！！",
        expected="お まえいつも なが<b>ぐつ</b>に かささしてキメーんだよ！！",
    )
    test(
        test_name="Should match reading in 4 kanji compound word",
        kanji="必",
        onyomi="ヒツ(漢)、ヒチ(呉)",
        kunyomi="かなら.ず",
        sentence="見敵必殺[けんてきひっさつ]の 指示[しじ]もないのに 戦闘[せんとう]は 不自然[ふしぜん]。",
        expected="けんてき<b>ヒッ</b>さつの しじもないのに せんとうは ふしぜん。",
    )
    test(
        test_name="Should match furigana for romaji numbers",
        kanji="賊",
        onyomi="ゾク(呉)、ソク(漢)",
        kunyomi="わるもの、そこ.なう",
        sentence="海賊[かいぞく]たちは ７[なな]つの 海[うみ]を 航海[こうかい]した。",
        expected="かい<b>ゾク</b>たちは ななつの うみを こうかいした。",
    )
    test(
        test_name="Should match the full reading match when there are multiple",
        kanji="由",
        onyomi="ユ(呉)、ユウ(漢)、ユイ(慣)",
        kunyomi="よし、よ.る、なお",
        # Both ゆ and ゆい are in the furigana but the correct match is ゆい
        sentence="彼女[かのじょ]は 由緒[ゆいしょ]ある 家柄[いえがら]の 出[で]だ。",
        expected="かのじょは <b>ユイ</b>しょある いえがらの でだ。",
    )
    test(
        test_name="small tsu 1/",
        kanji="剔",
        onyomi="テキ(漢)、チャク(呉)",
        kunyomi="えぐ.る、そ.る、のぞ.く",
        sentence="剔抉[てっけつ]",
        expected="<b>テッ</b>けつ",
    )
    test(
        test_name="small tsu 2/",
        kanji="一",
        onyomi="イチ(漢)、イツ(呉)",
        kunyomi="ひと、ひと.つ、はじ.め",
        sentence="一見[いっけん]",
        expected="<b>イッ</b>けん",
    )
    test(
        test_name="small tsu 3/",
        kanji="各",
        onyomi="カク(漢)、カ(呉)",
        kunyomi="おのおの",
        sentence="各国[かっこく]",
        expected="<b>カッ</b>こく",
    )
    test(
        test_name="small tsu 4/",
        kanji="吉",
        onyomi="キチ(漢)、キツ(呉)",
        kunyomi="よし",
        sentence="吉兆[きっちょう]",
        expected="<b>キッ</b>ちょう",
    )
    test(
        test_name="small tsu 5/",
        kanji="蔵",
        onyomi="ゾウ(漢)、ソウ(呉)",
        kunyomi="くら",
        sentence="秘蔵っ子[ひぞっこ]",
        expected="ひ<b>ゾッ</b>こ",
    )
    test(
        test_name="small tsu 6/",
        kanji="尻",
        onyomi="コウ(呉)",
        kunyomi="しり",
        sentence="尻尾[しっぽ]",
        expected="<b>しっ</b>ぽ",
    )
    test(
        test_name="small tsu 7/",
        kanji="呆",
        onyomi="ホウ(漢)、ボウ(慣)、ホ(呉)、タイ(慣)、ガイ(呉)",
        kunyomi="ほけ.る、ぼ.ける、あき.れる、おろか、おろ.か",
        sentence="呆気[あっけ]ない",
        expected="<b>あっ</b>けない",
    )
    test(
        test_name="small tsu 8/",
        kanji="甲",
        onyomi="コウ(漢)、カン(慣)、キョウ(呉)",
        kunyomi="きのえ、かぶと、よろい、つめ",
        sentence="甲冑[かっちゅう]の 試着[しちゃく]をお 願[ねが]いします｡",
        expected="<b>カッ</b>ちゅうの しちゃくをお ねがいします｡",
    )
    test(
        test_name="small tsu 9/",
        kanji="百",
        onyomi="ヒャク(呉)、ハク(漢)",
        kunyomi="もも",
        sentence="百貨店[ひゃっかてん]",
        expected="<b>ヒャッ</b>かてん",
    )
    test(
        test_name="Single kana reading conversion 1/",
        kanji="祖",
        # 祖 usually only lists ソ as the only onyomi
        onyomi="ソ(呉)、ゾ",
        kunyomi="おや、じじ、はじ.め",
        sentence="先祖[せんぞ]",
        expected="せん<b>ゾ</b>",
    )
    test(
        test_name="Single kana reading conversion 2/",
        kanji="来",
        onyomi="ライ(呉)、タイ",
        kunyomi="く.る、きた.る、きた.す、き.たす、き.たる、き、こ、こ.し、き.し",
        sentence="それは 私[わたし]たちの 日常生活[にちじょうせいかつ]の 仕来[しき]たりの １[ひと]つだ。",
        expected="それは わたしたちの にちじょうせいかつの し<b>き</b>たりの ひとつだ。",
    )
    test(
        test_name="Jukujigun test 大人 1/",
        kanji="大",
        onyomi="ダイ(呉)、タイ(漢)、タ(漢)、ダ(呉)",
        kunyomi="おお、おお.きい、おお.いに",
        sentence="大人[おとな] 達[たち]は 大[おお]きい",
        expected="<b>おと</b>な たちは <b>おお</b>きい",
    )
    test(
        test_name="Jukujigun test 大人 2/",
        kanji="人",
        onyomi="ジン(漢)、ニン(呉)",
        kunyomi="ひと",
        sentence="大人[おとな] 達[たち]は 人々[ひとびと]の 中[なか]に いる。",
        expected="おと<b>な</b> たちは <b>ひとびと</b>の なかに いる。",
    )
    test(
        test_name="Jukujigun test 今日 1/",
        kanji="今",
        onyomi="コン(呉)、キン(漢)",
        kunyomi="いま",
        sentence="今日[きょう]は 今[いま]まで 一日[いちにち] 何[なに]も しなかった。",
        expected="<b>きょ</b>うは <b>いま</b>まで いちにち なにも しなかった。",
    )
    test(
        test_name="Jukujigun test 今日 2/",
        kanji="日",
        onyomi="ニチ(呉)、ジツ(漢)、ニ",
        kunyomi="ひ、か",
        sentence="今日[きょう]は 今[いま]まで 一日[いちにち] 何[なに]も しなかった。",
        expected="きょ<b>う</b>は いままで いち<b>ニチ</b> なにも しなかった。",
    )
    test(
        test_name="Jukijigun test　百合 1/",
        kanji="百",
        onyomi="ヒャク(呉)、ハク(漢)",
        kunyomi="もも",
        sentence="百人[ひゃくにん]の 百合[ゆり]オタクが 合体[がったい]した。",
        expected="<b>ヒャク</b>にんの <b>ゆ</b>りオタクが がったいした。",
    )
    test(
        test_name="Jukijigun test　百合 2/",
        kanji="合",
        onyomi="ガッ(慣)、カッ(慣)、ゴウ(呉)、コウ(漢)",
        kunyomi="あ.う、あ.い、あい、あ.わす、あ.わせる",
        sentence="百人[ひゃくにん]の 百合[ゆり]オタクが 合体[がったい]した。",
        expected="ひゃくにんの ゆ<b>り</b>オタクが <b>ガッ</b>たいした。",
    )
    print("Ok.")


if __name__ == "__main__":
    main()
