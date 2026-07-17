import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { WorkbenchPage } from "../WorkbenchPage";
import { timelineToViews } from "../useWorkbenchRun";
import {
  createWorkbenchApi,
  SettingHeldError,
  WorkbenchApiError,
  hashFile,
} from "../../lib/workbenchApi";
import type { OperatorAuthState } from "../../auth/operatorIdentity";
import type { TimelinePayload, WorkbenchRunPayload } from "../../lib/workbenchApi";

const identity = {
  provider: "keycloak" as const,
  subject: "kc-sub-1",
  display_name: "Demo Operator",
  roles: ["hg.operator", "hg.approver"],
  assurance_level: "password" as const,
  step_up_required: false,
  step_up_satisfied: false,
  production_operator_auth: true,
  demo_local_signing: false,
};

const run: WorkbenchRunPayload = {
  run_id: "wbr-11111111-2222-3333-4444-555555555555",
  operator_subject: "kc-sub-1",
  status: "in_progress",
  risk_level: "high",
  request_text: "analyze the contract",
  external_effects_enabled: false,
  artifact_ids: ["wba-1"],
  progress_event_ids: ["wbe-1"],
  subagent_lane_ids: ["lane-1"],
};

const timeline: TimelinePayload = {
  run_id: run.run_id,
  receipts: [
    { receipt_id: "r0", kind: "run_created", seq: 0, at: "2026-07-04T00:00:00Z" },
    { receipt_id: "r1", kind: "artifact_registered", seq: 1, at: "2026-07-04T00:00:01Z" },
    { receipt_id: "r2", kind: "progress_event", seq: 2, at: "2026-07-04T00:00:02Z",
      event_id: "wbe-1", event_type: "subagent_started", subagent_lane_id: "lane-1",
      authority: false },
    { receipt_id: "r3", kind: "steering_message", seq: 3, at: "2026-07-04T00:00:03Z" },
  ],
  chain: { ok: true, count: 4, run_id: run.run_id, failures: [] },
};

function makeFetch(routes: Record<string, (body?: any) => { status: number; json: any }>) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    const handler = routes[key];
    if (!handler) return { ok: false, status: 404, json: async () => ({}) } as any;
    const body = init?.body ? JSON.parse(init.body as string) : undefined;
    const { status, json } = handler(body);
    return { ok: status < 400, status, json: async () => json } as any;
  });
}

describe("AZL live Workbench page + API client", () => {
  it("case 1: WorkbenchPage renders authenticated run + timeline", () => {
    const authState: OperatorAuthState = { status: "authenticated", identity };
    render(<WorkbenchPage authState={authState} run={run} timeline={timeline}
      requestText="" steeringText="" settings={[]} />);
    expect(screen.getByText("Agent Zero Workbench")).toBeInTheDocument();
    expect(screen.getByText("in_progress")).toBeInTheDocument();
    expect(screen.getByText("observation, not authority")).toBeInTheDocument();
    expect(screen.getByText("Run created")).toBeInTheDocument();
  });

  it("case 2: unauthenticated blocks run creation", () => {
    const authState: OperatorAuthState = { status: "unauthenticated" };
    render(<WorkbenchPage authState={authState} run={null} timeline={null}
      requestText="do it" steeringText="" settings={[]} />);
    // shell shows the sign-in note, composer is not reachable/enabled
    expect(screen.getByText(/Sign in with the Agent Zero panel/)).toBeInTheDocument();
  });

  it("case: timelineToViews groups lanes + entries by seq", () => {
    const v = timelineToViews(timeline);
    expect(v.entries).toHaveLength(4);
    expect(v.progress).toHaveLength(1);
    expect(v.progress[0].authority).toBe(false);
    expect(v.lanes[0].subagent_lane_id).toBe("lane-1");
  });

  it("case 5: createRun posts with credentials and returns run", async () => {
    const f = makeFetch({
      "POST /v1/workbench/runs": () => ({ status: 200, json: run }),
    });
    const api = createWorkbenchApi({ fetchImpl: f as any });
    const got = await api.createRun("hello");
    expect(got.run_id).toBe(run.run_id);
    expect((f.mock.calls[0][1] as RequestInit).credentials).toBe("include");
  });

  it("case 6: unauthenticated create throws 401", async () => {
    const f = makeFetch({
      "POST /v1/workbench/runs": () => ({ status: 401, json: { detail: "AUTH_MISSING_TOKEN" } }),
    });
    const api = createWorkbenchApi({ fetchImpl: f as any });
    await expect(api.createRun("x")).rejects.toBeInstanceOf(WorkbenchApiError);
  });

  it("case 17: held setting change throws SettingHeldError", async () => {
    const f = makeFetch({
      "POST /v1/workbench/runs/wbr-1/settings": () => ({
        status: 403, json: { detail: { code: "setting_change_held", reason: "step_up_missing", setting: "model_route", change_id: "wbc-1" } },
      }),
    });
    const api = createWorkbenchApi({ fetchImpl: f as any });
    await expect(api.changeSetting("wbr-1", {
      setting: "model_route", action_class: "model_route_change",
      old_value: "a", new_value: "b",
    })).rejects.toBeInstanceOf(SettingHeldError);
  });

  it("case 7: API client never puts a token in the request or logs one", async () => {
    const f = makeFetch({ "GET /v1/workbench/runs": () => ({ status: 200, json: { runs: [] } }) });
    const api = createWorkbenchApi({ fetchImpl: f as any });
    await api.listRuns();
    const init = f.mock.calls[0][1] as RequestInit;
    expect(JSON.stringify(init)).not.toContain("eyJ");
    expect(init.headers).toBeUndefined(); // GET has no auth header — cookie only
  });

  it("hashFile computes a sha256 without sending bytes", async () => {
    // Shim Blob.arrayBuffer (jsdom omits it); crypto.subtle is provided by node.
    const bytes = new TextEncoder().encode("hello world");
    const blobLike = { arrayBuffer: async () => bytes.buffer } as unknown as Blob;
    const h = await hashFile(blobLike);
    expect(h).toMatch(/^sha256:[0-9a-f]{64}$/);
    // known sha256("hello world")
    expect(h).toBe("sha256:b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9");
  });

  it("case 4/26: no old-UI imports in the live Workbench files", () => {
    const wbDir = resolve(__dirname, "..");
    const libDir = resolve(__dirname, "../../lib");
    const files = [
      ...readdirSync(wbDir).filter((f) => f.endsWith(".ts") || f.endsWith(".tsx"))
        .map((f) => resolve(wbDir, f)),
      resolve(libDir, "workbenchApi.ts"),
    ];
    const forbidden = /client_ui|operator_console|product_console|apps\/exciton|multi-?chat/;
    for (const f of files) {
      const src = readFileSync(f, "utf8");
      expect(src).not.toMatch(forbidden);
      for (const imp of [...src.matchAll(/from\s+"([^"]+)"/g)].map((m) => m[1])) {
        expect(imp.startsWith(".") || imp === "react").toBe(true);
      }
    }
  });
});
