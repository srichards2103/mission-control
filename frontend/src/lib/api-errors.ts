import { AxiosError } from "axios";

// Shared helpers for surfacing the API's error envelope ({"message": str, "extra": dict}).
// Every feature that performs mutations against the API needs both: errorMessage() for a
// top-level toast, fieldErrorsFrom() to map validation errors onto the right form fields.

// Both keys the backend can use for a non-field validation error, keyed under the generic
// top-level message "Validation error":
//  - "__all__": Django's NON_FIELD_ERRORS key. This is the live, common path — it's what
//    full_clean() produces for a CHECK-constraint violation (e.g. "end_date >= start_date"),
//    because ValidationError.error_dict already has that key and the backend's exception
//    handler passes a dict `extra.fields` straight through (see
//    backend/mission_control/common/exception_handler.py).
//  - "non_field_errors": the rarer path — only reachable via a bare `raise ValidationError("...")`
//    (a plain string/list, not a dict), which DRF's own convention would key this way.
// Read both; prefer neither over the other (front-end code shouldn't need to know which
// path a given service took).
function nonFieldErrorsIn(fields: unknown): string[] {
  if (!fields || typeof fields !== "object") return [];
  const record = fields as Record<string, unknown>;
  const all = record.__all__;
  const nonField = record.non_field_errors;
  const combined = [...(Array.isArray(all) ? all : []), ...(Array.isArray(nonField) ? nonField : [])];
  return combined.filter((m): m is string => typeof m === "string");
}

export function errorMessage(err: unknown): string {
  if (err instanceof AxiosError && typeof err.response?.data?.message === "string") {
    const message: string = err.response.data.message;
    // A non-field validation error's top-level message is pinned to the generic
    // "Validation error" string, which on its own tells the user nothing. Prefer the
    // actual reason when present. Every other case (business-rule 400s with a specific
    // message, network errors, etc.) is unaffected.
    if (message === "Validation error") {
      const nonFieldErrors = nonFieldErrorsIn(err.response?.data?.extra?.fields);
      if (nonFieldErrors.length > 0) {
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
    if (fields && typeof fields === "object") {
      const result = { ...(fields as Record<string, string[]>) };
      // Normalise Django's "__all__" onto "non_field_errors" so every form can render
      // one predictable key regardless of which shape a given validation error arrived
      // in. Keep "__all__" itself in the result too, in case a future consumer reads it
      // directly — this only adds a key, it never removes one.
      const nonFieldErrors = nonFieldErrorsIn(fields);
      if (nonFieldErrors.length > 0) {
        result.non_field_errors = nonFieldErrors;
      }
      return result;
    }
  }
  return {};
}
