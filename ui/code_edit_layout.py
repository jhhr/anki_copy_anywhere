"""A code-editing layout widget parallel to InterpolatedTextEditLayout.

Differences from the text editor:
  - Monospace font with 4-space tab stops.
  - Live Python syntax validation: the user code is wrapped in a dummy
    ``def`` so that ``return`` statements are syntactically valid at parse
    time.  ``SyntaxError`` / ``IndentationError`` messages are shown inline.
  - The same ``{{field}}`` interpolation-marker validation as the text editor.
  - A persistent security notice and available-names reference.

Public interface mirrors ``InterpolatedTextEditLayout`` so the two widgets can
be swapped in host editors without touching surrounding code:
  ``get_text()`` / ``set_text()`` / ``update_options()`` / ``validate_text()``
"""

import ast
import textwrap
from typing import Optional

from aqt.qt import (
    QFont,
    QFontMetrics,
    QLabel,
    QVBoxLayout,
    QWidget,
    qtmajor,
)

from .pasteable_text_edit import PasteableTextEdit
from ..logic.interpolate_fields import (
    ARG_SEPARATOR,
    ARG_VALIDATORS,
    CARD_VALUE_RE,
    NOTE_VALUE_RE,
    basic_arg_validator,
    get_fields_from_text,
    intr_format,
)

_SECURITY_NOTICE = (
    "⚠ <b>Code mode</b> — write the body of a function that <b>returns a string</b>. "
    "<tt>{{Field}}</tt> markers are resolved before execution.<br>"
    "Available names: <tt>re</tt>, <tt>json</tt>, <tt>html</tt>, <tt>print</tt>, "
    "<tt>find_cards</tt>, <tt>find_notes</tt>, <tt>note</tt>. "
    "<small>Built-ins are restricted to a safe subset.</small><br>"
    "<small>⚠ Fields containing HTML (quotes, tags) can break string literals — "
    "prefer <tt>note[\"Field Name\"]</tt> over <tt>\"{{Field Name}}\"</tt>.</small>"
)


class CodeEditLayout(QWidget):
    """Monospace code editor with Python syntax + interpolation validation.

    Designed to be a drop-in partner to ``InterpolatedTextEditLayout``: both
    share ``get_text()`` / ``set_text()`` / ``update_options()`` so the host
    editor can switch between them without special-casing.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        options_dict: Optional[dict] = None,
        is_required: bool = False,
        label: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        super().__init__(parent)

        self._validate_dict: dict = {}
        self._options_dict: dict = options_dict or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # --- Header label (mirrors InterpolatedTextEditLayout) ---------------
        self._label_widget = QLabel()
        layout.addWidget(self._label_widget)
        self.set_label(label)

        # --- Security / context notice -------------------------------------------
        self._notice_label = QLabel(_SECURITY_NOTICE)
        self._notice_label.setWordWrap(True)
        self._notice_label.setStyleSheet(
            "color: #ddd;"
            "border: 1px solid #ccc;"
            "border-radius: 4px;"
            "padding: 5px;"
            "font-size: 10px;"
        )
        layout.addWidget(self._notice_label)

        # --- Interpolation description (mirrors InterpolatedTextEditLayout) --
        self._description_label = QLabel()
        self._description_label.setWordWrap(True)
        self._description_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self._description_label)
        self.set_description(description)

        # --- Code editor ---------------------------------------------------------
        self.text_edit = PasteableTextEdit(
            parent=self,
            options_dict=self._options_dict,
            is_required=is_required,
            placeholder_text="return ...",
        )
        self._apply_code_font()
        self.text_edit.textChanged.connect(self.validate_text)
        layout.addWidget(self.text_edit)

        # --- Error / validation label --------------------------------------------
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

    # -------------------------------------------------------------------------
    # Font / appearance
    # -------------------------------------------------------------------------

    def _apply_code_font(self) -> None:
        font = QFont("Courier New")
        if qtmajor > 5:
            font.setStyleHint(QFont.StyleHint.Monospace)
        else:
            font.setStyleHint(QFont.Monospace)  # type: ignore[attr-defined]
        font.setPointSize(10)
        self.text_edit.setFont(font)
        tab_px = QFontMetrics(font).horizontalAdvance("    ")
        self.text_edit.setTabStopDistance(float(tab_px))

    # -------------------------------------------------------------------------
    # Public interface (mirrors InterpolatedTextEditLayout)
    # -------------------------------------------------------------------------

    def get_text(self) -> str:
        return self.text_edit.toPlainText()

    def set_text(self, text: str) -> None:
        self.text_edit.setPlainText(text)
        self.text_edit.update_required_style()

    def set_label(self, label: Optional[str]) -> None:
        if label:
            self._label_widget.setText(label)
            self._label_widget.show()
        else:
            self._label_widget.hide()

    def set_description(self, description: Optional[str]) -> None:
        if description:
            self._description_label.setText(description)
            self._description_label.show()
        else:
            self._description_label.hide()

    def update_options(
        self, new_options_dict: dict, new_validate_dict: dict
    ) -> None:
        self.text_edit.clear_options()
        self._options_dict = new_options_dict
        self._validate_dict = new_validate_dict
        self.text_edit.set_options_dict(new_options_dict)
        self.validate_text()

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate_text(self) -> None:
        code = self.text_edit.toPlainText()
        errors: list[str] = []

        # 1. Python syntax check (wrap in a def so ``return`` is legal at parse
        #    time; shift reported line numbers back by 1 to account for the
        #    injected ``def`` line).
        if code.strip():
            wrapped = "def _user_func():\n" + textwrap.indent(
                code if code else " ", "    "
            )
            try:
                ast.parse(wrapped)
            except SyntaxError as e:
                user_line = max(1, (e.lineno or 1) - 1)
                kind = (
                    "Indentation error"
                    if isinstance(e, IndentationError)
                    else "Syntax error"
                )
                errors.append(
                    f'<b style="color:red">{kind}</b> (line {user_line}): {e.msg}'
                )

        # 2. {{field}} interpolation-marker validation (same logic as
        #    InterpolatedTextEditLayout.validate_text()).
        fields = get_fields_from_text(code)
        for field in fields:
            arg: Optional[str] = None
            card_type_name: Optional[str] = None
            if ARG_SEPARATOR in field and "__" in field:
                m = NOTE_VALUE_RE.match(field)
                if m:
                    field, arg = m.group(1, 2)
                else:
                    m = CARD_VALUE_RE.match(field)
                    if m:
                        card_type_name, field, arg = m.group(1, 2, 3)
                        field = card_type_name + field

            try:
                self._validate_dict[intr_format(field.lower())]
            except KeyError:
                errors.append(
                    f'<b style="color:red">{field}</b>: Not a valid field'
                )
                continue

            if arg is not None:
                key = field[len(card_type_name) :] if card_type_name else field
                validator = ARG_VALIDATORS.get(key, None)
                if validator is not None:
                    error_msg = basic_arg_validator(arg) or validator(arg)
                    if error_msg:
                        errors.append(
                            f'{field} <span style="color: orange;">'
                            f'<b style="color:red">{arg or "[blank]"}</b>'
                            f": {error_msg}</span>"
                        )

        self.error_label.setText("<br/>".join(errors) if errors else "")
