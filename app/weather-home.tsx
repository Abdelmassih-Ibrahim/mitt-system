"use client";

import { useEffect, useState } from "react";

type Coordinates = {
  latitude: number;
  longitude: number;
  name: string;
};

type WeatherResponse = {
  current: {
    temperature_2m: number;
    apparent_temperature: number;
    relative_humidity_2m: number;
    precipitation: number;
    weather_code: number;
    wind_speed_10m: number;
    wind_direction_10m: number;
    is_day: number;
  };
  daily: {
    sunset: string[];
  };
};

type WeatherDescription = {
  label: string;
  icon: string;
  mood: string;
};

const STOCKHOLM: Coordinates = {
  latitude: 59.3293,
  longitude: 18.0686,
  name: "Stockholm",
};

const REFRESH_INTERVAL = 5 * 60 * 1000;
const STOCKHOLM_TIME_ZONE = "Europe/Stockholm";

function describeWeather(code: number, isDay: number): WeatherDescription {
  if (code === 0) {
    return {
      label: isDay ? "Klart och soligt" : "Klart",
      icon: isDay ? "☀️" : "🌙",
      mood: isDay ? "clear" : "night",
    };
  }
  if (code === 1) {
    return { label: "Mestadels klart", icon: isDay ? "🌤️" : "🌙", mood: "clear" };
  }
  if (code === 2) {
    return { label: "Växlande molnighet", icon: "⛅", mood: "cloud" };
  }
  if (code === 3) {
    return { label: "Mulet", icon: "☁️", mood: "cloud" };
  }
  if (code === 45 || code === 48) {
    return { label: "Dimma", icon: "🌫️", mood: "cloud" };
  }
  if (code >= 51 && code <= 67) {
    return { label: "Duggregn och regn", icon: "🌧️", mood: "rain" };
  }
  if (code >= 71 && code <= 77) {
    return { label: "Snöfall", icon: "🌨️", mood: "snow" };
  }
  if (code >= 80 && code <= 82) {
    return { label: "Regnskurar", icon: "🌦️", mood: "rain" };
  }
  if (code === 85 || code === 86) {
    return { label: "Snöbyar", icon: "🌨️", mood: "snow" };
  }
  if (code >= 95) {
    return { label: "Åska", icon: "⛈️", mood: "rain" };
  }
  return { label: "Väder på väg", icon: "🌥️", mood: "cloud" };
}

function formatTime(date: Date, options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat("sv-SE", {
    ...options,
    timeZone: STOCKHOLM_TIME_ZONE,
  }).format(date);
}

function windDirection(degrees: number) {
  const directions = ["N", "NÖ", "Ö", "SÖ", "S", "SV", "V", "NV"];
  return directions[Math.round(degrees / 45) % directions.length];
}

