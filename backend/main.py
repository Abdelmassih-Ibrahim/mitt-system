from __future__ import annotations

import os
import random
import sqlite3
import json
from uuid import UUID
from contextlib import asynccontextmanager, closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.places import PlaceBudget, PlaceCategory, PlaceInterest, PlaceSearchResult, find_nearby_places, search_cities
from backend.preferences import AppPreferences, DEFAULT_PREFERENCES
from backend.localization import translate_payload

WeatherMode = Literal["outdoor", "indoor", "surprise"]

DATABASE_PATH = Path(
    os.environ.get("WEATHER_DATABASE_PATH", Path(__file__).with_name("weather_capsules.sqlite3"))
)
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_FIELDS = ",".join(
    (
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "precipitation",
        "weather_code",
        "wind_speed_10m",
        "wind_direction_10m",
        "is_day",
    )
)
HOURLY_FIELDS = ",".join(
    (
        "temperature_2m",
        "apparent_temperature",
        "precipitation_probability",
        "weather_code",
        "wind_speed_10m",
        "wind_direction_10m",
        "is_day",
    )
)


class CurrentConditions(BaseModel):
    temperature: float
    feels_like: float
    humidity: int
    precipitation: float
    code: int
    wind_speed: float
    wind_direction: int
    is_day: bool


class WeatherMood(BaseModel):
    label: str
    icon: str
    mood: str


class ForecastHour(BaseModel):
    date: str
    time: str
    temperature: float
    feels_like: float | None
    precipitation_probability: int | None
    wind_speed: float | None
    wind_direction: int | None
    weather: WeatherMood
    is_day: bool


class OutdoorWindow(BaseModel):
    available: bool
    date: str | None
    start: str | None
    end: str | None
    explanation: str


class ScoreFactor(BaseModel):
    label: str
    deduction: int
    explanation: str


class SurvivalIndex(BaseModel):
    score: int
    level: str
    summary: str
    factors: list[ScoreFactor]
    disclaimer: str


class DayPlan(BaseModel):
    outfit_title: str
    outfit_text: str
    activity_title: str
    activity_text: str
    cafe_text: str
    tip: str


class Quest(BaseModel):
    title: str
    description: str
    reward: str


class WeatherDJ(BaseModel):
    genre: str
    mood: str
    soundscape: str
    reason: str


class WeatherPayload(BaseModel):
    city: str
    timezone: str
    date: str
    sunrise: str | None
    sunset: str | None
    temperature_min: float | None
    temperature_max: float | None
    refreshed_at: str
    headline: str
    current: CurrentConditions
    weather: WeatherMood
    survival: SurvivalIndex
    plan: DayPlan
    quest: Quest
    plans: dict[str, DayPlan]
    quests: dict[str, Quest]
    dj: WeatherDJ
    hourly: list[ForecastHour]
    outdoor_window: OutdoorWindow


class CapsuleCreate(BaseModel):
    city: str = Field(min_length=1, max_length=120)
    temperature: float
    condition: str = Field(min_length=1, max_length=120)
    quest: str = Field(min_length=1, max_length=200)
    note: str = Field(default="", max_length=280)


class Capsule(CapsuleCreate):
    id: int
    saved_at: str


