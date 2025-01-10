from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QGroupBox, QFormLayout, QLabel, 
                              QComboBox, QLineEdit, QPushButton,
                              QFileDialog)
from services.service_locator import ServiceLocator 
from services.navigation_service import ViewType

class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.viewmodel = self.locator.get_service("settings_viewmodel")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        calibration_group = QGroupBox("Calibration Settings")
        calibration_layout = QFormLayout()
        
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(self.viewmodel.get_target_types())
        # self.target_type_combo.currentTextChanged.connect(lambda v: )
        
        self.cube_size_edit = QLineEdit()
        self.cube_size_edit.setPlaceholderText("Size in mm")

        calibration_layout.addRow("Cube Size (mm):", self.cube_size_edit)
        calibration_layout.addRow("Target Type:", self.target_type_combo)
        
        calibration_group.setLayout(calibration_layout)
        main_layout.addWidget(calibration_group)

        # Camera Settings Group
        camera_group = QGroupBox("Camera Settings")
        camera_layout = QFormLayout()

        self.num_of_cameras = QLabel("Number of Cameras")
        self.num_of_cameras_combo = QComboBox()

        self.exposure_edit = QLineEdit()
        camera_layout.addRow("Exposure:", self.exposure_edit)
        camera_layout.addRow(self.num_of_cameras, self.num_of_cameras_combo)
        camera_group.setLayout(camera_layout)
        main_layout.addWidget(camera_group)

        # Application Settings Group
        app_group = QGroupBox("Application Settings")
        app_layout = QFormLayout()
        
        # Data path with browse button
        path_layout = QHBoxLayout()
        self.data_path_edit = QLineEdit()
        self.data_path_edit.textChanged.connect(
            lambda v: self.viewmodel.update_setting("app", "data_save_path", v)
        )
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_data_path)
        
        path_layout.addWidget(self.data_path_edit)
        path_layout.addWidget(browse_btn)
        app_layout.addRow("Data Save Path:", path_layout)
        
        save_btn = QPushButton("Save")
        back_btn = QPushButton("Back")
        save_btn.clicked.connect(self.save_settings)
        back_btn.clicked.connect(self.navigate_back)

        nav_group = QWidget()
        nav_group_layout = QHBoxLayout()
        nav_group_layout.addStretch()
        nav_group_layout.addWidget(back_btn)
        nav_group_layout.addWidget(save_btn)
        
        nav_group.setLayout(nav_group_layout)
        app_group.setLayout(app_layout)


        main_layout.addWidget(app_group)
        
        main_layout.addStretch()
        main_layout.addWidget(nav_group)


    def browse_data_path(self):
        """
        Opens a directory selection dialog when the browse button is clicked.
        Updates the data path text field with the selected directory.
        """
        current_path = self.data_path_edit.text()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Data Save Directory",
            current_path
        )
        if directory:  # If user didn't cancel
            self.data_path_edit.setText(directory)
            # Update the setting in our ViewModel
            self.view_model.set_data_save_path(directory)

    def save_settings(self):
        self.viewmodel.update_settings()

    def navigate_back(self):
        self.viewmodel.navigate_to(ViewType.MAIN)