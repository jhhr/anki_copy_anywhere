import sys
from typing import Optional

from .okurigana_dict import get_okuri_dict_for_okurigana

try:
    from ...utils.logger import Logger
except ImportError:
    from utils.logger import Logger

from .types import OkuriResults, OkuriType, PartOfSpeech


def starts_with_okurigana_conjugation(
    kana_text: str,
    kanji_okurigana: str,
    kanji: str,
    kanji_reading: str,
    part_of_speech: Optional[PartOfSpeech] = None,
    logger: Logger = Logger("error"),
) -> OkuriResults:
    """
    Determine if a kana text starts with okurigana and return that portion and the rest of the text.
    The text should have already been trimmed of the verb or adjective stem.
    :param kana_text: text to check for okurigana.
    :param kanji_okurigana: okurigana of the kanji.
    :param kanji: kanji whose okurigana is being checked in kana_text.
    :param kanji_reading: reading of the kanji.
    :param logger: Logger to use for debug messages.
    :param part_of_speech: Optional override for the part of speech.
    :return: tuple of the okurigana (if any) and the rest of the text
    """
    # Sanity check, we need at least one character, and at least the kanji okurigana
    if not kana_text or not kanji_okurigana:
        return OkuriResults("", kana_text, "no_okuri", None)

    # Get the okurigana dict for the kanji
    okuri_dict, part_of_speech_for_okuri = get_okuri_dict_for_okurigana(
        kanji_okurigana,
        kanji,
        kanji_reading,
        part_of_speech=part_of_speech,
        logger=logger,
    )

    if not okuri_dict:
        return OkuriResults("", kana_text, "no_okuri", None)

    logger.debug(
        f"kana_text: {kana_text}, kanji_okurigana: {kanji_okurigana}, kanji: {kanji},"
        f" kanji_reading: {kanji_reading}"
    )

    if not kana_text[0] in okuri_dict and not okuri_dict[""]:
        logger.debug("no okurigana found and no empty string okurigana")
        return OkuriResults("", kana_text, "no_okuri", None)

    okurigana = ""
    rest = kana_text
    prev_dict = okuri_dict
    okuri_result: OkuriType = "no_okuri"
    # Recurse into the dict to find the longest okurigana
    # ending in either cur_char not being in the dict or the dict being empty
    while True:
        cur_char = rest[0]
        logger.debug(
            f"okurigana: {okurigana}, rest: {rest}, cur_char: {cur_char}, in dict:"
            f" {cur_char in prev_dict}"
        )
        if cur_char not in prev_dict:
            logger.debug(
                f"reached dict end, empty_dict: {not prev_dict}, is_last:"
                f" {prev_dict.get('is_last')}"
            )
            okuri_result = "full_okuri" if prev_dict.get("is_last") else "partial_okuri"
            break
        prev_dict = prev_dict[cur_char]
        okurigana += cur_char
        rest = rest[1:]
        if not rest:
            logger.debug("reached text end")
            okuri_result = "full_okuri" if prev_dict.get("is_last") else "partial_okuri"
            break
    if not okurigana and okuri_dict[""]:
        # If no okurigana was found, but this conjugation can be valid with no okurigana,
        # then we indicate that this empty string is a full okurigana
        okuri_result = "empty_okuri"
    return OkuriResults(okurigana, rest, okuri_result, part_of_speech_for_okuri)


# Tests
def test(text, okurigana, kanji, kanji_reading, expected):
    okurigana, rest, return_type, result_part_of_speech = starts_with_okurigana_conjugation(
        text, okurigana, kanji, kanji_reading
    )
    try:
        assert okurigana == expected[0], f"okurigana: '{okurigana}' != '{expected[0]}'"
        assert rest == expected[1], f"rest: '{rest}' != '{expected[1]}'"
        assert return_type == expected[2], f"return_type: '{return_type}' != '{expected[2]}'"
        if len(expected) > 3:
            assert (
                result_part_of_speech == expected[3]
            ), f"part_of_speech: '{result_part_of_speech}' != '{expected[3]}'"
    except AssertionError as e:
        # Re-run with logging enabled
        starts_with_okurigana_conjugation(
            text, okurigana, kanji, kanji_reading, logger=Logger("debug")
        )
        print(f"\033[91mTest failed for '{text}' -- {e}\033[0m")
        # Stop the testing here
        sys.exit(0)


def main():
    # full okuri tests
    test(
        text="かったら",
        okurigana="い",
        kanji="無",
        kanji_reading="な",
        expected=("かったら", "", "full_okuri", "adj-i"),
    )
    test(
        text="ったか",
        okurigana="る",
        kanji="去",
        kanji_reading="さ",
        expected=("った", "か", "full_okuri", "v5r"),
    )
    test(
        text="ないで",
        okurigana="る",
        kanji="在",
        kanji_reading="あ",
        expected=("ないで", "", "full_okuri", "v5r-i"),
    )
    test(
        text="んでくれ",
        okurigana="ぬ",
        kanji="死",
        kanji_reading="し",
        expected=("んで", "くれ", "full_okuri", "v5n"),
    )
    test(
        text="くない",
        okurigana="きい",
        kanji="大",
        kanji_reading="おお",
        expected=("くない", "", "full_okuri", "adj-i"),
    )
    test(
        text="くないよ",
        okurigana="さい",
        kanji="小",
        kanji_reading="ちい",
        expected=("くない", "よ", "full_okuri", "adj-i"),
    )
    test(
        text="している",
        okurigana="る",
        kanji="為",
        kanji_reading="す",
        expected=("して", "いる", "full_okuri", "vs-i"),
    )
    test(
        text="してた",
        okurigana="する",
        kanji="動",
        kanji_reading="どう",
        # suru verbs should be vs-s but that's difficult to detect
        # When actually dealing with suru verbs, part_of_speech should be provided to the function
        # to get the correct okuri progression
        expected=("してた", "", "full_okuri", "vs-i"),
    )
    test(
        text="いでる",
        okurigana="ぐ",
        kanji="泳",
        kanji_reading="およ",
        expected=("いで", "る", "full_okuri", "v5g"),
    )
    test(
        text="いです",
        okurigana="い",
        kanji="良",
        kanji_reading="よ",
        expected=("い", "です", "full_okuri", "adj-ix"),
    )
    test(
        text="つ",
        okurigana="つ",
        kanji="待",
        kanji_reading="ま",
        expected=("つ", "", "full_okuri", "v5t"),
    )
    test(
        text="いてたか",
        okurigana="く",
        kanji="聞",
        kanji_reading="き",
        expected=("いて", "たか", "full_okuri", "v5k"),
    )
    # empty okuri tests
    test(
        # 恥[は]ずかしげな is an i-adjective, not na-adjective!
        text="げな",
        okurigana="ずかしい",
        kanji="恥",
        kanji_reading="は",
        expected=("", "げな", "empty_okuri", "adj-i"),
    )
    # partial okuri tests
    test(
        text="った",
        okurigana="る",
        kanji="去",
        kanji_reading="さ",
        expected=("った", "", "full_okuri", "v5r"),
    )
    print("\033[92mTests passed\033[0m")


if __name__ == "__main__":
    main()
