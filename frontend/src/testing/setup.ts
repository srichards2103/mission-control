import "@testing-library/jest-dom";
import { afterAll, afterEach, beforeAll } from "vitest";
import { resetMockData, server } from "./mocks";

// jsdom doesn't implement matchMedia. sonner's <Toaster/> (mounted in main.tsx, and in any
// test that renders through it) reads it unconditionally to resolve the "system" theme, so
// without this stub every such test throws "window.matchMedia is not a function".
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  resetMockData();
});
afterAll(() => server.close());
