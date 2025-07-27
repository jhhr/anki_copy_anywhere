from typing import Optional
from .okurigana_dict import (
    PartOfSpeech,
)
from .get_conjugatable_okurigana_stem import (
    get_conjugatable_okurigana_stem,
)
from .starts_with_okurigana_conjugation import (
    OkuriResults,
    starts_with_okurigana_conjugation,
)
from .types import HighlightArgs, WordData

try:
    from ...utils.logger import Logger
except ImportError:
    from utils.logger import Logger


def check_okurigana_for_inflection(
    reading_okurigana: str,
    reading: str,
    word_data: WordData,
    highlight_args: HighlightArgs,
    part_of_speech: Optional[PartOfSpeech] = None,
    logger: Logger = Logger("error"),
) -> OkuriResults:
    """
    Function that checks the okurigana for a match with the okurigana
    :param reading_okurigana: the okurigana to check
    :param reading: the kunyomi/onyomi reading to check against
    :param word_data: the word data containing the okurigana and other information
    :param highlight_args: the highlight arguments containing the kanji to match
    :param logger: the logger to use for debugging
    :param part_of_speech: optional override for the part of speech to use

    :return: (string, string) the okurigana that should be highlighted and the rest of the okurigana
    """
    # Kana text occurring after the kanji in the word, may not be okurigana and can
    # contain other kana after the okurigana
    maybe_okuri_text = word_data.get("okurigana")
    logger.debug(
        f"check okurigana 0 - kunyomi_okurigana: {reading_okurigana},"
        f" maybe_okurigana: {maybe_okuri_text} reading_okurigana: {reading_okurigana},"
        f" reading: {reading}, part_of_speech: {part_of_speech}"
    )

    if not maybe_okuri_text or not reading_okurigana:
        # If there is no okurigana or reading_okurigana, we can't check for inflections
        return OkuriResults("", "", "no_okuri")

    # Simple case, exact match, no need to check conjugations
    if reading_okurigana == maybe_okuri_text:
        return OkuriResults(reading_okurigana, "", "full_okuri")

    # Check what kind of inflections we should be looking for from the kunyomi okurigana
    conjugatable_stem = get_conjugatable_okurigana_stem(reading_okurigana)

    # Another simple case, stem is the same as the okurigana, no need to check conjugations
    if conjugatable_stem == maybe_okuri_text:
        return OkuriResults(conjugatable_stem, "", "full_okuri")

    logger.debug(
        f"check okurigana with reading_okurigana 1 - conjugatable_stem: {conjugatable_stem}"
    )
    if conjugatable_stem is None or not maybe_okuri_text.startswith(conjugatable_stem):
        logger.debug(
            "\ncheck okurigana with reading_okurigana 2 - no conjugatable_stem or no match"
        )
        # Not a verb or i-adjective, so just check for an exact match within the okurigana
        if maybe_okuri_text.startswith(reading_okurigana):
            logger.debug(
                f"check okurigana with reading_okurigana 3 - maybe_okuri_text: {maybe_okuri_text}"
            )
            return OkuriResults(
                reading_okurigana,
                maybe_okuri_text[len(reading_okurigana) :],
                "full_okuri",
            )
        logger.debug("\ncheck okurigana with reading_okurigana 4 - no match")
        return OkuriResults("", maybe_okuri_text, "no_okuri")

    # Remove the conjugatable_stem from maybe_okurigana
    trimmed_maybe_okuri = maybe_okuri_text[len(conjugatable_stem) :]
    logger.debug(f"check okurigana 5 - trimmed_maybe_okuri: {trimmed_maybe_okuri}")

    # Then check if that contains a conjugation for what we're looking for
    conjugated_okuri, rest, return_type = starts_with_okurigana_conjugation(
        trimmed_maybe_okuri,
        reading_okurigana,
        highlight_args["kanji_to_match"],
        reading,
        part_of_speech=part_of_speech,
        logger=logger,
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
