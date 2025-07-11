import html
import uuid
from typing import TypedDict, Optional, Union, Literal, Sequence
from typing_extensions import TypeGuard

from aqt import mw

from .logic.kana_highlight import FuriReconstruct
from .logic.interpolate_fields import (
    intr_format,
    TARGET_NOTES_COUNT,
)
from .utils.logger import LogLevel

tag = mw.addonManager.addonFromModule(__name__)


def load_config():
    return mw.addonManager.getConfig(tag)


def save_config(data):
    mw.addonManager.writeConfig(tag, data)


# def run_on_configuration_change(function):
#     mw.addonManager.setConfigUpdatedAction(__name__, lambda *_: function())


KANJIUM_TO_JAVDEJONG_PROCESS = "Pitch accent conversion: Kanjium to Javdejong"


class KanjiumToJavdejongProcess(TypedDict):
    guid: str
    name: str
    delimiter: str


REGEX_PROCESS = "Regex replace"


class RegexProcess(TypedDict):
    guid: str
    name: str
    regex: str
    replacement: str
    # Separators used when interpolation uses multiple notes
    regex_separator: str
    replacement_separator: str
    flags: Optional[str]


def get_regex_process_label(regex_process):
    regex = regex_process["regex"]
    if len(regex) > 40:
        regex = regex[:20] + "..."
    return f"{REGEX_PROCESS}: <code>{html.escape(regex)}</code>"


FONTS_CHECK_PROCESS = "Fonts check"


class FontsCheckProcess(TypedDict):
    guid: str
    name: str
    fonts_dict_file: str
    limit_to_fonts: Optional[list[str]]
    character_limit_regex: Optional[str]


def get_fonts_check_process_label(fonts_check_process):
    fonts_limit = fonts_check_process.get("limit_to_fonts", None)
    if fonts_limit:
        fonts_limit = f", (limit {len(fonts_limit)} fonts)"
    else:
        fonts_limit = ""
    return f"{FONTS_CHECK_PROCESS}: {fonts_check_process['fonts_dict_file']}{fonts_limit}"


KANA_HIGHLIGHT_PROCESS = "Kana Highlight"


class KanaHighlightProcess(TypedDict):
    guid: str
    name: str
    kanji_field: str
    return_type: FuriReconstruct
    assume_dictionary_form: bool
    wrap_readings_in_tags: bool
    merge_consecutive_tags: bool
    onyomi_to_katakana: bool


AnyProcess = Union[KanjiumToJavdejongProcess, RegexProcess, FontsCheckProcess, KanaHighlightProcess]


def is_kana_highlight_process(process: Union[dict, AnyProcess]) -> TypeGuard[KanaHighlightProcess]:
    return process.get("name") == KANA_HIGHLIGHT_PROCESS


def is_regex_process(process: Union[dict, AnyProcess]) -> TypeGuard[RegexProcess]:
    return process.get("name") == REGEX_PROCESS


def is_fonts_check_process(process: Union[dict, AnyProcess]) -> TypeGuard[FontsCheckProcess]:
    return process.get("name") == FONTS_CHECK_PROCESS


def is_kanjium_to_javdejong_process(
    process: Union[dict, AnyProcess],
) -> TypeGuard[KanjiumToJavdejongProcess]:
    return process.get("name") == KANJIUM_TO_JAVDEJONG_PROCESS


ALL_FIELD_TO_FIELD_PROCESS_NAMES = [
    KANJIUM_TO_JAVDEJONG_PROCESS,
    REGEX_PROCESS,
    FONTS_CHECK_PROCESS,
    KANA_HIGHLIGHT_PROCESS,
]
ALL_FIELD_TO_VARIABLE_PROCESS_NAMES = [
    REGEX_PROCESS,
]

NEW_PROCESS_DEFAULTS: dict[str, AnyProcess] = {
    KANJIUM_TO_JAVDEJONG_PROCESS: KanjiumToJavdejongProcess(
        name=KANJIUM_TO_JAVDEJONG_PROCESS,
        delimiter="・",
    ),
    REGEX_PROCESS: RegexProcess(
        name=REGEX_PROCESS,
        regex="",
        replacement="",
        flags="",
    ),
    FONTS_CHECK_PROCESS: FontsCheckProcess(
        name=FONTS_CHECK_PROCESS,
        fonts_dict_file="",
        limit_to_fonts=[],
        character_limit_regex="",
    ),
    KANA_HIGHLIGHT_PROCESS: KanaHighlightProcess(
        name=KANA_HIGHLIGHT_PROCESS,
        kanji_field="",
        return_type="kana_only",
        wrap_readings_in_tags=True,
        merge_consecutive_tags=True,
        assume_dictionary_form=False,
    ),
}

MULTIPLE_ALLOWED_PROCESS_NAMES = [
    REGEX_PROCESS,
]


