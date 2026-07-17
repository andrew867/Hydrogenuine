import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { ConfirmDialog } from "../ConfirmDialog";

describe("U-K4 ConfirmDialog typed confirm", () => {
  it("keeps confirm disabled until typed phrase matches", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        open
        title="Delete"
        description="This cannot be undone."
        typedConfirm="DELETE"
        onConfirm={onConfirm}
        onCancel={() => {}}
        destructive
      />,
    );
    const submit = screen.getByTestId("hg-confirm-submit");
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByTestId("hg-confirm-typed-input"), { target: { value: "DELET" } });
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByTestId("hg-confirm-typed-input"), { target: { value: "DELETE" } });
    expect(submit).not.toBeDisabled();
    fireEvent.click(submit);
    expect(onConfirm).toHaveBeenCalled();
  });
});
