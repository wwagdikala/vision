# src/core/error_handling/error_manager.py

from PySide6.QtCore import QObject, Signal
import traceback
from typing import Optional, List
from .exceptions import ErrorSeverity, ErrorCategory, ValidationSystemError

class SystemError:
    """Represents a system error with full context"""
    def __init__(self, 
                 severity: ErrorSeverity,
                 category: ErrorCategory,
                 message: str,
                 exception: Optional[Exception] = None,
                 recovery_hint: Optional[str] = None):
        self.severity = severity
        self.category = category
        self.message = message
        self.exception = exception
        self.recovery_hint = recovery_hint
        self.stack_trace = traceback.format_exc() if exception else None
        
    def __str__(self):
        return f"[{self.severity.value}][{self.category.value}] {self.message}"

class ErrorManager(QObject):
    """Centralized error management system"""
    
    error_occurred = Signal(SystemError)  # Emitted when new error occurs
    error_resolved = Signal(SystemError)  # Emitted when error is resolved
    
    def __init__(self):
        super().__init__()
        self.active_errors: List[SystemError] = []
        self.error_history: List[SystemError] = []
        
    def report_error(self, error: SystemError):
        """Report a new system error"""
        self.active_errors.append(error)
        self.error_history.append(error)
        self.error_occurred.emit(error)
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.handle_critical_error(error)
    
    def resolve_error(self, error: SystemError):
        """Mark an error as resolved"""
        if error in self.active_errors:
            self.active_errors.remove(error)
            self.error_resolved.emit(error)
    
    def handle_critical_error(self, error: SystemError):
        """Handle critical system errors"""
        self.log_critical_error(error)
        # Additional critical error handling as needed
        
    def log_critical_error(self, error: SystemError):
        """Log critical error details for analysis"""
        error_details = {
            'severity': error.severity.value,
            'category': error.category.value,
            'message': error.message,
            'stack_trace': error.stack_trace,
            'recovery_hint': error.recovery_hint
        }
        # TODO: Implement logging once logging system is in place
        
    def get_active_errors(self, 
                         severity: Optional[ErrorSeverity] = None,
                         category: Optional[ErrorCategory] = None) -> List[SystemError]:
        """Get filtered list of active errors"""
        errors = self.active_errors
        if severity:
            errors = [e for e in errors if e.severity == severity]
        if category:
            errors = [e for e in errors if e.category == category]
        return errors
    
    def has_critical_errors(self) -> bool:
        """Check if there are any active critical errors"""
        return any(e.severity == ErrorSeverity.CRITICAL 
                  for e in self.active_errors)