import React from "react";
import { Card } from "../components/Card";
import { PersonaBadge } from "./PersonaBadge";
import { Badge } from "../components/Badge";
import type { SubagentLaneView } from "./workbenchTypes";

// One subagent/persona progress lane. Progress within a lane is observation only.
export function SubagentLane({ lane }: { lane: SubagentLaneView }) {
  return (
    <Card className="hg-subagent-lane" data-lane-id={lane.subagent_lane_id}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <strong>{lane.label}</strong>
        <span style={{ display: "flex", gap: 6 }}>
          {lane.persona ? <PersonaBadge persona={lane.persona} /> : null}
          <Badge tone={lane.status === "completed" ? "success" : "info"}>{lane.status}</Badge>
        </span>
      </div>
      <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
        {lane.events.map((ev) => (
          <li key={ev.event_id}>
            <code>#{ev.seq}</code> {ev.event_type}
          </li>
        ))}
      </ul>
    </Card>
  );
}
