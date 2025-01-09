from enum import Enum
from typing import Dict, Union
from PySide6.QtWidgets import QStackedWidget, QWizard, QWidget
from PySide6.QtCore import Signal, Property, QObject 

class ViewType(Enum):
    MAIN = 'main_view'
    CALIBRATION = 'calibration_view'
    MEASUREMENT = 'measurement_view'
    ARCHIVE = 'archive_view'
    SETTINGS = 'settings_view'

    @classmethod
    def list(cls):
        return [member.value for member in cls]


class NavigationService(QObject):
    """
    Centralizes navigation logic and maintains view state.
    Created once at startup and accessed through ServiceLocator.
    """
    active_wizard_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.stacked_widget = None
        self.views: Dict[ViewType, Union[QWizard, QWidget]] = {}
        self._active_wizard = None
    
    @Property(bool, notify=active_wizard_changed)
    def active_wizard(self):
        return self._active_wizard
    
    @active_wizard.setter
    def active_wizard(self, value):
       if self._active_wizard != value:
            self._active_wizard = value
            self.active_wizard_changed.emit(value is not None)

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
        """Navigate to a specific view"""
        if view_type not in self.views:
            return
        
        view = self.views[view_type]

        if isinstance(view, QWizard):
            if self.active_wizard:
                self.active_wizard.close()
                self.active_wizard = None
            self.active_wizard = view
            view.show()
        else:
            self.stacked_widget.setCurrentWidget(view)

    def get_current_view(self):
        """Get the currently active view"""
        return self.stacked_widget.currentWidget()