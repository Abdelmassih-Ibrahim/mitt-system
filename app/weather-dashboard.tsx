"use client";

import { useEffect, useRef, useState } from "react";

type Mode = "outdoor" | "indoor" | "surprise";
type Coordinates = { latitude: number; longitude: number; name: string };
type WeatherPayload = {
  city: string;
  timezone: string;
  date: string;
  sunset: string | null;
  refreshed_at: string;
  current: {
    temperature: number;
    feels_like: number;
    humidity: number;
    precipitation: number;
    code: number;
    wind_speed: number;
    wind_direction: number;
    is_day: boolean;
  };
  weather: { label: string; icon: string; mood: string };
  survival: { score: number; level: string; summary: string };
  plan: {
    outfit_title: string;
    outfit_text: string;
    activity_title: string;
    activity_text: string;
    cafe_text: string;
    tip: string;
  };
  quest: { title: string; description: string; reward: string };
  dj: { genre: string; mood: string; soundscape: string; reason: string };
};
type Capsule = {
  id: number;
  city: string;
  temperature: number;
  condition: string;
  quest: string;
  note: string;
  saved_at: string;
};
type AudioState = { context: AudioContext; source: AudioBufferSourceNode; gain: GainNode };

const API_BASE = process.env.NEXT_PUBLIC_WEATHER_API ?? "http://127.0.0.1:8000";
const STOCKHOLM: Coordinates = { latitude: 59.3293, longitude: 18.0686, name: "Stockholm" };
const REFRESH_INTERVAL = 15 * 60 * 1000;
const PARTICLE_COUNT = 20;
const PARTICLE_POSITIONS = Array.from({ length: PARTICLE_COUNT }, (_, index) => ({
  key: index,
  style: {
    left: `${(index * 37) % 100}%`,
    top: `${(index * 53) % 100}%`,
    animationDelay: `${-(index % 8) * 0.47}s`,
    animationDuration: `${1.7 + (index % 5) * 0.31}s`,
  },
}));

function formatTime(date: Date, options: Intl.DateTimeFormatOptions, timeZone: string) {
  return new Intl.DateTimeFormat("sv-SE", { ...options, timeZone }).format(date);
}

function windDirection(degrees: number) {
  const directions = ["N", "NÖ", "Ö", "SÖ", "S", "SV", "V", "NV"];
  return directions[Math.round(degrees / 45) % directions.length];
}

