from typing import Optional, Callable
from .multi_combo_box import MultiComboBox
from .required_text_input import RequiredLineEdit


from anki.decks import DeckDict, DeckId
from anki.models import NotetypeDict
from anki.utils import ids2str
from aqt import mw
from aqt.qt import QCheckBox, QLabel

from ..logic.interpolate_fields import (
    BASE_NOTE_MENU_DICT,
    DESTINATION_PREFIX,
    VARIABLES_KEY,
    DESTINATION_NOTE_MENU_DICT,
)
from .interpolated_text_edit import make_validate_dict

from ..configuration import (
    COPY_MODE_WITHIN_NOTE,
    COPY_MODE_ACROSS_NOTES,
    CopyDefinition,
    DirectionType,
    CopyModeType,
    DIRECTION_DESTINATION_TO_SOURCES,
    get_variables_dict_from_variable_defs,
)

from .add_model_options_to_dict import add_model_options_to_dict
from .add_intersecting_model_field_options_to_dict import (
    add_intersecting_model_field_options_to_dict,
    get_intersecting_model_fields,
)


def get_new_base_dict(copy_mode: CopyModeType) -> dict:
    if copy_mode == COPY_MODE_WITHIN_NOTE:
        return DESTINATION_NOTE_MENU_DICT.copy()
    return DESTINATION_NOTE_MENU_DICT | BASE_NOTE_MENU_DICT


