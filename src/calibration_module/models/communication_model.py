from PySide6.QtCore import QObject, Signal, Property
from services.service_locator import ServiceLocator


class CommunicationModel(QObject):

    def __init__(self):
        super().__init__()
        self.service_settings = ServiceLocator.get_instance().get_service(
            "settings_service"
        )
        self.service_settings.setting_changed.connect(self.on_setting_changed)

    def on_setting_changed(self, key: str, value: str):
        pass
