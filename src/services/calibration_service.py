# services/calibration_storage.py
from PySide6.QtCore import QObject, Signal
import numpy as np
import json


class CalibrationStorage(QObject):
    calibration_changed = Signal()

    def __init__(self):
        super().__init__()
        self._camera_matrices = []
        self._dist_coeffs = []
        self._rotations = []
        self._translations = []
        self._is_calibrated = False

    def store_calibration(self, camera_matrices, dist_coeffs, rotations, translations):
        self._camera_matrices = camera_matrices
        self._dist_coeffs = dist_coeffs
        self._rotations = rotations
        self._translations = translations
        self._is_calibrated = True
        self.calibration_changed.emit()

    def get_calibration(self):
        if not self._is_calibrated:
            return None
        return {
            "camera_matrices": self._camera_matrices,
            "dist_coeffs": self._dist_coeffs,
            "rotations": self._rotations,
            "translations": self._translations,
        }

    def is_calibrated(self):
        return self._is_calibrated

    def clear_calibration(self):
        self._camera_matrices = []
        self._dist_coeffs = []
        self._rotations = []
        self._translations = []
        self._is_calibrated = False
        self.calibration_changed.emit()


    def save_calibration_json(self, filename="src/config/calib.json"):
        calibration_data = {
            "camera_matrices": [m.tolist() for m in self._camera_matrices],
            "dist_coeffs": [d.tolist() for d in self._dist_coeffs],
            "rotations": [r.tolist() for r in self._rotations],
            "translations": [t.tolist() for t in self._translations],
        }
        with open(filename, "w") as f:
            json.dump(calibration_data, f, indent=4)

    def load_calibration_json(self, filename="src/config/calib.json"):
        with open(filename, "r") as f:
            data = json.load(f)
        return {
            "camera_matrices": [np.array(m) for m in data["camera_matrices"]],
            "dist_coeffs": [np.array(d) for d in data["dist_coeffs"]],
            "rotations": [np.array(r) for r in data["rotations"]],
            "translations": [np.array(t) for t in data["translations"]],
        }