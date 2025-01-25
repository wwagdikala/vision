from PySide6.QtCore import QObject, Signal
import json
from pathlib import Path


class SettingsService(QObject):
    setting_changed = Signal(str, str)  # key, value

    def __init__(self):
        super().__init__()
        current_dir = Path(__file__).resolve().parent.parent / "config"
        self._settings_file = current_dir / "settings.json"
        print(f"Settings file: {self._settings_file}")

        self._default_settings = {
            "calibration": {
                "target_type": "checkerboard",
                "square_size": 25.5,
                "required_angles": 1,
                "min_quality_score": 0.25,
                "min_coverage": 0.25,
                "pattern_rows": 6,
                "pattern_cols": 9,
            },
            "cameras": {"camera_setup": "stereo_2"},
        }
        self._settings = self._default_settings.copy()
        self.load_settings()

    # In settings_service.py
    def get_setting(self, key: str) -> str:
        if "." in key:
            section, setting = key.split(".")
            return self._settings.get(section, {}).get(setting)
        # For backward compatibility with existing code
        # First try in calibration section
        value = self._settings.get("calibration", {}).get(key)
        if value is not None:
            return value
        # Then try in cameras section
        value = self._settings.get("cameras", {}).get(key)
        if value is not None:
            return value

        value = self._settings.get("app", {}).get(key)
        if value is not None:
            return value
        # Finally try in root (though we shouldn't have any here)
        return self._settings.get(key)

    def update_setting(self, key: str, value: str):
        if "." in key:
            section, setting = key.split(".")
            if section not in self._settings:
                self._settings[section] = {}
            self._settings[section][setting] = value
        else:
            self._settings[key] = value
        self.save_settings()
        self.setting_changed.emit(key, value)

    def load_settings(self):
        try:
            if self._settings_file.exists():
                with open(self._settings_file, "r") as f:
                    self._settings.update(json.load(f))
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        try:
            with open(self._settings_file, "w") as f:
                json.dump(self._settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
