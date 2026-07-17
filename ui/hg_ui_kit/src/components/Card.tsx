import React from "react";
import { cn } from "../lib/cn";

export function Card({
  children,
  className,
  title,
}: {
  children: React.ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <section className={cn("hg-card", className)}>
      {title ? <h3 style={{ marginTop: 0 }}>{title}</h3> : null}
      {children}
    </section>
  );
}
