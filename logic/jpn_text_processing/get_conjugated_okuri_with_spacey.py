import sys
import spacy
from typing import Literal

try:
    from ...utils.logger import Logger
except ImportError:
    from utils.logger import Logger

from .types import (
    OkuriResults,
)

spacy_nlp = spacy.load("ja_core_news_sm")


OkuriPrefix = Literal["kanji", "kanji_reading"]


def get_conjugated_okuri_with_spacey(
    kanji: str,
    kanji_reading: str,
    maybe_okuri: str,
    okuri_prefix: OkuriPrefix = "kanji",
    logger: Logger = Logger("error"),
) -> OkuriResults:
    """
    Determines the portion of text that is the conjugated okurigana for a kanji reading.
    :param maybe_okuri: The okurigana to check
    :param kanji: The kanji character
    :param kanji_reading: The reading of the kanji occurring before the okurigana
    :param logger: Logger instance for debugging
    :return: A tuple of the okurigana that is part of the conjugation for threading
            and the rest of the okurigana
    """
    logger.debug(
        f"get_conjugated_okuri - maybe_okuri: {maybe_okuri}, kanji: {kanji}, kanji_reading:"
        f" {kanji_reading}, okuri_prefix: {okuri_prefix}"
    )
    parse_text_prefix = None
    if okuri_prefix == "kanji":
        if kanji:
            parse_text_prefix = kanji
        elif kanji_reading:
            parse_text_prefix = kanji_reading
            okuri_prefix = "kanji_reading"
    elif okuri_prefix == "kanji_reading":
        if kanji_reading:
            parse_text_prefix = kanji_reading
        elif kanji:
            parse_text_prefix = kanji
            okuri_prefix = "kanji"
    if not parse_text_prefix:
        logger.error(
            f"get_conjugated_okuri - cannot set parse_text_prefix, okuri_prefix: {okuri_prefix},"
            f" kanji: {kanji}, kanji_reading: {kanji_reading}"
        )
        return OkuriResults("", maybe_okuri, "no_okuri", None)
    text_to_parse = f"{parse_text_prefix}{maybe_okuri}"

    okuri_type = "detected_okuri"

    # exceptions that parsing gets wrong
    if kanji == "久" and kanji_reading == "ひさ" and maybe_okuri.startswith("しぶり"):
        return OkuriResults("し", maybe_okuri[1:], okuri_type, "adj-i")
    if kanji == "仄々" and kanji_reading == "ほのぼの":
        if maybe_okuri.startswith("した"):
            rest_kana = maybe_okuri[2:]
            return OkuriResults("した", rest_kana, okuri_type, None)
        if maybe_okuri.startswith("しい"):
            rest_kana = maybe_okuri[2:]
            return OkuriResults("しい", rest_kana, okuri_type, "adj-i")
        if maybe_okuri.startswith("し"):
            rest_kana = maybe_okuri[1:]
            return OkuriResults("し", rest_kana, okuri_type, "adj-i")

    res_doc = spacy_nlp(text_to_parse)
    logger.debug(
        f"Parsed text: {text_to_parse} ->\n"
        + "\n".join([f"{token.text}, POS: {token.pos_}, TAG: {token.tag_}" for token in res_doc]),
    )
    if not res_doc:
        return OkuriResults("", maybe_okuri, "no_okuri", None)
    if not res_doc[0].pos_:
        logger.error(f"get_conjugated_okuri - No POS found for {text_to_parse}")
        return OkuriResults("", maybe_okuri, "no_okuri", None)

    first_token = res_doc[0]
    is_i_adjective = first_token.tag_.startswith("形容詞")
    is_na_adjective = first_token.tag_.startswith("形状詞-一般")
    is_verb = first_token.tag_.startswith("動詞")
    is_adverb = first_token.tag_.startswith("副詞")
    logger.debug(
        f"First token: {first_token.text}, POS: {first_token.pos_}, TAG: {first_token.tag_},"
        f" is_i_adjective: {is_i_adjective}, is_na_adjective: {is_na_adjective}, is_verb:"
        f" {is_verb}, is_adverb: {is_adverb}, continue:"
        f" {not (is_i_adjective or is_na_adjective or is_verb or is_adverb)}."
    )
    if not (is_i_adjective or is_na_adjective or is_verb or is_adverb):
        # If the first token is not one of the processable types, try again with kanji_reading
        # as the prefix
        if okuri_prefix == "kanji":
            logger.debug(
                f"First token is not a verb or adjective: {first_token.text}, POS:"
                f" {first_token.pos_}, TAG: {first_token.tag_}. Retrying with kanji_reading as"
                " prefix."
            )
            return get_conjugated_okuri_with_spacey(
                kanji,
                kanji_reading,
                maybe_okuri,
                okuri_prefix="kanji_reading",
                logger=logger,
            )
        elif okuri_prefix == "kanji_reading":
            logger.debug(
                f"First token is not a verb or adjective: {first_token.text}, POS:"
                f" {first_token.pos_}, TAG: {first_token.tag_}. Returning empty okuri."
            )
            return OkuriResults("", maybe_okuri, "no_okuri", None)
        else:
            logger.error(
                f"Unknown okuri_prefix: {okuri_prefix}. Expected 'kanji' or 'kanji_reading'."
            )
            return OkuriResults("", maybe_okuri, "no_okuri", None)
    # The first token will actually include the conjugation stem, so we need to extract it
    conjugated_okuri = first_token.text[len(parse_text_prefix) :]
    rest_kana = maybe_okuri[len(conjugated_okuri) :]
    logger.debug(
        f"Initial conjugated okuri: {conjugated_okuri}, rest_kana: {rest_kana}, first token:"
        f" {first_token.text}, POS: {first_token.pos_}, TAG: {first_token.tag_}"
    )
    rest_tokens = res_doc[1:]
    for token_index, token in enumerate(rest_tokens):
        # prev_token = rest_tokens[token_index - 1] if token_index > 0 else None
        add_to_conjugated_okuri = False
        if token.text in ["だろう", "でしょう", "なら", "から"]:
            add_to_conjugated_okuri = False
        elif is_verb:
            if token.tag_ in [
                # -ら,-れ,-た
                "助動詞",
                # -て
                "助詞-接続助詞",
            ]:
                add_to_conjugated_okuri = True
        elif is_i_adjective:
            if token.tag_ in [
                # -ない, -なかっ(た)
                "形容詞-非自立可能",
                # -て
                "助詞-接続助詞",
                # -た
                "助動詞",
                # -さ
                "接尾辞-名詞的-一般",
            ]:
                add_to_conjugated_okuri = True
        elif is_na_adjective:
            if token.text == "な":
                add_to_conjugated_okuri = True
        elif is_adverb:
            if token.tag_ in [
                # adverb that is also suru verb
                "動詞-非自立可能",
            ]:
                add_to_conjugated_okuri = True

        if add_to_conjugated_okuri:
            # If the token is an auxiliary or a non-independent adjective (ない), add it to the
            # conjugated okuri
            conjugated_okuri += token.text
            # Remove the text from the rest of the okurigana
            rest_kana = rest_kana[len(token.text) :]
            logger.debug(
                f"Added to okuri: {token.text}, POS: {token.pos_}, TAG: {token.tag_}, new okuri:"
                f" {conjugated_okuri}, rest_kana: {rest_kana}"
            )
        else:
            # If we hit a non-auxiliary token, stop processing
            logger.debug(
                f"Stopping at non-auxiliary token: {token.text}, POS: {token.pos_}, TAG:"
                f" {token.tag_}"
            )
            break
    return OkuriResults(conjugated_okuri, rest_kana, "detected_okuri", None)


