from __future__ import annotations

import math
import time
from typing import Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel

PlaceCategory = Literal["all", "cafe", "culture"]
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
USER_AGENT = "Vadervett/0.1 (weather-aware local discovery)"
CACHE_SECONDS = 600

CATEGORY_FILTERS: dict[PlaceCategory, str] = {
    "all": 'nwr(around:{radius},{latitude},{longitude})[name][amenity~"^(cafe|library|cinema|arts_centre|marketplace)$"];nwr(around:{radius},{latitude},{longitude})[name][tourism=museum];',
    "cafe": 'nwr(around:{radius},{latitude},{longitude})[name][amenity=cafe];',
    "culture": 'nwr(around:{radius},{latitude},{longitude})[name][amenity~"^(library|cinema|arts_centre|marketplace)$"];nwr(around:{radius},{latitude},{longitude})[name][tourism=museum];',
}


class NearbyPlace(BaseModel):
    osm_type: str
    osm_id: int
    name: str
    category: str
    latitude: float
    longitude: float
    distance_meters: int
    address: str | None
    opening_hours: str | None
    map_url: str
    directions_url: str
    reason: str


class PlaceSearchResult(BaseModel):
    places: list[NearbyPlace]
    radius_meters: int
    source: str = "OpenStreetMap contributors"
    source_url: str = "https://www.openstreetmap.org/copyright"
    data_timestamp: str | None = None


class CityResult(BaseModel):
    name: str
    admin1: str | None
    country: str
    latitude: float
    longitude: float
    timezone: str


_place_cache: dict[tuple[float, float, int, str], tuple[float, PlaceSearchResult]] = {}


def haversine_meters(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    earth_radius = 6_371_000
    latitude_delta = math.radians(latitude_b - latitude_a)
    longitude_delta = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(math.radians(latitude_a))
        * math.cos(math.radians(latitude_b))
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius * math.asin(math.sqrt(haversine))


def classify_place(tags: dict[str, str]) -> str:
    amenity = tags.get("amenity", "")
    if amenity == "cafe":
        return "Kafé"
    if amenity == "library":
        return "Bibliotek"
    if amenity == "cinema":
        return "Biograf"
    if amenity == "arts_centre" or amenity == "theatre":
        return "Kultur"
    if amenity == "marketplace":
        return "Saluhall / marknad"
    if tags.get("tourism") == "museum":
        return "Museum"
    return "Inomhusplats"


def weather_reason(category: str, wet: bool, cold: bool, windy: bool) -> str:
    if category == "Kafé":
        return "En varm paus nära till hands." if wet or cold else "En fin omväg för dagens kaffepaus."
    if category in {"Museum", "Bibliotek", "Biograf", "Kultur", "Saluhall / marknad"}:
        return "Skönt tak över huvudet när vädret är ruggigt." if wet or cold or windy else "Ett inomhusalternativ nära din promenad."
    return "Ett ställe värt att upptäcka i dag."


def parse_elements(
    elements: list[dict],
    latitude: float,
    longitude: float,
    radius_meters: int,
    weather_code: int,
    precipitation_probability: int,
    wind_speed: float,
    feels_like: float,
) -> list[NearbyPlace]:
    places: list[NearbyPlace] = []
    wet = precipitation_probability >= 40 or 51 <= weather_code <= 82 or weather_code >= 95
    cold = feels_like <= 5
    windy = wind_speed >= 30

    for element in elements:
        tags = element.get("tags", {})
        name = tags.get("name")
        location = element if "lat" in element and "lon" in element else element.get("center", {})
        place_latitude = location.get("lat")
        place_longitude = location.get("lon")
        if not name or place_latitude is None or place_longitude is None:
            continue

        distance = haversine_meters(latitude, longitude, place_latitude, place_longitude)
        if distance > radius_meters:
            continue

        address_parts = [tags.get("addr:street"), tags.get("addr:housenumber")]
        city = tags.get("addr:city")
        address = " ".join(part for part in address_parts if part)
        if city:
            address = f"{address}, {city}" if address else city

        place_type = element.get("type", "node")
        osm_id = element.get("id")
        if not isinstance(osm_id, int):
            continue

        places.append(
            NearbyPlace(
                osm_type=place_type,
                osm_id=osm_id,
                name=name,
                category=classify_place(tags),
                latitude=place_latitude,
                longitude=place_longitude,
                distance_meters=round(distance),
                address=address or None,
                opening_hours=tags.get("opening_hours"),
                map_url=f"https://www.openstreetmap.org/{quote(place_type)}/{osm_id}",
                directions_url=(
                    "https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route="
                    f"{latitude}%2C{longitude}%3B{place_latitude}%2C{place_longitude}"
                ),
                reason=weather_reason(classify_place(tags), wet, cold, windy),
            )
        )

    return sorted(places, key=lambda place: place.distance_meters)[:20]


async def find_nearby_places(
    latitude: float,
    longitude: float,
    radius_meters: int,
    category: PlaceCategory,
    weather_code: int,
    precipitation_probability: int,
    wind_speed: float,
    feels_like: float,
) -> PlaceSearchResult:
    cache_key = (round(latitude, 4), round(longitude, 4), radius_meters, category)
    cached = _place_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    query = (
        "[out:json][timeout:15];("
        + CATEGORY_FILTERS[category].format(
            radius=radius_meters, latitude=latitude, longitude=longitude
        )
        + ");out center tags;"
    )
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

    result = PlaceSearchResult(
        places=parse_elements(
            data.get("elements", []),
            latitude,
            longitude,
            radius_meters,
            weather_code,
            precipitation_probability,
            wind_speed,
            feels_like,
        ),
        radius_meters=radius_meters,
        data_timestamp=data.get("osm3s", {}).get("timestamp_osm_base"),
    )
    _place_cache[cache_key] = (time.monotonic(), result)
    return result


async def search_cities(query: str) -> list[CityResult]:
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(
            GEOCODING_URL,
            params={"name": query, "count": 8, "language": "sv", "format": "json", "countryCode": "SE"},
        )
        response.raise_for_status()
        data = response.json()

    return [
        CityResult(
            name=item["name"],
            admin1=item.get("admin1"),
            country=item.get("country", "Sverige"),
            latitude=item["latitude"],
            longitude=item["longitude"],
            timezone=item.get("timezone", "Europe/Stockholm"),
        )
        for item in data.get("results", [])
        if "latitude" in item and "longitude" in item and "name" in item
    ]
