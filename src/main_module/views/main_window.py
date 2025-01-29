from PySide6.QtWidgets import QMainWindow, QStackedWidget
from services.service_locator import ServiceLocator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Window")
        self.resize(800, 600)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Get navigation service and connect it
        locator = ServiceLocator.get_instance()
        navigation_service = locator.get_service('navigation_service')
        navigation_service.set_stacked_widget(self.stacked_widget)