WEATHER_CODES: dict[int, tuple[str, str, str]] = {
    0: ("Klart och soligt", "☀️", "clear"),
    1: ("Mestadels klart", "🌤️", "clear"),
    2: ("Växlande molnighet", "⛅", "cloud"),
    3: ("Mulet", "☁️", "cloud"),
    45: ("Dimma", "🌫️", "cloud"),
    48: ("Dimma med frost", "🌫️", "snow"),
    51: ("Lätt duggregn", "🌦️", "rain"),
    53: ("Duggregn och regn", "🌧️", "rain"),
    55: ("Tätt duggregn", "🌧️", "rain"),
    56: ("Underkylt duggregn", "🌧️", "snow"),
    57: ("Kraftigt underkylt duggregn", "🌧️", "snow"),
    61: ("Lätt regn", "🌦️", "rain"),
    63: ("Regn", "🌧️", "rain"),
    65: ("Kraftigt regn", "🌧️", "rain"),
    66: ("Underkylt regn", "🌧️", "snow"),
    67: ("Kraftigt underkylt regn", "🌧️", "snow"),
    71: ("Lätt snöfall", "🌨️", "snow"),
    73: ("Snöfall", "🌨️", "snow"),
    75: ("Kraftigt snöfall", "❄️", "snow"),
    77: ("Snökorn", "❄️", "snow"),
    80: ("Regnskurar", "🌦️", "rain"),
    81: ("Regnskurar", "🌧️", "rain"),
    82: ("Kraftiga regnskurar", "🌧️", "rain"),
    85: ("Snöbyar", "🌨️", "snow"),
    86: ("Kraftiga snöbyar", "❄️", "snow"),
    95: ("Åska", "⛈️", "storm"),
    96: ("Åska och hagel", "⛈️", "storm"),
    99: ("Kraftig åska och hagel", "⛈️", "storm"),
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Vädervett API",
    description="Väderstyrda planer och sparade väderkapslar.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Client-ID"],
)


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE_PATH)) as connection, connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS capsules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL DEFAULT 'legacy',
                city TEXT NOT NULL,
                temperature REAL NOT NULL,
                condition TEXT NOT NULL,
                quest TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                saved_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS app_preferences (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS user_preferences (client_id TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        capsule_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(capsules)").fetchall()
        }
        if "client_id" not in capsule_columns:
            connection.execute("ALTER TABLE capsules ADD COLUMN client_id TEXT NOT NULL DEFAULT 'legacy'")


def describe_weather(code: int, is_day: bool) -> WeatherMood:
    label, icon, mood = WEATHER_CODES.get(code, ("Väder på väg", "🌥️", "cloud"))
    if not is_day and mood == "clear":
        return WeatherMood(label="Klart i natt", icon="🌙", mood="night")
    if not is_day and mood == "cloud":
        return WeatherMood(label="Molnig kväll", icon="☁️", mood="night-cloud")
    return WeatherMood(label=label, icon=icon, mood=mood)


def calculate_survival(current: CurrentConditions) -> SurvivalIndex:
    factors: list[ScoreFactor] = []

    def add_factor(label: str, deduction: int, explanation: str) -> None:
        if deduction:
            factors.append(ScoreFactor(label=label, deduction=deduction, explanation=explanation))

    if current.feels_like <= -15:
        add_factor("Kyla", 45, f"Det känns som {round(current.feels_like)}°.")
    elif current.feels_like <= -5:
        add_factor("Kyla", 34, f"Det känns som {round(current.feels_like)}°.")
    elif current.feels_like <= 2:
        add_factor("Kyla", 24, f"Det känns som {round(current.feels_like)}°.")
    elif current.feels_like <= 7:
        add_factor("Kyla", 14, f"Det känns som {round(current.feels_like)}°.")
    elif current.feels_like <= 12:
        add_factor("Kyla", 6, f"Det känns som {round(current.feels_like)}°.")

    if current.wind_speed >= 60:
        add_factor("Vind", 32, f"Vinden ligger på {round(current.wind_speed)} km/h.")
    elif current.wind_speed >= 40:
        add_factor("Vind", 24, f"Vinden ligger på {round(current.wind_speed)} km/h.")
    elif current.wind_speed >= 25:
        add_factor("Vind", 14, f"Vinden ligger på {round(current.wind_speed)} km/h.")
    elif current.wind_speed >= 15:
        add_factor("Vind", 7, f"Vinden ligger på {round(current.wind_speed)} km/h.")

    if current.precipitation >= 5:
        add_factor("Nederbörd", 27, f"{current.precipitation:.1f} mm nederbörd nyligen.")
    elif current.precipitation >= 1:
        add_factor("Nederbörd", 20, f"{current.precipitation:.1f} mm nederbörd nyligen.")
    elif current.precipitation > 0:
        add_factor("Nederbörd", 11, f"{current.precipitation:.1f} mm nederbörd nyligen.")

    if current.code >= 95:
        add_factor("Åska", 25, "Åska gör utomhusplaner olämpliga.")
    if current.code in (45, 48):
        add_factor("Sikt", 8, "Dimma försämrar sikten.")

    score = max(0, 100 - sum(factor.deduction for factor in factors))
    if score >= 85:
        level, summary = "Väderbonus", "Härligt ute. Ta vara på ljuset."
    elif score >= 65:
        level, summary = "Ganska fint", "En lätt jacka räcker för många."
    elif score >= 40:
        level, summary = "Jacka och plan", "Kolla vinden och välj ett bra lager."
    else:
        level, summary = "Inomhus är rimligt", "Välj utefönstret noga eller gör det mysigt inne."

    return SurvivalIndex(
        score=score,
        level=level,
        summary=summary,
        factors=factors,
        disclaimer="Vädervetts uppskattning av utomhuskomfort, inte ett officiellt meteorologiskt mått.",
    )


def build_plan(
    current: CurrentConditions,
    mode: WeatherMode,
    thermal_sensitivity: Literal["cold", "neutral", "warm"] = "neutral",
) -> DayPlan:
    wet = current.precipitation > 0 or 51 <= current.code <= 82 or current.code >= 95
    cold_threshold = {"cold": 10, "neutral": 5, "warm": 1}[thermal_sensitivity]
    cold = current.feels_like <= cold_threshold
    windy = current.wind_speed >= 30

    if mode == "indoor":
        activity_title = "Gör inomhuset till äventyret."
        activity_text = "Välj ett växthus, litet galleri eller ett kafé du aldrig provat. Dagen behöver inte vara solig för att bli ny."
    elif mode == "surprise":
        activity_title = "Ta en omväg du inte planerat."
        activity_text = "Välj nästa gata genom att singla slant. Stanna vid första stället som ser varmt, märkligt eller oväntat ut."
    elif wet:
        activity_title = "Gör museet till utflykten."
        activity_text = "Välj en utställning eller ett växthus och låt skuren dra förbi innan du går vidare."
    elif windy:
        activity_title = "Hitta lä bakom husen."
        activity_text = "En skogsdunge eller en gata med lä gör promenaden mycket trevligare när vinden tar i."
    else:
        activity_title = "Ta omvägen genom parken."
        activity_text = "En kort promenad före eftermiddagskaffet kan vara dagens bästa paus."

    if wet:
        outfit_title = "Vattentätt före allt annat."
        outfit_text = "Välj jacka med huva och skor som tål väta. Byt paraply mot en ledig hand om det blåser."
        tip = "Huva slår paraply i blåst"
        cafe_text = "Sök skydd på ett kvarterskafé. Beställ något varmt och låt skuren passera."
    elif cold:
        outfit_title = "Lager på lager vinner."
        outfit_text = "En varm tröja under skaljackan gör promenaden skönare. Ta gärna mössa om vinden tar i."
        tip = "Ett extra lager skadar aldrig"
        cafe_text = "Hitta ett kafé med fönsterplats och se vädret sköta underhållningen."
    else:
        outfit_title = "Klä dig för en lång dag ute."
        outfit_text = "Ta med ett extra lager så kan du stanna ute även när temperaturen skiftar."
        tip = "Lätt lager · stor frihet"
        cafe_text = "Hitta ett kafé med fönsterplats och se vädret sköta underhållningen."

    if mode == "indoor":
        activity_title = "En liten inomhusvärld att upptäcka."
        activity_text = "Välj ett museum, växthus eller en bio med matiné. Ta en helt vanlig tisdag och gör den till en liten utflykt."

    return DayPlan(
        outfit_title=outfit_title,
        outfit_text=outfit_text,
        activity_title=activity_title,
        activity_text=activity_text,
        cafe_text=cafe_text,
        tip=tip,
    )


def build_quest(current: CurrentConditions, mode: WeatherMode, date: str) -> Quest:
    options: dict[str, list[Quest]] = {
        "rain": [
            Quest(title="Jakten på stadens bästa skydd", description="Hitta en plats med tak där du kan höra regnet utan att bli blöt.", reward="+1 regnresistent"),
            Quest(title="Fem droppar från torrskodd", description="Ta dig till ett varmt ställe med så få paraplyöppningar som möjligt.", reward="+1 paraplydiplomat"),
        ],
        "snow": [
            Quest(title="Första fotspåret", description="Hitta den tystaste snön i närmaste park och lämna dagens första spår.", reward="+1 vinterpoäng"),
            Quest(title="Varm dryck-radar", description="Promenera till närmaste ställe som serverar något rykande varmt.", reward="+1 frostskydd"),
        ],
        "clear": [
            Quest(title="Följ ljusstrimman", description="Hitta en solfläck du aldrig lagt märke till och stanna där i fem minuter.", reward="+1 solladdning"),
            Quest(title="Hem via omvägen", description="Ta tre nya gator på vägen hem och välj den finaste fasaden.", reward="+1 upptäckare"),
        ],
        "storm": [
            Quest(title="Stormspanaren", description="Betrakta vädret från en trygg plats och fånga dess mest dramatiska ljud.", reward="+1 vädermod"),
        ],
        "cloud": [
            Quest(title="Färgspaning", description="Hitta tre små färgklickar i en grå dag: en dörr, en mössa eller en skylt.", reward="+1 detaljseende"),
            Quest(title="Kvartersdetektiven", description="Upptäck en butik eller ett kafé på din gata som du aldrig lagt märke till.", reward="+1 lokalpoäng"),
        ],
        "night": [
            Quest(title="Skymningssamlaren", description="Hitta den finaste upplysta platsen i kvarteret innan du går hem.", reward="+1 kvällsljus"),
        ],
    }
    mood = describe_weather(current.code, current.is_day).mood
    pool = options.get(mood, options["cloud"])
    if mode == "indoor":
        pool = [
            Quest(title="En dörr du aldrig öppnat", description="Gå in på ett litet galleri, bokcafé eller växthus du annars hade gått förbi.", reward="+1 inomhusäventyrare"),
            Quest(title="Tre sidor på ett nytt ställe", description="Ta med en bok till ett kafé du aldrig besökt och läs tills regnet byter takt.", reward="+1 vardagsflykt"),
        ]
    elif mode == "surprise":
        pool = [
            Quest(title="Slantsinglarens rutt", description="Kasta ett mynt vid varje vägskäl: krona vänster, klave höger. Stanna efter fyra kast.", reward="+1 spontanitet"),
            Quest(title="Välj med öronen", description="Gå mot det mest intressanta ljudet du hör och se var det leder.", reward="+1 nyfikenhet"),
        ]

    rng = random.Random(f"{date}:{current.code}:{mode}")
    return rng.choice(pool)


def build_dj(current: CurrentConditions) -> WeatherDJ:
    if current.code >= 95:
        return WeatherDJ(genre="Cinematic ambient", mood="Dramatiskt lugn", soundscape="Avlägset muller och långsamma syntmattor", reason="Låt ovädret vara soundtrack, men lyssna inomhus.")
    if current.code >= 71 and current.code <= 86:
        return WeatherDJ(genre="Nordisk ambient", mood="Mjukt och frostigt", soundscape="Dämpat piano, snöknarr och varm bas", reason="Ett långsamt tempo passar en kall dag.")
    if current.precipitation > 0 or 51 <= current.code <= 67 or 80 <= current.code <= 82:
        return WeatherDJ(genre="Lo-fi jazz", mood="Fönsterplats", soundscape="Regn mot ruta, mjuk vinyl och kontrabas", reason="Låt regnet stå för hi-haten.")
    if current.code <= 1 and current.is_day:
        return WeatherDJ(genre="Indie pop", mood="Ljus i steget", soundscape="Lätt gitarr, fåglar och varm analog synth", reason="Spara lite av solen till promenaden.")
    if not current.is_day:
        return WeatherDJ(genre="Dream pop", mood="Blå timmen", soundscape="Glittrig synth och stadsljud på avstånd", reason="Kvällen får gärna gå i slow motion.")
    return WeatherDJ(genre="Soft electronic", mood="Lugn upptäckare", soundscape="Dämpad puls, stadssus och enstaka pianotoner", reason="En stadig rytm gör även en grå dag lättare.")


def build_headline(current: CurrentConditions, mood: WeatherMood, sunset: str | None) -> str:
    if current.code >= 95:
        return "Åskan får hålla showen. Du tar skydd."
    if current.wind_speed >= 40 and current.precipitation > 0:
        return "Sidoregn. Jackan får jobba övertid."
    if current.feels_like <= -5:
        return "Kylan har synpunkter på dina öron."
    if mood.mood == "clear" and current.is_day:
        return "Misstänkt mycket sol. Passa på."
    if mood.mood == "rain":
        return "Grå himmel. Kaffe är fortfarande lagligt."
    if sunset:
        return f"En stilla dag. Dagsljuset räcker till {sunset}."
    return "Vädret bestämmer tonen. Du bestämmer dagen."


def build_outdoor_window(
    hourly: list[ForecastHour], forecast_date: str, sunrise: str | None, sunset: str | None
) -> OutdoorWindow:
    suitable = [
        hour
        for hour in hourly
        if hour.date == forecast_date
        and hour.is_day
        and (hour.precipitation_probability is None or hour.precipitation_probability <= 30)
        and (hour.wind_speed is None or hour.wind_speed < 35)
        and hour.weather.mood not in ("storm", "snow")
    ]
    if not suitable:
        return OutdoorWindow(
            available=False,
            date=forecast_date,
            start=None,
            end=None,
            explanation="Ingen lugn och torr dagsljuslucka i den hämtade prognosen. Välj ett inomhusalternativ.",
        )

    start_hour = suitable[0]
    end_hour = suitable[0]
    longest_start = start_hour
    longest_end = end_hour
    longest_length = 1
    run_length = 1

    for previous, hour in zip(suitable, suitable[1:]):
        previous_hour = int(previous.time[:2])
        hour_value = int(hour.time[:2])
        if hour_value == (previous_hour + 1) % 24:
            run_length += 1
        else:
            run_length = 1
            start_hour = hour
        end_hour = hour
        if run_length > longest_length:
            longest_length = run_length
            longest_start = start_hour
            longest_end = end_hour

    if longest_length < 2:
        single_end = f"{(int(longest_end.time[:2]) + 1) % 24:02d}:00"
        if sunset and single_end > sunset:
            single_end = sunset
        return OutdoorWindow(
            available=True,
            date=forecast_date,
            start=longest_start.time,
            end=single_end,
            explanation=f"En kortare lucka med dagsljus och högst 30 % nederbördsrisk. Soluppgång {sunrise or 'saknas'}, solnedgång {sunset or 'saknas'}.",
        )

    end_hour_value = (int(longest_end.time[:2]) + 1) % 24
    end_time = f"{end_hour_value:02d}:00"
    if sunset and end_time > sunset:
        end_time = sunset
    return OutdoorWindow(
        available=True,
        date=forecast_date,
            start=longest_start.time,
        end=end_time,
        explanation=f"Längsta sammanhängande dagsljusfönstret med högst 30 % nederbördsrisk och vind under 35 km/h. Soluppgång {sunrise or 'saknas'}, solnedgång {sunset or 'saknas'}.",
    )


def build_payload(
    data: dict,
    city: str,
    mode: WeatherMode,
    thermal_sensitivity: Literal["cold", "neutral", "warm"] = "neutral",
) -> WeatherPayload:
    raw = data["current"]
    current = CurrentConditions(
        temperature=raw["temperature_2m"],
        feels_like=raw["apparent_temperature"],
        humidity=raw["relative_humidity_2m"],
        precipitation=raw["precipitation"],
        code=raw["weather_code"],
        wind_speed=raw["wind_speed_10m"],
        wind_direction=raw["wind_direction_10m"],
        is_day=bool(raw["is_day"]),
    )
    mood = describe_weather(current.code, current.is_day)
    local_date = data.get("daily", {}).get("time", [""])[0]
    sunrise_value = data.get("daily", {}).get("sunrise", [None])[0]
    sunset_value = data.get("daily", {}).get("sunset", [None])[0]
    sunrise = sunrise_value.split("T", maxsplit=1)[1][:5] if sunrise_value and "T" in sunrise_value else None
    sunset = sunset_value.split("T", maxsplit=1)[1][:5] if sunset_value and "T" in sunset_value else None
    raw_hourly = data.get("hourly", {})
    hourly_values: list[ForecastHour] = []
    times = raw_hourly.get("time", [])
    current_time = raw.get("time", "")
    current_hour = int(current_time[11:13]) if len(current_time) >= 13 else -1

    for index, timestamp in enumerate(times):
        hour_number = int(timestamp[11:13]) if len(timestamp) >= 13 else -1
        if timestamp[:10] == local_date and hour_number <= current_hour:
            continue
        try:
            hourly_values.append(
                ForecastHour(
                    date=timestamp[:10],
                    time=timestamp[11:16],
                    temperature=raw_hourly["temperature_2m"][index],
                    feels_like=raw_hourly.get("apparent_temperature", [None] * len(times))[index],
                    precipitation_probability=raw_hourly.get("precipitation_probability", [None] * len(times))[index],
                    wind_speed=raw_hourly.get("wind_speed_10m", [None] * len(times))[index],
                    wind_direction=raw_hourly.get("wind_direction_10m", [None] * len(times))[index],
                    weather=describe_weather(raw_hourly["weather_code"][index], bool(raw_hourly.get("is_day", [1] * len(times))[index])),
                    is_day=bool(raw_hourly.get("is_day", [1] * len(times))[index]),
                )
            )
        except (IndexError, KeyError, TypeError):
            continue

    daily = data.get("daily", {})
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    plans = {
        key: build_plan(current, key, thermal_sensitivity)
        for key in ("outdoor", "indoor", "surprise")
    }
    quests = {key: build_quest(current, key, local_date) for key in ("outdoor", "indoor", "surprise")}

    return WeatherPayload(
        city=city,
        timezone=data.get("timezone", "Europe/Stockholm"),
        date=local_date,
        sunrise=sunrise,
        sunset=sunset,
        temperature_min=min_temps[0] if min_temps else None,
        temperature_max=max_temps[0] if max_temps else None,
        refreshed_at=datetime.now(UTC).isoformat(),
        headline=build_headline(current, mood, sunset),
        current=current,
        weather=mood,
        survival=calculate_survival(current),
        plan=plans[mode],
        quest=quests[mode],
        plans=plans,
        quests=quests,
        dj=build_dj(current),
        hourly=hourly_values,
        outdoor_window=build_outdoor_window(hourly_values, local_date, sunrise, sunset),
    )


def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def normalize_client_id(client_id: str) -> str:
    try:
        return str(UUID(client_id))
    except ValueError as error:
        raise HTTPException(status_code=400, detail="A valid anonymous browser ID is required.") from error


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/weather", response_model=WeatherPayload)
async def get_weather(
    latitude: Annotated[float, Query(ge=-90, le=90)] = 59.3293,
    longitude: Annotated[float, Query(ge=-180, le=180)] = 18.0686,
    city: Annotated[str, Query(min_length=1, max_length=120)] = "Stockholm",
    mode: WeatherMode = "outdoor",
    thermal_sensitivity: Literal["cold", "neutral", "warm"] = "neutral",
    language: Literal["sv", "en"] = "sv",
) -> WeatherPayload:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_FIELDS,
        "hourly": HOURLY_FIELDS,
        "daily": "sunrise,sunset,temperature_2m_min,temperature_2m_max",
        "timezone": "auto",
        "forecast_hours": 24,
    }
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(WEATHER_URL, params=params)
            response.raise_for_status()
            data = response.json()
        payload = build_payload(data, city, mode, thermal_sensitivity)
        if language == "en":
            return WeatherPayload.model_validate(translate_payload(payload.model_dump()))
        return payload
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Väderdata kunde inte hämtas just nu.") from error


