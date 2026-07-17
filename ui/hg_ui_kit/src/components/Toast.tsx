import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { createPortal } from "react-dom";

export type ToastItem = {
  id: string;
  message: string;
  actionId?: string;
  tone?: "default" | "success" | "danger";
};

type ToastContextValue = {
  push: (toast: Omit<ToastItem, "id">) => string;
  dismiss: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);
  const push = useCallback((toast: Omit<ToastItem, "id">) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setItems((prev) => [...prev, { ...toast, id }]);
    window.setTimeout(() => dismiss(id), 6000);
    return id;
  }, [dismiss]);
  const value = useMemo(() => ({ push, dismiss }), [push, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {typeof document !== "undefined"
        ? createPortal(
            <div
              aria-live="polite"
              style={{
                position: "fixed",
                right: 16,
                bottom: 16,
                display: "flex",
                flexDirection: "column",
                gap: 8,
                zIndex: "var(--hg-z-toast)",
              }}
            >
              {items.map((toast) => (
                <div
                  key={toast.id}
                  data-testid="hg-toast"
                  data-action-id={toast.actionId ?? ""}
                  className="hg-card"
                  style={{ minWidth: 280 }}
                >
                  <div>{toast.message}</div>
                  {toast.actionId ? (
                    <div style={{ fontSize: 12, color: "var(--hg-text-muted)", marginTop: 4 }}>
                      Action ID:{" "}
                      <code data-testid="hg-toast-action-id">{toast.actionId}</code>
                    </div>
                  ) : null}
                  <button type="button" className="hg-btn" style={{ marginTop: 8 }} onClick={() => dismiss(toast.id)}>
                    Dismiss
                  </button>
                </div>
              ))}
            </div>,
            document.body,
          )
        : null}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
