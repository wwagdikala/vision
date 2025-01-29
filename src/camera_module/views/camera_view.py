from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import Qt, QSize, QPoint, QPointF
import numpy as np
from services.service_locator import ServiceLocator


class CameraView(QWidget):
    def __init__(self, view_model, parent=None):
        super().__init__(parent)

        self.settings_service = ServiceLocator.get_instance().get_service(
            "settings_service"
        )

        self.pan_offset = QPoint(0, 0)
        self.scale = 1.0
        self.pan_start = None
        self.setMouseTracking(True)

        self.view_model = view_model
        self.current_frame = None
        self.current_detection = None
        self.current_quality = None
        self.current_pixmap = None
        self.preview_active = False

        self.markers = []
        self.base_scale = 1.0
        self.zoom_factor = 1.0
        self.scale = 1.0
        self.pan_start = None
        self.pan_offset = QPoint(0, 0)

        # Create a vertical layout with no margins for maximum display space
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create a label that will display either status text or camera frames
        self.camera_label = QLabel()
        self.display_label = QLabel("Camera Not Started")
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(self.display_label)

        # Connect the view model's signal to our frame handler
        self.view_model.frame_ready.connect(self.handle_frame)
        self.view_model.error_occurred.connect(self.handle_error)
        self.view_model.marker_updated.connect(self.display_frame)

    def start(self):
        if not self.view_model.start_camera():
            self.display_label.setText(f"Failed to start camera")
            return False
        self.preview_active = True
        return True

    def stop(self):
        self.preview_active = False
        self.view_model.stop_camera()
        self.display_label.setText("Camera Not Started")
        self.current_frame = None

    def get_current_frame(self):
        if not self.view_model.preview_active:
            if self.view_model.start_camera():
                frame = self.view_model.capture_frame()
                self.view_model.stop_camera()
                return frame
        else:
            return self.view_model.capture_frame()
        return None

    def handle_frame(self, frame):
        self.current_frame = frame
        self.display_frame(frame)

    def display_frame(self, frame_or_markers):

        if isinstance(frame_or_markers, list):
            if self.current_frame is not None:
                self.display_camera_frame(self.current_frame)
            return

        if frame_or_markers is None:
            print("Warning: Received None frame in display_frame")
            return

        # Store the new frame and display it
        self.current_frame = frame_or_markers
        self.display_camera_frame(self.current_frame)

    def display_camera_frame(self, frame):
        """
        Handle the actual drawing of the frame and markers
        Args:
            frame: numpy array of the camera frame
        """
        try:
            height, width, channel = frame.shape
        except (AttributeError, ValueError) as e:
            print(f"Error processing frame: {e}")
            print(f"Frame type: {type(frame)}")
            return

        # Convert frame to Qt image
        bytes_per_line = channel * width
        q_image = QImage(
            frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
        )
        self.current_pixmap = QPixmap.fromImage(q_image)

        # Calculate scaling based on mode
        view_size = self.display_label.size()
        scale_x = view_size.width() / width
        scale_y = view_size.height() / height

        image_mode = self.settings_service.get_setting("cameras.image_mode")
        if image_mode == "fill":
            self.base_scale = max(scale_x, scale_y)
        else:  # "fit" mode
            self.base_scale = min(scale_x, scale_y)

        # Calculate final scale
        self.scale = self.base_scale * self.zoom_factor

        # Create scaled version of image
        scaled_size = QSize(int(width * self.scale), int(height * self.scale))
        scaled_pixmap = self.current_pixmap.scaled(
            scaled_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Ensure proper positioning
        self.constrainPan()

        # Create final image
        final_pixmap = QPixmap(self.display_label.size())
        final_pixmap.fill(Qt.black)
        painter = QPainter(final_pixmap)

        # Draw the camera frame
        painter.drawPixmap(self.pan_offset, scaled_pixmap)

        # Draw markers from viewmodel
        if self.view_model.markers:
            painter.setPen(QPen(QColor(0, 255, 0), 1))
            for x, y in self.view_model.markers:
                # Convert marker coordinates to screen coordinates
                screen_x = x * self.scale + self.pan_offset.x()
                screen_y = y * self.scale + self.pan_offset.y()

                # Draw crosshair
                size = 5
                painter.drawLine(
                    int(screen_x - size),
                    int(screen_y),
                    int(screen_x + size),
                    int(screen_y),
                )
                painter.drawLine(
                    int(screen_x),
                    int(screen_y - size),
                    int(screen_x),
                    int(screen_y + size),
                )

                # Draw circle
                # painter.drawEllipse(int(screen_x - 2), int(screen_y - 1), 4, 4)

        painter.end()
        self.display_label.setPixmap(final_pixmap)

    def handle_error(self, error_message):

        self.display_label.setText(f"Error: {error_message}")

    def update_overlay(self, points, quality=None):
        has_points = False
        if points is not None:
            if isinstance(points, np.ndarray):
                has_points = points.size > 0
            elif isinstance(points, list):
                has_points = len(points) > 0

        # Store or clear detection
        self.current_detection = points if has_points else None
        self.current_quality = quality if has_points else None

        if self.current_frame is not None:
            self.display_frame(self.current_frame)

        # ALWAYS trigger update to remove old overlay
        self.display_label.update()

    def _get_quality_color(self, quality_score: float) -> QColor:
        """Get color based on quality score"""
        if quality_score >= 0.8:
            return QColor(0, 255, 0)  # Good - Green
        elif quality_score >= 0.6:
            return QColor(255, 255, 0)  # Warning - Yellow
        else:
            return QColor(255, 0, 0)  # Poor - Red

    def constrainPan(self):
        if self.current_pixmap is None:
            return

        view_rect = self.display_label.rect()

        scaled_width = int(self.current_pixmap.width() * self.scale)
        scaled_height = int(self.current_pixmap.height() * self.scale)

        if scaled_width <= view_rect.width():
            self.pan_offset.setX((view_rect.width() - scaled_width) // 2)
        else:
            min_x = view_rect.width() - scaled_width  # Left edge
            max_x = 0  # Right edge
            self.pan_offset.setX(max(min_x, min(max_x, self.pan_offset.x())))

        if scaled_height <= view_rect.height():
            self.pan_offset.setY((view_rect.height() - scaled_height) // 2)
        else:
            min_y = view_rect.height() - scaled_height  # Top edge
            max_y = 0  # Bottom edge
            self.pan_offset.setY(max(min_y, min(max_y, self.pan_offset.y())))

    # Event handling

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Get measurement viewmodel to check state
            locator = ServiceLocator.get_instance()
            measurement_vm = locator.get_service("measurement_viewmodel")

            # Only allow point selection if measuring is active
            if not measurement_vm.measuring_active:
                return

            pos = event.pos()
            label_pos = self.display_label.mapFrom(self, pos)

            # Adjust coordinates for pan and scale
            adjusted_x = (label_pos.x() - self.pan_offset.x()) / self.scale
            adjusted_y = (label_pos.y() - self.pan_offset.y()) / self.scale

            # Let the viewmodel handle the point selection
            self.view_model.point_selected.emit(adjusted_x, adjusted_y)

        elif event.button() == Qt.MiddleButton:
            self.pan_start = event.pos()

    def wheelEvent(self, event):
        if not (self.preview_active and self.current_frame is not None):
            return

        delta = event.angleDelta().y()
        old_zoom = self.zoom_factor

        # Calculate the position of the cursor relative to the image
        # First, get the cursor position in widget coordinates
        mouse_pos = event.position()

        # Convert cursor position to be relative to the current image position
        image_point = QPointF(
            (mouse_pos.x() - self.pan_offset.x()) / self.scale,
            (mouse_pos.y() - self.pan_offset.y()) / self.scale,
        )

        # Update zoom factor
        if delta > 0:
            self.zoom_factor *= 1.1  # Zoom in
        else:
            self.zoom_factor *= 0.9  # Zoom out

        # Limit zoom range
        self.zoom_factor = max(1.0, min(5.0, self.zoom_factor))

        # Calculate new scale
        new_scale = self.base_scale * self.zoom_factor

        # Calculate new position to maintain cursor point
        new_x = mouse_pos.x() - (image_point.x() * new_scale)
        new_y = mouse_pos.y() - (image_point.y() * new_scale)

        # Update pan offset with new position
        self.pan_offset = QPoint(int(new_x), int(new_y))

        # Constrain the pan to keep image in bounds
        self.constrainPan()

        # Update display with new zoom
        self.display_frame(self.current_frame)

    def mouseMoveEvent(self, event):
        if self.pan_start and event.buttons() & Qt.MiddleButton:
            # Calculate the movement delta
            delta = event.pos() - self.pan_start
            self.pan_start = event.pos()

            # Update pan offset
            self.pan_offset += delta

            # Constrain the panning to keep image in bounds
            self.constrainPan()

            # Redisplay the frame with new pan position
            self.display_frame(self.current_frame)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.pan_start = None

    def closeEvent(self, event):
        self.stop()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_frame is not None:
            self.display_frame(self.current_frame)

    def paintEvent(self, event):
        super().paintEvent(event)

        if (
            self.current_detection is not None
            and self.current_pixmap is not None
            and len(self.current_detection) > 0
        ):

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
