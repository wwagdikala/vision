from PySide6.QtCore import QObject, Signal, Property
from PySide6.QtWidgets import QWizard
from services.service_locator import ServiceLocator
import numpy as np
from core.constants.calibration_constants import (
    CalibrationTarget, CameraSetupType, 
    CalibrationConfig, CalibrationResults
)
from core.error_handling.exceptions import CalibrationError
from calibration_module.models.factory import TargetDetectorFactory

class WizardViewModel(QObject):
    # Signals for view updates
    status_changed = Signal(str)
    progress_updated = Signal(int)
    calibration_finished = Signal(bool, str, dict)  # success, message, results
    
    def __init__(self):
        super().__init__()
        self.locator = ServiceLocator.get_instance()
        self.settings_service = self.locator.get_service('settings_service')
        
        # Initialize state
        self.calibration_successful = False
        self.is_calibrating = False
        self.calibration_results = None
        
        # Load configuration
        self._load_configuration()
        
    def _load_configuration(self):

        try:
            # Get camera setup type
            camera_setup_type = self.settings_service.get_settings(
                "calibration", "camera_setup", "type"
            )
            if camera_setup_type is None:
                raise ValueError("Camera setup type not found in settings")

            # Get target type
            target_type = self.settings_service.get_settings(
                "calibration", "target_type"
            )
            if target_type is None:
                raise ValueError("Target type not found in settings")

            # Create configuration object
            self.config = CalibrationConfig(
                camera_setup=CameraSetupType(camera_setup_type),
                target_type=CalibrationTarget(target_type),
                target_settings=self.settings_service.get_settings(
                    "calibration", "target_settings", target_type
                ) or {},
                quality_thresholds=self.settings_service.get_settings(
                    "calibration", "quality_thresholds"
                ) or {},
                validation_settings=self.settings_service.get_settings(
                    "calibration", "camera_setup", "cameras", 
                    camera_setup_type, "validation"
                ) or {}
            )

            # Create target detector based on configuration
            self.target_detector = TargetDetectorFactory.create(
                self.config.target_type,
                self.config.target_settings
            )

            # Set number of cameras based on setup type
            self.num_cameras = CameraSetupType.get_num_cameras(camera_setup_type)

        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            # Use default configuration
            self.config = CalibrationConfig(
                camera_setup=CameraSetupType.STEREO_3_COPLANAR,
                target_type=CalibrationTarget.CUBE,
                target_settings={
                    "size_mm": 100,
                    "min_corners": 6,
                    "corner_uncertainty_threshold": 0.5,
                    "refinement_window_size": 11
                },
                quality_thresholds={
                    "rms_error_threshold_mm": 0.2,
                    "min_cameras_per_point": 3,
                    "max_reprojection_error_mm": 0.2
                },
                validation_settings={}
            )
            self.num_cameras = 3


    def start_calibration(self, frames):
        """
        Start the calibration process with captured frames
        
        Args:
            frames: List of frames from each camera
        """
        if self.is_calibrating:
            self.status_changed.emit("Calibration already in progress")
            return False
            
        try:
            self.is_calibrating = True
            self.calibration_successful = False
            self.status_changed.emit("Starting calibration process...")
            self.progress_updated.emit(0)
            
            # Validate input
            if not self._validate_frames(frames):
                raise CalibrationError(
                    "Invalid frame input",
                    "Ensure all cameras are working and providing valid frames"
                )
            
            # Step 1: Target Detection (20% of progress)
            self.status_changed.emit("Detecting calibration target...")
            detection_results = []
            for i, frame in enumerate(frames):
                try:
                    result = self.target_detector.detect(frame)
                    detection_results.append(result)
                    self.progress_updated.emit(20 * (i + 1) // len(frames))
                except CalibrationError as e:
                    raise CalibrationError(
                        f"Target detection failed for camera {i+1}: {str(e)}",
                        e.recovery_hint
                    )
            
            # Step 2: Camera Calibration (60% of progress)
            self.status_changed.emit("Calibrating cameras...")
            calibration_service = self._get_calibration_service()
            
            calibration_results = calibration_service.calibrate(
                frames, detection_results, self.config,
                progress_callback=lambda p: self.progress_updated.emit(20 + int(p * 0.6))
            )
            
            # Step 3: Quality Validation (20% of progress)
            self.status_changed.emit("Validating calibration quality...")
            self._validate_calibration_quality(calibration_results)
            self.progress_updated.emit(100)
            
            # Store and report results
            self.calibration_results = calibration_results
            self.calibration_successful = True
            
            results_dict = {
                'rms_error': calibration_results.rms_error,
                'reprojection_error': sum(calibration_results.reprojection_errors) / len(calibration_results.reprojection_errors)
            }
            
            self.calibration_finished.emit(
                True, 
                "Calibration completed successfully", 
                results_dict
            )
            return True
            
        except CalibrationError as e:
            error_message = f"Calibration failed: {str(e)}"
            if e.recovery_hint:
                error_message += f"\nSuggestion: {e.recovery_hint}"
            self.calibration_finished.emit(False, error_message, None)
            return False
            
        except Exception as e:
            self.calibration_finished.emit(
                False,
                f"Unexpected error during calibration: {str(e)}",
                None
            )
            return False
            
        finally:
            self.is_calibrating = False

    def _validate_frames(self, frames) -> bool:
        """Validate input frames"""
        if len(frames) != self.num_cameras:
            return False
            
        for frame in frames:
            if frame is None or frame.size == 0:
                return False
        return True

    def _validate_calibration_quality(self, results: CalibrationResults):
        """Validate calibration results against quality thresholds"""
        # Check RMS error
        if results.rms_error > self.config.quality_thresholds['rms_error_threshold_mm']:
            raise CalibrationError(
                f"RMS error ({results.rms_error:.3f} mm) exceeds threshold "
                f"({self.config.quality_thresholds['rms_error_threshold_mm']} mm)",
                "Try improving lighting conditions and reducing environmental vibrations"
            )
        
        # Check reprojection errors
        mean_reproj_error = sum(results.reprojection_errors) / len(results.reprojection_errors)
        if mean_reproj_error > self.config.quality_thresholds['max_reprojection_error_mm']:
            raise CalibrationError(
                f"Mean reprojection error ({mean_reproj_error:.3f} mm) exceeds threshold",
                "Try improving target positioning and camera stability"
            )
        
        # Validate camera poses if validation settings are provided
        if self.config.validation_settings:
            self._validate_camera_poses(results)

    def _validate_camera_poses(self, results: CalibrationResults):
        """Validate camera poses against physical measurements if available"""
        if self.config.camera_setup == CameraSetupType.STEREO_3:
            # Validate stereo baseline distances if provided
            if 'camera_distances_mm' in self.config.validation_settings:
                expected_distances = self.config.validation_settings['camera_distances_mm']
                max_error = self.config.validation_settings.get('max_baseline_error_percent', 5.0)
                
                # Calculate and validate distances
                distances = self._calculate_camera_distances(results)
                for pair, expected in expected_distances.items():
                    measured = distances.get(pair)
                    if measured:
                        error_percent = abs(measured - expected) / expected * 100
                        if error_percent > max_error:
                            raise CalibrationError(
                                f"Camera distance validation failed for {pair}. "
                                f"Expected: {expected:.1f}mm, Measured: {measured:.1f}mm",
                                "Check camera mounting and measurement accuracy"
                            )

    def _calculate_camera_distances(self, results: CalibrationResults) -> dict:
        """Calculate distances between cameras from calibration results"""
        distances = {}
        for i in range(len(results.tvecs) - 1):
            dist = np.linalg.norm(results.tvecs[i] - results.tvecs[i+1])
            distances[f"cam{i+1}_to_cam{i+2}"] = dist
        return distances

    def _get_calibration_service(self):
        """Get appropriate calibration service based on configuration"""
        if self.config.camera_setup == CameraSetupType.STEREO_3:
            return self.locator.get_service('stereo_calibration_service')
        else:
            return self.locator.get_service('circle_calibration_service')

    def get_current_step(self) -> int:
        """Get current wizard step"""
        return self.wizard().currentId() if self.wizard() else 0
    
    def handle_wizard_finished(self, result: int):
        try:
            if result == QWizard.Accepted:
                # Save calibration results if successful
                if self.calibration_results:
                    self._save_calibration_results()

            # Reset state
            self.is_calibrating = False
            self.calibration_results = None

        except Exception as e:
            print(f"Error handling wizard completion: {str(e)}")
    @Property(bool)
    def is_complete(self):
        """Check if calibration is complete and successful"""
        return self.calibration_successful