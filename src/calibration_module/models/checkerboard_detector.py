import cv2
import numpy as np
from core.error_handling.exceptions import CalibrationError
from calibration_module.models.base_detector import TargetDetector, DetectionResult

class CheckerboardDetector(TargetDetector):
    def detect(self, image: np.ndarray) -> DetectionResult:
        """Detect checkerboard corners in image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        pattern_size = (
            self.settings['width_squares'] - 1,
            self.settings['height_squares'] - 1
        )
        
        # Find checkerboard corners
        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
        
        if not ret:
            raise CalibrationError(
                f"Could not find checkerboard pattern {pattern_size}",
                "Ensure checkerboard is fully visible and well-lit."
            )
            
        # Refine corners
        corners = cv2.cornerSubPix(
            gray, corners, (11, 11), (-1, -1),
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        )
        
        uncertainties = self._calculate_uncertainty(gray, corners.reshape(-1, 2), 11)
        
        # Generate 3D object points
        square_size = self.settings['square_size_mm']
        object_points = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
        object_points[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
        object_points *= square_size
        
        return DetectionResult(corners, object_points, uncertainties)