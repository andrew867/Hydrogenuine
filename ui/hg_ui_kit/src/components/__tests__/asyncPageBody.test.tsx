import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { AsyncPageBody } from "../AsyncPageBody";

describe("U-K11 AsyncPageBody five-state", () => {
  it("renders skeleton while loading", () => {
    render(
      <AsyncPageBody loading loadingLabel="Loading runs">
        <div>content</div>
      </AsyncPageBody>,
    );
    expect(screen.getByTestId("hg-page-skeleton")).toBeInTheDocument();
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("renders error state with retry", () => {
    const onRetry = vi.fn();
    render(
      <AsyncPageBody error="Network failed" onRetry={onRetry}>
        <div>content</div>
      </AsyncPageBody>,
    );
    expect(screen.getByTestId("hg-error-state")).toHaveTextContent("Network failed");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("renders empty state", () => {
    render(
      <AsyncPageBody
        empty
        emptyTitle="No runs"
        emptyDescription="Start a workflow to see runs here."
      >
        <div>content</div>
      </AsyncPageBody>,
    );
    expect(screen.getByTestId("hg-empty-state")).toHaveTextContent("No runs");
  });

  it("renders children on success", () => {
    render(
      <AsyncPageBody>
        <div>success body</div>
      </AsyncPageBody>,
    );
    expect(screen.getByText("success body")).toBeInTheDocument();
  });
});
