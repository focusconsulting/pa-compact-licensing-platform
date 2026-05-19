import { getCurrentSession } from "src/lib/auth";

/**
 * Authenticated fetch wrapper. Retrieves the current Cognito session on every
 * call — the library refreshes the token automatically when it is expired.
 */
export async function authFetch(
  path: string,
  options?: RequestInit,
): Promise<Response> {
  const session = await getCurrentSession();
  if (!session) {
    throw new Error("Not authenticated");
  }

  const token = session.getIdToken().getJwtToken();
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

  return fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
      Authorization: `Bearer ${token}`,
    },
  });
}