class EditState:
    """
    Class to hold the shared state of the editors
    """

    def __init__(
        self,
        copy_definition: Optional[CopyDefinition] = None,
        copy_mode: CopyModeType = COPY_MODE_WITHIN_NOTE,
    ):
        self.copy_mode = copy_mode
        self.definition_name = ""
        self.copy_into_note_types: str = ""
        self.selected_models: list[NotetypeDict] = []
        self.only_copy_into_decks: str = ""
        self.all_decks: list[DeckDict] = []
        self.current_deck_names: list[str] = []
        self.current_decks: list[NotetypeDict] = []
        self.current_decks_in_all_decks: list[DeckDict] = []
        self.copy_on_sync: bool = False
        self.copy_on_add: bool = False
        self.copy_on_review: bool = False
        self.copy_mode: CopyModeType = COPY_MODE_WITHIN_NOTE
        self.copy_direction: DirectionType = DIRECTION_DESTINATION_TO_SOURCES
        if copy_definition is not None:
            self.copy_mode = copy_definition.get("copy_mode", COPY_MODE_WITHIN_NOTE)
            self.definition_name = copy_definition.get("definition_name", "")
            self.copy_into_note_types = copy_definition.get("copy_into_note_types", "")
            self.only_copy_into_decks = copy_definition.get("only_copy_into_decks", "")
            self.copy_on_sync = copy_definition.get("copy_on_sync", False)
            self.copy_on_add = copy_definition.get("copy_on_add", False)
            self.copy_on_review = copy_definition.get("copy_on_review", False)
            if copy_definition.get("copy_mode") == COPY_MODE_ACROSS_NOTES:
                self.copy_direction = (
                    copy_definition.get("across_mode_direction") or DIRECTION_DESTINATION_TO_SOURCES
                )
        self.selected_model_callbacks: list[Callable[[list[NotetypeDict]], None]] = []
        self.copy_direction_callbacks: list[Callable[[DirectionType], None]] = []
        self.variable_names_callbacks: list[Callable[[list[str]], None]] = []

        self.pre_query_menu_options_dict: dict = BASE_NOTE_MENU_DICT.copy()
        self.post_query_menu_options_dict: dict = get_new_base_dict(self.copy_mode)
        self.post_query_text_edit_validate_dict: dict[str, bool] = {}
        self.pre_query_text_edit_validate_dict: dict[str, bool] = {}
        self.copy_into_variables: list[str] = [
            f["copy_into_variable"]
            for f in (copy_definition.get("field_to_variable_defs", []) if copy_definition else [])
        ]
        self.variables_dict: list[str] = get_variables_dict_from_variable_defs(
            self.copy_mode,
            self.copy_into_variables,
        )
        self.variables_validate_dict: dict[str, bool] = make_validate_dict(self.variables_dict)
        self.intersecting_fields: list[str] = get_intersecting_model_fields(self.selected_models)
        self.update_models()

        self.definition_name_editors: list[RequiredLineEdit] = []
        self.target_note_type_editors: list[MultiComboBox] = []
        self.target_note_type_callbacks: list[Callable[[QLabel], None]] = []
        self.only_copy_into_decks_editors: list[MultiComboBox] = []
        self.copy_on_sync_editors: list[QCheckBox] = []
        self.copy_on_add_editors: list[QCheckBox] = []
        self.copy_on_review_editors: list[QCheckBox] = []

        self.connect_definition_name_editor = self._make_connect_required_line_edit(
            self.definition_name_editors,
            "definition_name",
        )
        self.connect_target_note_type_editor = self._make_connect_multi_combobox_editor(
            self.target_note_type_editors,
            "copy_into_note_types",
            self.target_note_type_callbacks,
            self.update_models,
        )
        self.connect_only_copy_into_decks_editor = self._make_connect_multi_combobox_editor(
            self.only_copy_into_decks_editors,
            "only_copy_into_decks",
            self.target_note_type_callbacks,
            self.update_decks,
        )
        self.connect_copy_on_sync_checkbox = self._make_connect_checkbox_editor(
            self.copy_on_sync_editors,
            "copy_on_sync",
        )
        self.connect_copy_on_add_checkbox = self._make_connect_checkbox_editor(
            self.copy_on_add_editors,
            "copy_on_add",
        )
        self.connect_copy_on_review_checkbox = self._make_connect_checkbox_editor(
            self.copy_on_review_editors,
            "copy_on_review",
        )

    def _make_connect_required_line_edit(
        self,
        editors_list: list[RequiredLineEdit],
        state_attr: str,
        editor_callbacks: Optional[list[Callable[[None], None]]] = None,
    ):
        """
        Makes a function that connects a RequiredLineEdit editor to the state.
        It updates the state and calls the update function for all other editors.
        """

        def update_other_editors(triggering_editor: RequiredLineEdit):
            for editor in editors_list:
                if editor is triggering_editor:
                    continue
                editor.setText(getattr(self, state_attr))
                editor.update_required_style()

        def connect_func(
            line_edit: RequiredLineEdit,
            callback: Optional[Callable[[None], None]] = None,
        ):
            editors_list.append(line_edit)
            if editor_callbacks is not None:
                editor_callbacks.append(callback) if callback else None

            def update_state(text: str):
                setattr(self, state_attr, text.strip())
                update_other_editors(line_edit)
                if editor_callbacks:
                    for callback in editor_callbacks:
                        callback()

            line_edit.textChanged.connect(update_state)

        return connect_func

    def _make_connect_multi_combobox_editor(
        self,
        editors_list: list[MultiComboBox],
        state_attr: str,
        editor_callbacks: Optional[list[Callable[[MultiComboBox], None]]] = None,
        state_attr_callback: Optional[Callable[[None], None]] = None,
    ):
        """
        Makes a function that connects a MultiComboBox editor to the state.
        It updates the state and calls the update function for all other editors.
        """

        def update_other_editors(triggering_editor: MultiComboBox):
            for editor in editors_list:
                if editor is triggering_editor:
                    continue
                editor.setCurrentText(getattr(self, state_attr))
                editor.update_required_style()

        def connect_func(
            combobox: MultiComboBox,
            callback: Optional[Callable[[MultiComboBox], None]] = None,
        ):
            editors_list.append(combobox)
            if editor_callbacks is not None:
                editor_callbacks.append(callback) if callback else None

            def update_state(text: str):
                setattr(self, state_attr, text.strip())
                update_other_editors(combobox)
                if editor_callbacks:
                    for callback in editor_callbacks:
                        callback(combobox)
                if state_attr_callback:
                    state_attr_callback()

            combobox.currentTextChanged.connect(update_state)

        return connect_func

    def _make_connect_checkbox_editor(
        self,
        checkbox_editors: list[QCheckBox],
        state_attr: str,
        editor_callbacks: Optional[list[Callable[[QCheckBox], None]]] = None,
    ):
        """
        Makes a function that connects a QCheckBox editor to the state.
        It updates the state and calls the update function for all other editors.
        """

        def update_other_editors(triggering_editor: QCheckBox):
            for editor in checkbox_editors:
                if editor is triggering_editor:
                    continue
                editor.setChecked(self.copy_on_sync)

        def connect_func(
            checkbox: QCheckBox, callback: Optional[Callable[[QCheckBox], None]] = None
        ):
            checkbox_editors.append(checkbox)
            if editor_callbacks is not None:
                editor_callbacks.append(callback) if callback else None

            def update_state(checked: bool):
                setattr(self, state_attr, checked)
                update_other_editors(checkbox)
                if editor_callbacks:
                    for callback in editor_callbacks:
                        callback(checkbox)

            checkbox.toggled.connect(update_state)

        return connect_func

    def update_models(self):
        """
        Updates the selected models in the state.
        """
        models = list(
            filter(
                None,
                [
                    mw.col.models.by_name(name.strip('""'))
                    for name in self.copy_into_note_types.split(",")
                ],
            )
        )
        self.selected_models = models
        self.update_post_query_copy_from_options_dict()
        self.update_pre_query_copy_from_options_dict()
        self.update_decks()
        for callback in self.selected_model_callbacks:
            callback(self.selected_models)

    def add_selected_model_callback(self, callback: Callable[[list[NotetypeDict]], None]):
        """
        Adds a callback to be called when the selected models change.
        The callback will receive the list of selected models.
        """
        self.selected_model_callbacks.append(callback)

    def add_copy_direction_callback(self, callback: Callable[[DirectionType], None]):
        """
        Adds a callback to be called when the copy direction changes.
        The callback will receive the current copy direction.
        """
        self.copy_direction_callbacks.append(callback)

    def update_copy_direction(self, new_direction: DirectionType):
        """
        Updates the copy direction in the state and calls all registered callbacks.
        """
        if new_direction != self.copy_direction:
            self.copy_direction = new_direction
            for callback in self.copy_direction_callbacks:
                callback(self.copy_direction)
            self.update_post_query_copy_from_options_dict()

    def update_decks(self):
        assert mw.col.db is not None
        mids: list[int] = [model["id"] for model in self.selected_models]
        dids: list[DeckId] = mw.col.db.list(f"""
                SELECT DISTINCT CASE WHEN odid==0 THEN did ELSE odid END
                FROM cards c, notes n
                WHERE n.mid IN {ids2str(mids)}
                AND c.nid = n.id
            """)

        current_deck_names = self.only_copy_into_decks.strip('""').split('", "')
        all_decks = [mw.col.decks.get(did) for did in dids]
        all_decks = [d for d in all_decks if d is not None]
        current_decks_in_all_decks = [d for d in all_decks if d["name"] in current_deck_names]
        self.all_decks = all_decks
        self.current_deck_names = current_deck_names
        self.current_decks = list(
            filter(
                None,
                [mw.col.models.by_name(model_name) for model_name in current_deck_names],
            )
        )
        self.current_decks_in_all_decks = current_decks_in_all_decks

    def update_post_query_copy_from_options_dict(self):
        """
        Updates the raw options dict used for the "Define what to copy from" TextEdit right-click
        menu. The raw dict is used for validating the text in the TextEdit.
        The data available is the trigger note and targeted noted in Across Notes mode
        and only the trigger note in Within Note mode.
        """
        options_dict = get_new_base_dict(self.copy_mode)
        # Copy previously defined variables
        prev_variables_dict = self.post_query_menu_options_dict.get(VARIABLES_KEY, {})
        if prev_variables_dict:
            options_dict[VARIABLES_KEY] = prev_variables_dict

        trigger_model_names = [model["name"] for model in self.selected_models]

        if self.copy_mode == COPY_MODE_WITHIN_NOTE:
            # If there are multiple models, add the intersecting fields only
            if len(self.selected_models) > 1:
                self.intersecting_fields = get_intersecting_model_fields(self.selected_models)
                add_intersecting_model_field_options_to_dict(
                    models=self.selected_models,
                    target_dict=options_dict,
                    intersecting_fields=self.intersecting_fields,
                )
            elif len(self.selected_models) == 1:
                # Otherwise only add the single model as the target
                model = self.selected_models[0]
                add_model_options_to_dict(model["name"], model["id"], options_dict)
        else:
            # In across notes modes, add fields from all models
            models = mw.col.models.all_names_and_ids()
            if self.copy_direction == DIRECTION_DESTINATION_TO_SOURCES:
                # One destination model, many source models
                for model in models:
                    # Only the trigger note models are potential destinations
                    # The destination note will get added twice, as a source and as a destination
                    if model.name in trigger_model_names:
                        add_model_options_to_dict(
                            f"(Destination) {model.name}",
                            model.id,
                            options_dict,
                            DESTINATION_PREFIX,
                        )
                    # But every model is a potential source
                    add_model_options_to_dict(model.name, model.id, options_dict)
            else:
                # Many destination models, one source model
                for model in models:
                    # Every model is a potential destination
                    add_model_options_to_dict(
                        f"(Destination) {model.name}",
                        model.id,
                        options_dict,
                        DESTINATION_PREFIX,
                    )
                    # Only the trigger note models are potential sources
                    # The source note will get added twice, as a source and once as a destination
                    if model.name in trigger_model_names:
                        add_model_options_to_dict(model.name, model.id, options_dict)

        self.post_query_menu_options_dict = options_dict

        self.post_query_text_edit_validate_dict = make_validate_dict(options_dict)

    def update_variable_names(self, copy_into_variables: list[str]):
        self.copy_into_variables = copy_into_variables
        variables_dict = get_variables_dict_from_variable_defs(
            copy_mode=self.copy_mode,
            variable_defs=copy_into_variables,
        )
        self.variables_dict = variables_dict
        self.variables_validate_dict = make_validate_dict(variables_dict)
        if variables_dict:
            self.post_query_menu_options_dict[VARIABLES_KEY] = variables_dict
        else:
            # If there are no variables, remove the key from the dict
            self.post_query_menu_options_dict.pop(VARIABLES_KEY, None)
        self.post_query_text_edit_validate_dict = make_validate_dict(
            self.post_query_menu_options_dict
        )
        for callback in self.variable_names_callbacks:
            callback(self.copy_into_variables)

    def update_pre_query_copy_from_options_dict(self):
        """
        Updates the raw options dict used for the any InterpolatedTextEditLayout right-click
        menu used before a note query in Across Notes mode or when with the trigger note
        in Within Note mode. The raw dict is used for validating the text in the TextEdit.
        """
        field_names_by_model_dict = BASE_NOTE_MENU_DICT.copy()

        prev_variables_dict = self.pre_query_menu_options_dict.get(VARIABLES_KEY, {})
        if prev_variables_dict:
            field_names_by_model_dict[VARIABLES_KEY] = prev_variables_dict

        if len(self.selected_models) > 1:
            # If there are multiple models, add the intersecting fields only
            self.intersecting_fields = get_intersecting_model_fields(self.selected_models)
            add_intersecting_model_field_options_to_dict(
                models=self.selected_models,
                target_dict=field_names_by_model_dict,
                intersecting_fields=self.intersecting_fields,
            )
        elif len(self.selected_models) == 1:
            model = self.selected_models[0]
            add_model_options_to_dict(
                model_name=model["name"],
                model_id=model["id"],
                target_dict=field_names_by_model_dict,
            )

        self.pre_query_menu_options_dict = field_names_by_model_dict

        self.pre_query_text_edit_validate_dict = make_validate_dict(field_names_by_model_dict)
