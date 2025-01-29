# calibration_module/views/communication_setup_page.py

from PySide6.QtWidgets import (
    QWizardPage,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QGroupBox,
    QFileDialog,
    QHBoxLayout,
)
from services.service_locator import ServiceLocator
from components.ip_field import IPInputWidget


class CommunicationSetupPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Communication Setup")
        self.setSubTitle("Configure connection to CARTO navigation system")

        self.viewmodel = ServiceLocator.get_instance().get_service(
            "communication_viewmodel"
        )

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Network Configuration Group
        network_group = QGroupBox("Network Configuration")
        network_layout = QFormLayout()

        # Read-only IP display
        self.ip_display = QLabel(self.viewmodel.get_target_ip())
        network_layout.addRow("CARTO IP Address:", self.ip_display)

        # Status with test button
        status_layout = QHBoxLayout()
        self.connection_status = QLabel("Unknown")
        self.test_connection_btn = QPushButton("Test Connection")
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.test_connection_btn)
        network_layout.addRow("Connection Status:", status_layout)

        network_group.setLayout(network_layout)

        # DLI Configuration Group
        dli_group = QGroupBox("DLI Configuration")
        dli_layout = QFormLayout()

        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("e.g. 7.1")
        dli_layout.addRow("CARTO Version:", self.version_input)

        self.dli_status = QLabel("Enter CARTO version")
        dli_layout.addRow("DLI Status:", self.dli_status)

        self.import_button = QPushButton("Import DLI Files")
        self.import_button.setEnabled(False)
        dli_layout.addRow(self.import_button)

        dli_group.setLayout(dli_layout)

        layout.addWidget(network_group)
        layout.addWidget(dli_group)

    def connect_signals(self):
        # Connect UI signals to ViewModel
        self.test_connection_btn.clicked.connect(self.viewmodel.test_connection)
        self.version_input.textChanged.connect(self.viewmodel.validate_version)
        self.import_button.clicked.connect(self._handle_import_click)

        # Connect ViewModel signals to UI updates
        self.viewmodel.connection_status_changed.connect(self._update_connection_status)
        self.viewmodel.dli_status_changed.connect(self._update_dli_status)
        self.viewmodel.import_button_enabled_changed.connect(
            self.import_button.setEnabled
        )
        self.viewmodel.testing_state_changed.connect(self._update_testing_state)

    def _update_connection_status(self, text: str, color: str):
        """Updates connection status display"""
        self.connection_status.setText(text)
        self.connection_status.setStyleSheet(f"color: {color}")

    def _update_dli_status(self, text: str, color: str):
        """Updates DLI status display"""
        self.dli_status.setText(text)
        self.dli_status.setStyleSheet(f"color: {color}")

    def _update_testing_state(self, is_testing: bool):
        """Updates UI state during connection testing"""
        self.test_connection_btn.setEnabled(not is_testing)

    def _handle_import_click(self):
        """Handles import button click by showing file dialog"""
        dll_path, _ = QFileDialog.getOpenFileName(
            self, "Select DLINetinterface.dll", "", "DLL Files (*.dll)"
        )

        if dll_path:
            self.viewmodel.handle_dli_import(dll_path)
