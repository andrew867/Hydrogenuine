"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ThemeProvider, ToastProvider } from "hg_ui_kit";
import React, { useEffect } from "react";
import { useKeyRingStore, restoreKeysFromSessionStorage } from "@/store/keyRingStore";

const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5_000 } }
});

export function Providers({ children }: { children: React.ReactNode }) {
  const setOperatorKey = useKeyRingStore((s) => s.setOperatorKey);
  const setAdminKey = useKeyRingStore((s) => s.setAdminKey);
  const setServiceKey = useKeyRingStore((s) => s.setServiceKey);
  const setStepupToken = useKeyRingStore((s) => s.setStepupToken);
  const setBrowserSession = useKeyRingStore((s) => s.setBrowserSession);
  const markRestored = useKeyRingStore((s) => s.markRestored);
  useEffect(() => {
    restoreKeysFromSessionStorage(useKeyRingStore.getState, { setOperatorKey, setAdminKey, setServiceKey, setStepupToken, setBrowserSession });
    markRestored();
  }, [setOperatorKey, setAdminKey, setServiceKey, setStepupToken, setBrowserSession, markRestored]);

  return (
    <ThemeProvider defaultMode="dark" defaultDensity="comfortable">
      <ToastProvider>
        <QueryClientProvider client={client}>
          {children}
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
