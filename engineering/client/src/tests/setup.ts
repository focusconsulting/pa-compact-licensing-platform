import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, vi, type MockInstance } from "vitest";
import "../i18n/config";

let fetchSpy: MockInstance<typeof fetch>;

// A request no test answers (see `answerFetch`) fails instead of reaching the network.
beforeEach(() => {
  fetchSpy = vi
    .spyOn(globalThis, "fetch")
    .mockRejectedValue(new Error("fetch is not stubbed"));
});
afterEach(() => fetchSpy.mockRestore());
