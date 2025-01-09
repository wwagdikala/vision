# src/models/camera_model.py
import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal

class CameraModel(QObject):
    frame_ready = Signal(np.ndarray)
    error_occurred = Signal(str)
    status_changed = Signal(str)

    def __init__(self, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.camera = None
        self.is_running = False

    def start(self):
        try:
            self.camera = cv2.VideoCapture(self.camera_id)
            if not self.camera.isOpened():
                raise Exception("Could not open camera")
            
            self.is_running = True
            self.status_changed.emit("Camera running")
            return True
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def stop(self):
        if self.camera is not None:
            self.camera.release()
        self.is_running = False
        self.status_changed.emit("Camera stopped")

    def get_frame(self):
        if self.camera is None or not self.camera.isOpened():
            return None

        ret, frame = self.camera.read()
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None