import React from "react";

export type Crumb = { label: string; href?: string };

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" data-testid="hg-breadcrumbs">
      <ol style={{ display: "flex", gap: 8, listStyle: "none", padding: 0, margin: 0 }}>
        {items.map((item, index) => (
          <li key={`${item.label}-${index}`}>
            {item.href ? <a href={item.href}>{item.label}</a> : <span>{item.label}</span>}
            {index < items.length - 1 ? <span aria-hidden="true"> / </span> : null}
          </li>
        ))}
      </ol>
    </nav>
  );
}
