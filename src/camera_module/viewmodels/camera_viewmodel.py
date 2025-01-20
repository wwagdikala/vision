# src/viewmodels/camera_viewmodel.py
from PySide6.QtCore import QObject, Signal, QTimer
from services.service_locator import ServiceLocator


class CameraViewModel(QObject):

    frame_ready = Signal(object)  # Will emit processed frame for UI
    status_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, camera_model):
        super().__init__()
        self.camera_model = camera_model
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Connect model signals
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
        return self.camera_model.get_frame()
