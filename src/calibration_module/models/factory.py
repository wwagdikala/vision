from typing import Dict
from core.constants.calibration_constants import CalibrationTarget
from .cube_detector import CubeDetector
from .checkerboard_detector import CheckerboardDetector
from .circular_detector import CircularTargetDetector
from .base_detector import TargetDetector

class TargetDetectorFactory:
    """Factory class for creating target detectors based on configuration"""
    
    @staticmethod
    def create(target_type: CalibrationTarget, settings: Dict) -> TargetDetector:
        """
        Create appropriate target detector based on type
        
        Args:
            target_type: Type of calibration target to detect
            settings: Configuration settings for the detector
            
        Returns:
            TargetDetector: Configured detector instance
            
        Raises:
            ValueError: If target_type is unknown
        """
        if target_type == CalibrationTarget.CUBE:
            return CubeDetector(settings)
        elif target_type == CalibrationTarget.CHECKERBOARD:
            return CheckerboardDetector(settings)
        elif target_type == CalibrationTarget.CUBE_CIRCLES:
            return CircularTargetDetector(settings)
        else:
            raise ValueError(f"Unknown target type: {target_type}")