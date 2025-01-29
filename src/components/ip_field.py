from PySide6 import QtCore, QtWidgets, QtGui


class IPSsegmentEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setValidator(QtGui.QIntValidator(0, 255, self))
        self.setMaxLength(3)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(50)
        self.segment_index = 0

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        current_text = self.text()
        cursor_pos = self.cursorPosition()
        handled = False

        if event.key() == QtCore.Qt.Key.Key_Right:
            if cursor_pos == len(current_text) and self.segment_index < 3:
                self.focusNextChild()
                handled = True
        elif event.key() == QtCore.Qt.Key.Key_Left:
            if cursor_pos == 0 and self.segment_index > 0:
                self.focusPreviousChild()
                handled = True
        elif event.key() == QtCore.Qt.Key.Key_Backspace and not current_text:
            if self.segment_index > 0:
                self.focusPreviousChild()
                handled = True
        elif event.key() in (QtCore.Qt.Key.Key_Period, QtCore.Qt.Key.Key_Space):
            if self.segment_index < 3:
                self.focusNextChild()
                handled = True

        if not handled and len(current_text) >= 3 and self.segment_index < 3:
            self.focusNextChild()


class IPInputWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments = []
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for i in range(4):
            edit = IPSsegmentEdit()
            edit.segment_index = i
            self.segments.append(edit)
            layout.addWidget(edit)
            if i < 3:
                dot = QtWidgets.QLabel(".")
                dot.setFixedWidth(10)
                layout.addWidget(dot)

        self.setLayout(layout)

    def get_ip(self):
        ip_parts = []
        for edit in self.segments:
            text = edit.text()
            ip_parts.append(text if text else "0")
        return ".".join(ip_parts)

    def set_ip(self, ip):
        print(ip)
        parts = ip.split(".")
        for edit, part in zip(self.segments, parts):
            edit.setText(part)

    def set_readonly(self, readonly):
        for edit in self.segments:
            edit.setReadOnly(readonly)
