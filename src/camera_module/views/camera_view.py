from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import Qt
import numpy as np
from services.service_locator import ServiceLocator


class CameraView(QWidget):
    def __init__(self, view_model, parent=None):
        """
        Initialize a camera view widget that can display camera frames
        Args:
            view_model: The camera view model that handles camera operations
            parent: Optional parent widget (Qt standard)
        """
        super().__init__(parent)
        self.view_model = view_model
        self.current_frame = None
        self.current_detection = None
        self.current_quality = None
        self.current_pixmap = None  # Add this line
        self.preview_active = False

        # Create a vertical layout with no margins for maximum display space
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create a label that will display either status text or camera frames
        self.display_label = QLabel("Camera Not Started")
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(self.display_label)

        # Connect the view model's signal to our frame handler
        self.view_model.frame_ready.connect(self.handle_frame)
        self.view_model.error_occurred.connect(self.handle_error)

    def start(self):
        """Start continuous camera preview"""
        if not self.view_model.start_camera():
            self.display_label.setText(f"Failed to start camera")
            return False
        self.preview_active = True  # Set flag when preview starts
        return True

    def stop(self):
        self.preview_active = False
        self.view_model.stop_camera()
        self.display_label.setText("Camera Not Started")
        self.current_frame = None

    def get_current_frame(self):
        if not self.preview_active:
            if self.view_model.start_camera():
                frame = self.view_model.capture_frame()
                self.view_model.stop_camera()
                return frame
        else:
            # If already previewing, just get the current frame
            return self.view_model.capture_frame()
        return None

    def handle_frame(self, frame):
        """
        Handle a new frame received from the view model
        Args:
            frame: numpy.ndarray containing the image data
        """
        self.current_frame = frame
        self.display_frame(frame)

    # In camera_view.py - Update display_frame method
    def display_frame(self, frame):
        """Convert a numpy frame to QPixmap and display it in our label"""
        height, width, channel = frame.shape
        bytes_per_line = channel * width

        # Convert numpy array to QImage
        q_image = QImage(
            frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
        )

        # Create the base pixmap from the frame
        self.current_pixmap = QPixmap.fromImage(q_image)

        # Scale pixmap
        scaled_pixmap = self.current_pixmap.scaled(
            self.display_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Update label with the scaled pixmap
        self.display_label.setPixmap(scaled_pixmap)

        scaled_pixmap = self.current_pixmap.scaled(
            self.display_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.display_label.setPixmap(scaled_pixmap)

    def handle_error(self, error_message):
        """
        Display error messages in the camera view
        Args:
            error_message: String containing the error message
        """
        self.display_label.setText(f"Error: {error_message}")

    def closeEvent(self, event):
        """
        Clean up camera resources when the widget is closed
        Args:
            event: QCloseEvent from Qt
        """
        self.stop()
        super().closeEvent(event)

    def resizeEvent(self, event):
        """
        Handle widget resize events to properly scale the displayed image
        Args:
            event: QResizeEvent from Qt
        """
        super().resizeEvent(event)
        if self.current_frame is not None:
            self.display_frame(self.current_frame)

    # In camera_view.py - Add to existing class

    def update_overlay(self, points, quality=None):
        # Decide if we actually have points:
        has_points = False
        if points is not None:
            if isinstance(points, np.ndarray):
                has_points = points.size > 0
            elif isinstance(points, list):
                has_points = len(points) > 0

        # Store or clear detection
        self.current_detection = points if has_points else None
        self.current_quality = quality if has_points else None

        # Force re-draw of the underlying (raw) frame
        if self.current_frame is not None:
            self.display_frame(self.current_frame)

        # ALWAYS trigger update to remove old overlay
        self.display_label.update()

    def paintEvent(self, event):
        """Override paint event"""
        super().paintEvent(event)

        # Only draw overlay if we have detection points and a pixmap
        if (
            self.current_detection is not None
            and self.current_pixmap is not None
            and len(self.current_detection) > 0
        ):  # Added length check

            # Create working copy of current pixmap
            working_pixmap = self.current_pixmap.copy()
            painter = QPainter(working_pixmap)

            for point in self.current_detection:
                # Handle numpy array points
                if isinstance(point, np.ndarray):
                    if point.shape == (1, 2):
                        x = int(point[0][0])
                        y = int(point[0][1])
                    elif point.shape == (2,):
                        x = int(point[0])
                        y = int(point[1])
                    else:
                        continue

                    # Get color based on quality
                    if self.current_quality:
                        color = self._get_quality_color(
                            self.current_quality.get("score", 0)
                        )
                    else:
                        color = QColor(0, 255, 0)  # Default to green

                    painter.setPen(QPen(color, 2))
                    painter.drawEllipse(x - 3, y - 3, 6, 6)

            painter.end()

            # Scale and display the working pixmap
            scaled_pixmap = working_pixmap.scaled(
                self.display_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.display_label.setPixmap(scaled_pixmap)

    def _draw_detection_overlay(self):
        """Draw detection points and quality indicators"""
        if not hasattr(self, "current_detection"):
            return

        painter = QPainter(self.display_label)
        if not painter.begin(self.display_label):
            return

        try:
            # Scale points to match displayed image size
            scale_factor = self._calculate_scale_factor()

            for point in self.current_detection:
                # Draw scaled point with quality-based color
                scaled_point = point * scale_factor
                if hasattr(self, "current_quality") and self.current_quality:
                    color = self._get_quality_color(
                        self.current_quality.get("score", 0)
                    )
                else:
                    color = QColor(0, 255, 0)  # Default to green

                painter.setPen(QPen(color, 2))
                painter.drawEllipse(
                    int(scaled_point[0] - 3), int(scaled_point[1] - 3), 6, 6
                )
        finally:
            painter.end()

    def _get_quality_color(self, quality_score: float) -> QColor:
        """Get color based on quality score"""
        if quality_score >= 0.8:
            return QColor(0, 255, 0)  # Good - Green
        elif quality_score >= 0.6:
            return QColor(255, 255, 0)  # Warning - Yellow
        else:
            return QColor(255, 0, 0)  # Poor - Red

    def _calculate_scale_factor(self):
        """Calculate scale factor between original image and display size"""
        if not hasattr(self, "current_frame") or self.current_frame is None:
            return 1.0

        # Get original image dimensions
        img_height, img_width = self.current_frame.shape[:2]

        # Get display dimensions
        display_width = self.display_label.width()
        display_height = self.display_label.height()

        # Calculate scale factors
        width_scale = display_width / img_width
        height_scale = display_height / img_height

        # Use the smaller scale to maintain aspect ratio
        return min(width_scale, height_scale)

    def mousePressEvent(self, event):
        """Handle mouse click for point selection"""
        if not hasattr(self, "preview_active") or not self.preview_active:
            return

        # Get measurement viewmodel to check if measuring is active
        locator = ServiceLocator.get_instance()
        measurement_vm = locator.get_service("measurement_viewmodel")
        if not measurement_vm.measuring_active:
            return

        # Convert click coordinates to image coordinates
        pos = event.pos()
        label_pos = self.display_label.mapFrom(self, pos)

        if self.current_pixmap:
            # Convert coordinates from display scale to original image scale
            scale_factor = self._calculate_scale_factor()
            if scale_factor > 0:
                x = float(label_pos.x()) / scale_factor
                y = float(label_pos.y()) / scale_factor

                # Emit signal for point selection
                self.view_model.point_selected.emit(x, y)

                # Draw marker at selected point
                self.mark_point(x, y)

    def mark_point(self, x: float, y: float):
        """Draw a temporary marker at the selected point"""
        if self.current_pixmap is not None:
            working_pixmap = self.current_pixmap.copy()
            painter = QPainter(working_pixmap)

            # Draw a crosshair or circle at the point
            painter.setPen(QPen(QColor(255, 0, 0), 2))  # Red pen
            size = 10
            painter.drawLine(int(x - size), int(y), int(x + size), int(y))
            painter.drawLine(int(x), int(y - size), int(x), int(y + size))

            painter.end()

            # Scale and display
            scaled_pixmap = working_pixmap.scaled(
                self.display_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.display_label.setPixmap(scaled_pixmap)
