import { cn } from "@/lib/cn";

export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <section className={cn("rounded-3xl border border-border/70 bg-card/40 p-4 shadow-soft", className)}>{children}</section>;
}
