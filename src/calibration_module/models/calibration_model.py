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
        self.settings_service = ServiceLocator.get_instance().get_service(
            "settings_service"
        )
        # Store camera data
        self.n_cameras = 0
        self.camera_matrices = []
        self.dist_coeffs = []
        self.rotations = []
        self.translations = []

        # Multi-view data
        self.object_points = []
        self.image_points = []
        self.valid_views = []
        self._detector_initialized = False

    def reset(self):
        """
        Clear all stored calibration data so we can start fresh.
        """
        self.n_cameras = 0
        self.camera_matrices = []
        self.dist_coeffs = []
        self.rotations = []
        self.translations = []
        self.object_points = []
        self.image_points = []
        self.valid_views = []

    def initialize_cameras(self, n_cameras: int):
        """Initialize storage for N cameras (if not done)."""
        self.n_cameras = n_cameras
        # image_points[camera_index] = [view_0_points, view_1_points, ...]
        self.image_points = [[] for _ in range(n_cameras)]
        self.valid_views = [set() for _ in range(n_cameras)]

    def process_view(
        self,
        view_idx: int,
        frame_data: List[Tuple[np.ndarray, Optional[np.ndarray]]],
    ) -> bool:
        """
        Store one "view" of data from multiple cameras (if detected).
        Args:
            view_idx: The index of the current view (0-based).
            frame_data: List of (frame, detected_points_2d) for each camera.
        Returns:
            bool: True if at least 2 cameras had valid detections
        """
        # Make sure we know how many cameras we have
        n_cameras = len(frame_data)
        if self.n_cameras == 0:
            self.initialize_cameras(n_cameras)
        elif self.n_cameras != n_cameras:
            raise CalibrationError(
                f"Inconsistent camera count: expected {self.n_cameras}, got {n_cameras}"
            )

        # Ensure object_points list is long enough to store this view
        if len(self.object_points) <= view_idx:
            # Construct object points based on the pattern size
            rows = int(self.settings_service.get_setting("calibration.pattern_rows"))
            cols = int(self.settings_service.get_setting("calibration.pattern_cols"))
            square_size = float(
                self.settings_service.get_setting("calibration.square_size")
            )
            objp = np.zeros((rows * cols, 3), np.float32)
            objp[:, :2] = np.mgrid[0:rows, 0:cols].T.reshape(-1, 2) * square_size
            self.object_points.append(objp)

        valid_detections = 0
        for cam_idx, (frame, points_2d) in enumerate(frame_data):
            if len(self.image_points) <= cam_idx:
                self.image_points.append([])

            # Expand the list so image_points[cam_idx] has an entry for each view
            while len(self.image_points[cam_idx]) <= view_idx:
                self.image_points[cam_idx].append(None)

            if points_2d is not None and len(points_2d) > 0:
                # Convert to float32 shape (N,2)
                points_2d = np.array(points_2d, dtype=np.float32).reshape(-1, 2)
                self.image_points[cam_idx][view_idx] = points_2d
                self.valid_views[cam_idx].add(view_idx)
                valid_detections += 1
            else:
                self.image_points[cam_idx][view_idx] = None

        # Return True if at least 2 cameras had valid detections
        return valid_detections >= 2

    def calibrate_single_cameras(self):
        """
        Perform individual camera calibration for each camera,
        using the views where that camera had valid detections.
        """
        self.camera_matrices = []
        self.dist_coeffs = []
        self.rotations = []
        self.translations = []

        for cam_idx in range(self.n_cameras):
            valid_views = list(self.valid_views[cam_idx])
            if not valid_views:
                raise CalibrationError(f"No valid views for camera {cam_idx}")

            # Gather obj_points and img_points for the valid views
            obj_points_list = [self.object_points[v] for v in valid_views]
            img_points_list = [self.image_points[cam_idx][v] for v in valid_views]

            # Use the size of the first valid detection as the image size
            # (or you can store actual frame size if you like)
            some_points = img_points_list[0]
            # We need (width, height) as a tuple
            # If we don't have the real frame shape, we can guess or store it earlier
            # For now, let's guess a typical HD size:
            img_size = (1920, 1080)
            if some_points is not None and len(some_points) > 0:
                pass  # If you want to do more logic, do it here

            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                obj_points_list, img_points_list, img_size, None, None
            )
            if not ret:
                raise CalibrationError(
                    f"Single camera calibration failed for camera {cam_idx}"
                )

            self.camera_matrices.append(mtx)
            self.dist_coeffs.append(dist)

            # Store the last rvec/tvec, or average them. We'll just store the last one:
            self.rotations.append(rvecs[-1])
            self.translations.append(tvecs[-1])

    def perform_global_calibration(self):
        """
        Perform single-camera calibration first, then run bundle adjustment for multi-camera.
        Returns: dict with results
        """
        try:
            # Single-camera calibration
            self.calibrate_single_cameras()

            # Now run global optimization
            ba = BundleAdjustment()
            cameras = []
            for i in range(self.n_cameras):
                cam = CameraParameters(
                    camera_matrix=self.camera_matrices[i],
                    dist_coeffs=self.dist_coeffs[i],
                    rvec=self.rotations[i],
                    tvec=self.translations[i],
                )
                cameras.append(cam)

            ba.set_camera_parameters(cameras)
            ba.set_calibration_data(self.object_points, self.image_points)

            results = ba.optimize(verbose=False)
            if results["success"]:
                # Format results nicely
                summary = self._format_calibration_results(results)

                return summary
            else:
                return {
                    "success": False,
                    "message": "Global optimization failed",
                    "overall_rms": float("inf"),
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_calibration_results(self, results: dict) -> dict:
        """Format calibration results for display in the UI."""
        summary = {
            "success": results["success"],
            "overall_rms": results["overall_rms"],
            "overall_rms_mm": results.get("overall_rms_mm"),
            "per_camera": {},
            "baseline": {},
        }

        # Copy over camera_stats
        for cam_idx, stats in results["camera_stats"].items():
            summary["per_camera"][cam_idx] = {
                "rms": stats["rms"],
                "n_views": stats["n_valid_views"],
                "max_error": stats["max_error"],
            }

        # Compute pairwise baselines
        optimized_cameras = results["optimized_cameras"]
        for i in range(len(optimized_cameras) - 1):
            for j in range(i + 1, len(optimized_cameras)):
                R1, _ = cv2.Rodrigues(optimized_cameras[i].rvec)
                R2, _ = cv2.Rodrigues(optimized_cameras[j].rvec)
                t1 = optimized_cameras[i].tvec
                t2 = optimized_cameras[j].tvec

                R_rel = R2 @ R1.T
                t_rel = t2 - R_rel @ t1
                baseline = np.linalg.norm(t_rel)
                summary["baseline"][f"{i}-{j}"] = baseline

        return summary
