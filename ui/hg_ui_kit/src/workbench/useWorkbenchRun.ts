import { useCallback, useMemo, useState } from "react";
import {
  createWorkbenchApi,
  SettingHeldError,
  type TimelinePayload,
  type WorkbenchApiOptions,
  type WorkbenchRunPayload,
} from "../lib/workbenchApi";
import type {
  ReceiptTimelineEntry,
  SubagentLaneView,
  WorkbenchProgressView,
} from "./workbenchTypes";

// Derives progress views + subagent lanes + receipt-timeline entries from the
// polled receipt chain, diffing by monotonic seq (no SSE needed). Progress events
// are observation only — this hook never authorizes anything.
export function timelineToViews(tl: TimelinePayload): {
  progress: WorkbenchProgressView[];
  lanes: SubagentLaneView[];
  entries: ReceiptTimelineEntry[];
} {
  const progress: WorkbenchProgressView[] = [];
  const laneMap = new Map<string, SubagentLaneView>();
  const entries: ReceiptTimelineEntry[] = [];
  for (const r of tl.receipts) {
    entries.push({
      receipt_id: String(r.receipt_id ?? ""),
      kind: String(r.kind ?? ""),
      seq: Number(r.seq ?? 0),
      at: String(r.at ?? ""),
    });
    if (r.kind === "progress_event") {
      const ev: WorkbenchProgressView = {
        event_id: String(r.event_id ?? r.receipt_id ?? ""),
        seq: Number(r.seq ?? 0),
        event_type: String(r.event_type ?? "model_progress"),
        subagent_lane_id: (r.subagent_lane_id as string | undefined) ?? null,
        authority: false,
      };
      progress.push(ev);
      const laneId = ev.subagent_lane_id;
      if (laneId) {
        const lane = laneMap.get(laneId) ?? {
          subagent_lane_id: laneId,
          label: laneId,
          persona: null,
          status: "active",
          events: [],
        };
        lane.events.push(ev);
        laneMap.set(laneId, lane);
      }
    }
  }
  return { progress, lanes: [...laneMap.values()], entries };
}

export type WorkbenchRunState = {
  run: WorkbenchRunPayload | null;
  timeline: TimelinePayload | null;
  lastSeq: number;
  holdReason: string | null;
  error: string | null;
};

export function useWorkbenchRun(opts: WorkbenchApiOptions = {}) {
  const api = useMemo(() => createWorkbenchApi(opts), [opts.baseUrl]);
  const [state, setState] = useState<WorkbenchRunState>({
    run: null, timeline: null, lastSeq: -1, holdReason: null, error: null,
  });

  const createRun = useCallback(async (text: string) => {
    const run = await api.createRun(text);
    const timeline = await api.getTimeline(run.run_id);
    setState((s) => ({ ...s, run, timeline, holdReason: null, error: null }));
    return run;
  }, [api]);

  const refresh = useCallback(async () => {
    setState((s) => s);
    const run = state.run;
    if (!run) return;
    const timeline = await api.getTimeline(run.run_id);
    setState((s) => ({ ...s, timeline }));
  }, [api, state.run]);

  const changeSetting = useCallback(async (
    change: { setting: string; action_class: string; old_value: string; new_value: string },
  ) => {
    if (!state.run) return;
    try {
      await api.changeSetting(state.run.run_id, change);
      setState((s) => ({ ...s, holdReason: null }));
    } catch (e) {
      if (e instanceof SettingHeldError) {
        setState((s) => ({ ...s, holdReason: e.reason }));
      } else {
        throw e;
      }
    }
    await refresh();
  }, [api, state.run, refresh]);

  return { api, state, createRun, refresh, changeSetting };
}
