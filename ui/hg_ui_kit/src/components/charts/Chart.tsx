import React from "react";

export type ChartSeries = { name: string; values: number[] };

const palette = [
  "var(--hg-accent)",
  "var(--hg-status-success)",
  "var(--hg-status-warning)",
  "var(--hg-status-danger)",
  "var(--hg-status-info)",
];

/** Token-colored SVG line chart wrapper (no Recharts dep in kit). */
export function TokenLineChart({
  labels,
  series,
  height = 160,
}: {
  labels: string[];
  series: ChartSeries[];
  height?: number;
}) {
  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const width = Math.max(240, labels.length * 40);
  const step = width / Math.max(1, labels.length - 1);

  return (
    <svg data-testid="hg-token-chart" width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
      {series.map((s, si) => {
        const points = s.values
          .map((v, i) => `${i * step},${height - (v / max) * (height - 20) - 10}`)
          .join(" ");
        return (
          <polyline
            key={s.name}
            fill="none"
            stroke={palette[si % palette.length]}
            strokeWidth={2}
            points={points}
          />
        );
      })}
      {labels.map((label, i) => (
        <text key={label} x={i * step} y={height - 2} fontSize={10} fill="var(--hg-text-muted)">
          {label}
        </text>
      ))}
    </svg>
  );
}
