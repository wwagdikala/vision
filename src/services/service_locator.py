# src/services/service_locator.py
class ServiceLocator:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        if ServiceLocator._instance is not None:
            raise Exception("Use get_instance()")
        self._services = {}
        
    def register_service(self, name: str, service: object):
        if name in self._services:
            raise Exception(f"Service {name} already registered self._services[{name}] = {service}")
        self._services[name] = service
        
    def get_service(self, name: str) -> object:
        if name not in self._services:
            raise Exception(f"Service {name} not found")
        return self._services[name] 
       