@app.get("/api/locations/search")
async def get_location_suggestions(
    query: Annotated[str, Query(min_length=2, max_length=80)],
    language: Literal["sv", "en"] = "sv",
) -> list[dict]:
    try:
        return [city.model_dump() for city in await search_cities(query, language)]
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Ortsökningen är tillfälligt otillgänglig.") from error


@app.get("/api/places", response_model=PlaceSearchResult)
async def get_nearby_places(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    radius_meters: Annotated[int, Query(ge=250, le=5000)] = 1500,
    category: PlaceCategory = "all",
    weather_code: Annotated[int, Query(ge=0, le=99)] = 3,
    precipitation_probability: Annotated[int, Query(ge=0, le=100)] = 0,
    wind_speed: Annotated[float, Query(ge=0, le=300)] = 0,
    feels_like: Annotated[float, Query(ge=-100, le=100)] = 10,
    language: Literal["sv", "en"] = "sv",
    budget: PlaceBudget = "free",
    interests: Annotated[list[PlaceInterest], Query()] = [],
) -> PlaceSearchResult:
    try:
        return await find_nearby_places(
            latitude,
            longitude,
            radius_meters,
            category,
            weather_code,
            precipitation_probability,
            wind_speed,
            feels_like,
            language,
            interests,
            budget,
        )
    except httpx.HTTPError as error:
        return PlaceSearchResult(
            places=[],
            radius_meters=radius_meters,
            available=False,
            message="Karttjänsten svarar inte just nu. Försök igen lite senare.",
        )


