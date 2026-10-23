import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "src/api/schema";
import { getCurrentSession } from "src/lib/auth";

// Unset in Storybook, where requests go to the page's own origin.
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

async function bearerToken(): Promise<string> {
  const session = await getCurrentSession();
  if (!session) {
    throw new Error("Not authenticated");
  }
  return `Bearer ${session.getIdToken().getJwtToken()}`;
}

const authorize: Middleware = {
  async onRequest({ request }) {
    request.headers.set("Authorization", await bearerToken());
    return request;
  },
};

/**
 * The API client, typed from the generated schema (ADR-0013). Each call
 * carries the current Cognito session's ID token, which the library refreshes
 * when it has expired.
 */
export const api = createClient<paths>({
  baseUrl: BASE_URL,
  // Looked up per call, not captured at load, so MSW's patched fetch answers in tests and Storybook.
  fetch: (request) => globalThis.fetch(request),
});
api.use(authorize);

/** Authenticated `fetch` for calls the typed client cannot make, such as non-JSON bodies. */
export async function authFetch(
  path: string,
  options?: RequestInit,
): Promise<Response> {
  const authorization = await bearerToken();
  return fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
      Authorization: authorization,
    },
  });
}
