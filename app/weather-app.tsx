"use client";

import { useEffect, useState } from "react";
import HourlyForecast from "./components/hourly-forecast";
import NearbyPlaces from "./components/nearby-places";
import PreferencesPanel from "./components/preferences-panel";
import type { Capsule, Coordinates, Language, Mode, Preferences, WeatherPayload } from "./weather-types";

const API_BASE = process.env.NEXT_PUBLIC_WEATHER_API ?? "http://127.0.0.1:8000";
const STOCKHOLM: Coordinates = { latitude: 59.3293, longitude: 18.0686, name: "Stockholm", timezone: "Europe/Stockholm" };
const DEFAULT_PREFERENCES: Preferences = {
  location_name: "Stockholm", latitude: 59.3293, longitude: 18.0686, timezone: "Europe/Stockholm",
  language: "sv", temperature_unit: "celsius", thermal_sensitivity: "neutral",
  preferred_mode: "outdoor", walking_distance_meters: 1500, budget: "free",
  interests: ["coffee", "nature", "culture"],
};
const REFRESH_INTERVAL = 15 * 60 * 1000;

const ui = {
  sv: {
    tagline: "Väder med omtanke",
    intro: "Vädret bestämmer tonen. Du bestämmer dagen.",
    current: "JUST NU I",
    feels: "Känns som",
    humidity: "Luftfuktighet",
    wind: "Vind",
    sunrise: "Solen går upp",
    sunset: "Solen går ner",
    status: "Prognos hämtad",
    loading: "Hämtar den senaste prognosen…",
    unavailable: "Väderdata kunde inte hämtas. Kontrollera anslutningen och försök igen.",
    refresh: "Uppdatera",
    locate: "Använd min plats",
    locating: "Hämtar plats…",
    permission: "Plats används för att visa lokalt väder och verkliga ställen nära dig. Webbläsaren frågar om tillstånd.",
    find: "Sök ort",
    searchPlaceholder: "Skriv en svensk ort",
    nearby: "Välj ort",
    searchError: "Ortsökningen fungerar inte just nu.",
    score: "Dagens väderkomfort",
    scoreNote: "Vädervetts uppskattning, inte ett officiellt mått.",
    whyScore: "Vad påverkar poängen?",
    noFactors: "Inga större väderavdrag just nu.",
    ready: "Redo",
    outfit: "Klä dig för vädret",
    outfitWhy: "Varför de här lagren",
    activityLabel: "DAGENS ÖVERLEVNADSPLAN",
    activityTitle: "Tre sätt att möta dagen",
    outdoor: "BÄST UTOMHUS",
    indoor: "MYSIGT INNE",
    adventure: "OVÄNTAT ÄVENTYR",
    selected: "Ditt val",
    modeTitle: "Hur vill du möta dagen?",
    modes: { outdoor: "Jag vill ut", indoor: "Håll mig inne", surprise: "Överraska mig" },
    capsules: "Väderminnen",
    capsuleIntro: "Spara ett litet ögonblick från dagen.",
    capsulePlaceholder: "Vad vill du minnas?",
    saveCapsule: "Spara ögonblick",
    saving: "Sparar…",
    saved: "Ögonblicket sparades.",
    saveFailed: "Kunde inte spara väderminnet.",
    emptyCapsules: "Inga sparade väderminnen ännu.",
    delete: "Ta bort",
    footer: "Väderdata från Open-Meteo",
    languageSv: "Svenska",
    languageEn: "English",
  },
  en: {
    tagline: "Weather, with a little care",
    intro: "The weather sets the tone. You choose the day.",
    current: "RIGHT NOW IN",
    feels: "Feels like",
    humidity: "Humidity",
    wind: "Wind",
    sunrise: "Sunrise",
    sunset: "Sunset",
    status: "Forecast updated",
    loading: "Getting the latest forecast…",
    unavailable: "Weather data is unavailable. Check your connection and try again.",
    refresh: "Refresh",
    locate: "Use my location",
    locating: "Finding location…",
    permission: "Your location helps show local weather and real nearby places. Your browser will ask for permission.",
    find: "Search city",
    searchPlaceholder: "Enter a Swedish city",
    nearby: "Choose a city",
    searchError: "City search is unavailable right now.",
    score: "Today's weather comfort",
    scoreNote: "Vädervett estimate, not an official measure.",
    whyScore: "What affects the score?",
    noFactors: "No major weather deductions right now.",
    ready: "Ready",
    outfit: "Dress for this weather",
    outfitWhy: "Why these layers",
    activityLabel: "TODAY'S SURVIVAL PLAN",
    activityTitle: "Three ways to meet the day",
    outdoor: "BEST OUTDOOR OPTION",
    indoor: "COZY INDOOR OPTION",
    adventure: "UNEXPECTED ADVENTURE",
    selected: "Your choice",
    modeTitle: "How do you want to meet the day?",
    modes: { outdoor: "I want outside", indoor: "Keep me in", surprise: "Surprise me" },
    capsules: "Weather memories",
    capsuleIntro: "Save one small moment from today.",
    capsulePlaceholder: "What do you want to remember?",
    saveCapsule: "Save this moment",
    saving: "Saving…",
    saved: "Moment saved.",
    saveFailed: "Could not save this weather memory.",
    emptyCapsules: "No saved weather memories yet.",
    delete: "Delete",
    footer: "Weather data by Open-Meteo",
    languageSv: "Svenska",
    languageEn: "English",
  },
};

