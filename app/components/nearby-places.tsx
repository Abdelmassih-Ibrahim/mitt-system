"use client";

import { useEffect, useState } from "react";
import type { Coordinates, Language, NearbyPlace, PlaceCategory, WeatherPayload } from "../weather-types";

const API_BASE = process.env.NEXT_PUBLIC_WEATHER_API ?? "http://127.0.0.1:8000";
const copy = {
  sv: {
    eyebrow: "NÄRA DIG, PÅ RIKTIGT",
    title: "Ett bra ställe att landa på",
    lead: "Platser hämtade från OpenStreetMap. Inga påhittade favoriter.",
    all: "Alla",
    cafe: "Kaféer",
    culture: "Kultur & inomhus",
    loading: "Letar efter riktiga platser i närheten…",
    empty: "Hittade inga kartlagda platser inom den valda radien.",
    error: "Karttjänsten svarar inte just nu. Försök igen om en stund.",
    retry: "Försök igen",
    directions: "Vägbeskrivning",
    map: "Visa karta",
    hours: "Kartlagda tider",
    noHours: "Öppettider saknas i kartdatan",
    feeUnknown: "Avgift okänd",
    feeYes: "Kartdata anger avgift",
    feeNo: "Ingen avgift angiven",
    basedOn: "Relevans för dagens väder",
    distance: "från dig",
    attribution: "Kartdata © OpenStreetMap-bidragsgivare",
  },
  en: {
    eyebrow: "NEAR YOU, FOR REAL",
    title: "A good place to land",
    lead: "Places from OpenStreetMap. No invented local favourites.",
    all: "All places",
    cafe: "Cafés",
    culture: "Culture & indoors",
    loading: "Finding real places nearby…",
    empty: "No mapped places found within this radius.",
    error: "The map service is temporarily unavailable. Try again shortly.",
    retry: "Try again",
    directions: "Directions",
    map: "View map",
    hours: "Hours in map data",
    noHours: "Opening hours are not in the map data",
    feeUnknown: "Fee unknown",
    feeYes: "Map data lists a fee",
    feeNo: "No fee listed",
    basedOn: "Why it fits today",
    distance: "away",
    attribution: "Map data © OpenStreetMap contributors",
  },
};

function formatDistance(meters: number, language: Language) {
  if (meters < 1000) return `${meters} m ${language === "sv" ? "bort" : "away"}`;
  return `${(meters / 1000).toFixed(1).replace(".", language === "sv" ? "," : ".")} km ${language === "sv" ? "bort" : "away"}`;
}

function localizeCategory(category: string, language: Language) {
  if (language === "sv") return category;
  return ({
    "Kafé": "Café",
    "Bibliotek": "Library",
    "Biograf": "Cinema",
    "Kultur": "Arts venue",
    "Saluhall / marknad": "Market",
    "Museum": "Museum",
    "Park": "Park",
    "Inomhusplats": "Indoor place",
  } as Record<string, string>)[category] ?? category;
}

export default function NearbyPlaces({
  coordinates,
  weather,
  radius,
  language,
  budget,
  interests,
}: {
  coordinates: Coordinates;
  weather: WeatherPayload | null;
  radius: number;
  language: Language;
  budget: "free" | "low" | "flexible";
  interests: string[];
}) {
  const [category, setCategory] = useState<PlaceCategory>("all");
  const [places, setPlaces] = useState<NearbyPlace[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const text = copy[language];

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({
      latitude: String(coordinates.latitude),
      longitude: String(coordinates.longitude),
      radius_meters: String(radius),
      category,
      weather_code: String(weather?.current.code ?? 3),
      precipitation_probability: String(weather?.hourly[0]?.precipitation_probability ?? 0),
      wind_speed: String(weather?.current.wind_speed ?? 0),
      feels_like: String(weather?.current.feels_like ?? 10),
      language,
      budget,
    });
    interests.forEach((interest) => params.append("interests", interest));
    Promise.resolve().then(() => {
      if (controller.signal.aborted) return null;
      setIsLoading(true);
      setError("");
      return fetch(`${API_BASE}/api/places?${params}`, { signal: controller.signal, cache: "no-store" });
    })
      .then((response) => {
        if (!response) return null;
        return response;
      })
      .then(async (response) => {
        if (!response) return { places: [] as NearbyPlace[] };
        if (!response.ok) throw new Error("places-unavailable");
        return response.json() as Promise<{ places: NearbyPlace[] }>;
      })
      .then((result) => setPlaces(result.places))
      .catch((fetchError: unknown) => {
        if (fetchError instanceof Error && fetchError.name === "AbortError") return;
        setError(text.error);
        setPlaces([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });
    return () => controller.abort();
  }, [coordinates, radius, category, weather, attempt, language, text.error, budget, interests]);

  const categories: Array<{ id: PlaceCategory; label: string }> = [
    { id: "all", label: text.all },
    { id: "cafe", label: text.cafe },
    { id: "culture", label: text.culture },
  ];

  return (
    <section className="places-section" aria-labelledby="places-title">
      <div className="section-heading section-heading--editorial">
        <div>
          <p className="eyebrow">{text.eyebrow}</p>
          <h2 id="places-title">{text.title}</h2>
          <p className="section-description">{text.lead}</p>
        </div>
        <div className="place-filters" role="group" aria-label={text.title}>
          {categories.map((item) => (
            <button key={item.id} className={category === item.id ? "is-active" : ""} onClick={() => setCategory(item.id)} aria-pressed={category === item.id}>
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? <p className="places-state" role="status">{text.loading}</p> : null}
      {error ? <div className="places-state places-state--error" role="status"><span>{error}</span><button onClick={() => setAttempt((value) => value + 1)}>{text.retry}</button></div> : null}
      {!isLoading && !error && places.length === 0 ? <p className="places-state">{text.empty}</p> : null}

      {places.length ? (
        <div className="places-list">
          {places.slice(0, 6).map((place) => (
            <article className="place-row" key={`${place.osm_type}-${place.osm_id}`}>
              <span className="place-category-mark" aria-hidden="true">{place.category === "Kafé" ? "C" : "M"}</span>
              <div className="place-copy">
                <div className="place-name-line"><h3>{place.name}</h3><span>{formatDistance(place.distance_meters, language)}</span></div>
                <p className="place-meta">{localizeCategory(place.category, language)}{place.address ? ` · ${place.address}` : ""}</p>
                <p className="place-reason">{place.reason}</p>
                <p className="place-hours">{place.opening_hours ? `${text.hours}: ${place.opening_hours}` : text.noHours} · {place.fee === true ? text.feeYes : place.fee === false ? text.feeNo : text.feeUnknown}</p>
              </div>
              <div className="place-actions">
                <a href={place.directions_url} target="_blank" rel="noreferrer">{text.directions} ↗</a>
                <a href={place.map_url} target="_blank" rel="noreferrer">{text.map}</a>
              </div>
            </article>
          ))}
        </div>
      ) : null}
      <p className="map-attribution"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">{text.attribution}</a></p>
    </section>
  );
}