class CopyFieldToField(TypedDict):
    guid: str
    copy_into_note_field: str
    copy_from_text: str
    copy_if_empty: bool
    copy_on_unfocus_when_edit: bool
    copy_on_unfocus_when_add: bool
    copy_on_unfocus_trigger_field: str
    process_chain: Sequence[AnyProcess]


class CopyFieldToFile(TypedDict):
    guid: str
    copy_into_filename: str
    copy_from_text: str
    copy_if_empty: bool
    copy_on_unfocus_when_edit: bool
    copy_on_unfocus_when_add: bool
    copy_on_unfocus_trigger_field: str
    process_chain: Sequence[AnyProcess]


def get_field_to_field_unfocus_trigger_fields(
    field_to_field: CopyFieldToField, modifies_other_notes: bool
) -> list[str]:
    if modifies_other_notes:
        # source to destination mode is triggered by a field change in the trigger note
        # while the destination field is a different field in another note
        return field_to_field.get("copy_on_unfocus_trigger_field", "").strip('""').split('", "')
    else:
        # destination to sources mode or within note mode the destination and trigger fields
        # are in the same note
        return field_to_field.get("copy_on_unfocus_trigger_field", "").strip('""').split(
            '", "'
        ) or [field_to_field.get("copy_into_note_field", "")]


def get_triggered_field_to_field_def_for_field(
    field_to_field_defs: list[CopyFieldToField], field_name: str, modifies_other_notes: bool
) -> Union[CopyFieldToField, None]:
    """
    Get the field-to-field definition that matches the field_name and the mode.
    """
    for field_def in field_to_field_defs:
        trigger_fields = get_field_to_field_unfocus_trigger_fields(field_def, modifies_other_notes)
        if field_name in trigger_fields:
            return field_def
    return None


class CopyFieldToVariable(TypedDict):
    guid: str
    copy_into_variable: str
    copy_from_text: str
    process_chain: Sequence[AnyProcess]


CopyModeType = Literal["Within note", "Across notes"]
COPY_MODE_WITHIN_NOTE: CopyModeType = "Within note"
COPY_MODE_ACROSS_NOTES: CopyModeType = "Across notes"

DirectionType = Literal["Destination to sources", "Source to destinations"]
DIRECTION_DESTINATION_TO_SOURCES: DirectionType = "Destination to sources"
DIRECTION_SOURCE_TO_DESTINATIONS: DirectionType = "Source to destinations"

SELECT_CARD_BY_VALUES = ("None", "Random", "Least_reps")
SelectCardByType = Literal["None", "Random", "Least_reps"]


class CopyDefinition(TypedDict):
    guid: str
    definition_name: str
    copy_on_sync: bool
    copy_on_add: bool
    copy_on_review: bool
    copy_mode: CopyModeType
    copy_into_note_types: str
    across_mode_direction: Optional[DirectionType]
    field_to_field_defs: list[CopyFieldToField]
    field_to_file_defs: list[CopyFieldToFile]
    field_to_variable_defs: list[CopyFieldToVariable]
    only_copy_into_decks: str
    copy_from_cards_query: Optional[str]
    sort_by_field: Optional[str]
    select_card_by: SelectCardByType
    select_card_count: Optional[str]
    select_card_separator: Optional[str]


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings.
    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    v1_parts = list(map(int, version1.split(".")))
    v2_parts = list(map(int, version2.split(".")))

    # Pad the shorter list with zeros
    while len(v1_parts) < len(v2_parts):
        v1_parts.append(0)
    while len(v2_parts) < len(v1_parts):
        v2_parts.append(0)

    return (v1_parts > v2_parts) - (v1_parts < v2_parts)


def migrate_config():
    """
    Migrates old copy definitions to newer formats going through all
    version migrations.
    """
    config = Config()
    config.load()
    if compare_versions(config.version, "0.2.0") < 0:

        updated_definitions = []
        for definition in config.copy_definitions:
            if "guid" not in definition:
                definition["guid"] = str(uuid.uuid4())
            new_field_to_fields = []
            for field_to_field in definition.get("field_to_field_defs", []):
                if "guid" not in field_to_field:
                    field_to_field["guid"] = str(uuid.uuid4())
                new_processes = []
                for process in field_to_field.get("process_chain", []):
                    if "guid" not in process:
                        process["guid"] = str(uuid.uuid4())
                    new_processes.append(process)
                field_to_field["process_chain"] = new_processes
                new_field_to_fields.append(field_to_field)
            definition["field_to_field_defs"] = new_field_to_fields
            new_field_to_files = []
            for field_to_file in definition.get("field_to_file_defs", []):
                if "guid" not in field_to_file:
                    field_to_file["guid"] = str(uuid.uuid4())
                new_processes = []
                for process in field_to_file.get("process_chain", []):
                    if "guid" not in process:
                        process["guid"] = str(uuid.uuid4())
                    new_processes.append(process)
                field_to_file["process_chain"] = new_processes
                new_field_to_files.append(field_to_file)
            definition["field_to_file_defs"] = new_field_to_files
            new_field_to_variables = []
            for field_to_variable in definition.get("field_to_variable_defs", []):
                if "guid" not in field_to_variable:
                    field_to_variable["guid"] = str(uuid.uuid4())
                new_processes = []
                for process in field_to_variable.get("process_chain", []):
                    if "guid" not in process:
                        process["guid"] = str(uuid.uuid4())
                    new_processes.append(process)
                field_to_variable["process_chain"] = new_processes
                new_field_to_variables.append(field_to_variable)
            definition["field_to_variable_defs"] = new_field_to_variables
            updated_definitions.append(definition)
        config.data["copy_definitions"] = updated_definitions

    # Finished, set the version to latest
    config.data["version"] = "0.2.0"
    config.save()