export default function WeatherHome() {
  const [coordinates, setCoordinates] = useState(STOCKHOLM);
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [now, setNow] = useState<Date | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    const updateClock = () => setNow(new Date());
    updateClock();
    const timer = window.setInterval(updateClock, 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let activeController: AbortController | null = null;
    let mounted = true;

    const refreshWeather = async () => {
      activeController?.abort();
      const controller = new AbortController();
      activeController = controller;
      setIsRefreshing(true);

      const url = new URL("https://api.open-meteo.com/v1/forecast");
      url.searchParams.set("latitude", String(coordinates.latitude));
      url.searchParams.set("longitude", String(coordinates.longitude));
      url.searchParams.set(
        "current",
        "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m,is_day",
      );
      url.searchParams.set("daily", "sunset");
      url.searchParams.set("timezone", "auto");
      url.searchParams.set("forecast_days", "1");

      try {
        const response = await fetch(url, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error("Weather request failed");
        }

        const data = (await response.json()) as WeatherResponse;
        if (typeof data.current?.temperature_2m !== "number") {
          throw new Error("Weather data is incomplete");
        }

        if (mounted) {
          setWeather(data);
          setLastUpdated(new Date());
          setStatusMessage("");
        }
      } catch {
        if (mounted && !controller.signal.aborted) {
          setStatusMessage("Väderdata kunde inte hämtas. Försöker igen automatiskt.");
        }
      } finally {
        if (mounted && activeController === controller) {
          setIsRefreshing(false);
        }
      }
    };

    void refreshWeather();
    const timer = window.setInterval(refreshWeather, REFRESH_INTERVAL);

    return () => {
      mounted = false;
      window.clearInterval(timer);
      activeController?.abort();
    };
  }, [coordinates, refreshToken]);

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      setStatusMessage("Platsdelning stöds inte i den här webbläsaren.");
      return;
    }

    setIsLocating(true);
    setStatusMessage("");
    navigator.geolocation.getCurrentPosition(
      ({ coords: position }) => {
        setCoordinates({
          latitude: position.latitude,
          longitude: position.longitude,
          name: "Din plats",
        });
        setIsLocating(false);
      },
      (error) => {
        setStatusMessage(
          error.code === error.PERMISSION_DENIED
            ? "Platsåtkomst nekades. Visar Stockholm i stället."
            : "Kunde inte läsa din plats. Visar Stockholm i stället.",
        );
        setIsLocating(false);
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 12000 },
    );
  };

  const time = now
    ? formatTime(now, { hour: "2-digit", minute: "2-digit" })
    : "--:--";
  const seconds = now ? formatTime(now, { second: "2-digit" }) : "--";
  const date = now
    ? formatTime(now, { weekday: "long", day: "numeric", month: "long" })
    : "Hämtar lokal tid";

  const current = weather?.current;
  const condition = current
    ? describeWeather(current.weather_code, current.is_day)
    : { label: "Hämtar vädret", icon: "◌", mood: "cloud" };
  const temperature = current ? Math.round(current.temperature_2m) : null;
  const feelsLike = current ? Math.round(current.apparent_temperature) : null;
  const sunset = weather?.daily.sunset[0]?.split("T")[1]?.slice(0, 5);
  const isWet = Boolean(
    current &&
      (current.precipitation > 0 ||
        (current.weather_code >= 51 && current.weather_code <= 82) ||
        current.weather_code >= 95),
  );
  const isCold = current ? current.apparent_temperature <= 5 : true;
  const isWindy = current ? current.wind_speed_10m >= 30 : false;

  const outfitTitle = isWet
    ? "Vattentätt före allt annat."
    : isCold
      ? "Lager på lager vinner."
      : "Klä dig för en lång dag ute.";
  const outfitText = isWet
    ? "Välj jacka med huva och skor som tål väta. Byt paraply mot en ledig hand om det blåser."
    : isCold
      ? "En varm tröja under skaljackan gör promenaden skönare. Ta gärna mössa om vinden tar i."
      : "Ta med ett extra lager så kan du stanna ute även när temperaturen skiftar.";
  const activityTitle = isWet
    ? "Gör museet till utflykten."
    : isWindy
      ? "Hitta lä bakom husen."
      : "Ta omvägen genom parken.";
  const activityText = isWet
    ? "Välj en utställning eller ett växthus och låt skuren dra förbi innan du går vidare."
    : isWindy
      ? "En skogsdunge eller en gata med lä gör promenaden mycket trevligare i dag."
      : "En kort promenad före eftermiddagskaffet kan vara dagens bästa paus.";

  return (
    <main className="survival-app">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Vädervett, startsida">
          <span className="brand-mark">V</span>
          <span>VÄDERVETT</span>
        </a>
        <div className="topbar-note" aria-live="polite">
          <span className={`live-dot${isRefreshing ? " is-refreshing" : ""}`} />
          <span>{isRefreshing ? "HÄMTAR VÄDER" : "VÄDER UPPDATERAS AUTOMATISKT"}</span>
        </div>
        <div className="header-actions">
          <span className="location-label">
            <span aria-hidden="true">⌖</span> {coordinates.name}
          </span>
          <button className="location-button" onClick={useMyLocation} disabled={isLocating}>
            <span aria-hidden="true">◎</span>
            {isLocating ? "Letar plats…" : "Använd min plats"}
          </button>
        </div>
      </header>

      <div className="page-content" id="top">
        <section className="page-intro">
          <p className="eyebrow">VÄDER MED OMTANKE</p>
          <h1>Din dag, <span>just nu.</span></h1>
          <p>En liten plan för det stora svenska vädret.</p>
        </section>

        <section
          className={`weather-hero weather-hero--${condition.mood}${current?.is_day === 0 ? " weather-hero--night" : ""}`}
          aria-label={`Aktuellt väder i ${coordinates.name}`}
        >
          <div className="weather-main">
            <p className="eyebrow eyebrow--light">VÄDRET JUST NU <span className="live-pip" /></p>
            <div className="weather-reading">
              <span className="weather-icon" aria-hidden="true">{condition.icon}</span>
              <span className="temperature-value" aria-label={temperature === null ? "Laddar temperatur" : `${temperature} grader`}>
                {temperature === null ? "--" : `${temperature}°`}
              </span>
            </div>
            <h2 className="weather-description">{condition.label}</h2>
            <p className="weather-feels">
              {feelsLike === null ? "Kollar hur det känns ute" : `Känns som ${feelsLike}°`}
              {current && current.precipitation > 0 ? ` · ${current.precipitation.toFixed(1)} mm nederbörd` : ""}
            </p>
            <div className="weather-stats">
              <div>
                <span className="stat-symbol" aria-hidden="true">↗</span>
                <span><small>VIND</small><strong>{current ? `${Math.round(current.wind_speed_10m)} km/h ${windDirection(current.wind_direction_10m)}` : "--"}</strong></span>
              </div>
              <div>
                <span className="stat-symbol" aria-hidden="true">◌</span>
                <span><small>LUFTFUKTIGHET</small><strong>{current ? `${Math.round(current.relative_humidity_2m)}%` : "--"}</strong></span>
              </div>
            </div>
          </div>

          <aside className="clock-panel" aria-label="Lokal tid i Sverige">
            <div className="clock-panel__topline">
              <span className="clock-live"><span className="clock-live-dot" /> LIVE</span>
              <span className="clock-timezone">SVENSK TID</span>
            </div>
            <div className="clock-time" aria-live="off">
              <span>{time}</span>
              <small>{seconds}</small>
            </div>
            <p className="clock-date">{date}</p>
            <div className="clock-rule" />
            <div className="sunset-row">
              <span className="sunset-icon" aria-hidden="true">◒</span>
              <span>
                <small>{current?.is_day === 0 ? "SOLEN HAR GÅTT NER" : "SOLEN GÅR NER"}</small>
                <strong>{sunset ?? "--:--"}</strong>
              </span>
            </div>
          </aside>
          <span className="hero-coordinate" aria-hidden="true">VÄDERKOLL · {coordinates.name.toUpperCase()}</span>
        </section>

        <div className="update-row" aria-live="polite">
          <span>{statusMessage || (lastUpdated ? `Senast hämtat ${formatTime(lastUpdated, { hour: "2-digit", minute: "2-digit" })}` : "Hämtar senaste väderdata…")}</span>
          <button className="refresh-button" onClick={() => setRefreshToken((value) => value + 1)} disabled={isRefreshing}>
            <span aria-hidden="true">↻</span> Uppdatera nu
          </button>
        </div>

        <section className="plan-section" aria-labelledby="plan-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">DIN VÄDERSTYRDA PLAN</p>
              <h2 id="plan-title">Gör dagen lite lättare.</h2>
            </div>
            <p className="section-aside">Små råd, anpassade efter vädret där du är.</p>
          </div>

          <div className="plan-grid">
            <article className="plan-card outfit-card">
              <div className="card-topline">
                <span className="card-number">01</span>
                <span className="card-label">KLÄDER</span>
              </div>
              <div className="card-icon outfit-icon" aria-hidden="true">↗</div>
              <h3>{outfitTitle}</h3>
              <p>{outfitText}</p>
              <div className="card-tip"><span className="tip-dot" /><span>{isWet ? "Huva slår paraply i blåst" : "Ett extra lager skadar aldrig"}</span></div>
            </article>

            <article className="plan-card activity-card">
              <div className="card-topline">
                <span className="card-number">02</span>
                <span className="card-label">GÖR NÅGOT</span>
              </div>
              <div className="card-icon activity-icon" aria-hidden="true">⌂</div>
              <h3>{activityTitle}</h3>
              <p>{activityText}</p>
              <div className="card-tip"><span className="tip-dot" /><span>{isWet ? "Inomhus · lagom äventyr" : "Ute en stund · sedan fika"}</span></div>
            </article>

            <article className="plan-card cafe-card">
              <div className="card-topline">
                <span className="card-number">03</span>
                <span className="card-label">TA EN PAUS</span>
              </div>
              <div className="card-icon cafe-icon" aria-hidden="true">☕</div>
              <h3>Gör fikat till huvudnumret.</h3>
              <p>{isWet ? "Sök skydd på ett kvarterskafé. Beställ något varmt och låt skuren passera." : "Hitta ett kafé med fönsterplats och se vädret sköta underhållningen."}</p>
              <div className="card-tip"><span className="tip-dot" /><span>Nära dig · gärna kanelbulle</span></div>
            </article>
          </div>
        </section>

        <footer className="page-footer">
          <span>VÄDERVETT <span className="footer-mark">/</span> VÄDER MED OMTANKE</span>
          <span>VÄDERDATA FRÅN <a href="https://open-meteo.com/" target="_blank" rel="noreferrer">OPEN-METEO</a> · HÄMTAS VAR 5:E MINUT</span>
        </footer>
      </div>
    </main>
  );
}