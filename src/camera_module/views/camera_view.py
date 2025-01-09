from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

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
        """
        Start continuous camera preview
        Returns:
            bool: True if camera started successfully, False otherwise
        """
        if self.view_model.start_camera():
            self.preview_active = True
            return True
        return False

    def stop(self):
        """Stop continuous camera preview and clean up"""
        self.preview_active = False
        self.view_model.stop_camera()
        self.display_label.setText("Camera Not Started")
        self.current_frame = None

    def get_current_frame(self):
        """
        Get a single frame from the camera, whether previewing or not
        Returns:
            numpy.ndarray: The captured frame, or None if capture failed
        """
        if not self.preview_active:
            # If not previewing, temporarily start camera and capture one frame
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

    def display_frame(self, frame):
        """
        Convert a numpy frame to QPixmap and display it in our label
        Args:
            frame: numpy.ndarray containing the RGB image data
        """
        height, width, channel = frame.shape
        bytes_per_line = channel * width
        
        # Convert numpy array to QImage
        q_image = QImage(frame.data, width, height, 
                        bytes_per_line, QImage.Format.Format_RGB888)
        
        # Convert QImage to QPixmap and scale it to fit our label
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.display_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
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