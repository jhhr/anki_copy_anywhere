import re
from typing import Callable, Optional

# Name to use for detecting the process in the
# and also the GUI
REGEX_PROCESS = "Regex replace"


def regex_process(
        text: str,
        regex: str,
        replacement: str,
        flags: Optional[str],
        show_error_message: Callable[[str], None] = None
) -> str:
    """
     Basic regex processing step that replaces the text that matches the regex with the replacement.
     If no replacement is provided, instead only the match is returned.
    """
    if not show_error_message:
        def show_error_message(message: str):
            print(message)

    if regex is None or regex == "":
        show_error_message("Error in basic_regex_process: Missing 'regex'")
        return text

    if replacement is None:
        show_error_message("Error in basic_regex_process: Missing 'replacement'")
        return text

    if flags is None or flags == "":
        piped_flags = 0
    else:
        int_flags = [getattr(re, f) for f in flags.split(", ")]
        piped_flags = int_flags[0]
        # Combine rest of the flags with pipe
        for f in int_flags[1:]:
            piped_flags |= f

    regex = re.compile(regex, piped_flags)

    return regex.sub(replacement, text)