def get_variables_dict_from_variable_defs(
    copy_mode: CopyModeType,
    variable_defs: Union[Sequence[CopyFieldToVariable], Sequence[str]],
) -> dict[str, str]:
    variable_menu_dict: dict[str, str] = {}
    # Always include the target notes count variable as it will be generated
    # in any across notes mode copy operation
    if copy_mode == COPY_MODE_ACROSS_NOTES:
        variable_menu_dict[TARGET_NOTES_COUNT] = intr_format(TARGET_NOTES_COUNT)
    for variable_def in variable_defs:
        if isinstance(variable_def, str):
            # If the variable definition is just a string, use it directly
            variable_name = variable_def
        else:
            # Otherwise, extract the variable name from the definition
            variable_name = variable_def["copy_into_variable"]
        if variable_name is not None:
            variable_menu_dict[variable_name] = intr_format(variable_name)
    return variable_menu_dict


def definition_modifies_trigger_note(
    copy_definition: CopyDefinition,
) -> bool:
    targets_trigger_note = (
        copy_definition.get("copy_mode", None) == COPY_MODE_WITHIN_NOTE
        or copy_definition.get("across_mode_direction", None) == DIRECTION_DESTINATION_TO_SOURCES
    )
    # definition might only save stuff to files
    has_field_to_field_defs = len(copy_definition.get("field_to_field_defs", [])) > 0
    return targets_trigger_note and has_field_to_field_defs


def definition_modifies_other_notes(
    copy_definition: CopyDefinition,
) -> bool:
    targets_other_notes = (
        copy_definition.get("copy_mode", None) == COPY_MODE_ACROSS_NOTES
        or copy_definition.get("across_mode_direction", None) == DIRECTION_SOURCE_TO_DESTINATIONS
    )
    # definition might only save stuff to files
    has_field_to_field_defs = len(copy_definition.get("field_to_field_defs", [])) > 0
    return targets_other_notes and has_field_to_field_defs


class Config:
    def load(self):
        self.data = load_config()

    def save(self):
        save_config(self.data)

    @property
    def version(self) -> str:
        return self.data.get("version", "0.1.0")

    @property
    def log_level(self) -> LogLevel:
        return self.data.get("log_level", "error")

    @property
    def copy_fields_shortcut(self):
        return self.data["copy_fields_shortcut"]

    @copy_fields_shortcut.setter
    def copy_fields_shortcut(self, value):
        self.data["copy_fields_shortcut"] = value
        self.save()

    @property
    def copy_definitions(self):
        return self.data["copy_definitions"] or []

    def get_definition_by_name(self, name) -> Union[CopyDefinition, None]:
        # find the definition in the list of definitions
        for definition in self.data["copy_definitions"]:
            if definition["definition_name"] == name:
                return definition
        return None

    def add_definition(self, definition: CopyDefinition):
        if "guid" not in definition:
            definition["guid"] = str(uuid.uuid4())
        self.data["copy_definitions"].append(definition)
        self.save()

    def remove_definition_by_name(self, name: str):
        definition = self.get_definition_by_name(name)
        if definition is None:
            return
        if definition:
            self.data["copy_definitions"].remove(definition)
            self.save()

    def remove_definition_by_index(self, index: int):
        self.data["copy_definitions"].pop(index)
        self.save()

    def remove_definition_by_guid(self, guid: str):
        for index, definition in enumerate(self.data["copy_definitions"]):
            if definition["guid"] == guid:
                self.remove_definition_by_index(index)
                return

    def update_definition_by_name(
        self, name: str, new_definition: CopyDefinition
    ) -> Union[int, None]:
        for index, definition in enumerate(self.data["copy_definitions"]):
            if definition["definition_name"] == name:
                self.update_definition_by_index(index, new_definition)
                return index
        return None

    def update_definition_by_index(self, index: int, definition: CopyDefinition):
        self.data["copy_definitions"][index] = definition
        self.save()

    def update_definition_by_guid(
        self, guid: str, new_definition: CopyDefinition
    ) -> Union[int, None]:
        for index, definition in enumerate(self.data["copy_definitions"]):
            if definition["guid"] == guid:
                self.update_definition_by_index(index, new_definition)
                return index
        return None
