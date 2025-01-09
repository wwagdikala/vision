# src/viewmodels/calibration_viewmodel.py
from PySide6.QtCore import QObject, Signal
from calibration_module.models.wizard_model import WizardModel
from services.service_locator import ServiceLocator

class WizardViewModel(QObject):
    # Signals for the view
    status_changed = Signal(str)
    progress_updated = Signal(int)
    calibration_finished = Signal(bool, str)
    
    def __init__(self):
        super().__init__()
        locator = ServiceLocator.get_instance()
        self.calibration_model = locator.get_service('wizard_model')
        
        # Connect model signals to ViewModel
        self.calibration_model.calibration_status.connect(self.handle_status_update)
        self.calibration_model.calibration_progress.connect(self.handle_progress_update)
        self.calibration_model.calibration_complete.connect(self.handle_calibration_complete)
        
        self.is_calibrating = False

    def start_calibration(self, camera_frames):
        """
        Start the calibration process
        """
        if self.is_calibrating:
            self.status_changed.emit("Calibration already in progress")
            return False
            
        self.is_calibrating = True
        self.status_changed.emit("Preparing calibration...")
        
        # Validate frames
        if not self.validate_frames(camera_frames):
            self.is_calibrating = False
            self.status_changed.emit("Invalid camera frames")
            return False
            
        # Start calibration in model
        self.calibration_model.start_calibration(camera_frames)
        return True

    def validate_frames(self, frames):
        """
        Validate camera frames before calibration
        """
        if not frames or len(frames) != 3:  # Expecting 3 cameras
            return False
            
        for frame in frames:
            if frame is None or frame.size == 0:
                return False
        return True

    def handle_status_update(self, status):
        """
        Handle status updates from model
        """
        self.status_changed.emit(status)

    def handle_progress_update(self, progress):
        """
        Handle progress updates from model
        """
        self.progress_updated.emit(progress)

    def handle_calibration_complete(self, success, message=None):
        """
        Handle calibration completion
        """
        self.is_calibrating = False
        self.calibration_finished.emit(success, message)