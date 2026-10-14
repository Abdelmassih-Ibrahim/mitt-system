"use client";

import { useEffect, useState } from "react";
import type { Coordinates, Language, NearbyPlace, PlaceCategory, WeatherPayload } from "../weather-types";

type ResolvedPlaceImage = {
  image_url: string;
  image_page_url: string;
  image_source: "commons" | "google";
  author_attributions: Array<{ display_name: string; url: string }>;
};

const API_BASE = process.env.NEXT_PUBLIC_WEATHER_API ?? (typeof window === "undefined" ? "http://127.0.0.1:8000" : `${window.location.protocol}//${window.location.hostname}:8000`);
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
    serviceMessage: "Karttjänsten svarar inte just nu. Försök igen lite senare.",
    retry: "Försök igen",
    directions: "Vägbeskrivning",
    map: "Visa karta",
    photoSource: "Bildkälla",
    hours: "Kartlagda tider",
    noHours: "Öppettider saknas i kartdatan",
    feeUnknown: "Avgift okänd",
    feeYes: "Kartdata anger avgift",
    feeNo: "Ingen avgift angiven",
    basedOn: "Relevans för dagens väder",
    distance: "från dig",
    attribution: "Kartdata © OpenStreetMap-bidragsgivare",
    poweredByGeoapify: "Powered by Geoapify",
    googleMaps: "Google Maps",
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
    serviceMessage: "The map service is temporarily unavailable. Try again shortly.",
    retry: "Try again",
    directions: "Directions",
    map: "View map",
    photoSource: "Photo source",
    hours: "Hours in map data",
    noHours: "Opening hours are not in the map data",
    feeUnknown: "Fee unknown",
    feeYes: "Map data lists a fee",
    feeNo: "No fee listed",
    basedOn: "Why it fits today",
    distance: "away",
    attribution: "Map data © OpenStreetMap contributors",
    poweredByGeoapify: "Powered by Geoapify",
    googleMaps: "Google Maps",
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
    "Träning": "Fitness",
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
  const [resolvedImages, setResolvedImages] = useState<Record<string, ResolvedPlaceImage>>({});
  const [provider, setProvider] = useState<"overpass" | "geoapify">("overpass");
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
        return response.json() as Promise<{ places: NearbyPlace[]; available?: boolean; message?: string | null; provider?: "overpass" | "geoapify" }>;
      })
      .then((result) => {
        setPlaces(result.places);
        setProvider(result.provider ?? "overpass");
        if (result.available === false) setError(text.serviceMessage);
        const imageCandidates = result.places
          .filter((place) => !place.image_url)
          .slice(0, 6)
          .map(({ osm_type, osm_id, name, category, latitude, longitude }) => ({
            osm_type, osm_id, name, category, latitude, longitude,
          }));
        if (imageCandidates.length) {
          void fetch(`${API_BASE}/api/place-images`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              latitude: coordinates.latitude,
              longitude: coordinates.longitude,
              radius_meters: radius,
              category,
              language,
              places: imageCandidates,
            }),
            signal: controller.signal,
          })
            .then((response) => response.ok
              ? response.json() as Promise<Record<string, ResolvedPlaceImage>>
              : {})
            .then((images) => setResolvedImages((current) => ({ ...current, ...images })))
            .catch(() => undefined);
        }
      })
      .catch((fetchError: unknown) => {
        if (fetchError instanceof Error && fetchError.name === "AbortError") return;
        setError(text.error);
        setPlaces([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });
    return () => controller.abort();
  }, [coordinates, radius, category, weather, attempt, language, text.error, text.serviceMessage, budget, interests]);

  const categories: Array<{ id: PlaceCategory; label: string }> = [
    { id: "all", label: text.all },
    { id: "cafe", label: text.cafe },
    { id: "culture", label: text.culture },
  ];

  return (
    <section id="nearby-places" className="places-section" aria-labelledby="places-title">
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
          {places.slice(0, 6).map((place) => {
            const image = resolvedImages[`${place.osm_type}/${place.osm_id}`];
            const imageUrl = place.image_url ?? image?.image_url;
            const imagePageUrl = place.image_page_url ?? image?.image_page_url;
            return (
              <article className="place-row" key={`${place.osm_type}-${place.osm_id}`}>
                <div
                  className={`place-photo${imageUrl ? " place-photo--image" : " place-photo--placeholder"}`}
                  role="img"
                  aria-label={imageUrl ? `${place.name}, ${image?.image_source === "google" ? "Google Places photo" : "Wikimedia Commons photo"}` : `${place.category}: ${place.name}`}
                  style={imageUrl ? { backgroundImage: `url("${imageUrl}")` } : undefined}
                >
                  <span className="place-photo-mark" aria-hidden="true">({place.category === "Kafé" ? "C" : "M"})</span>
                </div>
                <div className="place-copy">
                  <div className="place-name-line"><h3>{place.name}</h3><span>{formatDistance(place.distance_meters, language)}</span></div>
                  <p className="place-meta">{localizeCategory(place.category, language)}{place.address ? ` · ${place.address}` : ""}</p>
                  <p className="place-reason">{place.reason}</p>
                  <p className="place-hours">{place.opening_hours ? `${text.hours}: ${place.opening_hours}` : text.noHours} · {place.fee === true ? text.feeYes : place.fee === false ? text.feeNo : text.feeUnknown}</p>
                </div>
                <div className="place-actions">
                  <a href={place.directions_url} target="_blank" rel="noreferrer">{text.directions} ↗</a>
                  <a href={place.map_url} target="_blank" rel="noreferrer">{text.map}</a>
                  {imagePageUrl ? <a href={imagePageUrl} target="_blank" rel="noreferrer">{image?.image_source === "google" ? text.googleMaps : text.photoSource} ↗</a> : null}
                  {image?.author_attributions.map((credit) => credit.url
                    ? <a key={`${credit.display_name}-${credit.url}`} href={credit.url} target="_blank" rel="noreferrer">{credit.display_name}</a>
                    : <span key={credit.display_name}>{credit.display_name}</span>)}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
      <p className="map-attribution"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">{text.attribution}</a>{provider === "geoapify" ? <> · <a href="https://www.geoapify.com/" target="_blank" rel="noreferrer">{text.poweredByGeoapify}</a></> : null}</p>
    </section>
  );
}
