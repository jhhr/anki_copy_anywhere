from typing import Union, Tuple

# Edited from https://github.com/yamagoya/jconj/blob/master/data/kwpos.csv
# Retained only the rows that the conjugation table had entries for.
PART_OF_SPEECH_NUM: dict[int, list[str]] = {
    1: ["adj-i", "adjective (keiyoushi)"],
    2: ["adj-na", "adjectival nouns or quasi-adjectives (keiyodoshi)"],
    7: ["adj-ix", "adjective (keiyoushi) - yoi/ii class"],
    28: ["v1", "Ichidan verb"],
    29: ["v1-s", "Ichidan verb - kureru special class"],
    # Verbs ending in -ある, as in おいてある/してある
    30: ["v5aru", "Godan verb - -aru special class"],
    31: ["v5b", "Godan verb with `bu' ending"],
    32: ["v5g", "Godan verb with `gu' ending"],
    33: ["v5k", "Godan verb with `ku' ending"],
    34: ["v5k-s", "Godan verb - Iku/Yuku special class"],
    35: ["v5m", "Godan verb with `mu' ending"],
    36: ["v5n", "Godan verb with `nu' ending"],
    37: ["v5r", "Godan verb with `ru' ending"],
    38: ["v5r-i", "Godan verb with `ru' ending (irregular verb)"],
    39: ["v5s", "Godan verb with `su' ending"],
    40: ["v5t", "Godan verb with `tsu' ending"],
    41: ["v5u", "Godan verb with `u' ending"],
    42: ["v5u-s", "Godan verb with `u' ending (special class)"],
    45: ["vk", "Kuru verb - special class"],
    46: ["vs", "noun or participle which takes the aux. verb suru"],
    # 発する/察する/属する/... also some can drop the る: 接す, 察す, ...
    # single kanji suru verbs that all have small つ reading
    47: ["vs-s", "suru verb - special class"],
    # 為る itself, where the potential is できる
    # Single kanji suru verbs that don't have small つ reading: 愛する, 関する, ... also 愛す
    # whose potential is different: 愛せる, 関せる, ...
    # also all other suru verbs where suru is conjugated as 為る
    48: ["vs-i", "suru verb - included"],
}

E_I_ENDING_KANA: set[str] = {
    "い",
    "え",
    "き",
    "け",
    "し",
    "せ",
    "ち",
    "て",
    "に",
    "ね",
    "ひ",
    "へ",
    "み",
    "め",
    "り",
    "れ",
}

GODAN_ENDINGS: dict[str, str] = {
    "う": "u",
    "く": "k",
    "ぐ": "g",
    "す": "s",
    "つ": "t",
    "ぬ": "n",
    "ぶ": "b",
    "む": "m",
    "る": "r",
}


# For getting the conjugation dict in POSSIBLE_OKURIGANA_PROGRESSION_DICT
# we need to determine the word's part of speech.
def get_part_of_speech(
    okurigana: str,
    kanji: str,
    kanji_reading: str,
) -> Union[str, None]:
    """
    Get the part of speech key for POSSIBLE_OKURIGANA_PROGRESSION_DICT for a word.
    :param okurigana: Always required.
    :param kanji: Required for identifying special irregular verbs.
    :param kanji_reading: Required for vs-s special case only.
    :return: part of speech key for POSSIBLE_OKURIGANA_PROGRESSION_DICT
        None if no part of speech key was found.
    """
    # Sanity check, need to have okurigana
    if not okurigana:
        return None

    # Special cases based on kanji + okurigana combinations
    if kanji == "行" and okurigana == "く":
        return "v5k-s"
    if kanji == "為" and okurigana == "る":
        return "vs-i"
    if kanji == "呉" and okurigana == "れる":
        return "v1-s"
    # Note: part of 有る's conjugations would actually use the kanji 無,
    # However, all those forms fit into the i-adjective patterns
    if kanji in ["有", "在"] and okurigana == "る":
        return "v5r-i"

    # Handle vs-s vs vs-i for special suru verbs
    if okurigana in ["する", "す"] and kanji_reading.endswith("っ"):
        return "vs-s"
    if okurigana in ["する", "す"]:
        return "vs-i"

    # Adjective patterns
    if okurigana == "い":
        if kanji == "良":  # Special case for よい/いい
            return "adj-ix"
        return "adj-i"
    if okurigana.endswith("い"):
        return "adj-i"
    if okurigana[-1] in ["か", "な", "だ"]:
        return "adj-na"

    # Regular verb patterns
    # Check ichidan vs godan
    if len(okurigana) >= 2 and okurigana.endswith("る") and okurigana[-2] in E_I_ENDING_KANA:
        # Verbs ending in eru/iru are ichidan
        return "v1"

    # Godan verb endings
    godan_type = GODAN_ENDINGS.get(okurigana[-1])
    print(f"last char: {okurigana[-1]}")
    if godan_type:
        return f"v5{godan_type}"

    return None  # Return None if no pattern matches


