from enum import Enum


class CalibrationTarget(Enum):
    CUBE = "cube"
    CHECKERBOARD = "checkerboard"

    @classmethod
    def list(cls) -> list:
        return [member.value for member in cls]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.list()


class CameraSetup(Enum):
    STEREO_3 = "stereo_3"
    STEREO_2 = "stereo_2"

    @classmethod
    def list(cls) -> list:
        return [member.value for member in cls]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.list()

    @classmethod
    def get_num_cameras(cls, setup: str) -> int:
        if setup == cls.STEREO_3.value:
            return 3
        elif setup == cls.STEREO_2.value:
            return 2
        else:
            return 3  # Default to stereo_3 if invalid setup
