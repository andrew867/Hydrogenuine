import React from "react";

export function TypingIndicator({ label = "Assistant is typing" }: { label?: string }) {
  return (
    <div
      data-testid="hg-typing-indicator"
      role="status"
      aria-live="polite"
      aria-label={label}
      style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "var(--hg-text-muted)", fontSize: 13 }}
    >
      <span>{label}</span>
      <span aria-hidden style={{ display: "inline-flex", gap: 4 }}>
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "var(--hg-text-muted)",
              animation: `hg-typing-bounce 1.2s ease-in-out ${dot * 0.15}s infinite`,
            }}
          />
        ))}
      </span>
      <style>{`
        @keyframes hg-typing-bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.45; }
          40% { transform: translateY(-3px); opacity: 1; }
        }
        @media (prefers-reduced-motion: reduce) {
          [data-testid="hg-typing-indicator"] span[aria-hidden] span { animation: none; opacity: 0.8; }
        }
      `}</style>
    </div>
  );
}
