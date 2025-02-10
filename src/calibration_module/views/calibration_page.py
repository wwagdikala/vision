from PySide6.QtWidgets import (
    QWizardPage,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QLabel,
    QPushButton,
    QProgressBar,
    QGroupBox,
)
from PySide6.QtCore import Qt
import numpy as np

from services.service_locator import ServiceLocator
from camera_module.views.camera_view import CameraView
from core.constants.settings_constants import CalibrationTarget, CameraSetup


class CalibrationPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("System Calibration")
        self.setSubTitle("Set up cameras and perform calibration")

        # Get dependencies
        self.locator = ServiceLocator.get_instance()
        self.settings_service = self.locator.get_service("settings_service")
        self.calibration_viewmodel = self.locator.get_service("calibration_viewmodel")

        # Connect signals from ViewModel
        self._connect_viewmodel_signals()

        # Initialize settings-dependent attributes
        self.camera_setup = self.settings_service.get_setting("cameras.camera_setup")
        self.target_type = self.settings_service.get_setting("calibration.target_type")
        self.preview_active = False

        self.setup_ui()
        self.update_instructions()
        self.setup_bindings()

    def _connect_viewmodel_signals(self):
        self.calibration_viewmodel.status_changed.connect(self.update_status)
        self.calibration_viewmodel.progress_updated.connect(self.update_progress)
        self.calibration_viewmodel.calibration_finished.connect(
            self.handle_calibration_complete
        )
        self.calibration_viewmodel.overlay_updated.connect(self._update_camera_overlays)
        self.calibration_viewmodel.camera_status_updated.connect(
            self.update_camera_status
        )
        self.calibration_viewmodel.view_captured.connect(self.handle_view_captured)
        self.calibration_viewmodel.guidance_updated.connect(self.update_guidance)

    def setup_ui(self):
        main_layout = QHBoxLayout()

        # Left panel (cameras and controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Camera views section
        camera_group = QGroupBox("Camera Views")
        camera_layout = QGridLayout()

        self.camera_views = []

        self.camera_status_labels = []
        num_cameras = CameraSetup.get_num_cameras(self.camera_setup)

        for i in range(num_cameras):
            container = QWidget()
            container_layout = QVBoxLayout(container)

            # Camera view
            camera_view = self.create_camera_view(i)
            container_layout.addWidget(camera_view)

            # Status label
            status_label = QLabel("Camera not started")
            status_label.setStyleSheet("color: gray;")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(status_label)

            self.camera_status_labels.append(status_label)
            camera_layout.addWidget(container, 0, i)

        camera_group.setLayout(camera_layout)
        left_layout.addWidget(camera_group)

        # Camera controls
        controls_layout = QHBoxLayout()
        self.preview_btn = QPushButton("Preview All Cameras")
        self.preview_btn.clicked.connect(self.toggle_preview)
        self.preview_btn.setFixedWidth(150)
        controls_layout.addWidget(self.preview_btn)

        self.calibrate_btn = QPushButton("Start Calibration")
        self.calibrate_btn.clicked.connect(self.on_calibrate_clicked)
        self.calibrate_btn.setFixedWidth(150)
        self.calibrate_btn.setEnabled(False)
        controls_layout.addWidget(self.calibrate_btn)

        self.re_calibrate_btn = QPushButton("Resetart Calibration")
        self.re_calibrate_btn.clicked.connect(self.on_re_calibrate_clicked)
        self.re_calibrate_btn.setFixedWidth(150)
        self.re_calibrate_btn.setEnabled(False)
        controls_layout.addWidget(self.re_calibrate_btn)

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

        # View progress
        self.view_progress = QLabel("Views: 0/0")
        status_layout.addWidget(self.view_progress)

        self.status_label = QLabel("Ready to start")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        # Results section
        self.results_label = QLabel()
        self.results_label.setWordWrap(True)
        self.results_label.setVisible(False)
        status_layout.addWidget(self.results_label)

        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)
        right_layout.addStretch()

        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        self.setLayout(main_layout)

    def setup_bindings(self):
        """
        Example of extra bindings to ViewModel signals that control button & progress UI directly.
        """
        self.calibration_viewmodel.button_enabled_changed.connect(
            self.calibrate_btn.setEnabled
        )
        self.calibration_viewmodel.button_text_changed.connect(
            self.calibrate_btn.setText
        )
        self.calibration_viewmodel.progress_visible_changed.connect(
            self.progress_bar.setVisible
        )
        self.calibration_viewmodel.button_reset_changed.connect(
            self.re_calibrate_btn.setEnabled
        )

    def toggle_preview(self):
        if not self.preview_active:
            success = True
            for i, camera_view in enumerate(self.camera_views):
                if not camera_view.start():
                    success = False
                    break
                else:
                    self.update_camera_status(i, "Camera active")

            if success:
                self.preview_active = True
                self.preview_btn.setText("Stop Preview")
                self.calibrate_btn.setEnabled(True)
                self.calibration_viewmodel.set_preview_active(True)
            else:
                self.status_label.setText("Failed to start all cameras")
        else:
            # Stop all cameras
            for i, camera_view in enumerate(self.camera_views):
                camera_view.stop()
                self.update_camera_status(i, "Camera stopped")

            self.preview_active = False
            self.preview_btn.setText("Preview All Cameras")
            self.calibrate_btn.setEnabled(False)
            self.calibration_viewmodel.set_preview_active(False)

    def on_calibrate_clicked(self):
        if not self.calibration_viewmodel.is_calibrating:
            # Initialize and start the calibration session
            self.calibration_viewmodel.begin_calibration_session()
            self.capture_new_view()
        else:
            # We are already calibrating, so just capture the next angle
            self.capture_new_view()

    def on_re_calibrate_clicked(self):
        if self.calibration_viewmodel.is_calibrating:
            self.calibration_viewmodel.reset_calibration()

    def capture_new_view(self):
        frames = []
        for i, camera_view in enumerate(self.camera_views):
            frame = camera_view.get_current_frame()
            if frame is None:
                self.update_status(f"Failed to capture frame from camera {i+1}")
                return
            frames.append(frame)

        self.calibration_viewmodel.process_frames(frames)

    def update_camera_status(self, camera_id: int, status: str):
        if 0 <= camera_id < len(self.camera_status_labels):
            label = self.camera_status_labels[camera_id]
            if "failed" in status.lower():
                label.setStyleSheet("color: red;")
            elif "detected" in status.lower():
                label.setStyleSheet("color: green;")
            else:
                label.setStyleSheet("color: gray;")
            label.setText(status)

    def handle_view_captured(self, current: int, total: int):
        self.view_progress.setText(f"Views: {current}/{total}")
        if current >= total:
            # All views captured, button might say "Complete" or be disabled
            self.calibrate_btn.setText("Calibrating...")
            self.calibrate_btn.setEnabled(False)
        else:
            self.calibrate_btn.setText(f"Capture View {current + 1}")

    def update_guidance(self, guidance: str):
        # We might add a separate label for guidance if you like
        # For now, let's just reuse the status_label or a new label
        self.status_label.setText(guidance)

    def _format_calibration_results(self, results: dict) -> str:
        text = "Calibration Results:\n\n"
        if "overall_rms" in results:
            text += f"Overall RMS Error: {results['overall_rms']:.3f} px\n\n"

        if "overall_rms_mm" in results:
            text += (
                f"Overall RMS Error (real-world): {results['overall_rms_mm']:.3f} mm\n"
            )

        if "per_camera" in results:
            text += "Per-Camera Results:\n"
            for cam_id, stats in results["per_camera"].items():
                text += f"\nCamera {cam_id}:\n"
                text += f"- RMS Error: {stats['rms']:.3f} px\n"
                text += f"- Valid Views: {stats.get('n_views', 0)}\n"
        if "baseline" in results:
            text += "\nCamera Baselines:\n"
            for pair, distance in results["baseline"].items():
                text += f"Cameras {pair}: {distance:.2f} mm\n"
        return text

    def update_status(self, status: str):
        self.status_label.setText(status)

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)

    def _update_camera_overlays(self, detections, quality):
        try:
            for i, camera_view in enumerate(self.camera_views):
                # Default to "no points" (empty) and empty quality
                detection_data = None
                detection_quality = {}

                # If we actually have a detection for camera i, use it
                if i < len(detections) and isinstance(detections[i], tuple):
                    detection_data = detections[i][0]  # the 2D points
                    detection_quality = quality.get(i, {})

                # Always call update_overlay, so cameras with no detection get cleared
                camera_view.update_overlay(detection_data, detection_quality)

        except Exception as e:
            print(f"Overlay error: {str(e)}")
            self.status_label.setText(f"Error updating overlays: {str(e)}")

    def create_camera_view(self, camera_id):
        camera_view = CameraView(
            self.locator.get_service(f"camera_viewmodel_{camera_id}")
        )
        camera_view.setMinimumSize(640, 480)
        camera_view.setStyleSheet(
            """
            QLabel {
                background-color: black;
                border: 1px solid #666;
                color: white;
            }
            """
        )
        self.camera_views.append(camera_view)
        return camera_view

    def update_instructions(self):
        """Update instructions based on target type."""
        instructions = "1. Click 'Preview All Cameras' to start camera feeds\n\n"

        if self.target_type == CalibrationTarget.CUBE.value:
            instructions += (
                "2. Place the calibration cube in the working volume\n"
                "3. Ensure the cube is visible in all cameras\n"
                "4. Check that cube corners are well-lit and visible\n"
                "5. Click 'Start Calibration' when ready (and follow instructions)"
            )
        else:  # CHECKERBOARD
            instructions += (
                "2. Hold the checkerboard in the working volume\n"
                "3. Ensure the pattern is fully visible\n"
                "4. Avoid reflections and ensure good lighting\n"
                "5. Click 'Start Calibration' when ready (and follow instructions)"
            )

        self.instructions_label.setText(instructions)

    def isComplete(self) -> bool:
        return (
            hasattr(self.calibration_viewmodel, "calibration_successful")
            and self.calibration_viewmodel.calibration_successful
        )

    def handle_calibration_complete(self, success: bool, message: str, results: dict):
        """Handle calibration completion signal from the ViewModel."""
        self.status_label.setText(message)
        self.calibrate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        if success and results:
            results_text = self._format_calibration_results(results)
            self.results_label.setText(results_text)
            self.results_label.setVisible(True)

        # If you want the wizard to move on automatically when calibration succeeds:
        if success and self.isComplete():
            self.completeChanged.emit()
