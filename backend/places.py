from __future__ import annotations

import asyncio
import math
import re
import time
import unicodedata
from typing import Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel

PlaceCategory = Literal["all", "cafe", "culture"]
PlaceInterest = Literal["coffee", "nature", "culture", "shopping", "photography", "fitness"]
PlaceBudget = Literal["free", "low", "flexible"]
OVERPASS_URLS = (
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
USER_AGENT = "Vadervett/0.1 (weather-aware local discovery)"
CACHE_SECONDS = 600
COMMONS_IMAGE_CACHE_SECONDS = 86_400

CATEGORY_FILTERS: dict[PlaceCategory, str] = {
    "all": 'nwr(around:{radius},{latitude},{longitude})[name][amenity~"^(cafe|library|cinema|arts_centre|marketplace|gym|sports_centre)$"];nwr(around:{radius},{latitude},{longitude})[name][tourism=museum];nwr(around:{radius},{latitude},{longitude})[name][leisure=park];',
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
    fee: bool | None
    image_url: str | None = None
    image_page_url: str | None = None
    map_url: str
    directions_url: str
    reason: str


class PlaceSearchResult(BaseModel):
    places: list[NearbyPlace]
    radius_meters: int
    available: bool = True
    message: str | None = None
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


_place_cache: dict[tuple[object, ...], tuple[float, PlaceSearchResult]] = {}
_commons_image_cache: dict[tuple[str, float, float], tuple[float, tuple[str, str] | None]] = {}


def _normalized_commons_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))


def commons_image_from_response(data: dict, place_name: str) -> tuple[str, str] | None:
    normalized_name = _normalized_commons_text(place_name)
    if normalized_name in {"park", "stadsparken", "museum", "bibliotek", "library", "cafe", "kafe"}:
        return None

    pages = data.get("query", {}).get("pages", {})
    ordered_pages = sorted(pages.values(), key=lambda page: page.get("index", 0))
    for page in ordered_pages:
        normalized_title = _normalized_commons_text(page.get("title", "").removeprefix("File:"))
        if normalized_name not in normalized_title:
            continue
        image_info = page.get("imageinfo", [])
        if not image_info:
            continue
        info = image_info[0]
        mime_type = info.get("mime", "")
        if mime_type and not mime_type.startswith("image/"):
            continue
        image_url = info.get("thumburl") or info.get("url")
        source_url = info.get("descriptionurl")
        if image_url and source_url:
            return image_url, source_url
    return None


async def _find_commons_image(client: httpx.AsyncClient, place: NearbyPlace) -> None:
    if place.image_url:
        return

    cache_key = (_normalized_commons_text(place.name), round(place.latitude, 5), round(place.longitude, 5))
    cached = _commons_image_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < COMMONS_IMAGE_CACHE_SECONDS:
        if cached[1]:
            place.image_url, place.image_page_url = cached[1]
        return

    image: tuple[str, str] | None = None
    try:
        response = await client.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": f'"{place.name}"',
                "gsrnamespace": 6,
                "gsrlimit": 8,
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "iiurlwidth": 640,
                "format": "json",
            },
        )
        response.raise_for_status()
        image = commons_image_from_response(response.json(), place.name)
    except (httpx.HTTPError, ValueError, TypeError):
        pass

    _commons_image_cache[cache_key] = (time.monotonic(), image)
    if image:
        place.image_url, place.image_page_url = image


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
    if amenity in {"gym", "sports_centre"}:
        return "Träning"
    if tags.get("leisure") == "park":
        return "Park"
    if tags.get("tourism") == "museum":
        return "Museum"
    return "Inomhusplats"


def weather_reason(category: str, wet: bool, cold: bool, windy: bool) -> str:
    if category == "Kafé":
        return "En varm paus under tak nära till hands." if wet or cold else "En fin omväg för dagens kaffepaus."
    if category in {"Museum", "Bibliotek", "Biograf", "Kultur", "Saluhall / marknad"}:
        return "Skönt tak över huvudet när vädret är ruggigt." if wet or cold or windy else "Ett inomhusalternativ nära din promenad."
    if category == "Park":
        return "Välj en kort slinga i dagsljus och kontrollera regnrisken först." if wet or cold or windy else "Ett grönt andrum nära dig när vädret tillåter."
    if category == "Träning":
        return "Ett inomhuspass när vädret gör utomhusträning mindre lockande."
    return "Ett ställe värt att upptäcka i dag."


def localize_reason(reason: str, language: Literal["sv", "en"]) -> str:
    if language == "sv":
        return reason
    translations = {
        "En varm paus under tak nära till hands.": "A warm break under cover, close by.",
        "En fin omväg för dagens kaffepaus.": "A pleasant detour for today's coffee break.",
        "Skönt tak över huvudet när vädret är ruggigt.": "A comfortable roof over your head in rough weather.",
        "Ett inomhusalternativ nära din promenad.": "An indoor option near your walk.",
        "Ett ställe värt att upptäcka i dag.": "A place worth discovering today.",
        "Välj en kort slinga i dagsljus och kontrollera regnrisken först.": "Choose a short loop in daylight and check the rain chance first.",
        "Ett grönt andrum nära dig när vädret tillåter.": "A green pause nearby when conditions allow.",
        "Ett inomhuspass när vädret gör utomhusträning mindre lockande.": "An indoor workout when the weather makes outdoor exercise less appealing.",
    }
    return translations.get(reason, reason)


