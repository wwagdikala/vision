from PySide6.QtCore import QObject, Signal, Property

class WelcomeViewModel(QObject):

    text_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._intro_text = """
        The calibration process consists of the following steps:
        1. Camera setup and verification
        2. System calibration using calibration cube
        3. Registration with magnetic tracking system
        4. Validation of calibration accuracy
        
        Please ensure you have:
        - Calibration cube ready
        - Magnetic tracking system running
        - Clear workspace around the aquarium
        """

    @Property(str, notify=text_changed)
    def intro_text(self):
        return self._intro_text

    @intro_text.setter
    def set_intro_text(self, text):
        self._intro_text = text
        self.text_changed.emit(text)
