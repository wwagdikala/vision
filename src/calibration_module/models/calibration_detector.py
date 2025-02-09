import cv2
import numpy as np
from typing import Tuple, Optional
from core.constants.settings_constants import CalibrationTarget
from core.error_handling.exceptions import CalibrationError
from services.service_locator import ServiceLocator
from dataclasses import dataclass


@dataclass
class CirclePatternConfig:
    """Configuration for circle pattern detection"""

    grid_rows: int
    grid_cols: int
    circle_spacing: float  # mm
    min_radius: int  # pixels
    max_radius: int  # pixels
    min_dist: int  # pixels
    quality_level: float  # 0-1, minimum quality for accepting detection


class CalibrationDetector:

    def __init__(self, target_type: str):
        self.target_type = target_type
        self.settings_service = ServiceLocator.get_instance().get_service(
            "settings_service"
        )

    def detect(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:

        try:
            if self.target_type == CalibrationTarget.CHECKERBOARD.value:
                return self._detect_checkerboard(image)
            elif self.target_type == CalibrationTarget.CIRCLE_CUBE.value:
                return self._detect_circle_pattern(image)
            else:  # Default to cube
                return self._detect_cube(image)

        except ValueError as e:
            raise CalibrationError(
                str(e), recovery_hint="Ensure the pattern is fully visible and well-lit"
            )

    def _detect_checkerboard(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        try:
            gray = (
                cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                if len(image.shape) == 3
                else image
            )

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

            flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
            ret, corners = cv2.findChessboardCorners(gray, pattern_size, flags)

            if not ret:
                print("Failed to find checkerboard pattern")
                raise ValueError(
                    "Could not find checkerboard pattern. Ensure the pattern is clearly visible."
                )

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

    def _detect_circle_pattern(
        self, image: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect circle pattern on cube face
        Returns:
            Tuple of (image_points, object_points) for detected circles
        """
        # Convert to grayscale if needed
        gray = (
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        )

        # Enhance image for better circle detection
        gray = cv2.equalizeHist(gray)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Find circles using Hough transform
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=self.circle_config.min_dist,
            param1=50,  # Edge detection parameter
            param2=30,  # Circle detection threshold
            minRadius=self.circle_config.min_radius,
            maxRadius=self.circle_config.max_radius,
        )

        if circles is None:
            raise CalibrationError(
                "No circles detected",
                recovery_hint="Check lighting and ensure circles are clearly visible",
            )

        # Get circle centers
        centers = circles[0, :, :2]  # Shape: (N, 2) for x,y coordinates

        # Sort circles into grid
        sorted_points = self._sort_circles_into_grid(centers)
        if sorted_points is None:
            raise CalibrationError(
                "Could not organize circles into grid pattern",
                recovery_hint="Ensure all circles are visible and pattern is not too distorted",
            )

        # Generate corresponding 3D object points
        object_points = self._generate_circle_object_points()

        # Validate detection quality
        if not self._validate_circle_detection(sorted_points):
            raise CalibrationError(
                "Circle detection quality too low",
                recovery_hint="Check for proper lighting and reduce camera motion",
            )

        return sorted_points, object_points

    def _sort_circles_into_grid(self, centers: np.ndarray) -> Optional[np.ndarray]:
        """Sort detected circle centers into a regular grid"""
        rows, cols = self.circle_config.grid_rows, self.circle_config.grid_cols
        expected_points = rows * cols

        if len(centers) < expected_points * 0.9:  # Allow 10% missing points
            return None

        try:
            # Find approximate grid spacing in pixels
            sorted_x = np.sort(np.unique(centers[:, 0]))
            sorted_y = np.sort(np.unique(centers[:, 1]))
            dx = np.median(np.diff(sorted_x))
            dy = np.median(np.diff(sorted_y))

            # Find top-left point (minimum x+y)
            top_left_idx = np.argmin(centers[:, 0] + centers[:, 1])
            top_left = centers[top_left_idx]

            # Initialize output grid
            grid_points = np.zeros((rows * cols, 2), dtype=np.float32)
            used_points = np.zeros(len(centers), dtype=bool)

            # Assign points to grid positions
            for i in range(rows):
                for j in range(cols):
                    expected_x = top_left[0] + j * dx
                    expected_y = top_left[1] + i * dy

                    # Find closest unused point
                    distances = np.sqrt(
                        (centers[:, 0] - expected_x) ** 2
                        + (centers[:, 1] - expected_y) ** 2
                    )
                    distances[used_points] = float("inf")

                    closest_idx = np.argmin(distances)
                    if distances[closest_idx] > max(dx, dy) * 0.5:
                        continue

                    grid_points[i * cols + j] = centers[closest_idx]
                    used_points[closest_idx] = True

            return grid_points

        except Exception as e:
            print(f"Grid sorting failed: {str(e)}")
            return None

    def _generate_circle_object_points(self) -> np.ndarray:
        """Generate 3D object points for circle pattern"""
        rows = self.circle_config.grid_rows
        cols = self.circle_config.grid_cols
        spacing = self.circle_config.circle_spacing

        object_points = np.zeros((rows * cols, 3), dtype=np.float32)
        for i in range(rows):
            for j in range(cols):
                object_points[i * cols + j] = [j * spacing, i * spacing, 0]

        return object_points

    def _validate_circle_detection(self, grid_points: np.ndarray) -> bool:
        """
        Validate quality of circle detection
        Returns: True if detection meets quality threshold
        """
        rows = self.circle_config.grid_rows
        cols = self.circle_config.grid_cols

        try:
            # Check point count
            min_points = int(rows * cols * self.circle_config.quality_level)
            if len(grid_points) < min_points:
                return False

            # Check grid regularity
            x_coords = grid_points[:, 0].reshape(rows, cols)
            y_coords = grid_points[:, 1].reshape(rows, cols)

            # Check spacing consistency
            dx = np.diff(x_coords, axis=1)
            dy = np.diff(y_coords, axis=0)

            spacing_variation = np.std(dx) / np.mean(dx) + np.std(dy) / np.mean(dy)
            if spacing_variation > 0.2:  # Allow 20% variation
                return False

            return True

        except Exception:
            return False
