import { AxiosError } from "axios";

// Shared helpers for surfacing the API's error envelope ({"message": str, "extra": dict}).
// Every feature that performs mutations against the API needs both: errorMessage() for a
// top-level toast, fieldErrorsFrom() to map validation errors onto the right form fields.

export function errorMessage(err: unknown): string {
  if (err instanceof AxiosError && typeof err.response?.data?.message === "string") {
    return err.response.data.message;
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
