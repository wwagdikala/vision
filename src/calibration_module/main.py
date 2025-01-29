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
from calibration_module.viewmodels.calibration_viewmodel import CalibrationViewModel
from calibration_module.views.calibration_page import CalibrationPage
from calibration_module.models.calibration_model import CalibrationModel
from calibration_module.views.communication_page import CommunicationSetupPage
from calibration_module.viewmodels.communication_viewmodel import (
    CommunicationSetupViewModel,
)


class CalibrationModule:
    def __init__(self):
        pass

    def initalize(self):
        camera_module = CameraModule()
        camera_module.initialize()
        locator = ServiceLocator.get_instance()

        calibration_model = CalibrationModel()
        wizard_model = WizardModel()
        locator.register_service("wizard_model", wizard_model)
        locator.register_service("calibration_model", calibration_model)

        locator.register_service("wizard_viewmodel", WizardViewModel())
        locator.register_service("welcome_viewmodel", WelcomeViewModel())
        locator.register_service(
            "communication_viewmodel", CommunicationSetupViewModel()
        )
        locator.register_service("calibration_viewmodel", CalibrationViewModel())

        locator.register_service("welcome_page", WelcomePage())
        locator.register_service("communication_view", CommunicationSetupPage())
        locator.register_service("calibration_page", CalibrationPage())

        return CalibrationWizard()

    def run(self):
        app = QApplication([])
        wizard = self.initalize()
        wizard.show()
        app.exec()


if __name__ == "__main__":
    calibration_module = CalibrationModule()
    calibration_module.run()
