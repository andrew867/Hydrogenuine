import React, { useId, useState } from "react";

export function Tooltip({ label, children }: { label: string; children: React.ReactNode }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  return (
    <span
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span aria-describedby={open ? id : undefined}>{children}</span>
      {open ? (
        <span
          id={id}
          role="tooltip"
          style={{
            position: "absolute",
            bottom: "100%",
            left: "50%",
            transform: "translateX(-50%)",
            marginBottom: 6,
            padding: "4px 8px",
            borderRadius: 6,
            background: "var(--hg-surface-raised)",
            border: "1px solid var(--hg-border)",
            fontSize: 12,
            whiteSpace: "nowrap",
            zIndex: 20,
          }}
        >
          {label}
        </span>
      ) : null}
    </span>
  );
}