const weatherTranslations: Record<string, string> = {
  "Klart och soligt": "Clear and sunny", "Mestadels klart": "Mostly clear", "Växlande molnighet": "Partly cloudy",
  "Mulet": "Overcast", "Dimma": "Fog", "Dimma med frost": "Freezing fog", "Lätt duggregn": "Light drizzle",
  "Duggregn och regn": "Drizzle and rain", "Tätt duggregn": "Dense drizzle", "Lätt regn": "Light rain",
  "Regn": "Rain", "Kraftigt regn": "Heavy rain", "Regnskurar": "Rain showers", "Kraftiga regnskurar": "Heavy showers",
  "Lätt snöfall": "Light snow", "Snöfall": "Snowfall", "Kraftigt snöfall": "Heavy snow", "Snöbyar": "Snow showers",
  "Kraftiga snöbyar": "Heavy snow showers", "Åska": "Thunderstorm", "Åska och hagel": "Thunderstorm and hail",
  "Klart i natt": "Clear tonight", "Molnig kväll": "Cloudy evening",
};
const phraseTranslations: Record<string, string> = {
  "Vattentätt före allt annat.": "Waterproof first.", "Lager på lager vinner.": "Layers make the difference.",
  "Klä dig för en lång dag ute.": "Dress for a long day outside.", "Gör museet till utflykten.": "Make the museum the outing.",
  "Hitta lä bakom husen.": "Find shelter between the buildings.", "Ta omvägen genom parken.": "Take the scenic route through the park.",
  "Gör inomhuset till äventyret.": "Make indoors the adventure.", "En liten inomhusvärld att upptäcka.": "A little indoor world to discover.",
  "Ta en omväg du inte planerat.": "Take an unplanned detour.", "En dörr du aldrig öppnat": "A door you've never opened",
  "Fem droppar från torrskodd": "Five drops from staying dry", "Jakten på stadens bästa skydd": "Find the city's best shelter",
  "Följ ljusstrimman": "Follow the strip of light", "Färgspaning": "Colour spotting",
};

function localize(value: string, language: Language) {
  return language === "en" ? (weatherTranslations[value] ?? phraseTranslations[value] ?? value) : value;
}

function temperatureValue(value: number, unit: Preferences["temperature_unit"]) {
  return Math.round(unit === "fahrenheit" ? value * 9 / 5 + 32 : value);
}

function formatTime(date: Date, options: Intl.DateTimeFormatOptions, timezone: string, language: Language) {
  return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-GB", { ...options, timeZone: timezone }).format(date);
}

