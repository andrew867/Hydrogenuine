import React from "react";
import { Badge } from "../components/Badge";
import type { WorkbenchProgressView } from "./workbenchTypes";

// Renders the model/progress event stream WITH an explicit non-authority label.
// The stream is observation only — it never authorizes an action. (Live SSE
// transport is a design handoff; this renders a polled event list.)
export function ModelProgressStream({ events }: { events: WorkbenchProgressView[] }) {
  return (
    <div className="hg-model-progress-stream">
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <strong>Progress</strong>
        <Badge tone="default" className="hg-non-authority-label">
          observation, not authority
        </Badge>
      </div>
      <ol style={{ margin: "6px 0 0", paddingLeft: 18 }}>
        {events.map((ev) => (
          <li key={ev.event_id} data-authority={String(ev.authority)}>
            <code>#{ev.seq}</code> {ev.event_type}
            {ev.persona ? ` · ${ev.persona}` : ""}
            {ev.detail ? ` — ${ev.detail}` : ""}
          </li>
        ))}
      </ol>
    </div>
  );
}