def get_okuri_dict_for_okurigana(
    okurigana: str,
    kanji: str,
    kanji_reading: str,
) -> Union[dict, None]:
    """
    Get the okurigana progression dict for a dictionary form word.
    :param okurigana: The okurigana of the kanji.
    :param kanji: The kanji.
    :param kanji_reading: The reading of the kanji
    :return: The okurigana progression dict for the word.
        None if the word is not conjugatable.
    """
    part_of_speech = get_part_of_speech(
        okurigana=okurigana,
        kanji=kanji,
        kanji_reading=kanji_reading,
    )
    print(f"part_of_speech: {part_of_speech}")
    if part_of_speech is None:
        return None
    return POSSIBLE_OKURIGANA_PROGRESSION_DICT[part_of_speech]


# Edited from https://github.com/yamagoya/jconj/blob/master/data/conjo.csv
# Retained only the conjugation and pos (part of speech) columns.
# Some unnecessary conjugations were removed like those ending
# in でしょう, ならば or です among others.
# euphonic changes were also removed except for the last vs-s (47) vs vs-i (48)
# suru verb classes
ALL_OKURI_BY_PART_OF_SPEECH: list[Union[Tuple[int, str], Tuple[int, str, str]]] = [
    (1, "い"),
    (1, "くない"),
    (1, "くないです"),
    (1, "くありません"),
    (1, "かった"),
    (1, "かったです"),
    (1, "くなかった"),
    (1, "くありませんでした"),
    (1, "く"),  # Added for adverbial conjugation of adjectives, e.g. 速く or 高くすぎる
    (1, "くて"),
    (1, "くなくて"),
    (1, "ければ"),
    (1, "くなければ"),
    (1, "くさせる"),
    (1, "かろう"),
    (1, "かったら"),
    (1, "くなかったら"),
    (1, "かったり"),
    (1, "さ"),  # Added for noun conjugation of adjectives, e.g. 高さ
    (1, ""),  # Added for e.g. 恥ずかし気な where the い is dropped
    (2, "だ"),
    (7, "い"),
    (28, "る"),
    (28, "ます"),
    (28, "ない"),
    (28, "ません"),
    (28, "た"),
    (28, "ました"),
    (28, "なかった"),
    (28, "ませんでした"),
    (28, "て"),
    (28, "まして"),
    (28, "なくて"),
    (28, "ないで"),
    (28, "ませんで"),
    (28, "れば"),
    (28, "なければ"),
    (28, "られて"),
    (28, "れる"),
    (28, "られます"),
    (28, "れます"),
    (28, "られない"),
    (28, "れない"),
    (28, "られません"),
    (28, "れません"),
    (28, "られる"),
    (28, "られます"),
    (28, "られない"),
    (28, "られません"),
    (28, "させる"),
    (28, "さす"),
    (28, "させます"),
    (28, "さします"),
    (28, "させない"),
    (28, "ささない"),
    (28, "させません"),
    (28, "さしません"),
    (28, "させられる"),
    (28, "させられます"),
    (28, "させられない"),
    (28, "させられません"),
    (28, "よう"),
    (28, "ましょう"),
    (28, "まい"),
    (28, "ますまい"),
    (28, "ろ"),
    (28, "なさい"),
    (28, "るな"),
    (28, "なさるな"),
    (28, "たら"),
    (28, "ましたら"),
    (28, "なかったら"),
    (28, "ませんでしたら"),
    (28, "たり"),
    (28, "ましたり"),
    (28, "なかったり"),
    (28, "ませんでしたり"),
    (29, "る"),
    (29, "ます"),
    (29, "ない"),
    (29, "ません"),
    (29, "た"),
    (29, "ました"),
    (29, "なかった"),
    (29, "ませんでした"),
    (29, "て"),
    (29, "まして"),
    (29, "なくて"),
    (29, "ないで"),
    (29, "ませんで"),
    (29, "れば"),
    (29, "なければ"),
    (29, "られる"),
    (29, "れる"),
    (29, "られます"),
    (29, "れます"),
    (29, "られない"),
    (29, "れない"),
    (29, "られません"),
    (29, "れません"),
    (29, "られる"),
    (29, "られます"),
    (29, "られない"),
    (29, "られません"),
    (29, "させる"),
    (29, "さす"),
    (29, "させます"),
    (29, "さします"),
    (29, "させない"),
    (29, "ささない"),
    (29, "させません"),
    (29, "さしません"),
    (29, "させられる"),
    (29, "させられます"),
    (29, "させられない"),
    (29, "させられません"),
    (29, "よう"),
    (29, "ましょう"),
    (29, "まい"),
    (29, "ますまい"),
    (29, "なさい"),
    (29, "るな"),
    (29, "なさるな"),
    (29, "たら"),
    (29, "ましたら"),
    (29, "なかったら"),
    (29, "ませんでしたら"),
    (29, "たり"),
    (29, "ましたり"),
    (29, "なかったり"),
    (29, "ませんでしたり"),
    (30, "る"),
    (30, "います"),
    (30, "らない"),
    (30, "いません"),
    (30, "った"),
    (30, "いました"),
    (30, "らなかった"),
    (30, "いませんでした"),
    (30, "って"),
    (30, "いまして"),
    (30, "らなくて"),
    (30, "らないで"),
    (30, "いませんで"),
    (30, "れば"),
    (30, "らなければ"),
    (30, "れる"),
    (30, "れます"),
    (30, "れない"),
    (30, "れません"),
    (30, "られる"),
    (30, "られます"),
    (30, "られない"),
    (30, "られません"),
    (30, "らせる"),
    (30, "らす"),
    (30, "らせます"),
    (30, "らします"),
    (30, "らせない"),
    (30, "らさない"),
    (30, "らせません"),
    (30, "らしません"),
    (30, "らせられる"),
    (30, "らされる"),
    (30, "らせられます"),
    (30, "らされます"),
    (30, "らせられない"),
    (30, "らされない"),
    (30, "らせられません"),
    (30, "らされません"),
    (30, "ろう"),
    (30, "いましょう"),
    (30, "るまい"),
    (30, "いませんまい"),
    (30, "い"),
    (30, "いなさい"),
    (30, "るな"),
    (30, "いなさるな"),
    (30, "ったら"),
    (30, "いましたら"),
    (30, "らなかったら"),
    (30, "いませんでしたら"),
    (30, "ったり"),
    (30, "いましたり"),
    (30, "らなかったり"),
    (30, "いませんでしたり"),
    (30, "い"),
    (31, "ぶ"),
    (31, "びます"),
    (31, "ばない"),
    (31, "びません"),
    (31, "んだ"),
    (31, "びました"),
    (31, "ばなかった"),
    (31, "びませんでした"),
    (31, "んで"),
    (31, "びまして"),
    (31, "ばなくて"),
    (31, "ばないで"),
    (31, "びませんで"),
    (31, "べば"),
    (31, "ばなければ"),
    (31, "べる"),
    (31, "べます"),
    (31, "べない"),
    (31, "べません"),
    (31, "ばれる"),
    (31, "ばれます"),
    (31, "ばれない"),
    (31, "ばれません"),
    (31, "ばせる"),
    (31, "ばす"),
    (31, "ばせます"),
    (31, "ばします"),
    (31, "ばせない"),
    (31, "ばさない"),
    (31, "ばせません"),
    (31, "ばしません"),
    (31, "ばせられる"),
    (31, "ばされる"),
    (31, "ばせられます"),
    (31, "ばされます"),
    (31, "ばせられない"),
    (31, "ばされない"),
    (31, "ばせられません"),
    (31, "ばされません"),
    (31, "ぼう"),
    (31, "びましょう"),
    (31, "ぶまい"),
    (31, "びませんまい"),
    (31, "べ"),
    (31, "びなさい"),
    (31, "ぶな"),
    (31, "びなさるな"),
    (31, "んだら"),
    (31, "びましたら"),
    (31, "ばなかったら"),
    (31, "びませんでしたら"),
    (31, "んだり"),
    (31, "びましたり"),
    (31, "ばなかったり"),
    (31, "びませんでしたり"),
    (31, "び"),
    (32, "ぐ"),
    (32, "ぎます"),
    (32, "がない"),
    (32, "ぎません"),
    (32, "いだ"),
    (32, "ぎました"),
    (32, "がなかった"),
    (32, "ぎませんでした"),
    (32, "いで"),
    (32, "ぎまして"),
    (32, "がなくて"),
    (32, "がないで"),
    (32, "ぎませんで"),
    (32, "げば"),
    (32, "がなければ"),
    (32, "げる"),
    (32, "げます"),
    (32, "げない"),
    (32, "げません"),
    (32, "がれる"),
    (32, "がれます"),
    (32, "がれない"),
    (32, "がれません"),
    (32, "がせる"),
    (32, "がす"),
    (32, "がせます"),
    (32, "がします"),
    (32, "がせない"),
    (32, "がさない"),
    (32, "がせません"),
    (32, "がしません"),
    (32, "がせられる"),
    (32, "がされる"),
    (32, "がせられます"),
    (32, "がされます"),
    (32, "がせられない"),
    (32, "がされない"),
    (32, "がせられません"),
    (32, "がされません"),
    (32, "ごう"),
    (32, "ぎましょう"),
    (32, "ぐまい"),
    (32, "ぎませんまい"),
    (32, "げ"),
    (32, "ぎなさい"),
    (32, "ぐな"),
    (32, "ぎなさるな"),
    (32, "いだら"),
    (32, "ぎましたら"),
    (32, "がなかったら"),
    (32, "ぎませんでしたら"),
    (32, "いだり"),
    (32, "ぎましたり"),
    (32, "がなかったり"),
    (32, "ぎませんでしたり"),
    (32, "ぎ"),
    (33, "く"),
    (33, "きます"),
    (33, "かない"),
    (33, "きません"),
    (33, "いた"),
    (33, "きました"),
    (33, "かなかった"),
    (33, "きませんでした"),
    (33, "いて"),
    (33, "きまして"),
    (33, "かなくて"),
    (33, "かないで"),
    (33, "きませんで"),
    (33, "けば"),
    (33, "かなければ"),
    (33, "ける"),
    (33, "けます"),
    (33, "けない"),
    (33, "けません"),
    (33, "かれる"),
    (33, "かれます"),
    (33, "かれない"),
    (33, "かれません"),
    (33, "かせる"),
    (33, "かす"),
    (33, "かせます"),
    (33, "かします"),
    (33, "かせない"),
    (33, "かさない"),
    (33, "かせません"),
    (33, "かしません"),
    (33, "かせられる"),
    (33, "かされる"),
    (33, "かせられます"),
    (33, "かされます"),
    (33, "かせられない"),
    (33, "かされない"),
    (33, "かせられません"),
    (33, "かされません"),
    (33, "こう"),
    (33, "きましょう"),
    (33, "くまい"),
    (33, "きませんまい"),
    (33, "け"),
    (33, "きなさい"),
    (33, "くな"),
    (33, "きなさるな"),
    (33, "いたら"),
    (33, "きましたら"),
    (33, "かなかったら"),
    (33, "きませんでしたら"),
    (33, "いたり"),
    (33, "きましたり"),
    (33, "かなかったり"),
    (33, "きませんでしたり"),
    (33, "き"),
    (34, "く"),
    (34, "きます"),
    (34, "かない"),
    (34, "きません"),
    (34, "った"),
    (34, "きました"),
    (34, "かなかった"),
    (34, "きませんでした"),
    (34, "って"),
    (34, "きまして"),
    (34, "かなくて"),
    (34, "かないで"),
    (34, "きませんで"),
    (34, "けば"),
    (34, "かなければ"),
    (34, "ける"),
    (34, "けます"),
    (34, "けない"),
    (34, "けません"),
    (34, "かれる"),
    (34, "かれます"),
    (34, "かれない"),
    (34, "かれません"),
    (34, "かせる"),
    (34, "かす"),
    (34, "かせます"),
    (34, "かします"),
    (34, "かせない"),
    (34, "かさない"),
    (34, "かせません"),
    (34, "かしません"),
    (34, "かせられる"),
    (34, "かされる"),
    (34, "かせられます"),
    (34, "かされます"),
    (34, "かせられない"),
    (34, "かされない"),
    (34, "かせられません"),
    (34, "かされません"),
    (34, "こう"),
    (34, "きましょう"),
    (34, "くまい"),
    (34, "きませんまい"),
    (34, "け"),
    (34, "きなさい"),
    (34, "くな"),
    (34, "きなさるな"),
    (34, "ったら"),
    (34, "きましたら"),
    (34, "かなかったら"),
    (34, "きませんでしたら"),
    (34, "ったり"),
    (34, "きましたり"),
    (34, "かなかったり"),
    (34, "きませんでしたり"),
    (34, "き"),
    (35, "む"),
    (35, "みます"),
    (35, "まない"),
    (35, "みません"),
    (35, "んだ"),
    (35, "みました"),
    (35, "まなかった"),
    (35, "みませんでした"),
    (35, "んで"),
    (35, "みまして"),
    (35, "まなくて"),
    (35, "まないで"),
    (35, "みませんで"),
    (35, "めば"),
    (35, "まなければ"),
    (35, "める"),
    (35, "めます"),
    (35, "めない"),
    (35, "めません"),
    (35, "まれる"),
    (35, "まれた"),
    (35, "まれます"),
    (35, "まれない"),
    (35, "まれません"),
    (35, "ませる"),
    (35, "ます"),
    (35, "ませます"),
    (35, "まします"),
    (35, "ませない"),
    (35, "まさない"),
    (35, "ませません"),
    (35, "ましません"),
    (35, "ませられる"),
    (35, "まされる"),
    (35, "ませられます"),
    (35, "まされます"),
    (35, "ませられない"),
    (35, "まされない"),
    (35, "ませられません"),
    (35, "まされません"),
    (35, "もう"),
    (35, "みましょう"),
    (35, "むまい"),
    (35, "みませんまい"),
    (35, "め"),
    (35, "みなさい"),
    (35, "むな"),
    (35, "みなさるな"),
    (35, "んだら"),
    (35, "みましたら"),
    (35, "まなかったら"),
    (35, "みませんでしたら"),
    (35, "んだり"),
    (35, "みましたり"),
    (35, "まなかったり"),
    (35, "みませんでしたり"),
    (35, "み"),
    (36, "ぬ"),
    (36, "にます"),
    (36, "なない"),
    (36, "にません"),
    (36, "んだ"),
    (36, "にました"),
    (36, "ななかった"),
    (36, "にませんでした"),
    (36, "んで"),
    (36, "にまして"),
    (36, "ななくて"),
    (36, "なないで"),
    (36, "にませんで"),
    (36, "ねば"),
    (36, "ななければ"),
    (36, "ねる"),
    (36, "ねます"),
    (36, "ねない"),
    (36, "ねません"),
    (36, "なれる"),
    (36, "なれます"),
    (36, "なれない"),
    (36, "なれません"),
    (36, "なせる"),
    (36, "なす"),
    (36, "なせます"),
    (36, "なします"),
    (36, "なせない"),
    (36, "なさない"),
    (36, "なせません"),
    (36, "なしません"),
    (36, "なせられる"),
    (36, "なされる"),
    (36, "なせられます"),
    (36, "なされます"),
    (36, "なせられない"),
    (36, "なされない"),
    (36, "なせられません"),
    (36, "なされません"),
    (36, "のう"),
    (36, "にましょう"),
    (36, "ぬまい"),
    (36, "にませんまい"),
    (36, "ね"),
    (36, "になさい"),
    (36, "ぬな"),
    (36, "になさるな"),
    (36, "んだら"),
    (36, "にましたら"),
    (36, "ななかったら"),
    (36, "にませんでしたら"),
    (36, "んだり"),
    (36, "にましたり"),
    (36, "ななかったり"),
    (36, "にませんでしたり"),
    (36, "に"),
    (37, "る"),
    (37, "ります"),
    (37, "らない"),
    (37, "りません"),
    (37, "った"),
    (37, "りました"),
    (37, "らなかった"),
    (37, "りませんでした"),
    (37, "って"),
    (37, "りまして"),
    (37, "らなくて"),
    (37, "らないで"),
    (37, "りませんで"),
    (37, "れば"),
    (37, "らなければ"),
    (37, "れる"),
    (37, "れます"),
    (37, "れない"),
    (37, "れません"),
    (37, "られる"),
    (37, "られます"),
    (37, "られない"),
    (37, "られません"),
    (37, "らせる"),
    (37, "らす"),
    (37, "らせます"),
    (37, "らします"),
    (37, "らせない"),
    (37, "らさない"),
    (37, "らせません"),
    (37, "らしません"),
    (37, "らせられる"),
    (37, "らされる"),
    (37, "らせられます"),
    (37, "らされます"),
    (37, "らせられない"),
    (37, "らされない"),
    (37, "らせられません"),
    (37, "らされません"),
    (37, "ろう"),
    (37, "りましょう"),
    (37, "るまい"),
    (37, "りませんまい"),
    (37, "れ"),
    (37, "りなさい"),
    (37, "るな"),
    (37, "りなさるな"),
    (37, "ったら"),
    (37, "りましたら"),
    (37, "らなかったら"),
    (37, "りませんでしたら"),
    (37, "ったり"),
    (37, "りましたり"),
    (37, "らなかったり"),
    (37, "りませんでしたり"),
    (37, "り"),
    (38, "る"),
    (38, "ります"),
    (38, "ない"),
    (38, "りません"),
    (38, "った"),
    (38, "りました"),
    (38, "なかった"),
    (38, "りませんでした"),
    (38, "って"),
    (38, "りまして"),
    (38, "なくて"),
    (38, "ないで"),
    (38, "りませんで"),
    (38, "れば"),
    (38, "なければ"),
    (38, "れる"),
    (38, "れます"),
    (38, "れない"),
    (38, "れません"),
    (38, "られる"),
    (38, "られます"),
    (38, "られない"),
    (38, "られません"),
    (38, "らせる"),
    (38, "らす"),
    (38, "らせます"),
    (38, "らします"),
    (38, "らせない"),
    (38, "らさない"),
    (38, "らせません"),
    (38, "らしません"),
    (38, "らせられる"),
    (38, "らされる"),
    (38, "らせられます"),
    (38, "らされます"),
    (38, "らせられない"),
    (38, "らされない"),
    (38, "らせられません"),
    (38, "らされません"),
    (38, "ろう"),
    (38, "りましょう"),
    (38, "るまい"),
    (38, "りませんまい"),
    (38, "れ"),
    (38, "りなさい"),
    (38, "るな"),
    (38, "りなさるな"),
    (38, "ったら"),
    (38, "りましたら"),
    (38, "なかったら"),
    (38, "りませんでしたら"),
    (38, "ったり"),
    (38, "りましたり"),
    (38, "なかったり"),
    (38, "りませんでしたり"),
    (38, "り"),
    (39, "す"),
    (39, "します"),
    (39, "さない"),
    (39, "しません"),
    (39, "した"),
    (39, "しました"),
    (39, "さなかった"),
    (39, "しませんでした"),
    (39, "して"),
    (39, "しまして"),
    (39, "さなくて"),
    (39, "さないで"),
    (39, "しませんで"),
    (39, "せば"),
    (39, "さなければ"),
    (39, "せる"),
    (39, "せます"),
    (39, "せない"),
    (39, "せません"),
    (39, "される"),
    (39, "されます"),
    (39, "されない"),
    (39, "されません"),
    (39, "させる"),
    (39, "さす"),
    (39, "させます"),
    (39, "さします"),
    (39, "させない"),
    (39, "ささない"),
    (39, "させません"),
    (39, "さしません"),
    (39, "させられる"),
    (39, "させられます"),
    (39, "させられない"),
    (39, "させられません"),
    (39, "そう"),
    (39, "しましょう"),
    (39, "すまい"),
    (39, "しませんまい"),
    (39, "せ"),
    (39, "しなさい"),
    (39, "すな"),
    (39, "しなさるな"),
    (39, "したら"),
    (39, "しましたら"),
    (39, "さなかったら"),
    (39, "しませんでしたら"),
    (39, "したり"),
    (39, "しましたり"),
    (39, "さなかったり"),
    (39, "しませんでしたり"),
    (39, "し"),
    (40, "つ"),
    (40, "ちます"),
    (40, "たない"),
    (40, "ちません"),
    (40, "った"),
    (40, "ちました"),
    (40, "たなかった"),
    (40, "ちませんでした"),
    (40, "って"),
    (40, "ちまして"),
    (40, "たなくて"),
    (40, "たないで"),
    (40, "ちませんで"),
    (40, "てば"),
    (40, "たなければ"),
    (40, "てる"),
    (40, "てます"),
    (40, "てない"),
    (40, "てません"),
    (40, "たれる"),
    (40, "たれます"),
    (40, "たれない"),
    (40, "たれません"),
    (40, "たせる"),
    (40, "たす"),
    (40, "たせます"),
    (40, "たします"),
    (40, "たせない"),
    (40, "たさない"),
    (40, "たせません"),
    (40, "たしません"),
    (40, "たせられる"),
    (40, "たされる"),
    (40, "たせられます"),
    (40, "たされます"),
    (40, "たせられない"),
    (40, "たされない"),
    (40, "たせられません"),
    (40, "たされません"),
    (40, "とう"),
    (40, "ちましょう"),
    (40, "つまい"),
    (40, "ちませんまい"),
    (40, "て"),
    (40, "ちなさい"),
    (40, "つな"),
    (40, "ちなさるな"),
    (40, "ったら"),
    (40, "ちまったら"),
    (40, "たなかったら"),
    (40, "ちませんでしたら"),
    (40, "ったり"),
    (40, "ちましたり"),
    (40, "たなかったり"),
    (40, "ちませんでしたり"),
    (40, "ち"),
    (41, "う"),
    (41, "います"),
    (41, "わない"),
    (41, "いません"),
    (41, "った"),
    (41, "いました"),
    (41, "わなかった"),
    (41, "いませんでした"),
    (41, "って"),
    (41, "いまして"),
    (41, "わなくて"),
    (41, "わないで"),
    (41, "いませんで"),
    (41, "えば"),
    (41, "わなければ"),
    (41, "える"),
    (41, "えます"),
    (41, "えない"),
    (41, "えません"),
    (41, "われる"),
    (41, "われます"),
    (41, "われない"),
    (41, "われません"),
    (41, "わせる"),
    (41, "わす"),
    (41, "わせます"),
    (41, "わします"),
    (41, "わせない"),
    (41, "わさない"),
    (41, "わせません"),
    (41, "わしません"),
    (41, "わせられる"),
    (41, "わされる"),
    (41, "わせられます"),
    (41, "わされます"),
    (41, "わせられない"),
    (41, "わされない"),
    (41, "わせられません"),
    (41, "わされません"),
    (41, "おう"),
    (41, "いましょう"),
    (41, "うまい"),
    (41, "いませんまい"),
    (41, "え"),
    (41, "いなさい"),
    (41, "うな"),
    (41, "いなさるな"),
    (41, "ったら"),
    (41, "いましたら"),
    (41, "わかったら"),
    (41, "いませんでしたら"),
    (41, "ったり"),
    (41, "いましたり"),
    (41, "わなかったり"),
    (41, "いませんでしたり"),
    (41, "い"),
    (42, "う"),
    (42, "います"),
    (42, "わない"),
    (42, "いません"),
    (42, "うた"),
    (42, "いました"),
    (42, "わなかった"),
    (42, "いませんでした"),
    (42, "うて"),
    (42, "いまして"),
    (42, "わなくて"),
    (42, "わないで"),
    (42, "いませんで"),
    (42, "えば"),
    (42, "わなければ"),
    (42, "える"),
    (42, "えます"),
    (42, "えない"),
    (42, "えません"),
    (42, "われる"),
    (42, "われます"),
    (42, "われない"),
    (42, "われません"),
    (42, "わせる"),
    (42, "わす"),
    (42, "わせます"),
    (42, "わします"),
    (42, "わせない"),
    (42, "わさない"),
    (42, "わせません"),
    (42, "わしません"),
    (42, "わせられる"),
    (42, "わされる"),
    (42, "わせられます"),
    (42, "わされます"),
    (42, "わせられない"),
    (42, "わされない"),
    (42, "わせられません"),
    (42, "わされません"),
    (42, "おう"),
    (42, "いましょう"),
    (42, "うまい"),
    (42, "いませんまい"),
    (42, "え"),
    (42, "いなさい"),
    (42, "うな"),
    (42, "いなさるな"),
    (42, "うたら"),
    (42, "いましたら"),
    (42, "わなかったら"),
    (42, "いませんでしたら"),
    (42, "うたり"),
    (42, "いましたり"),
    (42, "わなかったり"),
    (42, "いませんでしたり"),
    (42, "い"),
    (45, "る"),
    (45, "ます"),
    (45, "ない"),
    (45, "ません"),
    (45, "た"),
    (45, "ました"),
    (45, "なかった"),
    (45, "ませんでした"),
    (45, "て"),
    (45, "まして"),
    (45, "なくて"),
    (45, "ないで"),
    (45, "ませんで"),
    (45, "れば"),
    (45, "なければ"),
    (45, "られる"),
    (45, "れる"),
    (45, "られます"),
    (45, "れます"),
    (45, "られない"),
    (45, "れない"),
    (45, "られません"),
    (45, "れません"),
    (45, "られる"),
    (45, "られます"),
    (45, "られない"),
    (45, "られません"),
    (45, "させる"),
    (45, "さす"),
    (45, "させます"),
    (45, "さします"),
    (45, "させない"),
    (45, "ささない"),
    (45, "させません"),
    (45, "さしません"),
    (45, "させられる"),
    (45, "させられます"),
    (45, "させられない"),
    (45, "させられません"),
    (45, "よう"),
    (45, "ましょう"),
    (45, "まい"),
    (45, "ますまい"),
    (45, "い"),
    (45, "なさい"),
    (45, "るな"),
    (45, "なさるな"),
    (45, "たら"),
    (45, "ましたら"),
    (45, "なかったら"),
    (45, "ませんでしたら"),
    (45, "たり"),
    (45, "ましたり"),
    (45, "なかったり"),
    (45, "ませんでしたり"),
    (46, "する"),
    (47, "る", "す"),
    (47, "ます", "し"),
    (47, "ない", "さ"),
    (47, "ません", "し"),
    (47, "た", "し"),
    (47, "ました", "し"),
    (47, "なかった", "さ"),
    (47, "ませんでした", "し"),
    (47, "て", "し"),
    (47, "てた", "し"),
    (47, "まして", "し"),
    (47, "なくて", "さ"),
    (47, "ないで", "し"),
    (47, "ませんで", "し"),
    (47, "れば", "す"),
    (47, "ますなれば", "し"),
    (47, "なければ", "さ"),
    (47, "る", "え"),
    (47, "る", "う"),
    (47, "ます", "え"),
    (47, "ない", "え"),
    (47, "ません", "え"),
    (47, "れる", "さ"),
    (47, "れます", "さ"),
    (47, "れない", "さ"),
    (47, "れません", "さ"),
    (47, "せる", "さ"),
    (47, "す", "さ"),
    (47, "せます", "さ"),
    (47, "します", "さ"),
    (47, "せない", "さ"),
    (47, "さない", "さ"),
    (47, "せません", "さ"),
    (47, "しません", "さ"),
    (47, "せられる", "さ"),
    (47, "せられます", "さ"),
    (47, "せられない", "さ"),
    (47, "せられません", "さ"),
    (47, "よう", "し"),
    (47, "ましょう", "し"),
    (47, "るまい", "す"),
    (47, "ますまい", "し"),
    (47, "ろ", "し"),
    (47, "よ", "せ"),
    (47, "なさい", "し"),
    (47, "るな", "す"),
    (47, "なさるな", "し"),
    (47, "たら", "し"),
    (47, "ましたら", "し"),
    (47, "なかったら", "さ"),
    (47, "ませんでしたら", "し"),
    (47, "たり", "し"),
    (47, "ましたり", "し"),
    (47, "なかったり", "さ"),
    (47, "ませんでしたり", "し"),
    (47, "", "し"),
    (48, "る", "す"),
    (48, "ます", "し"),
    (48, "ない", "し"),
    (48, "ません", "し"),
    (48, "た", "し"),
    (48, "ました", "し"),
    (48, "なかった", "し"),
    (48, "ませんでした", "し"),
    (48, "て", "し"),
    (48, "てた", "し"),  # Added
    (48, "まして", "し"),
    (48, "なくて", "し"),
    (48, "ないで", "し"),
    (48, "ませんで", "し"),
    (48, "れば", "す"),
    (48, "ますなれば", "し"),
    (48, "なければ", "し"),
    (48, "る", "でき"),
    (48, "ます", "でき"),
    (48, "ない", "でき"),
    (48, "ません", "でき"),
    (48, "れる", "さ"),
    (48, "れます", "さ"),
    (48, "れない", "さ"),
    (48, "れません", "さ"),
    (48, "せる", "さ"),
    (48, "す", "さ"),
    (48, "せます", "さ"),
    (48, "します", "さ"),
    (48, "せない", "さ"),
    (48, "さない", "さ"),
    (48, "せません", "さ"),
    (48, "しません", "さ"),
    (48, "せられる", "さ"),
    (48, "せられます", "さ"),
    (48, "せられない", "さ"),
    (48, "せられません", "さ"),
    (48, "よう", "し"),
    (48, "ましょう", "し"),
    (48, "るまい", "す"),
    (48, "ますまい", "し"),
    (48, "ろ", "し"),
    (48, "よ", "せ"),
    (48, "なさい", "し"),
    (48, "るな", "す"),
    (48, "なさるな", "し"),
    (48, "たら", "し"),
    (48, "ましたら", "し"),
    (48, "なかったら", "し"),
    (48, "ませんでしたら", "し"),
    (48, "たり", "し"),
    (48, "ましたり", "し"),
    (48, "なかったり", "し"),
    (48, "ませんでしたり", "し"),
    (48, "", "し"),
]