function windDirection(degrees: number) {
  const directions = ["N", "NÖ", "Ö", "SÖ", "S", "SV", "V", "NV"];
  return directions[Math.round(degrees / 45) % directions.length];
}

function capsuleDate(value: string, language: Language) {
  return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-GB", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  }).format(new Date(value));
}

export default function WeatherApp() {
  const [coordinates, setCoordinates] = useState(STOCKHOLM);
  const [weather, setWeather] = useState<WeatherPayload | null>(null);
  const [capsules, setCapsules] = useState<Capsule[]>([]);
  const [clientId, setClientId] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES);
  const [mode, setMode] = useState<Mode>("outdoor");
  const [now, setNow] = useState<Date | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [capsuleNote, setCapsuleNote] = useState("");
  const [cityQuery, setCityQuery] = useState("");
  const [cityResults, setCityResults] = useState<Coordinates[]>([]);
  const [citySearchError, setCitySearchError] = useState("");
  const [searchingCities, setSearchingCities] = useState(false);
  const t = ui[preferences.language];

  useEffect(() => {
    const updateClock = () => setNow(new Date());
    updateClock();
    const timer = window.setInterval(updateClock, 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    document.documentElement.lang = preferences.language;
  }, [preferences.language]);

  useEffect(() => {
    const storageKey = "vadervett-browser-id";
    let id = window.localStorage.getItem(storageKey);
    if (!id) {
      id = window.crypto.randomUUID();
      window.localStorage.setItem(storageKey, id);
    }
    setClientId(id);
  }, []);

  useEffect(() => {
    if (!clientId) return;
    let active = true;
    const headers = { "X-Client-ID": clientId };
    Promise.all([
      fetch(`${API_BASE}/api/preferences`, { cache: "no-store", headers }).then((response) => response.ok ? response.json() as Promise<Preferences> : DEFAULT_PREFERENCES),
      fetch(`${API_BASE}/api/capsules`, { cache: "no-store", headers }).then((response) => response.ok ? response.json() as Promise<Capsule[]> : []),
    ]).then(([savedPreferences, savedCapsules]) => {
      if (!active) return;
      setPreferences(savedPreferences);
      setMode(savedPreferences.preferred_mode);
      setCoordinates({
        name: savedPreferences.location_name,
        latitude: savedPreferences.latitude,
        longitude: savedPreferences.longitude,
        timezone: savedPreferences.timezone,
      });
      setCapsules(savedCapsules);
    }).catch(() => {
      if (active) setStatusMessage("Python API is not available yet.");
    });
    return () => { active = false; };
  }, [clientId]);

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({
      latitude: String(coordinates.latitude), longitude: String(coordinates.longitude),
      city: coordinates.name, mode: "outdoor",
      thermal_sensitivity: preferences.thermal_sensitivity,
      language: preferences.language,
    });
    Promise.resolve().then(() => {
      if (controller.signal.aborted) return null;
      setIsRefreshing(true);
      return fetch(`${API_BASE}/api/weather?${params}`, { cache: "no-store", signal: controller.signal });
    })
      .then((response) => response)
      .then(async (response) => {
        if (!response) return null;
        if (!response.ok) throw new Error("weather-unavailable");
        return response.json() as Promise<WeatherPayload>;
      })
      .then((data) => {
        if (!data) return;
        setWeather(data);
        setLastUpdated(new Date());
        setStatusMessage("");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || (error instanceof Error && error.name === "AbortError")) return;
        setStatusMessage(t.unavailable);
      })
      .finally(() => { if (!controller.signal.aborted) setIsRefreshing(false); });
    const timer = window.setInterval(() => setRefreshToken((value) => value + 1), REFRESH_INTERVAL);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [coordinates, preferences.language, preferences.thermal_sensitivity, refreshToken, t.unavailable]);

  const localTime = now ? formatTime(now, { hour: "2-digit", minute: "2-digit" }, weather?.timezone ?? coordinates.timezone ?? "Europe/Stockholm", preferences.language) : "--:--";
  const seconds = now ? formatTime(now, { second: "2-digit" }, weather?.timezone ?? coordinates.timezone ?? "Europe/Stockholm", preferences.language) : "--";
  const date = now ? formatTime(now, { weekday: "long", day: "numeric", month: "long" }, weather?.timezone ?? coordinates.timezone ?? "Europe/Stockholm", preferences.language) : "";
  const condition = weather?.weather;
  const weatherMood = condition?.mood.replace(/[^a-z-]/g, "") ?? "cloud";
  const selectedPlan = weather?.plans[mode] ?? weather?.plan;
  const selectedQuest = weather?.quests[mode] ?? weather?.quest;
  const heroHeadline = weather?.headline
    ? preferences.language === "en"
      ? localize(weather.headline, "en")
      : weather.headline
    : t.intro;

  const useMyLocation = () => {
    setStatusMessage(t.permission);
    if (!navigator.geolocation) {
      setStatusMessage("Platsdelning stöds inte i den här webbläsaren.");
      return;
    }
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords: position }) => {
        const location = {
          name: preferences.language === "sv" ? "Min plats" : "My location",
          latitude: position.latitude,
          longitude: position.longitude,
          timezone: weather?.timezone ?? "Europe/Stockholm",
        };
        setCoordinates(location);
        void savePreferences({ ...preferences, location_name: location.name, latitude: location.latitude, longitude: location.longitude, timezone: location.timezone });
        setIsLocating(false);
      },
      () => {
        setStatusMessage(preferences.language === "sv" ? "Platsåtkomst nekades. Välj en ort i sökfältet i stället." : "Location access was declined. Search for a city instead.");
        setIsLocating(false);
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 12000 },
    );
  };

  const searchCities = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (cityQuery.trim().length < 2) return;
    setSearchingCities(true);
    setCitySearchError("");
    try {
      const response = await fetch(`${API_BASE}/api/locations/search?${new URLSearchParams({ query: cityQuery.trim(), language: preferences.language })}`);
      if (!response.ok) throw new Error("city-search-failed");
      const results = await response.json() as Array<{ name: string; admin1: string | null; latitude: number; longitude: number; timezone: string }>;
      setCityResults(results.map((result) => ({
        name: result.admin1 ? `${result.name}, ${result.admin1}` : result.name,
        latitude: result.latitude, longitude: result.longitude, timezone: result.timezone,
      })));
    } catch {
      setCitySearchError(t.searchError);
    } finally {
      setSearchingCities(false);
    }
  };

  const chooseLocation = (location: Coordinates) => {
    setCoordinates(location);
    setCityResults([]);
    setCityQuery("");
    void savePreferences({
      ...preferences,
      location_name: location.name,
      latitude: location.latitude,
      longitude: location.longitude,
      timezone: location.timezone ?? "Europe/Stockholm",
    }).catch(() => setStatusMessage(t.saveFailed));
  };

  const savePreferences = async (next: Preferences) => {
    if (!clientId) throw new Error("browser-id-not-ready");
    setIsSavingPreferences(true);
    try {
      const response = await fetch(`${API_BASE}/api/preferences`, {
        method: "PUT", headers: { "Content-Type": "application/json", "X-Client-ID": clientId ?? "" }, body: JSON.stringify(next),
      });
      if (!response.ok) throw new Error("preferences-invalid");
      const saved = await response.json() as Preferences;
      setPreferences(saved);
      setMode(saved.preferred_mode);
      setCoordinates({ name: saved.location_name, latitude: saved.latitude, longitude: saved.longitude, timezone: saved.timezone });
    } finally {
      setIsSavingPreferences(false);
    }
  };

  const saveCapsule = async () => {
    if (!weather || !selectedQuest) return;
    setIsSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/capsules`, {
        method: "POST", headers: { "Content-Type": "application/json", "X-Client-ID": clientId ?? "" },
        body: JSON.stringify({
          city: weather.city, temperature: weather.current.temperature,
          condition: weather.weather.label, quest: selectedQuest.title, note: capsuleNote,
        }),
      });
      if (!response.ok) throw new Error("capsule-save-failed");
      const capsule = await response.json() as Capsule;
      setCapsules((existing) => [capsule, ...existing].slice(0, 30));
      setCapsuleNote("");
      setStatusMessage(t.saved);
    } catch {
      setStatusMessage(t.saveFailed);
    } finally {
      setIsSaving(false);
    }
  };

  const deleteCapsule = async (id: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/capsules/${id}`, { method: "DELETE", headers: { "X-Client-ID": clientId ?? "" } });
      if (!response.ok) throw new Error("capsule-delete-failed");
      setCapsules((existing) => existing.filter((capsule) => capsule.id !== id));
    } catch {
      setStatusMessage("Could not delete that weather memory.");
    }
  };

  return (
    <main className={`survival-app editorial-app weather-scene--${weatherMood}`}>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Vädervett, startsida"><span className="brand-mark">V</span><span>VÄDERVETT</span></a>
        <div className="topbar-note"><span className={`live-dot${isRefreshing ? " is-refreshing" : ""}`} /><span>{isRefreshing ? "LIVE · HÄMTAR" : "SVERIGE, JUST NU"}</span></div>
        <div className="header-actions">
          <span className="location-label"><span aria-hidden="true">⌖</span>{weather?.city ?? coordinates.name}</span>
          <button className="location-button" onClick={useMyLocation} disabled={isLocating} title={t.permission}><span aria-hidden="true">◎</span>{isLocating ? t.locating : t.locate}</button>
        </div>
      </header>

      <div className="page-content" id="top">
        <section className="page-intro">
          <p className="eyebrow">{t.tagline}</p>
          <div className="intro-heading-row"><h1>{heroHeadline}</h1><time className="intro-clock" aria-label={`${date} ${localTime}`}><span>{localTime}</span><small>{seconds}</small><span className="intro-clock-date">{date}</span></time></div>
          <div className="intro-bottom-row"><p>{t.intro}</p><form className="city-search" onSubmit={(event) => void searchCities(event)}><label className="visually-hidden" htmlFor="city-search-input">{t.find}</label><input id="city-search-input" value={cityQuery} onChange={(event) => setCityQuery(event.target.value)} placeholder={t.searchPlaceholder} /><button type="submit" disabled={searchingCities}>{searchingCities ? "…" : t.find}</button></form></div>
          {citySearchError ? <p className="inline-error" role="status">{citySearchError}</p> : null}
          {cityResults.length ? <div className="city-results" role="listbox" aria-label={t.nearby}>{cityResults.map((city) => <button key={`${city.latitude}-${city.longitude}`} onClick={() => chooseLocation(city)}>{city.name}<span>{city.timezone}</span></button>)}</div> : null}
        </section>

        <section className={`weather-hero editorial-hero weather-hero--${weatherMood}`} aria-label={`${t.current} ${weather?.city ?? coordinates.name}`}>
          <div className={`weather-atmosphere atmosphere--${weatherMood}`} aria-hidden="true"><span className="weather-sun" /><span className="weather-cloud" /><i className="weather-particle" /><i className="weather-particle" /><i className="weather-particle" /><i className="weather-particle" /><i className="weather-particle" /></div>
          <div className="weather-main">
            <p className="eyebrow eyebrow--light">{t.current} {weather?.city.toUpperCase() ?? coordinates.name.toUpperCase()} <span className="live-pip" /></p>
            <div className="weather-reading"><span className="weather-icon" aria-hidden="true">{condition?.icon ?? "◌"}</span><span className="temperature-value" aria-label={weather ? `${temperatureValue(weather.current.temperature, preferences.temperature_unit)} degrees` : "Loading temperature"}>{weather ? `${temperatureValue(weather.current.temperature, preferences.temperature_unit)}°` : "—°"}</span></div>
            <h2 className="weather-description">{condition ? localize(condition.label, preferences.language) : (preferences.language === "sv" ? "Hämtar vädret" : "Getting the weather")}</h2>
            <p className="weather-feels">{weather ? `${t.feels} ${temperatureValue(weather.current.feels_like, preferences.temperature_unit)}°` : t.loading}{weather && weather.temperature_min !== null && weather.temperature_max !== null ? ` · ${temperatureValue(weather.temperature_min, preferences.temperature_unit)}° / ${temperatureValue(weather.temperature_max, preferences.temperature_unit)}°` : ""}</p>
            <div className="weather-stats"><div><small>{t.wind}</small><strong>{weather ? `${Math.round(weather.current.wind_speed)} km/h ${windDirection(weather.current.wind_direction)}` : "—"}</strong></div><div><small>{t.humidity}</small><strong>{weather ? `${weather.current.humidity}%` : "—"}</strong></div><div><small>{t.sunrise}</small><strong>{weather?.sunrise ?? "—"}</strong></div><div><small>{t.sunset}</small><strong>{weather?.sunset ?? "—"}</strong></div></div>
          </div>
          <div className="weather-hero-side"><aside className="daylight-panel"><p className="eyebrow">{preferences.language === "sv" ? "DAGENS LJUS" : "TODAY'S LIGHT"}</p><div className="daylight-times"><span><small>{t.sunrise}</small><strong>{weather?.sunrise ?? "—"}</strong></span><i aria-hidden="true" /><span><small>{t.sunset}</small><strong>{weather?.sunset ?? "—"}</strong></span></div><p>{weather?.outdoor_window.available ? `${weather.outdoor_window.start}–${weather.outdoor_window.end} · ${preferences.language === "sv" ? "promenadlucka" : "walk window"}` : (preferences.language === "sv" ? "Ta vara på ljuset" : "Make the most of the light")}</p></aside><div className="weather-source"><span>{isRefreshing ? t.loading : `${t.status} ${lastUpdated ? formatTime(lastUpdated, { hour: "2-digit", minute: "2-digit" }, weather?.timezone ?? "Europe/Stockholm", preferences.language) : ""}`}</span><button className="refresh-button" onClick={() => setRefreshToken((value) => value + 1)} disabled={isRefreshing}>{t.refresh} ↻</button></div></div>
        </section>
        {statusMessage ? <p className="status-message" role="status">{statusMessage}</p> : null}

        <section className="score-section" aria-labelledby="score-title">
          <div className="score-number-block"><p className="eyebrow">{t.score}</p><div><strong>{weather?.survival.score ?? "—"}</strong><span>/100</span></div><p>{weather ? localize(weather.survival.level, preferences.language) : t.loading}</p></div>
          <div className="score-details"><div className="score-track" role="meter" aria-label={t.score} aria-valuemin={0} aria-valuemax={100} aria-valuenow={weather?.survival.score ?? 0}><span style={{ width: `${weather?.survival.score ?? 0}%` }} /></div><p>{weather ? localize(weather.survival.summary, preferences.language) : t.scoreNote}</p><details><summary>{t.whyScore}</summary><p className="score-disclaimer">{weather?.survival.disclaimer ?? t.scoreNote}</p>{weather?.survival.factors.length ? <ul>{weather.survival.factors.map((factor) => <li key={factor.label}><strong>{factor.label} −{factor.deduction}</strong><span>{factor.explanation}</span></li>)}</ul> : <p>{t.noFactors}</p>}</details></div>
        </section>

        <section className="mode-section" aria-labelledby="mode-title"><div><p className="eyebrow">{t.activityLabel}</p><h2 id="mode-title">{t.modeTitle}</h2></div><div className="mode-switch" role="group" aria-label={t.modeTitle}>{(["outdoor", "indoor", "surprise"] as const).map((item) => <button key={item} className={mode === item ? "is-active" : ""} onClick={() => setMode(item)} aria-pressed={mode === item}>{t.modes[item]}</button>)}</div></section>

        <section className="outfit-section"><div className="section-heading section-heading--editorial"><div><p className="eyebrow">{t.outfit}</p><h2>{selectedPlan ? localize(selectedPlan.outfit_title, preferences.language) : t.loading}</h2><p className="section-description">{selectedPlan ? localize(selectedPlan.outfit_text, preferences.language) : ""}</p></div><span className="outfit-mark" aria-hidden="true">01</span></div>{selectedPlan?.tip ? <p className="outfit-tip">{localize(selectedPlan.tip, preferences.language)}</p> : null}</section>

        <section className="plan-section" aria-labelledby="plan-title"><div className="section-heading section-heading--editorial"><div><p className="eyebrow">{t.activityLabel}</p><h2 id="plan-title">{t.activityTitle}</h2></div><p className="section-aside">{t.selected}: {t.modes[mode]}</p></div><div className="plan-grid plan-grid--editorial"><article className="plan-card"><span className="card-label">02 / {t.outdoor}</span><h3>{localize(weather?.plans.outdoor.activity_title ?? "", preferences.language) || "—"}</h3><p>{localize(weather?.plans.outdoor.activity_text ?? "", preferences.language)}</p><p className="card-reason">{weather?.outdoor_window.available ? `${weather.outdoor_window.start}–${weather.outdoor_window.end}` : (preferences.language === "sv" ? "Ingen säker väderlucka utlovas" : "No suitable weather window promised")}</p></article><article className="plan-card"><span className="card-label">03 / {t.indoor}</span><h3>{localize(weather?.plans.indoor.activity_title ?? "", preferences.language) || "—"}</h3><p>{localize(weather?.plans.indoor.activity_text ?? "", preferences.language)}</p><p className="card-reason">{selectedPlan ? localize(selectedPlan.cafe_text, preferences.language) : ""}</p></article><article className="plan-card plan-card--accent"><span className="card-label">04 / {t.adventure}</span><h3>{localize(selectedQuest?.title ?? "", preferences.language) || "—"}</h3><p>{localize(selectedQuest?.description ?? "", preferences.language)}</p><p className="card-reason">{selectedQuest?.reward}</p></article></div></section>

        {weather ? <HourlyForecast hours={weather.hourly} window={weather.outdoor_window} language={preferences.language} unit={preferences.temperature_unit} /> : null}
        <NearbyPlaces coordinates={coordinates} weather={weather} radius={preferences.walking_distance_meters} language={preferences.language} budget={preferences.budget} interests={preferences.interests} />

        <PreferencesPanel key={JSON.stringify(preferences)} value={preferences} onSave={savePreferences} isSaving={isSavingPreferences || !clientId} onSaved={setStatusMessage} onError={setStatusMessage} />

        <section className="capsule-section" aria-labelledby="capsules-title"><div className="capsule-heading"><div><p className="eyebrow">{t.capsules}</p><h2 id="capsules-title">{t.capsuleIntro}</h2></div><div className="capsule-input-row"><label className="visually-hidden" htmlFor="capsule-note">{t.capsulePlaceholder}</label><input id="capsule-note" value={capsuleNote} maxLength={280} onChange={(event) => setCapsuleNote(event.target.value)} placeholder={t.capsulePlaceholder} /><button onClick={() => void saveCapsule()} disabled={!weather || !clientId || isSaving}>{isSaving ? t.saving : t.saveCapsule}</button></div></div><div className="capsule-list">{capsules.length ? capsules.slice(0, 4).map((capsule) => <article className="capsule-item" key={capsule.id}><span>{capsuleDate(capsule.saved_at, preferences.language)}</span><strong>{capsule.city} · {temperatureValue(capsule.temperature, preferences.temperature_unit)}° · {localize(capsule.condition, preferences.language)}</strong><p>{localize(capsule.quest, preferences.language)}{capsule.note ? ` · “${capsule.note}”` : ""}</p><button onClick={() => void deleteCapsule(capsule.id)} aria-label={`${t.delete} ${capsule.city}`}>{t.delete}</button></article>) : <p className="capsule-empty">{t.emptyCapsules}</p>}</div></section>

        <footer className="page-footer"><span>VÄDERVETT <span className="footer-mark">/</span> OUTSMART THE WEATHER</span><span>{t.footer} · <a href="https://open-meteo.com/" target="_blank" rel="noreferrer">OPEN-METEO</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OPENSTREETMAP</a></span></footer>
      </div>
    </main>
  );
}
