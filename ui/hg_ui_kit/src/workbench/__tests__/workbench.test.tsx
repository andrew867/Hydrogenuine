import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { WorkbenchShell } from "../WorkbenchShell";
import { RequestComposer } from "../RequestComposer";
import { WorkflowRunCard } from "../WorkflowRunCard";
import { ModelProgressStream } from "../ModelProgressStream";
import { SubagentLane } from "../SubagentLane";
import { ReceiptTimeline } from "../ReceiptTimeline";
import { ApprovalHoldBanner } from "../ApprovalHoldBanner";
import {
  progressEventIsObservationOnly,
  type WorkbenchRunView,
  type OperatorAuthState,
} from "../workbenchTypes";
import { containsRawToken } from "../../auth/operatorIdentity";
import type { OperatorAuthState as AuthState } from "../../auth/operatorIdentity";

const identity = {
  provider: "keycloak" as const,
  subject: "11111111-2222-3333-4444-555555555555",
  display_name: "Demo Operator",
  roles: ["hg.operator", "hg.approver"],
  assurance_level: "password" as const,
  step_up_required: false,
  step_up_satisfied: false,
  production_operator_auth: true,
  demo_local_signing: false,
};

const run: WorkbenchRunView = {
  run_id: "wbr-11111111-2222-3333-4444-555555555555",
  operator_subject: identity.subject,
  status: "in_progress",
  risk_level: "high",
  request_text: "analyze the contract",
  external_effects_enabled: false,
  subagent_lane_ids: ["lane-1"],
  artifact_ids: ["wba-abc"],
};

describe("AZW Workbench UX kit components", () => {
  it("case 20: WorkbenchShell renders authenticated state", () => {
    const state: AuthState = { status: "authenticated", identity };
    render(<WorkbenchShell authState={state}><div>run area</div></WorkbenchShell>);
    expect(screen.getByText("Agent Zero Workbench")).toBeInTheDocument();
    expect(screen.getByText("run area")).toBeInTheDocument();
  });

  it("case 21: RequestComposer disabled when unauthenticated", () => {
    const state: AuthState = { status: "unauthenticated" };
    render(<WorkbenchShell authState={state}><div>hidden</div></WorkbenchShell>);
    expect(screen.queryByText("hidden")).not.toBeInTheDocument();
    render(<RequestComposer authenticated={false} value="do it" />);
    expect(screen.getByLabelText("Workbench request")).toBeDisabled();
    expect(screen.getByRole("button", { name: /Create governed run/ })).toBeDisabled();
  });

  it("case 22: WorkflowRunCard renders risk/status + isolation", () => {
    render(<WorkflowRunCard run={run} />);
    expect(screen.getByText("in_progress")).toBeInTheDocument();
    expect(screen.getByText("risk: high")).toBeInTheDocument();
    expect(screen.getByText(/isolated · no external effects/)).toBeInTheDocument();
  });

  it("case 23: ModelProgressStream renders non-authority label", () => {
    render(<ModelProgressStream events={[
      { event_id: "e1", seq: 0, event_type: "model_progress", authority: false },
    ]} />);
    expect(screen.getByText("observation, not authority")).toBeInTheDocument();
  });

  it("case 24: SubagentLane renders persona/progress", () => {
    render(<SubagentLane lane={{
      subagent_lane_id: "lane-1", label: "Research", persona: "researcher",
      status: "active",
      events: [{ event_id: "e1", seq: 1, event_type: "subagent_progress", authority: false }],
    }} />);
    expect(screen.getByText("Research")).toBeInTheDocument();
    expect(screen.getByText("persona: researcher")).toBeInTheDocument();
    expect(screen.getByText("subagent_progress")).toBeInTheDocument();
  });

  it("case 25: ReceiptTimeline renders entries", () => {
    render(<ReceiptTimeline entries={[
      { receipt_id: "r1", kind: "run_created", seq: 0, at: "2026-07-04T00:00:00Z" },
      { receipt_id: "r2", kind: "steering_message", seq: 1, at: "2026-07-04T00:01:00Z" },
    ]} />);
    expect(screen.getByText("Run created")).toBeInTheDocument();
    expect(screen.getByText("Steering")).toBeInTheDocument();
  });

  it("ApprovalHoldBanner shows the hold reason", () => {
    render(<ApprovalHoldBanner reason="step_up_missing" setting="model_route" />);
    expect(screen.getByText("Action held")).toBeInTheDocument();
    expect(screen.getByText(/step_up_missing/)).toBeInTheDocument();
  });

  it("progress events are observation-only and carry no token", () => {
    const ev = { event_id: "e", seq: 0, event_type: "approval_required", authority: false as const };
    expect(progressEventIsObservationOnly(ev)).toBe(true);
    expect(containsRawToken({ detail: "ok" })).toBe(false);
    expect(containsRawToken({ leak: "eyJhbGciOiJSUzI1NiJ9.x.y" })).toBe(true);
  });

  it("case 26: no Workbench component imports old UI paths", () => {
    const dir = resolve(__dirname, "..");
    const files = readdirSync(dir).filter((f) => f.endsWith(".tsx") || f.endsWith(".ts"));
    const forbidden = /client_ui|operator_console|product_console|apps\/exciton|multi-?chat/;
    for (const f of files) {
      const src = readFileSync(resolve(dir, f), "utf8");
      expect(src).not.toMatch(forbidden);
      const imports = [...src.matchAll(/from\s+"([^"]+)"/g)].map((m) => m[1]);
      for (const imp of imports) {
        expect(imp.startsWith(".") || imp === "react").toBe(true);
      }
    }
  });
});
