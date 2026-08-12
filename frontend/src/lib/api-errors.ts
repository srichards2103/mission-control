import { AxiosError } from "axios";

// Shared helpers for surfacing the API's error envelope ({"message": str, "extra": dict}).
// Every feature that performs mutations against the API needs both: errorMessage() for a
// top-level toast, fieldErrorsFrom() to map validation errors onto the right form fields.

export function errorMessage(err: unknown): string {
  if (err instanceof AxiosError && typeof err.response?.data?.message === "string") {
    const message: string = err.response.data.message;
    // Non-field validation errors (e.g. Django's full_clean() raising on a CHECK
    // constraint like "end_date >= start_date") land in extra.fields.non_field_errors
    // with the top-level message pinned to the generic "Validation error" string, which
    // on its own tells the user nothing. Prefer the actual reason when present. Every
    // other case (business-rule 400s with a specific message, network errors, etc.)
    // is unaffected.
    if (message === "Validation error") {
      const nonFieldErrors = err.response?.data?.extra?.fields?.non_field_errors;
      if (Array.isArray(nonFieldErrors) && nonFieldErrors.length > 0) {
        return nonFieldErrors.join(" ");
      }
    }
    return message;
  }
  return "Something went wrong. Please try again.";
}

export function fieldErrorsFrom(err: unknown): Record<string, string[]> {
  if (err instanceof AxiosError) {
    const fields = err.response?.data?.extra?.fields;
    if (fields && typeof fields === "object") return fields as Record<string, string[]>;
  }
  return {};
}
