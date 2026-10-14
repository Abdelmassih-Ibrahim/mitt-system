from __future__ import annotations

import asyncio
import logging
import math
import os
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
GEOAPIFY_URL = "https://api.geoapify.com/v2/places"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
USER_AGENT = "Vadervett/0.1 (weather-aware local discovery)"
CACHE_SECONDS = 600
STALE_CACHE_SECONDS = 3600
PLACE_CACHE_MAX_ENTRIES = 256
CITY_CACHE_SECONDS = 300
CITY_STALE_SECONDS = 3600
CITY_CACHE_MAX_ENTRIES = 128
COMMONS_IMAGE_CACHE_SECONDS = 86_400
logger = logging.getLogger(__name__)

CATEGORY_FILTERS: dict[PlaceCategory, str] = {
    "all": 'nwr(around:{radius},{latitude},{longitude})[name][amenity~"^(cafe|library|cinema|arts_centre|marketplace|gym|sports_centre)$"];nwr(around:{radius},{latitude},{longitude})[name][tourism=museum];nwr(around:{radius},{latitude},{longitude})[name][leisure=park];',
    "cafe": 'nwr(around:{radius},{latitude},{longitude})[name][amenity=cafe];',
    "culture": 'nwr(around:{radius},{latitude},{longitude})[name][amenity~"^(library|cinema|arts_centre|marketplace)$"];nwr(around:{radius},{latitude},{longitude})[name][tourism=museum];',
}
GEOAPIFY_CATEGORIES: dict[PlaceCategory, tuple[str, ...]] = {
    "all": (
        "catering.cafe", "education.library", "entertainment.cinema",
        "entertainment.culture", "entertainment.museum", "leisure.park",
        "commercial.marketplace", "sport.fitness", "sport.sports_centre",
    ),
    "cafe": ("catering.cafe",),
    "culture": (
        "education.library", "entertainment.cinema", "entertainment.culture",
        "entertainment.museum", "commercial.marketplace",
    ),
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
    provider: Literal["overpass", "geoapify"] = "overpass"
    provider_url: str | None = None
    data_timestamp: str | None = None


class CityResult(BaseModel):
    name: str
    admin1: str | None
    country: str
    latitude: float
    longitude: float
    timezone: str


_place_cache: dict[tuple[object, ...], tuple[float, dict]] = {}
_place_inflight: dict[tuple[object, ...], asyncio.Task[dict]] = {}
_city_cache: dict[tuple[str, str], tuple[float, list[CityResult]]] = {}
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
    cache_key = (round(latitude, 5), round(longitude, 5), radius_meters, category, language)
    cached = _place_cache.get(cache_key)
    data = cached[1] if cached and time.monotonic() - cached[0] < CACHE_SECONDS else None

    query = (
        "[out:json][timeout:15];("
        + CATEGORY_FILTERS[category].format(
            radius=radius_meters, latitude=latitude, longitude=longitude
        )
        + ");out center tags;"
    )
    if data is None:
        task = _place_inflight.get(cache_key)
        if task is None:
            task = asyncio.create_task(
                _request_place_data(query, latitude, longitude, radius_meters, category, language)
            )
            _place_inflight[cache_key] = task
        try:
            data = await asyncio.shield(task)
            _place_cache.pop(cache_key, None)
            _place_cache[cache_key] = (time.monotonic(), data)
            while len(_place_cache) > PLACE_CACHE_MAX_ENTRIES:
                _place_cache.pop(next(iter(_place_cache)))
        except httpx.HTTPError:
            stale = _place_cache.get(cache_key)
            if stale and time.monotonic() - stale[0] < STALE_CACHE_SECONDS:
                data = stale[1]
            else:
                raise
        finally:
            if task.done() and _place_inflight.get(cache_key) is task:
                _place_inflight.pop(cache_key, None)

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
        provider=data.get("provider", "overpass"),
        provider_url="https://www.geoapify.com/" if data.get("provider") == "geoapify" else None,
        data_timestamp=data.get("osm3s", {}).get("timestamp_osm_base"),
    )
    return result


