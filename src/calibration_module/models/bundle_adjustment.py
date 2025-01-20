# calibration_module/models/bundle_adjustment.py
import numpy as np
from scipy.optimize import least_squares
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Set
import cv2


@dataclass
class CameraParameters:
    """Container for camera parameters"""

    camera_matrix: np.ndarray  # 3x3 intrinsic matrix
    dist_coeffs: np.ndarray  # Distortion coefficients
    rvec: np.ndarray  # Rotation vector (Rodrigues)
    tvec: np.ndarray  # Translation vector


class BundleAdjustment:
    def __init__(self):
        self.cameras: List[CameraParameters] = []
        self.object_points: List[np.ndarray] = []
        self.image_points: List[List[Optional[np.ndarray]]] = (
            []
        )  # [camera][view][point]
        self.valid_views: List[Set[int]] = []  # Set of valid view indices per camera
        self.n_cameras = 0
        self.n_views = 0
        self.n_points = 0

    def set_camera_parameters(self, cameras: List[CameraParameters]):
        self.cameras = cameras
        self.n_cameras = len(cameras)
        self.valid_views = [set() for _ in range(self.n_cameras)]

    def set_calibration_data(
        self,
        object_points: List[np.ndarray],
        image_points: List[List[Optional[np.ndarray]]],
    ):
        """
        Set calibration points data, handling partial visibility
        Args:
            object_points: List of object points for each view
            image_points: List of image points per camera and view, None for invalid views
        """
        self.object_points = object_points
        self.image_points = image_points
        self.n_views = len(object_points)
        self.n_points = object_points[0].shape[0]

        # Record valid views per camera
        for cam_idx in range(self.n_cameras):
            for view_idx in range(self.n_views):
                if image_points[cam_idx][view_idx] is not None:
                    self.valid_views[cam_idx].add(view_idx)

    def _params_to_vector(self) -> np.ndarray:
        """Convert current parameters to optimization vector (only extrinsics)"""
        params = []
        for cam in self.cameras:
            # Only include extrinsic parameters
            params.extend(cam.rvec.flatten())  # 3 parameters for rotation
            params.extend(cam.tvec.flatten())  # 3 parameters for translation
        return np.array(params)

    def _vector_to_params(self, x: np.ndarray):
        """Update camera parameters from optimization vector"""
        n_params_per_camera = 6  # 3 for rotation, 3 for translation
        for i in range(self.n_cameras):
            start_idx = i * n_params_per_camera
            self.cameras[i].rvec = x[start_idx : start_idx + 3].reshape(3, 1)
            self.cameras[i].tvec = x[start_idx + 3 : start_idx + 6].reshape(3, 1)

    def _compute_residuals(self, x: np.ndarray) -> np.ndarray:
        """
        Compute reprojection error residuals, handling partial visibility
        """
        self._vector_to_params(x)
        residuals = []

        for cam_idx in range(self.n_cameras):
            camera = self.cameras[cam_idx]
            camera_matrix = camera.camera_matrix  # Fixed
            dist_coeffs = camera.dist_coeffs  # Fixed
            # Only process views where this camera detected the pattern
            for view_idx in self.valid_views[cam_idx]:
                # Project points using current parameters
                projected_points, _ = cv2.projectPoints(
                    self.object_points[view_idx],
                    camera.rvec,
                    camera.tvec,
                    camera_matrix,
                    dist_coeffs,
                )

                # Ensure consistent shapes for subtraction
                proj_pts_2d = projected_points.reshape(-1, 2)
                image_pts = self.image_points[cam_idx][view_idx]

                if image_pts is not None:  # Extra safety check
                    error = (proj_pts_2d - image_pts).ravel()
                    residuals.extend(error)

        return np.array(residuals)

    def optimize(self, verbose: bool = True) -> Dict:
        """Run bundle adjustment optimization"""
        try:
            # Validate we have enough data
            if self.n_cameras < 2:
                raise ValueError("At least 2 cameras required for bundle adjustment")
            if self.n_views < 1:
                raise ValueError("At least 1 view required for bundle adjustment")

            # Validate camera parameters
            for cam in self.cameras:
                if cam.camera_matrix is None or cam.dist_coeffs is None:
                    raise ValueError(
                        "Camera intrinsics must be initialized before optimization"
                    )

            x0 = self._params_to_vector()

            if verbose:
                print("Starting bundle adjustment optimization...")
                initial_residuals = self._compute_residuals(x0)
                initial_cost = np.sum(initial_residuals**2)
                print(f"Initial cost: {initial_cost:.6f}")

            # Run optimization with TRF method for robust loss
            result = least_squares(
                self._compute_residuals,
                x0,
                method="trf",  # Changed from 'lm' to support robust loss
                loss="soft_l1",  # Changed from 'huber' for smoother loss
                f_scale=1.0,  # Tune this based on expected noise level
                max_nfev=200,  # Increased max iterations
                ftol=1e-10,
                xtol=1e-10,
                verbose=2 if verbose else 0,
            )

            # Update parameters with optimized values
            self._vector_to_params(result.x)

            # Compute final errors and diagnostics
            final_residuals = self._compute_residuals(result.x)
            if verbose:
                final_cost = np.sum(final_residuals**2)
                print(f"Final cost: {final_cost:.6f}")
                print(f"Overall RMS: {np.sqrt(np.mean(final_residuals**2)):.6f}mm")

            # Calculate per-camera statistics properly handling partial visibility
            camera_stats = self._compute_camera_statistics(final_residuals)

            return {
                "success": result.success,
                "camera_stats": camera_stats,
                "overall_rms": np.sqrt(np.mean(final_residuals**2)),
                "n_iterations": result.nfev,
                "optimized_cameras": self.cameras,
                "convergence_history": {},  # Empty since we removed callback
                "jacobian": result.jac,  # For potential covariance analysis
                "status": result.status,
                "message": result.message,
            }

        except Exception as e:
            print(f"Bundle adjustment failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "camera_stats": {},
                "overall_rms": float("inf"),
            }

    def _compute_camera_statistics(self, residuals: np.ndarray) -> Dict:
        """
        Compute per-camera statistics handling partial visibility
        """
        stats = {}
        residual_idx = 0

        for cam_idx in range(self.n_cameras):
            cam_residuals = []
            n_valid_views = len(self.valid_views[cam_idx])

            if n_valid_views > 0:
                points_per_view = self.n_points * 2
                n_residuals = n_valid_views * points_per_view
                cam_residuals = residuals[residual_idx : residual_idx + n_residuals]
                residual_idx += n_residuals

            stats[cam_idx] = {
                "rms": (
                    np.sqrt(np.mean(cam_residuals**2))
                    if len(cam_residuals) > 0
                    else np.inf
                ),
                "n_valid_views": n_valid_views,
                "max_error": (
                    np.max(np.abs(cam_residuals)) if len(cam_residuals) > 0 else np.inf
                ),
            }

        return stats

    def compute_covariance(self, result):
        """Compute parameter covariance from Jacobian"""
        # Get Jacobian at solution
        J = result.jac

        # Compute approximation to Hessian
        H = J.T @ J

        # Compute covariance (inverse of Hessian)
        try:
            cov = np.linalg.inv(H)
            return cov
        except np.linalg.LinAlgError:
            print("Warning: Could not compute parameter covariance")
            return None