@app.get("/api/preferences", response_model=AppPreferences)
def get_preferences(client_id: Annotated[str, Header(alias="X-Client-ID")]) -> AppPreferences:
    client_id = normalize_client_id(client_id)
    with closing(connect_database()) as connection:
        row = connection.execute(
            "SELECT data FROM user_preferences WHERE client_id = ?", (client_id,)
        ).fetchone()
    if row is None:
        return DEFAULT_PREFERENCES
    return AppPreferences.model_validate_json(row["data"])


@app.put("/api/preferences", response_model=AppPreferences)
def save_preferences(
    preferences: AppPreferences,
    client_id: Annotated[str, Header(alias="X-Client-ID")],
) -> AppPreferences:
    client_id = normalize_client_id(client_id)
    with closing(connect_database()) as connection, connection:
        connection.execute(
            "INSERT INTO user_preferences (client_id, data) VALUES (?, ?) "
            "ON CONFLICT(client_id) DO UPDATE SET data = excluded.data",
            (client_id, json.dumps(preferences.model_dump(), ensure_ascii=False)),
        )
    return preferences


@app.get("/api/capsules", response_model=list[Capsule])
def list_capsules(client_id: Annotated[str, Header(alias="X-Client-ID")]) -> list[Capsule]:
    client_id = normalize_client_id(client_id)
    with closing(connect_database()) as connection:
        rows = connection.execute(
            "SELECT id, city, temperature, condition, quest, note, saved_at "
            "FROM capsules WHERE client_id = ? ORDER BY id DESC LIMIT 30",
            (client_id,),
        ).fetchall()
    return [Capsule.model_validate(dict(row)) for row in rows]


@app.post("/api/capsules", response_model=Capsule, status_code=201)
def save_capsule(
    capsule: CapsuleCreate,
    client_id: Annotated[str, Header(alias="X-Client-ID")],
) -> Capsule:
    client_id = normalize_client_id(client_id)
    saved_at = datetime.now(ZoneInfo("Europe/Stockholm")).isoformat(timespec="seconds")
    with closing(connect_database()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO capsules (client_id, city, temperature, condition, quest, note, saved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                client_id,
                capsule.city,
                capsule.temperature,
                capsule.condition,
                capsule.quest,
                capsule.note,
                saved_at,
            ),
        )
        capsule_id = cursor.lastrowid
    return Capsule(id=capsule_id, saved_at=saved_at, **capsule.model_dump())


@app.delete("/api/capsules/{capsule_id}", status_code=204)
def delete_capsule(
    capsule_id: int,
    client_id: Annotated[str, Header(alias="X-Client-ID")],
) -> Response:
    client_id = normalize_client_id(client_id)
    with closing(connect_database()) as connection, connection:
        cursor = connection.execute(
            "DELETE FROM capsules WHERE id = ? AND client_id = ?", (capsule_id, client_id)
        )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Väderkapseln finns inte.")
    return Response(status_code=204)
