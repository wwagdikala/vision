
from camera_module.models.camera_model import CameraModel
from camera_module.viewmodels.camera_viewmodel import CameraViewModel
from services.service_locator import ServiceLocator



class CameraModule:
    def __init__(self):
        self.camera_models = []
        self.camera_viewmodels = []

    def initialize(self):
        """
        Initializes camera components, ensuring proper connection between
        models and viewmodels.
        """
        # First create all models
        for i in range(3):
            model = CameraModel(i)
            self.camera_models.append(model)
        
        # Then create viewmodels, passing them the corresponding models
        for i, model in enumerate(self.camera_models):
            viewmodel = CameraViewModel(model)  # Pass the model, not just index
            self.camera_viewmodels.append(viewmodel)
        
        # Register with service locator
        self._register_services()

    def _register_services(self):
        """
        Registers all camera components with the service locator.
        """
        locator = ServiceLocator.get_instance()
        for i, (model, viewmodel) in enumerate(zip(
                self.camera_models, self.camera_viewmodels)):
            locator.register_service(f'camera_model_{i}', model)
            locator.register_service(f'camera_viewmodel_{i}', viewmodel)