from PySide6.QtCore import QObject, Signal
import numpy as np
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ElectrodePosition:
    """Represents a single electrode position measurement"""

    position_3d: np.ndarray  # 3D position [x, y, z]
    timestamp: datetime  # Measurement timestamp
    confidence: float  # Confidence score (0-1)
    source: str  # 'camera' or 'navigation'


@dataclass
class MeasurementResult:
    """Represents a comparison between camera and navigation measurements"""

    camera_position: ElectrodePosition
    navigation_position: ElectrodePosition
    discrepancy: float  # Distance between positions in mm
    is_valid: bool  # Whether measurement meets accuracy requirements


class MeasurementModel(QObject):
    # Signals for notifying state changes
    measurement_updated = Signal(MeasurementResult)
    error_occurred = Signal(str)
    accuracy_warning = Signal(float, str)  # discrepancy, message

    def __init__(self):
        super().__init__()
        self.current_measurements: Dict[int, MeasurementResult] = (
            {}
        )  # electrode_id -> result
        self.accuracy_threshold = 1.0  # 1mm threshold

    def add_camera_position(
        self, electrode_id: int, position: np.ndarray, confidence: float
    ) -> bool:
        """Add a camera-based electrode position measurement"""
        try:
            pos = ElectrodePosition(
                position_3d=position,
                timestamp=datetime.now(),
                confidence=confidence,
                source="camera",
            )

            # If we have a navigation position for this electrode, compare them
            if electrode_id in self.current_measurements:
                self._update_measurement(electrode_id, camera_position=pos)
            else:
                # Create new measurement result awaiting navigation position
                self.current_measurements[electrode_id] = MeasurementResult(
                    camera_position=pos,
                    navigation_position=None,
                    discrepancy=None,
                    is_valid=False,
                )
            return True

        except Exception as e:
            self.error_occurred.emit(f"Error adding camera position: {str(e)}")
            return False

    def add_navigation_position(self, electrode_id: int, position: np.ndarray) -> bool:
        """Add a navigation system electrode position measurement"""
        try:
            pos = ElectrodePosition(
                position_3d=position,
                timestamp=datetime.now(),
                confidence=1.0,  # Navigation system is reference
                source="navigation",
            )

            if electrode_id in self.current_measurements:
                self._update_measurement(electrode_id, navigation_position=pos)
            else:
                # Create new measurement result awaiting camera position
                self.current_measurements[electrode_id] = MeasurementResult(
                    camera_position=None,
                    navigation_position=pos,
                    discrepancy=None,
                    is_valid=False,
                )
            return True

        except Exception as e:
            self.error_occurred.emit(f"Error adding navigation position: {str(e)}")
            return False

    def _update_measurement(
        self,
        electrode_id: int,
        camera_position: Optional[ElectrodePosition] = None,
        navigation_position: Optional[ElectrodePosition] = None,
    ):
        """Update measurement with new position data and calculate discrepancy"""
        result = self.current_measurements[electrode_id]

        if camera_position:
            result.camera_position = camera_position
        if navigation_position:
            result.navigation_position = navigation_position

        # If we have both positions, calculate discrepancy
        if result.camera_position and result.navigation_position:
            discrepancy = np.linalg.norm(
                result.camera_position.position_3d
                - result.navigation_position.position_3d
            )
            result.discrepancy = discrepancy
            result.is_valid = discrepancy <= self.accuracy_threshold

            if not result.is_valid:
                self.accuracy_warning.emit(
                    discrepancy,
                    f"Measurement accuracy ({discrepancy:.2f}mm) exceeds threshold",
                )

            self.measurement_updated.emit(result)
