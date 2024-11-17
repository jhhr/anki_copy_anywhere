import json
import re
from pathlib import Path
from typing import Callable, Optional

# noinspection PyUnresolvedReferences
from aqt import mw


def fonts_check_process(
        text: str,
        fonts_dict_file: str,
        limit_to_fonts: Optional[list[str]],
        character_limit_regex: Optional[str],
        show_error_message: Callable[[str], None] = None,
        file_cache: dict = None
) -> str:
    """
     Go through all the characters in the text and return the fonts that all have an entry in the fonts_dict_file.
     The fonts_dict_file should be a json file of the form {char: [font1, font2, ...], ...}. Additionally it should
     contain a list of all the fonts that are used in the collection in the key "all_fonts".

     :param text: The text to check
     :param fonts_dict_file: The path to the json file with the fonts dictionary
     :param limit_to_fonts: A list of font file names to limit the output to
     :param character_limit_regex: A regex to limit the characters to check
     :param show_error_message: A function that takes a string and shows an error message
     :param file_cache: A dictionary to cache the open JSON file contents, to avoid opening the file multiple times

     :return A string that can be parsed as an array of strings, e.g. '["font1", "font2", ...]'
    """

    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    if fonts_dict_file is None or fonts_dict_file == "":
        show_error_message("Error in fonts_check_process: Missing 'fonts_dict_file'")
        return ""

    char_regex = None
    if character_limit_regex is not None and character_limit_regex != "":
        char_regex = re.compile(character_limit_regex)

    # try to get the fonts_dict from the cache
    if file_cache is not None:
        fonts_dict = file_cache.get(fonts_dict_file, None)
    else:
        fonts_dict = None

    # if we didn't get the dict from cache, read the file
    if fonts_dict is None:
        media_path = Path(mw.pm.profileFolder(), 'collection.media')

        fonts_dict_file_full = media_path / fonts_dict_file
        if not fonts_dict_file_full.is_file():
            show_error_message(f"Error in fonts_check_process: File '{fonts_dict_file_full}' does not exist")
            return ""

        with open(fonts_dict_file_full, "r", encoding='utf-8') as f:
            file_content = f.read().strip()
            if not file_content:
                show_error_message(f"Error in fonts_check_process: File '{fonts_dict_file_full}' is empty")
                return ""

            try:
                fonts_dict = json.loads(file_content)
                # cache the dict
                if file_cache is not None:
                    file_cache[fonts_dict_file] = fonts_dict
            except json.JSONDecodeError as e:
                show_error_message(
                    f"Error in fonts_check_process: Invalid JSON content, check what your file contains: '{fonts_dict_file_full}' - {e}")
                return ""

    if text is None or text == "":
        show_error_message("Text was empty")
        return ""

    encountered_fonts = set()
    valid_fonts = set()
    some_chars_found = False
    all_chars_excluded_by_regex = None

    for char in text:
        if char_regex is not None:
            if not char_regex.fullmatch(char):
                all_chars_excluded_by_regex = True
                continue
            all_chars_excluded_by_regex = False

        char_fonts = fonts_dict.get(char, None)
        if char_fonts:
            some_chars_found = True
            encountered_fonts.update(char_fonts)
            # loop through encountered_fonts and set all char_fonts that are in it to True in valid_fonts, else False
            for font in encountered_fonts:
                if font in char_fonts:
                    valid_fonts.add(font)
                else:
                    valid_fonts.discard(font)

        if limit_to_fonts is not None:
            valid_fonts = valid_fonts.intersection(limit_to_fonts)

    join_str = "\", \""

    if not some_chars_found:
        if all_chars_excluded_by_regex:
            show_error_message(f"{text} - All characters excluded by regex")
        else:
            show_error_message(
                f"{text} - No characters had a match in the fonts dictionary, check that your dictionary has entries for the expected characters")
            return ""

        # All characters were excluded by the regex, so we assume they are all ok to be displayed by all the fonts
        if limit_to_fonts is not None:
            return f'["{join_str.join(limit_to_fonts)}"]'

        # If we didn't have limit_to_fonts, try to return the all_fonts key from the fonts_dict
        all_fonts = fonts_dict.get("all_fonts", None)
        if all_fonts is not None:
            return f'["{join_str.join(all_fonts)}"]'

        show_error_message(f"Dictionary '{fonts_dict_file}' does not contain an 'all_fonts' key")
        return ""

    if len(valid_fonts) == 0:
        show_error_message(f"{text} - Some characters had valid fonts but no fonts were valid for every character")
        return ""

    return f'["{join_str.join(valid_fonts)}"]'
