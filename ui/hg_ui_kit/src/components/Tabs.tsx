import React, { useState } from "react";

export type TabItem = { id: string; label: string; panel: React.ReactNode };

export function Tabs({ items, defaultId }: { items: TabItem[]; defaultId?: string }) {
  const [active, setActive] = useState(defaultId ?? items[0]?.id ?? "");
  const current = items.find((t) => t.id === active) ?? items[0];
  return (
    <div>
      <div role="tablist" style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {items.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={tab.id === active}
            className="hg-btn"
            onClick={() => setActive(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div role="tabpanel">{current?.panel}</div>
    </div>
  );
}
