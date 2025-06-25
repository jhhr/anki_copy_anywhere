import sys

from typing import Optional, Tuple
from .kana_highlight import kana_highlight, FuriReconstruct, WithTagsDef

try:
    from ..utils.logger import Logger
except ImportError:
    from utils.logger import Logger  # type: ignore[no-redef]


def test(
    test_name: str,
    kanji: Optional[str],
    sentence: str,
    ignore_fail: bool = False,
    assume_dictionary_form: bool = False,
    onyomi_to_katakana: bool = True,
    debug: bool = False,
    expected_furigana: Optional[str] = None,
    expected_furigana_with_tags_split: Optional[str] = None,
    expected_furigana_with_tags_merged: Optional[str] = None,
    expected_furikanji: Optional[str] = None,
    expected_furikanji_with_tags_split: Optional[str] = None,
    expected_furikanji_with_tags_merged: Optional[str] = None,
    expected_kana_only: Optional[str] = None,
    expected_kana_only_with_tags_split: Optional[str] = None,
    expected_kana_only_with_tags_merged: Optional[str] = None,
):
    """
    Function that tests the kana_highlight function
    """
    cases: list[Tuple[FuriReconstruct, WithTagsDef, Optional[str]]] = [
        (
            "furigana",
            WithTagsDef(False, False, onyomi_to_katakana, assume_dictionary_form),
            expected_furigana,
        ),
        (
            "furigana",
            WithTagsDef(True, False, onyomi_to_katakana, assume_dictionary_form),
            expected_furigana_with_tags_split,
        ),
        (
            "furigana",
            WithTagsDef(True, True, onyomi_to_katakana, assume_dictionary_form),
            expected_furigana_with_tags_merged,
        ),
        (
            "furikanji",
            WithTagsDef(False, False, onyomi_to_katakana, assume_dictionary_form),
            expected_furikanji,
        ),
        (
            "furikanji",
            WithTagsDef(True, False, onyomi_to_katakana, assume_dictionary_form),
            expected_furikanji_with_tags_split,
        ),
        (
            "furikanji",
            WithTagsDef(True, True, onyomi_to_katakana, assume_dictionary_form),
            expected_furikanji_with_tags_merged,
        ),
        (
            "kana_only",
            WithTagsDef(False, False, onyomi_to_katakana, assume_dictionary_form),
            expected_kana_only,
        ),
        (
            "kana_only",
            WithTagsDef(True, False, onyomi_to_katakana, assume_dictionary_form),
            expected_kana_only_with_tags_split,
        ),
        (
            "kana_only",
            WithTagsDef(True, True, onyomi_to_katakana, assume_dictionary_form),
            expected_kana_only_with_tags_merged,
        ),
    ]
    for return_type, with_tags_def, expected in cases:
        if not expected:
            continue
        logger = Logger("debug") if debug else Logger("error")
        result = kana_highlight(kanji, sentence, return_type, with_tags_def, logger=logger)
        if debug:
            print("\n\n")
        try:
            assert result == expected
        except AssertionError:
            if ignore_fail:
                continue
            # Re-run with logging enabled to see what went wrong
            kana_highlight(kanji, sentence, return_type, with_tags_def, logger=Logger("debug"))
            # Highlight the diff between the expected and the result
            print(f"""\033[91m{test_name}
Return type: {return_type}
{'With tags' if with_tags_def.with_tags else ''}
{'Tags merged' if with_tags_def.merge_consecutive else ''}
\033[93mExpected: {expected}
\033[92mGot:      {result}
\033[0m""")
            # Stop testing here
            sys.exit(0)


