from PySide6.QtCore import QObject, Signal
from services.navigation_service import ViewType
from services.service_locator import ServiceLocator

class MainViewViewModel(QObject):
    wizard_active_changed = Signal(bool)


    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.navigation_service = self.locator.get_service("navigation_service")
        self.navigation_service.active_wizard_changed.connect(self.wizard_active_changed.emit)

    def navigate_to(self, view_type: "ViewType"):
        self.navigation_service.navigate_to(view_type)

        
    
       