# Tests
def test(kanji, kanji_reading, maybe_okuri, expected, debug: bool = False):
    result = get_conjugated_okuri_with_spacey(
        kanji, kanji_reading, maybe_okuri, logger=Logger("debug" if debug else "error")
    )
    try:
        assert result == expected
    except AssertionError:
        # Re-run with logging enabled
        get_conjugated_okuri_with_spacey(kanji, kanji_reading, maybe_okuri, logger=Logger("debug"))
        print(f"""\033[91mget_part_of_speech({maybe_okuri}, {kanji}, {kanji_reading})
\033[93mExpected: {expected}
\033[92mGot:      {result}
\033[0m""")
        # Stop the testing here
        sys.exit(0)


def main():
    # Test cases
    test("逆上", "のぼ", "せたので", ("せた", "ので"))
    test("悔", "くや", "しいくらい", ("しい", "くらい"))
    test("安", "やす", "くなかった", ("くなかった", ""))
    test("来", "く", "れたらいくよ", ("れたら", "いくよ"))
    test("青", "あお", "かったらあかくぬって", ("かったら", "あかくぬって"))
    test("大", "おお", "きくてやわらかい", ("きくて", "やわらかい"))
    test("容易", "たやす", "くやったな", ("く", "やったな"))
    test("清々", "すがすが", "しくない", ("しくない", ""))
    test("恥", "は", "ずかしげなかおで", ("ずかし", "げなかおで"))
    test("察", "さっ", "していなかった", ("して", "いなかった"))
    test("為", "さ", "れるだろう", ("れる", "だろう"))
    test("知", "し", "ってるでしょう", ("ってる", "でしょう"))
    test("為", "し", "なかった", ("なかった", ""))
    test("挫", "くじ", "けられないで", ("けられないで", ""))
    test("何気", "なにげ", "に", ("", "に"))
    test("為", "す", "るしかない", ("る", "しかない"))
    test("静", "しず", "かに", ("か", "に"))
    test("静", "しず", "かでよい", ("か", "でよい"))
    test("静", "しず", "かなあおさ", ("かな", "あおさ"))
    test("高", "たか", "ければたかくなる", ("ければ", "たかくなる"))
    test("行", "い", "ったらしい", ("ったらしい", ""))
    test("行", "い", "ったらいくかも", ("ったら", "いくかも"))
    test("清々", "すっきり", "した", ("", "した"))
    test("熱々", "あつあつ", "だね", ("", "だね"))
    test("瑞々", "みずみず", "しさがいい", ("しさ", "がいい"))
    test("止", "ど", "め", ("め", ""))
    test("読", "よ", "みかた", ("み", "かた"))
    test("悪", "あ", "しがわからない", ("し", "がわからない"))
    test("死", "し", "んでいない", ("んで", "いない"))
    test("聞", "き", "いていたかい", ("いて", "いたかい"))
    # 久ぶりに doesn't get split into ひさし and ぶりに and is instead treated as a single noun
    test("久", "ひさ", "しぶりに", ("し", "ぶりに"))
    test("久", "ひさ", "しいきもち", ("しい", "きもち"))
    test("仄々", "ほのぼの", "したようす", ("した", "ようす"))
    # 欲する is detected as a noun, when ほっする is commonly considered a kunyomi for it
    # This would need to be handled by giving only the する part to the function
    # test("欲", "ほっ", "ればやる", ("れば", "やる"))
    test("欲", "ほ", "しいなら", ("しい", "なら"))
    test("放", "ほ", "ったらかす", ("ったら", "かす"))
    test("放", "ほう", "ったらかす", ("ったら", "かす"))
    test("放", "ほう", "っておく", ("って", "おく"))
    test("高", "たか", "めるから", ("める", "から"))
    test("厚", "あつ", "かましくてやかましい", ("かましくて", "やかましい"))
    test("抉", "えぐ", "られたように", ("られた", "ように"))
    # Works when using okuri_prefix="kanji_reading" instead of "kanji"
    test("抉", "えぐ", "かったよな", ("かった", "よな"))
    test("抉", "えぐ", "くてやわらかい", ("くて", "やわらかい"))
    test("", "として", "いるのは", ("", "いるのは"))
    print("\033[92mTests passed\033[0m")


if __name__ == "__main__":
    main()