def main():
    test(
        test_name="Should not crash with no kanji_to_highlight",
        kanji=None,
        sentence="漢字[かんじ]の読[よ]み方[かた]を学[まな]ぶ。",
        expected_furigana=" 漢字[カンジ]の 読[よ]み 方[かた]を 学[まな]ぶ。",
        expected_furikanji=" カンジ[漢字]の よ[読]み かた[方]を まな[学]ぶ。",
        expected_kana_only="カンジのよみかたをまなぶ。",
        expected_furigana_with_tags_split=(
            "<on> 漢[カン]</on><on> 字[ジ]</on>の<kun> 読[よ]</kun><oku>み</oku><kun>"
            " 方[かた]</kun>を<kun> 学[まな]</kun><oku>ぶ</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 漢字[カンジ]</on>の<kun> 読[よ]</kun><oku>み</oku><kun> 方[かた]</kun>を"
            "<kun> 学[まな]</kun><oku>ぶ</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> カン[漢]</on><on> ジ[字]</on>の<kun> よ[読]</kun><oku>み</oku><kun>"
            " かた[方]</kun>を<kun> まな[学]</kun><oku>ぶ</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> カンジ[漢字]</on>の<kun> よ[読]</kun><oku>み</oku><kun> かた[方]</kun>を"
            "<kun> まな[学]</kun><oku>ぶ</oku>。"
        ),
        expected_kana_only_with_tags_split=(
            "<on>カン</on><on>ジ</on>の<kun>よ</kun><oku>み</oku><kun>かた</kun>を"
            "<kun>まな</kun><oku>ぶ</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>カンジ</on>の<kun>よ</kun><oku>み</oku><kun>かた</kun>を"
            "<kun>まな</kun><oku>ぶ</oku>。"
        ),
    )
    test(
        test_name="Should not crash with kanji that has empty onyomi or kunyomi",
        kanji="匂",
        # 匂 has no onyomi, 区 has no kunyomi
        sentence="この 区域[くいき]は 匂[にお]いがする。",
        expected_kana_only="この クイキは <b>におい</b>がする。",
        expected_furigana="この 区域[クイキ]は<b> 匂[にお]い</b>がする。",
        expected_furikanji="この クイキ[区域]は<b> にお[匂]い</b>がする。",
        expected_kana_only_with_tags_split=(
            "この <on>ク</on><on>イキ</on>は <b><kun>にお</kun><oku>い</oku></b>がする。"
        ),
        expected_furigana_with_tags_split=(
            "この<on> 区[ク]</on><on> 域[イキ]</on>は<b><kun> 匂[にお]</kun><oku>い</oku></b>がする。"
        ),
        expected_furikanji_with_tags_split=(
            "この<on> ク[区]</on><on> イキ[域]</on>は<b><kun> にお[匂]</kun><oku>い</oku></b>がする。"
        ),
        expected_kana_only_with_tags_merged=(
            "この <on>クイキ</on>は <b><kun>にお</kun><oku>い</oku></b>がする。"
        ),
        expected_furigana_with_tags_merged=(
            "この<on> 区域[クイキ]</on>は<b><kun> 匂[にお]</kun><oku>い</oku></b>がする。"
        ),
        expected_furikanji_with_tags_merged=(
            "この<on> クイキ[区域]</on>は<b><kun> にお[匂]</kun><oku>い</oku></b>がする。"
        ),
    )
    test(
        test_name="Should not incorrectly match onyomi twice 1/",
        kanji="視",
        # しちょうしゃ　has し in it twice but only the first one should be highlighted
        sentence="視聴者[しちょうしゃ]",
        expected_kana_only="<b>シ</b>チョウシャ",
        expected_furigana="<b> 視[シ]</b> 聴者[チョウシャ]",
        expected_furikanji="<b> シ[視]</b> チョウシャ[聴者]",
        expected_kana_only_with_tags_split="<b><on>シ</on></b><on>チョウ</on><on>シャ</on>",
        expected_furigana_with_tags_split="<b><on> 視[シ]</on></b><on> 聴[チョウ]</on><on> 者[シャ]</on>",
        expected_furikanji_with_tags_split="<b><on> シ[視]</on></b><on> チョウ[聴]</on><on> シャ[者]</on>",
        expected_kana_only_with_tags_merged="<b><on>シ</on></b><on>チョウシャ</on>",
        expected_furigana_with_tags_merged="<b><on> 視[シ]</on></b><on> 聴者[チョウシャ]</on>",
        expected_furikanji_with_tags_merged="<b><on> シ[視]</on></b><on> チョウシャ[聴者]</on>",
    )
    test(
        test_name="Should not incorrectly match onyomi twice 2/",
        kanji="儀",
        # ぎょうぎ　has ぎ in it twice but only the first one should be highlighted
        sentence="行儀[ぎょうぎ]",
        expected_kana_only="ギョウ<b>ギ</b>",
        expected_furigana=" 行[ギョウ]<b> 儀[ギ]</b>",
        expected_furikanji=" ギョウ[行]<b> ギ[儀]</b>",
        expected_kana_only_with_tags_split="<on>ギョウ</on><b><on>ギ</on></b>",
        expected_furigana_with_tags_split="<on> 行[ギョウ]</on><b><on> 儀[ギ]</on></b>",
        expected_furikanji_with_tags_split="<on> ギョウ[行]</on><b><on> ギ[儀]</on></b>",
        expected_kana_only_with_tags_merged="<on>ギョウ</on><b><on>ギ</on></b>",
        expected_furigana_with_tags_merged="<on> 行[ギョウ]</on><b><on> 儀[ギ]</on></b>",
        expected_furikanji_with_tags_merged="<on> ギョウ[行]</on><b><on> ギ[儀]</on></b>",
    )
    test(
        test_name="Should not match onyomi in whole edge match 1/",
        kanji="嗜",
        # the onyomi し occurs in the middle of the furigana but should not be matched
        sentence="嗜[たしな]まれたことは？",
        expected_kana_only="<b>たしなまれた</b>ことは？",
        expected_furigana="<b> 嗜[たしな]まれた</b>ことは？",
        expected_furikanji="<b> たしな[嗜]まれた</b>ことは？",
        expected_kana_only_with_tags_split="<b><kun>たしな</kun><oku>まれた</oku></b>ことは？",
        expected_furigana_with_tags_split="<b><kun> 嗜[たしな]</kun><oku>まれた</oku></b>ことは？",
        expected_furikanji_with_tags_split="<b><kun> たしな[嗜]</kun><oku>まれた</oku></b>ことは？",
        expected_kana_only_with_tags_merged="<b><kun>たしな</kun><oku>まれた</oku></b>ことは？",
        expected_furigana_with_tags_merged="<b><kun> 嗜[たしな]</kun><oku>まれた</oku></b>ことは？",
    )
    test(
        test_name="Should match onyomi twice in whole edge match 2/",
        kanji="悠",
        # the onyomi ユウ occurs twice in the furigana and should be matched both times
        sentence="悠々[ゆうゆう]とした時間[じかん]。",
        expected_kana_only="<b>ユウユウ</b>としたジカン。",
        expected_furigana="<b> 悠々[ユウユウ]</b>とした 時間[ジカン]。",
        expected_furikanji="<b> ユウユウ[悠々]</b>とした ジカン[時間]。",
        expected_kana_only_with_tags_split="<b><on>ユウユウ</on></b>とした<on>ジ</on><on>カン</on>。",
        expected_furigana_with_tags_split=(
            "<b><on> 悠々[ユウユウ]</on></b>とした<on> 時[ジ]</on><on> 間[カン]</on>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><on> ユウユウ[悠々]</on></b>とした<on> ジ[時]</on><on> カン[間]</on>。"
        ),
        expected_kana_only_with_tags_merged="<b><on>ユウユウ</on></b>とした<on>ジカン</on>。",
        expected_furigana_with_tags_merged="<b><on> 悠々[ユウユウ]</on></b>とした<on> 時間[ジカン]</on>。",
        expected_furikanji_with_tags_merged="<b><on> ユウユウ[悠々]</on></b>とした<on> ジカン[時間]</on>。",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 1/",
        kanji="去",
        # 消え去[きえさ]った　has え in the middle but った at the end is not included in the furigana
        sentence="団子[だんご]が 消え去[きえさ]った。",
        expected_kana_only="ダンごが きえ<b>さった</b>。",
        expected_furigana=" 団子[ダンご]が 消[き]え<b> 去[さ]った</b>。",
        expected_furikanji=" ダンご[団子]が き[消]え<b> さ[去]った</b>。",
        expected_kana_only_with_tags_split=(
            "<on>ダン</on><kun>ご</kun>が"
            " <kun>き</kun><oku>え</oku><b><kun>さ</kun><oku>った</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 団[ダン]</on><kun> 子[ご]</kun>が<kun> 消[き]</kun><oku>え</oku><b><kun>"
            " 去[さ]</kun><oku>った</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ダン[団]</on><kun> ご[子]</kun>が<kun> き[消]</kun><oku>え</oku><b><kun>"
            " さ[去]</kun><oku>った</oku></b>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>ダン</on><kun>ご</kun>が"
            " <kun>き</kun><oku>え</oku><b><kun>さ</kun><oku>った</oku></b>。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 団[ダン]</on><kun> 子[ご]</kun>が<kun> 消[き]</kun><oku>え</oku><b><kun>"
            " 去[さ]</kun><oku>った</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ダン[団]</on><kun> ご[子]</kun>が<kun> き[消]</kun><oku>え</oku><b><kun>"
            " さ[去]</kun><oku>った</oku></b>。"
        ),
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 2/",
        kanji="隣",
        # 隣り合わせ[となりあわせ]のまち　has り　in the middle and わせ　at the end of the group
        sentence="隣り合わせ[となりあわせ]の町[まち]。",
        expected_kana_only="<b>となり</b>あわせのまち。",
        expected_furigana="<b> 隣[とな]り</b> 合[あ]わせの 町[まち]。",
        expected_furikanji="<b> とな[隣]り</b> あ[合]わせの まち[町]。",
        expected_kana_only_with_tags_split=(
            "<b><kun>とな</kun><oku>り</oku></b><kun>あ</kun><oku>わせ</oku>の<kun>まち</kun>。"
        ),
        expected_furigana_with_tags_split=(
            "<b><kun> 隣[とな]</kun><oku>り</oku></b><kun> 合[あ]</kun><oku>わせ</oku>の"
            "<kun> 町[まち]</kun>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><kun> とな[隣]</kun><oku>り</oku></b><kun> あ[合]</kun><oku>わせ</oku>の"
            "<kun> まち[町]</kun>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><kun>とな</kun><oku>り</oku></b><kun>あ</kun><oku>わせ</oku>の<kun>まち</kun>。"
        ),
        expected_furigana_with_tags_merged=(
            "<b><kun> 隣[とな]</kun><oku>り</oku></b><kun> 合[あ]</kun><oku>わせ</oku>の"
            "<kun> 町[まち]</kun>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><kun> とな[隣]</kun><oku>り</oku></b><kun> あ[合]</kun><oku>わせ</oku>の"
            "<kun> まち[町]</kun>。"
        ),
    )
    test(
        test_name="Onyomi repeater word with no highlight",
        kanji="",
        sentence=" 愈々[いよいよ]",
        expected_kana_only=" いよいよ",
        expected_furigana=" 愈々[いよいよ]",
        expected_furikanji=" いよいよ[愈々]",
        expected_kana_only_with_tags_split=" <kun>いよいよ</kun>",
        expected_furigana_with_tags_split="<kun> 愈々[いよいよ]</kun>",
        expected_furikanji_with_tags_split="<kun> いよいよ[愈々]</kun>",
        expected_kana_only_with_tags_merged=" <kun>いよいよ</kun>",
        expected_furigana_with_tags_merged="<kun> 愈々[いよいよ]</kun>",
        expected_furikanji_with_tags_merged="<kun> いよいよ[愈々]</kun>",
    )
    test(
        test_name="Kunyomi repeater word with no highlight",
        kanji="",
        sentence=" 努々[ゆめゆめ]",
        expected_kana_only=" ゆめゆめ",
        expected_furigana=" 努々[ゆめゆめ]",
        expected_furikanji=" ゆめゆめ[努々]",
        expected_kana_only_with_tags_split=" <kun>ゆめゆめ</kun>",
        expected_furigana_with_tags_split="<kun> 努々[ゆめゆめ]</kun>",
        expected_furikanji_with_tags_split="<kun> ゆめゆめ[努々]</kun>",
        expected_kana_only_with_tags_merged=" <kun>ゆめゆめ</kun>",
        expected_furigana_with_tags_merged="<kun> 努々[ゆめゆめ]</kun>",
        expected_furikanji_with_tags_merged="<kun> ゆめゆめ[努々]</kun>",
    )
    test(
        test_name="Jukujikun repeater word with no repeating furigana with no highlight",
        kanji="",
        sentence="<gikun> 清々[すっきり]する</gikun>",
        expected_kana_only="<gikun> すっきりする</gikun>",
        expected_furigana="<gikun> 清々[すっきり]する</gikun>",
        expected_furikanji="<gikun> すっきり[清々]する</gikun>",
        expected_kana_only_with_tags_split="<gikun> <juk>すっきり</juk>する</gikun>",
        expected_furigana_with_tags_split="<gikun><juk> 清々[すっきり]</juk>する</gikun>",
        expected_furikanji_with_tags_split="<gikun><juk> すっきり[清々]</juk>する</gikun>",
        expected_kana_only_with_tags_merged="<gikun> <juk>すっきり</juk>する</gikun>",
        expected_furigana_with_tags_merged="<gikun><juk> 清々[すっきり]</juk>する</gikun>",
        expected_furikanji_with_tags_merged="<gikun><juk> すっきり[清々]</juk>する</gikun>",
    )
    test(
        test_name="Should match 斯斯 as kunyomi in 斯斯然然 - no highlight",
        kanji="",
        sentence=" 斯々然々[かくかくしかじか]",
        expected_kana_only=" かくかくしかじか",
        expected_furigana=" 斯々然々[かくかくしかじか]",
        expected_furikanji=" かくかくしかじか[斯々然々]",
        expected_kana_only_with_tags_split=" <kun>かくかく</kun><kun>しかじか</kun>",
        expected_furigana_with_tags_split="<kun> 斯々[かくかく]</kun><kun> 然々[しかじか]</kun>",
        expected_furikanji_with_tags_split="<kun> かくかく[斯々]</kun><kun> しかじか[然々]</kun>",
        expected_kana_only_with_tags_merged=" <kun>かくかくしかじか</kun>",
        expected_furigana_with_tags_merged="<kun> 斯々然々[かくかくしかじか]</kun>",
        expected_furikanji_with_tags_merged="<kun> かくかくしかじか[斯々然々]</kun>",
    )
    test(
        test_name="Should match 斯斯 as kunyomi in 斯斯然然 - with highlight",
        kanji="斯",
        sentence=" 斯々然々[かくかくしかじか]",
        expected_kana_only=" <b>かくかく</b>しかじか",
        expected_furigana="<b> 斯々[かくかく]</b> 然々[しかじか]",
        expected_furikanji="<b> かくかく[斯々]</b> しかじか[然々]",
        expected_kana_only_with_tags_split=" <b><kun>かくかく</kun></b><kun>しかじか</kun>",
        expected_furigana_with_tags_split="<b><kun> 斯々[かくかく]</kun></b><kun> 然々[しかじか]</kun>",
        expected_furikanji_with_tags_split="<b><kun> かくかく[斯々]</kun></b><kun> しかじか[然々]</kun>",
        expected_kana_only_with_tags_merged=" <b><kun>かくかく</kun></b><kun>しかじか</kun>",
        expected_furigana_with_tags_merged="<b><kun> 斯々[かくかく]</kun></b><kun> 然々[しかじか]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> かくかく[斯々]</kun></b><kun> しかじか[然々]</kun>",
    )
    test(
        test_name="Matches word that uses the repeater 々 with rendaku 1/",
        kanji="国",
        sentence="国々[くにぐに]の 関係[かんけい]が 深い[ふかい]。",
        expected_kana_only="<b>くにぐに</b>の カンケイが ふかい。",
        expected_furigana="<b> 国々[くにぐに]</b>の 関係[カンケイ]が 深[ふか]い。",
        expected_furikanji="<b> くにぐに[国々]</b>の カンケイ[関係]が ふか[深]い。",
        expected_kana_only_with_tags_split=(
            "<b><kun>くにぐに</kun></b>の <on>カン</on><on>ケイ</on>が <kun>ふか</kun><oku>い</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<b><kun> 国々[くにぐに]</kun></b>の<on> 関[カン]</on><on>"
            " 係[ケイ]</on>が<kun> 深[ふか]</kun><oku>い</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><kun> くにぐに[国々]</kun></b>の<on> カン[関]</on><on>"
            " ケイ[係]</on>が<kun> ふか[深]</kun><oku>い</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><kun>くにぐに</kun></b>の <on>カンケイ</on>が <kun>ふか</kun><oku>い</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<b><kun> 国々[くにぐに]</kun></b>の<on> 関係[カンケイ]</on>が<kun>"
            " 深[ふか]</kun><oku>い</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><kun> くにぐに[国々]</kun></b>の<on> カンケイ[関係]</on>が<kun>"
            " ふか[深]</kun><oku>い</oku>。"
        ),
    )
    test(
        test_name="Matches word that uses the repeater 々 with rendaku 2/",
        kanji="時",
        sentence="時々[ときどき] 雨[あめ]が 降る[ふる]。",
        expected_kana_only="<b>ときどき</b> あめが ふる。",
        expected_furigana="<b> 時々[ときどき]</b> 雨[あめ]が 降[ふ]る。",
        expected_furikanji="<b> ときどき[時々]</b> あめ[雨]が ふ[降]る。",
        expected_kana_only_with_tags_split=(
            "<b><kun>ときどき</kun></b> <kun>あめ</kun>が <kun>ふ</kun><oku>る</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<b><kun> 時々[ときどき]</kun></b><kun> 雨[あめ]</kun>が<kun> 降[ふ]</kun><oku>る</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><kun> ときどき[時々]</kun></b><kun> あめ[雨]</kun>が<kun> ふ[降]</kun><oku>る</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><kun>ときどき</kun></b> <kun>あめ</kun>が <kun>ふ</kun><oku>る</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<b><kun> 時々[ときどき]</kun></b><kun> 雨[あめ]</kun>が<kun> 降[ふ]</kun><oku>る</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><kun> ときどき[時々]</kun></b><kun> あめ[雨]</kun>が<kun> ふ[降]</kun><oku>る</oku>。"
        ),
    )

    test(
        test_name="Matches word that uses the repeater 々 with rendaku 3/",
        kanji="云",
        sentence="云々[うんぬん]",
        expected_kana_only="<b>ウンヌン</b>",
        expected_furigana="<b> 云々[ウンヌン]</b>",
        expected_furikanji="<b> ウンヌン[云々]</b>",
        expected_kana_only_with_tags_split="<b><on>ウンヌン</on></b>",
        expected_furigana_with_tags_split="<b><on> 云々[ウンヌン]</on></b>",
        expected_furikanji_with_tags_split="<b><on> ウンヌン[云々]</on></b>",
        expected_kana_only_with_tags_merged="<b><on>ウンヌン</on></b>",
        expected_furigana_with_tags_merged="<b><on> 云々[ウンヌン]</on></b>",
        expected_furikanji_with_tags_merged="<b><on> ウンヌン[云々]</on></b>",
    )
    test(
        test_name="Rendaku test 1/",
        kanji="婦",
        sentence="新婦[しんぷ]",
        expected_kana_only="シン<b>プ</b>",
        expected_furigana=" 新[シン]<b> 婦[プ]</b>",
        expected_furikanji=" シン[新]<b> プ[婦]</b>",
        expected_kana_only_with_tags_split="<on>シン</on><b><on>プ</on></b>",
        expected_furigana_with_tags_split="<on> 新[シン]</on><b><on> 婦[プ]</on></b>",
        expected_furikanji_with_tags_split="<on> シン[新]</on><b><on> プ[婦]</on></b>",
        expected_kana_only_with_tags_merged="<on>シン</on><b><on>プ</on></b>",
        expected_furigana_with_tags_merged="<on> 新[シン]</on><b><on> 婦[プ]</on></b>",
        expected_furikanji_with_tags_merged="<on> シン[新]</on><b><on> プ[婦]</on></b>",
    )
    test(
        test_name="Matches repeater in the middle of the word from left edge",
        kanji="菜",
        sentence="娃々菜[わわさい]",
        expected_kana_only="ワワ<b>サイ</b>",
        expected_furigana=" 娃々[ワワ]<b> 菜[サイ]</b>",
        expected_furikanji=" ワワ[娃々]<b> サイ[菜]</b>",
        expected_kana_only_with_tags_split="<on>ワワ</on><b><on>サイ</on></b>",
        expected_furigana_with_tags_split="<on> 娃々[ワワ]</on><b><on> 菜[サイ]</on></b>",
        expected_furikanji_with_tags_split="<on> ワワ[娃々]</on><b><on> サイ[菜]</on></b>",
        expected_kana_only_with_tags_merged="<on>ワワ</on><b><on>サイ</on></b>",
        expected_furigana_with_tags_merged="<on> 娃々[ワワ]</on><b><on> 菜[サイ]</on></b>",
        expected_furikanji_with_tags_merged="<on> ワワ[娃々]</on><b><on> サイ[菜]</on></b>",
    )
    test(
        test_name="Matches repeater in the middle of the word from right edge",
        kanji="奄",
        sentence="気息奄々[きそくえんえん]",
        expected_kana_only="キソク<b>エンエン</b>",
        expected_kana_only_with_tags_split="<on>キ</on><on>ソク</on><b><on>エンエン</on></b>",
        expected_kana_only_with_tags_merged="<on>キソク</on><b><on>エンエン</on></b>",
    )
    test(
        test_name="Matches repeater in the middle of the word from middle edge",
        kanji="侃",
        sentence="熱々侃々諤々[あつあつかんかんがくがく]",
        expected_kana_only="あつあつ<b>カンカン</b>ガクガク",
        expected_kana_only_with_tags_split="<kun>あつあつ</kun><b><on>カンカン</on></b><on>ガクガク</on>",
        expected_kana_only_with_tags_merged="<kun>あつあつ</kun><b><on>カンカン</on></b><on>ガクガク</on>",
    )
    test(
        test_name="Matches word that uses the repeater 々 with small tsu",
        kanji="刻",
        sentence="刻々[こっこく]と 変化[へんか]する。",
        expected_kana_only="<b>コッコク</b>と ヘンカする。",
        expected_furigana="<b> 刻々[コッコク]</b>と 変化[ヘンカ]する。",
        expected_furikanji="<b> コッコク[刻々]</b>と ヘンカ[変化]する。",
        expected_kana_only_with_tags_split="<b><on>コッコク</on></b>と <on>ヘン</on><on>カ</on>する。",
        expected_furigana_with_tags_split=(
            "<b><on> 刻々[コッコク]</on></b>と<on> 変[ヘン]</on><on> 化[カ]</on>する。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><on> コッコク[刻々]</on></b>と<on> ヘン[変]</on><on> カ[化]</on>する。"
        ),
        expected_kana_only_with_tags_merged="<b><on>コッコク</on></b>と <on>ヘンカ</on>する。",
        expected_furigana_with_tags_merged="<b><on> 刻々[コッコク]</on></b>と<on> 変化[ヘンカ]</on>する。",
    )
    test(
        test_name="Matches repeater adjective 瑞々しい - with highlight",
        kanji="瑞",
        sentence="瑞々[みずみず]しく",
        expected_kana_only="<b>みずみずしく</b>",
        expected_furigana="<b> 瑞々[みずみず]しく</b>",
        expected_furikanji="<b> みずみず[瑞々]しく</b>",
        expected_kana_only_with_tags_split="<b><kun>みずみず</kun><oku>しく</oku></b>",
        expected_furigana_with_tags_split="<b><kun> 瑞々[みずみず]</kun><oku>しく</oku></b>",
        expected_furikanji_with_tags_split="<b><kun> みずみず[瑞々]</kun><oku>しく</oku></b>",
        expected_kana_only_with_tags_merged="<b><kun>みずみず</kun><oku>しく</oku></b>",
        expected_furigana_with_tags_merged="<b><kun> 瑞々[みずみず]</kun><oku>しく</oku></b>",
        expected_furikanji_with_tags_merged="<b><kun> みずみず[瑞々]</kun><oku>しく</oku></b>",
    )
    test(
        test_name="Matches repeater adjective 瑞々しい - no highlight",
        kanji="",
        sentence="瑞々[みずみず]しさ",
        expected_kana_only="みずみずしさ",
        expected_furigana=" 瑞々[みずみず]しさ",
        expected_furikanji=" みずみず[瑞々]しさ",
        expected_kana_only_with_tags_split="<kun>みずみず</kun><oku>しさ</oku>",
        expected_furigana_with_tags_split="<kun> 瑞々[みずみず]</kun><oku>しさ</oku>",
        expected_furikanji_with_tags_split="<kun> みずみず[瑞々]</kun><oku>しさ</oku>",
        expected_kana_only_with_tags_merged="<kun>みずみず</kun><oku>しさ</oku>",
        expected_furigana_with_tags_merged="<kun> 瑞々[みずみず]</kun><oku>しさ</oku>",
        expected_furikanji_with_tags_merged="<kun> みずみず[瑞々]</kun><oku>しさ</oku>",
    )
    test(
        test_name="Matches repeater adjective with other word - with highlight",
        kanji="瑞",
        sentence="超瑞々[ちょうみずみず]しい",
        expected_kana_only="チョウ<b>みずみずしい</b>",
        expected_furigana=" 超[チョウ]<b> 瑞々[みずみず]しい</b>",
        expected_furikanji=" チョウ[超]<b> みずみず[瑞々]しい</b>",
        expected_kana_only_with_tags_split="<on>チョウ</on><b><kun>みずみず</kun><oku>しい</oku></b>",
        expected_furigana_with_tags_split=(
            "<on> 超[チョウ]</on><b><kun> 瑞々[みずみず]</kun><oku>しい</oku></b>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> チョウ[超]</on><b><kun> みずみず[瑞々]</kun><oku>しい</oku></b>"
        ),
        expected_kana_only_with_tags_merged="<on>チョウ</on><b><kun>みずみず</kun><oku>しい</oku></b>",
        expected_furigana_with_tags_merged=(
            "<on> 超[チョウ]</on><b><kun> 瑞々[みずみず]</kun><oku>しい</oku></b>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> チョウ[超]</on><b><kun> みずみず[瑞々]</kun><oku>しい</oku></b>"
        ),
    )
    test(
        test_name="Matches repeater adjective with other word - no highlight",
        kanji="",
        sentence="超瑞々[ちょうみずみず]しい",
        expected_kana_only="チョウみずみずしい",
        expected_furigana=" 超瑞々[チョウみずみず]しい",
        expected_furikanji=" チョウみずみず[超瑞々]しい",
        expected_kana_only_with_tags_split="<on>チョウ</on><kun>みずみず</kun><oku>しい</oku>",
        expected_furigana_with_tags_split="<on> 超[チョウ]</on><kun> 瑞々[みずみず]</kun><oku>しい</oku>",
        expected_furikanji_with_tags_split="<on> チョウ[超]</on><kun> みずみず[瑞々]</kun><oku>しい</oku>",
        expected_kana_only_with_tags_merged="<on>チョウ</on><kun>みずみず</kun><oku>しい</oku>",
        expected_furigana_with_tags_merged="<on> 超[チョウ]</on><kun> 瑞々[みずみず]</kun><oku>しい</oku>",
        expected_furikanji_with_tags_merged="<on> チョウ[超]</on><kun> みずみず[瑞々]</kun><oku>しい</oku>",
    )
    test(
        test_name="Matches repeater adjective with other repeater word - with highlight",
        kanji="瑞",
        sentence="精々瑞々[せいせいみずみず]しい",
        expected_kana_only="セイセイ<b>みずみずしい</b>",
        expected_furigana=" 精々[セイセイ]<b> 瑞々[みずみず]しい</b>",
        expected_furikanji=" セイセイ[精々]<b> みずみず[瑞々]しい</b>",
        expected_kana_only_with_tags_split="<on>セイセイ</on><b><kun>みずみず</kun><oku>しい</oku></b>",
        expected_furigana_with_tags_split=(
            "<on> 精々[セイセイ]</on><b><kun> 瑞々[みずみず]</kun><oku>しい</oku></b>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> セイセイ[精々]</on><b><kun> みずみず[瑞々]</kun><oku>しい</oku></b>"
        ),
        expected_kana_only_with_tags_merged="<on>セイセイ</on><b><kun>みずみず</kun><oku>しい</oku></b>",
        expected_furigana_with_tags_merged=(
            "<on> 精々[セイセイ]</on><b><kun> 瑞々[みずみず]</kun><oku>しい</oku></b>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> セイセイ[精々]</on><b><kun> みずみず[瑞々]</kun><oku>しい</oku></b>"
        ),
    )
    test(
        test_name="Matches repeater adjective with other repeater word - no highlight",
        kanji="",
        sentence="精々瑞々[せいせいみずみず]しい",
        expected_kana_only="セイセイみずみずしい",
        expected_furigana=" 精々瑞々[セイセイみずみず]しい",
        expected_furikanji=" セイセイみずみず[精々瑞々]しい",
        expected_kana_only_with_tags_split="<on>セイセイ</on><kun>みずみず</kun><oku>しい</oku>",
        expected_furigana_with_tags_split=(
            "<on> 精々[セイセイ]</on><kun> 瑞々[みずみず]</kun><oku>しい</oku>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> セイセイ[精々]</on><kun> みずみず[瑞々]</kun><oku>しい</oku>"
        ),
        expected_kana_only_with_tags_merged="<on>セイセイ</on><kun>みずみず</kun><oku>しい</oku>",
        expected_furigana_with_tags_merged=(
            "<on> 精々[セイセイ]</on><kun> 瑞々[みずみず]</kun><oku>しい</oku>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> セイセイ[精々]</on><kun> みずみず[瑞々]</kun><oku>しい</oku>"
        ),
    )
    test(
        test_name="Matches rendaku containing repeater adjective 猛々しい - with highlight",
        kanji="猛",
        sentence="猛々[たけだけ]しい",
        expected_kana_only="<b>たけだけしい</b>",
        expected_furigana="<b> 猛々[たけだけ]しい</b>",
        expected_furikanji="<b> たけだけ[猛々]しい</b>",
        expected_kana_only_with_tags_split="<b><kun>たけだけ</kun><oku>しい</oku></b>",
        expected_furigana_with_tags_split="<b><kun> 猛々[たけだけ]</kun><oku>しい</oku></b>",
        expected_furikanji_with_tags_split="<b><kun> たけだけ[猛々]</kun><oku>しい</oku></b>",
        expected_kana_only_with_tags_merged="<b><kun>たけだけ</kun><oku>しい</oku></b>",
        expected_furigana_with_tags_merged="<b><kun> 猛々[たけだけ]</kun><oku>しい</oku></b>",
        expected_furikanji_with_tags_merged="<b><kun> たけだけ[猛々]</kun><oku>しい</oku></b>",
    )
    test(
        test_name="Matches rendaku containing repeater adjective 猛々しい - no highlight",
        kanji="",
        sentence="猛猛[たけだけ]しい",
        expected_kana_only="たけだけしい",
        expected_furigana=" 猛々[たけだけ]しい",
        expected_furikanji=" たけだけ[猛々]しい",
        expected_kana_only_with_tags_split="<kun>たけだけ</kun><oku>しい</oku>",
        expected_furigana_with_tags_split="<kun> 猛々[たけだけ]</kun><oku>しい</oku>",
        expected_furikanji_with_tags_split="<kun> たけだけ[猛々]</kun><oku>しい</oku>",
        expected_kana_only_with_tags_merged="<kun>たけだけ</kun><oku>しい</oku>",
        expected_furigana_with_tags_merged="<kun> 猛々[たけだけ]</kun><oku>しい</oku>",
        expected_furikanji_with_tags_merged="<kun> たけだけ[猛々]</kun><oku>しい</oku>",
    )
    test(
        test_name="Should be able to clean furigana that bridges over some okurigana 3/",
        kanji="止",
        # A third edge case: there is only okurigana at the end
        sentence="歯止め[はどめ]",
        expected_kana_only="は<b>どめ</b>",
        expected_furigana=" 歯[は]<b> 止[ど]め</b>",
        expected_furikanji=" は[歯]<b> ど[止]め</b>",
        expected_kana_only_with_tags_split="<kun>は</kun><b><kun>ど</kun><oku>め</oku></b>",
        expected_furigana_with_tags_split="<kun> 歯[は]</kun><b><kun> 止[ど]</kun><oku>め</oku></b>",
        expected_furikanji_with_tags_split="<kun> は[歯]</kun><b><kun> ど[止]</kun><oku>め</oku></b>",
        expected_kana_only_with_tags_merged="<kun>は</kun><b><kun>ど</kun><oku>め</oku></b>",
        expected_furigana_with_tags_merged="<kun> 歯[は]</kun><b><kun> 止[ど]</kun><oku>め</oku></b>",
        expected_furikanji_with_tags_merged="<kun> は[歯]</kun><b><kun> ど[止]</kun><oku>め</oku></b>",
    )
    test(
        test_name="Is able to match the same kanji occurring twice",
        kanji="閣",
        sentence="新[しん] 内閣[ないかく]の 組閣[そかく]が 発表[はっぴょう]された。",
        expected_kana_only="シン ナイ<b>カク</b>の ソ<b>カク</b>が ハッピョウされた。",
        expected_furigana=(
            " 新[シン] 内[ナイ]<b> 閣[カク]</b>の 組[ソ]<b> 閣[カク]</b>が 発表[ハッピョウ]された。"
        ),
        expected_furikanji=(
            " シン[新] ナイ[内]<b> カク[閣]</b>の ソ[組]<b> カク[閣]</b>が ハッピョウ[発表]された。"
        ),
    )
    test(
        test_name="Is able to match the same kanji occurring twice with other using small tsu",
        kanji="国",
        sentence="その2 国[こく]は 国交[こっこう]を 断絶[だんぜつ]した。",
        expected_kana_only="その2 <b>コク</b>は <b>コッ</b>コウを ダンゼツした。",
        expected_furigana="その2<b> 国[コク]</b>は<b> 国[コッ]</b> 交[コウ]を 断絶[ダンゼツ]した。",
        expected_furikanji="その2<b> コク[国]</b>は<b> コッ[国]</b> コウ[交]を ダンゼツ[断絶]した。",
        expected_kana_only_with_tags_split=(
            "その2 <b><on>コク</on></b>は <b><on>コッ</on></b><on>コウ</on>を"
            " <on>ダン</on><on>ゼツ</on>した。"
        ),
        expected_furigana_with_tags_split=(
            "その2<b><on> 国[コク]</on></b>は<b><on> 国[コッ]</on></b><on> 交[コウ]</on>を<on>"
            " 断[ダン]</on><on> 絶[ゼツ]</on>した。"
        ),
        expected_furikanji_with_tags_split=(
            "その2<b><on> コク[国]</on></b>は<b><on> コッ[国]</on></b><on> コウ[交]</on>を<on>"
            " ダン[断]</on><on> ゼツ[絶]</on>した。"
        ),
        expected_kana_only_with_tags_merged=(
            "その2 <b><on>コク</on></b>は <b><on>コッ</on></b><on>コウ</on>を <on>ダンゼツ</on>した。"
        ),
        expected_furigana_with_tags_merged=(
            "その2<b><on> 国[コク]</on></b>は<b><on> 国[コッ]</on></b><on> 交[コウ]</on>を<on>"
            " 断絶[ダンゼツ]</on>した。"
        ),
        expected_furikanji_with_tags_merged=(
            "その2<b><on> コク[国]</on></b>は<b><on> コッ[国]</on></b><on> コウ[交]</on>を<on>"
            " ダンゼツ[断絶]</on>した。"
        ),
    )
    test(
        test_name="Is able to pick the right reading when there are multiple matches 1/",
        kanji="靴",
        # ながぐつ　has が (onyomi か match) and ぐつ (kunyomi くつ) as matches
        sentence="お 前[まえ]いつも 長靴[ながぐつ]に 傘[かさ]さしてキメーんだよ！！",
        expected_kana_only="お まえいつも なが<b>ぐつ</b>に かささしてキメーんだよ！！",
        expected_furigana="お 前[まえ]いつも 長[なが]<b> 靴[ぐつ]</b>に 傘[かさ]さしてキメーんだよ！！",
        expected_furikanji="お まえ[前]いつも なが[長]<b> ぐつ[靴]</b>に かさ[傘]さしてキメーんだよ！！",
        expected_kana_only_with_tags_split=(
            "お <kun>まえ</kun>いつも <kun>なが</kun><b><kun>ぐつ</kun></b>に"
            " <kun>かさ</kun>さしてキメーんだよ！！"
        ),
        expected_furigana_with_tags_split=(
            "お<kun> 前[まえ]</kun>いつも<kun> 長[なが]</kun><b><kun> 靴[ぐつ]</kun></b>に"
            "<kun> 傘[かさ]</kun>さしてキメーんだよ！！"
        ),
        expected_furikanji_with_tags_split=(
            "お<kun> まえ[前]</kun>いつも<kun> なが[長]</kun><b><kun> ぐつ[靴]</kun></b>に"
            "<kun> かさ[傘]</kun>さしてキメーんだよ！！"
        ),
        expected_kana_only_with_tags_merged=(
            "お <kun>まえ</kun>いつも <kun>なが</kun><b><kun>ぐつ</kun></b>に"
            " <kun>かさ</kun>さしてキメーんだよ！！"
        ),
        expected_furigana_with_tags_merged=(
            "お<kun> 前[まえ]</kun>いつも<kun> 長[なが]</kun><b><kun> 靴[ぐつ]</kun></b>に"
            "<kun> 傘[かさ]</kun>さしてキメーんだよ！！"
        ),
        expected_furikanji_with_tags_merged=(
            "お<kun> まえ[前]</kun>いつも<kun> なが[長]</kun><b><kun> ぐつ[靴]</kun></b>に"
            "<kun> かさ[傘]</kun>さしてキメーんだよ！！"
        ),
    )
    test(
        test_name="Is able to pick the right reading when there are multiple matches 2/",
        kanji="輸",
        # 輸 has ゆ and しゅ as onyomi readings, should correctly match to the left edge
        sentence="輸出[ゆしゅつ]可能[かのう]。",
        expected_kana_only="<b>ユ</b>シュツカノウ。",
        expected_furigana="<b> 輸[ユ]</b> 出[シュツ] 可能[カノウ]。",
        expected_furikanji="<b> ユ[輸]</b> シュツ[出] カノウ[可能]。",
        expected_kana_only_with_tags_split="<b><on>ユ</on></b><on>シュツ</on><on>カ</on><on>ノウ</on>。",
        expected_furigana_with_tags_split=(
            "<b><on> 輸[ユ]</on></b><on> 出[シュツ]</on><on> 可[カ]</on><on> 能[ノウ]</on>。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><on> ユ[輸]</on></b><on> シュツ[出]</on><on> カ[可]</on><on> ノウ[能]</on>。"
        ),
        expected_kana_only_with_tags_merged="<b><on>ユ</on></b><on>シュツ</on><on>カノウ</on>。",
        expected_furigana_with_tags_merged=(
            "<b><on> 輸[ユ]</on></b><on> 出[シュツ]</on><on> 可能[カノウ]</on>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><on> ユ[輸]</on></b><on> シュツ[出]</on><on> カノウ[可能]</on>。"
        ),
    )
    test(
        test_name="Should match reading in 4 kanji compound word",
        kanji="必",
        sentence="見敵必殺[けんてきひっさつ]の 指示[しじ]もないのに 戦闘[せんとう]は 不自然[ふしぜん]。",
        expected_kana_only="ケンテキ<b>ヒッ</b>サツの シジもないのに セントウは フシゼン。",
        expected_furigana=(
            " 見敵[ケンテキ]<b> 必[ヒッ]</b> 殺[サツ]の 指示[シジ]もないのに"
            " 戦闘[セントウ]は 不自然[フシゼン]。"
        ),
        expected_furikanji=(
            " ケンテキ[見敵]<b> ヒッ[必]</b> サツ[殺]の シジ[指示]もないのに"
            " セントウ[戦闘]は フシゼン[不自然]。"
        ),
        expected_kana_only_with_tags_split=(
            "<on>ケン</on><on>テキ</on><b><on>ヒッ</on></b><on>サツ</on>の"
            " <on>シ</on><on>ジ</on>もないのに <on>セン</on><on>トウ</on>は"
            " <on>フ</on><on>シ</on><on>ゼン</on>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 見[ケン]</on><on> 敵[テキ]</on><b><on> 必[ヒッ]</on></b><on> 殺[サツ]</on>の"
            "<on> 指[シ]</on><on> 示[ジ]</on>もないのに<on> 戦[セン]</on><on> 闘[トウ]</on>は"
            "<on> 不[フ]</on><on> 自[シ]</on><on> 然[ゼン]</on>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ケン[見]</on><on> テキ[敵]</on><b><on> ヒッ[必]</on></b><on> サツ[殺]</on>の"
            "<on> シ[指]</on><on> ジ[示]</on>もないのに<on> セン[戦]</on><on> トウ[闘]</on>は"
            "<on> フ[不]</on><on> シ[自]</on><on> ゼン[然]</on>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>ケンテキ</on><b><on>ヒッ</on></b><on>サツ</on>の <on>シジ</on>もないのに"
            " <on>セントウ</on>は <on>フシゼン</on>。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 見敵[ケンテキ]</on><b><on> 必[ヒッ]</on></b><on> 殺[サツ]</on>の"
            "<on> 指示[シジ]</on>もないのに<on> 戦闘[セントウ]</on>は<on> 不自然[フシゼン]</on>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ケンテキ[見敵]</on><b><on> ヒッ[必]</on></b><on> サツ[殺]</on>の"
            "<on> シジ[指示]</on>もないのに<on> セントウ[戦闘]</on>は<on> フシゼン[不自然]</on>。"
        ),
    )
    test(
        test_name="Should match reading in middle of 3 kanji kunyomi compound",
        kanji="馴",
        sentence="幼馴染[おさななじ]みと 久[ひさ]しぶりに 会[あ]った。",
        expected_kana_only="おさな<b>な</b>じみと ひさしぶりに あった。",
        expected_furigana=" 幼[おさな]<b> 馴[な]</b> 染[じ]みと 久[ひさ]しぶりに 会[あ]った。",
        expected_furikanji=" おさな[幼]<b> な[馴]</b> じ[染]みと ひさ[久]しぶりに あ[会]った。",
        expected_kana_only_with_tags_split=(
            "<kun>おさな</kun><b><kun>な</kun></b><kun>じ</kun><oku>み</oku>と"
            " <kun>ひさ</kun><oku>し</oku>ぶりに <kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 幼[おさな]</kun><b><kun> 馴[な]</kun></b><kun> 染[じ]</kun><oku>み</oku>と<kun>"
            " 久[ひさ]</kun><oku>し</oku>ぶりに<kun> 会[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> おさな[幼]</kun><b><kun> な[馴]</kun></b><kun> じ[染]</kun><oku>み</oku>と<kun>"
            " ひさ[久]</kun><oku>し</oku>ぶりに<kun> あ[会]</kun><oku>った</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>おさな</kun><b><kun>な</kun></b><kun>じ</kun><oku>み</oku>と"
            " <kun>ひさ</kun><oku>し</oku>ぶりに <kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 幼[おさな]</kun><b><kun> 馴[な]</kun></b><kun> 染[じ]</kun><oku>み</oku>と<kun>"
            " 久[ひさ]</kun><oku>し</oku>ぶりに<kun> 会[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> おさな[幼]</kun><b><kun> な[馴]</kun></b><kun> じ[染]</kun><oku>み</oku>と<kun>"
            " ひさ[久]</kun><oku>し</oku>ぶりに<kun> あ[会]</kun><oku>った</oku>。"
        ),
    )
    test(
        test_name="Should match furigana for numbers",
        kanji="賊",
        # Note: jpn number
        sentence="海賊[かいぞく]たちは ７[なな]つの 海[うみ]を 航海[こうかい]した。",
        expected_kana_only="カイ<b>ゾク</b>たちは ななつの うみを コウカイした。",
        expected_furigana=" 海[カイ]<b> 賊[ゾク]</b>たちは ７[なな]つの 海[うみ]を 航海[コウカイ]した。",
        expected_furikanji=" カイ[海]<b> ゾク[賊]</b>たちは なな[７]つの うみ[海]を コウカイ[航海]した。",
        expected_kana_only_with_tags_split=(
            "<on>カイ</on><b><on>ゾク</on></b>たちは <kun>なな</kun><oku>つ</oku>の <kun>うみ</kun>を"
            " <on>コウ</on><on>カイ</on>した。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 海[カイ]</on><b><on> 賊[ゾク]</on></b>たちは<kun> ７[なな]</kun><oku>つ</oku>の"
            "<kun>"
            " 海[うみ]</kun>を<on> 航[コウ]</on><on> 海[カイ]</on>した。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> カイ[海]</on><b><on> ゾク[賊]</on></b>たちは<kun> なな[７]</kun><oku>つ</oku>の"
            "<kun>"
            " うみ[海]</kun>を<on> コウ[航]</on><on> カイ[海]</on>した。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>カイ</on><b><on>ゾク</on></b>たちは <kun>なな</kun><oku>つ</oku>の <kun>うみ</kun>を"
            " <on>コウカイ</on>した。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 海[カイ]</on><b><on> 賊[ゾク]</on></b>たちは<kun> ７[なな]</kun><oku>つ</oku>の"
            "<kun>"
            " 海[うみ]</kun>を<on> 航海[コウカイ]</on>した。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> カイ[海]</on><b><on> ゾク[賊]</on></b>たちは<kun> なな[７]</kun><oku>つ</oku>の"
            "<kun>"
            " うみ[海]</kun>を<on> コウカイ[航海]</on>した。"
        ),
    )
    test(
        test_name="Should match the full reading match when there are multiple /1",
        kanji="由",
        # Both ゆ and ゆい are in the furigana but the correct match is ゆい
        sentence="彼女[かのじょ]は 由緒[ゆいしょ]ある 家柄[いえがら]の 出[で]だ。",
        expected_kana_only="かのジョは <b>ユイ</b>ショある いえがらの でだ。",
        expected_furigana=" 彼女[かのジョ]は<b> 由[ユイ]</b> 緒[ショ]ある 家柄[いえがら]の 出[で]だ。",
        expected_furikanji=" かのジョ[彼女]は<b> ユイ[由]</b> ショ[緒]ある いえがら[家柄]の で[出]だ。",
        expected_kana_only_with_tags_split=(
            "<kun>かの</kun><on>ジョ</on>は <b><on>ユイ</on></b><on>ショ</on>ある"
            " <kun>いえ</kun><kun>がら</kun>の <kun>で</kun>だ。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 彼[かの]</kun><on> 女[ジョ]</on>は<b><on> 由[ユイ]</on></b><on>"
            " 緒[ショ]</on>ある<kun> 家[いえ]</kun><kun> 柄[がら]</kun>の<kun>"
            " 出[で]</kun>だ。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> かの[彼]</kun><on> ジョ[女]</on>は<b><on> ユイ[由]</on></b><on>"
            " ショ[緒]</on>ある<kun> いえ[家]</kun><kun> がら[柄]</kun>の<kun>"
            " で[出]</kun>だ。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>かの</kun><on>ジョ</on>は <b><on>ユイ</on></b><on>ショ</on>ある"
            " <kun>いえがら</kun>の <kun>で</kun>だ。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 彼[かの]</kun><on> 女[ジョ]</on>は<b><on> 由[ユイ]</on></b><on>"
            " 緒[ショ]</on>ある<kun> 家柄[いえがら]</kun>の<kun> 出[で]</kun>だ。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> かの[彼]</kun><on> ジョ[女]</on>は<b><on> ユイ[由]</on></b><on>"
            " ショ[緒]</on>ある<kun> いえがら[家柄]</kun>の<kun> で[出]</kun>だ。"
        ),
    )
    test(
        test_name="Should match the full reading match when there are multiple 2/",
        kanji="口",
        # Both ク (on) and くち (kun) are in the furigana but the correct match is くち
        sentence="口紅[くちべに]",
        expected_kana_only="<b>くち</b>べに",
        expected_furigana="<b> 口[くち]</b> 紅[べに]",
        expected_furikanji="<b> くち[口]</b> べに[紅]",
        expected_kana_only_with_tags_split="<b><kun>くち</kun></b><kun>べに</kun>",
        expected_furigana_with_tags_split="<b><kun> 口[くち]</kun></b><kun> 紅[べに]</kun>",
        expected_furikanji_with_tags_split="<b><kun> くち[口]</kun></b><kun> べに[紅]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>くち</kun></b><kun>べに</kun>",
        expected_furigana_with_tags_merged="<b><kun> 口[くち]</kun></b><kun> 紅[べに]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> くち[口]</kun></b><kun> べに[紅]</kun>",
    )
    test(
        test_name="small tsu 1/",
        kanji="剔",
        sentence="剔抉[てっけつ]",
        expected_kana_only="<b>テッ</b>ケツ",
        expected_furigana="<b> 剔[テッ]</b> 抉[ケツ]",
        expected_furikanji="<b> テッ[剔]</b> ケツ[抉]",
        expected_kana_only_with_tags_split="<b><on>テッ</on></b><on>ケツ</on>",
        expected_furigana_with_tags_split="<b><on> 剔[テッ]</on></b><on> 抉[ケツ]</on>",
        expected_furikanji_with_tags_split="<b><on> テッ[剔]</on></b><on> ケツ[抉]</on>",
        expected_kana_only_with_tags_merged="<b><on>テッ</on></b><on>ケツ</on>",
        expected_furigana_with_tags_merged="<b><on> 剔[テッ]</on></b><on> 抉[ケツ]</on>",
        expected_furikanji_with_tags_merged="<b><on> テッ[剔]</on></b><on> ケツ[抉]</on>",
    )
    test(
        test_name="small tsu 2/",
        kanji="一",
        sentence="一見[いっけん]",
        expected_kana_only="<b>イッ</b>ケン",
        expected_furigana="<b> 一[イッ]</b> 見[ケン]",
        expected_furikanji="<b> イッ[一]</b> ケン[見]",
        expected_kana_only_with_tags_split="<b><on>イッ</on></b><on>ケン</on>",
        expected_furigana_with_tags_split="<b><on> 一[イッ]</on></b><on> 見[ケン]</on>",
        expected_furikanji_with_tags_split="<b><on> イッ[一]</on></b><on> ケン[見]</on>",
        expected_kana_only_with_tags_merged="<b><on>イッ</on></b><on>ケン</on>",
        expected_furigana_with_tags_merged="<b><on> 一[イッ]</on></b><on> 見[ケン]</on>",
        expected_furikanji_with_tags_merged="<b><on> イッ[一]</on></b><on> ケン[見]</on>",
    )
    test(
        test_name="small tsu 3/",
        kanji="各",
        sentence="各国[かっこく]",
        expected_kana_only="<b>カッ</b>コク",
        expected_furigana="<b> 各[カッ]</b> 国[コク]",
        expected_furikanji="<b> カッ[各]</b> コク[国]",
        expected_kana_only_with_tags_split="<b><on>カッ</on></b><on>コク</on>",
        expected_furigana_with_tags_split="<b><on> 各[カッ]</on></b><on> 国[コク]</on>",
        expected_furikanji_with_tags_split="<b><on> カッ[各]</on></b><on> コク[国]</on>",
        expected_kana_only_with_tags_merged="<b><on>カッ</on></b><on>コク</on>",
        expected_furigana_with_tags_merged="<b><on> 各[カッ]</on></b><on> 国[コク]</on>",
        expected_furikanji_with_tags_merged="<b><on> カッ[各]</on></b><on> コク[国]</on>",
    )
    test(
        test_name="small tsu 4/",
        kanji="吉",
        sentence="吉兆[きっちょう]",
        expected_kana_only="<b>キッ</b>チョウ",
        expected_furigana="<b> 吉[キッ]</b> 兆[チョウ]",
        expected_furikanji="<b> キッ[吉]</b> チョウ[兆]",
        expected_kana_only_with_tags_split="<b><on>キッ</on></b><on>チョウ</on>",
        expected_furigana_with_tags_split="<b><on> 吉[キッ]</on></b><on> 兆[チョウ]</on>",
        expected_furikanji_with_tags_split="<b><on> キッ[吉]</on></b><on> チョウ[兆]</on>",
        expected_kana_only_with_tags_merged="<b><on>キッ</on></b><on>チョウ</on>",
        expected_furigana_with_tags_merged="<b><on> 吉[キッ]</on></b><on> 兆[チョウ]</on>",
        expected_furikanji_with_tags_merged="<b><on> キッ[吉]</on></b><on> チョウ[兆]</on>",
    )
    test(
        test_name="small tsu 5/",
        kanji="尻",
        # Should be considered a kunyomi match, it's the only instance of お->ぽ conversion
        # with small tsu
        sentence="尻尾[しっぽ]",
        expected_kana_only="<b>しっ</b>ぽ",
        expected_furigana="<b> 尻[しっ]</b> 尾[ぽ]",
        expected_furikanji="<b> しっ[尻]</b> ぽ[尾]",
        expected_kana_only_with_tags_split="<b><kun>しっ</kun></b><kun>ぽ</kun>",
        expected_furigana_with_tags_split="<b><kun> 尻[しっ]</kun></b><kun> 尾[ぽ]</kun>",
        expected_furikanji_with_tags_split="<b><kun> しっ[尻]</kun></b><kun> ぽ[尾]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>しっ</kun></b><kun>ぽ</kun>",
        expected_furigana_with_tags_merged="<b><kun> 尻[しっ]</kun></b><kun> 尾[ぽ]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> しっ[尻]</kun></b><kun> ぽ[尾]</kun>",
    )
    test(
        test_name="small tsu 6/",
        kanji="呆",
        sentence="呆気[あっけ]ない",
        expected_kana_only="<b>あっ</b>ケない",
        expected_furigana="<b> 呆[あっ]</b> 気[ケ]ない",
        expected_furikanji="<b> あっ[呆]</b> ケ[気]ない",
        expected_kana_only_with_tags_split="<b><kun>あっ</kun></b><on>ケ</on>ない",
        expected_furigana_with_tags_split="<b><kun> 呆[あっ]</kun></b><on> 気[ケ]</on>ない",
        expected_furikanji_with_tags_split="<b><kun> あっ[呆]</kun></b><on> ケ[気]</on>ない",
        expected_kana_only_with_tags_merged="<b><kun>あっ</kun></b><on>ケ</on>ない",
        expected_furigana_with_tags_merged="<b><kun> 呆[あっ]</kun></b><on> 気[ケ]</on>ない",
        expected_furikanji_with_tags_merged="<b><kun> あっ[呆]</kun></b><on> ケ[気]</on>ない",
    )
    test(
        test_name="small tsu 7/",
        kanji="甲",
        sentence="甲冑[かっちゅう]の 試着[しちゃく]をお 願[ねが]いします｡",
        expected_kana_only="<b>カッ</b>チュウの シチャクをお ねがいします｡",
        expected_furigana="<b> 甲[カッ]</b> 冑[チュウ]の 試着[シチャク]をお 願[ねが]いします｡",
        expected_furikanji="<b> カッ[甲]</b> チュウ[冑]の シチャク[試着]をお ねが[願]いします｡",
        expected_kana_only_with_tags_split=(
            "<b><on>カッ</on></b><on>チュウ</on>の"
            " <on>シ</on><on>チャク</on>をお <kun>ねが</kun><oku>い</oku>します｡"
        ),
        expected_furigana_with_tags_split=(
            "<b><on> 甲[カッ]</on></b><on> 冑[チュウ]</on>の<on> 試[シ]</on><on>"
            " 着[チャク]</on>をお<kun> 願[ねが]</kun><oku>い</oku>します｡"
        ),
        expected_furikanji_with_tags_split=(
            "<b><on> カッ[甲]</on></b><on> チュウ[冑]</on>の<on> シ[試]</on><on>"
            " チャク[着]</on>をお<kun> ねが[願]</kun><oku>い</oku>します｡"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><on>カッ</on></b><on>チュウ</on>の"
            " <on>シチャク</on>をお <kun>ねが</kun><oku>い</oku>します｡"
        ),
        expected_furigana_with_tags_merged=(
            "<b><on> 甲[カッ]</on></b><on> 冑[チュウ]</on>の<on> 試着[シチャク]</on>をお<kun>"
            " 願[ねが]</kun><oku>い</oku>します｡"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><on> カッ[甲]</on></b><on> チュウ[冑]</on>の<on> シチャク[試着]</on>をお<kun>"
            " ねが[願]</kun><oku>い</oku>します｡"
        ),
    )
    test(
        test_name="small tsu 8/",
        kanji="百",
        sentence="百貨店[ひゃっかてん]",
        expected_kana_only="<b>ヒャッ</b>カテン",
        expected_furigana="<b> 百[ヒャッ]</b> 貨店[カテン]",
        expected_furikanji="<b> ヒャッ[百]</b> カテン[貨店]",
        expected_kana_only_with_tags_split="<b><on>ヒャッ</on></b><on>カ</on><on>テン</on>",
        expected_furigana_with_tags_split="<b><on> 百[ヒャッ]</on></b><on> 貨[カ]</on><on> 店[テン]</on>",
        expected_furikanji_with_tags_split=(
            "<b><on> ヒャッ[百]</on></b><on> カ[貨]</on><on> テン[店]</on>"
        ),
        expected_kana_only_with_tags_merged="<b><on>ヒャッ</on></b><on>カテン</on>",
        expected_furigana_with_tags_merged="<b><on> 百[ヒャッ]</on></b><on> 貨店[カテン]</on>",
        expected_furikanji_with_tags_merged="<b><on> ヒャッ[百]</on></b><on> カテン[貨店]</on>",
    )
    test(
        test_name="small tsu 秘蔵っ子 with う dropped",
        kanji="蔵",
        sentence="秘蔵っ子[ひぞっこ]",
        expected_kana_only="ヒ<b>ゾ</b>っこ",
        expected_furigana=" 秘[ヒ]<b> 蔵[ゾ]</b>っ 子[こ]",
        expected_furikanji=" ヒ[秘]<b> ゾ[蔵]</b>っ こ[子]",
        expected_kana_only_with_tags_split="<on>ヒ</on><b><on>ゾ</on></b>っ<kun>こ</kun>",
        expected_furigana_with_tags_split="<on> 秘[ヒ]</on><b><on> 蔵[ゾ]</on></b>っ<kun> 子[こ]</kun>",
        expected_furikanji_with_tags_split=(
            "<on> ヒ[秘]</on><b><on> ゾ[蔵]</on></b>っ<kun> こ[子]</kun>"
        ),
        expected_kana_only_with_tags_merged="<on>ヒ</on><b><on>ゾ</on></b>っ<kun>こ</kun>",
        expected_furigana_with_tags_merged=(
            "<on> 秘[ヒ]</on><b><on> 蔵[ゾ]</on></b>っ<kun> 子[こ]</kun>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ヒ[秘]</on><b><on> ゾ[蔵]</on></b>っ<kun> こ[子]</kun>"
        ),
    )
    test(
        test_name="small tsu 秘蔵っ子 with う included",
        kanji="蔵",
        sentence="秘蔵っ子[ひぞうっこ]",
        expected_kana_only="ヒ<b>ゾウ</b>っこ",
        expected_furigana=" 秘[ヒ]<b> 蔵[ゾウ]</b>っ 子[こ]",
        expected_furikanji=" ヒ[秘]<b> ゾウ[蔵]</b>っ こ[子]",
        expected_kana_only_with_tags_split="<on>ヒ</on><b><on>ゾウ</on></b>っ<kun>こ</kun>",
        expected_furigana_with_tags_split=(
            "<on> 秘[ヒ]</on><b><on> 蔵[ゾウ]</on></b>っ<kun> 子[こ]</kun>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ヒ[秘]</on><b><on> ゾウ[蔵]</on></b>っ<kun> こ[子]</kun>"
        ),
        expected_kana_only_with_tags_merged="<on>ヒ</on><b><on>ゾウ</on></b>っ<kun>こ</kun>",
        expected_furigana_with_tags_merged=(
            "<on> 秘[ヒ]</on><b><on> 蔵[ゾウ]</on></b>っ<kun> 子[こ]</kun>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ヒ[秘]</on><b><on> ゾウ[蔵]</on></b>っ<kun> こ[子]</kun>"
        ),
    )
    test(
        test_name="small tsu 放[ほ]ったら with う dropped",
        kanji="放",
        sentence="放[ほ]ったらかす",
        expected_kana_only="<b>ほったら</b>かす",
        expected_furigana="<b> 放[ほ]ったら</b>かす",
        expected_furikanji="<b> ほ[放]ったら</b>かす",
        expected_kana_only_with_tags_split="<b><kun>ほ</kun><oku>ったら</oku></b>かす",
        expected_furigana_with_tags_split="<b><kun> 放[ほ]</kun><oku>ったら</oku></b>かす",
        expected_furikanji_with_tags_split="<b><kun> ほ[放]</kun><oku>ったら</oku></b>かす",
        expected_kana_only_with_tags_merged="<b><kun>ほ</kun><oku>ったら</oku></b>かす",
        expected_furigana_with_tags_merged="<b><kun> 放[ほ]</kun><oku>ったら</oku></b>かす",
        expected_furikanji_with_tags_merged="<b><kun> ほ[放]</kun><oku>ったら</oku></b>かす",
    )
    test(
        test_name="small tsu 放[ほ]ったら with う included",
        kanji="放",
        sentence="放[ほう]ったらかす",
        expected_kana_only="<b>ほうったら</b>かす",
        expected_furigana="<b> 放[ほう]ったら</b>かす",
        expected_furikanji="<b> ほう[放]ったら</b>かす",
        expected_kana_only_with_tags_split="<b><kun>ほう</kun><oku>ったら</oku></b>かす",
        expected_furigana_with_tags_split="<b><kun> 放[ほう]</kun><oku>ったら</oku></b>かす",
        expected_furikanji_with_tags_split="<b><kun> ほう[放]</kun><oku>ったら</oku></b>かす",
        expected_kana_only_with_tags_merged="<b><kun>ほう</kun><oku>ったら</oku></b>かす",
        expected_furigana_with_tags_merged="<b><kun> 放[ほう]</kun><oku>ったら</oku></b>かす",
        expected_furikanji_with_tags_merged="<b><kun> ほう[放]</kun><oku>ったら</oku></b>かす",
    )
    test(
        test_name="reading mixup /1",
        kanji="口",
        ignore_fail=True,
        # 口 kunyomi くち is found in the furigana but the correct match is the onyomi ク
        sentence="口調[くちょう]",
        expected_kana_only="<b>ク</b>チョウ",
        expected_kana_only_with_tags_split="<b><on>ク</on></b><on>チョウ</on>",
        expected_kana_only_with_tags_merged="<b><on>ク</on></b><on>チョウ</on>",
    )
    test(
        test_name="sound change readings 1/",
        kanji="青",
        # あお -> さお
        sentence="真[ま]っ青[さお]",
        expected_kana_only="まっ<b>さお</b>",
        expected_furigana=" 真[ま]っ<b> 青[さお]</b>",
        expected_furikanji=" ま[真]っ<b> さお[青]</b>",
        expected_kana_only_with_tags_split="<kun>ま</kun>っ<b><kun>さお</kun></b>",
        expected_furigana_with_tags_split="<kun> 真[ま]</kun>っ<b><kun> 青[さお]</kun></b>",
        expected_furikanji_with_tags_split="<kun> ま[真]</kun>っ<b><kun> さお[青]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>ま</kun>っ<b><kun>さお</kun></b>",
        expected_furigana_with_tags_merged="<kun> 真[ま]</kun>っ<b><kun> 青[さお]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> ま[真]</kun>っ<b><kun> さお[青]</kun></b>",
    )
    test(
        test_name="sound change readings 2/",
        kanji="赤",
        # あか -> か
        sentence="真っ赤[まっか]",
        expected_kana_only="まっ<b>か</b>",
        expected_furigana=" 真[ま]っ<b> 赤[か]</b>",
        expected_furikanji=" ま[真]っ<b> か[赤]</b>",
        expected_kana_only_with_tags_split="<kun>ま</kun>っ<b><kun>か</kun></b>",
        expected_furigana_with_tags_split="<kun> 真[ま]</kun>っ<b><kun> 赤[か]</kun></b>",
        expected_furikanji_with_tags_split="<kun> ま[真]</kun>っ<b><kun> か[赤]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>ま</kun>っ<b><kun>か</kun></b>",
        expected_furigana_with_tags_merged="<kun> 真[ま]</kun>っ<b><kun> 赤[か]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> ま[真]</kun>っ<b><kun> か[赤]</kun></b>",
    )
    test(
        test_name="sound change readings 3/",
        kanji="新",
        # あら -> さら
        sentence="真っ新[まっさら]",
        expected_kana_only="まっ<b>さら</b>",
        expected_furigana=" 真[ま]っ<b> 新[さら]</b>",
        expected_furikanji=" ま[真]っ<b> さら[新]</b>",
        expected_kana_only_with_tags_split="<kun>ま</kun>っ<b><kun>さら</kun></b>",
        expected_furigana_with_tags_split="<kun> 真[ま]</kun>っ<b><kun> 新[さら]</kun></b>",
        expected_furikanji_with_tags_split="<kun> ま[真]</kun>っ<b><kun> さら[新]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>ま</kun>っ<b><kun>さら</kun></b>",
        expected_furigana_with_tags_merged="<kun> 真[ま]</kun>っ<b><kun> 新[さら]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> ま[真]</kun>っ<b><kun> さら[新]</kun></b>",
    )
    test(
        test_name="sound change readings 4/",
        kanji="雨",
        # あめ -> さめ
        sentence="春雨[はるさめ]",
        expected_kana_only="はる<b>さめ</b>",
        expected_furigana=" 春[はる]<b> 雨[さめ]</b>",
        expected_furikanji=" はる[春]<b> さめ[雨]</b>",
        expected_kana_only_with_tags_split="<kun>はる</kun><b><kun>さめ</kun></b>",
        expected_furigana_with_tags_split="<kun> 春[はる]</kun><b><kun> 雨[さめ]</kun></b>",
        expected_furikanji_with_tags_split="<kun> はる[春]</kun><b><kun> さめ[雨]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>はる</kun><b><kun>さめ</kun></b>",
        expected_furigana_with_tags_merged="<kun> 春[はる]</kun><b><kun> 雨[さめ]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> はる[春]</kun><b><kun> さめ[雨]</kun></b>",
    )
    test(
        test_name="sound change readings 4/",
        kanji="雨",
        # あめ -> あま
        sentence="雨傘[あまがさ]",
        expected_kana_only="<b>あま</b>がさ",
        expected_furigana="<b> 雨[あま]</b> 傘[がさ]",
        expected_furikanji="<b> あま[雨]</b> がさ[傘]",
        expected_kana_only_with_tags_split="<b><kun>あま</kun></b><kun>がさ</kun>",
        expected_furigana_with_tags_split="<b><kun> 雨[あま]</kun></b><kun> 傘[がさ]</kun>",
        expected_furikanji_with_tags_split="<b><kun> あま[雨]</kun></b><kun> がさ[傘]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>あま</kun></b><kun>がさ</kun>",
        expected_furigana_with_tags_merged="<b><kun> 雨[あま]</kun></b><kun> 傘[がさ]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> あま[雨]</kun></b><kun> がさ[傘]</kun>",
    )
    test(
        test_name="sound change readings 5/",
        kanji="酒",
        # さけ -> さか
        sentence="居酒屋[いざかや]",
        expected_kana_only="い<b>ざか</b>や",
        expected_furigana=" 居[い]<b> 酒[ざか]</b> 屋[や]",
        expected_furikanji=" い[居]<b> ざか[酒]</b> や[屋]",
        expected_kana_only_with_tags_split="<kun>い</kun><b><kun>ざか</kun></b><kun>や</kun>",
        expected_furigana_with_tags_split=(
            "<kun> 居[い]</kun><b><kun> 酒[ざか]</kun></b><kun> 屋[や]</kun>"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> い[居]</kun><b><kun> ざか[酒]</kun></b><kun> や[屋]</kun>"
        ),
        expected_kana_only_with_tags_merged="<kun>い</kun><b><kun>ざか</kun></b><kun>や</kun>",
        expected_furigana_with_tags_merged=(
            "<kun> 居[い]</kun><b><kun> 酒[ざか]</kun></b><kun> 屋[や]</kun>"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> い[居]</kun><b><kun> ざか[酒]</kun></b><kun> や[屋]</kun>"
        ),
    )
    test(
        test_name="sound change readings 6/",
        kanji="応",
        # おう -> のう
        sentence="反応[はんのう]",
        expected_kana_only="ハン<b>ノウ</b>",
        expected_furigana=" 反[ハン]<b> 応[ノウ]</b>",
        expected_furikanji=" ハン[反]<b> ノウ[応]</b>",
        expected_kana_only_with_tags_split="<on>ハン</on><b><on>ノウ</on></b>",
        expected_furigana_with_tags_split="<on> 反[ハン]</on><b><on> 応[ノウ]</on></b>",
        expected_furikanji_with_tags_split="<on> ハン[反]</on><b><on> ノウ[応]</on></b>",
        expected_kana_only_with_tags_merged="<on>ハン</on><b><on>ノウ</on></b>",
        expected_furigana_with_tags_merged="<on> 反[ハン]</on><b><on> 応[ノウ]</on></b>",
        expected_furikanji_with_tags_merged="<on> ハン[反]</on><b><on> ノウ[応]</on></b>",
    )
    test(
        test_name="sound change readings 7/",
        kanji="皇",
        # おう -> のう
        sentence="天皇[てんのう]",
        expected_kana_only="テン<b>ノウ</b>",
        expected_furigana=" 天[テン]<b> 皇[ノウ]</b>",
        expected_furikanji=" テン[天]<b> ノウ[皇]</b>",
        expected_kana_only_with_tags_split="<on>テン</on><b><on>ノウ</on></b>",
        expected_furigana_with_tags_split="<on> 天[テン]</on><b><on> 皇[ノウ]</on></b>",
        expected_furikanji_with_tags_split="<on> テン[天]</on><b><on> ノウ[皇]</on></b>",
        expected_kana_only_with_tags_merged="<on>テン</on><b><on>ノウ</on></b>",
        expected_furigana_with_tags_merged="<on> 天[テン]</on><b><on> 皇[ノウ]</on></b>",
        expected_furikanji_with_tags_merged="<on> テン[天]</on><b><on> ノウ[皇]</on></b>",
    )
    test(
        test_name="sound dropped readings 1/",
        kanji="裸",
        # はだか -> はだ
        sentence="裸足[はだあし]",
        expected_kana_only="<b>はだ</b>あし",
        expected_furigana="<b> 裸[はだ]</b> 足[あし]",
        expected_furikanji="<b> はだ[裸]</b> あし[足]",
        expected_kana_only_with_tags_split="<b><kun>はだ</kun></b><kun>あし</kun>",
        expected_furigana_with_tags_split="<b><kun> 裸[はだ]</kun></b><kun> 足[あし]</kun>",
        expected_furikanji_with_tags_split="<b><kun> はだ[裸]</kun></b><kun> あし[足]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>はだ</kun></b><kun>あし</kun>",
        expected_furigana_with_tags_merged="<b><kun> 裸[はだ]</kun></b><kun> 足[あし]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> はだ[裸]</kun></b><kun> あし[足]</kun>",
    )
    test(
        test_name="sound dropped readings 2/",
        kanji="原",
        # はら -> は
        sentence="河原[かわら]",
        expected_kana_only="かわ<b>ら</b>",
        expected_furigana=" 河[かわ]<b> 原[ら]</b>",
        expected_furikanji=" かわ[河]<b> ら[原]</b>",
        expected_kana_only_with_tags_split="<kun>かわ</kun><b><kun>ら</kun></b>",
        expected_furigana_with_tags_split="<kun> 河[かわ]</kun><b><kun> 原[ら]</kun></b>",
        expected_furikanji_with_tags_split="<kun> かわ[河]</kun><b><kun> ら[原]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>かわ</kun><b><kun>ら</kun></b>",
        expected_furigana_with_tags_merged="<kun> 河[かわ]</kun><b><kun> 原[ら]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> かわ[河]</kun><b><kun> ら[原]</kun></b>",
    )
    test(
        test_name="sound fusion readings 1/",
        kanji="胡",
        # Likely by 黄[き] + 瓜[うり] forming 黄瓜[きゅうり] through sound fusion
        # 胡瓜 is read as きゅうり making 胡[きゅ] techinically jukujikun
        # However, since 瓜[うり] is a normal kunyomi reading, 黄瓜[きゅうり] can't be considered
        # jukujikun, thus we'll note 胡[きゅ] as a kunyomi
        sentence="胡瓜[きゅうり]",
        expected_kana_only="<b>きゅ</b>うり",
        expected_furigana="<b> 胡[きゅ]</b> 瓜[うり]",
        expected_furikanji="<b> きゅ[胡]</b> うり[瓜]",
        expected_kana_only_with_tags_split="<b><kun>きゅ</kun></b><kun>うり</kun>",
        expected_furigana_with_tags_split="<b><kun> 胡[きゅ]</kun></b><kun> 瓜[うり]</kun>",
        expected_furikanji_with_tags_split="<b><kun> きゅ[胡]</kun></b><kun> うり[瓜]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>きゅ</kun></b><kun>うり</kun>",
        expected_furigana_with_tags_merged="<b><kun> 胡[きゅ]</kun></b><kun> 瓜[うり]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> きゅ[胡]</kun></b><kun> うり[瓜]</kun>",
    )
    test(
        test_name="sound fusion readings 2/",
        kanji="狩",
        sentence="狩人[かりゅうど]",
        expected_kana_only="<b>かりゅ</b>うど",
        expected_furigana="<b> 狩[かりゅ]</b> 人[うど]",
        expected_furikanji="<b> かりゅ[狩]</b> うど[人]",
        expected_kana_only_with_tags_split="<b><kun>かりゅ</kun></b><kun>うど</kun>",
        expected_furigana_with_tags_split="<b><kun> 狩[かりゅ]</kun></b><kun> 人[うど]</kun>",
        expected_furikanji_with_tags_split="<b><kun> かりゅ[狩]</kun></b><kun> うど[人]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>かりゅ</kun></b><kun>うど</kun>",
        expected_furigana_with_tags_merged="<b><kun> 狩[かりゅ]</kun></b><kun> 人[うど]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> かりゅ[狩]</kun></b><kun> うど[人]</kun>",
    )
    test(
        test_name="Single kana reading conversion 1/",
        # 祖 usually only lists ソ as the only onyomi
        kanji="祖",
        sentence="先祖[せんぞ]",
        expected_kana_only="セン<b>ゾ</b>",
        expected_furigana=" 先[セン]<b> 祖[ゾ]</b>",
        expected_furikanji=" セン[先]<b> ゾ[祖]</b>",
        expected_kana_only_with_tags_split="<on>セン</on><b><on>ゾ</on></b>",
        expected_furigana_with_tags_split="<on> 先[セン]</on><b><on> 祖[ゾ]</on></b>",
        expected_furikanji_with_tags_split="<on> セン[先]</on><b><on> ゾ[祖]</on></b>",
        expected_kana_only_with_tags_merged="<on>セン</on><b><on>ゾ</on></b>",
        expected_furigana_with_tags_merged="<on> 先[セン]</on><b><on> 祖[ゾ]</on></b>",
        expected_furikanji_with_tags_merged="<on> セン[先]</on><b><on> ゾ[祖]</on></b>",
    )
    test(
        test_name="Single kana reading conversion 2/",
        kanji="来",
        sentence="それは 私[わたし]たちの 日常生活[にちじょうせいかつ]の 仕来[しき]たりの １[ひと]つだ。",
        expected_kana_only="それは わたしたちの ニチジョウセイカツの シ<b>きたり</b>の ひとつだ。",
        expected_furigana=(
            "それは 私[わたし]たちの 日常生活[ニチジョウセイカツ]の 仕[シ]<b>"
            " 来[き]たり</b>の １[ひと]つだ。"
        ),
        expected_furikanji=(
            "それは わたし[私]たちの ニチジョウセイカツ[日常生活]の シ[仕]<b>"
            " き[来]たり</b>の ひと[１]つだ。"
        ),
        expected_kana_only_with_tags_split=(
            "それは <kun>わたし</kun>たちの <on>ニチ</on><on>ジョウ</on><on>セイ</on><on>カツ</on>の "
            "<on>シ</on><b><kun>き</kun><oku>たり</oku></b>の <kun>ひと</kun><oku>つ</oku>だ。"
        ),
        expected_furigana_with_tags_split=(
            "それは<kun> 私[わたし]</kun>たちの<on> 日[ニチ]</on><on> 常[ジョウ]</on><on>"
            " 生[セイ]</on>"
            "<on> 活[カツ]</on>の<on> 仕[シ]</on><b><kun> 来[き]</kun><oku>たり</oku></b>の<kun>"
            " １[ひと]</kun>"
            "<oku>つ</oku>だ。"
        ),
        expected_furikanji_with_tags_split=(
            "それは<kun> わたし[私]</kun>たちの<on> ニチ[日]</on><on> ジョウ[常]</on><on>"
            " セイ[生]</on>"
            "<on> カツ[活]</on>の<on> シ[仕]</on><b><kun> き[来]</kun><oku>たり</oku></b>の<kun>"
            " ひと[１]</kun>"
            "<oku>つ</oku>だ。"
        ),
        expected_kana_only_with_tags_merged=(
            "それは <kun>わたし</kun>たちの <on>ニチジョウセイカツ</on>の"
            " <on>シ</on><b><kun>き</kun><oku>たり</oku></b>の "
            "<kun>ひと</kun><oku>つ</oku>だ。"
        ),
        expected_furigana_with_tags_merged=(
            "それは<kun> 私[わたし]</kun>たちの<on> 日常生活[ニチジョウセイカツ]</on>の"
            "<on> 仕[シ]</on><b><kun> 来[き]</kun><oku>たり</oku></b>の<kun> １[ひと]</kun>"
            "<oku>つ</oku>だ。"
        ),
        expected_furikanji_with_tags_merged=(
            "それは<kun> わたし[私]</kun>たちの<on> ニチジョウセイカツ[日常生活]</on>の"
            "<on> シ[仕]</on><b><kun> き[来]</kun><oku>たり</oku></b>の<kun> ひと[１]</kun>"
            "<oku>つ</oku>だ。"
        ),
    )
    test(
        test_name="word where shorter reading is incorrect 1/",
        # 不 has two matching onyomi フ and フウ where the shorter is correct for 不運
        ignore_fail=True,
        kanji="不",
        sentence="不運[ふうん]",
        expected_kana_only="<b>ふ</b>うん",
        expected_kana_only_with_tags_split="<b><on>ふ</on></b><on>うん</on>",
        expected_kana_only_with_tags_merged="<b><on>ふ</on></b><on>うん</on>",
    )
    test(
        test_name="jukujikun test 大人 1/",
        kanji="大",
        sentence="大人[おとな] 達[たち]は 大[おお]きいですね",
        expected_kana_only="<b>おと</b>な タチは <b>おおきい</b>ですね",
        expected_furigana="<b> 大[おと]</b> 人[な] 達[タチ]は<b> 大[おお]きい</b>ですね",
        expected_furikanji="<b> おと[大]</b> な[人] タチ[達]は<b> おお[大]きい</b>ですね",
        expected_kana_only_with_tags_split=(
            "<b><juk>おと</juk></b><juk>な</juk> <on>タチ</on>は"
            " <b><kun>おお</kun><oku>きい</oku></b>ですね"
        ),
        expected_furigana_with_tags_split=(
            "<b><juk> 大[おと]</juk></b><juk> 人[な]</juk><on> 達[タチ]</on>は<b><kun>"
            " 大[おお]</kun><oku>きい</oku></b>ですね"
        ),
        expected_furikanji_with_tags_split=(
            "<b><juk> おと[大]</juk></b><juk> な[人]</juk><on> タチ[達]</on>は<b><kun>"
            " おお[大]</kun><oku>きい</oku></b>ですね"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><juk>おと</juk></b><juk>な</juk> <on>タチ</on>は"
            " <b><kun>おお</kun><oku>きい</oku></b>ですね"
        ),
        expected_furigana_with_tags_merged=(
            "<b><juk> 大[おと]</juk></b><juk> 人[な]</juk><on> 達[タチ]</on>は<b><kun>"
            " 大[おお]</kun><oku>きい</oku></b>ですね"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><juk> おと[大]</juk></b><juk> な[人]</juk><on> タチ[達]</on>は<b><kun>"
            " おお[大]</kun><oku>きい</oku></b>ですね"
        ),
    )
    test(
        test_name="jukujikun test 大人 2/",
        kanji="人",
        sentence="大人[おとな] 達[たち]は 人々[ひとびと]の 中[なか]に いる。",
        expected_kana_only="おと<b>な</b> タチは <b>ひとびと</b>の なかに いる。",
        expected_furigana=" 大[おと]<b> 人[な]</b> 達[タチ]は<b> 人々[ひとびと]</b>の 中[なか]に いる。",
        expected_furikanji=" おと[大]<b> な[人]</b> タチ[達]は<b> ひとびと[人々]</b>の なか[中]に いる。",
        expected_kana_only_with_tags_split=(
            "<juk>おと</juk><b><juk>な</juk></b> <on>タチ</on>は <b><kun>ひとびと</kun></b>の"
            " <kun>なか</kun>に いる。"
        ),
        expected_furigana_with_tags_split=(
            "<juk> 大[おと]</juk><b><juk> 人[な]</juk></b><on> 達[タチ]</on>は<b><kun>"
            " 人々[ひとびと]</kun></b>"
            "の<kun> 中[なか]</kun>に いる。"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> おと[大]</juk><b><juk> な[人]</juk></b><on> タチ[達]</on>は<b><kun>"
            " ひとびと[人々]</kun></b>"
            "の<kun> なか[中]</kun>に いる。"
        ),
        expected_kana_only_with_tags_merged=(
            "<juk>おと</juk><b><juk>な</juk></b> <on>タチ</on>は <b><kun>ひとびと</kun></b>の"
            " <kun>なか</kun>に いる。"
        ),
        expected_furigana_with_tags_merged=(
            "<juk> 大[おと]</juk><b><juk> 人[な]</juk></b><on> 達[タチ]</on>は<b><kun>"
            " 人々[ひとびと]</kun></b>"
            "の<kun> 中[なか]</kun>に いる。"
        ),
        expected_furikanji_with_tags_merged=(
            "<juk> おと[大]</juk><b><juk> な[人]</juk></b><on> タチ[達]</on>は<b><kun>"
            " ひとびと[人々]</kun></b>"
            "の<kun> なか[中]</kun>に いる。"
        ),
    )
    test(
        test_name="jukujikun test 昨日",
        kanji="展",
        sentence="昨日[きのう]、 絵[え]の 展覧[てんらん] 会[かい]に 行[い]ってきました。",
        expected_kana_only="きのう、 エの <b>テン</b>ラン カイに いってきました。",
        expected_furigana=" 昨日[きのう]、 絵[エ]の<b> 展[テン]</b> 覧[ラン] 会[カイ]に 行[い]ってきました。",
        expected_furikanji=" きのう[昨日]、 エ[絵]の<b> テン[展]</b> ラン[覧] カイ[会]に い[行]ってきました。",
        expected_kana_only_with_tags_split=(
            "<juk>きの</juk><juk>う</juk>、 <on>エ</on>の <b><on>テン</on></b><on>ラン</on>"
            " <on>カイ</on>に <kun>い</kun><oku>って</oku>きました。"
        ),
        expected_furigana_with_tags_split=(
            "<juk> 昨[きの]</juk><juk> 日[う]</juk>、<on> 絵[エ]</on>の<b><on> 展[テン]</on></b>"
            "<on> 覧[ラン]</on><on> 会[カイ]</on>に<kun> 行[い]</kun><oku>って</oku>きました。"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> きの[昨]</juk><juk> う[日]</juk>、<on> エ[絵]</on>の<b><on> テン[展]</on></b>"
            "<on> ラン[覧]</on><on> カイ[会]</on>に<kun> い[行]</kun><oku>って</oku>きました。"
        ),
        expected_kana_only_with_tags_merged=(
            "<juk>きのう</juk>、 <on>エ</on>の <b><on>テン</on></b><on>ラン</on>"
            " <on>カイ</on>に <kun>い</kun><oku>って</oku>きました。"
        ),
        expected_furigana_with_tags_merged=(
            "<juk> 昨日[きのう]</juk>、<on> 絵[エ]</on>の<b><on> 展[テン]</on></b>"
            "<on> 覧[ラン]</on><on> 会[カイ]</on>に<kun> 行[い]</kun><oku>って</oku>きました。"
        ),
        expected_furikanji_with_tags_merged=(
            "<juk> きのう[昨日]</juk>、<on> エ[絵]</on>の<b><on> テン[展]</on></b>"
            "<on> ラン[覧]</on><on> カイ[会]</on>に<kun> い[行]</kun><oku>って</oku>きました。"
        ),
    )
    test(
        test_name="jukujikun test with repeater 明々後日",
        kanji="明",
        sentence="明々後日[しあさって]",
        expected_kana_only="<b>しあ</b>さって",
        expected_furigana="<b> 明々[しあ]</b> 後日[さって]",
        expected_furikanji="<b> しあ[明々]</b> さって[後日]",
        expected_kana_only_with_tags_split="<b><juk>しあ</juk></b><juk>さっ</juk><juk>て</juk>",
        expected_furigana_with_tags_split=(
            "<b><juk> 明々[しあ]</juk></b><juk> 後[さっ]</juk><juk> 日[て]</juk>"
        ),
        expected_furikanji_with_tags_split=(
            "<b><juk> しあ[明々]</juk></b><juk> さっ[後]</juk><juk> て[日]</juk>"
        ),
        expected_kana_only_with_tags_merged="<b><juk>しあ</juk></b><juk>さって</juk>",
        expected_furigana_with_tags_merged="<b><juk> 明々[しあ]</juk></b><juk> 後日[さって]</juk>",
        expected_furikanji_with_tags_merged="<b><juk> しあ[明々]</juk></b><juk> さって[後日]</juk>",
    )
    test(
        test_name="jukujikun test 明後日",
        kanji="後",
        # Problem with あ.かり getting kunyomi match on 明, so the reading is not fully
        # correctly identified as jukujikun
        sentence="明後日[あさって]",
        expected_kana_only="あ<b>さっ</b>て",
        expected_furigana=" 明[あ]<b> 後[さっ]</b> 日[て]",
        expected_furikanji=" あ[明]<b> さっ[後]</b> て[日]",
        expected_kana_only_with_tags_split="<kun>あ</kun><b><juk>さっ</juk></b><juk>て</juk>",
        expected_furigana_with_tags_split=(
            "<kun> 明[あ]</kun><b><juk> 後[さっ]</juk></b><juk> 日[て]</juk>"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> あ[明]</kun><b><juk> さっ[後]</juk></b><juk> て[日]</juk>"
        ),
        expected_kana_only_with_tags_merged="<kun>あ</kun><b><juk>さっ</juk></b><juk>て</juk>",
        expected_furigana_with_tags_merged=(
            "<kun> 明[あ]</kun><b><juk> 後[さっ]</juk></b><juk> 日[て]</juk>"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> あ[明]</kun><b><juk> さっ[後]</juk></b><juk> て[日]</juk>"
        ),
    )
    test(
        test_name="jukujikun test 清々しい no highlight",
        kanji="",
        sentence=" 清清[すがすが]しい",
        expected_kana_only=" すがすがしい",
        expected_furigana=" 清々[すがすが]しい",
        expected_furikanji=" すがすが[清々]しい",
        expected_kana_only_with_tags_split=" <juk>すがすが</juk>しい",
        expected_furigana_with_tags_split="<juk> 清々[すがすが]</juk>しい",
        expected_furikanji_with_tags_split="<juk> すがすが[清々]</juk>しい",
        expected_kana_only_with_tags_merged=" <juk>すがすが</juk>しい",
        expected_furigana_with_tags_merged="<juk> 清々[すがすが]</juk>しい",
        expected_furikanji_with_tags_merged="<juk> すがすが[清々]</juk>しい",
    )
    test(
        test_name="jukujikun test 清々しい with highlight",
        kanji="清",
        sentence="清清[すがすが]しい",
        expected_kana_only="<b>すがすが</b>しい",
        expected_furigana="<b> 清々[すがすが]</b>しい",
        expected_furikanji="<b> すがすが[清々]</b>しい",
        expected_kana_only_with_tags_split="<b><juk>すがすが</juk></b>しい",
        expected_furigana_with_tags_split="<b><juk> 清々[すがすが]</juk></b>しい",
        expected_furikanji_with_tags_split="<b><juk> すがすが[清々]</juk></b>しい",
        expected_kana_only_with_tags_merged="<b><juk>すがすが</juk></b>しい",
        expected_furigana_with_tags_merged="<b><juk> 清々[すがすが]</juk></b>しい",
        expected_furikanji_with_tags_merged="<b><juk> すがすが[清々]</juk></b>しい",
    )
    test(
        test_name="jukujikun test 清々しい with another word at left - no highlight",
        kanji="",
        sentence="趙清々[ちょうすがすが]しい",
        expected_kana_only="チョウすがすがしい",
        expected_furigana=" 趙清々[チョウすがすが]しい",
        expected_furikanji=" チョウすがすが[趙清々]しい",
        expected_kana_only_with_tags_split="<on>チョウ</on><juk>すがすが</juk>しい",
        expected_furigana_with_tags_split="<on> 趙[チョウ]</on><juk> 清々[すがすが]</juk>しい",
        expected_furikanji_with_tags_split="<on> チョウ[趙]</on><juk> すがすが[清々]</juk>しい",
        expected_kana_only_with_tags_merged="<on>チョウ</on><juk>すがすが</juk>しい",
        expected_furigana_with_tags_merged="<on> 趙[チョウ]</on><juk> 清々[すがすが]</juk>しい",
        expected_furikanji_with_tags_merged="<on> チョウ[趙]</on><juk> すがすが[清々]</juk>しい",
    )
    test(
        test_name="jukujikun test 清々しい with another word at left - with highlight",
        kanji="清",
        sentence="趙清々[ちょうすがすが]しい",
        expected_kana_only="チョウ<b>すがすが</b>しい",
        expected_furigana=" 趙[チョウ]<b> 清々[すがすが]</b>しい",
        expected_furikanji=" チョウ[趙]<b> すがすが[清々]</b>しい",
        expected_kana_only_with_tags_split="<on>チョウ</on><b><juk>すがすが</juk></b>しい",
        expected_furigana_with_tags_split="<on> 趙[チョウ]</on><b><juk> 清々[すがすが]</juk></b>しい",
        expected_furikanji_with_tags_split="<on> チョウ[趙]</on><b><juk> すがすが[清々]</juk></b>しい",
        expected_kana_only_with_tags_merged="<on>チョウ</on><b><juk>すがすが</juk></b>しい",
        expected_furigana_with_tags_merged="<on> 趙[チョウ]</on><b><juk> 清々[すがすが]</juk></b>しい",
        expected_furikanji_with_tags_merged="<on> チョウ[趙]</on><b><juk> すがすが[清々]</juk></b>しい",
    )
    test(
        test_name="jukujikun test 清々しい in middle of two words - no highlight",
        kanji="",
        sentence="趙清々瑞々[ちょうすがすがみずみず]しい",
        expected_kana_only="チョウすがすがみずみずしい",
        expected_furigana=" 趙清々瑞々[チョウすがすがみずみず]しい",
        expected_furikanji=" チョウすがすがみずみず[趙清々瑞々]しい",
        expected_kana_only_with_tags_split=(
            "<on>チョウ</on><juk>すがすが</juk><kun>みずみず</kun><oku>しい</oku>"
        ),
        expected_furigana_with_tags_split=(
            "<on> 趙[チョウ]</on><juk> 清々[すがすが]</juk><kun> 瑞々[みずみず]</kun><oku>しい</oku>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> チョウ[趙]</on><juk> すがすが[清々]</juk><kun> みずみず[瑞々]</kun><oku>しい</oku>"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>チョウ</on><juk>すがすが</juk><kun>みずみず</kun><oku>しい</oku>"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 趙[チョウ]</on><juk> 清々[すがすが]</juk><kun> 瑞々[みずみず]</kun><oku>しい</oku>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> チョウ[趙]</on><juk> すがすが[清々]</juk><kun> みずみず[瑞々]</kun><oku>しい</oku>"
        ),
    )
    test(
        test_name="jukujikun test 清々しい in middle of two words - with highlight",
        kanji="清",
        sentence="趙清々瑞々[ちょうすがすがみずみず]しい",
        expected_kana_only="チョウ<b>すがすが</b>みずみずしい",
        expected_furigana=" 趙[チョウ]<b> 清々[すがすが]</b> 瑞々[みずみず]しい",
        expected_furikanji=" チョウ[趙]<b> すがすが[清々]</b> みずみず[瑞々]しい",
        expected_kana_only_with_tags_split=(
            "<on>チョウ</on><b><juk>すがすが</juk></b><kun>みずみず</kun><oku>しい</oku>"
        ),
        expected_furigana_with_tags_split=(
            "<on> 趙[チョウ]</on><b><juk> 清々[すがすが]</juk></b><kun>"
            " 瑞々[みずみず]</kun><oku>しい</oku>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> チョウ[趙]</on><b><juk> すがすが[清々]</juk></b><kun>"
            " みずみず[瑞々]</kun><oku>しい</oku>"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>チョウ</on><b><juk>すがすが</juk></b><kun>みずみず</kun><oku>しい</oku>"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 趙[チョウ]</on><b><juk> 清々[すがすが]</juk></b><kun>"
            " 瑞々[みずみず]</kun><oku>しい</oku>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> チョウ[趙]</on><b><juk> すがすが[清々]</juk></b><kun>"
            " みずみず[瑞々]</kun><oku>しい</oku>"
        ),
    )
    test(
        test_name="jukujikun test ん ending",
        kanji="魁",
        sentence="花魁[おいらん]",
        expected_kana_only="おい<b>らん</b>",
        expected_kana_only_with_tags_split="<juk>おい</juk><b><juk>らん</juk></b>",
        expected_kana_only_with_tags_merged="<juk>おい</juk><b><juk>らん</juk></b>",
    )
    test(
        test_name="single-kanji juku in middle of word",
        kanji="気",
        sentence="意気地[いくじ]",
        expected_kana_only="イ<b>く</b>ジ",
        expected_kana_only_with_tags_split="<on>イ</on><b><juk>く</juk></b><on>ジ</on>",
        expected_kana_only_with_tags_merged="<on>イ</on><b><juk>く</juk></b><on>ジ</on>",
    )
    test(
        test_name="multi-kanji juku in middle of word matched left",
        kanji="百",
        # Made up word, are there any multi-kanji jukujikun words used like this?
        sentence="赤百合花壇[あかゆりかだん]",
        expected_kana_only="あか<b>ゆ</b>りカダン",
        expected_kana_only_with_tags_split=(
            "<kun>あか</kun><b><juk>ゆ</juk></b><juk>り</juk><on>カ</on><on>ダン</on>"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>あか</kun><b><juk>ゆ</juk></b><juk>り</juk><on>カダン</on>"
        ),
    )
    test(
        test_name="multi-kanji juku in middle of word matched right",
        kanji="合",
        sentence="赤百合花壇[あかゆりかだん]",
        expected_kana_only="あかゆ<b>り</b>カダン",
        expected_kana_only_with_tags_split=(
            "<kun>あか</kun><juk>ゆ</juk><b><juk>り</juk></b><on>カ</on><on>ダン</on>"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>あか</kun><juk>ゆ</juk><b><juk>り</juk></b><on>カダン</on>"
        ),
    )
    test(
        ignore_fail=True,
        test_name="jukujikun test 蕎麦 not matched",
        kanji="屋",
        sentence="蕎麦屋[そばや]",
        expected_kana_only="そば<b>や</b>",
        expected_kana_only_with_tags_split="<juk>そ</juk><juk>ば</juk><b><kun>や</kun></b>",
        expected_kana_only_with_tags_merged="<juk>そば</juk><b><kun>や</kun></b>",
    )
    test(
        test_name="jukujikun test 風邪 matched",
        kanji="風",
        # 風 has the kunyomi かぜ, but 風邪 should be read as the jukujikun かぜ
        sentence="風邪[かぜ]",
        expected_kana_only="<b>か</b>ぜ",
        expected_furigana="<b> 風[か]</b> 邪[ぜ]",
        expected_furikanji="<b> か[風]</b> ぜ[邪]",
        expected_kana_only_with_tags_split="<b><juk>か</juk></b><juk>ぜ</juk>",
        expected_furigana_with_tags_split="<b><juk> 風[か]</juk></b><juk> 邪[ぜ]</juk>",
        expected_furikanji_with_tags_split="<b><juk> か[風]</juk></b><juk> ぜ[邪]</juk>",
    )
    test(
        test_name="jukujikun test 風邪 not matched",
        kanji="引",
        # When not matched, jukujikun are automatically merged together
        # This is done intentionally in match_tags_with_kanji.py, so could be changed
        # Kind of makes sense you can't really choose which kanji matches with
        # which part of the furigana
        sentence="風邪[かぜ]を引[ひ]いた。",
        expected_kana_only="かぜを<b>ひいた</b>。",
        expected_furigana=" 風邪[かぜ]を<b> 引[ひ]いた</b>。",
        expected_furikanji=" かぜ[風邪]を<b> ひ[引]いた</b>。",
        expected_kana_only_with_tags_split=(
            "<juk>か</juk><juk>ぜ</juk>を<b><kun>ひ</kun><oku>いた</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<juk> 風[か]</juk><juk> 邪[ぜ]</juk>を<b><kun> 引[ひ]</kun><oku>いた</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> か[風]</juk><juk> ぜ[邪]</juk>を<b><kun> ひ[引]</kun><oku>いた</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<juk>かぜ</juk>を<b><kun>ひ</kun><oku>いた</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<juk> 風邪[かぜ]</juk>を<b><kun> 引[ひ]</kun><oku>いた</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<juk> かぜ[風邪]</juk>を<b><kun> ひ[引]</kun><oku>いた</oku></b>。"
        ),
    )
    test(
        test_name="jukujikun test with other readings after juku word /1",
        kanji="買",
        sentence="風邪薬[かぜぐすり]を買[か]った",
        expected_kana_only="かぜぐすりを<b>かった</b>",
        expected_furigana=" 風邪薬[かぜぐすり]を<b> 買[か]った</b>",
        expected_furikanji=" かぜぐすり[風邪薬]を<b> か[買]った</b>",
        expected_kana_only_with_tags_split=(
            "<juk>か</juk><juk>ぜ</juk><kun>ぐすり</kun>を<b><kun>か</kun><oku>った</oku></b>"
        ),
        expected_furigana_with_tags_split=(
            "<juk> 風[か]</juk><juk> 邪[ぜ]</juk><kun> 薬[ぐすり]</kun>を<b><kun>"
            " 買[か]</kun><oku>った</oku></b>"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> か[風]</juk><juk> ぜ[邪]</juk><kun> ぐすり[薬]</kun>を<b><kun>"
            " か[買]</kun><oku>った</oku></b>"
        ),
        expected_kana_only_with_tags_merged=(
            "<juk>かぜ</juk><kun>ぐすり</kun>を<b><kun>か</kun><oku>った</oku></b>"
        ),
        expected_furigana_with_tags_merged=(
            "<juk> 風邪[かぜ]</juk><kun> 薬[ぐすり]</kun>を<b><kun> 買[か]</kun><oku>った</oku></b>"
        ),
        expected_furikanji_with_tags_merged=(
            "<juk> かぜ[風邪]</juk><kun> ぐすり[薬]</kun>を<b><kun> か[買]</kun><oku>った</oku></b>"
        ),
    )
    test(
        test_name="jukujikun test with other readings after juku word /2",
        kanji="色",
        sentence="薔薇色[ばらいろ]",
        expected_kana_only="ばら<b>いろ</b>",
        expected_furigana=" 薔薇[ばら]<b> 色[いろ]</b>",
        expected_furikanji=" ばら[薔薇]<b> いろ[色]</b>",
        expected_kana_only_with_tags_split="<juk>ば</juk><juk>ら</juk><b><kun>いろ</kun></b>",
        expected_furigana_with_tags_split=(
            "<juk> 薔[ば]</juk><juk> 薇[ら]</juk><b><kun> 色[いろ]</kun></b>"
        ),
        expected_furikanji_with_tags_split=(
            "<juk> ば[薔]</juk><juk> ら[薇]</juk><b><kun> いろ[色]</kun></b>"
        ),
        expected_kana_only_with_tags_merged="<juk>ばら</juk><b><kun>いろ</kun></b>",
        expected_furigana_with_tags_merged="<juk> 薔薇[ばら]</juk><b><kun> 色[いろ]</kun></b>",
        expected_furikanji_with_tags_merged="<juk> ばら[薔薇]</juk><b><kun> いろ[色]</kun></b>",
    )
    test(
        test_name="multi-kanji jukujikun word with other readings after juku word non-matched",
        kanji="目",
        sentence="真面目[まじめ]",
        expected_kana_only="まじ<b>め</b>",
        expected_kana_only_with_tags_split="<juk>ま</juk><juk>じ</juk><b><kun>め</kun></b>",
        expected_kana_only_with_tags_merged="<juk>まじ</juk><b><kun>め</kun></b>",
    )
    test(
        test_name="multi-kanji jukujikun word with other readings after juku word matched left ",
        kanji="真",
        sentence="真面目[まじめ]",
        expected_kana_only="<b>ま</b>じめ",
        expected_kana_only_with_tags_split="<b><juk>ま</juk></b><juk>じ</juk><kun>め</kun>",
        expected_kana_only_with_tags_merged="<b><juk>ま</juk></b><juk>じ</juk><kun>め</kun>",
    )
    test(
        test_name="multi-kanji jukujikun word with other readings after juku word matched right",
        kanji="面",
        sentence="真面目[まじめ]",
        expected_kana_only="ま<b>じ</b>め",
        expected_kana_only_with_tags_split="<juk>ま</juk><b><juk>じ</juk></b><kun>め</kun>",
        expected_kana_only_with_tags_merged="<juk>ま</juk><b><juk>じ</juk></b><kun>め</kun>",
    )
    test(
        test_name="multi-kanji jukujikun verb reading matched left",
        kanji="揶",
        sentence="揶揄[からか]う",
        expected_kana_only="<b>から</b>かう",
        expected_kana_only_with_tags_split="<b><juk>から</juk></b><juk>か</juk>う",
        expected_kana_only_with_tags_merged="<b><juk>から</juk></b><juk>か</juk>う",
    )
    test(
        test_name="multi-kanji jukujikun verb reading matched right",
        kanji="揄",
        sentence="揶揄[からか]う",
        expected_kana_only="から<b>か</b>う",
        expected_kana_only_with_tags_split="<juk>から</juk><b><juk>か</juk></b>う",
        expected_kana_only_with_tags_merged="<juk>から</juk><b><juk>か</juk></b>う",
    )
    test(
        test_name="Should be able to handle vowel change /1",
        kanji="端",
        sentence="端折[はしょ]る",
        expected_kana_only="<b>はし</b>ょる",
        expected_kana_only_with_tags_split="<b><kun>はし</kun></b><kun>ょ</kun><oku>る</oku>",
        expected_kana_only_with_tags_merged="<b><kun>はし</kun></b><kun>ょ</kun><oku>る</oku>",
        expected_furigana="<b> 端[はし]</b> 折[ょ]る",
        expected_furigana_with_tags_split="<b><kun> 端[はし]</kun></b><kun> 折[ょ]</kun><oku>る</oku>",
        expected_furigana_with_tags_merged="<b><kun> 端[はし]</kun></b><kun> 折[ょ]</kun><oku>る</oku>",
        expected_furikanji="<b> はし[端]</b> ょ[折]る",
        expected_furikanji_with_tags_split="<b><kun> はし[端]</kun></b><kun> ょ[折]</kun><oku>る</oku>",
        expected_furikanji_with_tags_merged="<b><kun> はし[端]</kun></b><kun> ょ[折]</kun><oku>る</oku>",
    )
    test(
        test_name="Should be able to get dictionary form okurigana of jukujikun reading",
        kanji="逆",
        # No kunyomi to match, the okurigana would need to be analyzed to get the dictionary form
        # and then determine where the okurigana ends
        sentence="逆上[のぼ]せる",
        # Only dictionary forms can be handled for now
        assume_dictionary_form=True,
        expected_kana_only="<b>の</b>ぼせる",
        expected_furigana="<b> 逆[の]</b> 上[ぼ]せる",
        expected_furikanji="<b> の[逆]</b> ぼ[上]せる",
        expected_kana_only_with_tags_split="<b><juk>の</juk></b><juk>ぼ</juk><oku>せる</oku>",
        expected_furigana_with_tags_split="<b><juk> 逆[の]</juk></b><juk> 上[ぼ]</juk><oku>せる</oku>",
        expected_furikanji_with_tags_split="<b><juk> の[逆]</juk></b><juk> ぼ[上]</juk><oku>せる</oku>",
        expected_kana_only_with_tags_merged="<b><juk>の</juk></b><juk>ぼ</juk><oku>せる</oku>",
        expected_furigana_with_tags_merged="<b><juk> 逆[の]</juk></b><juk> 上[ぼ]</juk><oku>せる</oku>",
        expected_furikanji_with_tags_merged="<b><juk> の[逆]</juk></b><juk> ぼ[上]</juk><oku>せる</oku>",
    )
    test(
        test_name="Should be able to get inflected okurigana of jukujikun reading",
        kanji="逆",
        sentence="逆上[のぼ]せたので",
        # Trying to get the okurigana of the inflected form from jukujikun is too hard
        # for now, ignore
        ignore_fail=True,
        expected_kana_only="<b>の</b>せたので",
        expected_furigana="<b> 逆[の]</b> 上[ぼ]せたので",
        expected_furikanji="<b> の[逆]</b> ぼ[上]せたので",
        expected_kana_only_with_tags_split="<b><juk>の</juk></b><juk>ぼ</juk><oku>せた</oku>ので",
        expected_furigana_with_tags_split=(
            "<b><juk> 逆[の]</juk></b><juk> 上[ぼ]</juk><oku>せた</oku>ので"
        ),
        expected_furikanji_with_tags_split=(
            "<b><juk> の[逆]</juk></b><juk> ぼ[上]</juk><oku>せた</oku>ので"
        ),
        expected_kana_only_with_tags_merged="<b><juk>の</juk></b><juk>ぼせた</juk>ので",
        expected_furigana_with_tags_merged=(
            "<b><juk> 逆[の]</juk></b><juk> 上[ぼ]</juk><oku>せた</oku>ので"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><juk> の[逆]</juk></b><juk> ぼ[上]</juk><oku>せた</oku>ので"
        ),
    )
    test(
        test_name="ん should be combined with previous mora in jukujikun",
        kanji="麻",
        sentence="麻雀[まーじゃん]",
        expected_kana_only="<b>まー</b>じゃん",
        expected_kana_only_with_tags_split="<b><juk>まー</juk></b><juk>じゃん</juk>",
        expected_kana_only_with_tags_merged="<b><juk>まー</juk></b><juk>じゃん</juk>",
    )
    test(
        test_name="Should be able match noun form okuriganaless kunyomi reading 1/",
        kanji="曳",
        # ひ.く is a kunyomi for 曳 and both 曳き舟 and 曳船 are valid readings
        sentence="曳船[ひきふね]",
        expected_kana_only="<b>ひき</b>ふね",
        expected_furigana="<b> 曳[ひき]</b> 船[ふね]",
        expected_furikanji="<b> ひき[曳]</b> ふね[船]",
        expected_kana_only_with_tags_split="<b><kun>ひき</kun></b><kun>ふね</kun>",
        expected_furigana_with_tags_split="<b><kun> 曳[ひき]</kun></b><kun> 船[ふね]</kun>",
        expected_furikanji_with_tags_split="<b><kun> ひき[曳]</kun></b><kun> ふね[船]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>ひき</kun></b><kun>ふね</kun>",
        expected_furigana_with_tags_merged="<b><kun> 曳[ひき]</kun></b><kun> 船[ふね]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> ひき[曳]</kun></b><kun> ふね[船]</kun>",
    )
    test(
        test_name="Should be able match noun form okuriganaless kunyomi reading 2/",
        kanji="留",
        sentence="書留[かきとめ]",
        expected_kana_only="かき<b>とめ</b>",
        expected_furigana=" 書[かき]<b> 留[とめ]</b>",
        expected_furikanji=" かき[書]<b> とめ[留]</b>",
        expected_kana_only_with_tags_split="<kun>かき</kun><b><kun>とめ</kun></b>",
        expected_furigana_with_tags_split="<kun> 書[かき]</kun><b><kun> 留[とめ]</kun></b>",
        expected_furikanji_with_tags_split="<kun> かき[書]</kun><b><kun> とめ[留]</kun></b>",
        expected_kana_only_with_tags_merged="<kun>かき</kun><b><kun>とめ</kun></b>",
        expected_furigana_with_tags_merged="<kun> 書[かき]</kun><b><kun> 留[とめ]</kun></b>",
        expected_furikanji_with_tags_merged="<kun> かき[書]</kun><b><kun> とめ[留]</kun></b>",
    )
    test(
        test_name="Should be able match noun form okuriganaless kunyomi reading 3/",
        kanji="詣",
        sentence="初詣[はつもうで]",
        expected_kana_only="はつ<b>もうで</b>",
        expected_kana_only_with_tags_split="<kun>はつ</kun><b><kun>もうで</kun></b>",
        expected_kana_only_with_tags_merged="<kun>はつ</kun><b><kun>もうで</kun></b>",
    )
    test(
        test_name="Should be able to get okurigana of kunyomi reading 1/",
        kanji="置",
        sentence=" 風上[かざかみ]にも 置[お]けない",
        expected_kana_only=" かざかみにも <b>おけない</b>",
        expected_furigana=" 風上[かざかみ]にも<b> 置[お]けない</b>",
        expected_furikanji=" かざかみ[風上]にも<b> お[置]けない</b>",
        expected_kana_only_with_tags_split=(
            " <kun>かざ</kun><kun>かみ</kun>にも <b><kun>お</kun><oku>けない</oku></b>"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 風[かざ]</kun><kun> 上[かみ]</kun>にも<b><kun> 置[お]</kun><oku>けない</oku></b>"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> かざ[風]</kun><kun> かみ[上]</kun>にも<b><kun> お[置]</kun><oku>けない</oku></b>"
        ),
        expected_kana_only_with_tags_merged=(
            " <kun>かざかみ</kun>にも <b><kun>お</kun><oku>けない</oku></b>"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 風上[かざかみ]</kun>にも<b><kun> 置[お]</kun><oku>けない</oku></b>"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> かざかみ[風上]</kun>にも<b><kun> お[置]</kun><oku>けない</oku></b>"
        ),
    )
    test(
        test_name="Verb okurigana test 1/",
        kanji="来",
        sentence="今[いま]に 来[きた]るべし",
        expected_kana_only="いまに <b>きたる</b>べし",
        expected_furigana=" 今[いま]に<b> 来[きた]る</b>べし",
        expected_furikanji=" いま[今]に<b> きた[来]る</b>べし",
        expected_kana_only_with_tags_split="<kun>いま</kun>に <b><kun>きた</kun><oku>る</oku></b>べし",
        expected_furigana_with_tags_split=(
            "<kun> 今[いま]</kun>に<b><kun> 来[きた]</kun><oku>る</oku></b>べし"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> いま[今]</kun>に<b><kun> きた[来]</kun><oku>る</oku></b>べし"
        ),
        expected_kana_only_with_tags_merged="<kun>いま</kun>に <b><kun>きた</kun><oku>る</oku></b>べし",
        expected_furigana_with_tags_merged=(
            "<kun> 今[いま]</kun>に<b><kun> 来[きた]</kun><oku>る</oku></b>べし"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> いま[今]</kun>に<b><kun> きた[来]</kun><oku>る</oku></b>べし"
        ),
    )
    test(
        test_name="Verb okurigana test 2/",
        kanji="書",
        sentence="日記[にっき]を 書[か]いた。",
        expected_kana_only="ニッキを <b>かいた</b>。",
        expected_furigana=" 日記[ニッキ]を<b> 書[か]いた</b>。",
        expected_furikanji=" ニッキ[日記]を<b> か[書]いた</b>。",
        expected_kana_only_with_tags_split=(
            "<on>ニッ</on><on>キ</on>を <b><kun>か</kun><oku>いた</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 日[ニッ]</on><on> 記[キ]</on>を<b><kun> 書[か]</kun><oku>いた</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ニッ[日]</on><on> キ[記]</on>を<b><kun> か[書]</kun><oku>いた</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<on>ニッキ</on>を <b><kun>か</kun><oku>いた</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<on> 日記[ニッキ]</on>を<b><kun> 書[か]</kun><oku>いた</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ニッキ[日記]</on>を<b><kun> か[書]</kun><oku>いた</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 3/",
        kanji="話",
        sentence="友達[ともだち]と 話[はな]している。",
        expected_kana_only="ともダチと <b>はなして</b>いる。",
        expected_furigana=" 友達[ともダチ]と<b> 話[はな]して</b>いる。",
        expected_furikanji=" ともダチ[友達]と<b> はな[話]して</b>いる。",
        expected_kana_only_with_tags_split=(
            "<kun>とも</kun><on>ダチ</on>と <b><kun>はな</kun><oku>して</oku></b>いる。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 友[とも]</kun><on> 達[ダチ]</on>と<b><kun> 話[はな]</kun><oku>して</oku></b>いる。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> とも[友]</kun><on> ダチ[達]</on>と<b><kun> はな[話]</kun><oku>して</oku></b>いる。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>とも</kun><on>ダチ</on>と <b><kun>はな</kun><oku>して</oku></b>いる。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 友[とも]</kun><on> 達[ダチ]</on>と<b><kun> 話[はな]</kun><oku>して</oku></b>いる。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> とも[友]</kun><on> ダチ[達]</on>と<b><kun> はな[話]</kun><oku>して</oku></b>いる。"
        ),
    )
    test(
        test_name="Verb okurigana test 4/",
        kanji="聞",
        sentence="ニュースを 聞[き]きました。",
        expected_kana_only="ニュースを <b>ききました</b>。",
        expected_furigana="ニュースを<b> 聞[き]きました</b>。",
        expected_furikanji="ニュースを<b> き[聞]きました</b>。",
        expected_kana_only_with_tags_split="ニュースを <b><kun>き</kun><oku>きました</oku></b>。",
        expected_furigana_with_tags_split="ニュースを<b><kun> 聞[き]</kun><oku>きました</oku></b>。",
        expected_furikanji_with_tags_split="ニュースを<b><kun> き[聞]</kun><oku>きました</oku></b>。",
        expected_kana_only_with_tags_merged="ニュースを <b><kun>き</kun><oku>きました</oku></b>。",
        expected_furigana_with_tags_merged="ニュースを<b><kun> 聞[き]</kun><oku>きました</oku></b>。",
        expected_furikanji_with_tags_merged="ニュースを<b><kun> き[聞]</kun><oku>きました</oku></b>。",
    )
    test(
        test_name="Verb okurigana test 5/",
        kanji="走",
        sentence="公園[こうえん]で 走[はし]ろう。",
        expected_kana_only="コウエンで <b>はしろう</b>。",
        expected_furigana=" 公園[コウエン]で<b> 走[はし]ろう</b>。",
        expected_furikanji=" コウエン[公園]で<b> はし[走]ろう</b>。",
        expected_kana_only_with_tags_split=(
            "<on>コウ</on><on>エン</on>で <b><kun>はし</kun><oku>ろう</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 公[コウ]</on><on> 園[エン]</on>で<b><kun> 走[はし]</kun><oku>ろう</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> コウ[公]</on><on> エン[園]</on>で<b><kun> はし[走]</kun><oku>ろう</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<on>コウエン</on>で <b><kun>はし</kun><oku>ろう</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<on> 公園[コウエン]</on>で<b><kun> 走[はし]</kun><oku>ろう</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> コウエン[公園]</on>で<b><kun> はし[走]</kun><oku>ろう</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 6/",
        kanji="待",
        sentence="友達[ともだち]を 待[ま]つ。",
        expected_kana_only="ともダチを <b>まつ</b>。",
        expected_furigana=" 友達[ともダチ]を<b> 待[ま]つ</b>。",
        expected_furikanji=" ともダチ[友達]を<b> ま[待]つ</b>。",
        expected_kana_only_with_tags_split=(
            "<kun>とも</kun><on>ダチ</on>を <b><kun>ま</kun><oku>つ</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 友[とも]</kun><on> 達[ダチ]</on>を<b><kun> 待[ま]</kun><oku>つ</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> とも[友]</kun><on> ダチ[達]</on>を<b><kun> ま[待]</kun><oku>つ</oku></b>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>とも</kun><on>ダチ</on>を <b><kun>ま</kun><oku>つ</oku></b>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 友[とも]</kun><on> 達[ダチ]</on>を<b><kun> 待[ま]</kun><oku>つ</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> とも[友]</kun><on> ダチ[達]</on>を<b><kun> ま[待]</kun><oku>つ</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 7/",
        kanji="泳",
        sentence="海[うみ]で 泳[およ]ぐ。",
        expected_kana_only="うみで <b>およぐ</b>。",
        expected_furigana=" 海[うみ]で<b> 泳[およ]ぐ</b>。",
        expected_furikanji=" うみ[海]で<b> およ[泳]ぐ</b>。",
        expected_kana_only_with_tags_split="<kun>うみ</kun>で <b><kun>およ</kun><oku>ぐ</oku></b>。",
        expected_furigana_with_tags_split=(
            "<kun> 海[うみ]</kun>で<b><kun> 泳[およ]</kun><oku>ぐ</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> うみ[海]</kun>で<b><kun> およ[泳]</kun><oku>ぐ</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<kun>うみ</kun>で <b><kun>およ</kun><oku>ぐ</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<kun> 海[うみ]</kun>で<b><kun> 泳[およ]</kun><oku>ぐ</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> うみ[海]</kun>で<b><kun> およ[泳]</kun><oku>ぐ</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 8/",
        kanji="作",
        sentence="料理[りょうり]を 作[つく]る。",
        expected_kana_only="リョウリを <b>つくる</b>。",
        expected_furigana=" 料理[リョウリ]を<b> 作[つく]る</b>。",
        expected_furikanji=" リョウリ[料理]を<b> つく[作]る</b>。",
        expected_kana_only_with_tags_split=(
            "<on>リョウ</on><on>リ</on>を <b><kun>つく</kun><oku>る</oku></b>。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 料[リョウ]</on><on> 理[リ]</on>を<b><kun> 作[つく]</kun><oku>る</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> リョウ[料]</on><on> リ[理]</on>を<b><kun> つく[作]</kun><oku>る</oku></b>。"
        ),
        expected_kana_only_with_tags_merged="<on>リョウリ</on>を <b><kun>つく</kun><oku>る</oku></b>。",
        expected_furigana_with_tags_merged=(
            "<on> 料理[リョウリ]</on>を<b><kun> 作[つく]</kun><oku>る</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> リョウリ[料理]</on>を<b><kun> つく[作]</kun><oku>る</oku></b>。"
        ),
    )
    test(
        test_name="Verb okurigana test 9/",
        kanji="遊",
        sentence="子供[こども]と 遊[あそ]んでいるぞ。",
        expected_kana_only="こどもと <b>あそんで</b>いるぞ。",
        expected_furigana=" 子供[こども]と<b> 遊[あそ]んで</b>いるぞ。",
        expected_furikanji=" こども[子供]と<b> あそ[遊]んで</b>いるぞ。",
        expected_kana_only_with_tags_split=(
            "<kun>こ</kun><kun>ども</kun>と <b><kun>あそ</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 子[こ]</kun><kun> 供[ども]</kun>と<b><kun> 遊[あそ]</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> こ[子]</kun><kun> ども[供]</kun>と<b><kun> あそ[遊]</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>こども</kun>と <b><kun>あそ</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 子供[こども]</kun>と<b><kun> 遊[あそ]</kun><oku>んで</oku></b>いるぞ。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> こども[子供]</kun>と<b><kun> あそ[遊]</kun><oku>んで</oku></b>いるぞ。"
        ),
    )
    test(
        test_name="Verb okurigana test 10/",
        kanji="聞",
        # Both 聞く and 聞こえる will produce an okuri match but the correct should be 聞こえる
        sentence="音[おと]を 聞[き]こえたか？何[なに]も 聞[き]いていないよ",
        expected_kana_only="おとを <b>きこえた</b>か？なにも <b>きいて</b>いないよ",
        expected_furigana=" 音[おと]を<b> 聞[き]こえた</b>か？ 何[なに]も<b> 聞[き]いて</b>いないよ",
        expected_furikanji=" おと[音]を<b> き[聞]こえた</b>か？ なに[何]も<b> き[聞]いて</b>いないよ",
        expected_kana_only_with_tags_split=(
            "<kun>おと</kun>を <b><kun>き</kun><oku>こえた</oku></b>か？<kun>なに</kun>も"
            " <b><kun>き</kun><oku>いて</oku></b>いないよ"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 音[おと]</kun>を<b><kun> 聞[き]</kun><oku>こえた</oku></b>か？<kun>"
            " 何[なに]</kun>も"
            "<b><kun> 聞[き]</kun><oku>いて</oku></b>いないよ"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> おと[音]</kun>を<b><kun> き[聞]</kun><oku>こえた</oku></b>か？<kun>"
            " なに[何]</kun>も"
            "<b><kun> き[聞]</kun><oku>いて</oku></b>いないよ"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>おと</kun>を <b><kun>き</kun><oku>こえた</oku></b>か？<kun>なに</kun>も"
            " <b><kun>き</kun><oku>いて</oku></b>いないよ"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 音[おと]</kun>を<b><kun> 聞[き]</kun><oku>こえた</oku></b>か？<kun>"
            " 何[なに]</kun>も"
            "<b><kun> 聞[き]</kun><oku>いて</oku></b>いないよ"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> おと[音]</kun>を<b><kun> き[聞]</kun><oku>こえた</oku></b>か？<kun>"
            " なに[何]</kun>も"
            "<b><kun> き[聞]</kun><oku>いて</oku></b>いないよ"
        ),
    )
    test(
        test_name="Verb okurigana test 11/",
        kanji="抑",
        sentence="俳句[はいく]は 言葉[ことば]が 最小限[さいしょうげん]に 抑[おさ]えられている。",
        expected_kana_only="ハイクは ことばが サイショウゲンに <b>おさえられて</b>いる。",
        expected_furigana=(
            " 俳句[ハイク]は 言葉[ことば]が 最小限[サイショウゲン]に<b> 抑[おさ]えられて</b>いる。"
        ),
        expected_furikanji=(
            " ハイク[俳句]は ことば[言葉]が サイショウゲン[最小限]に<b> おさ[抑]えられて</b>いる。"
        ),
        expected_kana_only_with_tags_split=(
            "<on>ハイ</on><on>ク</on>は <kun>こと</kun><kun>ば</kun>が <on>サイ</on><on>ショウ</on>"
            "<on>ゲン</on>に <b><kun>おさ</kun><oku>えられて</oku></b>いる。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 俳[ハイ]</on><on> 句[ク]</on>は<kun> 言[こと]</kun><kun> 葉[ば]</kun>が<on>"
            " 最[サイ]</on><on>"
            " 小[ショウ]</on><on> 限[ゲン]</on>に<b><kun> 抑[おさ]</kun><oku>えられて</oku></b>いる。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ハイ[俳]</on><on> ク[句]</on>は<kun> こと[言]</kun><kun> ば[葉]</kun>が<on>"
            " サイ[最]</on><on>"
            " ショウ[小]</on><on> ゲン[限]</on>に<b><kun> おさ[抑]</kun><oku>えられて</oku></b>いる。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>ハイク</on>は <kun>ことば</kun>が <on>サイショウゲン</on>に"
            " <b><kun>おさ</kun><oku>えられて</oku></b>いる。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 俳句[ハイク]</on>は<kun> 言葉[ことば]</kun>が<on> 最小限[サイショウゲン]</on>に"
            "<b><kun> 抑[おさ]</kun><oku>えられて</oku></b>いる。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ハイク[俳句]</on>は<kun> ことば[言葉]</kun>が<on> サイショウゲン[最小限]</on>に"
            "<b><kun> おさ[抑]</kun><oku>えられて</oku></b>いる。"
        ),
    )
    test(
        test_name="Verb okurigana test 12/",
        kanji="染",
        sentence="幼馴染[おさななじ]みと 久[ひさ]しぶりに 会[あ]った。",
        expected_kana_only="おさなな<b>じみ</b>と ひさしぶりに あった。",
        expected_furigana=" 幼馴[おさなな]<b> 染[じ]み</b>と 久[ひさ]しぶりに 会[あ]った。",
        expected_furikanji=" おさなな[幼馴]<b> じ[染]み</b>と ひさ[久]しぶりに あ[会]った。",
        expected_kana_only_with_tags_split=(
            "<kun>おさな</kun><kun>な</kun><b><kun>じ</kun><oku>み</oku></b>と"
            " <kun>ひさ</kun><oku>し</oku>ぶりに <kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 幼[おさな]</kun><kun> 馴[な]</kun><b><kun> 染[じ]</kun><oku>み</oku></b>と<kun>"
            " 久[ひさ]</kun><oku>し</oku>ぶりに<kun> 会[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> おさな[幼]</kun><kun> な[馴]</kun><b><kun> じ[染]</kun><oku>み</oku></b>と<kun>"
            " ひさ[久]</kun><oku>し</oku>ぶりに<kun> あ[会]</kun><oku>った</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>おさなな</kun><b><kun>じ</kun><oku>み</oku></b>と <kun>ひさ</kun><oku>し</oku>ぶりに"
            " <kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 幼馴[おさなな]</kun><b><kun> 染[じ]</kun><oku>み</oku></b>と<kun>"
            " 久[ひさ]</kun><oku>し</oku>ぶりに<kun> 会[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> おさなな[幼馴]</kun><b><kun> じ[染]</kun><oku>み</oku></b>と<kun>"
            " ひさ[久]</kun><oku>し</oku>ぶりに<kun> あ[会]</kun><oku>った</oku>。"
        ),
    )
    test(
        test_name="Verb okurigana is gotten correctly when assuming dictionary form/",
        kanji="試",
        assume_dictionary_form=True,
        sentence="試[こころ]みる",
        expected_kana_only="<b>こころみる</b>",
        expected_furigana="<b> 試[こころ]みる</b>",
        expected_furikanji="<b> こころ[試]みる</b>",
        expected_kana_only_with_tags_split="<b><kun>こころ</kun><oku>みる</oku></b>",
        expected_furigana_with_tags_split="<b><kun> 試[こころ]</kun><oku>みる</oku></b>",
        expected_furikanji_with_tags_split="<b><kun> こころ[試]</kun><oku>みる</oku></b>",
    )
    test(
        test_name="Adjective okurigana test 1/",
        kanji="悲",
        sentence="彼[かれ]は 悲[かな]しくすぎるので、 悲[かな]しみの 悲[かな]しさを 悲[かな]しんでいる。",
        expected_kana_only=(
            "かれは <b>かなしく</b>すぎるので、 <b>かなしみ</b>の <b>かなしさ</b>を"
            " <b>かなしんで</b>いる。"
        ),
        expected_furigana=(
            " 彼[かれ]は<b> 悲[かな]しく</b>すぎるので、<b> 悲[かな]しみ</b>の<b>"
            " 悲[かな]しさ</b>を<b> 悲[かな]しんで</b>いる。"
        ),
        expected_furikanji=(
            " かれ[彼]は<b> かな[悲]しく</b>すぎるので、<b> かな[悲]しみ</b>の<b>"
            " かな[悲]しさ</b>を<b> かな[悲]しんで</b>いる。"
        ),
        expected_kana_only_with_tags_split=(
            "<kun>かれ</kun>は <b><kun>かな</kun><oku>しく</oku></b>すぎるので、"
            " <b><kun>かな</kun><oku>しみ</oku></b>の <b><kun>かな</kun><oku>しさ</oku></b>を"
            " <b><kun>かな</kun><oku>しんで</oku></b>いる。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 彼[かれ]</kun>は<b><kun> 悲[かな]</kun><oku>しく</oku></b>すぎるので、<b><kun>"
            " 悲[かな]</kun><oku>しみ</oku></b>の<b><kun> 悲[かな]</kun><oku>しさ</oku></b>を"
            "<b><kun> 悲[かな]</kun><oku>しんで</oku></b>いる。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> かれ[彼]</kun>は<b><kun> かな[悲]</kun><oku>しく</oku></b>すぎるので、<b><kun>"
            " かな[悲]</kun><oku>しみ</oku></b>の<b><kun> かな[悲]</kun><oku>しさ</oku></b>を"
            "<b><kun> かな[悲]</kun><oku>しんで</oku></b>いる。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>かれ</kun>は <b><kun>かな</kun><oku>しく</oku></b>すぎるので、"
            " <b><kun>かな</kun><oku>しみ</oku></b>の <b><kun>かな</kun><oku>しさ</oku></b>を"
            " <b><kun>かな</kun><oku>しんで</oku></b>いる。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 彼[かれ]</kun>は<b><kun> 悲[かな]</kun><oku>しく</oku></b>すぎるので、<b><kun>"
            " 悲[かな]</kun><oku>しみ</oku></b>の<b><kun> 悲[かな]</kun><oku>しさ</oku></b>を"
            "<b><kun> 悲[かな]</kun><oku>しんで</oku></b>いる。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> かれ[彼]</kun>は<b><kun> かな[悲]</kun><oku>しく</oku></b>すぎるので、<b><kun>"
            " かな[悲]</kun><oku>しみ</oku></b>の<b><kun> かな[悲]</kun><oku>しさ</oku></b>を"
            "<b><kun> かな[悲]</kun><oku>しんで</oku></b>いる。"
        ),
    )
    test(
        test_name="Adjective okurigana test 2/",
        kanji="青",
        sentence="空[そら]が 青[あお]かったら、 青[あお]くない 海[うみ]に 行[い]こう",
        expected_kana_only="そらが <b>あおかったら</b>、 <b>あおくない</b> うみに いこう",
        expected_furigana=" 空[そら]が<b> 青[あお]かったら</b>、<b> 青[あお]くない</b> 海[うみ]に 行[い]こう",
        expected_furikanji=" そら[空]が<b> あお[青]かったら</b>、<b> あお[青]くない</b> うみ[海]に い[行]こう",
        expected_kana_only_with_tags_split=(
            "<kun>そら</kun>が <b><kun>あお</kun><oku>かったら</oku></b>、"
            " <b><kun>あお</kun><oku>くない</oku></b> <kun>うみ</kun>に <kun>い</kun><oku>こう</oku>"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 空[そら]</kun>が<b><kun> 青[あお]</kun><oku>かったら</oku></b>、<b><kun>"
            " 青[あお]</kun><oku>くない</oku></b><kun> 海[うみ]</kun>に<kun>"
            " 行[い]</kun><oku>こう</oku>"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> そら[空]</kun>が<b><kun> あお[青]</kun><oku>かったら</oku></b>、<b><kun>"
            " あお[青]</kun><oku>くない</oku></b><kun> うみ[海]</kun>に<kun>"
            " い[行]</kun><oku>こう</oku>"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>そら</kun>が <b><kun>あお</kun><oku>かったら</oku></b>、"
            " <b><kun>あお</kun><oku>くない</oku></b> <kun>うみ</kun>に <kun>い</kun><oku>こう</oku>"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 空[そら]</kun>が<b><kun> 青[あお]</kun><oku>かったら</oku></b>、<b><kun>"
            " 青[あお]</kun><oku>くない</oku></b><kun> 海[うみ]</kun>に<kun>"
            " 行[い]</kun><oku>こう</oku>"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> そら[空]</kun>が<b><kun> あお[青]</kun><oku>かったら</oku></b>、<b><kun>"
            " あお[青]</kun><oku>くない</oku></b><kun> うみ[海]</kun>に<kun>"
            " い[行]</kun><oku>こう</oku>"
        ),
    )
    test(
        test_name="Adjective okurigana test 3/",
        kanji="高",
        sentence="山[やま]が 高[たか]ければ、 高層[こうそう]ビルが 高[たか]めてと 高[たか]ぶり",
        expected_kana_only=(
            "やまが <b>たかければ</b>、 <b>コウ</b>ソウビルが <b>たかめて</b>と <b>たかぶり</b>"
        ),
        expected_furigana=(
            " 山[やま]が<b> 高[たか]ければ</b>、<b> 高[コウ]</b> 層[ソウ]ビルが<b>"
            " 高[たか]めて</b>と<b> 高[たか]ぶり</b>"
        ),
        expected_furikanji=(
            " やま[山]が<b> たか[高]ければ</b>、<b> コウ[高]</b> ソウ[層]ビルが<b>"
            " たか[高]めて</b>と<b> たか[高]ぶり</b>"
        ),
        expected_kana_only_with_tags_split=(
            "<kun>やま</kun>が <b><kun>たか</kun><oku>ければ</oku></b>、"
            " <b><on>コウ</on></b><on>ソウ</on>ビルが <b><kun>たか</kun><oku>めて</oku></b>と"
            " <b><kun>たか</kun><oku>ぶり</oku></b>"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 山[やま]</kun>が<b><kun> 高[たか]</kun><oku>ければ</oku></b>、"
            "<b><on> 高[コウ]</on></b><on> 層[ソウ]</on>ビルが<b><kun>"
            " 高[たか]</kun><oku>めて</oku></b>と"
            "<b><kun> 高[たか]</kun><oku>ぶり</oku></b>"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> やま[山]</kun>が<b><kun> たか[高]</kun><oku>ければ</oku></b>、"
            "<b><on> コウ[高]</on></b><on> ソウ[層]</on>ビルが<b><kun>"
            " たか[高]</kun><oku>めて</oku></b>と"
            "<b><kun> たか[高]</kun><oku>ぶり</oku></b>"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>やま</kun>が <b><kun>たか</kun><oku>ければ</oku></b>、"
            " <b><on>コウ</on></b><on>ソウ</on>ビルが <b><kun>たか</kun><oku>めて</oku></b>と"
            " <b><kun>たか</kun><oku>ぶり</oku></b>"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 山[やま]</kun>が<b><kun> 高[たか]</kun><oku>ければ</oku></b>、"
            "<b><on> 高[コウ]</on></b><on> 層[ソウ]</on>ビルが<b><kun>"
            " 高[たか]</kun><oku>めて</oku></b>と"
            "<b><kun> 高[たか]</kun><oku>ぶり</oku></b>"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> やま[山]</kun>が<b><kun> たか[高]</kun><oku>ければ</oku></b>、"
            "<b><on> コウ[高]</on></b><on> ソウ[層]</on>ビルが<b><kun>"
            " たか[高]</kun><oku>めて</oku></b>と"
            "<b><kun> たか[高]</kun><oku>ぶり</oku></b>"
        ),
    )
    test(
        test_name="Adjective okurigana test 4/",
        kanji="厚",
        sentence="彼[かれ]は 厚かましい[あつかましい]。",
        expected_kana_only="かれは <b>あつかましい</b>。",
        expected_furigana=" 彼[かれ]は<b> 厚[あつ]かましい</b>。",
        expected_furikanji=" かれ[彼]は<b> あつ[厚]かましい</b>。",
        expected_kana_only_with_tags_split="<kun>かれ</kun>は <b><kun>あつ</kun><oku>かましい</oku></b>。",
        expected_furigana_with_tags_split=(
            "<kun> 彼[かれ]</kun>は<b><kun> 厚[あつ]</kun><oku>かましい</oku></b>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> かれ[彼]</kun>は<b><kun> あつ[厚]</kun><oku>かましい</oku></b>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>かれ</kun>は <b><kun>あつ</kun><oku>かましい</oku></b>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 彼[かれ]</kun>は<b><kun> 厚[あつ]</kun><oku>かましい</oku></b>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> かれ[彼]</kun>は<b><kun> あつ[厚]</kun><oku>かましい</oku></b>。"
        ),
    )
    test(
        test_name="Adjective okurigana test 5/",
        kanji="恥",
        sentence="恥[は]ずかしげな 顔[かお]で 恥[はじ]を 知[し]らない 振[ふ]りで 恥[は]じらってください。",
        expected_kana_only="<b>はずかし</b>げな かおで <b>はじ</b>を しらない ふりで <b>はじらって</b>ください。",
        expected_furigana=(
            "<b> 恥[は]ずかし</b>げな 顔[かお]で<b> 恥[はじ]</b>を 知[し]らない"
            " 振[ふ]りで<b> 恥[は]じらって</b>ください。"
        ),
        expected_furikanji=(
            "<b> は[恥]ずかし</b>げな かお[顔]で<b> はじ[恥]</b>を し[知]らない"
            " ふ[振]りで<b> は[恥]じらって</b>ください。"
        ),
        expected_kana_only_with_tags_split=(
            "<b><kun>は</kun><oku>ずかし</oku></b>げな <kun>かお</kun>で"
            " <b><kun>はじ</kun></b>を <kun>し</kun><oku>らない</oku>"
            " <kun>ふ</kun><oku>り</oku>で <b><kun>は</kun><oku>じらって</oku></b>ください。"
        ),
        expected_furigana_with_tags_split=(
            "<b><kun> 恥[は]</kun><oku>ずかし</oku></b>げな<kun> 顔[かお]</kun>で<b><kun>"
            " 恥[はじ]</kun></b>を<kun> 知[し]</kun><oku>らない</oku><kun>"
            " 振[ふ]</kun><oku>り</oku>で<b><kun> 恥[は]</kun><oku>じらって</oku></b>ください。"
        ),
        expected_furikanji_with_tags_split=(
            "<b><kun> は[恥]</kun><oku>ずかし</oku></b>げな<kun> かお[顔]</kun>で<b><kun>"
            " はじ[恥]</kun></b>を<kun> し[知]</kun><oku>らない</oku><kun>"
            " ふ[振]</kun><oku>り</oku>で<b><kun> は[恥]</kun><oku>じらって</oku></b>"
            "ください。"
        ),
        expected_kana_only_with_tags_merged=(
            "<b><kun>は</kun><oku>ずかし</oku></b>げな <kun>かお</kun>で"
            " <b><kun>はじ</kun></b>を <kun>し</kun><oku>らない</oku>"
            " <kun>ふ</kun><oku>り</oku>で <b><kun>は</kun><oku>じらって</oku></b>ください。"
        ),
        expected_furigana_with_tags_merged=(
            "<b><kun> 恥[は]</kun><oku>ずかし</oku></b>げな<kun> 顔[かお]</kun>で<b><kun>"
            " 恥[はじ]</kun></b>を<kun> 知[し]</kun><oku>らない</oku><kun>"
            " 振[ふ]</kun><oku>り</oku>で<b><kun> 恥[は]</kun><oku>じらって</oku></b>ください。"
        ),
        expected_furikanji_with_tags_merged=(
            "<b><kun> は[恥]</kun><oku>ずかし</oku></b>げな<kun> かお[顔]</kun>で<b><kun>"
            " はじ[恥]</kun></b>を<kun> し[知]</kun><oku>らない</oku><kun>"
            " ふ[振]</kun><oku>り</oku>で<b><kun> は[恥]</kun><oku>じらって</oku></b>ください。"
        ),
    )
    test(
        test_name="numbers of people /1",
        kanji="一",
        sentence="一人[ひとり]",
        expected_kana_only="<b>ひと</b>り",
        expected_furigana="<b> 一[ひと]</b> 人[り]",
        expected_furikanji="<b> ひと[一]</b> り[人]",
        expected_kana_only_with_tags_split="<b><kun>ひと</kun></b><kun>り</kun>",
        expected_furigana_with_tags_split="<b><kun> 一[ひと]</kun></b><kun> 人[り]</kun>",
        expected_furikanji_with_tags_split="<b><kun> ひと[一]</kun></b><kun> り[人]</kun>",
        expected_kana_only_with_tags_merged="<b><kun>ひと</kun></b><kun>り</kun>",
        expected_furigana_with_tags_merged="<b><kun> 一[ひと]</kun></b><kun> 人[り]</kun>",
        expected_furikanji_with_tags_merged="<b><kun> ひと[一]</kun></b><kun> り[人]</kun>",
    )
    test(
        test_name="numbers of people /2",
        kanji="沁",
        sentence="二人[ふたり]でしみじみと 語り合[かたりあ]った。",
        expected_kana_only="ふたりでしみじみと かたりあった。",
        expected_furigana=" 二人[ふたり]でしみじみと 語[かた]り 合[あ]った。",
        expected_furikanji=" ふたり[二人]でしみじみと かた[語]り あ[合]った。",
        expected_kana_only_with_tags_split=(
            "<kun>ふた</kun><kun>り</kun>でしみじみと"
            " <kun>かた</kun><oku>り</oku><kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_split=(
            "<kun> 二[ふた]</kun><kun> 人[り]</kun>でしみじみと<kun>"
            " 語[かた]</kun><oku>り</oku><kun> 合[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_split=(
            "<kun> ふた[二]</kun><kun> り[人]</kun>でしみじみと<kun>"
            " かた[語]</kun><oku>り</oku><kun> あ[合]</kun><oku>った</oku>。"
        ),
        expected_kana_only_with_tags_merged=(
            "<kun>ふたり</kun>でしみじみと <kun>かた</kun><oku>り</oku><kun>あ</kun><oku>った</oku>。"
        ),
        expected_furigana_with_tags_merged=(
            "<kun> 二人[ふたり]</kun>でしみじみと<kun> 語[かた]</kun><oku>り</oku><kun>"
            " 合[あ]</kun><oku>った</oku>。"
        ),
        expected_furikanji_with_tags_merged=(
            "<kun> ふたり[二人]</kun>でしみじみと<kun> かた[語]</kun><oku>り</oku><kun>"
            " あ[合]</kun><oku>った</oku>。"
        ),
    )
    test(
        test_name="numbers of people /3",
        kanji="三",
        sentence="三人[さんにん]",
        expected_kana_only="<b>サン</b>ニン",
        expected_furigana="<b> 三[サン]</b> 人[ニン]",
        expected_furikanji="<b> サン[三]</b> ニン[人]",
        expected_kana_only_with_tags_split="<b><on>サン</on></b><on>ニン</on>",
        expected_furigana_with_tags_split="<b><on> 三[サン]</on></b><on> 人[ニン]</on>",
        expected_furikanji_with_tags_split="<b><on> サン[三]</on></b><on> ニン[人]</on>",
        expected_kana_only_with_tags_merged="<b><on>サン</on></b><on>ニン</on>",
        expected_furigana_with_tags_merged="<b><on> 三[サン]</on></b><on> 人[ニン]</on>",
        expected_furikanji_with_tags_merged="<b><on> サン[三]</on></b><on> ニン[人]</on>",
    )
    test(
        test_name="生 readings /1",
        kanji="生",
        sentence="生粋[きっすい]",
        expected_kana_only="<b>きっ</b>スイ",
        expected_furigana="<b> 生[きっ]</b> 粋[スイ]",
        expected_furikanji="<b> きっ[生]</b> スイ[粋]",
        expected_kana_only_with_tags_split="<b><kun>きっ</kun></b><on>スイ</on>",
        expected_furigana_with_tags_split="<b><kun> 生[きっ]</kun></b><on> 粋[スイ]</on>",
        expected_furikanji_with_tags_split="<b><kun> きっ[生]</kun></b><on> スイ[粋]</on>",
        expected_kana_only_with_tags_merged="<b><kun>きっ</kun></b><on>スイ</on>",
        expected_furigana_with_tags_merged="<b><kun> 生[きっ]</kun></b><on> 粋[スイ]</on>",
        expected_furikanji_with_tags_merged="<b><kun> きっ[生]</kun></b><on> スイ[粋]</on>",
    )
    test(
        test_name="生 readings /2",
        kanji="生",
        sentence="生地[きじ]",
        expected_kana_only="<b>き</b>ジ",
        expected_furigana="<b> 生[き]</b> 地[ジ]",
        expected_furikanji="<b> き[生]</b> ジ[地]",
        expected_kana_only_with_tags_split="<b><kun>き</kun></b><on>ジ</on>",
        expected_furigana_with_tags_split="<b><kun> 生[き]</kun></b><on> 地[ジ]</on>",
        expected_furikanji_with_tags_split="<b><kun> き[生]</kun></b><on> ジ[地]</on>",
        expected_kana_only_with_tags_merged="<b><kun>き</kun></b><on>ジ</on>",
        expected_furigana_with_tags_merged="<b><kun> 生[き]</kun></b><on> 地[ジ]</on>",
        expected_furikanji_with_tags_merged="<b><kun> き[生]</kun></b><on> ジ[地]</on>",
    )
    test(
        test_name="生 readings /3",
        kanji="生",
        sentence="弥生[やよい]",
        expected_kana_only="や<b>よい</b>",
        expected_kana_only_with_tags_split="<kun>や</kun><b><kun>よい</kun></b>",
        expected_kana_only_with_tags_merged="<kun>や</kun><b><kun>よい</kun></b>",
    )
    test(
        test_name="生 readings /4",
        kanji="生",
        sentence="芝生[しばふ]",
        expected_kana_only="しば<b>ふ</b>",
        expected_kana_only_with_tags_split="<kun>しば</kun><b><kun>ふ</kun></b>",
        expected_kana_only_with_tags_merged="<kun>しば</kun><b><kun>ふ</kun></b>",
    )
    test(
        test_name="生 readings /5",
        kanji="生",
        sentence="生憎[あいにく]",
        expected_kana_only="<b>あい</b>にく",
        expected_kana_only_with_tags_split="<b><kun>あい</kun></b><kun>にく</kun>",
        expected_kana_only_with_tags_merged="<b><kun>あい</kun></b><kun>にく</kun>",
    )
    test(
        test_name="10 and １０ read as じっ or じゅっ no highlight",
        kanji=None,
        sentence="１０分[じゅっぷん]と10分[じっぷん]と10冊[じゅっさつ]",
        expected_kana_only="ジュップンとジップンとジュッサツ",
        expected_furigana=" １０分[ジュップン]と 10分[ジップン]と 10冊[ジュッサツ]",
        expected_furikanji=" ジュップン[１０分]と ジップン[10分]と ジュッサツ[10冊]",
        expected_kana_only_with_tags_split=(
            "<on>ジュッ</on><on>プン</on>と<on>ジッ</on><on>プン</on>と<on>ジュッ</on><on>サツ</on>"
        ),
        expected_furigana_with_tags_split=(
            "<on> １０[ジュッ]</on><on> 分[プン]</on>と<on> 10[ジッ]</on><on> 分[プン]</on>と<on>"
            " 10[ジュッ]</on><on> 冊[サツ]</on>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ジュッ[１０]</on><on> プン[分]</on>と<on> ジッ[10]</on><on> プン[分]</on>と<on>"
            " ジュッ[10]</on><on> サツ[冊]</on>"
        ),
        expected_kana_only_with_tags_merged="<on>ジュップン</on>と<on>ジップン</on>と<on>ジュッサツ</on>",
        expected_furigana_with_tags_merged=(
            "<on> １０分[ジュップン]</on>と<on> 10分[ジップン]</on>と<on> 10冊[ジュッサツ]</on>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ジュップン[１０分]</on>と<on> ジップン[10分]</on>と<on> ジュッサツ[10冊]</on>"
        ),
    )
    test(
        test_name="10 and １０ read as じっ or じゅっ highlight",
        kanji="分",
        sentence="１０分[じゅっぷん]と10分[じっぷん]と１０冊[じゅっさつ]",
        expected_kana_only="ジュッ<b>プン</b>とジッ<b>プン</b>とジュッサツ",
        expected_furigana=" １０[ジュッ]<b> 分[プン]</b>と 10[ジッ]<b> 分[プン]</b>と １０冊[ジュッサツ]",
        expected_furikanji=" ジュッ[１０]<b> プン[分]</b>と ジッ[10]<b> プン[分]</b>と ジュッサツ[１０冊]",
        expected_kana_only_with_tags_split=(
            "<on>ジュッ</on><b><on>プン</on></b>と<on>ジッ</on><b><on>プン</on></b>と<on>ジュッ</on>"
            "<on>サツ</on>"
        ),
        expected_furigana_with_tags_split=(
            "<on> １０[ジュッ]</on><b><on> 分[プン]</on></b>と<on> 10[ジッ]</on><b><on>"
            " 分[プン]</on></b>と<on> １０[ジュッ]</on><on> 冊[サツ]</on>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ジュッ[１０]</on><b><on> プン[分]</on></b>と<on> ジッ[10]</on><b><on>"
            " プン[分]</on></b>と<on> ジュッ[１０]</on><on> サツ[冊]</on>"
        ),
        # fmt: off
        expected_kana_only_with_tags_merged=(
            "<on>ジュッ</on><b><on>プン</on></b>と<on>ジッ</on><b><on>プン</on></b>と"
            "<on>ジュッサツ</on>"
        ),
        # fmt: on
        expected_furigana_with_tags_merged=(
            "<on> １０[ジュッ]</on><b><on> 分[プン]</on></b>と<on> 10[ジッ]</on><b><on>"
            " 分[プン]</on></b>と<on> １０冊[ジュッサツ]</on>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ジュッ[１０]</on><b><on> プン[分]</on></b>と<on> ジッ[10]</on><b><on>"
            " プン[分]</on></b>と<on> ジュッサツ[１０冊]</on>"
        ),
    )
    test(
        test_name="More numbers with furigana /1",
        kanji="",
        sentence="１[いち] ２[に] ３[さん] ４[よん] ０[ぜろ]",
        expected_kana_only="イチ ニ サン よん ぜろ",
        expected_furigana=" １[イチ] ２[ニ] ３[サン] ４[よん] ０[ぜろ]",
        expected_furikanji=" イチ[１] ニ[２] サン[３] よん[４] ぜろ[０]",
        expected_kana_only_with_tags_split=(
            "<on>イチ</on> <on>ニ</on> <on>サン</on> <kun>よん</kun> <kun>ぜろ</kun>"
        ),
        expected_furigana_with_tags_split=(
            "<on> １[イチ]</on><on> ２[ニ]</on><on> ３[サン]</on><kun> ４[よん]</kun><kun>"
            " ０[ぜろ]</kun>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> イチ[１]</on><on> ニ[２]</on><on> サン[３]</on><kun> よん[４]</kun><kun>"
            " ぜろ[０]</kun>"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>イチ</on> <on>ニ</on> <on>サン</on> <kun>よん</kun> <kun>ぜろ</kun>"
        ),
        expected_furigana_with_tags_merged=(
            "<on> １[イチ]</on><on> ２[ニ]</on><on> ３[サン]</on><kun> ４[よん]</kun><kun>"
            " ０[ぜろ]</kun>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> イチ[１]</on><on> ニ[２]</on><on> サン[３]</on><kun> よん[４]</kun><kun>"
            " ぜろ[０]</kun>"
        ),
    )
    test(
        test_name="Small tens",
        kanji="",
        sentence="３０分[さんじゅっぷん] 40分[よんじゅっぷん] １０時間[じゅうじかん] ５冊[ごさつ]",
        expected_kana_only="サンジュップン よんジュップン ジュウジカン ゴサツ",
        expected_furigana=" ３０分[サンジュップン] 40分[よんジュップン] １０時間[ジュウジカン] ５冊[ゴサツ]",
        expected_furikanji=" サンジュップン[３０分] よんジュップン[40分] ジュウジカン[１０時間] ゴサツ[５冊]",
        expected_kana_only_with_tags_split=(
            "<on>サン</on><on>ジュッ</on><on>プン</on> <kun>よん</kun><on>ジュッ</on><on>プン</on>"
            " <on>"
            "ジュウ</on><on>ジ</on><on>カン</on> <on>ゴ</on><on>サツ</on>"
        ),
        expected_furigana_with_tags_split=(
            "<on> ３０[サンジュッ]</on><on> 分[プン]</on><mix> 40[よんジュッ]</mix><on>"
            " 分[プン]</on><on> １０[ジュウ]</on><on> 時[ジ]</on><on> 間[カン]</on><on>"
            " ５[ゴ]</on><on>"
            " 冊[サツ]</on>"
        ),
        expected_furikanji_with_tags_split=(
            "<on> サンジュッ[３０]</on><on> プン[分]</on><mix> よんジュッ[40]</mix><on>"
            " プン[分]</on><on> ジュウ[１０]</on><on> ジ[時]</on><on> カン[間]</on><on>"
            " ゴ[５]</on><on> サツ[冊]</on>"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>サンジュップン</on> <kun>よん</kun><on>ジュップン</on> <on>ジュウジカン</on>"
            " <on>ゴサツ</on>"
        ),
        expected_furigana_with_tags_merged=(
            "<on> ３０分[サンジュップン]</on><mix> 40[よんジュッ]</mix><on> 分[プン]</on><on>"
            " １０時間[ジュウジカン]</on><on> ５冊[ゴサツ]</on>"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> サンジュップン[３０分]</on><mix> よんジュッ[40]</mix><on> プン[分]</on><on>"
            " ジュウジカン[１０時間]</on><on> ゴサツ[５冊]</on>"
        ),
    )
    test(
        test_name="Small teens",
        kanji="",
        sentence="15歳[じゅうごさい]に １１個[じゅういっこ]の ７番目[ななばんめ]をもらった。",
        expected_kana_only="ジュウゴサイに ジュウイッコの ななバンめをもらった。",
        expected_furigana=" 15歳[ジュウゴサイ]に １１個[ジュウイッコ]の ７番目[ななバンめ]をもらった。",
        expected_furikanji=" ジュウゴサイ[15歳]に ジュウイッコ[１１個]の ななバンめ[７番目]をもらった。",
        expected_kana_only_with_tags_split=(
            "<on>ジュウ</on><on>ゴ</on><on>サイ</on>に <on>ジュウ</on><on>イッ</on><on>コ</on>の"
            " <kun>なな</kun><on>バン</on><kun>め</kun>をもらった。"
        ),
        expected_furigana_with_tags_split=(
            "<on> 15[ジュウゴ]</on><on> 歳[サイ]</on>に<on> １１[ジュウイッ]</on><on>"
            " 個[コ]</on>の<kun> ７[なな]</kun><on> 番[バン]</on><kun> 目[め]</kun>をもらった。"
        ),
        expected_furikanji_with_tags_split=(
            "<on> ジュウゴ[15]</on><on> サイ[歳]</on>に<on> ジュウイッ[１１]</on><on>"
            " コ[個]</on>の<kun> なな[７]</kun><on> バン[番]</on><kun> め[目]</kun>をもらった。"
        ),
        expected_kana_only_with_tags_merged=(
            "<on>ジュウゴサイ</on>に <on>ジュウイッコ</on>の"
            " <kun>なな</kun><on>バン</on><kun>め</kun>をもらった。"
        ),
        expected_furigana_with_tags_merged=(
            "<on> 15歳[ジュウゴサイ]</on>に<on> １１個[ジュウイッコ]</on>の"
            "<kun> ７[なな]</kun><on> 番[バン]</on><kun> 目[め]</kun>をもらった。"
        ),
        expected_furikanji_with_tags_merged=(
            "<on> ジュウゴサイ[15歳]</on>に<on> ジュウイッコ[１１個]</on>の"
            "<kun> なな[７]</kun><on> バン[番]</on><kun> め[目]</kun>をもらった。"
        ),
    )
    test(
        test_name="Three digit numbers",
        kanji="",
        sentence=(
            "123[ひゃくにじゅうさん] 402[よんひゃくに] ３２０[さんびゃくにじゅう]"
            " 888[はっぴゃくはちじゅうはち]"
            " ４６６０[よんせんろっぴゃくろくじゅう]"
        ),
        expected_kana_only=(
            "ヒャクニジュウサン よんヒャクニ サンビャクニジュウ ハッピャクハチジュウハチ"
            " よんセンロッピャクロクジュウ"
        ),
        expected_furigana=(
            " 123[ヒャクニジュウサン] 402[よんヒャクニ] ３２０[サンビャクニジュウ]"
            " 888[ハッピャクハチジュウハチ] ４６６０[よんセンロッピャクロクジュウ]"
        ),
        expected_furikanji=(
            " ヒャクニジュウサン[123] よんヒャクニ[402] サンビャクニジュウ[３２０]"
            " ハッピャクハチジュウハチ[888] よんセンロッピャクロクジュウ[４６６０]"
        ),
        expected_kana_only_with_tags_split=(
            "<on>ヒャク</on><on>ニ</on><on>ジュウ</on><on>サン</on> <kun>よん</kun><on>ヒャク</on>"
            "<on>ニ</on> <on>サン</on><on>ビャク</on><on>ニ</on><on>ジュウ</on> <on>ハッ</on>"
            "<on>ピャク</on><on>ハチ</on><on>ジュウ</on><on>ハチ</on> <kun>よん</kun><on>"
            "セン</on><on>ロッ</on><on>ピャク</on><on>ロク</on><on>ジュウ</on>"
        ),
        expected_furigana_with_tags_split=(
            "<mix> 123[ヒャクニジュウサン]</mix><mix> 402[よんヒャクニ]</mix><mix>"
            " ３２０[サンビャクニジュウ]</mix><mix> 888[ハッピャクハチジュウハチ]</mix>"
            "<mix> ４６６０[よんセンロッピャクロクジュウ]</mix>"
        ),
        expected_furikanji_with_tags_split=(
            "<mix> ヒャクニジュウサン[123]</mix><mix> よんヒャクニ[402]</mix><mix>"
            " サンビャクニジュウ[３２０]</mix><mix> ハッピャクハチジュウハチ[888]</mix>"
            "<mix> よんセンロッピャクロクジュウ[４６６０]</mix>"
        ),
    )
    test(
        test_name="為る conjugations /!",
        kanji="",
        sentence="為[し]て 為[し]た 為[し]ました 為[さ]れる 為[し]ろ 為[し]ません それを為[し]",
        expected_kana_only_with_tags_split=(
            "<kun>し</kun><oku>て</oku> <kun>し</kun><oku>た</oku> <kun>し</kun><oku>ました</oku>"
            " <kun>さ</kun><oku>れる</oku> <kun>し</kun><oku>ろ</oku> <kun>し</kun><oku>ません</oku>"
            " それを<kun>し</kun>"
        ),
    )
    test(
        test_name="為る conjugations /2",
        kanji="",
        sentence="為[し]まった 為[し]ない 為[し]なかった 為[さ]せない 為[さ]せた 為[さ]せました",
        expected_kana_only_with_tags_split=(
            "<kun>し</kun><oku>ま</oku>った <kun>し</kun><oku>ない</oku>"
            " <kun>し</kun><oku>なかった</oku>"
            " <kun>さ</kun><oku>せない</oku> <kun>さ</kun><oku>せ</oku>た"
            " <kun>さ</kun><oku>せま</oku>した"
        ),
    )
    test(
        test_name="為る conjugations /3",
        kanji="",
        sentence="為[さ]せて 為[さ]せられ 為[さ]せろ 為[さ]せません 為[さ]せて 為[さ]せられた",
        expected_kana_only_with_tags_split=(
            "<kun>さ</kun><oku>せ</oku>て <kun>さ</kun><oku>せられ</oku> <kun>さ</kun><oku>せ</oku>ろ"
            " <kun>さ</kun><oku>せません</oku> <kun>さ</kun><oku>せ</oku>て"
            " <kun>さ</kun><oku>せられ</oku>た"
        ),
    )
    print("\n\033[92mTests passed\033[0m")


if __name__ == "__main__":
    main()
