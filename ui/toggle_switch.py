"""A custom toggle-switch widget for use in place of QCheckBox.

Draws a rounded track with a sliding circular thumb — analogous to mobile
toggle switches.  Exposes the same interface as a ``QCheckBox``:
  - ``isChecked()``
  - ``setChecked(bool)``
  - ``toggled`` signal

Usage::

    switch = ToggleSwitch("Execute content as Python code")
    switch.toggled.connect(my_slot)
"""

from aqt.qt import (
    QAbstractButton,
    QColor,
    QFontMetrics,
    QPainter,
    QPen,
    QRect,
    QSize,
    QSizePolicy,
    Qt,
    qtmajor,
)

if qtmajor > 5:
    _PointingHand = Qt.CursorShape.PointingHandCursor
    _Antialiasing = QPainter.RenderHint.Antialiasing
    _NoPen = Qt.PenStyle.NoPen
else:
    _PointingHand = Qt.PointingHandCursor  # type: ignore[attr-defined]
    _Antialiasing = QPainter.Antialiasing  # type: ignore[attr-defined]
    _NoPen = Qt.NoPen  # type: ignore[attr-defined]

_TRACK_W = 36
_TRACK_H = 18
_THUMB_D = 14  # diameter
_THUMB_MARGIN = 2  # gap between thumb and track edge
_GAP = 8  # pixels between track and label


class ToggleSwitch(QAbstractButton):
    """A painted toggle switch that behaves like a checkable QAbstractButton."""

    def __init__(self, label: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setText(label)
        self.setCursor(_PointingHand)
        self.setSizePolicy(QSizePolicy.Policy.Fixed if qtmajor > 5 else QSizePolicy.Fixed, QSizePolicy.Policy.Fixed if qtmajor > 5 else QSizePolicy.Fixed)  # type: ignore[attr-defined]

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(self.text()) if self.text() else 0
        label_part = _GAP + text_w if text_w else 0
        height = max(_TRACK_H, fm.height())
        return QSize(_TRACK_W + label_part + 2, height + 4)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(_Antialiasing)

        h = self.height()
        track_y = (h - _TRACK_H) // 2

        # --- Track -----------------------------------------------------------
        track_color = QColor("#4a86d9") if self.isChecked() else QColor("#aaaaaa")
        p.setBrush(track_color)
        p.setPen(_NoPen)
        p.drawRoundedRect(QRect(0, track_y, _TRACK_W, _TRACK_H), _TRACK_H / 2, _TRACK_H / 2)

        # --- Thumb -----------------------------------------------------------
        thumb_y = track_y + _THUMB_MARGIN
        if self.isChecked():
            thumb_x = _TRACK_W - _THUMB_D - _THUMB_MARGIN
        else:
            thumb_x = _THUMB_MARGIN
        p.setBrush(QColor("white"))
        p.setPen(QPen(QColor("#cccccc"), 0.5))
        p.drawEllipse(QRect(thumb_x, thumb_y, _THUMB_D, _THUMB_D))

        # --- Label -----------------------------------------------------------
        if self.text():
            fm = QFontMetrics(self.font())
            text_x = _TRACK_W + _GAP
            text_y = (h + fm.ascent() - fm.descent()) // 2
            p.setPen(QPen(self.palette().windowText().color()))
            p.drawText(text_x, text_y, self.text())

        p.end()
