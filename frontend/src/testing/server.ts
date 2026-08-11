// Re-exports the single shared MSW server instance from ./mocks. There must be
// only one setupServer() active per test run (it patches global http/https
// interceptors), so this file is kept only for backward-compat imports.
export { server } from "./mocks";
