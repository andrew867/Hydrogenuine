"use client";

import React from "react";

type Name =
  | "panelLeft"
  | "panelRight"
  | "plus"
  | "search"
  | "send"
  | "refresh"
  | "copy"
  | "chevronDown"
  | "chevronUp"
  | "close"
  | "zap"
  | "file"
  | "download"
  | "archive"
  | "trash"
  | "home"
  | "star";

export function Icon({ name, className }: { name: Name; className?: string }) {
  const props = { className: "h-5 w-5 " + (className || ""), fill: "none", stroke: "currentColor" } as any;
  switch (name) {
    case "panelLeft":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M3 4h18v16H3z" />
          <path d="M9 4v16" />
        </svg>
      );
    case "panelRight":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M3 4h18v16H3z" />
          <path d="M15 4v16" />
        </svg>
      );
    case "plus":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M12 5v14" />
          <path d="M5 12h14" />
        </svg>
      );
    case "search":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
      );
    case "send":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M22 2L11 13" />
          <path d="M22 2l-7 20-4-9-9-4z" />
        </svg>
      );
    case "refresh":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M21 12a9 9 0 1 1-2.64-6.36" />
          <path d="M21 3v6h-6" />
        </svg>
      );
    case "copy":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <rect x="9" y="9" width="13" height="13" rx="1" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      );
    case "chevronDown":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M6 9l6 6 6-6" />
        </svg>
      );
    case "chevronUp":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M18 15l-6-6-6 6" />
        </svg>
      );
    case "close":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M18 6L6 18" />
          <path d="M6 6l12 12" />
        </svg>
      );
    case "zap":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
        </svg>
      );
    case "file":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <path d="M14 2v6h6" />
        </svg>
      );
    case "download":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <path d="M7 10l5 5 5-5" />
          <path d="M12 15V3" />
        </svg>
      );
    case "archive":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M3 7h18" />
          <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12" />
          <path d="M9 12h6" />
          <path d="M4 3h16v4H4z" />
        </svg>
      );
    case "trash":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M3 6h18" />
          <path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" />
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
          <path d="M10 11v6" />
          <path d="M14 11v6" />
        </svg>
      );
    case "home":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M3 11l9-8 9 8" />
          <path d="M5 10v10h14V10" />
        </svg>
      );
    case "star":
      return (
        <svg {...props} viewBox="0 0 24 24" strokeWidth="2">
          <path d="M12 3l2.9 5.88 6.5.94-4.7 4.58 1.11 6.47L12 17.77l-5.81 3.1 1.11-6.47-4.7-4.58 6.5-.94z" />
        </svg>
      );
    default:
      return null;
  }
}
