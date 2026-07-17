"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";
import { getRouteCrumbs } from "@/lib/routeTaxonomy";
import { cn } from "@/lib/cn";

export function RouteBreadcrumbs() {
  const pathname = usePathname();
  const crumbs = getRouteCrumbs(pathname);
  if (!crumbs.length) return null;
  return (
    <nav aria-label="Breadcrumb" className="border-b border-border/70 bg-bg/60 backdrop-blur px-3 py-2 text-xs text-muted">
      <ol className="flex flex-wrap items-center gap-1">
        {crumbs.map((crumb, index) => {
          const last = index === crumbs.length - 1;
          return (
            <li key={`${crumb.href}-${crumb.label}`} className="flex items-center gap-1">
              {last ? (
                <span className="font-medium text-text">{crumb.label}</span>
              ) : (
                <Link href={crumb.href} className={cn("hover:text-text transition")}>
                  {crumb.label}
                </Link>
              )}
              {!last ? <span aria-hidden="true">/</span> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
