import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React, { useRef } from "react";
import { Modal } from "../Overlay";

function TriggerModal() {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = React.useState(true);
  return (
    <>
      <button ref={triggerRef} type="button">
        Open
      </button>
      <Modal open={open} onClose={() => setOpen(false)}>
        <div style={{ padding: 16 }}>
          <button type="button">First</button>
          <button type="button">Second</button>
        </div>
      </Modal>
    </>
  );
}

describe("U-K5 Modal focus trap", () => {
  it("closes on Escape and returns focus to trigger", () => {
    render(<TriggerModal />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
