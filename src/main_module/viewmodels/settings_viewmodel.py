from PySide6.QtCore import QObject
from PySide6.QtCore import Signal, Property
from services.service_locator import ServiceLocator
from core.constants.settings_constants import CalibrationTarget
from services.navigation_service import ViewType

class SettingsViewModel(QObject):
    target_type_changed = Signal()
    def __init__(self):
        super().__init__()
        self.settings_locator = ServiceLocator.get_instance().get_service("settings_service")
        self.naviation_sevice = ServiceLocator.get_instance().get_service("navigation_service")
        self._target_type = self.get_settings("calibration", "target_type")
        self.connect_signals()

    def get_target_type(self):
        return self._target_type
    
    def set_target_type(self, value):
        if CalibrationTarget.is_valid(value):
            self._target_type = value
            self.update_settings("calibration", "target_type", value)
            self.target_type_changed.emit()
        else:
            print(f"Invalid target type: {value}")
    
    target_type = Property(str, get_target_type, set_target_type, notify=target_type_changed)

    def get_target_types(self):
        return CalibrationTarget.list()

    def get_settings(self, section: str, key: str):
        return self.settings_locator.get_settings(section, key) 
    
    def update_settings(self, section: str, key: str, value):
        self.settings_locator.update_settings(section, key, value)

    def connect_signals(self):
        self.settings_locator.setting_changed.connect(self.on_setting_changed)

    def on_setting_changed(self, section: str, key: str, value):
        pass

    def navigate_to(self, view_type: "ViewType"):
        self.naviation_sevice.navigate_to(view_type)

        

