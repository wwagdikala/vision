from PySide6.QtCore import Signal, QObject
from pathlib import Path
import json

class SettingsService(QObject):
    setting_changed = Signal(str, str, object)  # section, key, value
    
    def __init__(self):
        super().__init__()
        self.settings_file = Path("config/app_settings.json")
        self._settings = {}

        self._default_settings = {
            "calibration": {
                "target_type": "cube",
                "cube_size_mm": 100,
            },
            "cameras": {
                "exposure": 100,
            },
            "app": {
                "data_save_path": "dklfd",
            },
        }
        self.load_settings()

    def get_settings(self, section: str, key: str):
        return self._settings.get(section, {}).get(key) 
    
    def update_settings(self, section: str, key: str, value):
        if section not in self._settings:
            self._settings[section] = {}
        if self.get_settgins(section, key) != value:
            self._settings[section][key] = value
            self.setting_changed.emit(section, key, value)
            self.save_settings()

    def load_settings(self):
        try:
            settings_path = Path(self.settings_file)
            if settings_path.exists():
                with open(self.settings_file, 'r') as f:
                    content = f.read()
                    if content.strip():
                        self._settings.update(json.loads(content))
                    else:
                        print("Settings file is empty, using defaults")
            else:
                print("Settings file doesn't exist, creating with defaults")
                self._settings = self._default_settings.copy()
                self.save_settings()  # Create file with defaults
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in settings file: {e}")
            print("Backing up corrupted file and creating new one with defaults")
            # Backup corrupted file
            if settings_path.exists():
                backup_path = str(settings_path) + '.backup'
                settings_path.rename(backup_path)
            self.save_settings()
        except Exception as e:
            print(f"Unexpected error loading settings: {e}")
            self.save_settings()

    def save_settings(self):
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file , 'w') as f:
                json.dump(self._settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")
