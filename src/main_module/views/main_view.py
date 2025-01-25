from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt
from services.service_locator import ServiceLocator
from services.navigation_service import ViewType


class MainView(QWidget):
    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.view_model = self.locator.get_service("main_viewmodel")
        self.init_ui()
        self.connect_signals()

    def init_ui(self):

        layout = QVBoxLayout()

        # crearte buttons
        self.calibrate_btn = QPushButton("Calibrate")
        self.measure_btn = QPushButton("Measure")
        self.archive_btn = QPushButton("Archive")
        self.settings_btn = QPushButton("Settings")

        layout.addWidget(self.calibrate_btn)
        layout.addWidget(self.measure_btn)
        layout.addWidget(self.archive_btn)
        layout.addWidget(self.settings_btn)

        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def connect_signals(self):
        self.calibrate_btn.clicked.connect(
            lambda: self.view_model.navigate_to(ViewType.CALIBRATION)
        )
        self.settings_btn.clicked.connect(
            lambda: self.view_model.navigate_to(ViewType.SETTINGS)
        )
        self.measure_btn.clicked.connect(
            lambda: self.view_model.navigate_to(ViewType.MEASUREMENT)
        )

        self.view_model.get_global_state().wizard_active_state_changed.connect(
            self.change_view_block
        )

    def change_view_block(self, is_active: bool):
        for element in self.findChildren(QWidget):
            element.setEnabled(not is_active)
