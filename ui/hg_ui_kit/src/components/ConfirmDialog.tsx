import React, { useId, useState } from "react";
import { Modal } from "./Overlay";
import { Button } from "./Button";
import { Input } from "./Input";

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  typedConfirm,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  typedConfirm?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const titleId = useId();
  const [typed, setTyped] = useState("");
  const canConfirm = !typedConfirm || typed === typedConfirm;

  return (
    <Modal open={open} onClose={onCancel} labelledBy={titleId}>
      <div style={{ padding: 16 }}>
        <h2 id={titleId} style={{ marginTop: 0 }}>
          {title}
        </h2>
        <p>{description}</p>
        {typedConfirm ? (
          <div style={{ marginBottom: 12 }}>
            <label>
              Type <code>{typedConfirm}</code> to confirm
              <Input
                data-testid="hg-confirm-typed-input"
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                style={{ marginTop: 8 }}
              />
            </label>
          </div>
        ) : null}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <Button onClick={onCancel}>{cancelLabel}</Button>
          <Button
            variant={destructive ? "danger" : "primary"}
            data-testid="hg-confirm-submit"
            disabled={!canConfirm}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
