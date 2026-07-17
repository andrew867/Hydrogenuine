import React from "react";
import { cn } from "../lib/cn";

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "primary" | "danger";
};

export function Button({ variant = "default", className, ...props }: ButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        "hg-btn",
        variant === "primary" && "hg-btn--primary",
        variant === "danger" && "hg-btn--danger",
        className,
      )}
      {...props}
    />
  );
}

export function IconButton({
  label,
  className,
  children,
  ...props
}: ButtonProps & { label: string; children: React.ReactNode }) {
  return (
    <button type="button" aria-label={label} className={cn("hg-btn", className)} {...props}>
      {children}
    </button>
  );
}
