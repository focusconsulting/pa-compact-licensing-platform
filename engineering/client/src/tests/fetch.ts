import { vi } from "vitest";

/** Answers every `fetch` with `body` as JSON; read what was sent from the returned spy's calls. */
export function answerFetch(body: unknown, status = 200) {
  return vi
    .mocked(globalThis.fetch)
    .mockImplementation(() => Promise.resolve(Response.json(body, { status })));
}
