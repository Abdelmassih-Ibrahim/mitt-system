export type Language = "sv" | "en";
export type TemperatureUnit = "celsius" | "fahrenheit";
export type ThermalSensitivity = "cold" | "neutral" | "warm";
export type Mode = "outdoor" | "indoor" | "surprise";
export type PlaceCategory = "all" | "cafe" | "culture";

export type Coordinates = {
  latitude: number;
  longitude: number;
  name: string;
  timezone?: string;
};

export type WeatherMood = { label: string; icon: string; mood: string };
export type ForecastHour = {
  date: string;
  time: string;
  temperature: number;
  feels_like: number | null;
  precipitation_probability: number | null;
  wind_speed: number | null;
  wind_direction: number | null;
  weather: WeatherMood;
  is_day: boolean;
};
export type OutdoorWindow = {
  available: boolean;
  date: string | null;
  start: string | null;
  end: string | null;
  explanation: string;
};
export type ScoreFactor = { label: string; deduction: number; explanation: string };
export type Plan = {
  outfit_title: string;
  outfit_text: string;
  activity_title: string;
  activity_text: string;
  cafe_text: string;
  tip: string;
};
export type Quest = { title: string; description: string; reward: string };
export type WeatherDJ = { genre: string; mood: string; soundscape: string; reason: string };

export type WeatherPayload = {
  city: string;
  timezone: string;
  date: string;
  sunrise: string | null;
  sunset: string | null;
  temperature_min: number | null;
  temperature_max: number | null;
  refreshed_at: string;
  headline: string;
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
  weather: WeatherMood;
  survival: {
    score: number;
    level: string;
    summary: string;
    factors: ScoreFactor[];
    disclaimer: string;
  };
  plan: Plan;
  quest: Quest;
  plans: Record<Mode, Plan>;
  quests: Record<Mode, Quest>;
  dj: WeatherDJ;
  hourly: ForecastHour[];
  outdoor_window: OutdoorWindow;
};

export type Capsule = {
  id: number;
  city: string;
  temperature: number;
  condition: string;
  quest: string;
  note: string;
  saved_at: string;
};

export type Preferences = {
  location_name: string;
  latitude: number;
  longitude: number;
  timezone: string;
  language: Language;
  temperature_unit: TemperatureUnit;
  thermal_sensitivity: ThermalSensitivity;
  preferred_mode: Mode;
  walking_distance_meters: number;
  budget: "free" | "low" | "flexible";
  interests: Array<"coffee" | "nature" | "culture" | "shopping" | "photography" | "fitness">;
};

export type NearbyPlace = {
  osm_type: string;
  osm_id: number;
  name: string;
  category: string;
  latitude: number;
  longitude: number;
  distance_meters: number;
  address: string | null;
  opening_hours: string | null;
  fee: boolean | null;
  map_url: string;
  directions_url: string;
  reason: string;
};
