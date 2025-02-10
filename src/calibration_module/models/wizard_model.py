# src/models/calibration_model.py
import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal

class WizardModel(QObject):
    def __init__(self):
        super().__init__()
