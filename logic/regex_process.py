import re
from typing import Callable, Optional


def regex_process(
    text: str,
    regex: Optional[str],
    replacement: Optional[str],
    flags: Optional[str],
    show_error_message: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Basic regex processing step that replaces the text that matches the regex with the replacement.
    If no replacement is provided, instead only the match is returned.
    """
    if not show_error_message:

        def show_error_message(message: str):
            print(message)

    if not regex:
        show_error_message("Error in basic_regex_process: Missing 'regex'")
        return text

    if replacement is None:
        # Replace can be "" but not None
        show_error_message("Error in basic_regex_process: Missing 'replacement'")
        return text

    if not flags:
        piped_flags = 0
    else:
        int_flags = [getattr(re, f) for f in flags.split(", ")]
        piped_flags = int_flags[0]
        # Combine rest of the flags with pipe
        for f in int_flags[1:]:
            piped_flags |= f

    compiled_regex = re.compile(regex, piped_flags)

    return compiled_regex.sub(replacement, text)


def test(
    test_name: str,
    text: str,
    regex: str,
    replacement: str,
    flags: Optional[str],
    expected: str,
):
    result = regex_process(text, regex, replacement, flags, None)
    try:
        assert result == expected
    except AssertionError:
        print(f"""{test_name}
Expected: {expected}
Got: {result}
""")
        raise


def main():
    test(
        test_name="Replacement with groups",
        text="<i>abc123</i>def456<i>ghi789</i>",
        regex=r"<i>(.*)</i>",
        replacement=r"\1",
        flags=None,
        expected="abc123def456",
    )
    print("Ok.")


if __name__ == "__main__":
    main()
