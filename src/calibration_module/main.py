import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication
from services.service_locator import ServiceLocator
from calibration_module.views.wizard_view import CalibrationWizard
from calibration_module.viewmodels.wizard_viewmodel import WizardViewModel
from calibration_module.views.welcome_page import WelcomePage
from calibration_module.viewmodels.welcome_viewmodel import WelcomeViewModel
from camera_module.camera_module import CameraModule
from calibration_module.models.wizard_model import WizardModel

class CalibrationModule:
    def __init__(self):
        pass

    def initalize(self):
        camera_module = CameraModule()
        camera_module.initialize()
        locator = ServiceLocator.get_instance()

        wizard_model = WizardModel()
        locator.register_service("wizard_model", wizard_model)
        wizard_viewmodel = WizardViewModel()
        welcome_viewmodel = WelcomeViewModel()
        locator.register_service("welcome_viewmodel", welcome_viewmodel)
        welcome_page = WelcomePage()
        locator.register_service("welcome_page", welcome_page)
        locator.register_service("wizard_viewmodel", wizard_viewmodel)

        return CalibrationWizard()

    def run(self):
        app = QApplication([])
        wizard = self.initalize()
        wizard.show()
        app.exec()

if __name__ == "__main__":
    calibration_module = CalibrationModule()
    calibration_module.run()