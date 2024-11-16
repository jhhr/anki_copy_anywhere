from typing import TypedDict, Optional, Union

# noinspection PyUnresolvedReferences
from aqt import mw

tag = mw.addonManager.addonFromModule(__name__)


def load_config():
    return mw.addonManager.getConfig(tag)


def save_config(data):
    mw.addonManager.writeConfig(tag, data)


def run_on_configuration_change(function):
    mw.addonManager.setConfigUpdatadAction(__name__, lambda *_: function())


KANJIUM_TO_JAVDEJONG_PROCESS = "Pitch accent conversion: Kanjium to Javdejong"


class KanjiumToJavdejongProcess(TypedDict):
    name: str
    delimiter: str


REGEX_PROCESS = "Regex replace"
class RegexProcess(TypedDict):
    name: str
    regex: str
    replacement: str
    flags: Optional[str]


FONTS_CHECK_PROCESS = "Fonts check"


class FontsCheckProcess(TypedDict):
    name: str
    fonts_dict_file: str
    limit_to_fonts: Optional[str]
    character_limit_regex: Optional[str]

KANA_HIGHLIGHT_PROCESS = "Kana Highlight"
class KanaHighlightProcess(TypedDict):
    name: str
    onyomi_field: str
    kunyomi_field: str
    kanji_field: str


ALL_PROCESS_NAMES = [
    KANJIUM_TO_JAVDEJONG_PROCESS,
    REGEX_PROCESS,
    FONTS_CHECK_PROCESS,
    KANA_HIGHLIGHT_PROCESS,
]

NEW_PROCESS_DEFAULTS = {
    KANJIUM_TO_JAVDEJONG_PROCESS: {
        "name": KANJIUM_TO_JAVDEJONG_PROCESS,
        "delimiter": "・",
    },
    REGEX_PROCESS: {
        "name": REGEX_PROCESS,
        "regex": "",
        "replacement": "",
        "flags": "",
    },
    FONTS_CHECK_PROCESS: {
        "name": FONTS_CHECK_PROCESS,
        "fonts_dict_file": "",
        "limit_to_fonts": "",
        "character_limit_regex": "",
    },
    KANA_HIGHLIGHT_PROCESS: {
        "name": KANA_HIGHLIGHT_PROCESS,
        "onyomi_field": "",
        "kunyomi_field": "",
        "kanji_field": "",
    },
}

MULTIPLE_ALLOWED_PROCESS_NAMES = [
    REGEX_PROCESS,
]

class CopyFieldToField(TypedDict):
    copy_into_note_field: str
    copy_from_text: str
    copy_if_empty: bool
    process_chain: list


COPY_MODE_WITHIN_NOTE = "Within note"
COPY_MODE_ACROSS_NOTES = "Across notes"

class CopyDefinition(TypedDict):
    definition_name: str
    copy_on_sync: bool
    copy_on_add: bool
    copy_mode: str
    copy_into_note_type: str
    field_to_field_defs: list[CopyFieldToField]
    only_copy_into_decks: str
    copy_from_cards_query: Optional[str]
    select_card_by: Optional[str]
    select_card_count: Optional[str]
    select_card_separator: Optional[str]


class Config:
    def load(self):
        self.data = load_config()

    def save(self):
        save_config(self.data)

    @property
    def days_to_cache_fields_menu(self):
        return self.data["days_to_cache_fields_menu"]

    @days_to_cache_fields_menu.setter
    def days_to_cache_fields_menu(self, value):
        self.data["days_to_cache_fields_menu"] = value
        self.save()

    @property
    def days_to_cache_fields_auto(self):
        return self.data["days_to_cache_fields_auto"]

    @days_to_cache_fields_auto.setter
    def days_to_cache_fields_auto(self, value):
        self.data["days_to_cache_fields_auto"] = value
        self.save()

    @property
    def cache_new_cards_count(self):
        return self.data["cache_new_cards_count"]

    @cache_new_cards_count.setter
    def cache_new_cards_count(self, value):
        self.data["cache_new_cards_count"] = value
        self.save()

    @property
    def copy_definitions(self):
        return self.data["copy_definitions"] or []

    def get_definition_by_name(self, name) -> dict:
        # find the definition in the list of definitions
        for definition in self.data["copy_definitions"]:
            if definition["definition_name"] == name:
                return definition

    def add_definition(self, definition: CopyDefinition):
        self.data["copy_definitions"].append(definition)
        self.save()

    def remove_definition_by_name(self, name: str):
        definition = self.get_definition_by_name(name)
        if definition:
            self.data["copy_definitions"].remove(definition)
            self.save()

    def remove_definition_by_index(self, index: int):
        self.data["copy_definitions"].pop(index)
        self.save()

    def update_definition_by_name(self, name: str, new_definition: dict) -> Union[int, None]:
        for index, definition in enumerate(self.data["copy_definitions"]):
            if definition["definition_name"] == name:
                self.update_definition_by_index(index, new_definition)
                return index
        return None

    def update_definition_by_index(self, index: int, definition: dict):
        self.data["copy_definitions"][index] = definition
        self.save()
