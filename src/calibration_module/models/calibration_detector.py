import cv2
import numpy as np
from typing import Tuple, Optional
from core.constants.settings_constants import CalibrationTarget
from core.error_handling.exceptions import CalibrationError
from services.service_locator import ServiceLocator


class CalibrationDetector:
    """Simplified detector for cube and checkerboard calibration targets"""

    def __init__(self, target_type: str):
        """Initialize detector for specified target type"""
        self.target_type = target_type
        self.settings_service = ServiceLocator.get_instance().get_service(
            "settings_service"
        )

    # In calibration_detector.py - Update the detect method
    def detect(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect calibration pattern in image
        Returns:
            Tuple of (image_points, object_points)
        """
        try:
            if self.target_type == CalibrationTarget.CHECKERBOARD.value:
                return self._detect_checkerboard(image)
            else:  # Default to cube
                return self._detect_cube(image)
        except ValueError as e:
            # Convert to more specific error
            raise CalibrationError(
                str(e), recovery_hint="Ensure the pattern is fully visible and well-lit"
            )

    def _detect_checkerboard(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Detect checkerboard pattern"""
        try:
            gray = (
                cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                if len(image.shape) == 3
                else image
            )

            # Get pattern parameters from settings
            pattern_rows = int(
                self.settings_service.get_setting("calibration.pattern_rows")
            )
            pattern_cols = int(
                self.settings_service.get_setting("calibration.pattern_cols")
            )
            pattern_size = (pattern_rows, pattern_cols)
            square_size = float(
                self.settings_service.get_setting("calibration.square_size")
            )

            print(f"Looking for pattern: {pattern_size}, square size: {square_size}mm")
            print(f"Image shape: {gray.shape}")

            # Add flags for better detection
            flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
            ret, corners = cv2.findChessboardCorners(gray, pattern_size, flags)

            if not ret:
                print("Failed to find checkerboard pattern")
                # Save debug image if needed
                # cv2.imwrite(f"debug_pattern_{time.time()}.jpg", gray)
                raise ValueError(
                    "Could not find checkerboard pattern. Ensure the pattern is clearly visible."
                )

            # Refine corners
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

            print(f"Found {len(corners)} corners")

            # Generate 3D object points
            object_points = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
            object_points[:, :2] = np.mgrid[
                0 : pattern_size[0], 0 : pattern_size[1]
            ].T.reshape(-1, 2)
            object_points *= square_size

            return corners, object_points

        except Exception as e:
            print(f"Checkerboard detection error: {str(e)}")
            raise

    def _detect_cube(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Detect calibration cube corners"""
        gray = (
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        )

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # Find cube corners
        corners = []
        for contour in contours:
            if cv2.contourArea(contour) < 100:  # Filter small contours
                continue

            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) >= 4:  # We're looking for corners
                refined_corners = cv2.cornerSubPix(
                    gray,
                    np.float32(approx),
                    (11, 11),
                    (-1, -1),
                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001),
                )
                corners.extend(refined_corners)

        if len(corners) < 4:  # Need at least 4 corners
            raise ValueError("Could not find enough cube corners")

        # Create corresponding 3D points (assuming 100mm cube)
        cube_size = 100.0  # mm
        object_points = np.array(
            [
                [0, 0, 0],
                [cube_size, 0, 0],
                [cube_size, cube_size, 0],
                [0, cube_size, 0],
                [0, 0, cube_size],
                [cube_size, 0, cube_size],
                [cube_size, cube_size, cube_size],
                [0, cube_size, cube_size],
            ],
            dtype=np.float32,
        )

        return np.array(corners), object_points
