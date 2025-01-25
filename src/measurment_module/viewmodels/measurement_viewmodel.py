# In measurement_module/viewmodels/measurement_viewmodel.py
from PySide6.QtCore import QObject, Signal
import numpy as np
import cv2
from services.service_locator import ServiceLocator
from core.constants.calibration_constants import CameraSetup


class MeasurementViewModel(QObject):
    measurement_updated = Signal(float)  # Distance in mm
    status_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.calibration_storage = self.locator.get_service("calibration_storage")
        self.settings_service = self.locator.get_service("settings_service")
        self.debug_mode = self.settings_service.get_setting("app.debug_mode")
        self.global_state = self.locator.get_service("global_state")
        self.camera_viewmodels = []

        # Get camera viewmodels
        num_cameras = self.get_camera_count()
        for i in range(num_cameras):
            vm = self.locator.get_service(f"camera_viewmodel_{i}")
            self.camera_viewmodels.append(vm)
            vm.point_selected.connect(
                lambda x, y, cam_idx=i: self.handle_point_selection(cam_idx, x, y)
            )

        self.preview_active = False
        self.measuring_active = False

        # Updated data structure for points
        self.point1_data = []  # [(cam_idx, x, y), ...] for first point
        self.point2_data = []  # [(cam_idx, x, y), ...] for second point
        self.current_point = 1  # 1 or 2

    def start_measuring(self):
        """Start measurement mode"""
        self.measuring_active = True
        self.point1_data = []
        self.point2_data = []
        self.current_point = 1

        # Work with viewmodels instead of views
        for viewmodel in self.camera_viewmodels:
            viewmodel.freeze_frame()
            viewmodel.clear_markers()  # We'll need to add this method to the camera viewmodel
        self.status_changed.emit("Select point 1 in first camera view")

    def stop_measuring(self):
        """Stop measurement mode"""
        self.measuring_active = False
        self.point1_data = []
        self.point2_data = []

        # Work with viewmodels instead of views
        for viewmodel in self.camera_viewmodels:
            viewmodel.clear_markers()  # We'll need to add this method to the camera viewmodel
            viewmodel.unfreeze_frame()
        self.status_changed.emit("Measurement stopped")

    def _compute_3d_distance(self):
        """Compute 3D distance between selected points"""
        try:
            calib = self.calibration_storage.get_calibration()
            if not calib:
                self.status_changed.emit("No calibration data available")
                return

            points_3d = []
            # Process each point (point1 and point2)
            for point_data in [self.point1_data, self.point2_data]:
                # Get projection matrices and 2D points
                proj_matrices = []
                points_2d = []

                for cam_idx, x, y in point_data:
                    # Build projection matrix for this camera
                    K = calib["camera_matrices"][cam_idx]
                    R, _ = cv2.Rodrigues(calib["rotations"][cam_idx])
                    t = calib["translations"][cam_idx]
                    P = K @ np.hstack([R, t])

                    proj_matrices.append(P)
                    points_2d.append(np.array([x, y]))

                # Convert to correct format for triangulation
                points_2d = np.array(points_2d).T  # Shape: 2xN

                # Triangulate this point
                points_4d = cv2.triangulatePoints(
                    proj_matrices[0],
                    proj_matrices[1],
                    points_2d[:, 0:1],
                    points_2d[:, 1:2],
                )

                # Convert to 3D
                point_3d = (points_4d[:3] / points_4d[3]).reshape(3)
                points_3d.append(point_3d)

            # Compute distance
            distance = np.linalg.norm(points_3d[0] - points_3d[1])
            self.measurement_updated.emit(distance)
            self.status_changed.emit(f"Measured distance: {distance:.2f} mm")

            # Reset for next measurement
            self.point1_data = []
            self.point2_data = []
            self.current_point = 1
            self.status_changed.emit("Select point 1 in first camera view")

        except Exception as e:
            print(f"Error computing 3D distance: {str(e)}")
            self.status_changed.emit(f"Measurement failed: {str(e)}")

    def get_camera_count(self):
        setup = self.settings_service.get_setting("cameras.camera_setup")
        return CameraSetup.get_num_cameras(setup)

    def start_preview(self):

        if not self.calibration_storage.is_calibrated():
            if not self.debug_mode:
                self.status_changed.emit("System not calibrated")
                return False
            else:
                self.status_changed.emit("Debug mode: System not calibrated")

        try:
            # Initialize camera views
            for vm in self.camera_viewmodels:
                if not vm.start_camera():
                    self.status_changed.emit("Failed to start cameras")
                    return False

            self.preview_active = True
            self.status_changed.emit("Preview started")
            return True

        except Exception as e:
            self.status_changed.emit(f"Preview failed: {str(e)}")
            return False

    def stop_preview(self):
        """Stop camera preview"""
        try:
            # Stop cameras
            for vm in self.camera_viewmodels:
                vm.stop_camera()

            self.preview_active = False
            self.measuring_active = False
            self.point1_data = []
            self.point2_data = []
            self.current_point = 1
            self.status_changed.emit("Preview stopped")

        except Exception as e:
            self.status_changed.emit(f"Error stopping preview: {str(e)}")

    def handle_point_selection(self, camera_idx: int, x: float, y: float):
        """Handle point selection from cameras"""
        if not self.measuring_active:
            return

        # Check if we've already used this camera for the current point
        current_points = (
            self.point1_data if self.current_point == 1 else self.point2_data
        )
        if any(cam_idx == camera_idx for cam_idx, _, _ in current_points):
            self.status_changed.emit(
                f"Point {self.current_point} already selected in this camera"
            )
            return

        # Check if we've reached our point limit
        if len(self.point1_data) == 2 and len(self.point2_data) == 2:
            self.status_changed.emit("All points have been selected")
            return

        # Store the point data
        if self.current_point == 1:
            if len(self.point1_data) < 2:  # Only allow 2 points for point 1
                self.point1_data.append((camera_idx, x, y))
                # Mark point in the appropriate camera viewmodel
                self.camera_viewmodels[camera_idx].mark_point(
                    x, y
                )  # Changed from camera_views to camera_viewmodels
                if len(self.point1_data) == 1:
                    self.status_changed.emit("Select point 1 in second camera view")
                elif len(self.point1_data) == 2:
                    self.current_point = 2
                    self.status_changed.emit("Select point 2 in first camera view")
        else:  # current_point == 2
            if len(self.point2_data) < 2:  # Only allow 2 points for point 2
                self.point2_data.append((camera_idx, x, y))
                # Mark point in the appropriate camera viewmodel
                self.camera_viewmodels[camera_idx].mark_point(
                    x, y
                )  # Changed from camera_views to camera_viewmodels
                if len(self.point2_data) == 1:
                    self.status_changed.emit("Select point 2 in second camera view")
                elif len(self.point2_data) == 2:
                    self._compute_3d_distance()
