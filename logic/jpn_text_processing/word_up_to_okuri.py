import sys
import re
from dataclasses import dataclass

from .regex import (
    KANJI_AND_FURIGANA_AND_OKURIGANA_RE,
)

WORD_SPLIT_RE = rf"^(.*?) ?{KANJI_AND_FURIGANA_AND_OKURIGANA_RE}$"
WORD_SPLIT_REC = re.compile(WORD_SPLIT_RE)


@dataclass
class WordSplitResult:
    before: str
    kanji: str
    furigana: str
    okurigana: str


def word_up_to_okuri(
    word: str,
) -> WordSplitResult:
    """
    Split a furigana syntax word into the uninflected part and the kanji + okurigana part that
    can be inflected.
    """
    # Find all matches of the kanji-furigana pattern
    import re

    matches = list(re.finditer(KANJI_AND_FURIGANA_AND_OKURIGANA_RE, word))

    if not matches:
        return WordSplitResult(before=word, kanji="", furigana="", okurigana="")

    # Get the last match (rightmost furigana pattern)
    last_match = matches[-1]

    # Everything before the last match
    before = word[: last_match.start()].rstrip()

    # Extract kanji, furigana, and okurigana from the last match
    kanji = last_match.group(1) or ""
    furigana = last_match.group(2) or ""
    okurigana = last_match.group(3) or ""

    # Now manually check characters after the "before" part until we reach the kanji
    # This handles spaces and other characters that should be part of "before"
    current_pos = len(before)

    # Skip forward until we find the first character of the kanji
    while current_pos < len(word) and kanji and word[current_pos] != kanji[0]:
        before += word[current_pos]
        current_pos += 1

    return WordSplitResult(before=before, kanji=kanji, furigana=furigana, okurigana=okurigana)


def test(
    text: str,
    expected: WordSplitResult,
    ignore_fail: bool = False,
):
    result = word_up_to_okuri(text)
    try:
        # Compare each part of the result
        assert result == expected
    except AssertionError:
        if ignore_fail:
            return
        # Highlight the diff between the expected and the result
        print(f"""\033[91m{text}
\033[93mExpected: {expected.before}, {expected.kanji}, {expected.furigana}, {expected.okurigana}
\033[92mGot:      {result.before}, {result.kanji}, {result.furigana}, {result.okurigana}
\033[0m""")
        # Stop testing here
        sys.exit(0)


def main():
    test(
        "漢字[かんじ]",
        WordSplitResult(before="", kanji="漢字", furigana="かんじ", okurigana=""),
    )
    test(
        "漢字[かんじ]の",
        WordSplitResult(before="", kanji="漢字", furigana="かんじ", okurigana="の"),
    )
    test(
        "読[よ]みます",
        WordSplitResult(before="", kanji="読", furigana="よ", okurigana="みます"),
    )
    # Hiragana before kanji
    test(
        "ご都合主義[つごうしゅぎ]",
        WordSplitResult(before="ご", kanji="都合主義", furigana="つごうしゅぎ", okurigana=""),
    )
    test(
        "やり 直[なお]す",
        WordSplitResult(before="やり ", kanji="直", furigana="なお", okurigana="す"),
    )
    # Katakana before kanji
    test(
        "ド 忘[わす]れる",
        WordSplitResult(before="ド ", kanji="忘", furigana="わす", okurigana="れる"),
    )
    test(
        "ピリ 辛[から]",
        WordSplitResult(before="ピリ ", kanji="辛", furigana="から", okurigana=""),
    )
    test(
        "感慨深[かんがいぶか]い",
        WordSplitResult(before="", kanji="感慨深", furigana="かんがいぶか", okurigana="い"),
    )
    test(
        "書[か]き 留[と]め",
        WordSplitResult(before="書[か]き ", kanji="留", furigana="と", okurigana="め"),
    )
    test(
        " 会[あ]って 見[み]る",
        WordSplitResult(before=" 会[あ]って ", kanji="見", furigana="み", okurigana="る"),
    )
    test(
        "便宜[べんぎ]を 図[はか]る",
        WordSplitResult(before="便宜[べんぎ]を ", kanji="図", furigana="はか", okurigana="る"),
    )
    test(
        "焼[や]け 棒杙[ぼっくい]",
        WordSplitResult(before="焼[や]け ", kanji="棒杙", furigana="ぼっくい", okurigana=""),
    )
    test("当[あ]て", WordSplitResult(before="", kanji="当", furigana="あ", okurigana="て"))
    test("したためる", WordSplitResult(before="したためる", kanji="", furigana="", okurigana=""))
    test("ダサい", WordSplitResult(before="ダサい", kanji="", furigana="", okurigana=""))
    # Missing space before furigana
    test(
        "意[い]を決[けっ]する",
        WordSplitResult(before="意[い]を", kanji="決", furigana="けっ", okurigana="する"),
    )
    # Space in string start
    test(
        " 見定[みさだ]める",
        WordSplitResult(before=" ", kanji="見定", furigana="みさだ", okurigana="める"),
    )
    # Space in start of the string but not before the last kanji
    test(
        " 入[い]れ込[こ]む",
        WordSplitResult(before=" 入[い]れ", kanji="込", furigana="こ", okurigana="む"),
    )
    test(
        "粛々[しゅくしゅく]",
        WordSplitResult(before="", kanji="粛々", furigana="しゅくしゅく", okurigana=""),
    )
    test(
        " 斯々然々[かくかくしかじか]",
        WordSplitResult(before=" ", kanji="斯々然々", furigana="かくかくしかじか", okurigana=""),
    )
    # Okurigana with small tsu
    test(
        "宵[よい]っぱり",
        WordSplitResult(before="", kanji="宵", furigana="よい", okurigana="っぱり"),
    )
    # Other characters before kanji
    test(
        "倉[くら]・納屋[なや]",
        WordSplitResult(before="倉[くら]・", kanji="納屋", furigana="なや", okurigana=""),
    )
    print("\n\033[92mTests passed\033[0m")


if __name__ == "__main__":
    main()
