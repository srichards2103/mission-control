import { cn } from "@/lib/utils";

/* Statuses render as a small colored dot + plain text — never a filled pill. */

export type StatusDotColor = "gray" | "amber" | "blue" | "green" | "purple" | "red";

const DOT_COLORS: Record<StatusDotColor, string> = {
  gray: "bg-muted-foreground/60",
  amber: "bg-amber-500",
  blue: "bg-blue-500",
  green: "bg-emerald-500",
  purple: "bg-violet-500",
  red: "bg-red-500",
};

export function StatusDot({
  color,
  children,
  muted = false,
  className,
}: {
  color: StatusDotColor;
  children: React.ReactNode;
  /** Render the label in muted ink (e.g. cancelled / inactive). */
  muted?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-sm whitespace-nowrap",
        muted && "text-muted-foreground",
        className,
      )}
    >
      <span aria-hidden className={cn("size-1.5 shrink-0 rounded-full", DOT_COLORS[color])} />
      {children}
    </span>
  );
}
