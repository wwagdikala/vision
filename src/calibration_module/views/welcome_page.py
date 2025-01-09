from PySide6.QtWidgets import QWizardPage, QVBoxLayout, QLabel, QPushButton
from services.service_locator import ServiceLocator

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.viewmodel = self.locator.get_service("welcome_viewmodel")
        self.init_ui()


    def  init_ui(self):
        self.setTitle("Welcome to Calibration Wizard")
        self.setSubTitle("This wizard will guide you through the calibration process")
        
        layout = QVBoxLayout()
        intro_text = self.viewmodel.intro_text
        
        label = QLabel(intro_text)
        self.viewmodel.text_changed.connect(label.setText)
        label.setWordWrap(True)
        layout.addWidget(label)
        
        self.setLayout(layout)