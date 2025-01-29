# measurement_module/viewmodels/measurement_viewmodel.py

from PySide6.QtCore import QObject, Signal
import numpy as np
from services.service_locator import ServiceLocator
from core.constants.calibration_constants import CameraSetup
from measurement_module.models.measurement_model import MeasurementModel


class MeasurementViewModel(QObject):
    # Keep existing signals exactly as they are for View compatibility
    measurement_updated = Signal(float)
    status_changed = Signal(str)

    def __init__(self):
        super().__init__()
        # Keep existing service initialization
        self.locator = ServiceLocator.get_instance()
        self.calibration_storage = self.locator.get_service("calibration_storage")
        print(self.calibration_storage)
        self.settings_service = self.locator.get_service("settings_service")
        self.debug_mode = self.settings_service.get_setting("app.debug_mode")
        self.global_state = self.locator.get_service("global_state")

        # Initialize measurement model
        self.measurement_model = MeasurementModel()

        # Connect model signals
        self.measurement_model.measurement_updated.connect(
            self._handle_measurement_update
        )
        self.measurement_model.error_occurred.connect(
            lambda msg: self.status_changed.emit(f"Error: {msg}")
        )
        self.measurement_model.triangulation_failed.connect(
            lambda msg: self.status_changed.emit(f"Triangulation failed: {msg}")
        )

        # Keep existing camera viewmodel initialization
        self.camera_viewmodels = []
        num_cameras = self.get_camera_count()
        for i in range(num_cameras):
            vm = self.locator.get_service(f"camera_viewmodel_{i}")
            self.camera_viewmodels.append(vm)
            vm.point_selected.connect(
                lambda x, y, cam_idx=i: self.handle_point_selection(cam_idx, x, y)
            )

        # State management - keep all existing state variables
        self.preview_active = False
        self.measuring_active = False
        self.point1_data = []
        self.point2_data = []
        self.current_point = 1

    def start_measuring(self):
        """Start measurement mode - required by the View"""
        self.measuring_active = True
        self.point1_data = []
        self.point2_data = []
        self.current_point = 1

        # Freeze camera frames for measurement
        for viewmodel in self.camera_viewmodels:
            viewmodel.freeze_frame()
            viewmodel.clear_markers()
        self.status_changed.emit("Select point 1 in first camera view")

    def stop_measuring(self):
        """Stop measurement mode - required by the View"""
        self.measuring_active = False
        self.point1_data = []
        self.point2_data = []

        # Unfreeze camera frames
        for viewmodel in self.camera_viewmodels:
            viewmodel.clear_markers()
            viewmodel.unfreeze_frame()
        self.status_changed.emit("Measurement stopped")

    def handle_point_selection(self, camera_idx: int, x: float, y: float):
        """Handle point selection - maintain existing workflow while using the model"""
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

        # Store point and update UI
        if self.current_point == 1:
            if len(self.point1_data) < 2:
                self.point1_data.append((camera_idx, x, y))
                self.camera_viewmodels[camera_idx].mark_point(x, y)

                if len(self.point1_data) == 1:
                    self.status_changed.emit("Select point 1 in second camera view")
                elif len(self.point1_data) == 2:
                    self.current_point = 2
                    self.status_changed.emit("Select point 2 in first camera view")
        else:  # current_point == 2
            if len(self.point2_data) < 2:
                self.point2_data.append((camera_idx, x, y))
                self.camera_viewmodels[camera_idx].mark_point(x, y)

                if len(self.point2_data) == 1:
                    self.status_changed.emit("Select point 2 in second camera view")
                elif len(self.point2_data) == 2:
                    # Use model to compute the measurement
                    self._compute_measurement()

    def _compute_measurement(self):
        """Use measurement model to compute distance between points"""
        # First point
        result1 = self.measurement_model.compute_measurement(self.point1_data, 0)
        if result1 is None:
            self.status_changed.emit("Failed to compute first point")
            return

        # Second point
        result2 = self.measurement_model.compute_measurement(self.point2_data, 1)
        if result2 is None:
            self.status_changed.emit("Failed to compute second point")
            return

        # Calculate distance between points
        point1 = result1.camera_position.position_3d
        point2 = result2.camera_position.position_3d
        distance = np.linalg.norm(point1 - point2)

        # Emit results using existing signal format
        self.measurement_updated.emit(distance)

        # Reset for next measurement
        self.point1_data = []
        self.point2_data = []
        self.current_point = 1
        for vm in self.camera_viewmodels:
            vm.clear_markers()

        self.status_changed.emit("Select point 1 in first camera view")

    def _handle_measurement_update(self, result):
        """Handle measurement updates from model while maintaining View compatibility"""
        # The View expects updates through measurement_updated and status_changed signals,
        # so we don't need to handle the model's measurement_updated signal directly yet
        pass

    # Keep existing preview methods exactly as they are
    def start_preview(self):
        if not self.calibration_storage.is_calibrated():
            if not self.debug_mode:
                self.status_changed.emit("System not calibrated")
                return False
            else:
                self.status_changed.emit("Debug mode: System not calibrated")

        try:
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
        try:
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

    def get_camera_count(self):
        setup = self.settings_service.get_setting("cameras.camera_setup")
        return CameraSetup.get_num_cameras(setup)
