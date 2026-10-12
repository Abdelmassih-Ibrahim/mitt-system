import type { ForecastHour, Language, OutdoorWindow, TemperatureUnit } from "../weather-types";

const copy = {
  sv: {
    eyebrow: "NÄR SKA DU GÅ UT?",
    title: "Dagens väder, timme för timme",
    window: "Bästa promenadfönstret",
    none: "Ingen lugn promenadlucka i prognosen",
    noHours: "Timprognosen kunde inte hämtas just nu.",
    daylight: "Dagsljus",
    rain: "Regnrisk",
    wind: "Vind",
    source: "Prognos från Open-Meteo. Vädermodeller uppdateras med olika intervall.",
  },
  en: {
    eyebrow: "WHEN TO HEAD OUT",
    title: "Today, hour by hour",
    window: "Best window for a walk",
    none: "No calm walking window in this forecast",
    noHours: "The hourly forecast is unavailable right now.",
    daylight: "Daylight",
    rain: "Rain chance",
    wind: "Wind",
    source: "Forecast by Open-Meteo. Weather models update at different intervals.",
  },
};

function temperatureValue(value: number, unit: TemperatureUnit) {
  const shown = unit === "fahrenheit" ? value * 9 / 5 + 32 : value;
  return `${Math.round(shown)}°`;
}

function windDirection(degrees: number | null) {
  if (degrees === null) return "";
  const directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return directions[Math.round(degrees / 45) % directions.length];
}

export default function HourlyForecast({
  hours,
  window,
  language,
  unit,
}: {
  hours: ForecastHour[];
  window: OutdoorWindow;
  language: Language;
  unit: TemperatureUnit;
}) {
  const text = copy[language];
  return (
    <section className="forecast-section" aria-labelledby="forecast-title">
      <div className="section-heading section-heading--editorial">
        <div>
          <p className="eyebrow">{text.eyebrow}</p>
          <h2 id="forecast-title">{text.title}</h2>
        </div>
        <span className="forecast-date-label">{hours.length ? `${hours.length} ${language === "sv" ? "timmar framåt" : "hours ahead"}` : ""}</span>
      </div>

      <div className={`walk-window${window.available ? " walk-window--available" : " walk-window--none"}`}>
        <span className="walk-window-icon" aria-hidden="true">{window.available ? "↗" : "⌂"}</span>
        <div>
          <strong>{window.available ? text.window : text.none}</strong>
          <p>{window.available ? `${window.start}–${window.end} · ${window.explanation}` : window.explanation}</p>
        </div>
      </div>

      {hours.length ? (
        <div className="hourly-track" aria-label={text.title}>
          {hours.map((hour) => (
            <article className="hourly-item" key={`${hour.time}-${hour.weather.mood}`}>
              <time>{hour.time}</time>
              <span className="hourly-icon" aria-hidden="true">{hour.weather.icon}</span>
              <strong>{temperatureValue(hour.temperature, unit)}</strong>
              <span className="hourly-feels">{hour.feels_like === null ? "—" : `${language === "sv" ? "Känns" : "Feels"} ${temperatureValue(hour.feels_like, unit)}`}</span>
              <span className="hourly-rain">{hour.precipitation_probability === null ? "—" : `${hour.precipitation_probability}% ${text.rain.toLocaleLowerCase(language)}`}</span>
              {hour.wind_speed !== null && hour.wind_speed >= 20 ? (
                <span className="hourly-wind">{text.wind} {Math.round(hour.wind_speed)} km/h {windDirection(hour.wind_direction)}</span>
              ) : <span className="hourly-wind">{hour.is_day ? text.daylight : ""}</span>}
            </article>
          ))}
        </div>
      ) : <p className="forecast-empty">{text.noHours}</p>}
      <p className="data-source-note">{text.source}</p>
    </section>
  );
}
