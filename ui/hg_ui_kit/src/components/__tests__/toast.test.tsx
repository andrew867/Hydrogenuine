import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { ToastProvider, useToast } from "../Toast";

function Probe() {
  const { push } = useToast();
  return (
    <button type="button" onClick={() => push({ message: "Saved", actionId: "act-123" })}>
      Push
    </button>
  );
}

describe("U-K6 Toast", () => {
  it("announces via aria-live and exposes action id", () => {
    render(
      <ToastProvider>
        <Probe />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Push" }));
    const toast = screen.getByTestId("hg-toast");
    expect(toast.parentElement?.getAttribute("aria-live")).toBe("polite");
    expect(screen.getByTestId("hg-toast-action-id").textContent).toBe("act-123");
  });
});
