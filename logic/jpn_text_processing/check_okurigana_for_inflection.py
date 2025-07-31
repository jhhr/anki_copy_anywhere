from typing import Optional
from .types import (
    PartOfSpeech,
)
from .get_conjugatable_okurigana_stem import (
    CONJUGATABLE_LAST_OKURI_PART_OF_SPEECH,
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
        f"check okurigana 0 - reading_okurigana: {reading_okurigana}, maybe_okurigana:"
        f" {maybe_okuri_text}, reading: {reading}, part_of_speech: {part_of_speech}"
    )

    if not maybe_okuri_text or not reading_okurigana:
        # If there is no okurigana or reading_okurigana, we can't check for inflections
        return OkuriResults("", "", "no_okuri")

    # Simple case, exact match, no need to check conjugations
    if reading_okurigana == maybe_okuri_text:
        return OkuriResults(reading_okurigana, "", "full_okuri", None)

    # Check what kind of inflections we should be looking for from the kunyomi okurigana
    conjugatable_stem, possible_parts_of_speech = get_conjugatable_okurigana_stem(reading_okurigana)

    # Another simple case, stem is the same as the okurigana, no need to check conjugations
    if conjugatable_stem == maybe_okuri_text:
        # If we wanted to accurately get the part of speech, we'd need to do the full okuri check
        if len(possible_parts_of_speech) == 1:
            detected_part_of_speech = possible_parts_of_speech[0]
        elif part_of_speech:
            detected_part_of_speech = part_of_speech
        else:
            detected_part_of_speech = None
        return OkuriResults(conjugatable_stem, "", "full_okuri", detected_part_of_speech)

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
    conjugated_okuri, rest, return_type, detected_part_of_speech = (
        starts_with_okurigana_conjugation(
            trimmed_maybe_okuri,
            reading_okurigana,
            highlight_args["kanji_to_match"],
            reading,
            part_of_speech=part_of_speech,
            logger=logger,
        )
    )
    logger.debug(
        f"check okurigana 6 - conjugated_okuri: {conjugated_okuri}, rest: {rest},"
        f" return_type: {return_type}, detected_part_of_speech: {detected_part_of_speech}"
    )

    if return_type != "no_okuri":
        logger.debug(
            f"check okurigana 7 - result: {conjugatable_stem + conjugated_okuri}, rest: {rest}"
        )
        # remember to add the stem back!
        return OkuriResults(
            conjugatable_stem + conjugated_okuri, rest, return_type, detected_part_of_speech
        )

    # No match, this text doesn't contain okurigana for the kunyomi word
    logger.debug("\ncheck okurigana 8 - no match")
    return OkuriResults("", maybe_okuri_text, "no_okuri")


def check_any_okurigana_for_inflection(
    word_data: WordData,
    highlight_args: HighlightArgs,
    logger: Logger = Logger("error"),
) -> OkuriResults:
    """
    Check if the okurigana in the word_data matched any possible inflections, checking the starting
    point for inflection in any position of the okurigana.

    :param word_data: the word data containing the okurigana and other information
    :param highlight_args: the highlight arguments containing the kanji to match
    :param logger: the logger to use for debugging
    """
    okurigana = word_data.get("okurigana", "")
    if not okurigana:
        logger.debug("check_any_okurigana_for_inflection: no okurigana found")
        return OkuriResults("", "", "no_okuri")
    logger.debug(f"check_any_okurigana_for_inflection: okurigana: {okurigana}")
    # Check for inflections starting from the beginning of the okurigana
    okuri_results: list[OkuriResults] = []
    # Check each character in the okurigana to see if it can be a starting point
    for okuri_index in range(len(okurigana) - 1):
        for (
            base_conjugation_ending,
            parts_of_speech,
        ) in CONJUGATABLE_LAST_OKURI_PART_OF_SPEECH.items():
            # Otherwise, check conjugations for the possible parts of speech
            okuri_upto_cur = okurigana[: okuri_index + 1]

            logger.debug(
                f"check_any_okurigana_for_inflection: okuri_upto_cur: {okuri_upto_cur},"
                f" base_conjugation_ending: {base_conjugation_ending}, parts_of_speech:"
                f" {parts_of_speech}"
            )
            for part_of_speech in parts_of_speech:
                cur_res = check_okurigana_for_inflection(
                    okuri_upto_cur + base_conjugation_ending,
                    "",
                    word_data,
                    highlight_args,
                    logger=logger,
                    part_of_speech=part_of_speech,
                )
                if cur_res.result == "empty_okuri":
                    # Skip empty okuri results, they won't be correct
                    continue
                elif cur_res.result != "no_okuri":
                    # If we found a valid okurigana, add it to the results
                    logger.debug(
                        f"check_any_okurigana_for_inflection: found okuri: {cur_res.okurigana},"
                        f" rest_kana: {cur_res.rest_kana}, result: {cur_res.result}"
                    )
                    okuri_results.append(cur_res)

    logger.debug(f"check_any_okurigana_for_inflection: all okuri results found: {okuri_results}")
    # Return the result with the longest okurigana match
    if okuri_results:
        return max(okuri_results, key=lambda res: len(res.okurigana))

    # No okurigana matched any inflection
    return OkuriResults("", okurigana, "no_okuri")
