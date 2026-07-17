import React from "react";
import { Badge } from "../components/Badge";

// A persona label on a lane. Recording only — a persona choice is a governed
// config change on the backend, not silent UI state.
export function PersonaBadge({ persona }: { persona: string }) {
  return (
    <Badge tone="info" className="hg-persona-badge">
      persona: {persona}
    </Badge>
  );
}
