import React from "react";
import { WorkbenchShell } from "./WorkbenchShell";
import { RequestComposer } from "./RequestComposer";
import { WorkflowRunCard } from "./WorkflowRunCard";
import { ModelProgressStream } from "./ModelProgressStream";
import { SubagentLane } from "./SubagentLane";
import { SteeringMessageBox } from "./SteeringMessageBox";
import { GovernedSettingsPanel, type GovernedSetting } from "./GovernedSettingsPanel";
import { ApprovalHoldBanner } from "./ApprovalHoldBanner";
import { ArtifactUploadPanel, type ArtifactUploadState } from "./ArtifactUploadPanel";
import { Badge } from "../components/Badge";
import { ReceiptTimeline } from "./ReceiptTimeline";
import { timelineToViews } from "./useWorkbenchRun";
import type { OperatorAuthState } from "../auth/operatorIdentity";
import type { TimelinePayload, WorkbenchRunPayload } from "../lib/workbenchApi";

// The Agent Zero Workbench page — composes the kit components against a governed
// run. Presentational + prop-driven so it renders in a browser and unit-tests
// without one. Auth-gated: run controls appear only when authenticated.
export function WorkbenchPage({
  authState,
  run,
  timeline,
  requestText,
  onRequestChange,
  onCreateRun,
  steeringText,
  onSteeringChange,
  onSendSteering,
  settings,
  onRequestSettingChange,
  holdReason,
  uploadState,
  onSelectFile,
  transport = "polling",
  submitting,
}: {
  authState: OperatorAuthState;
  run: WorkbenchRunPayload | null;
  timeline: TimelinePayload | null;
  requestText: string;
  onRequestChange?: (v: string) => void;
  onCreateRun?: (v: string) => void;
  steeringText: string;
  onSteeringChange?: (v: string) => void;
  onSendSteering?: (v: string) => void;
  settings: GovernedSetting[];
  onRequestSettingChange?: (key: string) => void;
  holdReason?: string | null;
  uploadState?: ArtifactUploadState;
  onSelectFile?: (file: File) => void;
  transport?: "stream" | "polling";
  submitting?: boolean;
}) {
  const authed = authState.status === "authenticated";
  const held = Boolean(holdReason) || run?.status === "held";
  const views = timeline ? timelineToViews(timeline) : { progress: [], lanes: [], entries: [] };
  return (
    <WorkbenchShell authState={authState}>
      <RequestComposer
        authenticated={authed}
        value={requestText}
        onChange={onRequestChange}
        onSubmit={onCreateRun}
        submitting={submitting}
      />
      {run ? (
        <div className="hg-workbench-run" data-testid="wb-run">
          <WorkflowRunCard
            run={{
              run_id: run.run_id,
              operator_subject: run.operator_subject,
              status: run.status as any,
              risk_level: run.risk_level,
              request_text: run.request_text,
              external_effects_enabled: run.external_effects_enabled,
              subagent_lane_ids: run.subagent_lane_ids,
              artifact_ids: run.artifact_ids,
            }}
          />
          {held ? <ApprovalHoldBanner reason={holdReason ?? "step-up required"} /> : null}
          <div
            className="hg-workbench-transport"
            style={{ margin: "4px 0" }}
            data-testid="wb-transport"
            data-transport={transport}
          >
            <Badge tone={transport === "stream" ? "success" : "default"}>
              {transport === "stream"
                ? "progress: live SSE stream (observation, not authority)"
                : "progress: polling fallback"}
            </Badge>
          </div>
          <ArtifactUploadPanel
            artifactIds={run.artifact_ids}
            uploadState={uploadState}
            onSelectFile={onSelectFile}
            disabled={!authed}
          />
          <ModelProgressStream events={views.progress} />
          {views.lanes.map((lane) => (
            <SubagentLane key={lane.subagent_lane_id} lane={lane} />
          ))}
          <SteeringMessageBox
            authenticated={authed}
            value={steeringText}
            onChange={onSteeringChange}
            onSend={onSendSteering}
          />
          <GovernedSettingsPanel
            settings={settings}
            onRequestChange={onRequestSettingChange}
          />
          <ReceiptTimeline entries={views.entries} />
        </div>
      ) : null}
    </WorkbenchShell>
  );
}
