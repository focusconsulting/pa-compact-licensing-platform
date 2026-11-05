import { vi } from "vitest";

/** Answers every `fetch` with `body` as JSON; read what was sent from the returned spy's calls. */
export function answerFetch(body: unknown, status = 200) {
  return vi
    .mocked(globalThis.fetch)
    .mockImplementation(() => Promise.resolve(Response.json(body, { status })));
}

type Answer = Response | (() => Response);

/**
 * Answers each `fetch` by its method and path, such as `"POST /api/me/documents"`. A list
 * answers in turn and repeats its last; an unrouted call rejects.
 */
export function routeFetch(routes: Record<string, Answer | Answer[]>) {
  const calls: Record<string, number> = {};
  return vi.mocked(globalThis.fetch).mockImplementation(async (input, init) => {
    const request = input instanceof Request ? input : new Request(input, init);
    const route = `${request.method} ${new URL(request.url).pathname}`;
    const answers = routes[route];
    if (!answers) {
      throw new Error(`fetch not routed: ${route}`);
    }
    const list = Array.isArray(answers) ? answers : [answers];
    const turn = calls[route] ?? 0;
    calls[route] = turn + 1;
    const answer = list[Math.min(turn, list.length - 1)];
    return typeof answer === "function" ? answer() : answer.clone();
  });
}
