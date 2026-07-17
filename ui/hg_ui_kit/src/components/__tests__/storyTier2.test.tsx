import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import React from "react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ThemeProvider } from "../../theme/ThemeProvider";
import { EmptyState } from "../EmptyState";
import { ErrorState } from "../ErrorState";
import { TokenLineChart } from "../charts/Chart";

describe("U-S2 microcopy snapshots", () => {
  it("EmptyState and ErrorState use U0 copy patterns", () => {
    const { container: empty } = render(
      <EmptyState title="No runs yet" description="Completed runs will appear here." actionLabel="Start run" onAction={() => {}} />,
    );
    expect(empty.textContent).toContain("No runs yet");
    expect(empty.textContent).toContain("Completed runs will appear here.");

    const { container: err } = render(
      <ErrorState message="Gateway unreachable. Check VPN." requestId="req-abc" onRetry={() => {}} />,
    );
    expect(err.textContent).toContain("Gateway unreachable");
    expect(err.textContent).toContain("req-abc");
  });
});

describe("U-S3 charts wrapper", () => {
  it("renders token-colored chart in dark theme", () => {
    const { getByTestId } = render(
      <ThemeProvider defaultMode="dark">
        <TokenLineChart labels={["a", "b"]} series={[{ name: "latency", values: [1, 2] }]} />
      </ThemeProvider>,
    );
    const chart = getByTestId("hg-token-chart");
    expect(chart.querySelector("polyline")?.getAttribute("stroke")).toContain("var(--hg-accent)");
  });
});

describe("U-S4 reduced motion", () => {
  it("tokens.css sets zero motion durations under prefers-reduced-motion", () => {
    const css = readFileSync(resolve(__dirname, "../../tokens/tokens.css"), "utf8");
    expect(css).toContain("prefers-reduced-motion: reduce");
    expect(css).toContain("--hg-motion-fast: 0ms");
  });
});
