"use client";

import { useEffect, useState, type FormEvent } from "react";
import type { Language, Mode, Preferences } from "../weather-types";

const interests = ["coffee", "nature", "culture", "shopping", "photography", "fitness"] as const;
const text = {
  sv: {
    title: "Ställ in din vardag",
    description: "Dina val sparas lokalt utan konto och styr råden framöver.",
    language: "Språk",
    unit: "Temperatur",
    feel: "Jag brukar",
    cold: "Frysa lätt",
    neutral: "Vara lagom",
    warm: "Bli varm",
    mode: "Helst idag",
    outdoor: "Gå ut",
    indoor: "Stanna inne",
    surprise: "Överraska mig",
    radius: "Gångradie",
    budget: "Aktivitetsbudget",
    free: "Gratis helst",
    low: "Låg",
    flexible: "Flexibel",
    interests: "Sånt jag gillar",
    coffee: "Kaffe",
    nature: "Natur",
    culture: "Kultur",
    shopping: "Shopping",
    photography: "Foto",
    fitness: "Träning",
    save: "Spara mina val",
    saving: "Sparar…",
    saved: "Dina val är sparade på den här installationen.",
    failed: "Kunde inte spara. Kontrollera att Python-API:t är igång.",
    km: "km",
  },
  en: {
    title: "Make it yours",
    description: "Preferences are stored locally without an account and shape future advice.",
    language: "Language",
    unit: "Temperature",
    feel: "I tend to",
    cold: "Feel cold",
    neutral: "Feel average",
    warm: "Feel warm",
    mode: "Today I'd rather",
    outdoor: "Go out",
    indoor: "Stay in",
    surprise: "Surprise me",
    radius: "Walking radius",
    budget: "Activity budget",
    free: "Free if possible",
    low: "Low",
    flexible: "Flexible",
    interests: "Things I enjoy",
    coffee: "Coffee",
    nature: "Nature",
    culture: "Culture",
    shopping: "Shopping",
    photography: "Photography",
    fitness: "Fitness",
    save: "Save preferences",
    saving: "Saving…",
    saved: "Your preferences are saved on this installation.",
    failed: "Could not save. Check that the Python API is running.",
    km: "km",
  },
};

export default function PreferencesPanel({
  value,
  onSave,
  isSaving,
  onSaved,
  onError,
}: {
  value: Preferences;
  onSave: (preferences: Preferences) => Promise<void>;
  isSaving: boolean;
  onSaved: (message: string) => void;
  onError: (message: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  const t = text[draft.language];

  useEffect(() => setDraft(value), [value]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await onSave(draft);
      onSaved(t.saved);
    } catch {
      onError(t.failed);
    }
  };

  return (
    <details className="preferences-panel">
      <summary><span>{t.title}</span><span className="preferences-summary-icon" aria-hidden="true">＋</span></summary>
      <form className="preferences-form" onSubmit={submit}>
        <p className="preferences-description">{t.description}</p>
        <div className="preferences-grid">
          <label className="preference-field">
            <span>{t.language}</span>
            <select value={draft.language} onChange={(event) => setDraft({ ...draft, language: event.target.value as Language })}>
              <option value="sv">Svenska</option><option value="en">English</option>
            </select>
          </label>
          <label className="preference-field">
            <span>{t.unit}</span>
            <select value={draft.temperature_unit} onChange={(event) => setDraft({ ...draft, temperature_unit: event.target.value as Preferences["temperature_unit"] })}>
              <option value="celsius">Celsius °C</option><option value="fahrenheit">Fahrenheit °F</option>
            </select>
          </label>
          <label className="preference-field">
            <span>{t.feel}</span>
            <select value={draft.thermal_sensitivity} onChange={(event) => setDraft({ ...draft, thermal_sensitivity: event.target.value as Preferences["thermal_sensitivity"] })}>
              <option value="cold">{t.cold}</option><option value="neutral">{t.neutral}</option><option value="warm">{t.warm}</option>
            </select>
          </label>
          <label className="preference-field">
            <span>{t.mode}</span>
            <select value={draft.preferred_mode} onChange={(event) => setDraft({ ...draft, preferred_mode: event.target.value as Mode })}>
              <option value="outdoor">{t.outdoor}</option><option value="indoor">{t.indoor}</option><option value="surprise">{t.surprise}</option>
            </select>
          </label>
          <label className="preference-field preference-field--range">
            <span>{t.radius}: {(draft.walking_distance_meters / 1000).toLocaleString(draft.language, { maximumFractionDigits: 1 })} {t.km}</span>
            <input type="range" min="250" max="5000" step="250" value={draft.walking_distance_meters} onChange={(event) => setDraft({ ...draft, walking_distance_meters: Number(event.target.value) })} />
          </label>
          <label className="preference-field">
            <span>{t.budget}</span>
            <select value={draft.budget} onChange={(event) => setDraft({ ...draft, budget: event.target.value as Preferences["budget"] })}>
              <option value="free">{t.free}</option><option value="low">{t.low}</option><option value="flexible">{t.flexible}</option>
            </select>
          </label>
        </div>
        <fieldset className="interest-fieldset">
          <legend>{t.interests}</legend>
          <div className="interest-options">
            {interests.map((interest) => (
              <label key={interest}>
                <input
                  type="checkbox"
                  checked={draft.interests.includes(interest)}
                  onChange={(event) => {
                    const next = event.target.checked
                      ? [...draft.interests, interest]
                      : draft.interests.filter((item) => item !== interest);
                    setDraft({ ...draft, interests: next });
                  }}
                />
                {t[interest]}
              </label>
            ))}
          </div>
        </fieldset>
        <button className="preferences-save" type="submit" disabled={isSaving}>{isSaving ? t.saving : t.save}</button>
      </form>
    </details>
  );
}
