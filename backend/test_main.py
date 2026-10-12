from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import (
    app,
    build_dj,
    build_plan,
    build_quest,
    build_payload,
    calculate_survival,
    describe_weather,
    CurrentConditions,
)
from backend.places import parse_elements
from backend.preferences import AppPreferences


class WeatherLogicTests(unittest.TestCase):
    def test_weather_code_maps_to_rain_mood(self) -> None:
        mood = describe_weather(63, True)
        self.assertEqual(mood.label, "Regn")
        self.assertEqual(mood.mood, "rain")

    def test_weather_code_maps_clear_night(self) -> None:
        mood = describe_weather(0, False)
        self.assertEqual(mood.label, "Klart i natt")
        self.assertEqual(mood.mood, "night")

    def test_comfortable_weather_has_higher_survival_score(self) -> None:
        rough_weather = CurrentConditions(
            temperature=-2,
            feels_like=-9,
            humidity=95,
            precipitation=4,
            code=63,
            wind_speed=46,
            wind_direction=190,
            is_day=False,
        )
        mild_weather = CurrentConditions(
            temperature=18,
            feels_like=18,
            humidity=45,
            precipitation=0,
            code=1,
            wind_speed=7,
            wind_direction=180,
            is_day=True,
        )
        rough_score = calculate_survival(rough_weather).score
        mild_score = calculate_survival(mild_weather).score
        self.assertGreater(mild_score, rough_score)
        self.assertGreaterEqual(rough_score, 0)
        self.assertLessEqual(mild_score, 100)

    def test_payload_includes_only_upcoming_local_hours(self) -> None:
        data = {
            "timezone": "Europe/Stockholm",
            "current": {
                "time": "2026-10-12T14:30",
                "temperature_2m": 9,
                "apparent_temperature": 6,
                "relative_humidity_2m": 80,
                "precipitation": 0.1,
                "weather_code": 51,
                "wind_speed_10m": 18,
                "wind_direction_10m": 210,
                "is_day": 1,
            },
            "hourly": {
                "time": [
                    "2026-10-12T14:00",
                    "2026-10-12T15:00",
                    "2026-10-12T16:00",
                    "2026-10-13T09:00",
                    "2026-10-13T10:00",
                ],
                "temperature_2m": [9, 8, 7, 12, 13],
                "apparent_temperature": [6, 5, 4, 11, 12],
                "precipitation_probability": [80, 45, 10, 0, 0],
                "weather_code": [51, 3, 1, 0, 0],
                "wind_speed_10m": [18, 14, 8, 8, 7],
                "is_day": [1, 1, 1, 1, 1],
            },
            "daily": {
                "time": ["2026-10-12"],
                "sunrise": ["2026-10-12T07:30"],
                "sunset": ["2026-10-12T17:49"],
            },
        }

        payload = build_payload(data, "Stockholm", "outdoor")

        self.assertEqual(
            [(hour.date, hour.time) for hour in payload.hourly],
            [
                ("2026-10-12", "15:00"),
                ("2026-10-12", "16:00"),
                ("2026-10-13", "09:00"),
                ("2026-10-13", "10:00"),
            ],
        )
        self.assertEqual(payload.hourly[0].precipitation_probability, 45)
        self.assertEqual(payload.sunrise, "07:30")
        self.assertTrue(payload.outdoor_window.available)
        self.assertEqual(payload.outdoor_window.start, "16:00")
        self.assertEqual(payload.outdoor_window.end, "17:00")

    def test_plan_mode_changes_activity(self) -> None:
        current = CurrentConditions(
            temperature=7,
            feels_like=4,
            humidity=90,
            precipitation=0.4,
            code=61,
            wind_speed=22,
            wind_direction=220,
            is_day=True,
        )
        outdoor = build_plan(current, "outdoor")
        indoor = build_plan(current, "indoor")
        self.assertNotEqual(outdoor.activity_title, indoor.activity_title)
        self.assertIn("inomhus", indoor.activity_title.lower())

    def test_quest_is_stable_for_same_weather_and_date(self) -> None:
        current = CurrentConditions(
            temperature=8,
            feels_like=6,
            humidity=65,
            precipitation=0,
            code=2,
            wind_speed=9,
            wind_direction=270,
            is_day=True,
        )
        first = build_quest(current, "outdoor", "2026-10-12")
        second = build_quest(current, "outdoor", "2026-10-12")
        self.assertEqual(first, second)

    def test_weather_dj_reflects_rain(self) -> None:
        current = CurrentConditions(
            temperature=9,
            feels_like=6,
            humidity=90,
            precipitation=0.1,
            code=53,
            wind_speed=18,
            wind_direction=10,
            is_day=True,
        )
        dj = build_dj(current)
        self.assertEqual(dj.genre, "Lo-fi jazz")
        self.assertIn("regn", dj.soundscape.lower())

    def test_nearby_places_use_real_osm_tags_and_drop_missing_names(self) -> None:
        places = parse_elements(
            [
                {
                    "type": "node",
                    "id": 456,
                    "lat": 59.3300,
                    "lon": 18.0686,
                    "tags": {
                        "name": "Kvarterskaféet",
                        "amenity": "cafe",
                        "addr:street": "Exempelgatan",
                        "addr:housenumber": "4",
                        "opening_hours": "Mo-Fr 08:00-18:00",
                    },
                },
                {"type": "node", "id": 789, "lat": 59.3294, "lon": 18.0686, "tags": {"amenity": "cafe"}},
                {"type": "node", "id": 999, "lat": 59.5, "lon": 18.0686, "tags": {"name": "Too far", "amenity": "cafe"}},
            ],
            59.3293,
            18.0686,
            1000,
            63,
            80,
            30,
            4,
        )
        self.assertEqual(len(places), 1)
        self.assertEqual(places[0].name, "Kvarterskaféet")
        self.assertEqual(places[0].category, "Kafé")
        self.assertEqual(places[0].address, "Exempelgatan 4")
        self.assertEqual(places[0].opening_hours, "Mo-Fr 08:00-18:00")
        self.assertIn("openstreetmap.org/directions", places[0].directions_url)
        self.assertIn("tak", places[0].reason)


