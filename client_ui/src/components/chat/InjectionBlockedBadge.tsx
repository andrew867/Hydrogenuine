"use client";

/**
 * Pack10: Shows why a message was blocked (prompt-injection policy).
 * Displays score and action only; no sensitive user content.
 */

export type InjectionAssessment = {
  score: number;
  recommended_action: string;
  indicator_ids?: string[];
  indicators?: string[];
};

type InjectionBlockedBadgeProps = {
  message?: string;
  assessment: InjectionAssessment;
  onDismiss?: () => void;
  className?: string;
};

export function InjectionBlockedBadge({
  message = "Message blocked by prompt-injection policy.",
  assessment,
  onDismiss,
  className = "",
}: InjectionBlockedBadgeProps) {
  const { score, recommended_action, indicator_ids = [] } = assessment;

  return (
    <div
      className={`rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40 px-3 py-2 text-sm ${className}`}
      role="alert"
    >
      <div className="font-medium text-amber-800 dark:text-amber-200">
        {message}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-amber-700 dark:text-amber-300">
        <span>Score: {score}</span>
        <span>Action: {recommended_action}</span>
        {indicator_ids.length > 0 && (
          <span className="font-mono">Indicators: {indicator_ids.join(", ")}</span>
        )}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="mt-2 text-xs underline text-amber-600 hover:text-amber-800 dark:text-amber-400 dark:hover:text-amber-200"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}
