import re

from .kana_conv import to_katakana

# Regex matching any kanji characters
# Include the kanji repeater punctuation as something that will be cleaned off
# Also include numbers as they are sometimes used in furigana
KANJI_RE = r"([\d々\u4e00-\u9faf\u3400-\u4dbf]+)"
KANJI_REC = re.compile(KANJI_RE)
# Same as above but allows for being empty
KANJI_RE_OPT = r"([\d々\u4e00-\u9faf\u3400-\u4dbf]*)"

# Matching any furigana with match groups
FURIGANA_RE = r" ?([^ >]+?)\[(.+?)\]"
FURIGANA_REC = re.compile(FURIGANA_RE)

# Matching any furigana without match groups
FURIGANA_NO_GROUPS_RE = r" ?[^ >]+\[[^ >]+\]"
FURIGANA_NO_GROUPS_REC = re.compile(FURIGANA_NO_GROUPS_RE)

# Text that contains any kanji repeated, to be replaced by the kanji+々
DOUBLE_KANJI_RE = r"([\u4e00-\u9faf\u3400-\u4dbf])\1"
DOUBLE_KANJI_REC = re.compile(DOUBLE_KANJI_RE)

KANJI_AND_REPEATER_RE = r"([\u4e00-\u9faf\u3400-\u4dbf]々)"
KANJI_AND_REPEATER_REC = re.compile(KANJI_AND_REPEATER_RE)

# Regex matching any kanji and furigana + hiragana after the furigana
KANJI_AND_FURIGANA_AND_OKURIGANA_RE = r"([\d々\u4e00-\u9faf\u3400-\u4dbf]+)\[(.+?)\]([ぁ-ん]*)"
KANJI_AND_FURIGANA_AND_OKURIGANA_REC = re.compile(KANJI_AND_FURIGANA_AND_OKURIGANA_RE)

HIRAGANA_RE = "([ぁ-ん])"
KATAKANA_RE = "([ァ-ン])"
KATAKANA_REC = re.compile(KATAKANA_RE)

# Palatilized (拗音) mora and other non-straight mora
PALATALIZED_MORA = [
    "くぃ",
    "きゃ",
    "きゅ",
    "きぇ",
    "きょ",
    "ぐぃ",
    "ぎゃ",
    "ぎゅ",
    "ぎぇ",
    "ぎょ",
    "すぃ",
    "しゃ",
    "しゅ",
    "しぇ",
    "しょ",
    "ずぃ",
    "じゃ",
    "じゅ",
    "じぇ",
    "じょ",
    "てぃ",
    "とぅ",
    "ちゃ",
    "ちゅ",
    "ちぇ",
    "ちょ",
    "でぃ",
    "どぅ",
    "ぢゃ",
    "でゅ",
    "ぢゅ",
    "ぢぇ",
    "ぢょ",
    "つぁ",
    "つぃ",
    "つぇ",
    "つぉ",
    "づぁ",
    "づぃ",
    "づぇ",
    "づぉ",
    "ひぃ",
    "ほぅ",
    "ひゃ",
    "ひゅ",
    "ひぇ",
    "ひょ",
    "びぃ",
    "びゃ",
    "びゅ",
    "びぇ",
    "びょ",
    "ぴぃ",
    "ぴゃ",
    "ぴゅ",
    "ぴぇ",
    "ぴょ",
    "ふぁ",
    "ふぃ",
    "ふぇ",
    "ふぉ",
    "ゔぁ",
    "ゔぃ",
    "ゔぇ",
    "ゔぉ",
    "ぬぃ",
    "にゃ",
    "にゅ",
    "にぇ",
    "にょ",
    "むぃ",
    "みゃ",
    "みゅ",
    "みぇ",
    "みょ",
    "るぃ",
    "りゃ",
    "りゅ",
    "りぇ",
    "りょ",
    "いぇ",
]

SINGLE_KANA_MORA = [
    "か",
    "く",
    "け",
    "こ",
    "き",
    "が",
    "ぐ",
    "げ",
    "ご",
    "ぎ",
    "さ",
    "す",
    "せ",
    "そ",
    "し",
    "ざ",
    "ず",
    "づ",
    "ぜ",
    "ぞ",
    "じ",
    "ぢ",
    "た",
    "と",
    "て",
    "と",
    "ち",
    "だ",
    "で",
    "ど",
    "ぢ",
    "つ",
    "づ",
    "は",
    "へ",
    "ほ",
    "ひ",
    "ば",
    "ぶ",
    "べ",
    "ぼ",
    "ぼ",
    "び",
    "ぱ",
    "ぷ",
    "べ",
    "ぽ",
    "ぴ",
    "ふ",
    "ゔ",
    "な",
    "ぬ",
    "ね",
    "の",
    "に",
    "ま",
    "む",
    "め",
    "も",
    "み",
    "ら",
    "る",
    "れ",
    "ろ",
    "り",
    "あ",
    "い",
    "う",
    "え",
    "お",
    "や",
    "ゆ",
    "よ",
    "わ",
    "ゐ",
    "ゑ",
    "を",
]

# Elongated vowels of the single kana mora (直音)
LONG_STRAIGHT_MORA = [f"{kana}ー" for kana in SINGLE_KANA_MORA]

# First all two kana more, so they get matched first, then the single kana mora
ALL_MORA = (
    PALATALIZED_MORA
    + LONG_STRAIGHT_MORA
    + SINGLE_KANA_MORA
    + [
        "ん",
    ]
)

# Add the small tsu versions of all mora to be matched first
ALL_MORA_RE = "|".join([m + "っ" for m in ALL_MORA] + ALL_MORA)
ALL_MORA_REC = re.compile(rf"({ALL_MORA_RE})")


RENDAKU_CONVERSION_DICT_HIRAGANA = {
    "か": ["が"],
    "き": ["ぎ"],
    "く": ["ぐ"],
    "け": ["げ"],
    "こ": ["ご"],
    "さ": ["ざ"],
    "し": ["じ"],
    "す": ["ず"],
    "せ": ["ぜ"],
    "そ": ["ぞ"],
    "た": ["だ"],
    "ち": ["ぢ"],
    "つ": ["づ"],
    "て": ["で"],
    "と": ["ど"],
    "は": ["ば", "ぱ"],
    "ひ": ["び", "ぴ"],
    "ふ": ["ぶ", "ぷ"],
    "へ": ["べ", "ぺ"],
    "ほ": ["ぼ", "ぽ"],
    "う": ["ぬ"],
}
# Convert HIRAGANA_CONVERSION_DICT to katakana with to_katakana
RENDAKU_CONVERSION_DICT_KATAKANA = {
    to_katakana(k): [to_katakana(v) for v in vs]
    for k, vs in RENDAKU_CONVERSION_DICT_HIRAGANA.items()
}
