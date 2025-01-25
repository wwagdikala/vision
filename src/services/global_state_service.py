from PySide6.QtCore import QObject, Signal, Property


class GlobalStateService(QObject):
    calibration_state_changed = Signal()
    cam_preview_state_changed = Signal()
    wizard_active_state_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.calibration_state = False
        self.cam_preview_state = False
        self.wizard_active_state = False

    @Property(bool, notify=calibration_state_changed)
    def is_calibrated(self):
        return self.calibration_state

    @is_calibrated.setter
    def is_calibrated(self, value):
        if self.calibration_state != value:
            self.calibration_state = value
            self.calibration_state_changed.emit(value)

    @Property(bool, notify=cam_preview_state_changed)
    def is_preview_active(self):
        return self.cam_preview_state

    @is_preview_active.setter
    def is_cam_preview_active(self, value):
        if self.cam_preview_state != value:
            self.cam_preview_state = value
            self.cam_preview_state_changed.emit(value)

    @Property(bool, notify=wizard_active_state_changed)
    def is_wizard_active(self):
        return self.wizard_active_state

    @is_wizard_active.setter
    def is_wizard_active(self, value):
        if self.wizard_active_state != value:
            self.wizard_active_state = value
            self.wizard_active_state_changed.emit(value)
