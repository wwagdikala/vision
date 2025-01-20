# calibration_module/models/calibration_model.py
from calibration_module.models.bundle_adjustment import (
    BundleAdjustment,
    CameraParameters,
)
from typing import List, Tuple, Optional
from PySide6.QtCore import QObject, Signal
from services.service_locator import ServiceLocator
from core.error_handling.exceptions import CalibrationError
import numpy as np
import cv2


class CalibrationModel(QObject):
    calibration_status = Signal(str)
    calibration_progress = Signal(int)
    calibration_complete = Signal(bool, str, dict)

    def __init__(self):
        super().__init__()
        # Existing initialization
        self.settings_service = ServiceLocator.get_instance().get_service(
            "settings_service"
        )

        # Add new attributes for multi-view calibration
        self.n_cameras = 0
        self.n_required_views = int(
            self.settings_service.get_setting("calibration.required_angles")
        )
        self.current_view = 0

        # Storage for calibration data
        self.camera_matrices = []  # Per-camera intrinsics
        self.dist_coeffs = []  # Per-camera distortion
        self.rotations = []  # Add storage for rotations
        self.translations = []  # Add storage for translations
        self.object_points = []  # 3D points for each view
        self.image_points = []  # 2D points per camera per view
        self.valid_views = []  # Track which views are valid for each camera

    def initialize_cameras(self, n_cameras: int):
        """Initialize storage for N cameras"""
        self.n_cameras = n_cameras
        self.image_points = [[] for _ in range(n_cameras)]
        self.valid_views = [set() for _ in range(n_cameras)]

    def calibrate_single_cameras(self):
        """Perform single-camera calibration for each camera"""
        self.camera_matrices = []
        self.dist_coeffs = []
        self.rotations = []  # Add storage for rotations
        self.translations = []  # Add storage for translations

        for cam_idx in range(self.n_cameras):
            # Get valid object and image points for this camera
            valid_views = list(self.valid_views[cam_idx])
            if not valid_views:
                raise CalibrationError(f"No valid views for camera {cam_idx}")

            obj_points = [self.object_points[v] for v in valid_views]
            img_points = [self.image_points[cam_idx][v] for v in valid_views]

            # Get image size from first valid view
            img_size = img_points[0].shape[::-1]

            # Calibrate single camera
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                obj_points, img_points, img_size, None, None
            )

            if not ret:
                raise CalibrationError(
                    f"Single camera calibration failed for camera {cam_idx}"
                )

            self.camera_matrices.append(mtx)
            self.dist_coeffs.append(dist)

            self.rotations.append(rvecs[-1])
            self.translations.append(tvecs[-1])

            self.calibration_status.emit(
                f"Camera {cam_idx} calibrated: RMS = {ret:.3f}"
            )
            print(f"Camera {cam_idx} calibrated: RMS = {ret:.3f}")

    def process_view(
        self, frame_data: List[Tuple[np.ndarray, Optional[np.ndarray]]]
    ) -> bool:
        """
        Process a new view from all cameras
        Args:
            frame_data: List of (frame, detected_points) tuples for each camera
        Returns:
            bool: True if the view was successfully processed
        """
        if self.current_view >= self.n_required_views:
            return False

        # Add object points for this view if needed
        if len(self.object_points) <= self.current_view:
            # Get pattern size from settings
            rows = int(self.settings_service.get_setting("calibration.pattern_rows"))
            cols = int(self.settings_service.get_setting("calibration.pattern_cols"))
            square_size = float(
                self.settings_service.get_setting("calibration.square_size")
            )

            # Create object points for checkerboard pattern
            objp = np.zeros((rows * cols, 3), np.float32)
            objp[:, :2] = np.mgrid[0:rows, 0:cols].T.reshape(-1, 2) * square_size
            self.object_points.append(objp)

        # Process detections from each camera
        valid_detections = 0
        for cam_idx, (frame, points) in enumerate(frame_data):
            if points is not None:
                # Store points in correct format
                points = np.array(points, dtype=np.float32).reshape(-1, 2)
                if len(self.image_points) <= cam_idx:
                    self.image_points.append([])
                self.image_points[cam_idx].append(points)
                self.valid_views[cam_idx].add(self.current_view)
                valid_detections += 1
            else:
                if len(self.image_points) <= cam_idx:
                    self.image_points.append([])
                self.image_points[cam_idx].append(None)

        self.current_view += 1
        return valid_detections >= 2  # Minimum 2 cameras needed

    def perform_global_calibration(self):
        """Perform global bundle adjustment"""
        try:
            # First perform single camera calibration
            self.calibrate_single_cameras()

            # Initialize bundle adjustment
            ba = BundleAdjustment()

            # Create camera parameters
            cameras = []
            for i in range(self.n_cameras):
                # Use identity rotation and zero translation as initial guess
                cam = CameraParameters(
                    camera_matrix=self.camera_matrices[i],
                    dist_coeffs=self.dist_coeffs[i],
                    rvec=self.rotations[i],  # From single camera calibration
                    tvec=self.translations[i],  # From single camera calibration
                )
                cameras.append(cam)

            # Set up and run optimization
            ba.set_camera_parameters(cameras)
            ba.set_calibration_data(self.object_points, self.image_points)

            results = ba.optimize(verbose=True)

            if results["success"]:
                # Format results for UI
                summary = self._format_calibration_results(results)
                self.calibration_complete.emit(True, "Calibration successful", summary)
            else:
                self.calibration_complete.emit(
                    False, "Global optimization failed", results
                )

        except Exception as e:
            self.calibration_complete.emit(False, f"Calibration failed: {str(e)}", {})

    def _format_calibration_results(self, results: dict) -> dict:
        """Format calibration results for display"""
        summary = {
            "overall_rms": results["overall_rms"],
            "per_camera": {},
            "baseline": {},  # For stereo measurements
        }

        # Per-camera statistics
        for cam_idx, stats in results["camera_stats"].items():
            summary["per_camera"][cam_idx] = {
                "rms": stats["rms"],
                "n_views": stats["n_valid_views"],
                "max_error": stats["max_error"],
            }

        # Calculate baselines between cameras
        optimized_cameras = results["optimized_cameras"]
        for i in range(len(optimized_cameras) - 1):
            for j in range(i + 1, len(optimized_cameras)):
                # Compute relative transformation
                R1, _ = cv2.Rodrigues(optimized_cameras[i].rvec)
                R2, _ = cv2.Rodrigues(optimized_cameras[j].rvec)
                t1 = optimized_cameras[i].tvec
                t2 = optimized_cameras[j].tvec

                # Relative transformation
                R_rel = R2 @ R1.T
                t_rel = t2 - R_rel @ t1

                # Calculate baseline
                baseline = np.linalg.norm(t_rel)
                summary["baseline"][f"{i}-{j}"] = baseline

        return summary
