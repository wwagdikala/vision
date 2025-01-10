from PySide6.QtWidgets import (QWizardPage, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QWidget, QLabel, QPushButton, 
                             QProgressBar, QGroupBox, QFrame)
from PySide6.QtCore import Qt
from services.service_locator import ServiceLocator
from camera_module.views.camera_view import CameraView

class CameraSetupPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Camera Calibration")
        self.setSubTitle("Set up cameras and perform calibration")
        # Get dependencies
        self.locator = ServiceLocator.get_instance()
        self.settings_service = self.locator.get_service("settings_service")
        self.wizard_viewmodel = self.locator.get_service("wizard_viewmodel")
        # Connect signals
        self.wizard_viewmodel.status_changed.connect(self.update_status)
        self.wizard_viewmodel.progress_updated.connect(self.update_progress)
        self.wizard_viewmodel.calibration_finished.connect(self.handle_calibration_complete)
        # Initialize settings-dependent attributes before UI setup
        self.camera_setup = self.settings_service.get_settings(
            "calibration", "camera_setup", "type"
        ) or "stereo_3_coplanar"  # Default value if not found
        self.target_type = self.settings_service.get_settings(
            "calibration", "target_type"
        ) or "cube"  # Default value if not found
        self.preview_active = False
        # Now we can safely set up the UI
        self.setup_ui()
        self.update_instructions()

    def setup_ui(self):
        main_layout = QHBoxLayout()
        
        # Left panel (cameras and controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Camera views section
        camera_group = QGroupBox("Camera Views")
        camera_layout = QGridLayout()
        
        self.camera_views = []
        num_cameras = self.get_num_cameras()
        
        # Arrange cameras based on setup type
        if self.camera_setup == "stereo_3":
            # Horizontal arrangement for 3 cameras
            for i in range(num_cameras):
                camera_view = self.create_camera_view(i)
                camera_layout.addWidget(camera_view, 0, i)
        else:  # circle_5
            # Arrange 5 cameras in a circle-like pattern
            positions = [(0,1), (0,2), (1,2), (1,0), (0,0)]  # Clock-wise arrangement
            for i in range(num_cameras):
                camera_view = self.create_camera_view(i)
                row, col = positions[i]
                camera_layout.addWidget(camera_view, row, col)
        
        camera_group.setLayout(camera_layout)
        left_layout.addWidget(camera_group)
        
        # Camera controls
        controls_layout = QHBoxLayout()
        self.preview_btn = QPushButton("Preview All Cameras")
        self.preview_btn.clicked.connect(self.toggle_preview)
        self.preview_btn.setFixedWidth(150)
        controls_layout.addWidget(self.preview_btn)
        
        self.calibrate_btn = QPushButton("Start Calibration")
        self.calibrate_btn.clicked.connect(self.start_calibration)
        self.calibrate_btn.setFixedWidth(150)
        self.calibrate_btn.setEnabled(False)  # Disabled until preview starts
        controls_layout.addWidget(self.calibrate_btn)
        
        left_layout.addLayout(controls_layout)
        
        # Right panel (instructions and status)
        right_panel = QWidget()
        right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout(right_panel)
        
        # Instructions group
        instructions_group = QGroupBox("Instructions")
        instructions_layout = QVBoxLayout()
        self.instructions_label = QLabel()
        self.instructions_label.setWordWrap(True)
        instructions_layout.addWidget(self.instructions_label)
        instructions_group.setLayout(instructions_layout)
        right_layout.addWidget(instructions_group)
        
        # Status group
        status_group = QGroupBox("Calibration Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready to start")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        # Quality indicators
        self.quality_frame = QFrame()
        quality_layout = QGridLayout()
        quality_layout.addWidget(QLabel("RMS Error:"), 0, 0)
        self.rms_label = QLabel("--")
        quality_layout.addWidget(self.rms_label, 0, 1)
        
        quality_layout.addWidget(QLabel("Reprojection Error:"), 1, 0)
        self.reproj_label = QLabel("--")
        quality_layout.addWidget(self.reproj_label, 1, 1)
        
        self.quality_frame.setLayout(quality_layout)
        self.quality_frame.setVisible(False)
        status_layout.addWidget(self.quality_frame)
        
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        self.setLayout(main_layout)

    def create_camera_view(self, camera_id):
        """Create a camera view with proper styling"""
        camera_view = CameraView(
            self.locator.get_service(f'camera_viewmodel_{camera_id}')
        )
        camera_view.setMinimumSize(320, 240)
        camera_view.setStyleSheet("""
            QLabel {
                background-color: black;
                border: 1px solid #666;
                color: white;
            }
        """)
        self.camera_views.append(camera_view)
        return camera_view

    def get_num_cameras(self):
        return 3 if self.camera_setup == "stereo_3_coplanar" else 5

    def update_instructions(self):
        """Update instructions based on target type"""
        instructions = "1. Click 'Preview All Cameras' to start camera feeds\n\n"
        
        if self.target_type == "cube":
            instructions += (
                "2. Place the calibration cube in the working volume\n"
                "3. Ensure the cube is visible in all cameras\n"
                "4. Check that cube corners are well-lit and visible\n"
                "5. Click 'Start Calibration' when ready"
            )
        elif self.target_type == "checkerboard":
            instructions += (
                "2. Hold the checkerboard in the working volume\n"
                "3. Ensure the pattern is fully visible\n"
                "4. Avoid reflections and ensure good lighting\n"
                "5. Click 'Start Calibration' when ready"
            )
        else:  # cube_circles
            instructions += (
                "2. Place the circle-pattern cube in position\n"
                "3. Ensure circles are clearly visible\n"
                "4. Check for good contrast and lighting\n"
                "5. Click 'Start Calibration' when ready"
            )
            
        self.instructions_label.setText(instructions)

    def toggle_preview(self):
        """Toggle camera preview state"""
        if not self.preview_active:
            success = True
            for camera_view in self.camera_views:
                if not camera_view.start():
                    success = False
                    break
            
            if success:
                self.preview_active = True
                self.preview_btn.setText("Stop Preview")
                self.calibrate_btn.setEnabled(True)
            else:
                self.status_label.setText("Failed to start all cameras")
        else:
            for camera_view in self.camera_views:
                camera_view.stop()
            self.preview_active = False
            self.preview_btn.setText("Preview All Cameras")
            self.calibrate_btn.setEnabled(False)

    def start_calibration(self):
        """Start the calibration process"""
        if not self.preview_active:
            self.status_label.setText("Please start camera preview first")
            return
        
        self.calibrate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.quality_frame.setVisible(False)
        
        # Collect frames from cameras
        frames = []
        for camera_view in self.camera_views:
            frame = camera_view.get_current_frame()
            if frame is None:
                self.status_label.setText("Failed to capture frames from all cameras")
                self.calibrate_btn.setEnabled(True)
                return
            frames.append(frame)
        
        # Start calibration via ViewModel
        self.wizard_viewmodel.start_calibration(frames)

    def update_status(self, status: str):
        """Update status message"""
        self.status_label.setText(status)

    def update_progress(self, value: int):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def handle_calibration_complete(self, success: bool, message: str, results: dict = None):
        """Handle calibration completion"""
        self.status_label.setText(message)
        self.calibrate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success and results:
            self.quality_frame.setVisible(True)
            self.rms_label.setText(f"{results.get('rms_error', 0):.3f} mm")
            self.reproj_label.setText(f"{results.get('reprojection_error', 0):.3f} px")
            
            if self.isComplete():
                self.wizard().next()
        else:
            self.quality_frame.setVisible(False)

    def isComplete(self) -> bool:
        """Check if the page is complete and calibration successful"""
        return hasattr(self.wizard_viewmodel, 'calibration_successful') and \
               self.wizard_viewmodel.calibration_successful