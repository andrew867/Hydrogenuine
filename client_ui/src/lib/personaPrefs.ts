"use client";

const STORAGE_KEY = "hg.personaPrefs.v1";

type PersonaPrefs = {
  favorites: string[];
  recent: string[];
};

function readPrefs(): PersonaPrefs {
  if (typeof window === "undefined") return { favorites: [], recent: [] };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { favorites: [], recent: [] };
    const parsed = JSON.parse(raw) as PersonaPrefs;
    return {
      favorites: Array.isArray(parsed?.favorites) ? parsed.favorites.filter(Boolean).slice(0, 12) : [],
      recent: Array.isArray(parsed?.recent) ? parsed.recent.filter(Boolean).slice(0, 12) : [],
    };
  } catch {
    return { favorites: [], recent: [] };
  }
}

function writePrefs(prefs: PersonaPrefs): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export function getPersonaPrefs(): PersonaPrefs {
  return readPrefs();
}

export function recordPersonaRecent(personaId: string): PersonaPrefs {
  const prefs = readPrefs();
  prefs.recent = [personaId, ...prefs.recent.filter((value) => value !== personaId)].slice(0, 8);
  writePrefs(prefs);
  return prefs;
}

export function togglePersonaFavorite(personaId: string): PersonaPrefs {
  const prefs = readPrefs();
  const exists = prefs.favorites.includes(personaId);
  prefs.favorites = exists
    ? prefs.favorites.filter((value) => value !== personaId)
    : [personaId, ...prefs.favorites].slice(0, 12);
  writePrefs(prefs);
  return prefs;
}
