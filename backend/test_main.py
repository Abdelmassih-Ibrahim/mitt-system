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
    calculate_survival,
    describe_weather,
    CurrentConditions,
)


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


class CapsuleApiTests(unittest.TestCase):
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
