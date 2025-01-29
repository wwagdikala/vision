# measurement_module/models/measurement_model.py

from PySide6.QtCore import QObject, Signal
import numpy as np
import cv2
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from services.service_locator import ServiceLocator


@dataclass
class ElectrodePosition:
    """Represents a single electrode position measurement from either camera or navigation system"""

    position_3d: np.ndarray  # 3D position in world coordinates [x, y, z]
    timestamp: datetime  # When the measurement was taken
    confidence: float  # Measurement confidence (0-1)
    source: str  # Either 'camera' or 'navigation'


@dataclass
class MeasurementResult:
    """Represents a complete measurement comparing camera and navigation positions"""

    camera_position: ElectrodePosition  # Position measured by camera system
    navigation_position: ElectrodePosition  # Position from navigation system
    discrepancy: float  # Distance between positions in mm
    is_valid: bool  # Whether measurement meets accuracy requirements


class MeasurementModel(QObject):
    """
    Handles core measurement logic including triangulation, validation, and comparison
    between camera and navigation system measurements.
    """

    # Signals for notifying state changes
    measurement_updated = Signal(MeasurementResult)  # New measurement completed
    triangulation_failed = Signal(str)  # Triangulation error
    navigation_updated = Signal(ElectrodePosition)  # New navigation data
    error_occurred = Signal(str)  # General errors
    accuracy_warning = Signal(float, str)  # When accuracy threshold exceeded

    def __init__(self):
        super().__init__()
        self.calibration_storage = ServiceLocator.get_instance().get_service(
            "calibration_storage"
        )

        # Storage for ongoing measurements
        self.current_measurements: Dict[int, MeasurementResult] = (
            {}
        )  # electrode_id -> result
        self.accuracy_threshold = 1.0  # 1mm threshold for valid measurements

    def triangulate_point(
        self, point_data: List[Tuple[int, float, float]]
    ) -> Optional[np.ndarray]:
        try:
            calib = self.calibration_storage.get_calibration()
            if not calib:
                self.error_occurred.emit("No calibration data available")
                return None

            # Build projection matrices and 2D points arrays
            proj_matrices = []
            points_2d = []

            for cam_idx, x, y in point_data:
                # Build projection matrix using calibration data
                K = calib["camera_matrices"][cam_idx]
                R, _ = cv2.Rodrigues(calib["rotations"][cam_idx])
                t = calib["translations"][cam_idx]
                P = K @ np.hstack([R, t])

                proj_matrices.append(P)
                points_2d.append(np.array([x, y]))

            # Convert to format needed for triangulation
            points_2d = np.array(points_2d).T  # Shape: 2xN

            # Perform triangulation
            points_4d = cv2.triangulatePoints(
                proj_matrices[0],
                proj_matrices[1],
                points_2d[:, 0:1],
                points_2d[:, 1:2],
            )

            # Convert from homogeneous to 3D coordinates
            point_3d = (points_4d[:3] / points_4d[3]).reshape(3)
            return point_3d

        except Exception as e:
            self.triangulation_failed.emit(f"Triangulation failed: {str(e)}")
            return None

    def compute_measurement(
        self, point_data: List[Tuple[int, float, float]], electrode_id: int
    ) -> Optional[MeasurementResult]:
        """
        Computes a complete measurement for an electrode, including triangulation
        and comparison with navigation data if available.

        Args:
            point_data: Camera view points for triangulation
            electrode_id: Identifier for this electrode

        Returns:
            MeasurementResult if successful, None if computation fails
        """
        # Triangulate the point from camera data
        point_3d = self.triangulate_point(point_data)
        if point_3d is None:
            return None

        # Create camera position measurement
        camera_position = ElectrodePosition(
            position_3d=point_3d,
            timestamp=datetime.now(),
            confidence=self._calculate_confidence(point_data),
            source="camera",
        )

        # Check if we have navigation data for this electrode
        if electrode_id in self.current_measurements:
            result = self.current_measurements[electrode_id]
            if result.navigation_position:
                # Update existing measurement with new camera position
                result.camera_position = camera_position
                result.discrepancy = np.linalg.norm(
                    camera_position.position_3d - result.navigation_position.position_3d
                )
                result.is_valid = result.discrepancy <= self.accuracy_threshold
        else:
            # Create new measurement result awaiting navigation data
            result = MeasurementResult(
                camera_position=camera_position,
                navigation_position=None,
                discrepancy=None,
                is_valid=False,
            )
            self.current_measurements[electrode_id] = result

        self.measurement_updated.emit(result)
        return result

    def add_navigation_position(self, electrode_id: int, position: np.ndarray) -> None:
        """
        Updates measurement with position data from navigation system.

        Args:
            electrode_id: Identifier for the electrode
            position: 3D position from navigation system
        """
        nav_position = ElectrodePosition(
            position_3d=position,
            timestamp=datetime.now(),
            confidence=1.0,  # Navigation system is our reference
            source="navigation",
        )

        if electrode_id in self.current_measurements:
            result = self.current_measurements[electrode_id]
            result.navigation_position = nav_position

            if result.camera_position:
                # Update discrepancy if we have both measurements
                result.discrepancy = np.linalg.norm(
                    result.camera_position.position_3d - nav_position.position_3d
                )
                result.is_valid = result.discrepancy <= self.accuracy_threshold

                if not result.is_valid:
                    self.accuracy_warning.emit(
                        result.discrepancy,
                        f"Measurement accuracy ({result.discrepancy:.2f}mm) exceeds threshold",
                    )
        else:
            # Create new measurement result awaiting camera position
            result = MeasurementResult(
                camera_position=None,
                navigation_position=nav_position,
                discrepancy=None,
                is_valid=False,
            )
            self.current_measurements[electrode_id] = result

        self.navigation_updated.emit(nav_position)

    def _calculate_confidence(
        self, point_data: List[Tuple[int, float, float]]
    ) -> float:
        """
        Calculates confidence score for camera measurements based on:
        - Number of camera views used
        - Distribution of views
        - Triangulation quality

        Returns:
            Confidence score between 0 and 1
        """
        # For now, implement a basic confidence based on number of views
        # This can be enhanced with more sophisticated metrics
        n_views = len(point_data)
        if n_views < 2:
            return 0.0
        return min(1.0, n_views / 2)  # 2 views = 1.0 confidence
