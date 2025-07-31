from typing import Union

from .types import PartOfSpeech

CONJUGATABLE_LAST_OKURI_PART_OF_SPEECH: dict[str, list[PartOfSpeech]] = {
    # Godan verbs
    "う": ["v5u"],
    "く": ["v5k"],
    "ぐ": ["v5g"],
    "す": ["v5s"],
    "つ": ["v5t"],
    "ぬ": ["v5n"],
    "ぶ": ["v5b"],
    "む": ["v5m"],
    # Godan or ichidan, note also jiru and zuru verbs are ichidan, also each suru verb special class
    "る": ["v5r", "v1", "vs", "vs-i", "vs-s"],
    # i-adjectives
    "い": ["adj-i"],
}


CONJUGATABLE_LAST_OKURI: set[str] = CONJUGATABLE_LAST_OKURI_PART_OF_SPEECH.keys()


def get_conjugatable_okurigana_stem(
    plain_okuri: str,
) -> tuple[Union[str, None], list[PartOfSpeech]]:
    """
    Returns the stem of a word's okurigana.
    :param plain_okuri: A dictionary form word's okurigana
    :return: The stem of the okurigana, after which conjugation is applied.
        Will be empty when the plain_okuri was a single kana and matches a conjugatable okuri.
        Return is None when there was no okuri or it was not conjugatable.
    """
    # Sanity check, we need at least one character
    if not plain_okuri:
        return None, []
    maybe_stem = plain_okuri[-1]
    if maybe_stem in CONJUGATABLE_LAST_OKURI_PART_OF_SPEECH:
        return plain_okuri[:-1], CONJUGATABLE_LAST_OKURI_PART_OF_SPEECH[maybe_stem]
    return None, []
