from PySide6.QtCore import QObject, Signal
from services.service_locator import ServiceLocator


class WizardViewModel(QObject):
    status_changed = Signal(str)
    progress_updated = Signal(int)
    wizard_completed = Signal(bool, str)  # Changed from calibration_finished

    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.settings_service = self.locator.get_service("settings_service")

        # Track overall wizard state
        self.current_step = 0
        self.step_statuses = {}
        self._load_configuration()

    def _load_configuration(self):
        """Load wizard configuration"""
        try:
            # Load general wizard settings
            # NOT camera-specific settings
            pass
        except Exception as e:
            print(f"Error loading wizard configuration: {str(e)}")

    def handle_step_completion(
        self, step_number: int, success: bool, results: dict = None
    ):
        """Handle completion of a wizard step"""
        self.step_statuses[step_number] = success
        if success and self._can_proceed():
            self.progress_updated.emit(self._calculate_progress())
