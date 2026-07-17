import React from "react";

export type SkipToContentProps = {
  targetId?: string;
  label?: string;
};

/** WCAG 2.4.1 bypass block — first focusable element in each app shell. */
export function SkipToContent({ targetId = "main-content", label = "Skip to main content" }: SkipToContentProps) {
  return (
    <a href={`#${targetId}`} className="hg-skip-link">
      {label}
    </a>
  );
}
