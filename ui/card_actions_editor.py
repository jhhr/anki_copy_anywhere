import html
from typing import Optional, Dict
import uuid

from aqt import mw
from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QComboBox,
    QButtonGroup,
    QRadioButton,
    QDoubleSpinBox,
    QLineEdit,
    qtmajor,
)

if qtmajor > 5:
    QFrameStyledPanel = QFrame.Shape.StyledPanel
    QFrameShadowRaised = QFrame.Shadow.Raised
else:
    QFrameStyledPanel = QFrame.StyledPanel  # type: ignore
    QFrameShadowRaised = QFrame.Raised  # type: ignore

from ..configuration import (
    CARD_TYPE_SEPARATOR,
    COPY_MODE_ACROSS_NOTES,
    DIRECTION_SOURCE_TO_DESTINATIONS,
    CardAction,
    CopyDefinition,
)
from .code_edit_layout import CodeEditLayout, CARD_ACTION_CODE_NOTICE
from .edit_state import EditState
from .grouped_combo_box import GroupedComboBox
from .toggle_switch import ToggleSwitch

base_description = """<p>Configure actions to perform on any destination note's card types.
            Select a card type from the dropdown to configure its action.</p>"""

source_to_destinations_description = (
    "<p><small>Note: Card actions are performed on the queried notes' cards.</small></p>"
)
destination_to_sources_description = (
    "<p><small>Note: Card actions are performed on the trigger note's cards.</small></p>"
)


def _card_action_to_initial_code(
    change_deck=None,
    set_flag=None,
    suspend=None,
    bury=None,
    set_desired_retention=None,
) -> str:
    """Generate initial Python code that returns a CardActionDict from the given form values.

    Produces a ``return { ... }`` block pre-populated with the current form
    values so the user has a ready-made starting point when switching to code
    mode.
    """
    return (
        "return {\n"
        f'    "change_deck": {change_deck!r},\n'
        f'    "set_flag": {set_flag!r},\n'
        f'    "suspend": {suspend!r},\n'
        f'    "bury": {bury!r},\n'
        f'    "set_desired_retention": {set_desired_retention!r},\n'
        "}"
    )