class CapsuleApiTests(unittest.TestCase):
    def test_preferences_are_saved_and_returned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "preferences.sqlite3"
            with patch("backend.main.DATABASE_PATH", database):
                with TestClient(app) as client:
                    defaults = client.get("/api/preferences")
                    self.assertEqual(defaults.status_code, 200)
                    self.assertEqual(defaults.json()["language"], "sv")

                    saved = client.put(
                        "/api/preferences",
                        json={
                            "language": "en",
                            "temperature_unit": "fahrenheit",
                            "thermal_sensitivity": "cold",
                            "preferred_mode": "indoor",
                            "walking_distance_meters": 900,
                            "budget": "low",
                            "interests": ["coffee", "culture"],
                        },
                    )
                    self.assertEqual(saved.status_code, 200)
                    self.assertEqual(client.get("/api/preferences").json(), saved.json())

                    invalid = client.put(
                        "/api/preferences",
                        json={"language": "xx", "walking_distance_meters": 9000},
                    )
                    self.assertEqual(invalid.status_code, 422)

    def test_capsules_can_be_saved_listed_and_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "capsules.sqlite3"
            with patch("backend.main.DATABASE_PATH", database):
                with TestClient(app) as client:
                    saved = client.post(
                        "/api/capsules",
                        json={
                            "city": "Stockholm",
                            "temperature": 9,
                            "condition": "Regn",
                            "quest": "Hitta stadens bästa skydd",
                            "note": "Första regndagen",
                        },
                    )
                    self.assertEqual(saved.status_code, 201)
                    capsule = saved.json()
                    self.assertEqual(capsule["city"], "Stockholm")

                    listed = client.get("/api/capsules")
                    self.assertEqual(listed.status_code, 200)
                    self.assertEqual(len(listed.json()), 1)
                    self.assertEqual(listed.json()[0]["note"], "Första regndagen")

                    deleted = client.delete(f"/api/capsules/{capsule['id']}")
                    self.assertEqual(deleted.status_code, 204)
                    self.assertEqual(client.get("/api/capsules").json(), [])


if __name__ == "__main__":
    unittest.main()
