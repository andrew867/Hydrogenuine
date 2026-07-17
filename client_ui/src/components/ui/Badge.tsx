import { cn } from "@/lib/cn";

type Tone = "neutral" | "accent" | "ok" | "warning" | "danger";

const toneClass: Record<Tone, string> = {
  neutral: "bg-card/60 border-border/70 text-text",
  accent: "bg-accent/15 border-accent/30 text-accent",
  ok: "bg-ok/15 border-ok/30 text-ok",
  warning: "bg-[rgb(255,190,90)/0.15] border-[rgb(255,190,90)/0.25] text-[rgb(255,190,90)]",
  danger: "bg-danger/15 border-danger/30 text-danger"
};

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) {
  return (
    <span className={cn("inline-flex items-center px-2 py-1 rounded-xl border text-[11px] font-semibold", toneClass[tone])}>
      {children}
    </span>
  );
}
