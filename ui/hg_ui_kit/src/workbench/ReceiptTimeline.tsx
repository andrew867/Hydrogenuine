import React from "react";
import { Badge } from "../components/Badge";
import type { ReceiptTimelineEntry } from "./workbenchTypes";

const KIND_LABEL: Record<string, string> = {
  run_created: "Run created",
  artifact_registered: "Artifact",
  progress_event: "Progress",
  steering_message: "Steering",
  setting_change: "Setting change",
};

// The tamper-evident receipt timeline for a run (chained; validated server-side).
export function ReceiptTimeline({ entries }: { entries: ReceiptTimelineEntry[] }) {
  return (
    <div className="hg-receipt-timeline">
      <strong>Receipts</strong>
      <ol style={{ margin: "6px 0 0", paddingLeft: 18 }} data-testid="wb-timeline">
        {entries.map((e) => (
          <li key={e.receipt_id} data-kind={e.kind}>
            <code>#{e.seq}</code> <Badge tone="info">{KIND_LABEL[e.kind] ?? e.kind}</Badge>{" "}
            <span style={{ opacity: 0.7 }}>{e.at}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
