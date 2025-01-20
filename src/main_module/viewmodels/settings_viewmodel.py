from PySide6.QtCore import QObject, Signal, Property
from core.constants.settings_constants import CalibrationTarget, CameraSetup
from services.service_locator import ServiceLocator
from services.navigation_service import ViewType


class SettingsViewModel(QObject):
    settings_changed = Signal()

    def __init__(self):
        super().__init__()
        self._settings_service = ServiceLocator.get_instance().get_service(
            "settings_service"
        )
        self._navigation_service = ServiceLocator.get_instance().get_service(
            "navigation_service"
        )

        # Connect to service changes
        self._settings_service.setting_changed.connect(self._on_setting_changed)

    def _on_setting_changed(self, key: str, value: str):
        self.settings_changed.emit()

    def update_setting(self, key: str, value: str):
        """Update setting value using the nested structure"""
        self._settings_service.update_setting(key, value)

    def get_setting(self, key: str) -> str:
        """Get setting value using the nested structure"""
        return self._settings_service.get_setting(key)

    @Property(str, notify=settings_changed)
    def camera_setup(self) -> str:
        return self._settings_service.get_setting("camera_setup")

    @camera_setup.setter
    def camera_setup(self, value: str):
        if CameraSetup.is_valid(value):
            self._settings_service.update_setting("camera_setup", value)

    @Property(str, notify=settings_changed)
    def target_type(self) -> str:
        return self._settings_service.get_setting("target_type")

    @target_type.setter
    def target_type(self, value: str):
        if CalibrationTarget.is_valid(value):
            self._settings_service.update_setting("target_type", value)

    def get_camera_setups(self) -> list:
        return CameraSetup.list()

    def get_target_types(self) -> list:
        return CalibrationTarget.list()

    def get_setting(self, key: str) -> str:
        return self._settings_service.get_setting(key)

    # Add property setters/getters for each new setting
    @Property(int, notify=settings_changed)
    def pattern_rows(self) -> int:
        return int(self._settings_service.get_setting("pattern_rows"))

    @pattern_rows.setter
    def pattern_rows(self, value: int):
        self._settings_service.update_setting("pattern_rows", str(value))

    @Property(int, notify=settings_changed)
    def pattern_cols(self) -> int:
        return int(self._settings_service.get_setting("pattern_cols"))

    @pattern_rows.setter
    def pattern_cols(self, value: int):
        self._settings_service.update_setting("pattern_cols", str(value))

    def navigate_back(self):
        self._navigation_service.navigate_to(ViewType.MAIN)
