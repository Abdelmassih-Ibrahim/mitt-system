from __future__ import annotations

import os
import random
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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


class SurvivalIndex(BaseModel):
    score: int
    level: str
    summary: str


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
    sunset: str | None
    refreshed_at: str
    current: CurrentConditions
    weather: WeatherMood
    survival: SurvivalIndex
    plan: DayPlan
    quest: Quest
    dj: WeatherDJ


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
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS capsules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                temperature REAL NOT NULL,
                condition TEXT NOT NULL,
                quest TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                saved_at TEXT NOT NULL
            )
            """
        )


def describe_weather(code: int, is_day: bool) -> WeatherMood:
    label, icon, mood = WEATHER_CODES.get(code, ("Väder på väg", "🌥️", "cloud"))
    if not is_day and mood == "clear":
        return WeatherMood(label="Klart i natt", icon="🌙", mood="night")
    if not is_day and mood == "cloud":
        return WeatherMood(label="Molnig kväll", icon="☁️", mood="night-cloud")
    return WeatherMood(label=label, icon=icon, mood=mood)


def calculate_survival(current: CurrentConditions) -> SurvivalIndex:
    score = 0
    if current.feels_like <= -15:
        score += 45
    elif current.feels_like <= -5:
        score += 34
    elif current.feels_like <= 2:
        score += 24
    elif current.feels_like <= 7:
        score += 14
    elif current.feels_like <= 12:
        score += 6

    if current.wind_speed >= 60:
        score += 32
    elif current.wind_speed >= 40:
        score += 24
    elif current.wind_speed >= 25:
        score += 14
    elif current.wind_speed >= 15:
        score += 7

    if current.precipitation >= 5:
        score += 27
    elif current.precipitation >= 1:
        score += 20
    elif current.precipitation > 0:
        score += 11

    if current.code >= 95:
        score += 25
    if current.code in (45, 48):
        score += 8

    score = min(score, 100)
    if score >= 70:
        return SurvivalIndex(score=score, level="Expedition", summary="Vädret kräver en genomtänkt plan.")
    if score >= 45:
        return SurvivalIndex(score=score, level="Äventyr", summary="Ute går bra med rätt förberedelser.")
    if score >= 20:
        return SurvivalIndex(score=score, level="Jackväder", summary="Ett extra lager gör dagen enklare.")
    return SurvivalIndex(score=score, level="Lätt bris", summary="Bra läge för en spontan sväng ut.")


def build_plan(current: CurrentConditions, mode: WeatherMode) -> DayPlan:
    wet = current.precipitation > 0 or 51 <= current.code <= 82 or current.code >= 95
    cold = current.feels_like <= 5
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
        activity_title = "En ny värld bakom nästa dörr."
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


def build_payload(data: dict, city: str, mode: WeatherMode) -> WeatherPayload:
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
    sunset_value = data.get("daily", {}).get("sunset", [None])[0]
    sunset = sunset_value.split("T", maxsplit=1)[1][:5] if sunset_value and "T" in sunset_value else None

    return WeatherPayload(
        city=city,
        timezone=data.get("timezone", "Europe/Stockholm"),
        date=local_date,
        sunset=sunset,
        refreshed_at=datetime.now(UTC).isoformat(),
        current=current,
        weather=mood,
        survival=calculate_survival(current),
        plan=build_plan(current, mode),
        quest=build_quest(current, mode, local_date),
        dj=build_dj(current),
    )


def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/weather", response_model=WeatherPayload)
async def get_weather(
    latitude: Annotated[float, Query(ge=-90, le=90)] = 59.3293,
    longitude: Annotated[float, Query(ge=-180, le=180)] = 18.0686,
    city: Annotated[str, Query(min_length=1, max_length=120)] = "Stockholm",
    mode: WeatherMode = "outdoor",
) -> WeatherPayload:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_FIELDS,
        "daily": "sunset",
        "timezone": "auto",
        "forecast_days": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(WEATHER_URL, params=params)
            response.raise_for_status()
            data = response.json()
        return build_payload(data, city, mode)
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Väderdata kunde inte hämtas just nu.") from error


@app.get("/api/capsules", response_model=list[Capsule])
def list_capsules() -> list[Capsule]:
    with connect_database() as connection:
        rows = connection.execute(
            "SELECT id, city, temperature, condition, quest, note, saved_at "
            "FROM capsules ORDER BY id DESC LIMIT 30"
        ).fetchall()
    return [Capsule.model_validate(dict(row)) for row in rows]


@app.post("/api/capsules", response_model=Capsule, status_code=201)
def save_capsule(capsule: CapsuleCreate) -> Capsule:
    saved_at = datetime.now(ZoneInfo("Europe/Stockholm")).isoformat(timespec="seconds")
    with connect_database() as connection:
        cursor = connection.execute(
            "INSERT INTO capsules (city, temperature, condition, quest, note, saved_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
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
def delete_capsule(capsule_id: int) -> Response:
    with connect_database() as connection:
        cursor = connection.execute("DELETE FROM capsules WHERE id = ?", (capsule_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Väderkapseln finns inte.")
    return Response(status_code=204)
