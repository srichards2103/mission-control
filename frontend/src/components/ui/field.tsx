import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";

/* Form field: 12px muted label above the control, field errors underneath. */

export function Field({
  label,
  htmlFor,
  errors,
  children,
  className,
}: {
  label: React.ReactNode;
  htmlFor?: string;
  /** DRF-style list of messages for this field; joined with spaces. */
  errors?: string[];
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {errors && errors.length > 0 && <FieldError>{errors.join(" ")}</FieldError>}
    </div>
  );
}

export function FieldError({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="text-xs text-destructive">
      {children}
    </p>
  );
}
