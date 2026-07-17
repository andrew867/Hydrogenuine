export type PersonaOption = {
  fingerprint_id: string;
  name: string;
  type: string;
  source: string;
  skins: Array<{ id: string; name: string }>;
};

export type PersonaGroup = {
  key: string;
  label: string;
  personas: PersonaOption[];
};

const TYPE_LABELS: Record<string, string> = {
  canada: "Canada",
  custom: "Custom",
  culture: "Culture",
  default: "Factory",
  fictional: "Fictional",
  historical: "Historical",
  imported: "Imported",
};

function titleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1))
    .join(" ");
}

export function personaTypeLabel(type: string): string {
  const normalized = (type || "default").trim().toLowerCase();
  return TYPE_LABELS[normalized] || titleCase(normalized);
}

export function groupPersonas(personas: PersonaOption[]): PersonaGroup[] {
  const map = new Map<string, PersonaGroup>();
  for (const persona of personas) {
    const key = (persona.type || "default").trim().toLowerCase() || "default";
    const existing = map.get(key);
    if (existing) {
      existing.personas.push(persona);
      continue;
    }
    map.set(key, { key, label: personaTypeLabel(key), personas: [persona] });
  }
  return Array.from(map.values())
    .map((group) => ({
      ...group,
      personas: [...group.personas].sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
}
