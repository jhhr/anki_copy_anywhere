import sys

try:
    from ...utils.logger import Logger
except ImportError:
    from utils.logger import Logger  # type: ignore[no-redef]

JPN_NUMBER_TO_NUM = {
    "１": 1,
    "２": 2,
    "３": 3,
    "４": 4,
    "５": 5,
    "６": 6,
    "７": 7,
    "８": 8,
    "９": 9,
    "０": 0,
}


KANJI_NUMERALS = {
    0: "零",
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "七",
    8: "八",
    9: "九",
}

KANJI_UNITS = {
    1: "",
    10: "十",
    100: "百",
    1000: "千",
    10000: "万",
    # 億 is 万 number of 万
    100000000: "億",
    # 兆 is 万 number of 億
    1000000000000: "兆",
    # 京 is 万 number of 兆 etc.
    10000000000000000: "京",
}

NUMBER_TO_KANJI = {}
for num, kanji in KANJI_NUMERALS.items():
    NUMBER_TO_KANJI[str(num)] = kanji
for jpn_num, num in JPN_NUMBER_TO_NUM.items():
    NUMBER_TO_KANJI[jpn_num] = KANJI_NUMERALS[num]


def recursive_number_to_kanji(
    num: int, result: list[str], digit_mult=1, logger: Logger = Logger("error")
) -> None:
    """
    Recursively converts a number to its kanji representation.
    Args:
        num (int): The number to convert.
        result (list[str]): The list to append the kanji representation to.
    """
    logger.debug(f"Converting number: {num}, digit_mult: {digit_mult}")
    unit = 1
    # how many 十, 百, 千, 万, 億 we have
    while num > 0:
        digit = num % 10
        logger.debug(f"Processing digit: {digit}, unit: {unit}")
        if digit > 0:
            try:
                kanji_digit = NUMBER_TO_KANJI[str(digit)]
            except KeyError:
                logger.error(f"Digit {digit} not found in NUMBER_TO_KANJI mapping.")
                return
            if unit in KANJI_UNITS:
                logger.debug(f"Adding kanji digit {kanji_digit} with unit {KANJI_UNITS[unit]}")
                # if the digit_mult is 1, we just use the kanji digit
                if digit_mult > 1:
                    # If the digit is not 1, we add the kanji digit with the unit
                    if digit == 1 and digit_mult in KANJI_UNITS:
                        kanji_digit = KANJI_UNITS[digit_mult]
                    elif digit_mult in KANJI_UNITS:
                        kanji_digit += KANJI_UNITS[digit_mult]
                partial_num = kanji_digit
                cur_unit = KANJI_UNITS[unit]
                # If previous units is the same, omit it from this append
                max_further_index = len(result) - 1
                if cur_unit == "万":
                    max_further_index = len(result) - 3
                if cur_unit == "億":
                    max_further_index -= 4
                if cur_unit == "兆":
                    max_further_index -= 7
                if cur_unit == "京":
                    max_further_index -= 11
                further_index = len(result) - 1
                found_same_unit = False
                while (
                    further_index >= 0
                    and further_index >= max_further_index
                    and not found_same_unit
                ):
                    if result[further_index].endswith(cur_unit):
                        found_same_unit = True
                    further_index -= 1

                logger.debug(
                    f"Cur unit: {cur_unit}, Found same unit: {found_same_unit}, further_index:"
                    f" {further_index}, max_further_index: {max_further_index}"
                )
                if not found_same_unit:
                    partial_num += cur_unit
                result.append(partial_num)
                logger.debug(f"Appended {partial_num} to result, current result: {result}")
            else:
                # The unit is a multiple of another smaller unit, start from 10
                logger.debug(f"Recursive call for unit {unit}, digit {digit}")
                sub_num = digit * unit // 10
                logger.debug(f"Recursively processing number {sub_num}")
                recursive_number_to_kanji(sub_num, result, digit_mult * 10, logger)

        num //= 10
        unit *= 10


