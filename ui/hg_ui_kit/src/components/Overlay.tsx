import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { getFocusable, trapFocus } from "../lib/focusTrap";

export type OverlayProps = {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  labelledBy?: string;
  className?: string;
  position?: "center" | "right" | "bottom";
};

export function Overlay({
  open,
  onClose,
  children,
  labelledBy,
  className,
  position = "center",
}: OverlayProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    triggerRef.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const focusables = panel ? getFocusable(panel) : [];
    focusables[0]?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (panel) trapFocus(panel, event);
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      triggerRef.current?.focus();
    };
  }, [open, onClose]);

  if (!open || typeof document === "undefined") return null;

  const positionStyle: React.CSSProperties =
    position === "right"
      ? { justifyContent: "flex-end" }
      : position === "bottom"
        ? { alignItems: "flex-end" }
        : { alignItems: "center", justifyContent: "center" };

  return createPortal(
    <div
      className={className}
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--hg-surface-overlay)",
        display: "flex",
        zIndex: "var(--hg-z-modal)",
        ...positionStyle,
      }}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        style={{
          background: "var(--hg-surface-raised)",
          border: "1px solid var(--hg-border)",
          borderRadius: "var(--hg-radius-md)",
          maxHeight: "90vh",
          overflow: "auto",
          margin: position === "right" ? 0 : 16,
          width: position === "right" ? "min(480px, 100%)" : "min(640px, 100%)",
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}

export function Modal(props: Omit<OverlayProps, "position">) {
  return <Overlay {...props} position="center" />;
}

export function Sheet(props: Omit<OverlayProps, "position">) {
  return <Overlay {...props} position="right" />;
}

export function Drawer(props: Omit<OverlayProps, "position">) {
  return <Overlay {...props} position="bottom" />;
}