async def _request_place_data(
    query: str,
    latitude: float,
    longitude: float,
    radius_meters: int,
    category: PlaceCategory,
    language: Literal["sv", "en"],
) -> dict:
    api_key = os.environ.get("GEOAPIFY_API_KEY", "").strip()
    if api_key:
        try:
            return await _request_geoapify_data(
                latitude, longitude, radius_meters, category, language, api_key
            )
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                logger.error("Geoapify rejected GEOAPIFY_API_KEY with HTTP %s", error.response.status_code)
                raise
            logger.warning("Geoapify request failed; trying Overpass: %s", error)
        except (httpx.HTTPError, ValueError, TypeError) as error:
            logger.warning("Geoapify request failed; trying Overpass: %s", error)
    return await _request_overpass_data(query)


async def _request_geoapify_data(
    latitude: float,
    longitude: float,
    radius_meters: int,
    category: PlaceCategory,
    language: Literal["sv", "en"],
    api_key: str,
) -> dict:
    params = {
        "categories": ",".join(GEOAPIFY_CATEGORIES[category]),
        "filter": f"circle:{longitude},{latitude},{radius_meters}",
        "bias": f"proximity:{longitude},{latitude}",
        "limit": 20,
        "lang": language,
        "apiKey": api_key,
    }
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(5, connect=2), headers={"User-Agent": USER_AGENT}
    ) as client:
        response = await client.get(GEOAPIFY_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    return {
        "elements": _geoapify_features_to_osm_elements(payload.get("features", [])),
        "provider": "geoapify",
    }


def _geoapify_features_to_osm_elements(features: list[dict]) -> list[dict]:
    osm_type_names = {"n": "node", "w": "way", "r": "relation"}
    elements: list[dict] = []
    for feature in features:
        properties = feature.get("properties", {})
        raw = properties.get("datasource", {}).get("raw", {})
        osm_id = raw.get("osm_id")
        osm_type = osm_type_names.get(raw.get("osm_type"))
        name = properties.get("name") or raw.get("name")
        geometry = feature.get("geometry", {}).get("coordinates", [])
        longitude = properties.get("lon", geometry[0] if len(geometry) >= 2 else None)
        latitude = properties.get("lat", geometry[1] if len(geometry) >= 2 else None)
        if not isinstance(osm_id, int) or osm_type is None or not name or latitude is None or longitude is None:
            continue

        tags = {
            key: value
            for key, value in raw.items()
            if key not in {"lat", "lon", "osm_id", "osm_type"} and isinstance(value, str)
        }
        tags["name"] = name
        for source_key, target_key in (
            ("street", "addr:street"),
            ("housenumber", "addr:housenumber"),
            ("city", "addr:city"),
        ):
            if properties.get(source_key):
                tags.setdefault(target_key, properties[source_key])

        elements.append({
            "type": osm_type,
            "id": osm_id,
            "lat": latitude,
            "lon": longitude,
            "tags": tags,
        })
    return elements


async def _request_overpass_data(query: str) -> dict:
    last_error: httpx.HTTPError | None = None
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(4, connect=1.5), headers={"User-Agent": USER_AGENT}
    ) as client:
        for endpoint in OVERPASS_URLS:
            try:
                response = await client.post(
                    endpoint,
                    data={"data": query},
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                data["provider"] = "overpass"
                return data
            except httpx.HTTPError as error:
                last_error = error
                logger.warning(
                    "Overpass request to %s failed (%s): %s",
                    endpoint,
                    type(error).__name__,
                    error,
                )
    if last_error:
        raise last_error
    raise httpx.ConnectError("No Overpass endpoint is available")


async def search_cities(query: str, language: Literal["sv", "en"] = "sv") -> list[CityResult]:
    cache_key = (" ".join(query.casefold().split()), language)
    cached = _city_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < CITY_CACHE_SECONDS:
        return cached[1]

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5, connect=2), headers={"User-Agent": USER_AGENT}
        ) as client:
            response = await client.get(
                GEOCODING_URL,
                params={"name": query, "count": 8, "language": language, "format": "json", "countryCode": "SE"},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        stale = _city_cache.get(cache_key)
        if stale and time.monotonic() - stale[0] < CITY_STALE_SECONDS:
            return stale[1]
        raise

    results = [
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
    _city_cache.pop(cache_key, None)
    _city_cache[cache_key] = (time.monotonic(), results)
    while len(_city_cache) > CITY_CACHE_MAX_ENTRIES:
        _city_cache.pop(next(iter(_city_cache)))
    return results
