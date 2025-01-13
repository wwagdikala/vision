from PySide6.QtCore import QObject, Signal, Property, Slot
from services.service_locator import ServiceLocator
from core.constants.settings_constants import CalibrationTarget, CameraSetup
from typing import Dict, Any
from copy import deepcopy

class SettingsViewModel(QObject):
    # Signals for property changes and validation
    target_type_changed = Signal()
    settings_changed = Signal(bool)  # Indicates if there are unsaved changes
    save_completed = Signal(bool, str)  # Success flag and message
    validation_error = Signal(str)  # Error message for invalid settings
    number_of_cameras_changed = Signal()

    def __init__(self):
        super().__init__()
        self.settings_service = ServiceLocator.get_instance().get_service("settings_service")
        
        # Store current and pending settings separately
        self._current_settings = {}
        self._pending_settings = {}
        self._has_unsaved_changes = False
        
        # Load initial settings
        self._load_settings()
        self.connect_signals()

    def _load_settings(self):
        """Load settings from service and create a working copy"""
        # Get all settings sections we care about
        sections = ["calibration", "cameras", "app"]
        
        for section in sections:
            self._current_settings[section] = {}
            for key in self._get_section_keys(section):
                value = self.settings_service.get_settings(section, key)
                self._current_settings[section][key] = value
        
        # Create a working copy for pending changes
        self._pending_settings = deepcopy(self._current_settings)

    def _get_section_keys(self, section: str) -> list:
        """Return expected keys for each section"""
        section_keys = {
            "calibration": ["target_type", "cube_size_mm"],
            "cameras": ["exposure"],
            "app": ["data_save_path"]
        }
        return section_keys.get(section, [])

    @Property(str, notify=target_type_changed)
    def target_type(self) -> str:
        """Get current target type setting"""
        return self._pending_settings["calibration"]["target_type"]
    
    @target_type.setter
    def target_type(self, value: str):
        if CalibrationTarget.is_valid(value):
            print(value)
            self._update_pending_setting("calibration", "target_type", value)
        else:
            self.validation_error.emit(f"Invalid target type: {value}")

    @Property(int, notify=number_of_cameras_changed)
    def number_of_cameras(self) -> int:
        return self._pending_settings["cameras"]["camera_setup"]
    
    @number_of_cameras.setter
    def number_of_cameras(self, value: int):
        if CameraSetup.is_valid(value):
            self._update_pending_setting("cameras", "camera_setup", value)
        else:
            self.validation_error.emit(f"Invalid camera setup: {value}")

    def get_camera_setups(self) -> list:
        setup_list = CameraSetup.num_of_cameras_list()
        print(setup_list)
        return [str(num) for num in setup_list]

    def _update_pending_setting(self, section: str, key: str, value: Any):
        """Update a pending setting and emit change signal"""
        if section not in self._pending_settings:
            self._pending_settings[section] = {}
            
        if self._pending_settings[section].get(key) != value:
            self._pending_settings[section][key] = value
            self._has_unsaved_changes = True
            self.settings_changed.emit(True)

    def save_settings(self) -> bool:
        """Save all pending settings to the service"""
        print(self._current_settings)
        try:
            # Validate all pending settings first
            if not self._validate_pending_settings():
                return False

            # Apply all changes
            for section, settings in self._pending_settings.items():
                for key, value in settings.items():
                    if self._current_settings[section].get(key) != value:
                        self.settings_service.update_settings(section, key, value)

            # Update current settings to match pending
            self._current_settings = deepcopy(self._pending_settings)
            self._has_unsaved_changes = False
            self.settings_changed.emit(False)
            self.save_completed.emit(True, "Settings saved successfully")
            return True

        except Exception as e:
            self.save_completed.emit(False, f"Failed to save settings: {str(e)}")
            return False

    def revert_changes(self):
        """Revert pending changes back to current settings"""
        self._pending_settings = deepcopy(self._current_settings)
        self._has_unsaved_changes = False
        self.settings_changed.emit(False)
        self.target_type_changed.emit()  # Refresh UI

    def _validate_pending_settings(self) -> bool:
        """Validate all pending settings before save"""
        try:
            # Validate target type
            target_type = self._pending_settings["calibration"]["target_type"]
            if not CalibrationTarget.is_valid(target_type):
                self.validation_error.emit(f"Invalid target type: {target_type}")
                return False

            # Validate cube size (must be positive)
            cube_size = self._pending_settings["calibration"]["cube_size_mm"]
            if not isinstance(cube_size, (int, float)) or cube_size <= 0:
                self.validation_error.emit("Cube size must be a positive number")
                return False

            # Validate camera exposure (must be positive)
            exposure = self._pending_settings["cameras"]["exposure"]
            if not isinstance(exposure, int) or exposure <= 0:
                self.validation_error.emit("Exposure must be a positive integer")
                return False

            # Validate data save path (must be non-empty)
            save_path = self._pending_settings["app"]["data_save_path"]
            if not save_path or not isinstance(save_path, str):
                self.validation_error.emit("Invalid data save path")
                return False

            return True

        except Exception as e:
            self.validation_error.emit(f"Validation error: {str(e)}")
            return False

    def connect_signals(self):
        """Connect to settings service signals"""
        self.settings_service.setting_changed.connect(self._on_service_setting_changed)

    def _on_service_setting_changed(self, section: str, key: str, value: Any):
        """Handle settings changes from the service"""
        if section in self._current_settings:
            self._current_settings[section][key] = value
            # Only update pending if no unsaved changes
            if not self._has_unsaved_changes:
                self._pending_settings[section][key] = value

    def get_target_types(self) -> list:
        """Get list of valid target types"""
        return CalibrationTarget.list()

    @Property(bool, notify=settings_changed)
    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes"""
        return self._has_unsaved_changes