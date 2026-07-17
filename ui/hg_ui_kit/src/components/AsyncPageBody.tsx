import React from "react";
import { PageSkeleton } from "./PageSkeleton";
import { ErrorState } from "./ErrorState";
import { EmptyState } from "./EmptyState";

export function AsyncPageBody({
  loading = false,
  error,
  onRetry,
  empty = false,
  emptyTitle = "Nothing here yet",
  emptyDescription = "No data to display.",
  emptyActionLabel,
  onEmptyAction,
  loadingLabel,
  children,
}: {
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyActionLabel?: string;
  onEmptyAction?: () => void;
  loadingLabel?: string;
  children: React.ReactNode;
}) {
  if (loading) {
    return <PageSkeleton label={loadingLabel} />;
  }
  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }
  if (empty) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        actionLabel={emptyActionLabel}
        onAction={onEmptyAction}
      />
    );
  }
  return <>{children}</>;
}
