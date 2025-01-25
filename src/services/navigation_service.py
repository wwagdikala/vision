from enum import Enum
from typing import Dict, Union
from PySide6.QtWidgets import QStackedWidget, QWizard, QWidget
from PySide6.QtCore import Signal, Property, QObject
from services.service_locator import ServiceLocator


class ViewType(Enum):
    MAIN = "main_view"
    CALIBRATION = "calibration_view"
    MEASUREMENT = "measurement_view"
    ARCHIVE = "archive_view"
    SETTINGS = "settings_view"

    @classmethod
    def list(cls):
        return [member.value for member in cls]


class NavigationService(QObject):

    def __init__(self):
        super().__init__()
        self.global_state = ServiceLocator.get_instance().get_service("global_state")
        self.stacked_widget = None
        self.views: Dict[ViewType, Union[QWizard, QWidget]] = {}
        self._active_wizard = self.global_state.is_wizard_active

    def set_stacked_widget(self, widget: QStackedWidget):
        """Called by MainWindow to set the stacked widget"""
        self.stacked_widget = widget
        # Add any previously registered views to the widget
        for view in self.views.values():
            self.stacked_widget.addWidget(view)

    def register_view(self, view_type: ViewType, view: Union[QWizard, QWidget]):
        """Register a view for a specific view type"""
        self.views[view_type] = view
        if isinstance(view, QWidget) and not isinstance(view, QWizard):
            self.stacked_widget.addWidget(view)

    def navigate_to(self, view_type: ViewType):
        if view_type not in self.views:
            return

        view = self.views[view_type]

        if isinstance(view, QWizard):
            self.global_state.is_wizard_active = True
            view.finished.connect(self.on_wizard_closed)
            view.show()
        else:
            self.stacked_widget.setCurrentWidget(view)

    def on_wizard_closed(self):
        self.global_state.is_wizard_active = False

    def get_current_view(self):
        """Get the currently active view"""
        return self.stacked_widget.currentWidget()
