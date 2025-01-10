from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple


class CalibrationTarget(Enum):
    CUBE = 'cube'
    CUBE_CIRCLES = 'cube_circles'
    CHECKERBOARD = 'checkerboard'

    @classmethod
    def list(cls) -> List[str]:
        return [member.value for member in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.list()

@dataclass
class CalibrationSettings:
    """Holds calibration-specific settings"""
    rms_error_threshold_mm: float
    min_cameras_per_point: int

@dataclass
class CubeSettings:
    """Settings for cube calibration target"""
    size_mm: float
    min_corners: int
    corner_uncertainty_threshold: float
    refinement_window_size: int

@dataclass
class CubeCirclesSettings:
    """Settings for cube with circles calibration target"""
    size_mm: float
    circles_per_face: int
    circle_diameter_mm: float
    min_circles: int

@dataclass
class CheckerboardSettings:
    """Settings for checkerboard calibration target"""
    width_squares: int
    height_squares: int
    square_size_mm: float
    min_corners: int
    
    def get_pattern_size(self) -> Tuple[int, int]:
        """Get pattern size for OpenCV calibration"""
        return (self.width_squares - 1, self.height_squares - 1)
    
    def get_object_points(self) -> List[List[float]]:
        """Generate 3D points for checkerboard pattern"""
        pattern_size = self.get_pattern_size()
        object_points = []
        for i in range(pattern_size[1]):
            for j in range(pattern_size[0]):
                object_points.append([
                    j * self.square_size_mm,
                    i * self.square_size_mm,
                    0
                ])
        return object_points