class CardActionsEditor(QWidget):
    """
    Editor for card actions. Shows a dropdown to select card types from the selected note types,
    and inline editors for each CardAction property (change_deck, set_flag, suspend, bury).
    """

    def __init__(
        self,
        parent,
        state: EditState,
        copy_definition: Optional[CopyDefinition],
    ):
        super().__init__(parent)
        self.state = state
        self.copy_definition = copy_definition
        self.initialized = False

        # Store callback entries for controlling visibility
        self.selected_model_callback = state.add_selected_model_callback(
            self.update_card_type_options, is_visible=False
        )

        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        # Add description label
        self.description_label = QLabel()
        self.vbox.addWidget(self.description_label)

        # Container for all action editors (displayed inline)
        self.actions_container_widget = QWidget()
        self.actions_layout = QVBoxLayout(self.actions_container_widget)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.vbox.addWidget(self.actions_container_widget)

        # Add new action button and selector
        self.card_type_selector = GroupedComboBox(is_required=False)
        self.card_type_selector.setPlaceholderText("Select a card type to add")
        self.add_action_button = QPushButton("Add Card Action")
        self.add_action_button.clicked.connect(self.add_new_action)

        add_action_layout = QHBoxLayout()
        add_action_layout.addWidget(QLabel("<h3>Card Type:</h3>"))
        add_action_layout.addWidget(self.card_type_selector)
        add_action_layout.addWidget(self.add_action_button)
        add_action_layout.addStretch()

        self.vbox.addLayout(add_action_layout)

        # Map card type names to their UI components
        self.action_ui_components: Dict[str, Dict] = {}

        # Map card type names to their CardAction definitions
        self.card_actions: Dict[str, CardAction] = {}

        # Load existing card actions from copy_definition
        if copy_definition and copy_definition.get("card_actions"):
            for action in copy_definition["card_actions"]:
                card_type_name = action.get("card_type_name", "")
                if card_type_name:
                    self.card_actions[card_type_name] = action

    def enable_callbacks(self):
        """Enable callbacks when the widget becomes visible"""
        self.selected_model_callback.is_visible = True

    def disable_callbacks(self):
        """Disable callbacks when the widget is not visible"""
        self.selected_model_callback.is_visible = False

    def set_description(self):
        """Update the description label based on the current copy mode and direction"""
        if self.state.copy_mode == COPY_MODE_ACROSS_NOTES:
            if self.state.copy_direction == DIRECTION_SOURCE_TO_DESTINATIONS:
                description = source_to_destinations_description
            else:
                description = destination_to_sources_description
        else:  # COPY_MODE_WITHIN_NOTE
            description = ""  # or a specific description for within-note mode
        self.description_label.setText(base_description + description)

    def initialize_ui_state(self):
        """Perform expensive UI state initialization when component is first shown"""
        if self.initialized:
            return

        self.enable_callbacks()
        self.update_card_type_options()
        self.set_description()

        # Display all existing actions
        for card_type_name, action in self.card_actions.items():
            self.create_action_editor(card_type_name, action)

        self.initialized = True

    def update_card_type_options(self):
        """
        Depending on copy_mode, either update the card type dropdown with card types from
        selected note types or all note types in the collection.
        Only shows card types that haven't been added yet.
        """
        current_text = self.card_type_selector.currentText()
        self.card_type_selector.blockSignals(True)
        self.card_type_selector.clear()

        has_available_types = False

        if (
            self.state.copy_mode == COPY_MODE_ACROSS_NOTES
            and self.state.copy_direction == DIRECTION_SOURCE_TO_DESTINATIONS
        ):
            # in this mode, card actions apply to destination notes' cards so show all card types
            # from all existing note types
            all_note_types = mw.col.models.all()
            for model in all_note_types:
                model_name = model["name"]
                templates = model.get("tmpls", [])

                # Collect available templates for this model (not already added)
                available_templates = []
                for template in templates:
                    template_name = template.get("name", "")
                    item_text = f"{model_name}{CARD_TYPE_SEPARATOR}{template_name}"
                    # Only add if not already in card_actions
                    if item_text not in self.card_actions:
                        available_templates.append(item_text)

                # Only add the group if there are available templates
                if available_templates:
                    self.card_type_selector.addGroup(model_name)
                    for item_text in available_templates:
                        self.card_type_selector.addItemToGroup(model_name, item_text)
                        has_available_types = True

            # Restore previous selection if it still exists and is still available
            if current_text and current_text not in self.card_actions:
                index = self.card_type_selector.findText(current_text)
                if index >= 0:
                    self.card_type_selector.setCurrentIndex(index)

            self.card_type_selector.blockSignals(False)

            # Disable if no available types
            if not has_available_types:
                self.card_type_selector.setPlaceholderText("All card types have been configured")
                self.card_type_selector.setDisabled(True)
                self.add_action_button.setDisabled(True)
            else:
                self.card_type_selector.setPlaceholderText("Select a card type to add")
                self.card_type_selector.setDisabled(False)
                self.add_action_button.setDisabled(False)

            return

        if not self.state.selected_models:
            self.card_type_selector.setPlaceholderText("First, select a trigger note type")
            self.card_type_selector.setDisabled(True)
            self.add_action_button.setDisabled(True)
            self.card_type_selector.blockSignals(False)
            return

        # Group card types by note type
        for model in self.state.selected_models:
            model_name = model["name"]
            templates = model.get("tmpls", [])

            # Collect available templates for this model (not already added)
            available_templates = []
            for template in templates:
                template_name = template.get("name", "")
                item_text = f"{model_name}{CARD_TYPE_SEPARATOR}{template_name}"
                # Only add if not already in card_actions
                if item_text not in self.card_actions:
                    available_templates.append(item_text)

            # Only add the group if there are available templates
            if available_templates:
                self.card_type_selector.addGroup(model_name)
                for item_text in available_templates:
                    self.card_type_selector.addItemToGroup(model_name, item_text)
                    has_available_types = True

        # Restore previous selection if it still exists and is still available
        if current_text and current_text not in self.card_actions:
            index = self.card_type_selector.findText(current_text)
            if index >= 0:
                self.card_type_selector.setCurrentIndex(index)

        self.card_type_selector.blockSignals(False)

        # Disable if no available types
        if not has_available_types:
            self.card_type_selector.setPlaceholderText("All card types have been configured")
            self.card_type_selector.setDisabled(True)
            self.add_action_button.setDisabled(True)
        else:
            self.card_type_selector.setPlaceholderText("Select a card type to add")
            self.card_type_selector.setDisabled(False)
            self.add_action_button.setDisabled(False)

    def add_new_action(self):
        """Called when the Add Card Action button is clicked"""
        card_type_name = self.card_type_selector.currentText()

        if not card_type_name:
            return

        # Check if action already exists
        if card_type_name in self.card_actions:
            return

        # Create new action
        new_action: CardAction = {
            "guid": str(uuid.uuid4()),
            "card_type_name": card_type_name,
            "change_deck": None,
            "set_flag": None,
            "suspend": None,
            "bury": None,
            "set_desired_retention": None,
            "use_code": False,
            "action_code": "",
        }

        self.card_actions[card_type_name] = new_action

        # Create and display the action editor
        self.create_action_editor(card_type_name, new_action)

        # Clear the selector and refresh dropdown to remove the added card type
        self.card_type_selector.setCurrentIndex(-1)
        self.update_card_type_options()

    def create_action_editor(self, card_type_name: str, action: CardAction):
        """Create the UI for editing a single CardAction and add it inline"""
        # Don't create if already exists
        if card_type_name in self.action_ui_components:
            return

        # Create a frame for the action editor
        frame = QFrame()
        frame.setFrameShape(QFrameStyledPanel)
        frame.setFrameShadow(QFrameShadowRaised)
        frame_layout = QVBoxLayout(frame)
        self.actions_layout.addWidget(frame)

        # Header
        header = QLabel(f"<h3>Actions for card type: <em>{html.escape(card_type_name)}</em></h3>")
        frame_layout.addWidget(header)

        # Code mode toggle
        use_code_toggle = ToggleSwitch("Execute as Python code")
        frame_layout.addWidget(use_code_toggle)

        # --- Form mode container ---
        form_mode_container = QWidget()
        form_layout = QFormLayout(form_mode_container)

        # 1. Change Deck dropdown
        deck_combo = QComboBox()
        deck_combo.addItem("-")
        all_decks = mw.col.decks.all_names_and_ids()
        for deck_name_and_id in all_decks:
            deck_combo.addItem(deck_name_and_id.name)
        current_deck = action.get("change_deck")
        if current_deck:
            index = deck_combo.findText(current_deck)
            if index >= 0:
                deck_combo.setCurrentIndex(index)
        else:
            deck_combo.setCurrentIndex(0)
        form_layout.addRow(QLabel("<b>Move card to deck:</b>"), deck_combo)

        # 2. Set Flag button group
        flag_group = QButtonGroup()
        flag_layout = QHBoxLayout()
        flag_options = [
            (None, "N/A"),
            (0, "No flag"),
            (1, "Red"),
            (2, "Orange"),
            (3, "Green"),
            (4, "Blue"),
            (5, "Pink"),
            (6, "Turquoise"),
            (7, "Purple"),
        ]
        current_flag = action.get("set_flag")
        for value, text in flag_options:
            radio = QRadioButton(text)
            radio.setProperty("flag_value", value)
            flag_group.addButton(radio)
            flag_layout.addWidget(radio)
            if current_flag == value or (current_flag is None and value is None):
                radio.setChecked(True)
        form_layout.addRow(QLabel("<b>Set card flag:</b>"), flag_layout)

        # 3. Suspend button group
        suspend_group = QButtonGroup()
        suspend_layout = QHBoxLayout()
        current_suspend = action.get("suspend")
        for value, text in [(None, "N/A"), (True, "Suspend"), (False, "Unsuspend")]:
            radio = QRadioButton(text)
            radio.setProperty("suspend_value", value)
            suspend_group.addButton(radio)
            suspend_layout.addWidget(radio)
            if current_suspend == value or (current_suspend is None and value is None):
                radio.setChecked(True)
        form_layout.addRow(QLabel("<b>Suspend card:</b>"), suspend_layout)

        # 4. Bury button group
        bury_group = QButtonGroup()
        bury_layout = QHBoxLayout()
        current_bury = action.get("bury")
        for value, text in [(None, "N/A"), (True, "Bury"), (False, "Unbury")]:
            radio = QRadioButton(text)
            radio.setProperty("bury_value", value)
            bury_group.addButton(radio)
            bury_layout.addWidget(radio)
            if current_bury == value or (current_bury is None and value is None):
                radio.setChecked(True)
        form_layout.addRow(QLabel("<b>Bury card:</b>"), bury_layout)

        # 5. Set desired retention
        dr_layout = QHBoxLayout()
        dr_number_input = QDoubleSpinBox()
        dr_number_input.setRange(0.0, 0.99)
        dr_number_input.setSingleStep(0.01)
        dr_number_input.setDecimals(2)
        dr_number_input.setSpecialValueText(" ")
        dr_number_input.setValue(0.0)
        dr_string_input = QLineEdit()
        dr_string_input.setPlaceholderText("Custom data property name")
        current_dr = action.get("set_desired_retention")
        if isinstance(current_dr, (float, int)) and not isinstance(current_dr, bool):
            dr_number_input.setValue(float(current_dr))
        elif isinstance(current_dr, str) and current_dr:
            dr_string_input.setText(current_dr)

        def _dr_number_changed(value, _s=dr_string_input, _n=dr_number_input):
            if value >= 0.01:
                _s.blockSignals(True)
                _s.clear()
                _s.blockSignals(False)

        def _dr_string_changed(text, _n=dr_number_input):
            if text:
                _n.blockSignals(True)
                _n.setValue(0.0)
                _n.blockSignals(False)

        dr_number_input.valueChanged.connect(_dr_number_changed)
        dr_string_input.textChanged.connect(_dr_string_changed)
        dr_layout.addWidget(QLabel("Float (0.01\u20130.99):"))
        dr_layout.addWidget(dr_number_input)
        dr_layout.addWidget(QLabel("or custom data property:"))
        dr_layout.addWidget(dr_string_input)
        dr_layout.addStretch()
        form_layout.addRow(QLabel("<b>Set desired retention:</b>"), dr_layout)

        frame_layout.addWidget(form_mode_container)

        # --- Code mode widget ---
        code_editor = CodeEditLayout(
            parent=frame,
            options_dict=self.state.post_query_menu_options_dict,
            is_required=False,
            label=None,
            description=None,
            notice=CARD_ACTION_CODE_NOTICE,
        )
        code_editor.update_options(
            self.state.post_query_menu_options_dict,
            self.state.post_query_text_edit_validate_dict,
        )
        code_editor.set_text(action.get("action_code", "") or "")
        code_editor.hide()
        frame_layout.addWidget(code_editor)

        # Apply initial mode and wire toggle
        initial_use_code = action.get("use_code", False)
        if initial_use_code:
            use_code_toggle.setChecked(True)
            form_mode_container.hide()
            code_editor.show()

        def on_use_code_toggled(checked: bool):
            form_mode_container.setVisible(not checked)
            code_editor.setVisible(checked)
            if checked and not code_editor.get_text().strip():
                deck_text = deck_combo.currentText()
                current_change_deck = None if deck_text == "-" else deck_text
                current_set_flag = next(
                    (b.property("flag_value") for b in flag_group.buttons() if b.isChecked()),
                    None,
                )
                current_suspend = next(
                    (b.property("suspend_value") for b in suspend_group.buttons() if b.isChecked()),
                    None,
                )
                current_bury = next(
                    (b.property("bury_value") for b in bury_group.buttons() if b.isChecked()),
                    None,
                )
                dr_string = dr_string_input.text().strip()
                dr_number = dr_number_input.value()
                current_dr = dr_string or (dr_number if dr_number >= 0.01 else None)
                code_editor.set_text(
                    _card_action_to_initial_code(
                        change_deck=current_change_deck,
                        set_flag=current_set_flag,
                        suspend=current_suspend,
                        bury=current_bury,
                        set_desired_retention=current_dr,
                    )
                )

        use_code_toggle.toggled.connect(on_use_code_toggled)

        # Delete button
        delete_button = QPushButton("Delete this card action")
        delete_button.clicked.connect(lambda: self.delete_action(card_type_name))
        frame_layout.addWidget(delete_button)

        # Store UI components for later retrieval
        self.action_ui_components[card_type_name] = {
            "frame": frame,
            "use_code_toggle": use_code_toggle,
            "form_mode_container": form_mode_container,
            "deck_combo": deck_combo,
            "flag_group": flag_group,
            "suspend_group": suspend_group,
            "bury_group": bury_group,
            "dr_number_input": dr_number_input,
            "dr_string_input": dr_string_input,
            "code_editor": code_editor,
        }

    def save_action(self, card_type_name: str):
        """Save a specific action from its UI components"""
        if card_type_name not in self.action_ui_components:
            return

        ui = self.action_ui_components[card_type_name]
        use_code = ui["use_code_toggle"].isChecked()

        # Read form fields (always saved so values are preserved when toggling modes)
        deck_text = ui["deck_combo"].currentText()
        change_deck = None if deck_text == "-" else deck_text

        set_flag = None
        for button in ui["flag_group"].buttons():
            if button.isChecked():
                set_flag = button.property("flag_value")
                break

        suspend = None
        for button in ui["suspend_group"].buttons():
            if button.isChecked():
                suspend = button.property("suspend_value")
                break

        bury = None
        for button in ui["bury_group"].buttons():
            if button.isChecked():
                bury = button.property("bury_value")
                break

        dr_string = ui["dr_string_input"].text().strip()
        dr_number = ui["dr_number_input"].value()
        if dr_string:
            set_desired_retention = dr_string
        elif dr_number >= 0.01:
            set_desired_retention = dr_number
        else:
            set_desired_retention = None

        existing = self.card_actions.get(card_type_name, {})
        self.card_actions[card_type_name] = {
            "guid": existing.get("guid", str(uuid.uuid4())),
            "card_type_name": card_type_name,
            "change_deck": change_deck,
            "set_flag": set_flag,
            "suspend": suspend,
            "bury": bury,
            "set_desired_retention": set_desired_retention,
            "use_code": use_code,
            "action_code": ui["code_editor"].get_text(),
        }

    def delete_action(self, card_type_name: str):
        """Delete a card action and its UI"""
        # Remove from data
        if card_type_name in self.card_actions:
            del self.card_actions[card_type_name]

        # Remove from UI
        if card_type_name in self.action_ui_components:
            ui_components = self.action_ui_components[card_type_name]
            frame = ui_components["frame"]
            self.actions_layout.removeWidget(frame)
            frame.deleteLater()
            del self.action_ui_components[card_type_name]

        # Refresh dropdown to show the deleted card type as available again
        self.update_card_type_options()

    def get_card_actions(self) -> list[CardAction]:
        """Return the list of card actions"""
        # Save all actions from their UI components
        for card_type_name in list(self.action_ui_components.keys()):
            self.save_action(card_type_name)

        # Include actions with non-empty code or any non-None form field
        result = []
        for action in self.card_actions.values():
            if (
                (action.get("use_code", False) and action.get("action_code", "").strip())
                or action.get("change_deck") is not None
                or action.get("set_flag") is not None
                or action.get("suspend") is not None
                or action.get("bury") is not None
                or action.get("set_desired_retention") is not None
            ):
                result.append(action)

        return result
