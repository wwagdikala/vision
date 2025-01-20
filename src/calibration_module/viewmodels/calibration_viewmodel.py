# calibration_module/viewmodels/calibration_viewmodel.py

from PySide6.QtCore import QObject, Signal
from typing import List, Dict
import numpy as np
import cv2

from core.error_handling.exceptions import (
    CalibrationError,
    ErrorSeverity,
    ErrorCategory,
)
from services.service_locator import ServiceLocator
from core.constants.settings_constants import CalibrationTarget
from calibration_module.models.calibration_detector import CalibrationDetector


class CalibrationViewModel(QObject):
    # Signals used by the view
    status_changed = Signal(str)
    progress_updated = Signal(int)
    calibration_finished = Signal(bool, str, dict)  # success, message, results
    overlay_updated = Signal(list, dict)  # points, quality metrics per camera
    preview_state_changed = Signal(bool)  # True when preview is active
    quality_updated = Signal(dict)  # Quality metrics for current detection

    # Multi-view signals
    view_captured = Signal(int, int)  # current_view, total_views
    camera_status_updated = Signal(int, str)  # camera_id, status
    guidance_updated = Signal(str)  # Calibration guidance message

    # UI control signals
    button_enabled_changed = Signal(bool)  # Controls calibrate button enabled state
    button_text_changed = Signal(str)  # Controls calibrate button text
    progress_visible_changed = Signal(bool)  # Controls progress bar visibility

    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.settings_service = self.locator.get_service("settings_service")
        self.calibration_model = self.locator.get_service("calibration_model")
        self.error_manager = self.locator.get_service("error_manager")

        # State management
        self.is_calibrating = False
        self.preview_active = False
        self.required_views = int(
            self.settings_service.get_setting("calibration.required_angles")
        )

        # Runtime data
        self._current_detections = None
        self._current_quality = None
        self._detector = None

        self._initialize_detector()

    def _initialize_detector(self):
        """Initialize pattern detector based on settings."""
        try:
            target_type = self.settings_service.get_setting("calibration.target_type")
            self._detector = CalibrationDetector(target_type)
        except Exception as e:
            self.error_manager.report_error(
                SystemError(
                    ErrorSeverity.ERROR,
                    ErrorCategory.CALIBRATION,
                    f"Failed to initialize detector: {str(e)}",
                )
            )

    def set_preview_active(self, active: bool) -> bool:
        """
        Enable or disable preview mode.
        The view should handle actually turning on/off camera feeds.
        """
        self.preview_active = active
        self.preview_state_changed.emit(active)

        if active:
            self.status_changed.emit("Preview started - position calibration target")
        else:
            self._clear_overlay()
            self.status_changed.emit("Preview stopped")
        return True

    def start_calibration(self, frames: List[np.ndarray]) -> bool:

        try:
            num_cameras = len(frames)
            self.calibration_model.initialize_cameras(num_cameras)
            self.is_calibrating = True
            # Update UI state

            # self.button_enabled_changed.emit(False)
            self.progress_visible_changed.emit(True)
            self.progress_updated.emit(0)
            self.button_text_changed.emit("Capture View")
            # Process frames
            return self.process_frames(frames)
            # if self.process_frames(frames):
            #     self.button_text_changed.emit("Capture View")
            #     self.button_enabled_changed.emit(True)
            #     return True
            # else:
            #     self.button_enabled_changed.emit(True)
            #     return False

        except Exception as e:
            self.status_changed.emit(f"Calibration error: {str(e)}")
            self.button_enabled_changed.emit(True)
            self.progress_updated.emit(0)
            return False

    def process_frames(self, frames: List[np.ndarray]) -> bool:
        try:
            if not frames:
                raise ValueError("No frames provided")

            detections = []
            quality_metrics = {}

            for i, frame in enumerate(frames):
                try:
                    points_2d, points_3d = self._detector.detect(frame)
                    detections.append((points_2d, points_3d))
                    quality_metrics[i] = self._calculate_detection_quality(points_2d)
                    self.camera_status_updated.emit(
                        i, f"Pattern detected: {len(points_2d)} points"
                    )
                except Exception as e:
                    self.camera_status_updated.emit(i, f"Detection failed: {str(e)}")
                    return False

            # Debugging for overlay
            print("\nSending overlay update:")
            print(f"Number of detections: {len(detections)}")
            for i, det in enumerate(detections):
                shape_info = det[0].shape if det[0] is not None else "None"
                print(f"Camera {i} detection shape: {shape_info}")

            self._current_detections = detections
            self._current_quality = quality_metrics
            self.overlay_updated.emit(detections, quality_metrics)

            frame_data = [(frame, det[0]) for frame, det in zip(frames, detections)]
            if self._validate_detection_quality(quality_metrics):
                if self.calibration_model.process_view(frame_data):
                    # Get current progress from model

                    current_view = self.calibration_model.current_view
                    total_views = self.calibration_model.n_required_views
                    self.calibration_model.current_view += 1
                    # Update progress
                    progress = (current_view / total_views) * 100
                    self.progress_updated.emit(progress)

                    # Check if calibration is complete
                    if current_view >= total_views:
                        self.status_changed.emit("Performing global calibration...")
                        self.calibration_model.perform_global_calibration()
                    return True
            return False

        except Exception as e:
            self._handle_error("Frame processing failed", e)
            return False

    def capture_view(self) -> bool:
        """Capture current view if quality is acceptable."""
        if not self._current_detections or not self._current_quality:
            self.status_changed.emit("No valid detection to capture")
            return False

        try:
            if self._validate_detection_quality(self._current_quality):
                # Save to model
                self.calibration_model.save_angle_data(
                    self.current_view, self._current_detections, self._current_quality
                )

                self.current_view += 1
                self.view_captured.emit(self.current_view, self.required_views)

                progress = (self.current_view / self.required_views) * 100
                self.progress_updated.emit(progress)

                if self.current_view >= self.required_views:
                    return self._complete_calibration()
                else:
                    self._update_guidance()
                    return True
            else:
                self.status_changed.emit("Detection quality insufficient for capture")
                return False

        except Exception as e:
            self._handle_error("Failed to capture view", e)
            return False

    def _complete_calibration(self):
        """Complete the calibration process."""
        try:
            self.status_changed.emit("Performing final calibration...")
            results = self.calibration_model.perform_global_calibration()

            if self._validate_calibration_results(results):
                self.calibration_finished.emit(
                    True, "Calibration completed successfully", results
                )
                self.status_changed.emit("Calibration successful")
                # Optionally, store a success flag if you want the wizard to detect success
                setattr(self, "calibration_successful", True)
                return True
            else:
                self.calibration_finished.emit(
                    False, "Calibration failed accuracy requirements", results
                )
                self.status_changed.emit("Calibration failed - please retry")
                return False

        except Exception as e:
            self._handle_error("Calibration computation failed", e)
            self.calibration_finished.emit(False, str(e), None)
            return False

    def _calculate_detection_quality(self, points_2d: np.ndarray) -> dict:
        """Calculate quality metrics for detected points."""
        try:
            if points_2d is None or len(points_2d) == 0:
                return {"score": 0, "coverage": 0, "stability": 0}

            # Get frame dimensions from settings or use defaults
            frame_width = 1920
            frame_height = 1080

            # Calculate coverage
            rect = cv2.boundingRect(points_2d)
            pattern_area = rect[2] * rect[3]
            frame_area = frame_width * frame_height
            coverage = pattern_area / frame_area

            # Calculate point distribution
            center = np.mean(points_2d, axis=0)
            distances = np.linalg.norm(points_2d - center, axis=1)
            distribution = np.std(distances) / np.mean(distances)

            # Combined quality score
            quality_score = min(1.0, (coverage * 0.6 + (1.0 - distribution) * 0.4))

            return {
                "score": quality_score,
                "coverage": coverage,
                "stability": 1.0 - distribution,
            }

        except Exception as e:
            self._handle_error("Quality calculation failed", e)
            return {"score": 0, "coverage": 0, "stability": 0}

    def _validate_detection_quality(self, quality_metrics: Dict) -> bool:
        """Validate if detection quality is sufficient for capture."""
        try:
            min_quality_score = float(
                self.settings_service.get_setting("calibration.min_quality_score")
            )
            min_coverage = float(
                self.settings_service.get_setting("calibration.min_coverage")
            )

            print(f"\nValidating detection quality:")
            print(f"Minimum required score: {min_quality_score}")
            print(f"Minimum required coverage: {min_coverage}")

            valid_cameras = 0
            for cam_idx, metrics in quality_metrics.items():
                print(f"\nCamera {cam_idx}:")
                print(f"Score: {metrics['score']:.3f} (min: {min_quality_score})")
                print(f"Coverage: {metrics['coverage']:.3f} (min: {min_coverage})")

                if (
                    metrics["score"] >= min_quality_score
                    and metrics["coverage"] >= min_coverage
                ):
                    valid_cameras += 1
                    print(f"Camera {cam_idx} PASSED validation")
                else:
                    print(f"Camera {cam_idx} FAILED validation")

            is_valid = valid_cameras >= 2
            print(f"\nTotal valid cameras: {valid_cameras} (need at least 2)")
            print(f"Overall validation {'PASSED' if is_valid else 'FAILED'}")

            return is_valid

        except Exception as e:
            self._handle_error("Quality validation failed", e)
            print(f"Validation error: {str(e)}")
            return False

    def _validate_calibration_results(self, results: dict) -> bool:
        """Validate final calibration results."""
        try:
            if not results.get("success", False):
                return False

            # Check overall RMS error
            if results.get("overall_rms", float("inf")) > 1.0:  # threshold
                return False

            # Check per-camera RMS errors
            for cam_stats in results.get("per_camera", {}).values():
                if cam_stats.get("rms", float("inf")) > 1.5:  # threshold
                    return False

            return True

        except Exception as e:
            self._handle_error("Results validation failed", e)
            return False

    def _update_guidance(self):
        """Update user guidance based on the current state."""
        if not self.is_calibrating:
            return

        current = self.current_view
        total = self.required_views

        if current >= total:
            self.guidance_updated.emit(
                "All views captured. Ready for final calibration."
            )
            return

        messages = [
            "Place pattern in front view, slightly tilted",
            "Move pattern to the left side",
            "Move pattern to the right side",
            "Tilt pattern forward ~45°",
            "Tilt pattern backward ~45°",
            "Rotate pattern clockwise ~45°",
            "Rotate pattern counter-clockwise ~45°",
            "Move pattern closer to cameras",
            "Move pattern farther from cameras",
            "Place pattern at an arbitrary position",
        ]

        msg_idx = min(current, len(messages) - 1)
        guidance = (
            f"View {current + 1}/{total}: {messages[msg_idx]}\n"
            f"Ensure pattern is visible in at least two cameras"
        )
        self.guidance_updated.emit(guidance)

    def _clear_overlay(self):
        """Clear detection overlay."""
        self.overlay_updated.emit([], {})

    def _handle_error(self, context: str, error: Exception):
        """Handle and report errors."""
        error_msg = f"{context}: {str(error)}"
        system_error = SystemError(
            ErrorSeverity.ERROR, ErrorCategory.CALIBRATION, error_msg, error
        )
        self.error_manager.report_error(system_error)
        self.status_changed.emit(error_msg)