def parse_elements(
    elements: list[dict],
    latitude: float,
    longitude: float,
    radius_meters: int,
    weather_code: int,
    precipitation_probability: int,
    wind_speed: float,
    feels_like: float,
    language: Literal["sv", "en"] = "sv",
    interests: list[PlaceInterest] | None = None,
    budget: PlaceBudget = "free",
) -> list[NearbyPlace]:
    ranked_places: list[tuple[int, NearbyPlace]] = []
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

        fee_tag = tags.get("fee")
        has_fee = True if fee_tag == "yes" else False if fee_tag == "no" else None
        if budget == "free" and has_fee is True:
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

        category_label = classify_place(tags)
        commons_file = tags.get("wikimedia_commons", "")
        image_url = None
        image_page_url = None
        if commons_file.startswith("File:"):
            file_name = commons_file[5:].strip().replace(" ", "_")
            encoded_file_name = quote(file_name, safe="_")
            image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{encoded_file_name}"
            image_page_url = f"https://commons.wikimedia.org/wiki/File:{encoded_file_name}"
        place = NearbyPlace(
                osm_type=place_type,
                osm_id=osm_id,
                name=name,
                category=category_label,
                latitude=place_latitude,
                longitude=place_longitude,
                distance_meters=round(distance),
                address=address or None,
                opening_hours=tags.get("opening_hours"),
                fee=has_fee,
                image_url=image_url,
                image_page_url=image_page_url,
                map_url=f"https://www.openstreetmap.org/{quote(place_type)}/{osm_id}",
                directions_url=(
                    "https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route="
                    f"{latitude}%2C{longitude}%3B{place_latitude}%2C{place_longitude}"
                ),
                reason=localize_reason(weather_reason(category_label, wet, cold, windy), language),
            )
        interest_set = set(interests or [])
        rank = 0
        if "coffee" in interest_set and category_label == "Kafé":
            rank += 4
        if "nature" in interest_set and category_label == "Park":
            rank += 4
        if "culture" in interest_set and category_label in {"Museum", "Bibliotek", "Biograf", "Kultur"}:
            rank += 4
        if "shopping" in interest_set and category_label == "Saluhall / marknad":
            rank += 4
        if "fitness" in interest_set and category_label == "Träning":
            rank += 4
        if "photography" in interest_set and category_label in {"Museum", "Park", "Kultur"}:
            rank += 2
        if budget != "flexible" and has_fee is False:
            rank += 1
        ranked_places.append((rank, place))

    ranked_places.sort(key=lambda item: (-item[0], item[1].distance_meters))
    return [place for _, place in ranked_places[:20]]


async def find_nearby_places(
    latitude: float,
    longitude: float,
    radius_meters: int,
    category: PlaceCategory,
    weather_code: int,
    precipitation_probability: int,
    wind_speed: float,
    feels_like: float,
    language: Literal["sv", "en"] = "sv",
    interests: list[PlaceInterest] | None = None,
    budget: PlaceBudget = "free",
) -> PlaceSearchResult:
    cache_key = (
        round(latitude, 4), round(longitude, 4), radius_meters, category,
        weather_code, precipitation_probability, round(wind_speed), round(feels_like), language,
        tuple(interests or ()), budget,
    )
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
    data: dict | None = None
    last_error: httpx.HTTPError | None = None
    async with httpx.AsyncClient(timeout=11, headers={"User-Agent": USER_AGENT}) as client:
        for endpoint in OVERPASS_URLS:
            try:
                response = await client.post(
                    endpoint,
                    data={"data": query},
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                break
            except httpx.HTTPError as error:
                last_error = error
    if data is None:
        if last_error:
            raise last_error
        raise httpx.ConnectError("No Overpass endpoint is available")

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
            language,
            interests,
            budget,
        ),
        radius_meters=radius_meters,
        data_timestamp=data.get("osm3s", {}).get("timestamp_osm_base"),
    )
    image_candidates = [place for place in result.places[:6] if not place.image_url]
    if image_candidates:
        async with httpx.AsyncClient(timeout=4, headers={"User-Agent": USER_AGENT}) as client:
            await asyncio.gather(*(_find_commons_image(client, place) for place in image_candidates))
    _place_cache[cache_key] = (time.monotonic(), result)
    return result


async def search_cities(query: str, language: Literal["sv", "en"] = "sv") -> list[CityResult]:
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(
            GEOCODING_URL,
            params={"name": query, "count": 8, "language": language, "format": "json", "countryCode": "SE"},
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
