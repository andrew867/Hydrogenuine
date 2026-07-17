"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/cn";

type HardNavLinkProps = React.AnchorHTMLAttributes<HTMLAnchorElement> & {
  href: string;
  replace?: boolean;
  disabled?: boolean;
};

function shouldUseBrowserNavigation(event: React.MouseEvent<HTMLAnchorElement>, target?: string) {
  if (event.button !== 0) return false;
  if (target && target !== "_self") return false;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
  return true;
}

export function HardNavLink({
  href,
  replace = false,
  disabled = false,
  className,
  onClick,
  target,
  rel,
  children,
  ...props
}: HardNavLinkProps) {
  const router = useRouter();

  const handleClick = React.useCallback(
    (event: React.MouseEvent<HTMLAnchorElement>) => {
      onClick?.(event);
      if (event.defaultPrevented || disabled) {
        event.preventDefault();
        return;
      }
      if (!shouldUseBrowserNavigation(event, target)) {
        return;
      }
      if (typeof window !== "undefined") {
        const url = new URL(href, window.location.href);
        if (url.origin !== window.location.origin) {
          return;
        }
        event.preventDefault();
        if (replace) {
          window.location.replace(url.toString());
          return;
        }
        window.location.assign(url.toString());
        return;
      }
      event.preventDefault();
      if (replace) {
        router.replace(href);
        return;
      }
      router.push(href);
    },
    [disabled, href, onClick, replace, router, target]
  );

  return (
    <a
      {...props}
      href={href}
      target={target}
      rel={rel}
      aria-disabled={disabled || undefined}
      onClick={handleClick}
      className={cn(disabled && "pointer-events-none opacity-50", className)}
    >
      {children}
    </a>
  );
}
