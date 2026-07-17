import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  createWorkbenchApi,
  openWorkbenchStream,
  uploadArtifactBytes,
  WorkbenchApiError,
} from "../../lib/workbenchApi";
import { ArtifactUploadPanel } from "../ArtifactUploadPanel";
import { WorkbenchPage } from "../WorkbenchPage";
import type {
  OperatorAuthState,
} from "../../auth/operatorIdentity";
import type { WorkbenchRunPayload } from "../../lib/workbenchApi";

const identity = {
  provider: "keycloak" as const,
  subject: "kc-sub-1",
  display_name: "Op",
  roles: ["hg.operator"],
  assurance_level: "password" as const,
  step_up_required: false,
  step_up_satisfied: false,
  production_operator_auth: true,
  demo_local_signing: false,
};

const run: WorkbenchRunPayload = {
  run_id: "wbr-abc",
  operator_subject: "kc-sub-1",
  status: "in_progress",
  risk_level: "low",
  request_text: "x",
  external_effects_enabled: false,
  artifact_ids: ["wba-1"],
  progress_event_ids: [],
  subagent_lane_ids: [],
};

// Build a fetch whose response body is a ReadableStream over the given SSE text.
function sseFetch(text: string, status = 200) {
  const enc = new TextEncoder();
  return vi.fn(async () => {
    let sent = false;
    return {
      ok: status < 400,
      status,
      body: {
        getReader: () => ({
          read: async () => {
            if (sent) return { done: true, value: undefined };
            sent = true;
            return { done: false, value: enc.encode(text) };
          },
        }),
      },
    } as any;
  });
}

