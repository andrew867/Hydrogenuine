import React from "react";
import { Button } from "../components/Button";

// Composes a user request into a governed run. Disabled unless authenticated —
// the UI mirrors the backend (which rejects unauthenticated run creation).
export function RequestComposer({
  authenticated,
  value,
  onChange,
  onSubmit,
  submitting,
}: {
  authenticated: boolean;
  value: string;
  onChange?: (v: string) => void;
  onSubmit?: (v: string) => void;
  submitting?: boolean;
}) {
  return (
    <div className="hg-request-composer">
      <textarea
        className="hg-input"
        aria-label="Workbench request"
        placeholder="Describe the task to run…"
        value={value}
        disabled={!authenticated || submitting}
        onChange={(e) => onChange?.(e.target.value)}
      />
      <Button
        data-testid="wb-create-run"
        disabled={!authenticated || !value.trim() || submitting}
        onClick={() => onSubmit?.(value)}
      >
        {submitting ? "Creating governed run…" : "Create governed run"}
      </Button>
      {!authenticated ? (
        <p className="hg-composer-disabled-reason" role="note" style={{ opacity: 0.8 }}>
          Sign in to create a run.
        </p>
      ) : null}
    </div>
  );
}
