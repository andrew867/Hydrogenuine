"use client";

import { useCallback, useState } from "react";
import { ErrorState, Button } from "hg_ui_kit";

export type ApiErrorLike = Error & {
  status?: number;
  requestId?: string;
  code?: string;
  detail?: string;
};

type ApiErrorDisplayProps = {
  error: ApiErrorLike | null;
  /** Optional endpoint for debug bundle (e.g. "GET /v1/principals"). */
  endpoint?: string;
  className?: string;
};

export function ApiErrorDisplay({ error, endpoint, className = "" }: ApiErrorDisplayProps) {
  const [copied, setCopied] = useState(false);

  const copyDebugBundle = useCallback(() => {
    if (!error) return;
    const bundle = {
      requestId: (error as ApiErrorLike).requestId ?? null,
      endpoint: endpoint ?? null,
      status: (error as ApiErrorLike).status ?? null,
      code: (error as ApiErrorLike).code ?? null,
      message: error.message,
      detail: (error as ApiErrorLike).detail ?? null,
    };
    void navigator.clipboard.writeText(JSON.stringify(bundle, null, 2)).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [error, endpoint]);

  if (!error) return null;

  const err = error as ApiErrorLike;
  const message = [err.code, error.message, err.detail].filter(Boolean).join(" — ");

  return (
    <div className={className}>
      <ErrorState title="Request failed" message={message} requestId={err.requestId ?? undefined} />
      <Button type="button" onClick={copyDebugBundle} style={{ marginTop: 8 }}>
        {copied ? "Copied" : "Copy debug bundle"}
      </Button>
    </div>
  );
}