# Create a dict all possible kana progressions in the list of okurigana by part of speech.
#
# This dictionary is used to determine if a kana text starts with okurigana.


# The result is a dictionary where on
# - the 1st level are 1st kana characters of an okurigana
# - the 2nd level are the 2nd kana characters of okurigana that
#   began with the 1st character (the key of 1st level)
# - the 3rd level are the 3rd kana characters of okurigana that
#   began with the 1st and 2nd characters (the keys of the previous levels)
# - and so on
# Ending in an empty dict which indicates the end of the okurigana.
POSSIBLE_OKURIGANA_PROGRESSION_DICT: dict[str, dict] = {}


# Populating POSSIBLE_OKURIGANA_PROGRESSION_DICT
def add_char_dict(kana_char, char_dict, is_last):
    if kana_char not in char_dict:
        char_dict[kana_char] = {}
    # Include a marker that this is one possible end of a okurigana
    if is_last is True:
        char_dict[kana_char]["is_last"] = True
    return char_dict[kana_char]


def add_chars_to_dict(kana_chars, char_dict):
    for i, kana in enumerate(kana_chars):
        is_last = i >= len(kana_chars) - 1
        char_dict = add_char_dict(kana, char_dict, is_last)


for item in ALL_OKURI_BY_PART_OF_SPEECH:
    if len(item) == 3:
        pos_num, okuri, euph = item
    else:
        pos_num, okuri = item
        euph = ""
    # Get part of speech string id
    # Get part of speech string id
    pos_id, pos_desc = PART_OF_SPEECH_NUM[pos_num]
    if pos_id not in POSSIBLE_OKURIGANA_PROGRESSION_DICT:
        POSSIBLE_OKURIGANA_PROGRESSION_DICT[pos_id] = {}
    # Recursively add each kana character of the okurigana to the dict
    add_chars_to_dict(okuri, POSSIBLE_OKURIGANA_PROGRESSION_DICT[pos_id])
    # Also add entry for blank okuri, which indicates no conjugation applied on the stem,
    # e.g. 恥ずかし気な
    add_char_dict("", POSSIBLE_OKURIGANA_PROGRESSION_DICT[pos_id], is_last=True)
    # If this okuri had a euphonic change entry, add the same progression for it too
    if euph:
        add_chars_to_dict(f"{euph}{okuri}", POSSIBLE_OKURIGANA_PROGRESSION_DICT[pos_id])
