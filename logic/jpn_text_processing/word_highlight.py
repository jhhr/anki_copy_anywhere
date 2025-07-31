try:
    from ...utils.logger import Logger
except ImportError:
    from utils.logger import Logger  # type: ignore[no-redef]

from .starts_with_okurigana_conjugation import starts_with_okurigana_conjugation


def word_highlight(text: str, word: str, logger: Logger) -> list[tuple[int, int]]:
    """
    Takes a japanese word or phrase in dictionary form and finds any inflected occurrences of
    it in the given text. The word and text is expected to be in furigana syntax; with brackets
    containing the reading of the kanji words.

    Furigana syntax in text includes a space before the word begins, e.g "この 家[いえ]は" with the
    exception that the beginning of the string can omit the space, e.g "家[いえ]で 居[い]る".

    The word is then expected to be in the same syntax, e.g "家[いえ]". but the matched occurrence
    in the should include the space before the word. For example:

    word_highlight("この 家[いえ]は", "家[いえ]") --> (2, 7), "この* 家[いえ]*は"
    word_highlight("家[いえ]で 居[い]る", "家[いえ]") --> (0, 5), "*家[いえ]*で 居[い]る"

    Inflected forms are found for verbs up and including auxiliary verbs like いる, させる, せる
    negation forms like ない, させない, せない, な but not すぎる, すぎない.
    For example:
    word_highlight("私は 食[た]べている", "食[た]べる") --> (3, 11), "私は *食[た]べている*"
    word_highlight() --> (0, 10), "*食[た]べさせる*な!"

    For adjectives, the inflected forms are found up to and including the い form, but not
    the な form except when な is included in the word to match.
    For example:
    word_highlight("これ、 大[おお]きすぎない？", "大[おお]きい") --> (4, 10), "これ、 *大[おお]き*すぎない？"
    word_highlight("大[おお]きな 家[いえ]", "大[おお]きい") --> (0, 6), "*大[おお]き*な 家[いえ]"
    word_highlight("大[おお]きな 家[いえ]", "大[おお]きいな") --> (0, 7), "*大[おお]きな* 家[いえ]"
    word_highlight("安[やす]くて 良[い]いな～", "安[やす]い") --> (0, 7), "*安[やす]くて* 良[い]いな～"
    word_highlight("高[たか]いでも 良[よ]かろう", "良[い]い") --> (9, 16), "高[たか]いでも* 良[よ]かろう*"

    Args:
        text (str): The input text where the word needs to be highlighted.
        word (str): The word to highlight.

    Returns:
        list[tuple[int,int]]: A list of tuples containing the start and end indices of the
        word occurrences in the text.
    """
    if not text or not word:
        return []
