from PySide6.QtWidgets import QWizardPage, QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QLabel, QPushButton, QProgressBar
from services.service_locator import ServiceLocator
from PySide6.QtCore import Qt
from camera_module.views.camera_view import CameraView

class CameraSetupPage(QWizardPage):     
    def __init__(self, parent=None):
        super().__init__()
        self.setTitle("Camera Setup and Calibration")
        self.setSubTitle("Set up cameras and perform cube calibration")
        
        # Get dependencies
        self.locator = ServiceLocator.get_instance()
        self.wizard_viewmodel = self.locator.get_service('wizard_viewmodel')
        self.wizard_viewmodel.status_changed.connect(self.update_status)
        self.wizard_viewmodel.progress_updated.connect(self.update_progress)
        self.wizard_viewmodel.calibration_finished.connect(self.handle_calibration_complete)
        
        self.setup_ui()
        self.preview_active = False

    def setup_ui(self):
        # Main layout
        main_layout = QHBoxLayout()
        
        # Left panel (cameras)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        camera_grid = QGridLayout()
        
        # Create camera views
        self.camera_views = []
        for i in range(3):
            camera_view = CameraView(self.locator.get_service(f'camera_viewmodel_{i}'))
            camera_view.setStyleSheet("background-color: black;")
            camera_view.setMinimumSize(320, 240)
            self.camera_views.append(camera_view)
            camera_grid.addWidget(camera_view, i // 2, i % 2)
            
        left_layout.addLayout(camera_grid)
        left_layout.addStretch()
        
        # Preview button
        preview_btn = QPushButton("Preview All Cameras")
        preview_btn.clicked.connect(self.toggle_preview)
        preview_btn.setFixedWidth(200)
        left_layout.addWidget(preview_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Right panel (sidebar)
        right_panel = QWidget()
        right_panel.setFixedWidth(250)
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("Calibration Controls"))
        
        # Status label
        self.status_label = QLabel("Ready to calibrate")
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        # Calibrate button
        self.calibrate_btn = QPushButton("Start Cube Calibration")
        self.calibrate_btn.clicked.connect(self.start_calibration)
        right_layout.addWidget(self.calibrate_btn)
        
        right_layout.addStretch()
        
        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        self.setLayout(main_layout)


    def toggle_preview(self):
        if not self.preview_active:
            for camera_view in self.camera_views:
                camera_view.start()
            self.preview_active = True
            self.sender().setText("Stop Preview")
        else:
            for camera_view in self.camera_views:
                camera_view.stop()
            self.preview_active = False
            self.sender().setText("Preview All Cameras")

    def start_calibration(self):
        if not self.preview_active:
            self.status_label.setText("Please start camera preview first")
            return
            
        self.calibrate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Collect frames from cameras
        frames = []
        for camera_view in self.camera_views:
            frame = camera_view.get_current_frame()  # Need to add this method to CameraView
            if frame is None:
                self.status_label.setText('Failed to capture frames from all cameras')
                self.calibrate_btn.setEnabled(True)
                return
            frames.append(frame)
        # Start calibration via ViewModel
        self.calibration_viewmodel.start_calibration(frames)

    def update_status(self, status):
        self.status_label.setText(status)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def handle_calibration_complete(self, success, message):
        self.status_label.setText(message)
        self.calibrate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)