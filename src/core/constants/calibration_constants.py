from enum import Enum


class CalibrationSettings(Enum):
    REQUIRED_ANGLES = "required_angles"
    SQUARE_SIZE = "square_size"
    MIN_QUALITY_SCORE = "min_quality_score"
    MIN_COVERAGE = "min_coverage"
    PATTERN_ROWS = "pattern_rows"
    PATTERN_COLS = "pattern_cols"

    @classmethod
    def get_default(cls) -> dict:
        return {
            cls.REQUIRED_ANGLES.value: 1,
            cls.SQUARE_SIZE.value: 25.0,
            cls.MIN_QUALITY_SCORE.value: 0.25,
            cls.MIN_COVERAGE.value: 0.25,
            cls.PATTERN_ROWS.value: 6,
            cls.PATTERN_COLS.value: 9,
        }


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
    STEREO_4 = "stereo_4"

    @classmethod
    def list(cls) -> list:
        return [member.value for member in cls]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.list()

    @classmethod
    def get_num_cameras(cls, setup: str) -> int:
        return 3 if setup == cls.STEREO_3.value else 2
