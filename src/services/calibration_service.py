# services/calibration_storage.py
from PySide6.QtCore import QObject, Signal
import numpy as np


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
