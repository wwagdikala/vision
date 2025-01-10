from PySide6.QtCore import Signal, QObject
from pathlib import Path
import json
from typing import Any, Optional
from functools import reduce

class SettingsService(QObject):
    setting_changed = Signal(str, str, object)  # section, key, value
    
    def __init__(self):
        super().__init__()
        self._settings_file = Path("config/app_settings.json")
        self._settings = {}

        self._default_settings = {
            "calibration": {
                "camera_setup": {
                    "type": "stereo_3_coplanar",  # Updated to match our enum
                    "cameras": {
                        "stereo_3_coplanar": {
                            "num_cameras": 3,
                            "validation": {
                                "camera_distances_mm": {
                                    "cam1_to_cam2": 200,
                                    "cam2_to_cam3": 200
                                }
                            }
                        },
                        "circle_5": {
                            "num_cameras": 5,
                            "validation": {
                                "expected_circle_diameter_mm": 500
                            }
                        }
                    }
                },
                "target_type": "cube",
                "target_settings": {
                    "cube": {
                        "size_mm": 100,
                        "min_corners": 6,
                        "corner_uncertainty_threshold": 0.5,
                        "refinement_window_size": 11
                    }
                },
                "quality_thresholds": {
                    "rms_error_threshold_mm": 0.2,
                    "min_cameras_per_point": 3,
                    "max_reprojection_error_mm": 0.2
                }
            }
        }
        self.load_settings()

    def get_settings(self, *path_parts: str) -> Any:
        try:
            return reduce(
                lambda d, key: d.get(key, {}), 
                path_parts[:-1],
                self._settings
            ).get(path_parts[-1])
        except (AttributeError, IndexError):
            return None

    def update_settings(self, value: Any, *path_parts: str):
        """
        Update setting at specified path.
        
        Args:
            value: New value to set
            *path_parts: Path to the setting to update
            
        Example:
            update_settings("cube", "calibration", "target_type")
        """
        if not path_parts:
            return

        # Navigate to the parent dictionary
        current = self._settings
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Update the value
        current[path_parts[-1]] = value
        
        # Emit signal with the full path and new value
        self.setting_changed.emit(".".join(path_parts), path_parts[-1], value)
        
        self.save_settings()

    def load_settings(self):
        """Load settings from file, use defaults if necessary"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    content = f.read()
                    if content.strip():
                        self._settings.update(json.loads(content))
                    else:
                        print("Settings file is empty, using defaults")
                        self._settings = self._default_settings.copy()
            else:
                print("Settings file doesn't exist, creating with defaults")
                self._settings = self._default_settings.copy()
                self.save_settings()
        except Exception as e:
            print(f"Error loading settings: {e}")
            self._settings = self._default_settings.copy()
            self.save_settings()

    def save_settings(self):
        """Save current settings to file"""
        try:
            self._settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._settings_file, 'w') as f:
                json.dump(self._settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")