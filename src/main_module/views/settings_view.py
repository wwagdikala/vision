from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QFormLayout, QLabel, 
                             QComboBox, QLineEdit, QPushButton,
                             QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from services.service_locator import ServiceLocator 

class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.viewmodel = self.locator.get_service("settings_viewmodel")
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Calibration Settings Group
        calibration_group = QGroupBox("Calibration Settings")
        calibration_layout = QFormLayout()
        
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(self.viewmodel.get_target_types())
        current_target = self.viewmodel.target_type
        self.target_type_combo.setCurrentText(current_target)
        
        self.cube_size_edit = QLineEdit()
        self.cube_size_edit.setPlaceholderText("Size in mm")

        # Add widgets to layout
        calibration_layout.addRow("Target Type:", self.target_type_combo)
        calibration_layout.addRow("Cube Size (mm):", self.cube_size_edit)
        calibration_group.setLayout(calibration_layout)

        # Add group to main layout
        main_layout.addWidget(calibration_group)

        # Camera Settings Group
        camera_group = QGroupBox("Camera Settings")
        camera_layout = QFormLayout()
        
        self.exposure_edit = QLineEdit()
        self.number_of_cameras = QComboBox()
        self.number_of_cameras.addItems(self.viewmodel.get_camera_setups())

        camera_layout.addRow("Number of cameras", self.number_of_cameras)
        camera_layout.addRow("Exposure:", self.exposure_edit)
        camera_group.setLayout(camera_layout)

        # Add group to main layout
        main_layout.addWidget(camera_group)

        # Application Settings Group
        app_group = QGroupBox("Application Settings")
        app_layout = QFormLayout()
        
        # Data path with browse button
        path_layout = QHBoxLayout()
        self.data_path_edit = QLineEdit()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_data_path)
        
        path_layout.addWidget(self.data_path_edit)
        path_layout.addWidget(browse_btn)
        app_layout.addRow("Data Save Path:", path_layout)
        app_group.setLayout(app_layout)
        main_layout.addWidget(app_group)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        
        # Save Button
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.viewmodel.save_settings)
        self.save_btn.setEnabled(False)  # Initially disabled
        
        # Revert Button
        self.revert_btn = QPushButton("Revert Changes")
        self.revert_btn.clicked.connect(self.viewmodel.revert_changes)
        self.revert_btn.setEnabled(False)  # Initially disabled
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.revert_btn)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        main_layout.addLayout(button_layout)
        main_layout.addStretch()

    def connect_signals(self):
        # Connect UI elements to ViewModel
        self.target_type_combo.currentTextChanged.connect(
            lambda v: setattr(self.viewmodel, 'target_type', v)
        )
        self.cube_size_edit.textChanged.connect(
            lambda v: self.viewmodel._update_pending_setting(
                "calibration", "cube_size_mm", float(v) if v else 0
            )
        )
        self.exposure_edit.textChanged.connect(
            lambda v: self.viewmodel._update_pending_setting(
                "cameras", "exposure", int(v) if v else 0
            )
        )
        self.data_path_edit.textChanged.connect(
            lambda v: self.viewmodel._update_pending_setting(
                "app", "data_save_path", v
            )
        )
        
        # Connect ViewModel signals
        self.viewmodel.settings_changed.connect(self.on_settings_changed)
        self.viewmodel.save_completed.connect(self.on_save_completed)
        self.viewmodel.validation_error.connect(self.show_error)

    def browse_data_path(self):
        """Handle browse button click for data save path"""
        current_path = self.data_path_edit.text()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Data Save Directory",
            current_path
        )
        if directory:  # If user didn't cancel
            self.data_path_edit.setText(directory)

    def on_settings_changed(self, has_changes: bool):
        """Enable/disable save and revert buttons based on changes"""
        self.save_btn.setEnabled(has_changes)
        self.revert_btn.setEnabled(has_changes)

    def on_save_completed(self, success: bool, message: str):
        """Handle save completion"""
        if success:
            QMessageBox.information(self, "Settings Saved", message)
        else:
            QMessageBox.warning(self, "Save Failed", message)

    def show_error(self, message: str):
        """Display validation errors"""
        QMessageBox.warning(self, "Validation Error", message)