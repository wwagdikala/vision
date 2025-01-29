from camera_module.models.camera_model import CameraModel
from camera_module.viewmodels.camera_viewmodel import CameraViewModel
from services.service_locator import ServiceLocator
from core.constants.settings_constants import CameraSetup


class CameraModule:
    def __init__(self):
        self.settings_service = ServiceLocator.get_instance().get_service(
            "settings_service"
        )
        self._setup_type = self.settings_service.get_setting("camera_setup")
        self._number_of_cameras = CameraSetup.get_num_cameras(self._setup_type)
        self.camera_models = []
        self.camera_viewmodels = []

    def initialize(self):
        # Create models for each camera
        for i in range(self._number_of_cameras):
            model = CameraModel(i)
            self.camera_models.append(model)

        # Create viewmodels with corresponding models
        for i, model in enumerate(self.camera_models):
            viewmodel = CameraViewModel(model)
            self.camera_viewmodels.append(viewmodel)

        # Register with service locator
        self._register_services()

    def _register_services(self):
        """Register all camera components with the service locator."""
        locator = ServiceLocator.get_instance()
        for i, (model, viewmodel) in enumerate(
            zip(self.camera_models, self.camera_viewmodels)
        ):
            locator.register_service(f"camera_model_{i}", model)
            locator.register_service(f"camera_viewmodel_{i}", viewmodel)
