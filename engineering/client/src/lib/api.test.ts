import { describe, it, expect, vi, beforeEach } from "vitest";
import type { CognitoUserSession } from "amazon-cognito-identity-js";
import { http, HttpResponse } from "msw";

import * as authLib from "src/lib/auth";
import { server } from "src/tests/server";
import { api, authFetch } from "./api";

vi.mock("src/lib/auth");

function signInWith(token: string) {
  vi.mocked(authLib.getCurrentSession).mockResolvedValue({
    getIdToken: () => ({ getJwtToken: () => token }),
  } as CognitoUserSession);
}

/** Answers `method` on `path` with what the request carried. */
function echo(method: "get" | "post", path: string) {
  server.use(
    http[method](`*${path}`, async ({ request }) =>
      HttpResponse.json({
        url: request.url,
        authorization: request.headers.get("Authorization"),
        contentType: request.headers.get("Content-Type"),
        body: method === "post" ? await request.text() : null,
      }),
    ),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("api", () => {
  it("returns the generated mock's body for /api/me", async () => {
    signInWith("my-token");

    const { data } = await api.GET("/api/me");

    expect(data?.data.email).toBe("pat.morgan@example.com");
  });

  it("sends the session's ID token to the API's base URL", async () => {
    signInWith("my-token");
    echo("get", "/api/me");

    // The echo handler answers with what the request carried, not a user.
    const { data } = await api.GET("/api/me");

    expect(data).toMatchObject({
      url: "http://api.test/api/me",
      authorization: "Bearer my-token",
    });
  });

  it("throws when not authenticated", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);

    await expect(api.GET("/api/me")).rejects.toThrow("Not authenticated");
  });
});

describe("authFetch", () => {
  it("throws when not authenticated", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);

    await expect(authFetch("/api/test")).rejects.toThrow("Not authenticated");
  });

  it("sends the token with the caller's headers, method, and body", async () => {
    signInWith("token-abc");
    echo("post", "/api/data");

    const response = await authFetch("/api/data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: '{"key":"val"}',
    });

    expect(await response.json()).toEqual({
      url: "http://api.test/api/data",
      authorization: "Bearer token-abc",
      contentType: "application/json",
      body: '{"key":"val"}',
    });
  });
});

describe("without NEXT_PUBLIC_API_BASE_URL", () => {
  it("calls the page's own origin", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", undefined);
    vi.resetModules();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response());
    const { authFetch: relativeFetch } = await import("./api");
    signInWith("token");

    await relativeFetch("/api/test");

    expect(fetchSpy).toHaveBeenCalledWith("/api/test", expect.anything());
    fetchSpy.mockRestore();
    vi.unstubAllEnvs();
  });
});
