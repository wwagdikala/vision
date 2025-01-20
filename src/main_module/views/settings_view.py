from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QGroupBox,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
)
from services.service_locator import ServiceLocator


class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.viewmodel = ServiceLocator.get_instance().get_service("settings_viewmodel")
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Settings group
        settings_group = QGroupBox("System Settings")
        form_layout = QFormLayout()

        # Camera setup combo
        self.camera_setup_combo = QComboBox()
        self.camera_setup_combo.addItems(self.viewmodel.get_camera_setups())
        self.camera_setup_combo.setCurrentText(self.viewmodel.camera_setup)
        form_layout.addRow("Camera Setup:", self.camera_setup_combo)

        # Target type combo
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(self.viewmodel.get_target_types())
        self.target_type_combo.setCurrentText(self.viewmodel.target_type)
        form_layout.addRow("Target Type:", self.target_type_combo)

        self.pattern_rows_spin = QSpinBox()
        self.pattern_rows_spin.setRange(2, 20)
        self.pattern_rows_spin.setValue(int(self.viewmodel.get_setting("pattern_rows")))
        form_layout.addRow("Pattern Rows:", self.pattern_rows_spin)

        self.pattern_cols_spin = QSpinBox()
        self.pattern_cols_spin.setRange(2, 20)
        self.pattern_cols_spin.setValue(int(self.viewmodel.get_setting("pattern_cols")))
        form_layout.addRow("Pattern Columns:", self.pattern_cols_spin)

        # Add quality threshold settings
        self.quality_score_spin = QDoubleSpinBox()
        self.quality_score_spin.setRange(0.1, 1.0)
        self.quality_score_spin.setSingleStep(0.05)
        self.quality_score_spin.setValue(
            float(self.viewmodel.get_setting("min_quality_score"))
        )
        form_layout.addRow("Min Quality Score:", self.quality_score_spin)

        self.coverage_spin = QDoubleSpinBox()
        self.coverage_spin.setRange(0.1, 1.0)
        self.coverage_spin.setSingleStep(0.05)
        self.coverage_spin.setValue(float(self.viewmodel.get_setting("min_coverage")))
        form_layout.addRow("Min Coverage:", self.coverage_spin)

        settings_group.setLayout(form_layout)
        layout.addWidget(settings_group)
        layout.addStretch()

        buttons_section = QWidget()
        self.button_layout = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.back_btn)
        buttons_section.setLayout(self.button_layout)
        layout.addWidget(buttons_section)

    def connect_signals(self):
        # Connect UI to ViewModel
        self.camera_setup_combo.currentTextChanged.connect(
            lambda v: self.viewmodel.update_setting("cameras.camera_setup", v)
        )
        self.target_type_combo.currentTextChanged.connect(
            lambda v: self.viewmodel.update_setting("calibration.target_type", v)
        )
        # Add new signals
        self.pattern_rows_spin.valueChanged.connect(
            lambda v: self.viewmodel.update_setting("calibration.pattern_rows", v)
        )
        self.pattern_cols_spin.valueChanged.connect(
            lambda v: self.viewmodel.update_setting("calibration.pattern_cols", v)
        )
        self.quality_score_spin.valueChanged.connect(
            lambda v: self.viewmodel.update_setting(
                "calibration.min_quality_score", str(v)
            )
        )
        self.coverage_spin.valueChanged.connect(
            lambda v: self.viewmodel.update_setting("calibration.min_coverage", str(v))
        )

        self.back_btn.clicked.connect(self.viewmodel.navigate_back)
        # Update UI when settings change
        self.viewmodel.settings_changed.connect(self.update_ui)

    def update_ui(self):
        self.camera_setup_combo.setCurrentText(self.viewmodel.camera_setup)
        self.target_type_combo.setCurrentText(self.viewmodel.target_type)
