"use client";

import React, { useEffect, useMemo, useState } from "react";
import type { PersonaOption } from "@/lib/personaGroups";
import { groupPersonas, personaTypeLabel } from "@/lib/personaGroups";
import { getPersonaPrefs, recordPersonaRecent, togglePersonaFavorite } from "@/lib/personaPrefs";
import { Icon } from "@/components/ui/Icon";
import { Badge } from "@/components/ui/Badge";

type PersonaPickerProps = {
  personas: PersonaOption[];
  fingerprintId: string;
  skinId: string;
  onFingerprintChange: (value: string) => void;
  onSkinChange: (value: string) => void;
  allowDefault?: boolean;
  compact?: boolean;
  loading?: boolean;
};

type GroupKey = string;

export function PersonaPicker({
  personas,
  fingerprintId,
  skinId,
  onFingerprintChange,
  onSkinChange,
  allowDefault = true,
  compact = false,
  loading = false,
}: PersonaPickerProps) {
  const [query, setQuery] = useState("");
  const [prefsVersion, setPrefsVersion] = useState(0);
  const prefs = useMemo(() => {
    void prefsVersion;
    return getPersonaPrefs();
  }, [prefsVersion]);
  const selectedPersona = personas.find((persona) => persona.fingerprint_id === fingerprintId) || null;
  const grouped = useMemo(() => groupPersonas(personas), [personas]);
  const filteredGroups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const base = grouped
      .map((group) => ({
        ...group,
        personas: group.personas.filter((persona) => {
          if (!q) return true;
          return [persona.name, persona.fingerprint_id, persona.type, persona.source]
            .join(" ")
            .toLowerCase()
            .includes(q);
        }),
      }))
      .filter((group) => group.personas.length > 0);
    const byId = new Map(personas.map((persona) => [persona.fingerprint_id, persona]));
    const favoritePersonas = prefs.favorites.map((id) => byId.get(id)).filter(Boolean) as PersonaOption[];
    const recentPersonas = prefs.recent.map((id) => byId.get(id)).filter(Boolean) as PersonaOption[];
    const extras = [];
    if (favoritePersonas.length) extras.push({ key: "favorites", label: "Favorites", personas: favoritePersonas });
    if (recentPersonas.length) extras.push({ key: "recent", label: "Recent", personas: recentPersonas });
    return [...extras, ...base];
  }, [grouped, personas, prefs.favorites, prefs.recent, query]);
  const [activeGroup, setActiveGroup] = useState<GroupKey>(() => filteredGroups[0]?.key || "all");

  useEffect(() => {
    if (!filteredGroups.some((group) => group.key === activeGroup)) {
      setActiveGroup(filteredGroups[0]?.key || "all");
    }
  }, [activeGroup, filteredGroups]);

  const activeEntries = filteredGroups.find((group) => group.key === activeGroup)?.personas ?? [];
  const visibleEntries = activeEntries.length ? activeEntries : filteredGroups[0]?.personas ?? [];
  const selectedSkin = selectedPersona?.skins.find((skin) => skin.id === skinId) || null;

  const applyPersona = (persona: PersonaOption) => {
    onFingerprintChange(persona.fingerprint_id);
    onSkinChange("");
    recordPersonaRecent(persona.fingerprint_id);
    setPrefsVersion((value) => value + 1);
  };

  const toggleFavorite = (personaId: string) => {
    togglePersonaFavorite(personaId);
    setPrefsVersion((value) => value + 1);
  };

  return (
    <div className={`rounded-2xl border border-border/70 bg-card/50 ${compact ? "p-3" : "p-4"}`}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Persona workspace</div>
          <div className="text-xs text-muted">Search, preview, and switch by category.</div>
        </div>
        {selectedPersona ? <Badge tone="neutral">{personaTypeLabel(selectedPersona.type)}</Badge> : null}
      </div>

      <div className={`grid gap-3 ${compact ? "lg:grid-cols-[180px_minmax(0,1fr)]" : "lg:grid-cols-[220px_minmax(0,1fr)_280px]"}`}>
        <div className="space-y-3">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search personas"
            disabled={loading}
            className="w-full rounded-xl border border-border/70 bg-bg/50 px-3 py-2 text-sm outline-none focus:border-accent/60"
          />
          <div className="flex flex-wrap gap-2 lg:flex-col">
            {allowDefault ? (
              <button
                type="button"
                onClick={() => {
                  onFingerprintChange("");
                  onSkinChange("");
                }}
                className={`rounded-xl border px-3 py-2 text-left text-sm ${!fingerprintId ? "border-accent/50 bg-accent/10" : "border-border/70 bg-bg/40 hover:bg-card/60"}`}
              >
                Default assistant
              </button>
            ) : null}
            {loading ? (
              <div className="rounded-xl border border-dashed border-border/70 px-3 py-3 text-sm text-muted">
                Loading personas…
              </div>
            ) : null}
            {filteredGroups.map((group) => (
              <button
                key={group.key}
                type="button"
                onClick={() => setActiveGroup(group.key)}
                className={`rounded-xl border px-3 py-2 text-left text-sm ${activeGroup === group.key ? "border-accent/50 bg-accent/10" : "border-border/70 bg-bg/40 hover:bg-card/60"}`}
              >
                <div className="font-medium">{group.label}</div>
                <div className="text-[11px] text-muted">{group.personas.length} persona(s)</div>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          {loading ? (
            <div className="rounded-2xl border border-dashed border-border/70 px-4 py-8 text-sm text-muted">
              Loading personas and skins…
            </div>
          ) : (
            <div className="grid gap-2 md:grid-cols-2">
              {visibleEntries.map((persona) => {
              const isSelected = persona.fingerprint_id === fingerprintId;
              const isFavorite = prefs.favorites.includes(persona.fingerprint_id);
              return (
                <button
                  key={persona.fingerprint_id}
                  type="button"
                  onClick={() => applyPersona(persona)}
                  className={`rounded-2xl border p-3 text-left ${isSelected ? "border-accent/50 bg-accent/10" : "border-border/70 bg-bg/40 hover:bg-card/60"}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate font-medium">{persona.name}</div>
                      <div className="text-[11px] uppercase tracking-wide text-muted">
                        {personaTypeLabel(persona.type)} · {persona.source}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        toggleFavorite(persona.fingerprint_id);
                      }}
                      className="rounded-lg p-1 text-muted hover:bg-bg/50 hover:text-text"
                      aria-label={isFavorite ? "Remove favorite" : "Add favorite"}
                      title={isFavorite ? "Remove favorite" : "Add favorite"}
                    >
                      <Icon name="star" className={`h-4 w-4 ${isFavorite ? "text-accent" : ""}`} />
                    </button>
                  </div>
                  <div className="mt-2 text-xs text-muted">
                    {persona.skins.length ? `${persona.skins.length} skin(s)` : "Base fingerprint only"}
                  </div>
                </button>
              );
              })}
            </div>
          )}
          {!loading && !visibleEntries.length ? <div className="rounded-2xl border border-dashed border-border/70 px-4 py-6 text-sm text-muted">No personas match this filter.</div> : null}
        </div>

        {!compact ? (
          <div className="rounded-2xl border border-border/70 bg-bg/40 p-4">
            <div className="text-xs uppercase tracking-[0.16em] text-muted">Preview</div>
            {loading ? (
              <div className="mt-3 text-sm text-muted">Loading persona preview…</div>
            ) : selectedPersona ? (
              <div className="mt-3 space-y-3">
                <div>
                  <div className="text-lg font-semibold">{selectedPersona.name}</div>
                  <div className="text-sm text-muted">{personaTypeLabel(selectedPersona.type)} persona</div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge tone="neutral">{selectedPersona.source}</Badge>
                  <Badge tone="neutral">{selectedPersona.fingerprint_id}</Badge>
                </div>
                <div>
                  <div className="mb-2 text-xs uppercase tracking-wide text-muted">Skins</div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => onSkinChange("")}
                      className={`rounded-xl border px-3 py-2 text-sm ${!skinId ? "border-accent/50 bg-accent/10" : "border-border/70 bg-card/40 hover:bg-card/60"}`}
                    >
                      Base only
                    </button>
                    {selectedPersona.skins.map((skin) => (
                      <button
                        key={skin.id}
                        type="button"
                        onClick={() => onSkinChange(skin.id)}
                        className={`rounded-xl border px-3 py-2 text-sm ${skin.id === skinId ? "border-accent/50 bg-accent/10" : "border-border/70 bg-card/40 hover:bg-card/60"}`}
                      >
                        {skin.name}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="rounded-2xl border border-border/70 bg-card/30 px-3 py-3 text-sm text-muted">
                  {selectedSkin
                    ? `Skin active: ${selectedSkin.name}.`
                    : selectedPersona.skins.length
                      ? "Choose a skin to alter presentation without changing the base fingerprint."
                      : "This persona has no additional skins yet."}
                </div>
              </div>
            ) : (
              <div className="mt-3 text-sm text-muted">No persona selected. Use the default assistant or pick a category on the left.</div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
