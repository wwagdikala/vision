# src/core/error_handling/exceptions.py

from enum import Enum
from typing import Optional

class ErrorSeverity(Enum):
    """Defines the severity levels for system errors"""
    CRITICAL = "CRITICAL"   # System cannot continue, requires immediate attention
    ERROR = "ERROR"         # Operation failed but system can continue
    WARNING = "WARNING"     # Potential issue that requires attention
    INFO = "INFO"          # Informational message about system state

class ErrorCategory(Enum):
    """Categorizes the type of error for proper handling"""
    CAMERA = "CAMERA"           # Camera-related errors
    CALIBRATION = "CALIBRATION" # Calibration process errors
    MEASUREMENT = "MEASUREMENT" # Measurement accuracy errors
    HARDWARE = "HARDWARE"       # Hardware communication errors
    SYSTEM = "SYSTEM"          # General system errors
    UI = "UI"                  # User interface errors

class ValidationSystemError(Exception):
    """Base exception class for all system errors"""
    def __init__(self, message: str, recovery_hint: Optional[str] = None):
        super().__init__(message)
        self.recovery_hint = recovery_hint

class CameraError(ValidationSystemError):
    """Camera-specific error"""
    def __init__(self, message: str, camera_id: int, recovery_hint: Optional[str] = None):
        super().__init__(message, recovery_hint)
        self.camera_id = camera_id

class CalibrationError(ValidationSystemError):
    """Calibration-specific error"""
    def __init__(self, message: str, recovery_hint: Optional[str] = None):
        super().__init__(message, recovery_hint)

class MeasurementError(ValidationSystemError):
    """Measurement-specific error"""
    def __init__(self, message: str, accuracy: float, threshold: float, 
                 recovery_hint: Optional[str] = None):
        super().__init__(message, recovery_hint)
        self.accuracy = accuracy
        self.threshold = threshold