function formatCapsuleDate(value: string) {
  return new Intl.DateTimeFormat("sv-SE", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function WeatherDashboard() {
  const [coordinates, setCoordinates] = useState(STOCKHOLM);
  const [weather, setWeather] = useState<WeatherPayload | null>(null);
  const [capsules, setCapsules] = useState<Capsule[]>([]);
  const [mode, setMode] = useState<Mode>("outdoor");
  const [now, setNow] = useState<Date | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSoundPlaying, setIsSoundPlaying] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [capsuleNote, setCapsuleNote] = useState("");
  const audioRef = useRef<AudioState | null>(null);

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

      const params = new URLSearchParams({
        latitude: String(coordinates.latitude),
        longitude: String(coordinates.longitude),
        city: coordinates.name,
        mode,
      });

      try {
        const response = await fetch(`${API_BASE}/api/weather?${params}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Väderdata kunde inte hämtas.");
        const data = (await response.json()) as WeatherPayload;
        if (mounted) {
          setWeather(data);
          setLastUpdated(new Date());
          setStatusMessage("");
        }
      } catch {
        if (mounted && !controller.signal.aborted) {
          setStatusMessage("Pythonvädret svarar inte ännu. Kontrollerar anslutningen igen strax.");
        }
      } finally {
        if (mounted && activeController === controller) setIsRefreshing(false);
      }
    };

    void refreshWeather();
    const timer = window.setInterval(refreshWeather, REFRESH_INTERVAL);
    return () => {
      mounted = false;
      window.clearInterval(timer);
      activeController?.abort();
    };
  }, [coordinates, mode, refreshToken]);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/api/capsules`, { cache: "no-store" })
      .then((response) => (response.ok ? response.json() as Promise<Capsule[]> : []))
      .then((data) => {
        if (active) setCapsules(data);
      })
      .catch(() => {
        if (active) setStatusMessage("Väderkapslar blir tillgängliga när Pythonservern är igång.");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => () => {
    const audio = audioRef.current;
    if (audio) {
      void audio.context.close();
      audioRef.current = null;
    }
  }, []);

  const timezone = weather?.timezone ?? "Europe/Stockholm";
  const time = now ? formatTime(now, { hour: "2-digit", minute: "2-digit" }, timezone) : "--:--";
  const seconds = now ? formatTime(now, { second: "2-digit" }, timezone) : "--";
  const date = now
    ? formatTime(now, { weekday: "long", day: "numeric", month: "long" }, timezone)
    : "Hämtar lokal tid";
  const condition = weather?.weather ?? { label: "Hämtar vädret", icon: "◌", mood: "cloud" };
  const safeMood = condition.mood.replace(/[^a-z-]/g, "");
  const isNight = weather ? !weather.current.is_day : false;

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      setStatusMessage("Platsdelning stöds inte i den här webbläsaren.");
      return;
    }
    setIsLocating(true);
    setStatusMessage("");
    navigator.geolocation.getCurrentPosition(
      ({ coords: position }) => {
        setCoordinates({ latitude: position.latitude, longitude: position.longitude, name: "Min plats" });
        setIsLocating(false);
      },
      (error) => {
        setStatusMessage(error.code === error.PERMISSION_DENIED
          ? "Platsåtkomst nekades. Visar Stockholm i stället."
          : "Kunde inte läsa platsen. Visar Stockholm i stället.");
        setIsLocating(false);
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 12000 },
    );
  };

  const saveCapsule = async () => {
    if (!weather) return;
    setIsSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/capsules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          city: weather.city,
          temperature: weather.current.temperature,
          condition: weather.weather.label,
          quest: weather.quest.title,
          note: capsuleNote,
        }),
      });
      if (!response.ok) throw new Error("Kunde inte spara kapseln.");
      const capsule = (await response.json()) as Capsule;
      setCapsules((existing) => [capsule, ...existing].slice(0, 30));
      setCapsuleNote("");
      setStatusMessage("Väderögonblicket sparades i din kapselsamling.");
    } catch {
      setStatusMessage("Kapseln kunde inte sparas. Kontrollera att Pythonservern är igång.");
    } finally {
      setIsSaving(false);
    }
  };

  const deleteCapsule = async (id: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/capsules/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Kunde inte ta bort kapseln.");
      setCapsules((existing) => existing.filter((capsule) => capsule.id !== id));
    } catch {
      setStatusMessage("Kapseln kunde inte tas bort just nu.");
    }
  };

  const toggleSoundscape = async () => {
    const activeAudio = audioRef.current;
    if (activeAudio) {
      activeAudio.gain.gain.setTargetAtTime(0, activeAudio.context.currentTime, 0.12);
      activeAudio.source.stop(activeAudio.context.currentTime + 0.5);
      audioRef.current = null;
      setIsSoundPlaying(false);
      return;
    }

    const AudioContextType = window.AudioContext;
    if (!AudioContextType) {
      setStatusMessage("Ljudlandskap stöds inte i den här webbläsaren.");
      return;
    }

    const context = new AudioContextType();
    const buffer = context.createBuffer(1, context.sampleRate * 3, context.sampleRate);
    const channel = buffer.getChannelData(0);
    let previousSample = 0;
    for (let index = 0; index < channel.length; index += 1) {
      const whiteNoise = Math.random() * 2 - 1;
      previousSample = (previousSample + 0.025 * whiteNoise) / 1.025;
      channel[index] = previousSample * 3.5;
    }

    const source = context.createBufferSource();
    const filter = context.createBiquadFilter();
    const gain = context.createGain();
    source.buffer = buffer;
    source.loop = true;
    filter.type = "lowpass";
    filter.frequency.value = condition.mood.includes("snow") ? 430 : condition.mood.includes("clear") ? 1450 : 780;
    gain.gain.value = 0;
    source.connect(filter);
    filter.connect(gain);
    gain.connect(context.destination);
    source.start();
    gain.gain.setTargetAtTime(0.045, context.currentTime, 0.7);
    audioRef.current = { context, source, gain };
    setIsSoundPlaying(true);
  };

  const current = weather?.current;
  return (
    <main className={`survival-app weather-scene--${safeMood}`}>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Vädervett, startsida">
          <span className="brand-mark">V</span><span>VÄDERVETT</span>
        </a>
        <div className="topbar-note" aria-live="polite">
          <span className={`live-dot${isRefreshing ? " is-refreshing" : ""}`} />
          <span>{isRefreshing ? "PYTHON HÄMTAR VÄDER" : "LIVE · UPPDATERAS VAR 15:E MINUT"}</span>
        </div>
        <div className="header-actions">
          <span className="location-label"><span aria-hidden="true">⌖</span>{coordinates.name}</span>
          <button className="location-button" onClick={useMyLocation} disabled={isLocating} aria-label="Använd min plats" title="Använd min plats">
            <span aria-hidden="true">◎</span>{isLocating ? "Letar plats…" : "Använd min plats"}
          </button>
        </div>
      </header>

      <div className="page-content" id="top">
        <section className="page-intro">
          <p className="eyebrow">VÄDER MED OMTANKE <span className="intro-spark">✳</span></p>
          <h1>Din dag, <span>just nu.</span></h1>
          <p>Prognosen är bara början. Resten är din lilla plan.</p>
        </section>

        <section
          className={`weather-hero weather-hero--${safeMood}${isNight ? " weather-hero--night" : ""}`}
          aria-label={`Aktuellt väder i ${weather?.city ?? coordinates.name}`}
        >
          <div className={`weather-atmosphere atmosphere--${safeMood}`} aria-hidden="true">
            <span className="weather-sun" /><span className="weather-cloud" />
            {PARTICLE_POSITIONS.map((particle) => <span className="weather-particle" key={particle.key} style={particle.style} />)}
          </div>
          <div className="weather-main">
            <p className="eyebrow eyebrow--light">VÄDRET JUST NU <span className="live-pip" /></p>
            <div className="weather-reading">
              <span className="weather-icon" aria-hidden="true">{condition.icon}</span>
              <span className="temperature-value" aria-label={current ? `${Math.round(current.temperature)} grader` : "Laddar temperatur"}>
                {current ? `${Math.round(current.temperature)}°` : "--"}
              </span>
            </div>
            <h2 className="weather-description">{condition.label}</h2>
            <p className="weather-feels">
              {current ? `Känns som ${Math.round(current.feels_like)}°` : "Väntar på färska väderdata"}
              {current && current.precipitation > 0 ? ` · ${current.precipitation.toFixed(1)} mm nederbörd` : ""}
            </p>
            <div className="weather-stats">
              <div><span className="stat-symbol" aria-hidden="true">↗</span><span><small>VIND</small><strong>{current ? `${Math.round(current.wind_speed)} km/h ${windDirection(current.wind_direction)}` : "--"}</strong></span></div>
              <div><span className="stat-symbol" aria-hidden="true">◌</span><span><small>LUFTFUKTIGHET</small><strong>{current ? `${current.humidity}%` : "--"}</strong></span></div>
            </div>
          </div>

          <aside className="clock-panel" aria-label="Lokal tid">
            <div className="clock-panel__topline">
              <span className="clock-live"><span className="clock-live-dot" /> LIVE</span>
              <span className="clock-timezone">{timezone.replaceAll("_", " ").toUpperCase()}</span>
            </div>
            <div className="clock-time" aria-live="off"><span>{time}</span><small>{seconds}</small></div>
            <p className="clock-date">{date}</p>
            <div className="clock-rule" />
            <div className="sunset-row">
              <span className="sunset-icon" aria-hidden="true">◒</span>
              <span><small>{isNight ? "SOLEN HAR GÅTT NER" : "SOLEN GÅR NER"}</small><strong>{weather?.sunset ?? "--:--"}</strong></span>
            </div>
          </aside>
          <span className="hero-coordinate" aria-hidden="true">VÄDERKOLL · {weather?.city.toUpperCase() ?? "NÄRA DIG"}</span>
        </section>

        <div className="update-row" aria-live="polite">
          <span>{statusMessage || (lastUpdated ? `Python uppdaterade vädret ${formatTime(lastUpdated, { hour: "2-digit", minute: "2-digit" }, timezone)}` : "Ansluter till väderstationen…")}</span>
          <button className="refresh-button" onClick={() => setRefreshToken((value) => value + 1)} disabled={isRefreshing}>
            <span aria-hidden="true">↻</span> Uppdatera väder
          </button>
        </div>

        <section className="survival-section" aria-labelledby="survival-title">
          <div className="survival-meter-panel">
            <div className="section-kicker"><span className="neon-chip">01 / BEREDSKAP</span><span className="section-kicker-line" /></div>
            <div className="survival-meter-heading">
              <div><p className="eyebrow">DIN DAGSFORM MOT VÄDRET</p><h2 id="survival-title">Överlevnadsnivå</h2></div>
              <div className="survival-score"><strong>{weather?.survival.score ?? "--"}</strong><span>/ 100</span></div>
            </div>
            <div className="survival-track" role="meter" aria-label="Väderutmaning" aria-valuemin={0} aria-valuemax={100} aria-valuenow={weather?.survival.score ?? 0}>
              <span style={{ width: `${weather?.survival.score ?? 0}%` }} />
            </div>
            <div className="survival-summary"><strong>{weather?.survival.level ?? "Läser av läget"}</strong><span>{weather?.survival.summary ?? "Vädret väger ihop temperatur, vind och nederbörd."}</span></div>
          </div>

          <div className="mode-panel">
            <div className="section-kicker"><span className="neon-chip neon-chip--coral">02 / DIN PLAN</span><span className="section-kicker-line" /></div>
            <p className="eyebrow">VAD KÄNNER DU FÖR?</p>
            <div className="mode-switch" role="group" aria-label="Välj din dagsplan">
              <button className={mode === "outdoor" ? "is-active" : ""} onClick={() => setMode("outdoor")} aria-pressed={mode === "outdoor"}><span>↗</span>Jag vill ut</button>
              <button className={mode === "indoor" ? "is-active" : ""} onClick={() => setMode("indoor")} aria-pressed={mode === "indoor"}><span>⌂</span>Håll mig inne</button>
              <button className={mode === "surprise" ? "is-active" : ""} onClick={() => setMode("surprise")} aria-pressed={mode === "surprise"}><span>✳</span>Överraska mig</button>
            </div>
            <p className="mode-caption">Samma väder. Helt olika sorts dag.</p>
          </div>
        </section>

        <section className="plan-section" aria-labelledby="plan-title">
          <div className="section-heading">
            <div><p className="eyebrow">DIN VÄDERSTYRDA PLAN</p><h2 id="plan-title">Gör dagen lite lättare.</h2></div>
            <p className="section-aside">Små råd, anpassade efter vädret där du är.</p>
          </div>
          <div className="plan-grid">
            <article className="plan-card outfit-card">
              <div className="card-topline"><span className="card-number">01</span><span className="card-label">KLÄDER</span></div>
              <div className="card-icon outfit-icon" aria-hidden="true">↗</div>
              <h3>{weather?.plan.outfit_title ?? "Väntar på vädret."}</h3>
              <p>{weather?.plan.outfit_text ?? "Klädrådet formar sig när den aktuella prognosen kommit fram."}</p>
              <div className="card-tip"><span className="tip-dot" /><span>{weather?.plan.tip ?? "Läser av temperatur och vind"}</span></div>
            </article>
            <article className="plan-card activity-card">
              <div className="card-topline"><span className="card-number">02</span><span className="card-label">GÖR NÅGOT</span></div>
              <div className="card-icon activity-icon" aria-hidden="true">⌂</div>
              <h3>{weather?.plan.activity_title ?? "Dagens idé är på väg."}</h3>
              <p>{weather?.plan.activity_text ?? "Välj om du vill ut, stanna inne eller bli överraskad."}</p>
              <div className="card-tip"><span className="tip-dot" /><span>{mode === "indoor" ? "Inomhus · lagom äventyr" : mode === "surprise" ? "Uppdrag: följ nyfikenheten" : "Väderstyrt · nära dig"}</span></div>
            </article>
            <article className="plan-card cafe-card">
              <div className="card-topline"><span className="card-number">03</span><span className="card-label">TA EN PAUS</span></div>
              <div className="card-icon cafe-icon" aria-hidden="true">☕</div>
              <h3>Gör fikat till huvudnumret.</h3>
              <p>{weather?.plan.cafe_text ?? "En varm paus finns i planen så snart väderdata är inne."}</p>
              <div className="card-tip"><span className="tip-dot" /><span>Nära dig · gärna kanelbulle</span></div>
            </article>
          </div>
        </section>

        <section className="quest-dj-grid" aria-label="Dagens uppdrag och vädermusik">
          <article className="quest-panel">
            <div className="section-kicker"><span className="neon-chip">03 / SIDOPPDRAG</span><span className="section-kicker-line" /></div>
            <div className="quest-heading"><span className="quest-emblem" aria-hidden="true">✳</span><div><p className="eyebrow">DAGENS LILLA ÄVENTYR</p><h2>{weather?.quest.title ?? "Ett uppdrag väntar på vädret."}</h2></div></div>
            <p className="quest-description">{weather?.quest.description ?? "När Pythonvädret har laddat får du ett mikroäventyr att ta med ut."}</p>
            <div className="quest-reward"><span aria-hidden="true">✦</span>{weather?.quest.reward ?? "+1 nyfikenhet"}</div>
          </article>

          <article className="dj-panel">
            <div className="section-kicker"><span className="neon-chip neon-chip--coral">04 / VÄDER-DJ</span><span className="section-kicker-line" /></div>
            <div className="dj-heading"><div className={`sound-bars${isSoundPlaying ? " is-playing" : ""}`} aria-hidden="true"><i /><i /><i /><i /><i /></div><div><p className="eyebrow">LJUDSPÅR FÖR JUST NU</p><h2>{weather?.dj.genre ?? "Bygger dagens ljudbild"}</h2></div></div>
            <p className="dj-soundscape">{weather?.dj.soundscape ?? "En liten ljudvärld formas av dagens prognos."}</p>
            <p className="dj-reason">{weather?.dj.reason ?? "Väder möter stämning."}</p>
            <button className={`sound-button${isSoundPlaying ? " is-playing" : ""}`} onClick={() => void toggleSoundscape()}>
              <span aria-hidden="true">{isSoundPlaying ? "Ⅱ" : "▶"}</span>{isSoundPlaying ? "Pausa ljudlandskap" : "Spela atmosfären"}
            </button>
          </article>
        </section>

        <section className="capsule-section" aria-labelledby="capsules-title">
          <div className="capsule-heading">
            <div><p className="eyebrow">EN LITEN TIDSKAPSEL</p><h2 id="capsules-title">Spara känslan i luften.</h2><p>Gör om dagens väder och uppdrag till ett minne du kan öppna senare.</p></div>
            <div className="capsule-form">
              <label htmlFor="capsule-note">En rad från dagen <span>VALFRITT</span></label>
              <div className="capsule-input-row"><input id="capsule-note" value={capsuleNote} maxLength={280} onChange={(event) => setCapsuleNote(event.target.value)} placeholder="Vad vill du minnas?" /><button onClick={() => void saveCapsule()} disabled={!weather || isSaving}>{isSaving ? "Sparar…" : "Spara väderkapsel"}<span aria-hidden="true">↗</span></button></div>
            </div>
          </div>
          <div className="capsule-list">
            {capsules.length === 0 ? (
              <div className="capsule-empty"><span aria-hidden="true">◌</span><span>Din samling väntar på sitt första väderögonblick.</span></div>
            ) : capsules.slice(0, 4).map((capsule) => (
              <article className="capsule-item" key={capsule.id}>
                <span className="capsule-date">{formatCapsuleDate(capsule.saved_at)}</span>
                <strong>{capsule.city} · {Math.round(capsule.temperature)}° · {capsule.condition}</strong>
                <span className="capsule-quest">{capsule.quest}</span>
                {capsule.note ? <span className="capsule-note">“{capsule.note}”</span> : null}
                <button className="capsule-delete" onClick={() => void deleteCapsule(capsule.id)} aria-label={`Ta bort väderkapsel från ${capsule.city}`} title="Ta bort">×</button>
              </article>
            ))}
          </div>
        </section>

        <footer className="page-footer">
          <span>VÄDERVETT <span className="footer-mark">/</span> EN PLAN FÖR VERKLIGHETEN</span>
          <span>PYTHON + <a href="https://open-meteo.com/" target="_blank" rel="noreferrer">OPEN-METEO</a> · <span className="footer-online"><i /> STATIONEN ÄR VAKEN</span></span>
        </footer>
      </div>
    </main>
  );
}
