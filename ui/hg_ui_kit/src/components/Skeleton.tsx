import React from "react";
import { cn } from "../lib/cn";

export function Skeleton({
  width = "100%",
  height = 16,
  className,
}: {
  width?: number | string;
  height?: number | string;
  className?: string;
}) {
  return <div className={cn("hg-skeleton", className)} style={{ width, height }} aria-hidden="true" />;
}
