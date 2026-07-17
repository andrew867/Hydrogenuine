"use client";

import React, { useCallback, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { cn } from "@/lib/cn";

type SteeringAxis = { path: string; label: string; min?: number; max?: number; helper?: string };
type SteeringGroup = { id: string; label: string; description: string; axes: SteeringAxis[] };

const STEERING_GROUPS: SteeringGroup[] = [
  {
    id: "communication",
    label: "Communication",
    description: "How the agent speaks and frames output.",
    axes: [
      { path: "communication.directness", label: "Directness" },
      { path: "communication.brevity_preference", label: "Brevity" },
      { path: "communication.tolerance_for_bullshit", label: "Noise tolerance" },
      { path: "communication.humor_deployment", label: "Humor" },
      { path: "communication.conceptual_precision_primacy", label: "Precision" },
    ],
  },
  {
    id: "reasoning",
    label: "Reasoning",
    description: "How the agent thinks through ambiguity and structure.",
    axes: [
      { path: "reasoning_style.systems_first", label: "Systems-first" },
      { path: "reasoning_style.tolerance_for_ambiguity", label: "Ambiguity tolerance" },
      { path: "reasoning_style.abstraction_to_implementation", label: "Implementation grounding" },
      { path: "reasoning_style.long_range_vision", label: "Long-range vision" },
      { path: "reasoning_style.recursive_self_reference", label: "Self-reflection" },
    ],
  },
  {
    id: "execution",
    label: "Execution",
    description: "How the agent balances quality, speed, and control.",
    axes: [
      { path: "decision_making.checkpoint_discipline", label: "Checkpoint discipline" },
      { path: "decision_making.ships_before_perfect", label: "Ship before perfect" },
      { path: "decision_making.reversibility_awareness", label: "Reversibility awareness" },
      { path: "decision_making.scope_creep_resistance", label: "Scope discipline" },
      { path: "decision_making.knowing_when_to_stop", label: "Stop at enough" },
    ],
  },
  {
    id: "attention",
    label: "Attention",
    description: "How the agent holds focus and context.",
    axes: [
      { path: "attention.hyperfocus_depth", label: "Hyperfocus depth" },
      { path: "attention.distraction_resistance_when_locked_in", label: "Distraction resistance" },
      { path: "attention.context_switching_cost", label: "Context switch cost" },
      { path: "attention.self_observation_in_real_time", label: "Self-observation" },
    ],
  },
];

export function ChatSteeringSliders({ chatId }: { chatId: string }) {
  const qc = useQueryClient();
  const [pending, setPending] = useState<Record<string, number>>({});

  const { data: traitState = { traits: {}, traitOverrides: {} } } = useQuery({
    queryKey: ["chat-traits", chatId],
    queryFn: () => hgApi.getChatTraits(chatId),
    enabled: !!chatId,
  });

  const traits = traitState?.traits ?? {};
  const traitOverrides = useMemo(() => traitState?.traitOverrides ?? {}, [traitState?.traitOverrides]);
  const activeTraitCount = useMemo(() => Object.keys(traitOverrides ?? {}).length, [traitOverrides]);

  const updateTrait = useCallback(
    async (path: string, value: number) => {
      setPending((p) => ({ ...p, [path]: value }));
      const next = { ...traitOverrides, [path]: value };
      try {
        await hgApi.putChatTraits(chatId, next);
        await qc.invalidateQueries({ queryKey: ["chat-traits", chatId] });
        await qc.invalidateQueries({ queryKey: ["chat", chatId] });
      } finally {
        setPending((p) => {
          const o = { ...p };
          delete o[path];
          return o;
        });
      }
    },
    [chatId, traitOverrides, qc]
  );

  const resetTraits = useCallback(async () => {
    setPending({});
    await hgApi.putChatTraits(chatId, {});
    await qc.invalidateQueries({ queryKey: ["chat-traits", chatId] });
    await qc.invalidateQueries({ queryKey: ["chat", chatId] });
  }, [chatId, qc]);

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-muted">Steering</div>
          <div className="text-xs text-muted">
            Runtime trait controls for this chat. {activeTraitCount ? `${activeTraitCount} overrides on top of the active persona.` : "Sliders reflect the active persona/base defaults."}
          </div>
        </div>
        <button
          type="button"
          onClick={() => void resetTraits()}
          disabled={!activeTraitCount}
          className="rounded-xl border border-border/70 px-2.5 py-1 text-xs text-muted hover:border-accent/50 hover:text-text disabled:opacity-40"
        >
          Reset
        </button>
      </div>
      <div className="space-y-4">
        {STEERING_GROUPS.map((group) => (
          <div key={group.id} className="rounded-2xl border border-border/70 bg-card/40 p-3">
            <div className="mb-3">
              <div className="text-sm font-semibold">{group.label}</div>
              <div className="text-xs text-muted">{group.description}</div>
            </div>
            <div className="space-y-3">
              {group.axes.map(({ path, label, min = 0, max = 1 }) => {
                const value = pending[path] ?? traits[path] ?? 0.5;
                return (
                  <div key={path} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted">{label}</span>
                      <span className="tabular-nums">{value.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min={min}
                      max={max}
                      step={0.05}
                      value={value}
                      onChange={(e) => updateTrait(path, parseFloat(e.target.value))}
                      className={cn("w-full h-2 rounded-full appearance-none bg-card/80", "accent-accent")}
                    />
                    <div className="text-[11px] text-muted">
                      {path in traitOverrides ? "Manual override" : "Persona/default baseline"}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
