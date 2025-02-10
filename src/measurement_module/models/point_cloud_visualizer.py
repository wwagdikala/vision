from typing import List, Tuple, Optional
import numpy as np
import cv2
import pyvista as pv
from measurement_module.models.measurement_model import MeasurementModel
from services.service_locator import ServiceLocator

class PointCloudVisualizer:
    def __init__(self, plotter: pv.Plotter):
        self.plotter = plotter
        self.locator = ServiceLocator.get_instance()
        self.calibration_storage = self.locator.get_service("calibration_storage")
        self.measurement_model = MeasurementModel()
        
        self.points_3d = []
        self.point_colors = []

        self.min_depth = 1 
        self.max_depth = 500 
        self.stereo_matcher = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=128,  # Double the search range
            blockSize=7,         # Balance noise vs. detail
            uniquenessRatio=5,   # Lower to accept more matches
            speckleWindowSize=100,
            speckleRange=2,
            disp12MaxDiff=5,
            P1=8*3*7**2,        # Smoothness parameters
            P2=32*3*7**2
        )
        
    def detect_points(self, frame: np.ndarray, min_distance: int = 10) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY) if len(frame.shape) == 3 else frame
        
        points = cv2.goodFeaturesToTrack(
            gray,
            maxCorners=1000,  # Maximum number of points
            qualityLevel=0.01,
            minDistance=min_distance,  # Minimum distance between points
            blockSize=7
        )
        
        if points is not None:
            return points.reshape(-1, 2)
        return np.array([])

    def compute_point_cloud_triangulation(self, frames: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """Compute 3D point cloud from stereo frames"""
        if not self.calibration_storage.is_calibrated():
            raise ValueError("System not calibrated")
            
        # Detect points in both frames
        points_cam1 = self.detect_points(frames[0])
        points_cam2 = self.detect_points(frames[1])
        
        if len(points_cam1) == 0 or len(points_cam2) == 0:
            return np.array([]), np.array([])
            
        # Get calibration data
        calib = self.calibration_storage.get_calibration()
        K1 = calib["camera_matrices"][0]
        K2 = calib["camera_matrices"][1]
        R1, _ = cv2.Rodrigues(calib["rotations"][0])
        R2, _ = cv2.Rodrigues(calib["rotations"][1])
        t1 = calib["translations"][0]
        t2 = calib["translations"][1]
        
        # Build projection matrices
        P1 = K1 @ np.hstack([R1, t1])
        P2 = K2 @ np.hstack([R2, t2])
        
        # Match points between views using optical flow
        points_cam2_matched, status, err = cv2.calcOpticalFlowPyrLK(
            cv2.cvtColor(frames[0], cv2.COLOR_RGB2GRAY),
            cv2.cvtColor(frames[1], cv2.COLOR_RGB2GRAY),
            points_cam1.astype(np.float32),
            None
        )
        
        # Filter points based on status
        good_matches = status.ravel() == 1
        points_cam1 = points_cam1[good_matches]
        points_cam2_matched = points_cam2_matched[good_matches]
        
        # Triangulate matched points
        points_4d = cv2.triangulatePoints(
            P1, P2,
            points_cam1.T,
            points_cam2_matched.T
        )
        
        # Convert to 3D coordinates
        points_3d = (points_4d[:3, :] / points_4d[3, :]).T
        
        # Generate colors based on reprojection error
        colors = self._compute_point_colors(points_3d, points_cam1, points_cam2_matched, P1, P2)
        
        return points_3d, colors
    
    # Disparity map
    def compute_point_cloud(self, frames: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        if not self.calibration_storage.is_calibrated():
            raise ValueError("System not calibrated")

        # Get calibration data
        calib = self.calibration_storage.get_calibration()
        baseline = np.linalg.norm(calib["translations"][1] - calib["translations"][0])
        K1 = calib["camera_matrices"][0]
        focal_length = K1[0, 0]  # Assuming square pixels
        print(f"Baseline: {baseline:.3f}m | Focal: {focal_length:.1f}px")


        # Rectify images (prerequisite for disparity maps)
        left_rect, right_rect = self._rectify_images(frames[0], frames[1])

        # Compute disparity map
        left_gray = cv2.cvtColor(left_rect, cv2.COLOR_RGB2GRAY)
        right_gray = cv2.cvtColor(right_rect, cv2.COLOR_RGB2GRAY)
        disparity = self.stereo_matcher.compute(left_gray, right_gray).astype(np.float32) / 16.0

        disp_vis = cv2.normalize(disparity, None, 0, 255, cv2.NORM_MINMAX)
        cv2.imwrite("debug_disparity.png", disp_vis.astype(np.uint8))

        # Convert disparity to depth
        valid_mask = disparity > 0
        depth = (baseline * focal_length) / (disparity + 1e-6)  # Avoid division by zero

        valid_pixels = disparity[disparity > 0]
        print(f"Disparity stats: Min={valid_pixels.min():.1f}, Max={valid_pixels.max():.1f}")
        print(f"Valid disparity pixels: {len(valid_pixels)}/{disparity.size}")

        # Apply depth constraints
        depth_mask = (depth >= self.min_depth) & (depth <= self.max_depth)
        final_mask = valid_mask & depth_mask

        # Get 3D coordinates
        points_3d = self._depth_to_3d(depth, K1, final_mask)

        # Get colors from original image
        colors = left_rect[final_mask].reshape(-1, 3) / 255.0

        return points_3d, colors
    
    def _rectify_images(self, left: np.ndarray, right: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Rectify stereo images using calibration data"""
        calib = self.calibration_storage.get_calibration()

        # Get rectification parameters
        R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(
            calib["camera_matrices"][0],
            calib["dist_coeffs"][0],
            calib["camera_matrices"][1],
            calib["dist_coeffs"][1],
            (left.shape[1], left.shape[0]),
            calib["rotations"][1],
            calib["translations"][1],
            flags=cv2.CALIB_ZERO_DISPARITY
        )

        # Create rectification maps
        map1x, map1y = cv2.initUndistortRectifyMap(
            calib["camera_matrices"][0],
            calib["dist_coeffs"][0],
            R1, P1,
            (left.shape[1], left.shape[0]),
            cv2.CV_32FC1
        )

        map2x, map2y = cv2.initUndistortRectifyMap(
            calib["camera_matrices"][1],
            calib["dist_coeffs"][1],
            R2, P2,
            (right.shape[1], right.shape[0]),
            cv2.CV_32FC1
        )

        # Apply rectification
        left_rect = cv2.remap(left, map1x, map1y, cv2.INTER_LINEAR)
        right_rect = cv2.remap(right, map2x, map2y, cv2.INTER_LINEAR)

        cv2.imwrite("rectified_left.png", left_rect)
        cv2.imwrite("rectified_right.png", right_rect)

        return left_rect, right_rect

    def _depth_to_3d(self, depth: np.ndarray, K: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Convert depth map to 3D points using camera intrinsics"""
        fx = K[0, 0]
        fy = K[1, 1]
        cx = K[0, 2]
        cy = K[1, 2]

        # Create grid of pixel coordinates
        u, v = np.meshgrid(np.arange(depth.shape[1]), np.arange(depth.shape[0]))
        u = u[mask].astype(np.float32)
        v = v[mask].astype(np.float32)
        z = depth[mask]

        # Convert to 3D
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy

        return np.vstack([x, y, z]).T

    def _compute_point_colors(self, points_3d: np.ndarray, 
                            points1: np.ndarray, 
                            points2: np.ndarray,
                            P1: np.ndarray,
                            P2: np.ndarray) -> np.ndarray:
        """Compute colors based on reprojection error"""
        # Project 3D points back to both cameras
        points_4d = np.hstack([points_3d, np.ones((len(points_3d), 1))])
        proj1 = (P1 @ points_4d.T).T
        proj2 = (P2 @ points_4d.T).T
        
        # Convert to image coordinates
        proj1 = proj1[:, :2] / proj1[:, 2:]
        proj2 = proj2[:, :2] / proj2[:, 2:]
        
        # Compute reprojection errors
        error1 = np.linalg.norm(proj1 - points1, axis=1)
        error2 = np.linalg.norm(proj2 - points2, axis=1)
        total_error = (error1 + error2) / 2
        
        # Normalize errors to 0-1 range for coloring
        max_allowed_error = 2.0  # pixels
        error_normalized = np.clip(total_error / max_allowed_error, 0, 1)
        
        # Create color array (red = high error, green = low error)
        colors = np.zeros((len(points_3d), 3))
        colors[:, 0] = error_normalized  # Red channel
        colors[:, 1] = 1 - error_normalized  # Green channel
        
        return colors
        
    def update_visualization(self, frames: List[np.ndarray]):

        try:
            # Compute new point cloud
            points, colors = self.compute_point_cloud(frames)
            if len(points) == 0:
                print("No points detected")
                return
            
            # Clear all previous actors (if that's acceptable)
            self.plotter.clear()
    
            # Create point cloud mesh
            cloud = pv.PolyData(points)
            
            # Add new points with colors and optionally give the actor a name
            self.plotter.add_mesh(
                cloud,
                style='points',
                point_size=5,
                render_points_as_spheres=True,
                scalars=colors,
                rgb=True,
                opacity=1.0,  # No transparency
                name="point_cloud"
            )

            self.plotter.camera_position = [
                (np.max(points[:,0])+100, np.max(points[:,1])+100, np.max(points[:,2])+100),
                np.mean(points, axis=0),
                (0, 0, 1)
            ]
            self.plotter.reset_camera()
            # print(f"Point range (mm): X({points[:,0].min():.2f}-{points[:,0].max():.2f})")
            # print(f"                 Y({points[:,1].min():.2f}-{points[:,1].max():.2f})")
            # print(f"                 Z({points[:,2].min():.2f}-{points[:,2].max():.2f})")
            # Update the render window
            self.plotter.render()
    
        except Exception as e:
            print(f"Error updating point cloud: {str(e)}")
                
    def clear(self):
        """Clear all points from visualization"""
        self.plotter.clear_points()
        self.plotter.render()