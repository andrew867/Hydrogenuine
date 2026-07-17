import React from "react";
import { Button } from "./Button";

export function JumpToBottomFab({
  visible,
  onClick,
  label = "Jump to latest",
}: {
  visible: boolean;
  onClick: () => void;
  label?: string;
}) {
  if (!visible) return null;
  return (
    <Button
      type="button"
      variant="primary"
      data-testid="hg-jump-to-bottom"
      onClick={onClick}
      style={{
        position: "absolute",
        right: 16,
        bottom: 88,
        zIndex: "var(--hg-z-overlay)",
        borderRadius: 999,
        boxShadow: "var(--hg-shadow-md)",
      }}
    >
      {label}
    </Button>
  );
}
