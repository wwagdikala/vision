from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWizard
from services.navigation_service import ViewType
from services.service_locator import ServiceLocator


class MainViewViewModel(QObject):

    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.navigation_service = self.locator.get_service("navigation_service")
        self.global_state = self.locator.get_service("global_state")

    def navigate_to(self, view_type: "ViewType"):
        self.navigation_service.navigate_to(view_type)

    def get_global_state(self):
        return self.global_state
