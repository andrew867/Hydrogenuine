"use client";

import React from "react";
import { Modal } from "hg_ui_kit";
import { dismissTour, isTourDismissed } from "@/lib/tourStorage";
import { Button } from "@/components/ui/Button";

export type GuidedTourStep = {
  id: string;
  title: string;
  body: string;
};

export const DEFAULT_TOUR_STEPS: GuidedTourStep[] = [
  {
    id: "welcome",
    title: "Welcome to your workspace",
    body: "Hydrogenuine keeps chat, swarm runs, research, and approvals in one shell. This short tour shows the lanes you will use most often.",
  },
  {
    id: "lanes",
    title: "Pick a lane",
    body: "Use the workspace map to start a chat, open research, fan out a swarm, or jump to approvals. Sample prompts on the home screen create a live thread in one click.",
  },
  {
    id: "swarm",
    title: "Run a swarm",
    body: "Launch parallel agents from the sidebar zap button or the current-events preset. The swarm overview page tracks every agent without opening each chat.",
  },
  {
    id: "governance",
    title: "Stay in control",
    body: "When the runtime needs a human decision, approvals surface in chat and the notification bell. Step-up verification protects high-risk actions.",
  },
];

export function GuidedTour({
  userId,
  steps = DEFAULT_TOUR_STEPS,
  onComplete,
}: {
  userId: string;
  steps?: GuidedTourStep[];
  onComplete?: () => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [index, setIndex] = React.useState(0);

  React.useEffect(() => {
    if (!userId) return;
    if (!isTourDismissed(userId)) {
      setOpen(true);
      setIndex(0);
    }
  }, [userId]);

  const step = steps[index];
  const isLast = index >= steps.length - 1;

  const closeTour = (persist: boolean) => {
    if (persist) dismissTour(userId);
    setOpen(false);
    onComplete?.();
  };

  if (!step) return null;

  return (
    <Modal open={open} onClose={() => closeTour(true)}>
      <div
        className="max-w-lg p-6"
        data-testid="hg-guided-tour"
        role="dialog"
        aria-labelledby="hg-guided-tour-title"
        aria-describedby="hg-guided-tour-body"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          Step {index + 1} of {steps.length}
        </p>
        <h2 id="hg-guided-tour-title" className="mt-2 text-xl font-semibold">
          {step.title}
        </h2>
        <p id="hg-guided-tour-body" className="mt-3 text-sm text-muted">
          {step.body}
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            className="text-sm text-muted hover:text-text"
            data-testid="hg-guided-tour-dismiss"
            onClick={() => closeTour(true)}
          >
            Skip tour
          </button>
          <div className="flex gap-2">
            {index > 0 ? (
              <Button type="button" onClick={() => setIndex((i) => Math.max(0, i - 1))}>
                Back
              </Button>
            ) : null}
            <Button
              type="button"
              data-testid={isLast ? "hg-guided-tour-finish" : "hg-guided-tour-next"}
              onClick={() => {
                if (isLast) closeTour(true);
                else setIndex((i) => Math.min(steps.length - 1, i + 1));
              }}
            >
              {isLast ? "Finish" : "Next"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
