import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication
from main_module.views.main_window import MainWindow
from services.service_locator import ServiceLocator
from services.settings_service import SettingsService
from services.navigation_service import NavigationService
from services.navigation_service import ViewType
from calibration_module.main import CalibrationModule

from main_module.viewmodels.main_viewmodel import MainViewViewModel
from main_module.viewmodels.settings_viewmodel import SettingsViewModel
from calibration_module.viewmodels.wizard_viewmodel import WizardViewModel

from main_module.views.main_view import MainView 
from main_module.views.settings_view import SettingsView
from calibration_module.views.wizard_view import CalibrationWizard

from calibration_module.models.wizard_model import WizardModel
from core.error_handling.error_manager import ErrorManager

def initialize(locator):
    locator.register_service("settings_service", SettingsService())

    error_manager = ErrorManager()

    locator.register_service("error_manager", error_manager)
    calibration_module = CalibrationModule()
    wizard_view = calibration_module.initalize()
    locator.register_service("calibration_module", calibration_module)
    

    locator.register_service("main_viewmodel", MainViewViewModel())
    locator.register_service("settings_viewmodel", SettingsViewModel())
    
    locator.register_service("main_view", MainView())
    locator.register_service("settings_view", SettingsView())
    locator.register_service("wizard_view", wizard_view)

    navigation_service = locator.get_service("navigation_service")
    navigation_service.register_view(ViewType.MAIN, locator.get_service("main_view"))
    navigation_service.register_view(ViewType.SETTINGS, locator.get_service("settings_view"))
    navigation_service.register_view(ViewType.CALIBRATION, locator.get_service("wizard_view"))

    # return navigation_service.get_current_view()

    
if __name__ == "__main__":
    app = QApplication([])
    locator = ServiceLocator.get_instance()
    locator.register_service("navigation_service", NavigationService())
    window = MainWindow()
    initialize(locator)
    window.show()
    app.exec()