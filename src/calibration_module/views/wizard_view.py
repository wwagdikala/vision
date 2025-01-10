from PySide6.QtWidgets import QWizard
from services.service_locator import ServiceLocator
from calibration_module.views.camera_setup_page import CameraSetupPage
from calibration_module.views.welcome_page import WelcomePage

class CalibrationWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calibration Wizard")
        self.resize(800, 600)
        self.locator = ServiceLocator.get_instance()
        
        # Get or create viewmodel
        self.viewmodel = self.locator.get_service("wizard_viewmodel")
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        self.addPage(WelcomePage())
        self.addPage(CameraSetupPage())

    def connect_signals(self):
        if hasattr(self.viewmodel, 'handle_wizard_finished'):
            self.finished.connect(self.viewmodel.handle_wizard_finished)
        else:
            print("Warning: WizardViewModel missing handle_wizard_finished method")