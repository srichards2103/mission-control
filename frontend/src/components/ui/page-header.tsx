import { cn } from "@/lib/utils";

/* Page title row: 15px semibold title on the left, actions on the right. */

export function PageHeader({
  title,
  actions,
  className,
}: {
  title: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex h-8 items-center justify-between gap-3", className)}>
      <h1 className="text-[15px] leading-none font-semibold tracking-[-0.01em]">{title}</h1>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

/* 12px muted section label, for sub-groups within a page. */
export function SectionLabel({
  children,
  className,
  ...props
}: React.ComponentProps<"h2">) {
  return (
    <h2
      className={cn("text-xs font-medium text-muted-foreground", className)}
      {...props}
    >
      {children}
    </h2>
  );
}
