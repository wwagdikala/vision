# calibration_module/models/bundle_adjustment.py

import numpy as np
from scipy.optimize import least_squares
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Set
import cv2


@dataclass
class CameraParameters:
    camera_matrix: np.ndarray  # 3x3 intrinsic matrix
    dist_coeffs: np.ndarray  # Distortion coefficients
    rvec: np.ndarray  # Rotation vector (Rodrigues)
    tvec: np.ndarray  # Translation vector


class BundleAdjustment:
    def __init__(self):
        self.cameras: List[CameraParameters] = []
        self.object_points: List[np.ndarray] = []
        # image_points[camera_idx][view_idx] = 2D points or None
        self.image_points: List[List[Optional[np.ndarray]]] = []
        self.valid_views: List[Set[int]] = []
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
        self.object_points = object_points
        self.image_points = image_points
        self.n_views = len(object_points)
        if self.n_views > 0:
            self.n_points = self.object_points[0].shape[0]
        else:
            self.n_points = 0

        # Mark valid views
        for cam_idx in range(self.n_cameras):
            for view_idx, pts in enumerate(self.image_points[cam_idx]):
                if pts is not None:
                    self.valid_views[cam_idx].add(view_idx)

    def _params_to_vector(self) -> np.ndarray:
        """Convert camera extrinsic params (rvec, tvec) to a single vector."""
        params = []
        for cam in self.cameras:
            params.extend(cam.rvec.flatten())  # 3 rotation
            params.extend(cam.tvec.flatten())  # 3 translation
        return np.array(params, dtype=np.float64)

    def _vector_to_params(self, x: np.ndarray):
        n_params_per_cam = 6
        for i in range(self.n_cameras):
            start = i * n_params_per_cam
            self.cameras[i].rvec = x[start : start + 3].reshape(3, 1)
            self.cameras[i].tvec = x[start + 3 : start + 6].reshape(3, 1)

    def _compute_residuals(self, x: np.ndarray) -> np.ndarray:
        self._vector_to_params(x)
        residuals = []

        for cam_idx in range(self.n_cameras):
            cam = self.cameras[cam_idx]
            for view_idx in self.valid_views[cam_idx]:
                # Project
                obj_pts_3d = self.object_points[view_idx]
                projected, _ = cv2.projectPoints(
                    obj_pts_3d, cam.rvec, cam.tvec, cam.camera_matrix, cam.dist_coeffs
                )
                proj_pts_2d = projected.reshape(-1, 2)

                # Compare with actual 2D
                img_pts_2d = self.image_points[cam_idx][view_idx]
                if img_pts_2d is not None:
                    error = (proj_pts_2d - img_pts_2d).ravel()
                    residuals.extend(error)

        return np.array(residuals, dtype=np.float64)

    def optimize(self, verbose: bool = True) -> Dict:
        if self.n_cameras < 1 or self.n_views < 1:
            return {
                "success": False,
                "error": "Not enough cameras or views for bundle adjustment",
                "camera_stats": {},
                "overall_rms": float("inf"),
            }

        x0 = self._params_to_vector()
        if verbose:
            print("Starting bundle adjustment...")

        try:
            result = least_squares(
                self._compute_residuals,
                x0,
                method="trf",
                loss="soft_l1",
                f_scale=1.0,
                max_nfev=200,
                ftol=1e-10,
                xtol=1e-10,
                verbose=2 if verbose else 0,
            )
            self._vector_to_params(result.x)
            final_res = self._compute_residuals(result.x)

            # Compute stats
            camera_stats = self._compute_camera_statistics(final_res)
            overall_rms = np.sqrt(np.mean(final_res**2)) if len(final_res) else 0.0

            stereo_rms_mm = None
            if len(self.cameras) >= 2:
                stereo_rms_mm = self._compute_stereo_3d_error(
                    self.cameras, self.object_points, self.image_points
                )

            return {
                "success": result.success,
                "camera_stats": camera_stats,
                "overall_rms": overall_rms,
                "overall_rms_mm": stereo_rms_mm,
                "n_iterations": result.nfev,
                "optimized_cameras": self.cameras,
                "status": result.status,
                "message": result.message,
            }
        except Exception as e:
            print(f"Bundle adjustment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "camera_stats": {},
                "overall_rms": float("inf"),
            }

    def _compute_camera_statistics(self, final_residuals: np.ndarray) -> Dict:
        """
        We break down residuals camera by camera. Each valid view has 2D * N_points errors.
        """
        stats = {}
        idx = 0
        for cam_idx in range(self.n_cameras):
            cam_residuals = []
            n_valid_views = len(self.valid_views[cam_idx])

            # For each valid view, we have self.n_points * 2 residual values
            # So total residual count for this camera = n_valid_views * (n_points*2)
            count_for_cam = n_valid_views * (self.n_points * 2)
            if count_for_cam > 0:
                cam_residuals = final_residuals[idx : idx + count_for_cam]
                idx += count_for_cam

            if len(cam_residuals):
                rms = np.sqrt(np.mean(cam_residuals**2))
                max_err = np.max(np.abs(cam_residuals))
            else:
                rms = float("inf")
                max_err = float("inf")

            stats[cam_idx] = {
                "rms": rms,
                "n_valid_views": n_valid_views,
                "max_error": max_err,
            }

        return stats

    def _compute_stereo_3d_error(self, cameras, object_points, image_points):
        """
        Compute 3D error by triangulating points and comparing to known 3D positions.
        Returns RMS error in millimeters.
        """
        try:
            if len(cameras) < 2:
                return None
    
            # Build projection matrices
            P = []
            for cam_idx in range(2):
                R, _ = cv2.Rodrigues(cameras[cam_idx].rvec)
                t = cameras[cam_idx].tvec
                Rt = np.hstack([R, t])
                K = cameras[cam_idx].camera_matrix
                P.append(K @ Rt)
    
            all_3d_errors = []
            
            # Track errors per view for outlier detection
            view_errors = []
    
            for view_idx in range(len(object_points)):
                corners_cam0 = image_points[0][view_idx] if view_idx < len(image_points[0]) else None
                corners_cam1 = image_points[1][view_idx] if view_idx < len(image_points[1]) else None
    
                if corners_cam0 is None or corners_cam1 is None:
                    continue
    
                num_corners = min(len(corners_cam0), len(corners_cam1))
                pts0 = corners_cam0[:num_corners].T.astype(np.float64)
                pts1 = corners_cam1[:num_corners].T.astype(np.float64)
    
                # Triangulate points
                hom_points_3d = cv2.triangulatePoints(P[0], P[1], pts0, pts1)
                triangulated_3d = (hom_points_3d[:3, :] / hom_points_3d[3, :]).T
    
                # Get corresponding known 3D points
                known_3d_subset = object_points[view_idx][:num_corners]
    
                # Compute simple rigid transformation without scale
                try:
                    R, t = self._estimate_rigid_transform(known_3d_subset, triangulated_3d)
                    transformed_points = (R @ triangulated_3d.T + t.reshape(-1, 1)).T
                    
                    # Compute errors for this view
                    view_error = np.linalg.norm(transformed_points - known_3d_subset, axis=1)
                    view_errors.append(np.median(view_error))
                    all_3d_errors.extend(view_error.tolist())
                    
                except Exception as e:
                    print(f"Error in alignment for view {view_idx}: {str(e)}")
                    continue
    
            if len(all_3d_errors) > 0:
                # Filter out outlier views
                median_view_error = np.median(view_errors)
                mad = np.median(np.abs(view_errors - median_view_error))
                threshold = median_view_error + 2.5 * mad  # Use MAD for robust outlier detection
                
                # Only use errors from good views
                filtered_errors = [err for err, view_err in zip(all_3d_errors, view_errors) 
                                 if view_err <= threshold]
                
                if filtered_errors:
                    rms_3d = float(np.sqrt(np.mean(np.square(filtered_errors))))
                    return rms_3d
            return None
    
        except Exception as e:
            print(f"Bundle adjustment 3D error computation failed: {str(e)}")
            return None
    
    def _estimate_rigid_transform(self, A, B):
        """
        Estimate rigid transformation between two point sets without scale.
        """
        # Center the points
        centroid_A = np.mean(A, axis=0)
        centroid_B = np.mean(B, axis=0)
        
        # Center the points
        AA = A - centroid_A
        BB = B - centroid_B
        
        # Compute rotation
        H = AA.T @ BB
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        
        # Ensure right-handed coordinate system
        if np.linalg.det(R) < 0:
            Vt[-1,:] *= -1
            R = Vt.T @ U.T
        
        # Compute translation
        t = centroid_A - R @ centroid_B
        
        return R, t