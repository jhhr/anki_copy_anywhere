import sys
from typing import Literal, NamedTuple

try:
    from .okurigana_dict import get_okuri_dict_for_okurigana
except ImportError:
    from okurigana_dict import get_okuri_dict_for_okurigana

LOG = False


def log(*args):
    if LOG:
        print(*args)


class OkuriResults(NamedTuple):
    okurigana: str
    rest_kana: str
    result: Literal['full_okuri', 'partial_okuri', "empty_okuri", "no_okuri"]


def starts_with_okurigana_conjugation(
        kana_text: str,
        kanji_okurigana: str,
        kanji: str,
        kanji_reading: str,
) -> OkuriResults:
    """
    Determine if a kana text starts with okurigana and return that portion and the rest of the text.
    The text should have already been trimmed of the verb or adjective stem.
    :param kana_text: text to check for okurigana.
    :param kanji_okurigana: okurigana of the kanji.
    :param kanji: kanji whose okurigana is being checked in kana_text.
    :param kanji_reading: reading of the kanji.
    :return: tuple of the okurigana (if any) and the rest of the text
    """
    # Sanity check, we need at least one character, and at least the kanji okurigana
    if not kana_text or not kanji_okurigana:
        return OkuriResults("", kana_text, "no_okuri")

    # Get the okurigana dict for the kanji
    okuri_dict = get_okuri_dict_for_okurigana(kanji_okurigana, kanji, kanji_reading)

    if not okuri_dict:
        return OkuriResults("", kana_text, "no_okuri")

    log(f"kana_text: {kana_text}, kanji_okurigana: {kanji_okurigana}, kanji: {kanji}, kanji_reading: {kanji_reading}, okuri_dict: {okuri_dict}")

    if not kana_text[0] in okuri_dict and not okuri_dict[""]:
        log("no okurigana found and no empty string okurigana")
        return OkuriResults("", kana_text, "no_okuri")

    okurigana = ""
    rest = kana_text
    prev_dict = okuri_dict
    return_type = None
    # Recurse into the dict to find the longest okurigana
    # ending in either cur_char not being in the dict or the dict being empty
    while True:
        cur_char = rest[0]
        log(f"okurigana: {okurigana}, rest: {rest}, cur_char: {cur_char}, in dict: {cur_char in prev_dict}")
        if not cur_char in prev_dict:
            log(f"reached dict end, empty_dict: {not prev_dict}, is_last: {prev_dict.get('is_last')}")
            return_type = "full_okuri" if prev_dict.get("is_last") else "partial_okuri"
            break
        prev_dict = prev_dict[cur_char]
        okurigana += cur_char
        rest = rest[1:]
        if not rest:
            log("reached text end")
            return_type = "full_okuri" if prev_dict.get("is_last") else "partial_okuri"
            break
    if not okurigana and okuri_dict[""]:
        # If no okurigana was found, but this conjugation can be valid with no okurigana,
        # then we indicate that this empty string is a full okurigana
        return_type = "empty_okuri"
    return OkuriResults(okurigana, rest, return_type)


# Tests
def test(text, okurigana, kanji, kanji_reading, expected):
    okurigana, rest, return_type = starts_with_okurigana_conjugation(text, okurigana, kanji, kanji_reading)
    try:
        global LOG
        assert okurigana == expected[0], f"okurigana: '{okurigana}' != '{expected[0]}'"
        assert rest == expected[1], f"rest: '{rest}' != '{expected[1]}'"
        assert return_type == expected[2], f"return_type: '{return_type}' != '{expected[2]}'"
    except AssertionError as e:
        # Re-run with logging enabled
        LOG = True
        starts_with_okurigana_conjugation(text, okurigana, kanji, kanji_reading)
        print(f"\033[91mTest failed for '{text}' -- {e}\033[0m")
        # Stop the testing here
        sys.exit(1)
    finally:
        LOG = False


def main():
    test(
        text="かったら",
        okurigana="い",
        kanji="無",
        kanji_reading="な",
        expected=("かったら", "", "full_okuri")
    )
    test(
        text="ったか",
        okurigana="る",
        kanji="去",
        kanji_reading="さ",
        expected=("った", "か", "full_okuri")
    )
    test(
        text="ないで",
        okurigana="る",
        kanji="在",
        kanji_reading="あ",
        expected=("ないで", "", "full_okuri")
    )
    test(
        text="んでくれ",
        okurigana="ぬ",
        kanji="死",
        kanji_reading="し",
        expected=("んで", "くれ", "full_okuri")
    )
    test(
        text="くない",
        okurigana="きい",
        kanji="大",
        kanji_reading="おお",
        expected=("くない", "", "full_okuri")
    )
    test(
        text="くないよ",
        okurigana="さい",
        kanji="小",
        kanji_reading="ちい",
        expected=("くない", "よ", "full_okuri")
    )
    test(
        text="している",
        okurigana="る",
        kanji="為",
        kanji_reading="す",
        expected=("して", "いる", "full_okuri")
    )
    test(
        text="してた",
        okurigana="する",
        kanji="動",
        kanji_reading="どう",
        expected=("してた", "", "full_okuri")
    )
    test(
        text="いでる",
        okurigana="ぐ",
        kanji="泳",
        kanji_reading="およ",
        expected=("いで", "る", "full_okuri")
    )
    test(
        text="いです",
        okurigana="い",
        kanji="良",
        kanji_reading="よ",
        expected=("い", "です", "full_okuri")
    )
    test(
        text="つ",
        okurigana="つ",
        kanji="待",
        kanji_reading="ま",
        expected=("つ", "", "full_okuri")
    )
    test(
        text="いてたか",
        okurigana="く",
        kanji="聞",
        kanji_reading="き",
        expected=("いて", "たか", "full_okuri")
    )
    test(
        text="げな",
        okurigana="ずかしい",
        kanji="恥",
        kanji_reading="は",
        expected=("", "げな", "empty_okuri")
    )
    print('Ok')


if __name__ == "__main__":
    main()
