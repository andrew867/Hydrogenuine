import { cn } from "@/lib/cn";

type Tone = "neutral" | "ok" | "danger";

const toneClass: Record<Tone, string> = {
  neutral: "bg-card/70 border-border/70 hover:border-accent/60",
  ok: "bg-ok/15 border-ok/30 hover:bg-ok/20",
  danger: "bg-danger/15 border-danger/30 hover:bg-danger/20"
};

export function Button({
  children,
  onClick,
  disabled,
  tone = "neutral",
  className,
  type = "button"
}: {
  children: React.ReactNode;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  disabled?: boolean;
  tone?: Tone;
  className?: string;
  type?: "button" | "submit" | "reset";
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "px-3 py-2 rounded-2xl border text-sm font-semibold active:scale-[0.99] transition",
        toneClass[tone],
        disabled ? "opacity-50 cursor-not-allowed" : "",
        className
      )}
    >
      {children}
    </button>
  );
}