describe("WBT transport hardening — upload + SSE client", () => {
  it("uploadArtifactBytes sends multipart FormData with no JSON content-type", async () => {
    const f = vi.fn(async (_url: string, init?: RequestInit) => ({
      ok: true, status: 200,
      json: async () => ({
        artifact_id: "wba-9", run_id: "wbr-abc", filename: "a.txt",
        mime_type: "text/plain", size_bytes: 3, content_hash: "sha256:" + "0".repeat(64),
        source: "upload_bytes", stored_path_ref: "artifacts/wba-9_a.txt", label: "a.txt",
        receipt_hash: "sha256:" + "1".repeat(64), stored: true, external_storage: false,
      }),
    } as any));
    const blob = new Blob([new Uint8Array([1, 2, 3])], { type: "text/plain" });
    const res = await uploadArtifactBytes(f as any, "", "wbr-abc", blob, {
      filename: "a.txt", expectedHash: "sha256:" + "0".repeat(64), label: "a.txt",
    });
    expect(res.source).toBe("upload_bytes");
    expect(res.external_storage).toBe(false);
    const init = f.mock.calls[0][1] as RequestInit;
    expect(init.credentials).toBe("include");
    expect(init.body).toBeInstanceOf(FormData);
    // no explicit Content-Type — the browser adds the multipart boundary
    expect((init.headers as any) ?? undefined).toBeUndefined();
    const form = init.body as FormData;
    expect(form.get("expected_sha256")).toBe("sha256:" + "0".repeat(64));
    expect(form.get("file")).toBeInstanceOf(Blob);
  });

  it("upload surfaces a 413 as WorkbenchApiError(upload_too_large)", async () => {
    const f = vi.fn(async () => ({
      ok: false, status: 413, json: async () => ({ detail: "upload_too_large" }),
    } as any));
    const blob = new Blob([new Uint8Array([1])]);
    await expect(uploadArtifactBytes(f as any, "", "wbr-abc", blob))
      .rejects.toMatchObject({ status: 413, code: "upload_too_large" });
  });

  it("openWorkbenchStream parses finite SSE frames via injectable fetch", async () => {
    const text =
      'id: 0\nevent: receipt\ndata: {"seq":0,"kind":"run_created"}\n\n' +
      'id: 1\nevent: receipt\ndata: {"seq":1,"kind":"artifact_registered"}\n\n' +
      'event: end\ndata: {"authority":false}\n\n';
    const f = sseFetch(text);
    const frames: any[] = [];
    await openWorkbenchStream("wbr-abc", {
      fetchImpl: f as any, onEvent: (fr) => frames.push(fr),
    });
    const init = f.mock.calls[0][1] as RequestInit;
    expect(init.credentials).toBe("include");
    const receipts = frames.filter((fr) => fr.event === "receipt");
    expect(receipts).toHaveLength(2);
    expect(JSON.parse(receipts[0].data).seq).toBe(0);
    // the terminal frame reaffirms the stream carries no authority
    const end = frames.find((fr) => fr.event === "end");
    expect(JSON.parse(end.data).authority).toBe(false);
  });

  it("openWorkbenchStream throws on a 403 so the caller can fall back to poll", async () => {
    const f = vi.fn(async () => ({ ok: false, status: 403, body: null } as any));
    await expect(openWorkbenchStream("wbr-abc", { fetchImpl: f as any, onEvent: () => {} }))
      .rejects.toBeInstanceOf(WorkbenchApiError);
  });

  it("openStream passes since_seq through to the query", async () => {
    const f = sseFetch("event: end\ndata: {}\n\n");
    const api = createWorkbenchApi({ fetchImpl: f as any });
    await api.openStream("wbr-abc", { sinceSeq: 5, onEvent: () => {} });
    expect(f.mock.calls[0][0]).toContain("since_seq=5");
  });

  it("ArtifactUploadPanel exposes a file input and reports states", () => {
    const onSelectFile = vi.fn();
    const { rerender } = render(
      <ArtifactUploadPanel artifactIds={["wba-1"]} onSelectFile={onSelectFile} />,
    );
    const input = screen.getByLabelText("Upload artifact file") as HTMLInputElement;
    const file = new File([new Uint8Array([1, 2, 3])], "c.txt", { type: "text/plain" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(onSelectFile).toHaveBeenCalledWith(file);

    rerender(<ArtifactUploadPanel artifactIds={["wba-1"]}
      uploadState={{ status: "uploading" }} />);
    expect(screen.getByText(/Uploading bytes to local store/)).toBeInTheDocument();

    rerender(<ArtifactUploadPanel artifactIds={["wba-1"]} uploadState={{
      status: "uploaded",
      last: { filename: "c.txt", size_bytes: 3, content_hash: "sha256:" + "a".repeat(64) },
    }} />);
    expect(screen.getByText(/Stored/)).toBeInTheDocument();

    rerender(<ArtifactUploadPanel artifactIds={["wba-1"]}
      uploadState={{ status: "error", error: "upload_too_large" }} />);
    expect(screen.getByText(/upload_too_large/)).toBeInTheDocument();
  });

  it("WorkbenchPage shows the live-stream vs polling transport badge", () => {
    const authState: OperatorAuthState = { status: "authenticated", identity };
    const { rerender } = render(
      <WorkbenchPage authState={authState} run={run} timeline={null}
        requestText="" steeringText="" settings={[]} transport="stream" />,
    );
    expect(screen.getByText(/live SSE stream/)).toBeInTheDocument();
    rerender(<WorkbenchPage authState={authState} run={run} timeline={null}
      requestText="" steeringText="" settings={[]} transport="polling" />);
    expect(screen.getByText(/polling fallback/)).toBeInTheDocument();
  });

  it("no old-UI imports in the transport files", () => {
    const files = [
      resolve(__dirname, "../ArtifactUploadPanel.tsx"),
      resolve(__dirname, "../../lib/workbenchApi.ts"),
    ];
    const forbidden = /client_ui|operator_console|product_console|apps\/exciton|multi-?chat/;
    for (const file of files) {
      const src = readFileSync(file, "utf8");
      expect(src).not.toMatch(forbidden);
      for (const imp of [...src.matchAll(/from\s+"([^"]+)"/g)].map((m) => m[1])) {
        expect(imp.startsWith(".") || imp === "react").toBe(true);
      }
    }
  });
});
