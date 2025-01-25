# src/viewmodels/camera_viewmodel.py
from PySide6.QtCore import QObject, Signal, QTimer, Property
from services.service_locator import ServiceLocator


class CameraViewModel(QObject):

    frame_ready = Signal(object)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    preview_status_changed = Signal(bool)
    point_selected = Signal(float, float)
    marker_updated = Signal(list)

    def __init__(self, camera_model):
        super().__init__()
        self.camera_model = camera_model
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.markers = []
        self.frozen_frame = None  # Add this to store frozen frame
        self.is_frozen = False  # Add freeze state

        self.camera_model.status_changed.connect(self.status_changed)
        self.camera_model.error_occurred.connect(self.error_occurred)

    def start_camera(self):
        if self.camera_model.start():
            self.timer.start(30)  # 30ms = ~33fps
            return True
        return False

    def stop_camera(self):
        self.timer.stop()
        self.camera_model.stop()

    def update_frame(self):
        frame = self.camera_model.get_frame()
        if frame is not None:
            self.frame_ready.emit(frame)

    def capture_frame(self):
        """Get current frame (frozen or live)"""
        if self.is_frozen and self.frozen_frame is not None:
            return self.frozen_frame
        return self.camera_model.get_frame()

    def freeze_frame(self):
        """Freeze the current frame"""
        self.is_frozen = True
        self.frozen_frame = self.camera_model.get_frame()
        self.timer.stop()
        if self.frozen_frame is not None:
            self.frame_ready.emit(self.frozen_frame)

    def unfreeze_frame(self):
        """Resume live preview"""
        self.is_frozen = False
        self.frozen_frame = None
        self.timer.start(30)

    def mark_point(self, x: float, y: float):
        """Store a new marker point and notify view"""
        self.markers.append((x, y))
        # Emit updated markers list to view
        self.marker_updated.emit(self.markers)

    def clear_markers(self):
        """Clear all stored markers"""
        self.markers = []
        # Emit empty list to clear view
        self.marker_updated.emit(self.markers)

    @Property(bool, notify=preview_status_changed)
    def preview_active(self):
        return self.timer.isActive()

    @preview_active.setter
    def preview_active(self, value):
        if value:
            self.start_camera()
        else:
            self.stop_camera()
        self.preview_status_changed.emit(value)
