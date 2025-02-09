from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from services.service_locator import ServiceLocator
from services.navigation_service import ViewType
import os
from pathlib import Path

class MainView(QWidget):
    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.view_model = self.locator.get_service("main_viewmodel")
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # Use QHBoxLayout for horizontal arrangement
        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()


        # Define button configurations
        buttons = [
            ("Calibrate", "calibration.png", ViewType.CALIBRATION),
            ("Measure", "measure.png", ViewType.MEASUREMENT),
            ("Archive", "archive.png", ViewType.ARCHIVE),
            ("Settings", "settings.png", ViewType.SETTINGS)
        ]

        # Create and style buttons
        for text, icon_name, view_type in buttons:
            btn = self.create_nav_button(text, icon_name, view_type)
            button_layout.addWidget(btn)

        # Center the buttons
        button_layout.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(button_layout)
        main_layout.setAlignment(Qt.AlignCenter)
        
        self.setLayout(main_layout)

    def create_nav_button(self, text, icon_name, view_type):
        btn = QPushButton(text)

        icon_path = str(Path(__file__).resolve().parent.parent / "assets" / icon_name)
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
        else:
            print(f"Warning: Icon not found at {icon_path}")

        
        # Style the button
        btn.setMinimumSize(120, 120)
        btn.setMaximumSize(120, 120)
        btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #cccccc;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        
        # Set icon size
        btn.setIconSize(btn.size() * 0.5)
        
        # Connect click handler
        btn.clicked.connect(lambda: self.view_model.navigate_to(view_type))
        
        return btn

    def connect_signals(self):
        self.view_model.get_global_state().wizard_active_state_changed.connect(
            self.change_view_block
        )

    def change_view_block(self, is_active: bool):
        for element in self.findChildren(QWidget):
            element.setEnabled(not is_active)