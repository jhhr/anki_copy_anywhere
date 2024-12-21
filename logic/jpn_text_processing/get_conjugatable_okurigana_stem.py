from typing import Union

CONJUGATABLE_LAST_OKURI = {
    # Godan verbs
    "う",
    "く",
    "ぐ",
    "す",
    "つ",
    "ぬ",
    "ぶ",
    "む",
    # Godan or ichidan, note also jiru and zuru verbs are ichidan
    "る",
    # i-adjectives
    "い",
}


def get_conjugatable_okurigana_stem(plain_okuri: str) -> Union[str, None]:
    """
    Returns the stem of a word's okurigana.
    :param plain_okuri: A dictionary form word's okurigana
    :return: The stem of the okurigana, after which conjugation is applied.
        Will be empty when the plain_okuri was a single kana and matches a conjugatable okuri.
        Return is None when there was no okuri or it was not conjugatable.
    """
    # Sanity check, we need at least one character
    if not plain_okuri:
        return None
    if plain_okuri[-1] in CONJUGATABLE_LAST_OKURI:
        return plain_okuri[:-1]
    return None