def number_to_kanji(num_str: str, logger: Logger = Logger("error")) -> str:
    """
    Converts a string representation of a number into its kanji representation.

    Args:
        num_str (str): The string representation of the number to convert.

    Returns:
        str: The kanji representation of the number.
    """

    # Normalize the input string to handle full-width characters
    clean_num_str = num_str.strip()
    clean_num_str = "".join(str(JPN_NUMBER_TO_NUM.get(char, char)) for char in num_str)

    if not clean_num_str.isdigit():
        logger.debug(f"Input string '{num_str}' is not a valid number.")
        # If the string contains non-digit characters, return it as is
        return num_str

    num = int(clean_num_str)

    if num in KANJI_NUMERALS:
        return KANJI_NUMERALS[num]

    result = []

    recursive_number_to_kanji(num, result, digit_mult=1, logger=logger)

    # Reverse the result to get the correct order
    result.reverse()
    kanji_result = "".join(result)
    # Remove leading ones in front of 十, 百, 千, 万, 億
    for unit_kanji in KANJI_UNITS.values():
        if unit_kanji and unit_kanji in kanji_result:
            logger.debug(f"Removing leading '一' before {unit_kanji}")
            kanji_result = kanji_result.replace("一" + unit_kanji, unit_kanji)

    return kanji_result


# test cases
if __name__ == "__main__":
    test_cases = [
        # non-parseable cases return as is
        ("", ""),
        (" ", " "),
        ("abc", "abc"),
        ("123abc", "123abc"),
        ("１２３あえいおう", "１２３あえいおう"),
        ("123-456", "123-456"),
        # Already in kanji, basically same as non-parseable cases
        ("億", "億"),
        ("零", "零"),
        ("万", "万"),
        ("一十", "一十"),
        ("二", "二"),
        ("三十", "三十"),
        ("四", "四"),
        ("五", "五"),
        ("六千", "六千"),
        ("七", "七"),
        ("八", "八"),
        ("九", "九"),
        ("十", "十"),
        ("３百", "３百"),
        ("千", "千"),
        ("0", "零"),
        ("０", "零"),
        ("1", "一"),
        ("１", "一"),
        ("2", "二"),
        ("２", "二"),
        ("3", "三"),
        ("３", "三"),
        ("4", "四"),
        ("４", "四"),
        ("5", "五"),
        ("５", "五"),
        ("6", "六"),
        ("６", "六"),
        ("7", "七"),
        ("７", "七"),
        ("8", "八"),
        ("８", "八"),
        ("9", "九"),
        ("９", "九"),
        ("10", "十"),
        ("１０", "十"),
        ("11", "十一"),
        ("１１", "十一"),
        ("20", "二十"),
        ("２０", "二十"),
        ("21", "二十一"),
        ("２１", "二十一"),
        ("30", "三十"),
        ("３０", "三十"),
        ("100", "百"),
        ("１００", "百"),
        ("123", "百二十三"),
        ("１２３", "百二十三"),
        ("4567", "四千五百六十七"),
        ("４５６７", "四千五百六十七"),
        ("89012", "八万九千十二"),
        ("８９０１２", "八万九千十二"),
        ("1000000", "百万"),
        ("１００００００", "百万"),
        ("100000000", "億"),
        ("１００００００００", "億"),
        ("1234000000", "十二億三千四百万"),
        ("１２３４００００００", "十二億三千四百万"),
        ("1234567890", "十二億三千四百五十六万七千八百九十"),
        ("１２３４５６７８９０", "十二億三千四百五十六万七千八百九十"),
        ("10000400000060000003", "千京四百兆六千万三"),
        ("１００００４００００００６００００００３", "千京四百兆六千万三"),
        ("一二三四五六七八九", "一二三四五六七八九"),
    ]

    for input, expected in test_cases:
        result = number_to_kanji(input)
        try:
            assert result == expected
        except AssertionError:
            # Re-run with logging enabled to see what went wrong
            print("\n")
            logger = Logger("debug")
            result = number_to_kanji(input, logger=logger)
            print(f"""\033[91mTest failed
\033[93mInput: {input}
\033[92mExpected: {expected}
\033[93mGot:      {result}
\033[0m""")
            # Stop testing here
            sys.exit(0)
    print("\n\033[92mTests passed\033[0m")
