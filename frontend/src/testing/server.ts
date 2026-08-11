import { setupServer } from "msw/node";

// Shared MSW server for tests that need to fake backend responses instead of
// mocking axios/api-client internals directly.
export const server = setupServer();
