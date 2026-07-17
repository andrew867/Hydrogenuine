// Agent Zero Workbench view models — display-safe mirror of the hg_workbench
// receipts (never carries tokens; session ids are shown hashed only).
export type WorkbenchRunStatus =
  | "created"
  | "in_progress"
  | "held"
  | "completed"
  | "failed";

export type WorkbenchRunView = {
  run_id: string;
  operator_subject: string;
  status: WorkbenchRunStatus;
  risk_level: string;
  request_text: string;
  external_effects_enabled: boolean; // always false in the foundation
  subagent_lane_ids: string[];
  artifact_ids: string[];
};

export type WorkbenchProgressView = {
  event_id: string;
  seq: number;
  event_type: string;
  subagent_lane_id?: string | null;
  persona?: string | null;
  detail?: string;
  authority: false; // observation, never authority
};

export type SubagentLaneView = {
  subagent_lane_id: string;
  label: string;
  persona?: string | null;
  status: string;
  events: WorkbenchProgressView[];
};

export type ReceiptTimelineEntry = {
  receipt_id: string;
  kind: string;
  seq: number;
  at: string;
};

// A progress event carries no authorization capability — the UI must never treat
// it as one. This guard makes that testable.
export function progressEventIsObservationOnly(ev: WorkbenchProgressView): boolean {
  const anyEv = ev as unknown as Record<string, unknown>;
  return (
    ev.authority === false &&
    !("permit" in anyEv) &&
    !("capability" in anyEv) &&
    !("token" in anyEv)
  );
}

// `containsRawToken` lives in ./auth/operatorIdentity (single source of truth);
// import it from there — it is re-exported through the kit barrel.
