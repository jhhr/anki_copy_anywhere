import sys
from typing import Literal

try:
    from ...utils.logger import Logger
except ImportError:
    from utils.logger import Logger

from .mecab_controller.mecab_controller import MecabController
from .mecab_controller.basic_types import (
    Inflection,
    MecabParsedToken,
    PartOfSpeech,
)

from .types import (
    OkuriResults,
)

OkuriPrefix = Literal["kanji", "kanji_reading"]

mecab = MecabController()


def get_conjugated_okuri_with_mecab(
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
    if not maybe_okuri:
        logger.debug("get_conjugated_okuri - No okurigana provided, no processing needed.")
        return OkuriResults("", "", "no_okuri", None)
    parse_text_prefix = None
    if okuri_prefix == "kanji":
        if kanji:
            # Exception for 為 as its headword doesn't get detected correctly so process it using
            # the kanji reading
            if (kanji == "為" and kanji_reading == "し") or kanji == "抉":
                parse_text_prefix = kanji_reading
                okuri_prefix = "kanji_reading"
            else:
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

    tokens: list[MecabParsedToken] = list(mecab._analyze(text_to_parse))
    logger.debug(
        f"Parsed text: {text_to_parse} ->\n"
        + "\n".join([f"{token.word}, PartOfSpeech: {token.part_of_speech}" for token in tokens]),
    )
    if not tokens:
        logger.debug(
            f"get_conjugated_okuri - No tokens found for text: {text_to_parse}, returning no okuri."
        )
        return OkuriResults("", maybe_okuri, "no_okuri", None)
    first_token = tokens[0]
    if not first_token.part_of_speech:
        logger.error(f"get_conjugated_okuri - No PartOfSpeech found for {text_to_parse}")
        return OkuriResults("", maybe_okuri, "no_okuri", None)

    is_i_adjective = first_token.part_of_speech == PartOfSpeech.i_adjective or (
        # i-adjective inflected to く gets categorized as an adverb
        first_token.part_of_speech == PartOfSpeech.adverb
        and first_token.word.endswith("く")
    )
    is_na_adjective = first_token.part_of_speech == PartOfSpeech.noun and (
        first_token.word.endswith("か")
    )
    is_verb = first_token.part_of_speech == PartOfSpeech.verb
    is_adverb = first_token.part_of_speech == PartOfSpeech.adverb
    # Need to check nouns for words like 止め or 恥ずかしげな
    is_noun = first_token.part_of_speech == PartOfSpeech.noun
    logger.debug(
        f"First token: {first_token.word},  PartOfSpeech: {first_token.part_of_speech},"
        f" is_i_adjective: {is_i_adjective}, is_na_adjective: {is_na_adjective}, is_verb:"
        f" {is_verb}, is_adverb: {is_adverb}, is_noun: {is_noun}, continue:"
        f" {not (is_i_adjective or is_na_adjective or is_verb or is_adverb or is_noun)}."
    )
    if not (is_i_adjective or is_na_adjective or is_verb or is_adverb or is_noun):
        # If the first token is not one of the processable types, try again with kanji_reading
        # as the prefix
        if okuri_prefix == "kanji":
            logger.debug(
                f"First token not valid: {first_token.word}, PartOfSpeech:"
                f" {first_token.part_of_speech}, Retrying with kanji_reading as"
                " prefix."
            )
            return get_conjugated_okuri_with_mecab(
                kanji,
                kanji_reading,
                maybe_okuri,
                okuri_prefix="kanji_reading",
                logger=logger,
            )
        elif okuri_prefix == "kanji_reading":
            logger.debug(
                f"First token is not a verb or adjective: {first_token.word}, PartOfSpeech:"
                f" {first_token.part_of_speech}, Returning empty okuri."
            )
            return OkuriResults("", maybe_okuri, "no_okuri", None)
        else:
            logger.error(
                f"Unknown okuri_prefix: {okuri_prefix}. Expected 'kanji' or 'kanji_reading'."
            )
            return OkuriResults("", maybe_okuri, "no_okuri", None)
    # The first token will actually include the conjugation stem, so we need to extract it
    conjugated_okuri = first_token.word[len(parse_text_prefix) :]
    # Exception for nouns like 恥ずかしげな where the げ should be considered not a conjugation
    # as it is in fact 恥ずかし気な
    if is_noun and first_token.word.endswith("げ"):
        conjugated_okuri = first_token.word[len(parse_text_prefix) : -1]
        okuri_type = "full_okuri"
        logger.debug(
            f"Detected okuri for noun: {conjugated_okuri}, rest:"
            f" {maybe_okuri[len(conjugated_okuri):]}"
        )
        return OkuriResults(
            conjugated_okuri, maybe_okuri[len(conjugated_okuri) :], okuri_type, None
        )
    rest_kana = maybe_okuri[len(conjugated_okuri) :]
    logger.debug(
        f"Initial conjugated okuri: {conjugated_okuri}, rest_kana: {rest_kana}, first token:"
        f" {first_token.word}, PartOfSpeech: {first_token.part_of_speech}"
    )
    rest_tokens = tokens[1:]
    for token_index, token in enumerate(rest_tokens):
        next_token = rest_tokens[token_index + 1] if token_index + 1 < len(rest_tokens) else None
        add_to_conjugated_okuri = False
        if token.word in ["だろう", "でしょう", "なら", "から"]:
            add_to_conjugated_okuri = False
        elif is_verb:
            if (
                (
                    token.part_of_speech == PartOfSpeech.bound_auxiliary
                    and token.inflection_type is not None
                    and token.headword not in ["だ", "です"]
                )
                or (
                    token.part_of_speech == PartOfSpeech.particle
                    and (
                        token.word == "て"
                        or (token.word == "で" and next_token and next_token.headword == "いる")
                    )
                )
                or (
                    # -られ, -させ
                    token.part_of_speech == PartOfSpeech.verb
                    and token.headword in ["れる", "られる", "せる", "させる", "てる"]
                )
            ):
                add_to_conjugated_okuri = True
        elif is_i_adjective:
            if (
                (
                    # -ない, -なかっ(た)
                    token.part_of_speech == PartOfSpeech.bound_auxiliary
                    and (
                        token.inflection_type
                        in [
                            Inflection.continuative_ta,
                            Inflection.hypothetical,
                        ]
                        or token.word in ["た", "ない"]
                    )
                )
                or (token.part_of_speech == PartOfSpeech.particle and token.word in ["て", "ば"])
                or token.word == "さ"
            ):
                add_to_conjugated_okuri = True
        elif is_na_adjective:
            if token.word == "な":
                add_to_conjugated_okuri = True
        elif is_adverb or is_noun:
            # handle suru verbs
            if (token.part_of_speech == PartOfSpeech.verb and token.headword == "する") or (
                token.part_of_speech == PartOfSpeech.bound_auxiliary and token.headword != "だ"
            ):
                add_to_conjugated_okuri = True

        if add_to_conjugated_okuri:
            # If the token is an auxiliary or a non-independent adjective (ない), add it to the
            # conjugated okuri
            conjugated_okuri += token.word
            # Remove the text from the rest of the okurigana
            rest_kana = rest_kana[len(token.word) :]
            logger.debug(
                f"Added to okuri: {token.word}, PartOfSpeech: {token.part_of_speech}, new okuri:"
                f" {conjugated_okuri}, rest_kana: {rest_kana}"
            )
        else:
            # If we hit a non-auxiliary token, stop processing
            logger.debug(
                f"Stopping at non-auxiliary token: {token.word}, PartOfSpeech:"
                f" {token.part_of_speech},"
            )
            break
    return OkuriResults(conjugated_okuri, rest_kana, "detected_okuri", None)


# Tests
def test(kanji, kanji_reading, maybe_okuri, expected, debug: bool = False):
    result = get_conjugated_okuri_with_mecab(
        kanji, kanji_reading, maybe_okuri, logger=Logger("debug" if debug else "error")
    )
    try:
        assert result.okurigana == expected[0]
        assert result.rest_kana == expected[1]
    except AssertionError:
        # Re-run with logging enabled
        get_conjugated_okuri_with_mecab(kanji, kanji_reading, maybe_okuri, logger=Logger("debug"))
        print(f"""\033[91mget_part_of_speech({maybe_okuri}, {kanji}, {kanji_reading})
\033[93mExpected: {expected}
\033[92mGot:      {(result.okurigana, result.rest_kana)}
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
    # 恥ずかしげ gets categorized as a noun
    test("恥", "は", "ずかしげなかおで", ("ずかし", "げなかおで"))
    test("察", "さっ", "していなかった", ("して", "いなかった"))
    test("為", "さ", "れるだろう", ("れる", "だろう"))
    test("知", "し", "ってるでしょう", ("ってる", "でしょう"))
    test("為", "し", "なかった", ("なかった", ""))
    test("挫", "くじ", "けられないで", ("けられない", "で"))
    test("挫", "くじ", "けさせてやる", ("けさせて", "やる"))
    test("何気", "なにげ", "にと", ("に", "と"))
    test("為", "す", "るしかない", ("る", "しかない"))
    test("静", "しず", "かにいった", ("かに", "いった"))
    test("静", "しず", "かでよい", ("か", "でよい"))
    test("静", "しず", "かなあおさ", ("かな", "あおさ"))
    test("高", "たか", "ければたかくなる", ("ければ", "たかくなる"))
    test("行", "い", "ったらしい", ("ったらしい", ""))
    test("行", "い", "ったらいくかも", ("ったら", "いくかも"))
    test("清々", "すっきり", "した", ("した", ""))
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
    # えぐくて is too niche for mecab...
    # test("抉", "えぐ", "くてやわらかい", ("くて", "やわらかい"))
    test("", "として", "いるのは", ("", "いるのは"))
    print("\033[92mTests passed\033[0m")


if __name__ == "__main__":
    main()
