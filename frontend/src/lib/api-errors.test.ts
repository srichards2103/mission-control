import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/testing/server";
import { api } from "./api-client";
import { errorMessage, fieldErrorsFrom, rowErrorsFrom } from "./api-errors";

// Drives a real request through the real axios client and MSW so we get a genuine
// AxiosError, rather than hand-constructing one (which risks not matching the shape
// axios actually produces).
async function captureError(status: number, body: Record<string, unknown>): Promise<unknown> {
  server.use(http.get("/api/v1/probe/", () => HttpResponse.json(body, { status })));
  try {
    await api.get("/probe/");
  } catch (err) {
    return err;
  }
  throw new Error("expected the request to reject");
}

describe("errorMessage", () => {
  it("unwraps the live __all__ shape (Django's NON_FIELD_ERRORS key, the common CHECK-constraint path)", async () => {
    // Exact payload the real backend returns for end_date < start_date (see
    // backend/mission_control/common/exception_handler.py: full_clean() raises a dict-
    // keyed ValidationError, which passes straight through under "__all__").
    const err = await captureError(400, {
      message: "Validation error",
      extra: { fields: { __all__: ["Constraint “mission_dates_ordered” is violated."] } },
    });
    expect(errorMessage(err)).toBe("Constraint “mission_dates_ordered” is violated.");
  });

  it("unwraps the non_field_errors shape (the rarer bare-string ValidationError path)", async () => {
    const err = await captureError(400, {
      message: "Validation error",
      extra: { fields: { non_field_errors: ["Some other non-field reason."] } },
    });
    expect(errorMessage(err)).toBe("Some other non-field reason.");
  });

  it("leaves a specific business-rule message untouched even alongside non-field fields", async () => {
    const err = await captureError(400, {
      message: "You cannot modify your own account.",
      extra: { fields: { __all__: ["irrelevant"] } },
    });
    expect(errorMessage(err)).toBe("You cannot modify your own account.");
  });

  it("returns the generic message unchanged when there are no non-field errors to unwrap", async () => {
    const err = await captureError(400, {
      message: "Validation error",
      extra: { fields: { name: ["This field is required."] } },
    });
    expect(errorMessage(err)).toBe("Validation error");
  });

  it("treats an empty __all__ array as absent and falls back to the generic message", async () => {
    const err = await captureError(400, { message: "Validation error", extra: { fields: { __all__: [] } } });
    expect(errorMessage(err)).toBe("Validation error");
  });

  it("falls back to the generic client message for a network error with no response body", async () => {
    server.use(http.get("/api/v1/probe/", () => HttpResponse.error()));
    let err: unknown;
    try {
      await api.get("/probe/");
    } catch (e) {
      err = e;
    }
    expect(errorMessage(err)).toBe("Something went wrong. Please try again.");
  });
});

describe("fieldErrorsFrom", () => {
  it("normalises __all__ onto non_field_errors, keeping the original __all__ key too", async () => {
    const err = await captureError(400, {
      message: "Validation error",
      extra: { fields: { __all__: ["Constraint “mission_dates_ordered” is violated."] } },
    });
    expect(fieldErrorsFrom(err)).toEqual({
      __all__: ["Constraint “mission_dates_ordered” is violated."],
      non_field_errors: ["Constraint “mission_dates_ordered” is violated."],
    });
  });

  it("leaves an already-non_field_errors-keyed payload unchanged in shape", async () => {
    const err = await captureError(400, {
      message: "Validation error",
      extra: { fields: { non_field_errors: ["Some other non-field reason."] } },
    });
    expect(fieldErrorsFrom(err)).toEqual({ non_field_errors: ["Some other non-field reason."] });
  });

  it("passes field-keyed errors through unchanged when there is no non-field error", async () => {
    const err = await captureError(400, {
      message: "Validation error",
      extra: { fields: { email: ["Email already in use."] } },
    });
    expect(fieldErrorsFrom(err)).toEqual({ email: ["Email already in use."] });
  });

  it("returns an empty object for a non-AxiosError value", () => {
    expect(fieldErrorsFrom(new Error("boom"))).toEqual({});
  });
});

describe("rowErrorsFrom", () => {
  it("reads the unwrapped shape (extra.fields keyed directly by row index) -- PUT /api/v1/me/skills/", async () => {
    // Exact payload captured live: PUT /api/v1/me/skills/ takes a bulk `items` array
    // as the whole request body, so the row-index keys sit directly under extra.fields.
    const err = await captureError(400, {
      message: "Validation error",
      extra: { fields: { "1": { proficiency: ["Ensure this value is less than or equal to 10."] } } },
    });
    expect(rowErrorsFrom(err)).toEqual({ 1: ["Ensure this value is less than or equal to 10."] });
  });

  it("reads the wrapped shape (extra.fields.items keyed by row index) -- PUT /api/v1/missions/:id/requirements/", async () => {
    // Exact payload captured live: the request body is {"items": [...]}, so the
    // row-index keys sit one level deeper, under "items".
    const err = await captureError(400, {
      message: "Validation error",
      extra: { fields: { items: { "1": { min_proficiency: ["Ensure this value is less than or equal to 10."] } } } },
    });
    expect(rowErrorsFrom(err)).toEqual({ 1: ["Ensure this value is less than or equal to 10."] });
  });

  it("collects multiple failing rows, each keyed by its own index", async () => {
    const err = await captureError(400, {
      message: "Validation error",
      extra: {
        fields: {
          "0": { skill_id: ["This skill does not exist."] },
          "2": { proficiency: ["Ensure this value is greater than or equal to 1."] },
        },
      },
    });
    expect(rowErrorsFrom(err)).toEqual({
      0: ["This skill does not exist."],
      2: ["Ensure this value is greater than or equal to 1."],
    });
  });

  it("does not misread a flat field-keyed error as row-indexed", async () => {
    const err = await captureError(400, {
      message: "Validation error",
      extra: { fields: { name: ["This field may not be blank."] } },
    });
    expect(rowErrorsFrom(err)).toEqual({});
  });

  it("returns an empty object for a non-AxiosError value", () => {
    expect(rowErrorsFrom(new Error("boom"))).toEqual({});
  });
});
