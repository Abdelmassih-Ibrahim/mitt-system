from typing import Literal

from pydantic import BaseModel, Field


class AppPreferences(BaseModel):
    location_name: str = Field(default="Stockholm", min_length=1, max_length=120)
    latitude: float = Field(default=59.3293, ge=-90, le=90)
    longitude: float = Field(default=18.0686, ge=-180, le=180)
    timezone: str = Field(default="Europe/Stockholm", min_length=1, max_length=80)
    language: Literal["sv", "en"] = "sv"
    temperature_unit: Literal["celsius", "fahrenheit"] = "celsius"
    thermal_sensitivity: Literal["cold", "neutral", "warm"] = "neutral"
    preferred_mode: Literal["outdoor", "indoor", "surprise"] = "outdoor"
    walking_distance_meters: int = Field(default=1500, ge=250, le=5000)
    budget: Literal["free", "low", "flexible"] = "free"
    interests: list[Literal["coffee", "nature", "culture", "shopping", "photography", "fitness"]] = Field(
        default_factory=lambda: ["coffee", "nature", "culture"], max_length=6
    )


DEFAULT_PREFERENCES = AppPreferences()
