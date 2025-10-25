from contextlib import suppress
from typing import Optional
from aqt import mw

from aqt.qt import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFormLayout,
)

from ..configuration import (
    COPY_MODE_WITHIN_NOTE,
    DIRECTION_DESTINATION_TO_SOURCES,
    CopyDefinition,
    CopyModeType,
)

from .multi_combo_box import MultiComboBox


from .edit_state import EditState


class TagEditor(QWidget):
    """
    Class for editing tags to add/remove for a note or notes
    """

    def __init__(
        self,
        parent,
        state: EditState,
        copy_definition: Optional[CopyDefinition],
        copy_mode: CopyModeType,
    ):
        super().__init__(parent)
        self.state = state
        if copy_definition is None:
            self.add_tags_str = ""
            self.remove_tags_str = ""
        else:
            self.add_tags_str = copy_definition.get("add_tags", "")
            self.remove_tags_str = copy_definition.get("remove_tags", "")
        self.copy_definition = copy_definition
        self.copy_mode = copy_mode

        self.all_tags: list[str] = mw.col.tags.all()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.direction_callback = state.add_copy_direction_callback(
            self.update_direction_labels, is_visible=False
        )

        # Show two combo boxes for adding/removing tags
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)
        self.add_tags_label = QLabel("Tags to add")
        self.add_tags_combo_box = MultiComboBox(self)
        self.form_layout.addRow(self.add_tags_label, self.add_tags_combo_box)

        self.remove_tags_label = QLabel("Tags to remove")
        self.remove_tags_combo_box = MultiComboBox(self)
        self.form_layout.addRow(self.remove_tags_label, self.remove_tags_combo_box)

    def get_add_tags(self) -> str:
        return self.add_tags_combo_box.currentText()

    def get_remove_tags(self) -> str:
        return self.remove_tags_combo_box.currentText()

    def update_direction_labels(self):
        if self.state.copy_mode == COPY_MODE_WITHIN_NOTE:
            add_tag_label_clarification = "to the trigger note"
            remove_tag_label_clarification = "from the trigger note"
        elif self.state.copy_direction == DIRECTION_DESTINATION_TO_SOURCES:
            add_tag_label_clarification = "to the trigger note"
            remove_tag_label_clarification = "from the trigger note"
        else:
            add_tag_label_clarification = "from the searched note"
            remove_tag_label_clarification = "to the searched note"

        self.add_tags_label.setText(f"Tags to add {add_tag_label_clarification}")
        self.remove_tags_label.setText(f"Tags to remove {remove_tag_label_clarification}")

    def enable_callbacks(self):
        self.direction_callback.is_visible = True

    def disable_callbacks(self):
        self.direction_callback.is_visible = False

    def initialize_ui_state(self):
        self.remove_tags_combo_box.addItems(self.all_tags)

        with suppress(KeyError):
            for tag in self.remove_tags_str.strip('""').split('", "'):
                if tag and tag not in self.all_tags:
                    self.remove_tags_combo_box.addItem(tag)
            self.remove_tags_combo_box.setCurrentText(self.remove_tags_str)
        self.add_tags_combo_box.addItems(self.all_tags)

        with suppress(KeyError):
            for tag in self.add_tags_str.strip('""').split('", "'):
                if tag and tag not in self.all_tags:
                    self.add_tags_combo_box.addItem(tag)
            self.add_tags_combo_box.setCurrentText(self.add_tags_str)

        self.update_direction_labels()
        self.enable_callbacks()
