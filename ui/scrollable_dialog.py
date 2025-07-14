from aqt.qt import (
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QDialog,
    QGuiApplication,
    QLayout,
)


class ScrollableQDialog(QDialog):

    def __init__(
        self,
        parent=None,
        footer_layout: QLayout = None,
        no_fixed_size: bool = False,
    ):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)

        self.scroll_area = QScrollArea(self)
        self.main_layout.addWidget(self.scroll_area)
        self.scroll_area.setWidgetResizable(True)

        self.inner_widget = QWidget()
        self.scroll_area.setWidget(self.inner_widget)

        # Get the screen size
        screen = QGuiApplication.primaryScreen()
        if screen and not no_fixed_size:
            geometry = screen.availableGeometry()
            # Set the initial size to a percentage of the screen size
            self.resize(int(geometry.width() * 0.6), int(geometry.height() * 0.95))

        # Add footer to the main layout
        if footer_layout:
            self.main_layout.addLayout(footer_layout)
