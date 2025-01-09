from PySide6.QtWidgets import QWizard
from services.service_locator import ServiceLocator
from calibration_module.views.camera_setup_page import CameraSetupPage

class CalibrationWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calibration Wizard")
        self.resize(800, 600)
        self.locator = ServiceLocator.get_instance()
        self.viewmodel = self.locator.get_service("wizard_viewmodel")
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        welcome_page = self.locator.get_service("welcome_page")
        self.addPage(welcome_page)
        self.addPage(CameraSetupPage())


    def connect_signals(self):
        self.finished.connect(self.viewmodel.handle_calibration_complete)