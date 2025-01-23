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
    button_reset_changed = Signal(bool)  # Controls redetect button State
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
        self.current_view = 0
        self.calibration_successful = False

        # Runtime data
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

    def begin_calibration_session(self):
        """
        Reset everything to start capturing multiple views.
        """
        self.is_calibrating = True
        self.calibration_successful = False
        self.current_view = 0

        # Reset model data
        self.calibration_model.reset()

        # Update UI signals
        self.button_text_changed.emit("Capture View 1")
        self.button_enabled_changed.emit(True)
        self.progress_visible_changed.emit(True)
        self.progress_updated.emit(0)
        self.button_reset_changed.emit(True)
        self.status_changed.emit("Calibration started. Capture your first view.")
        self._update_guidance()

    def process_frames(self, frames: List[np.ndarray]) -> bool:
        """
        Capture/detect the pattern in these frames, store in model, increment current_view.
        If we've reached required_views, perform final calibration.
        """
        if not self.is_calibrating:
            self.status_changed.emit("Not in calibration mode.")
            return False
        if not frames:
            self.status_changed.emit("No frames provided.")
            return False

        try:
            # Detect pattern in each camera
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

            # Send overlay for debugging
            self.overlay_updated.emit(detections, quality_metrics)

            # Validate quality across cameras
            if not self._validate_detection_quality(quality_metrics):
                self.status_changed.emit("Detection quality insufficient")
                return False

            # Store data in the Model at the index = current_view
            success = self.calibration_model.process_view(
                view_idx=self.current_view,
                frame_data=[(frame, det[0]) for frame, det in zip(frames, detections)],
            )
            if not success:
                self.status_changed.emit("Failed to process view in model")
                return False

            # Mark this view as captured
            self.current_view += 1
            self.view_captured.emit(self.current_view, self.required_views)

            # Update progress bar
            progress_val = int((self.current_view / self.required_views) * 100)
            self.progress_updated.emit(progress_val)

            if self.current_view >= self.required_views:
                # All required views have been captured -> run global calibration
                self._complete_calibration()
            else:
                # Not done yet. Let user know which angle to do next.
                self.button_text_changed.emit(f"Capture View {self.current_view + 1}")
                self._update_guidance()

            return True

        except Exception as e:
            self._handle_error("Frame processing failed", e)
            return False

    def _complete_calibration(self):
        """Perform final steps: single camera calibrations + global bundle adjustment."""
        self.status_changed.emit("Performing global calibration...")
        results = self.calibration_model.perform_global_calibration()
        success = results.get("success", False)

        if success:
            try:
                calibration_storage = self.locator.get_service("calibration_storage")
                calibration_storage.store_calibration(
                    camera_matrices=self.calibration_model.camera_matrices,
                    dist_coeffs=self.calibration_model.dist_coeffs,
                    rotations=self.calibration_model.rotations,
                    translations=self.calibration_model.translations,
                )
                print("Calibration results stored successfully")
            except Exception as e:
                print(f"Failed to store calibration: {str(e)}")
            # Continue with emit since calibration itself was successful
            self.calibration_successful = True
            self.calibration_finished.emit(
                True, "Calibration completed successfully", results
            )
            self.status_changed.emit("Calibration successful!")
        else:
            self.calibration_finished.emit(
                False, "Calibration failed accuracy requirements", results
            )
            self.status_changed.emit("Calibration failed - please retry")

        self.is_calibrating = False

    def _calculate_detection_quality(self, points_2d: np.ndarray) -> dict:
        """Calculate some simple quality metrics for the detected points."""
        try:
            if points_2d is None or len(points_2d) == 0:
                return {"score": 0, "coverage": 0, "stability": 0}

            frame_width = 1920
            frame_height = 1080

            # coverage
            rect = cv2.boundingRect(points_2d)
            pattern_area = rect[2] * rect[3]
            frame_area = frame_width * frame_height
            coverage = pattern_area / frame_area if frame_area > 0 else 0

            # distribution
            center = np.mean(points_2d, axis=0)
            distances = np.linalg.norm(points_2d - center, axis=1)
            distribution = (
                np.std(distances) / np.mean(distances) if np.mean(distances) > 0 else 1
            )

            # simple score
            quality_score = min(1.0, coverage * 0.6 + (1.0 - distribution) * 0.4)

            return {
                "score": quality_score,
                "coverage": coverage,
                "stability": 1.0 - distribution,
            }
        except Exception as e:
            self._handle_error("Quality calculation failed", e)
            return {"score": 0, "coverage": 0, "stability": 0}

    def _validate_detection_quality(self, quality_metrics: Dict) -> bool:
        """Validate if detection quality is sufficient."""
        try:
            min_quality_score = float(
                self.settings_service.get_setting("calibration.min_quality_score")
            )
            min_coverage = float(
                self.settings_service.get_setting("calibration.min_coverage")
            )

            valid_cameras = 0
            for cam_idx, metrics in quality_metrics.items():
                score_ok = metrics["score"] >= min_quality_score
                coverage_ok = metrics["coverage"] >= min_coverage
                if score_ok and coverage_ok:
                    valid_cameras += 1

            # For multi-camera systems, you might require at least 2 cameras pass
            # or that ALL cameras pass. For now, let's say at least 2 must pass:
            return valid_cameras >= 2

        except Exception as e:
            self._handle_error("Quality validation failed", e)
            return False

    def _update_guidance(self):
        """Provide guidance text based on the current view index."""
        if not self.is_calibrating:
            return

        total = self.required_views
        current = self.current_view
        if current >= total:
            self.guidance_updated.emit(
                "All views captured. Running final calibration..."
            )
            return

        # Some example guidance
        messages = [
            "Place pattern front-and-center, slightly tilted",
            "Move pattern left or tilt left ~30°",
            "Move pattern right or tilt right ~30°",
            "Tilt forward/backward ~45°",
            "Rotate pattern around its axis ~45°",
            "Move pattern closer or further from cameras",
            "Try an arbitrary orientation for coverage",
        ]

        # Limit the index for messages
        msg_idx = min(current, len(messages) - 1)
        guidance = f"View {current + 1}/{total}: {messages[msg_idx]}"
        self.guidance_updated.emit(guidance)

    def _clear_overlay(self):
        """Clear detection overlays."""
        self.overlay_updated.emit([], {})

    def _handle_error(self, context: str, error: Exception):
        """Handle and report errors."""
        error_msg = f"{context}: {str(error)}"
        system_error = SystemError(
            ErrorSeverity.ERROR, ErrorCategory.CALIBRATION, error_msg, error
        )
        self.error_manager.report_error(system_error)
        self.status_changed.emit(error_msg)

    def reset_calibration(self):
        """Reset calibration state and clear all data."""
        print("Resetting calibration state")
        self.is_calibrating = False
        self.calibration_successful = False
        self.current_view = 0
        self.calibration_model.reset()
        self.status_changed.emit("Calibration reset")
        self._clear_overlay()
        self.button_text_changed.emit("Start Calibration")
        self.button_enabled_changed.emit(True)
        self.button_reset_changed.emit(False)
        self.progress_visible_changed.emit(False)
        self.guidance_updated.emit("")
        self.camera_status_updated.emit(0, "")
        self.camera_status_updated.emit(1, "")
