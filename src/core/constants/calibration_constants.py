from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import numpy as np

from enum import Enum
from typing import List

class CameraSetupType(Enum):
    STEREO_2 = 'stereo_2'                     # 2 cameras in stereo arrangement
    STEREO_3 = 'stereo_3'  # 3 cameras in coplanar arrangement
    CIRCLE_5 = 'circle_5'                     # 5 cameras in circle

    @classmethod
    def list(cls) -> List[str]:
        return [member.value for member in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.list()
    
    @classmethod
    def get_num_cameras(cls, setup_type: str) -> int:
        """Get the number of cameras for a given setup type"""
        camera_counts = {
            cls.STEREO_3_COPLANAR.value: 3,
            cls.CIRCLE_5.value: 5
        }
        return camera_counts.get(setup_type)

    @classmethod
    def list(cls) -> List[str]:
        return [member.value for member in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.list()
    
    @classmethod
    def is_stereo_setup(cls, value: str) -> bool:
        """Check if the setup type is a stereo arrangement"""
        return value in [cls.STEREO_2.value, 
                        cls.STEREO_3_LINEAR.value,
                        cls.STEREO_3_TRIANGLE.value]
    
    @classmethod
    def is_circle_setup(cls, value: str) -> bool:
        """Check if the setup type is a circular arrangement"""
        return value in [cls.CIRCLE_4.value,
                        cls.CIRCLE_5.value,
                        cls.CIRCLE_6.value]
    
    @classmethod
    def is_grid_setup(cls, value: str) -> bool:
        """Check if the setup type is a grid arrangement"""
        return value in [cls.GRID_2X2.value,
                        cls.GRID_2X3.value]
    
    @classmethod
    def get_num_cameras(cls, setup_type: str) -> int:
        """Get the number of cameras for a given setup type"""
        camera_counts = {
            cls.STEREO_2.value: 2,
            cls.STEREO_3_LINEAR.value: 3,
            cls.STEREO_3_TRIANGLE.value: 3,
            cls.CIRCLE_4.value: 4,
            cls.CIRCLE_5.value: 5,
            cls.CIRCLE_6.value: 6,
            cls.GRID_2X2.value: 4,
            cls.GRID_2X3.value: 6
        }
        return camera_counts.get(setup_type)

class CalibrationTarget(Enum):
    CUBE = 'cube'
    CUBE_CIRCLES = 'cube_circles'
    CHECKERBOARD = 'checkerboard'

@dataclass
class CalibrationResults:
    """Stores the results of camera calibration"""
    camera_matrices: List[np.ndarray]
    dist_coeffs: List[np.ndarray]
    rvecs: List[np.ndarray]
    tvecs: List[np.ndarray]
    rms_error: float
    reprojection_errors: List[float]
    image_size: Tuple[int, int]

@dataclass
class DetectionResult:
    """Stores the results of target detection"""
    points_2d: np.ndarray  # Detected points in image
    points_3d: np.ndarray  # Corresponding 3D points
    uncertainties: np.ndarray  # Detection uncertainties

@dataclass
class CalibrationConfig:
    """Holds configuration for calibration process"""
    camera_setup: CameraSetupType
    target_type: CalibrationTarget
    target_settings: dict
    quality_thresholds: dict
    validation_settings: dict

