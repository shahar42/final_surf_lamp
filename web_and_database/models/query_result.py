"""
Query Result Wrapper - Encapsulates database query results as single reference object.
Reduces parameter passing overhead and improves code maintainability.
"""

from dataclasses import dataclass
from data_base import Arduino, Location, User
from config import STALE_DATA_THRESHOLD


@dataclass
class ArduinoQueryResult:
    """
    Encapsulates Arduino database query results.

    Instead of unpacking and passing (arduino, location, user) separately,
    pass this single object through function calls.
    """
    arduino: Arduino
    location: Location
    user: User

    def __post_init__(self):
        if not self.arduino:
            raise ValueError("Arduino object is required")
        if not self.location:
            raise ValueError("Location object is required")
        if not self.user:
            raise ValueError("User object is required")

    @property
    def arduino_id(self) -> int:
        return self.arduino.arduino_id

    @property
    def user_location(self) -> str:
        return self.user.location

    @property
    def wave_height_m(self) -> float:
        return self.location.wave_height_m or 0.0

    @property
    def wave_period_s(self) -> float:
        return self.location.wave_period_s or 0.0

    @property
    def wind_speed_mps(self) -> float:
        return self.location.wind_speed_mps or 0.0

    @property
    def wind_direction_deg(self) -> int:
        return self.location.wind_direction_deg or 0

    @property
    def is_stale(self) -> bool:
        consecutive = getattr(self.location, 'consecutive_identical_updates', 0) or 0
        return consecutive > STALE_DATA_THRESHOLD

    def __repr__(self) -> str:
        return f"ArduinoQueryResult(arduino_id={self.arduino_id}, location={self.user_location})"
