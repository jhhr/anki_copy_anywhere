import pytest

from _anki_addon.logic.interpolate_fields import (
    extract_cloze_patterns,
    get_fields_from_text,
    interpolate_from_text,
)


class FakeNote:
    """Minimal dict-like note stub that satisfies to_lowercase_dict and get_from_note_fields."""

    def __init__(self, fields: dict):
        self._fields = fields

    # Always truthy so get_from_note_fields doesn't raise ValueError
    def __bool__(self) -> bool:
        return True

    def items(self):
        return self._fields.items()

    def keys(self):
        return self._fields.keys()

    def values(self):
        return self._fields.values()


class TestExtractClozePatterns:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("", []),
            ("plain text", []),
            # Simple cloze
            ("{{c1::word}}", [(0, 12, "1", "word")]),
            # Cloze with hint — hint separator is just part of the content
            ("{{c1::word::hint}}", [(0, 18, "1", "word::hint")]),
            # Multiple non-nested clozes
            ("{{c1::foo}} {{c2::bar}}", [(0, 11, "1", "foo"), (12, 23, "2", "bar")]),
            # Interpolation field inside cloze — {{ raises depth, not treated as close
            ("{{c1::{{FieldName}}}}", [(0, 21, "1", "{{FieldName}}")]),
            # Nested cloze — outer captures inner as content; inner not in result list
            ("{{c1::outer {{c2::inner}} text}}", [(0, 32, "1", "outer {{c2::inner}} text")]),
            # Malformed: no closing }} — skipped
            ("{{c1::unclosed", []),
            # Adjacent clozes
            ("{{c1::a}}{{c2::b}}", [(0, 9, "1", "a"), (9, 18, "2", "b")]),
            # Multi-digit cloze number
            ("{{c10::word}}", [(0, 13, "10", "word")]),
            # Cloze not at start of string
            ("prefix {{c1::word}}", [(7, 19, "1", "word")]),
        ],
    )
    def test_extract_cloze_patterns(self, text, expected):
        assert extract_cloze_patterns(text) == expected


class TestGetFieldsFromText:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("", []),
            ("plain text", []),
            # Plain interpolation field
            ("{{FieldName}}", ["FieldName"]),
            # Cloze is not treated as an interpolation field
            ("{{c1::word}}", []),
            # Field inside cloze content IS returned
            ("{{c1::{{FieldName}}}}", ["FieldName"]),
            # Field inside cloze + field outside cloze both returned
            ("{{c1::{{Field1}}}} {{Field2}}", ["Field1", "Field2"]),
            # Non-cloze field returned; cloze itself is not
            ("{{FieldName}} {{c1::cloze}}", ["FieldName"]),
            # Nested cloze with no fields
            ("{{c1::{{c2::word}}}}", []),
            # Field in cloze content before hint separator
            ("{{c1::{{Field1}}::hint}}", ["Field1"]),
            # Multiple plain fields
            ("{{Field1}} {{Field2}}", ["Field1", "Field2"]),
        ],
    )
    def test_get_fields_from_text(self, text, expected):
        assert get_fields_from_text(text) == expected


class TestInterpolateFromTextCloze:
    """Tests for interpolate_from_text focused on cloze notation handling."""

    @pytest.mark.parametrize(
        "text, note_fields, expected_text, expected_invalid",
        [
            # Plain text with no special syntax passes through
            ("plain text", {"F": "v"}, "plain text", []),
            # Cloze without any interpolation field passes through unchanged
            ("{{c1::word}}", {"F": "v"}, "{{c1::word}}", []),
            # Field outside cloze is substituted normally
            ("{{Word}}", {"Word": "hello"}, "hello", []),
            # Field inside cloze content is substituted
            ("{{c1::{{Word}}}}", {"Word": "hello"}, "{{c1::hello}}", []),
            # Cloze passes through while an adjacent field is substituted
            (
                "{{c1::word}} {{Field}}",
                {"Field": "value"},
                "{{c1::word}} value",
                [],
            ),
            # Field inside cloze AND field outside cloze both substituted
            (
                "{{c1::{{Word}}}} {{Other}}",
                {"Word": "hello", "Other": "world"},
                "{{c1::hello}} world",
                [],
            ),
            # Invalid field inside cloze is reported and cleared
            ("{{c1::{{BadField}}}}", {"F": "v"}, "{{c1::}}", ["badfield"]),
            # Cloze hint is preserved; field before the hint separator is substituted
            (
                "{{c1::{{Word}}::hint}}",
                {"Word": "hello"},
                "{{c1::hello::hint}}",
                [],
            ),
            # Multiple clozes, each containing their own field
            (
                "{{c1::{{Field1}}}} {{c2::{{Field2}}}}",
                {"Field1": "foo", "Field2": "bar"},
                "{{c1::foo}} {{c2::bar}}",
                [],
            ),
            # Surrounding text is preserved
            (
                "prefix {{c1::{{Word}}}} suffix",
                {"Word": "hello"},
                "prefix {{c1::hello}} suffix",
                [],
            ),
            # Invalid field outside cloze reported; valid field inside cloze substituted
            (
                "{{c1::{{Valid}}}} {{Invalid}}",
                {"Valid": "value"},
                "{{c1::value}} ",
                ["invalid"],
            ),
            # Field lookup is case-insensitive
            ("{{c1::{{WORD}}}}", {"Word": "hello"}, "{{c1::hello}}", []),
            # Nested cloze: field inside inner cloze is substituted; wrappers preserved
            (
                "{{c1::outer {{c2::{{Word}}}} end}}",
                {"Word": "hello"},
                "{{c1::outer {{c2::hello}} end}}",
                [],
            ),
        ],
    )
    def test_cloze_interpolation(self, text, note_fields, expected_text, expected_invalid):
        note = FakeNote(note_fields)
        result_text, result_invalid = interpolate_from_text(text, source_note=note)
        assert result_text == expected_text
        assert result_invalid == expected_invalid
