from typing import Optional, Literal, TypedDict, NamedTuple


class WithTagsDef(NamedTuple):
    """
    NamedTuple for the definition of the tags to wrap the furigana in
    :param with_tags
    :param merge_consecutive
    :param onyomi_to_katakana
    :param include_suru_okuri
    """

    with_tags: bool
    merge_consecutive: bool
    onyomi_to_katakana: bool
    include_suru_okuri: bool


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
    furigana_is_katakana: bool
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
    full_word: str
    full_furigana: str


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
    :param match_type
    """

    furigana: str
    okurigana: str
    rest_kana: str
    left_word: str
    middle_word: str
    right_word: str
    edge: Edge
    match_type: MatchType


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


PartOfSpeech = Literal[
    "adj-i",
    "adj-na",
    "adj-ix",
    "v1",
    "v1-s",
    "v5aru",
    "v5b",
    "v5g",
    "v5k",
    "v5k-s",
    "v5m",
    "v5n",
    "v5r",
    "v5r-i",
    "v5s",
    "v5t",
    "v5u",
    "v5u-s",
    "vk",
    "vs",
    "vs-s",
    "vs-i",
]

PARTS_OF_SPEECH: list[PartOfSpeech] = [
    "adj-i",
    "adj-na",
    "adj-ix",
    "v1",
    "v1-s",
    "v5aru",
    "v5b",
    "v5g",
    "v5k",
    "v5k-s",
    "v5m",
    "v5n",
    "v5r",
    "v5r-i",
    "v5s",
    "v5t",
    "v5u",
    "v5u-s",
    "vk",
    "vs",
    "vs-s",
    "vs-i",
]

OkuriType = Literal["full_okuri", "partial_okuri", "empty_okuri", "no_okuri", "detected_okuri"]


class OkuriResults(NamedTuple):
    okurigana: str
    rest_kana: str
    result: OkuriType
    part_of_speech: Optional[PartOfSpeech] = None
