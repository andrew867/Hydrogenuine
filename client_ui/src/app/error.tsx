"use client";

import { ErrorState } from "hg_ui_kit";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="p-6 max-w-lg mx-auto">
      <ErrorState
        title="Application error"
        message={error.message || "An unexpected error occurred in this view."}
        requestId={error.digest}
        onRetry={reset}
      />
    </main>
  );
}
