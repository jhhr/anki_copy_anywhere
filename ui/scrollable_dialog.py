# noinspection PyUnresolvedReferences
from aqt.qt import (
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QDialog,
    QGuiApplication,
)


class ScrollableQDialog(QDialog):
    def __init__(self, parent=None, footer_layout=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.scroll_area = QScrollArea(self)
        self.layout.addWidget(self.scroll_area)
        self.scroll_area.setWidgetResizable(True)

        self.inner_widget = QWidget()
        self.scroll_area.setWidget(self.inner_widget)

        # Get the screen size
        screen = QGuiApplication.primaryScreen().availableGeometry()

        # Set the initial size to a percentage of the screen size
        self.resize(int(screen.width() * 0.6), int(screen.height() * 0.95))

        # Add footer to the main layout
        if footer_layout:
            self.layout.addLayout(footer_layout)
