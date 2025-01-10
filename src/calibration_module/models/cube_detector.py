import cv2
import numpy as np
from core.constants.calibration_constants import DetectionResult
from core.error_handling.exceptions import CalibrationError
from calibration_module.models.base_detector import TargetDetector

class CubeDetector(TargetDetector):
    def detect(self, image: np.ndarray) -> DetectionResult:
        """Detect cube corners in image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Find contours
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_LIST, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        corners = []
        for contour in contours:
            if cv2.contourArea(contour) < 100:
                continue
                
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) >= 4:
                refined_corners = cv2.cornerSubPix(
                    gray, 
                    np.float32(approx), 
                    (self.settings['refinement_window_size'],)*2,
                    (-1, -1),
                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                )
                corners.extend(refined_corners)
        
        if len(corners) < self.settings['min_corners']:
            raise CalibrationError(
                f"Insufficient corners detected: {len(corners)}. Need at least {self.settings['min_corners']}.",
                "Ensure cube is fully visible and well-lit."
            )
            
        corners = np.array(corners, dtype=np.float32)
        uncertainties = self._calculate_uncertainty(
            gray, corners, self.settings['refinement_window_size']
        )
        
        # Create 3D points
        s = self.settings['size_mm']
        object_points = np.array([
            [0, 0, 0], [s, 0, 0], [s, s, 0], [0, s, 0],
            [0, 0, s], [s, 0, s], [s, s, s], [0, s, s]
        ], dtype=np.float32)
        
        return DetectionResult(corners, object_points, uncertainties)
