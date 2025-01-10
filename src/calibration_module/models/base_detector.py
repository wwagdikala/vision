from abc import ABC, abstractmethod
import cv2
import numpy as np
from typing import Optional
from core.constants.calibration_constants import DetectionResult

class TargetDetector(ABC):
    """Base class for all calibration target detectors"""
    
    def __init__(self, settings: dict):
        self.settings = settings

    @abstractmethod
    def detect(self, image: np.ndarray) -> DetectionResult:
        """Detect calibration target in image"""
        pass
    
    def _calculate_uncertainty(self, image: np.ndarray, 
                             points: np.ndarray, 
                             window_size: int) -> np.ndarray:
        """Calculate detection uncertainty for points"""
        uncertainties = []
        half_size = window_size // 2
        
        for point in points:
            x, y = int(point[0]), int(point[1])
            patch = image[
                max(0, y-half_size):min(image.shape[0], y+half_size+1),
                max(0, x-half_size):min(image.shape[1], x+half_size+1)
            ]
            
            gx = cv2.Sobel(patch, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(patch, cv2.CV_64F, 0, 1, ksize=3)
            
            grad_mag = np.sqrt(gx**2 + gy**2)
            uncertainty = 1.0 / (np.mean(grad_mag) + 1e-6)
            uncertainties.append(uncertainty)
            
        return np.array(uncertainties)