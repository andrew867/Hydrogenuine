import React, { useState } from "react";
import { IconButton } from "./Button";
import { Badge } from "./Badge";
import { Sheet } from "./Overlay";

export type NotificationItem = {
  id: string;
  title: string;
  href?: string;
  createdAt?: string | number;
};

export function NotificationBell({
  items,
  onOpenItem,
}: {
  items: NotificationItem[];
  onOpenItem?: (item: NotificationItem) => void;
}) {
  const [open, setOpen] = useState(false);
  const count = items.length;

  return (
    <>
      <div style={{ position: "relative" }}>
        <IconButton label="Notifications" onClick={() => setOpen(true)}>
          🔔
        </IconButton>
        {count > 0 ? (
          <span
            data-testid="hg-notification-count"
            style={{
              position: "absolute",
              top: -4,
              right: -4,
              background: "var(--hg-status-danger)",
              color: "#fff",
              borderRadius: 999,
              fontSize: 10,
              padding: "2px 5px",
            }}
          >
            {count}
          </span>
        ) : null}
      </div>
      <Sheet open={open} onClose={() => setOpen(false)}>
        <div style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>Notifications</h2>
          {items.length === 0 ? (
            <p style={{ color: "var(--hg-text-muted)" }}>No new notifications.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0 }}>
              {items.map((item) => (
                <li key={item.id} style={{ marginBottom: 12 }}>
                  <button
                    type="button"
                    className="hg-btn"
                    style={{ width: "100%", justifyContent: "space-between" }}
                    onClick={() => {
                      onOpenItem?.(item);
                      setOpen(false);
                    }}
                  >
                    <span>{item.title}</span>
                    <Badge tone="info">new</Badge>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Sheet>
    </>
  );
}
