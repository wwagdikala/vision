# measurement_module/views/measurement_view.py
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QTabWidget,
    QMessageBox,
)

from PySide6.QtCore import Qt, QTimer
from services.service_locator import ServiceLocator
from camera_module.views.camera_view import CameraView
from measurement_module.views.visualization_view import VisualizationView
import os



class MeasurementView(QWidget):
    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.viewmodel = self.locator.get_service("measurement_viewmodel")
        self.preview_active = False
        self.measuring_active = False 
        calibration_storage = self.locator.get_service("calibration_storage")

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create and add manual measurement tab
        self.manual_tab = QWidget()
        self.setup_manual_tab()
        self.tab_widget.addTab(self.manual_tab, "Manual Measurement")

        # Create and add 3D visualization tab
        self.visual_tab = QWidget()
        self.setup_visual_tab()
        self.tab_widget.addTab(self.visual_tab, "3D Visualization")

        main_layout.addWidget(self.tab_widget)

    def setup_manual_tab(self):
        """Set up the manual measurement tab - keeping existing functionality"""
        layout = QHBoxLayout(self.manual_tab)

        # Left panel with cameras
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        camera_group = QGroupBox("Camera Views")
        camera_layout = QGridLayout()

        self.camera_views = []
        num_cameras = self.viewmodel.get_camera_count()

        for i in range(num_cameras):
            view = self.create_camera_view(i)
            camera_layout.addWidget(view, i // 2, i % 2)
            self.camera_views.append(view)

        camera_group.setLayout(camera_layout)
        left_layout.addWidget(camera_group)

        # Controls
        controls_layout = QHBoxLayout()
        self.preview_btn = QPushButton("Start Preview")
        self.measure_btn = QPushButton("Start Measuring")
        self.measure_btn.setEnabled(False)

        controls_layout.addWidget(self.preview_btn)
        controls_layout.addWidget(self.measure_btn)
        left_layout.addLayout(controls_layout)

        # Right panel
        right_panel = QWidget()
        right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout(right_panel)

        # Instructions
        instructions_group = QGroupBox("Instructions")
        instructions_layout = QVBoxLayout()
        self.instructions_label = QLabel(
            "1. Click 'Start Preview' to view cameras\n"
            "2. Click 'Start Measuring' to begin\n"
            "3. Click two points in the views to measure distance"
        )
        self.instructions_label.setWordWrap(True)
        instructions_layout.addWidget(self.instructions_label)
        instructions_group.setLayout(instructions_layout)
        right_layout.addWidget(instructions_group)

        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Ready to start")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)

        # Results
        results_group = QGroupBox("Measurement Results")
        results_layout = QVBoxLayout()
        self.results_label = QLabel("No measurements yet")
        self.results_label.setWordWrap(True)
        results_layout.addWidget(self.results_label)
        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group)

        right_layout.addStretch()

        # Add panels to layout
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)

    def setup_visual_tab(self):
        layout = QVBoxLayout(self.visual_tab)
    
        self.vis_view = VisualizationView()
        layout.addWidget(self.vis_view)
    
        controls_layout = QHBoxLayout()
    
        self.capture_btn = QPushButton("Start Capture")
        self.capture_btn.clicked.connect(self.toggle_point_cloud_capture)
        controls_layout.addWidget(self.capture_btn)
    
        # Status label
        self.visual_status_label = QLabel("3D visualization ready")
        controls_layout.addWidget(self.visual_status_label)
        controls_layout.addStretch()
    
        layout.addLayout(controls_layout)

    def create_camera_view(self, camera_id):
        view = CameraView(self.locator.get_service(f"camera_viewmodel_{camera_id}"))
        view.setMinimumSize(640, 480)
        return view

    def connect_signals(self):
        self.preview_btn.clicked.connect(self.toggle_preview)
        self.measure_btn.clicked.connect(self.toggle_measuring)

        self.viewmodel.measurement_updated.connect(self.update_results)
        self.viewmodel.status_changed.connect(
            self.update_status
        )  # Now we have update_status

    def toggle_preview(self):
        if not self.preview_active:
            if self.viewmodel.start_preview():
                self.preview_active = True  # Update state
                self.preview_btn.setText("Stop Preview")
                self.measure_btn.setEnabled(True)

                # Start all camera views
                for view in self.camera_views:
                    view.start()
        else:
            self.preview_active = False  # Update state
            self.viewmodel.stop_preview()
            self.preview_btn.setText("Start Preview")
            self.measure_btn.setEnabled(False)

            # Stop all camera views
            for view in self.camera_views:
                view.stop()

    def toggle_measuring(self):
        if not self.measuring_active:
            self.measuring_active = True
            self.measure_btn.setText("Stop Measuring")
            self.viewmodel.start_measuring()
        else:
            self.measuring_active = False
            self.measure_btn.setText("Start Measuring")
            self.viewmodel.stop_measuring()

    def update_results(self, distance):
        self.results_label.setText(f"Distance: {distance:.2f} mm")

    def update_status(self, status: str):  # Add the missing method
        self.status_label.setText(status)

    def toggle_point_cloud_capture(self):
        if self.capture_btn.text() == "Start Capture":
            self.start_point_cloud_capture()
        else:
            self.stop_point_cloud_capture()

    def start_point_cloud_capture(self):
        # Start cameras if not already running
        if not self.preview_active:
            if not self.viewmodel.start_preview():
                self.visual_status_label.setText("Failed to start cameras")
                return
            self.preview_active = True
    
        # Start capture timer for periodic updates
        self.point_cloud_timer = QTimer()
        self.point_cloud_timer.timeout.connect(self.update_point_cloud)
        self.point_cloud_timer.start(100)  # Update every 100ms
    
        self.capture_btn.setText("Stop Capture")
        self.visual_status_label.setText("Capturing point cloud...")
    
    def stop_point_cloud_capture(self):
        if hasattr(self, 'point_cloud_timer'):
            self.point_cloud_timer.stop()
        
        # Clear the point cloud
        self.vis_view.clear_point_cloud()
        
        self.capture_btn.setText("Start Capture")
        self.visual_status_label.setText("Capture stopped")
    
    def update_point_cloud(self):
        try:
            # Get current frames from all cameras
            frames = []
            for camera_view in self.camera_views:
                frame = camera_view.get_current_frame()
                if frame is None:
                    self.visual_status_label.setText("Failed to get camera frame")
                    return
                frames.append(frame)
            
            # Update the visualization
            self.vis_view.update_point_cloud(frames)
            
        except Exception as e:
            self.visual_status_label.setText(f"Error updating point cloud: {str(e)}")