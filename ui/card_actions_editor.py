from typing import Optional, Dict
import uuid

from aqt import mw
from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QFormLayout,
    QPushButton,
    QComboBox,
    QButtonGroup,
    QRadioButton,
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
from .edit_state import EditState
from .grouped_combo_box import GroupedComboBox

base_description = """<p>Configure actions to perform on any destination note's card types.
            Select a card type from the dropdown to configure its action.</p>"""

source_to_destinations_description = (
    "<p><small>Note: Card actions are performed on the queried notes' cards.</small></p>"
)
destination_to_sources_description = (
    "<p><small>Note: Card actions are performed on the trigger note's cards.</small></p>"
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
        self.add_action_form = QFormLayout()
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

        # Add frame to the actions layout
        self.actions_layout.addWidget(frame)

        # Header - show both model and card type in a readable format
        # card_type_name is just the template name from GroupedComboBox
        header = QLabel(f"<h3>Actions for card type: <em>{card_type_name}</em></h3>")
        frame_layout.addWidget(header)

        form_layout = QFormLayout()
        frame_layout.addLayout(form_layout)

        # 1. Change Deck dropdown
        deck_combo = QComboBox()
        deck_combo.addItem("-")  # Default: no action

        # Add all decks
        all_decks = mw.col.decks.all_names_and_ids()
        for deck_name_and_id in all_decks:
            deck_combo.addItem(deck_name_and_id.name)

        # Set current value
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

            # Set checked state
            if current_flag == value:
                radio.setChecked(True)
            elif current_flag is None and value is None:
                radio.setChecked(True)

        form_layout.addRow(QLabel("<b>Set card flag:</b>"), flag_layout)

        # 3. Suspend button group
        suspend_group = QButtonGroup()
        suspend_layout = QHBoxLayout()

        suspend_options = [
            (None, "N/A"),
            (True, "Suspend"),
            (False, "Unsuspend"),
        ]

        current_suspend = action.get("suspend")
        for value, text in suspend_options:
            radio = QRadioButton(text)
            radio.setProperty("suspend_value", value)
            suspend_group.addButton(radio)
            suspend_layout.addWidget(radio)

            # Set checked state
            if current_suspend == value:
                radio.setChecked(True)
            elif current_suspend is None and value is None:
                radio.setChecked(True)

        form_layout.addRow(QLabel("<b>Suspend card:</b>"), suspend_layout)

        # 4. Bury button group
        bury_group = QButtonGroup()
        bury_layout = QHBoxLayout()

        bury_options = [
            (None, "N/A"),
            (True, "Bury"),
            (False, "Unbury"),
        ]

        current_bury = action.get("bury")
        for value, text in bury_options:
            radio = QRadioButton(text)
            radio.setProperty("bury_value", value)
            bury_group.addButton(radio)
            bury_layout.addWidget(radio)

            # Set checked state
            if current_bury == value:
                radio.setChecked(True)
            elif current_bury is None and value is None:
                radio.setChecked(True)

        form_layout.addRow(QLabel("<b>Bury card:</b>"), bury_layout)

        # Delete button
        delete_button = QPushButton("Delete this card action")
        delete_button.clicked.connect(lambda: self.delete_action(card_type_name))
        form_layout.addRow("", delete_button)

        # Store UI components for later retrieval
        self.action_ui_components[card_type_name] = {
            "frame": frame,
            "deck_combo": deck_combo,
            "flag_group": flag_group,
            "suspend_group": suspend_group,
            "bury_group": bury_group,
        }

    def save_action(self, card_type_name: str):
        """Save a specific action from its UI components"""
        if card_type_name not in self.action_ui_components:
            return

        ui_components = self.action_ui_components[card_type_name]
        deck_combo = ui_components["deck_combo"]
        flag_group = ui_components["flag_group"]
        suspend_group = ui_components["suspend_group"]
        bury_group = ui_components["bury_group"]

        # Get change_deck value
        deck_text = deck_combo.currentText()
        change_deck = None if deck_text == "-" else deck_text

        # Get set_flag value
        set_flag = None
        for button in flag_group.buttons():
            if button.isChecked():
                set_flag = button.property("flag_value")
                break

        # Get suspend value
        suspend = None
        for button in suspend_group.buttons():
            if button.isChecked():
                suspend = button.property("suspend_value")
                break

        # Get bury value
        bury = None
        for button in bury_group.buttons():
            if button.isChecked():
                bury = button.property("bury_value")
                break

        # Update the action
        self.card_actions[card_type_name] = {
            "guid": self.card_actions[card_type_name].get("guid", str(uuid.uuid4())),
            "card_type_name": card_type_name,
            "change_deck": change_deck,
            "set_flag": set_flag,
            "suspend": suspend,
            "bury": bury,
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

        # Return only actions that have at least one non-None value
        result = []
        for action in self.card_actions.values():
            if (
                action.get("change_deck") is not None
                or action.get("set_flag") is not None
                or action.get("suspend") is not None
                or action.get("bury") is not None
            ):
                result.append(action)

        return result
