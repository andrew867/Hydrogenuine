"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { appendReturnUrl } from "@/lib/navigationContext";
import type { SwarmRunResponse } from "@/types/hg";
import type { SwarmModalPreset } from "@/store/uiStore";
import { Icon } from "@/components/ui/Icon";
import { Button } from "@/components/ui/Button";

const WEATHER_PROVINCES = [
  "Ontario",
  "Quebec",
  "British Columbia",
  "Alberta",
  "Manitoba",
  "Saskatchewan",
  "Nova Scotia",
  "New Brunswick",
  "Newfoundland and Labrador",
  "Prince Edward Island",
];

const WEATHER_TASKS = WEATHER_PROVINCES.map((p) => `What's the weather in ${p}?`);

const CURRENT_EVENTS_TASK =
  "Research today's top current events in technology, business, and science. Each agent should cover a distinct angle and cite sources.";

export function SwarmRunModal({
  open,
  onClose,
  preset = null,
  autoNavigateToSwarm = false,
}: {
  open: boolean;
  onClose: () => void;
  preset?: SwarmModalPreset;
  autoNavigateToSwarm?: boolean;
}) {
  const router = useRouter();
  const qc = useQueryClient();
  const [mode, setMode] = useState<"task" | "tasks">("task");
  const [task, setTask] = useState("");
  const [tasksText, setTasksText] = useState("");
  const [count, setCount] = useState(3);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SwarmRunResponse | null>(null);
  const taskPreview = mode === "tasks"
    ? tasksText.split("\n").map((item) => item.trim()).filter(Boolean)
    : task.trim()
      ? Array.from({ length: count }, (_, index) => `Agent ${index + 1}: ${task.trim()}`)
      : [];

  const handleWeatherPreset = () => {
    setMode("tasks");
    setTasksText(WEATHER_TASKS.join("\n"));
  };

  const handleCurrentEventsPreset = () => {
    setMode("task");
    setTask(CURRENT_EVENTS_TASK);
    setCount(3);
  };

  useEffect(() => {
    if (!open || !preset) return;
    if (preset === "weather") handleWeatherPreset();
    if (preset === "current-events") handleCurrentEventsPreset();
  }, [open, preset]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setRunning(true);
    try {
      const res =
        mode === "task"
          ? await hgApi.runSwarm({ task: task.trim(), count })
          : await hgApi.runSwarm({
              tasks: tasksText
                .split("\n")
                .map((s) => s.trim())
                .filter(Boolean),
            });
      setResult(res);
      await qc.invalidateQueries({ queryKey: ["chats"] });
      await qc.invalidateQueries({ queryKey: ["approvals"] });
      if (autoNavigateToSwarm && res.swarm_run_id) {
        onClose();
        router.push(`/swarm/${encodeURIComponent(res.swarm_run_id)}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Swarm run failed");
    } finally {
      setRunning(false);
    }
  };

  const handleClose = () => {
    if (!running) {
      setError(null);
      setResult(null);
      setTask("");
      setTasksText("");
      setCount(3);
      onClose();
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={handleClose}
    >
      <div
        className="bg-bg border border-border rounded-2xl shadow-xl max-w-lg w-full p-5 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Run swarm</h2>
          <button
            type="button"
            className="p-2 rounded-xl hover:bg-card/60"
            onClick={handleClose}
            disabled={running}
            aria-label="Close"
          >
            <Icon name="close" className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-3">
            <div>
              <div className="text-sm font-semibold">What do you want this swarm to do?</div>
              <div className="text-xs text-muted">Start from a human prompt. Choose whether every agent gets the same brief or you want one line per agent.</div>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => setMode("task")}
                className={`rounded-2xl border px-4 py-3 text-left ${mode === "task" ? "border-accent/50 bg-accent/10" : "border-border/70 bg-bg/40 hover:bg-card/60"}`}
              >
                <div className="font-medium">Single brief</div>
                <div className="mt-1 text-xs text-muted">Broadcast one goal, let the swarm attack it in parallel.</div>
              </button>
              <button
                type="button"
                onClick={() => setMode("tasks")}
                className={`rounded-2xl border px-4 py-3 text-left ${mode === "tasks" ? "border-accent/50 bg-accent/10" : "border-border/70 bg-bg/40 hover:bg-card/60"}`}
              >
                <div className="font-medium">One brief per agent</div>
                <div className="mt-1 text-xs text-muted">Hand-craft the exact decomposition, one line per agent.</div>
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleCurrentEventsPreset}
              className="text-sm text-accent hover:underline"
              data-testid="swarm-preset-current-events"
            >
              Current events swarm (3 agents)
            </button>
            <button
              type="button"
              onClick={handleWeatherPreset}
              className="text-sm text-accent hover:underline"
              data-testid="swarm-preset-weather"
            >
              Weather job (10 provinces)
            </button>
          </div>

          {mode === "task" ? (
            <>
              <div>
                <label className="block text-sm text-muted mb-1">Brief</label>
                <textarea
                  className="w-full rounded-xl bg-card/80 border border-border/70 p-3 outline-none focus:border-accent/60 min-h-[80px]"
                  placeholder="e.g. Research the top local stories, compare sources, and summarize the signal."
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-1">Number of agents (count)</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  className="w-full rounded-xl bg-card/80 border border-border/70 p-2 outline-none focus:border-accent/60"
                  value={count}
                  onChange={(e) => setCount(parseInt(e.target.value, 10) || 3)}
                />
              </div>
            </>
          ) : (
            <div>
              <label id="swarm-tasks-label" className="block text-sm text-muted mb-1" htmlFor="swarm-tasks-input">
                Agent briefs (one per line)
              </label>
              <textarea
                id="swarm-tasks-input"
                aria-labelledby="swarm-tasks-label"
                className="w-full rounded-xl bg-card/80 border border-border/70 p-3 outline-none focus:border-accent/60 min-h-[120px] font-mono text-sm"
                placeholder="Task 1&#10;Task 2&#10;..."
                value={tasksText}
                onChange={(e) => setTasksText(e.target.value)}
                required={mode === "tasks"}
              />
            </div>
          )}

          {taskPreview.length ? (
            <div className="rounded-2xl border border-border/70 bg-card/50 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-semibold">Launch preview</div>
                <div className="text-xs text-muted">{taskPreview.length} agent{taskPreview.length === 1 ? "" : "s"}</div>
              </div>
              <div className="space-y-2 text-sm">
                {taskPreview.slice(0, 6).map((entry, index) => (
                  <div key={`${index}-${entry}`} className="rounded-xl border border-border/70 bg-bg/40 px-3 py-2">
                    {entry}
                  </div>
                ))}
                {taskPreview.length > 6 ? <div className="text-xs text-muted">+ {taskPreview.length - 6} more agent brief(s)</div> : null}
              </div>
            </div>
          ) : null}

          {error && (
            <div className="text-destructive text-sm">{error}</div>
          )}

          {result && (
            <div className="rounded-xl bg-card/80 border border-border/70 p-3 space-y-2">
              <div className="font-medium">Created {result.chat_ids.length} chat(s)</div>
              <ul className="list-disc list-inside text-sm space-y-1">
                {result.chat_ids.map((id) => (
                  <li key={id}>
                    <Link
                      href={appendReturnUrl(`/chat/${encodeURIComponent(id)}`)}
                      className="text-accent hover:underline"
                      onClick={handleClose}
                    >
                      {id.slice(0, 8)}…
                    </Link>
                  </li>
                ))}
              </ul>
              {result.swarm_run_id && (
                <p className="text-sm">
                  <Link
                    href={appendReturnUrl(`/swarm/${encodeURIComponent(result.swarm_run_id)}`)}
                    className="text-accent hover:underline"
                    onClick={handleClose}
                  >
                    Open swarm overview
                  </Link>
                </p>
              )}
              {result.approval_ids && result.approval_ids.length > 0 && (
                <p className="text-sm text-muted">
                  {result.approval_ids.length} approval(s) pending. Go to Approvals to approve.
                </p>
              )}
            </div>
          )}

          <div className="flex gap-2 justify-end">
            <Button onClick={handleClose} disabled={running}>
              Cancel
            </Button>
            <button
              type="submit"
              disabled={running}
              className="px-3 py-2 rounded-2xl border text-sm font-semibold bg-ok/15 border-ok/30 hover:bg-ok/20 disabled:opacity-50"
            >
              {running ? "Running…" : "Run swarm"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
