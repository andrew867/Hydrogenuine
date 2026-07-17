import React from "react";
import { Card } from "../components/Card";
import { Badge, BadgeTone } from "../components/Badge";
import { RunIsolationBadge } from "./RunIsolationBadge";
import type { WorkbenchRunView } from "./workbenchTypes";

const STATUS_TONE: Record<string, BadgeTone> = {
  created: "info",
  in_progress: "info",
  held: "warning",
  completed: "success",
  failed: "danger",
};

const RISK_TONE: Record<string, BadgeTone> = {
  low: "default",
  medium: "info",
  high: "warning",
  restricted: "danger",
  breakglass: "danger",
};

export function WorkflowRunCard({ run }: { run: WorkbenchRunView }) {
  return (
    <Card className="hg-workflow-run-card">
      <div data-testid="wb-run-card" data-run-id={run.run_id}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <code title={run.run_id}>{run.run_id.slice(0, 18)}…</code>
        <RunIsolationBadge runId={run.run_id} externalEffectsEnabled={run.external_effects_enabled} />
      </div>
      <p style={{ margin: "6px 0" }}>{run.request_text}</p>
      <div style={{ opacity: 0.75, fontSize: "0.85em" }} data-testid="wb-run-operator">
        Operator: <code>{run.operator_subject}</code>
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <span data-testid="wb-run-status">
          <Badge tone={STATUS_TONE[run.status] ?? "default"}>{run.status}</Badge>
        </span>
        <Badge tone={RISK_TONE[run.risk_level] ?? "default"}>risk: {run.risk_level}</Badge>
        {run.subagent_lane_ids.length ? (
          <Badge tone="info">{run.subagent_lane_ids.length} lane(s)</Badge>
        ) : null}
        {run.artifact_ids.length ? (
          <Badge tone="info">{run.artifact_ids.length} artifact(s)</Badge>
        ) : null}
      </div>
      </div>
    </Card>
  );
}
